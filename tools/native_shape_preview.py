"""Compare existing native shape values in a real character scene, without bloom."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import composition, ui  # noqa: E402
from tools.build_examples import create_effect  # noqa: E402
from tools.character_scene import add_effects, setup_base  # noqa: E402

CASES = {
    "charge": (
        {"Nucleus Stored Size": 2.8, "Nucleus Compression": 0.8, "Release Stretch": 2.0},
        (18, 36, 46),
    ),
    "lightning": ({"Bolt Length": 4.8, "Branch Reach": 1.4}, (2, 3, 12)),
}


def hashes():
    paths = sorted((ROOT / "blender_vfx_studio").rglob("*.py"))
    paths += [
        ROOT / "tools" / n
        for n in (
            "native_shape_preview.py",
            "build_examples.py",
            "charge_design.py",
            "character_scene.py",
            "lightning_asset.py",
        )
    ]
    paths += sorted((ROOT / "assets/character-review/kaykit").iterdir())
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
        if p.is_file()
    }


def setup(effect, light, far):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fixture = setup_base(light=light, far=far)
    scene = bpy.context.scene
    if effect == "charge":
        group = add_effects(fixture)["effects"][0]
    else:
        offset = fixture["contact"]["frame"] - 3
        for actor in (fixture["caster"], fixture["defender"]):
            for track in actor["rig"].animation_data.nla_tracks:
                for strip in track.strips:
                    strip.frame_start_raw -= offset
                    strip.frame_end_raw -= offset
        scene.frame_set(1)
        group = create_effect("lightning-strike")
        group.location = (0.8, 0.08, 0.03)
        group.update_tag()
        focus = Vector((0, 0, 1.8))
        scene.camera.rotation_euler = (
            (focus - scene.camera.location).to_track_quat("-Z", "Y").to_euler()
        )
        scene.camera.data.lens = 32
    names = set(CASES[effect][0])
    member = next(
        m for m in composition.members(group) if names <= ui._native_shape_values(m).keys()
    )
    return member


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--effect", choices=tuple(CASES), required=True)
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--far", action="store_true")
    parser.add_argument("--frames", type=int, nargs="+")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh factory background process")
    changes, defaults = CASES[args.effect]
    frames = args.frames or list(defaults)
    if min(frames) < 1 or max(frames) > (52 if args.effect == "charge" else 19):
        parser.error("Frames must be inside this effect's review range")
    frozen = hashes()
    folder = (
        ROOT
        / "work/native-shape"
        / args.effect
        / (("dark" if args.dark else "light") + ("-far" if args.far else "-near"))
    )
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / "review-settings.json"
    record.unlink(missing_ok=True)
    results = []
    for case in ("baseline", "edited"):
        member = setup(args.effect, not args.dark, args.far)
        values = ui._native_shape_values(member)
        if case == "edited":
            for name, value in changes.items():
                values[name][1].default_value = value
        scene = bpy.context.scene
        scene.frame_set(frames[len(frames) // 2])
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / f"{case}.blend"))
        settings = {name: float(values[name][1].default_value) for name in changes}
        for frame in frames:
            scene.frame_set(frame)
            scene.render.filepath = str(folder / f"{case}-{frame:04d}.png")
            started = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            results.append(
                dict(case=case, frame=frame, values=settings, seconds=time.perf_counter() - started)
            )
            print("NATIVE_SHAPE_FRAME", results[-1], flush=True)
    if hashes() != frozen:
        raise RuntimeError("Source changed during review")
    record.write_text(
        json.dumps(
            dict(
                effect=args.effect,
                frames=frames,
                engine="BLENDER_EEVEE",
                resolution=[960, 540],
                dark=args.dark,
                far=args.far,
                bloom=False,
                source_sha256=frozen,
                results=results,
                realtime_playback_reviewed=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
