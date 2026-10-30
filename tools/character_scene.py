"""Build a native rigged-character fixture; no retargeting or runtime callbacks."""

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets/character-review/kaykit"
FRAMES = 96


def actor(model, label, location, rotation, *, sword=False):
    manifest = json.loads((ASSETS / "provenance.json").read_text())
    path = ASSETS / f"{model}.glb"
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["files"][path.name]["sha256"]:
        raise ValueError(f"Character source changed: {path.name}")
    before_objects, before_actions = set(bpy.data.objects), set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = set(bpy.data.objects) - before_objects
    actions = {}
    for action in set(bpy.data.actions) - before_actions:
        name = action.name
        if name[-4:-3] == "." and name[-3:].isdigit():
            name = name[:-4]
        actions[name] = action
    rig = next(o for o in imported if o.type == "ARMATURE")
    rig.animation_data_clear()
    rig.name = label
    kept = {"2H_Sword", "Knight_Helmet", "Knight_Cape"} if sword else {"Knife", "Rogue_Cape"}
    removed = []
    for obj in imported:
        if obj.type == "MESH" and obj.parent_type == "BONE":
            base = obj.name.removesuffix(".001")
            if base not in kept:
                removed.append(obj)
    retained = imported - set(removed)
    for obj in removed:
        bpy.data.objects.remove(obj, do_unlink=True)
    for obj in retained:
        if obj != rig and obj.parent is None:
            obj.hide_render = obj.hide_viewport = True
    idle = actions["2H_Melee_Idle" if sword else "Idle"]
    clip(rig, idle, 1, 97, loop=True)
    bpy.context.scene.frame_set(1)
    graph = bpy.context.evaluated_depsgraph_get()
    body = [o for o in rig.children if o.type == "MESH" and o.parent_type != "BONE"]
    points = [o.matrix_world @ v.co for o in body for v in o.evaluated_get(graph).data.vertices]
    low, high = min(p.z for p in points), max(p.z for p in points)
    scale = 1.8 / (high - low)
    rig.scale = (scale,) * 3
    rig.location = (*location, -low * scale)
    rig.rotation_mode = "QUATERNION"
    rig.rotation_quaternion = Quaternion((0, 0, 1), rotation) @ rig.rotation_quaternion
    for obj in retained:
        obj["review_actor"] = label
    weapon = next(
        (o for o in retained if o.name.removesuffix(".001") == ("2H_Sword" if sword else "Knife")),
        None,
    )
    return {"rig": rig, "actions": actions, "weapon": weapon, "model": model}


def clip(rig, action, start, end, *, blend=0, loop=False):
    track = rig.animation_data_create().nla_tracks.new()
    track.name = action.name
    strip = track.strips.new(action.name, start, action)
    strip.action_slot = action.slots[0]
    strip.action_frame_start, strip.action_frame_end = action.frame_range
    duration = strip.action_frame_end - strip.action_frame_start
    strip.scale = 1 if loop else (end - start) / duration
    strip.repeat = (end - start) / duration if loop else 1
    strip.blend_in = strip.blend_out = blend
    strip.extrapolation = "NOTHING"
    return strip


