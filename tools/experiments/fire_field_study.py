"""Original flame-field study. No tutorial texture or copied graph."""

import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if not bpy.app.background or not bpy.data.filepath:
    raise RuntimeError("Open a generated fire review scene in background mode")
from blender_vfx_studio.nodes import ACTIVE, PROGRESS  # noqa: E402
from tools.charge_design import _Fields  # noqa: E402

s = bpy.context.scene
root = next(o for o in bpy.data.objects if "Fire Height" in o)
old = root.children[0]
old.hide_render = False
# Existing sculpted flames become secondary tips around the field body.
old.data.materials[0].surface_render_method = "BLENDED"
ot = old.data.materials[0].node_tree
mask = ot.nodes.new("ShaderNodeMapRange")
mask.inputs["From Min"].default_value = 0.25
mask.inputs["From Max"].default_value = 0.8
mask.inputs["To Min"].default_value = 0.12
mask.inputs["To Max"].default_value = 0.7
ot.links.new(ot.nodes["Height Along Each Flame"].outputs["Fac"], mask.inputs["Value"])
weight = ot.nodes.new("ShaderNodeMath")
weight.operation = "MULTIPLY"
ot.links.new(ot.nodes["Flame Erosion"].inputs[0].links[0].from_socket, weight.inputs[0])
ot.links.new(mask.outputs[0], weight.inputs[1])
ot.links.new(weight.outputs[0], ot.nodes["Flame Erosion"].inputs[0])
mesh = bpy.data.meshes.new("Field study source")
obj = bpy.data.objects.new("Field study", mesh)
s.collection.objects.link(obj)
obj.parent = root
material = bpy.data.materials.new("Original warped flame field")
material.use_nodes = True
material.surface_render_method = "BLENDED"
material.node_tree.nodes.clear()
obj.data.materials.append(material)
g = _Fields(material.node_tree, root)
p = g.value("Native progress", expression=PROGRESS)
clock = g.m("Flame clock", "MULTIPLY", p, g.value("Flow", prop="Fire Flow Speed"))
a = g.n("ShaderNodeAttribute", "Native field UV", attribute_name="fire_field_uv")
xy = g.n("ShaderNodeSeparateXYZ", "UV")
g.link(a.outputs["Vector"], xy.inputs[0])
x = g.m("Across flame", "MULTIPLY_ADD", xy.outputs["X"], 2)
x.node.inputs[2].default_value = -1
y = xy.outputs["Y"]
sample = g.xyz(
    "Advected noise coordinates",
    g.m("Noise across", "MULTIPLY", x, 1.5),
    g.m(
        "Noise rises",
        "SUBTRACT",
        g.m("Noise height", "MULTIPLY", y, 2.5),
        g.m("Advection", "MULTIPLY", clock, 0.22),
    ),
    0,
)
noise = g.n("ShaderNodeTexNoise", "Upward large eddies")
g.link(sample, noise.inputs["Vector"])
noise.inputs["Scale"].default_value = 2.5
noise.inputs["Detail"].default_value = 1
signed = g.m("Signed eddies", "SUBTRACT", noise.outputs["Fac"], 0.5)
warp = g.m("Warp grows above the fuel", "MULTIPLY", g.m("Distortion", "MULTIPLY", signed, 0.65), y)
yw = g.m("Fold the silhouette upward", "ADD", y, warp)
fields = []
for i, (offset, height, breadth, phase) in enumerate(
    ((0, 0.96, 0.62, 0), (-0.31, 0.7, 0.29, 1.5), (0.29, 0.78, 0.26, 3.3))
):
    t = g.m(f"{i} local height", "DIVIDE", yw, height)
    remain = g.m(f"{i} taper", "MAXIMUM", g.m(f"{i} remaining", "SUBTRACT", 1, t), 0)
    # The foot opens above the ground, rather than ending in a wide flat bar.
    fuel = g.m(f"{i} fuel offset", "ADD", g.m(f"{i} fuel height", "MULTIPLY", t, 3), 0.1)
    fuel = g.m(f"{i} bound fuel", "MINIMUM", g.m(f"{i} positive fuel", "MAXIMUM", fuel, 0), 1)
    radius = g.m(
        f"{i} teardrop section",
        "MULTIPLY",
        g.m(f"{i} narrow crown", "POWER", remain, 1.05),
        g.m(f"{i} rising foot", "SQRT", fuel),
    )
    phase_height = g.m(f"{i} neck height", "MULTIPLY_ADD", t, 11)
    phase_height.node.inputs[2].default_value = phase
    wave = g.m(
        f"{i} travelling neck",
        "SINE",
        g.m(f"{i} neck rises", "SUBTRACT", phase_height, g.m(f"{i} speed", "MULTIPLY", clock, 0.8)),
    )
    neck = g.m(f"{i} neck amount", "MULTIPLY_ADD", wave, 0.22)
    neck.node.inputs[2].default_value = 0.78
    radius = g.m(f"{i} breathing radius", "MULTIPLY", radius, neck)
    radius = g.m(f"{i} breadth", "MULTIPLY", radius, breadth)
    curl_height = g.m(f"{i} curl height", "MULTIPLY_ADD", t, 7)
    curl_height.node.inputs[2].default_value = phase
    bend = g.m(
        f"{i} bend",
        "MULTIPLY",
        g.m(
            f"{i} bend phase",
            "SINE",
            g.m(
                f"{i} curl phase",
                "SUBTRACT",
                curl_height,
                g.m(f"{i} curl speed", "MULTIPLY", clock, 0.5),
            ),
        ),
        g.m(f"{i} stronger at crown", "MULTIPLY", t, 0.15),
    )
    centre = g.m(f"{i} lobe centre", "ADD", bend, offset)
    field = g.m(
        f"{i} contour",
        "SUBTRACT",
        radius,
        g.m(f"{i} distance from centre", "ABSOLUTE", g.m(f"{i} x distance", "SUBTRACT", x, centre)),
    )
    field = g.m(f"{i} above fuel", "MINIMUM", field, g.m(f"{i} bottom boundary", "MULTIPLY", y, 2))
    fields.append(field)
