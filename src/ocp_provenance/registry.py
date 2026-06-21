from __future__ import annotations

from collections import defaultdict

from ._types import SourceLocation


class ProvenanceRegistry:
    """Maps topological shapes to the source locations that created/modified them."""

    def __init__(self) -> None:
        self._map: dict[int, list[SourceLocation]] = defaultdict(list)

    def assign(self, shape_hash: int, location: SourceLocation) -> None:
        """Record that a shape was created/modified at location."""
        locs = self._map[shape_hash]
        if not locs or locs[-1] != location:
            locs.append(location)

    def propagate(self, old_hash: int, new_hash: int) -> None:
        """Copy provenance from old shape to new shape (modification lineage)."""
        if old_hash in self._map and old_hash != new_hash:
            existing = self._map[new_hash]
            for loc in self._map[old_hash]:
                if not existing or existing[-1] != loc:
                    existing.append(loc)

    def lookup(self, shape_hash: int) -> list[SourceLocation]:
        """Return all source locations for a shape, oldest first."""
        return list(self._map.get(shape_hash, []))

    def clear(self) -> None:
        """Remove all provenance data."""
        self._map.clear()

    def __len__(self) -> int:
        return len(self._map)
