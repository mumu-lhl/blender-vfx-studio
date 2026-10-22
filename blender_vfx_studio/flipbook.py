"""Native flipbook UVs and sprite lifetime; no per-frame Python."""

from .nodes import ACTIVE, PROGRESS, TIME_PROPS, drive, node


def geometry(obj, root):
    import bpy

    tree = bpy.data.node_groups.new("VFX Sprite Geometry", "GeometryNodeTree")
    tree["vfx_id"] = root["vfx_id"]
    for direction in ("INPUT", "OUTPUT"):
        tree.interface.new_socket(
            name="Geometry", in_out=direction, socket_type="NodeSocketGeometry"
        )
    inp = node(tree, "NodeGroupInput", "Original Mesh", -600, 200)
    out = node(tree, "NodeGroupOutput", "Output", 500, 200)
    scale = node(tree, "ShaderNodeCombineXYZ", "Sprite Size", -400, 0)
    scale.inputs["Z"].default_value = 1
    transform = node(tree, "GeometryNodeTransform", "Sprite Transform", -100, 200)
    active = node(tree, "ShaderNodeValue", "Active", -400, -200)
    inactive = node(tree, "ShaderNodeMath", "Inactive", -100, -200, operation="LESS_THAN")
    inactive.inputs[1].default_value = 0.5
    delete = node(tree, "GeometryNodeDeleteGeometry", "Outside Lifetime", 200, 200, domain="POINT")
    for axis, prop in [("X", "width"), ("Y", "height")]:
        drive(scale.inputs[axis], "default_value", root, "p", {"p": prop})
    drive(active.outputs[0], "default_value", root, ACTIVE, TIME_PROPS)
    link = tree.links.new
    link(inp.outputs["Geometry"], transform.inputs["Geometry"])
    link(scale.outputs[0], transform.inputs["Scale"])
    link(transform.outputs[0], delete.inputs["Geometry"])
    link(active.outputs[0], inactive.inputs[0])
    link(inactive.outputs[0], delete.inputs["Selection"])
    link(delete.outputs[0], out.inputs["Geometry"])
    obj.modifiers.new("VFX • Editable Sprite", "NODES").node_group = tree
    return tree


