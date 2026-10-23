"""Native two-bone rig with parent animation and a constrained blade tip."""

import math

import bpy


def animated_rig():
    parent = bpy.data.objects.new("Rig Parent", None)
    control = bpy.data.objects.new("Blade Rotation Control", None)
    for obj in (parent, control):
        bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.armature_add()
    rig = bpy.context.object
    rig.name = "Animated Blade Rig"
    bpy.ops.object.mode_set(mode="EDIT")
    base = rig.data.edit_bones[0]
    base.name = "Handle"
    base.head, base.tail = (0, 0, 0), (0, 1, 0)
    blade = rig.data.edit_bones.new("Blade")
    blade.head, blade.tail = (0, 1, 0), (0, 3, 0)
    blade.parent, blade.use_connect = base, True
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.parent = parent
    rig.location, rig.rotation_euler, rig.scale = (0.3, -0.4, 0.2), (0.1, 0.2, 0.3), (1.2, 0.8, 1.1)
    handle = rig.pose.bones["Handle"]
    handle.rotation_mode = "XYZ"
    control.rotation_mode = "XYZ"
    constraint = rig.pose.bones["Blade"].constraints.new("COPY_ROTATION")
    constraint.target = control
    constraint.owner_space = constraint.target_space = "LOCAL"
    for frame, angle in ((1, -0.8), (11, 0), (21, 0.9)):
        control.rotation_euler.z = angle
        control.keyframe_insert(data_path="rotation_euler", frame=frame)
        handle.rotation_euler.z = angle * 0.25
        handle.keyframe_insert(data_path="rotation_euler", frame=frame)
        parent.location.x = (frame - 1) * 0.02
        parent.rotation_euler.z = angle * 0.1
        parent.keyframe_insert(data_path="location", frame=frame)
        parent.keyframe_insert(data_path="rotation_euler", frame=frame)
    assert math.isclose(rig.data.bones["Blade"].length, 2)
    bpy.context.scene.frame_set(1)
    return rig, parent, control
