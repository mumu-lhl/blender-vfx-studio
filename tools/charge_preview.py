"""Review the actual Energy Charge starter's lifetime without preview-only glow."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import assets, composition  # noqa: E402
from tools.build_examples import create_effect  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--legacy", action="store_true", help="Restore the old starter's Fade values"
    )
    parser.add_argument("--light", action="store_true")
    parser.add_argument(
        "--sampled", action="store_true", help="Render every other frame plus key review frames"
    )
    parser.add_argument(
        "--frames", type=int, nargs="+", help="Render only these frames for a focused comparison"
    )
    parser.add_argument(
        "--baseline-asset", type=Path, help="Load a complete old asset instead of rebuilding it"
    )
    parser.add_argument("--engine", choices=("CYCLES", "BLENDER_EEVEE"), default="CYCLES")
    parser.add_argument(
        "--view", choices=("default", "front", "side", "high", "far"), default="default"
    )
    parser.add_argument("--view-transform", choices=("Standard", "AgX"), default="Standard")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if args.frames and (min(args.frames) < 1 or args.sampled):
        parser.error(
            "--frames requires positive frame numbers and cannot be combined with --sampled"
        )
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh background process with --factory-startup and no project")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sources = ("tools/build_examples.py", "tools/charge_design.py", "tools/charge_preview.py")
    source_hashes = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources
    }
    root = (
        assets.load(bpy.context, args.baseline_asset)
        if args.baseline_asset
        else create_effect("energy-charge")
    )
    if args.legacy:
        for member in composition.members(root):
            if member["vfx_module"] == "mesh.ring":
                member["fade"] = 0.35
            elif member["vfx_module"] == "shader.shield":
                member["fade"] = 0.0
            if member["vfx_module"] in {"mesh.ring", "shader.shield"}:
                member.children[0].data.materials[0].surface_render_method = "DITHERED"
            member.update_tag()
    scene = bpy.context.scene
    scene.render.fps = 24
    camera = bpy.data.objects.new(
        "Charge Review Camera", bpy.data.cameras.new("Charge Review Camera")
    )
    scene.collection.objects.link(camera)
    views = {
        "default": ((4, -6, 3.5), 7.2),
        "front": ((0, -7, 2.5), 7.2),
        "side": ((7, 0, 2.5), 7.2),
        "high": ((0, -4, 7), 7.2),
        "far": ((4, -6, 3.5), 14.4),
    }
    position, scale = views[args.view]
    camera.location = position
    camera.rotation_euler = (
        (Vector((0, 0, 0.1)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    # The original square thumbnail framing crops the ground rings at 16:9.
    camera.data.type, camera.data.ortho_scale = "ORTHO", scale
    scene.camera = camera
    scene.world = bpy.data.worlds.new("Charge Review Background")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        (0.55, 0.60, 0.68, 1) if args.light else (0.008, 0.012, 0.02, 1)
    )
    scene.render.engine = args.engine
    scene.cycles.device, scene.cycles.samples = "CPU", 24
    scene.cycles.use_denoising = False
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = args.view_transform
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"
    prefix = (
        "baseline-" if args.baseline_asset else "legacy-" if args.legacy else ""
    ) + args.engine.lower()
    prefix += "-light" if args.light else ""
    prefix += f"-{args.view}" if args.view != "default" else ""
    prefix += "-agx" if args.view_transform == "AgX" else ""
    folder = ROOT / "work/visual-charge" / prefix
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / "render-settings.json"
    record.unlink(missing_ok=True)
    frames = {1, 4, 7, 13, 22, 31, 37, 42, 43, 45, 46, 48, 49}
    if args.sampled:
        frames.update(range(1, 50, 2))
    if args.frames:
        frames = set(args.frames)
    for frame in sorted(frames):
        scene.frame_set(frame)
        scene.render.filepath = str(folder / f"charge-{prefix}-{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    scene.frame_set(31)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "charge.blend"))
    if source_hashes != {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources
    }:
        raise RuntimeError("Source changed during rendering; rerender a frozen revision")
    record.write_text(
        json.dumps(
            {
                "engine": args.engine,
                "light": args.light,
                "view": args.view,
                "camera_position": list(camera.location),
                "camera_target": [0, 0, 0.1],
                "ortho_scale": camera.data.ortho_scale,
                "color_management": {
                    "view_transform": scene.view_settings.view_transform,
                    "look": scene.view_settings.look,
                    "exposure": scene.view_settings.exposure,
                    "gamma": scene.view_settings.gamma,
                },
                "resolution": [960, 540],
                "fps": scene.render.fps,
                "rendered_frames": sorted(frames),
                "saved_frame": 31,
                "source_sha256": source_hashes,
                "baseline_sha256": hashlib.sha256(args.baseline_asset.read_bytes()).hexdigest()
                if args.baseline_asset
                else None,
                "inspection": "rendering does not automatically approve visual quality",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
