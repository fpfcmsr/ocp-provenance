"""Diagnostic: dump provenance keys vs viewer shape IDs."""

from build123d import Box, BuildPart, Cylinder, Mode, Sphere, fillet
from build123d.topology import operation_journal
from ocp_provenance import build_provenance_map, build_provenance_maps, provenance

with provenance() as journal:
    with BuildPart() as box:
        Box(10, 10, 10)
        Cylinder(3, 12, mode=Mode.SUBTRACT, align=(None, None, None))
        fillet(box.edges(), 0.5)

    with BuildPart() as sphere:
        Sphere(5)

    print(
        f"Inside context: operation_journal.get(None) = {operation_journal.get(None)}"
    )
    print(f"Journal is: {journal}")

print(f"Outside context: operation_journal.get(None) = {operation_journal.get(None)}")

# Check per-object provenance
maps = build_provenance_maps(journal, box, sphere)

print("=== Per-object provenance maps ===")
for i, (obj, m) in enumerate(zip([box, sphere], maps)):
    label = "box" if i == 0 else "sphere"
    face_keys = sorted(k for k in m if k.startswith("faces/"))
    edge_keys = sorted(k for k in m if k.startswith("edges/"))
    vert_keys = sorted(k for k in m if k.startswith("vertices/"))
    print(
        f"\n{label}: {len(face_keys)} faces, {len(edge_keys)} edges, {len(vert_keys)} vertices"
    )
    for k in face_keys[:5]:
        locs = m[k]
        last = locs[-1]
        print(f"  {k} -> :{last['lineno']} {last['code_context']} ({last['kind']})")
    if len(face_keys) > 5:
        print(f"  ... and {len(face_keys) - 5} more faces")

# Now simulate what show() does via _convert
print("\n=== Simulating show() pipeline ===")
from ocp_vscode.show import _build_provenance_for_mapping, _convert, _get_leaf_ids

cad_objs = (box, sphere)
t, mapping = _convert(
    *cad_objs,
    names=["box", "sphere"],
    colors=[None, None],
    alphas=[None, None],
    modes=[None, None],
    materials=[None, None],
    progress=None,
)

leaf_ids = list(_get_leaf_ids(mapping))
print(f"Leaf IDs from mapping tree: {leaf_ids}")
print(f"Number of cad_objs: {len(cad_objs)}, Number of leaves: {len(leaf_ids)}")

if len(leaf_ids) != len(maps):
    print(f"\n*** MISMATCH: {len(leaf_ids)} leaves vs {len(maps)} provenance maps ***")
    print("This would cause _build_provenance_for_mapping to return None!")
else:
    # Stitch
    stitched = {}
    for leaf_id, prov_dict in zip(leaf_ids, maps):
        for key, val in prov_dict.items():
            stitched[f"{leaf_id}/{key}"] = val

    print(f"\nStitched provenance: {len(stitched)} keys")
    face_keys = sorted(k for k in stitched if "/faces/" in k)
    print(f"Face keys ({len(face_keys)}):")
    for k in face_keys[:8]:
        locs = stitched[k]
        last = locs[-1]
        print(f"  {k} -> :{last['lineno']} {last['code_context']}")
    if len(face_keys) > 8:
        print(f"  ... and {len(face_keys) - 8} more")

# Check what _build_provenance_for_mapping returns
print("\n=== Testing _build_provenance_for_mapping ===")
result = _build_provenance_for_mapping(cad_objs, None, mapping)
if result is None:
    print("*** RETURNED None — provenance will not be sent to viewer ***")
else:
    print(f"Returned {len(result)} keys")
    face_keys = sorted(k for k in result if "/faces/" in k)
    print(f"Sample face keys:")
    for k in face_keys[:5]:
        locs = result[k]
        last = locs[-1]
        print(f"  {k} -> :{last['lineno']} {last['code_context']}")
