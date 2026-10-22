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
print("COMPOSITION_NATIVE_REOPEN_OK")
