"""Edited echo lifetimes replay after source removal, without the extension."""

import sys

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
root = bpy.data.objects["Persisted Edited Echo Tail"]
assert root["duration"] == 35
assert "User Animated Mesh" not in bpy.data.objects
for frame in (35, 7, 36, 19, 7):
    bpy.context.scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    actual = [
        component
        for obj in bpy.data.objects
        if obj.get("vfx_composition") == root
        for vertex in obj.children[0].evaluated_get(graph).data.vertices
        for component in vertex.co
    ] or [0.0]
    assert actual == list(root[f"expected_tail_points_{frame}"])
assert not bpy.app.handlers.frame_change_pre
assert not bpy.app.handlers.frame_change_post
print("EDITED_ECHO_TAIL_NATIVE_NO_SOURCE_AND_CLEAR")
