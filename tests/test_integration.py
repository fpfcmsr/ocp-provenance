"""Integration tests for ocp-provenance with build123d."""

import pytest
from ocp_provenance import SourceLocation, get_provenance, provenance


class TestProvenanceBasic:
    def test_box_faces_have_provenance(self):
        from build123d import Box, BuildPart

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)

        result = part.part
        faces = result.faces()
        assert len(faces) == 6

        for face in faces:
            locs = get_provenance(journal, face)
            assert len(locs) > 0, f"Face has no provenance"
            assert any("Box" in (loc.code_context or "") for loc in locs)

    def test_fillet_provenance(self):
        from build123d import Box, BuildPart, fillet

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)
                fillet(part.edges(), 1)

        result = part.part
        faces = result.faces()
        assert len(faces) > 6  # fillet adds faces

        provenance_found = False
        for face in faces:
            locs = get_provenance(journal, face)
            if locs:
                provenance_found = True
        assert provenance_found, "No faces have provenance"

    def test_boolean_subtract_provenance(self):
        from build123d import Box, BuildPart, Cylinder, Mode

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)
                Cylinder(3, 12, mode=Mode.SUBTRACT, align=(None, None, None))

        result = part.part
        faces = result.faces()

        provenance_found = False
        for face in faces:
            locs = get_provenance(journal, face)
            if locs:
                provenance_found = True
        assert provenance_found, "No faces have provenance after boolean subtract"

    def test_journal_deactivates_on_exit(self):
        from build123d.topology import operation_journal

        with provenance() as journal:
            assert operation_journal.get(None) is journal
        assert operation_journal.get(None) is None

    def test_no_provenance_without_journal(self):
        from build123d import Box, BuildPart
        from build123d.topology import operation_journal

        assert operation_journal.get(None) is None
        with BuildPart() as part:
            Box(10, 10, 10)
        # No crash, no provenance — journal was not active

    def test_source_location_fields(self):
        from build123d import Box, BuildPart

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)

        result = part.part
        face = result.faces()[0]
        locs = get_provenance(journal, face)
        assert len(locs) > 0

        loc = locs[0]
        assert isinstance(loc, SourceLocation)
        assert loc.filename.endswith(".py")
        assert loc.lineno > 0
        assert loc.function is not None

    def test_edge_provenance(self):
        from build123d import Box, BuildPart

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)

        result = part.part
        edges = result.edges()
        assert len(edges) == 12

        tracked = sum(1 for e in edges if get_provenance(journal, e))
        assert tracked == 12, f"Only {tracked}/12 edges have provenance"

    def test_vertex_provenance(self):
        from build123d import Box, BuildPart

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)

        result = part.part
        vertices = result.vertices()
        assert len(vertices) == 8

        tracked = sum(1 for v in vertices if get_provenance(journal, v))
        assert tracked == 8, f"Only {tracked}/8 vertices have provenance"

    def test_edge_provenance_through_fillet(self):
        from build123d import Box, BuildPart, fillet

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)
                fillet(part.edges(), 1)

        result = part.part
        edges = result.edges()

        tracked = sum(1 for e in edges if get_provenance(journal, e))
        assert tracked == len(edges), (
            f"Only {tracked}/{len(edges)} edges have provenance after fillet"
        )

    def test_build_provenance_map_face_count(self):
        from build123d import Box, BuildPart
        from ocp_provenance import build_provenance_map

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)

        prov = build_provenance_map(journal, part)
        face_keys = [k for k in prov if k.startswith("faces/")]
        edge_keys = [k for k in prov if k.startswith("edges/")]
        vertex_keys = [k for k in prov if k.startswith("vertices/")]

        assert len(face_keys) == 6
        assert len(edge_keys) == 12
        assert len(vertex_keys) == 8

    def test_build_provenance_map_key_format(self):
        from build123d import Box, BuildPart
        from ocp_provenance import build_provenance_map

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)

        prov = build_provenance_map(journal, part)
        for key in prov:
            assert key.startswith(
                ("faces/faces_", "edges/edges_", "vertices/vertices_")
            )
            # Value is a list of location dicts
            locs = prov[key]
            assert isinstance(locs, list)
            assert len(locs) > 0
            for loc in locs:
                assert "filename" in loc
                assert "lineno" in loc
                assert "kind" in loc

    def test_build_provenance_map_serializable(self):
        import json

        from build123d import Box, BuildPart
        from ocp_provenance import build_provenance_map

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)

        prov = build_provenance_map(journal, part)
        roundtripped = json.loads(json.dumps(prov))
        assert roundtripped == prov

    def test_build_provenance_map_matches_tessellate_order(self):
        from build123d import Box, BuildPart, Cylinder, Mode, fillet
        from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX
        from OCP.TopExp import TopExp
        from OCP.TopTools import TopTools_IndexedMapOfShape
        from ocp_provenance import build_provenance_map

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)
                Cylinder(3, 12, mode=Mode.SUBTRACT, align=(None, None, None))
                fillet(part.edges(), 0.5)

        prov = build_provenance_map(journal, part)
        w = part.part.wrapped

        for typ, prefix in [
            (TopAbs_FACE, "faces"),
            (TopAbs_EDGE, "edges"),
            (TopAbs_VERTEX, "vertices"),
        ]:
            shape_map = TopTools_IndexedMapOfShape()
            TopExp.MapShapes_s(w, typ, shape_map)
            expected_count = shape_map.Extent()
            actual_keys = [k for k in prov if k.startswith(f"{prefix}/")]
            assert len(actual_keys) == expected_count, (
                f"{prefix}: expected {expected_count} keys, got {len(actual_keys)}"
            )

    def test_build_provenance_map_empty_without_journal(self):
        from build123d import Box, BuildPart
        from ocp_provenance import build_provenance_map

        with provenance() as journal:
            pass  # no shapes built

        with BuildPart() as part:
            Box(10, 10, 10)

        prov = build_provenance_map(journal, part)
        assert len(prov) == 0

    def test_build_provenance_maps_length(self):
        from build123d import Box, BuildPart, Sphere
        from ocp_provenance import build_provenance_maps

        with provenance() as journal:
            with BuildPart() as part_a:
                Box(10, 10, 10)
            with BuildPart() as part_b:
                Sphere(5)

        maps = build_provenance_maps(journal, part_a, part_b)
        assert len(maps) == 2
        assert isinstance(maps[0], dict)
        assert isinstance(maps[1], dict)

    def test_build_provenance_maps_per_object_counts(self):
        from build123d import Box, BuildPart, Sphere
        from ocp_provenance import build_provenance_maps

        with provenance() as journal:
            with BuildPart() as part_a:
                Box(10, 10, 10)
            with BuildPart() as part_b:
                Sphere(5)

        maps = build_provenance_maps(journal, part_a, part_b)
        face_a = [k for k in maps[0] if k.startswith("faces/")]
        face_b = [k for k in maps[1] if k.startswith("faces/")]
        assert len(face_a) == 6
        assert len(face_b) == 1

    def test_build_provenance_maps_no_key_collisions_when_prefixed(self):
        from build123d import Box, BuildPart, Sphere
        from ocp_provenance import build_provenance_maps

        with provenance() as journal:
            with BuildPart() as part_a:
                Box(10, 10, 10)
            with BuildPart() as part_b:
                Sphere(5)

        maps = build_provenance_maps(journal, part_a, part_b)
        prefixes = ["/Group/Solid", "/Group/Solid(2)"]
        combined = {}
        for prefix, prov_dict in zip(prefixes, maps):
            for key, val in prov_dict.items():
                full_key = f"{prefix}/{key}"
                assert full_key not in combined, f"Collision: {full_key}"
                combined[full_key] = val
        assert len(combined) > 0

    def test_build_provenance_maps_skips_non_cad(self):
        from build123d import Box, BuildPart
        from ocp_provenance import build_provenance_maps

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)

        maps = build_provenance_maps(journal, part, "not_a_shape", None)
        assert len(maps) == 3
        assert len(maps[0]) > 0
        assert len(maps[1]) == 0
        assert len(maps[2]) == 0

    def test_registry_clear(self):
        from build123d import Box, BuildPart

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)

        assert len(journal.registry) > 0
        journal.registry.clear()
        assert len(journal.registry) == 0
