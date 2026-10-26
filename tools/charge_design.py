"""Authored charge shapes: native flame core, converging ribbons and spiral motes."""

import math

from mathutils import Vector

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

    def attr(self, name, data_type="FLOAT"):
        n = self.n("GeometryNodeInputNamedAttribute", name, data_type=data_type)
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


def _inward_packet(g, p, u, strand):
    """A broad head and tapered tail travel toward increasing path coordinates."""
    phase = g.m(
        "Unequal Intake Phase",
        "SUBTRACT",
        u,
        g.m("Path Offset", "MULTIPLY", strand, 0.173),
    )
    phase = g.m(
        "Packets Accelerate Inward",
        "SUBTRACT",
        phase,
        g.m("Packet Travel", "MULTIPLY", g.m("Packet Acceleration", "MULTIPLY", p, p), 4),
    )
    phase = g.m("Repeated Intake", "FRACT", phase)
    packet = g.m(
        "Inward Energy Packet",
        "MULTIPLY",
        g.stage("Packet Trailing Edge", phase, 0.02, 0.38),
        g.m("Packet Leading Edge", "SUBTRACT", 1, g.stage("Packet Head", phase, 0.58, 0.72)),
    )
    return packet, phase


def _surface(root, *, core=False):
    material = root.children[0].data.materials[0]
    material.name = "VFX • Charge Plasma Core" if core else "VFX • Charge Flow"
    tree = material.node_tree
    tree.animation_data_clear()
    tree.nodes.clear()
    g = _Fields(tree, root)
    p = g.value("Charge Clock", expression=PROGRESS)
    if core:
        alpha = g.value("Core Surface Opacity", prop="opacity")
    else:
        ignite = g.stage("Ignition", p, 0, 0.16)
        release = g.stage("Release And Break Apart", p, 0.82, 1)
        loss = g.m("Editable Fade", "MULTIPLY", release, g.value("Fade", prop="fade"))
        alpha = g.m(
            "Charge Envelope", "MULTIPLY", ignite, g.m("Opacity After Release", "SUBTRACT", 1, loss)
        )
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
    if not core:
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
        packet, packet_phase = _inward_packet(g, p, u, attribute("charge_tongue"))
        uneven = g.m("Uneven Packet Surface", "MULTIPLY_ADD", noise.outputs["Fac"], 0.45)
        uneven.node.inputs[2].default_value = 0.5
        hot = g.m(
            "Bright Intake Heads",
            "MULTIPLY",
            packet,
            uneven,
        )
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
        packet_alpha = g.m(
            "Pointed Energy Segments",
            "GREATER_THAN",
            g.m("Taper Moving Packet Width", "SUBTRACT", packet, side),
            0.08,
        )
        alpha = g.m("Separated Energy Wisps", "MULTIPLY", alpha, packet_alpha)
        hot = g.m("Flow Emphasis", "MULTIPLY", hot, 0.6)
    mix = g.n("ShaderNodeMixRGB", "Dark Body And Flowing Energy")
    g.link(hot, mix.inputs[0])
    g.link(body, mix.inputs[1])
    hot_color = g.n("ShaderNodeMixRGB", "Editable Color To Hot Light")
    hot_color.inputs[0].default_value = 0.08 if core else 0.035
    g.link(color.outputs[0], hot_color.inputs[1])
    hot_color.inputs[2].default_value = (0.9, 0.95, 1.0, 1)
    g.link(hot_color.outputs[0], mix.inputs[2])
    surface_color = mix.outputs[0]
    if core:
        inner = attribute("charge_inner")
        facing = g.n("ShaderNodeVectorMath", "Plasma Facing", operation="DOT_PRODUCT")
        g.link(normal.outputs["Normal"], facing.inputs[0])
        g.link(normal.outputs["Incoming"], facing.inputs[1])
        front = g.stage(
            "Hot Facing With Dark Silhouette",
            g.m("Two Sided Plasma Facing", "ABSOLUTE", facing.outputs["Value"]),
            0.3,
            0.8,
        )
        pressure = g.m("Pressure Concentrates Light", "MULTIPLY_ADD", gather, 0.5)
        pressure.node.inputs[2].default_value = 0.45
        spent = g.stage("Release Spends Concentrated Light", p, 0.78, 0.92)
        light_remaining = g.m("Light Left Before Debris", "SUBTRACT", 1, spent)
        pressure = g.m("Spend White Front During Release", "MULTIPLY", pressure, light_remaining)
        center_mix = g.n("ShaderNodeMixRGB", "White Heart Cyan Midtone Ink Edge")
        front = g.m(
            "Light Concentrates At Incoming Tips",
            "MULTIPLY",
            front,
            g.m(
                "Moving Intake Front",
                "MULTIPLY",
                g.stage("Intake Front Arrives", packet_phase, 0.5, 0.58),
                g.m(
                    "Intake Front Passes",
                    "SUBTRACT",
                    1,
                    g.stage("Intake Front Leaves", packet_phase, 0.64, 0.72),
                ),
            ),
        )
        g.link(g.m("Hot Front Coverage", "MULTIPLY", front, pressure), center_mix.inputs[0])
        g.link(surface_color, center_mix.inputs[1])
        leading_color = g.n("ShaderNodeMixRGB", "Narrow Moving Plasma Front")
        leading_color.inputs[0].default_value = 0.7
        g.link(color.outputs[0], leading_color.inputs[1])
        leading_color.inputs[2].default_value = (0.8, 0.98, 1, 1)
        g.link(leading_color.outputs[0], center_mix.inputs[2])
        surface_color = center_mix.outputs[0]
        kernel_color = g.n("ShaderNodeMixRGB", "Concentrated Inner Light")
        brightness = g.m("Inner Compression Brightness", "MULTIPLY_ADD", gather, 0.3)
        brightness.node.inputs[2].default_value = 0.55
        g.link(
            g.m("Spend Inner White During Release", "MULTIPLY", brightness, light_remaining),
            kernel_color.inputs[0],
        )
        g.link(color.outputs[0], kernel_color.inputs[1])
        kernel_color.inputs[2].default_value = (0.9, 0.98, 1, 1)
        core_mix = g.n("ShaderNodeMixRGB", "Light Beneath Broken Shell")
        g.link(inner, core_mix.inputs[0])
        g.link(surface_color, core_mix.inputs[1])
        g.link(kernel_color.outputs[0], core_mix.inputs[2])
        surface_color = core_mix.outputs[0]
        edge = g.m(
            "Core Silhouette Boundary",
            "SUBTRACT",
            1,
            g.stage(
                "Core Edge Transition",
                g.m("Core Two Sided Facing", "ABSOLUTE", facing.outputs["Value"]),
                0.2,
                0.7,
            ),
        )
        edge = g.m("Editable Core Edge", "MULTIPLY", edge, g.value("Core Edge Contrast", 0.85))
        edge_mix = g.n("ShaderNodeMixRGB", "Dark Contour Around Luminous Paths")
        g.link(edge, edge_mix.inputs[0])
        g.link(surface_color, edge_mix.inputs[1])
        g.link(g.v("Core Ink Tint", "SCALE", color.outputs[0], 0.035), edge_mix.inputs[2])
        surface_color = edge_mix.outputs[0]
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
    vertices, faces, cross_sections = [], [], []
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
    # Unequal curved strands leave actual space around a small nucleus.
    # These are authored rest paths; native fields below animate compression.
    for tongue, (phase, turns, reach, rise, breadth) in enumerate(
        (
            (0.0, 2.15, 1.1, 0.55, 0.20),
            (1.35, 2.7, 0.88, 0.6, 0.09),
            (2.7, 3.5, 1.0, -0.7, 0.10),
            (3.65, 1.65, 0.88, -0.45, 0.13),
            (4.8, 2.9, 0.9, 0.5, 0.08),
            (5.6, 3.8, 0.8, -0.7, 0.075),
        )
    ):
        primary = tongue in (0, 3)
        # Spend more path samples on the broad silhouette, keeping the same budget.
        base, steps, sides = len(vertices), 22 if primary else 10, 6 if primary else 3

        def center(t):
            angle = phase + turns * t + 0.12 * math.sin(t * 9 + phase)
            if primary:
                angle += 0.28 * math.sin(math.tau * t)
            radius = reach * (0.06 + 0.94 * (1 - t) ** (1.25 if primary else 0.85))
            return Vector(
                (
                    radius * math.cos(angle),
                    radius * math.sin(angle),
                    math.sin(math.pi * t) * rise * (1 - 0.4 * t),
                )
            )

        for j in range(steps):
            t = j / (steps - 1)
            point = center(t)
            tangent = (center(min(t + 0.002, 1)) - center(max(t - 0.002, 0))).normalized()
            side = tangent.cross(Vector((0, 0, 1))).normalized()
            up = tangent.cross(side).normalized()
            width = breadth * max(math.sin(math.pi * t), 0) ** 0.65 * (0.45 + 0.65 * t)
            for k in range(sides):
                a = k * math.tau / sides + 0.18 * math.sin(t * 5 + tongue)
                depth = 0.5 if primary else 0.28
                offset = width * (side * math.cos(a) + up * math.sin(a) * depth)
                vertices.append(tuple(point + offset))
                cross_sections.append(tuple(offset))
                for name, value in zip(
                    core_attrs, (t, math.sin(a), math.cos(a), 0.0, float(tongue))
                ):
                    core_attrs[name].append(value)
        for j in range(steps - 1):
            for k in range(sides):
                a, b = base + j * sides + k, base + j * sides + (k + 1) % sides
                faces.append((a, b, b + sides, a + sides))
    base, steps, sides = len(vertices), 9, 6
    for j in range(steps):
        t = j / (steps - 1)
        radius = max(math.sin(math.pi * t), 0) * 0.18
        for k in range(sides):
            a = k * math.tau / sides
            vertices.append((radius * math.cos(a), radius * math.sin(a), (t - 0.5) * 0.4))
            cross_sections.append((0, 0, 0))
            for name, value in zip(core_attrs, (t, math.sin(a), math.cos(a), 1.0, 6.0)):
                core_attrs[name].append(value)
    for j in range(steps - 1):
        for k in range(sides):
            a, b = base + j * sides + k, base + j * sides + (k + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    _mesh(layer, vertices, faces, core_attrs)
    cross = layer.data.attributes.new("charge_cross", "FLOAT_VECTOR", "POINT")
    for slot, value in zip(cross.data, cross_sections):
        slot.vector = value
    for face in layer.data.polygons:
        face.use_smooth = True
    p = g.value("Charge Clock", expression=PROGRESS)
    ignite = g.stage("Ignition Growth", p, 0, 0.18)
    gather = g.stage("Compression Builds", p, 0.45, 0.84)
    release = g.stage("Release Collapse", p, 0.84, 1)
    remaining = g.m("Remaining Shape", "SUBTRACT", 1, release)
    width = g.m(
        "Narrow Under Compression",
        "SUBTRACT",
        1,
        g.m("Compression Amount", "MULTIPLY", gather, 0.62),
    )
    height = g.m(
        "Compact Pressure Volume", "SUBTRACT", 1, g.m("Pressure Height", "MULTIPLY", gather, 0.4)
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
    pressure_width, pressure_height = width, height
    width = g.m("Core Width", "MULTIPLY", width, radius)
    height = g.m("Core Height", "MULTIPLY", height, radius)
    scale = g.n("GeometryNodeTransform", "Stretch And Compress")
    g.link(geometry, scale.inputs["Geometry"])
    g.link(g.xyz("Core Proportions", width, width, height), scale.inputs["Scale"])
    pos = g.n("GeometryNodeInputPosition", "Core Position")
    axes = g.n("ShaderNodeSeparateXYZ", "Height Along Flame")
    twist = g.n(
        "ShaderNodeVectorRotate", "Accelerating Helical Distortion", rotation_type="AXIS_ANGLE"
    )
    packet, _ = _inward_packet(g, p, g.attr("charge_core_u"), g.attr("charge_tongue"))
    main_guide = g.value("Main Intake Guide Width", 0.14)
    section = g.m(
        "Energy Heads Swell And Tails Thin",
        "MULTIPLY_ADD",
        packet,
        g.m("Main Intake Width Range", "SUBTRACT", 1.32, main_guide),
    )
    g.link(main_guide, section.node.inputs[2])
    primary = g.m(
        "Broad Intake Paths",
        "MAXIMUM",
        g.m("First Main Intake", "LESS_THAN", g.attr("charge_tongue"), 0.5),
        g.m(
            "Second Main Intake",
            "LESS_THAN",
            g.m(
                "Second Intake Distance",
                "ABSOLUTE",
                g.m("Second Intake Index", "SUBTRACT", g.attr("charge_tongue"), 3),
            ),
            0.5,
        ),
    )
    auxiliary = g.m("Secondary Intake Paths", "SUBTRACT", 1, primary)
    guide = g.value("Auxiliary Guide Width", 0.0)
    concentrated = g.m(
        "Auxiliary Packet Volume",
        "MULTIPLY_ADD",
        g.m("Auxiliary Packet Taper", "POWER", packet, 2),
        g.m("Auxiliary Width Range", "SUBTRACT", g.value("Auxiliary Packet Width", 1.32), guide),
    )
    g.link(guide, concentrated.node.inputs[2])
    section = g.m(
        "Different Main And Secondary Sections",
        "ADD",
        section,
        g.m(
            "Secondary Section Difference",
            "MULTIPLY",
            auxiliary,
            g.m("Thinner Between Energy Packets", "SUBTRACT", concentrated, section),
        ),
    )
    # The nucleus has its own pulse; the moving packet only affects intake paths.
    section = g.m(
        "Keep Nucleus Section",
        "ADD",
        section,
        g.m(
            "Only Strand Sections Pulse",
            "MULTIPLY",
            g.attr("charge_inner"),
            g.m("Nucleus Section Difference", "SUBTRACT", 0.85, section),
        ),
    )
    retained_width = g.m("Retained Strand Width", "SUBTRACT", section, pressure_width)
    retained_height = g.m("Retained Strand Depth", "SUBTRACT", section, pressure_height)
    correction = g.v(
        "Density Builds Between Strands",
        "MULTIPLY",
        g.attr("charge_cross", "FLOAT_VECTOR"),
        g.xyz(
            "Keep Cross Sections Under Pressure",
            g.m("Width Retention Scale", "MULTIPLY", retained_width, radius),
            g.m("Second Width Retention Scale", "MULTIPLY", retained_width, radius),
            g.m("Depth Retention Scale", "MULTIPLY", retained_height, radius),
        ),
    )
    adjusted = g.v("Compress Paths Without Thinning Energy", "ADD", pos.outputs[0], correction)
    g.link(adjusted, twist.inputs["Vector"])
    # Shape fields must read the adjusted section too. Otherwise a zero-width
    # strand still separates because each original vertex twists and roils
    # from a different rest position.
    g.link(adjusted, axes.inputs[0])
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
        g.m("Roil Along Height", "ADD", g.m("Roil Wavelength", "MULTIPLY", u, 6), phase),
        clock,
    )
    bulge = g.m("Passing Energy Bulge", "MULTIPLY_ADD", g.m("Roil Wave", "SINE", wave), 0.18)
    bulge.node.inputs[2].default_value = 1
    curled = g.n("ShaderNodeSeparateXYZ", "Twisted Flame Coordinates")
    g.link(twist.outputs[0], curled.inputs[0])
    tip = g.m("Flexible Tongue Tips", "MULTIPLY", u, u)
    flex = g.m("Tip Curl Distance", "MULTIPLY", tip, g.m("Curl Scale", "MULTIPLY", radius, 0.1))
    flex = g.m(
        "Restrain Inner Tip Curl",
        "MULTIPLY",
        flex,
        g.m(
            "Kernel Curl Restraint",
            "SUBTRACT",
            1,
            g.m("Inner Curl Reduction", "MULTIPLY", g.attr("charge_inner"), 0.85),
        ),
    )
    flex = g.m(
        "Tips Converge Under Pressure",
        "MULTIPLY",
        flex,
        g.m(
            "Tightening Endpoints", "SUBTRACT", 1, g.m("Endpoint Pressure", "MULTIPLY", gather, 0.6)
        ),
    )
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
    focus = g.m("Keep A Small Dense Nucleus", "MULTIPLY", g.attr("charge_inner"), 0.75)
    counter_x = g.m(
        "Nucleus Width Retained",
        "ADD",
        1,
        g.m(
            "Nucleus Width Compensation",
            "MULTIPLY",
            focus,
            g.m(
                "Relative Width Loss",
                "SUBTRACT",
                g.m("Inverse Pressure Width", "DIVIDE", 1, pressure_width),
                1,
            ),
        ),
    )
    counter_z = g.m(
        "Nucleus Height Retained",
        "ADD",
        1,
        g.m(
            "Nucleus Height Compensation",
            "MULTIPLY",
            focus,
            g.m(
                "Relative Height Loss",
                "SUBTRACT",
                g.m("Inverse Pressure Height", "DIVIDE", 1, pressure_height),
                1,
            ),
        ),
    )
    position = g.v(
        "Dense Focus Within Contracting Strands",
        "MULTIPLY",
        g.xyz("Roiling Flame Volume", *shaped, curled.outputs["Z"]),
        g.xyz("Nucleus Pressure Balance", counter_x, counter_x, counter_z),
    )
    g.link(position, deform.inputs["Position"])
    noise = g.n("ShaderNodeTexNoise", "Roiling Flame Contour", noise_dimensions="4D")
    noise.inputs["Scale"].default_value = 3.5
    noise.inputs["Detail"].default_value = 1.0
    g.link(adjusted, noise.inputs["Vector"])
    g.link(
        g.m("Contour Motion Accelerates", "MULTIPLY", g.m("Contour Clock", "MULTIPLY", p, p), 8),
        noise.inputs["W"],
    )
    centered = g.v("Centered Contour Noise", "SUBTRACT", noise.outputs["Color"], (0.5, 0.5, 0.5))
    displacement = g.v(
        "Alive Silhouette", "SCALE", centered, g.m("Contour Amplitude", "MULTIPLY", radius, 0.035)
    )
    g.link(displacement, deform.inputs["Offset"])

    breakup = g.n("ShaderNodeTexNoise", "Native Core Breakup", noise_dimensions="4D")
    g.link(pos.outputs[0], breakup.inputs["Vector"])
    g.link(g.value("Breakup Scale", prop="noise_scale"), breakup.inputs["Scale"])
    g.link(g.m("Breakup Clock", "MULTIPLY", p, 3), breakup.inputs["W"])
    erode = g.m(
        "Native Release Erosion",
        "MULTIPLY",
        g.stage("Strands Release", p, 0.82, 1),
        g.value("Breakup Fade", prop="fade"),
    )
    threshold = g.m(
        "Erosion Threshold",
        "ADD",
        g.value("Core Dissolve", prop="dissolve"),
        g.m("Release Breakup", "MULTIPLY", erode, 0.95),
    )
    kernel = g.m(
        "Kernel Starts Dissolving Later",
        "ADD",
        g.m("Kernel Base Dissolve", "MULTIPLY", g.value("Nucleus Dissolve", prop="dissolve"), 0.35),
        g.m(
            "Kernel Releases Quickly",
            "MULTIPLY",
            g.stage("Nucleus Release Window", p, 0.84, 0.94),
            g.value("Nucleus Fade", prop="fade"),
        ),
    )
    threshold = g.m(
        "Strand And Kernel Erosion",
        "ADD",
        threshold,
        g.m(
            "Only Nucleus Threshold",
            "MULTIPLY",
            g.attr("charge_inner"),
            g.m("Nucleus Threshold Difference", "SUBTRACT", kernel, threshold),
        ),
    )
    cut = g.n("GeometryNodeDeleteGeometry", "Erode Core Faces", domain="FACE")
    g.link(deform.outputs[0], cut.inputs["Geometry"])
    g.link(
        g.m("Spent Core Faces", "LESS_THAN", breakup.outputs["Fac"], threshold),
        cut.inputs["Selection"],
    )

    # Invisible nested shells can exhaust Cycles' default transparent bounce budget.
    # Remove their evaluated geometry once hidden or collapsed; keep the editable mesh.
    transparent = g.m(
        "Core Opacity Off", "LESS_THAN", g.value("Visibility Opacity", prop="opacity"), 1e-6
    )
    dissolved = g.m(
        "Core Fully Dissolved",
        "GREATER_THAN",
        g.value("Visibility Dissolve", prop="dissolve"),
        0.999999,
    )
    finished = g.m("Core Collapse Complete", "LESS_THAN", remaining, 0.35)
    invisible = g.m(
        "Core Has Finished Or Is Hidden",
        "MAXIMUM",
        finished,
        g.m("Core Hidden By Parameters", "MAXIMUM", transparent, dissolved),
    )
    hide = g.n("GeometryNodeDeleteGeometry", "Skip Invisible Core Surfaces", domain="POINT")
    g.link(cut.outputs[0], hide.inputs["Geometry"])
    g.link(invisible, hide.inputs["Selection"])
    _finish(g, hide.outputs[0])
    _surface(root, core=True)
    root["vfx_parameter_keys"] = "radius,expansion,opacity,strength,dissolve,noise_scale,fade"


def ribbons(root, *, ground=False):
    layer, g, geometry = _geometry(
        root, "Ground Intake Strokes" if ground else "Converging Vortex Ribbons"
    )
    vertices, faces = [], []
    attrs = {k: [] for k in ("charge_u", "charge_side", "charge_phase", "charge_weight")}
    count, steps = (5, 9) if ground else (3, 41)
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
    z = g.m("Rising Flow", "MULTIPLY", g.m("Path Height", "MULTIPLY", u, u), 0 if ground else 1.1)
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
    turn = g.value("Mote Intake Turn", 1.6)
    g.link(g.m("Swirl During Flight", "MULTIPLY", phase, turn), rotate.inputs["Angle"])
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
        "Angular Speed", "MULTIPLY", g.m("Speed Per Radius", "DIVIDE", speed, safe), turn
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
