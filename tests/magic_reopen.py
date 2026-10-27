"""Layered seal formation and release replay in a new process without the extension."""

import sys

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
root = bpy.data.objects["Persisted Magic Circle"]
seal = next(o for o in root.children if o.name.startswith("Magic • Seal"))
for frame in (60, 0, 8, 73, 35, 60):
    bpy.context.scene.frame_set(frame)
    actual = len(
        seal.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    )
    expected = root[f"expected_vertices_{frame}"] if frame in (8, 35, 60) else 0
    assert actual == expected, (frame, actual, expected)
bpy.context.scene.frame_set(73)
assert not any(
    o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    for o in root.children_recursive
    if o.get("vfx_role") == "layer"
)
print("MAGIC_NATIVE_REOPEN_OK")
