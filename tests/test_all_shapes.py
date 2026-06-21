"""Comprehensive provenance test for all build123d shape-creating operations.

Verifies that every face/edge/vertex on the final part has at least one
provenance entry, and that the code_context field points back to the
operation that created or modified it.
"""

import json

import OCP.TopAbs as ta
import pytest
from build123d import (
    Align,
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Circle,
    Cone,
    Cylinder,
    Keep,
    Line,
    Locations,
    Mode,
    Plane,
    Polyline,
    Rectangle,
    RegularPolygon,
    Sphere,
    Torus,
    Wedge,
    add,
    chamfer,
    draft,
    extrude,
    fillet,
    loft,
    make_face,
    offset,
    revolve,
    scale,
    split,
    sweep,
    thicken,
)
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape
from ocp_provenance import (
    ProvenanceJournal,
    build_provenance_map,
    build_provenance_maps,
    provenance,
)


def _count_subshapes(wrapped, shape_type):
    m = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(wrapped, shape_type, m)
    return m.Extent()


def _face_count(wrapped):
    return _count_subshapes(wrapped, ta.TopAbs_ShapeEnum.TopAbs_FACE)


def _edge_count(wrapped):
    return _count_subshapes(wrapped, ta.TopAbs_ShapeEnum.TopAbs_EDGE)


def _vertex_count(wrapped):
    return _count_subshapes(wrapped, ta.TopAbs_ShapeEnum.TopAbs_VERTEX)


def _provenance_coverage(journal, builder):
    """Return (total_faces, matched_faces, prov_map) for a built part."""
    wrapped = builder.part.wrapped
    prov = build_provenance_map(journal, builder)
    total = _face_count(wrapped)
    matched = sum(1 for k in prov if k.startswith("faces/"))
    return total, matched, prov


def _assert_all_faces_have_provenance(journal, builder, label=""):
    total, matched, prov = _provenance_coverage(journal, builder)
    assert total > 0, f"{label}: part has no faces"
    assert matched == total, f"{label}: {matched}/{total} faces have provenance"
    return prov


def _assert_provenance_mentions(prov, substring, category="faces"):
    """At least one entry in the given category mentions substring in code_context."""
    for key, locs in prov.items():
        if not key.startswith(f"{category}/"):
            continue
        for loc in locs:
            if substring in loc.get("code_context", ""):
                return
    raise AssertionError(
        f"No {category} entry mentions '{substring}'. "
        f"Keys: {[k for k in prov if k.startswith(f'{category}/')]}"
    )


# ---------------------------------------------------------------------------
# Part primitives
# ---------------------------------------------------------------------------


