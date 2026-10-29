"""Author a complete lightning strike from existing controllers and native fields."""

import math
import random

from mathutils import Vector

from blender_vfx_studio import composition, core
from blender_vfx_studio.nodes import ACTIVE, PROGRESS
from tools.charge_design import _Fields, _geometry, _mesh


def _pulse(g, p):
    flashes = []
    for name, begin, peak, hold, end, weight in (
        ("First Strike", 0.0, 0.08, 0.16, 0.25, 1.0),
        ("Restrike", 0.30, 0.34, 0.40, 0.49, 0.78),
        ("Last Arc", 0.57, 0.61, 0.66, 0.81, 0.45),
    ):
        value = g.m(
            name + " Envelope",
            "MULTIPLY",
            g.stage(name + " Arrives", p, begin, peak),
            g.m(name + " Leaves", "SUBTRACT", 1, g.stage(name + " Ends", p, hold, end)),
        )
        flashes.append(g.m(name + " Weight", "MULTIPLY", value, weight))
    return g.m(
        "Three Separated Discharges",
        "MAXIMUM",
        flashes[0],
        g.m("Later Discharges", "MAXIMUM", flashes[1], flashes[2]),
    )


def _bolt(root, quality):
    layer, g, geometry = _geometry(root, "Branching Lightning")
    randomizer = random.Random(37)
    segments, forks, fork_segments, planes = {
        "LOW": (18, 5, 4, 2),
        "MEDIUM": (32, 7, 7, 3),
        "HIGH": (48, 9, 11, 3),
    }[quality]
    trunk = []
    # A few large direction changes carry the silhouette; small deviations
    # provide electrical detail without making every segment equally jagged.
    macro = [
        (0, 0),
        (0.32, 0.12),
        (-0.15, -0.16),
        (0.38, 0.08),
        (-0.20, -0.12),
        (0.10, 0.10),
        (-0.10, -0.05),
        (0, 0),
    ]
    for i in range(segments + 1):
        t = i / segments
        segment = min(int(t * (len(macro) - 1)), len(macro) - 2)
        fraction = t * (len(macro) - 1) - segment
        x, y = [
            macro[segment][axis] * (1 - fraction) + macro[segment + 1][axis] * fraction
            for axis in (0, 1)
        ]
        envelope = math.sin(math.pi * t)
        trunk.append(
            Vector(
                (
                    x + randomizer.uniform(-0.045, 0.045) * envelope,
                    y + randomizer.uniform(-0.03, 0.03) * envelope,
                    1 - t,
                )
            )
        )
    paths = [(trunk, Vector(), 0)]
    for index in range(forks):
        anchor = trunk[round(segments * (0.15 + index * 0.7 / max(forks - 1, 1)))].copy()
        sign = -1 if index % 2 else 1
        end = anchor + Vector(
            (
                sign * randomizer.uniform(0.65, 1.25),
                randomizer.uniform(-0.55, 0.55),
                -randomizer.uniform(0.12, 0.25),
            )
        )
        end.z = max(end.z, 0.02)
        points = []
        for i in range(fork_segments + 1):
            t = i / fork_segments
            point = anchor.lerp(end, t)
            point += Vector(
                (
                    randomizer.uniform(-0.12, 0.12),
                    randomizer.uniform(-0.08, 0.08),
                    randomizer.uniform(-0.035, 0.035),
                )
            ) * math.sin(math.pi * t)
            points.append(point)
        paths.append((points, anchor, index + 1))
    vertices, faces = [], []
    attrs = {key: [] for key in ("bolt_side", "bolt_branch", "bolt_width", "bolt_along")}
    offsets, anchors = [], []
    for points, anchor, branch in paths:
        for plane in range(planes):
            base = len(vertices)
            for i, point in enumerate(points):
                tangent = points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]
                tangent = (tangent * Vector((0.8, 0.8, 3.6))).normalized()
                side = tangent.cross(Vector((0, 1, 0))).normalized()
                up = tangent.cross(side).normalized()
                cross = side * math.cos(plane * math.pi / planes) + up * math.sin(
                    plane * math.pi / planes
                )
                t = i / (len(points) - 1)
                width = (
                    (
                        0.65
                        + 0.55 * math.sin(math.pi * t) ** 0.7
                        + 0.75 * math.exp(-(((t - 1) / 0.1) ** 2))
                    )
                    if branch == 0
                    else 0.52 * (1 - t) ** 0.7 + 0.025
                )
                for sign in (-1, 1):
                    offset = cross * sign
                    vertices.append(tuple(point + offset))
                    offsets.append(offset)
                    anchors.append(anchor)
                    for key, value in zip(attrs, (float(sign), float(branch), width, 1 - point.z)):
                        attrs[key].append(value)
            for i in range(len(points) - 1):
                a = base + i * 2
                faces.append((a, a + 1, a + 3, a + 2))
    _mesh(layer, vertices, faces, attrs)
    for name, values in (("bolt_offset", offsets), ("bolt_anchor", anchors)):
        attribute = layer.data.attributes.new(name, "FLOAT_VECTOR", "POINT")
        for item, value in zip(attribute.data, values):
            item.vector = value
    p = g.value("Strike Clock", expression=PROGRESS)
    pulse = _pulse(g, p)
    position = g.n("GeometryNodeInputPosition", "Editable Rest Geometry")
    offset = g.attr("bolt_offset", "FLOAT_VECTOR")
    center = g.v("Editable Bolt Centerline", "SUBTRACT", position.outputs[0], offset)
    is_branch = g.m("Is Branch", "GREATER_THAN", g.attr("bolt_branch"), 0)
    reach = g.m("Branch Reach Difference", "SUBTRACT", g.value("Branch Reach", 1.0), 1)
    reach = g.m("Trunk And Branch Reach", "MULTIPLY_ADD", reach, is_branch)
    reach.node.inputs[2].default_value = 1
    anchor = g.attr("bolt_anchor", "FLOAT_VECTOR")
    center = g.v(
        "Branches Stay Connected",
        "ADD",
        anchor,
        g.v(
            "Editable Branch Span",
            "SCALE",
            g.v("Branch From Junction", "SUBTRACT", center, anchor),
            reach,
        ),
    )
    axes = g.n("ShaderNodeSeparateXYZ", "Centerline Axes")
    g.link(center, axes.inputs[0])
    radius = g.value("Lateral Spread", prop="radius")
    scaled = g.xyz(
        "Strike Dimensions",
        g.m("Spread X", "MULTIPLY", axes.outputs["X"], radius),
        g.m("Spread Y", "MULTIPLY", axes.outputs["Y"], radius),
        g.m("Strike Height", "MULTIPLY", axes.outputs["Z"], g.value("Bolt Length", 3.6)),
    )
    noise = g.n("ShaderNodeTexNoise", "Changing Electrical Path", noise_dimensions="4D")
    g.link(center, noise.inputs["Vector"])
    g.link(g.value("Jitter Detail", prop="noise_scale"), noise.inputs["Scale"])
    noise.inputs["Detail"].default_value = 1
    g.link(
        g.m("New Shape Each Discharge", "FLOOR", g.m("Discharge Shape Clock", "MULTIPLY", p, 6)),
        noise.inputs["W"],
    )
    jitter = g.v("Signed Path Jitter", "SUBTRACT", noise.outputs["Color"], (0.5, 0.5, 0.5))
    jitter = g.v(
        "Keep The Contact Fixed",
        "SCALE",
        jitter,
        g.m(
            "Jitter Away From Contact",
            "MULTIPLY",
            radius,
            g.m(
                "End Jitter Envelope",
                "MULTIPLY",
                g.m(
                    "Path Envelope",
                    "SINE",
                    g.m("Height Half Turn", "MULTIPLY", axes.outputs["Z"], math.pi),
                ),
                0.16,
            ),
        ),
    )
    center = g.v("Discharging Centerline", "ADD", scaled, jitter)
    width = g.m("Bolt Full Width", "MULTIPLY", g.value("Width", prop="width"), 0.5)
    width = g.m("Main And Fine Branch Width", "MULTIPLY", width, g.attr("bolt_width"))
    width = g.m("Discharge Thickness", "MULTIPLY", width, pulse)
    shaped = g.n("GeometryNodeSetPosition", "Native Bolt Shape")
    g.link(geometry, shaped.inputs["Geometry"])
    g.link(
        g.v("Crossed Ribbons", "ADD", center, g.v("Ribbon Thickness", "SCALE", offset, width)),
        shaped.inputs["Position"],
    )
    reveal = g.stage("Strike Travels To Ground", p, 0, 0.12)
    not_yet = g.m("Not Reached By Strike", "GREATER_THAN", g.attr("bolt_along"), reveal)
    inactive = g.m("Outside Lifetime", "LESS_THAN", g.value("Active", expression=ACTIVE), 0.5)
    off = g.m("Between Discharges", "LESS_THAN", pulse, 0.06)
    dissolve = g.value("Dissolve", prop="dissolve")
    erosion = g.m(
        "Weaker Branches Erode First",
        "MULTIPLY",
        dissolve,
        g.m("Branch Erosion Weight", "MULTIPLY_ADD", is_branch, 0.45),
    )
    g.tree.nodes["Branch Erosion Weight"].inputs[2].default_value = 0.55
    eroded = g.m("Eroded Paths", "LESS_THAN", noise.outputs["Fac"], erosion)
    fully_dissolved = g.m(
        "Fully Dissolved", "GREATER_THAN", g.value("Dissolve", prop="dissolve"), 0.9999
    )
    hide = g.n("GeometryNodeDeleteGeometry", "Only Live Electrical Paths", domain="POINT")
    g.link(shaped.outputs[0], hide.inputs["Geometry"])
    g.link(
        g.m(
            "Hidden Strike",
            "MAXIMUM",
            not_yet,
            g.m(
                "Off Or Outside Lifetime",
                "MAXIMUM",
                off,
                g.m(
                    "Inactive Or Dissolved",
                    "MAXIMUM",
                    inactive,
                    g.m("Dissolved Paths", "MAXIMUM", eroded, fully_dissolved),
                ),
            ),
        ),
        hide.inputs["Selection"],
    )
    out = g.n("NodeGroupOutput", "Output")
    g.link(hide.outputs[0], out.inputs["Geometry"])
    root["vfx_parameter_keys"] = "radius,width,strength,noise_scale,dissolve"
    _material(root)


