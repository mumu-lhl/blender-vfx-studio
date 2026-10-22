"""Saved crescent mesh and shader evaluate with no extension."""

import bpy

root = bpy.data.objects["Persisted Slash"]
layer = root.children[0]
for frame, axis in ((1, 0), (13, 1), (1, 0)):
    bpy.context.scene.frame_set(frame)
    result = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    assert min(v.co[axis] for v in result.vertices) >= -1e-5
    assert abs(max(v.co.length for v in result.vertices) - 2) < 1e-5
bpy.context.scene.frame_set(25)
assert not layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
print("SLASH_NATIVE_REOPEN_OK")
