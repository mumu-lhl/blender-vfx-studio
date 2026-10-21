"""Native node and driver construction. Nothing runs per frame in Python."""

from .timing import ACTIVE, PROGRESS


def node(tree, kind, name, x, y, **attrs):
    result = tree.nodes.new(kind)
    result.name = result.label = name
    result.location = (x, y)
    for key, value in attrs.items():
        setattr(result, key, value)
    return result


def drive(owner, path, controller, expression, properties, index=None):
    curve = owner.driver_add(path) if index is None else owner.driver_add(path, index)
    driver = curve.driver
    driver.type = "SCRIPTED"
    for name, prop in properties.items():
        var = driver.variables.new()
        var.name = name
        var.type = "SINGLE_PROP"
        var.targets[0].id = controller
        var.targets[0].data_path = f'["{prop}"]'
    driver.expression = expression
    return curve


TIME_PROPS = {"s": "start", "d": "duration", "v": "speed", "l": "loop"}


def geometry(obj, controller, uid):
    import bpy

    tree = bpy.data.node_groups.new("VFX Ring Geometry", "GeometryNodeTree")
    tree["vfx_id"] = uid
    tree.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    sockets = {}
    for name, default in [
        ("Radius", 1.0),
        ("Width", 0.15),
        ("Expansion", 3.0),
        ("Progress", 0.0),
        ("Active", 1.0),
    ]:
        socket = tree.interface.new_socket(name=name, in_out="INPUT", socket_type="NodeSocketFloat")
        socket.default_value = default
        sockets[name] = socket.identifier
    inp = node(tree, "NodeGroupInput", "Ring Controls", -700, 200)
    out = node(tree, "NodeGroupOutput", "Output", 650, 200)
    pos = node(tree, "GeometryNodeInputPosition", "Original Position", -700, -80)
    normal = node(
        tree, "ShaderNodeVectorMath", "Radial Direction", -500, -80, operation="NORMALIZE"
    )
    attr = node(
        tree, "GeometryNodeInputNamedAttribute", "Inner Edge Mask", -700, -300, data_type="FLOAT"
    )
    attr.inputs["Name"].default_value = "vfx_inner"
    width = node(tree, "ShaderNodeMath", "Inner Offset", -450, -300, operation="MULTIPLY")
    expand = node(tree, "ShaderNodeMath", "Expansion Over Life", -450, 150, operation="MULTIPLY")
    radius = node(tree, "ShaderNodeMath", "Animated Radius", -250, 150, operation="ADD")
    subtract = node(tree, "ShaderNodeMath", "Ring Width", -80, -80, operation="SUBTRACT")
    clamp = node(tree, "ShaderNodeMath", "Positive Radius", 90, -80, operation="MAXIMUM")
    clamp.inputs[1].default_value = 0.001
    scale = node(tree, "ShaderNodeVectorMath", "Radial Position", 260, -80, operation="SCALE")
    setpos = node(tree, "GeometryNodeSetPosition", "Procedural Ring", 450, 200)
    hide = node(tree, "GeometryNodeDeleteGeometry", "Outside Lifetime", 450, 450, domain="POINT")
    inactive = node(tree, "ShaderNodeMath", "Inactive", 100, 450, operation="LESS_THAN")
    inactive.inputs[1].default_value = 0.5
    link = tree.links.new
    link(pos.outputs["Position"], normal.inputs[0])
    link(attr.outputs["Attribute"], width.inputs[0])
    link(inp.outputs["Width"], width.inputs[1])
    link(inp.outputs["Expansion"], expand.inputs[0])
    link(inp.outputs["Progress"], expand.inputs[1])
    link(inp.outputs["Radius"], radius.inputs[0])
    link(expand.outputs[0], radius.inputs[1])
    link(radius.outputs[0], subtract.inputs[0])
    link(width.outputs[0], subtract.inputs[1])
    link(subtract.outputs[0], clamp.inputs[0])
    link(normal.outputs["Vector"], scale.inputs[0])
    link(clamp.outputs[0], scale.inputs["Scale"])
    link(inp.outputs["Geometry"], setpos.inputs["Geometry"])
    link(scale.outputs["Vector"], setpos.inputs["Position"])
    link(inp.outputs["Active"], inactive.inputs[0])
    link(inactive.outputs[0], hide.inputs["Selection"])
    link(setpos.outputs["Geometry"], hide.inputs["Geometry"])
    link(hide.outputs["Geometry"], out.inputs["Geometry"])
    mod = obj.modifiers.new("VFX • Editable Ring", "NODES")
    mod.node_group = tree
    for name, prop in [("Radius", "radius"), ("Width", "width"), ("Expansion", "expansion")]:
        getattr(mod.properties.inputs, sockets[name]).value = controller[prop]
        drive(
            obj,
            f'modifiers["{mod.name}"].properties.inputs.{sockets[name]}.value',
            controller,
            "p",
            {"p": prop},
        )
    for name, expression in [("Progress", PROGRESS), ("Active", ACTIVE)]:
        getattr(mod.properties.inputs, sockets[name]).value = 0.0
        drive(
            obj,
            f'modifiers["{mod.name}"].properties.inputs.{sockets[name]}.value',
            controller,
            expression,
            TIME_PROPS,
        )
    return tree


