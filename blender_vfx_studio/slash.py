"""Editable crescent slash driven entirely by native geometry and shader nodes."""

import math

import bpy

from . import core, nodes
from .nodes import ACTIVE, PROGRESS, TIME_PROPS, drive, node
from .parameters import (
    SLASH_PARAMETERS,
    SLASH_PARAMETERS_V1,
    SLASH_PARAMETERS_V2,
    SLASH_PARAMETERS_V3,
    SLASH_PARAMETERS_V4,
)


def create(context, quality="MEDIUM", *, asset_version=5):
    if asset_version not in (1, 2, 3, 4, 5):
        raise ValueError("Unsupported slash asset version")
    modern = asset_version >= 2
    segments = {"LOW": 32, "MEDIUM": 64, "HIGH": 128}.get(quality)
    if segments is None:
        raise ValueError("Unknown slash quality")
    root, collection = core._controller(
        context,
        "Arc Slash",
        "mesh.slash",
        quality,
        {
            1: SLASH_PARAMETERS_V1,
            2: SLASH_PARAMETERS_V2,
            3: SLASH_PARAMETERS_V3,
            4: SLASH_PARAMETERS_V4,
        }.get(asset_version, SLASH_PARAMETERS),
        {},
    )
    root["vfx_asset_version"] = asset_version
    uid = root["vfx_id"]
    vertices, faces, coordinates, bands = [], [], [], []
    across = (0, 0.06, 0.16, 0.35, 0.65, 1) if modern else (0, 1)
    for band in range(3 if modern else 1):
        base = len(vertices)
        for i in range(segments + 1):
            u = i / segments
            for v in across:
                angle = (u - 0.5) * math.radians(root["arc"]) * (1 - band * 0.16) - band * 0.14
                shape_u = u ** (1 + root["head_bias"] * 3) if asset_version >= 4 else u
                taper = max(math.sin(math.pi * shape_u), 0) ** root["taper"]
                if modern:
                    if asset_version >= 4:
                        taper *= 1 - 0.52 * bool(band) - 0.1 * band
                    else:
                        taper *= (1 - root["head_bias"] * (1 - u)) * (0.12 if band else 1)
                radius = max(root["radius"] * (1 + band * 0.075) - root["width"] * taper * v, 0.001)
                vertices.append((radius * math.cos(angle), radius * math.sin(angle), 0))
                coordinates.append((u, v))
                bands.append(float(band))
        for i in range(segments):
            for j in range(len(across) - 1):
                a = base + i * len(across) + j
                faces.append((a, a + len(across), a + len(across) + 1, a + 1))
    mesh = bpy.data.meshes.new("VFX • Slash Base")
    core._tag(mesh, uid)
    mesh.from_pydata(vertices, [], faces)
    for name, values in (
        ("vfx_arc", [u for u, v in coordinates]),
        ("vfx_inner", [v for u, v in coordinates]),
        ("vfx_wake", bands),
    ):
        if name == "vfx_wake" and not modern:
            continue
        attribute = mesh.attributes.new(name, "FLOAT", "POINT")
        for item, value in zip(attribute.data, values):
            item.value = value
    uv = mesh.uv_layers.new(name="VFX UV")
    for loop in mesh.loops:
        uv.data[loop.index].uv = coordinates[loop.vertex_index]
    mesh.update()
    layer = bpy.data.objects.new("VFX • Slash Layer", mesh)
    core._tag(layer, uid, "layer")
    collection.objects.link(layer)
    layer.parent = root
    if modern:
        from .slash_shader import shader

        material = shader(root, uid)
    else:
        material = nodes.shader(root, uid)
    material.name = "VFX • Slash Dissolve"
    uv_node = material.node_tree.nodes["Slash UV" if modern else "Ring UV"]
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
    motion = progress
    modern = root["vfx_asset_version"] >= 2
    shaped = root["vfx_asset_version"] >= 3
    layered = root["vfx_asset_version"] >= 4
    band = None
    if modern:
        attr = node(
            tree, "GeometryNodeInputNamedAttribute", "Wake Index", -1500, -1000, data_type="FLOAT"
        )
        attr.inputs["Name"].default_value = "vfx_wake"
        band = attr.outputs["Attribute"]
        if layered:
            delay = math_node("Layer Birth Delay", "MULTIPLY", band, 0.06, -1700, -2600)
            age = math_node("Time Since Layer Birth", "SUBTRACT", progress, delay, -1500, -2600)
            age = math_node("Nonnegative Layer Age", "MAXIMUM", age, 0, -1300, -2600)
            span = math_node("Wake Life Extension", "MULTIPLY", band, 0.1, -1700, -2800)
            span = math_node("Independent Layer Span", "ADD", span, 1, -1500, -2800)
            progress = math_node("Layer Local Clock", "DIVIDE", age, span, -1100, -2600)
            motion = progress
        one_minus = math_node("Remaining Life", "SUBTRACT", 1, progress, -1200, -1000)
        cubic = math_node("Ease Out Cube", "POWER", one_minus, 3, -1000, -1000)
        eased = math_node("Fast Sweep", "SUBTRACT", 1, cubic, -800, -1000)
        difference = math_node("Sweep Difference", "SUBTRACT", eased, progress, -600, -1000)
        ease = value("Motion Ease", "motion_ease", -1200, -1200)
        weighted = math_node("Ease Amount", "MULTIPLY", difference, ease, -400, -1000)
        motion = math_node("Sweep Clock", "ADD", progress, weighted, -200, -1000)
    arc = value("Arc Radians", "arc", -1200, 100, "p*0.017453292519943295")
    spin = value("Spin Radians", "spin", -1200, -100, "p*0.017453292519943295")
    centered = math_node("Centered Arc", "SUBTRACT", u.outputs["Attribute"], 0.5, -950, 500)
    if layered:
        negative = math_node("Negative Sweep", "LESS_THAN", spin, 0, -1700, 3100)
        reverse = math_node("Reverse Arc Direction", "MULTIPLY", negative, 2, -1500, 3100)
        orientation = math_node("Arc Follows Sweep Direction", "SUBTRACT", 1, reverse, -1300, 3100)
        centered = math_node(
            "Leading End Follows Spin", "MULTIPLY", centered, orientation, -1100, 3100
        )
    if modern:
        shorter = math_node("Wake Arc Reduction", "MULTIPLY", band, 0.16, -800, 1800)
        shorter = math_node("Wake Arc Fraction", "SUBTRACT", 1, shorter, -600, 1800)
        centered = math_node("Shorter Wakes", "MULTIPLY", centered, shorter, -400, 1800)
    angle = math_node("Arc Angle", "MULTIPLY", centered, arc, -700, 500)
    rotation = math_node("Spin Over Life", "MULTIPLY", spin, motion, -950, -100)
    angle = math_node("Animated Angle", "ADD", angle, rotation, -450, 500)
    if modern:
        lag = math_node("Wake Lag", "MULTIPLY", band, -0.14, -300, 1200)
        sign = math_node("Sweep Direction", "SIGN", spin, 0, -500, 1400)
        lag = math_node("Directional Wake Lag", "MULTIPLY", lag, sign, -300, 1400)
        angle = math_node("Trailing Angle", "ADD", angle, lag, -100, 1200)
    if shaped:
        spread = value("Wake Spread", "wake_spread", -800, 2200)
        separation = math_node("Separating Clock", "MULTIPLY", motion, spread, -600, 2200)
        separation = math_node("Wake Separation", "MULTIPLY", separation, band, -400, 2200)
        separation = math_node("Trailing Separation", "MULTIPLY", separation, -0.42, -200, 2200)
        separation = math_node("Signed Separation", "MULTIPLY", separation, sign, 0, 2200)
        angle = math_node("Separating Wakes", "ADD", angle, separation, 200, 2200)
    direction = node(tree, "ShaderNodeCombineXYZ", "Radial Direction", 50, 500)
    link(math_node("Cosine", "COSINE", angle, 0, -200, 500), direction.inputs["X"])
    link(math_node("Sine", "SINE", angle, 0, -200, 300), direction.inputs["Y"])
    width = value("Width", "width", -700, -300)
    taper = value("Taper", "taper", -700, -500)
    taper_u = u.outputs["Attribute"]
    if modern:
        attack = value("Attack", "attack", -1500, -2100)
        front = math_node("Reveal Progress", "DIVIDE", progress, attack, -1300, -2100)
        front = math_node("Reveal End", "MINIMUM", front, 1, -1100, -2100)
        front = math_node("Nonzero Reveal", "MAXIMUM", front, 0.0001, -900, -2100)
        taper_u = math_node("Moving Tip Coordinates", "DIVIDE", taper_u, front, -700, -2100)
        taper_u = math_node("Clamped Tip", "MINIMUM", taper_u, 1, -500, -2100)
        if layered:
            bias = value("Head Bias", "head_bias", -1500, -3000)
            exponent = math_node("Head Concentration", "MULTIPLY", bias, 3, -1300, -3000)
            exponent = math_node("Leading Mass Power", "ADD", exponent, 1, -1100, -3000)
            taper_u = math_node("Wide Head Pointed Tail", "POWER", taper_u, exponent, -300, -2100)
    across = math_node("Taper Angle", "MULTIPLY", taper_u, math.pi, -950, -800)
    taper_sine = math_node("Taper Sine", "SINE", across, 0, -700, -800)
    positive = math_node("Nonnegative Taper", "MAXIMUM", taper_sine, 0, -450, -800)
    amount = math_node("Tip Taper", "POWER", positive, taper, -200, -700)
    if modern:
        if not layered:
            bias = value("Head Bias", "head_bias", -1200, -1400)
            tail = math_node("Tail Weight", "SUBTRACT", 1, u.outputs["Attribute"], -1000, -1400)
            bias = math_node("Asymmetric Weight", "MULTIPLY", bias, tail, -800, -1400)
            bias = math_node("Leading Body", "SUBTRACT", 1, bias, -600, -1400)
            amount = math_node("Biased Taper", "MULTIPLY", amount, bias, -400, -1400)
        wake = math_node("Is Wake", "GREATER_THAN", band, 0.5, -1000, -1600)
        narrow = math_node(
            "Wake Narrowing", "MULTIPLY", wake, 0.52 if layered else 0.88, -800, -1600
        )
        if layered:
            distance = math_node("Outer Wake Is Thinner", "MULTIPLY", band, 0.1, -1000, -3300)
            narrow = math_node("Unequal Wake Widths", "ADD", narrow, distance, -600, -1600)
        narrow = math_node("Ribbon Width Factor", "SUBTRACT", 1, narrow, -600, -1600)
        amount = math_node("Wake Width", "MULTIPLY", amount, narrow, -200, -1400)
        shrink = math_node("Release Width", "MULTIPLY", progress, 0.55, -1000, -1800)
        shrink = math_node("Width Envelope", "SUBTRACT", 1, shrink, -800, -1800)
        amount = math_node("Width Over Life", "MULTIPLY", amount, shrink, 0, -1400)
    if root["vfx_asset_version"] >= 5:
        # Same moving islands as the shader, with actual pointed geometry.
        phase = math_node(
            "Wake Fragment Along Arc", "MULTIPLY", u.outputs["Attribute"], 15, -1700, -3600
        )
        phase = math_node(
            "Wake Fragment Offset",
            "ADD",
            phase,
            math_node("Wake Fragment Layer", "MULTIPLY", band, 1.7, -1700, -3800),
            -1500,
            -3600,
        )
        phase = math_node(
            "Wake Fragment Travel",
            "SUBTRACT",
            phase,
            math_node("Wake Fragment Clock", "MULTIPLY", progress, 6, -1500, -3800),
            -1300,
            -3600,
        )
        profile = math_node("Wake Fragment Curve", "SINE", phase, 0, -1100, -3600)
        profile = math_node("Wake Fragment Ends", "ADD", profile, 0.25, -900, -3600)
        profile = math_node("Nonnegative Wake Width", "MAXIMUM", profile, 0, -700, -3600)
        profile = math_node("Wake Width Normalized", "DIVIDE", profile, 1.25, -500, -3600)
        area = value("Afterimage Area", "afterimage", -1700, -4000)
        area = math_node("Wake Area Width", "SQRT", area, 0, -1500, -4000)
        profile = math_node("Editable Fragment Width", "MULTIPLY", profile, area, -300, -3600)
        delta = math_node("Fragment Width Difference", "SUBTRACT", profile, 1, -100, -3600)
        delta = math_node("Wake Only Width Difference", "MULTIPLY", delta, wake, 100, -3600)
        profile = math_node("Keep Primary Width", "ADD", delta, 1, 300, -3600)
        amount = math_node("Tapered Colored Wake Width", "MULTIPLY", amount, profile, 500, -3600)
    offset = math_node("Tapered Width", "MULTIPLY", width, amount, 50, -500)
    offset = math_node("Inner Offset", "MULTIPLY", offset, inner.outputs["Attribute"], 300, -300)
    radius = value("Radius", "radius", -450, 100)
    expansion = value("Expansion", "expansion", -450, -100)
    growth = math_node("Radius Growth", "MULTIPLY", progress, expansion, -200, 100)
    radius = math_node("Outer Radius", "ADD", radius, growth, 50, 100)
    if modern:
        offset_wake = math_node("Wake Spacing", "MULTIPLY", band, 0.075, 0, 1500)
        offset_wake = math_node("Radius Relative Wake", "MULTIPLY", radius, offset_wake, 200, 1500)
        radius = math_node("Wake Radius", "ADD", radius, offset_wake, 400, 1500)
    if shaped:
        from .slash_shape import shape

        radius, offset, depth = shape(
            tree,
            root,
            u.outputs["Attribute"],
            inner.outputs["Attribute"],
            band,
            progress,
            radius,
            offset,
        )
    radius = math_node("Inner Radius", "SUBTRACT", radius, offset, 550, 100)
    radius = math_node("Positive Radius", "MAXIMUM", radius, 0.001, 800, 100)
    scale = node(tree, "ShaderNodeVectorMath", "Arc Position", 1050, 500, operation="SCALE")
    link(direction.outputs[0], scale.inputs[0])
    link(radius, scale.inputs["Scale"])
    setpos = node(tree, "GeometryNodeSetPosition", "Crescent Shape", 1200, 800)
    link(inp.outputs["Geometry"], setpos.inputs["Geometry"])
    if shaped:
        z = node(tree, "ShaderNodeCombineXYZ", "Blade Depth", 1050, 100)
        link(depth, z.inputs["Z"])
        position = node(tree, "ShaderNodeVectorMath", "Banked Arc", 1100, 300, operation="ADD")
        link(scale.outputs[0], position.inputs[0])
        link(z.outputs[0], position.inputs[1])
        link(position.outputs[0], setpos.inputs["Position"])
    else:
        link(scale.outputs[0], setpos.inputs["Position"])
    hide = node(tree, "GeometryNodeDeleteGeometry", "Outside Lifetime", 1450, 800, domain="POINT")
    active = value("Active", None, 800, -500, ACTIVE, TIME_PROPS)
    inactive = math_node("Inactive", "LESS_THAN", active, 0.5, 1050, -300)
    link(setpos.outputs[0], hide.inputs["Geometry"])
    link(inactive, hide.inputs["Selection"])
    link(hide.outputs[0], out.inputs["Geometry"])
    obj.modifiers.new("VFX • Procedural Slash", "NODES").node_group = tree
