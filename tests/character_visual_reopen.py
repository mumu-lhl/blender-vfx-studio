"""Seek a real combat scene without loading the extension and compare actual HD pixels."""

import argparse
import hashlib
import json
import math
import sys
from array import array
from pathlib import Path

import bpy
from mathutils import Euler, Vector

assert not any("blender_vfx_studio" in name for name in sys.modules)
folder = Path(bpy.data.filepath).parent
settings = json.loads((folder / "character-settings.json").read_text())
assert settings["contact"]["verified_intersection"]
assert len([obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]) == 2
assert all(image.packed_file for image in bpy.data.images if image.source == "FILE")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--frames", type=int, nargs="+", default=[53, 16, 32])
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
frames = args.frames
if len(set(frames)) < 2:
    parser.error("Use at least two distinct sampled frames to check native animation")
scene = bpy.context.scene
for frame in (47, 49, 51):
    scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    socket = bpy.data.objects["Charge socket • world up"].evaluated_get(graph)
    blade = next(sample for sample in settings["blade_trace"] if sample["frame"] == frame)
    direction = (Vector(blade["tip"]) - Vector(blade["hilt"])).normalized()
    self_direction = (socket.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    assert self_direction.dot(direction) > 0.999, "Native charge release must aim along the blade"
scene.frame_set(47)
core = bpy.data.objects["Charge • Compressed Core"].children[0]
assert core.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices, (
    "The charge focus must survive until the slash begins"
)
scene.frame_set(53)
pressure = bpy.data.objects["Combat • Impact Burst"]
body = next(child for child in pressure.children if "Main Shards" in child.name).children[0]
rotation = (
    body.modifiers[0]
    .node_group.nodes["Pressure Surface Alignment"]
    .inputs["Rotation"]
    .default_value
)
surface_normal = (
    body.matrix_world.to_3x3() @ Euler(rotation).to_matrix() @ Vector((0, 0, 1))
).normalized()
assert surface_normal.dot(Vector(settings["contact"]["hits"][0]["normal"])) > 0.999, (
    "Native pressure sheets must open across the struck surface"
)
slash = bpy.data.objects["Combat • Arc Slash"].children[0]
mesh = slash.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
angles = []
for band in range(3):
    vertex = next(
        v
        for v in mesh.vertices
        if abs(mesh.attributes["vfx_wake"].data[v.index].value - band) < 0.01
        and abs(mesh.attributes["vfx_arc"].data[v.index].value - 0.5) < 0.01
        and mesh.attributes["vfx_inner"].data[v.index].value < 0.001
    )
    angles.append(math.atan2(vertex.co.y, vertex.co.x))
assert all((angles[0] - angle + math.pi) % math.tau - math.pi > 0.05 for angle in angles[1:]), (
    "Native wakes must trail the main slash rather than stack at the same angle"
)
poses = []
for frame in frames:
    if frame not in settings["frames"]:
        raise AssertionError("Render each requested frame before native validation")
    scene.frame_set(frame)
    rig = bpy.data.objects["Caster • Knight"].evaluated_get(bpy.context.evaluated_depsgraph_get())
    poses.append(tuple(rig.pose.bones["hand.r"].matrix.translation))
    destination = folder / "native"
    destination.mkdir(exist_ok=True)
    scene.render.filepath = str(destination / f"character-{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
    expected = bpy.data.images.load(str(folder / f"character-{frame:04d}.png"))
    actual = bpy.data.images.load(scene.render.filepath)
    assert expected.size[:] == actual.size[:] == (960, 540)
    assert array("f", expected.pixels[:]).tobytes() == array("f", actual.pixels[:]).tobytes()
    bpy.data.images.remove(expected)
    bpy.data.images.remove(actual)
assert poses[0] != poses[1], "The character attack must play, not just the VFX"
scene.frame_set(96)
assert not any(
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    for obj in scene.objects
    if obj.get("vfx_role") == "layer"
)
assert not any("blender_vfx_studio" in name for name in sys.modules)
record = {
    "native_render_verified": True,
    "frames": frames,
    "clear_frame": 96,
    "scene_sha256": hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
    "source_frame_sha256": {
        f"character-{frame:04d}.png": hashlib.sha256(
            (folder / f"character-{frame:04d}.png").read_bytes()
        ).hexdigest()
        for frame in frames
    },
}
(folder / "native-check.json").write_text(json.dumps(record, indent=2) + "\n")
print("CHARACTER_NATIVE_HD_PIXELS_IDENTICAL_RIG_ANIMATED_AND_TAIL_CLEAR")
