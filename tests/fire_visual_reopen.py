"""Compare real fire HD stages after native addon-free out-of-order seeking."""

import hashlib
import json
import sys
from array import array
from pathlib import Path

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
folder = Path(bpy.data.filepath).parent
record = json.loads((folder / "fire-settings.json").read_text())
scene = bpy.context.scene
for frame in (60, 25, 36):
    assert frame in record["frames"]
    scene.frame_set(frame)
    native = folder / "native"
    native.mkdir(exist_ok=True)
    scene.render.filepath = str(native / f"fire-{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
    expected = bpy.data.images.load(str(folder / f"fire-{frame:04d}.png"))
    actual = bpy.data.images.load(scene.render.filepath)
    assert expected.size[:] == actual.size[:] == (960, 540)
    assert array("f", expected.pixels[:]).tobytes() == array("f", actual.pixels[:]).tobytes()
    bpy.data.images.remove(expected)
    bpy.data.images.remove(actual)
scene.frame_set(70)
assert not any(
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    for obj in scene.objects
    if obj.get("vfx_role") == "layer"
)
(folder / "native-check.json").write_text(
    json.dumps(
        {
            "native_render_verified": True,
            "frames": [60, 25, 36],
            "clear_frame": 70,
            "scene_sha256": hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
        },
        indent=2,
    )
    + "\n"
)
print("FIRE_HD_NATIVE_PIXELS_IDENTICAL_AND_CLEAR")
