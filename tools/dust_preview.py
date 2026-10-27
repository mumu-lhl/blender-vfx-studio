"""Render an editable dust landing on a rigged character, without runtime callbacks."""

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
from blender_vfx_studio.animation import curves  # noqa: E402
from tools.character_scene import actor, clip, setup_stage  # noqa: E402
from tools.dust_asset import create  # noqa: E402

FRAMES = (5, 16, 26, 27, 29, 33, 39, 47, 55, 60)


def hashes():
    paths = sorted((ROOT / "blender_vfx_studio").rglob("*.py"))
    paths += [
        ROOT / "tools" / n
        for n in ("dust_asset.py", "dust_preview.py", "character_scene.py", "charge_design.py")
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
    scene.frame_start, scene.frame_end = 1, 60
    character = actor("Knight", "Landing Knight", (0, 0), math.pi, sword=True)
    rig = character["rig"]
    clip(rig, character["actions"]["Jump_Full_Short"], 1, 33)
    # This game clip is in-place. Author an ordinary editable root translation.
    ground = rig.location.z
    for frame in range(1, 61):
        t = min(1, max(0, (frame - 5) / 22))
        rig.location.z = ground + 4 * 0.75 * t * (1 - t)
        rig.keyframe_insert(data_path="location", index=2, frame=frame)
    for curve in curves(rig):
        if curve.data_path != "location" or curve.array_index != 2:
            continue
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    feet = [o for o in rig.children if o.type == "MESH" and "leg" in o.name.lower()]
    if not feet:
        raise RuntimeError("Landing fixture needs actual leg geometry")
    trace, airborne, contact = [], False, None
    for frame in range(1, 41):
        scene.frame_set(frame)
        graph = bpy.context.evaluated_depsgraph_get()
        z = min(
            (ev.matrix_world @ v.co).z
            for obj in feet
            for ev in [obj.evaluated_get(graph)]
            for v in ev.data.vertices
        )
        trace.append({"frame": frame, "lowest_foot_z": z})
        airborne |= z > 0.12
        if airborne and z <= 0.02 and contact is None:
            contact = frame
    if contact is None:
        raise RuntimeError("No evaluated foot/ground contact after jump")
    setup_stage(light=light, far=far, focus=(0, 0, 1), lens=40)
    scene.eevee.taa_render_samples = 32
    before = set(scene.objects)
    scene.frame_set(contact)
    root = create(bpy.context)
    root.location = (0, 0, 0.03)
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
        "frame": contact,
        "foot_trace": trace,
        "pose": "KayKit Jump_Full_Short, in-place",
        "root_motion": "Native keyed 0.75 m arc from frame 5 to 27",
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
        / "work/dust-review"
        / (("dark" if args.dark else "light") + ("-far" if args.far else "-near"))
    )
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / "dust-settings.json"
    record.unlink(missing_ok=True)
    scene = bpy.context.scene
    scene.frame_set(contact["frame"] + 6)
    saved_frame = scene.frame_current
    scene.render.filepath = "//renders/dust-"
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "dust.blend"))
    frames = list(range(1, 61)) if args.sequence else args.frames or list(FRAMES)
    if any(f < 1 or f > 60 for f in frames):
        raise ValueError("Dust review frames must be within 1–60")
    timings = []
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = str(folder / f"dust-{frame:04d}.png")
        started = time.perf_counter()
        bpy.ops.render.render(write_still=True)
        timings.append({"frame": frame, "seconds": time.perf_counter() - started})
        print("DUST_FRAME", timings[-1], flush=True)
    if hashes() != frozen:
        raise RuntimeError("Dust source changed during render batch")
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
