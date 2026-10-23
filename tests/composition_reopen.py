"""Group timing and coordinated loop play without extension code."""

import bpy

root = bpy.data.objects["Composition Burst"]
layer = root.children[0]
for frame, visible in ((13, True), (37, False), (49, False), (61, True), (85, False), (0, False)):
    bpy.context.scene.frame_set(frame)
    result = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    assert bool(result.vertices) == visible, (frame, root["start"])
    assert all(
        c.driver.is_valid and c.driver.is_simple_expression for c in root.animation_data.drivers
    )
root = bpy.data.objects["Ungrouped Burst"]
assert root.parent is None and root.get("vfx_composition") is None
assert root["start"] == 61 and root["duration"] == 24 and not root["loop"]
assert tuple(round(v, 5) for v in root.matrix_world.translation) == (2, 3, 4)
for frame, visible in ((61, True), (85, False), (109, False), (13, False), (70, True)):
    bpy.context.scene.frame_set(frame)
    mesh = root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    assert bool(mesh.vertices) == visible, frame
print("COMPOSITION_NATIVE_REOPEN_OK")
