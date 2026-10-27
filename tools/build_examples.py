"""Build native starter assets and embedded CPU previews in a fresh process."""

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
from blender_vfx_studio.nodes import drive, node  # noqa: E402

EXAMPLES = ("energy-charge", "impact-burst", "arc-slash", "lightning-strike")
QUALITY_ASSETS = ("lightning-strike",)
PREVIEWS = {
    "energy-charge": (31, (4, -6, 3.5), (0, 0, 0.1), 4.8),
    "impact-burst": (5, (3, -5, 6), (0, 0, 0), 5.0),
    "arc-slash": (5, (0, 0, 8), (0, 0, 0), 5.4),
    "lightning-strike": (4, (4, -6, 3.8), (0, 0, 1.6), 5.2),
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


def create_effect(key, *, quality=None):
    if key not in EXAMPLES:
        raise ValueError("Unknown starter effect")
    if quality is not None and key not in QUALITY_ASSETS:
        raise ValueError("This starter asset keeps its original quality")
    context = bpy.context
    context.scene.frame_set(1)
    if key == "energy-charge":
        from tools.charge_design import core_shape, ribbons, spiral_motes

        color = (0.03, 0.45, 1.0)
        outer = configure(
            core.create(context, "ENERGY_RING", "LOW"),
            color,
            radius=1.65,
            width=0.06,
            strength=0.9,
            duration=48.0,
            dissolve=0.08,
            noise_scale=7.0,
            fade=1.0,
        )
        outer.name = "Charge • Converging Vortex"
        inner = configure(
            core.create(context, "ENERGY_RING", "LOW"),
            color,
            radius=1.55,
            width=0.09,
            strength=0.45,
            duration=48.0,
            dissolve=0.08,
            noise_scale=7.0,
            fade=1.0,
        )
        inner.name = "Charge • Ground Intake"
        inner.location.z = -0.8
        shield = configure(
            core.create_shield(context, "LOW"),
            color,
            radius=0.75,
            opacity=1.0,
            strength=1.2,
            duration=48.0,
            dissolve=0.08,
            noise_scale=4.5,
            fade=1.0,
        )
        shield.name = "Charge • Compressed Core"
        particles = configure(
            core.create_emitter(context),
            color,
            rate=14.0,
            lifetime=0.8,
            emission_seconds=1.2,
            duration=48.0,
            velocity=2.6,
            gravity=0.0,
            spread=1.0,
            randomness=0.0,
            spawn_radius=1.7,
            size=0.07,
            strength=2.0,
            seed=9,
        )
        particles.name = "Charge • Spiral Motes"
        _shape_charge_motes(particles)
        core_shape(shield)
        ribbons(outer)
        ribbons(inner, ground=True)
        spiral_motes(particles)
        for member in (outer, inner, shield):
            member.children[0].data.materials[0].surface_render_method = "BLENDED"
        # Depth-correct cutouts keep the inner nucleus behind the outer shell in Eevee.
        shield.children[0].data.materials[0].surface_render_method = "DITHERED"
        root = composition.create(context, [outer, inner, shield, particles])
        root.name = "Energy Charge"
    elif key == "lightning-strike":
        from tools.lightning_asset import create

        root = create(context, "MEDIUM" if quality is None else quality)
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
    entries = [(key, None, key + ".blend") for key in EXAMPLES]
    entries += [
        (key, quality, f"quality/{key}-{quality.lower()}.blend")
        for key in QUALITY_ASSETS
        for quality in ("LOW", "HIGH")
    ]
    for key, quality, relative in entries:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        root = create_effect(key, quality=quality)
        if quality:
            root.name += " [" + quality + "]"
        preview_scene(key)
        path = previews / (Path(relative).stem + ".png")
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(path), check_existing=False)
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
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
                archive.write(path, path.relative_to(output).as_posix())
            archive.write(guide, "README.md")
            archive.write(ROOT / "LICENSE", "LICENSE")
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print("STARTER_LIBRARY_BUILT", destination)


if __name__ == "__main__":
    main()
