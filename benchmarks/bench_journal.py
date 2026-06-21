"""Benchmark provenance journal overhead: ON vs OFF.

Run with: uv run python benchmarks/bench_journal.py
"""

from __future__ import annotations

import statistics
import time

from build123d import (
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Circle,
    Cylinder,
    Keep,
    Line,
    Mode,
    Plane,
    Polyline,
    Rectangle,
    RegularPolygon,
    Sphere,
    Wedge,
    chamfer,
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
from ocp_provenance import provenance


def _bench(fn, *, warmup: int = 3, repeats: int = 30) -> float:
    for _ in range(warmup):
        fn()
    times: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter_ns()
        fn()
        times.append((time.perf_counter_ns() - t0) / 1e6)
    return statistics.median(times)


# ---------------------------------------------------------------------------
# Build functions
# ---------------------------------------------------------------------------


def build_box():
    with BuildPart():
        Box(10, 10, 10)


def build_box_fillet():
    with BuildPart() as p:
        Box(10, 10, 10)
        fillet(p.edges(), 1)


def build_box_chamfer():
    with BuildPart() as p:
        Box(10, 10, 10)
        chamfer(p.edges(), 1)


def build_box_cyl_fillet():
    with BuildPart() as p:
        Box(20, 20, 20)
        Cylinder(5, 25, mode=Mode.SUBTRACT)
        fillet(p.edges(), 1)


def build_sketch_extrude_fillet():
    with BuildPart() as p:
        with BuildSketch():
            Rectangle(12, 12)
            Circle(3, mode=Mode.SUBTRACT)
        extrude(amount=8)
        fillet(p.edges(), 1)


def build_offset():
    with BuildPart() as p:
        Box(10, 10, 10)
        offset(amount=-1, openings=p.faces().sort_by(Axis.Z)[-1:])


def build_split():
    with BuildPart():
        Box(10, 10, 10)
        split(bisect_by=Plane.XZ, keep=Keep.TOP)


def build_scale():
    with BuildPart():
        Box(10, 10, 10)
        scale(by=1.5)


def build_loft():
    with BuildPart():
        with BuildSketch(Plane.XY):
            Rectangle(10, 10)
        with BuildSketch(Plane.XY.offset(10)):
            RegularPolygon(4, 6)
        loft()


def build_revolve():
    with BuildPart():
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Polyline([(0, 0), (5, 0), (5, 10), (0, 10)], close=True)
            make_face()
        revolve(axis=Axis.Z)


def build_sweep():
    with BuildPart():
        with BuildLine():
            Line((0, 0, 0), (0, 0, 20))
        with BuildSketch():
            Rectangle(4, 4)
        sweep()


def build_thicken():
    with BuildPart():
        with BuildSketch():
            Rectangle(10, 10)
        thicken(amount=3)


def build_complex_multi():
    with BuildPart() as p:
        Box(20, 20, 20)
        Cylinder(5, 25, mode=Mode.SUBTRACT)
        fillet(p.edges(), 1)
    with BuildPart():
        Sphere(5)
    with BuildPart():
        Wedge(10, 10, 10, 2, 2, 8, 8)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

BUILDS = [
    ("Box", build_box),
    ("Box+fillet", build_box_fillet),
    ("Box+chamfer", build_box_chamfer),
    ("Box-Cyl+fillet", build_box_cyl_fillet),
    ("Sketch+extrude+fillet", build_sketch_extrude_fillet),
    ("Box+offset", build_offset),
    ("Box+split", build_split),
    ("Box+scale", build_scale),
    ("Loft", build_loft),
    ("Revolve", build_revolve),
    ("Sweep", build_sweep),
    ("Thicken", build_thicken),
    ("Multi-part (3 parts)", build_complex_multi),
]


def main():
    hdr = f"{'Operation':30s} {'OFF':>8s} {'ON':>8s} {'Overhead':>10s} {'%':>7s}"
    print(hdr)
    print("-" * len(hdr))

    for label, fn in BUILDS:
        med_off = _bench(fn)

        def with_journal(f=fn):
            with provenance():
                f()

        med_on = _bench(with_journal)
        overhead = med_on - med_off
        pct = overhead / med_off * 100 if med_off > 0 else 0
        print(
            f"{label:30s} {med_off:6.2f}ms {med_on:6.2f}ms {overhead:+8.2f}ms {pct:+6.1f}%"
        )


if __name__ == "__main__":
    main()
