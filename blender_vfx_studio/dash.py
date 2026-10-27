"""Explicitly capture a few posed meshes; native shield nodes play the echoes."""

import math

import bpy

from . import composition, core
from .nodes import PROGRESS, TIME_PROPS, drive, node

QUALITY_COUNTS = {"LOW": 2, "MEDIUM": 3, "HIGH": 4}
MAX_CAPTURE_VERTICES = 1_000_000  # Allocation guard, not a performance promise.


def sample(context, source, first, last, quality, *, count=None):
    if quality not in QUALITY_COUNTS:
        raise ValueError("Unknown dash quality")
    if count is None:
        count = QUALITY_COUNTS[quality]
    if type(count) is not int or not 2 <= count <= 32:
        raise ValueError("Echo count must be an integer between 2 and 32")
    if (
        source is None
        or source.name not in context.scene.objects
        or source.type not in {"MESH", "ARMATURE"}
        or core.resolve(source) is not None
    ):
        raise ValueError("Choose a mesh or armature in this scene outside the VFX hierarchy")
    if type(first) is not int or type(last) is not int or not -100000 <= first < last <= 100000:
        raise ValueError("Use increasing integer endpoints between -100000 and 100000")
    scene = context.scene
    if scene.render.frame_map_old != scene.render.frame_map_new:
        raise ValueError("Capture with 1:1 Time Remapping; retime the stored echoes afterwards")
    candidates = (
        [source]
        if source.type == "MESH"
        else [o for o in source.children_recursive if o.type == "MESH" and core.resolve(o) is None]
    )
    if not candidates:
        raise ValueError("The source has no mesh descendants to capture")
    frame, subframe = scene.frame_current, scene.frame_subframe
    samples, allocated = [], 0
    try:
        scene.frame_set(last)
        origin = source.evaluated_get(
            context.evaluated_depsgraph_get()
        ).matrix_world.translation.copy()
        for index in range(count):
            current = first + (last - first) * index / (count - 1)
            scene.frame_set(math.floor(current), subframe=current % 1)
            graph = context.evaluated_depsgraph_get()
            vertices, faces = [], []
            for obj in candidates:
                if obj.hide_render or not obj.visible_get():
                    continue
                evaluated = obj.evaluated_get(graph)
                mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=graph)
                try:
                    allocated += len(mesh.vertices)
                    if allocated > MAX_CAPTURE_VERTICES:
                        raise ValueError(
                            "Capture exceeds one million stored vertices; use fewer echoes or meshes"
                        )
                    offset = len(vertices)
                    for vertex in mesh.vertices:
                        position = evaluated.matrix_world @ vertex.co - origin
                        if not all(math.isfinite(v) and abs(v) <= 1e8 for v in position):
                            raise ValueError(
                                "Source contains invalid or excessively large positions"
                            )
                        vertices.append(tuple(position))
                    mirrored = evaluated.matrix_world.determinant() < 0
                    faces.extend(
                        tuple(
                            offset + i
                            for i in (reversed(face.vertices) if mirrored else face.vertices)
                        )
                        for face in mesh.polygons
                    )
                finally:
                    evaluated.to_mesh_clear()
            if not vertices or not faces:
                raise ValueError(
                    f"No visible evaluated mesh at frame {current}; realize instances first"
                )
            samples.append((current, vertices, faces))
    finally:
        scene.frame_set(frame, subframe=subframe)
    return origin, samples


