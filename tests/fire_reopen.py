"""Saved fire plays without the extension or its asset builders."""

import sys

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
root = bpy.data.objects["Persisted Stylized Fire"]
flame = next(obj for obj in root.children if "Sculpted Tongues" in obj.name)
for frame in (44, 0, 8, 53, 20, 44):
    bpy.context.scene.frame_set(frame)
    mesh = flame.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    expected = root[f"expected_vertices_{frame}"] if frame in (8, 20, 44) else 0
    assert len(mesh.vertices) == expected
bpy.context.scene.frame_set(53)
assert not any(
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    for obj in root.children_recursive
    if obj.get("vfx_role") == "layer"
)
print("FIRE_NATIVE_REOPEN_OK")
