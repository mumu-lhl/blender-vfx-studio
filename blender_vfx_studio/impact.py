"""Editable four-layer hit: short flash, directional shards, wave and embers."""

from . import composition, core
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
        (0.8, 0.9, 1),
        duration=7.0,
        count=5,
        shape=1,
        stretch=2.4,
        planar=1.0,
        motion_ease=0.0,
        size=0.18,
        spawn_radius=0.0,
        velocity=0.0,
        gravity=0.0,
        spread=1.0,
        randomness=0.6,
        fade=1.0,
        strength=2.4,
        seed=31,
    )
    shards = configure(
        core.create_particle(context, quality),
        "Impact • Main Shards",
        (1.0, 0.22, 0.025),
        duration=18.0,
        count=12,
        shape=1,
        stretch=6.0,
        planar=0.9,
        motion_ease=0.75,
        size=0.07,
        spawn_radius=0.05,
        velocity=3.0,
        motion_seconds=0.55,
        gravity=0.35,
        spread=1.0,
        randomness=0.7,
        fade=1.0,
        strength=2.0,
        seed=17,
    )
    wave = configure(
        core.create(context, "SHOCKWAVE", quality),
        "Impact • Shockwave",
        (0.8, 0.09, 0.008),
        start=start + 1,
        duration=18.0,
        radius=0.1,
        expansion=2.5,
        width=0.055,
        strength=1.2,
        dissolve=0.35,
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
        f"min(c+{PROGRESS}*f*0.65,1)",
        dict(TIME_PROPS, c="dissolve", f="fade"),
    )
    wave.location.z -= 0.05
    embers = configure(
        core.create_particle(context, quality),
        "Impact • Embers",
        (1.0, 0.065, 0.004),
        start=start + 2,
        duration=22.0,
        count=18,
        shape=1,
        stretch=2.5,
        planar=0.65,
        motion_ease=0.3,
        size=0.024,
        spawn_radius=0.12,
        velocity=3.8,
        motion_seconds=0.7,
        gravity=1.8,
        spread=1.0,
        randomness=0.9,
        fade=1.0,
        strength=1.0,
        seed=29,
    )
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