def material(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = 0.9
    return mat


def setup_base(*, light=True, far=False, view="front", engine="BLENDER_EEVEE"):
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = 1, FRAMES
    caster = actor("Knight", "Caster • Knight", (-0.8, 0), math.pi / 2, sword=True)
    defender = actor("Rogue", "Defender • Rogue", (0.8, 0.08), -math.pi / 2)
    preparation = clip(caster["rig"], caster["actions"]["2H_Melee_Attack_Chop"], 1, 41)
    preparation.action_frame_end = (
        preparation.action_frame_start
        + (preparation.action_frame_end - preparation.action_frame_start) * 0.18
    )
    preparation.scale = 40 / (preparation.action_frame_end - preparation.action_frame_start)
    preparation.blend_in, preparation.blend_out = 12, 4
    preparation.name = "Charge preparation • native chop opening"
    clip(caster["rig"], caster["actions"]["2H_Melee_Attack_Slice"], 37, 69, blend=4)
    # The actual blade trace determines contact; the reaction begins there.
    weapon = caster["weapon"]
    tip = max(weapon.data.vertices, key=lambda v: v.co.length_squared).co.copy()
    trace = []
    for frame in range(41, 57):
        scene.frame_set(frame)
        evaluated = weapon.evaluated_get(bpy.context.evaluated_depsgraph_get())
        a, b = evaluated.matrix_world.translation, evaluated.matrix_world @ tip
        hits = []
        for body in defender["rig"].children:
            if body.type != "MESH" or body.parent_type == "BONE":
                continue
            target_mesh = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
            inverse = target_mesh.matrix_world.inverted()
            local_a, local_b = inverse @ a, inverse @ b
            delta = local_b - local_a
            hit, position, normal, _ = target_mesh.ray_cast(
                local_a, delta.normalized(), distance=delta.length
            )
            if hit:
                point = target_mesh.matrix_world @ position
                world_normal = (
                    target_mesh.matrix_world.to_3x3().inverted().transposed() @ normal
                ).normalized()
                hits.append(
                    {
                        "position": list(point),
                        "normal": list(world_normal),
                        "mesh": body.name,
                        "distance": (point - a).length,
                    }
                )
        trace.append(
            {
                "frame": frame,
                "hilt": list(a),
                "tip": list(b),
                "hits": sorted(hits, key=lambda h: h["distance"]),
            }
        )
    # A sword is a segment. Use its nearest point to the target upper torso.
    target = Vector((0.8, 0.08, 1.05))

    def distance(sample):
        a, b = Vector(sample["hilt"]), Vector(sample["tip"])
        t = min(max((target - a).dot(b - a) / (b - a).length_squared, 0), 1)
        return (a + t * (b - a) - target).length

    intersections = [sample for sample in trace if sample["hits"]]
    contact = intersections[0] if intersections else min(trace, key=distance)
    contact["verified_intersection"] = bool(intersections)
    clip(
        defender["rig"],
        defender["actions"]["Hit_A"],
        contact["frame"],
        contact["frame"] + 22,
        blend=1,
    )
    # Discard unused imported clips, keeping the native NLA actions that play.
    for action in list(bpy.data.actions):
        action.use_fake_user = False
        if action.users == 0:
            bpy.data.actions.remove(action)
    for image in bpy.data.images:
        if image.source == "FILE" and not image.packed_file:
            image.pack()
    setup_stage(light=light, far=far, view=view, engine=engine)
    scene.frame_set(contact["frame"])
    return {
        "caster": caster,
        "defender": defender,
        "contact": contact,
        "target": target,
        "trace": trace,
        "tip_local": tip,
    }


def add_effects(fixture):
    """Fit editable starter effects to this sword stroke with native keys."""
    from blender_vfx_studio import binding, composition
    from blender_vfx_studio.animation import curves
    from tools.build_examples import create_effect

    scene = bpy.context.scene
    contact = fixture["contact"]
    if not contact["verified_intersection"]:
        raise RuntimeError("The blade misses the defender; fix the scene before reviewing VFX")
    before = set(scene.objects)
    weapon, tip = fixture["caster"]["weapon"], fixture["tip_local"]
    midpoint = bpy.data.objects.new("Charge socket • blade midpoint", None)
    scene.collection.objects.link(midpoint)
    midpoint.parent = weapon
    for frame, reach in ((1, 0.2), (37, 0.2), (43, 0.5)):
        midpoint.location = tip * reach
        midpoint.keyframe_insert(data_path="location", frame=frame)
    for curve in curves(midpoint):
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    socket = bpy.data.objects.new("Charge socket • world up", None)
    scene.collection.objects.link(socket)
    follow = socket.constraints.new("COPY_LOCATION")
    follow.target = midpoint
    scene.frame_set(1)
    charge = create_effect("energy-charge")
    # Place this asset's native discharge peak at measured blade contact.
    # A fixed duration releases into the backswing, before the blade turns.
    nucleus = next(m for m in composition.members(charge) if m["vfx_module"] == "shader.shield")
    release = nucleus.children[0].modifiers[0].node_group.nodes["Release Pinch Begins"]
    peak = release.inputs["From Max"].default_value
    charge["duration"] = (contact["frame"] - charge["start"]) * charge["speed"] / peak
    fixture["charge_release"] = {
        "frame": contact["frame"],
        "phase": peak,
        "duration": charge["duration"],
    }
    bpy.context.view_layer.update()
    charge.location = socket.evaluated_get(
        bpy.context.evaluated_depsgraph_get()
    ).matrix_world.translation
    binding.bind(bpy.context, charge, socket)

    # The stored focus turns into the blade before discharge, rather than
    # collapsing vertically while an unrelated slash appears across it.
    socket.rotation_mode = "QUATERNION"
    previous = Quaternion()
    for frame in (1, *range(41, 52)):
        scene.frame_set(frame)
        matrix = weapon.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world
        direction = (matrix @ tip - matrix.translation).normalized()
        aim = Vector((0, 0, 1)).rotation_difference(direction)
        rotation = Quaternion().slerp(aim, min(max((frame - 41) / 6, 0), 1))
        rotation.make_compatible(previous)
        previous = rotation.copy()
        socket.rotation_quaternion = rotation
        socket.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    for curve in curves(socket):
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"

    hit_frame = contact["frame"]
    slash = create_effect("arc-slash")
    slash.name = "Combat • Arc Slash"
    slash["start"], slash["duration"] = float(hit_frame - 2), 10.0
    # The native effect's radius matches the imported sword's measured world length.
    sample = fixture["trace"][0]
    slash["radius"] = (Vector(sample["tip"]) - Vector(sample["hilt"])).length
    directions = {
        item["frame"]: Vector(item["tip"]) - Vector(item["hilt"]) for item in fixture["trace"]
    }
    # This shot is a close sword cut, not the asset's broad standalone sweep.
    # Measure the arc traversed into contact; leave some trailing coverage.
    slash["arc"] = math.degrees(directions[hit_frame - 2].angle(directions[hit_frame])) * 0.85
    slash["width"] = slash["radius"] * 0.14
    slash["expansion"] = 0.0
    slash["bank"], slash["contour"] = 0.10, 0.35
    slash["afterimage"], slash["wake_spread"] = 0.28, 0.3
    for index, color in enumerate((0.025, 0.32, 0.7)):
        slash[f"color_{index}"] = color
    normal = directions[hit_frame - 2].cross(directions[hit_frame + 2]).normalized()
    if normal.length < 0.9:
        raise RuntimeError("Cannot determine the sword's swing plane")
    plane = Vector((0, 0, 1)).rotation_difference(normal)
    slash.rotation_mode = "QUATERNION"
    previous = None
    for frame in range(hit_frame - 2, hit_frame + 9):
        scene.frame_set(frame)
        matrix = weapon.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world
        blade = matrix @ tip - matrix.translation
        direction = blade.normalized()
        # The stroke is not planar: projecting every blade into the fixed
        # reference plane lifts the slash off the sword during contact.
        # Keep the nearest plane that actually contains this frame's blade.
        frame_normal = normal - direction * normal.dot(direction)
        if frame_normal.length < 1e-6:
            raise RuntimeError("Cannot fit the slash plane to this blade direction")
        slash_plane = Vector((0, 0, 1)).rotation_difference(frame_normal.normalized())
        radial = slash_plane.inverted() @ blade
        progress = min(max((frame - slash["start"]) / slash["duration"], 0), 1)
        front = min(progress / slash["attack"], 1)
        clock = progress + slash["motion_ease"] * (1 - (1 - progress) ** 3 - progress)
        # Cancel only the main blade's native rotation. Preserve Spin so its
        # sign and each wake's independent local clock still produce trailing layers.
        angle = (
            math.atan2(radial.y, radial.x)
            - (front - 0.5) * math.radians(slash["arc"])
            - math.radians(slash["spin"]) * clock
        )
        rotation = slash_plane @ Quaternion((0, 0, 1), angle)
        if previous is not None:
            rotation.make_compatible(previous)
        previous = rotation.copy()
        slash.location, slash.rotation_quaternion = matrix.translation, rotation
        slash.keyframe_insert(data_path="location", frame=frame)
        slash.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    for curve in curves(slash):
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    impact = create_effect("impact-burst")
    impact.name = "Combat • Impact Burst"
    impact["start"], impact["duration"] = float(hit_frame), 24.0
    impact.location = contact["hits"][0]["position"]
    impact.rotation_mode, impact.rotation_quaternion = "QUATERNION", plane
    # Pressure opens over the struck surface. The wave keeps the measured
    # swing plane; rotating the whole burst also rotates its long pressure arcs.
    surface = Vector((0, 0, 1)).rotation_difference(Vector(contact["hits"][0]["normal"]))
    body = next(c for c in impact.children if "Main Shards" in c.name)
    body.children[0].modifiers[0].node_group.nodes["Pressure Surface Alignment"].inputs[
        "Rotation"
    ].default_value = (plane.inverted() @ surface).to_euler()
    for effect in (charge, slash, impact):
        effect.update_tag()
    collection = bpy.data.collections.new("Combat VFX • toggle for comparison")
    scene.collection.children.link(collection)
    for obj in set(scene.objects) - before - {midpoint, socket}:
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
    for label, frame in (
        ("Charge", 1),
        ("Wind-up", 37),
        ("Discharge peak", hit_frame),
        ("Verified blade contact", hit_frame),
        ("Aftermath", hit_frame + 24),
        ("Recovery", 80),
    ):
        scene.timeline_markers.new(label, frame=frame)
    scene.frame_set(hit_frame)
    fixture.update(effects=(charge, slash, impact), effects_collection=collection)
    return fixture


def setup_stage(
    *, light=True, far=False, view="front", engine="BLENDER_EEVEE", focus=(0, 0, 0.95), lens=50
):
    """Shared neutral stage for actual character/effect comparisons."""
    scene = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=200)
    floor = bpy.context.object
    floor.name = "Stage • Ground"
    floor.data.materials.append(
        material("Stage floor", (0.62, 0.66, 0.72) if light else (0.035, 0.045, 0.06))
    )
    scene.world = bpy.data.worlds.new("Character review world")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        (0.62, 0.66, 0.72, 1) if light else (0.018, 0.023, 0.035, 1)
    )
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4
    for name, location, energy, size in (("Key", (0, -4, 6), 900, 5), ("Rim", (-2, 3, 4), 600, 4)):
        lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
        scene.collection.objects.link(lamp)
        lamp.location = location
        lamp.rotation_euler = (
            (Vector((0, 0, 1)) - lamp.location).to_track_quat("-Z", "Y").to_euler()
        )
        lamp.data.energy, lamp.data.shape, lamp.data.size = energy, "DISK", size
    focus = Vector(focus)
    camera = bpy.data.objects.new(
        "Character combat camera", bpy.data.cameras.new("Character combat camera")
    )
    scene.collection.objects.link(camera)
    camera.location = focus + Vector((0, 7, 3.2) if view == "front" else (0, -7, 3.2))
    camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type, camera.data.lens = "PERSP", lens
    if far:
        camera.location = focus + (camera.location - focus) * 2
    camera.data.ortho_scale = 12.8 if far else 6.4
    scene.camera = camera
    scene.render.engine = engine
    scene.eevee.taa_render_samples = 16
    scene.cycles.device, scene.cycles.samples = "CPU", 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform, scene.view_settings.look = "AgX", "None"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
