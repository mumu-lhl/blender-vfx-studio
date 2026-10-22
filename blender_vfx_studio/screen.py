"""Opt-in native compositor layers; preserve the surrounding user's graph."""

import uuid

import bpy

from .nodes import ACTIVE, PROGRESS, TIME_PROPS, drive, node
from .parameters import SCREEN_PARAMETERS

ORIGINAL_FLAG = "vfx_screen_original_compositing"


def _destination(scene):
    """Preflight before creating any controller or changing links."""
    tree = scene.compositing_node_group
    if tree is None:
        return None, None
    if tree.users > 1 or tree.library:
        raise ValueError(
            "Compositor is shared or linked; make it single-user before adding Screen VFX"
        )
    outputs = [n for n in tree.nodes if n.type == "GROUP_OUTPUT" and n.is_active_output]
    if len(outputs) != 1 or outputs[0].inputs.get("Image") is None:
        raise ValueError("Compositor requires one active group output with an Image input")
    target = outputs[0].inputs["Image"]
    if target.type != "RGBA":
        raise ValueError("Compositor Image output must be a color socket")
    if len(target.links) != 1:
        raise ValueError("Connect the compositor Image output before adding Screen VFX")
    return tree, target


def _base(scene):
    tree = bpy.data.node_groups.new("VFX • Scene Compositor", "CompositorNodeTree")
    tree["vfx_screen_base"] = True
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    out = node(tree, "NodeGroupOutput", "Scene Output", 650, 200)
    render = node(tree, "CompositorNodeRLayers", "Scene Render", -300, 200)
    render.scene = scene
    for n in (out, render):
        n["vfx_role"] = "screen_base"
    tree["vfx_base_layer"] = render.layer
    tree.links.new(render.outputs["Image"], out.inputs["Image"])
    scene.compositing_node_group = tree
    return tree, out.inputs["Image"]


def _group(root):
    tree = bpy.data.node_groups.new("VFX • Glare + Flash", "CompositorNodeTree")
    tree["vfx_id"] = root["vfx_id"]
    for direction in ("INPUT", "OUTPUT"):
        tree.interface.new_socket(name="Image", in_out=direction, socket_type="NodeSocketColor")
    inp = node(tree, "NodeGroupInput", "Input", -700, 200)
    out = node(tree, "NodeGroupOutput", "Output", 750, 200)
    glare = node(tree, "CompositorNodeGlare", "Glare", -100, 200)
    glare.inputs["Type"].default_value = "Fog Glow"
    glare.inputs["Quality"].default_value = "Low"
    active = node(tree, "ShaderNodeValue", "Active", -700, -100)
    progress = node(tree, "ShaderNodeValue", "Progress", -700, -300)
    strength = node(tree, "ShaderNodeMath", "Active Glare", -400, 0, operation="MULTIPLY")
    fade = node(tree, "ShaderNodeMath", "Flash Fade", -400, -300, operation="MULTIPLY")
    remain = node(tree, "ShaderNodeMath", "Remaining Flash", -200, -300, operation="SUBTRACT")
    remain.inputs[0].default_value = 1
    flash = node(tree, "ShaderNodeMath", "Flash Strength", 0, -300, operation="MULTIPLY")
    visible = node(tree, "ShaderNodeMath", "Active Flash", 200, -100, operation="MULTIPLY")
    mix = node(tree, "ShaderNodeMixRGB", "Flash Overlay", 500, 200, blend_type="MIX")
    for n, expression in [(active, ACTIVE), (progress, PROGRESS)]:
        drive(n.outputs[0], "default_value", root, expression, TIME_PROPS)
    for socket, prop in [
        (strength.inputs[1], "strength"),
        (fade.inputs[1], "fade"),
        (flash.inputs[1], "flash"),
        (glare.inputs["Threshold"], "threshold"),
        (glare.inputs["Size"], "glow_size"),
    ]:
        drive(socket, "default_value", root, "p", {"p": prop})
    for i in range(3):
        drive(mix.inputs[2], "default_value", root, "p", {"p": f"color_{i}"}, i)
    mix.inputs[2].default_value[3] = 1
    link = tree.links.new
    link(inp.outputs["Image"], glare.inputs["Image"])
    link(active.outputs[0], strength.inputs[0])
    link(strength.outputs[0], glare.inputs["Strength"])
    link(progress.outputs[0], fade.inputs[0])
    link(fade.outputs[0], remain.inputs[1])
    link(remain.outputs[0], flash.inputs[0])
    link(flash.outputs[0], visible.inputs[0])
    link(active.outputs[0], visible.inputs[1])
    link(visible.outputs[0], mix.inputs[0])
    link(glare.outputs["Image"], mix.inputs[1])
    link(mix.outputs[0], out.inputs["Image"])
    return tree


