"""Comprehensive provenance viewer test.

Covers every instrumented operation and common combinations.
Run with the OCP CAD Viewer active in VS Code, then click any face
in the viewer — the Properties panel shows source-line provenance,
and VS Code jumps to the originating line.

Usage:
    uv run python examples/demo_provenance_viewer.py
"""

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
    Location,
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
    mirror,
    offset,
    revolve,
    scale,
    split,
    sweep,
    thicken,
)
from ocp_provenance import provenance
from ocp_vscode import show

SPACING = 25

with provenance():
    # ===================================================================
    # Row 1: Primitives (Y=0)
    # ===================================================================

    with BuildPart(Location((0 * SPACING, 0, 0))) as box:
        Box(10, 10, 10)

    with BuildPart(Location((1 * SPACING, 0, 0))) as cyl:
        Cylinder(5, 10)

    with BuildPart(Location((2 * SPACING, 0, 0))) as sph:
        Sphere(5)

    with BuildPart(Location((3 * SPACING, 0, 0))) as cone:
        Cone(5, 2, 10)

    with BuildPart(Location((4 * SPACING, 0, 0))) as torus:
        Torus(8, 2)

    with BuildPart(Location((5 * SPACING, 0, 0))) as wedge:
        Wedge(10, 10, 10, 2, 2, 8, 8)

    # ===================================================================
    # Row 2: Single modifiers (Y=1)
    # ===================================================================

    with BuildPart(Location((0 * SPACING, 1 * SPACING, 0))) as box_fillet:
        Box(10, 10, 10)
        fillet(box_fillet.edges(), 1)

    with BuildPart(Location((1 * SPACING, 1 * SPACING, 0))) as box_chamfer:
        Box(10, 10, 10)
        chamfer(box_chamfer.edges(), 1)

    with BuildPart(Location((2 * SPACING, 1 * SPACING, 0))) as box_draft:
        Box(10, 10, 20)
        sides = box_draft.faces().filter_by(Axis.Z, reverse=True)
        draft(sides, Plane.XY, 3)

    with BuildPart(Location((3 * SPACING, 1 * SPACING, 0))) as cyl_fillet:
        Cylinder(5, 10)
        fillet(cyl_fillet.edges(), 1)

    # ===================================================================
    # Row 3: Booleans (Y=2)
    # ===================================================================

    with BuildPart(Location((0 * SPACING, 2 * SPACING, 0))) as bool_sub:
        Box(10, 10, 10)
        Cylinder(3, 12, mode=Mode.SUBTRACT)

    with BuildPart(Location((1 * SPACING, 2 * SPACING, 0))) as bool_int:
        Box(10, 10, 10)
        Sphere(7, mode=Mode.INTERSECT)

    with BuildPart(Location((2 * SPACING, 2 * SPACING, 0))) as bool_add:
        Box(10, 10, 5)
        with BuildPart(Plane.XY.offset(5)):
            Cylinder(3, 5)

    with BuildPart(Location((3 * SPACING, 2 * SPACING, 0))) as bool_multi:
        Box(14, 14, 14)
        Cylinder(3, 20, mode=Mode.SUBTRACT)
        Sphere(4, mode=Mode.SUBTRACT)

    # ===================================================================
    # Row 4: Sketch → 3D operations (Y=3)
    # ===================================================================

    with BuildPart(Location((0 * SPACING, 3 * SPACING, 0))) as ext_rect:
        with BuildSketch():
            Rectangle(10, 10)
        extrude(amount=5)

    with BuildPart(Location((1 * SPACING, 3 * SPACING, 0))) as ext_hex:
        with BuildSketch():
            RegularPolygon(5, 6)
        extrude(amount=5)

    with BuildPart(Location((2 * SPACING, 3 * SPACING, 0))) as rev:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Polyline([(0, 0), (5, 0), (5, 10), (0, 10)], close=True)
            make_face()
        revolve(axis=Axis.Z)

    with BuildPart(Location((3 * SPACING, 3 * SPACING, 0))) as lofted:
        with BuildSketch(Plane.XY):
            Rectangle(10, 10)
        with BuildSketch(Plane.XY.offset(10)):
            RegularPolygon(4, 6)
        loft()

    with BuildPart(Location((4 * SPACING, 3 * SPACING, 0))) as swept:
        with BuildLine():
            Line((0, 0, 0), (0, 0, 20))
        with BuildSketch():
            Rectangle(4, 4)
        sweep()

    with BuildPart(Location((5 * SPACING, 3 * SPACING, 0))) as thick:
        with BuildSketch():
            Rectangle(10, 10)
        thicken(amount=3)

    # ===================================================================
    # Row 5: Offset, split, scale, mirror (Y=4)
    # ===================================================================

    with BuildPart(Location((0 * SPACING, 4 * SPACING, 0))) as box_offset:
        Box(10, 10, 10)
        offset(amount=-1, openings=box_offset.faces().sort_by(Axis.Z)[-1:])

    with BuildPart(Location((1 * SPACING, 4 * SPACING, 0))) as box_split:
        Box(10, 10, 10)
        split(bisect_by=Plane.XZ, keep=Keep.TOP)

    with BuildPart(Location((2 * SPACING, 4 * SPACING, 0))) as box_scale:
        Box(10, 10, 10)
        scale(by=1.5)

    with BuildPart(Location((3 * SPACING, 4 * SPACING, 0))) as box_mirror:
        Box(10, 10, 10, align=(Align.MIN, Align.MIN, Align.MIN))
        mirror(about=Plane.YZ)

    with BuildPart(Location((4 * SPACING, 4 * SPACING, 0))) as box_scale_nu:
        Box(10, 10, 10)
        scale(by=(2, 1, 0.5))

    # ===================================================================
    # Row 6: Combinations (Y=5)
    # ===================================================================

    with BuildPart(Location((0 * SPACING, 5 * SPACING, 0))) as sub_fillet:
        Box(20, 20, 20)
        Cylinder(5, 25, mode=Mode.SUBTRACT)
        fillet(sub_fillet.edges(), 1)

    with BuildPart(Location((1 * SPACING, 5 * SPACING, 0))) as ext_fillet:
        with BuildSketch():
            Rectangle(12, 12)
        extrude(amount=8)
        fillet(ext_fillet.edges(), 1)

    with BuildPart(Location((2 * SPACING, 5 * SPACING, 0))) as offset_fillet:
        Box(14, 14, 14)
        offset(amount=-2, openings=offset_fillet.faces().sort_by(Axis.Z)[-1:])
        fillet(offset_fillet.edges().filter_by(Axis.Z), 0.5)

    with BuildPart(Location((3 * SPACING, 5 * SPACING, 0))) as split_chamfer:
        Cylinder(6, 12)
        split(bisect_by=Plane.XZ, keep=Keep.TOP)
        chamfer(split_chamfer.edges().filter_by(Axis.Z), 1)

    with BuildPart(Location((4 * SPACING, 5 * SPACING, 0))) as scale_sub:
        Box(10, 10, 10)
        scale(by=1.5)
        Cylinder(3, 20, mode=Mode.SUBTRACT)

    with BuildPart(Location((5 * SPACING, 5 * SPACING, 0))) as mirror_fillet:
        Box(10, 10, 10, align=(Align.MIN, Align.MIN, Align.MIN))
        mirror(about=Plane.YZ)
        fillet(mirror_fillet.edges(), 1)

    with BuildPart(Location((6 * SPACING, 5 * SPACING, 0))) as sketch_mirror:
        with BuildSketch():
            Rectangle(10, 5, align=(Align.MIN, Align.MIN))
            mirror(about=Plane.YZ)
        extrude(amount=3)

    # ===================================================================
    # Row 7: Standalone sketches (Y=6)
    # ===================================================================

    with BuildSketch(Plane.XY.offset(6 * SPACING)) as sk_rect:
        Rectangle(10, 10)

    with BuildSketch(
        Plane(
            origin=(1 * SPACING, 0, 6 * SPACING),
        )
    ) as sk_circle:
        Circle(5)

    with BuildSketch(
        Plane(
            origin=(2 * SPACING, 0, 6 * SPACING),
        )
    ) as sk_hex:
        RegularPolygon(5, 6)

    with BuildSketch(
        Plane(
            origin=(3 * SPACING, 0, 6 * SPACING),
        )
    ) as sk_bool:
        Rectangle(12, 12)
        Circle(3, mode=Mode.SUBTRACT)

    with BuildSketch(
        Plane(
            origin=(4 * SPACING, 0, 6 * SPACING),
        )
    ) as sk_mirror:
        Rectangle(10, 5, align=(Align.MIN, Align.MIN))
        mirror(about=Plane.YZ)

    with BuildSketch(
        Plane(
            origin=(5 * SPACING, 0, 6 * SPACING),
        )
    ) as sk_multi_hole:
        Rectangle(14, 14)
        with Locations((4, 4), (-4, -4), (4, -4), (-4, 4)):
            Circle(1.5, mode=Mode.SUBTRACT)

    with BuildSketch(
        Plane(
            origin=(6 * SPACING, 0, 6 * SPACING),
        )
    ) as sk_polyline:
        with BuildLine():
            Polyline([(0, 0), (10, 0), (8, 8), (0, 10)], close=True)
        make_face()

    # ===================================================================
    # Row 8: Sketch combinations (Y=7)
    # ===================================================================

    with BuildSketch(
        Plane(
            origin=(0, 0, 7 * SPACING),
        )
    ) as sk_add:
        Rectangle(10, 6)
        Rectangle(6, 10)

    with BuildSketch(
        Plane(
            origin=(1 * SPACING, 0, 7 * SPACING),
        )
    ) as sk_intersect:
        Rectangle(10, 10)
        Circle(6, mode=Mode.INTERSECT)

    with BuildSketch(
        Plane(
            origin=(2 * SPACING, 0, 7 * SPACING),
        )
    ) as sk_nested:
        Circle(8)
        Circle(6, mode=Mode.SUBTRACT)
        Circle(4)
        Circle(2, mode=Mode.SUBTRACT)

    with BuildSketch(
        Plane(
            origin=(3 * SPACING, 0, 7 * SPACING),
        )
    ) as sk_multi_bool:
        Rectangle(20, 20)
        Circle(3, mode=Mode.SUBTRACT)
        Rectangle(4, 4, mode=Mode.SUBTRACT)

    # ===================================================================
    # show() — viewer picks up provenance automatically
    # ===================================================================

    show(
        # Row 1: Primitives
        box,
        cyl,
        sph,
        cone,
        torus,
        wedge,
        # Row 2: Modifiers
        box_fillet,
        box_chamfer,
        box_draft,
        cyl_fillet,
        # Row 3: Booleans
        bool_sub,
        bool_int,
        bool_add,
        bool_multi,
        # Row 4: Sketch → 3D
        ext_rect,
        ext_hex,
        rev,
        lofted,
        swept,
        thick,
        # Row 5: Offset / split / scale / mirror
        box_offset,
        box_split,
        box_scale,
        box_mirror,
        box_scale_nu,
        # Row 6: 3D combinations
        sub_fillet,
        ext_fillet,
        offset_fillet,
        split_chamfer,
        scale_sub,
        mirror_fillet,
        sketch_mirror,
        # Row 7: Standalone sketches
        sk_rect,
        sk_circle,
        sk_hex,
        sk_bool,
        sk_mirror,
        sk_multi_hole,
        sk_polyline,
        # Row 8: Sketch combinations
        sk_add,
        sk_intersect,
        sk_nested,
        sk_multi_bool,
        names=[
            # Row 1
            "Box",
            "Cylinder",
            "Sphere",
            "Cone",
            "Torus",
            "Wedge",
            # Row 2
            "Box+fillet",
            "Box+chamfer",
            "Box+draft",
            "Cyl+fillet",
            # Row 3
            "Box-Cyl",
            "Box∩Sphere",
            "Box+Cyl",
            "Box-Cyl-Sphere",
            # Row 4
            "extrude(Rect)",
            "extrude(Hex)",
            "revolve",
            "loft",
            "sweep",
            "thicken",
            # Row 5
            "offset",
            "split",
            "scale",
            "mirror",
            "scale(non-uniform)",
            # Row 6
            "sub+fillet",
            "extrude+fillet",
            "offset+fillet",
            "split+chamfer",
            "scale+subtract",
            "mirror+fillet",
            "sketch(mirror)+extrude",
            # Row 7
            "sk:Rect",
            "sk:Circle",
            "sk:Hex",
            "sk:Rect-Circle",
            "sk:mirror",
            "sk:multi-hole",
            "sk:Polyline",
            # Row 8
            "sk:Rect+Rect",
            "sk:Rect∩Circle",
            "sk:nested-rings",
            "sk:multi-bool",
        ],
    )
