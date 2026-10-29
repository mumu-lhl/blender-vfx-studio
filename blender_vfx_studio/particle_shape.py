"""Pointed native particle shapes and tip gradients for Burst particles."""

from .nodes import drive, node


def geometry(tree, root, ico, material_node, instance, scale, direction):
    link = tree.links.new
    shape = node(tree, "ShaderNodeValue", "Shard Shape", 500, 1500)
    drive(shape.outputs[0], "default_value", root, "min(max(floor(p),0),1)", {"p": "shape"})
    shard = node(tree, "GeometryNodeMeshUVSphere", "Pointed Shard", 700, 1700)
    shard.inputs["Segments"].default_value = 4
    shard.inputs["Rings"].default_value = 3
    shard.inputs["Radius"].default_value = 1
    switch = node(tree, "GeometryNodeSwitch", "Round Or Shard", 950, 1700, input_type="GEOMETRY")
    link(shape.outputs[0], switch.inputs["Switch"])
    link(ico.outputs["Mesh"], switch.inputs["False"])
    link(shard.outputs["Mesh"], switch.inputs["True"])
    position = node(tree, "GeometryNodeInputPosition", "Local Shard Position", 500, 2100)
    axes = node(tree, "ShaderNodeSeparateXYZ", "Tip Axis", 700, 2100)
    link(position.outputs[0], axes.inputs[0])
    heat = node(tree, "ShaderNodeMath", "Tail To Tip", 950, 2100, operation="MULTIPLY_ADD")
    link(axes.outputs["Z"], heat.inputs[0])
    heat.inputs[1].default_value, heat.inputs[2].default_value = 0.5, 0.5
    store = node(
        tree,
        "GeometryNodeStoreNamedAttribute",
        "Keep Tip Gradient",
        1200,
        1700,
        data_type="FLOAT",
        domain="POINT",
    )
    store.inputs["Name"].default_value = "vfx_spark_heat"
    link(switch.outputs[0], store.inputs["Geometry"])
    link(heat.outputs[0], store.inputs["Value"])
    link(store.outputs[0], material_node.inputs["Geometry"])
    narrow = node(tree, "ShaderNodeMath", "Shard Narrowing", 700, 1300, operation="MULTIPLY_ADD")
    link(shape.outputs[0], narrow.inputs[0])
    narrow.inputs[1].default_value, narrow.inputs[2].default_value = -0.76, 1
    width = node(tree, "ShaderNodeMath", "Shard Width", 950, 1300, operation="MULTIPLY")
    link(scale, width.inputs[0])
    link(narrow.outputs[0], width.inputs[1])
    length = node(tree, "ShaderNodeValue", "Stretch", 500, 1000)
    drive(
        length.outputs[0],
        "default_value",
        root,
        "1+(max(p,1)-1)*min(max(floor(k),0),1)",
        {"p": "stretch", "k": "shape"},
    )
    length_scale = node(tree, "ShaderNodeMath", "Shard Length", 950, 1000, operation="MULTIPLY")
    link(scale, length_scale.inputs[0])
    link(length.outputs[0], length_scale.inputs[1])
    dimensions = node(tree, "ShaderNodeCombineXYZ", "Particle Dimensions", 1200, 1300)
    link(width.outputs[0], dimensions.inputs["X"])
    link(width.outputs[0], dimensions.inputs["Y"])
    link(length_scale.outputs[0], dimensions.inputs["Z"])
    link(dimensions.outputs[0], instance.inputs["Scale"])
    align = node(
        tree, "FunctionNodeAlignEulerToVector", "Aim Shard Along Travel", 1200, 1000, axis="Z"
    )
    link(direction, align.inputs["Vector"])
    link(shape.outputs[0], align.inputs["Factor"])
    link(align.outputs["Rotation"], instance.inputs["Rotation"])


def shade(tree, root, emission):
    link = tree.links.new
    attr = node(
        tree, "ShaderNodeAttribute", "Shard Heat", -1000, 500, attribute_name="vfx_spark_heat"
    )
    tint = node(tree, "ShaderNodeCombineXYZ", "Editable Particle Color", -1000, 0)
    for index in range(3):
        drive(tint.inputs[index], "default_value", root, "c", {"c": f"color_{index}"})
    # Round particles keep the original uniform color. Shards darken toward the tail.
    darkness = node(tree, "ShaderNodeMath", "Cool Tail", -750, 500, operation="MULTIPLY_ADD")
    link(attr.outputs["Fac"], darkness.inputs[0])
    drive(darkness.inputs[1], "default_value", root, "0.8*k", {"k": "shape"})
    drive(darkness.inputs[2], "default_value", root, "1-0.8*k", {"k": "shape"})
    color = node(tree, "ShaderNodeVectorMath", "Tail Color", -500, 0, operation="SCALE")
    link(tint.outputs[0], color.inputs[0])
    link(darkness.outputs[0], color.inputs["Scale"])
    hot = node(tree, "ShaderNodeMath", "Hot Tip", -750, 800, operation="POWER")
    link(attr.outputs["Fac"], hot.inputs[0])
    hot.inputs[1].default_value = 5
    weight = node(tree, "ShaderNodeMath", "Shard Highlight Only", -500, 700, operation="MULTIPLY")
    link(hot.outputs[0], weight.inputs[0])
    drive(weight.inputs[1], "default_value", root, "min(max(floor(p),0),1)", {"p": "shape"})
    mix = node(tree, "ShaderNodeMixRGB", "White Hot Tip", -250, 0, blend_type="MIX")
    link(weight.outputs[0], mix.inputs[0])
    link(color.outputs[0], mix.inputs[1])
    mix.inputs[2].default_value = (0.9, 0.95, 1, 1)
    link(mix.outputs[0], emission.inputs["Color"])