class TestPartPrimitives:
    """Each 3D primitive used alone in a BuildPart."""

    def test_box(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
        prov = _assert_all_faces_have_provenance(j, p, "Box")
        assert any(
            "Box" in loc["code_context"] for locs in prov.values() for loc in locs
        )

    def test_cylinder(self):
        with provenance() as j:
            with BuildPart() as p:
                Cylinder(5, 10)
        _assert_all_faces_have_provenance(j, p, "Cylinder")

    def test_sphere(self):
        with provenance() as j:
            with BuildPart() as p:
                Sphere(5)
        _assert_all_faces_have_provenance(j, p, "Sphere")

    def test_cone(self):
        with provenance() as j:
            with BuildPart() as p:
                Cone(5, 2, 10)
        _assert_all_faces_have_provenance(j, p, "Cone")

    def test_torus(self):
        with provenance() as j:
            with BuildPart() as p:
                Torus(10, 3)
        _assert_all_faces_have_provenance(j, p, "Torus")

    def test_wedge(self):
        with provenance() as j:
            with BuildPart() as p:
                Wedge(10, 10, 10, 2, 2, 8, 8)
        _assert_all_faces_have_provenance(j, p, "Wedge")


# ---------------------------------------------------------------------------
# Modifier operations (fillet, chamfer, draft, hollow)
# ---------------------------------------------------------------------------


class TestModifiers:
    def test_fillet(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                fillet(p.edges(), 1)
        prov = _assert_all_faces_have_provenance(j, p, "Box+fillet")
        assert any(
            "fillet" in loc["code_context"] for locs in prov.values() for loc in locs
        )

    def test_chamfer(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                chamfer(p.edges(), 1)
        prov = _assert_all_faces_have_provenance(j, p, "Box+chamfer")
        assert any(
            "chamfer" in loc["code_context"] for locs in prov.values() for loc in locs
        )

    def test_draft(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 20)
                sides = p.faces().filter_by(Axis.Z, reverse=True)
                draft(sides, Plane.XY, 3)
        _assert_all_faces_have_provenance(j, p, "Box+draft")

    def test_fillet_cylinder(self):
        with provenance() as j:
            with BuildPart() as p:
                Cylinder(5, 10)
                fillet(p.edges(), 1)
        _assert_all_faces_have_provenance(j, p, "Cylinder+fillet")


# ---------------------------------------------------------------------------
# Offset and split
# ---------------------------------------------------------------------------


class TestOffsetAndSplit:
    def test_offset_3d(self):
        """offset creates inner faces with kind='created'."""
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                offset(amount=-1, openings=p.faces().sort_by(Axis.Z)[-1:])
        prov = _assert_all_faces_have_provenance(j, p, "offset(Box)")
        assert any(
            "offset" in loc["code_context"] for locs in prov.values() for loc in locs
        )
        has_created = any(
            "offset" in loc["code_context"] and loc["kind"] == "created"
            for locs in prov.values()
            for loc in locs
        )
        assert has_created, "inner faces should have kind='created'"

    def test_split(self):
        """split preserves provenance on kept faces."""
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                split(bisect_by=Plane.XZ, keep=Keep.TOP)
        prov = _assert_all_faces_have_provenance(j, p, "split(Box)")
        assert any(
            "split" in loc["code_context"] for locs in prov.values() for loc in locs
        )

    def test_split_preserves_origin(self):
        """Surviving faces after split trace back to the original Box."""
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                split(bisect_by=Plane.XZ, keep=Keep.TOP)
        prov = _assert_all_faces_have_provenance(j, p, "split origin")
        has_box_origin = any(
            "Box" in loc["code_context"] and loc["kind"] == "created"
            for locs in prov.values()
            for loc in locs
        )
        assert has_box_origin, "surviving faces should trace to Box"


# ---------------------------------------------------------------------------
# Scale
# ---------------------------------------------------------------------------


class TestScale:
    def test_uniform_scale(self):
        """Uniform scale preserves all faces with modified provenance."""
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                scale(by=2)
        prov = _assert_all_faces_have_provenance(j, p, "scale(Box)")
        assert any(
            "scale" in loc["code_context"] and loc["kind"] == "modified"
            for locs in prov.values()
            for loc in locs
        )

    def test_nonuniform_scale(self):
        """Non-uniform scale (via GTransform) also preserves provenance."""
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                scale(by=(2, 1, 0.5))
        prov = _assert_all_faces_have_provenance(j, p, "scale(Box, non-uniform)")
        assert any(
            "scale" in loc["code_context"] for locs in prov.values() for loc in locs
        )

    def test_scale_preserves_origin(self):
        """Scaled faces trace back to the original Box."""
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                scale(by=2)
        prov = _assert_all_faces_have_provenance(j, p, "scale origin")
        has_box_origin = any(
            "Box" in loc["code_context"] and loc["kind"] == "created"
            for locs in prov.values()
            for loc in locs
        )
        assert has_box_origin, "scaled faces should trace to Box"


# ---------------------------------------------------------------------------
# Boolean operations
# ---------------------------------------------------------------------------


class TestBooleans:
    def test_subtract(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                Cylinder(3, 12, mode=Mode.SUBTRACT)
        prov = _assert_all_faces_have_provenance(j, p, "Box-Cyl")
        assert any(
            "Cylinder" in loc["code_context"] for locs in prov.values() for loc in locs
        )

    def test_intersect(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                Sphere(7, mode=Mode.INTERSECT)
        _assert_all_faces_have_provenance(j, p, "Box∩Sphere")

    def test_add(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 5)
                with BuildPart(Plane.XY.offset(5)):
                    Cylinder(3, 5)
        _assert_all_faces_have_provenance(j, p, "Box+Cyl")

    def test_subtract_then_fillet(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(20, 20, 20)
                Cylinder(5, 25, mode=Mode.SUBTRACT)
                fillet(p.edges(), 1)
        _assert_all_faces_have_provenance(j, p, "Box-Cyl+fillet")


# ---------------------------------------------------------------------------
# Sketch → extrude / revolve / sweep / loft / thicken
# ---------------------------------------------------------------------------


class TestSketchOps:
    def test_extrude_rectangle(self):
        with provenance() as j:
            with BuildPart() as p:
                with BuildSketch():
                    Rectangle(10, 10)
                extrude(amount=5)
        _assert_all_faces_have_provenance(j, p, "extrude(Rectangle)")

    def test_extrude_polygon(self):
        with provenance() as j:
            with BuildPart() as p:
                with BuildSketch():
                    RegularPolygon(5, 6)
                extrude(amount=5)
        _assert_all_faces_have_provenance(j, p, "extrude(Hexagon)")

    def test_revolve(self):
        with provenance() as j:
            with BuildPart() as p:
                with BuildSketch(Plane.XZ):
                    with BuildLine():
                        Polyline([(0, 0), (5, 0), (5, 10), (0, 10)], close=True)
                    make_face()
                revolve(axis=Axis.Z)
        _assert_all_faces_have_provenance(j, p, "revolve")

    def test_loft(self):
        with provenance() as j:
            with BuildPart() as p:
                with BuildSketch(Plane.XY):
                    Rectangle(10, 10)
                with BuildSketch(Plane.XY.offset(10)):
                    RegularPolygon(4, 6)
                loft()
        _assert_all_faces_have_provenance(j, p, "loft")

    def test_sweep(self):
        with provenance() as j:
            with BuildPart() as p:
                with BuildLine():
                    Line((0, 0, 0), (0, 0, 20))
                with BuildSketch():
                    Rectangle(4, 4)
                sweep()
        _assert_all_faces_have_provenance(j, p, "sweep")

    def test_thicken(self):
        with provenance() as j:
            with BuildPart() as p:
                with BuildSketch():
                    Rectangle(10, 10)
                thicken(amount=3)
        _assert_all_faces_have_provenance(j, p, "thicken")


# ---------------------------------------------------------------------------
# Multi-part scenarios
# ---------------------------------------------------------------------------


class TestMultiPart:
    def test_two_boxes(self):
        with provenance() as j:
            with BuildPart() as a:
                Box(10, 10, 10)
            with BuildPart() as b:
                Box(5, 5, 5)
        maps = build_provenance_maps(j, a, b)
        assert len(maps) == 2
        assert sum(1 for k in maps[0] if k.startswith("faces/")) == 6
        assert sum(1 for k in maps[1] if k.startswith("faces/")) == 6

    def test_box_and_sphere(self):
        with provenance() as j:
            with BuildPart() as a:
                Box(10, 10, 10)
            with BuildPart() as b:
                Sphere(5)
        maps = build_provenance_maps(j, a, b)
        a_faces = sum(1 for k in maps[0] if k.startswith("faces/"))
        b_faces = sum(1 for k in maps[1] if k.startswith("faces/"))
        assert a_faces == 6
        assert b_faces == 1

    def test_three_parts_order(self):
        with provenance() as j:
            with BuildPart() as a:
                Box(10, 10, 10)
            with BuildPart() as b:
                Cylinder(5, 10)
            with BuildPart() as c:
                Sphere(3)
        maps = build_provenance_maps(j, a, b, c)
        assert len(maps) == 3
        assert all(len(m) > 0 for m in maps)
        # Box code_context should mention Box, Cylinder should mention Cylinder, etc.
        a_ctx = {loc["code_context"] for locs in maps[0].values() for loc in locs}
        b_ctx = {loc["code_context"] for locs in maps[1].values() for loc in locs}
        c_ctx = {loc["code_context"] for locs in maps[2].values() for loc in locs}
        assert any("Box" in c for c in a_ctx)
        assert any("Cylinder" in c for c in b_ctx)
        assert any("Sphere" in c for c in c_ctx)

    def test_complex_parts_no_collision(self):
        """Two complex parts stitched with different leaf IDs have no key overlap."""
        with provenance() as j:
            with BuildPart() as a:
                Box(10, 10, 10)
                fillet(a.edges(), 1)
            with BuildPart() as b:
                Cylinder(5, 10)
                chamfer(b.edges(), 0.5)
        maps = build_provenance_maps(j, a, b)
        stitched = {}
        for prefix, m in zip(["/G/A", "/G/B"], maps):
            for key, val in m.items():
                full = f"{prefix}/{key}"
                assert full not in stitched, f"collision: {full}"
                stitched[full] = val
        assert len(stitched) > 0


# ---------------------------------------------------------------------------
# Edge and vertex provenance
# ---------------------------------------------------------------------------


class TestEdgesAndVertices:
    def test_box_edges_have_provenance(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
        prov = build_provenance_map(j, p)
        edge_keys = [k for k in prov if k.startswith("edges/")]
        total_edges = _edge_count(p.part.wrapped)
        assert len(edge_keys) == total_edges

    def test_box_vertices_have_provenance(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
        prov = build_provenance_map(j, p)
        vert_keys = [k for k in prov if k.startswith("vertices/")]
        total_verts = _vertex_count(p.part.wrapped)
        assert len(vert_keys) == total_verts

    def test_fillet_creates_new_edges(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                fillet(p.edges(), 1)
        prov = build_provenance_map(j, p)
        edge_keys = [k for k in prov if k.startswith("edges/")]
        total_edges = _edge_count(p.part.wrapped)
        assert len(edge_keys) == total_edges
        assert any(
            "fillet" in loc["code_context"] for locs in prov.values() for loc in locs
        )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_json_round_trip(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                fillet(p.edges(), 1)
        prov = build_provenance_map(j, p)
        dumped = json.dumps(prov)
        loaded = json.loads(dumped)
        assert loaded == prov

    def test_multi_part_json_round_trip(self):
        with provenance() as j:
            with BuildPart() as a:
                Box(10, 10, 10)
            with BuildPart() as b:
                Sphere(5)
        maps = build_provenance_maps(j, a, b)
        for m in maps:
            dumped = json.dumps(m)
            loaded = json.loads(dumped)
            assert loaded == m


# ---------------------------------------------------------------------------
# Source location quality
# ---------------------------------------------------------------------------


class TestSourceLocations:
    def test_location_fields_present(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
        prov = build_provenance_map(j, p)
        for key, locs in prov.items():
            for loc in locs:
                assert "filename" in loc
                assert "lineno" in loc
                assert "function" in loc
                assert "code_context" in loc
                assert "kind" in loc
                assert loc["filename"].endswith(".py")
                assert isinstance(loc["lineno"], int)

    def test_code_context_matches_operation(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(20, 20, 20)
                Cylinder(3, 25, mode=Mode.SUBTRACT)
                fillet(p.edges(), 0.5)
        prov = build_provenance_map(j, p)
        all_contexts = set()
        for locs in prov.values():
            for loc in locs:
                all_contexts.add(loc["code_context"])
        assert any("Box" in c for c in all_contexts)
        assert any("Cylinder" in c for c in all_contexts)
        assert any("fillet" in c for c in all_contexts)

    def test_kind_field_created_vs_modified(self):
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                fillet(p.edges(), 1)
        prov = build_provenance_map(j, p)
        kinds = set()
        for locs in prov.values():
            for loc in locs:
                kinds.add(loc["kind"])
        assert "created" in kinds or "modified" in kinds

    def test_boolean_split_created_vs_modified(self):
        """Boolean subtract: hole faces are 'created', surviving faces 'modified'."""
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
                Cylinder(3, 12, mode=Mode.SUBTRACT)
        prov = build_provenance_map(j, p)
        has_bool_created = False
        has_bool_modified = False
        for locs in prov.values():
            for loc in locs:
                if "Cylinder" in loc.get("code_context", ""):
                    if loc["kind"] == "created":
                        has_bool_created = True
                    elif loc["kind"] == "modified":
                        has_bool_modified = True
        assert has_bool_created, "hole faces should have kind='created'"
        assert has_bool_modified, "surviving faces should have kind='modified'"


# ---------------------------------------------------------------------------
# Standalone BuildSketch and BuildLine
# ---------------------------------------------------------------------------


class TestStandaloneSketchAndLine:
    def test_sketch_rectangle(self):
        """Standalone BuildSketch faces/edges/vertices have provenance."""
        with provenance() as j:
            with BuildSketch() as s:
                Rectangle(10, 10)
        prov = build_provenance_map(j, s)
        faces = [k for k in prov if k.startswith("faces/")]
        edges = [k for k in prov if k.startswith("edges/")]
        verts = [k for k in prov if k.startswith("vertices/")]
        assert len(faces) == 1
        assert len(edges) == 4
        assert len(verts) == 4
        assert all(
            "Rectangle" in loc["code_context"] for locs in prov.values() for loc in locs
        )

    def test_sketch_circle(self):
        with provenance() as j:
            with BuildSketch() as s:
                Circle(5)
        prov = build_provenance_map(j, s)
        faces = [k for k in prov if k.startswith("faces/")]
        assert len(faces) == 1
        assert any(
            "Circle" in loc["code_context"] for locs in prov.values() for loc in locs
        )

    def test_sketch_boolean(self):
        """Sketch with subtract: face traces to original creator."""
        with provenance() as j:
            with BuildSketch() as s:
                Rectangle(20, 20)
                Circle(3, mode=Mode.SUBTRACT)
        prov = build_provenance_map(j, s)
        faces = [k for k in prov if k.startswith("faces/")]
        assert len(faces) >= 1
        first_created = None
        for loc in prov[faces[0]]:
            if loc["kind"] == "created":
                first_created = loc
                break
        assert first_created is not None
        assert "Rectangle" in first_created["code_context"]

    def test_line_two_segments(self):
        """BuildLine edges have provenance."""
        with provenance() as j:
            with BuildLine() as l:
                Line((0, 0), (10, 0))
                Line((10, 0), (10, 10))
        prov = build_provenance_map(j, l)
        edges = [k for k in prov if k.startswith("edges/")]
        assert len(edges) == 2
        assert any(
            "Line" in loc["code_context"] for locs in prov.values() for loc in locs
        )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_journal(self):
        """Journal with no operations produces empty map."""
        j = ProvenanceJournal()
        with BuildPart() as p:
            Box(10, 10, 10)
        prov = build_provenance_map(j, p)
        assert prov == {}

    def test_non_shape_object(self):
        """Non-shape objects produce empty dict in maps list."""
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
        maps = build_provenance_maps(j, "not a shape", 42)
        assert maps == [{}, {}]

    def test_single_object_maps_vs_map(self):
        """build_provenance_maps with one object matches build_provenance_map."""
        with provenance() as j:
            with BuildPart() as p:
                Box(10, 10, 10)
        single = build_provenance_map(j, p)
        multi = build_provenance_maps(j, p)
        assert len(multi) == 1
        assert multi[0] == single
