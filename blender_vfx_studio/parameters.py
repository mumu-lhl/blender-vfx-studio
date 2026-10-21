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
