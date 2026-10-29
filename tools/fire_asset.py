"""Author a sculpted, rising flame with native deformation and painted heat bands."""

import math

from blender_vfx_studio import composition, core
from blender_vfx_studio.nodes import ACTIVE, PROGRESS, drive
from blender_vfx_studio.palettes import FIRE_PALETTES, FIRE_STOPS
from tools.charge_design import _Fields, _geometry, _mesh


def _flames(root, quality):
    layer, g, geometry = _geometry(root, "Rising Sculpted Flame")
    rows, sides = {"LOW": (14, 8), "MEDIUM": (22, 12), "HIGH": (30, 16)}[quality]
    vertices, faces, centers = [], [], []
    attributes = {k: [] for k in ("fire_u", "fire_lobe", "fire_inner")}
    # Unequal outer lobes and a smaller forward hot tongue share a grounded base.
    for index, (x, y, height, breadth, bend, inner) in enumerate(
        (
            (0, 0.03, 1, 0.50, -0.12, 0),
            (-0.26, 0, 0.83, 0.29, -0.20, 0),
            (0.28, 0.04, 0.68, 0.25, 0.24, 0),
            (0, -0.25, 0.52, 0.24, 0.17, 1),
            (0.06, 0.26, 0.44, 0.22, -0.14, 1),
        )
    ):
        base = len(vertices)
        for row in range(rows + 1):
            u = row / rows
            radius = max(0.002, (0.6 + 0.4 * math.sin(math.pi * u)) * (1 - u) ** 0.85 * breadth)
            cx = x * (1 - u) + bend * math.sin(math.pi * u) + 0.22 * math.sin(u * 5) * u
            cy = y * (1 - u * 0.5) + 0.13 * math.sin(u * 4 + index) * u
            for side in range(sides):
                a = side / sides * math.tau
                fold = 1 + 0.15 * math.sin(3 * a + u * 8 + index)
                vertices.append(
                    (
                        cx + math.cos(a) * radius * fold,
                        cy + math.sin(a) * radius * 0.65 * fold,
                        u * height,
                    )
                )
                centers.append((cx, cy, u * height))
                for key, value in zip(attributes, (u, index, inner)):
                    attributes[key].append(value)
        faces.append(tuple(base + side for side in reversed(range(sides))))
        for row in range(rows):
            for side in range(sides):
                a = base + row * sides + side
                b = base + row * sides + (side + 1) % sides
                faces.append((a, b, b + sides, a + sides))
    _mesh(layer, vertices, faces, attributes)
    rest = layer.data.attributes.new("fire_center", "FLOAT_VECTOR", "POINT")
    for item, center in zip(rest.data, centers):
        item.vector = center
    for face in layer.data.polygons:
        face.use_smooth = True
    p = g.value("Fire Clock", expression=PROGRESS)
    ignite = g.stage("Fast Ignition", p, 0.01, 0.14)
    release = g.stage("Fuel Runs Out", p, 0.64, 1)
    remaining = g.m(
        "Remaining Fuel",
        "SUBTRACT",
        1,
        g.m("Editable Extinction", "MULTIPLY", release, g.value("Fade", prop="fade")),
    )
    envelope = g.m("Fire Envelope", "MULTIPLY", ignite, remaining)
    pos = g.n("GeometryNodeInputPosition", "Editable Rest Flame")
    axes = g.n("ShaderNodeSeparateXYZ", "Rest Axes")
    g.link(pos.outputs[0], axes.inputs[0])
    u = g.attr("fire_u")
    phase = g.m(
        "Flame Flow Phase",
        "SUBTRACT",
        g.m("Rolling Flame Time", "MULTIPLY", p, g.value("Flow Speed", prop="Fire Flow Speed")),
        g.m("Flow Up The Tongue", "MULTIPLY", u, 12),
    )
    phase = g.m(
        "Tongues Rise At Different Times",
        "ADD",
        phase,
        g.m("Tongue Phase", "MULTIPLY", g.attr("fire_lobe"), 1.9),
    )
    pulse = g.m(
        "Living Flame Breadth", "MULTIPLY_ADD", g.m("Travelling Flame Lobe", "SINE", phase), 0.32
    )
    pulse.node.inputs[2].default_value = 0.68
    pulse = g.m(
        "Keep A Connected Hot Foot",
        "ADD",
        1,
        g.m(
            "Necks Above The Foot",
            "MULTIPLY",
            g.stage("Neck Starts Above Ground", u, 0.08, 0.35),
            g.m("Travelling Neck Depth", "SUBTRACT", pulse, 1),
        ),
    )
    center = g.attr("fire_center", "FLOAT_VECTOR")
    section = g.v("Section Around Its Own Rising Path", "SUBTRACT", pos.outputs[0], center)
    section = g.v("Moving Bulges And Narrow Necks", "SCALE", section, pulse)
    rest_position = g.v("Connected Unequal Flame Streams", "ADD", center, section)
    g.link(rest_position, axes.inputs[0])
    width = g.value("Width", prop="width")
    width = g.m(
        "Ignition And Shrinking Breadth",
        "MULTIPLY",
        width,
        g.m("Soft Extinction", "SQRT", envelope),
    )
    height = g.value("Flame Height", prop="Fire Height")
    height = g.m(
        "Height During Ignition",
        "MULTIPLY",
        height,
        g.m("Growing Flame Height", "MULTIPLY_ADD", ignite, 0.7),
    )
    g.tree.nodes["Growing Flame Height"].inputs[2].default_value = 0.3
    position = g.xyz(
        "Flame Proportions",
        g.m("Flame X", "MULTIPLY", axes.outputs["X"], width),
        g.m("Flame Y", "MULTIPLY", axes.outputs["Y"], width),
        g.m("Flame Z", "MULTIPLY", axes.outputs["Z"], height),
    )
    noise = g.n("ShaderNodeTexNoise", "Large Moving Flame Folds", noise_dimensions="4D")
    g.link(pos.outputs[0], noise.inputs["Vector"])
    noise.inputs["Scale"].default_value = 2.3
    noise.inputs["Detail"].default_value = 1
    clock = g.m("Shared Flame Clock", "MULTIPLY", p, g.value("Flow Speed", prop="Fire Flow Speed"))
    g.link(g.m("Unsteady Flame Clock", "MULTIPLY", clock, 0.25), noise.inputs["W"])
    curl = g.v("Signed Flame Curl", "SUBTRACT", noise.outputs["Color"], (0.5, 0.5, 0.5))
    curl = g.v(
        "Curl Away From Ground",
        "SCALE",
        curl,
        g.m(
            "Editable Tip Curl",
            "MULTIPLY",
            g.m("Tip Curl Envelope", "POWER", u, 0.8),
            g.value("Curl", prop="Fire Curl"),
        ),
    )
    position = g.v("Moving Asymmetric Tongues", "ADD", position, curl)
    bend = g.m(
        "Rising Fold Envelope",
        "MULTIPLY",
        g.m("Fold Away From Ground", "POWER", u, 0.8),
        g.value("Curl", prop="Fire Curl"),
    )
    position = g.v(
        "Flame Folds Travel Upward",
        "ADD",
        position,
        g.xyz(
            "Two Plane Updraft",
            g.m(
                "Sideways Rising Fold",
                "MULTIPLY",
                g.m("Rolling Fold", "SINE", phase),
                g.m("Fold Width", "MULTIPLY", bend, 0.25),
            ),
            g.m(
                "Depth Of Rising Fold",
                "MULTIPLY",
                g.m("Turning Fold", "COSINE", phase),
                g.m("Fold Depth", "MULTIPLY", bend, 0.16),
            ),
            0,
        ),
    )
    position = g.v(
        "Last Flame Lifts Away",
        "ADD",
        position,
        g.xyz("Extinction Lift", 0, 0, g.m("Final Lift", "MULTIPLY", release, 0.45)),
    )
    deform = g.n("GeometryNodeSetPosition", "Native Flame Motion")
    g.link(geometry, deform.inputs["Geometry"])
    g.link(position, deform.inputs["Position"])
    hide = g.n("GeometryNodeDeleteGeometry", "Invisible Flame Cleanup", domain="POINT")
    inactive = g.m("Outside Lifetime", "LESS_THAN", g.value("Active", expression=ACTIVE), 0.5)
    empty = g.m("No Fuel", "LESS_THAN", envelope, 0.005)
    dissolved = g.m("Fully Dissolved", "GREATER_THAN", g.value("Dissolve", prop="dissolve"), 0.9999)
    g.link(deform.outputs[0], hide.inputs["Geometry"])
    g.link(
        g.m(
            "Hide Flame", "MAXIMUM", inactive, g.m("Off Or Dissolved", "MAXIMUM", empty, dissolved)
        ),
        hide.inputs["Selection"],
    )
    out = g.n("NodeGroupOutput", "Output")
    g.link(hide.outputs[0], out.inputs["Geometry"])
    root["vfx_parameter_keys"] = "width,strength,noise_scale,dissolve,fade"
    _material(root)


