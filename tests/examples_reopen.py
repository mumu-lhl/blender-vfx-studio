"""Native starter playback after saving, without the authoring extension."""

import sys

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
roots = [obj for obj in bpy.data.objects if obj.name.startswith("Persisted Starter ")]
assert len(roots) == 7
for frame in (16, 0, 7, 61, 16):
    bpy.context.scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    for root in roots:
        count = sum(
            len(obj.evaluated_get(graph).data.vertices)
            for obj in root.children_recursive
            if obj.get("vfx_role") == "layer" and obj.type == "MESH"
        )
        expected = root[f"expected_vertices_{frame}"] if frame in (7, 16) else 0
        assert count == expected, (root.name, frame, count, expected)
        bundle = next(c for c in root.users_collection if c.get("vfx_bundle_version"))
        assert bundle.preview.is_image_custom
        assert bundle.preview.image_size[:] == (2, 2)
assert len(bpy.data.cameras) == 0
assert len(bpy.data.images) == 0
assert bpy.context.scene.compositing_node_group is None
print("STARTER_LIBRARY_NATIVE_REOPEN_OK")
