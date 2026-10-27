"""Stateless rolling dust, diffuse billows and small physical-looking grit."""

import math
import random

from mathutils import Vector

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


def _billows(root, quality):
    layer, g, geometry = _geometry(root, "Unequal Rolling Dust Banks")
    count, sides, rings = {"LOW": (9, 8, 6), "MEDIUM": (14, 12, 8), "HIGH": (20, 16, 10)}[quality]
    randomizer = random.Random(73)
    vertices, faces = [], []
    fields = {
        name: [] for name in ("dust_delay", "dust_seed", "dust_scale", "dust_lift", "dust_travel")
    }
    centers, directions, axes = [], [], []
    for index in range(count):
        cluster = index if index < 3 else (index - 3) % 3
        angle = (1.45, 0.12, 2.95)[cluster] + (0 if index < 3 else randomizer.uniform(-0.35, 0.35))
        direction = Vector((math.cos(angle), math.sin(angle) * 0.7, 0))
        travel = (0.22, 0.92, 1.0)[cluster] if index < 3 else randomizer.uniform(0.22, 0.82)
        scale = (1.15, 0.9, 0.8)[index] if index < 3 else randomizer.uniform(0.35, 0.7)
        delay = 0.015 * index if index < 3 else randomizer.uniform(0.02, 0.14)
        lift = (0.75, 0.45, 0.6)[index] if index < 3 else randomizer.uniform(0.2, 0.65)
        center = direction * 0.12 * travel + Vector((0, 0, 0.1))
        base = len(vertices)
        for j in range(rings + 1):
            theta = j * math.pi / rings
            for k in range(sides):
                phi = k * math.tau / sides
                local = (
                    Vector(
                        (
                            math.sin(theta) * math.cos(phi),
                            math.sin(theta) * math.sin(phi),
                            math.cos(theta),
                        )
                    )
                    * scale
                )
                vertices.append(tuple(center + local))
                centers.append(center)
                directions.append(direction)
                axes.append(Vector((-direction.y, direction.x, 0)).normalized())
                for name, value in zip(fields, (delay, index * 0.71, scale, lift, travel)):
                    fields[name].append(value)
        for j in range(rings):
            for k in range(sides):
                a, b = base + j * sides + k, base + j * sides + (k + 1) % sides
                faces.append((a, a + sides, b + sides, b))
    _mesh(layer, vertices, faces, fields)
    for polygon in layer.data.polygons:
        polygon.use_smooth = True
    for name, values in (
        ("dust_center", centers),
        ("dust_direction", directions),
        ("dust_roll_axis", axes),
    ):
        attribute = layer.data.attributes.new(name, "FLOAT_VECTOR", "POINT")
        for item, value in zip(attribute.data, values):
            item.vector = value
    p = g.value("Dust Clock", expression=PROGRESS)
    delay = g.attr("dust_delay")
    age = g.m(
        "Delayed Billow Age",
        "DIVIDE",
        g.m("Time Since Birth", "SUBTRACT", p, delay),
        g.m("Remaining Span", "SUBTRACT", 1, delay),
    )
    age = g.m("Nonnegative Age", "MAXIMUM", age, 0)
    age = g.m("Bounded Age", "MINIMUM", age, 1)
    ignite = g.stage("Volume Rolls Up", age, 0, 0.23)
    loss = g.m(
        "Volume Dissipation",
        "MULTIPLY",
        g.stage("Volume Thins", age, 0.58, 1),
        g.value("Fade", prop="fade"),
    )
    size = g.m(
        "Growing Then Dissipating Volume",
        "MULTIPLY",
        ignite,
        g.m("Remaining Volume", "SUBTRACT", 1, loss),
    )
    position = g.n("GeometryNodeInputPosition", "Editable Billow Rest Shape")
    local = g.v(
        "Local Billow Surface",
        "SUBTRACT",
        position.outputs[0],
        g.attr("dust_center", "FLOAT_VECTOR"),
    )
    noise = g.n("ShaderNodeTexNoise", "Broad Rolling Lobes", noise_dimensions="4D")
    g.link(local, noise.inputs["Vector"])
    g.link(g.value("Billow Detail", prop="noise_scale"), noise.inputs["Scale"])
    noise.inputs["Detail"].default_value = 1.0
    g.link(
        g.m(
            "Lobes Evolve",
            "ADD",
            g.attr("dust_seed"),
            g.m("Slow Cloud Evolution", "MULTIPLY", age, 0.7),
        ),
        noise.inputs["W"],
    )
    bulge = g.m("Uneven Billow Silhouette", "MULTIPLY_ADD", noise.outputs["Fac"], 0.6)
    bulge.node.inputs[2].default_value = 0.72
    local = g.v("Sculpted Dust Volume", "SCALE", local, bulge)
    roll = g.n("ShaderNodeVectorRotate", "Billows Curl As They Spread", rotation_type="AXIS_ANGLE")
    g.link(local, roll.inputs["Vector"])
    g.link(g.attr("dust_roll_axis", "FLOAT_VECTOR"), roll.inputs["Axis"])
    g.link(g.m("Billow Roll", "MULTIPLY", age, g.value("Roll Speed", 1.7)), roll.inputs["Angle"])
    local = g.v(
        "Billow Width Over Life",
        "SCALE",
        roll.outputs[0],
        g.m(
            "Local Volume Scale",
            "MULTIPLY",
            size,
            g.m("Half Cloud Width", "MULTIPLY", g.value("Width", prop="width"), 0.5),
        ),
    )
    ease = g.m(
        "Horizontal Motion Slows",
        "SUBTRACT",
        1,
        g.m("Remaining Motion", "POWER", g.m("Remaining Life", "SUBTRACT", 1, age), 3),
    )
    distance = g.m(
        "Distance From Impact",
        "ADD",
        g.value("Initial Radius", prop="radius"),
        g.m("Outward Expansion", "MULTIPLY", ease, g.value("Expansion", prop="expansion")),
    )
    distance = g.m("Different Travel Distances", "MULTIPLY", distance, g.attr("dust_travel"))
    center = g.v(
        "Unequal Spreading Banks", "SCALE", g.attr("dust_direction", "FLOAT_VECTOR"), distance
    )
    lift = g.m(
        "Billows Rise",
        "MULTIPLY",
        g.m("Rising Motion", "POWER", age, 1.3),
        g.m("Independent Rise", "MULTIPLY", g.attr("dust_lift"), g.value("Rise Height", 0.85)),
    )
    lift = g.m(
        "Ground Clearance",
        "ADD",
        lift,
        g.m(
            "Billow Ground Height",
            "MULTIPLY",
            ignite,
            g.m("Rest Height", "MULTIPLY", g.attr("dust_scale"), 0.12),
        ),
    )
    center = g.v("Rising Dust Centers", "ADD", center, g.xyz("Rise Above Ground", 0, 0, lift))
    deform = g.n("GeometryNodeSetPosition", "Native Rolling Dust")
    g.link(geometry, deform.inputs["Geometry"])
    g.link(g.v("Rolling Billows", "ADD", center, local), deform.inputs["Position"])
    store = g.n(
        "GeometryNodeStoreNamedAttribute",
        "Each Billow Keeps Its Age",
        data_type="FLOAT",
        domain="POINT",
    )
    store.inputs["Name"].default_value = "dust_age"
    g.link(deform.outputs[0], store.inputs["Geometry"])
    g.link(age, store.inputs["Value"])
    cut = g.n("GeometryNodeDeleteGeometry", "Frayed Dissipation", domain="FACE")
    erosion = g.m(
        "Erosion Threshold",
        "ADD",
        g.value("Dissolve", prop="dissolve"),
        g.m("Late Cloud Fraying", "MULTIPLY", loss, 0.65),
    )
    g.link(store.outputs[0], cut.inputs["Geometry"])
    g.link(
        g.m("Lost Smoke Surface", "LESS_THAN", noise.outputs["Fac"], erosion),
        cut.inputs["Selection"],
    )
    hide = g.n("GeometryNodeDeleteGeometry", "Only Living Billows", domain="POINT")
    inactive = g.m("Outside Lifetime", "LESS_THAN", g.value("Active", expression=ACTIVE), 0.5)
    empty = g.m("Volume Is Gone", "LESS_THAN", size, 0.015)
    invisible = g.m(
        "Fully Dissolved", "GREATER_THAN", g.value("Visibility Dissolve", prop="dissolve"), 0.9999
    )
    g.link(cut.outputs[0], hide.inputs["Geometry"])
    g.link(
        g.m(
            "Invisible Billows",
            "MAXIMUM",
            inactive,
            g.m("Spent Or Dissolved", "MAXIMUM", empty, invisible),
        ),
        hide.inputs["Selection"],
    )
    out = g.n("NodeGroupOutput", "Output")
    g.link(hide.outputs[0], out.inputs["Geometry"])
    root["vfx_parameter_keys"] = "radius,width,expansion,noise_scale,dissolve,fade"
    _diffuse(root)


def create(context, quality="MEDIUM"):
    if quality not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("Unknown dust quality")
    body = core.create(context, "ENERGY_RING", quality)
    start = float(body["start"])
    for key, value in dict(
        radius=0.06,
        width=1.15,
        expansion=1.6,
        noise_scale=3.5,
        duration=32.0,
        dissolve=0.0,
        fade=1.0,
        loop=False,
    ).items():
        body[key] = value
    for i, value in enumerate((0.32, 0.25, 0.18)):
        body[f"color_{i}"] = value
    body.name = "Dust • Rolling Banks"
    _billows(body, quality)
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
