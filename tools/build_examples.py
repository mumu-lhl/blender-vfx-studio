"""Build three native starter assets and embedded CPU previews in a fresh process."""

import os
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import assets, composition, core  # noqa: E402
from blender_vfx_studio.nodes import PROGRESS, TIME_PROPS, drive, node  # noqa: E402

EXAMPLES = ("energy-charge", "impact-burst", "arc-slash")
PREVIEWS = {
    "energy-charge": (22, (4, -6, 3.5), (0, 0, 0.1), 4.8),
    "impact-burst": (5, (3, -5, 6), (0, 0, 0), 5.0),
    "arc-slash": (5, (0, 0, 8), (0, 0, 0), 5.4),
}


def configure(root, color, **values):
    for i, value in enumerate(color):
        root[f"color_{i}"] = value
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    return root


def _shape_charge_motes(particles):
    """Author only this complete asset's private native shape and tip gradient."""
    tree = particles.children[0].modifiers[0].node_group
    # Low-poly pointed motes replace the LOW icospheres without adding particles.
    shard = node(tree, "GeometryNodeMeshUVSphere", "Charge Mote Shape", 500, 1700)
    shard.inputs["Segments"].default_value = 4
    shard.inputs["Rings"].default_value = 3
    shard.inputs["Radius"].default_value = 1
    position = node(tree, "GeometryNodeInputPosition", "Mote Local Position", 0, 2100)
    axes = node(tree, "ShaderNodeSeparateXYZ", "Mote Tip Axis", 200, 2100)
    tree.links.new(position.outputs[0], axes.inputs[0])
    heat = node(tree, "ShaderNodeMath", "Tail To Leading Tip", 400, 2100, operation="MULTIPLY_ADD")
    tree.links.new(axes.outputs["Z"], heat.inputs[0])
    heat.inputs[1].default_value, heat.inputs[2].default_value = 0.5, 0.5
    store = node(
        tree,
        "GeometryNodeStoreNamedAttribute",
        "Charge Tip Gradient",
        700,
        1700,
        data_type="FLOAT",
        domain="POINT",
    )
    store.inputs["Name"].default_value = "vfx_charge_tip"
    tree.links.new(shard.outputs["Mesh"], store.inputs["Geometry"])
    tree.links.new(heat.outputs[0], store.inputs["Value"])
    tree.links.new(store.outputs["Geometry"], tree.nodes["Particle Material"].inputs["Geometry"])
    shape = node(tree, "ShaderNodeVectorMath", "Mote Proportions", 700, 1300, operation="SCALE")
    shape.inputs[0].default_value = (0.4, 0.4, 2.6)
    tree.links.new(tree.nodes["Particle Scale"].outputs[0], shape.inputs["Scale"])
    tree.links.new(shape.outputs[0], tree.nodes["Particle Instances"].inputs["Scale"])
    inward = node(
        tree, "ShaderNodeVectorMath", "Leading Tip Toward Center", 700, 1000, operation="SCALE"
    )
    inward.inputs["Scale"].default_value = -1
    tree.links.new(tree.nodes["Direction"].outputs[0], inward.inputs[0])
    align = node(tree, "FunctionNodeAlignEulerToVector", "Aim Mote Inward", 950, 1000, axis="Z")
    tree.links.new(inward.outputs[0], align.inputs["Vector"])
    tree.links.new(align.outputs["Rotation"], tree.nodes["Particle Instances"].inputs["Rotation"])
    material = particles.children[0].data.materials[0].node_tree
    tip = node(
        material,
        "ShaderNodeAttribute",
        "Charge Leading Tip",
        -1000,
        400,
        attribute_name="vfx_charge_tip",
    )
    color = node(material, "ShaderNodeCombineXYZ", "Editable Mote Color", -1000, 0)
    for index in range(3):
        drive(color.inputs[index], "default_value", particles, "p", {"p": f"color_{index}"})
    dark = node(material, "ShaderNodeVectorMath", "Mote Dark Tail", -750, -200, operation="SCALE")
    dark.inputs["Scale"].default_value = 0.2
    material.links.new(color.outputs[0], dark.inputs[0])
    gradient = node(material, "ShaderNodeMixRGB", "Tail To Cyan Tip", -500, 200)
    material.links.new(tip.outputs["Fac"], gradient.inputs[0])
    material.links.new(dark.outputs[0], gradient.inputs[1])
    material.links.new(color.outputs[0], gradient.inputs[2])
    material.links.new(gradient.outputs[0], material.nodes["Particle Emission"].inputs["Color"])