def shader(root, image):
    import bpy

    mat = bpy.data.materials.new("VFX • Flipbook Atlas")
    mat["vfx_id"] = root["vfx_id"]
    mat.use_nodes = True
    mat.surface_render_method = "DITHERED"
    tree = mat.node_tree
    tree.nodes.clear()
    link = tree.links.new

    def value(name, expression, properties, x, y):
        n = node(tree, "ShaderNodeValue", name, x, y)
        drive(n.outputs[0], "default_value", root, expression, properties)
        return n.outputs[0]

    def math(name, operation, a, b=0, x=0, y=0):
        n = node(tree, "ShaderNodeMath", name, x, y, operation=operation)
        for socket, source in zip(n.inputs, (a, b)):
            if isinstance(source, (int, float)):
                socket.default_value = source
            else:
                link(source, socket)
        return n.outputs[0]

    cols = value("Columns", "max(floor(p),1)", {"p": "columns"}, -1600, 600)
    rows = value("Rows", "max(floor(p),1)", {"p": "rows"}, -1600, 400)
    first = value("First", "max(floor(p),0)", {"p": "first_frame"}, -1600, 200)
    last = value("Last", "max(floor(p),0)", {"p": "last_frame"}, -1600, 0)
    progress = value("Progress", PROGRESS, TIME_PROPS, -1600, -200)
    capacity = math(
        "Last Cell",
        "SUBTRACT",
        math("Cell Count", "MULTIPLY", cols, rows, -1400, 600),
        1,
        -1200,
        600,
    )
    first = math("Clamped First", "MINIMUM", first, capacity, -1000, 400)
    last = math(
        "Clamped Last",
        "MAXIMUM",
        first,
        math("Last In Grid", "MINIMUM", last, capacity, -1200, 0),
        -1000,
        100,
    )
    count = math(
        "Frame Count", "ADD", math("Range", "SUBTRACT", last, first, -800, 200), 1, -600, 200
    )
    # Render-time frame conversion can place an exact cell boundary just below it.
    # One millionth of a cycle absorbs float32 noise, preserving subframe playback.
    progress = math("Playback Tolerance", "ADD", progress, 0.000001, -1000, -200)
    step = math(
        "Frame Step",
        "FLOOR",
        math("Playback", "MULTIPLY", progress, count, -800, -200),
        x=-600,
        y=-200,
    )
    index = math(
        "Atlas Frame",
        "MINIMUM",
        math("Frame Index", "ADD", first, step, -400, 100),
        last,
        -200,
        100,
    )
    col = math("Column", "MODULO", index, cols, 0, 300)
    row = math("Row", "FLOOR", math("Row Division", "DIVIDE", index, cols, 0, 0), x=200, y=0)
    row = math(
        "Row From Bottom", "SUBTRACT", math("Top Row", "SUBTRACT", rows, 1, 0, -200), row, 400, 0
    )
    uv = node(tree, "ShaderNodeTexCoord", "Sprite UV", 0, 600)
    xy = node(tree, "ShaderNodeSeparateXYZ", "Local UV", 200, 600)
    link(uv.outputs["UV"], xy.inputs[0])
    u = math(
        "Atlas U", "DIVIDE", math("Cell U", "ADD", xy.outputs["X"], col, 400, 500), cols, 600, 500
    )
    v = math(
        "Atlas V", "DIVIDE", math("Cell V", "ADD", xy.outputs["Y"], row, 600, 200), rows, 800, 200
    )
    coord = node(tree, "ShaderNodeCombineXYZ", "Atlas UV", 1000, 500)
    link(u, coord.inputs["X"])
    link(v, coord.inputs["Y"])
    tex = node(
        tree,
        "ShaderNodeTexImage",
        "Atlas Image",
        1200,
        500,
        image=image,
        interpolation="Closest",
        extension="CLIP",
    )
    link(coord.outputs[0], tex.inputs["Vector"])
    surface(tree, root, tex)
    return mat


def surface(tree, root, tex):
    """Shared tint, emission and alpha for atlas and sequence textures."""
    link = tree.links.new

    def value(name, expression, properties, x, y):
        n = node(tree, "ShaderNodeValue", name, x, y)
        drive(n.outputs[0], "default_value", root, expression, properties)
        return n.outputs[0]

    def math_node(name, operation, a, b, x, y):
        n = node(tree, "ShaderNodeMath", name, x, y, operation=operation)
        link(a, n.inputs[0])
        link(b, n.inputs[1])
        return n.outputs[0]

    tint = node(tree, "ShaderNodeMixRGB", "Sprite Tint", 1500, 500, blend_type="MULTIPLY")
    tint.inputs[0].default_value = 1
    for i in range(3):
        drive(tint.inputs[2], "default_value", root, "p", {"p": f"color_{i}"}, i)
    link(tex.outputs["Color"], tint.inputs[1])
    emission = node(tree, "ShaderNodeEmission", "Emission", 1750, 500)
    drive(emission.inputs["Strength"], "default_value", root, "p", {"p": "strength"})
    link(tint.outputs[0], emission.inputs["Color"])
    opacity = value("Opacity", "p", {"p": "opacity"}, 1200, 0)
    fade = value("Lifetime Fade", f"1-{PROGRESS}*f", dict(TIME_PROPS, f="fade"), 1200, -200)
    alpha = math_node("Image Alpha", "MULTIPLY", tex.outputs["Alpha"], opacity, 1500, 200)
    alpha = math_node("Lifetime Alpha", "MULTIPLY", alpha, fade, 1750, 200)
    transparent = node(tree, "ShaderNodeBsdfTransparent", "Transparent", 1750, 0)
    mix = node(tree, "ShaderNodeMixShader", "Sprite Surface", 1950, 400)
    out = node(tree, "ShaderNodeOutputMaterial", "Surface", 2150, 400)
    link(alpha, mix.inputs[0])
    link(transparent.outputs[0], mix.inputs[1])
    link(emission.outputs[0], mix.inputs[2])
    link(mix.outputs[0], out.inputs["Surface"])
