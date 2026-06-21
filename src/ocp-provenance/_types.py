from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class SourceLocation:
    """A Python source code location."""

    filename: str
    lineno: int
    function: str
    code_context: str | None = None
    kind: str = "created"
