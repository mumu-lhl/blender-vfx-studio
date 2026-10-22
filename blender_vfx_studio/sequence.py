"""Numbered image sprites controlled by native ImageUser offset drivers."""

import re
from pathlib import Path

import bpy

from . import core, flipbook
from .nodes import PROGRESS, TIME_PROPS, drive, node
from .parameters import SEQUENCE_PARAMETERS


def files(filepath, count):
    if type(count) is not int or not 1 <= count <= 4096:
        raise ValueError("Sequence frame count must be an integer between 1 and 4096")
    path = Path(bpy.path.abspath(str(filepath))).expanduser().resolve()
    match = re.fullmatch(r"(.*?)([0-9]+)(\.[^.]+)", path.name)
    if match is None:
        raise ValueError("Choose a numbered first image, such as burst0010.png")
    prefix, digits, suffix = match.groups()
    base = int(digits)
    if base + count - 1 > 1000000:
        raise ValueError("Sequence file numbers must stay between 0 and 1000000")
    for number in range(base, base + count):
        current = path.with_name(f"{prefix}{number:0{len(digits)}d}{suffix}")
        if not current.is_file():
            raise ValueError("Sequence image not found: " + str(current))
    return path, base


def texture(root):
    for child in root.children_recursive:
        if child.get("vfx_id") == root["vfx_id"] and child.type == "MESH":
            for material in child.data.materials:
                if material and material.use_nodes:
                    tex = material.node_tree.nodes.get("Sequence Image")
                    if tex and tex.type == "TEX_IMAGE":
                        return tex
    raise ValueError("Sequence Image node is missing; restore it before exporting")


def snapshot(root):
    tex = texture(root)
    image = tex.image
    count = root.get("vfx_sequence_count")
    if image is None or image.source != "SEQUENCE":
        raise ValueError("Choose a sequence image before exporting a parameter preset")
    path, base = files(bpy.path.abspath(image.filepath, library=image.library), count)
    if tex.image_user.frame_duration != count or root.get("vfx_sequence_base") != base:
        raise ValueError("Sequence source/count changed; create a new sequence effect")
    return {"image": str(path), "frame_count": count}


def create(context, filepath, frame_count=16):
    path, base = files(filepath, frame_count)  # Check every requested file before scene mutation.
    try:
        image = bpy.data.images.load(str(path), check_existing=False)
    except RuntimeError as error:
        raise ValueError("Cannot load first sequence image") from error
    if image.source != "FILE" or min(image.size) < 1:
        bpy.data.images.remove(image)
        raise ValueError("Choose a numbered still-image sequence")
    image.source = "SEQUENCE"
    root, collection = core._controller(
        context,
        "Image Sequence",
        "flipbook.sequence",
        "LOW",
        SEQUENCE_PARAMETERS,
        {"last_frame": frame_count - 1},
    )
    root["vfx_sequence_count"], root["vfx_sequence_base"] = frame_count, base
    uid = root["vfx_id"]
    mesh = bpy.data.meshes.new("VFX • Sequence Quad")
    core._tag(mesh, uid)
    mesh.from_pydata(
        [(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)], [], [(0, 1, 2, 3)]
    )
    mesh.update()
    uv = mesh.uv_layers.new(name="VFX UV")
    for item, coord in zip(uv.data, ((0, 0), (1, 0), (1, 1), (0, 1))):
        item.uv = coord
    layer = bpy.data.objects.new("VFX • Sequence Layer", mesh)
    core._tag(layer, uid, "layer")
    collection.objects.link(layer)
    layer.parent = root
    layer["vfx_sequence_progress"] = 0.0
    drive(layer, '["vfx_sequence_progress"]', root, PROGRESS, TIME_PROPS)
    mesh.materials.append(shader(root, image, layer))
    flipbook.geometry(layer, root)
    core.select(context, root)
    return root


def shader(root, image, layer):
    material = bpy.data.materials.new("VFX • Image Sequence")
    core._tag(material, root["vfx_id"])
    material.use_nodes = True
    material.surface_render_method = "DITHERED"
    tree = material.node_tree
    tree.nodes.clear()
    uv = node(tree, "ShaderNodeTexCoord", "Sprite UV", 700, 500)
    tex = node(
        tree,
        "ShaderNodeTexImage",
        "Sequence Image",
        1200,
        500,
        image=image,
        interpolation="Closest",
        extension="CLIP",
    )
    tree.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    user = tex.image_user
    user.use_auto_refresh = True
    user.use_cyclic = False
    user.frame_start = 1
    user.frame_duration = root["vfx_sequence_count"]
    first = "min(max(a,0),n-1)"
    last = f"max({first},min(max(b,0),n-1))"
    desired = f"min({first}+floor((p+0.000001)*({last}-({first})+1)),{last})+z"
    # Blender clamps raw scene time BEFORE adding ImageUser.offset (image.cc).
    curve = drive(
        user,
        "frame_offset",
        root,
        f"{desired}-min(max(t,0),n)",
        dict(
            a="first_frame",
            b="last_frame",
            n="vfx_sequence_count",
            z="vfx_sequence_base",
        ),
    )
    # A layer property keeps each expression under Blender's 255-character limit.
    progress = curve.driver.variables.new()
    progress.name, progress.type = "p", "SINGLE_PROP"
    progress.targets[0].id = layer
    progress.targets[0].data_path = '["vfx_sequence_progress"]'
    variable = curve.driver.variables.new()
    variable.name, variable.type = "t", "CONTEXT_PROP"
    variable.targets[0].context_property = "ACTIVE_SCENE"
    variable.targets[0].data_path = "frame_current"
    flipbook.surface(tree, root, tex)
    return material
