"""Instance lifecycle and ownership. Builders create private, native assets."""

import math
import uuid

import bpy

from . import nodes
from .parameters import PARAMETERS
from .registry import MODULES, PRESETS

SCHEMA_VERSION = 1


def resolve(obj):
    """Resolve an active layer/controller, refusing manually copied IDs."""
    while obj is not None:
        if obj.get("vfx_role") == "controller":
            uid = obj.get("vfx_id")
            roots = [
                o
                for o in bpy.data.objects
                if o.get("vfx_id") == uid and o.get("vfx_role") == "controller"
            ]
            if len(roots) != 1:
                raise ValueError("Ambiguous VFX ID: use VFX Duplicate instead of Shift-D")
            if obj.get("vfx_schema") != SCHEMA_VERSION:
                raise ValueError("Unsupported VFX schema; update the extension before editing")
            return obj
        obj = obj.parent
    return None


def _tag(data, uid, role=None):
    data["vfx_id"] = uid
    if role:
        data["vfx_role"] = role


def create(context, preset="SHOCKWAVE", quality="MEDIUM"):
    settings = PRESETS[preset]
    segments = {"LOW": 32, "MEDIUM": 64, "HIGH": 128}[quality]
    uid = str(uuid.uuid4())
    collection = bpy.data.collections.new("VFX • " + settings["label"])
    _tag(collection, uid)
    context.scene.collection.children.link(collection)
    root = bpy.data.objects.new(settings["label"] + " • Controller", None)
    collection.objects.link(root)
    _tag(root, uid, "controller")
    root["vfx_schema"] = SCHEMA_VERSION
    root["vfx_module"] = "mesh.ring"
    root["vfx_asset_version"] = MODULES["mesh.ring"].asset_version
    root["vfx_quality"] = quality
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.5
    root.location = context.scene.cursor.location
    for key, (default, minimum, maximum, description) in PARAMETERS.items():
        value = settings.get(key, default)
        if key.startswith("color_"):
            value = settings["color"][int(key[-1])]
        if key == "start":
            value = float(context.scene.frame_current)
        root[key] = value
        ui = {"description": description}
        if minimum is not None:
            ui.update(min=minimum, max=maximum, soft_min=minimum, soft_max=min(maximum, 100))
        root.id_properties_ui(key).update(**ui)
    vertices = []
    faces = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        for r in (1.0, 0.8):
            vertices.append((r * math.cos(angle), r * math.sin(angle), 0))
    for i in range(segments):
        a, b = i * 2, ((i + 1) % segments) * 2
        faces.append((a, b, b + 1, a + 1))
    mesh = bpy.data.meshes.new("VFX • Ring Base")
    _tag(mesh, uid)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mask = mesh.attributes.new("vfx_inner", "FLOAT", "POINT")
    for i, item in enumerate(mask.data):
        item.value = i % 2
    uv = mesh.uv_layers.new(name="VFX UV")
    for polygon in mesh.polygons:
        u = polygon.index / segments
        for index, coord in zip(
            polygon.loop_indices, [(u, 0), (u + 1 / segments, 0), (u + 1 / segments, 1), (u, 1)]
        ):
            uv.data[index].uv = coord
    layer = bpy.data.objects.new("VFX • Ring Layer", mesh)
    collection.objects.link(layer)
    layer.parent = root
    _tag(layer, uid, "layer")
    mesh.materials.append(nodes.shader(root, uid))
    nodes.geometry(layer, root, uid)
    select(context, root)
    return root


def select(context, root):
    for obj in context.selected_objects:
        obj.select_set(False)
    root.select_set(True)
    context.view_layer.objects.active = root
    root.update_tag()
    context.view_layer.update()


def _remap_drivers(data, mapping):
    animation = data.animation_data
    if animation is None:
        return
    # Explicitly copy Actions: bpy ID.copy otherwise shares user keyframes.
    if animation.action:
        animation.action = animation.action.copy()
    for track in animation.nla_tracks:
        for strip in track.strips:
            if strip.action:
                strip.action = strip.action.copy()
    for curve in animation.drivers:
        for var in curve.driver.variables:
            for target in var.targets:
                if target.id in mapping:
                    target.id = mapping[target.id]