def _reveal_charge_ring(root, attack):
    """Draw two opposing arcs in this asset's private material, then close the ring."""
    tree = root.children[0].data.materials[0].node_tree
    link = tree.links.new
    progress = node(tree, "ShaderNodeValue", "Charge Progress", -1400, 1000)
    drive(progress.outputs[0], "default_value", root, PROGRESS, TIME_PROPS)
    duration = node(tree, "ShaderNodeValue", "Draw Duration", -1400, 800)
    duration.outputs[0].default_value = attack
    coverage = node(tree, "ShaderNodeMapRange", "Smooth Arc Reveal", -1150, 1000)
    coverage.interpolation_type = "SMOOTHSTEP"
    coverage.clamp = True
    link(progress.outputs[0], coverage.inputs["Value"])
    link(duration.outputs[0], coverage.inputs["From Max"])
    sectors = node(tree, "ShaderNodeMath", "Opposing Arc Starts", -1150, 650, operation="MULTIPLY")
    link(tree.nodes["Across Width"].outputs["X"], sectors.inputs[0])
    sectors.inputs[1].default_value = 2
    phase = node(tree, "ShaderNodeMath", "Arc Phase", -900, 650, operation="FRACT")
    link(sectors.outputs[0], phase.inputs[0])
    phase_range = node(tree, "ShaderNodeMath", "Closing Margin", -700, 650, operation="MULTIPLY")
    phase_range.inputs[1].default_value = 0.96
    link(phase.outputs[0], phase_range.inputs[0])
    distance = node(
        tree, "ShaderNodeMath", "Distance Behind Leading Edge", -650, 1000, operation="SUBTRACT"
    )
    link(coverage.outputs[0], distance.inputs[0])
    link(phase_range.outputs[0], distance.inputs[1])
    edge = node(tree, "ShaderNodeMapRange", "Soft Leading Edge", -400, 1000)
    edge.clamp = True
    edge.inputs["From Max"].default_value = 0.04
    link(distance.outputs[0], edge.inputs["Value"])
    buildup = node(tree, "ShaderNodeMath", "Stroke Build Up", -150, 1000, operation="MULTIPLY")
    link(edge.outputs[0], buildup.inputs[0])
    link(coverage.outputs[0], buildup.inputs[1])
    alpha = node(tree, "ShaderNodeMath", "Revealed Ring Opacity", 150, 1000, operation="MULTIPLY")
    link(tree.nodes["Opacity"].outputs[0], alpha.inputs[0])
    link(buildup.outputs[0], alpha.inputs[1])
    link(alpha.outputs[0], tree.nodes["Soft Dissolve Surface"].inputs[0])


