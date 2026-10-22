"""New process, no extension imports, auto-execution disabled."""

import math
import sys

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
roots = [o for o in bpy.data.objects if o.get("vfx_role") == "controller"]
assert len(roots) == 4
birth = next(r for r in roots if r.name == "Persisted Fractional Birth")
roots.remove(birth)
for frame in (13, 0, 25, 1, 7, 24):
    bpy.context.scene.frame_set(frame)
    for root in roots:
        layer = root.children[0]
        mesh = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        actual = max((math.hypot(v.co.x, v.co.y) for v in mesh.vertices), default=0)
        initial = 1.0 if root.name in {"Persisted Copy", "Persisted Preset"} else 0.2
        expected = initial + 3 * (frame - 1) / 24 if 1 <= frame < 25 else 0
        assert abs(actual - expected) < 1e-5, (root.name, frame, actual, expected)
        for data in (layer, layer.data.materials[0].node_tree):
            assert all(c.driver.is_valid for c in data.animation_data.drivers)
assert birth["start"] == 7.5
bpy.context.scene.frame_set(7, subframe=0.5)
mesh = birth.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
assert abs(max(v.co.length for v in mesh.vertices) - 0.2) < 1e-5
bpy.context.scene.frame_set(7, subframe=0.25)
assert not birth.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
print("NATIVE_REOPEN_OK", bpy.app.version_string)
