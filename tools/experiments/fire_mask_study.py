"""Test an original generated density mask in the saved native field study."""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio.nodes import ACTIVE, PROGRESS  # noqa: E402
from tools.charge_design import _Fields  # noqa: E402

if not bpy.app.background or not bpy.data.filepath:
    raise RuntimeError("Open the generated field study in background mode")
scene = bpy.context.scene
panel = bpy.data.objects["Field study"]
root = panel.parent
old = next(o for o in root.children if o != panel and o.type == "MESH")
for collection in list(panel.users_collection):
    collection.objects.unlink(panel)
old.users_collection[0].objects.link(panel)
old_tree = old.data.materials[0].node_tree
weight = old_tree.nodes["Flame Erosion"].inputs[0].links[0].from_node
mask = weight.inputs[1].links[0].from_node
mask.inputs["From Min"].default_value = 0.65
mask.inputs["From Max"].default_value = 0.95
mask.inputs["To Min"].default_value = 0
mask.inputs["To Max"].default_value = 0.65

material = panel.data.materials[0]
tree = material.node_tree
tree.animation_data_clear()
tree.nodes.clear()
material.surface_render_method = "BLENDED"
g = _Fields(tree, root)
p = g.value("Native fire progress", expression=PROGRESS)
clock = g.m("Editable flow clock", "MULTIPLY", p, g.value("Flow", prop="Fire Flow Speed"))
uv = g.n("ShaderNodeAttribute", "Native UV", attribute_name="fire_field_uv")
axes = g.n("ShaderNodeSeparateXYZ", "UV axes")
g.link(uv.outputs["Vector"], axes.inputs[0])
y = axes.outputs["Y"]
noise = g.n("ShaderNodeTexNoise", "Rising mask folds")
g.link(
    g.xyz(
        "Upward fold sampling",
        g.m("Fold across", "MULTIPLY", axes.outputs["X"], 2),
        g.m(
            "Fold rises",
            "SUBTRACT",
            g.m("Fold height", "MULTIPLY", y, 3),
            g.m("Fold advection", "MULTIPLY", clock, 0.14),
        ),
        0,
    ),
    noise.inputs["Vector"],
)
g.link(
    g.m("Mask detail", "MULTIPLY", g.value("Detail", prop="noise_scale"), 0.5),
    noise.inputs["Scale"],
)
noise.inputs["Detail"].default_value = 1
channels = g.n("ShaderNodeSeparateXYZ", "Fold directions")
g.link(noise.outputs["Color"], channels.inputs[0])
curl = g.m("Editable distortion", "MULTIPLY", g.value("Curl", prop="Fire Curl"), 0.4)
curl = g.m("Crown bends more", "MULTIPLY", curl, y)
warped = g.xyz(
    "Flowing texture UV",
    g.m(
        "Distorted U",
        "ADD",
        axes.outputs["X"],
        g.m(
            "Side fold",
            "MULTIPLY",
            g.m("Signed side", "SUBTRACT", channels.outputs["X"], 0.5),
            curl,
        ),
    ),
    g.m(
        "Distorted V",
        "ADD",
        y,
        g.m(
            "Vertical fold",
            "MULTIPLY",
            g.m("Signed rise", "SUBTRACT", channels.outputs["Y"], 0.5),
            curl,
        ),
    ),
    0,
)
sample = g.v(
    "Room around moving tips",
    "ADD",
    g.v("Texture margin", "SCALE", warped, 1.3),
    (-0.15, -0.15, 0),
)
path = ROOT / "assets/experiments/fire-density.png"
image = bpy.data.images.load(str(path), check_existing=False)
image.colorspace_settings.name = "Non-Color"
image.pack()
phase = g.m("Updraft cycle", "FRACT", g.m("Updraft time", "MULTIPLY", clock, 0.12))
phase_b = g.m("Staggered updraft", "FRACT", g.m("Second flow phase", "ADD", phase, 0.5))
flow = g.xyz("Heat moves upward above the fuel", 0, g.m("Upward travel", "MULTIPLY", y, 0.13), 0)
textures = []
for index, cycle in enumerate((phase, phase_b)):
    texture = g.n("ShaderNodeTexImage", f"Original flame density flow {index}")
    texture.image = image
    texture.extension = "CLIP"
    g.link(
        g.v(
            f"Advected UV {index}",
            "SUBTRACT",
            sample,
            g.v(f"Flow distance {index}", "SCALE", flow, cycle),
        ),
        texture.inputs["Vector"],
    )
    textures.append(texture.outputs["Color"])
