"""Re-render the saved proxy shot with no extension and compare all PNG channels."""

import sys
from array import array
from pathlib import Path

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
scene = bpy.context.scene
folder = Path(bpy.data.filepath).parent
assert scene.render.resolution_x == 960 and scene.render.resolution_y == 540
for frame in (36, 0, 8):
    scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    vertices = sum(
        len(obj.evaluated_get(graph).data.vertices)
        for obj in scene.objects
        if obj.get("vfx_role") == "layer"
    )
    assert (vertices > 0) if frame == 8 else vertices == 0
scene.render.filepath = str(folder / "native-check.png")
bpy.ops.render.render(write_still=True)
expected = bpy.data.images.load(str(folder / "combat-0008.png"))
actual = bpy.data.images.load(str(folder / "native-check.png"))
assert expected.size[:] == actual.size[:]
assert array("f", expected.pixels[:]).tobytes() == array("f", actual.pixels[:]).tobytes()
print("COMBAT_NATIVE_RENDER_ALL_CHANNELS_IDENTICAL")
