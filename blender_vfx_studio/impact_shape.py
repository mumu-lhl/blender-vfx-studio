"""Author private Impact meshes; the saved native graphs handle playback."""

import math

import bmesh
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
        if isinstance(source, (int, float, tuple)):
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
    """A compact nucleus and four unequal narrow spokes, lasting three frames."""
    sphere = bmesh.new()
    try:
        bmesh.ops.create_icosphere(sphere, subdivisions=1, radius=0.22)
        sphere.verts.ensure_lookup_table()
        sphere.verts.index_update()
        vertices = [(v.co.x, v.co.y * 0.85, v.co.z * 0.65) for v in sphere.verts]
        faces = [tuple(v.index for v in face.verts) for face in sphere.faces]
    finally:
        sphere.free()
    heat = [1.0] * len(vertices)
    uv = [(0, 0)] * len(vertices)
    for lobe, (direction, height, width) in enumerate(
        (
            ((1, 0.15, 0.2), 0.55, 0.035),
            ((-1, 0.3, 0.15), 0.32, 0.025),
            ((-0.2, -1, 0.1), 0.4, 0.02),
            ((0.8, -0.6, 0.15), 0.7, 0.04),
        )
    ):
        axis = Vector(direction).normalized()
        side = axis.cross(Vector((0, 0, 1))).normalized()
        up = axis.cross(side).normalized()
        base, steps, sides = len(vertices), 3, 3
        for i in range(steps + 1):
            u = i / steps
            center = axis * (height * u) + side * (0.06 * math.sin(math.pi * u))
            radius = width * max(math.sin(math.pi * u), 0)
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
    """Three pressure plumes, four fine ejections and two trailing curls."""
    vertices, faces, paths = [], [], []
    widths, directions, lobes = [], [], []
    phases, births, heat, uv = [], [], [], []
    steps = {"LOW": 12, "MEDIUM": 24, "HIGH": 40}[quality]
    radial_steps = {"LOW": 18, "MEDIUM": 26, "HIGH": 38}[quality]

    def vertex(path, width, direction, role, index, birth, u, v):
        vertices.append(tuple(path + width))
        paths.append(tuple(path))
        widths.append(tuple(width))
        directions.append(tuple(direction))
        lobes.append(role)
        phases.append(index * 1.8)
        births.append(birth)
        heat.append((0.95, 0.8, 0.4)[role] * (1 - u))
        uv.append((u, v))

    def rows(base, count, sides, *, closed=False):
        for i in range(count - 1):
            for j in range(sides if closed else sides - 1):
                a = base + i * sides + j
                b = base + i * sides + (j + 1) % sides
                faces.append((a, b, b + sides, a + sides))

    # Spend the mesh budget on a few rounded, curled masses instead of seven
    # equally sampled tubes. Cross sections follow each authored path tangent.
    for index, (angle, reach, bend, lift, breadth, depth, front, back, birth) in enumerate(
        (
            (0.75, 0.75, -0.45, 0.55, 0.45, 0.85, 0.75, 0.8, 0.0),
            (3.55, 0.55, 0.32, -0.45, 0.32, 0.75, 0.55, 0.65, 0.035),
            (5.1, 0.65, -0.3, 0.4, 0.28, 0.8, 1.2, 0.8, 0.065),
        )
    ):
        direction = Vector((math.cos(angle), math.sin(angle), 0))
        sideways = Vector((-direction.y, direction.x, 0))
        base, sides = len(vertices), 8 if quality == "HIGH" else 6

        def center(u):
            point = direction * (u * reach) + sideways * (
                bend * math.sin(math.pi * u) * (0.2 + 0.8 * u)
            )
            point.z = lift * math.sin(math.pi * u) + 0.08 * reach * u
            return point

        peak = front / (front + back)
        for i in range(radial_steps + 1):
            u = i / radial_steps
            path = center(u)
            tangent = (center(min(u + 0.001, 1)) - center(max(u - 0.001, 0))).normalized()
            side = tangent.cross(Vector((0, 0, 1))).normalized()
            up = tangent.cross(side).normalized()
            profile = (u / peak) ** front * ((1 - u) / (1 - peak)) ** back
            profile *= 1 + 0.12 * math.sin(u * 12 + index * 2)
            for j in range(sides):
                cross = j / sides * math.tau + 0.2 * math.sin(u * 5 + index)
                width = breadth * profile * (side * math.cos(cross) + up * math.sin(cross) * depth)
                vertex(
                    path, width, direction, 0, index, birth, u, angle / math.tau + j / sides * 0.1
                )
        rows(base, radial_steps + 1, sides, closed=True)

    fine_steps = {"LOW": 10, "MEDIUM": 16, "HIGH": 24}[quality]
    for index, (angle, reach, bend, lift, breadth, birth) in enumerate(
        (
            (1.75, 1.9, -0.10, 0.16, 0.035, 0.0),
            (2.65, 1.2, 0.12, -0.12, 0.025, 0.02),
            (4.2, 1.6, -0.08, 0.18, 0.03, 0.045),
            (5.85, 1.1, 0.15, -0.1, 0.02, 0.07),
        ),
        3,
    ):
        direction = Vector((math.cos(angle), math.sin(angle), 0))
        side = Vector((-direction.y, direction.x, 0))
        base = len(vertices)
        for i in range(fine_steps + 1):
            u = i / fine_steps
            path = direction * (u * reach) + side * (bend * math.sin(math.pi * u))
            path.z = lift * math.sin(math.pi * u) + 0.08 * u
            profile = 3.2 * u**0.45 * (1 - u) ** 1.45
            for v in (-1, 0, 1):
                width = side * (v * breadth * profile)
                width.z = (1 - abs(v)) * breadth * profile * 0.4
                vertex(path, width, direction, 1, index, birth, u, (v + 1) / 2)
        rows(base, fine_steps + 1, 3)

    for index, (angle, reach, bend, lift, breadth, birth) in enumerate(
        (
            (-2.3, 0.55, -0.18, 0.22, 0.09, 0.07),
            (2.85, 0.42, 0.18, -0.32, 0.08, 0.11),
        ),
        7,
    ):
        direction = Vector((math.cos(angle), math.sin(angle), 0))
        side = Vector((-direction.y, direction.x, 0))
        base = len(vertices)
        for i in range(steps + 1):
            u = i / steps
            path = direction * (u * reach) + side * (bend * math.sin(math.pi * u))
            path.z = lift * math.sin(math.pi * u) + 0.12 * u
            profile = max(math.sin(math.pi * u), 0) ** 0.7
            for v in (-1, -0.18, 0.25, 1):
                tooth = 1 + 0.22 * math.sin(u * 19 + index) * abs(v)
                width = side * (v * breadth * profile * tooth)
                width.z = (1 - abs(v)) * breadth * profile * 0.7
                vertex(path, width, direction, 2, index, birth, u, (v + 1) / 2)
        rows(base, steps + 1, 4)
    layer = _mesh(
        root,
        vertices,
        faces,
        {
            "impact_path": ("FLOAT_VECTOR", paths),
            "impact_width": ("FLOAT_VECTOR", widths),
            "impact_direction": ("FLOAT_VECTOR", directions),
            "impact_lobe": ("FLOAT", lobes),
            "impact_phase": ("FLOAT", phases),
            "impact_birth": ("FLOAT", births),
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
    primary = graph.math("Pressure Shell Part", "LESS_THAN", lobe, 0.5)
    fine = graph.math(
        "Fine Ejection Part",
        "MULTIPLY",
        graph.math("Not Pressure Body", "GREATER_THAN", lobe, 0.5),
        graph.math("Not Auxiliary Curl", "LESS_THAN", lobe, 1.5),
    )
    delay = graph.attribute("impact_birth")
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
    speed = graph.math("Faster Fine Ejection", "MULTIPLY", fine, 0.45)
    speed = graph.math(
        "Gas Drag Difference",
        "SUBTRACT",
        speed,
        graph.math("Slower Pressure Body", "MULTIPLY", primary, 0.1),
    )
    speed = graph.math("Role Travel Speed", "ADD", speed, 1)
    distance = graph.math("Separate Ejection Speeds", "MULTIPLY", distance, speed)
    jitter_phase = graph.math(
        "Lobe Seed", "ADD", graph.attribute("impact_phase"), graph.value("Seed", "seed")
    )
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
    late = graph.math("After Pressure Peak", "SUBTRACT", local, 0.24, clamp=True)
    late = graph.math("Peeling Shell", "MULTIPLY", late, 1.35, clamp=True)
    difference = graph.math("Shell / Tongue Drift", "SUBTRACT", late, local)
    difference = graph.math("Only Peel Main Shell", "MULTIPLY", difference, primary)
    drift = graph.math("Independent Release Motion", "ADD", local, difference)
    drift = graph.math("Detached Jet Tails", "MULTIPLY", drift, distance)
    drift = graph.vector(
        "Outward Jet Drift", "SCALE", graph.attribute("impact_direction", "FLOAT_VECTOR"), drift
    )
    path = graph.vector("Separating Ejection", "ADD", path, drift)
    frequency = graph.math("Slower Pressure Curl", "MULTIPLY", primary, 8)
    frequency = graph.math("Role Flow Frequency", "SUBTRACT", 14, frequency)
    phase = graph.math("Jet Flow Clock", "MULTIPLY", local, frequency)
    phase = graph.math("Independent Jet Phase", "ADD", phase, graph.attribute("impact_phase"))
    pulse = graph.math("Flow Along Jet", "MULTIPLY", graph.attribute("impact_u"), 9)
    pulse = graph.math("Traveling Pressure", "SUBTRACT", pulse, phase)
    pulse = graph.math("Pressure Pulses", "SINE", pulse)
    pulse = graph.math("Pulse Depth", "MULTIPLY", pulse, 0.22)
    pulse = graph.math("Living Cross Section", "ADD", pulse, 0.78)
    side = graph.vector(
        "Jet Bend Direction",
        "CROSS_PRODUCT",
        graph.attribute("impact_direction", "FLOAT_VECTOR"),
        (0, 0, 1),
    )
    sway = graph.math("Jet Curl", "SINE", phase)
    middle = graph.math("Jet Middle Phase", "MULTIPLY", graph.attribute("impact_u"), math.pi)
    middle = graph.math("Stable Jet Ends", "SINE", middle)
    sway = graph.math("Middle Curl", "MULTIPLY", sway, middle)
    sway = graph.math("Growing Curl", "MULTIPLY", sway, local)
    sway = graph.math("Curl Range", "MULTIPLY", sway, 0.22)
    sway = graph.math("Curl Distance", "MULTIPLY", sway, distance)
    path = graph.vector(
        "Bending Ejection", "ADD", path, graph.vector("Curl Offset", "SCALE", side, sway)
    )
    rise = graph.math("Fine Ejection Snap", "MULTIPLY", fine, 0.075)
    rise = graph.math("Role Pressure Rise", "SUBTRACT", 0.13, rise)
    pressure = graph.math("Pressure Rise", "DIVIDE", local, rise, clamp=True)
    shrink = graph.math("Width Loss", "MULTIPLY", local, graph.value("Fade", "fade"))
    loss = graph.math("Pressure Retains Volume", "MULTIPLY", primary, 0.55)
    loss = graph.math("Role Width Loss", "SUBTRACT", 1, loss)
    shrink = graph.math("Separate Volume And Streak Loss", "MULTIPLY", shrink, loss)
    shrink = graph.math("Width Remaining", "SUBTRACT", 1, shrink)
    inflate = graph.math("Pressure Expansion", "MULTIPLY", primary, local)
    inflate = graph.math("Pressure Expansion Amount", "MULTIPLY", inflate, 0.4)
    inflate = graph.math("Retained Pressure Mass", "ADD", inflate, 1)
    shrink = graph.math("Volume Before Fragmentation", "MULTIPLY", shrink, inflate)
    size = graph.math("Body Breadth", "MULTIPLY", graph.value("Size", "size"), 8)
    size = graph.math("Pressurized Breadth", "MULTIPLY", size, pressure)
    size = graph.math("Releasing Breadth", "MULTIPLY", size, shrink)
    size = graph.math("Pulsing Breadth", "MULTIPLY", size, pulse)
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
    spent = graph.math("Core Life / Fade", "MULTIPLY", local, graph.value("Core Fade", "fade"))
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
    birth = graph.node("ShaderNodeAttribute", "Pressure Birth", attribute_name="impact_birth")
    age = graph.math(
        "Material Time Since Birth", "SUBTRACT", progress, birth.outputs["Fac"], clamp=True
    )
    progress = graph.math(
        "Material Local Age",
        "DIVIDE",
        age,
        graph.math("Material Life Span", "SUBTRACT", 1, birth.outputs["Fac"]),
        clamp=True,
    )
    part = graph.node("ShaderNodeAttribute", "Pressure Part", attribute_name="impact_lobe")
    primary = graph.math("Main Pressure Shell", "LESS_THAN", part.outputs["Fac"], 0.5)
    auxiliary = graph.math("Auxiliary Curl Part", "GREATER_THAN", part.outputs["Fac"], 1.5)
    fade = graph.value("Jet Fade", "fade")
    axes = graph.node("ShaderNodeSeparateXYZ", "Along / Across Jet")
    graph.connect(uv.outputs["UV"], axes.inputs[0])
    normal = graph.node("ShaderNodeNewGeometry", "Pressure Face Normal")
    facing = graph.node("ShaderNodeVectorMath", "Illustrated Light", operation="DOT_PRODUCT")
    graph.connect(normal.outputs["Normal"], facing.inputs[0])
    facing.inputs[1].default_value = (-0.36, -0.48, 0.8)
    shade = graph.node("ShaderNodeMapRange", "Rounded Jet Shade", interpolation_type="SMOOTHSTEP")
    graph.connect(facing.outputs["Value"], shade.inputs["Value"])
    shade.inputs["From Min"].default_value, shade.inputs["From Max"].default_value = 0.35, 0.85
    shade.inputs["To Min"].default_value, shade.inputs["To Max"].default_value = 1, 0
    contrast = graph.node("ShaderNodeValue", "Side Contrast")
    contrast.outputs[0].default_value = 0.6
    shadow = graph.math(
        "Editable Shadow Contrast", "MULTIPLY", shade.outputs[0], contrast.outputs[0]
    )
    dark = graph.vector("Deep Orange Edge", "SCALE", tint.outputs[0], 0.055)
    body = graph.node("ShaderNodeMixRGB", "Two Tone Pressure")
    graph.connect(shadow, body.inputs[0])
    graph.connect(tint.outputs[0], body.inputs[1])
    graph.connect(dark, body.inputs[2])
    cooling = graph.math("Pressure Heat Spent", "SUBTRACT", progress, 0.2, clamp=True)
    cooling = graph.math("Pressure Cooling Speed", "MULTIPLY", cooling, 3.5, clamp=True)
    cooling = graph.math("Pressure Body Cools First", "MULTIPLY", cooling, primary)
    cooling = graph.math("Editable Pressure Cooling", "MULTIPLY", cooling, fade)
    cooling = graph.math("Pressure Color Loss", "MULTIPLY", cooling, 0.9)
    heat_left = graph.math("Pressure Color Remaining", "SUBTRACT", 1, cooling)
    rim = graph.node("ShaderNodeMapRange", "Red Edge Gradient", interpolation_type="SMOOTHSTEP")
    graph.connect(axes.outputs["X"], rim.inputs["Value"])
    rim.inputs["From Min"].default_value, rim.inputs["From Max"].default_value = 0.5, 0.9
    rim_color = graph.node("ShaderNodeVectorMath", "Red Orange Rim", operation="MULTIPLY")
    graph.connect(tint.outputs[0], rim_color.inputs[0])
    rim_color.inputs[1].default_value = (0.45, 0.2, 0.3)
    bands = graph.node("ShaderNodeMixRGB", "Orange / Red Edge")
    graph.connect(rim.outputs[0], bands.inputs[0])
    graph.connect(body.outputs[0], bands.inputs[1])
    graph.connect(rim_color.outputs[0], bands.inputs[2])
    core_ramp = graph.node(
        "ShaderNodeMapRange", "Hot Core Gradient", interpolation_type="SMOOTHSTEP"
    )
    graph.connect(axes.outputs["X"], core_ramp.inputs["Value"])
    core_ramp.inputs["From Min"].default_value, core_ramp.inputs["From Max"].default_value = (
        0.025,
        0.16,
    )
    core_ramp.inputs["To Min"].default_value, core_ramp.inputs["To Max"].default_value = 1, 0
    core = core_ramp.outputs[0]
    spent = graph.math("After Peak Light", "SUBTRACT", progress, 0.16, clamp=True)
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
    stretch.inputs[1].default_value = (2.2, 10, 1)
    graph.connect(stretch.outputs[0], noise.inputs["Vector"])
    streak = graph.math("Fine Flow Fibers", "MULTIPLY", axes.outputs["Y"], 100)
    streak = graph.math(
        "Bending Fibers",
        "ADD",
        streak,
        graph.math("Flow Distortion", "MULTIPLY", noise.outputs["Fac"], 17),
    )
    streak = graph.math(
        "Radial Flow Detail",
        "ADD",
        streak,
        graph.math("Along Fiber", "MULTIPLY", axes.outputs["X"], 12),
    )
    streak = graph.math(
        "Advect Fine Fibers",
        "SUBTRACT",
        streak,
        graph.math("Fiber Clock", "MULTIPLY", progress, 12),
    )
    streak = graph.math("Fiber Bands", "SINE", streak)
    streak = graph.math("Positive Fiber Range", "MULTIPLY", streak, 0.5)
    streak = graph.math("Normalized Fibers", "ADD", streak, 0.5)
    detail = graph.node("ShaderNodeValue", "Flow Detail Contrast")
    detail.outputs[0].default_value = 0.45
    brush = graph.math("Fiber Darkness", "SUBTRACT", 1, streak)
    brush = graph.math("Editable Flow Contrast", "MULTIPLY", brush, detail.outputs[0])
    brush = graph.math("Preserve Body Color", "SUBTRACT", 1, brush)
    graph.connect(
        graph.vector("Pressure Flow Detail", "SCALE", body.outputs[0], brush), bands.inputs[1]
    )
    graph.connect(graph.math("Advecting Flow", "MULTIPLY", progress, 1.5), noise.inputs["W"])
    release_start = graph.math("Pressure Holds Its Mass", "MULTIPLY", primary, 0.1)
    release_start = graph.math(
        "Auxiliary Curl Delay",
        "ADD",
        release_start,
        graph.math("Curl Holds Briefly", "MULTIPLY", auxiliary, 0.12),
    )
    release_start = graph.math("Role Breakup Start", "ADD", release_start, 0.18)
    release = graph.math("After Main Punch", "SUBTRACT", progress, release_start, clamp=True)
    rate = graph.math("Pressure Breakup Difference", "MULTIPLY", primary, 1.25)
    rate = graph.math(
        "Curl Breakup Difference",
        "ADD",
        rate,
        graph.math("Curl Breakup Rate", "MULTIPLY", auxiliary, 1.1),
    )
    rate = graph.math("Role Dissipation Rate", "SUBTRACT", 2.6, rate)
    release = graph.math("Jet Dissipation", "MULTIPLY", release, rate)
    release = graph.math("Editable Dissipation", "MULTIPLY", release, fade)
    tear = graph.math("Beyond Compression Core", "GREATER_THAN", axes.outputs["X"], 0.22)
    core_release = graph.math("Release Compression", "SUBTRACT", progress, 0.15, clamp=True)
    core_release = graph.math("Core Breakup Stage", "MULTIPLY", core_release, 5, clamp=True)
    core_release = graph.math("Editable Core Breakup", "MULTIPLY", core_release, fade)
    region = graph.math("Body / Spent Core", "MAXIMUM", tear, core_release)
    angle = graph.math("Pressure Angle", "MULTIPLY", axes.outputs["Y"], math.tau)
    focus = graph.math("Main Jet Center", "SUBTRACT", angle, 0.75)
    focus = graph.math("Main Jet Distance", "ABSOLUTE", focus)
    focus = graph.math("Main Jet Span", "DIVIDE", focus, 0.32)
    focus = graph.math("Main Jet Weight", "SUBTRACT", 1, focus, clamp=True)
    focus = graph.math("Protect Main Jet", "MULTIPLY", focus, primary)
    focus = graph.math("Never Preserve Spent Core", "MULTIPLY", focus, tear)
    focus = graph.math("Main Jet Density", "MULTIPLY", focus, 0.14)
    cutoff = graph.math("Subordinate Flow Density", "SUBTRACT", 0.36, focus)
    cutoff = graph.math(
        "Keep Young Pressure Solid",
        "SUBTRACT",
        cutoff,
        graph.math("Pressure Density Support", "MULTIPLY", primary, 0.14),
    )
    taper = graph.node("ShaderNodeMapRange", "Outer Tongue Taper", interpolation_type="SMOOTHSTEP")
    graph.connect(axes.outputs["X"], taper.inputs["Value"])
    taper.inputs["From Min"].default_value, taper.inputs["From Max"].default_value = 0.38, 0.98
    taper.inputs["To Max"].default_value = 0.12
    cutoff = graph.math("Pointed Flow Ends", "ADD", cutoff, taper.outputs[0])
    tear = graph.math("Torn Flow Cutoff", "MULTIPLY", region, cutoff)
    cutoff = graph.math("Flow Then Release", "ADD", tear, release)
    visible = graph.math("Remaining Jet Pieces", "GREATER_THAN", noise.outputs["Fac"], cutoff)
    distance = graph.math("Distance To Burning Edge", "SUBTRACT", noise.outputs["Fac"], cutoff)
    edge = graph.node("ShaderNodeMapRange", "Burning Edge Width", interpolation_type="SMOOTHSTEP")
    graph.connect(distance, edge.inputs["Value"])
    edge.inputs["From Max"].default_value = 0.035
    edge.inputs["To Min"].default_value, edge.inputs["To Max"].default_value = 1, 0
    cooling = graph.math("After Edge Flash", "SUBTRACT", progress, 0.28, clamp=True)
    cooling = graph.math("Edge Cooling", "MULTIPLY", cooling, 3, clamp=True)
    cooling = graph.math("Editable Edge Cooling", "MULTIPLY", cooling, fade)
    cooling = graph.math("Remaining Edge Heat", "SUBTRACT", 1, cooling)
    edge_heat = graph.math("Hot Edge Then Embers", "MULTIPLY", edge.outputs[0], cooling)
    edge_weight = graph.math("Pressure Edge Is Subordinate", "MULTIPLY", primary, 0.6)
    edge_weight = graph.math("Role Edge Heat", "SUBTRACT", 1, edge_weight)
    edge_heat = graph.math("Narrow Pressure Edge Light", "MULTIPLY", edge_heat, edge_weight)
    color_edge = graph.node("ShaderNodeMixRGB", "Hot Torn Edge")
    graph.connect(edge_heat, color_edge.inputs[0])
    graph.connect(color.outputs[0], color_edge.inputs[1])
    color_edge.inputs[2].default_value = (1, 0.65, 0.12, 1)
    facing = graph.node("ShaderNodeVectorMath", "View Facing", operation="DOT_PRODUCT")
    graph.connect(normal.outputs["Normal"], facing.inputs[0])
    graph.connect(normal.outputs["Incoming"], facing.inputs[1])
    facing = graph.math("Both Sides Facing", "ABSOLUTE", facing.outputs["Value"])
    band = graph.node("ShaderNodeMapRange", "Rim Width", interpolation_type="SMOOTHSTEP")
    graph.connect(facing, band.inputs["Value"])
    band.inputs["From Min"].default_value, band.inputs["From Max"].default_value = 0.3, 0.85
    band.inputs["To Min"].default_value, band.inputs["To Max"].default_value = 1, 0
    contrast = graph.node("ShaderNodeValue", "Rim Contrast")
    contrast.outputs[0].default_value = 0.85
    rim = graph.math("Editable Silhouette", "MULTIPLY", band.outputs[0], contrast.outputs[0])
    outlined = graph.node("ShaderNodeMixRGB", "Orange Silhouette")
    graph.connect(rim, outlined.inputs[0])
    graph.connect(color_edge.outputs[0], outlined.inputs[1])
    graph.connect(dark, outlined.inputs[2])
    hot = graph.math("Pressure Hot Center", "SUBTRACT", axes.outputs["X"], 0.4)
    hot = graph.math("Pressure Center Distance", "ABSOLUTE", hot)
    hot = graph.math("Pressure Center Width", "DIVIDE", hot, 0.45)
    hot = graph.math("Inner Pressure Heat", "SUBTRACT", 1, hot, clamp=True)
    front = graph.node("ShaderNodeMapRange", "Pressure Inner Face", interpolation_type="SMOOTHSTEP")
    graph.connect(facing, front.inputs["Value"])
    front.inputs["From Min"].default_value, front.inputs["From Max"].default_value = 0.35, 0.95
    hot = graph.math("Warm Facing Volume", "MULTIPLY", hot, front.outputs[0])
    hot = graph.math("Only Pressure Has Warm Interior", "MULTIPLY", hot, primary)
    hot = graph.math("Pressure Interior Weight", "MULTIPLY", hot, 0.8)
    warm = graph.node("ShaderNodeMixRGB", "Editable Tint To Pressure Heat")
    warm.inputs[0].default_value = 0.4
    graph.connect(tint.outputs[0], warm.inputs[1])
    warm.inputs[2].default_value = (1, 0.94, 0.72, 1)
    volume = graph.node("ShaderNodeMixRGB", "Hot Pressure Volume")
    graph.connect(hot, volume.inputs[0])
    graph.connect(outlined.outputs[0], volume.inputs[1])
    graph.connect(warm.outputs[0], volume.inputs[2])
    graph.connect(
        graph.vector("Cooling Complete Pressure Color", "SCALE", volume.outputs[0], heat_left),
        emission.inputs["Color"],
    )
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
    progress = tree.nodes["Ring Controls"].outputs["Progress"]
    remaining = graph.math("Pressure Life Remaining", "SUBTRACT", 1, progress)
    eased = graph.math(
        "Fast Pressure Front", "SUBTRACT", 1, graph.math("Pressure Drag", "POWER", remaining, 3)
    )
    difference = graph.math("Pressure Acceleration", "SUBTRACT", eased, progress)
    ease = graph.node("ShaderNodeValue", "Pressure Ease")
    ease.outputs[0].default_value = 0.75
    difference = graph.math("Editable Pressure Ease", "MULTIPLY", difference, ease.outputs[0])
    clock = graph.math("Pressure Clock", "ADD", progress, difference)
    graph.connect(clock, tree.nodes["Expansion Over Life"].inputs[1])
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