def _material(root):
    material = root.children[0].data.materials[0]
    material.name = "VFX • White Lightning And Blue Boundary"
    material.node_tree.animation_data_clear()
    material.node_tree.nodes.clear()
    material.use_backface_culling = False
    g = _Fields(material.node_tree, root)
    p = g.value("Strike Clock", expression=PROGRESS)
    pulse = _pulse(g, p)
    side = g.n("ShaderNodeAttribute", "Width Across Ribbon", attribute_name="bolt_side")
    inside = g.m(
        "Distance From Ink Edge",
        "SUBTRACT",
        1,
        g.m("Absolute Ribbon Side", "ABSOLUTE", side.outputs["Fac"]),
    )
    core_mask = g.stage("Thin White Electrical Core", inside, 0.62, 0.83)
    color = g.n("ShaderNodeCombineXYZ", "Editable Electric Color")
    from blender_vfx_studio.nodes import drive

    for i in range(3):
        drive(color.inputs[i], "default_value", root, "c", {"c": f"color_{i}"})
    body = g.v("Blue Support Stroke", "SCALE", color.outputs[0], 0.26)
    white = g.n("ShaderNodeMixRGB", "Cold White Main Core")
    white.inputs[0].default_value = 0.87
    g.link(color.outputs[0], white.inputs[1])
    white.inputs[2].default_value = (0.85, 0.95, 1.0, 1)
    mix = g.n("ShaderNodeMixRGB", "Core Inside Blue Outline")
    g.link(core_mask, mix.inputs[0])
    g.link(body, mix.inputs[1])
    g.link(white.outputs[0], mix.inputs[2])
    border = g.n("ShaderNodeMixRGB", "Dark Outer Boundary")
    g.link(g.stage("Narrow Ink Edge", inside, 0, 0.12), border.inputs[0])
    g.link(g.v("Electric Ink", "SCALE", color.outputs[0], 0.018), border.inputs[1])
    g.link(mix.outputs[0], border.inputs[2])
    branch = g.n("ShaderNodeAttribute", "Branch Weight", attribute_name="bolt_branch")
    hierarchy = g.m(
        "Subordinate Forks",
        "SUBTRACT",
        1,
        g.m(
            "Fork Brightness Reduction",
            "MULTIPLY",
            g.m("Is Fork", "GREATER_THAN", branch.outputs["Fac"], 0),
            0.48,
        ),
    )
    emission = g.n("ShaderNodeEmission", "Native Lightning Surface")
    g.link(
        g.v("Main And Supporting Discharges", "SCALE", border.outputs[0], hierarchy),
        emission.inputs["Color"],
    )
    radiance = g.m("Narrowing Arcs Stay Luminous", "MULTIPLY_ADD", pulse, 0.75)
    radiance.node.inputs[2].default_value = 0.25
    g.link(
        g.m("Pulse Energy", "MULTIPLY", radiance, g.value("Emission", prop="strength")),
        emission.inputs["Strength"],
    )
    out = g.n("ShaderNodeOutputMaterial", "Output")
    g.link(emission.outputs[0], out.inputs["Surface"])


