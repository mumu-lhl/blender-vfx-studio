"""Recreate a CPU Cycles preview: blender -b --python tools/preview.py."""

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from demo_atlas import create as demo_atlas  # noqa: E402

from blender_vfx_studio import core, trail  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--engine", choices=("CYCLES", "BLENDER_EEVEE"), default="CYCLES")
parser.add_argument("--scale", type=int, default=100)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])

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
output = ROOT / "work"
output.mkdir(exist_ok=True)
sprite = core.create_flipbook(bpy.context, demo_atlas(output / "demo-atlas.png"))
sprite.location = (0, -2.5, 1.4)
sprite.rotation_euler = (math.radians(70), 0, 0)
sprite["strength"] = 3.0
sprite.update_tag()
particles = core.create_particle(bpy.context)
particles.location = (-0.5, 1, 2)
for key, value in {
    "count": 48,
    "size": 0.08,
    "velocity": 2.0,
    "gravity": 1.5,
    "spawn_radius": 0.2,
    "fade": 0.3,
    "strength": 6.0,
}.items():
    particles[key] = value
particles.update_tag()
emitter = bpy.data.objects.new("Ribbon Preview Source", None)
scene.collection.objects.link(emitter)
for frame in range(1, 25):
    t = (frame - 1) / 23
    emitter.location = (-3 + 6 * t, 0.3, 1.4 + 0.6 * math.sin(t * math.pi))
    emitter.keyframe_insert(data_path="location", frame=frame)
ribbon = trail.create(bpy.context, emitter, first=1, last=24)
ribbon["width"] = 0.35
ribbon["length"] = 0.65
ribbon["color_0"], ribbon["color_1"], ribbon["color_2"] = 0.05, 1.0, 0.4
ribbon.update_tag()
screen = core.create_screen(bpy.context)
screen["strength"] = 0.6
screen["glow_size"] = 0.25
screen.update_tag()
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
scene.render.compositor_device = "CPU"
scene.render.engine = args.engine
scene.cycles.device = "CPU"
scene.cycles.samples = 32
scene.cycles.use_denoising = False
scene.render.resolution_x = 800
scene.render.resolution_y = 500
scene.render.resolution_percentage = max(1, min(args.scale, 100))
scene.view_settings.view_transform = "AgX"
output = ROOT / "work"
output.mkdir(exist_ok=True)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(
    output / ("preview.png" if args.engine == "CYCLES" else "preview-eevee.png")
)
core.select(bpy.context, left)
bpy.ops.wm.save_as_mainfile(filepath=str(output / "preview.blend"))
bpy.ops.render.render(write_still=True)
print("PREVIEW_OK", args.engine)
