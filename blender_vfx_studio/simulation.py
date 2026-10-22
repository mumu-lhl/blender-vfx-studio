"""Solve a small native cloth sheet, then store motion as absolute shape keys."""

import hashlib
import json
import math

import bpy
from mathutils import Matrix

from . import core, particle
from .animation import curves
from .nodes import ACTIVE, PROGRESS, TIME_PROPS, drive, node
from .parameters import SIMULATION_PARAMETERS


def parts(root):
    root = core.resolve(root)
    if root is None or root["vfx_module"] != "simulation.cloth":
        raise ValueError("Select a cloth simulation effect")
    found = {}
    for kind in ("source", "output"):
        objects = [
            o
            for o in root.children_recursive
            if o.get("vfx_id") == root["vfx_id"]
            and o.get("vfx_sim_part") == kind
            and o.type == "MESH"
        ]
        if len(objects) != 1:
            raise ValueError("Cloth source/output is missing or ambiguous")
        found[kind] = objects[0]
    source = found["source"]
    if len(source.modifiers) != 1 or source.modifiers[0].type != "CLOTH":
        raise ValueError("Keep exactly one Cloth modifier on the simulation source")
    return source, found["output"], source.modifiers[0]


def _collection(root):
    found = [c for c in root.users_collection if c.get("vfx_id") == root["vfx_id"]]
    if len(found) != 1:
        raise ValueError("Simulation requires its original private collection")
    return found[0]


def create(context, quality="LOW"):
    divisions = {"LOW": 8, "MEDIUM": 12, "HIGH": 16}.get(quality)
    if divisions is None:
        raise ValueError("Unknown simulation quality")
    root, collection = core._controller(
        context, "Cloth Energy Sheet", "simulation.cloth", quality, SIMULATION_PARAMETERS, {}
    )
    root["vfx_sim_first"], root["vfx_sim_last"], root["vfx_sim_step"] = 1, 25, 1
    mesh = bpy.data.meshes.new("VFX • Cloth Rest Mesh")
    core._tag(mesh, root["vfx_id"])
    n = divisions
    mesh.from_pydata(
        [(2 * x / n - 1, 2 * y / n - 1, 1.5) for y in range(n + 1) for x in range(n + 1)],
        [],
        [
            (y * (n + 1) + x, y * (n + 1) + x + 1, (y + 1) * (n + 1) + x + 1, (y + 1) * (n + 1) + x)
            for y in range(n)
            for x in range(n)
        ],
    )
    source = bpy.data.objects.new("VFX • Cloth Source", mesh)
    collection.objects.link(source)
    source.parent = root
    core._tag(source, root["vfx_id"], "layer")
    source["vfx_sim_part"] = "source"
    source.hide_render = True
    source.hide_set(True)
    pin = source.vertex_groups.new(name="VFX Pin")
    pin.add(list(range(n * (n + 1), (n + 1) ** 2)), 1.0, "REPLACE")
    cloth = source.modifiers.new("VFX • Native Cloth Solver", "CLOTH")
    cloth.settings.vertex_group_mass = pin.name
    cloth.settings.quality = 3
    cloth.settings.mass = 0.1
    cloth.settings.effector_weights.collection = collection
    cloth.collision_settings.use_collision = False
    output_mesh = mesh.copy()
    core._tag(output_mesh, root["vfx_id"])
    output = bpy.data.objects.new("VFX • Cloth Output", output_mesh)
    core._tag(output, root["vfx_id"], "layer")
    output["vfx_sim_part"] = "output"
    collection.objects.link(output)
    output.parent = root
    output_mesh.materials.append(particle.material(root))
    _geometry(output, root)
    core.select(context, root)
    return root


def _settings(data):
    result = {}
    for prop in data.bl_rna.properties:
        if prop.is_readonly or prop.type in {"POINTER", "COLLECTION"}:
            continue
        value = getattr(data, prop.identifier)
        result[prop.identifier] = (
            list(value)
            if getattr(prop, "is_array", False)
            else sorted(value)
            if isinstance(value, set)
            else value
        )
    return result


