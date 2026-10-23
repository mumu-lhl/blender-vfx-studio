"""Native ribbon still evaluates after deleting source and disabling extension."""

import bpy

root = bpy.data.objects["Persisted Ribbon"]
layer = root.children[0]
for frame, expected in ((11, 2), (6, 0.25), (16, 5.75)):
    bpy.context.scene.frame_set(frame)
    mesh = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    head = (mesh.vertices[-2].co + mesh.vertices[-1].co) * 0.5
    assert abs(head.x - expected) < 1e-5, (frame, head)
    assert abs((mesh.vertices[-2].co - mesh.vertices[-1].co).length - 0.4) < 1e-5
bpy.context.scene.frame_set(21)
assert len(layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices) == 0
print("TRAIL_NATIVE_REOPEN_OK")

root = bpy.data.objects["Persisted Bone Tail"]
assert root["vfx_bone_tail"]
# Remove the rig and its animation dependencies; only the stored world path remains.
for name in ("Animated Blade Rig", "Rig Parent", "Blade Rotation Control"):
    bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
layer = root.children[0]
for frame in (16, 1, 11, 6, 16):
    bpy.context.scene.frame_set(frame)
    mesh = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    tip = (mesh.vertices[-2].co + mesh.vertices[-1].co) * 0.5
    assert all(abs(a - b) < 1e-5 for a, b in zip(tip, root[f"expected_tip_{frame}"]))
print("BONE_TAIL_NATIVE_REOPEN_OK")