def _contact_corona(root, quality):
    """Grounded, connected return paths repeat with the main discharge clock."""
    layer, g, geometry = _geometry(root, "Branching Contact Return")
    arms, steps = {"LOW": (3, 4), "MEDIUM": (5, 7), "HIGH": (7, 10)}[quality]
    randomizer = random.Random(83)
    paths = []
    for index in range(arms):
        angle = index * 2.399963 + 0.3
        radial = Vector((math.cos(angle), math.sin(angle), 0))
        lateral = Vector((-radial.y, radial.x, 0))
        reach = randomizer.uniform(0.75, 1.2)
        points = []
        for step in range(steps + 1):
            t = step / steps
            point = radial * (reach * t)
            point += lateral * (randomizer.uniform(-0.16, 0.16) * math.sin(math.pi * t))
            point.z = 0.04 + 0.08 * math.sin(math.pi * t)
            points.append(point)
        paths.append((points, 0))
        junction = steps // 2
        start = points[junction]
        end = start + radial * 0.24 + lateral * (0.28 if index % 2 else -0.28)
        end.z = 0.04
        paths.append(([start, start.lerp(end, 0.5) + lateral * 0.07, end], 1))

    vertices, faces, offsets = [], [], []
    attrs = {name: [] for name in ("bolt_side", "bolt_branch", "contact_width", "contact_along")}
    for points, branch in paths:
        for plane in range(2):
            base = len(vertices)
            for index, point in enumerate(points):
                tangent = (
                    points[min(index + 1, len(points) - 1)] - points[max(index - 1, 0)]
                ).normalized()
                across = tangent.cross(Vector((0, 0, 1))).normalized()
                up = tangent.cross(across).normalized()
                side = across if plane == 0 else up
                t = index / (len(points) - 1)
                for sign in (-1, 1):
                    offset = side * sign
                    vertices.append(tuple(point + offset))
                    offsets.append(offset)
                    for name, value in zip(
                        attrs,
                        (sign, branch, (0.65 if branch else 1) * (1 - t) ** 0.65 + 0.02, t),
                    ):
                        attrs[name].append(value)
            for index in range(len(points) - 1):
                a = base + index * 2
                faces.append((a, a + 1, a + 3, a + 2))
    _mesh(layer, vertices, faces, attrs)
    attribute = layer.data.attributes.new("contact_offset", "FLOAT_VECTOR", "POINT")
    for item, value in zip(attribute.data, offsets):
        item.vector = value

    p = g.value("Contact Discharge Clock", expression=PROGRESS)
    pulse = _pulse(g, p)
    # Restart propagation at each discharge rather than letting one ring grow
    # continuously underneath the later strikes. Each fork stays at its junction.
    age = g.m(
        "First Or Second Contact Age",
        "SUBTRACT",
        p,
        g.m(
            "Second Contact Start",
            "MULTIPLY",
            g.m("After Second Contact", "GREATER_THAN", p, 0.30),
            0.30,
        ),
    )
    age = g.m(
        "Current Contact Age",
        "SUBTRACT",
        age,
        g.m(
            "Third Contact Start",
            "MULTIPLY",
            g.m("After Third Contact", "GREATER_THAN", p, 0.57),
            0.27,
        ),
    )
    # The later pulse peaks last less than two frames. Reach outside the
    # contact footprint before they narrow, instead of expanding after the hit.
    travel = g.stage("Ground Return Spreads", age, 0, 0.06)
    radius = g.m(
        "Contact Footprint",
        "ADD",
        g.value("Contact Radius", prop="radius"),
        g.m("Ground Reach", "MULTIPLY", travel, g.value("Ground Expansion", prop="expansion")),
    )
    position = g.n("GeometryNodeInputPosition", "Editable Contact Paths")
    offset = g.attr("contact_offset", "FLOAT_VECTOR")
    center = g.v("Contact Centerlines", "SUBTRACT", position.outputs[0], offset)
    center = g.v(
        "Radial Ground Spread", "MULTIPLY", center, g.xyz("Ground Dimensions", radius, radius, 1)
    )
    root_width = g.value("Return Width", prop="width")
    width = g.m("Contact Width", "MULTIPLY", root_width, g.attr("contact_width"))
    width = g.m("Contact Pulse Width", "MULTIPLY", width, pulse)
    width = g.m(
        "Main Strike Reaches Contact",
        "MULTIPLY",
        width,
        g.stage("First Ground Arrival", p, 0.08, 0.12),
    )
    shaped = g.n("GeometryNodeSetPosition", "Native Ground Return Shape")
    g.link(geometry, shaped.inputs["Geometry"])
    g.link(
        g.v(
            "Connected Contact Ribbons",
            "ADD",
            center,
            g.v("Crossed Contact Width", "SCALE", offset, width),
        ),
        shaped.inputs["Position"],
    )
    off = g.m("Between Contact Discharges", "LESS_THAN", pulse, 0.06)
    off = g.m(
        "Before Or Between Contacts", "MAXIMUM", off, g.m("Not Yet Grounded", "LESS_THAN", p, 0.08)
    )
    off = g.m(
        "Contact Disabled Or Between Pulses",
        "MAXIMUM",
        off,
        g.m("Zero Return Width", "LESS_THAN", root_width, 1e-8),
    )
    inactive = g.m(
        "Outside Contact Lifetime", "LESS_THAN", g.value("Contact Active", expression=ACTIVE), 0.5
    )
    tip = g.m(
        "Contact Tips Erode",
        "GREATER_THAN",
        g.attr("contact_along"),
        g.m("Remaining Contact Reach", "SUBTRACT", 1, g.value("Contact Dissolve", prop="dissolve")),
    )
    tip = g.m(
        "Contact Dissolved",
        "MAXIMUM",
        tip,
        g.m(
            "Fully Dissolved Contact",
            "GREATER_THAN",
            g.value("Full Contact Dissolve", prop="dissolve"),
            0.9999,
        ),
    )
    hide = g.n("GeometryNodeDeleteGeometry", "Only Live Contact Returns", domain="POINT")
    g.link(shaped.outputs[0], hide.inputs["Geometry"])
    g.link(
        g.m(
            "Hidden Contact",
            "MAXIMUM",
            off,
            g.m("Contact Inactive Or Eroded", "MAXIMUM", inactive, tip),
        ),
        hide.inputs["Selection"],
    )
    out = g.n("NodeGroupOutput", "Output")
    g.link(hide.outputs[0], out.inputs["Geometry"])
    root["vfx_parameter_keys"] = "radius,expansion,width,strength,dissolve"
    _material(root)


