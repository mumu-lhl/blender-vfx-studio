"""Render three editable shield variations on CPU; optionally compare Eevee."""

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
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
if bpy.data.filepath:
    raise RuntimeError("Run in a fresh Blender process, without an open project")
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_set(1)
for index, (label, settings) in enumerate(
    (
        ("Fresnel", {}),
        ("Dissolve", {"dissolve": 0.54, "color_0": 0.7, "color_1": 0.08}),
        ("Tight Rim", {"rim_power": 1.5, "color_0": 0.08, "color_1": 1.0, "color_2": 0.4}),
    )
):
    root = core.create_shield(bpy.context)
    root.location = ((index - 1) * 3.3, 0, 0)
    for key, value in {"radius": 1.3, "dissolve": 0.0, "strength": 4.0, **settings}.items():
        root[key] = value
    root.update_tag()
    # Ordinary scene objects demonstrate visibility through the shield center.
    bpy.ops.mesh.primitive_cube_add(size=0.7, location=root.location)
    cube = bpy.context.object
    cube.rotation_euler = (0.3, 0.2, 0.4)
    material = bpy.data.materials.new("Preview Cube")
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        0.2,
        0.25,
        0.3,
        1,
    )
    cube.data.materials.append(material)
    text = bpy.data.curves.new(label, "FONT")
    text.body, text.align_x, text.size = label, "CENTER", 0.28
    obj = bpy.data.objects.new(label, text)
    scene.collection.objects.link(obj)
    obj.location = (root.location.x, -0.1, -1.7)
    obj.rotation_euler = (Vector((0, -10, 3)) - obj.location).to_track_quat("Z", "Y").to_euler()
    mat = bpy.data.materials.new("Preview Label")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Emission Color"].default_value = (0.6, 0.7, 0.8, 1)
    bsdf.inputs["Emission Strength"].default_value = 1
    text.materials.append(mat)
bpy.ops.object.camera_add(location=(0, -10, 3))
cam = bpy.context.object
cam.rotation_euler = (Vector((0, 0, -0.2)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.type, cam.data.ortho_scale = "ORTHO", 11
scene.camera = cam
bpy.ops.object.light_add(type="AREA", location=(0, -3, 6))
bpy.context.object.data.energy = 700
bpy.context.object.data.size = 6
scene.world = bpy.data.worlds.new("Preview Background")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.008, 0.012, 0.025, 1)
screen = core.create_screen(bpy.context)
screen["strength"] = 0.2
screen.update_tag()
scene.frame_set(13)
scene.render.engine = args.engine
scene.render.compositor_device = "CPU"
scene.cycles.device = "CPU"
scene.cycles.samples = 32
scene.cycles.use_denoising = False
scene.render.resolution_x, scene.render.resolution_y = 900, 360
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
output = ROOT / "work"
output.mkdir(exist_ok=True)
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(
    output / ("shield-preview.png" if args.engine == "CYCLES" else "shield-eevee.png")
)
bpy.ops.wm.save_as_mainfile(filepath=str(output / "shield-preview.blend"))
bpy.ops.render.render(write_still=True)
print("SHIELD_PREVIEW_OK", args.engine)
