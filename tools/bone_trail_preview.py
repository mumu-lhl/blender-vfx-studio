"""Compare head and tail sampling on a rotating bone using native saved ribbons."""

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import trail  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--engine", choices=("CYCLES", "BLENDER_EEVEE"), default="CYCLES")
parser.add_argument("--scale", type=int, default=100)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
if bpy.data.filepath:
    raise RuntimeError("Use a fresh Blender process without an open project")
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def emission(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    shader = tree.nodes.new("ShaderNodeEmission")
    shader.inputs["Color"].default_value = (*color, 1)
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(shader.outputs[0], out.inputs["Surface"])
    return mat


white = emission("Preview labels and blade", (0.65, 0.75, 0.85))
for x, use_tail, label in (
    (-2.5, False, "Head: stationary pivot"),
    (2.5, True, "Tail: rotating blade tip"),
):
    scene.frame_set(1)
    bpy.ops.object.armature_add(location=(x, 0, 0))
    rig = bpy.context.object
    bpy.ops.object.mode_set(mode="EDIT")
    rig.data.edit_bones[0].tail = (0, 2, 0)
    bpy.ops.object.mode_set(mode="OBJECT")
    bone = rig.pose.bones[0]
    bone.rotation_mode = "XYZ"
    for frame, angle in ((1, -60), (25, 60)):
        bone.rotation_euler.z = math.radians(angle)
        bone.keyframe_insert(data_path="rotation_euler", frame=frame)
    root = trail.create(bpy.context, rig, bone.name, 1, 25, 1, bone_tail=use_tail)
    for key, value in dict(width=0.14, length=1.0, fade=0.0, strength=2.0).items():
        root[key] = value
    for i, value in enumerate((0.1, 0.6, 1.0)):
        root[f"color_{i}"] = value
    root.update_tag()
    scene.frame_set(24)
    evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    pose = evaluated.pose.bones[bone.name]
    points = [evaluated.matrix_world @ p for p in (pose.head, pose.tail)]
    curve = bpy.data.curves.new("Blade at frame 24", "CURVE")
    curve.dimensions, curve.bevel_depth, curve.bevel_resolution = "3D", 0.025, 2
    spline = curve.splines.new("POLY")
    spline.points.add(1)
    for point, position in zip(spline.points, points):
        point.co = (*position, 1)
    obj = bpy.data.objects.new(curve.name, curve)
    scene.collection.objects.link(obj)
    curve.materials.append(white)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.07, location=points[0])
    bpy.context.object.data.materials.append(white)
    text = bpy.data.curves.new(label, "FONT")
    text.body, text.align_x, text.size = label, "CENTER", 0.23
    obj = bpy.data.objects.new(label, text)
    scene.collection.objects.link(obj)
    obj.location = (x, -0.5, 0)
    text.materials.append(white)

bpy.ops.object.camera_add(location=(0, 0.8, 10))
cam = bpy.context.object
cam.rotation_euler = (Vector((0, 0.8, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.type, cam.data.ortho_scale = "ORTHO", 10
scene.camera = cam
scene.world = bpy.data.worlds.new("Preview Background")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.005, 0.005, 0.005, 1)
scene.render.engine = args.engine
if args.engine == "CYCLES":
    scene.cycles.device, scene.cycles.samples = "CPU", 32
scene.view_settings.view_transform = "Standard"
scene.render.resolution_x, scene.render.resolution_y = 1000, 450
scene.render.resolution_percentage = args.scale
work = ROOT / "work"
work.mkdir(exist_ok=True)
scene.render.filepath = str(work / "bone-trail-preview.png")
bpy.ops.wm.save_as_mainfile(filepath=str(work / "bone-trail-preview.blend"))
bpy.ops.render.render(write_still=True)
