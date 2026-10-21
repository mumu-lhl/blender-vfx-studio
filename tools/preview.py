"""Recreate a CPU Cycles preview: blender -b --python tools/preview.py."""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import core  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_set(1)
left = core.create(bpy.context, "SHOCKWAVE")
left.location = (-1.8, 0, 0.04)
right = core.create(bpy.context, "ENERGY_RING")
right.location = (1.8, 0.2, 1.4)
right.rotation_euler = (math.radians(70), 0, 0)
for key, value in {"color_0": 0.6, "color_1": 0.05, "color_2": 1.0, "dissolve": 0.52}.items():
    right[key] = value
right.update_tag()
scene.frame_set(13)
bpy.ops.mesh.primitive_plane_add(size=200)
floor = bpy.context.object
mat = bpy.data.materials.new("Preview Floor")
mat.diffuse_color = (0.018, 0.025, 0.04, 1)
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.006, 0.01, 0.018, 1)
mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.7
floor.data.materials.append(mat)
bpy.ops.object.camera_add(location=(7, -10, 10))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, 0.5)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 10.5
scene.camera = camera
bpy.ops.object.light_add(type="AREA", location=(0, -2, 7))
bpy.context.object.data.energy = 80
bpy.context.object.data.shape = "DISK"
bpy.context.object.data.size = 8
scene.world = bpy.data.worlds.new("Preview World")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.015, 0.02, 0.035, 1)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 32
scene.cycles.use_denoising = False
scene.render.resolution_x = 800
scene.render.resolution_y = 500
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
output = ROOT / "work"
output.mkdir(exist_ok=True)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(output / "preview.png")
core.select(bpy.context, left)
bpy.ops.wm.save_as_mainfile(filepath=str(output / "preview.blend"))
bpy.ops.render.render(write_still=True)
print("CPU_PREVIEW_OK")
