"""Stateless rolling dust, diffuse billows and small physical-looking grit."""

import math
import random

from blender_vfx_studio import composition, core
from blender_vfx_studio.nodes import ACTIVE, PROGRESS, drive
from tools.charge_design import _Fields, _geometry, _mesh


def _color(g, root, name="Editable Dust Color"):
    color = g.n("ShaderNodeCombineXYZ", name)
    for i in range(3):
        drive(color.inputs[i], "default_value", root, "c", {"c": f"color_{i}"})
    return color.outputs[0]


def _diffuse(root, *, haze=False, grit=False):
    material = root.children[0].data.materials[0]
    material.name = (
        "VFX • Dust Grit" if grit else "VFX • Ground Dust" if haze else "VFX • Rolling Dust"
    )
    tree = material.node_tree
    tree.animation_data_clear()
    tree.nodes.clear()
    material.surface_render_method = "DITHERED"
    material.use_backface_culling = not haze
    g = _Fields(tree, root)
    color = _color(g, root)
    diffuse = g.n("ShaderNodeBsdfPrincipled", "Rough Nonemissive Dust")
    diffuse.inputs["Roughness"].default_value = 1
    diffuse.inputs["Specular IOR Level"].default_value = 0
    g.link(color, diffuse.inputs["Base Color"])
    if grit:
        out = g.n("ShaderNodeOutputMaterial", "Output")
        g.link(diffuse.outputs[0], out.inputs["Surface"])
        return
    coordinates = g.n("ShaderNodeTexCoord", "Cloud Coordinates")
    noise = g.n("ShaderNodeTexNoise", "Painted Dust Variation", noise_dimensions="3D")
    g.link(coordinates.outputs["Generated"], noise.inputs["Vector"])
    g.link(g.value("Surface Detail", prop="noise_scale"), noise.inputs["Scale"])
    noise.inputs["Detail"].default_value = 1.2
    value = g.m("Soft Surface Values", "MULTIPLY_ADD", noise.outputs["Fac"], 0.35)
    value.node.inputs[2].default_value = 0.7
    g.link(
        g.v("Dust Color With Internal Values", "SCALE", color, value), diffuse.inputs["Base Color"]
    )
    p = g.value("Dust Clock", expression=PROGRESS)
    if haze:
        alpha = g.m(
            "Ground Veil Density",
            "MULTIPLY",
            g.value("Ground Density", 0.18),
            g.m(
                "Veil Lifetime",
                "MULTIPLY",
                g.stage("Veil Ignites", p, 0, 0.12),
                g.m("Veil Dissipates", "SUBTRACT", 1, g.stage("Veil Fades", p, 0.45, 1)),
            ),
        )
        inner = g.n("ShaderNodeAttribute", "Soft Outside Edge", attribute_name="vfx_inner")
        alpha = g.m(
            "Feathered Ground Veil",
            "MULTIPLY",
            alpha,
            g.stage("Outer Edge Softness", inner.outputs["Fac"], 0, 0.3),
        )
    else:
        age = g.n("ShaderNodeAttribute", "Each Billow Age", attribute_name="dust_age")
        geometry = g.n("ShaderNodeNewGeometry", "Billow Surface")
        facing = g.n("ShaderNodeVectorMath", "Billow Facing", operation="DOT_PRODUCT")
        g.link(geometry.outputs["Normal"], facing.inputs[0])
        g.link(geometry.outputs["Incoming"], facing.inputs[1])
        edge = g.stage(
            "Soft Billow Border",
            g.m("Two Sided Facing", "ABSOLUTE", facing.outputs["Value"]),
            0.04,
            0.38,
        )
        alpha = g.m("Cloud Density", "MULTIPLY", edge, g.value("Billow Density", 0.82))
        alpha = g.m(
            "Dust Appears",
            "MULTIPLY",
            alpha,
            g.stage("Density Builds", age.outputs["Fac"], 0, 0.18),
        )
        fade = g.m(
            "Density Releases",
            "MULTIPLY",
            g.stage("Density Thins", age.outputs["Fac"], 0.58, 1),
            g.value("Fade", prop="fade"),
        )
        alpha = g.m(
            "Smoke Dissipation", "MULTIPLY", alpha, g.m("Remaining Density", "SUBTRACT", 1, fade)
        )
        bump = g.n("ShaderNodeBump", "Subtle Billow Folds")
        bump.inputs["Strength"].default_value = 0.17
        bump.inputs["Distance"].default_value = 0.08
        g.link(noise.outputs["Fac"], bump.inputs["Height"])
        g.link(bump.outputs["Normal"], diffuse.inputs["Normal"])
    transparent = g.n("ShaderNodeBsdfTransparent", "Air Between Billows")
    mix = g.n("ShaderNodeMixShader", "Dust In Air")
    g.link(alpha, mix.inputs[0])
    g.link(transparent.outputs[0], mix.inputs[1])
    g.link(diffuse.outputs[0], mix.inputs[2])
    out = g.n("ShaderNodeOutputMaterial", "Output")
    g.link(mix.outputs[0], out.inputs["Surface"])


