"""Author one combat shot using existing native clips, effects and cel materials."""

import bpy


def _time_curve(strip, keys, end):
    strip.frame_end = end
    strip.use_animated_time = True
    strip.use_animated_time_cyclic = False
    for curve in strip.fcurves:
        if curve.data_path == "strip_time":
            curve.keyframe_points.clear()
    first, last = strip.action_frame_start, strip.action_frame_end
    for frame, fraction in keys:
        strip.strip_time = first + (last - first) * fraction
        strip.keyframe_insert(data_path="strip_time", frame=frame)
    for curve in strip.fcurves:
        if curve.data_path == "strip_time":
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"


def prepare_attack(strip):
    """Load the existing backswing, hold it, then freeze contact for two frames."""
    _time_curve(
        strip,
        (
            (1, 0),
            (12, 0.055),
            (28, 0.24),
            (39, 0.24),
            (43, 0.26),
            (47, 0.3125),
            (49, 0.375),
            (51, 0.375),
            (71, 1),
        ),
        75,
    )


def prepare_reaction(strip, hit):
    strip.blend_in = 0
    _time_curve(strip, ((hit, 0), (hit + 2, 0), (hit + 24, 1)), hit + 26)


def _node_keys(socket, values):
    for frame, value in values:
        socket.default_value = value
        socket.keyframe_insert(data_path="default_value", frame=frame)


def direct_effects(fixture):
    """Let gathered energy reach the cut, then separate flash and aftermath."""
    from mathutils import Vector

    from blender_vfx_studio import composition
    from blender_vfx_studio.animation import curves

    charge, slash, impact = fixture["effects"]
    hit = fixture["contact"]["frame"]
    sample = next(q for q in fixture["trace"] if q["frame"] == hit)
    blade = Vector(sample["tip"]) - Vector(sample["hilt"])
    point = Vector(fixture["contact"]["hits"][0]["position"])
    fraction = (point - Vector(sample["hilt"])).dot(blade) / blade.length_squared
    socket = bpy.data.objects["Charge socket • blade midpoint"]
    for frame, amount in (
        (1, 0.48),
        (28, 0.52),
        (39, 0.52),
        (43, 0.68),
        (47, fraction),
        (hit, fraction),
        (hit + 5, fraction),
    ):
        socket.location = fixture["tip_local"] * amount
        socket.keyframe_insert(data_path="location", frame=frame)
    for curve in curves(socket):
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    for member in composition.members(charge):
        if member.name.endswith("Compressed Core"):
            tree = member.children[0].modifiers[0].node_group
            _node_keys(
                tree.nodes["Nucleus Stored Size"].outputs[0],
                (
                    (1, 1.9),
                    (20, 2.2),
                    (32, 2.65),
                    (39, 2.8),
                    (43, 1.9),
                    (47, 1.15),
                    (hit, 0.9),
                    (hit + 5, 0.6),
                ),
            )
            tree.nodes["Intake Weight"].outputs[0].default_value = 0.28
        elif member.name.endswith("Spiral Motes"):
            member["rate"], member["size"], member["strength"] = 6, 0.052, 0.65
        else:
            member["strength"] *= 0.6
        member.update_tag()
    slash["bank"], slash["contour"] = 0.05, 0.2
    slash["afterimage"] = 0.24
    # Existing independent layer clocks remain native composition drivers.
    timings = {
        "Core Flash": (0, 2),
        "Burst Core": (1, 10),
        "Main Shards": (1, 14),
        "Shockwave": (2, 16),
        "Embers": (3, 21),
    }
    for member in composition.members(impact):
        offset, duration = next(
            value for label, value in timings.items() if member.name.endswith(label)
        )
        member["vfx_offset_ratio"] = offset / impact["duration"]
        member["vfx_duration_ratio"] = duration / impact["duration"]
        if member.name.endswith("Core Flash"):
            member["size"] = 0.3
            for index, value in enumerate((1.0, 0.86, 0.62)):
                member[f"color_{index}"] = value
        elif member.name.endswith("Burst Core"):
            member["opacity"] = 0.65
        elif member.name.endswith("Shockwave"):
            member["strength"] = 0.9
        member.update_tag()
    fixture["direction"] = {
        "hold_frames": [hit, hit + 1, hit + 2],
        "blade_energy_fraction": fraction,
        "realtime_playback_reviewed": False,
    }
    for obj in (charge, slash, impact):
        obj.update_tag()
    bpy.context.view_layer.update()
    bpy.context.scene.frame_set(hit)


def cel_materials():
    """Eevee-only three-band shading; never change effect materials or source assets."""
    materials = {}
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or not obj.get("review_actor"):
            continue
        for slot in obj.material_slots:
            original = slot.material
            if original is None:
                continue
            if original in materials:
                slot.material = materials[original]
                continue
            material = original.copy()
            material.name = "Cel • " + original.name
            nodes, links = material.node_tree.nodes, material.node_tree.links
            bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
            color_input = bsdf.inputs["Base Color"]
            source = color_input.links[0].from_socket if color_input.is_linked else None
            diffuse = nodes.new("ShaderNodeBsdfDiffuse")
            diffuse.name = "Cel Light Response"
            diffuse.inputs["Color"].default_value = (1, 1, 1, 1)
            convert = nodes.new("ShaderNodeShaderToRGB")
            convert.name = "Eevee Native Light Bands"
            links.new(diffuse.outputs[0], convert.inputs[0])
            ramp = nodes.new("ShaderNodeValToRGB")
            ramp.name = "Editable Cel Shadow Midtone Light"
            ramp.color_ramp.interpolation = "CONSTANT"
            for element in list(ramp.color_ramp.elements)[1:]:
                ramp.color_ramp.elements.remove(element)
            ramp.color_ramp.elements[0].position = 0
            ramp.color_ramp.elements[0].color = (0.22, 0.31, 0.49, 1)
            for position, color in ((0.42, (0.60, 0.68, 0.83, 1)), (0.78, (1, 1, 0.96, 1))):
                ramp.color_ramp.elements.new(position).color = color
            links.new(convert.outputs["Color"], ramp.inputs[0])
            mix = nodes.new("ShaderNodeMixRGB")
            mix.name, mix.blend_type = "Original Palette Times Cel Bands", "MULTIPLY"
            mix.inputs[0].default_value = 1
            if source is None:
                mix.inputs[1].default_value = color_input.default_value
            else:
                links.new(source, mix.inputs[1])
            links.new(ramp.outputs[0], mix.inputs[2])
            emission = nodes.new("ShaderNodeEmission")
            emission.name = "Flat Cel Surface"
            links.new(mix.outputs[0], emission.inputs["Color"])
            output = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
            links.new(emission.outputs[0], output.inputs["Surface"])
            for node, location in (
                (diffuse, (-600, 300)),
                (convert, (-400, 300)),
                (ramp, (-150, 300)),
                (mix, (100, 200)),
                (emission, (350, 200)),
                (output, (600, 200)),
            ):
                node.location = location
            nodes.remove(bsdf)
            materials[original] = material
            slot.material = material
    return len(materials)
