"""Native-only render helpers shared with the extension-free reload check."""

from pathlib import Path

import bpy

WORK = Path(__file__).resolve().parents[1] / "work"


def camera():
    scene = bpy.context.scene
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 5)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 4
    scene.camera = cam
    scene.world = bpy.data.worlds.new("Black")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
    scene.render.engine = "CYCLES"
    scene.render.compositor_device = "CPU"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 48
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(WORK / "particle-pixels.png")


def render_pixels(frame):
    bpy.context.scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(bpy.context.scene.render.filepath, check_existing=False)
    result = list(image.pixels)
    bpy.data.images.remove(image)
    return result
