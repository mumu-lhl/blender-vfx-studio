"""Render an editable dash cast with a rigged character, without runtime callbacks."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import dash  # noqa: E402
from tools.character_scene import setup_stage  # noqa: E402
from tools.dash_asset import create, runner  # noqa: E402

FRAMES = (1, 5, 7, 12, 19, 23, 27, 33, 37, 48)


def hashes():
    paths = sorted((ROOT / "blender_vfx_studio").rglob("*.py"))
    paths += [
        ROOT / "tools" / n for n in ("dash_asset.py", "dash_preview.py", "character_scene.py")
    ]
    paths += sorted((ROOT / "assets/character-review/kaykit").iterdir())
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
        if p.is_file()
    }


def setup(*, light=True, far=False, count=None, first=6, last=18):
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = 1, 48
    setup_stage(light=light, far=far, focus=(0, 0, 1), lens=40)
    before = set(scene.objects)
    scene.frame_set(1)
    if count is None and (first, last) == (6, 18):
        root, character = create(bpy.context, keep_character=True)
    else:
        character = runner()
        root = dash.create(bpy.context, character["rig"], first, last, count=count)
    fx = bpy.data.collections.new("Combat VFX • toggle for comparison")
    scene.collection.children.link(fx)
    for obj in set(scene.objects) - before:
        if not obj.get("vfx_id"):
            continue
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        fx.objects.link(obj)
    bpy.ops.file.pack_all()
    return {
        "frame": 19,
        "pose": "KayKit Running_A",
        "sample_frames": list(root["vfx_capture_frames"]),
        "root_motion": "Native keyed dash from X=-2 to X=1.4, frames 1–19",
        "source_actor": character["rig"].name,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--far", action="store_true")
    parser.add_argument("--echo-count", type=int)
    parser.add_argument("--capture-first", type=int, default=6)
    parser.add_argument("--capture-last", type=int, default=18)
    parser.add_argument("--sequence", action="store_true")
    parser.add_argument("--frames", nargs="+", type=int)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh factory background process")
    if args.echo_count is not None and not 2 <= args.echo_count <= 32:
        parser.error("Echo count must be within 2–32")
    if not 1 <= args.capture_first < args.capture_last <= 19:
        parser.error("This running fixture supports capture within frames 1–19")
    frozen = hashes()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    contact = setup(
        light=not args.dark,
        far=args.far,
        count=args.echo_count,
        first=args.capture_first,
        last=args.capture_last,
    )
    folder = (
        ROOT
        / "work/dash-review"
        / (
            ("dark" if args.dark else "light")
            + ("-far" if args.far else "-near")
            + (
                ""
                if args.echo_count is None and (args.capture_first, args.capture_last) == (6, 18)
                else f"-echoes-{args.echo_count or 3}-{args.capture_first}-{args.capture_last}"
            )
        )
    )
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / "dash-settings.json"
    record.unlink(missing_ok=True)
    scene = bpy.context.scene
    scene.frame_set(contact["frame"])
    saved_frame = scene.frame_current
    scene.render.filepath = "//renders/dash-"
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "dash.blend"))
    frames = list(range(1, 49)) if args.sequence else args.frames or list(FRAMES)
    if any(f < 1 or f > 48 for f in frames):
        raise ValueError("Dash review frames must be within 1–48")
    timings = []
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = str(folder / f"dash-{frame:04d}.png")
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        timings.append({"frame": frame, "seconds": time.perf_counter() - started})
        print("DASH_FRAME", timings[-1], flush=True)
    if hashes() != frozen:
        raise RuntimeError("Dash source changed during render batch")
    record.write_text(
        json.dumps(
            dict(
                engine=scene.render.engine,
                blender_version=bpy.app.version_string,
                frames=frames,
                fps=24,
                fps_base=1,
                resolution=[960, 540],
                samples=scene.eevee.taa_render_samples,
                view_transform=scene.view_settings.view_transform,
                look=scene.view_settings.look,
                bloom=False,
                dark=args.dark,
                far=args.far,
                contact=contact,
                source_sha256=frozen,
                saved_frame=saved_frame,
                render_timings=timings,
                realtime_playback_reviewed=False,
                method="Rendered PNG stages; realtime playback unreviewed",
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
