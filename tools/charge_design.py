"""Authored charge shapes: native flame core, converging ribbons and spiral motes."""

import math

from blender_vfx_studio.nodes import ACTIVE, PROGRESS, TIME_PROPS, drive, node


class _Fields:
    """Small construction helpers; the saved result contains ordinary Blender nodes."""

    def __init__(self, tree, root):
        self.tree, self.root, self.index = tree, root, 0

    def n(self, kind, name, **values):
        i = self.index
        self.index += 1
        return node(self.tree, kind, name, (i // 8) * 260, -(i % 8) * 220, **values)

    def link(self, source, target):
        self.tree.links.new(source, target)

    def value(self, name, default=0, prop=None, expression=None):
        n = self.n("ShaderNodeValue", name)
        n.outputs[0].default_value = default
        if expression:
            drive(n.outputs[0], "default_value", self.root, expression, TIME_PROPS)
        elif prop:
            drive(n.outputs[0], "default_value", self.root, "p", {"p": prop})
        return n.outputs[0]

    def m(self, name, op, a, b=0):
        n = self.n("ShaderNodeMath", name, operation=op)
        for slot, arg in zip(n.inputs, (a, b)):
            if isinstance(arg, (int, float)):
                slot.default_value = arg
            else:
                self.link(arg, slot)
        return n.outputs[0]

    def xyz(self, name, x, y, z):
        n = self.n("ShaderNodeCombineXYZ", name)
        for slot, arg in zip(n.inputs, (x, y, z)):
            if isinstance(arg, (int, float)):
                slot.default_value = arg
            else:
                self.link(arg, slot)
        return n.outputs[0]

    def v(self, name, op, a, b):
        n = self.n("ShaderNodeVectorMath", name, operation=op)
        self.link(a, n.inputs[0])
        slot = n.inputs["Scale"] if op == "SCALE" else n.inputs[1]
        if isinstance(b, (int, float, tuple)):
            slot.default_value = b
        else:
            self.link(b, slot)
        return n.outputs[0]

    def stage(self, name, p, start, end):
        n = self.n("ShaderNodeMapRange", name)
        n.interpolation_type, n.clamp = "SMOOTHSTEP", True
        n.inputs["From Min"].default_value = start
        n.inputs["From Max"].default_value = end
        self.link(p, n.inputs["Value"])
        return n.outputs[0]

    def attr(self, name):
        n = self.n("GeometryNodeInputNamedAttribute", name, data_type="FLOAT")
        n.inputs["Name"].default_value = name
        return n.outputs["Attribute"]


def _geometry(root, label):
    layer = root.children[0]
    tree = layer.modifiers[0].node_group
    tree.animation_data_clear()
    tree.nodes.clear()
    tree.name = "VFX • " + label
    layer.name = "VFX • " + label
    layer.data.name = "VFX • " + label + " Mesh"
    g = _Fields(tree, root)
    inp = g.n("NodeGroupInput", "Authored Editable Mesh")
    return layer, g, inp.outputs["Geometry"]


def _finish(g, geometry):
    active = g.value("Outside Effect Lifetime", expression=f"1-({ACTIVE})")
    hide = g.n("GeometryNodeDeleteGeometry", "Native Lifetime", domain="POINT")
    g.link(geometry, hide.inputs["Geometry"])
    g.link(active, hide.inputs["Selection"])
    out = g.n("NodeGroupOutput", "Output")
    g.link(hide.outputs[0], out.inputs["Geometry"])


def _mesh(layer, vertices, faces, attributes=None):
    mesh = layer.data
    mesh.clear_geometry()
    mesh.from_pydata(vertices, [], faces)
    for face in mesh.polygons:
        face.use_smooth = False
    for name, values in (attributes or {}).items():
        attr = mesh.attributes.get(name) or mesh.attributes.new(name, "FLOAT", "POINT")
        for slot, value in zip(attr.data, values):
            slot.value = value
    mesh.update()


def _surface(root, *, core=False):
    material = root.children[0].data.materials[0]
    material.name = "VFX • Charge Plasma Core" if core else "VFX • Charge Flow"
    tree = material.node_tree
    tree.animation_data_clear()
    tree.nodes.clear()
    g = _Fields(tree, root)
    p = g.value("Charge Clock", expression=PROGRESS)
    ignite = g.stage("Ignition", p, 0, 0.16)
    release = g.stage("Release And Break Apart", p, 0.82, 1)
    loss = g.m("Editable Fade", "MULTIPLY", release, g.value("Fade", prop="fade"))
    alpha = g.m(
        "Charge Envelope",
        "MULTIPLY",
        1 if core else ignite,
        g.m("Opacity After Release", "SUBTRACT", 1, loss),
    )
    if core:
        alpha = g.m("Editable Opacity", "MULTIPLY", alpha, g.value("Opacity", prop="opacity"))
    envelope = alpha
    color = g.n("ShaderNodeCombineXYZ", "Editable Energy Color")
    for i in range(3):
        drive(color.inputs[i], "default_value", root, "c", {"c": f"color_{i}"})
    coords = g.n("ShaderNodeTexCoord", "Authored Shape Coordinates")
    noise = g.n("ShaderNodeTexNoise", "Turbulent Energy Channels", noise_dimensions="4D")
    channels = g.v(
        "Longitudinal Channels",
        "MULTIPLY",
        coords.outputs["Generated"],
        (3.0, 3.0, 0.55) if core else (1.0, 1.0, 1.0),
    )
    g.link(channels, noise.inputs["Vector"])
    g.link(g.value("Noise Scale", prop="noise_scale"), noise.inputs["Scale"])
    noise.inputs["Detail"].default_value = 1.5
    g.link(
        g.m("Channel Acceleration", "MULTIPLY", g.m("Charge Squared", "MULTIPLY", p, p), 9),
        noise.inputs["W"],
    )
    erosion = g.m(
        "Release Erosion",
        "ADD",
        g.value("Dissolve", prop="dissolve"),
        g.m("Erosion During Release", "MULTIPLY", release, 0.8),
    )
    alpha = g.m(
        "Broken Energy Surface",
        "MULTIPLY",
        alpha,
        g.m("Surviving Energy", "GREATER_THAN", noise.outputs["Fac"], erosion),
    )
    gather = g.stage("Increasing Concentration", p, 0.15, 0.8)

    def attribute(name):
        return g.n("ShaderNodeAttribute", name, attribute_name=name).outputs["Fac"]

    if core:
        normal = g.n("ShaderNodeNewGeometry", "Core Surface Normal")
        facing = g.n("ShaderNodeVectorMath", "Illustrated Volume", operation="DOT_PRODUCT")
        g.link(normal.outputs["Normal"], facing.inputs[0])
        facing.inputs[1].default_value = (-0.45, -0.65, 0.6)
        u = attribute("charge_core_u")
        angle = g.m(
            "Angle Around Core",
            "ARCTAN2",
            attribute("charge_angle_sin"),
            attribute("charge_angle_cos"),
        )
        phase = g.m(
            "Helical Veins",
            "ADD",
            g.m("Three Energy Veins", "MULTIPLY", angle, 3),
            g.m("Veins Rise Along Core", "MULTIPLY", u, 5),
        )
        phase = g.m(
            "Vein Turbulence",
            "ADD",
            phase,
            g.m("Uneven Veins", "MULTIPLY", noise.outputs["Fac"], 1.7),
        )
        phase = g.m(
            "Veins Accelerate",
            "SUBTRACT",
            phase,
            g.m("Flow Speed", "MULTIPLY", g.m("Flow Clock", "MULTIPLY", p, p), 9),
        )
        thin = g.m("Thin Curving Channel", "ABSOLUTE", g.m("Channel Wave", "SINE", phase))
        hot = g.m("Bright Vein", "SUBTRACT", 1, g.stage("Vein Soft Edges", thin, 0.10, 0.32))
        hot = g.m("Concentrated Veins", "MULTIPLY", hot, gather)
        # Three illustrated values describe volume without a glossy gradient or broad random holes.
        mid = g.m("Lit Midtone", "GREATER_THAN", facing.outputs["Value"], 0.05)
        bright = g.m("Narrow Lit Face", "GREATER_THAN", facing.outputs["Value"], 0.55)
        cel = g.m("Dark To Midtone", "MULTIPLY_ADD", mid, 0.18)
        cel.node.inputs[2].default_value = 0.045
        cel = g.m(
            "Readable Lit Volume", "ADD", cel, g.m("Lit Face Value", "MULTIPLY", bright, 0.32)
        )
        body = g.v("Readable Dark And Light Body", "SCALE", color.outputs[0], cel)
    else:
        u, side, strand = (
            attribute("charge_flow_u"),
            attribute("charge_side"),
            attribute("charge_phase"),
        )
        side = g.m("Absolute Edge", "ABSOLUTE", side)
        center = g.m("Distance From Edge", "SUBTRACT", 1, side)
        soft = g.stage("Small Soft Border", center, 0, 0.18)
        alpha = g.m("Ribbon Opacity", "MULTIPLY", alpha, soft)
        along = g.m(
            "Brighter Toward Core", "MULTIPLY_ADD", g.m("Head Concentration", "MULTIPLY", u, u), 0.8
        )
        along.node.inputs[2].default_value = 0.2
        across = g.m(
            "Ink Edge And Midtone",
            "MULTIPLY_ADD",
            g.m("Ribbon Midtone Width", "GREATER_THAN", center, 0.2),
            0.20,
        )
        across.node.inputs[2].default_value = 0.055
        across = g.m(
            "Illustrated Stream Bands",
            "ADD",
            across,
            g.m(
                "Narrow Cyan Center",
                "MULTIPLY",
                g.m("Center Band Width", "GREATER_THAN", center, 0.65),
                0.65,
            ),
        )
        body = g.v(
            "Ink Edge And Cyan Body",
            "SCALE",
            color.outputs[0],
            g.m("Guided Ribbon Color", "MULTIPLY", along, across),
        )
        wave = g.m(
            "Flow Bands",
            "ADD",
            g.m("Three Flow Packets", "MULTIPLY", u, 3),
            g.m("Unequal Packet Phase", "MULTIPLY", strand, 0.2),
        )
        wave = g.m(
            "Flow Moves Inward",
            "SUBTRACT",
            wave,
            g.m("Accelerating Packet Clock", "MULTIPLY", g.m("Packet Time", "MULTIPLY", p, p), 12),
        )
        wave = g.m("Repeated Packets", "FRACT", wave)
        hot = g.m(
            "Packet Length",
            "MULTIPLY",
            g.stage("Packet Arrives", wave, 0.05, 0.2),
            g.m("Packet Tail", "SUBTRACT", 1, g.stage("Packet Passes", wave, 0.55, 0.85)),
        )
        packet = hot
        hot = g.m("Packet Follows Core", "MULTIPLY", hot, across)
        packet_alpha = g.m("Visible Flow Packets", "MULTIPLY_ADD", packet, 0.65)
        packet_alpha.node.inputs[2].default_value = 0.35
        alpha = g.m("Separated Energy Wisps", "MULTIPLY", alpha, packet_alpha)
        hot = g.m("Flow Emphasis", "MULTIPLY", hot, 0.6)
    mix = g.n("ShaderNodeMixRGB", "Dark Body And Flowing Energy")
    g.link(hot, mix.inputs[0])
    g.link(body, mix.inputs[1])
    hot_color = g.n("ShaderNodeMixRGB", "Editable Color To Hot Light")
    hot_color.inputs[0].default_value = 0.85 if core else 0.035
    g.link(color.outputs[0], hot_color.inputs[1])
    hot_color.inputs[2].default_value = (0.9, 0.95, 1.0, 1)
    g.link(hot_color.outputs[0], mix.inputs[2])
    surface_color = mix.outputs[0]
    if core:
        inner = attribute("charge_inner")
        cracks = g.m("Cutout Energy Channels", "GREATER_THAN", hot, 0.3)
        shell_alpha = g.m(
            "Shell Openings", "MULTIPLY", alpha, g.m("Shell Coverage", "SUBTRACT", 1, cracks)
        )
        alpha_mix = g.n("ShaderNodeMixRGB", "Shell And Inner Opacity")
        g.link(inner, alpha_mix.inputs[0])
        g.link(shell_alpha, alpha_mix.inputs[1])
        inner_survival = g.m(
            "Inner Dissolves Last",
            "SUBTRACT",
            1,
            g.stage("Inner Dissolve Threshold", g.value("Inner Dissolve", prop="dissolve"), 0.7, 1),
        )
        g.link(
            g.m("Internal Energy Envelope", "MULTIPLY", envelope, inner_survival),
            alpha_mix.inputs[2],
        )
        alpha = alpha_mix.outputs[0]
        kernel_color = g.n("ShaderNodeMixRGB", "Concentrated Inner Light")
        brightness = g.m("Inner Compression Brightness", "MULTIPLY_ADD", gather, 0.3)
        brightness.node.inputs[2].default_value = 0.55
        g.link(brightness, kernel_color.inputs[0])
        g.link(color.outputs[0], kernel_color.inputs[1])
        kernel_color.inputs[2].default_value = (0.9, 0.98, 1, 1)
        core_mix = g.n("ShaderNodeMixRGB", "Light Beneath Broken Shell")
        g.link(inner, core_mix.inputs[0])
        g.link(surface_color, core_mix.inputs[1])
        g.link(kernel_color.outputs[0], core_mix.inputs[2])
        surface_color = core_mix.outputs[0]
    emission = g.n("ShaderNodeEmission", "Native Energy Surface")
    g.link(surface_color, emission.inputs["Color"])
    g.link(g.value("Emission", prop="strength"), emission.inputs["Strength"])
    transparent = g.n("ShaderNodeBsdfTransparent", "Transparent")
    surface = g.n("ShaderNodeMixShader", "Ignite And Dissipate")
    g.link(alpha, surface.inputs[0])
    g.link(transparent.outputs[0], surface.inputs[1])
    g.link(emission.outputs[0], surface.inputs[2])
    out = g.n("ShaderNodeOutputMaterial", "Output")
    g.link(surface.outputs[0], out.inputs["Surface"])


def core_shape(root):
    layer, g, geometry = _geometry(root, "Compressed Flame Core")
    vertices, faces = [], []
    core_attrs = {
        k: []
        for k in (
            "charge_core_u",
            "charge_angle_sin",
            "charge_angle_cos",
            "charge_inner",
            "charge_tongue",
        )
    }
    # Three unequal flame tongues share one native editable mesh.
    for tongue, (steps, sides, height, breadth, offset) in enumerate(
        [
            (17, 8, 1.0, 0.55, (0.0, 0.0)),
            (11, 6, 0.67, 0.3, (-0.65, 0.16)),
            (11, 6, 0.50, 0.24, (0.62, -0.18)),
            (9, 6, 0.67, 0.24, (0.0, 0.0)),
        ]
    ):
        base = len(vertices)
        for j in range(steps):
            t = j / (steps - 1)
            z = (-0.75 + 1.95 * t) * height
            radius = max(math.sin(math.pi * t), 0.004) ** 0.85 * breadth * (1 - 0.3 * t)
            for k in range(sides):
                a = k * math.tau / sides + z * 0.65 + tongue * 0.7
                r = radius * (1 + 0.12 * math.sin(k * 2.3 + t * 8 + tongue))
                bend = 0.12 * math.sin(t * 3.5 + tongue) * t
                vertices.append(
                    (r * math.cos(a) + offset[0] * t + bend, r * math.sin(a) + offset[1] * t, z)
                )
                core_attrs["charge_core_u"].append(t)
                core_attrs["charge_angle_sin"].append(math.sin(a))
                core_attrs["charge_angle_cos"].append(math.cos(a))
                core_attrs["charge_inner"].append(1.0 if tongue == 3 else 0.0)
                core_attrs["charge_tongue"].append(float(tongue))
        for j in range(steps - 1):
            for k in range(sides):
                a, b = base + j * sides + k, base + j * sides + (k + 1) % sides
                faces.append((a, b, b + sides, a + sides))
    _mesh(layer, vertices, faces, core_attrs)
    for face in layer.data.polygons:
        face.use_smooth = True
    p = g.value("Charge Clock", expression=PROGRESS)
    ignite = g.stage("Ignition Growth", p, 0, 0.18)
    gather = g.stage("Compression Builds", p, 0.12, 0.8)
    release = g.stage("Release Collapse", p, 0.84, 1)
    remaining = g.m("Remaining Shape", "SUBTRACT", 1, release)
    width = g.m(
        "Narrow Under Compression",
        "SUBTRACT",
        1,
        g.m("Compression Amount", "MULTIPLY", gather, 0.32),
    )
    height = g.m(
        "Stretch Under Tension", "ADD", 0.6, g.m("Tension Height", "MULTIPLY", gather, 0.6)
    )
    radius = g.m(
        "Core Radius",
        "MULTIPLY",
        g.m(
            "Animated Radius",
            "ADD",
            g.value("Radius", prop="radius"),
            g.m("Radius Growth", "MULTIPLY", g.value("Expansion", prop="expansion"), p),
        ),
        g.m("Ignite Then Collapse", "MULTIPLY", ignite, remaining),
    )
    width = g.m("Core Width", "MULTIPLY", width, radius)
    height = g.m("Core Height", "MULTIPLY", height, radius)
    scale = g.n("GeometryNodeTransform", "Stretch And Compress")
    g.link(geometry, scale.inputs["Geometry"])
    g.link(g.xyz("Core Proportions", width, width, height), scale.inputs["Scale"])
    pos = g.n("GeometryNodeInputPosition", "Core Position")
    axes = g.n("ShaderNodeSeparateXYZ", "Height Along Flame")
    g.link(pos.outputs[0], axes.inputs[0])
    twist = g.n(
        "ShaderNodeVectorRotate", "Accelerating Helical Distortion", rotation_type="AXIS_ANGLE"
    )
    g.link(pos.outputs[0], twist.inputs["Vector"])
    twist.inputs["Axis"].default_value = (0, 0, 1)
    angle = g.m(
        "Twist Along Height",
        "MULTIPLY",
        axes.outputs["Z"],
        g.m("Spin Accelerates", "MULTIPLY", g.m("Squared Time", "MULTIPLY", p, p), 3.5),
    )
    g.link(angle, twist.inputs["Angle"])
    # Travel along each tongue rather than rotating a rigid, leaf-shaped shell.
    # One coherent bulge and a delayed tip curl keep the low-resolution mesh legible.
    u = g.attr("charge_core_u")
    tongue = g.attr("charge_tongue")
    clock = g.m("Accelerating Roil Clock", "MULTIPLY", g.m("Roil Time", "MULTIPLY", p, p), 18)
    phase = g.m("Independent Tongue Phase", "MULTIPLY", tongue, 2.1)
    wave = g.m(
        "Energy Rises Along Tongue",
        "SUBTRACT",
        g.m("Roil Along Height", "ADD", g.m("Roil Wavelength", "MULTIPLY", u, 9), phase),
        clock,
    )
    bulge = g.m("Passing Energy Bulge", "MULTIPLY_ADD", g.m("Roil Wave", "SINE", wave), 0.18)
    bulge.node.inputs[2].default_value = 1
    curled = g.n("ShaderNodeSeparateXYZ", "Twisted Flame Coordinates")
    g.link(twist.outputs[0], curled.inputs[0])
    tip = g.m("Flexible Tongue Tips", "MULTIPLY", u, u)
    flex = g.m("Tip Curl Distance", "MULTIPLY", tip, g.m("Curl Scale", "MULTIPLY", radius, 0.32))
    curl = g.m("Tip Follows Rising Energy", "ADD", wave, 1.2)
    shaped = []
    for axis, operation in (("X", "SINE"), ("Y", "COSINE")):
        shaped.append(
            g.m(
                "Curl Tongue " + axis,
                "ADD",
                g.m("Roiling Width " + axis, "MULTIPLY", curled.outputs[axis], bulge),
                g.m(
                    "Flexible Tip " + axis,
                    "MULTIPLY",
                    flex,
                    g.m("Tip Direction " + axis, operation, curl),
                ),
            )
        )
    deform = g.n("GeometryNodeSetPosition", "Irregular Flame Silhouette")
    g.link(scale.outputs[0], deform.inputs["Geometry"])
    g.link(g.xyz("Roiling Flame Volume", *shaped, curled.outputs["Z"]), deform.inputs["Position"])
    noise = g.n("ShaderNodeTexNoise", "Roiling Flame Contour", noise_dimensions="4D")
    noise.inputs["Scale"].default_value = 3.5
    noise.inputs["Detail"].default_value = 1.0
    g.link(pos.outputs[0], noise.inputs["Vector"])
    g.link(
        g.m("Contour Motion Accelerates", "MULTIPLY", g.m("Contour Clock", "MULTIPLY", p, p), 8),
        noise.inputs["W"],
    )
    centered = g.v("Centered Contour Noise", "SUBTRACT", noise.outputs["Color"], (0.5, 0.5, 0.5))
    displacement = g.v(
        "Alive Silhouette", "SCALE", centered, g.m("Contour Amplitude", "MULTIPLY", radius, 0.18)
    )
    g.link(displacement, deform.inputs["Offset"])

    _finish(g, deform.outputs[0])
    _surface(root, core=True)
    root["vfx_parameter_keys"] = "radius,expansion,opacity,strength,dissolve,noise_scale,fade"


def ribbons(root, *, ground=False):
    layer, g, geometry = _geometry(
        root, "Ground Intake Strokes" if ground else "Converging Vortex Ribbons"
    )
    vertices, faces = [], []
    attrs = {k: [] for k in ("charge_u", "charge_side", "charge_phase", "charge_weight")}
    count, steps = (5, 9) if ground else (3, 49)
    for strand in range(count):
        phase = strand * math.tau / count + 0.13 * math.sin(strand * 7)
        for j in range(steps):
            u = j / (steps - 1)
            for side in (-1, 1):
                vertices.append((math.cos(phase) * (1 - u), math.sin(phase) * (1 - u), u))
                for key, value in zip(
                    attrs, (u, side, phase, 0.7 + 0.3 * math.sin(strand * 4 + 1))
                ):
                    attrs[key].append(value)
        for j in range(steps - 1):
            a = strand * steps * 2 + j * 2
            faces.append((a, a + 1, a + 3, a + 2))
    _mesh(layer, vertices, faces, attrs)
    for face in layer.data.polygons:
        face.use_smooth = True
    p = g.value("Charge Clock", expression=PROGRESS)
    path_t, side, phase, weight = (g.attr(k) for k in attrs)
    head = g.stage("Path Draws Toward Core", p, 0, 0.45 if ground else 0.55)
    u = g.m("Smoothly Advancing Head", "MULTIPLY", path_t, head)
    gather = g.stage("Field Contracts", p, 0.15, 0.82)
    release = g.stage("Field Collapses", p, 0.84, 1)
    remaining = g.m("Remaining Field", "SUBTRACT", 1, release)
    compression = g.m(
        "Radial Compression", "SUBTRACT", 1, g.m("Concentration", "MULTIPLY", gather, 0.55)
    )
    inverse = g.m("Distance To Core", "SUBTRACT", 1, u)
    radial_profile = g.m("Curving Toward Core", "POWER", inverse, 0.85 if ground else 1.2)
    radial_profile = g.m("Inner Radius", "ADD", radial_profile, 0.12)
    radius = g.m(
        "Field Radius",
        "MULTIPLY",
        radial_profile,
        g.m(
            "Animated Radius",
            "ADD",
            g.value("Radius", prop="radius"),
            g.m("Radius Growth", "MULTIPLY", g.value("Expansion", prop="expansion"), p),
        ),
    )
    radius = g.m(
        "Compressed Radius",
        "MULTIPLY",
        radius,
        g.m("Collapse Radius", "MULTIPLY", compression, remaining),
    )
    radius = g.m("Asymmetric Reach", "MULTIPLY", radius, weight)
    turns = g.value(
        "Intake Curvature" if ground else "Spiral Turns", default=0.95 if ground else 7.8
    )
    angle = g.m("Path Curve", "ADD", phase, g.m("Curve Along Stroke", "MULTIPLY", u, turns))
    spin = g.m(
        "Accelerating Rotation",
        "MULTIPLY",
        g.m("Squared Time", "MULTIPLY", p, p),
        2 if ground else 10,
    )
    angle = g.m("Moving Spiral", "ADD", angle, spin)
    wobble = g.m(
        "Uneven Stroke",
        "SINE",
        g.m(
            "Small Curl",
            "ADD",
            g.m("Fine Path", "MULTIPLY", u, 17),
            g.m("Moving Curl", "ADD", phase, g.m("Curl Speed", "MULTIPLY", p, 11)),
        ),
    )
    angle = g.m("Organic Spiral", "ADD", angle, g.m("Curl Amount", "MULTIPLY", wobble, 0.08))
    taper = g.m("Tapered Ends", "SINE", g.m("Half Wave Along Stroke", "MULTIPLY", path_t, math.pi))
    width = g.m("Ribbon Width", "MULTIPLY", g.value("Width", prop="width"), taper)
    width = g.m("Width Per Stroke", "MULTIPLY", width, weight)
    width = g.m("Width Builds With Stroke", "MULTIPLY", width, g.m("Stroke Growth", "SQRT", head))
    ripple = g.m(
        "Traveling Width Ripple",
        "SINE",
        g.m(
            "Ripple Motion",
            "SUBTRACT",
            g.m("Ripple Along Path", "ADD", g.m("Uneven Edge", "MULTIPLY", u, 23), phase),
            g.m("Ripple Acceleration", "MULTIPLY", g.m("Ripple Clock", "MULTIPLY", p, p), 22),
        ),
    )
    variation = g.m("Varying Stream Width", "MULTIPLY_ADD", ripple, 0.25)
    variation.node.inputs[2].default_value = 0.75
    width = g.m("Unsteady Energy Stream", "MULTIPLY", width, variation)

    side_offset = g.m("Across Ribbon", "MULTIPLY", side, width)
    angle = g.m("Ribbon Bank", "ADD", angle, side_offset)
    x = g.m("Spiral X", "MULTIPLY", radius, g.m("Cosine", "COSINE", angle))
    y = g.m("Spiral Y", "MULTIPLY", radius, g.m("Sine", "SINE", angle))
    z = g.m("Rising Flow", "MULTIPLY", g.m("Path Height", "MULTIPLY", u, u), 0 if ground else 1.55)
    z = g.m("Flow Origin", "SUBTRACT", z, 0 if ground else 0.65)
    z = g.m(
        "Bank Height",
        "ADD",
        z,
        g.m("Twisted Cross Section", "MULTIPLY", side_offset, 0.25 if ground else 1.4),
    )
    shape = g.n("GeometryNodeSetPosition", "Authored Converging Paths")
    g.link(geometry, shape.inputs["Geometry"])
    g.link(g.xyz("Three Dimensional Intake", x, y, z), shape.inputs["Position"])
    store = g.n(
        "GeometryNodeStoreNamedAttribute",
        "Preserve Moving Flow Coordinates",
        data_type="FLOAT",
        domain="POINT",
    )
    store.inputs["Name"].default_value = "charge_flow_u"
    g.link(shape.outputs[0], store.inputs["Geometry"])
    g.link(u, store.inputs["Value"])
    _finish(g, store.outputs[0])
    _surface(root)
    root["vfx_parameter_keys"] = "radius,width,expansion,strength,dissolve,noise_scale,fade"


def spiral_motes(root):
    tree = root.children[0].modifiers[0].node_group
    root["vfx_parameter_keys"] = (
        "rate,lifetime,emission_seconds,velocity,spread,randomness,spawn_radius,size,fade,strength,seed"
    )
    g = _Fields(tree, root)
    # Keep the bounded birth pool, individual age, size fade and native material.
    radius = tree.nodes["Spawn Radius"].outputs[0]
    travel = tree.nodes["Travel"].outputs[0]
    safe = g.m("Nonzero Spawn Radius", "MAXIMUM", radius, 0.001)
    phase = g.m("Gathering Travel", "DIVIDE", travel, safe)
    phase = g.m("Stop At Core", "MINIMUM", phase, 1)
    phase = g.m("Nonnegative Travel", "MAXIMUM", phase, 0)
    fraction = g.m(
        "Accelerating Convergence", "SUBTRACT", 1, g.m("Quadratic Travel", "MULTIPLY", phase, phase)
    )
    distance = g.m("Spiral Radius", "MULTIPLY", radius, fraction)
    direction = g.v(
        "Gathering Volume", "MULTIPLY", tree.nodes["Direction"].outputs[0], (1, 1, 0.45)
    )
    direction = g.v("Gather Above The Ground", "ADD", direction, (0, 0, 0.18))
    normalize = g.n("ShaderNodeVectorMath", "Normalized Gathering Volume", operation="NORMALIZE")
    g.link(direction, normalize.inputs[0])
    direction = normalize.outputs[0]
    rotate = g.n(
        "ShaderNodeVectorRotate", "Curved Gathering Trajectory", rotation_type="AXIS_ANGLE"
    )
    rotate.inputs["Axis"].default_value = (0, 0, 1)
    g.link(direction, rotate.inputs["Vector"])
    g.link(g.m("Swirl During Flight", "MULTIPLY", phase, 3.5), rotate.inputs["Angle"])
    position = g.v("Spiral Particle Position", "SCALE", rotate.outputs[0], distance)
    g.link(position, tree.nodes["Particle Motion"].inputs["Position"])
    speed = tree.nodes["Varied Velocity"].outputs[0]
    inward_speed = g.m(
        "Radial Acceleration",
        "MULTIPLY",
        g.m("Increasing Inward Speed", "MULTIPLY", speed, phase),
        -2,
    )
    inward = g.v("Inward Velocity", "SCALE", rotate.outputs[0], inward_speed)
    cross = g.v("Orbit Tangent", "CROSS_PRODUCT", rotate.outputs[0], (0, 0, -1))
    angular_speed = g.m(
        "Angular Speed", "MULTIPLY", g.m("Speed Per Radius", "DIVIDE", speed, safe), 3.5
    )
    sideways = g.v(
        "Tangential Velocity",
        "SCALE",
        cross,
        g.m("Orbit Speed", "MULTIPLY", angular_speed, distance),
    )
    tangent = g.v("Curved Trajectory Tangent", "ADD", inward, sideways)
    fallback = g.v("Stable Tip At Rest", "SCALE", rotate.outputs[0], -0.001)
    g.link(
        g.v("Leading Tip Direction", "ADD", tangent, fallback),
        tree.nodes["Aim Mote Inward"].inputs["Vector"],
    )
    birth = g.stage("Mote Ignition", tree.nodes["Bounded Individual Progress"].outputs[0], 0, 0.12)
    size = g.m(
        "Mote Birth And Lifetime Size", "MULTIPLY", tree.nodes["Particle Scale"].outputs[0], birth
    )
    g.link(size, tree.nodes["Mote Proportions"].inputs["Scale"])
    tree.nodes["Mote Proportions"].inputs[0].default_value = (0.5, 0.5, 3.8)
