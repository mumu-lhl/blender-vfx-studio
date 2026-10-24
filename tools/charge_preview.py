"""Review the actual Energy Charge starter's lifetime without preview-only glow."""

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import composition  # noqa: E402
from tools.build_examples import create_effect  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--legacy", action="store_true", help="Restore the old starter's Fade values"
    )
    parser.add_argument("--light", action="store_true")
    parser.add_argument("--engine", choices=("CYCLES", "BLENDER_EEVEE"), default="CYCLES")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError("Use a fresh background process with --factory-startup and no project")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    root = create_effect("energy-charge")
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
    camera = bpy.data.objects.new(
        "Charge Review Camera", bpy.data.cameras.new("Charge Review Camera")
    )
    scene.collection.objects.link(camera)
    camera.location = (4, -6, 3.5)
    camera.rotation_euler = (
        (Vector((0, 0, 0.1)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    # The original square thumbnail framing crops the ground rings at 16:9.
    camera.data.type, camera.data.ortho_scale = "ORTHO", 7.2
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
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    prefix = ("legacy-" if args.legacy else "") + args.engine.lower()
    prefix += "-light" if args.light else ""
    folder = ROOT / "work/visual-charge" / prefix
    folder.mkdir(parents=True, exist_ok=True)
    for frame in (1, 4, 7, 13, 22, 31, 37, 42, 46, 48, 49):
        scene.frame_set(frame)
        scene.render.filepath = str(folder / f"charge-{prefix}-{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    scene.frame_set(22)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "charge.blend"))


if __name__ == "__main__":
    main()
