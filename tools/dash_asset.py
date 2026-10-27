"""A reproducible CC0 character dash; stored pose meshes need no live character."""

import math

import bpy

from blender_vfx_studio import dash
from blender_vfx_studio.animation import curves
from tools.character_scene import actor, clip


def runner():
    character = actor("Knight", "Dash Runner", (-2, 0), math.pi / 2, sword=True)
    rig = character["rig"]
    clip(rig, character["actions"]["Running_A"], 1, 19)
    for frame, x in ((1, -2), (5, -1.8), (10, -0.8), (15, 0.8), (19, 1.4), (48, 1.4)):
        rig.location.x = x
        rig.keyframe_insert(data_path="location", index=0, frame=frame)
    for curve in curves(rig):
        if curve.data_path == "location" and curve.array_index == 0:
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"
    return character


def create(context, quality="MEDIUM", *, keep_character=False):
    if quality not in dash.QUALITY_COUNTS:
        raise ValueError("Unknown dash quality")
    before = set(bpy.data.objects)
    character = runner()
    effect = dash.create(context, character["rig"], 6, 18, quality)
    # Complete starter files use a consistent start; the shot keeps actual sample time.
    if not keep_character:
        for obj in set(bpy.data.objects) - before - set([effect, *effect.children_recursive]):
            bpy.data.objects.remove(obj, do_unlink=True)
        effect["start"] = 1.0
        effect.update_tag()
    for action in list(bpy.data.actions):
        if action.users == 0:
            bpy.data.actions.remove(action)
    return effect, character if keep_character else None
