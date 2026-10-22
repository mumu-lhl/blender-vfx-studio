"""Stored cloth poses need neither the solver source nor extension to play."""

import bpy

root = bpy.data.objects["Persisted Cloth"]
output = next(o for o in root.children if o.get("vfx_sim_part") == "output")
source = next(o for o in root.children if o.get("vfx_sim_part") == "source")
bpy.data.objects.remove(source, do_unlink=True)
for frame, expected_z in zip(
    (13, 1, 24, 13), list(root["test_expected_z"]) + [root["test_expected_z"][0]]
):
    bpy.context.scene.frame_set(frame)
    mesh = output.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    assert abs(mesh.vertices[0].co.z - expected_z) < 1e-5, (frame, mesh.vertices[0].co.z)
    assert abs(mesh.vertices[-1].co.z - 1.5) < 1e-5
bpy.context.scene.frame_set(25)
assert not output.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
print("SIMULATION_NATIVE_REOPEN_OK")
