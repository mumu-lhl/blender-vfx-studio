"""Small module/preset catalog; builders remain lazy bpy imports."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    id: str
    label: str
    asset_version: int
    stateful: bool = False


MODULES = {
    "flipbook.sequence": Module("flipbook.sequence", "Image Sequence Sprite", 1),
    "shader.shield": Module("shader.shield", "Fresnel Energy Shield", 1),
    "mesh.slash": Module("mesh.slash", "Arc Slash", 1),
    "simulation.cloth": Module("simulation.cloth", "Cloth Energy Sheet", 1, stateful=True),
    "core.composition": Module("core.composition", "VFX Composition", 1),
    "trail.ribbon": Module("trail.ribbon", "Sampled Ribbon Trail", 1),
    "mesh.ring": Module("mesh.ring", "Procedural Ring", 1),
    "flipbook.atlas": Module("flipbook.atlas", "Flipbook Atlas", 1),
    "particle.burst": Module("particle.burst", "Particle Burst", 1),
    "screen.glare": Module("screen.glare", "Screen Glare + Flash", 1),
}
PRESETS = {
    "ARC_SLASH": {"label": "Arc Slash"},
    "SHOCKWAVE": {
        "label": "Shockwave",
        "radius": 0.2,
        "width": 0.18,
        "expansion": 3.0,
        "duration": 24.0,
        "strength": 8.0,
        "dissolve": 0.25,
        "fade": 1.0,
        "color": (0.08, 0.5, 1.0),
    },
    "ENERGY_RING": {
        "label": "Energy Ring",
        "radius": 1.5,
        "width": 0.14,
        "expansion": 0.0,
        "duration": 48.0,
        "strength": 6.0,
        "dissolve": 0.3,
        "fade": 0.0,
        "color": (0.6, 0.08, 1.0),
    },
}
