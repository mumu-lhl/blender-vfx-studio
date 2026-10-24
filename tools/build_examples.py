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
