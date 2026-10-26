"""Seek a real combat scene without loading the extension and compare actual HD pixels."""

import hashlib
import json
import sys
from array import array
from pathlib import Path

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
folder = Path(bpy.data.filepath).parent
settings = json.loads((folder / "character-settings.json").read_text())
assert settings["contact"]["verified_intersection"]
assert len([obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]) == 2
assert all(image.packed_file for image in bpy.data.images if image.source == "FILE")
scene = bpy.context.scene
poses = []
for frame in (53, 16, 32):
    if frame not in settings["frames"]:
        raise AssertionError("Render the charge, hit and build-up frames before native validation")
    scene.frame_set(frame)
    rig = bpy.data.objects["Caster • Knight"].evaluated_get(bpy.context.evaluated_depsgraph_get())
    poses.append(tuple(rig.pose.bones["hand.r"].matrix.translation))
    destination = folder / "native"
    destination.mkdir(exist_ok=True)
    scene.render.filepath = str(destination / f"character-{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
    expected = bpy.data.images.load(str(folder / f"character-{frame:04d}.png"))
    actual = bpy.data.images.load(scene.render.filepath)
    assert expected.size[:] == actual.size[:] == (960, 540)
    assert array("f", expected.pixels[:]).tobytes() == array("f", actual.pixels[:]).tobytes()
    bpy.data.images.remove(expected)
    bpy.data.images.remove(actual)
assert poses[0] != poses[1], "The character attack must play, not just the VFX"
scene.frame_set(96)
assert not any(
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    for obj in scene.objects
    if obj.get("vfx_role") == "layer"
)
assert not any("blender_vfx_studio" in name for name in sys.modules)
record = {
    "native_render_verified": True,
    "frames": [53, 16, 32],
    "clear_frame": 96,
    "scene_sha256": hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
    "source_frame_sha256": {
        f"character-{frame:04d}.png": hashlib.sha256(
            (folder / f"character-{frame:04d}.png").read_bytes()
        ).hexdigest()
        for frame in (53, 16, 32)
    },
}
(folder / "native-check.json").write_text(json.dumps(record, indent=2) + "\n")
print("CHARACTER_NATIVE_HD_PIXELS_IDENTICAL_RIG_ANIMATED_AND_TAIL_CLEAR")