field = g.m(
    "Three unequal flame lobes",
    "MAXIMUM",
    fields[0],
    g.m("Smaller side lobes", "MAXIMUM", fields[1], fields[2]),
)
cleft = g.m(
    "Cooling pockets open",
    "MULTIPLY",
    g.m(
        "Large cool valley",
        "MAXIMUM",
        g.m("Cool valley threshold", "SUBTRACT", noise.outputs["Fac"], 0.42),
        0,
    ),
    g.m("Pockets above fuel", "MULTIPLY", g.stage("Pockets grow above base", y, 0.1, 0.7), 0.7),
)
field = g.m("Upward pockets cut the silhouette", "SUBTRACT", field, cleft)
release = g.stage("Fuel ends", p, 0.64, 1)
field = g.m(
    "Fuel separates before the crown",
    "SUBTRACT",
    field,
    g.m(
        "Last fuel retreats",
        "MULTIPLY",
        g.m("Editable retirement", "MULTIPLY", release, g.value("Fade", prop="fade")),
        g.m("Lower fuel goes first", "SUBTRACT", 0.38, g.m("Upper tips", "MULTIPLY", y, 0.25)),
    ),
)
field = g.m("Editable erosion", "SUBTRACT", field, g.value("Dissolve", prop="dissolve"))
alpha = g.stage("Fine silhouette edge", field, 0, 0.018)
alpha = g.m("Native active life", "MULTIPLY", alpha, g.value("Active", expression=ACTIVE))
alpha = g.m("Ignition", "MULTIPLY", alpha, g.stage("Fuel catches", p, 0.01, 0.1))
heat = g.m("Depth in the hot body", "MULTIPLY", field, 1.9)
heat = g.m("Cool edge and hot interior", "ADD", heat, 0.12)
heat = g.m(
    "Hot pockets remain as cold valleys open",
    "ADD",
    heat,
    g.m(
        "Advected heat",
        "MULTIPLY",
        g.m("Hot part of the eddy", "SUBTRACT", 1, noise.outputs["Fac"]),
        0.42,
    ),
)
heat = g.m(
    "Fuel heat",
    "ADD",
    heat,
    g.m("Lower fuel still burns", "MULTIPLY", g.m("Lower fuel", "SUBTRACT", 1, y), 0.12),
)
ramp = g.n("ShaderNodeValToRGB", "Editable heat palette")
ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
original = old.data.materials[0].node_tree.nodes["Painted Red Orange Yellow"].color_ramp
for i, e in enumerate(original.elements):
    target = ramp.color_ramp.elements[0] if i == 0 else ramp.color_ramp.elements.new(e.position)
    target.position = e.position
    target.color = e.color