def create(context, quality="MEDIUM"):
    if quality not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("Unknown lightning quality")
    bolt = core.create(context, "ENERGY_RING", quality)
    start = float(bolt["start"])
    for key, value in dict(
        radius=0.8,
        width=0.095,
        strength=3.2,
        noise_scale=4.5,
        dissolve=0.0,
        duration=18.0,
        loop=False,
    ).items():
        bolt[key] = value
    for i, value in enumerate((0.025, 0.24, 1.0)):
        bolt[f"color_{i}"] = value
    bolt.name = "Lightning • Main Discharges"
    _bolt(bolt, quality)
    sparks = core.create_particle(context, quality)
    for key, value in dict(
        start=start + 2,
        duration=15.0,
        count={"LOW": 9, "MEDIUM": 11, "HIGH": 15}[quality],
        size=0.032,
        shape=1.0,
        stretch=8.0,
        planar=0.3,
        velocity=2.8,
        gravity=2.5,
        spread=0.8,
        randomness=0.7,
        spawn_radius=0.06,
        strength=1.3,
        seed=17,
        loop=False,
    ).items():
        sparks[key] = value
    for i, value in enumerate((0.1, 0.45, 1.0)):
        sparks[f"color_{i}"] = value
    sparks.name = "Lightning • Contact Sparks"
    wave = core.create(context, "SHOCKWAVE", quality)
    for key, value in dict(
        start=start,
        duration=18.0,
        radius=0.06,
        width=0.065,
        expansion=0.75,
        strength=0.65,
        dissolve=0.15,
        fade=1.0,
        loop=False,
    ).items():
        wave[key] = value
    for i, value in enumerate((0.025, 0.18, 1.0)):
        wave[f"color_{i}"] = value
    wave.name = "Lightning • Contact Corona"
    _contact_corona(wave, quality)
    flash = core.create_particle(context, quality)
    for key, value in dict(
        start=start + 2,
        duration=4.0,
        count={"LOW": 3, "MEDIUM": 5, "HIGH": 7}[quality],
        size=0.075,
        shape=1.0,
        stretch=5.5,
        planar=0.9,
        velocity=0.2,
        gravity=0.0,
        spread=1.0,
        randomness=0.4,
        spawn_radius=0.03,
        strength=3.0,
        fade=1.0,
        seed=4,
        loop=False,
    ).items():
        flash[key] = value
    for i, value in enumerate((0.65, 0.85, 1.0)):
        flash[f"color_{i}"] = value
    flash.name = "Lightning • Contact Flash"
    for member in (bolt, sparks, wave, flash):
        member.update_tag()
    root = composition.create(context, [bolt, sparks, wave, flash])
    root.name, root["vfx_quality"] = "Lightning Strike", quality
    root["loop"] = False
    root.update_tag()
    context.view_layer.update()
    return root
