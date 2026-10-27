"""Render a native magic-circle preparation and fire-release character sequence."""

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
from tools.fire_asset import create as create_fire  # noqa: E402
from tools.magic_asset import create as create_magic  # noqa: E402

FRAMES = (1, 16, 40, 51, 52, 56, 64, 69, 73, 76, 96, 104, 108)


def hashes():
    paths = sorted((ROOT / "blender_vfx_studio").rglob("*.py"))
    paths += [
        ROOT / "tools" / n
        for n in (
            "fire_asset.py",
            "magic_asset.py",
            "spell_preview.py",
            "character_scene.py",
            "charge_design.py",
        )
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
    scene.frame_start, scene.frame_end = 1, 108
    character = actor("Knight", "Spell Caster", (-0.65, 0), math.pi / 2, sword=True)
    clip(character["rig"], character["actions"]["Spellcast_Raise"], 1, 24)
    clip(character["rig"], character["actions"]["Spellcast_Long"], 24, 52)
    release = clip(character["rig"], character["actions"]["Spellcast_Shoot"], 52, 74)
    release.blend_out = 6
    # Extend the existing loop so recovery keeps its original animation phase.
    idle = character["rig"].animation_data.nla_tracks[0].strips[0]
    idle.repeat = (109 - idle.frame_start) / (idle.action_frame_end - idle.action_frame_start)
    setup_stage(light=light, far=far, focus=(0, 0, 1.05), lens=36)
    before = set(scene.objects)
    scene.frame_set(1)
    magic = create_magic(bpy.context)
    magic.name = "Spell • Magic Circle"
    magic.location = (-0.65, 0, 0.03)
    magic.update_tag()
    scene.frame_set(52)
    fire = create_fire(bpy.context)
    fire.name = "Spell • Fire Release"
    fire.location = (0.65, 0, 0.03)
    fire.update_tag()
    for label, frame in (
        ("Preparation", 1),
        ("Hold", 24),
        ("Release", 52),
        ("Circle clear", 73),
        ("All clear", 104),
    ):
        scene.timeline_markers.new(label, frame=frame)
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
        "frame": 52,
        "pose": "KayKit Spellcast_Raise / Long / Shoot",
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
        / "work/spell-review"
        / (("dark" if args.dark else "light") + ("-far" if args.far else "-near"))
    )
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / "spell-settings.json"
    record.unlink(missing_ok=True)
    scene = bpy.context.scene
    scene.frame_set(contact["frame"] + 7)
    saved_frame = scene.frame_current
    scene.render.filepath = "//renders/spell-"
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "spell.blend"))
    frames = list(range(1, 109)) if args.sequence else args.frames or list(FRAMES)
    if any(f < 1 or f > 108 for f in frames):
        raise ValueError("Spell review frames must be within 1–108")
    timings = []
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = str(folder / f"spell-{frame:04d}.png")
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        timings.append({"frame": frame, "seconds": time.perf_counter() - started})
        print("SPELL_FRAME", timings[-1], flush=True)
    if hashes() != frozen:
        raise RuntimeError("Spell source changed during render batch")
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
