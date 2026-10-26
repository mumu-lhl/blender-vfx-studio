"""Render a complete rigged sword fight using the actual native starter effects."""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.character_scene import FRAMES, add_effects, setup_base  # noqa: E402


def source_hashes():
    paths = sorted((ROOT / "blender_vfx_studio").rglob("*.py"))
    paths += [
        ROOT / "tools" / name
        for name in (
            "character_scene.py",
            "character_combat.py",
            "build_examples.py",
            "charge_design.py",
        )
    ]
    paths += sorted((ROOT / "assets/character-review/kaykit").iterdir())
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
        if p.is_file()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--far", action="store_true")
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--no-fx", action="store_true")
    parser.add_argument("--sequence", action="store_true")
    parser.add_argument("--frames", type=int, nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh background process with --factory-startup and no project")
    frozen = source_hashes()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fixture = add_effects(
        setup_base(light=not args.dark, far=args.far, view="reverse" if args.reverse else "front")
    )
    scene = bpy.context.scene
    fixture["effects_collection"].hide_render = args.no_fx
    hit = fixture["contact"]["frame"]
    frames = (
        list(range(1, FRAMES + 1))
        if args.sequence
        else args.frames or [1, 16, 32, 43, 47, hit, hit + 4, hit + 12, 80, 96]
    )
    if any(f < 1 or f > FRAMES for f in frames):
        raise ValueError("Frames must be within the complete 1–96 shot")
    variant = ("dark" if args.dark else "light") + ("-far" if args.far else "-near")
    variant += "-reverse" if args.reverse else ""
    variant += "-no-fx" if args.no_fx else ""
    folder = args.output or ROOT / "work/character-combat" / variant
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / "character-settings.json"
    record.unlink(missing_ok=True)
    scene.frame_set(hit)
    scene.render.filepath = "//renders/character-"
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "character.blend"))
    timings = []
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = str(folder / f"character-{frame:04d}.png")
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        seconds = time.perf_counter() - started
        timings.append({"frame": frame, "render_wall_seconds": seconds})
        print(f"CHARACTER_FRAME {frame} {seconds:.4f}s", flush=True)
    if frozen != source_hashes():
        raise RuntimeError("Scene or generator source changed during rendering; repeat this review")
    quota = Path("/sys/fs/cgroup/cpu.max")
    record.write_text(
        json.dumps(
            {
                "engine": scene.render.engine,
                "blender_version": bpy.app.version_string,
                "resolution": [960, 540],
                "samples": scene.eevee.taa_render_samples,
                "fps": scene.render.fps,
                "fps_base": scene.render.fps_base,
                "frames": frames,
                "dark": args.dark,
                "far": args.far,
                "reverse": args.reverse,
                "no_fx": args.no_fx,
                "view_transform": scene.view_settings.view_transform,
                "look": scene.view_settings.look,
                "bloom": False,
                "camera_location": list(scene.camera.location),
                "camera_lens_mm": scene.camera.data.lens,
                "contact": fixture["contact"],
                "blade_trace": fixture["trace"],
                "source_sha256": frozen,
                "render_timings": timings,
                "cpu_quota": quota.read_text().strip() if quota.exists() else None,
                "blender_threads": scene.render.threads,
                "software_gl_requested": os.getenv("LIBGL_ALWAYS_SOFTWARE") == "1",
                "lp_num_threads": os.getenv("LP_NUM_THREADS"),
                "saved_frame": hit,
                "portable_render_path": "//renders/character-",
                "method": "PNG frames; realtime playback unreviewed",
                "realtime_playback_reviewed": False,
                "limits": [
                    "Stylized CC0 low-poly characters, not a production anime rig",
                    "Headless render wall time is not interactive viewport FPS",
                    "Timing and transforms are shot-specific; starter effect builders are unchanged",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