def _insert(scene, root, group):
    tree, target = _destination(scene)
    if tree is None:
        tree, target = _base(scene)
    if ORIGINAL_FLAG not in tree:
        tree[ORIGINAL_FLAG] = scene.render.use_compositing
    source = target.links[0].from_socket
    layer = node(tree, "CompositorNodeGroup", root.name, 300, 200, node_tree=group)
    layer["vfx_id"] = root["vfx_id"]
    layer["vfx_role"] = "screen_layer"
    tree.links.new(source, layer.inputs["Image"])
    tree.links.new(layer.outputs["Image"], target)
    root["vfx_scene"] = scene
    scene.render.use_compositing = True


def create(context):
    from . import core

    _destination(context.scene)
    root, _ = core._controller(context, "Screen VFX", "screen.glare", "LOW", SCREEN_PARAMETERS, {})
    _insert(context.scene, root, _group(root))
    core.select(context, root)
    return root


def _layer(root):
    scene = root.get("vfx_scene")
    if not isinstance(scene, bpy.types.Scene) or scene.compositing_node_group is None:
        raise ValueError("Screen compositor is missing; restore it before removing the controller")
    tree = scene.compositing_node_group
    layers = [
        n
        for n in tree.nodes
        if n.get("vfx_id") == root["vfx_id"] and n.get("vfx_role") == "screen_layer"
    ]
    if len(layers) != 1:
        raise ValueError("Screen layer is missing or ambiguous; restore the compositor graph")
    return scene, tree, layers[0]


def duplicate(context, root):
    from . import core

    _, _, source = _layer(root)
    if (
        source.node_tree is None
        or source.inputs.get("Image") is None
        or source.outputs.get("Image") is None
    ):
        raise ValueError("Screen Image interface was edited; restore it before duplication")
    _destination(context.scene)
    clone = root.copy()
    clone["vfx_id"] = str(uuid.uuid4())
    collection = bpy.data.collections.new("VFX • Screen Copy")
    collection["vfx_id"] = clone["vfx_id"]
    context.scene.collection.children.link(collection)
    collection.objects.link(clone)
    group = source.node_tree.copy()
    group["vfx_id"] = clone["vfx_id"]
    mapping = {root: clone}
    core._remap_drivers(clone, mapping)
    core._remap_drivers(group, mapping)
    _insert(context.scene, clone, group)
    core.select(context, clone)
    return clone


def remove(root):
    scene, tree, layer = _layer(root)
    if tree.users > 1 or tree.library:
        raise ValueError(
            "Compositor is shared or linked; make it single-user before removing Screen VFX"
        )
    group = layer.node_tree
    if group and (group.users > 1 or group.get("vfx_id") != root["vfx_id"]):
        raise ValueError("Screen node group is shared or replaced; restore it before deletion")
    inputs = layer.inputs.get("Image")
    outputs = layer.outputs.get("Image")
    if inputs is None or outputs is None or (outputs.links and len(inputs.links) != 1):
        raise ValueError("Screen Image connections were edited; reconnect the input before removal")
    if inputs.links:
        source = inputs.links[0].from_socket
        for link in list(outputs.links):
            tree.links.new(source, link.to_socket)
    tree.nodes.remove(layer)
    if group and group.users == 0:
        bpy.data.node_groups.remove(group)
    if any(n.get("vfx_role") == "screen_layer" for n in tree.nodes):
        return
    if ORIGINAL_FLAG in tree:
        if scene.render.use_compositing and not tree[ORIGINAL_FLAG]:
            scene.render.use_compositing = False
        del tree[ORIGINAL_FLAG]
    # Removing our effect must not discard edits made to the generated base.
    if _untouched_base(tree, scene):
        scene.compositing_node_group = None
        if tree.users == 0:
            bpy.data.node_groups.remove(tree)


def _untouched_base(tree, scene):
    if not tree.get("vfx_screen_base") or len(tree.nodes) != 2 or len(tree.links) != 1:
        return False
    output = tree.nodes.get("Scene Output")
    render = tree.nodes.get("Scene Render")
    if output is None or render is None:
        return False
    if output.bl_idname != "NodeGroupOutput" or render.bl_idname != "CompositorNodeRLayers":
        return False
    if (
        output.label != "Scene Output"
        or render.label != "Scene Render"
        or output.location[:] != (650, 200)
        or render.location[:] != (-300, 200)
        or render.scene != scene
        or render.layer != tree.get("vfx_base_layer")
    ):
        return False
    if len(tree.interface.items_tree) != 1 or tree.interface.items_tree[0].name != "Image":
        return False
    link = tree.links[0]
    return (
        link.from_node == render
        and link.from_socket.name == "Image"
        and link.to_node == output
        and link.to_socket.name == "Image"
    )
