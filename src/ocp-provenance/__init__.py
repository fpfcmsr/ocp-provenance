"""ocp-provenance: Source maps for CAD.

Maps every face/edge in a build123d shape back to the Python source line
that created or modified it.
"""

from ._types import SourceLocation
from .journal import ProvenanceJournal
from .registry import ProvenanceRegistry


def provenance() -> ProvenanceJournal:
    """Create and return a provenance journal context manager.

    Usage::

        with provenance() as journal:
            with BuildPart() as p:
                Box(10, 10, 10)
                fillet(p.edges(), 1)

        for face in p.part.faces():
            locs = get_provenance(journal, face)
            for loc in locs:
                print(f"  {loc.filename}:{loc.lineno}")
    """
    return ProvenanceJournal()


def get_provenance(journal: ProvenanceJournal, shape) -> list[SourceLocation]:
    """Query provenance for a build123d Shape (Face, Edge, etc.)."""
    wrapped = getattr(shape, "wrapped", None)
    if wrapped is None:
        return []
    return journal.registry.lookup(hash(wrapped))


__all__ = [
    "SourceLocation",
    "ProvenanceJournal",
    "ProvenanceRegistry",
    "provenance",
    "get_provenance",
]
