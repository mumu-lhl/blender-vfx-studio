"""A short expanding gas nucleus between the contact flash and spent pressure."""

import math

import bmesh

from .impact_shape import _geometry, _mesh, _Nodes
from .nodes import PROGRESS


def build(root, quality):
    sphere = bmesh.new()
    try:
        bmesh.ops.create_icosphere(
            sphere, subdivisions={"LOW": 2, "MEDIUM": 3, "HIGH": 4}[quality], radius=1
        )
        sphere.verts.ensure_lookup_table()
        sphere.verts.index_update()
        vertices = []
        for vertex in sphere.verts:
            direction = vertex.co.normalized()
            angle = math.atan2(direction.y, direction.x)
            radius = 0.8 + 0.18 * math.sin(angle * 3 + direction.z * 1.7)
            radius += 0.12 * math.cos(direction.z * 5 + angle)
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
    layer = _mesh(root, vertices, faces, {}, [(0, 0)] * len(vertices))
    for face in layer.data.polygons:
        face.use_smooth = True
    graph, position = _geometry(root, "Expanding Burst Core")
    progress = graph.value("Burst Core Progress", expression=PROGRESS)
    grow = graph.node(
        "ShaderNodeMapRange", "Compression Opens Quickly", interpolation_type="SMOOTHSTEP"
    )
    graph.connect(progress, grow.inputs["Value"])
    grow.inputs["From Max"].default_value = 0.25
    grow.inputs["To Min"].default_value = 0.18
    age = graph.math("Editable Cooling Age", "MULTIPLY", progress, graph.value("Fade", "fade"))
    remaining = graph.math(
        "Core Loses Mass", "SUBTRACT", 1, graph.math("Mass Loss Rate", "MULTIPLY", age, 0.7)
    )
    remaining = graph.math("No Inverted Core", "MAXIMUM", remaining, 0)
    size = graph.math("Core Envelope", "MULTIPLY", grow.outputs[0], remaining)
    size = graph.math("Core Art Size", "MULTIPLY", size, graph.value("Size", "size"))
    original = graph.node("GeometryNodeInputPosition", "Unequal Pressure Lobes").outputs[0]
    noise = graph.node("ShaderNodeTexNoise", "Rolling Core Surface", noise_dimensions="4D")
    graph.connect(original, noise.inputs["Vector"])
    noise.inputs["Scale"].default_value = 3.5
    noise.inputs["Detail"].default_value = 2
    graph.connect(graph.math("Surface Roll Clock", "MULTIPLY", progress, 2.5), noise.inputs["W"])
    bulge = graph.math("Surface Bulges", "MULTIPLY", noise.outputs["Fac"], 0.4)
    bulge = graph.math("Preserve Core Mass", "ADD", bulge, 0.8)
    size = graph.math("Moving Core Silhouette", "MULTIPLY", size, bulge)
    graph.connect(graph.vector("Expanding Lobes", "SCALE", original, size), position)

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
    visible = graph.math("Remaining Burning Gas", "GREATER_THAN", noise.outputs["Fac"], cutoff)
    tint = graph.node("ShaderNodeCombineXYZ", "Editable Core Color")
    for index in range(3):
        graph.connect(graph.value(f"Color {index}", f"color_{index}"), tint.inputs[index])
    hot = graph.math("Heat In The Core", "MULTIPLY", facing, 0.7)
    hot = graph.math(
        "Gas Heat Variation",
        "ADD",
        hot,
        graph.math("Local Heat", "MULTIPLY", noise.outputs["Fac"], 0.3),
    )
    heat = graph.node("ShaderNodeMapRange", "Hot Gas Pockets", interpolation_type="SMOOTHSTEP")
    graph.connect(hot, heat.inputs["Value"])
    heat.inputs["From Min"].default_value = 0.65
    heat.inputs["From Max"].default_value = 0.95
    cooling = graph.math("Core Cools To Its Tint", "SUBTRACT", 1, age, clamp=True)
    hot = graph.math("Cooling Heat Pockets", "MULTIPLY", heat.outputs[0], cooling)
    color = graph.node("ShaderNodeMixRGB", "Tinted Gas And Hot Pockets")
    graph.connect(hot, color.inputs[0])
    graph.connect(tint.outputs[0], color.inputs[1])
    color.inputs[2].default_value = (1, 0.95, 0.8, 1)
    edge = graph.node("ShaderNodeMixRGB", "Pigmented Gas Edge")
    graph.connect(facing, edge.inputs[0])
    graph.connect(graph.vector("Dark Gas Tint", "SCALE", tint.outputs[0], 0.08), edge.inputs[1])
    graph.connect(color.outputs[0], edge.inputs[2])
    emission = graph.node("ShaderNodeEmission", "Burning Core Emission")
    graph.connect(edge.outputs[0], emission.inputs["Color"])
    graph.connect(graph.value("Strength", "strength"), emission.inputs["Strength"])
    transparent = graph.node("ShaderNodeBsdfTransparent", "Spent Gas")
    mix = graph.node("ShaderNodeMixShader", "Core Erodes Into Gaps")
    graph.connect(visible, mix.inputs[0])
    graph.connect(transparent.outputs[0], mix.inputs[1])
    graph.connect(emission.outputs[0], mix.inputs[2])
    output = graph.node("ShaderNodeOutputMaterial", "Core Surface Output")
    graph.connect(mix.outputs[0], output.inputs["Surface"])
    root["vfx_parameter_keys"] = "size,fade,strength"
