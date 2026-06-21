"""Show all provenance entries (not just last) for each face."""

from build123d import Box, BuildPart, Cylinder, Mode, Sphere, fillet
from ocp_provenance import build_provenance_map, provenance

with provenance() as journal:
    with BuildPart() as box:
        Box(10, 10, 10)
        Cylinder(3, 12, mode=Mode.SUBTRACT, align=(None, None, None))
        fillet(box.edges(), 0.5)

    with BuildPart() as sphere:
        Sphere(5)

prov_box = build_provenance_map(journal, box)
prov_sphere = build_provenance_map(journal, sphere)

print("=== BOX: all provenance entries per face ===")
face_keys = sorted(k for k in prov_box if k.startswith("faces/"))
for k in face_keys:
    locs = prov_box[k]
    print(f"\n  {k} ({len(locs)} entries):")
    for loc in locs:
        print(f"    :{loc['lineno']} {loc['code_context']} ({loc['kind']})")

print(f"\n=== SPHERE ===")
for k in sorted(prov_sphere):
    if k.startswith("faces/"):
        locs = prov_sphere[k]
        print(f"  {k} ({len(locs)} entries):")
        for loc in locs:
            print(f"    :{loc['lineno']} {loc['code_context']} ({loc['kind']})")

# Count how many faces mention Box, Cylinder, fillet
box_mention = sum(
    1 for k in face_keys if any("Box" in l["code_context"] for l in prov_box[k])
)
cyl_mention = sum(
    1 for k in face_keys if any("Cylinder" in l["code_context"] for l in prov_box[k])
)
fil_mention = sum(
    1 for k in face_keys if any("fillet" in l["code_context"] for l in prov_box[k])
)
print(f"\n=== Summary ===")
print(f"Faces mentioning Box: {box_mention}/{len(face_keys)}")
print(f"Faces mentioning Cylinder: {cyl_mention}/{len(face_keys)}")
print(f"Faces mentioning fillet: {fil_mention}/{len(face_keys)}")
