"""Compare the actual saved HD Impact frames without importing the extension."""

import json
import sys
from array import array
from pathlib import Path

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
file = Path(bpy.data.filepath)
record = json.loads(file.with_name(file.stem + "-settings.json").read_text(encoding="utf-8"))
scene = bpy.context.scene
native = file.parent / "native"
native.mkdir(exist_ok=True)
for frame in (14, 2, 5):
    scene.frame_set(frame)
    scene.render.filepath = str(native / f"{file.stem}-{frame}.png")
    bpy.ops.render.render(write_still=True)
    expected = bpy.data.images.load(str(file.parent / record["images"][str(frame)]))
    actual = bpy.data.images.load(scene.render.filepath)
    assert expected.size[:] == actual.size[:] == (960, 540)
    assert array("f", expected.pixels[:]).tobytes() == array("f", actual.pixels[:]).tobytes()
    bpy.data.images.remove(expected)
    bpy.data.images.remove(actual)
scene.frame_set(25)
assert not any(
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    for obj in scene.objects
    if obj.get("vfx_role") == "layer"
)
print("IMPACT_HD_NATIVE_APPEAR_PEAK_RELEASE_IDENTICAL_AND_TAIL_CLEAR")
