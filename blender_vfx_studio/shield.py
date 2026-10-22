"""Native spherical shield: editable mesh, radius nodes and exterior Fresnel shading."""

import bmesh
import bpy

from . import core
from .nodes import ACTIVE, PROGRESS, TIME_PROPS, drive, node
from .parameters import SHIELD_PARAMETERS


def create(context, quality="MEDIUM"):
    segments = {"LOW": 16, "MEDIUM": 32, "HIGH": 64}.get(quality)
    if segments is None:
        raise ValueError("Unknown shield quality")
    root, collection = core._controller(
        context, "Fresnel Energy Shield", "shader.shield", quality, SHIELD_PARAMETERS, {}
    )
    mesh = bpy.data.meshes.new("VFX • Shield Sphere")
    core._tag(mesh, root["vfx_id"])
    bm = bmesh.new()
    try:
        bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=segments // 2, radius=1)
        bm.to_mesh(mesh)
    finally:
        bm.free()
    for face in mesh.polygons:
        face.use_smooth = True
    mesh.update()
    layer = bpy.data.objects.new("VFX • Shield Layer", mesh)
    core._tag(layer, root["vfx_id"], "layer")
    collection.objects.link(layer)
    layer.parent = root
    mesh.materials.append(shader(root))
    geometry(layer, root)
    core.select(context, root)
    return root


def geometry(layer, root):
    tree = bpy.data.node_groups.new("VFX • Shield Radius and Lifetime", "GeometryNodeTree")
    core._tag(tree, root["vfx_id"])
    for direction in ("INPUT", "OUTPUT"):
        tree.interface.new_socket(
            name="Geometry", in_out=direction, socket_type="NodeSocketGeometry"
        )
    link = tree.links.new
    inp = node(tree, "NodeGroupInput", "Editable Sphere", -600, 200)
    out = node(tree, "NodeGroupOutput", "Output", 400, 200)
    radius = node(tree, "ShaderNodeValue", "Animated Radius", -600, -50)
    drive(
        radius.outputs[0],
        "default_value",
        root,
        f"r+e*{PROGRESS}",
        dict(TIME_PROPS, r="radius", e="expansion"),
    )
    scale = node(tree, "ShaderNodeCombineXYZ", "Uniform Radius", -350, -50)
    for socket in scale.inputs:
        link(radius.outputs[0], socket)
    transform = node(tree, "GeometryNodeTransform", "Scale Sphere", -100, 200)
    link(inp.outputs["Geometry"], transform.inputs["Geometry"])
    link(scale.outputs[0], transform.inputs["Scale"])
    hide = node(tree, "GeometryNodeDeleteGeometry", "Outside Lifetime", 150, 200, domain="POINT")
    inactive = node(tree, "ShaderNodeValue", "Inactive", -100, -100)
    drive(inactive.outputs[0], "default_value", root, f"1-({ACTIVE})", TIME_PROPS)
    link(transform.outputs[0], hide.inputs["Geometry"])
    link(inactive.outputs[0], hide.inputs["Selection"])
    link(hide.outputs[0], out.inputs["Geometry"])
    layer.modifiers.new("VFX • Shield Shape", "NODES").node_group = tree


def shader(root):
    material = bpy.data.materials.new("VFX • Fresnel Shield")
    core._tag(material, root["vfx_id"])
    material.use_nodes = True
    material.surface_render_method = "DITHERED"
    tree = material.node_tree
    tree.nodes.clear()
    link = tree.links.new

    def math_node(name, operation, a, b, x, y):
        result = node(tree, "ShaderNodeMath", name, x, y, operation=operation)
        for socket, value in zip(result.inputs, (a, b)):
            if isinstance(value, (int, float)):
                socket.default_value = value
            else:
                link(value, socket)
        return result.outputs[0]

    fresnel = node(tree, "ShaderNodeFresnel", "Fresnel Edge", -1000, 450)
    drive(fresnel.inputs["IOR"], "default_value", root, "p", {"p": "ior"})
    power = node(tree, "ShaderNodeMath", "Rim Falloff", -750, 450, operation="POWER")
    link(fresnel.outputs[0], power.inputs[0])
    drive(power.inputs[1], "default_value", root, "p", {"p": "rim_power"})
    coords = node(tree, "ShaderNodeTexCoord", "Sphere Coordinates", -1250, 50)
    noise = node(
        tree, "ShaderNodeTexNoise", "Flowing Volume Noise", -1000, 50, noise_dimensions="4D"
    )
    link(coords.outputs["Generated"], noise.inputs["Vector"])
    drive(noise.inputs["Scale"], "default_value", root, "p", {"p": "noise_scale"})
    drive(noise.inputs["W"], "default_value", root, f"{PROGRESS}*f", dict(TIME_PROPS, f="flow"))
    cutoff = node(tree, "ShaderNodeMath", "Dissolve", -750, 50, operation="GREATER_THAN")
    link(noise.outputs["Fac"], cutoff.inputs[0])
    drive(cutoff.inputs[1], "default_value", root, "p", {"p": "dissolve"})
    geometry = node(tree, "ShaderNodeNewGeometry", "Surface Side", -1000, -250)
    front = math_node("Exterior Only", "SUBTRACT", 1, geometry.outputs["Backfacing"], -750, -250)
    alpha = math_node("Rim × Noise", "MULTIPLY", power.outputs[0], cutoff.outputs[0], -500, 450)
    alpha = math_node("Front Surface", "MULTIPLY", alpha, front, -250, 450)
    fade = node(tree, "ShaderNodeValue", "Lifetime Opacity", -500, 0)
    drive(
        fade.outputs[0],
        "default_value",
        root,
        f"o*(1-{PROGRESS}*f)",
        dict(TIME_PROPS, o="opacity", f="fade"),
    )
    alpha = math_node("Final Opacity", "MULTIPLY", alpha, fade.outputs[0], 0, 450)
    emission = node(tree, "ShaderNodeEmission", "Shield Emission", 0, 0)
    for index in range(3):
        drive(emission.inputs["Color"], "default_value", root, "p", {"p": f"color_{index}"}, index)
    drive(emission.inputs["Strength"], "default_value", root, "p", {"p": "strength"})
    transparent = node(tree, "ShaderNodeBsdfTransparent", "Transparent", 0, 200)
    mix = node(tree, "ShaderNodeMixShader", "Shield Surface", 250, 300)
    link(alpha, mix.inputs[0])
    link(transparent.outputs[0], mix.inputs[1])
    link(emission.outputs[0], mix.inputs[2])
    out = node(tree, "ShaderNodeOutputMaterial", "Output", 500, 300)
    link(mix.outputs[0], out.inputs["Surface"])
    return material
