"""An emissive density core inside the existing animated charge envelope."""

from tools.charge_design import _Fields


def add_density_core(root):
    layer = root.children[0]
    material = layer.data.materials[0]
    tree = layer.modifiers[0].node_group
    g = _Fields(tree, root)
    output = next(n for n in tree.nodes if n.type == "GROUP_OUTPUT")
    original = output.inputs["Geometry"].links[0].from_socket
    select = g.n("GeometryNodeSeparateGeometry", "Stored Density Envelope", domain="FACE")
    g.link(original, select.inputs["Geometry"])
    g.link(g.attr("charge_heart"), select.inputs["Selection"])
    bounds = g.n("GeometryNodeBoundBox", "Stored Envelope Bounds")
    g.link(select.outputs["Selection"], bounds.inputs["Geometry"])
    diagonal = g.n("ShaderNodeVectorMath", "Fill The Entire Envelope", operation="DISTANCE")
    g.link(bounds.outputs["Min"], diagonal.inputs[0])
    g.link(bounds.outputs["Max"], diagonal.inputs[1])
    volume = g.n("GeometryNodeMeshToVolume", "Native Stored Density")
    volume.inputs["Voxel Amount"].default_value = 32
    volume.inputs["Density"].default_value = 1
    g.link(select.outputs["Selection"], volume.inputs["Mesh"])
    g.link(diagonal.outputs["Value"], volume.inputs["Interior Band Width"])
    assign = g.n("GeometryNodeSetMaterial", "Stored Density Material")
    assign.inputs["Material"].default_value = material
    g.link(volume.outputs[0], assign.inputs["Geometry"])
    joined = g.n("GeometryNodeJoinGeometry", "Editable Envelope And Stored Density")
    # Keep the editable mesh and its attributes, but hide its solid surface in
    # the material. The renderer receives the native volume component as well.
    g.link(original, joined.inputs[0])
    g.link(assign.outputs[0], joined.inputs[0])
    g.link(joined.outputs[0], output.inputs["Geometry"])

    shade = _Fields(material.node_tree, root)
    nodes = material.node_tree.nodes
    grid = shade.n("ShaderNodeAttribute", "Stored Density Grid", attribute_name="density")
    coords = shade.n("ShaderNodeTexCoord", "Local Stored Energy Coordinates")
    radius = shade.n("ShaderNodeVectorMath", "Distance Into The Stored Mass", operation="LENGTH")
    shade.link(coords.outputs["Object"], radius.inputs[0])
    clock = nodes["Charge Clock"].outputs[0]
    clock = shade.m(
        "Density Flow Accelerates",
        "MULTIPLY",
        shade.m("Density Time", "MULTIPLY", clock, clock),
        20,
    )
    distance = shade.m(
        "Density Radius Units",
        "DIVIDE",
        radius.outputs["Value"],
        shade.m(
            "Safe Density Radius", "MAXIMUM", shade.value("Density Radius", prop="radius"), 0.001
        ),
    )
    wave = shade.m(
        "Density Front Travels Inward",
        "ADD",
        shade.m("Density Front Spacing", "MULTIPLY", distance, 18),
        clock,
    )
    front = shade.m(
        "Dense Inward Front", "MULTIPLY_ADD", shade.m("Density Front Wave", "SINE", wave), 0.5
    )
    front.node.inputs[2].default_value = 0.5
    noise = shade.n("ShaderNodeTexNoise", "Unequal Stored Density", noise_dimensions="4D")
    shade.link(coords.outputs["Object"], noise.inputs["Vector"])
    shade.link(shade.value("Density Detail", prop="noise_scale"), noise.inputs["Scale"])
    shade.link(shade.m("Density Roil", "MULTIPLY", clock, 0.15), noise.inputs["W"])
    noise.inputs["Detail"].default_value = 2
    detail = shade.m("Coherent Density Variation", "MULTIPLY_ADD", noise.outputs["Fac"], 0.25)
    detail.node.inputs[2].default_value = 0.75
    front = shade.m("Density Front Detail", "MULTIPLY", front, detail)
    fill = shade.m("Connected Mass Between Fronts", "MULTIPLY_ADD", front, 0.65)
    fill.node.inputs[2].default_value = 0.35
    density = shade.m("Only Native Grid Cells Emit", "MULTIPLY", grid.outputs["Fac"], fill)
    density = shade.m(
        "Editable Stored Density Opacity",
        "MULTIPLY",
        density,
        shade.value("Density Opacity", prop="opacity"),
    )
    values = nodes["Pressure Heart Volume Values"]
    shade.link(front, values.inputs[0])
    hot = shade.m(
        "Hot Density Threshold", "GREATER_THAN", front, nodes["Nucleus White Threshold"].outputs[0]
    )
    hot = shade.m(
        "Limited Density White",
        "MINIMUM",
        shade.m("Density White Values", "MULTIPLY", hot, values.outputs[0]),
        1,
    )
    color = shade.n("ShaderNodeMixRGB", "Stored Blue Mass And Hot Fronts")
    shade.link(hot, color.inputs[0])
    shade.link(nodes["Editable Energy Color"].outputs[0], color.inputs[1])
    color.inputs[2].default_value = (0.9, 0.98, 1, 1)
    emission = shade.n("ShaderNodeEmission", "Emission Inside The Stored Mass")
    shade.link(color.outputs[0], emission.inputs["Color"])
    stored = nodes["Stored Energy Concentration"].outputs[0]
    gain = shade.m("Energy Accumulates In Density", "MULTIPLY_ADD", stored, 6)
    gain.node.inputs[2].default_value = 2
    strength = shade.m("Density Carries Stored Light", "MULTIPLY", density, gain)
    shade.link(
        shade.m(
            "Editable Density Emission",
            "MULTIPLY",
            strength,
            shade.value("Density Emission", prop="strength"),
        ),
        emission.inputs["Strength"],
    )
    absorption = shade.n("ShaderNodeVolumeAbsorption", "Blue Density Against Light Backgrounds")
    shade.link(nodes["Editable Energy Color"].outputs[0], absorption.inputs["Color"])
    shade.link(
        shade.m("Stored Optical Depth", "MULTIPLY", density, 2.5), absorption.inputs["Density"]
    )
    combined = shade.n("ShaderNodeAddShader", "Emissive Absorbing Stored Volume")
    shade.link(emission.outputs[0], combined.inputs[0])
    shade.link(absorption.outputs[0], combined.inputs[1])
    material_output = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
    shade.link(combined.outputs[0], material_output.inputs["Volume"])
