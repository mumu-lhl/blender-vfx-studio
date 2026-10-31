"""Editable hit with distinct compression, burning core, pressure and embers."""

from . import composition, core
from .impact_gas import create as gas_core
from .impact_shape import flash as flash_shape
from .impact_shape import jets
from .impact_shape import wave as wave_shape
from .nodes import PROGRESS, TIME_PROPS, drive


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
    flash_shape(flash)
    burst = configure(
        gas_core(context, quality),
        "Impact • Burst Core",
        (1.0, 0.22, 0.025),
        duration=8.0,
        width=1.6,
        height=1.3,
        opacity=1.0,
        fade=0.2,
        strength=2.0,
    )
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
        size=0.16,
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
        expansion=2.0,
        width=0.12,
        strength=1.2,
        dissolve=0.28,
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
    members = [flash, burst, shards, wave, embers]
    group = composition.create(context, members)
    group.name = "Impact Burst"
    # Keep the composition origin at the cursor while preserving every member's pose.
    worlds = {root: root.matrix_world.copy() for root in members}
    group.location = origin
    context.view_layer.update()
    for root, world in worlds.items():
        root.matrix_world = world
    group["loop"] = False
    group.update_tag()
    core.select(context, group)
    return group
