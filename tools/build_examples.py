"""Build three native starter assets and embedded CPU previews in a fresh process."""

import math
import os
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import assets, composition, core  # noqa: E402

EXAMPLES = ("energy-charge", "impact-burst", "arc-slash")
PREVIEWS = {
    "energy-charge": (22, (4, -6, 3.5), (0, 0, 0.1), 4.8),
    "impact-burst": (10, (5, -7, 4), (0, 0, 0.2), 4.8),
    "arc-slash": (7, (0, 0, 8), (0, 0, 0), 5.0),
}


def configure(root, color, **values):
    for i, value in enumerate(color):
        root[f"color_{i}"] = value
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    return root


def create_effect(key):
    if key not in EXAMPLES:
        raise ValueError("Unknown starter effect")
    context = bpy.context
    context.scene.frame_set(1)
    if key == "energy-charge":
        color = (0.03, 0.45, 1.0)
        outer = configure(
            core.create(context, "ENERGY_RING", "LOW"),
            color,
            radius=1.6,
            width=0.065,
            duration=48.0,
            strength=3.5,
            dissolve=0.12,
            fade=0.35,
        )
        outer.location.z = -0.8
        inner = configure(
            core.create(context, "ENERGY_RING", "LOW"),
            color,
            radius=1.35,
            width=0.025,
            duration=48.0,
            strength=3.5,
            dissolve=0.08,
            fade=0.35,
        )
        inner.location.z = -0.8
        shield = configure(
            core.create_shield(context, "LOW"),
            color,
            radius=1.0,
            opacity=0.45,
            strength=2.5,
            ior=1.05,
            rim_power=1.2,
            dissolve=0.2,
            flow=1.2,
            duration=48.0,
        )
        particles = configure(
            core.create_emitter(context),
            color,
            rate=18.0,
            lifetime=0.8,
            emission_seconds=1.2,
            duration=48.0,
            velocity=1.7,
            gravity=0.15,
            spread=0.8,
            spawn_radius=0.5,
            size=0.035,
            strength=3.0,
            seed=9,
        )
        particles.location.z = -0.5
        root = composition.create(context, [outer, inner, shield, particles])
        root.name = "Energy Charge"
    elif key == "impact-burst":
        color = (1.0, 0.15, 0.015)
        ring = configure(
            core.create(context, "SHOCKWAVE", "LOW"),
            color,
            radius=0.15,
            expansion=3.2,
            width=0.2,
            duration=24.0,
            fade=1.0,
            dissolve=0.15,
            strength=4.0,
        )
        particles = configure(
            core.create_particle(context),
            color,
            count=40,
            velocity=3.0,
            gravity=1.8,
            motion_seconds=0.75,
            size=0.07,
            spawn_radius=0.08,
            spread=0.85,
            randomness=0.7,
            strength=4.0,
            fade=1.0,
            duration=24.0,
            seed=17,
        )
        root = composition.create(context, [ring, particles])
        root.name = "Impact Burst"
    else:
        root = configure(
            core.create(context, "ARC_SLASH", "LOW"),
            (0.6, 0.06, 1.0),
            radius=1.8,
            width=0.5,
            arc=200.0,
            spin=165.0,
            taper=0.65,
            expansion=0.3,
            duration=18.0,
            strength=4.0,
            dissolve=0.12,
            noise_scale=7.0,
            fade=0.8,
        )
        root.rotation_euler.z = math.radians(-30)
        root.name = "Arc Slash"
    root["loop"] = False
    root.update_tag()
    context.view_layer.update()
    return root


def preview_scene(key):
    """Preview-only helpers are deliberately outside the exported effect hierarchy."""
    scene = bpy.context.scene
    frame, location, target, scale = PREVIEWS[key]
    bpy.ops.object.camera_add(location=location)
    camera = bpy.context.object
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type, camera.data.ortho_scale = "ORTHO", scale
    scene.camera = camera
    scene.world = bpy.data.worlds.new("Starter Preview Background")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.003,
        0.005,
        0.008,
        1,
    )
    scene.render.engine = "CYCLES"
    scene.cycles.device, scene.cycles.samples = "CPU", 32
    scene.render.compositor_device = "CPU"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    glow = core.create_screen(bpy.context)
    glow["strength"], glow["fade"] = 0.25, 0.0
    glow.update_tag()
    scene.frame_set(frame)


def main():
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError(
            "Use a fresh background process with --factory-startup and no open project"
        )
    version = tomllib.loads(
        (ROOT / "blender_vfx_studio/blender_manifest.toml").read_text(encoding="utf-8")
    )["version"]
    output = ROOT / "dist/examples"
    previews = ROOT / "work/examples"
    output.mkdir(parents=True, exist_ok=True)
    previews.mkdir(parents=True, exist_ok=True)
    files = []
    for key in EXAMPLES:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        root = create_effect(key)
        preview_scene(key)
        path = previews / (key + ".png")
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(path), check_existing=False)
        destination = output / (key + ".blend")
        assets.write(destination, root, preview_image=image)
        files.append(destination)
        print("STARTER_ASSET_BUILT", key, flush=True)
    guide = ROOT / "docs/STARTER_LIBRARY.md"
    destination = ROOT / "dist" / f"blender-vfx-studio-examples-{version}.zip"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", dir=destination.parent, delete=False) as f:
            temporary = Path(f.name)
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.name)
            archive.write(guide, "README.md")
            archive.write(ROOT / "LICENSE", "LICENSE")
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print("STARTER_LIBRARY_BUILT", destination)


if __name__ == "__main__":
    main()
