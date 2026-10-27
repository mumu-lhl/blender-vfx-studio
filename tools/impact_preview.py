"""Render the actual Impact Burst in three stages at 960x540, without bloom."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import assets, core  # noqa: E402


def setup(
    *,
    engine="CYCLES",
    light=False,
    baseline_asset=None,
    pale=False,
    far=False,
    view_transform="Standard",
    view="default",
):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    root = (
        assets.load(bpy.context, baseline_asset)
        if baseline_asset
        else core.create(bpy.context, "IMPACT_BURST", "LOW")
    )
    scene = bpy.context.scene
    camera = bpy.data.objects.new("Acceptance Camera", bpy.data.cameras.new("Acceptance Camera"))
    scene.collection.objects.link(camera)
    camera.location = {
        "default": (3, -5, 6),
        "front": (0, -8, 1.5),
        "side": (8, 0, 1.5),
        "high": (0.1, 0, 8),
    }[view]
    camera.rotation_euler = (-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type, camera.data.ortho_scale = "ORTHO", 14 if far else 8.2
    scene.camera = camera
    scene.world = bpy.data.worlds.new("Neutral Background")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        (0.72, 0.76, 0.8, 1)
        if pale
        else (0.18, 0.20, 0.24, 1)
        if light
        else (0.008, 0.012, 0.02, 1)
    )
    scene.render.engine = engine
    scene.cycles.device, scene.cycles.samples = "CPU", 24
    scene.cycles.use_denoising = False
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.frame_start, scene.frame_end, scene.render.fps = 1, 25, 24
    scene.view_settings.view_transform = view_transform
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"
    return root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--light", action="store_true")
    parser.add_argument("--pale", action="store_true")
    parser.add_argument("--far", action="store_true")
    parser.add_argument("--view-transform", choices=("Standard", "AgX"), default="Standard")
    parser.add_argument("--view", choices=("default", "front", "side", "high"), default="default")
    parser.add_argument("--baseline-asset", type=Path, help="Import an actual old complete effect")
    parser.add_argument("--sampled", action="store_true")
    parser.add_argument("--sequence", action="store_true", help="Render all 25 frames for playback")
    parser.add_argument("--frames", type=int, nargs="+")
    parser.add_argument("--engine", choices=("CYCLES", "BLENDER_EEVEE"), default="CYCLES")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh background process with --factory-startup and no project")
    if sum((args.sampled, args.sequence, bool(args.frames))) > 1:
        parser.error("Choose one effect source and one frame selection")
    if args.frames and min(args.frames) < 1:
        parser.error("Frames must be positive")
    sources = [
        "blender_vfx_studio/" + name + ".py"
        for name in ("impact", "impact_shape", "particle", "particle_shape", "nodes", "composition")
    ]
    sources.append("tools/impact_preview.py")

    def hashes():
        return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources}

    source_hashes = hashes()
    setup(
        engine=args.engine,
        light=args.light,
        baseline_asset=args.baseline_asset,
        pale=args.pale,
        far=args.far,
        view_transform=args.view_transform,
        view=args.view,
    )
    folder = ROOT / "work/visual-impact"
    folder.mkdir(parents=True, exist_ok=True)
    prefix = args.engine.lower()
    prefix += "-light" if args.light else ""
    prefix += "-baseline" if args.baseline_asset else ""
    prefix += "-pale" if args.pale else ""
    prefix += "-far" if args.far else ""
    prefix += "-agx" if args.view_transform == "AgX" else ""
    prefix += f"-{args.view}" if args.view != "default" else ""
    stages = [("appear", 2), ("peak", 5), ("decay", 14)]
    if args.sequence or args.sampled or args.frames:
        frames = (
            list(range(1, 26))
            if args.sequence
            else [1, 2, 3, 5, 7, 9, 11, 14, 17, 21, 24, 25]
            if args.sampled
            else sorted(set(args.frames))
        )
        stages = [(f"{frame:04d}", frame) for frame in frames]
    record = folder / f"impact-{prefix}-settings.json"
    record.unlink(missing_ok=True)
    for stage, frame in stages:
        bpy.context.scene.frame_set(frame)
        bpy.context.scene.render.filepath = str(folder / f"impact-{prefix}-{stage}.png")
        bpy.ops.render.render(write_still=True)
    bpy.context.scene.frame_set(5)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / f"impact-{prefix}.blend"))
    if hashes() != source_hashes:
        raise RuntimeError("Builder changed during rendering; repeat this review")
    scene = bpy.context.scene
    record.write_text(
        json.dumps(
            {
                "effect": "impact-burst",
                "engine": args.engine,
                "frames": [frame for stage, frame in stages],
                "images": {str(frame): f"impact-{prefix}-{stage}.png" for stage, frame in stages},
                "source_sha256": source_hashes,
                "baseline_sha256": hashlib.sha256(args.baseline_asset.read_bytes()).hexdigest()
                if args.baseline_asset
                else None,
                "resolution": [960, 540],
                "fps": scene.render.fps,
                "fps_base": scene.render.fps_base,
                "saved_frame": scene.frame_current,
                "camera_location": list(scene.camera.location),
                "view": args.view,
                "ortho_scale": scene.camera.data.ortho_scale,
                "background_color": list(
                    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value
                ),
                "view_transform": scene.view_settings.view_transform,
                "realtime_playback_reviewed": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