def signature(context, root):
    source, _, cloth = parts(root)
    if (
        not 1 <= len(source.data.vertices) <= 625
        or len(source.data.polygons) > 1250
        or len(source.data.edges) > 2500
    ):
        raise ValueError("Cloth source exceeds the 625 vertex / 1250 face / 2500 edge budget")
    data = {
        "positions": [list(v.co) for v in source.data.vertices],
        "faces": [list(p.vertices) for p in source.data.polygons],
        "edges": [list(e.vertices) for e in source.data.edges],
        "groups": [g.name for g in source.vertex_groups],
        "weights": [[(g.group, g.weight) for g in v.groups] for v in source.data.vertices],
        "settings": _settings(cloth.settings),
        "collisions": _settings(cloth.collision_settings),
        "forces": _settings(cloth.settings.effector_weights),
        "gravity": list(context.scene.gravity),
        "use_gravity": context.scene.use_gravity,
        "fps": context.scene.render.fps,
        "fps_base": context.scene.render.fps_base,
        "source_transform": [list(row) for row in source.matrix_basis],
        "source_animation": bool(
            source.animation_data or source.data.animation_data or source.constraints
        ),
        "private_forces": cloth.settings.effector_weights.collection == _collection(root),
        "range": [root["vfx_sim_first"], root["vfx_sim_last"], root["vfx_sim_step"]],
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()


def state(context, root):
    _, output, _ = parts(root)
    if output.data.shape_keys is None:
        return "UNBAKED"
    return "BAKED" if root.get("vfx_sim_signature") == signature(context, root) else "STALE"


def _private_output(root, output):
    if output.data.get("vfx_id") != root["vfx_id"] or output.data.users != 1:
        raise ValueError("Make the output mesh private before replacing the bake")
    key = output.data.shape_keys
    if key and (
        key.get("vfx_id") != root["vfx_id"]
        or key.use_fake_user
        or key.use_extra_user
        or any(user != output.data for user in bpy.data.user_map(subset={key}).get(key, set()))
    ):
        raise ValueError(
            "Baked shape keys are shared or user-owned; preserve them before replacing"
        )


def bake(context, root):
    if context.mode != "OBJECT":
        raise ValueError("Leave Edit/Pose Mode before baking")
    root = core.resolve(root)
    source, output, cloth = parts(root)
    _private_output(root, output)
    first, last, step = (root[k] for k in ("vfx_sim_first", "vfx_sim_last", "vfx_sim_step"))
    if any(type(v) is not int for v in (first, last, step)) or not (
        1 <= first < last <= 100000
        and step >= 1
        and (last - first) % step == 0
        and last - first <= 240
        and (last - first) // step + 1 <= 121
    ):
        raise ValueError(
            "Use a range spanning at most 240 frames, an exact step and at most 121 stored poses"
        )
    if len(source.data.vertices) > 625 or not source.data.vertices:
        raise ValueError("Cloth source must contain 1–625 vertices")
    if (
        source.animation_data
        or source.data.animation_data
        or source.data.shape_keys
        or source.constraints
        or source.matrix_basis != Matrix.Identity(4)
    ):
        raise ValueError(
            "Use a static source mesh with applied transforms; animate the baked controller instead"
        )
    if any(c.data_path in {"gravity", "use_gravity"} for c in curves(context.scene)):
        raise ValueError("Animated scene gravity is not supported by this bake")
    collection = _collection(root)
    if (
        cloth.settings.effector_weights.collection != collection
        or any(o.field and o.field.type != "NONE" for o in collection.all_objects)
        or cloth.collision_settings.use_collision
    ):
        raise ValueError(
            "Use the private force collection without force fields or external collisions"
        )
    cache = cloth.point_cache
    if cache.use_disk_cache or cache.use_external:
        raise ValueError("Use the source's internal point cache, not external/disk cache")
    if not 1 <= cloth.settings.quality <= 12:
        raise ValueError("Use 1–12 cloth quality steps for the bounded CPU bake")
    if cloth.collision_settings.use_self_collision:
        raise ValueError("Self collisions are not supported by this bounded bake")
    if source.name not in context.view_layer.objects:
        raise ValueError("Include the simulation source in this view layer before baking")
    digest = signature(context, root)
    scene = context.scene
    frame, subframe = scene.frame_current, scene.frame_subframe
    parent, inverse, basis = (
        source.parent,
        source.matrix_parent_inverse.copy(),
        source.matrix_basis.copy(),
    )
    hidden = source.hide_get()
    poses = []
    try:
        source.hide_set(False)
        source.parent = None
        source.matrix_world = Matrix.Identity(4)  # Physics runs in the effect's local space.
        cache.frame_start, cache.frame_end = first, last
        with context.temp_override(object=source, active_object=source, point_cache=cache):
            bpy.ops.ptcache.free_bake()
        for frame_index in range(first, last + 1):
            scene.frame_set(frame_index)
            evaluated = source.evaluated_get(context.evaluated_depsgraph_get())
            if len(evaluated.data.vertices) != len(source.data.vertices):
                raise ValueError("Simulation topology changed during bake")
            if (frame_index - first) % step == 0:
                coords = [
                    component for vertex in evaluated.data.vertices for component in vertex.co
                ]
                if not all(math.isfinite(v) and abs(v) <= 1e8 for v in coords):
                    raise ValueError(
                        "Simulation produced invalid positions; lower forces or adjust solver settings"
                    )
                poses.append(coords)
    finally:
        source.parent = parent
        source.matrix_parent_inverse, source.matrix_basis = inverse, basis
        source.hide_set(hidden)
        scene.frame_set(frame, subframe=subframe)
    # Build replacement data away from the visible output; failed sampling keeps its old bake.
    mesh = source.data.copy()
    mesh.use_fake_user = False
    mesh.materials.clear()
    for polygon in mesh.polygons:
        polygon.material_index = 0
    core._tag(mesh, root["vfx_id"])
    staging = bpy.data.objects.new("VFX • Bake Staging", mesh)
    try:
        for i, coords in enumerate(poses):
            key = staging.shape_key_add(name=f"Sample {first + i * step}")
            key.interpolation = "KEY_LINEAR"
            key.data.foreach_set("co", coords)
        keys = mesh.shape_keys
        keys.use_relative = False
        core._tag(keys, root["vfx_id"])
        drive(keys, "eval_time", root, f"({PROGRESS})*{(len(poses) - 1) * 10}", TIME_PROPS)
        for material in output.data.materials:
            mesh.materials.append(material)
        old = output.data
        output.data = mesh
        bpy.data.meshes.remove(old)
        root["vfx_sim_signature"] = digest
        root["vfx_sim_samples"] = len(poses)
    finally:
        bpy.data.objects.remove(staging, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    core.select(context, root)


def clear(root):
    root = core.resolve(root)
    _, output, _ = parts(root)
    _private_output(root, output)
    output.shape_key_clear()
    for key in ("vfx_sim_signature", "vfx_sim_samples"):
        if key in root:
            del root[key]


def after_duplicate(root):
    source, _, cloth = parts(root)
    cloth.settings.effector_weights.collection = _collection(root)
    source.hide_set(True)


def _geometry(obj, root):
    tree = bpy.data.node_groups.new("VFX • Baked Cloth Lifetime", "GeometryNodeTree")
    core._tag(tree, root["vfx_id"])
    for direction in ("INPUT", "OUTPUT"):
        tree.interface.new_socket(
            name="Geometry", in_out=direction, socket_type="NodeSocketGeometry"
        )
    inp = node(tree, "NodeGroupInput", "Baked Shape", 0, 0)
    out = node(tree, "NodeGroupOutput", "Output", 600, 0)
    hide = node(tree, "GeometryNodeDeleteGeometry", "Outside Lifetime", 400, 0, domain="POINT")
    active = node(tree, "ShaderNodeValue", "Active", 0, -200)
    drive(active.outputs[0], "default_value", root, ACTIVE, TIME_PROPS)
    inactive = node(tree, "ShaderNodeMath", "Inactive", 200, -200, operation="LESS_THAN")
    inactive.inputs[1].default_value = 0.5
    tree.links.new(active.outputs[0], inactive.inputs[0])
    tree.links.new(inactive.outputs[0], hide.inputs["Selection"])
    tree.links.new(inp.outputs["Geometry"], hide.inputs["Geometry"])
    tree.links.new(hide.outputs[0], out.inputs["Geometry"])
    obj.modifiers.new("VFX • Baked Playback", "NODES").node_group = tree
