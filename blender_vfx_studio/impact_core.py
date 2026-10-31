"""A short expanding gas nucleus between the contact flash and spent pressure."""

import math

import bmesh

from .impact_shape import _geometry, _mesh, _Nodes
from .nodes import PROGRESS


def build(root, quality):
    sphere = bmesh.new()
    try:
        bmesh.ops.create_icosphere(
            sphere, subdivisions={"LOW": 3, "MEDIUM": 4, "HIGH": 5}[quality], radius=1
        )
        sphere.verts.ensure_lookup_table()
        sphere.verts.index_update()
        vertices, outflow, tips = [], [], []
        for vertex in sphere.verts:
            direction = vertex.co.normalized()
            angle = math.atan2(direction.y, direction.x)
            radius = 0.8 + 0.18 * math.sin(angle * 3 + direction.z * 1.7)
            radius += 0.12 * math.cos(direction.z * 5 + angle)
            tip = max(0, math.sin(angle * 3 + direction.z * 1.7)) ** 3
            tip *= 1 - 0.6 * abs(direction.z)
            tips.append(tip)
            outflow.append(tuple(direction * tip))
            vertices.append(
                (
                    direction.x * radius * (1 + direction.z * 0.18),
                    direction.y * radius * 0.85,
                    direction.z * radius * 0.78 + 0.12 * (1 - direction.z**2) * math.sin(angle * 2),
                )
            )
        faces = [tuple(v.index for v in face.verts) for face in sphere.faces]
    finally:
        sphere.free()
    layer = _mesh(
        root,
        vertices,
        faces,
        {"impact_core_outflow": ("FLOAT_VECTOR", outflow), "impact_core_tip": ("FLOAT", tips)},
        [(0, 0)] * len(vertices),
    )
    for face in layer.data.polygons:
        face.use_smooth = True
    graph, position = _geometry(root, "Expanding Burst Core")
    progress = graph.value("Burst Core Progress", expression=PROGRESS)
    remaining = graph.math("Time Before The Gas Stops", "SUBTRACT", 1, progress, clamp=True)
    drag = graph.math("Rapid Outflow Then Drag", "POWER", remaining, 3)
    travel = graph.math("Gas Keeps Moving Outward", "SUBTRACT", 1, drag)
    size = graph.math("Compressed Core Opens", "ADD", travel, 0.18)
    art_size = graph.value("Size", "size")
    size = graph.math("Core Art Size", "MULTIPLY", size, art_size)
    original = graph.node("GeometryNodeInputPosition", "Unequal Pressure Lobes").outputs[0]
    noise = graph.node("ShaderNodeTexNoise", "Rolling Core Surface", noise_dimensions="4D")
    graph.connect(original, noise.inputs["Vector"])
    noise.inputs["Scale"].default_value = 3.5
    noise.inputs["Detail"].default_value = 2
    graph.connect(graph.math("Surface Roll Clock", "MULTIPLY", progress, 2.5), noise.inputs["W"])
    bulge = graph.math("Surface Bulges", "MULTIPLY", noise.outputs["Fac"], 0.4)
    bulge = graph.math("Preserve Core Mass", "ADD", bulge, 0.8)
    size = graph.math("Moving Core Silhouette", "MULTIPLY", size, bulge)
    outflow = graph.math("Unequal Front Travel", "MULTIPLY", travel, art_size)
    outflow = graph.math("Separating Gas Tongues", "MULTIPLY", outflow, 0.4)
    graph.connect(
        graph.vector(
            "Gas Leaves The Contact",
            "ADD",
            graph.vector("Expanding Lobes", "SCALE", original, size),
            graph.vector(
                "Outward Moving Fronts",
                "SCALE",
                graph.attribute("impact_core_outflow", "FLOAT_VECTOR"),
                outflow,
            ),
        ),
        position,
    )

    material = layer.data.materials[0]
    material.node_tree.animation_data_clear()
    material.node_tree.nodes.clear()
    graph = _Nodes(material.node_tree, root)
    progress = graph.value("Burst Core Progress", expression=PROGRESS)
    age = graph.math("Core Erosion Age", "MULTIPLY", progress, graph.value("Fade", "fade"))
    coordinates = graph.node("ShaderNodeTexCoord", "Core Local Coordinates")
    noise = graph.node("ShaderNodeTexNoise", "Burning Gas Detail", noise_dimensions="4D")
    graph.connect(coordinates.outputs["Generated"], noise.inputs["Vector"])
    noise.inputs["Scale"].default_value = 4
    noise.inputs["Detail"].default_value = 2
    graph.connect(graph.math("Gas Flow Clock", "MULTIPLY", progress, 3), noise.inputs["W"])
    normal = graph.node("ShaderNodeNewGeometry", "Core Surface")
    facing = graph.node("ShaderNodeVectorMath", "Core Faces The Viewer", operation="DOT_PRODUCT")
    graph.connect(normal.outputs["Normal"], facing.inputs[0])
    graph.connect(normal.outputs["Incoming"], facing.inputs[1])
    facing = graph.math("Two Sided Core", "ABSOLUTE", facing.outputs["Value"])
    squared = graph.math("Erosion Accelerates After Expansion", "MULTIPLY", age, age)
    cutoff = graph.math("Gas Breakup Range", "MULTIPLY", squared, 0.75)
    cutoff = graph.math("Gas Breakup Threshold", "ADD", cutoff, 0.13)
    tips = graph.node("ShaderNodeAttribute", "Ejected Gas Fronts", attribute_name="impact_core_tip")
    coverage = graph.math(
        "Fronts Outlive The Connecting Gas", "MULTIPLY", tips.outputs["Fac"], 0.12
    )
    coverage = graph.math("Unequal Gas Coverage", "ADD", noise.outputs["Fac"], coverage)
    visible = graph.math("Remaining Burning Gas", "GREATER_THAN", coverage, cutoff)
    tint = graph.node("ShaderNodeCombineXYZ", "Editable Core Color")
    for index in range(3):
        graph.connect(graph.value(f"Color {index}", f"color_{index}"), tint.inputs[index])
    hot = graph.math("Heat In The Core", "MULTIPLY", facing, 0.35)
    hot = graph.math(
        "Gas Heat Variation",
        "ADD",
        hot,
        graph.math("Local Heat", "MULTIPLY", noise.outputs["Fac"], 0.65),
    )
    heat = graph.node("ShaderNodeMapRange", "Hot Gas Pockets", interpolation_type="SMOOTHSTEP")
    graph.connect(hot, heat.inputs["Value"])
    heat.inputs["From Min"].default_value = 0.4
    heat.inputs["From Max"].default_value = 0.75
    cooling = graph.math("Core Cools To Its Tint", "SUBTRACT", 1, age, clamp=True)
    hot = graph.math("Cooling Heat Pockets", "MULTIPLY", heat.outputs[0], cooling)
    color = graph.node("ShaderNodeMixRGB", "Tinted Gas And Hot Pockets")
    graph.connect(hot, color.inputs[0])
    graph.connect(tint.outputs[0], color.inputs[1])
    hot_tint = graph.node("ShaderNodeCombineXYZ", "Heat Keeps The Editable Hue")
    for index in range(3):
        graph.connect(
            graph.math(
                f"Hot Color {index}",
                "POWER",
                graph.math(
                    f"Nonnegative Color {index}",
                    "MAXIMUM",
                    graph.value(f"Heat Tint {index}", f"color_{index}"),
                    0,
                ),
                0.3,
            ),
            hot_tint.inputs[index],
        )
    graph.connect(hot_tint.outputs[0], color.inputs[2])
    edge = graph.node("ShaderNodeMixRGB", "Pigmented Gas Edge")
    graph.connect(facing, edge.inputs[0])
    graph.connect(graph.vector("Dark Gas Tint", "SCALE", tint.outputs[0], 0.08), edge.inputs[1])
    graph.connect(color.outputs[0], edge.inputs[2])
    density = graph.node(
        "ShaderNodeMapRange", "Hot Pockets And Darker Gas", interpolation_type="SMOOTHSTEP"
    )
    graph.connect(noise.outputs["Fac"], density.inputs["Value"])
    density.inputs["From Min"].default_value = 0.34
    density.inputs["From Max"].default_value = 0.62
    density.inputs["To Min"].default_value = 0.12
    emission = graph.node("ShaderNodeEmission", "Burning Core Emission")
    graph.connect(
        graph.vector("Moving Gas Color Structure", "SCALE", edge.outputs[0], density.outputs[0]),
        emission.inputs["Color"],
    )
    graph.connect(graph.value("Strength", "strength"), emission.inputs["Strength"])
    transparent = graph.node("ShaderNodeBsdfTransparent", "Spent Gas")
    mix = graph.node("ShaderNodeMixShader", "Core Erodes Into Gaps")
    graph.connect(visible, mix.inputs[0])
    graph.connect(transparent.outputs[0], mix.inputs[1])
    graph.connect(emission.outputs[0], mix.inputs[2])
    output = graph.node("ShaderNodeOutputMaterial", "Core Surface Output")
    graph.connect(mix.outputs[0], output.inputs["Surface"])
    root["vfx_parameter_keys"] = "size,fade,strength"
