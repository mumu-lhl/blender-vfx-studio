"""Instance lifecycle and ownership. Builders create private, native assets."""

import math
import uuid

import bpy

from . import nodes
from .parameters import FLIPBOOK_PARAMETERS, PARAMETERS, preset_parameters_for
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
            module = obj.get("vfx_module")
            if (
                not isinstance(module, str)
                or module not in MODULES
                or obj.get("vfx_asset_version") != MODULES[module].asset_version
            ):
                raise ValueError(
                    "Unsupported VFX module or asset version; update the extension before editing"
                )
            return obj
        obj = obj.parent
    return None


def _tag(data, uid, role=None):
    data["vfx_id"] = uid
    if role:
        data["vfx_role"] = role


def _controller(context, label, module, quality, parameters, settings):
    uid = str(uuid.uuid4())
    collection = bpy.data.collections.new("VFX • " + label)
    _tag(collection, uid)
    context.scene.collection.children.link(collection)
    root = bpy.data.objects.new(label + " • Controller", None)
    collection.objects.link(root)
    _tag(root, uid, "controller")
    root["vfx_schema"] = SCHEMA_VERSION
    root["vfx_module"] = module
    root["vfx_asset_version"] = MODULES[module].asset_version
    root["vfx_quality"] = quality
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.5
    root.location = context.scene.cursor.location
    for key, (default, minimum, maximum, description) in parameters.items():
        value = settings.get(key, default)
        if key.startswith("color_") and "color" in settings:
            value = settings["color"][int(key[-1])]
        if key == "start":
            value = float(context.scene.frame_current)
        root[key] = value
        ui = {"description": description}
        if minimum is not None:
            ui.update(min=minimum, max=maximum, soft_min=minimum, soft_max=min(maximum, 100))
        root.id_properties_ui(key).update(**ui)
    return root, collection


def create(context, preset="SHOCKWAVE", quality="MEDIUM"):
    settings = PRESETS[preset]
    segments = {"LOW": 32, "MEDIUM": 64, "HIGH": 128}[quality]
    root, collection = _controller(
        context, settings["label"], "mesh.ring", quality, PARAMETERS, settings
    )
    uid = root["vfx_id"]
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


def duplicate(context, root, *, _standalone=True, _references=None):
    root = resolve(root)
    if root is None:
        raise ValueError("Select a VFX controller or layer")
    if root["vfx_module"] == "screen.glare":
        from . import screen

        return screen.duplicate(context, root)
    if root["vfx_module"] == "core.composition":
        from . import composition

        return composition.duplicate(context, root)
    if _standalone and root.get("vfx_composition"):
        from . import composition

        composition.check_detach(root)
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
    assets = {}
    for source in sources:
        clone = source.copy()
        _tag(clone, uid)
        collection.objects.link(clone)
        mapping[source] = clone
        private.append(clone)
        if source.data:
            clone.data = source.data.copy()
            assets[source.data] = clone.data
            _tag(clone.data, uid)
            private.append(clone.data)
            for slot in clone.material_slots:
                if slot.material:
                    original = slot.material
                    if original not in assets:
                        assets[original] = original.copy()
                        _tag(assets[original], uid)
                        private.append(assets[original])
                        if original.node_tree:
                            assets[original.node_tree] = assets[original].node_tree
                            private.append(assets[original].node_tree)
                    slot.material = assets[original]
            for modifier in clone.modifiers:
                if modifier.type == "NODES" and modifier.node_group:
                    original = modifier.node_group
                    if original not in assets:
                        assets[original] = original.copy()
                        _tag(assets[original], uid)
                        private.append(assets[original])
                    modifier.node_group = assets[original]
    for source, clone in mapping.items():
        clone.parent = mapping.get(source.parent, source.parent)
    references = dict(_references or {}) | mapping | assets
    for data in private:
        _remap_drivers(data, references)
        if isinstance(data, bpy.types.Object):
            for modifier in data.modifiers:
                if modifier.type != "NODES" or modifier.node_group is None:
                    continue
                for item in modifier.node_group.interface.items_tree:
                    if item.item_type != "SOCKET" or item.in_out != "INPUT":
                        continue
                    setting = getattr(modifier.properties.inputs, item.identifier, None)
                    original = getattr(setting, "value", None)
                    if isinstance(original, bpy.types.ID) and original in references:
                        setting.value = references[original]
        if isinstance(data, bpy.types.NodeTree):
            for n in data.nodes:
                for socket in n.inputs:
                    original = getattr(socket, "default_value", None)
                    if isinstance(original, bpy.types.ID) and original in references:
                        socket.default_value = references[original]
    if _standalone and root.get("vfx_composition"):
        from . import composition

        composition.detach(context, mapping[root])
    select(context, mapping[root])
    return mapping[root]


