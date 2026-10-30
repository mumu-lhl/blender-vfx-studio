"""An emissive density core inside the existing animated charge envelope."""

from tools.charge_design import _Fields


def add_density_core(root):
    layer = root.children[0]
    material = layer.data.materials[0]
    volume_material = _density_material(root, material)
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
    assign.inputs["Material"].default_value = volume_material
    g.link(volume.outputs[0], assign.inputs["Geometry"])
    visible = g.n("GeometryNodeSwitch", "Skip Empty Density Envelopes", input_type="GEOMETRY")
    g.link(
        g.m("Density Envelope Has Size", "GREATER_THAN", diagonal.outputs["Value"], 0.0001),
        visible.inputs["Switch"],
    )
    g.link(assign.outputs[0], visible.inputs["True"])
    joined = g.n("GeometryNodeJoinGeometry", "Editable Envelope And Stored Density")
    # Keep the editable mesh and its attributes, but hide its solid surface in
    # the material. The renderer receives the native volume component as well.
    g.link(original, joined.inputs[0])
    g.link(visible.outputs[0], joined.inputs[0])
    g.link(joined.outputs[0], output.inputs["Geometry"])


def _density_material(root, surface):
    material = surface.copy()
    material.name = "VFX • Stored Plasma Density"
    material["vfx_id"] = root["vfx_id"]
    tree = material.node_tree
    tree["vfx_id"] = root["vfx_id"]
    tree.animation_data_clear()
    tree.nodes.clear()
    root.children[0].data.materials.append(material)
    g = _Fields(tree, root)

    def control(name, source, direction, index):
        value = g.value(name)
        curve = value.driver_add("default_value")
        curve.driver.expression = "v"
        variable = curve.driver.variables.new()
        variable.name = "v"
        variable.targets[0].id_type = "MATERIAL"
        variable.targets[0].id = surface
        variable.targets[0].data_path = (
            'node_tree.nodes["' + source + '"].' + direction + "[" + str(index) + "].default_value"
        )
        return value

    threshold = control("Stored White Threshold", "Nucleus White Threshold", "outputs", 0)
    contrast = control("Stored Light Contrast", "Pressure Heart Volume Values", "inputs", 1)
    bias = control("Stored Light Bias", "Pressure Heart Volume Values", "inputs", 2)
    from blender_vfx_studio.nodes import PROGRESS

    p = g.value("Density Clock", expression=PROGRESS)
    clock = g.m(
        "Density Flow Accelerates", "MULTIPLY", g.m("Density Squared Time", "MULTIPLY", p, p), 20
    )
    coords = g.n("ShaderNodeTexCoord", "Stored Volume Coordinates")
    centered = g.v(
        "Center Within Density Bounds", "SUBTRACT", coords.outputs["Generated"], (0.5, 0.5, 0.5)
    )
    radius = g.n("ShaderNodeVectorMath", "Density Radius", operation="LENGTH")
    g.link(centered, radius.inputs[0])
    falloff = g.m(
        "Soft Density Boundary",
        "SUBTRACT",
        1,
        g.stage("Density Boundary Falloff", radius.outputs["Value"], 0.12, 0.49),
    )
    wave = g.m(
        "Energy Moves Into The Center",
        "ADD",
        g.m("Density Front Spacing", "MULTIPLY", radius.outputs["Value"], 24),
        clock,
    )
    front = g.m("Inward Stored Front", "MULTIPLY_ADD", g.m("Stored Front Wave", "SINE", wave), 0.5)
    front.node.inputs[2].default_value = 0.5
    noise = g.n("ShaderNodeTexNoise", "Unequal Plasma Density", noise_dimensions="4D")
    g.link(coords.outputs["Generated"], noise.inputs["Vector"])
    g.link(g.value("Density Detail", prop="noise_scale"), noise.inputs["Scale"])
    g.link(g.m("Slow Density Roil", "MULTIPLY", clock, 0.15), noise.inputs["W"])
    noise.inputs["Detail"].default_value = 2
    variation = g.m("Connected Density Detail", "MULTIPLY_ADD", noise.outputs["Fac"], 0.25)
    variation.node.inputs[2].default_value = 0.75
    front = g.m("Unequal Inward Fronts", "MULTIPLY", front, variation)
    fill = g.m("Mass Between Fronts", "MULTIPLY_ADD", front, 0.65)
    fill.node.inputs[2].default_value = 0.35
    density = g.m("Soft Three Dimensional Mass", "MULTIPLY", falloff, fill)
    density = g.m(
        "Editable Volume Opacity", "MULTIPLY", density, g.value("Volume Opacity", prop="opacity")
    )
    color = g.xyz(
        "Editable Stored Color",
        *(g.value("Stored Color " + str(i), prop="color_" + str(i)) for i in range(3)),
    )
    values = g.m("White In The Flowing Mass", "MULTIPLY_ADD", front, contrast)
    g.link(bias, values.node.inputs[2])
    hot = g.m("Stored Hot Fronts", "GREATER_THAN", front, threshold)
    hot = g.m(
        "Limited Stored White", "MINIMUM", g.m("Editable Stored White", "MULTIPLY", values, hot), 1
    )
    tint = g.n("ShaderNodeMixRGB", "Blue Mass And Hot Density")
    g.link(hot, tint.inputs[0])
    g.link(color, tint.inputs[1])
    tint.inputs[2].default_value = (0.9, 0.98, 1, 1)
    volume = g.n("ShaderNodeVolumePrincipled", "Native Stored Plasma Volume")
    g.link(color, volume.inputs["Color"])
    g.link(g.m("Native Density Scale", "MULTIPLY", density, 0.5), volume.inputs["Density"])
    g.link(tint.outputs[0], volume.inputs["Emission Color"])
    stored = g.stage("Stored Energy Concentration", p, 0.3, 0.84)
    gain = g.m("Energy Builds Within The Volume", "MULTIPLY_ADD", stored, 6)
    gain.node.inputs[2].default_value = 2
    strength = g.m("Concentrated Volume Light", "MULTIPLY", density, gain)
    g.link(
        g.m(
            "Editable Stored Emission",
            "MULTIPLY",
            strength,
            g.value("Volume Emission", prop="strength"),
        ),
        volume.inputs["Emission Strength"],
    )
    output = g.n("ShaderNodeOutputMaterial", "Output")
    g.link(volume.outputs[0], output.inputs["Volume"])
    return material
