"""Check the actual saved charge scene's opening, peak and tail without importing the add-on."""

import sys
from array import array
from pathlib import Path

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
scene = bpy.context.scene
folder = Path(bpy.data.filepath).parent
scene.frame_set(49)
graph = bpy.context.evaluated_depsgraph_get()
assert not any(
    len(obj.evaluated_get(graph).data.vertices)
    for obj in scene.objects
    if obj.get("vfx_role") == "layer"
)
for frame in (4, 7, 22, 37, 48):
    scene.frame_set(frame)
    scene.render.filepath = str(folder / f"native-check-{frame}.png")
    bpy.ops.render.render(write_still=True)
    expected = bpy.data.images.load(str(folder / f"charge-{folder.name}-{frame:04d}.png"))
    actual = bpy.data.images.load(scene.render.filepath)
    assert expected.size[:] == actual.size[:] == (960, 540)
    assert array("f", expected.pixels[:]).tobytes() == array("f", actual.pixels[:]).tobytes()
    bpy.data.images.remove(expected)
    bpy.data.images.remove(actual)
print("CHARGE_OPENING_PEAK_AND_TAIL_NATIVE_ALL_CHANNELS_IDENTICAL")
