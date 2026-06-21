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

    def test_registry_clear(self):
        from build123d import Box, BuildPart

        with provenance() as journal:
            with BuildPart() as part:
                Box(10, 10, 10)

        assert len(journal.registry) > 0
        journal.registry.clear()
        assert len(journal.registry) == 0
