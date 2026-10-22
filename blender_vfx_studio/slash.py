"""Editable crescent slash driven entirely by native geometry and shader nodes."""

import math

import bpy

from . import core, nodes
from .nodes import ACTIVE, PROGRESS, TIME_PROPS, drive, node
from .parameters import SLASH_PARAMETERS


def create(context, quality="MEDIUM"):
    segments = {"LOW": 32, "MEDIUM": 64, "HIGH": 128}.get(quality)
    if segments is None:
        raise ValueError("Unknown slash quality")
    root, collection = core._controller(
        context, "Arc Slash", "mesh.slash", quality, SLASH_PARAMETERS, {}
    )
    uid = root["vfx_id"]
    vertices, faces = [], []
    for i in range(segments + 1):
        u = i / segments
        angle = (u - 0.5) * math.radians(root["arc"])
        taper = max(math.sin(math.pi * u), 0) ** root["taper"]
        for radius in (root["radius"], max(root["radius"] - root["width"] * taper, 0.001)):
            vertices.append((radius * math.cos(angle), radius * math.sin(angle), 0))
        if i < segments:
            a = 2 * i
            faces.append((a, a + 2, a + 3, a + 1))
    mesh = bpy.data.meshes.new("VFX • Slash Base")
    core._tag(mesh, uid)
    mesh.from_pydata(vertices, [], faces)
    for name, values in (
        ("vfx_arc", [i / segments for i in range(segments + 1) for _ in range(2)]),
        ("vfx_inner", [i % 2 for i in range(2 * (segments + 1))]),
    ):
        attribute = mesh.attributes.new(name, "FLOAT", "POINT")
        for item, value in zip(attribute.data, values):
            item.value = value
    uv = mesh.uv_layers.new(name="VFX UV")
    for polygon in mesh.polygons:
        u = polygon.index / segments
        for index, coord in zip(
            polygon.loop_indices, [(u, 0), (u + 1 / segments, 0), (u + 1 / segments, 1), (u, 1)]
        ):
            uv.data[index].uv = coord
    mesh.update()
    layer = bpy.data.objects.new("VFX • Slash Layer", mesh)
    core._tag(layer, uid, "layer")
    collection.objects.link(layer)
    layer.parent = root
    material = nodes.shader(root, uid)
    material.name = "VFX • Slash Dissolve"
    uv_node = material.node_tree.nodes["Ring UV"]
    uv_node.name = uv_node.label = "Slash UV"
    mesh.materials.append(material)
    geometry(layer, root)
    core.select(context, root)
    return root


def geometry(obj, root):
    tree = bpy.data.node_groups.new("VFX • Crescent Slash", "GeometryNodeTree")
    core._tag(tree, root["vfx_id"])
    for direction in ("INPUT", "OUTPUT"):
        tree.interface.new_socket(
            name="Geometry", in_out=direction, socket_type="NodeSocketGeometry"
        )
    link = tree.links.new
    inp = node(tree, "NodeGroupInput", "Base Arc", -1200, 800)
    out = node(tree, "NodeGroupOutput", "Output", 1700, 800)

    def value(name, prop, x, y, expression="p", properties=None):
        n = node(tree, "ShaderNodeValue", name, x, y)
        drive(n.outputs[0], "default_value", root, expression, properties or {"p": prop})
        return n.outputs[0]

    def math_node(name, operation, a, b, x, y):
        n = node(tree, "ShaderNodeMath", name, x, y, operation=operation)
        for socket, source in zip(n.inputs, (a, b)):
            if isinstance(source, (int, float)):
                socket.default_value = source
            else:
                link(source, socket)
        return n.outputs[0]

    u = node(tree, "GeometryNodeInputNamedAttribute", "Along Arc", -1200, 500, data_type="FLOAT")
    u.inputs["Name"].default_value = "vfx_arc"
    inner = node(
        tree, "GeometryNodeInputNamedAttribute", "Inner Edge", -1200, -300, data_type="FLOAT"
    )
    inner.inputs["Name"].default_value = "vfx_inner"
    progress = value("Progress", None, -1200, -600, PROGRESS, TIME_PROPS)
    arc = value("Arc Radians", "arc", -1200, 100, "p*0.017453292519943295")
    spin = value("Spin Radians", "spin", -1200, -100, "p*0.017453292519943295")
    centered = math_node("Centered Arc", "SUBTRACT", u.outputs["Attribute"], 0.5, -950, 500)
    angle = math_node("Arc Angle", "MULTIPLY", centered, arc, -700, 500)
    rotation = math_node("Spin Over Life", "MULTIPLY", spin, progress, -950, -100)
    angle = math_node("Animated Angle", "ADD", angle, rotation, -450, 500)
    direction = node(tree, "ShaderNodeCombineXYZ", "Radial Direction", 50, 500)
    link(math_node("Cosine", "COSINE", angle, 0, -200, 500), direction.inputs["X"])
    link(math_node("Sine", "SINE", angle, 0, -200, 300), direction.inputs["Y"])
    width = value("Width", "width", -700, -300)
    taper = value("Taper", "taper", -700, -500)
    across = math_node("Taper Angle", "MULTIPLY", u.outputs["Attribute"], math.pi, -950, -800)
    taper_sine = math_node("Taper Sine", "SINE", across, 0, -700, -800)
    positive = math_node("Nonnegative Taper", "MAXIMUM", taper_sine, 0, -450, -800)
    amount = math_node("Tip Taper", "POWER", positive, taper, -200, -700)
    offset = math_node("Tapered Width", "MULTIPLY", width, amount, 50, -500)
    offset = math_node("Inner Offset", "MULTIPLY", offset, inner.outputs["Attribute"], 300, -300)
    radius = value("Radius", "radius", -450, 100)
    expansion = value("Expansion", "expansion", -450, -100)
    growth = math_node("Radius Growth", "MULTIPLY", progress, expansion, -200, 100)
    radius = math_node("Outer Radius", "ADD", radius, growth, 50, 100)
    radius = math_node("Inner Radius", "SUBTRACT", radius, offset, 550, 100)
    radius = math_node("Positive Radius", "MAXIMUM", radius, 0.001, 800, 100)
    scale = node(tree, "ShaderNodeVectorMath", "Arc Position", 1050, 500, operation="SCALE")
    link(direction.outputs[0], scale.inputs[0])
    link(radius, scale.inputs["Scale"])
    setpos = node(tree, "GeometryNodeSetPosition", "Crescent Shape", 1200, 800)
    link(inp.outputs["Geometry"], setpos.inputs["Geometry"])
    link(scale.outputs[0], setpos.inputs["Position"])
    hide = node(tree, "GeometryNodeDeleteGeometry", "Outside Lifetime", 1450, 800, domain="POINT")
    active = value("Active", None, 800, -500, ACTIVE, TIME_PROPS)
    inactive = math_node("Inactive", "LESS_THAN", active, 0.5, 1050, -300)
    link(setpos.outputs[0], hide.inputs["Geometry"])
    link(inactive, hide.inputs["Selection"])
    link(hide.outputs[0], out.inputs["Geometry"])
    obj.modifiers.new("VFX • Procedural Slash", "NODES").node_group = tree