def _volume(root, quality):
    """One bounded density field avoids stacks of translucent spherical shells."""
    layer, g, geometry = _geometry(root, "Procedural Dust Density Bounds")
    vertices = [
        (-1, -1, 0),
        (1, -1, 0),
        (1, 1, 0),
        (-1, 1, 0),
        (-1, -1, 1),
        (1, -1, 1),
        (1, 1, 1),
        (-1, 1, 1),
    ]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    _mesh(layer, vertices, faces)
    layer.display_type = "WIRE"
    radius, width, expansion = [
        g.value(name, prop=prop)
        for name, prop in (
            ("Initial Radius", "radius"),
            ("Billow Width", "width"),
            ("Expansion", "expansion"),
        )
    ]
    extent_x = g.m(
        "Horizontal Density Bounds",
        "ADD",
        g.m("Spread Bounds", "ADD", radius, expansion),
        g.m("Billow Padding", "MULTIPLY", width, 0.85),
    )
    extent_y = g.m(
        "Depth Density Bounds",
        "ADD",
        g.m("Depth Spread", "ADD", radius, g.m("Depth Expansion", "MULTIPLY", expansion, 0.7)),
        g.m("Depth Padding", "MULTIPLY", width, 0.85),
    )
    height = g.m(
        "Vertical Density Bounds",
        "ADD",
        g.value("Rise Height", prop="Dust Rise Height"),
        g.m("Top Padding", "MULTIPLY_ADD", width, 0.7),
    )
    g.tree.nodes["Top Padding"].inputs[2].default_value = 0.15
    domain = g.n("GeometryNodeTransform", "Density Domain Follows Editable Parameters")
    g.link(geometry, domain.inputs["Geometry"])
    g.link(g.xyz("Density Domain Size", extent_x, extent_y, height), domain.inputs["Scale"])
    bounds = g.n("GeometryNodeBoundBox", "Density Grid Bounds")
    g.link(domain.outputs[0], bounds.inputs["Geometry"])
    position = g.n("GeometryNodeInputPosition", "Density Voxel Position")
    density = _density(g, position.outputs[0], quality)
    grid = g.n("GeometryNodeVolumeCube", "Native Procedural Dust Grid")
    for axis, resolution in zip(
        "XYZ", {"LOW": (20, 20, 14), "MEDIUM": (32, 32, 24), "HIGH": (48, 48, 36)}[quality]
    ):
        grid.inputs["Resolution " + axis].default_value = resolution
    g.link(density, grid.inputs["Density"])
    g.link(bounds.outputs["Min"], grid.inputs["Min"])
    g.link(bounds.outputs["Max"], grid.inputs["Max"])
    # Loose edges keep the editable domain visible in Solid mode; they do not render faces.
    wire = g.n(
        "GeometryNodeDeleteGeometry", "Editable Wire Domain", domain="FACE", mode="ONLY_FACE"
    )
    wire.inputs["Selection"].default_value = True
    g.link(domain.outputs[0], wire.inputs["Geometry"])
    joined = g.n("GeometryNodeJoinGeometry", "Density And Native Domain Handles")
    g.link(grid.outputs[0], joined.inputs[0])
    g.link(wire.outputs[0], joined.inputs[0])
    inactive = g.m("Outside Lifetime", "LESS_THAN", g.value("Active", expression=ACTIVE), 0.5)
    invisible = g.m("Fully Dissolved", "GREATER_THAN", g.value("Dissolve", prop="dissolve"), 0.9999)
    zero = g.m("Density Is Off", "LESS_THAN", g.value("Density", prop="Dust Density"), 1e-6)
    hide = g.n("GeometryNodeSwitch", "Skip Invisible Density Grids", input_type="GEOMETRY")
    g.link(
        g.m("Hidden Density", "MAXIMUM", inactive, g.m("No Dust", "MAXIMUM", invisible, zero)),
        hide.inputs["Switch"],
    )
    g.link(joined.outputs[0], hide.inputs["False"])
    output = g.n("NodeGroupOutput", "Output")
    g.link(hide.outputs[0], output.inputs["Geometry"])
    root["vfx_parameter_keys"] = "radius,width,expansion,noise_scale,dissolve,fade"
    material = layer.data.materials[0]
    material.name = "VFX • Rolling Dust Volume"
    material.node_tree.animation_data_clear()
    material.node_tree.nodes.clear()
    g = _Fields(material.node_tree, root)
    volume = g.n("ShaderNodeVolumePrincipled", "Nonemissive Dust Volume")
    # The generated native grid supplies the density attribute; no mesh-boundary medium.
    volume.inputs["Density"].default_value = 1.0
    volume.inputs["Anisotropy"].default_value = 0.1
    g.link(_color(g, root), volume.inputs["Color"])
    out = g.n("ShaderNodeOutputMaterial", "Output")
    g.link(volume.outputs["Volume"], out.inputs["Volume"])


