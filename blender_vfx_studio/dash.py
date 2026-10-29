"""Explicitly capture a few posed meshes; native shield nodes play the echoes."""

import math

import bpy

from . import composition, core
from .animation import curves
from .nodes import PROGRESS, TIME_PROPS, drive, node
from .parameters import GROUP_PARAMETERS

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
    """Keep a transparent body while the colored contour outlasts its fill."""
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
    body.inputs[1].default_value, body.inputs[2].default_value = 0.70, 0.30
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
    border.inputs["From Min"].default_value, border.inputs["From Max"].default_value = 0.12, 0.38
    tree.links.new(tree.nodes["Rim Falloff"].outputs[0], border.inputs["Value"])
    dark = node(
        tree, "ShaderNodeVectorMath", "Deep Spectral Outline", -400, -650, operation="SCALE"
    )
    tree.links.new(color.outputs[0], dark.inputs[0])
    dark.inputs["Scale"].default_value = 0.08
    mix = node(tree, "ShaderNodeMixRGB", "Cyan Edge With Dark Border", -150, -450)
    tree.links.new(border.outputs[0], mix.inputs[0])
    tree.links.new(color.outputs[0], mix.inputs[1])
    tree.links.new(dark.outputs[0], mix.inputs[2])
    tree.links.new(mix.outputs[0], emission.inputs["Color"])

    contour_life = node(tree, "ShaderNodeValue", "Retained Contour Life", -900, -900)
    drive(
        contour_life.outputs[0],
        "default_value",
        member,
        f"o*pow(max(1-({PROGRESS}),0),0.45*f)",
        dict(TIME_PROPS, o="opacity", f="fade"),
    )
    contour = border.outputs[0]
    for index, (label, factor) in enumerate(
        (
            ("Contour Age", contour_life.outputs[0]),
            ("Dissolve Contour", tree.nodes["Dissolve"].outputs[0]),
            ("Exterior Contour", tree.nodes["Exterior Only"].outputs[0]),
        )
    ):
        mask = node(tree, "ShaderNodeMath", label, -600 + index * 220, -900, operation="MULTIPLY")
        tree.links.new(contour, mask.inputs[0])
        tree.links.new(factor, mask.inputs[1])
        contour = mask.outputs[0]
    opacity = node(
        tree, "ShaderNodeMath", "Fill Or Retained Contour", 150, -650, operation="MAXIMUM"
    )
    tree.links.new(tree.nodes["Final Opacity"].outputs[0], opacity.inputs[0])
    tree.links.new(contour, opacity.inputs[1])
    tree.links.new(opacity.outputs[0], tree.nodes["Shield Surface"].inputs[0])


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


def _echoes(group):
    group = core.resolve(group)
    if group is None or group["vfx_module"] != "core.composition":
        raise ValueError("Select a captured echo composition")
    try:
        frames = list(group.get("vfx_capture_frames", ()))
    except TypeError:
        raise ValueError("Repair invalid capture frame metadata") from None
    children = composition.members(group)
    if not 2 <= len(frames) == len(children) <= 32 or any(
        child["vfx_module"] != "shader.shield" or "vfx_capture_frame" not in child
        for child in children
    ):
        raise ValueError("Select an intact captured echo composition; edit mixed layers separately")
    captured = [child["vfx_capture_frame"] for child in children]
    if any(type(f) not in (int, float) or not math.isfinite(f) for f in frames + captured):
        raise ValueError("Repair invalid capture frame metadata")
    if sorted(frames) != sorted(captured) or len(set(frames)) != len(frames):
        raise ValueError("Capture frame metadata does not match the pose layers")
    return group, sorted(children, key=lambda child: child["vfx_capture_frame"])


def tail_frames(group):
    """Current first-pose lifetime before group and layer Speed, for the dialog."""
    group, children = _echoes(group)
    return max(1.0, float(group["duration"]) * float(children[0]["vfx_duration_ratio"]))


def set_tail(context, group, tail):
    """Adjust owned timing coefficients, retaining entry spacing and captured data."""
    if type(tail) not in (int, float) or not math.isfinite(tail) or not 1 <= tail <= 100000:
        raise ValueError("Echo tail must be between 1 and 100000 frames")
    group, children = _echoes(group)
    if any(
        o.library or o.override_library or o.name not in context.scene.objects
        for o in [group, *children]
    ):
        raise ValueError("Echo timing requires local controllers in the active scene")
    if any(c.data_path == '["duration"]' for c in curves(group)):
        raise ValueError("Group Duration is animated; edit its timing channels directly")
    coefficients = ("vfx_offset_ratio", "vfx_duration_ratio", "vfx_local_speed")
    for child in children:
        composition.check_timing(child)
        if any(c.data_path in {f'["{k}"]' for k in coefficients} for c in curves(child)):
            raise ValueError("Layer timing ratios or Local Speed are animated; edit them directly")
    if any(k not in c or type(c[k]) not in (int, float) for c in children for k in coefficients):
        raise ValueError("Repair invalid echo timing coefficients")
    if type(group.get("duration")) not in (int, float):
        raise ValueError("Repair invalid echo group duration")
    duration = float(group["duration"])
    previous = [(c, *(float(c[k]) for k in coefficients)) for c in children]
    if (
        not math.isfinite(duration)
        or duration < 1
        or any(not math.isfinite(value) for row in previous for value in row[1:])
    ):
        raise ValueError("Repair invalid echo timing before setting the tail")
    offsets = [duration * max(row[1], 0) for row in previous]
    total = max(
        1.0, *(offset + tail / max(row[3], 0.001) for offset, row in zip(offsets, previous))
    )
    if total > GROUP_PARAMETERS["duration"][2]:
        raise ValueError("Tail would exceed the composition duration limit of 100000 frames")
    try:
        for child, offset in zip(children, offsets):
            child["vfx_offset_ratio"] = offset / total
            child["vfx_duration_ratio"] = float(tail) / total
            child.update_tag()
        group["duration"] = total
        group.update_tag()
        context.view_layer.update()
    except Exception:
        for child, offset, ratio, _ in previous:
            child["vfx_offset_ratio"], child["vfx_duration_ratio"] = offset, ratio
            child.update_tag()
        group["duration"] = duration
        group.update_tag()
        raise
    return group
