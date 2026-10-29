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


def _support_weight(g, geometry):
    weight = g.m(
        "Bound Support Weight",
        "MINIMUM",
        1,
        g.m(
            "Nonnegative Support Weight",
            "MAXIMUM",
            g.tree.nodes["Intake Weight"].outputs[0]
            if g.tree.nodes.get("Intake Weight")
            else g.value("Intake Weight", 0.6),
            0,
        ),
    )
    store = g.n(
        "GeometryNodeStoreNamedAttribute",
        "Carry Support Weight To Material",
        data_type="FLOAT",
        domain="POINT",
    )
    store.inputs["Name"].default_value = "charge_support_weight"
    g.link(geometry, store.inputs["Geometry"])
    g.link(weight, store.inputs["Value"])
    return store.outputs[0]


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


def _inward_packet(g, p, u, strand, filament):
    """A broad head and tapered tail travel toward increasing path coordinates."""
    phase = g.m(
        "Unequal Intake Phase",
        "SUBTRACT",
        u,
        g.m("Path Offset", "MULTIPLY", strand, 0.173),
    )
    phase = g.m(
        "Filament Intake Stagger",
        "SUBTRACT",
        phase,
        g.m("Filament Phase Offset", "MULTIPLY", filament, 0.21),
    )
    phase = g.m(
        "Packets Accelerate Inward",
        "SUBTRACT",
        phase,
        g.m("Packet Travel", "MULTIPLY", g.m("Packet Acceleration", "MULTIPLY", p, p), 4),
    )
    phase = g.m("Repeated Intake", "FRACT", phase)
    primary = g.m(
        "Primary Intake Selection",
        "MAXIMUM",
        g.m("First Primary Intake", "LESS_THAN", strand, 0.5),
        g.m(
            "Second Primary Intake",
            "LESS_THAN",
            g.m("Primary Index Distance", "ABSOLUTE", g.m("Primary Index", "SUBTRACT", strand, 3)),
            0.5,
        ),
    )
    compression = g.m("Primary Packet Compression", "MULTIPLY_ADD", primary, 0.45)
    compression.node.inputs[2].default_value = 1
    phase = g.m("Shorter Primary Packet", "MULTIPLY", phase, compression)

    packet = g.m(
        "Inward Energy Packet",
        "MULTIPLY",
        g.stage("Packet Trailing Edge", phase, 0.02, 0.48),
        g.m("Packet Leading Edge", "SUBTRACT", 1, g.stage("Packet Head", phase, 0.58, 0.72)),
    )
    return packet, phase, primary


