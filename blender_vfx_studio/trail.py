"""Explicit animation sampling and native, time-interpolated ribbon playback."""

import math

import bpy
from mathutils import Vector

from . import core, particle
from .nodes import ACTIVE, PROGRESS, TIME_PROPS, drive, node
from .parameters import TRAIL_PARAMETERS


def sample(context, source, bone, first, last, step):
    if (
        source is None
        or source.name not in context.scene.objects
        or core.resolve(source) is not None
    ):
        raise ValueError("Choose a source object in this scene outside the VFX hierarchy")
    if bone and (source.type != "ARMATURE" or bone not in source.pose.bones):
        raise ValueError("Choose an existing pose bone on the source armature")
    if any(type(v) is not int for v in (first, last, step)) or not (
        -100000 <= first < last <= 100000 and step >= 1 and (last - first) % step == 0
    ):
        raise ValueError("Use an increasing frame range exactly divisible by a positive step")
    if (last - first) // step + 1 > 2048:
        raise ValueError("Trail sampling is limited to 2048 points; increase the step")
    scene = context.scene
    frame, subframe = scene.frame_current, scene.frame_subframe
    points = []
    try:
        for current in range(first, last + 1, step):
            scene.frame_set(current)
            evaluated = source.evaluated_get(context.evaluated_depsgraph_get())
            matrix = evaluated.matrix_world
            position = matrix @ evaluated.pose.bones[bone].head if bone else matrix.translation
            if not all(math.isfinite(v) and abs(v) <= 1e8 for v in position):
                raise ValueError(
                    "Source animation contains an invalid or excessively large position"
                )
            points.append(tuple(position))
    finally:
        scene.frame_set(frame, subframe=subframe)
    return points


def mesh_data(points, uid):
    mesh = bpy.data.meshes.new("VFX • Baked Ribbon Samples")
    mesh["vfx_id"] = uid
    mesh.from_pydata(
        [p for p in points for _ in range(2)],
        [],
        [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(len(points) - 1)],
    )
    side = mesh.attributes.new("vfx_side", "FLOAT_VECTOR", "POINT")
    previous = Vector((1, 0, 0))
    for i in range(len(points)):
        tangent = Vector(points[min(i + 1, len(points) - 1)]) - Vector(points[max(0, i - 1)])
        cross = tangent.cross(Vector((0, 0, 1)))
        if cross.length < 1e-6:
            cross = tangent.cross(Vector((0, 1, 0)))
        direction = cross.normalized() if cross.length > 1e-6 else previous
        if direction.dot(previous) < 0:
            direction = -direction
        previous = direction
        side.data[2 * i].vector = -direction
        side.data[2 * i + 1].vector = direction
    mesh.update()
    return mesh


def create(context, source, bone="", first=1, last=25, step=1):
    points = sample(
        context, source, bone, first, last, step
    )  # No mutation until sampling succeeds.
    root, collection = core._controller(
        context, "Ribbon Trail", "trail.ribbon", "LOW", TRAIL_PARAMETERS, {}
    )
    root.location = (0, 0, 0)  # Samples use world space; controller may be transformed afterwards.
    root["start"], root["duration"] = float(first), float(last - first)
    root["vfx_source"] = source
    root["vfx_bone"] = bone
    root["vfx_bake_first"], root["vfx_bake_last"], root["vfx_bake_step"] = first, last, step
    root["vfx_samples"] = len(points)
    mesh = mesh_data(points, root["vfx_id"])
    layer = bpy.data.objects.new("VFX • Ribbon Layer", mesh)
    core._tag(layer, root["vfx_id"], "layer")
    collection.objects.link(layer)
    layer.parent = root
    mat = particle.material(root)
    mesh.materials.append(mat)
    geometry(layer, root)
    core.select(context, root)
    return root


def layer_for(root):
    layers = [
        o
        for o in root.children_recursive
        if o.get("vfx_id") == root["vfx_id"] and o.get("vfx_role") == "layer" and o.type == "MESH"
    ]
    if len(layers) != 1:
        raise ValueError("Trail requires one unambiguous ribbon layer")
    return layers[0]


def rebake(context, root):
    root = core.resolve(root)
    if root is None or root["vfx_module"] != "trail.ribbon":
        raise ValueError("Select a ribbon trail")
    layer = layer_for(root)
    old = layer.data
    if old.get("vfx_id") != root["vfx_id"] or old.users != 1:
        raise ValueError("Ribbon mesh must be private before rebaking")
    points = sample(
        context,
        root.get("vfx_source"),
        root.get("vfx_bone", ""),
        root["vfx_bake_first"],
        root["vfx_bake_last"],
        root["vfx_bake_step"],
    )
    # Convert world samples to the layer's current local space, retaining controller transforms.
    if abs(layer.matrix_world.determinant()) < 1e-10:
        raise ValueError("Ribbon transform is singular; restore nonzero scale before rebaking")
    inverse = layer.matrix_world.inverted()
    mesh = mesh_data([inverse @ Vector(p) for p in points], root["vfx_id"])
    for mat in old.materials:
        mesh.materials.append(mat)
    layer.data = mesh
    root["vfx_samples"] = len(points)
    bpy.data.meshes.remove(old)
    core.select(context, root)