def _material(root):
    material = root.children[0].data.materials[0]
    material.name = "VFX • Painted Flame Heat"
    material.node_tree.animation_data_clear()
    material.node_tree.nodes.clear()
    material.surface_render_method = "DITHERED"
    g = _Fields(material.node_tree, root)
    p = g.value("Fire Clock", expression=PROGRESS)
    clock = g.m("Shared Flame Clock", "MULTIPLY", p, g.value("Flow Speed", prop="Fire Flow Speed"))
    coordinates = g.n("ShaderNodeTexCoord", "Local Flame Coordinates")
    noise = g.n("ShaderNodeTexNoise", "Rising Broken Heat Bands", noise_dimensions="4D")
    sample = g.v(
        "Long Vertical Flame Strokes", "MULTIPLY", coordinates.outputs["Object"], (1.6, 1.6, 0.85)
    )
    sample = g.v(
        "Heat Advects Upward",
        "SUBTRACT",
        sample,
        g.xyz("Rising Heat", 0, 0, g.m("Heat Speed", "MULTIPLY", clock, 0.25)),
    )
    g.link(sample, noise.inputs["Vector"])
    g.link(g.value("Heat Detail", prop="noise_scale"), noise.inputs["Scale"])
    noise.inputs["Detail"].default_value = 1.2
    g.link(g.m("Heat Evolution", "MULTIPLY", clock, 0.06), noise.inputs["W"])
    u = g.n("ShaderNodeAttribute", "Height Along Each Flame", attribute_name="fire_u").outputs[
        "Fac"
    ]
    inner = g.n("ShaderNodeAttribute", "Hot Inner Tongue", attribute_name="fire_inner").outputs[
        "Fac"
    ]
    heat = g.m("Hotter Flame Base", "SUBTRACT", 1.08, g.m("Cooler Tips", "MULTIPLY", u, 0.52))
    heat = g.m(
        "Heat Folds",
        "ADD",
        heat,
        g.m(
            "Broad Heat Variation",
            "MULTIPLY",
            g.m("Cool Clefts And Hot Streams", "SUBTRACT", noise.outputs["Fac"], 0.5),
            0.5,
        ),
    )
    heat = g.m("Inner Core Heat", "ADD", heat, g.m("Core Accent", "MULTIPLY", inner, 0.12))
    normal = g.n("ShaderNodeLayerWeight", "Dark Flame Boundary")
    heat = g.m(
        "Cool Edge",
        "SUBTRACT",
        heat,
        g.m("Edge Contrast", "MULTIPLY", normal.outputs["Facing"], 0.24),
    )
    ramp = g.n("ShaderNodeValToRGB", "Painted Red Orange Yellow")
    colors = tuple(zip(FIRE_STOPS, FIRE_PALETTES["ORANGE"]))
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = colors[0]
    for at, color in colors[1:]:
        ramp.color_ramp.elements.new(at).color = color
    ramp.color_ramp.interpolation = "EASE"
    g.link(heat, ramp.inputs[0])
    tint = g.n("ShaderNodeCombineXYZ", "Editable Flame Tint")
    for index in range(3):
        drive(tint.inputs[index], "default_value", root, "p", {"p": f"color_{index}"})
    color = g.v("Tinted Heat Bands", "MULTIPLY", ramp.outputs["Color"], tint.outputs[0])
    emission = g.n("ShaderNodeEmission", "Flame Radiance")
    g.link(color, emission.inputs["Color"])
    g.link(g.value("Strength", prop="strength"), emission.inputs["Strength"])
    release = g.stage("Late Extinction", p, 0.64, 1)
    threshold = g.m(
        "Living Flame Separates Toward The Crown",
        "MULTIPLY_ADD",
        g.m("Upper Flame Breakup", "POWER", u, 1.25),
        0.36,
    )
    threshold.node.inputs[2].default_value = 0.18
    # Keep the narrow crown's leading edge. Eroding its whole height equally
    # leaves a round middle bulge after the pointed top has disappeared.
    threshold = g.m(
        "Pointed Crown Outlives The Cleft",
        "SUBTRACT",
        threshold,
        g.m(
            "Keep Thin Rising Tips", "MULTIPLY", g.stage("Above The Last Fork", u, 0.72, 0.98), 0.18
        ),
    )
    phase = g.m("Rising Cleft Phase", "SUBTRACT", g.m("Cleft Height", "MULTIPLY", u, 12), clock)
    lobe = g.n("ShaderNodeAttribute", "Each Tongue's Flow Phase", attribute_name="fire_lobe")
    phase = g.m(
        "Cleft Follows Its Own Neck",
        "SUBTRACT",
        phase,
        g.m("Tongue Phase", "MULTIPLY", lobe.outputs["Fac"], 1.9),
    )
    threshold = g.m(
        "Forks Open Between Rising Bulges",
        "ADD",
        threshold,
        g.m(
            "Clefts Leave The Foot Intact",
            "MULTIPLY",
            g.stage("Fork Above Ground", u, 0.15, 0.55),
            g.m("Alternating Cleft Depth", "MULTIPLY", g.m("Rising Cleft", "SINE", phase), 0.08),
        ),
    )
    threshold = g.m(
        "Fuel Erosion",
        "ADD",
        g.m(
            "Editable Dissolve And Living Crown",
            "ADD",
            threshold,
            g.value("Dissolve", prop="dissolve"),
        ),
        g.m(
            "Breaking Last Tongues",
            "MULTIPLY",
            g.m("Editable Extinction", "MULTIPLY", release, g.value("Fade", prop="fade")),
            g.m(
                "Fuel Stops At The Foot First",
                "ADD",
                0.15,
                g.m(
                    "Unfed Flame Base",
                    "MULTIPLY",
                    g.m("Height Above The Fuel", "SUBTRACT", 1, u),
                    0.55,
                ),
            ),
        ),
    )
    alive = g.stage(
        "Soft Broken Heat Edge",
        g.m("Heat Above Erosion", "SUBTRACT", noise.outputs["Fac"], threshold),
        0,
        0.035,
    )
    air = g.n("ShaderNodeBsdfTransparent", "Air Between Flame Tongues")
    mix = g.n("ShaderNodeMixShader", "Flame Erosion")
    g.link(alive, mix.inputs[0])
    g.link(air.outputs[0], mix.inputs[1])
    g.link(emission.outputs[0], mix.inputs[2])
    out = g.n("ShaderNodeOutputMaterial", "Output")
    g.link(mix.outputs[0], out.inputs["Surface"])


