"""Author one combat shot using existing native clips, effects and cel materials."""

import math

import bpy
from mathutils import Vector


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


def plant_preparation(rig):
    """Load the hips while native IK keeps the original soles on the ground."""
    from blender_vfx_studio.animation import curves

    scene = bpy.context.scene
    samples = {}
    for frame in range(1, 48):
        scene.frame_set(frame)
        evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
        samples[frame] = {}
        for side in ("l", "r"):
            hip = rig.matrix_world @ evaluated.pose.bones["upperleg." + side].head
            knee = rig.matrix_world @ evaluated.pose.bones["lowerleg." + side].head
            ankle = rig.matrix_world @ evaluated.pose.bones["foot." + side].head
            axis = (ankle - hip).normalized()
            bend = knee - hip - axis * (knee - hip).dot(axis)
            direction = bend.normalized() if bend.length > 0.005 else Vector((1, 0, 0))
            samples[frame][side] = (
                rig.matrix_world @ evaluated.pose.bones["foot." + side].matrix,
                knee.copy(),
                knee + direction * 0.75,
            )
    collection = bpy.data.collections.new("Combat • Pose Controls")
    scene.collection.children.link(collection)
    controls, constraints = [], []

    def control(name):
        obj = bpy.data.objects.new(name, None)
        collection.objects.link(obj)
        obj.empty_display_size = 0.08
        controls.append(obj)
        return obj

    for side in ("l", "r"):
        goal = control("Foot plant • " + side)
        pole = control("Knee direction • " + side)
        goal.rotation_mode = "QUATERNION"
        previous = None
        for frame in range(1, 48):
            matrix, _, point = samples[frame][side]
            goal.location = matrix.translation
            rotation = matrix.to_quaternion()
            if previous is not None:
                rotation.make_compatible(previous)
            previous = rotation.copy()
            goal.rotation_quaternion = rotation
            pole.location = point
            goal.keyframe_insert(data_path="location", frame=frame)
            goal.keyframe_insert(data_path="rotation_quaternion", frame=frame)
            pole.keyframe_insert(data_path="location", frame=frame)
        leg = rig.pose.bones["lowerleg." + side]
        rig.pose.bones["upperleg." + side].ik_stretch = leg.ik_stretch = 0
        ik = leg.constraints.new("IK")
        ik.name = "Native planted leg"
        ik.target, ik.pole_target = goal, pole
        ik.chain_count, ik.use_stretch = 2, False
        constraints.append(ik)
        rotation = rig.pose.bones["foot." + side].constraints.new("COPY_ROTATION")
        rotation.name, rotation.target = "Preserve planted sole", goal
        rotation.owner_space = rotation.target_space = "WORLD"
        constraints.append(rotation)
        # glTF preserves the limb axes. Choose the matching native pole roll
        # at zero load, rather than assuming both legs use the same roll.
        trials = []
        for angle in (0, math.pi / 2, -math.pi / 2, math.pi):
            ik.pole_angle = angle
            scene.frame_set(1)
            bpy.context.view_layer.update()
            evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
            knee = rig.matrix_world @ evaluated.pose.bones["lowerleg." + side].head
            trials.append(((knee - samples[1][side][1]).length, angle))
        ik.pole_angle = min(trials)[1]
    shift = control("Body load • edit location keys")
    offset = rig.pose.bones["hips"].constraints.new("COPY_LOCATION")
    offset.name, offset.target = "Load without moving the feet", shift
    offset.owner_space = offset.target_space = "WORLD"
    offset.use_offset = True
    constraints.append(offset)
    for frame, location in (
        (1, (0, 0, 0)),
        (12, (-0.015, 0, -0.01)),
        (28, (-0.06, 0, -0.06)),
        (39, (-0.08, 0, -0.07)),
        (43, (-0.03, 0, -0.025)),
        (47, (0, 0, 0)),
        (96, (0, 0, 0)),
    ):
        shift.location = location
        shift.keyframe_insert(data_path="location", frame=frame)
    for constraint in constraints:
        for frame, value in ((1, 1), (46, 1), (47, 0), (96, 0)):
            constraint.influence = value
            constraint.keyframe_insert(data_path="influence", frame=frame)
    for obj in controls:
        for curve in curves(obj):
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"
    for curve in curves(rig):
        if ".constraints[" in curve.data_path:
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"
    scene.frame_set(1)


def _node_keys(socket, values):
    for frame, value in values:
        socket.default_value = value
        socket.keyframe_insert(data_path="default_value", frame=frame)


def direct_effects(fixture):
    """Let gathered energy reach the cut, then separate flash and aftermath."""
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
        "Core Flash": (0, 4),
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
            # Keep the contact focus through the pose hold, then compress it
            # as pressure opens. Use layer progress so composition retiming
            # carries the envelope with it, without scene-frame keyframes.
            tree = member.children[0].modifiers[0].node_group
            hold = tree.nodes.new("ShaderNodeMapRange")
            hold.name = hold.label = "Contact Hold Then Compression"
            hold.location = (200, -650)
            hold.clamp = True
            hold.inputs["From Min"].default_value = 0.5
            hold.inputs["From Max"].default_value = 5 / 6
            tree.links.new(tree.nodes["Progress"].outputs[0], hold.inputs["Value"])
            tree.links.new(hold.outputs[0], tree.nodes["Editable Collapse"].inputs[0])
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
