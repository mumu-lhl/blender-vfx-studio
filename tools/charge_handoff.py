"""Inspect real charge/slash/hit overlap with the existing neutral combat proxies."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio.animation import curves  # noqa: E402
from tools.build_examples import create_effect  # noqa: E402
from tools.combat_preview import setup  # noqa: E402

FRAMES = (1, 7, 13, 19, 25, 26, 27, 28, 29, 30, 31, 32, 33, 37, 45, 55, 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--light", action="store_true")
    parser.add_argument("--engine", choices=("CYCLES", "BLENDER_EEVEE"), default="CYCLES")
    parser.add_argument("--sequence", action="store_true", help="Render all 60 frames at 24 fps")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh background process with --factory-startup and no project")
    sources = sorted((ROOT / "blender_vfx_studio").rglob("*.py")) + [
        ROOT / "tools" / name
        for name in (
            "build_examples.py",
            "charge_design.py",
            "combat_preview.py",
            "charge_handoff.py",
        )
    ]
    sources.append(ROOT / "blender_vfx_studio/blender_manifest.toml")

    def hashes():
        return {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sources
        }

    source_hashes = hashes()
    slash, impact = setup(light=args.light, engine=args.engine)
    scene = bpy.context.scene
    slash["start"], impact["start"] = 27.0, 31.0
    slash.update_tag()
    impact.update_tag()
    for curve in curves(bpy.data.objects["Weapon timing proxy"]):
        for key in curve.keyframe_points:
            key.co.x += 24
            key.handle_left.x += 24
            key.handle_right.x += 24
        curve.update()
    for marker in scene.timeline_markers:
        marker.frame += 24
    scene.cursor.location = (0, 0, 0)
    charge = create_effect("energy-charge")
    charge.location = (-1, 0, 0.92)
    charge["duration"] = 32.0
    charge.update_tag()
    scene.timeline_markers.new("Charge begins", frame=1)
    scene.frame_end = 60
    variant = args.engine.lower() + ("-light" if args.light else "-dark")
    folder = ROOT / "work/charge-handoff" / variant
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / "review-settings.json"
    record.unlink(missing_ok=True)
    frames = list(range(1, 61)) if args.sequence else list(FRAMES)
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = str(folder / f"handoff-{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    scene.frame_set(31)
    scene.render.filepath = "//renders/handoff-"
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "handoff.blend"))
    if hashes() != source_hashes:
        raise RuntimeError("Builder changed during rendering; repeat this review")
    record.write_text(
        json.dumps(
            {
                "engine": args.engine,
                "light": args.light,
                "resolution": [960, 540],
                "fps": scene.render.fps,
                "fps_base": scene.render.fps_base,
                "frames": frames,
                "source_sha256": source_hashes,
                "blender_version": bpy.app.version_string,
                "saved_frame": scene.frame_current,
                "portable_render_path": scene.render.filepath,
                "camera_location": list(scene.camera.location),
                "camera_width": scene.camera.data.ortho_scale,
                "view_transform": scene.view_settings.view_transform,
                "look": scene.view_settings.look,
                "exposure": scene.view_settings.exposure,
                "gamma": scene.view_settings.gamma,
                "bloom": False,
                "charge": [1, 33],
                "slash": [27, 39],
                "impact": [31, 55],
                "method": "PNG frames; realtime playback unreviewed",
                "realtime_playback_reviewed": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
