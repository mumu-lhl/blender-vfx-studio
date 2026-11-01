"""Inspect the saved field study without importing the extension."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

if any("blender_vfx_studio" in name for name in sys.modules):
    raise RuntimeError("Open the study in a fresh process without the extension")

scene = bpy.context.scene
folder = Path(bpy.data.filepath).parent
field = bpy.data.objects["Field study"]
for frame in (1, 70):
    scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    assert not field.evaluated_get(graph).data.vertices
scene.frame_set(40)
assert len(field.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices) == 4
scene.render.filepath = str(folder / "native-0040.png")
bpy.ops.render.render(write_still=True)
scene.render.resolution_x, scene.render.resolution_y = 480, 270
frames = [1, 17, *range(19, 70, 4), 71]
rows = []
for frame in frames:
    scene.frame_set(frame)
    path = folder / f"sample-{frame:04}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    rows.append({"frame": frame, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
(folder / "native-record.json").write_text(
    json.dumps(
        {
            "native_only": True,
            "clear_frames": [1, 70],
            "hd_frame": 40,
            "motion_resolution": [480, 270],
            "samples": rows,
            "realtime_playback_reviewed": False,
            "whole_effect_art_approved": False,
        },
        indent=2,
    )
    + "\n"
)
print("NATIVE_FIRE_FIELD_STUDY_REOPEN_COMPLETE")