def _density(g, position, quality):
    p = g.value("Dust Clock", expression=PROGRESS)
    noise = g.n("ShaderNodeTexNoise", "Advected Cloud Folds", noise_dimensions="4D")
    shift = g.m(
        "Upward Rolling Pattern", "MULTIPLY", p, g.value("Roll Speed", prop="Dust Roll Speed")
    )
    sample = g.v(
        "Noise Rises Through The Cloud",
        "SUBTRACT",
        position,
        g.xyz("Rising Pattern", 0, 0, shift),
    )
    g.link(sample, noise.inputs["Vector"])
    g.link(g.value("Noise Detail", prop="noise_scale"), noise.inputs["Scale"])
    noise.inputs["Detail"].default_value = {"LOW": 0.5, "MEDIUM": 1.2, "HIGH": 2.0}[quality]
    g.link(g.m("Slow Cloud Evolution", "MULTIPLY", p, 0.4), noise.inputs["W"])
    warped = g.v(
        "Broad Density Folds",
        "ADD",
        position,
        g.v(
            "Curl The Density Surface",
            "SCALE",
            g.v("Signed Cloud Noise", "SUBTRACT", noise.outputs["Color"], (0.5, 0.5, 0.5)),
            g.m("Fold Size", "MULTIPLY", g.value("Width", prop="width"), 0.4),
        ),
    )
    count = {"LOW": 5, "MEDIUM": 7, "HIGH": 10}[quality]
    randomizer = random.Random(73)
    density = 0
    for index in range(count):
        prefix = f"Billow {index + 1}"
        cluster = index if index < 3 else (index - 3) % 3
        angle = (1.45, 0.12, 2.95)[cluster] + (0 if index < 3 else randomizer.uniform(-0.35, 0.35))
        travel = (0.22, 0.92, 1.0)[cluster] if index < 3 else randomizer.uniform(0.22, 0.82)
        scale = (1.15, 0.9, 0.8)[index] if index < 3 else randomizer.uniform(0.38, 0.7)
        delay = index * 0.015 if index < 3 else randomizer.uniform(0.02, 0.14)
        lift = (0.75, 0.45, 0.6)[index] if index < 3 else randomizer.uniform(0.2, 0.65)
        age = g.m(
            prefix + " Age", "DIVIDE", g.m(prefix + " Since Birth", "SUBTRACT", p, delay), 1 - delay
        )
        age = g.m(prefix + " Nonnegative Age", "MAXIMUM", age, 0)
        age = g.m(prefix + " Bounded Age", "MINIMUM", age, 1)
        grow = g.stage(prefix + " Rolls Up", age, 0, 0.23)
        loss = g.m(
            prefix + " Density Loss",
            "MULTIPLY",
            g.stage(prefix + " Releases", age, 0.58, 1),
            g.value(prefix + " Fade", prop="fade"),
        )
        size = g.m(
            prefix + " Size",
            "MULTIPLY",
            grow,
            g.m(prefix + " Remaining Volume", "SUBTRACT", 1, loss),
        )
        ease = g.m(
            prefix + " Slowing Spread",
            "SUBTRACT",
            1,
            g.m(
                prefix + " Motion Cube",
                "POWER",
                g.m(prefix + " Remaining Time", "SUBTRACT", 1, age),
                3,
            ),
        )
        distance = g.m(
            prefix + " Travel",
            "MULTIPLY",
            travel,
            g.m(
                prefix + " Radius",
                "ADD",
                g.value(prefix + " Initial Radius", prop="radius"),
                g.m(
                    prefix + " Expansion",
                    "MULTIPLY",
                    ease,
                    g.value(prefix + " Outward Travel", prop="expansion"),
                ),
            ),
        )
        height = g.m(
            prefix + " Rise",
            "MULTIPLY",
            g.m(prefix + " Rising Age", "POWER", age, 1.3),
            g.m(
                prefix + " Rise Height",
                "MULTIPLY",
                lift,
                g.value(prefix + " Editable Rise", prop="Dust Rise Height"),
            ),
        )
        height = g.m(prefix + " Above Ground", "ADD", height, 0.12 * scale)
        center = g.xyz(
            prefix + " Center",
            g.m(prefix + " X", "MULTIPLY", distance, math.cos(angle)),
            g.m(prefix + " Y", "MULTIPLY", distance, math.sin(angle) * 0.7),
            height,
        )
        radius = g.m(
            prefix + " Width",
            "MULTIPLY",
            g.value(prefix + " Cloud Width", prop="width"),
            scale * 0.55,
        )
        radius = g.m(prefix + " Growing Radius", "MULTIPLY", radius, size)
        radius = g.m(prefix + " Safe Radius", "MAXIMUM", radius, 0.0001)
        dist = g.n("ShaderNodeVectorMath", prefix + " Distance", operation="DISTANCE")
        g.link(warped, dist.inputs[0])
        g.link(center, dist.inputs[1])
        relative = g.m(prefix + " Relative Distance", "DIVIDE", dist.outputs["Value"], radius)
        soft = g.m(
            prefix + " Soft Density",
            "MAXIMUM",
            g.m(
                prefix + " Feathered Shape",
                "SUBTRACT",
                1,
                g.m(prefix + " Squared Radius", "MULTIPLY", relative, relative),
            ),
            0,
        )
        soft = g.m(prefix + " Soft Interior", "MULTIPLY", soft, soft)
        soft = g.m(
            prefix + " Dissipating Density",
            "MULTIPLY",
            soft,
            g.m(prefix + " Remaining Density", "SUBTRACT", 1, loss),
        )
        density = g.m(prefix + " Joins Cloud", "ADD", density, soft)
    variation = g.m("Cloud Density Variation", "MULTIPLY_ADD", noise.outputs["Fac"], 0.7)
    variation.node.inputs[2].default_value = 0.3
    density = g.m("Turbulent Density", "MULTIPLY", density, variation)
    dissolve = g.value("Dissolve", prop="dissolve")
    density = g.m(
        "Eroding Density", "MAXIMUM", g.m("Dust Dissolves", "SUBTRACT", density, dissolve), 0
    )
    density = g.m(
        "Dust Optical Density", "MULTIPLY", density, g.value("Density", prop="Dust Density")
    )
    return density