def duplicate(context, root):
    root = resolve(root)
    if root is None:
        raise ValueError("Select a VFX controller or layer")
    uid = str(uuid.uuid4())
    collection = bpy.data.collections.new("VFX • Copy")
    _tag(collection, uid)
    context.scene.collection.children.link(collection)
    sources = [root] + [
        o
        for o in root.children_recursive
        if o.get("vfx_id") == root["vfx_id"] and o.get("vfx_role") == "layer"
    ]
    mapping = {}
    private = []
    for source in sources:
        clone = source.copy()
        _tag(clone, uid)
        collection.objects.link(clone)
        mapping[source] = clone
        private.append(clone)
        if source.data:
            clone.data = source.data.copy()
            _tag(clone.data, uid)
            private.append(clone.data)
            for slot in clone.material_slots:
                if slot.material:
                    slot.material = slot.material.copy()
                    _tag(slot.material, uid)
                    private.append(slot.material)
                    if slot.material.node_tree:
                        private.append(slot.material.node_tree)
            for modifier in clone.modifiers:
                if modifier.type == "NODES" and modifier.node_group:
                    modifier.node_group = modifier.node_group.copy()
                    _tag(modifier.node_group, uid)
                    private.append(modifier.node_group)
    for source, clone in mapping.items():
        clone.parent = mapping.get(source.parent, source.parent)
    for data in private:
        _remap_drivers(data, mapping)
    select(context, mapping[root])
    return mapping[root]


def delete(root):
    root = resolve(root)
    if root is None:
        raise ValueError("Select a VFX controller or layer")
    uid = root["vfx_id"]
    owned = [root] + [
        o
        for o in root.children_recursive
        if o.get("vfx_id") == uid and o.get("vfx_role") == "layer"
    ]
    # Shared generated assets still depend on this controller. Refuse destructive
    # unlinking rather than leave another object with broken native drivers.
    meshes = {o.data for o in owned if o.type == "MESH"}
    materials = {m for mesh in meshes for m in mesh.materials if m}
    groups = {
        m.node_group for o in owned for m in o.modifiers if m.type == "NODES" and m.node_group
    }
    for mesh in meshes:
        if mesh.get("vfx_id") == uid and mesh.users > sum(o.data == mesh for o in owned):
            raise ValueError("VFX mesh is shared; unlink external users before deleting")
    for material in materials:
        users = sum(sum(m == material for m in mesh.materials) for mesh in meshes)
        if material.get("vfx_id") == uid and material.users > users:
            raise ValueError("VFX material is shared; unlink external users before deleting")
    for group in groups:
        users = sum(
            sum(m.type == "NODES" and m.node_group == group for m in o.modifiers) for o in owned
        )
        if group.get("vfx_id") == uid and group.users > users:
            raise ValueError("VFX node group is shared; unlink external users before deleting")
    resources = []
    for obj in owned:
        # Retain foreign children and their world-space transforms.
        for child in list(obj.children):
            if child not in owned:
                matrix = child.matrix_world.copy()
                child.parent = None
                child.matrix_world = matrix
        if obj.type == "MESH":
            resources.append((bpy.data.meshes, obj.data))
            resources.extend((bpy.data.materials, m) for m in obj.data.materials if m)
        resources.extend(
            (bpy.data.node_groups, m.node_group)
            for m in obj.modifiers
            if m.type == "NODES" and m.node_group
        )
    unique = {data.as_pointer(): (store, data) for store, data in resources}
    for obj in reversed(owned):
        bpy.data.objects.remove(obj, do_unlink=True)
    # Meshes release material users first. Foreign data is retained.
    for store, data in unique.values():
        if data.get("vfx_id") == uid and data.users == 0:
            store.remove(data)
    for collection in list(bpy.data.collections):
        if collection.get("vfx_id") == uid and not collection.objects and not collection.children:
            bpy.data.collections.remove(collection)


def preset_snapshot(root):
    from . import presets

    root = resolve(root)
    if root is None:
        raise ValueError("Select a VFX controller or layer")
    return presets.validate(
        {
            "format_version": presets.FORMAT_VERSION,
            "module": root["vfx_module"],
            "asset_version": root["vfx_asset_version"],
            "name": root.name[:80],
            "quality": root["vfx_quality"],
            "parameters": {key: root[key] for key in presets.PRESET_PARAMETERS},
        }
    )


def create_from_preset(context, data):
    from . import presets

    data = presets.validate(data)  # Validate completely before mutating Blender data.
    root = create(context, quality=data["quality"])
    root.name = data["name"]
    for key, value in data["parameters"].items():
        root[key] = value
    select(context, root)
    return root
