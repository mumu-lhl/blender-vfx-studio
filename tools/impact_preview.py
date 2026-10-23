"""Render the actual Impact Burst in three stages at 960x540, without bloom."""

import argparse
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import composition, core  # noqa: E402


def legacy_effect():
    ring = core.create(bpy.context, "SHOCKWAVE", "LOW")
    particles = core.create_particle(bpy.context, asset_version=1)
    for root, values in (
        (ring, dict(radius=0.15, expansion=3.2, width=0.2, dissolve=0.15)),
        (
            particles,
            dict(
                count=40,
                velocity=3.0,
                gravity=1.8,
                motion_seconds=0.75,
                size=0.07,
                spawn_radius=0.08,
                spread=0.85,
                randomness=0.7,
                seed=17,
            ),
        ),
    ):
        for key, value in dict(
            values, duration=24.0, strength=4.0, fade=1.0, color_0=1.0, color_1=0.15, color_2=0.015
        ).items():
            root[key] = value
        root.update_tag()
    group = composition.create(bpy.context, [ring, particles])
    group["loop"] = False
    group.update_tag()
    return group


def setup(*, legacy=False, engine="CYCLES", light=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    root = legacy_effect() if legacy else core.create(bpy.context, "IMPACT_BURST", "LOW")
    scene = bpy.context.scene
    camera = bpy.data.objects.new("Acceptance Camera", bpy.data.cameras.new("Acceptance Camera"))
    scene.collection.objects.link(camera)
    camera.location = (3, -5, 6)
    camera.rotation_euler = (-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type, camera.data.ortho_scale = "ORTHO", 8.2
    scene.camera = camera
    scene.world = bpy.data.worlds.new("Neutral Background")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        (0.18, 0.20, 0.24, 1) if light else (0.008, 0.012, 0.02, 1)
    )
    scene.render.engine = engine
    scene.cycles.device, scene.cycles.samples = "CPU", 24
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    return root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", action="store_true")
    parser.add_argument("--light", action="store_true")
    parser.add_argument("--engine", choices=("CYCLES", "BLENDER_EEVEE"), default="CYCLES")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh background process with --factory-startup and no project")
    setup(legacy=args.legacy, engine=args.engine, light=args.light)
    folder = ROOT / "work/visual-impact"
    folder.mkdir(parents=True, exist_ok=True)
    prefix = "legacy" if args.legacy else args.engine.lower()
    prefix += "-light" if args.light else ""
    for stage, frame in (("appear", 2), ("peak", 5), ("decay", 14)):
        bpy.context.scene.frame_set(frame)
        bpy.context.scene.render.filepath = str(folder / f"impact-{prefix}-{stage}.png")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / f"impact-{prefix}.blend"))


if __name__ == "__main__":
    main()
