"""Native compositor playback in a new process with script auto-execution disabled."""

import sys

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
root = next(o for o in bpy.data.objects if o.get("vfx_module") == "screen.glare")
scene = bpy.context.scene
assert root["vfx_scene"] == scene
layer = next(n for n in scene.compositing_node_group.nodes if n.get("vfx_id") == root["vfx_id"])
for frame, expected in [(3, 0.5), (1, 1), (5, 1), (0, 0), (2, 0.75)]:
    scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(scene.render.filepath, check_existing=False)
    index = (16 * 32 + 16) * 4
    values = image.pixels[index : index + 3]
    assert all(abs(c - expected) < 0.01 for c in values), (frame, list(values), expected)
    bpy.data.images.remove(image)
    assert all(
        c.driver.is_valid and c.driver.is_simple_expression
        for c in layer.node_tree.animation_data.drivers
    )
print("SCREEN_NATIVE_REOPEN_OK")
