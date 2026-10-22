"""Persistent ring parameter metadata; no Blender dependency."""

# key: (default, min, max, description). ID properties survive UI unregistration.
PARAMETERS = {
    "start": (1.0, -100000.0, 100000.0, "Start frame"),
    "duration": (24.0, 1.0, 100000.0, "Lifetime in frames at speed 1"),
    "speed": (1.0, 0.001, 1000.0, "Playback multiplier"),
    "loop": (False, None, None, "Repeat after duration; hidden before start"),
    "radius": (0.2, 0.001, 10000.0, "Outer radius at birth"),
    "width": (0.18, 0.001, 10000.0, "Ring width; inner radius clamps above zero"),
    "expansion": (3.0, 0.0, 10000.0, "Added radius over one lifetime"),
    "strength": (8.0, 0.0, 1000.0, "Emission strength"),
    "dissolve": (0.25, 0.0, 1.0, "Noise cutoff; 1 fully dissolves"),
    "noise_scale": (8.0, 0.01, 1000.0, "UV noise scale"),
    "fade": (1.0, 0.0, 1.0, "Opacity loss over lifetime"),
    "color_0": (0.08, 0.0, 1.0, "Linear red"),
    "color_1": (0.5, 0.0, 1.0, "Linear green"),
    "color_2": (1.0, 0.0, 1.0, "Linear blue"),
}

# Keep the original ring schema unchanged for saved instances and v1 presets.
COMMON_PARAMETERS = {
    key: PARAMETERS[key]
    for key in (
        "start",
        "duration",
        "speed",
        "loop",
        "strength",
        "fade",
        "color_0",
        "color_1",
        "color_2",
    )
}
FLIPBOOK_PARAMETERS = {
    **COMMON_PARAMETERS,
    "strength": (1.0, 0.0, 1000.0, "Emission strength"),
    "fade": (0.0, 0.0, 1.0, "Opacity loss over lifetime"),
    "color_0": (1.0, 0.0, 1.0, "Linear red tint"),
    "color_1": (1.0, 0.0, 1.0, "Linear green tint"),
    "color_2": (1.0, 0.0, 1.0, "Linear blue tint"),
    "columns": (4, 1, 256, "Atlas column count"),
    "rows": (4, 1, 256, "Atlas row count"),
    "first_frame": (0, 0, 65535, "First atlas cell, zero-based from top left"),
    "last_frame": (15, 0, 65535, "Last atlas cell, inclusive; clamps to grid"),
    "width": (2.0, 0.001, 10000.0, "Sprite width"),
    "height": (2.0, 0.001, 10000.0, "Sprite height"),
    "opacity": (1.0, 0.0, 1.0, "Sprite opacity"),
}


SCREEN_PARAMETERS = {
    **COMMON_PARAMETERS,
    "duration": (24.0, 1.0, 100000.0, "Flash lifetime in frames at speed 1"),
    "loop": (True, None, None, "Repeat screen effect and flash"),
    "strength": (0.3, 0.0, 100.0, "Glare strength during lifetime"),
    "fade": (1.0, 0.0, 1.0, "Flash fade over lifetime"),
    "color_0": (1.0, 0.0, 1.0, "Flash red"),
    "color_1": (1.0, 0.0, 1.0, "Flash green"),
    "color_2": (1.0, 0.0, 1.0, "Flash blue"),
    "threshold": (1.0, 0.0, 10000.0, "Glare highlight threshold"),
    "glow_size": (0.25, 0.0, 1.0, "Glare size"),
    "flash": (0.0, 0.0, 1.0, "Flash overlay opacity at birth"),
}


PARTICLE_PARAMETERS = {
    **COMMON_PARAMETERS,
    "strength": (4.0, 0.0, 1000.0, "Particle emission strength"),
    "color_0": (1.0, 0.0, 1.0, "Linear red"),
    "color_1": (0.35, 0.0, 1.0, "Linear green"),
    "color_2": (0.04, 0.0, 1.0, "Linear blue"),
    "count": (64, 1, 2048, "Particle count; bounded to 2048 at evaluation"),
    "seed": (1, 0, 1000000, "Deterministic random seed"),
    "motion_seconds": (
        1.0,
        0.001,
        100.0,
        "Physical trajectory time; timeline stretches this motion",
    ),
    "velocity": (3.0, 0.0, 100.0, "Initial velocity in units per motion second"),
    "gravity": (2.0, 0.0, 1000.0, "Downward acceleration in units per motion second squared"),
    "spread": (1.0, 0.0, 1.0, "Direction spread: zero points up, one covers all directions"),
    "randomness": (0.5, 0.0, 1.0, "Velocity and size variation"),
    "spawn_radius": (0.05, 0.0, 1000.0, "Initial radial offset"),
    "size": (0.06, 0.001, 100.0, "Particle radius at birth"),
}


TRAIL_PARAMETERS = {
    **COMMON_PARAMETERS,
    "width": (0.2, 0.001, 100.0, "Full ribbon width"),
    "length": (0.35, 0.001, 1.0, "Visible trailing fraction of the sampled timeline"),
    "fade": (0.0, 0.0, 1.0, "Width loss over lifetime"),
}


GROUP_PARAMETERS = {key: PARAMETERS[key] for key in ("start", "duration", "speed", "loop")}


def parameters_for(module):
    if module == "core.composition":
        return GROUP_PARAMETERS
    if module == "trail.ribbon":
        return TRAIL_PARAMETERS
    if module == "mesh.ring":
        return PARAMETERS
    if module == "flipbook.atlas":
        return FLIPBOOK_PARAMETERS
    if module == "screen.glare":
        return SCREEN_PARAMETERS
    if module == "particle.burst":
        return PARTICLE_PARAMETERS
    raise ValueError("Unknown VFX module")


def preset_parameters_for(module):
    return {key: spec for key, spec in parameters_for(module).items() if key != "start"}
