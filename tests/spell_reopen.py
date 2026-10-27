"""A complete saved cast replays with the extension absent and autoexec disabled."""

import hashlib
import json
import sys
from array import array

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)


def snapshot(frame):
    scene = bpy.context.scene
    scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    result = {}
    for obj in scene.objects:
        if obj.get("vfx_role") != "layer":
            continue
        evaluated = obj.evaluated_get(graph)
        values = array("f", [c for v in evaluated.data.vertices for c in v.co])
        values.extend(c for row in evaluated.matrix_world for c in row)
        result[obj.name] = hashlib.sha256(values.tobytes()).hexdigest()
    return result


for frame, expected in json.loads(bpy.context.scene["spell_expected_snapshots"]).items():
    assert snapshot(int(frame)) == expected, frame
assert not bpy.app.handlers.frame_change_pre
assert not bpy.app.handlers.frame_change_post
print("SPELL_SCENE_NATIVE_REPLAY_OK")
