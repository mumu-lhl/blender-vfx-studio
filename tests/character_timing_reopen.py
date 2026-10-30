"""Verify contact-aligned discharge and baked blade aiming without the add-on."""

import sys

import bpy
from mathutils import Vector

assert not any("blender_vfx_studio" in name for name in sys.modules)
scene = bpy.context.scene
hit, peak = scene["timing_contact"], scene["timing_peak"]
core = bpy.data.objects["Charge • Compressed Core"].children[0]
tree = core.modifiers[0].node_group
scene.frame_set(hit - 2)
assert tree.nodes["Charge Clock"].outputs[0].default_value < peak - 0.02
scene.frame_set(hit)
assert abs(tree.nodes["Charge Clock"].outputs[0].default_value - peak) < 1e-5
assert (
    abs(core.data.materials[0].node_tree.nodes["Charge Clock"].outputs[0].default_value - peak)
    < 1e-5
)
for frame in range(hit - 2, hit + 3):
    scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    matrix = bpy.data.objects[scene["timing_weapon"]].evaluated_get(graph).matrix_world
    direction = (matrix @ Vector(scene["timing_tip"]) - matrix.translation).normalized()
    socket = bpy.data.objects["Charge socket • world up"].evaluated_get(graph)
    aim = (socket.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    assert aim.dot(direction) > 0.999999, f"Charge leaves the blade direction at {frame}"
    slash = bpy.data.objects["Combat • Arc Slash"].evaluated_get(graph)
    normal = (slash.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    assert abs(normal.dot(direction)) < 1e-5, "Native slash plane must contain the blade"
scene.frame_set(96)
assert not any(
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    for obj in scene.objects
    if obj.get("vfx_role") == "layer"
)
assert not any("blender_vfx_studio" in name for name in sys.modules)
print("CHARACTER_CHARGE_CONTACT_NATIVE_TIMING_AND_DIRECTION_OK")
