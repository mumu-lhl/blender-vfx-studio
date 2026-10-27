"""Dust playback and density properties survive a new process without the extension."""

import sys

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
root = bpy.data.objects["Persisted Dust Impact"]
member = next(o for o in root.children if "Rolling Banks" in o.name)
for frame in (16, 0, 7, 33, 16):
    bpy.context.scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    layer = member.children[0].evaluated_get(graph)
    actual = [c for vertex in layer.data.vertices for c in vertex.co]
    expected = list(root[f"expected_bounds_{frame}"]) if frame in (7, 16) else []
    assert actual == expected, (frame, actual, expected)
    for data in (layer.data.materials[0].node_tree, member.children[0].modifiers[0].node_group):
        assert all(curve.driver.is_valid for curve in data.animation_data.drivers)
assert member["Dust Density"] == 8
print("DUST_NATIVE_REOPEN_OK")
