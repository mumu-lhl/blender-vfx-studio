"""Compare real complete spell stages after native addon-free out-of-order seeking."""

import argparse
import hashlib
import json
import sys
from array import array
from pathlib import Path

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
folder = Path(bpy.data.filepath).parent
record = json.loads((folder / "spell-settings.json").read_text())
scene = bpy.context.scene
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--frames", type=int, nargs="+", default=[96, 16, 64])
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
for frame in args.frames:
    assert frame in record["frames"]
    scene.frame_set(frame)
    native = folder / "native"
    native.mkdir(exist_ok=True)
    scene.render.filepath = str(native / f"spell-{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
    expected = bpy.data.images.load(str(folder / f"spell-{frame:04d}.png"))
    actual = bpy.data.images.load(scene.render.filepath)
    assert expected.size[:] == actual.size[:] == (960, 540)
    assert array("f", expected.pixels[:]).tobytes() == array("f", actual.pixels[:]).tobytes()
    bpy.data.images.remove(expected)
    bpy.data.images.remove(actual)
scene.frame_set(104)
assert not any(
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    for obj in scene.objects
    if obj.get("vfx_role") == "layer"
)
(folder / "native-check.json").write_text(
    json.dumps(
        {
            "native_render_verified": True,
            "frames": args.frames,
            "clear_frame": 104,
            "scene_sha256": hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
        },
        indent=2,
    )
    + "\n"
)
print("SPELL_HD_NATIVE_PIXELS_IDENTICAL_AND_CLEAR")