def shader(controller, uid):
    import bpy

    mat = bpy.data.materials.new("VFX • Emissive Dissolve")
    mat["vfx_id"] = uid
    mat.use_nodes = True
    mat.surface_render_method = "DITHERED"
    tree = mat.node_tree
    tree.nodes.clear()
    link = tree.links.new
    out = node(tree, "ShaderNodeOutputMaterial", "Surface", 900, 100)
    mix = node(tree, "ShaderNodeMixShader", "Soft Dissolve Surface", 680, 100)
    transparent = node(tree, "ShaderNodeBsdfTransparent", "Transparent", 450, 20)
    emission = node(tree, "ShaderNodeEmission", "Emission", 450, -100)
    for index in range(3):
        drive(
            emission.inputs["Color"],
            "default_value",
            controller,
            "c",
            {"c": f"color_{index}"},
            index,
        )
    drive(emission.inputs["Strength"], "default_value", controller, "p", {"p": "strength"})
    uv = node(tree, "ShaderNodeTexCoord", "Ring UV", -900, 200)
    separate = node(tree, "ShaderNodeSeparateXYZ", "Across Width", -700, 250)
    edge = node(tree, "ShaderNodeMath", "Soft Edges", -500, 250, operation="PINGPONG")
    edge.inputs[1].default_value = 0.5
    boost = node(tree, "ShaderNodeMath", "Edge Opacity", -300, 250, operation="MULTIPLY")
    boost.inputs[1].default_value = 2.0
    flow = node(tree, "ShaderNodeVectorMath", "UV Flow", -700, -100, operation="ADD")
    drive(flow.inputs[1], "default_value", controller, f"{PROGRESS}*2", TIME_PROPS, 0)
    noise = node(tree, "ShaderNodeTexNoise", "Dissolve Noise", -500, -100)
    noise.inputs["Scale"].default_value = 8.0
    drive(noise.inputs["Scale"], "default_value", controller, "p", {"p": "noise_scale"})
    threshold = node(
        tree, "ShaderNodeMath", "Dissolve Threshold", -260, -100, operation="GREATER_THAN"
    )
    drive(threshold.inputs[1], "default_value", controller, "p", {"p": "dissolve"})
    alpha = node(tree, "ShaderNodeMath", "Edge × Noise", -50, 200, operation="MULTIPLY")
    fade = node(tree, "ShaderNodeValue", "Lifetime Fade", -50, -100)
    drive(
        fade.outputs[0], "default_value", controller, f"1-{PROGRESS}*f", dict(TIME_PROPS, f="fade")
    )
    opacity = node(tree, "ShaderNodeMath", "Opacity", 220, 200, operation="MULTIPLY")
    link(uv.outputs["UV"], separate.inputs[0])
    link(separate.outputs["Y"], edge.inputs[0])
    link(edge.outputs[0], boost.inputs[0])
    link(uv.outputs["UV"], flow.inputs[0])
    link(flow.outputs[0], noise.inputs["Vector"])
    link(noise.outputs["Fac"], threshold.inputs[0])
    link(boost.outputs[0], alpha.inputs[0])
    link(threshold.outputs[0], alpha.inputs[1])
    link(alpha.outputs[0], opacity.inputs[0])
    link(fade.outputs[0], opacity.inputs[1])
    link(opacity.outputs[0], mix.inputs[0])
    link(transparent.outputs[0], mix.inputs[1])
    link(emission.outputs[0], mix.inputs[2])
    link(mix.outputs[0], out.inputs["Surface"])
    return mat
