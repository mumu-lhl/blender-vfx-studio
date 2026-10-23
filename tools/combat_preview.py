"""Review slash-to-hit timing with native weapon/target proxies, without bloom."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from impact_preview import setup as impact_setup  # noqa: E402

from blender_vfx_studio import core  # noqa: E402


def proxy(name, location, scale, color, *, sphere=False, parent=None):
    if sphere:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1)
    else:
        bpy.ops.mesh.primitive_cube_add(size=2)
    obj = bpy.context.object
    obj.name, obj.parent = name, parent
    obj.location, obj.scale = location, scale
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1)
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*color, 1)
    obj.data.materials.append(material)
    return obj


def setup(*, light=False, wide=False, engine="CYCLES"):
    impact = impact_setup(light=light, engine=engine)
    impact.location = (1.3, -0.17, 0.92)
    impact["start"] = 7.0
    impact.update_tag()
    scene = bpy.context.scene
    # Match a modest viewport sample budget for software Eevee review.
    scene.eevee.taa_render_samples = 16
    if light:
        scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
            0.55,
            0.60,
            0.68,
            1,
        )
    scene.cursor.location = (-1, 0, 0.92)
    slash = core.create(bpy.context, "ARC_SLASH", "LOW")
    for key, value in dict(
        start=3.0, duration=12.0, loop=False, radius=2.3, width=0.55, arc=100.0, spin=125.0
    ).items():
        slash[key] = value
    contact_progress = 4 / 12
    contact_clock = contact_progress + slash["motion_ease"] * (
        1 - (1 - contact_progress) ** 3 - contact_progress
    )
    offset = -50 - 125 * contact_clock
    slash.rotation_euler.z = math.radians(offset)
    slash.update_tag()
    pivot = bpy.data.objects.new("Weapon timing proxy", None)
    scene.collection.objects.link(pivot)
    pivot.location = scene.cursor.location
    proxy("Proxy blade", (1.15, 0, 0), (1.15, 0.025, 0.04), (0.18, 0.25, 0.34), parent=pivot)
    proxy("Proxy guard", (0, 0, 0), (0.05, 0.16, 0.06), (0.07, 0.09, 0.12), parent=pivot)
    proxy(
        "Target timing proxy", (1.5, 0.15, 0.55), (0.3, 0.3, 0.55), (0.08, 0.12, 0.18), sphere=True
    )
    # Store ordinary transform keys. Playback never imports this script.
    for frame in range(1, 37):
        progress = min(max((frame - 3) / 12, 0), 1)
        clock = progress + slash["motion_ease"] * (1 - (1 - progress) ** 3 - progress)
        front = min(progress / slash["attack"], 1)
        pivot.rotation_euler.z = math.radians(offset + (front - 0.5) * 100 + 125 * clock)
        pivot.keyframe_insert(data_path="rotation_euler", frame=frame)
    focus = Vector((0.3, 0, 0.7))
    scene.camera.location = focus + Vector((3, -6, 8))
    scene.camera.rotation_euler = (
        (focus - scene.camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    scene.camera.data.ortho_scale = 19.0 if wide else 9.5
    lamp = bpy.data.objects.new("Proxy area light", bpy.data.lights.new("Proxy area light", "AREA"))
    scene.collection.objects.link(lamp)
    lamp.location, lamp.data.energy, lamp.data.shape, lamp.data.size = (0, -3, 6), 500, "DISK", 5
    for label, frame in (("Slash begins", 3), ("Hit", 7), ("Recovery", 15), ("Tail ends", 31)):
        scene.timeline_markers.new(label, frame=frame)
    scene.frame_start, scene.frame_end, scene.render.fps = 1, 36, 24
    return slash, impact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--light", action="store_true")
    parser.add_argument(
        "--wide", action="store_true", help="Double the visible width without resizing effects"
    )
    parser.add_argument("--engine", choices=("CYCLES", "BLENDER_EEVEE"), default="CYCLES")
    parser.add_argument("--sequence", action="store_true", help="Render every frame from 1 to 36")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh background process with --factory-startup and no project")
    setup(light=args.light, wide=args.wide, engine=args.engine)
    background = "light" if args.light else "dark"
    variant = (
        background
        if args.engine == "CYCLES" and not args.wide
        else (f"{args.engine.lower()}-{'wide' if args.wide else 'near'}-{background}")
    )
    folder = ROOT / "work/visual-combat" / variant
    folder.mkdir(parents=True, exist_ok=True)
    # An interrupted or keyframe-only render must not certify an older sequence.
    settings_path = folder / "render-settings.json"
    settings_path.unlink(missing_ok=True)
    (folder.parent / "index.html").unlink(missing_ok=True)
    frames = list(range(1, 37)) if args.sequence else [4, 8, 12, 23]
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        bpy.context.scene.render.filepath = str(folder / f"combat-{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    # Open the review scene on the hit, rather than an empty final frame.
    bpy.context.scene.frame_set(8)
    bpy.context.scene.render.filepath = str(folder / "combat-0008.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "combat.blend"))
    settings = {
        "engine": args.engine,
        "background": background,
        "camera_width": 19.0 if args.wide else 9.5,
        "resolution": [960, 540],
        "fps": 24,
        "rendered_frames": frames,
        "samples": 16 if args.engine == "BLENDER_EEVEE" else 24,
        "bloom": False,
    }
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
