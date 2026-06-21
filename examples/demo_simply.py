"""Demo: click a face in the viewer → editor jumps to the source line.

Usage:
    1. Start the OCP CAD Viewer in VS Code
    2. Run this script
    3. Activate the Properties tool in the viewer
    4. Click any face on either part — VS Code highlights the source line

Provenance is detected automatically by show() when a journal is active.
"""

from build123d import Box, BuildPart, Cylinder, Mode, Sphere, fillet
from ocp_provenance import provenance
from ocp_vscode import show

with provenance() as journal:
    with BuildPart() as box:
        Box(10, 10, 10)
        Cylinder(3, 12, mode=Mode.SUBTRACT, align=(None, None, None))
        fillet(box.edges(), 0.5)

    with BuildPart() as sphere:
        Sphere(5)

    show(box, sphere)
