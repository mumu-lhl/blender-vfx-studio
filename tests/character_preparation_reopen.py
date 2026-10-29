"""The native wind-up changes preparation while preserving the measured slice."""

import sys

import bpy
from mathutils import Vector

assert not any("blender_vfx_studio" in name for name in sys.modules)
scene = bpy.context.scene
rig = bpy.data.objects["Caster • Knight"]
weapon = bpy.data.objects[scene["timing_weapon"]]
tip = Vector(scene["timing_tip"])
track = next(
    track
    for track in rig.animation_data.nla_tracks
    if any(strip.name.startswith("Charge preparation") for strip in track.strips)
)


def blade(frame):
    scene.frame_set(frame)
    matrix = weapon.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world
    return matrix.translation.copy(), matrix @ tip


frames = (1, 16, 32, *range(41, 57))
prepared = {frame: blade(frame) for frame in frames}
track.mute = True
original = {frame: blade(frame) for frame in frames}
assert max((a - b).length for a, b in zip(prepared[32], original[32], strict=True)) > 0.1
assert all((a - b).length < 1e-5 for a, b in zip(prepared[1], original[1], strict=True))
for frame in range(41, 57):
    assert all(
        (a - b).length < 1e-5 for a, b in zip(prepared[frame], original[frame], strict=True)
    ), f"Preparation changes the measured attack at frame {frame}"
track.mute = False
for frame in (32, 1, 49, 16):
    assert all((a - b).length < 1e-5 for a, b in zip(blade(frame), prepared[frame], strict=True))
assert not any("blender_vfx_studio" in name for name in sys.modules)
print("CHARACTER_PREPARATION_NATIVE_POSE_AND_ORIGINAL_ATTACK_OK")
