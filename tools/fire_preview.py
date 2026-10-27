"""Render an editable fire cast with a rigged character, without runtime callbacks."""

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.character_scene import actor, clip, setup_stage  # noqa: E402
from tools.fire_asset import create  # noqa: E402

FRAMES = (1, 14, 18, 20, 25, 36, 48, 60, 69, 72)


def hashes():
    paths = sorted((ROOT / "blender_vfx_studio").rglob("*.py"))
    paths += [
        ROOT / "tools" / n
        for n in ("fire_asset.py", "fire_preview.py", "character_scene.py", "charge_design.py")
    ]
    paths += sorted((ROOT / "assets/character-review/kaykit").iterdir())
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
        if p.is_file()
    }


def setup(*, light=True, far=False):
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = 1, 72
    character = actor("Knight", "Fire Caster", (-0.65, 0), math.pi / 2, sword=True)
    clip(character["rig"], character["actions"]["Spellcast_Raise"], 1, 18)
    clip(character["rig"], character["actions"]["Spellcast_Shoot"], 18, 40)
    setup_stage(light=light, far=far, focus=(0, 0, 1.05), lens=40)
    before = set(scene.objects)
    scene.frame_set(18)
    root = create(bpy.context)
    root.location = (0.65, 0, 0.03)
    root.update_tag()
    fx = bpy.data.collections.new("Combat VFX • toggle for comparison")
    scene.collection.children.link(fx)
    for obj in set(scene.objects) - before:
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        fx.objects.link(obj)
    for action in list(bpy.data.actions):
        if action.users == 0:
            bpy.data.actions.remove(action)
    bpy.ops.file.pack_all()
    return {
        "frame": 18,
        "pose": "KayKit Spellcast_Raise / Spellcast_Shoot",
        "trigger": "Authored spell release, not a claimed physical contact",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--far", action="store_true")
    parser.add_argument("--sequence", action="store_true")
    parser.add_argument("--frames", nargs="+", type=int)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh factory background process")
    frozen = hashes()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    contact = setup(light=not args.dark, far=args.far)
    folder = (
        ROOT
        / "work/fire-review"
        / (("dark" if args.dark else "light") + ("-far" if args.far else "-near"))
    )
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / "fire-settings.json"
    record.unlink(missing_ok=True)
    scene = bpy.context.scene
    scene.frame_set(contact["frame"] + 7)
    saved_frame = scene.frame_current
    scene.render.filepath = "//renders/fire-"
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "fire.blend"))
    frames = list(range(1, 73)) if args.sequence else args.frames or list(FRAMES)
    if any(f < 1 or f > 72 for f in frames):
        raise ValueError("Fire review frames must be within 1–72")
    timings = []
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = str(folder / f"fire-{frame:04d}.png")
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        timings.append({"frame": frame, "seconds": time.perf_counter() - started})
        print("FIRE_FRAME", timings[-1], flush=True)
    if hashes() != frozen:
        raise RuntimeError("Fire source changed during render batch")
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
