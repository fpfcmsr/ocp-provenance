"""Bridge between ocp-provenance and vscode-ocp-cad-viewer.

Produces provenance maps keyed by viewer sub-shape paths
(e.g. "faces/faces_0") so the viewer backend can look up source
locations when the user clicks a shape.
"""

from __future__ import annotations

from typing import Any

import OCP.TopAbs as ta
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape

from ._types import SourceLocation
from .journal import ProvenanceJournal

_VIEWER_TYPES = [
    (ta.TopAbs_ShapeEnum.TopAbs_FACE, "faces", "faces"),
    (ta.TopAbs_ShapeEnum.TopAbs_EDGE, "edges", "edges"),
    (ta.TopAbs_ShapeEnum.TopAbs_VERTEX, "vertices", "vertices"),
]


def _get_wrapped(obj: Any):
    # Prefer _obj.wrapped for builders — the public properties (.sketch, .line)
    # may re-wrap the shape (e.g. BuildSketch.sketch applies from_local_coords
    # on every access, producing new sub-shape pointers that don't match the
    # registry).  _obj is the stable internal state.
    internal = getattr(obj, "_obj", None)
    if internal is not None and hasattr(internal, "wrapped"):
        return internal.wrapped
    if hasattr(obj, "part"):
        return obj.part.wrapped
    if hasattr(obj, "wrapped"):
        return obj.wrapped
    return None


def _loc_to_dict(loc: SourceLocation) -> dict:
    return {
        "filename": loc.filename,
        "lineno": loc.lineno,
        "function": loc.function,
        "code_context": loc.code_context,
        "kind": loc.kind,
    }


def _build_one(journal: ProvenanceJournal, wrapped) -> dict[str, list[dict]]:
    """Build a provenance map for a single shape's sub-shapes."""
    result: dict[str, list[dict]] = {}
    for shape_type, category, prefix in _VIEWER_TYPES:
        shape_map = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(wrapped, shape_type, shape_map)
        for i in range(shape_map.Extent()):
            sub = shape_map.FindKey(i + 1)
            locs = journal.registry.lookup(hash(sub))
            if locs:
                key = f"{category}/{prefix}_{i}"
                result[key] = [_loc_to_dict(loc) for loc in locs]
    return result


def build_provenance_map(
    journal: ProvenanceJournal,
    *cad_objs: Any,
) -> dict[str, list[dict]]:
    """Build a flat provenance map for a single object.

    For multi-object ``show()`` calls, use ``build_provenance_maps``
    (plural) instead.
    """
    result: dict[str, list[dict]] = {}
    for obj in cad_objs:
        wrapped = _get_wrapped(obj)
        if wrapped is None:
            continue
        result.update(_build_one(journal, wrapped))
    return result


def build_provenance_maps(
    journal: ProvenanceJournal,
    *cad_objs: Any,
) -> list[dict[str, list[dict]]]:
    """Build one provenance map per object, for multi-part stitching.

    Returns a list (same length as *cad_objs*) where each element is a
    dict keyed by relative sub-shape path (``faces/faces_0``, etc.).
    Objects that have no provenance or no ``.wrapped`` produce an empty
    dict in their slot.

    The caller (typically ``show()``) walks the viewer's mapping tree to
    find each leaf's ID and prefixes the keys accordingly.
    """
    result: list[dict[str, list[dict]]] = []
    for obj in cad_objs:
        wrapped = _get_wrapped(obj)
        if wrapped is None:
            result.append({})
            continue
        result.append(_build_one(journal, wrapped))
    return result
