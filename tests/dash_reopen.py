"""Captured poses have no source dependency and replay without the extension."""

import sys

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
root = next(o for o in bpy.data.objects if o.get("vfx_module") == "core.composition")
assert isinstance(root["vfx_capture_source_name"], str)
assert not any(o.name == "User Animated Mesh" for o in bpy.data.objects)
assert list(root["vfx_capture_frames"]) == [1, 3.75, 6.5, 9.25, 12]
assert len(root.children) == 5
for frame in (14, 0, 7, 31, 14):
    bpy.context.scene.frame_set(frame)
    count = sum(
        len(o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)
        for o in root.children_recursive
        if o.get("vfx_role") == "layer"
    )
    assert (count > 0) == (frame in (7, 14)), (frame, count)
print("DASH_NATIVE_WITHOUT_SOURCE_OK")
