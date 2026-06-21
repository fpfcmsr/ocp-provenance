from __future__ import annotations

import contextvars
from typing import Any

import OCP.TopAbs as ta
from build123d.topology import operation_journal
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS_Shape
from OCP.TopTools import TopTools_IndexedMapOfShape

from ._types import SourceLocation
from .framewalker import find_user_frame
from .history import trace_boolean, trace_boolean_split, trace_maker, trace_maker_split
from .registry import ProvenanceRegistry

_TRACKED_TYPES = (ta.TopAbs_ShapeEnum.TopAbs_FACE,)


def _iter_subshapes(
    wrapped: TopoDS_Shape,
    shape_type: ta.TopAbs_ShapeEnum | None = None,
) -> list[TopoDS_Shape]:
    """Extract unique sub-shapes from a TopoDS_Shape.

    If shape_type is None, extracts all tracked types.
    Uses TopExp.MapShapes_s for deduplication (shared sub-shapes visited once).
    """
    types = (shape_type,) if shape_type is not None else _TRACKED_TYPES
    result: list[TopoDS_Shape] = []
    for st in types:
        m = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(wrapped, st, m)
        for i in range(m.Extent()):
            result.append(m.FindKey(i + 1))
    return result


class ProvenanceJournal:
    """Implements the OperationJournal protocol for provenance tracking.

    Usage::

        from ocp_provenance import provenance, get_provenance

        with provenance() as journal:
            with BuildPart() as p:
                Box(10, 10, 10)
                fillet(p.edges(), 1)

        for face in p.part.faces():
            locs = get_provenance(journal, face)
            for loc in locs:
                print(f"  {loc.filename}:{loc.lineno} — {loc.code_context}")
    """

    def __init__(self) -> None:
        self.registry = ProvenanceRegistry()
        self._token: contextvars.Token | None = None

    def record(self, event: str, /, **kwargs: Any) -> None:
        """Handle an operation event from build123d."""
        loc = find_user_frame(extra_skip=0)

        if event == "boolean":
            self._handle_boolean(loc, **kwargs)
        elif event == "context_add":
            self._handle_context_add(loc, **kwargs)
        elif event in (
            "fillet",
            "chamfer",
            "hollow",
            "draft",
            "thicken",
            "offset_3d",
            "split",
            "scale",
        ):
            self._handle_maker_op(loc, **kwargs)
        elif event in ("extrude", "revolve", "sweep", "loft"):
            self._handle_creation(loc, **kwargs)

    def _handle_boolean(
        self,
        loc: SourceLocation | None,
        *,
        operation: Any,
        upgrader: Any,
        args: list,
        tools: list,
        result: Any,
    ) -> None:
        if loc is None:
            return

        generated_hashes: set[int] = set()
        modified_hashes: set[int] = set()

        input_subshapes: list[TopoDS_Shape] = []
        for shape_list in (args, tools):
            for shape in shape_list:
                wrapped = getattr(shape, "wrapped", None) or getattr(
                    shape, "_wrapped", None
                )
                if wrapped is not None:
                    input_subshapes.extend(_iter_subshapes(wrapped))

        for in_shape in input_subshapes:
            old_hash = hash(in_shape)
            modified, generated = trace_boolean_split(in_shape, operation, upgrader)
            for desc in modified:
                new_hash = hash(desc)
                modified_hashes.add(new_hash)
                self.registry.propagate(old_hash, new_hash)
            for desc in generated:
                generated_hashes.add(hash(desc))

        loc_modified = SourceLocation(
            filename=loc.filename,
            lineno=loc.lineno,
            function=loc.function,
            code_context=loc.code_context,
            kind="modified",
        )
        loc_created = SourceLocation(
            filename=loc.filename,
            lineno=loc.lineno,
            function=loc.function,
            code_context=loc.code_context,
            kind="created",
        )
        result_wrapped = getattr(result, "wrapped", None) or getattr(
            result, "_wrapped", None
        )
        if result_wrapped is not None:
            for subshape in _iter_subshapes(result_wrapped):
                h = hash(subshape)
                if h in generated_hashes:
                    self.registry.assign(h, loc_created)
                else:
                    self.registry.assign(h, loc_modified)

    def _handle_context_add(
        self,
        loc: SourceLocation | None,
        *,
        builder: Any,
        objects: list,
        mode: Any,
        before: Any,
        after: Any,
        lasts: dict,
    ) -> None:
        if loc is None:
            return

        if hasattr(mode, "name") and mode.name == "REPLACE":
            return

        from build123d.topology import Face

        for shape in lasts.get(Face, []):
            wrapped = getattr(shape, "wrapped", None)
            if wrapped is not None:
                self.registry.assign(hash(wrapped), loc)

    def _handle_maker_op(
        self,
        loc: SourceLocation | None,
        *,
        builder: Any,
        input_shape: Any,
        result: Any,
    ) -> None:
        if loc is None:
            return

        generated_hashes: set[int] = set()
        modified_hashes: set[int] = set()

        input_wrapped = getattr(input_shape, "wrapped", None)
        if input_wrapped is not None:
            for in_shape in _iter_subshapes(input_wrapped):
                old_hash = hash(in_shape)
                modified, generated = trace_maker_split(in_shape, builder)
                for desc in modified:
                    new_hash = hash(desc)
                    modified_hashes.add(new_hash)
                    self.registry.propagate(old_hash, new_hash)
                for desc in generated:
                    generated_hashes.add(hash(desc))

        loc_modified = SourceLocation(
            filename=loc.filename,
            lineno=loc.lineno,
            function=loc.function,
            code_context=loc.code_context,
            kind="modified",
        )
        loc_created = SourceLocation(
            filename=loc.filename,
            lineno=loc.lineno,
            function=loc.function,
            code_context=loc.code_context,
            kind="created",
        )

        result_wrapped = getattr(result, "wrapped", None)
        if result_wrapped is not None:
            for subshape in _iter_subshapes(result_wrapped):
                h = hash(subshape)
                if h in generated_hashes:
                    self.registry.assign(h, loc_created)
                else:
                    self.registry.assign(h, loc_modified)

    def _handle_creation(
        self,
        loc: SourceLocation | None,
        **kwargs: Any,
    ) -> None:
        if loc is None:
            return

        result = kwargs.get("result")
        if result is None:
            return

        result_wrapped = getattr(result, "wrapped", None)
        if result_wrapped is not None:
            for subshape in _iter_subshapes(result_wrapped):
                self.registry.assign(hash(subshape), loc)

    def activate(self) -> None:
        """Set this journal as the active operation journal."""
        self._token = operation_journal.set(self)

    def deactivate(self) -> None:
        """Remove this journal from the active context."""
        if self._token is not None:
            operation_journal.reset(self._token)
            self._token = None

    def __enter__(self) -> ProvenanceJournal:
        self.activate()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        self.deactivate()
        return False
