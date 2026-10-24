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


SEQUENCE_PARAMETERS = {
    key: spec for key, spec in FLIPBOOK_PARAMETERS.items() if key not in {"columns", "rows"}
}
SEQUENCE_PARAMETERS["last_frame"] = (
    15,
    0,
    4095,
    "Last image index relative to the selected first file",
)
SEQUENCE_PARAMETERS["first_frame"] = (
    0,
    0,
    4095,
    "First image index relative to the selected first file",
)

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


PARTICLE_PARAMETERS_V1 = {
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


EMITTER_PARAMETERS = {
    key: spec
    for key, spec in PARTICLE_PARAMETERS_V1.items()
    if key not in {"count", "motion_seconds"}
}
EMITTER_PARAMETERS.update(
    {
        "duration": (48.0, 1.0, 100000.0, "Playback frames for emission plus the lifetime tail"),
        "rate": (
            64.0,
            0.0,
            10000.0,
            "Requested particles per motion second; limited by the 2048-slot pool",
        ),
        "emission_seconds": (1.5, 0.0, 100.0, "Motion seconds during which particles are born"),
        "lifetime": (0.6, 0.001, 100.0, "Individual particle lifetime in motion seconds"),
        "fade": (1.0, 0.0, 1.0, "Size loss over each particle's own lifetime"),
    }
)


PARTICLE_PARAMETERS = {
    **PARTICLE_PARAMETERS_V1,
    "shape": (0, 0, 1, "0: round particle; 1: pointed shard"),
    "stretch": (1.0, 1.0, 24.0, "Shard half-length as a multiple of Size"),
    "planar": (0.0, 0.0, 1.0, "Flatten random directions into local XY before applying Spread"),
    "motion_ease": (0.0, 0.0, 1.0, "Fast initial travel followed by deceleration; zero is linear"),
}


TRAIL_PARAMETERS = {
    **COMMON_PARAMETERS,
    "width": (0.2, 0.001, 100.0, "Full ribbon width"),
    "length": (0.35, 0.001, 1.0, "Visible trailing fraction of the sampled timeline"),
    "fade": (0.0, 0.0, 1.0, "Width loss over lifetime"),
}


SLASH_PARAMETERS_V1 = {
    **PARAMETERS,
    "radius": (1.8, 0.001, 10000.0, "Outer radius at birth"),
    "width": (0.45, 0.001, 10000.0, "Maximum radial width"),
    "expansion": (0.2, 0.0, 10000.0, "Added radius over lifetime"),
    "duration": (16.0, 1.0, 100000.0, "Lifetime in frames at speed 1"),
    "dissolve": (0.15, 0.0, 1.0, "Noise cutoff; 1 fully dissolves"),
    "arc": (150.0, 1.0, 359.0, "Arc angle in degrees, centered on local +X"),
    "spin": (120.0, -1440.0, 1440.0, "Rotation in degrees over lifetime"),
    "taper": (0.5, 0.01, 4.0, "Tip narrowing; larger values make a thinner crescent"),
}

SLASH_PARAMETERS_V2 = {
    **SLASH_PARAMETERS_V1,
    "width": (0.62, 0.001, 10000.0, "Maximum body width"),
    "arc": (185.0, 1.0, 359.0, "Sweep angle centered on local +X"),
    "spin": (105.0, -1440.0, 1440.0, "Total sweep rotation"),
    "strength": (2.2, 0.0, 1000.0, "Blade emission; body and wake stay dimmer"),
    "color_0": (0.32, 0.0, 1.0, "Linear body red"),
    "color_1": (0.035, 0.0, 1.0, "Linear body green"),
    "color_2": (0.8, 0.0, 1.0, "Linear body blue"),
    "attack": (0.18, 0.02, 0.5, "Fraction of lifetime used to reveal the blade"),
    "motion_ease": (0.85, 0.0, 1.0, "Sweep deceleration; zero gives linear motion"),
    "head_bias": (0.7, 0.0, 1.0, "Move body weight toward the leading tip"),
    "core_width": (0.12, 0.02, 0.4, "Bright blade width relative to body"),
    "afterimage": (0.28, 0.0, 1.0, "Opacity of two subordinate native wake ribbons"),
    "streaks": (0.65, 0.0, 1.0, "Anisotropic filament contrast in the body"),
    "breakup": (0.75, 0.0, 1.0, "Directional noise erosion after the strike"),
}

SLASH_PARAMETERS = {
    **SLASH_PARAMETERS_V2,
    "strength": (1.6, 0.0, 1000.0, "Blade emission; illustrated body stays darker"),
    "contour": (0.65, 0.0, 1.0, "Uneven leading hook and torn inner silhouette"),
    "bank": (0.22, -1.0, 1.0, "Depth bend relative to radius; zero flattens the blade"),
    "wake_spread": (0.7, 0.0, 1.0, "Wake separation during the sweep and release"),
}

SHIELD_PARAMETERS = {
    **COMMON_PARAMETERS,
    "loop": (True, None, None, "Repeat shield animation; hidden before start"),
    "fade": (0.0, 0.0, 1.0, "Opacity loss over lifetime"),
    "radius": (1.5, 0.001, 10000.0, "Sphere radius at birth"),
    "expansion": (0.0, 0.0, 10000.0, "Added radius over lifetime"),
    "opacity": (0.85, 0.0, 1.0, "Maximum exterior surface opacity"),
    "ior": (
        1.15,
        1.001,
        3.0,
        "Index of refraction; larger values strengthen the face-on reflection",
    ),
    "rim_power": (0.5, 0.05, 8.0, "Fresnel power; larger values narrow the bright rim"),
    "strength": (3.0, 0.0, 1000.0, "Emission strength; glow requires a compositor"),
    "dissolve": (0.15, 0.0, 1.0, "Noise cutoff; 1 fully dissolves"),
    "noise_scale": (6.0, 0.01, 1000.0, "Generated-coordinate noise scale"),
    "flow": (2.0, -100.0, 100.0, "Noise evolution over one lifetime; zero holds still"),
}

SIMULATION_PARAMETERS = {key: spec for key, spec in COMMON_PARAMETERS.items() if key != "fade"}

GROUP_PARAMETERS = {key: PARAMETERS[key] for key in ("start", "duration", "speed", "loop")}


def parameters_for(module, asset_version=None):
    if module == "particle.emitter":
        return EMITTER_PARAMETERS
    if module == "flipbook.sequence":
        return SEQUENCE_PARAMETERS
    if module == "shader.shield":
        return SHIELD_PARAMETERS
    if module == "mesh.slash":
        return {1: SLASH_PARAMETERS_V1, 2: SLASH_PARAMETERS_V2}.get(asset_version, SLASH_PARAMETERS)
    if module == "simulation.cloth":
        return SIMULATION_PARAMETERS
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
        return PARTICLE_PARAMETERS_V1 if asset_version == 1 else PARTICLE_PARAMETERS
    raise ValueError("Unknown VFX module")


def preset_parameters_for(module, asset_version=None):
    return {
        key: spec for key, spec in parameters_for(module, asset_version).items() if key != "start"
    }
