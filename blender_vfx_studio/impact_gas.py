"""An original painted heat atlas using the existing native flipbook player."""

from pathlib import Path

import bpy

from . import core
from .impact_shape import _Nodes


def create(context, quality):
    path = Path(__file__).with_name("assets") / "burst_heat.png"
    if not path.is_file():
        raise ValueError("The bundled burst atlas is missing; reinstall the extension")
    image = bpy.data.images.load(str(path), check_existing=False)
    image.name = "VFX • Original Burst Heat"
    image.colorspace_settings.name = "Non-Color"
    image.alpha_mode = "STRAIGHT"
    image["vfx_burst_heat"] = 1
    image.pack()
    # Images keep Blender's ordinary sharing and user-data deletion behavior.
    root = core.create_flipbook(context, image, columns=4, rows=2)
    root["vfx_quality"] = quality
    root["vfx_parameter_keys"] = "width,height,opacity,fade,strength"
    layer = root.children[0]
    tree = layer.modifiers[0].node_group
    geometry = tree.nodes["Outside Lifetime"].outputs[0]
    camera = tree.nodes.new("GeometryNodeInputActiveCamera")
    camera.label = "Native Active Camera"
    camera.location = (-400, -400)
    info = tree.nodes.new("GeometryNodeObjectInfo")
    info.transform_space = "RELATIVE"
    info.label = "Camera In Sprite Space"
    info.location = (-150, -400)
    tree.links.new(camera.outputs[0], info.inputs["Object"])
    transform = tree.nodes.new("GeometryNodeTransform")
    transform.name = transform.label = "Face The Active Camera"
    transform.location = (500, 200)
    tree.links.new(geometry, transform.inputs["Geometry"])
    tree.links.new(info.outputs["Rotation"], transform.inputs["Rotation"])
    tree.links.new(transform.outputs[0], tree.nodes["Output"].inputs[0])
    tree.nodes["Output"].location = (850, 200)

    material = layer.data.materials[0]
    material.surface_render_method = "BLENDED"
    tree = material.node_tree
    before = set(tree.nodes)
    graph = _Nodes(tree, root)
    tree.nodes["Atlas Image"].interpolation = "Linear"
    heat = tree.nodes["Atlas Image"].outputs["Color"]
    hot = graph.node("ShaderNodeCombineXYZ", "Heat Keeps The Editable Hue")
    for index in range(3):
        graph.connect(
            graph.math(
                f"Hot Channel {index}",
                "POWER",
                graph.value(f"Gas Tint {index}", f"color_{index}"),
                0.25,
            ),
            hot.inputs[index],
        )
    warm = graph.node(
        "ShaderNodeMapRange", "Cold Gas To Saturated Heat", interpolation_type="SMOOTHSTEP"
    )
    graph.connect(heat, warm.inputs["Value"])
    warm.inputs["From Min"].default_value = 0.1
    warm.inputs["From Max"].default_value = 0.45
    body = graph.node("ShaderNodeMixRGB", "Dark Gas And Burning Body")
    graph.connect(warm.outputs[0], body.inputs[0])
    graph.connect(
        graph.vector("Subordinate Gas Tint", "SCALE", tree.nodes["Sprite Tint"].outputs[0], 0.08),
        body.inputs[1],
    )
    tint = graph.node("ShaderNodeCombineXYZ", "Editable Burning Gas Color")
    for index in range(3):
        graph.connect(graph.value(f"Body Tint {index}", f"color_{index}"), tint.inputs[index])
    graph.connect(tint.outputs[0], body.inputs[2])
    pockets = graph.node("ShaderNodeMapRange", "Local Hot Pockets", interpolation_type="SMOOTHSTEP")
    graph.connect(heat, pockets.inputs["Value"])
    pockets.inputs["From Min"].default_value = 0.55
    pockets.inputs["From Max"].default_value = 0.9
    color = graph.node("ShaderNodeMixRGB", "Burning Body And Hot Pockets")
    graph.connect(pockets.outputs[0], color.inputs[0])
    graph.connect(body.outputs[0], color.inputs[1])
    graph.connect(hot.outputs[0], color.inputs[2])
    graph.connect(color.outputs[0], tree.nodes["Emission"].inputs["Color"])
    created = set(tree.nodes) - before
    frame = tree.nodes.new("NodeFrame")
    frame.label = "Original gas heat and soft view coverage"
    for item in created:
        item.parent = frame
    frame.location = (2300, -600)
    return root