def create(context, quality="MEDIUM"):
    if quality not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("Unknown fire quality")
    flame = core.create(context, "ENERGY_RING", quality)
    start = float(flame["start"])
    for key, value in dict(
        width=1.15, strength=2.2, noise_scale=3.0, dissolve=0, fade=1, duration=48, loop=False
    ).items():
        flame[key] = value
    for index in range(3):
        flame[f"color_{index}"] = 1.0
    for name, value, maximum in (
        ("Fire Height", 2.2, 30),
        ("Fire Flow Speed", 22.0, 100),
        ("Fire Curl", 0.6, 5),
    ):
        flame[name] = value
        flame.id_properties_ui(name).update(min=0, max=maximum, description=name)
    flame.name = "Fire • Sculpted Tongues"
    _flames(flame, quality)
    embers = core.create_emitter(context, quality)
    for key, value in dict(
        start=start + 4,
        duration=48,
        rate={"LOW": 8.0, "MEDIUM": 13.0, "HIGH": 18.0}[quality],
        lifetime=0.65,
        emission_seconds=1.2,
        size=0.035,
        shape=1,
        stretch=3,
        planar=0.4,
        velocity=1.8,
        gravity=-0.6,
        spread=0.45,
        spawn_radius=0.12,
        fade=1,
        strength=1.4,
        loop=False,
        seed=67,
    ).items():
        embers[key] = value
    embers["color_0"], embers["color_1"], embers["color_2"] = 1, 0.21, 0.015
    embers.name = "Fire • Rising Embers"
    for obj in (flame, embers):
        obj.update_tag()
    root = composition.create(context, [flame, embers])
    root.name, root["vfx_quality"], root["loop"] = "Stylized Fire", quality, False
    root.update_tag()
    context.view_layer.update()
    return root