def create_effect(key):
    if key not in EXAMPLES:
        raise ValueError("Unknown starter effect")
    context = bpy.context
    context.scene.frame_set(1)
    if key == "energy-charge":
        color = (0.03, 0.45, 1.0)
        outer = configure(
            core.create(context, "ENERGY_RING", "LOW"),
            color,
            radius=0.9,
            width=0.02,
            duration=48.0,
            strength=0.9,
            dissolve=0.12,
            fade=1.0,
        )
        outer.name = "Charge • Orbit"
        outer.rotation_euler = (1.1, 0.35, 0.25)
        drive(outer, "rotation_euler", outer, f"0.25+({PROGRESS})*6.283185", TIME_PROPS, 2)
        inner = configure(
            core.create(context, "ENERGY_RING", "LOW"),
            color,
            radius=1.35,
            width=0.025,
            duration=48.0,
            strength=0.6,
            dissolve=0.08,
            fade=1.0,
        )
        inner.location.z = -0.8
        shield = configure(
            core.create_shield(context, "LOW"),
            color,
            radius=0.65,
            opacity=0.95,
            strength=1.6,
            ior=1.3,
            rim_power=0.05,
            dissolve=0.1,
            flow=2.4,
            duration=48.0,
            fade=1.0,
        )
        # A dark center and cyan edge preserve a focal shape on pale backgrounds.
        tree = shield.children[0].data.materials[0].node_tree
        tint = node(tree, "ShaderNodeRGB", "Editable Charge Color", -750, -600)
        for index in range(3):
            drive(tint.outputs[0], "default_value", shield, "p", {"p": f"color_{index}"}, index)
        dark = node(tree, "ShaderNodeVectorMath", "Dark Charge Body", -500, -600, operation="SCALE")
        tree.links.new(tint.outputs[0], dark.inputs[0])
        dark.inputs["Scale"].default_value = 0.05
        gradient = node(tree, "ShaderNodeMixRGB", "Body To Cyan Rim", -250, -600)
        tree.links.new(tree.nodes["Fresnel Edge"].outputs[0], gradient.inputs[0])
        tree.links.new(dark.outputs[0], gradient.inputs[1])
        tree.links.new(tint.outputs[0], gradient.inputs[2])
        tree.links.new(gradient.outputs[0], tree.nodes["Shield Emission"].inputs["Color"])
        buildup = node(tree, "ShaderNodeValue", "Charge Build Up", -500, -850)
        drive(
            buildup.outputs[0],
            "default_value",
            shield,
            f"min(max(({PROGRESS})/0.3,0),1)",
            TIME_PROPS,
        )
        visible = node(tree, "ShaderNodeMath", "Gathering Opacity", 0, -600, operation="MULTIPLY")
        tree.links.new(tree.nodes["Final Opacity"].outputs[0], visible.inputs[0])
        tree.links.new(buildup.outputs[0], visible.inputs[1])
        tree.links.new(visible.outputs[0], tree.nodes["Shield Surface"].inputs[0])
        _reveal_charge_ring(inner, 0.22)
        _reveal_charge_ring(outer, 0.30)
        # Private starter materials: avoid noisy hashed transparency at low Eevee samples.
        for member in (outer, inner, shield):
            member.children[0].data.materials[0].surface_render_method = "BLENDED"
        particles = configure(
            core.create_emitter(context),
            color,
            rate=18.0,
            lifetime=0.8,
            emission_seconds=1.2,
            duration=48.0,
            velocity=1.5,
            gravity=0.0,
            spread=1.0,
            randomness=0.0,
            spawn_radius=1.4,
            size=0.035,
            strength=3.0,
            seed=9,
        )
        particles.name = "Charge • Inward Motes"
        # Edit only this asset's private native graph. Generic emitters still move outward.
        tree = particles.children[0].modifiers[0].node_group
        distance = tree.nodes["Radial Distance"]
        distance.name = distance.label = "Remaining Gathering Radius"
        distance.operation = "SUBTRACT"
        tree.links.new(tree.nodes["Spawn Radius"].outputs[0], distance.inputs[0])
        tree.links.new(tree.nodes["Travel"].outputs[0], distance.inputs[1])
        stop = node(tree, "ShaderNodeMath", "Stop At Center", 300, -450, operation="MAXIMUM")
        stop.inputs[1].default_value = 0
        tree.links.new(distance.outputs[0], stop.inputs[0])
        tree.links.new(stop.outputs[0], tree.nodes["Radial Motion"].inputs["Scale"])
        _shape_charge_motes(particles)
        particles.location.z = 0.0
        root = composition.create(context, [outer, inner, shield, particles])
        root.name = "Energy Charge"
    elif key == "impact-burst":
        root = core.create(context, "IMPACT_BURST", "LOW")
    else:
        root = core.create(context, "ARC_SLASH", "LOW")
        root["duration"] = 18.0
        root.name = "Arc Slash"
    root["loop"] = False
    root.update_tag()
    context.view_layer.update()
    return root


def preview_scene(key):
    """Preview-only helpers are deliberately outside the exported effect hierarchy."""
    scene = bpy.context.scene
    frame, location, target, scale = PREVIEWS[key]
    bpy.ops.object.camera_add(location=location)
    camera = bpy.context.object
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type, camera.data.ortho_scale = "ORTHO", scale
    scene.camera = camera
    scene.world = bpy.data.worlds.new("Starter Preview Background")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.003,
        0.005,
        0.008,
        1,
    )
    scene.render.engine = "CYCLES"
    scene.cycles.device, scene.cycles.samples = "CPU", 32
    scene.render.compositor_device = "CPU"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    if key == "energy-charge":
        glow = core.create_screen(bpy.context)
        glow["strength"], glow["fade"] = 0.25, 0.0
        glow.update_tag()
    scene.frame_set(frame)


def main():
    if not bpy.app.background or "--factory-startup" not in sys.argv or bpy.data.filepath:
        raise RuntimeError(
            "Use a fresh background process with --factory-startup and no open project"
        )
    version = tomllib.loads(
        (ROOT / "blender_vfx_studio/blender_manifest.toml").read_text(encoding="utf-8")
    )["version"]
    output = ROOT / "dist/examples"
    previews = ROOT / "work/examples"
    output.mkdir(parents=True, exist_ok=True)
    previews.mkdir(parents=True, exist_ok=True)
    files = []
    for key in EXAMPLES:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        root = create_effect(key)
        preview_scene(key)
        path = previews / (key + ".png")
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(path), check_existing=False)
        destination = output / (key + ".blend")
        assets.write(destination, root, preview_image=image)
        files.append(destination)
        print("STARTER_ASSET_BUILT", key, flush=True)
    guide = ROOT / "docs/STARTER_LIBRARY.md"
    destination = ROOT / "dist" / f"blender-vfx-studio-examples-{version}.zip"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", dir=destination.parent, delete=False) as f:
            temporary = Path(f.name)
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.name)
            archive.write(guide, "README.md")
            archive.write(ROOT / "LICENSE", "LICENSE")
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print("STARTER_LIBRARY_BUILT", destination)


if __name__ == "__main__":
    main()
