"""Native clean geometry and RGB keyframes replay after all UI proxies are gone."""

import sys

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
assert not hasattr(bpy.types.Object, "vfx_primary_color")
root = bpy.data.objects["Persisted Art Slash"]
for frame in (11, 2, 5, 17, 5):
    bpy.context.scene.frame_set(frame)
    mesh = root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    if frame == 17:
        assert not mesh.vertices
        continue
    actual = [c for v in mesh.vertices for c in v.co]
    assert actual == list(root[f"expected_shape_{frame}"])
    assert [root[f"color_{i}"] for i in range(3)] == list(root[f"expected_color_{frame}"])
assert not bpy.app.handlers.frame_change_pre
assert not bpy.app.handlers.frame_change_post
print("ART_CONTROLS_NATIVE_REPLAY_OK")
