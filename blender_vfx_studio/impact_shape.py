"""Author private Impact meshes; the saved native graphs handle playback."""

import math

import bpy
from mathutils import Vector

from . import core
from .nodes import ACTIVE, PROGRESS, TIME_PROPS, drive, node


class _Nodes:
    def __init__(self, tree, root):
        self.tree, self.root, self.count = tree, root, 0

    def node(self, kind, name, **attrs):
        n = node(self.tree, kind, name, (self.count % 7) * 220, -(self.count // 7) * 200, **attrs)
        self.count += 1
        return n

    def connect(self, source, target):
        if isinstance(source, (int, float)):
            target.default_value = source
        else:
            self.tree.links.new(source, target)

    def math(self, name, operation, a, b=0, *, clamp=False):
        n = self.node("ShaderNodeMath", name, operation=operation)
        self.connect(a, n.inputs[0])
        self.connect(b, n.inputs[1])
        n.use_clamp = clamp
        return n.outputs[0]

    def value(self, name, prop=None, expression="p", properties=None):
        n = self.node("ShaderNodeValue", name)
        drive(
            n.outputs[0],
            "default_value",
            self.root,
            expression,
            properties or ({"p": prop} if prop else TIME_PROPS),
        )
        return n.outputs[0]

    def vector(self, name, operation, a, b):
        n = self.node("ShaderNodeVectorMath", name, operation=operation)
        self.connect(a, n.inputs[0])
        self.connect(b, n.inputs["Scale"] if operation == "SCALE" else n.inputs[1])
        return n.outputs[0]

    def attribute(self, name, data_type="FLOAT"):
        n = self.node("GeometryNodeInputNamedAttribute", name, data_type=data_type)
        n.inputs["Name"].default_value = name
        return n.outputs["Attribute"]


def _mesh(root, vertices, faces, attributes, uv):
    layer = root.children[0]
    previous = layer.data
    material = previous.materials[0]
    mesh = bpy.data.meshes.new("VFX • Impact Authored Mesh")
    core._tag(mesh, root["vfx_id"])
    mesh.from_pydata(vertices, [], faces)
    for name, (kind, values) in attributes.items():
        attr = mesh.attributes.new(name, kind, "POINT")
        for item, value in zip(attr.data, values):
            if kind == "FLOAT_VECTOR":
                item.vector = value
            else:
                item.value = value
    texcoords = mesh.uv_layers.new(name="Impact UV")
    for loop in mesh.loops:
        texcoords.data[loop.index].uv = uv[loop.vertex_index]
    mesh.materials.append(material)
    mesh.update()
    layer.data = mesh
    if previous.users == 0:
        bpy.data.meshes.remove(previous)
    for modifier in list(layer.modifiers):
        tree = modifier.node_group
        layer.modifiers.remove(modifier)
        if tree.users == 0:
            bpy.data.node_groups.remove(tree)
    return layer


def _geometry(root, label):
    tree = bpy.data.node_groups.new("VFX • " + label, "GeometryNodeTree")
    core._tag(tree, root["vfx_id"])
    for direction in ("INPUT", "OUTPUT"):
        tree.interface.new_socket(
            name="Geometry", in_out=direction, socket_type="NodeSocketGeometry"
        )
    graph = _Nodes(tree, root)
    source = graph.node("NodeGroupInput", "Authored Shape")
    position = graph.node("GeometryNodeSetPosition", "Impact Shape")
    graph.connect(source.outputs[0], position.inputs["Geometry"])
    hide = graph.node("GeometryNodeDeleteGeometry", "Outside Lifetime", domain="POINT")
    graph.connect(position.outputs[0], hide.inputs["Geometry"])
    graph.connect(
        graph.math("Inactive", "LESS_THAN", graph.value("Active", expression=ACTIVE), 0.5),
        hide.inputs["Selection"],
    )
    output = graph.node("NodeGroupOutput", "Output")
    graph.connect(hide.outputs[0], output.inputs[0])
    root.children[0].modifiers.new("VFX • " + label, "NODES").node_group = tree
    return graph, position.inputs["Position"]


def flash(root):
    """Three unequal, noncoplanar lobes replace five overlapping flat stars."""
    vertices, faces, heat, uv = [], [], [], []
    for lobe, (direction, height, width) in enumerate(
        (
            ((1, 0.05, 0.18), 0.95, 0.30),
            ((1, 0.45, 0.45), 0.85, 0.16),
            ((1, -0.35, 0.10), 0.65, 0.14),
        )
    ):
        axis = Vector(direction).normalized()
        side = axis.cross(Vector((0, 0, 1))).normalized()
        up = axis.cross(side).normalized()
        base, steps, sides = len(vertices), 8, 6
        for i in range(steps + 1):
            u = i / steps
            center = axis * (height * u) + side * (0.22 * u * u)
            radius = width * max(math.sin(math.pi * u), 0) ** 0.65
            for j in range(sides):
                angle = j / sides * math.tau
                ripple = 1 + 0.16 * math.sin(i * 2.3 + j * 1.7 + lobe)
                point = center + radius * ripple * (side * math.cos(angle) + up * math.sin(angle))
                vertices.append(tuple(point))
                heat.append(0.25 + 0.65 * max(math.cos(angle), 0) + 0.1 * u)
                uv.append((u, j / sides))
        for i in range(steps):
            for j in range(sides):
                a = base + i * sides + j
                b = base + i * sides + (j + 1) % sides
                faces.append((a, b, b + sides, a + sides))
    layer = _mesh(root, vertices, faces, {"vfx_spark_heat": ("FLOAT", heat)}, uv)
    for face in layer.data.polygons:
        face.use_smooth = True
    material = layer.data.materials[0]
    graph = _Nodes(material.node_tree, root)
    normal = material.node_tree.nodes["Illustrated Light"].outputs["Value"]
    lit = graph.math("Flat White Face", "GREATER_THAN", normal, 0.48)
    tint = material.node_tree.nodes["Editable Particle Color"].outputs[0]
    dark = graph.vector("Warm Shadow", "SCALE", tint, 0.12)
    color = graph.node("ShaderNodeMixRGB", "Illustrated Hit Volume")
    graph.connect(lit, color.inputs[0])
    graph.connect(dark, color.inputs[1])
    color.inputs[2].default_value = (1, 0.95, 0.8, 1)
    graph.connect(color.outputs[0], material.node_tree.nodes["Particle Emission"].inputs["Color"])
    graph, position = _geometry(root, "Hit Compression")
    progress = graph.value("Progress", expression=PROGRESS)
    remaining = graph.math(
        "Collapse",
        "SUBTRACT",
        1,
        graph.math("Editable Collapse", "MULTIPLY", progress, graph.value("Fade", "fade")),
    )
    size = graph.math("Flash Size", "MULTIPLY", graph.value("Size", "size"), 2.5)
    size = graph.math("Compression Scale", "MULTIPLY", size, remaining)
    original = graph.node("GeometryNodeInputPosition", "Lobe Shape").outputs[0]
    graph.connect(graph.vector("Compressed Lobes", "SCALE", original, size), position)
    root["vfx_parameter_keys"] = "size,fade,strength"


def jets(root, quality):
    """A torn pressure shell carries the hit, with two smaller trailing tongues."""
    vertices, faces, paths, widths, directions, lobes, heat, uv = [], [], [], [], [], [], [], []
    steps = {"LOW": 12, "MEDIUM": 24, "HIGH": 40}[quality]
    sectors = {"LOW": 32, "MEDIUM": 48, "HIGH": 64}[quality]
    rows = {"LOW": 8, "MEDIUM": 12, "HIGH": 18}[quality]
    for i in range(rows + 1):
        u = i / rows
        for j in range(sectors + 1):
            angle = j / sectors * math.tau
            reach = 0.67
            for center, span, height in (
                (0.1, 0.28, 0.55),
                (0.75, 0.32, 1.3),
                (1.6, 0.30, 0.45),
                (2.3, 0.21, 0.65),
                (3.1, 0.32, 0.4),
                (3.95, 0.25, 0.75),
                (4.6, 0.3, 0.5),
                (5.5, 0.24, 0.65),
            ):
                delta = abs((angle - center + math.pi) % math.tau - math.pi)
                reach += max(1 - delta / span, 0) * height
            sweep = angle + 0.4 * u * u
            direction = Vector((math.cos(sweep), math.sin(sweep), 0))
            radial = u * 0.65 * (0.7 + 0.3 * reach)
            bulge = 0.65 * math.sin(math.pi * u) * (1 + 0.14 * math.cos(angle * 3))
            path = Vector((direction.x * radial, direction.y * radial, u * 0.35 * reach + bulge))
            profile = u**0.85
            width = direction * (profile * 0.8 * reach**1.3)
            vertices.append(tuple(path + width))
            paths.append(tuple(path))
            widths.append(tuple(width))
            directions.append(tuple(direction))
            lobes.append(0)
            heat.append(0.95 * (1 - u))
            uv.append((u, j / sectors))
    for i in range(rows):
        for j in range(sectors):
            a = i * (sectors + 1) + j
            faces.append((a, a + 1, a + sectors + 2, a + sectors + 1))
    for lobe, (angle, reach, bend, lift, breadth) in enumerate(
        (
            (-2.3, 0.55, -0.18, 0.22, 0.09),
            (2.85, 0.42, 0.18, -0.32, 0.08),
        ),
        1,
    ):
        direction = Vector((math.cos(angle), math.sin(angle), 0))
        side = Vector((-direction.y, direction.x, 0))
        base = len(vertices)
        for i in range(steps + 1):
            u = i / steps
            path = direction * (u * reach) + side * (bend * math.sin(math.pi * u))
            path.z = lift * math.sin(math.pi * u) + 0.12 * lobe * u
            outline = (
                (0, 0),
                (0.15, 0.8),
                (0.23, 0.3),
                (0.34, 1),
                (0.44, 0.4),
                (0.58, 0.65),
                (0.68, 0.15),
                (0.8, 0.3),
                (1, 0),
            )
            left, right = next((a, b) for a, b in zip(outline, outline[1:]) if a[0] <= u <= b[0])
            fraction = (u - left[0]) / (right[0] - left[0])
            profile = left[1] + fraction * (right[1] - left[1])
            for v in (-1, -0.18, 0.25, 1):
                tooth = 1 + 0.38 * math.sin(u * (23 if v > 0 else 31) + lobe) * abs(v)
                width = side * (v * breadth * profile * tooth)
                width.z = (1 - abs(v)) * breadth * profile * 0.7
                vertices.append(tuple(path + width))
                paths.append(tuple(path))
                directions.append(tuple(direction))
                widths.append(tuple(width))
                lobes.append(lobe)
                heat.append((0.95 if lobe == 0 else 0.55 if lobe < 3 else 0.3) * (1 - u))
                uv.append((u, (v + 1) / 2))
        for i in range(steps):
            for j in range(3):
                a = base + i * 4 + j
                faces.append((a, a + 4, a + 5, a + 1))
    layer = _mesh(
        root,
        vertices,
        faces,
        {
            "impact_path": ("FLOAT_VECTOR", paths),
            "impact_width": ("FLOAT_VECTOR", widths),
            "impact_direction": ("FLOAT_VECTOR", directions),
            "impact_lobe": ("FLOAT", lobes),
            "impact_u": ("FLOAT", [value[0] for value in uv]),
            "vfx_spark_heat": ("FLOAT", heat),
        },
        uv,
    )
    for face in layer.data.polygons:
        face.use_smooth = True
    layer.data.update()
    graph, position = _geometry(root, "Torn Impact Pressure Shell")
    progress = graph.value("Progress", expression=PROGRESS)
    lobe = graph.attribute("impact_lobe")
    delay = graph.math("Different Jet Starts", "MULTIPLY", lobe, 0.025)
    local = graph.math("Jet Age", "SUBTRACT", progress, delay, clamp=True)
    local = graph.math(
        "Jet Lifetime",
        "DIVIDE",
        local,
        graph.math("Remaining Jet Interval", "SUBTRACT", 1, delay),
        clamp=True,
    )
    remaining = graph.math("Remaining Life", "SUBTRACT", 1, local)
    ease = graph.math(
        "Fast Ejection", "SUBTRACT", 1, graph.math("Drag Cube", "POWER", remaining, 3)
    )
    clock = graph.math("Linear / Eased Difference", "SUBTRACT", ease, local)
    clock = graph.math("Motion Ease", "MULTIPLY", clock, graph.value("Motion Ease", "motion_ease"))
    clock = graph.math("Ejection Clock", "ADD", local, clock)
    distance = graph.math(
        "Ejection Seconds", "MULTIPLY", clock, graph.value("Motion Seconds", "motion_seconds")
    )
    distance = graph.math(
        "Ejection Distance", "MULTIPLY", distance, graph.value("Velocity", "velocity")
    )
    distance = graph.math(
        "Initial Reach", "ADD", distance, graph.value("Spawn Radius", "spawn_radius")
    )
    stretch = graph.math("Relative Stretch", "MULTIPLY", graph.value("Stretch", "stretch"), 0.25)
    distance = graph.math("Jet Reach", "MULTIPLY", distance, stretch)
    jitter_phase = graph.math("Lobe Seed", "ADD", lobe, graph.value("Seed", "seed"))
    jitter = graph.math(
        "Reach Variation", "SINE", graph.math("Seed Phase", "MULTIPLY", jitter_phase, 2.73)
    )
    jitter = graph.math("Variation Range", "MULTIPLY", jitter, 0.16)
    jitter = graph.math("Randomness", "MULTIPLY", jitter, graph.value("Randomness", "randomness"))
    distance = graph.math(
        "Unequal Reach", "MULTIPLY", distance, graph.math("Reach Factor", "ADD", 1, jitter)
    )
    path = graph.vector(
        "Jet Centerline", "SCALE", graph.attribute("impact_path", "FLOAT_VECTOR"), distance
    )
    late = graph.math("After Pressure Peak", "SUBTRACT", local, 0.4, clamp=True)
    late = graph.math("Peeling Shell", "MULTIPLY", late, 1.8, clamp=True)
    primary = graph.math("Pressure Shell Part", "LESS_THAN", lobe, 0.5)
    difference = graph.math("Shell / Tongue Drift", "SUBTRACT", late, local)
    difference = graph.math("Only Peel Main Shell", "MULTIPLY", difference, primary)
    drift = graph.math("Independent Release Motion", "ADD", local, difference)
    drift = graph.math("Detached Jet Tails", "MULTIPLY", drift, distance)
    drift = graph.vector(
        "Outward Jet Drift", "SCALE", graph.attribute("impact_direction", "FLOAT_VECTOR"), drift
    )
    path = graph.vector("Separating Ejection", "ADD", path, drift)
    pressure = graph.math("Pressure Rise", "DIVIDE", local, 0.12, clamp=True)
    shrink = graph.math("Width Loss", "MULTIPLY", local, graph.value("Fade", "fade"))
    shrink = graph.math("Width Remaining", "SUBTRACT", 1, shrink)
    size = graph.math("Body Breadth", "MULTIPLY", graph.value("Size", "size"), 8)
    size = graph.math("Pressurized Breadth", "MULTIPLY", size, pressure)
    size = graph.math("Releasing Breadth", "MULTIPLY", size, shrink)
    width = graph.vector(
        "Jet Cross Section", "SCALE", graph.attribute("impact_width", "FLOAT_VECTOR"), size
    )
    combined = graph.vector("Curved Jet Body", "ADD", path, width)
    flatten = graph.node("ShaderNodeCombineXYZ", "Editable Depth")
    flatten.inputs["X"].default_value = flatten.inputs["Y"].default_value = 1
    graph.connect(
        graph.math(
            "Depth Fraction",
            "SUBTRACT",
            1,
            graph.math("Planar Amount", "MULTIPLY", graph.value("Planar", "planar"), 1),
        ),
        flatten.inputs["Z"],
    )
    graph.connect(
        graph.vector("Depth Shaped Jets", "MULTIPLY", combined, flatten.outputs[0]), position
    )
    core = graph.math("Compression Vertices", "LESS_THAN", graph.attribute("impact_u"), 0.22)
    core = graph.math("Only Main Compression", "MULTIPLY", core, primary)
    spent = graph.math("Core Life / Fade", "MULTIPLY", progress, graph.value("Core Fade", "fade"))
    spent = graph.math("Core Fully Spent", "GREATER_THAN", spent, 0.52)
    selection = graph.math("Spent Inner Pole", "MULTIPLY", core, spent)
    remove = graph.node("GeometryNodeDeleteGeometry", "Remove Spent Compression", domain="POINT")
    graph.connect(graph.tree.nodes["Outside Lifetime"].outputs[0], remove.inputs["Geometry"])
    graph.connect(selection, remove.inputs["Selection"])
    graph.connect(remove.outputs[0], graph.tree.nodes["Output"].inputs[0])
    root["vfx_parameter_keys"] = (
        "seed,motion_seconds,velocity,randomness,spawn_radius,size,fade,strength,stretch,planar,motion_ease"
    )
    _erode(root)


def _erode(root):
    material = root.children[0].data.materials[0]
    material.surface_render_method = "DITHERED"
    material.node_tree.animation_data_clear()
    material.node_tree.nodes.clear()
    graph = _Nodes(material.node_tree, root)
    tint = graph.node("ShaderNodeCombineXYZ", "Editable Particle Color")
    for index in range(3):
        drive(tint.inputs[index], "default_value", root, "p", {"p": f"color_{index}"})
    uv = graph.node("ShaderNodeTexCoord", "Impact UV")
    progress = graph.value("Jet Progress", expression=PROGRESS)
    fade = graph.value("Jet Fade", "fade")
    axes = graph.node("ShaderNodeSeparateXYZ", "Along / Across Jet")
    graph.connect(uv.outputs["UV"], axes.inputs[0])
    normal = graph.node("ShaderNodeNewGeometry", "Pressure Face Normal")
    facing = graph.node("ShaderNodeVectorMath", "Illustrated Light", operation="DOT_PRODUCT")
    graph.connect(normal.outputs["Normal"], facing.inputs[0])
    facing.inputs[1].default_value = (-0.36, -0.48, 0.8)
    shadow = graph.math("Single Shadow Tone", "LESS_THAN", facing.outputs["Value"], 0.78)
    contrast = graph.node("ShaderNodeValue", "Side Contrast")
    contrast.outputs[0].default_value = 0.85
    shadow = graph.math("Editable Shadow Contrast", "MULTIPLY", shadow, contrast.outputs[0])
    dark = graph.vector("Deep Orange Edge", "SCALE", tint.outputs[0], 0.055)
    body = graph.node("ShaderNodeMixRGB", "Two Tone Pressure")
    graph.connect(shadow, body.inputs[0])
    graph.connect(tint.outputs[0], body.inputs[1])
    graph.connect(dark, body.inputs[2])
    rim = graph.math("Outer Pressure Rim", "GREATER_THAN", axes.outputs["X"], 0.67)
    rim_color = graph.node("ShaderNodeVectorMath", "Red Orange Rim", operation="MULTIPLY")
    graph.connect(tint.outputs[0], rim_color.inputs[0])
    rim_color.inputs[1].default_value = (0.45, 0.2, 0.3)
    bands = graph.node("ShaderNodeMixRGB", "Orange / Red Edge")
    graph.connect(rim, bands.inputs[0])
    graph.connect(body.outputs[0], bands.inputs[1])
    graph.connect(rim_color.outputs[0], bands.inputs[2])
    core = graph.math("Compact Hot Core", "LESS_THAN", axes.outputs["X"], 0.22)
    spent = graph.math("After Peak Light", "SUBTRACT", progress, 0.24, clamp=True)
    spent = graph.math("Spend White Light", "MULTIPLY", spent, 5, clamp=True)
    spent = graph.math("Editable Light Release", "MULTIPLY", spent, fade)
    core = graph.math(
        "Remaining White Core",
        "MULTIPLY",
        core,
        graph.math("White Remaining", "SUBTRACT", 1, spent),
    )
    color = graph.node("ShaderNodeMixRGB", "Hot Core / Orange Body")
    graph.connect(core, color.inputs[0])
    graph.connect(bands.outputs[0], color.inputs[1])
    color.inputs[2].default_value = (1, 0.93, 0.78, 1)
    emission = graph.node("ShaderNodeEmission", "Particle Emission")
    graph.connect(color.outputs[0], emission.inputs["Color"])
    graph.connect(graph.value("Emission", "strength"), emission.inputs["Strength"])
    noise = graph.node("ShaderNodeTexNoise", "Jet Surface Breakup", noise_dimensions="4D")
    noise.inputs["Scale"].default_value = 2.8
    noise.inputs["Detail"].default_value = 1
    stretch = graph.node("ShaderNodeVectorMath", "Along Flow Noise", operation="MULTIPLY")
    graph.connect(uv.outputs["UV"], stretch.inputs[0])
    stretch.inputs[1].default_value = (0.4, 10, 1)
    graph.connect(stretch.outputs[0], noise.inputs["Vector"])
    brush = graph.math("Flow Tone Range", "MULTIPLY", noise.outputs["Fac"], 0.35)
    brush = graph.math("Preserve Body Color", "ADD", brush, 0.65)
    graph.connect(
        graph.vector("Pressure Flow Detail", "SCALE", body.outputs[0], brush), bands.inputs[1]
    )
    graph.connect(graph.math("Advecting Flow", "MULTIPLY", progress, 1.5), noise.inputs["W"])
    release = graph.math("After Main Punch", "SUBTRACT", progress, 0.28, clamp=True)
    release = graph.math("Jet Dissipation", "MULTIPLY", release, 1.35)
    release = graph.math("Editable Dissipation", "MULTIPLY", release, fade)
    tear = graph.math("Beyond Compression Core", "GREATER_THAN", axes.outputs["X"], 0.22)
    core_release = graph.math("Release Compression", "SUBTRACT", progress, 0.28, clamp=True)
    core_release = graph.math("Core Breakup Stage", "MULTIPLY", core_release, 5, clamp=True)
    core_release = graph.math("Editable Core Breakup", "MULTIPLY", core_release, fade)
    region = graph.math("Body / Spent Core", "MAXIMUM", tear, core_release)
    angle = graph.math("Pressure Angle", "MULTIPLY", axes.outputs["Y"], math.tau)
    focus = graph.math("Main Jet Center", "SUBTRACT", angle, 0.75)
    focus = graph.math("Main Jet Distance", "ABSOLUTE", focus)
    focus = graph.math("Main Jet Span", "DIVIDE", focus, 0.32)
    focus = graph.math("Main Jet Weight", "SUBTRACT", 1, focus, clamp=True)
    part = graph.node("ShaderNodeAttribute", "Pressure Part", attribute_name="impact_lobe")
    primary = graph.math("Main Pressure Shell", "LESS_THAN", part.outputs["Fac"], 0.5)
    focus = graph.math("Protect Main Jet", "MULTIPLY", focus, primary)
    focus = graph.math("Never Preserve Spent Core", "MULTIPLY", focus, tear)
    focus = graph.math("Main Jet Density", "MULTIPLY", focus, 0.14)
    cutoff = graph.math("Subordinate Flow Density", "SUBTRACT", 0.47, focus)
    tear = graph.math("Torn Flow Cutoff", "MULTIPLY", region, cutoff)
    cutoff = graph.math("Flow Then Release", "ADD", tear, release)
    visible = graph.math("Remaining Jet Pieces", "GREATER_THAN", noise.outputs["Fac"], cutoff)
    transparent = graph.node("ShaderNodeBsdfTransparent", "Dissipated Jet")
    mix = graph.node("ShaderNodeMixShader", "Opaque / Missing Pieces")
    graph.connect(visible, mix.inputs[0])
    graph.connect(transparent.outputs[0], mix.inputs[1])
    graph.connect(emission.outputs[0], mix.inputs[2])
    output = graph.node("ShaderNodeOutputMaterial", "Surface")
    graph.connect(mix.outputs[0], output.inputs["Surface"])


def wave(root):
    """Break the perfect circle into unequal, slightly warped pressure arcs."""
    tree = root.children[0].modifiers[0].node_group
    graph = _Nodes(tree, root)
    position = tree.nodes["Radial Position"].outputs[0]
    separate = graph.node("ShaderNodeSeparateXYZ", "Pressure Coordinates")
    graph.connect(position, separate.inputs[0])
    phase = graph.math("Broad Pressure Lobe", "MULTIPLY", separate.outputs["X"], 4.3)
    ripple = graph.math("Uneven Pressure", "SINE", phase)
    ripple = graph.math("Contour Depth", "MULTIPLY", ripple, 0.065)
    factor = graph.math("Pressure Radius Factor", "ADD", 1, ripple)
    position = graph.vector("Warped Pressure", "SCALE", position, factor)
    ellipse = graph.node("ShaderNodeCombineXYZ", "Directional Pressure Plane")
    for socket, value in zip(ellipse.inputs, (1.2, 0.73, 1)):
        socket.default_value = value
    graph.connect(
        graph.vector("Elliptical Pressure", "MULTIPLY", position, ellipse.outputs[0]),
        tree.nodes["Procedural Ring"].inputs["Position"],
    )
    material = root.children[0].data.materials[0]
    material.surface_render_method = "BLENDED"
    graph = _Nodes(material.node_tree, root)
    axes = graph.node("ShaderNodeSeparateXYZ", "Pressure UV")
    graph.connect(material.node_tree.nodes["Ring UV"].outputs["UV"], axes.inputs[0])
    phase = graph.math("Unequal Pressure Arcs", "MULTIPLY", axes.outputs["X"], 18)
    pattern = graph.math("Pressure Gaps", "SINE", phase)
    pattern = graph.math("Open Pressure Sectors", "GREATER_THAN", pattern, -0.15)
    opacity = material.node_tree.nodes["Opacity"].outputs[0]
    graph.connect(
        graph.math("Broken Pressure Surface", "MULTIPLY", opacity, pattern),
        material.node_tree.nodes["Soft Dissolve Surface"].inputs[0],
    )
