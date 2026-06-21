from __future__ import annotations

import linecache
import os
import sys

from ._types import SourceLocation

_skip_dirs: set[str] | None = None


def _init_skip_dirs() -> set[str]:
    global _skip_dirs
    dirs: set[str] = set()
    for mod_name in ("build123d", "ocp_provenance"):
        mod = sys.modules.get(mod_name)
        if mod is not None:
            mod_file = getattr(mod, "__file__", None)
            if mod_file:
                pkg_dir = os.path.dirname(os.path.abspath(mod_file))
                dirs.add(pkg_dir)
    _skip_dirs = dirs
    return dirs


def add_skip_directory(path: str) -> None:
    """Add a directory to skip when walking the call stack."""
    global _skip_dirs
    if _skip_dirs is None:
        _init_skip_dirs()
    assert _skip_dirs is not None
    _skip_dirs.add(os.path.abspath(path))


def find_user_frame(extra_skip: int = 0) -> SourceLocation | None:
    """Walk the call stack and return the first frame from user code.

    Skips frames inside build123d, ocp_provenance, and any directories
    added via add_skip_directory().
    """
    skip = _skip_dirs if _skip_dirs is not None else _init_skip_dirs()
    frame = sys._getframe(1 + extra_skip)
    while frame is not None:
        filename = frame.f_code.co_filename
        if filename.startswith("<"):
            frame = frame.f_back
            continue
        abs_filename = os.path.abspath(filename)
        if not any(abs_filename.startswith(d) for d in skip):
            line = linecache.getline(filename, frame.f_lineno)
            return SourceLocation(
                filename=filename,
                lineno=frame.f_lineno,
                function=frame.f_code.co_name,
                code_context=line.strip() if line else None,
            )
        frame = frame.f_back
    return None