def delete(root):
    root = resolve(root)
    if root is None:
        raise ValueError("Select a VFX controller or layer")
    if root["vfx_module"] == "core.composition":
        from . import composition

        return composition.remove(root)
    if root["vfx_module"] == "screen.glare":
        from . import screen

        screen.remove(root)
    _delete_spatial(root)


def _delete_spatial(root, validate_only=False):
    uid = root["vfx_id"]
    owned = [root] + [
        o
        for o in root.children_recursive
        if o.get("vfx_id") == uid and o.get("vfx_role") == "layer"
    ]
    # Shared generated assets still depend on this controller. Refuse destructive
    # unlinking rather than leave another object with broken native drivers.
    meshes = {o.data for o in owned if o.type == "MESH"}
    meshes.update(m for m in bpy.data.meshes if m.get("vfx_id") == uid)
    materials = {m for mesh in meshes for m in mesh.materials if m}
    materials.update(m for m in bpy.data.materials if m.get("vfx_id") == uid)
    groups = {
        m.node_group for o in owned for m in o.modifiers if m.type == "NODES" and m.node_group
    }
    groups.update(g for g in bpy.data.node_groups if g.get("vfx_id") == uid)
    for mesh in meshes:
        if mesh.get("vfx_id") == uid and mesh.users > sum(o.data == mesh for o in owned):
            raise ValueError("VFX mesh is shared; unlink external users before deleting")
    # Private GN Set Material references are internal consumers, not external sharing.
    internal = set(owned) | {data for data in meshes | groups if data.get("vfx_id") == uid}
    consumers = bpy.data.user_map(subset=materials) if materials else {}
    for material in materials:
        if material.get("vfx_id") == uid and (
            material.use_fake_user
            or material.use_extra_user
            or any(user not in internal for user in consumers.get(material, set()))
        ):
            raise ValueError("VFX material is shared; unlink external users before deleting")
    for group in groups:
        users = sum(
            sum(m.type == "NODES" and m.node_group == group for m in o.modifiers) for o in owned
        )
        if group.get("vfx_id") == uid and group.users > users:
            raise ValueError("VFX node group is shared; unlink external users before deleting")
    if validate_only:
        return
    # UUID ownership also discovers generated assets detached during native editing.
    resources = (
        [(bpy.data.meshes, m) for m in meshes]
        + [(bpy.data.node_groups, g) for g in groups]
        + [(bpy.data.materials, m) for m in materials]
    )
    for obj in owned:
        for child in list(obj.children):
            if child not in owned:
                matrix = child.matrix_world.copy()
                child.parent = None
                child.matrix_world = matrix
    unique = {data.as_pointer(): (store, data) for store, data in resources}
    for obj in reversed(owned):
        bpy.data.objects.remove(obj, do_unlink=True)
    # Meshes release material users first. Foreign data is retained.
    for store, data in sorted(
        unique.values(), key=lambda item: isinstance(item[1], bpy.types.Material)
    ):
        if data.get("vfx_id") != uid:
            continue
        if isinstance(data, bpy.types.Material):
            # Blender 5.2 can retain a stale count after removing a modifier's ID input.
            # All real external consumers were rejected before mutation; check again.
            if not bpy.data.user_map(subset={data}).get(data):
                store.remove(data)
        elif data.users == 0:
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
            "assets": _preset_assets(root),
            "module": root["vfx_module"],
            "asset_version": root["vfx_asset_version"],
            "name": root.name[:80],
            "quality": root["vfx_quality"],
            "parameters": {key: root[key] for key in preset_parameters_for(root["vfx_module"])},
        }
    )