def _surface(root, *, core=False, ground=False):
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
        packet, packet_phase, primary = _inward_packet(
            g, p, u, attribute("charge_tongue"), attribute("charge_filament")
        )
        uneven = g.m("Uneven Packet Surface", "MULTIPLY_ADD", noise.outputs["Fac"], 0.45)
        uneven.node.inputs[2].default_value = 0.5
        hot = g.m(
            "Bright Intake Heads",
            "MULTIPLY",
            packet,
            uneven,
        )
        across = g.m(
            "Filament Center Distance",
            "SUBTRACT",
            1,
            g.m("Absolute Filament Side", "ABSOLUTE", attribute("charge_filament_side")),
        )
        center_light = g.m("Concentrated Light Within Filament", "POWER", across, 2)
        center_light = g.m("Filament Body And Vein", "MULTIPLY_ADD", center_light, 0.4)
        center_light.node.inputs[2].default_value = 0.6
        hot = g.m(
            "Narrow Painted Intake Light",
            "MULTIPLY",
            hot,
            g.m(
                "Only Primary Width Shading",
                "ADD",
                1,
                g.m(
                    "Primary Vein Difference",
                    "MULTIPLY",
                    primary,
                    g.m("Vein Below Flat Brightness", "SUBTRACT", center_light, 1),
                ),
            ),
        )

        channels = noise
        channels.name = "Advected Intake Channels"
        g.link(g.m("Slow Channel Churn", "MULTIPLY", p, 0.35), channels.inputs["W"])
        g.link(
            g.xyz(
                "Coordinates Along The Moving Intake",
                g.m("Longitudinal Channel Stretch", "MULTIPLY", packet_phase, 1.3),
                g.m(
                    "Channels Around The First Side", "MULTIPLY", attribute("charge_angle_sin"), 1.9
                ),
                g.m(
                    "Channels Around The Second Side",
                    "MULTIPLY",
                    attribute("charge_angle_cos"),
                    1.9,
                ),
            ),
            channels.inputs["Vector"],
        )
        g.link(
            g.m(
                "Intake Channel Scale",
                "MULTIPLY",
                g.value("Channel Detail", prop="noise_scale"),
                0.55,
            ),
            channels.inputs["Scale"],
        )
        channels.inputs["Detail"].default_value = 2
        painted = g.stage("Readable Flow Channels", channels.outputs["Fac"], 0.32, 0.68)
        contrast = g.value("Intake Channel Contrast", 0.65)
        painted = g.m("Channel Values", "MULTIPLY_ADD", painted, contrast)
        g.link(g.m("Unbroken Channel Body", "SUBTRACT", 1, contrast), painted.node.inputs[2])
        hot = g.m(
            "Light Follows The Advected Channels",
            "MULTIPLY",
            hot,
            g.m(
                "Only Primary Channel Values",
                "ADD",
                1,
                g.m(
                    "Primary Channel Difference",
                    "MULTIPLY",
                    primary,
                    g.m("Channel Value Difference", "SUBTRACT", painted, 1),
                ),
            ),
        )
        fraying = g.value("Intake Fraying", 0.23)
        edge_fraying = g.m(
            "Stronger Edge Fraying",
            "MULTIPLY_ADD",
            g.m("Intake Side", "ABSOLUTE", attribute("charge_filament_side")),
            0.43,
        )
        edge_fraying.node.inputs[2].default_value = 1
        fringe = g.m("Intake Fraying Threshold", "MULTIPLY", fraying, edge_fraying)
        survive = g.m("Long Wisps Survive", "GREATER_THAN", channels.outputs["Fac"], fringe)
        survive = g.m(
            "Fraying Can Be Disabled",
            "MAXIMUM",
            survive,
            g.m("Intake Fraying Off", "LESS_THAN", fraying, 1e-6),
        )
        alpha = g.m(
            "Frayed Primary Surface",
            "MULTIPLY",
            alpha,
            g.m(
                "Only Primary Fraying",
                "ADD",
                1,
                g.m(
                    "Primary Fraying Difference",
                    "MULTIPLY",
                    primary,
                    g.m("Fraying Below Full Opacity", "SUBTRACT", survive, 1),
                ),
            ),
        )
        # Three illustrated values describe volume without a glossy gradient.
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
        density = g.value("Flow Packet Density", 1.2 if ground else 1.6)
        wave = g.m(
            "Flow Bands",
            "ADD",
            g.m("Packets Along Each Stream", "MULTIPLY", u, density),
            g.m("Unequal Packet Phase", "MULTIPLY", strand, 0.2),
        )
        travel = g.m(
            "Accelerating Packet Travel",
            "MULTIPLY",
            g.m("Packet Time", "MULTIPLY", p, p),
            g.value("Inward Flow Travel", 4 if ground else 4.5),
        )
        wave = g.m(
            "Flow Moves Inward",
            "SUBTRACT",
            wave,
            g.m("Packet Clock Follows Density", "MULTIPLY", travel, density),
        )
        wave = g.m("Repeated Packets", "FRACT", wave)
        hot = g.m(
            "Packet Length",
            "MULTIPLY",
            g.stage("Packet Arrives", wave, 0.02, 0.52),
            g.m("Packet Tail", "SUBTRACT", 1, g.stage("Packet Passes", wave, 0.56, 0.70)),
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
        stored = g.stage("Stored Energy Concentration", p, 0.30, 0.84)
        brightness = g.m("Inner Compression Brightness", "MULTIPLY_ADD", stored, 0.77)
        brightness.node.inputs[2].default_value = 0.08
        energy_remaining = g.m(
            "Nucleus Energy Remaining",
            "SUBTRACT",
            1,
            g.stage("Nucleus Hands Off Energy", p, 0.88, 0.96),
        )
        g.link(
            g.m("Spend Inner White During Release", "MULTIPLY", brightness, energy_remaining),
            kernel_color.inputs[0],
        )
        # A traveling light front follows each curved sheet, rather than painting
        # a fixed white patch on its facing normals.
        nucleus_phase = g.m(
            "Stored Energy Flow Phase",
            "FRACT",
            g.m(
                "Energy Travels Into The Focus",
                "SUBTRACT",
                g.m(
                    "Unequal Stored Front Phase",
                    "ADD",
                    u,
                    g.m("Stored Sheet Phase", "MULTIPLY", attribute("charge_filament"), 0.65),
                ),
                g.m(
                    "Stored Flow Accelerates",
                    "MULTIPLY",
                    g.m("Stored Flow Time", "MULTIPLY", p, p),
                    3.5,
                ),
            ),
        )
        nucleus_front = g.m(
            "Narrow Stored Energy Front",
            "MULTIPLY",
            g.stage("Stored Front Arrives", nucleus_phase, 0.25, 0.5),
            g.m(
                "Stored Front Tapers",
                "SUBTRACT",
                1,
                g.stage("Stored Front Passes", nucleus_phase, 0.55, 0.78),
            ),
        )
        kernel_face = g.m(
            "Nucleus White Face",
            "GREATER_THAN",
            g.m("Nucleus Facing Magnitude", "ABSOLUTE", facing.outputs["Value"]),
            g.value("Nucleus White Threshold", 0.35),
        )
        vein = g.m(
            "Narrow Vein Across Curled Sheets",
            "SUBTRACT",
            1,
            g.stage(
                "Stored Vein Edges",
                g.m("Distance From Stored Vein", "ABSOLUTE", attribute("charge_filament_side")),
                0.15,
                0.5,
            ),
        )
        flow = g.m("Connected Vein With A Moving Front", "MULTIPLY_ADD", nucleus_front, 0.75)
        flow.node.inputs[2].default_value = 0.25
        stored_facing = kernel_face
        heart_values = g.m("Pressure Heart Volume Values", "MULTIPLY_ADD", cel, 1.4)
        heart_values.node.inputs[2].default_value = 0.25
        stored_facing = g.m(
            "Lit Ridges In The Pressure Heart", "MULTIPLY", stored_facing, heart_values
        )
        heart_flow = g.m(
            "Flowing Light Across The Stored Volume", "MULTIPLY_ADD", nucleus_front, 0.7
        )
        heart_flow.node.inputs[2].default_value = 0.3
        stored_facing = g.m("Moving Plasma Within The Heart", "MULTIPLY", stored_facing, heart_flow)
        kernel_face = g.m(
            "Nucleus White Patch",
            "MULTIPLY",
            kernel_face,
            g.m("Stored Vein And Front", "MULTIPLY", vein, flow),
        )
        kernel_face = g.m(
            "Stored Heart Retains Its Energy",
            "MAXIMUM",
            kernel_face,
            g.m(
                "Dense Heart With A Colored Contour",
                "MULTIPLY",
                attribute("charge_heart"),
                stored_facing,
            ),
        )
        white_amount = kernel_color.inputs[0].links[0].from_socket
        g.link(
            g.m("Restricted Nucleus White", "MULTIPLY", white_amount, kernel_face),
            kernel_color.inputs[0],
        )
        kernel_body = g.m(
            "Nucleus Blue Faces",
            "MULTIPLY_ADD",
            g.m("Nucleus Midtone Face", "GREATER_THAN", facing.outputs["Value"], 0.08),
            0.5,
        )
        g.link(g.value("Nucleus Blue Depth", 0.27), kernel_body.node.inputs[2])
        g.link(
            g.v("Nucleus Colored Pressure Body", "SCALE", color.outputs[0], kernel_body),
            kernel_color.inputs[1],
        )
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
        side = attribute("charge_filament_side")
        lane = attribute("charge_filament")
        notch_clock = g.m(
            "Advected Filament Nicks",
            "ADD",
            g.m("Nicks Along Packet", "MULTIPLY", packet_phase, 17),
            g.m("Unequal Filament Nicks", "MULTIPLY", lane, 2.4),
        )
        coverage = g.m(
            "Nicked Edge Width", "MULTIPLY_ADD", g.m("Edge Lobes", "SINE", notch_clock), 0.12
        )
        coverage.node.inputs[2].default_value = 0.88
        shift = g.m(
            "Unequal Filament Edges",
            "MULTIPLY",
            g.m("Edge Bias", "SINE", g.m("Longer Edge Lobes", "MULTIPLY", packet_phase, 9)),
            0.10,
        )
        across = g.m(
            "Distance Across Filament",
            "ABSOLUTE",
            g.m("Shifted Filament Center", "ADD", side, shift),
        )
        border = g.stage(
            "Ink Along Nicked Edge",
            g.m("Relative Filament Width", "DIVIDE", across, coverage),
            0.75,
            0.98,
        )
        edge = g.m(
            "View And Filament Boundary",
            "MAXIMUM",
            edge,
            g.m("Only Filament Ink", "MULTIPLY", border, primary),
        )
        edge = g.m("Editable Core Edge", "MULTIPLY", edge, g.value("Core Edge Contrast", 0.85))
        edge_mix = g.n("ShaderNodeMixRGB", "Dark Contour Around Luminous Paths")
        g.link(edge, edge_mix.inputs[0])
        g.link(surface_color, edge_mix.inputs[1])
        g.link(g.v("Core Ink Tint", "SCALE", color.outputs[0], 0.035), edge_mix.inputs[2])
        hierarchy = g.m(
            "Filament Value Hierarchy",
            "SUBTRACT",
            1,
            g.m("Secondary Filament Value", "MULTIPLY", lane, 0.3),
        )
        surface_color = g.v(
            "Primary And Supporting Filament Color", "SCALE", edge_mix.outputs[0], hierarchy
        )
    support = attribute("charge_support_weight")
    if core:
        support = g.m(
            "Keep The Nucleus Independent",
            "ADD",
            support,
            g.m(
                "Nucleus Ignores Support Weight",
                "MULTIPLY",
                attribute("charge_inner"),
                g.m("Remaining Support Weight", "SUBTRACT", 1, support),
            ),
        )
    # Eevee's dithered core needs solid moving sections. Reduce their cross
    # section in Geometry Nodes; only fully hidden support is cut out here.
    if core:
        support = g.m("Support Is Visible", "GREATER_THAN", support, 0)
    alpha = g.m("Supporting Layer Opacity", "MULTIPLY", alpha, support)
    emission = g.n("ShaderNodeEmission", "Native Energy Surface")
    g.link(surface_color, emission.inputs["Color"])
    radiance = g.value("Emission", prop="strength")
    if core:
        stored_light = g.m("Light Stored In The Dense Heart", "MULTIPLY", stored, energy_remaining)
        stored_light = g.m(
            "Only The Heart Stores Radiance", "MULTIPLY", stored_light, attribute("charge_heart")
        )
        front_radiance = g.m(
            "Energy Concentrates In Moving Fronts", "MULTIPLY_ADD", nucleus_front, 5
        )
        front_radiance.node.inputs[2].default_value = 2
        stored_light = g.m(
            "Light Follows The Stored Front", "MULTIPLY", stored_light, front_radiance
        )
        stored_light = g.m("Accumulating Heart Radiance", "ADD", stored_light, 1)
        radiance = g.m("Stored Pressure Becomes Light", "MULTIPLY", radiance, stored_light)
    g.link(radiance, emission.inputs["Strength"])
    transparent = g.n("ShaderNodeBsdfTransparent", "Transparent")
    surface = g.n("ShaderNodeMixShader", "Ignite And Dissipate")
    g.link(alpha, surface.inputs[0])
    g.link(transparent.outputs[0], surface.inputs[1])
    g.link(emission.outputs[0], surface.inputs[2])
    out = g.n("ShaderNodeOutputMaterial", "Output")
    g.link(surface.outputs[0], out.inputs["Surface"])


def core_shape(root):
    layer, g, geometry = _geometry(root, "Compressed Flame Core")
    vertices, faces, cross_sections, shell_sections = [], [], [], []
    core_attrs = {
        k: []
        for k in (
            "charge_core_u",
            "charge_angle_sin",
            "charge_angle_cos",
            "charge_inner",
            "charge_tongue",
            "charge_filament",
            "charge_filament_side",
            "charge_heart",
        )
    }
    # Unequal curved strands leave actual space around a small nucleus.
    # These are authored rest paths; native fields below animate compression.
    for tongue, (phase, turns, reach, rise, breadth) in enumerate(
        (
            (0.0, 1.25, 1.1, 0.75, 0.28),
            (1.35, 2.7, 0.88, 0.6, 0.09),
            (2.7, 3.5, 1.0, -0.7, 0.10),
            (3.65, 1.0, 0.88, -0.62, 0.19),
        )
    ):
        primary = tongue in (0, 3)
        # Spend more path samples on the broad silhouette, keeping the same budget.
        base, steps, sides = len(vertices), 27 if primary else 10, 6 if primary else 3

        def center(t):
            angle = phase + turns * t + 0.12 * math.sin(t * 9 + phase)
            if primary:
                angle += 0.28 * math.sin(math.tau * t) + 0.08 * math.sin(t * 18 + phase) * math.sin(
                    math.pi * t
                )
            radius = reach * (0.06 + 0.94 * (1 - t) ** 0.85)
            if primary:
                radius *= 1 + 0.14 * math.sin(t * 13 + phase) * math.sin(math.pi * t)
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
                filament = k // 3 if primary else 0
                lane_center = Vector()
                if primary:
                    a = (k % 3) * math.tau / 3 + filament * 0.9 + 0.6 * math.sin(t * 12 + filament)
                    lane_center = width * (
                        side * (-0.35, 0.5)[filament] + up * (0.35, -0.45)[filament]
                    )
                    raw = []
                    for corner in range(3):
                        angle = (
                            corner * math.tau / 3
                            + filament * 0.9
                            + 0.6 * math.sin(t * 12 + filament)
                        )
                        edge = 1 - 0.17 * math.sin(t * 23 + filament) * (
                            0.5 + 0.5 * math.cos(angle)
                        )
                        raw.append(
                            width
                            * (0.72, 0.42)[filament]
                            * edge
                            * (side * math.cos(angle) + up * math.sin(angle) * 0.65)
                        )
                    offset = raw[k % 3] - sum(raw, Vector()) / 3

                else:
                    offset = width * (side * math.cos(a) + up * math.sin(a) * 0.28)
                vertices.append(tuple(point + lane_center + offset))
                cross_sections.append(tuple(offset))
                shell_sections.append((0, 0, 0))
                for name, value in zip(
                    core_attrs,
                    (
                        t,
                        math.sin(a),
                        math.cos(a),
                        0.0,
                        float(tongue),
                        float(filament),
                        math.cos(a) if primary else 0.0,
                        0.0,
                    ),
                ):
                    core_attrs[name].append(value)
        for j in range(steps - 1):
            for k in range(sides):
                next_k = (k // 3) * 3 + (k + 1) % 3 if primary else (k + 1) % sides
                a, b = base + j * sides + k, base + j * sides + next_k
                faces.append((a, b, b + sides, a + sides))
    # Curled, unequal energy sheets leave real gaps around a shared focus.
    # Rounded lens sections provide depth from side views without solid leaf faces.
    lens = ((-1, 0), (-0.65, 0.7), (0.65, 0.7), (1, 0), (0.65, -0.7), (-0.65, -0.7))
    petals = (
        (0.0, 2.8, 0.19, 0.64, 0.09),
        (2.05, 3.3, 0.16, 0.53, 0.075),
        (4.55, 2.2, 0.12, 0.43, 0.045),
    )
    for lobe, (phase, turn, reach, rise, breadth) in enumerate(petals):
        base, steps, sides = len(vertices), 19, len(lens)

        def center(t):
            angle = phase + turn * t
            radius = reach * (0.22 + 0.78 * (1 - t) ** 0.7)
            return Vector((math.cos(angle) * radius, math.sin(angle) * radius, (t - 0.5) * rise))

        for j in range(steps):
            t = j / (steps - 1)
            profile = max(math.sin(math.pi * t), 0) ** 0.7
            angle = phase + turn * t
            radial = Vector((math.cos(angle), math.sin(angle), 0))
            tangent = (center(min(t + 0.001, 1)) - center(max(t - 0.001, 0))).normalized()
            normal = tangent.cross(radial).normalized()
            point = center(t)
            for k, (across, depth) in enumerate(lens):
                offset = profile * (radial * breadth * across + normal * 0.018 * depth)
                vertices.append(tuple(point + offset))
                cross_sections.append((0, 0, 0))
                shell_sections.append(tuple(offset))
                a = k * math.tau / sides
                for name, value in zip(
                    core_attrs, (t, math.sin(a), math.cos(a), 1.0, 6.0, lobe * 0.25, across, 0.0)
                ):
                    core_attrs[name].append(value)
        for j in range(steps - 1):
            for k in range(sides):
                a, b = base + j * sides + k, base + j * sides + (k + 1) % sides
                faces.append((a, b, b + sides, a + sides))
    # A filled, twisted pressure knot sits inside the curled shell. Its volume
    # inherits the existing storage, compression and directed-release controls.
    base, rows, sides = len(vertices), 18, 12
    for row in range(rows + 1):
        u = row / rows
        profile = max(0.02, (1 - (2 * u - 1) ** 2) ** 0.65)
        for side in range(sides):
            a = side / sides * math.tau
            angle = a + 0.9 * u
            radius = (
                0.13
                * profile
                * (1 + 0.32 * math.cos(3 * a + 2 * u) + 0.07 * math.cos(5 * a - 4 * u))
            )
            vertices.append(
                (
                    0.025 * math.sin(math.pi * u) * math.sin(6 * u) + radius * math.cos(angle),
                    0.02 * math.sin(math.pi * u) * math.cos(5 * u) + radius * math.sin(angle),
                    (u - 0.5) * 0.46,
                )
            )
            cross_sections.append((0, 0, 0))
            shell_sections.append((0, 0, 0))
            for name, value in zip(
                core_attrs,
                (
                    u,
                    math.sin(a),
                    math.cos(a),
                    1.0,
                    7.0,
                    0.45 * math.sin(a) + 0.2 * math.cos(2 * a),
                    0.0,
                    1.0,
                ),
            ):
                core_attrs[name].append(value)
    faces.append(tuple(base + side for side in reversed(range(sides))))
    for row in range(rows):
        for side in range(sides):
            a = base + row * sides + side
            b = base + row * sides + (side + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(base + rows * sides + side for side in range(sides)))
    _mesh(layer, vertices, faces, core_attrs)
    cross = layer.data.attributes.new("charge_cross", "FLOAT_VECTOR", "POINT")
    for slot, value in zip(cross.data, cross_sections):
        slot.vector = value
    shell_attr = layer.data.attributes.new("charge_shell", "FLOAT_VECTOR", "POINT")
    for slot, value in zip(shell_attr.data, shell_sections):
        slot.vector = value
    shells = g.n("GeometryNodeSetPosition", "Editable Pressure Shell Width")
    g.link(geometry, shells.inputs["Geometry"])
    g.link(
        g.v(
            "Shell Section From Its Centerline",
            "SCALE",
            g.attr("charge_shell", "FLOAT_VECTOR"),
            g.m("Shell Width From Rest", "SUBTRACT", g.value("Nucleus Shell Width", 0.22), 1),
        ),
        shells.inputs["Offset"],
    )
    geometry = shells.outputs["Geometry"]
    for face in layer.data.polygons:
        face.use_smooth = True
    p = g.value("Charge Clock", expression=PROGRESS)
    ignite = g.stage("Ignition Growth", p, 0, 0.18)
    gather = g.stage("Compression Builds", p, 0.30, 0.84)
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
    packet, _, primary = _inward_packet(
        g, p, g.attr("charge_core_u"), g.attr("charge_tongue"), g.attr("charge_filament")
    )
    main_guide = g.m(
        "One Continuous Guide Per Bundle",
        "MULTIPLY",
        g.value("Main Intake Guide Width", 0.055),
        g.m("Leading Filament Guide", "LESS_THAN", g.attr("charge_filament"), 0.5),
    )
    section = g.m(
        "Energy Heads Swell And Tails Thin",
        "MULTIPLY_ADD",
        packet,
        g.m("Main Intake Width Range", "SUBTRACT", 1.32, main_guide),
    )
    g.link(main_guide, section.node.inputs[2])
    auxiliary = g.m("Secondary Intake Paths", "SUBTRACT", 1, primary)
    guide = g.value("Auxiliary Guide Width", 0.0)
    concentrated = g.m(
        "Auxiliary Packet Volume",
        "MULTIPLY_ADD",
        g.m("Auxiliary Packet Taper", "POWER", packet, 2),
        g.m("Auxiliary Width Range", "SUBTRACT", g.value("Auxiliary Packet Width", 0.85), guide),
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
    intake_weight = g.m(
        "Bound Intake Width Weight",
        "MINIMUM",
        1,
        g.m("Nonnegative Intake Width Weight", "MAXIMUM", g.value("Intake Weight", 0.6), 0),
    )
    intake_weight = g.m(
        "Intake Gives Way To Stored Energy",
        "MULTIPLY",
        intake_weight,
        g.m(
            "Quieter Intake Under Pressure",
            "SUBTRACT",
            1,
            g.m("Stored Focus", "MULTIPLY", gather, 0.45),
        ),
    )
    section = g.m("Weight Supporting Intake Sections", "MULTIPLY", section, intake_weight)
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
    # A whole section turns and drifts together. Sampling its individual
    # vertices shears the tube, especially during late, fast rotation.
    section_offset = g.v(
        "Current Cross Section Offset",
        "SCALE",
        g.attr("charge_cross", "FLOAT_VECTOR"),
        g.m("Cross Section Scale", "MULTIPLY", section, radius),
    )
    centerline = g.v("Intake Centerline", "SUBTRACT", adjusted, section_offset)
    g.link(centerline, axes.inputs[0])
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
    seed_size = g.value("Nucleus Seed Size", 0.65)
    stored_size = g.value("Nucleus Stored Size", 2.3)
    growth = g.m(
        "Nucleus Stores Incoming Energy",
        "MULTIPLY_ADD",
        gather,
        g.m("Stored Size Range", "SUBTRACT", stored_size, seed_size),
    )
    g.link(seed_size, growth.node.inputs[2])
    growth = g.m(
        "Nucleus Growth Only",
        "ADD",
        1,
        g.m(
            "Inner Growth Difference",
            "MULTIPLY",
            g.attr("charge_inner"),
            g.m("Growth Relative To Strands", "SUBTRACT", growth, 1),
        ),
    )
    position = g.v("Stored Energy Volume", "SCALE", position, growth)
    # The stored volume flattens while the intake paths keep moving. Expanding
    # its cross section compensates for the lost height, then discharge turns
    # that compact shape into a needle without changing the outer strands.
    compression = g.m(
        "Bound Nucleus Compression",
        "MINIMUM",
        g.m("Nonnegative Nucleus Compression", "MAXIMUM", g.value("Nucleus Compression", 0.6), 0),
        0.85,
    )
    stored_tension = g.m(
        "Compression Ends As Energy Releases",
        "MULTIPLY",
        gather,
        g.m(
            "Pressure Becomes Discharge",
            "SUBTRACT",
            1,
            g.stage("Nucleus Unloads Compression", p, 0.84, 0.88),
        ),
    )
    compressed_height = g.m(
        "Stored Height Loss",
        "SUBTRACT",
        1,
        g.m("Compression Tracks Stored Energy", "MULTIPLY", stored_tension, compression),
    )
    compressed_width = g.m(
        "Stored Volume Width", "SQRT", g.m("Keep Stored Volume", "DIVIDE", 1, compressed_height)
    )
    nucleus = g.attr("charge_inner")
    sideways = g.m(
        "Nucleus Expands Sideways",
        "ADD",
        1,
        g.m(
            "Only Nucleus Width Expands",
            "MULTIPLY",
            nucleus,
            g.m("Extra Stored Width", "SUBTRACT", compressed_width, 1),
        ),
    )
    vertical = g.m(
        "Nucleus Compacts Vertically",
        "ADD",
        1,
        g.m(
            "Only Nucleus Height Compacts",
            "MULTIPLY",
            nucleus,
            g.m("Lost Stored Height", "SUBTRACT", compressed_height, 1),
        ),
    )
    compression_axes = g.xyz("Nucleus Compression Proportions", sideways, sideways, vertical)
    position = g.v(
        "Incoming Energy Pressurizes The Nucleus", "MULTIPLY", position, compression_axes
    )
    pulse = g.m(
        "Stored Energy Discharge",
        "MULTIPLY",
        g.stage("Release Pinch Begins", p, 0.84, 0.88),
        g.m("Release Pinch Ends", "SUBTRACT", 1, g.stage("Release Pinch Settles", p, 0.90, 0.96)),
    )
    pulse = g.m("Only The Nucleus Discharges", "MULTIPLY", pulse, g.attr("charge_inner"))
    pinch = g.m(
        "Nucleus Width During Discharge",
        "SUBTRACT",
        1,
        g.m("Release Width Pinch", "MULTIPLY", pulse, g.value("Release Pinch", 0.55)),
    )
    stretch = g.m(
        "Nucleus Height During Discharge", "MULTIPLY_ADD", pulse, g.value("Release Stretch", 1.4)
    )
    stretch.node.inputs[2].default_value = 1
    discharge_axes = g.xyz("Nucleus Discharge Proportions", pinch, pinch, stretch)
    position = g.v("Stored Energy Becomes A Short Needle", "MULTIPLY", position, discharge_axes)
    # Discharge travels toward local +Z rather than stretching equally into
    # both ends. Orient the controller toward the receiving weapon or spell.
    position = g.v(
        "Stored Energy Travels Into The Release",
        "ADD",
        position,
        g.xyz(
            "Forward Discharge",
            0,
            0,
            g.m(
                "Release Travel",
                "MULTIPLY",
                pulse,
                g.m("Radius Relative Travel", "MULTIPLY", radius, 0.8),
            ),
        ),
    )
    g.link(position, deform.inputs["Position"])
    noise = g.n("ShaderNodeTexNoise", "Roiling Flame Contour", noise_dimensions="4D")
    noise.inputs["Scale"].default_value = 3.5
    noise.inputs["Detail"].default_value = 1.0
    g.link(centerline, noise.inputs["Vector"])
    g.link(
        g.m("Contour Motion Accelerates", "MULTIPLY", g.m("Contour Clock", "MULTIPLY", p, p), 8),
        noise.inputs["W"],
    )
    centered = g.v("Centered Contour Noise", "SUBTRACT", noise.outputs["Color"], (0.5, 0.5, 0.5))
    displacement = g.v(
        "Alive Silhouette", "SCALE", centered, g.m("Contour Amplitude", "MULTIPLY", radius, 0.035)
    )
    # Scaling the nucleus includes its contour displacement, so a zero seed
    # remains collapsed rather than leaving a small cloud of noisy vertices.
    displacement = g.v("Stored Energy Contour", "SCALE", displacement, growth)
    displacement = g.v("Compressed Nucleus Contour", "MULTIPLY", displacement, compression_axes)
    g.link(
        g.v("Discharging Contour", "MULTIPLY", displacement, discharge_axes),
        deform.inputs["Offset"],
    )

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
            g.stage("Nucleus Release Window", p, 0.88, 0.96),
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
    _finish(g, _support_weight(g, hide.outputs[0]))
    _surface(root, core=True)
    root["vfx_parameter_keys"] = "radius,expansion,opacity,strength,dissolve,noise_scale,fade"


def ribbons(root, *, ground=False):
    layer, g, geometry = _geometry(
        root, "Ground Intake Strokes" if ground else "Converging Vortex Ribbons"
    )
    vertices, faces = [], []
    attrs = {k: [] for k in ("charge_u", "charge_side", "charge_phase", "charge_weight")}
    count, steps = (3, 15) if ground else (3, 41)
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
        "Intake Curvature" if ground else "Spiral Turns", default=0.95 if ground else 2.4
    )
    angle = g.m("Path Curve", "ADD", phase, g.m("Curve Along Stroke", "MULTIPLY", u, turns))
    spin = g.m(
        "Accelerating Rotation",
        "MULTIPLY",
        g.m("Squared Time", "MULTIPLY", p, p),
        g.value("Field Rotation", 2 if ground else 3.8),
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
    elevation = g.m(
        "Unequal Intake Elevation", "SINE", g.m("Intake Elevation Phase", "ADD", phase, 0.7)
    )
    z = g.m(
        "Paths Arrive At The Core",
        "MULTIPLY",
        inverse,
        g.m(
            "Intake Height",
            "MULTIPLY",
            elevation,
            g.value("Intake Vertical Reach", 0 if ground else 0.9),
        ),
    )
    z = g.m(
        "Bank Height",
        "ADD",
        z,
        g.m("Twisted Cross Section", "MULTIPLY", side_offset, 0.25 if ground else 1.4),
    )
    if ground:
        z = g.m(
            "Ground Intake Joins The Core",
            "ADD",
            z,
            g.m(
                "Ground Stroke Lifts Toward Its Head",
                "MULTIPLY",
                g.m("Curved Ground Approach", "MULTIPLY", u, u),
                g.value("Ground Intake Lift", 0.8),
            ),
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
    _finish(g, _support_weight(g, store.outputs[0]))
    _surface(root, ground=ground)
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
