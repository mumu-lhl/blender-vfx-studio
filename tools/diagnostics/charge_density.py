"""Reproduce the archived charge-density trial; this is not a released asset builder."""

import argparse
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from particle_test_support import camera  # noqa: E402

from blender_vfx_studio import composition  # noqa: E402
from tools.build_examples import create_effect  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--plain", action="store_true", help="Use a constant Principled Volume as a control"
)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
bpy.ops.wm.read_factory_settings(use_empty=True)
effect = create_effect("energy-charge")
core = next(r for r in composition.members(effect) if r["vfx_module"] == "shader.shield")
camera()
scene = bpy.context.scene
scene.render.resolution_x = scene.render.resolution_y = 96
scene.render.filepath = str(ROOT / "work/charge-density-diagnostic.png")
if args.plain:
    tree = core.children[0].data.materials[1].node_tree
    tree.animation_data_clear()
    tree.nodes.clear()
    volume = tree.nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Density"].default_value = 1
    volume.inputs["Emission Strength"].default_value = 4
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(volume.outputs[0], output.inputs["Volume"])
print("DENSITY_TRIAL_BEFORE_SEEK", flush=True)
scene.frame_set(31)
print("DENSITY_TRIAL_BEFORE_RENDER", flush=True)
bpy.ops.render.render(write_still=True)
print("DENSITY_TRIAL_RENDER_COMPLETED", flush=True)