weight = g.m(
    "Continuous flow weight",
    "SUBTRACT",
    1,
    g.m("Flow triangle", "ABSOLUTE", g.m("Signed cycle", "MULTIPLY_ADD", phase, 2)),
)
geometry_cycle = tree.nodes["Signed cycle"]
geometry_cycle.inputs[2].default_value = -1
blend = g.n("ShaderNodeMixRGB", "Continuous advected density")
g.link(weight, blend.inputs[0])
g.link(textures[1], blend.inputs[1])
g.link(textures[0], blend.inputs[2])
density = blend.outputs["Color"]
retirement = g.m(
    "Editable retirement",
    "MULTIPLY",
    g.stage("Fuel ends", p, 0.64, 1),
    g.value("Fade", prop="fade"),
)
threshold = g.m(
    "Fuel stops from the root",
    "MULTIPLY",
    retirement,
    g.m("Crown retains heat", "SUBTRACT", 0.9, g.m("Height", "MULTIPLY", y, 0.35)),
)
threshold = g.m("Editable dissolve", "ADD", threshold, g.value("Dissolve", prop="dissolve"))
threshold = g.m("Defined cool edge", "ADD", threshold, 0.045)
alpha = g.stage("Density edge", g.m("Remaining density", "SUBTRACT", density, threshold), 0, 0.07)
alpha = g.m("Native active lifetime", "MULTIPLY", alpha, g.value("Active", expression=ACTIVE))
alpha = g.m("Ignition", "MULTIPLY", alpha, g.stage("Fuel catches", p, 0.01, 0.1))
heat = g.m("Density into editable heat", "MULTIPLY_ADD", density, 1.15)
heat.node.inputs[2].default_value = 0.04
ramp = g.n("ShaderNodeValToRGB", "Editable heat palette")
ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
for i, element in enumerate(old_tree.nodes["Painted Red Orange Yellow"].color_ramp.elements):
    target = (
        ramp.color_ramp.elements[0] if i == 0 else ramp.color_ramp.elements.new(element.position)
    )
    target.position, target.color = element.position, element.color
ramp.color_ramp.interpolation = "EASE"
g.link(heat, ramp.inputs[0])
tint = g.xyz("Editable tint", *(g.value(f"Tint {i}", prop=f"color_{i}") for i in range(3)))
emission = g.n("ShaderNodeEmission", "Original burning folds")
g.link(g.v("Tinted heat", "MULTIPLY", ramp.outputs["Color"], tint), emission.inputs["Color"])
g.link(g.value("Strength", prop="strength"), emission.inputs["Strength"])
air = g.n("ShaderNodeBsdfTransparent", "Air")
mix = g.n("ShaderNodeMixShader", "Density coverage")
g.link(alpha, mix.inputs[0])
g.link(air.outputs[0], mix.inputs[1])
g.link(emission.outputs[0], mix.inputs[2])
out = g.n("ShaderNodeOutputMaterial", "Output")
g.link(mix.outputs[0], out.inputs["Surface"])

# Let ignition grow the body, rather than reveal a full-height icon at once.
geometry = panel.modifiers[0].node_group
g = _Fields(geometry, root)
p = g.value("Body progress", expression=PROGRESS)
ignition = g.stage("Body grows from fuel", p, 0.01, 0.14)
height = g.m("Ignition height", "MULTIPLY_ADD", ignition, 0.65)
height.node.inputs[2].default_value = 0.35
g.link(
    g.m("Growing body height", "MULTIPLY", geometry.nodes["Height"].outputs[0], height),
    geometry.nodes["Carrier height"].inputs[0],
)
geometry.nodes["Carrier height"].inputs[1].default_value = 0.95
g.link(
    g.m(
        "Growing body breadth",
        "MULTIPLY",
        geometry.nodes["Width"].outputs[0],
        g.m("Ignition breadth", "SQRT", ignition),
    ),
    geometry.nodes["Carrier width"].inputs[0],
)
geometry.nodes["Carrier width"].inputs[1].default_value = 1.8
geometry.nodes["Half height"].inputs[1].default_value = 0.43

folder = ROOT / "work/fire-mask-flow-study"
folder.mkdir(parents=True, exist_ok=True)
frames = [20, 36, 40, 45, 60]
for frame in frames:
    scene.frame_set(frame)
    scene.render.filepath = str(folder / f"fire-{frame:04}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(folder / "fire.blend"))
(folder / "record.json").write_text(
    json.dumps(
        {
            "frames": frames,
            "density_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "density_source": "Original OpenAI image generation; unchanged PNG",
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "realtime_playback_reviewed": False,
        },
        indent=2,
    )
    + "\n"
)
print("ORIGINAL_PAINTED_FIRE_MASK_STUDY_COMPLETE")