def _surface(member):
    """Retain shield controls, add a legible body and a faster opacity falloff."""
    material = member.children[0].data.materials[0]
    material.name = "VFX • Spectral Dash Echo"
    material.surface_render_method = "BLENDED"
    material.use_backface_culling = True  # The saved shader already makes back faces transparent.
    tree = material.node_tree
    body = node(tree, "ShaderNodeMath", "Body Beneath The Rim", -650, 650, operation="MULTIPLY_ADD")
    edge = node(tree, "ShaderNodeMapRange", "Defined Spectral Edge", -900, 650)
    edge.interpolation_type, edge.clamp = "SMOOTHSTEP", True
    edge.inputs["From Min"].default_value, edge.inputs["From Max"].default_value = 0.025, 0.3
    tree.links.new(tree.nodes["Rim Falloff"].outputs[0], edge.inputs["Value"])
    tree.links.new(edge.outputs[0], body.inputs[0])
    body.inputs[1].default_value, body.inputs[2].default_value = 0.85, 0.15
    tree.links.new(body.outputs[0], tree.nodes["Rim × Noise"].inputs[0])
    fade = tree.nodes["Lifetime Opacity"].outputs[0]
    fade.driver_remove("default_value")
    drive(
        fade,
        "default_value",
        member,
        f"o*pow(max(1-({PROGRESS}),0),0.85*f)",
        dict(TIME_PROPS, o="opacity", f="fade"),
    )

    color = node(tree, "ShaderNodeCombineXYZ", "Editable Spectral Tint", -900, -450)
    emission = tree.nodes["Shield Emission"]
    for index in range(3):
        emission.inputs["Color"].driver_remove("default_value", index)
        drive(color.inputs[index], "default_value", member, "c", {"c": f"color_{index}"})
    border = node(tree, "ShaderNodeMapRange", "Dark Outer Contour", -650, -450)
    border.interpolation_type, border.clamp = "SMOOTHSTEP", True
    border.inputs["From Min"].default_value, border.inputs["From Max"].default_value = 0.45, 0.8
    tree.links.new(tree.nodes["Fresnel Edge"].outputs[0], border.inputs["Value"])
    dark = node(
        tree, "ShaderNodeVectorMath", "Deep Spectral Outline", -400, -650, operation="SCALE"
    )
    tree.links.new(color.outputs[0], dark.inputs[0])
    dark.inputs["Scale"].default_value = 0.18
    mix = node(tree, "ShaderNodeMixRGB", "Cyan Edge With Dark Border", -150, -450)
    tree.links.new(border.outputs[0], mix.inputs[0])
    tree.links.new(color.outputs[0], mix.inputs[1])
    tree.links.new(dark.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], emission.inputs["Color"])


def create(context, source, first, last, quality="MEDIUM", *, tail=18.0, count=None):
    if type(tail) not in (int, float) or not math.isfinite(tail) or not 1 <= tail <= 100000:
        raise ValueError("Echo tail must be between 1 and 100000 frames")
    origin, samples = sample(context, source, first, last, quality, count=count)
    members = []
    try:
        for index, (frame, vertices, faces) in enumerate(samples):
            member = core.create_shield(context, "LOW")
            members.append(member)
            member.name = f"Dash • Pose {index + 1}"
            member["vfx_quality"] = quality
            member["start"], member["duration"], member["loop"] = float(frame), float(tail), False
            for key, value in dict(
                radius=1.0,
                expansion=0.0,
                opacity=0.82,
                strength=1.0,
                ior=1.3,
                rim_power=1.0,
                noise_scale=6.0,
                flow=1.5,
                dissolve=0.04,
                fade=1.0,
            ).items():
                member[key] = value
            # Older poses carry less light; they never rival the live character.
            t = index / max(1, len(samples) - 1)
            member["color_0"], member["color_1"], member["color_2"] = (
                0.015,
                0.16 + 0.25 * t,
                0.55 + 0.35 * t,
            )
            member["vfx_parameter_keys"] = (
                "opacity,strength,ior,rim_power,noise_scale,flow,dissolve,fade"
            )
            member["vfx_capture_frame"] = frame
            layer = member.children[0]
            layer.name = "VFX • Frozen Character Pose"
            layer.data.name = "VFX • Editable Captured Pose"
            layer.data.clear_geometry()
            layer.data.from_pydata(vertices, [], faces)
            for face in layer.data.polygons:
                face.use_smooth = True
            layer.data.update()
            member.location = origin
            _surface(member)
            member.update_tag()
        group = composition.create(context, members)
        worlds = [m.matrix_world.copy() for m in members]
        group.location = origin
        context.view_layer.update()
        for member, world in zip(members, worlds):
            member.matrix_world = world
        group.name, group["vfx_quality"], group["loop"] = "Character Dash Echoes", quality, False
        group["vfx_capture_source_name"] = source.name
        group["vfx_capture_frames"] = [s[0] for s in samples]
        core.select(context, group)
        return group
    except Exception:
        for member in members:
            if member.name in bpy.data.objects:
                core.delete(member)
        raise
