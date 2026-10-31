"""Compare native Slice preparation poses; VFX remain hidden in this diagnostic."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
assert not any("blender_vfx_studio" in name for name in sys.modules)
if not bpy.data.filepath:
    raise RuntimeError("Open the generated character-combat .blend in a fresh process")
scene = bpy.context.scene
folder = ROOT / "work/slice-preparation"
folder.mkdir(parents=True, exist_ok=True)
source = hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest()
bpy.data.collections["Combat VFX • toggle for comparison"].hide_render = True
scene.render.resolution_x, scene.render.resolution_y = 480, 270
for frame in (16, 32, 37):
    scene.frame_set(frame)
    scene.render.filepath = str(folder / f"before-{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
rig = bpy.data.objects["Caster • Knight"]
strip = next(
    strip
    for track in rig.animation_data.nla_tracks
    for strip in track.strips
    if strip.action and "2H_Melee_Attack_Slice" in strip.action.name
)
start, end = strip.action_frame_start, strip.action_frame_end
strip.frame_start, strip.frame_end = 1, 69
strip.blend_in, strip.blend_out = 12, 4
strip.use_animated_time = True
strip.use_animated_time_cyclic = False
for curve in strip.fcurves:
    if curve.data_path == "strip_time":
        curve.keyframe_points.clear()
junction = 37 + (69 - 37) * 0.18
time_keys = ((1, start), (junction, start + (end - start) * 0.18), (69, end))
for frame, action_frame in time_keys:
    strip.strip_time = action_frame
    strip.keyframe_insert(data_path="strip_time", frame=frame)
for curve in strip.fcurves:
    if curve.data_path == "strip_time":
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
assert any(curve.data_path == "strip_time" for curve in strip.fcurves)
for frame in (1, 16, 32, 37, 41, 45, 49, 57, 69):
    scene.frame_set(frame)
    scene.render.filepath = str(folder / f"after-{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(folder / "pose.blend"))
(folder / "settings.json").write_text(
    json.dumps(
        {
            "source_scene_sha256": source,
            "action": strip.action.name,
            "action_range": [start, end],
            "time_keys": time_keys,
            "vfx_hidden": True,
            "contact_retimed_or_validated": False,
            "art_acceptance": "pending actual image inspection",
        },
        indent=2,
    )
    + "\n"
)
print("NATIVE_SLICE_PREPARATION_POSES_RENDERED")
