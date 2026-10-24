"""Render the saved handoff without the extension; ensure the final frame is clear."""

import sys
from array import array
from pathlib import Path

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
scene = bpy.context.scene
assert scene.frame_current == 31
folder = Path(bpy.data.filepath).parent
scene.frame_set(60)
graph = bpy.context.evaluated_depsgraph_get()
assert not any(
    len(obj.evaluated_get(graph).data.vertices)
    for obj in scene.objects
    if obj.get("vfx_role") == "layer"
)
for frame in (31, 33):
    scene.frame_set(frame)
    scene.render.filepath = str(folder / f"native-check-{frame}.png")
    bpy.ops.render.render(write_still=True)
    expected = bpy.data.images.load(str(folder / f"handoff-{frame:04d}.png"))
    actual = bpy.data.images.load(scene.render.filepath)
    assert expected.size[:] == actual.size[:] == (960, 540)
    assert array("f", expected.pixels[:]).tobytes() == array("f", actual.pixels[:]).tobytes()
    bpy.data.images.remove(expected)
    bpy.data.images.remove(actual)
print("CHARGE_HANDOFF_NATIVE_ALL_CHANNELS_IDENTICAL_AND_TAIL_CLEAR")
