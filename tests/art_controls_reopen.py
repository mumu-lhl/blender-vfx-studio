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
fire = bpy.data.objects["Persisted Blue Fire"]
flame = next(o for o in fire.children if "Sculpted Tongues" in o.name)
ramp = flame.children[0].data.materials[0].node_tree.nodes["Painted Red Orange Yellow"]
assert [c for e in ramp.color_ramp.elements for c in e.color] == list(fire["expected_heat_colors"])
for frame in (44, 8, 20, 44):
    bpy.context.scene.frame_set(frame)
    mesh = flame.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    assert [c for v in mesh.vertices for c in v.co] == list(fire[f"expected_shape_{frame}"])
assert not bpy.app.handlers.frame_change_pre
assert not bpy.app.handlers.frame_change_post
print("ART_CONTROLS_NATIVE_REPLAY_OK")