def create_from_preset(context, data):
    from . import presets

    data = presets.validate(data)  # Validate completely before mutating Blender data.
    if data["module"] == "screen.glare":
        root = create_screen(context)
    elif data["module"] == "particle.burst":
        root = create_particle(context, data["quality"])
    elif data["module"] == "flipbook.atlas":
        image = load_atlas(data["assets"]["image"])
        root = create_flipbook(
            context, image, data["parameters"]["columns"], data["parameters"]["rows"]
        )
    else:
        root = create(context, quality=data["quality"])
    root.name = data["name"]
    root["vfx_quality"] = data["quality"]
    for key, value in data["parameters"].items():
        root[key] = value
    select(context, root)
    return root


def load_atlas(filepath):
    from pathlib import Path

    path = Path(filepath)
    if not path.is_file():
        raise ValueError("Atlas image not found: " + str(path))
    try:
        image = bpy.data.images.load(str(path.resolve()), check_existing=True)
    except RuntimeError as error:
        raise ValueError("Cannot load atlas image") from error
    validate_atlas(image)
    return image


def validate_atlas(image):
    if image is None or image.source not in {"FILE", "GENERATED"} or min(image.size) < 1:
        raise ValueError("Choose a loaded still image for the atlas")


def atlas_node(root):
    for layer in root.children_recursive:
        if layer.get("vfx_id") != root["vfx_id"] or layer.type != "MESH":
            continue
        for material in layer.data.materials:
            if material and material.node_tree:
                tex = material.node_tree.nodes.get("Atlas Image")
                if tex and tex.type == "TEX_IMAGE":
                    return tex
    raise ValueError("Atlas Image node is missing; restore it before exporting a preset")


def _preset_assets(root):
    if root["vfx_module"] in {"trail.ribbon", "core.composition"}:
        raise ValueError("Native paths and compositions require .blend Append or Duplicate")
    if root["vfx_module"] != "flipbook.atlas":
        return {}
    image = atlas_node(root).image
    validate_atlas(image)
    if not image.filepath:
        raise ValueError("Save the atlas image to disk before exporting a parameter preset")
    return {"image": bpy.path.abspath(image.filepath, library=image.library)}


def create_flipbook(context, image, columns=4, rows=4):
    from . import flipbook

    validate_atlas(image)
    if (
        type(columns) is not int
        or type(rows) is not int
        or not 1 <= columns <= 256
        or not 1 <= rows <= 256
    ):
        raise ValueError("Atlas rows and columns must be integers between 1 and 256")
    settings = {"columns": columns, "rows": rows, "last_frame": columns * rows - 1}
    root, collection = _controller(
        context, "Flipbook", "flipbook.atlas", "LOW", FLIPBOOK_PARAMETERS, settings
    )
    uid = root["vfx_id"]
    mesh = bpy.data.meshes.new("VFX • Sprite Quad")
    _tag(mesh, uid)
    mesh.from_pydata(
        [(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)], [], [(0, 1, 2, 3)]
    )
    mesh.update()
    uv = mesh.uv_layers.new(name="VFX UV")
    for index, coord in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[index].uv = coord
    layer = bpy.data.objects.new("VFX • Flipbook Layer", mesh)
    collection.objects.link(layer)
    layer.parent = root
    _tag(layer, uid, "layer")
    mesh.materials.append(flipbook.shader(root, image))
    flipbook.geometry(layer, root)
    select(context, root)
    return root


def create_screen(context):
    from . import screen

    return screen.create(context)


def create_particle(context, quality="LOW"):
    from . import particle
    from .parameters import PARTICLE_PARAMETERS

    if quality not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("Unknown particle quality")
    root, collection = _controller(
        context, "Particle Burst", "particle.burst", quality, PARTICLE_PARAMETERS, {}
    )
    mesh = bpy.data.meshes.new("VFX • Particle Source")
    _tag(mesh, root["vfx_id"])
    layer = bpy.data.objects.new("VFX • Particle Layer", mesh)
    _tag(layer, root["vfx_id"], "layer")
    collection.objects.link(layer)
    layer.parent = root
    material = particle.material(root)
    mesh.materials.append(material)
    particle.geometry(layer, root, material, quality)
    select(context, root)
    return root
