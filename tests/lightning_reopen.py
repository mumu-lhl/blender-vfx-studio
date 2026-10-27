"""Saved lightning plays without the extension or its asset builders."""

import sys

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
root = bpy.data.objects["Persisted Lightning Strike"]
bolt = next(obj for obj in root.children if "Main Discharges" in obj.name)
for frame in (12, 3, 7, 19, 0, 3):
    bpy.context.scene.frame_set(frame)
    mesh = bolt.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    expected = root[f"expected_vertices_{frame}"] if frame in (3, 7, 12) else 0
    assert len(mesh.vertices) == expected
bpy.context.scene.frame_set(20)
assert not any(
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    for obj in root.children_recursive
    if obj.get("vfx_role") == "layer"
)
print("LIGHTNING_NATIVE_REOPEN_OK")
