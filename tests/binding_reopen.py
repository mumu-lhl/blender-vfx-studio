"""Binding uses only persisted native constraints and animation."""

import bpy

root = bpy.data.objects["Persisted Bound Ring"]
for frame, expected_x in ((11, 3), (1, 1), (11, 3)):
    bpy.context.scene.frame_set(frame)
    matrix = root.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world
    assert abs(matrix.translation.x - expected_x) < 1e-5
    assert abs(matrix.translation.y - 2) < 1e-5
    assert abs(matrix.translation.z - 3) < 1e-5
print("BINDING_NATIVE_REOPEN_OK")
