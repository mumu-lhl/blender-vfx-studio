"""Compare actual dash/landing HD frames in a process without the extension."""

import argparse
import hashlib
import json
import sys
from array import array
from pathlib import Path

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
folder = Path(bpy.data.filepath).parent
settings = json.loads((folder / "dash-landing-settings.json").read_text())
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--frames", type=int, nargs="+", default=[52, 18, 35])
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
assert len(set(args.frames)) >= 2
assert all(frame in settings["frames"] for frame in args.frames)
assert settings["resolution"] == [960, 540]
scene = bpy.context.scene
rig = next(obj for obj in scene.objects if obj.type == "ARMATURE")
assert all(image.packed_file for image in bpy.data.images if image.source == "FILE")
poses = []
for frame in args.frames:
    scene.frame_set(frame)
    poses.append(tuple(rig.matrix_world.translation))
    destination = folder / "native"
    destination.mkdir(exist_ok=True)
    scene.render.filepath = str(destination / f"dash-landing-{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
    expected = bpy.data.images.load(str(folder / f"dash-landing-{frame:04d}.png"))
    actual = bpy.data.images.load(scene.render.filepath)
    assert expected.size[:] == actual.size[:] == (960, 540)
    assert array("f", expected.pixels[:]).tobytes() == array("f", actual.pixels[:]).tobytes()
    bpy.data.images.remove(expected)
    bpy.data.images.remove(actual)
assert len(set(poses)) > 1, "The live character must keep its native movement"
scene.frame_set(84)
assert not any(
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    for obj in scene.objects
    if obj.get("vfx_role") == "layer"
)
assert not any("blender_vfx_studio" in name for name in sys.modules)
(folder / "native-check.json").write_text(
    json.dumps(
        {
            "frames": args.frames,
            "pixels_identical": True,
            "clear_frame": 84,
            "scene_sha256": hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
            "source_frame_sha256": {
                str(frame): hashlib.sha256(
                    (folder / f"dash-landing-{frame:04d}.png").read_bytes()
                ).hexdigest()
                for frame in args.frames
            },
        },
        indent=2,
    )
    + "\n"
)
print("DASH_LANDING_HD_NATIVE_PIXELS_IDENTICAL_ACTOR_MOVES_AND_RECOVERY_CLEAR")
