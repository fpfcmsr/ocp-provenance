from build123d import *
from ocp_provenance import provenance
from ocp_vscode.show import _get_leaf_ids, _convert, _build_provenance_for_mapping

with provenance() as j:
    with BuildPart() as a:
        Box(10, 10, 10)
    with BuildPart() as b:
        Sphere(5)
    with BuildSketch() as s:
        Rectangle(10, 10)

cad_objs = (a, b, s)
t, mapping = _convert(*cad_objs)
leaf_ids = list(_get_leaf_ids(mapping))

print(f"cad_objs: {len(cad_objs)}")
print(f"leaf_ids: {len(leaf_ids)}")
print(f"leaves:   {leaf_ids}")

result = _build_provenance_for_mapping(cad_objs, None, mapping)
print(f"provenance result: {'dict with ' + str(len(result)) + ' keys' if
result else 'None'}")