"""Render actual default slashes at emergence, peak and decay, without bloom."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import core  # noqa: E402


def setup(
    *,
    engine="CYCLES",
    light=False,
    angled=False,
    far=False,
    pale=False,
    view_transform="Standard",
):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    root = core.create(bpy.context, "ARC_SLASH")
    root["duration"], root["loop"] = 18.0, False
    root.update_tag()
    camera = bpy.data.objects.new("Acceptance Camera", bpy.data.cameras.new("Acceptance Camera"))
    scene.collection.objects.link(camera)
    camera.location = (3, -4, 7) if angled else (0, 0, 8)
    camera.rotation_euler = (
        (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    camera.data.type, camera.data.ortho_scale = "ORTHO", 14 if far else 9.2
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
    if pale:
        scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
            0.72,
            0.76,
            0.8,
            1,
        )
    scene.render.engine = engine
    scene.cycles.device, scene.cycles.samples = "CPU", 24
    scene.cycles.use_denoising = False
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = view_transform
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"
    return root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--light", action="store_true")
    parser.add_argument("--pale", action="store_true", help="Near-white background instead of gray")
    parser.add_argument("--view-transform", choices=("Standard", "AgX"), default="Standard")
    parser.add_argument("--engine", choices=("CYCLES", "BLENDER_EEVEE"), default="CYCLES")
    parser.add_argument("--sampled", action="store_true", help="Render every other frame plus peak")
    parser.add_argument("--frames", type=int, nargs="+")
    parser.add_argument("--angled", action="store_true", help="Review the native blade depth")
    parser.add_argument("--far", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh background process with --factory-startup and no project")
    if args.sampled and args.frames:
        parser.error("Choose one frame selection and one asset version")
    if args.frames and min(args.frames) < 1:
        parser.error("Frames must be positive")
    sources = [
        "blender_vfx_studio/" + name + ".py"
        for name in ("slash", "slash_shape", "slash_shader", "parameters", "registry")
    ]
    sources.append("tools/slash_preview.py")

    def hashes():
        return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources}

    source_hashes = hashes()
    root = setup(
        engine=args.engine,
        light=args.light,
        angled=args.angled,
        far=args.far,
        pale=args.pale,
        view_transform=args.view_transform,
    )
    folder = ROOT / "work/visual-slash"
    folder.mkdir(parents=True, exist_ok=True)
    prefix = args.engine.lower()
    prefix += "-light" if args.light else ""
    prefix += "-angled" if args.angled else ""
    prefix += "-far" if args.far else ""
    prefix += "-pale" if args.pale else ""
    prefix += "-agx" if args.view_transform == "AgX" else ""
    stages = [("appear", 2), ("peak", 5), ("decay", 11)]
    if args.sampled or args.frames:
        frames = sorted(set(range(1, 20, 2)) | {2, 5}) if args.sampled else sorted(set(args.frames))
        stages = [(f"{frame:04d}", frame) for frame in frames]
    record = folder / f"slash-{prefix}-settings.json"
    record.unlink(missing_ok=True)
    for stage, frame in stages:
        bpy.context.scene.frame_set(frame)
        bpy.context.scene.render.filepath = str(folder / f"slash-{prefix}-{stage}.png")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / f"slash-{prefix}.blend"))
    if hashes() != source_hashes:
        raise RuntimeError("Builder changed during rendering; repeat this review")
    record.write_text(
        json.dumps(
            {
                "asset_version": root["vfx_asset_version"],
                "engine": args.engine,
                "light_background": args.light or args.pale,
                "background_color": list(
                    bpy.context.scene.world.node_tree.nodes["Background"]
                    .inputs["Color"]
                    .default_value
                ),
                "frames": [frame for stage, frame in stages],
                "images": {str(frame): f"slash-{prefix}-{stage}.png" for stage, frame in stages},
                "resolution": [960, 540],
                "source_sha256": source_hashes,
                "camera_location": list(bpy.context.scene.camera.location),
                "ortho_scale": bpy.context.scene.camera.data.ortho_scale,
                "view_transform": bpy.context.scene.view_settings.view_transform,
                "realtime_playback_reviewed": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