ramp.color_ramp.interpolation = "EASE"
g.link(heat, ramp.inputs[0])
emission = g.n("ShaderNodeEmission", "Fire radiance")
g.link(ramp.outputs["Color"], emission.inputs["Color"])
g.link(g.value("Strength", prop="strength"), emission.inputs["Strength"])
air = g.n("ShaderNodeBsdfTransparent", "Air")
mix = g.n("ShaderNodeMixShader", "Native flame surface")
g.link(alpha, mix.inputs[0])
g.link(air.outputs[0], mix.inputs[1])
g.link(emission.outputs[0], mix.inputs[2])
out = g.n("ShaderNodeOutputMaterial", "Output")
g.link(mix.outputs[0], out.inputs["Surface"])
# A native camera-facing carrier; the material creates the silhouette.
tree = bpy.data.node_groups.new("Original flame field carrier", "GeometryNodeTree")
tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
mod = obj.modifiers.new("Native flame field", "NODES")
mod.node_group = tree
g = _Fields(tree, root)
width = g.m("Carrier width", "MULTIPLY", g.value("Width", prop="width"), 1.6)
height = g.m("Carrier height", "MULTIPLY", g.value("Height", prop="Fire Height"), 0.75)
grid = g.n("GeometryNodeMeshGrid", "Field carrier")
grid.inputs["Vertices X"].default_value = 2
grid.inputs["Vertices Y"].default_value = 2
g.link(width, grid.inputs["Size X"])
g.link(height, grid.inputs["Size Y"])
pos = g.n("GeometryNodeInputPosition", "Carrier position")
axes = g.n("ShaderNodeSeparateXYZ", "Carrier axes")
g.link(pos.outputs[0], axes.inputs[0])
uv = g.xyz(
    "Original UV",
    g.m("U", "ADD", g.m("U normalized", "DIVIDE", axes.outputs["X"], width), 0.5),
    g.m("V", "ADD", g.m("V normalized", "DIVIDE", axes.outputs["Y"], height), 0.5),
    0,
)
store = g.n(
    "GeometryNodeStoreNamedAttribute", "Store field UV", data_type="FLOAT_VECTOR", domain="CORNER"
)
store.inputs["Name"].default_value = "fire_field_uv"
g.link(grid.outputs["Mesh"], store.inputs["Geometry"])
g.link(uv, store.inputs["Value"])
move = g.n("GeometryNodeTransform", "Foot at origin")
g.link(store.outputs[0], move.inputs["Geometry"])
g.link(
    g.xyz("Grounded origin", 0, g.m("Half height", "MULTIPLY", height, 0.5), 0),
    move.inputs["Translation"],
)
cam = g.n("GeometryNodeInputActiveCamera", "Native camera")
info = g.n("GeometryNodeObjectInfo", "Camera in field space", transform_space="RELATIVE")
g.link(cam.outputs[0], info.inputs["Object"])
face = g.n("GeometryNodeTransform", "Native billboard")
g.link(move.outputs[0], face.inputs["Geometry"])
g.link(info.outputs["Rotation"], face.inputs["Rotation"])
mat = g.n("GeometryNodeSetMaterial", "Field shader")
mat.inputs["Material"].default_value = material
g.link(face.outputs[0], mat.inputs["Geometry"])
clear = g.n("GeometryNodeDeleteGeometry", "Native lifetime", domain="POINT")
g.link(mat.outputs[0], clear.inputs["Geometry"])
g.link(
    g.m("Outside native life", "SUBTRACT", 1, g.value("Active", expression=ACTIVE)),
    clear.inputs["Selection"],
)
out = g.n("NodeGroupOutput", "Output")
g.link(clear.outputs[0], out.inputs[0])
folder = ROOT / "work/fire-field-study"
folder.mkdir(parents=True, exist_ok=True)
for frame in (36, 40, 45):
    s.frame_set(frame)
    s.render.filepath = str(folder / f"fire-{frame:04}.png")
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(folder / "fire.blend"))
print("ORIGINAL_NATIVE_FLAME_FIELD_STUDY_COMPLETE")