def create(context, quality="MEDIUM"):
    if quality not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("Unknown dust quality")
    body = core.create(context, "ENERGY_RING", quality)
    start = float(body["start"])
    for key, value in dict(
        radius=0.06,
        width=1.7,
        expansion=1.3,
        noise_scale=3.5,
        duration=32.0,
        dissolve=0.0,
        fade=1.0,
        loop=False,
    ).items():
        body[key] = value
    for i, value in enumerate((0.56, 0.46, 0.34)):
        body[f"color_{i}"] = value
    body.name = "Dust • Rolling Banks"
    for name, value, maximum in (
        ("Dust Rise Height", 0.85, 10.0),
        ("Dust Roll Speed", 1.7, 10.0),
        ("Dust Density", 8.0, 40.0),
    ):
        body[name] = value
        body.id_properties_ui(name).update(min=0.0, max=maximum, description=name)
    _volume(body, quality)
    haze = core.create(context, "SHOCKWAVE", quality)
    for key, value in dict(
        start=start,
        duration=26.0,
        radius=0.06,
        width=1.2,
        expansion=1.7,
        noise_scale=3.0,
        dissolve=0.0,
        fade=1.0,
        loop=False,
    ).items():
        haze[key] = value
    haze.location.z += 0.025
    for i, value in enumerate((0.20, 0.15, 0.10)):
        haze[f"color_{i}"] = value
    haze.name = "Dust • Ground Veil"
    haze["vfx_parameter_keys"] = "radius,width,expansion,noise_scale,fade"
    _diffuse(haze, haze=True)
    grit = core.create_particle(context, quality)
    for key, value in dict(
        start=start,
        duration=16.0,
        count={"LOW": 8, "MEDIUM": 14, "HIGH": 20}[quality],
        size=0.035,
        shape=1.0,
        stretch=2.0,
        planar=0.5,
        velocity=2.2,
        gravity=4.0,
        spread=1.0,
        randomness=0.8,
        spawn_radius=0.05,
        fade=1.0,
        seed=29,
        loop=False,
    ).items():
        grit[key] = value
    for i, value in enumerate((0.15, 0.10, 0.055)):
        grit[f"color_{i}"] = value
    grit.name = "Dust • Small Grit"
    grit["vfx_parameter_keys"] = (
        "count,size,shape,stretch,planar,motion_seconds,motion_ease,velocity,gravity,spread,randomness,spawn_radius,fade,seed"
    )
    _diffuse(grit, grit=True)
    for member in (body, haze, grit):
        member.update_tag()
    root = composition.create(context, [body, haze, grit])
    root.name, root["vfx_quality"] = "Dust Impact", quality
    root["loop"] = False
    root.update_tag()
    context.view_layer.update()
    return root
