"""Render actual default slashes at emergence, peak and decay, without bloom."""

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import core, slash  # noqa: E402


def setup(*, legacy=False, engine="CYCLES", light=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    root = (
        slash.create(bpy.context, asset_version=1)
        if legacy
        else core.create(bpy.context, "ARC_SLASH")
    )
    root["duration"], root["loop"] = 18.0, False
    root.update_tag()
    camera = bpy.data.objects.new("Acceptance Camera", bpy.data.cameras.new("Acceptance Camera"))
    scene.collection.objects.link(camera)
    camera.location = (0, 0, 8)
    camera.rotation_euler = (
        (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    camera.data.type, camera.data.ortho_scale = "ORTHO", 9.2
    scene.camera = camera
    scene.world = bpy.data.worlds.new("Neutral Navy")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.008,
        0.012,
        0.02,
        1,
    )
    if light:
        scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
            0.18,
            0.20,
            0.24,
            1,
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
    folder = ROOT / "work/visual-slash"
    folder.mkdir(parents=True, exist_ok=True)
    prefix = "legacy" if args.legacy else args.engine.lower()
    prefix += "-light" if args.light else ""
    for stage, frame in (("appear", 2), ("peak", 5), ("decay", 11)):
        bpy.context.scene.frame_set(frame)
        bpy.context.scene.render.filepath = str(folder / f"slash-{prefix}-{stage}.png")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / f"slash-{prefix}.blend"))


if __name__ == "__main__":
    main()
