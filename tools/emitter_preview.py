"""Render fill, steady emission and tail phases of native continuous emitters."""

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import core  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--engine", choices=("CYCLES", "BLENDER_EEVEE"), default="CYCLES")
parser.add_argument("--scale", type=int, default=100)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
if bpy.data.filepath:
    raise RuntimeError("Use a fresh Blender process without an open project")
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_set(1)
for i, (label, seconds, color) in enumerate(
    (
        ("Fill (0.2 s)", 0.2, (0.1, 0.65, 1)),
        ("Emitting (1.4 s)", 1.4, (1, 0.25, 0.02)),
        ("Tail (2.6 s)", 2.6, (0.7, 0.08, 1)),
    )
):
    root = core.create_emitter(bpy.context)
    root.location.x = (i - 1) * 2.8
    for key, value in dict(
        start=61 - seconds * 24,
        duration=72.0,
        rate=48.0,
        lifetime=0.8,
        emission_seconds=2.2,
        velocity=3.0,
        gravity=3.0,
        spread=0.35,
        size=0.13,
        strength=3.0,
        seed=7,
    ).items():
        root[key] = value
    for index, value in enumerate(color):
        root[f"color_{index}"] = value
    root.update_tag()
    # A small ordinary scene mesh marks the emitter origin.
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.22,
        minor_radius=0.015,
        major_segments=32,
        minor_segments=6,
        location=(root.location.x, 0, 0),
    )
    mat = bpy.data.materials.new("Preview Origin")
    mat.use_nodes = True
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Emission Color"].default_value = (*color, 1)
    shader.inputs["Emission Strength"].default_value = 1
    bpy.context.object.data.materials.append(mat)
    text = bpy.data.curves.new(label, "FONT")
    text.body, text.align_x, text.size = label, "CENTER", 0.24
    obj = bpy.data.objects.new(label, text)
    scene.collection.objects.link(obj)
    obj.location = (root.location.x, -0.4, -0.5)
    obj.rotation_euler = (Vector((0, -11, 4)) - obj.location).to_track_quat("Z", "Y").to_euler()
    text.materials.append(mat)
bpy.ops.object.camera_add(location=(0, -11, 4))
cam = bpy.context.object
cam.rotation_euler = (Vector((0, 0, 0.6)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.type, cam.data.ortho_scale = "ORTHO", 9.4
scene.camera = cam
scene.world = bpy.data.worlds.new("Preview Background")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.006, 0.009, 0.02, 1)
screen = core.create_screen(bpy.context)
screen["strength"] = 0.3
screen.update_tag()
scene.frame_set(61)
scene.render.engine = args.engine
scene.render.compositor_device = "CPU"
scene.cycles.device = "CPU"
scene.cycles.samples = 32
scene.cycles.use_denoising = False
scene.render.resolution_x, scene.render.resolution_y = 900, 450
scene.render.resolution_percentage = max(1, min(args.scale, 100))
scene.view_settings.view_transform = "AgX"
output = ROOT / "work"
output.mkdir(exist_ok=True)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(
    output / ("emitter-preview.png" if args.engine == "CYCLES" else "emitter-eevee.png")
)
bpy.ops.wm.save_as_mainfile(filepath=str(output / "emitter-preview.blend"))
bpy.ops.render.render(write_still=True)
print("EMITTER_PREVIEW_OK", args.engine)
