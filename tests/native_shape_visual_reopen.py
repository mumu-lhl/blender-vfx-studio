"""Replay a saved art-control comparison without loading the extension."""

import argparse
import hashlib
import json
import sys
from array import array
from pathlib import Path

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--case", choices=("baseline", "edited"), default="edited")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
folder = Path(bpy.data.filepath).parent
settings = json.loads((folder / "review-settings.json").read_text())
scene = bpy.context.scene
assert scene.render.engine == settings["engine"]
assert [scene.render.resolution_x, scene.render.resolution_y] == settings["resolution"]
assert Path(bpy.data.filepath).stem == args.case
native = folder / "native"
native.mkdir(exist_ok=True)
verified = []
for frame in reversed(settings["frames"]):
    scene.frame_set(frame)
    expected_path = folder / f"{args.case}-{frame:04d}.png"
    scene.render.filepath = str(native / f"{args.case}-{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
    expected = bpy.data.images.load(str(expected_path), check_existing=False)
    actual = bpy.data.images.load(scene.render.filepath, check_existing=False)
    assert expected.size[:] == actual.size[:] == tuple(settings["resolution"])
    assert array("f", expected.pixels[:]).tobytes() == array("f", actual.pixels[:]).tobytes()
    bpy.data.images.remove(expected)
    bpy.data.images.remove(actual)
    verified.append(
        {"frame": frame, "sha256": hashlib.sha256(expected_path.read_bytes()).hexdigest()}
    )
scene.frame_set(96)
graph = bpy.context.evaluated_depsgraph_get()
assert not any(
    len(obj.evaluated_get(graph).data.vertices)
    for obj in scene.objects
    if obj.get("vfx_role") == "layer" and obj.type == "MESH"
)
assert not any("blender_vfx_studio" in name for name in sys.modules)
record = {
    "case": args.case,
    "frames": verified,
    "scene_sha256": hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
    "clear_frame": 96,
    "realtime_playback_reviewed": False,
}
(folder / f"{args.case}-native-check.json").write_text(json.dumps(record, indent=2) + "\n")
print("NATIVE_SHAPE_HD_PIXELS_IDENTICAL_AND_TAIL_CLEAR", args.case, flush=True)
