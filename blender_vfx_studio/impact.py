"""Editable four-layer hit: short flash, pressure body, broken wave and embers."""

from . import composition, core
from .impact_shape import flash as flash_shape
from .impact_shape import jets
from .impact_shape import wave as wave_shape
from .nodes import PROGRESS, TIME_PROPS, drive, node


def _shade_shards(root):
    """Author dark side facets in this Impact member's private material."""
    tree = root.children[0].data.materials[0].node_tree
    link = tree.links.new
    normal = node(tree, "ShaderNodeNewGeometry", "Shard Face Normal", -1000, -400)
    facing = node(
        tree, "ShaderNodeVectorMath", "Illustrated Light", -750, -400, operation="DOT_PRODUCT"
    )
    link(normal.outputs["Normal"], facing.inputs[0])
    facing.inputs[1].default_value = (-0.36, -0.48, 0.8)
    sides = node(tree, "ShaderNodeMapRange", "Side Facets", -500, -400)
    sides.interpolation_type = "SMOOTHSTEP"
    link(facing.outputs["Value"], sides.inputs["Value"])
    sides.inputs["From Min"].default_value = 0.25
    sides.inputs["From Max"].default_value = 0.95
    sides.inputs["To Min"].default_value = 1
    sides.inputs["To Max"].default_value = 0
    contrast = node(tree, "ShaderNodeValue", "Side Contrast", -500, -700)
    contrast.outputs[0].default_value = 0.85
    amount = node(tree, "ShaderNodeMath", "Side Shade Amount", -250, -400, operation="MULTIPLY")
    link(sides.outputs[0], amount.inputs[0])
    link(contrast.outputs[0], amount.inputs[1])
    dark = node(tree, "ShaderNodeVectorMath", "Dark Side Color", -250, -700, operation="SCALE")
    link(tree.nodes["Editable Particle Color"].outputs[0], dark.inputs[0])
    dark.inputs["Scale"].default_value = 0.025
    body = node(tree, "ShaderNodeMixRGB", "Faceted Shard Body", 0, -400)
    link(amount.outputs[0], body.inputs[0])
    link(tree.nodes["Tail Color"].outputs[0], body.inputs[1])
    link(dark.outputs[0], body.inputs[2])
    # Keep the existing white leading tip independent of the dark side facets.
    link(body.outputs[0], tree.nodes["White Hot Tip"].inputs[1])
    tree.nodes["White Hot Tip"].location = (250, 0)
    tree.nodes["Particle Emission"].location = (500, 0)
    tree.nodes["Surface"].location = (750, 0)


def create(context, quality="LOW"):
    if quality not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("Unknown impact quality")
    start = float(context.scene.frame_current_final)
    origin = context.scene.cursor.location.copy()

    def configure(root, label, color, **values):
        root.name = label
        for index, value in enumerate(color):
            root[f"color_{index}"] = value
        for key, value in values.items():
            root[key] = value
        root.update_tag()
        return root

    flash = configure(
        core.create_particle(context, quality),
        "Impact • Core Flash",
        (1.0, 0.6, 0.15),
        duration=3.0,
        count=5,
        shape=1,
        stretch=2.0,
        planar=1.0,
        motion_ease=0.0,
        size=0.42,
        spawn_radius=0.0,
        velocity=0.0,
        gravity=0.0,
        spread=1.0,
        randomness=0.6,
        fade=1.0,
        strength=2.4,
        seed=31,
    )
    _shade_shards(flash)
    flash_shape(flash)
    shards = configure(
        core.create_particle(context, quality),
        "Impact • Main Shards",
        (1.0, 0.22, 0.025),
        duration=18.0,
        count=12,
        shape=1,
        stretch=4.0,
        planar=0.35,
        motion_ease=0.75,
        size=0.11,
        spawn_radius=0.05,
        velocity=3.0,
        motion_seconds=0.55,
        gravity=0.35,
        spread=1.0,
        randomness=0.7,
        fade=1.0,
        strength=1.6,
        seed=17,
    )
    jets(shards, quality)
    wave = configure(
        core.create(context, "SHOCKWAVE", quality),
        "Impact • Shockwave",
        (0.8, 0.09, 0.008),
        start=start + 1,
        duration=18.0,
        radius=0.1,
        expansion=3.0,
        width=0.12,
        strength=1.2,
        dissolve=0.42,
        noise_scale=10.0,
        fade=1.0,
    )
    # Author the wave's erosion in its private material; it follows group retiming.
    cutoff = wave.children[0].data.materials[0].node_tree.nodes["Dissolve Threshold"].inputs[1]
    cutoff.driver_remove("default_value")
    drive(
        cutoff,
        "default_value",
        wave,
        f"min(c+{PROGRESS}*f*0.58,1)",
        dict(TIME_PROPS, c="dissolve", f="fade"),
    )
    wave.location.z -= 0.05
    wave_shape(wave)
    embers = configure(
        core.create_particle(context, quality),
        "Impact • Embers",
        (1.0, 0.065, 0.004),
        start=start + 2,
        duration=22.0,
        count=18,
        shape=1,
        stretch=2.5,
        planar=0.35,
        motion_ease=0.55,
        size=0.034,
        spawn_radius=0.12,
        velocity=2.8,
        motion_seconds=0.7,
        gravity=1.8,
        spread=1.0,
        randomness=0.9,
        fade=1.0,
        strength=1.0,
        seed=29,
    )
    embers.children[0].modifiers[0].node_group.nodes["Shard Narrowing"].inputs[
        1
    ].default_value = -0.5
    group = composition.create(context, [flash, shards, wave, embers])
    group.name = "Impact Burst"
    # Keep the composition origin at the cursor while preserving every member's pose.
    worlds = {root: root.matrix_world.copy() for root in (flash, shards, wave, embers)}
    group.location = origin
    context.view_layer.update()
    for root, world in worlds.items():
        root.matrix_world = world
    group["loop"] = False
    group.update_tag()
    core.select(context, group)
    return group
