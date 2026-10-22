"""Deterministic native particle burst; no simulation state or per-frame Python."""

from .nodes import ACTIVE, PROGRESS, TIME_PROPS, drive, node


def material(root):
    import bpy

    mat = bpy.data.materials.new("VFX • Particle Emission")
    mat["vfx_id"] = root["vfx_id"]
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    emission = node(tree, "ShaderNodeEmission", "Particle Emission", 0, 0)
    out = node(tree, "ShaderNodeOutputMaterial", "Surface", 250, 0)
    for i in range(3):
        drive(emission.inputs["Color"], "default_value", root, "p", {"p": f"color_{i}"}, i)
    drive(emission.inputs["Strength"], "default_value", root, "p", {"p": "strength"})
    tree.links.new(emission.outputs[0], out.inputs["Surface"])
    return mat


def geometry(obj, root, mat, quality):
    import bpy

    tree = bpy.data.node_groups.new("VFX • Deterministic Burst", "GeometryNodeTree")
    tree["vfx_id"] = root["vfx_id"]
    tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    link = tree.links.new

    def value(name, prop, x, y, expression="p", properties=None):
        n = node(tree, "ShaderNodeValue", name, x, y)
        drive(n.outputs[0], "default_value", root, expression, properties or {"p": prop})
        return n.outputs[0]

    def math(name, operation, a, b, x, y):
        n = node(tree, "ShaderNodeMath", name, x, y, operation=operation)
        for socket, source in zip(n.inputs, (a, b)):
            if isinstance(source, (float, int)):
                socket.default_value = source
            else:
                link(source, socket)
        return n.outputs[0]

    def vector(name, operation, a, b, x, y):
        n = node(tree, "ShaderNodeVectorMath", name, x, y, operation=operation)
        link(a, n.inputs[0])
        if b is not None:
            link(b, n.inputs["Scale"] if operation == "SCALE" else n.inputs[1])
        return n.outputs[0]

    line = node(tree, "GeometryNodeMeshLine", "Burst Points", -800, 800)
    line.inputs["Offset"].default_value = (0, 0, 0)
    drive(line.inputs["Count"], "default_value", root, "min(max(floor(p),1),2048)", {"p": "count"})
    index = node(tree, "GeometryNodeInputIndex", "Particle ID", -1400, 500)
    random = node(
        tree, "FunctionNodeRandomValue", "Random Direction", -1200, 400, data_type="FLOAT_VECTOR"
    )
    next(s for s in random.inputs if s.name == "Min" and s.type == "VECTOR").default_value = (
        -1,
        -1,
        -1,
    )
    next(s for s in random.inputs if s.name == "Max" and s.type == "VECTOR").default_value = (
        1,
        1,
        1,
    )
    scalar = node(
        tree, "FunctionNodeRandomValue", "Random Variation", -1200, 100, data_type="FLOAT"
    )
    next(s for s in scalar.inputs if s.name == "Min" and s.type == "VALUE").default_value = 0.5
    next(s for s in scalar.inputs if s.name == "Max" and s.type == "VALUE").default_value = 1.5
    for n, offset in [(random, 0), (scalar, 17)]:
        link(index.outputs[0], n.inputs["ID"])
        drive(
            n.inputs["Seed"],
            "default_value",
            root,
            f"min(max(floor(p),0),1000000)+{offset}",
            {"p": "seed"},
        )
    spread = value("Spread", "spread", -1400, -200)
    radial = vector(
        "Spread Direction",
        "SCALE",
        next(s for s in random.outputs if s.type == "VECTOR"),
        spread,
        -900,
        400,
    )
    bias = node(tree, "ShaderNodeCombineXYZ", "Up Bias", -900, 100)
    link(math("Up Amount", "SUBTRACT", 1, spread, -1200, -200), bias.inputs["Z"])
    direction = vector(
        "Direction",
        "NORMALIZE",
        vector("Biased Direction", "ADD", radial, bias.outputs[0], -700, 400),
        None,
        -500,
        400,
    )
    randomness = value("Randomness", "randomness", -1200, -450)
    random_offset = math(
        "Variation Offset",
        "SUBTRACT",
        next(s for s in scalar.outputs if s.type == "VALUE"),
        1,
        -900,
        -450,
    )
    variation = math(
        "Variation",
        "ADD",
        math("Variation Amount", "MULTIPLY", random_offset, randomness, -700, -450),
        1,
        -500,
        -450,
    )
    progress = value("Progress", None, -1200, -700, PROGRESS, TIME_PROPS)
    seconds = value("Motion Seconds", "motion_seconds", -1200, -900)
    time = math("Motion Time", "MULTIPLY", progress, seconds, -900, -700)
    velocity = value("Velocity", "velocity", -700, -900)
    speed = math("Varied Velocity", "MULTIPLY", velocity, variation, -300, -450)
    distance = math("Travel", "MULTIPLY", speed, time, -100, -450)
    radius = value("Spawn Radius", "spawn_radius", -300, -700)
    distance = math("Radial Distance", "ADD", distance, radius, 100, -450)
    position = vector("Radial Motion", "SCALE", direction, distance, 300, 300)
    gravity = value("Gravity", "gravity", -700, -1100)
    fall = math(
        "Fall",
        "MULTIPLY",
        math("Time Squared", "MULTIPLY", time, time, -500, -900),
        math("Downward Gravity", "MULTIPLY", gravity, -0.5, -500, -1100),
        -200,
        -900,
    )
    offset = node(tree, "ShaderNodeCombineXYZ", "Gravity Offset", 100, -800)
    link(fall, offset.inputs["Z"])
    location = vector("Ballistic Position", "ADD", position, offset.outputs[0], 500, 300)
    setpos = node(tree, "GeometryNodeSetPosition", "Particle Motion", 700, 800)
    link(line.outputs["Mesh"], setpos.inputs["Geometry"])
    link(location, setpos.inputs["Position"])
    active = value("Active", None, 300, -1100, ACTIVE, TIME_PROPS)
    delete = node(tree, "GeometryNodeDeleteGeometry", "Outside Lifetime", 950, 800, domain="POINT")
    link(setpos.outputs["Geometry"], delete.inputs["Geometry"])
    link(math("Inactive", "LESS_THAN", active, 0.5, 500, -1100), delete.inputs["Selection"])
    ico = node(tree, "GeometryNodeMeshIcoSphere", "Particle Mesh", 700, 500)
    ico.inputs["Radius"].default_value = 1
    ico.inputs["Subdivisions"].default_value = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}[quality]
    material_node = node(tree, "GeometryNodeSetMaterial", "Particle Material", 950, 500)
    material_node.inputs["Material"].default_value = mat
    link(ico.outputs["Mesh"], material_node.inputs["Geometry"])
    size = value("Size", "size", 100, -1100)
    fade = value("Fade", "fade", 100, -1300)
    remaining = math(
        "Remaining Size",
        "SUBTRACT",
        1,
        math("Size Fade", "MULTIPLY", progress, fade, 300, -1300),
        500,
        -1300,
    )
    scale = math(
        "Particle Scale",
        "MULTIPLY",
        math("Varied Size", "MULTIPLY", size, variation, 700, -1100),
        remaining,
        900,
        -1100,
    )
    instance = node(tree, "GeometryNodeInstanceOnPoints", "Particle Instances", 1200, 800)
    link(delete.outputs["Geometry"], instance.inputs["Points"])
    link(material_node.outputs["Geometry"], instance.inputs["Instance"])
    link(scale, instance.inputs["Scale"])
    realize = node(tree, "GeometryNodeRealizeInstances", "Editable Mesh Output", 1450, 800)
    out = node(tree, "NodeGroupOutput", "Output", 1700, 800)
    link(instance.outputs["Instances"], realize.inputs["Geometry"])
    link(realize.outputs["Geometry"], out.inputs["Geometry"])
    obj.modifiers.new("VFX • Native Burst", "NODES").node_group = tree
    return tree
