"""Render the actual lightning asset on a rigged character with a complete strike cycle."""

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
from tools.build_examples import create_effect  # noqa: E402
from tools.character_scene import setup_base  # noqa: E402

FRAMES = (1, 2, 3, 4, 7, 8, 12, 16, 19, 28)


def hashes():
    paths = sorted((ROOT / "blender_vfx_studio").rglob("*.py"))
    paths += [
        ROOT / "tools" / name
        for name in (
            "build_examples.py",
            "charge_design.py",
            "character_scene.py",
            "lightning_asset.py",
            "lightning_preview.py",
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
    parser.add_argument("--sequence", action="store_true")
    parser.add_argument("--frames", type=int, nargs="+")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh background process with --factory-startup and no project")
    frozen = hashes()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fixture = setup_base(light=not args.dark)
    scene = bpy.context.scene
    offset = fixture["contact"]["frame"] - 3
    # Translate the existing NLA strips without stretching their action ranges.
    for actor in (fixture["caster"], fixture["defender"]):
        for track in actor["rig"].animation_data.nla_tracks:
            for strip in track.strips:
                strip.frame_start_raw -= offset
                strip.frame_end_raw -= offset
    scene.frame_set(3)
    weapon = fixture["caster"]["weapon"].evaluated_get(bpy.context.evaluated_depsgraph_get())
    assert (weapon.matrix_world.translation - Vector(fixture["contact"]["hilt"])).length < 1e-5
    scene.frame_start, scene.frame_end = 1, 28
    scene.frame_set(1)
    before = set(scene.objects)
    effect = create_effect("lightning-strike")
    effect.location = (0.8, 0.08, 0.03)
    effect.update_tag()
    collection = bpy.data.collections.new("Combat VFX • toggle for comparison")
    scene.collection.children.link(collection)
    for obj in set(scene.objects) - before:
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
    focus = Vector((0, 0, 1.8))
    if args.far:
        scene.camera.location = focus + (scene.camera.location - focus) * 2
    scene.camera.rotation_euler = (
        (focus - scene.camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    scene.camera.data.lens = 32
    for label, frame in (
        ("Leader", 1),
        ("Contact", 3),
        ("Restrike", 8),
        ("Last arc", 12),
        ("Clear", 19),
    ):
        scene.timeline_markers.new(label, frame=frame)
    folder = (
        ROOT
        / "work/lightning-review"
        / (("dark" if args.dark else "light") + ("-far" if args.far else "-near"))
    )
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / "lightning-settings.json"
    record.unlink(missing_ok=True)
    frames = list(range(1, 29)) if args.sequence else args.frames or list(FRAMES)
    if any(f < 1 or f > 28 for f in frames):
        raise ValueError("Review frames must be within 1–28")
    scene.frame_set(3)
    scene.render.filepath = "//renders/lightning-"
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "lightning.blend"))
    timings = []
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = str(folder / f"lightning-{frame:04d}.png")
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        timings.append({"frame": frame, "seconds": time.perf_counter() - started})
        print("LIGHTNING_FRAME", timings[-1], flush=True)
    if hashes() != frozen:
        raise RuntimeError("Lightning or scene source changed while rendering")
    record.write_text(
        json.dumps(
            {
                "engine": scene.render.engine,
                "blender_version": bpy.app.version_string,
                "frames": frames,
                "fps": 24,
                "fps_base": 1,
                "resolution": [960, 540],
                "samples": scene.eevee.taa_render_samples,
                "view_transform": scene.view_settings.view_transform,
                "look": scene.view_settings.look,
                "bloom": False,
                "dark": args.dark,
                "far": args.far,
                "contact": {
                    **fixture["contact"],
                    "source_frame": fixture["contact"]["frame"],
                    "frame": 3,
                },
                "actor_timeline_offset": -offset,
                "source_sha256": frozen,
                "render_timings": timings,
                "saved_frame": 3,
                "portable_render_path": "//renders/lightning-",
                "camera_location": list(scene.camera.location),
                "camera_lens_mm": scene.camera.data.lens,
                "realtime_playback_reviewed": False,
                "method": "PNG stages and optional complete sequence; realtime playback unreviewed",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
