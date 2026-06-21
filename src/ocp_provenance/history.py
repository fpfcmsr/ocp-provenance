from __future__ import annotations

from OCP.TopoDS import TopoDS_Shape
from OCP.TopTools import TopTools_ListOfShape


def _toptools_list_to_list(tl: TopTools_ListOfShape) -> list[TopoDS_Shape]:
    """Convert a TopTools_ListOfShape to a Python list.

    Uses IsEmpty/First to avoid pybind11 iterator overhead (~180µs)
    for the common 0- and 1-element cases.
    """
    if tl.IsEmpty():
        return []
    if tl.Size() == 1:
        return [tl.First()]
    return [s for s in tl]


def trace_boolean(
    source_face: TopoDS_Shape,
    operation,
    upgrader,
) -> list[TopoDS_Shape]:
    """Trace a source face through a boolean operation + optional upgrader.

    Returns the list of faces in the final shape that descend from source_face.
    """
    if operation.IsDeleted(source_face):
        return []

    modified = _toptools_list_to_list(operation.Modified(source_face))
    generated = _toptools_list_to_list(operation.Generated(source_face))

    descendants = modified + generated
    if not descendants:
        descendants = [source_face]

    if upgrader is not None:
        try:
            history = upgrader.History()
        except Exception:
            return descendants
        final = []
        for desc in descendants:
            if history.IsRemoved(desc):
                continue
            merged = _toptools_list_to_list(history.Modified(desc))
            if merged:
                final.extend(merged)
            else:
                final.append(desc)
        return final

    return descendants


def trace_boolean_split(
    source_face: TopoDS_Shape,
    operation,
    upgrader,
) -> tuple[list[TopoDS_Shape], list[TopoDS_Shape]]:
    """Like trace_boolean but returns (modified, generated) separately.

    After upgrader pass, each descendant is classified by whether it came
    from the operation's Modified or Generated list.
    """
    if operation.IsDeleted(source_face):
        return [], []

    modified = _toptools_list_to_list(operation.Modified(source_face))
    generated = _toptools_list_to_list(operation.Generated(source_face))

    if upgrader is None:
        return modified, generated

    try:
        history = upgrader.History()
    except Exception:
        return modified, generated

    def _apply_upgrader(shapes: list[TopoDS_Shape]) -> list[TopoDS_Shape]:
        final: list[TopoDS_Shape] = []
        for desc in shapes:
            if history.IsRemoved(desc):
                continue
            merged = _toptools_list_to_list(history.Modified(desc))
            if merged:
                final.extend(merged)
            else:
                final.append(desc)
        return final

    return _apply_upgrader(modified), _apply_upgrader(generated)


def trace_maker(
    source_face: TopoDS_Shape,
    builder,
) -> list[TopoDS_Shape]:
    """Trace a source face through a BRepBuilderAPI_MakeShape-derived builder.

    Works with BRepFilletAPI_MakeFillet, MakeChamfer,
    BRepOffsetAPI_MakeThickSolid, BRepOffsetAPI_DraftAngle, etc.
    """
    modified, generated = trace_maker_split(source_face, builder)
    descendants = modified + generated
    return descendants if descendants else [source_face]


def trace_maker_split(
    source_face: TopoDS_Shape,
    builder,
) -> tuple[list[TopoDS_Shape], list[TopoDS_Shape]]:
    """Like trace_maker but returns (modified, generated) separately."""
    try:
        modified = _toptools_list_to_list(builder.Modified(source_face))
    except Exception:
        modified = []
    try:
        generated = _toptools_list_to_list(builder.Generated(source_face))
    except Exception:
        generated = []
    return modified, generated