def geometry(obj, root):
    tree = bpy.data.node_groups.new("VFX • Sampled Ribbon Playback", "GeometryNodeTree")
    tree["vfx_id"] = root["vfx_id"]
    for direction in ("INPUT", "OUTPUT"):
        tree.interface.new_socket(
            name="Geometry", in_out=direction, socket_type="NodeSocketGeometry"
        )
    link = tree.links.new
    inp = node(tree, "NodeGroupInput", "Baked Samples", -1500, 800)
    out = node(tree, "NodeGroupOutput", "Output", 1800, 800)
    counter = [0]

    def math_node(operation, a, b=0):
        counter[0] += 1
        n = node(
            tree,
            "ShaderNodeMath",
            f"{operation} {counter[0]}",
            -900 + counter[0] * 80,
            -300,
            operation=operation,
        )
        for socket, source in zip(n.inputs, (a, b)):
            if isinstance(source, (int, float)):
                socket.default_value = source
            else:
                link(source, socket)
        return n.outputs[0]

    def value(name, expression, props):
        n = node(tree, "ShaderNodeValue", name, -1500, -100 * len(tree.nodes))
        drive(n.outputs[0], "default_value", root, expression, props)
        return n.outputs[0]

    progress = value("Progress", PROGRESS, TIME_PROPS)
    count = value("Last Sample", "max(n-1,1)", {"n": "vfx_samples"})
    head = math_node("MULTIPLY", progress, count)
    tail = math_node(
        "MAXIMUM",
        math_node(
            "SUBTRACT",
            head,
            math_node(
                "MULTIPLY", count, value("Trail Length", "min(max(p,0.001),1)", {"p": "length"})
            ),
        ),
        0,
    )
    index = node(tree, "GeometryNodeInputIndex", "Ribbon Vertex", -1500, 300).outputs[0]
    original = math_node("FLOOR", math_node("DIVIDE", index, 2))
    clamped = math_node("MINIMUM", math_node("MAXIMUM", original, tail), head)
    low = math_node("FLOOR", clamped)
    fraction = math_node("SUBTRACT", clamped, low)
    parity = math_node("MODULO", index, 2)
    low_index = math_node("ADD", math_node("MULTIPLY", low, 2), parity)
    high_index = math_node(
        "ADD",
        math_node("MULTIPLY", math_node("MINIMUM", math_node("ADD", low, 1), count), 2),
        parity,
    )
    position = node(tree, "GeometryNodeInputPosition", "Sample Position", -1500, 100).outputs[0]
    attr = node(
        tree,
        "GeometryNodeInputNamedAttribute",
        "Ribbon Side",
        -1500,
        -100,
        data_type="FLOAT_VECTOR",
    )
    attr.inputs["Name"].default_value = "vfx_side"

    def interpolate(field, label):
        sockets = []
        for name, sample_index in (("Lower", low_index), ("Upper", high_index)):
            n = node(
                tree,
                "GeometryNodeSampleIndex",
                label + name,
                400,
                len(tree.nodes) * 30,
                data_type="FLOAT_VECTOR",
                domain="POINT",
            )
            link(inp.outputs["Geometry"], n.inputs["Geometry"])
            link(field, n.inputs["Value"])
            link(sample_index, n.inputs["Index"])
            sockets.append(n.outputs["Value"])
        mix = node(
            tree,
            "ShaderNodeMix",
            label + " Interpolate",
            800,
            len(tree.nodes) * 30,
            data_type="VECTOR",
        )
        link(fraction, mix.inputs[0])
        vectors = [s for s in mix.inputs if s.type == "VECTOR"]
        link(sockets[0], vectors[-2])
        link(sockets[1], vectors[-1])
        return next(s for s in mix.outputs if s.type == "VECTOR")

    center = interpolate(position, "Center")
    side = interpolate(attr.outputs["Attribute"], "Side")
    width = value("Half Width", "max(w,0.001)*0.5", {"w": "width"})
    fade = value("Fade", "p", {"p": "fade"})
    width = math_node(
        "MULTIPLY", width, math_node("SUBTRACT", 1, math_node("MULTIPLY", progress, fade))
    )
    scale = node(tree, "ShaderNodeVectorMath", "Ribbon Width", 1000, 200, operation="SCALE")
    link(side, scale.inputs[0])
    link(width, scale.inputs["Scale"])
    offset = node(tree, "ShaderNodeVectorMath", "Ribbon Position", 1200, 300, operation="ADD")
    link(center, offset.inputs[0])
    link(scale.outputs[0], offset.inputs[1])
    setpos = node(tree, "GeometryNodeSetPosition", "Time Interpolated Ribbon", 1400, 800)
    link(inp.outputs["Geometry"], setpos.inputs["Geometry"])
    link(offset.outputs[0], setpos.inputs["Position"])
    hide = node(tree, "GeometryNodeDeleteGeometry", "Outside Lifetime", 1600, 800, domain="POINT")
    link(setpos.outputs[0], hide.inputs["Geometry"])
    active = value("Active", ACTIVE, TIME_PROPS)
    link(math_node("LESS_THAN", active, 0.5), hide.inputs["Selection"])
    link(hide.outputs[0], out.inputs["Geometry"])
    obj.modifiers.new("VFX • Ribbon Playback", "NODES").node_group = tree
