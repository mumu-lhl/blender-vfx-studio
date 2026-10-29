"""Draw a layered calligraphic seal, counterrotate its runes and lift release marks."""

import math

from mathutils import Vector

from blender_vfx_studio import composition, core
from blender_vfx_studio.nodes import ACTIVE, PROGRESS, drive
from tools.charge_design import _Fields, _geometry, _mesh


def _glyph(index):
    # Original abstract stroke motifs, not a font or imported texture.
    motifs = (
        [[(-0.35, -0.5), (0, 0.5), (0.35, -0.5)], [(-0.2, 0), (0.25, 0)]],
        [[(-0.25, -0.5), (-0.25, 0.5), (0.3, 0.15), (-0.25, -0.05), (0.3, -0.5)]],
        [[(-0.3, 0.5), (0.25, 0.5), (-0.2, 0), (0.3, -0.5), (-0.3, -0.5)]],
        [
            [(0, -0.5), (0, 0.5)],
            [(-0.35, 0.2), (0, 0.5), (0.35, 0.2)],
            [(-0.3, -0.15), (0.3, -0.15)],
        ],
        [[(-0.3, 0.5), (0.3, 0.1), (-0.3, -0.5)], [(-0.3, 0.05), (0.3, 0.05)]],
        [[(0, -0.5), (-0.3, 0), (0, 0.5), (0.3, 0), (0, -0.5)], [(0, 0.5), (0, 0.8)]],
    )
    return motifs[index % len(motifs)]


def _mesh_pattern(layer, kind, quality):
    detail = {"LOW": 20, "MEDIUM": 32, "HIGH": 48}[quality]
    vertices, faces = [], []
    attributes = {k: [] for k in ("sigil_draw", "sigil_edge", "sigil_weight")}
    offsets, anchors = [], []

    def stroke(points, weight, phase, *, normal=(0, 0, 1), anchor=(0, 0, 0)):
        points = [Vector(p) for p in points]
        subdivisions = max(
            1, math.ceil({"LOW": 8, "MEDIUM": 12, "HIGH": 18}[quality] / (len(points) - 1))
        )
        points = [
            a.lerp(b, i / subdivisions)
            for a, b in zip(points, points[1:])
            for i in range(subdivisions)
        ] + [points[-1]]
        base = len(vertices)
        for i, position in enumerate(points):
            tangent = points[min(i + 1, len(points) - 1)] - points[max(0, i - 1)]
            side = Vector(normal).cross(tangent).normalized()
            for sign in (-1, 1):
                offset = side * sign
                vertices.append(tuple(position + offset))
                offsets.append(offset)
                if kind == "release":
                    anchors.append(anchor)
                attributes["sigil_draw"].append(phase + (1 - phase) * i / (len(points) - 1))
                attributes["sigil_edge"].append((sign + 1) / 2)
                attributes["sigil_weight"].append(weight)
        for i in range(len(points) - 1):
            a = base + 2 * i
            faces.append((a, a + 1, a + 3, a + 2))

    def circle(radius, start, end, weight, phase):
        n = max(3, round(detail * (end - start) / math.pi))
        stroke(
            [
                (radius * math.cos(a), radius * math.sin(a), 0)
                for a in [start + (end - start) * i / n for i in range(n + 1)]
            ],
            weight,
            phase,
        )

    if kind == "seal":
        for index in range(6):
            phi = index * math.tau / 6
            points = []
            for i in range(detail + 1):
                t = i / detail
                radius = 0.1 + 0.52 * math.sin(math.pi * t)
                a = phi + 0.24 * math.sin(math.tau * t)
                points.append((radius * math.cos(a), radius * math.sin(a), 0))
            stroke(points, 1.25, 0.015 * index)
            a, b = phi + 0.14, phi + math.tau / 3 - 0.14
            stroke(
                [
                    (0.48 * math.cos(a), 0.48 * math.sin(a), 0),
                    (0.48 * math.cos(b), 0.48 * math.sin(b), 0),
                ],
                0.45,
                0.12,
            )
        for i in range(6):
            a = i * math.tau / 6
            circle(0.7, a + 0.04, a + math.tau / 6 - 0.04, 0.6, 0.05)
            circle(1.02, a + 0.045, a + math.tau / 6 - 0.045, 0.8, 0.14)
        circle(0.11, 0, math.tau, 0.7, 0)
    elif kind == "runes":
        circle(0.79, 0, math.tau, 0.45, 0.15)
        circle(0.96, 0, math.tau, 0.45, 0.15)
        for index in range(18):
            a = index * math.tau / 18
            for path in _glyph(index):
                stroke(
                    [
                        (
                            (0.875 + y * 0.12) * math.cos(a) - x * 0.12 * math.sin(a),
                            (0.875 + y * 0.12) * math.sin(a) + x * 0.12 * math.cos(a),
                            0,
                        )
                        for x, y in path
                    ],
                    0.58,
                    0.18 + index * 0.004,
                )
    else:
        for index in range(6):
            a = index * math.tau / 6
            normal = (math.cos(a), math.sin(a), 0)
            for path in _glyph(index):
                stroke(
                    [
                        (
                            0.52 * math.cos(a) - x * 0.21 * math.sin(a),
                            0.52 * math.sin(a) + x * 0.21 * math.cos(a),
                            (y + 0.5) * 0.32,
                        )
                        for x, y in path
                    ],
                    0.62,
                    0.08 * index,
                    normal=normal,
                    anchor=(0.52 * math.cos(a), 0.52 * math.sin(a), 0),
                )
    _mesh(layer, vertices, faces, attributes)
    attr = layer.data.attributes.new("sigil_offset", "FLOAT_VECTOR", "POINT")
    for item, offset in zip(attr.data, offsets):
        item.vector = offset
    if kind == "release":
        attr = layer.data.attributes.new("sigil_anchor", "FLOAT_VECTOR", "POINT")
        for item, anchor in zip(attr.data, anchors):
            item.vector = anchor


def _pattern(root, kind, quality):
    layer, g, geometry = _geometry(root, "Calligraphic " + kind.title())
    _mesh_pattern(layer, kind, quality)
    p = g.value("Seal Clock", expression=PROGRESS)
    position = g.n("GeometryNodeInputPosition", "Editable Ink Rest Mesh")
    offset = g.attr("sigil_offset", "FLOAT_VECTOR")
    center = g.v("Authored Stroke Center", "SUBTRACT", position.outputs[0], offset)
    radius = g.value("Seal Radius", prop="radius")
    center = g.v("Editable Seal Size", "SCALE", center, radius)
    if kind == "release":
        lifted = g.stage("Runes Lift At Release", p, 0.68, 0.87)
        gather = g.m("Nonnegative Release Gather", "MAXIMUM", g.value("Release Gather", 0), 0)
        gather = g.m("Bounded Release Gather", "MINIMUM", gather, 1)
        gather = g.m("Gather During Release", "MULTIPLY", gather, lifted)
        anchor = g.v("Scaled Rune Anchors", "SCALE", g.attr("sigil_anchor", "FLOAT_VECTOR"), radius)
        center = g.v(
            "Gather Centers Without Shrinking Strokes",
            "SUBTRACT",
            center,
            g.v("Gathered Rune Anchors", "SCALE", anchor, gather),
        )
    width = g.m(
        "Individual Stroke Weight",
        "MULTIPLY",
        g.attr("sigil_weight"),
        g.value("Ink Width", prop="width"),
    )
    shaped = g.v(
        "Sized Calligraphic Ink", "ADD", center, g.v("Stroke Width", "SCALE", offset, width)
    )
    rotation = g.n(
        "ShaderNodeVectorRotate", "Counterrotating Native Seal", rotation_type="AXIS_ANGLE"
    )
    rotation.inputs["Axis"].default_value = (0, 0, 1)
    g.link(shaped, rotation.inputs["Vector"])
    angle = g.m(
        "Rotation Through The Cycle", "MULTIPLY", p, g.value("Editable Spin", prop="Sigil Spin")
    )
    g.link(g.m("Spin In Radians", "MULTIPLY", angle, math.pi / 180), rotation.inputs["Angle"])
    shaped = rotation.outputs["Vector"]
    if kind == "release":
        direction = g.n("ShaderNodeCombineXYZ", "Release Direction")
        direction.inputs["Z"].default_value = 1
        unit = g.n("ShaderNodeVectorMath", "Unit Release Direction", operation="NORMALIZE")
        g.link(direction.outputs[0], unit.inputs[0])
        shaped = g.v(
            "Rising Rune Stamps",
            "ADD",
            shaped,
            g.v(
                "Editable Release Travel",
                "SCALE",
                unit.outputs[0],
                g.m("Lift Height", "MULTIPLY", lifted, g.value("Rune Lift", prop="Sigil Lift")),
            ),
        )
        draw = g.stage("Release Marks Ignite", p, 0.5, 0.62)
        alpha = g.m(
            "Release Mark Life",
            "MULTIPLY",
            draw,
            g.m(
                "Release Marks Leave",
                "SUBTRACT",
                1,
                g.m(
                    "Release Fade",
                    "MULTIPLY",
                    g.stage("Release Ends", p, 0.78, 0.98),
                    g.value("Fade", prop="fade"),
                ),
            ),
        )
    else:
        draw = g.stage("Ink Draws The Seal", p, 0, 0.33)
        alpha = g.m(
            "Seal Life",
            "MULTIPLY",
            g.stage("Ink Appears", p, 0, 0.07),
            g.m(
                "Seal Fades",
                "SUBTRACT",
                1,
                g.m(
                    "Seal Fade",
                    "MULTIPLY",
                    g.stage("Seal Leaves", p, 0.72, 1),
                    g.value("Fade", prop="fade"),
                ),
            ),
        )
    move = g.n("GeometryNodeSetPosition", "Editable Seal Motion")
    g.link(geometry, move.inputs["Geometry"])
    g.link(shaped, move.inputs["Position"])
    hide = g.n("GeometryNodeDeleteGeometry", "Undrawn Or Inactive Ink", domain="POINT")
    inactive = g.m("Outside Lifetime", "LESS_THAN", g.value("Active", expression=ACTIVE), 0.5)
    undrawn = g.m("Ink Has Not Reached Here", "GREATER_THAN", g.attr("sigil_draw"), draw)
    empty = g.m("Layer Is Invisible", "LESS_THAN", alpha, 0.002)
    dissolved = g.m("Fully Dissolved", "GREATER_THAN", g.value("Dissolve", prop="dissolve"), 0.9999)
    g.link(move.outputs[0], hide.inputs["Geometry"])
    g.link(
        g.m(
            "Hidden Ink",
            "MAXIMUM",
            inactive,
            g.m(
                "Waiting Or Finished",
                "MAXIMUM",
                undrawn,
                g.m("Empty Ink", "MAXIMUM", empty, dissolved),
            ),
        ),
        hide.inputs["Selection"],
    )
    out = g.n("NodeGroupOutput", "Output")
    g.link(hide.outputs[0], out.inputs["Geometry"])
    root["vfx_parameter_keys"] = "radius,width,strength,noise_scale,dissolve,fade"
    _surface(root, kind)


def _surface(root, kind):
    material = root.children[0].data.materials[0]
    material.name = "VFX • " + kind.title() + " Ink"
    material.node_tree.animation_data_clear()
    material.node_tree.nodes.clear()
    material.surface_render_method = "BLENDED"
    g = _Fields(material.node_tree, root)
    p = g.value("Seal Clock", expression=PROGRESS)
    color = g.n("ShaderNodeCombineXYZ", "Editable Ink Color")
    for index in range(3):
        drive(color.inputs[index], "default_value", root, "c", {"c": f"color_{index}"})
    attr = g.n("ShaderNodeAttribute", "Stroke Edge", attribute_name="sigil_edge")
    edge = g.m(
        "Across The Stroke", "ABSOLUTE", g.m("Centered Ink", "SUBTRACT", attr.outputs["Fac"], 0.5)
    )
    inner = g.m("Narrow Bright Center", "SUBTRACT", 1, g.stage("Dark Outline", edge, 0.12, 0.5))
    ramp = g.n("ShaderNodeMixRGB", "Colored Edge And Bright Ink")
    g.link(inner, ramp.inputs[0])
    g.link(g.v("Deep Ink Border", "SCALE", color.outputs[0], 0.14), ramp.inputs[1])
    g.link(color.outputs[0], ramp.inputs[2])
    emission = g.n("ShaderNodeEmission", "Ink Radiance")
    g.link(ramp.outputs[0], emission.inputs["Color"])
    g.link(g.value("Strength", prop="strength"), emission.inputs["Strength"])
    coords = g.n("ShaderNodeTexCoord", "Seal Coordinates")
    noise = g.n("ShaderNodeTexNoise", "Flowing Ink Grain", noise_dimensions="4D")
    g.link(coords.outputs["Object"], noise.inputs["Vector"])
    g.link(g.value("Detail", prop="noise_scale"), noise.inputs["Scale"])
    noise.inputs["Detail"].default_value = 1
    g.link(g.m("Ink Evolution", "MULTIPLY", p, 2), noise.inputs["W"])
    cutoff = g.m(
        "Ink Erosion", "GREATER_THAN", noise.outputs["Fac"], g.value("Dissolve", prop="dissolve")
    )
    if kind == "release":
        opacity = g.m(
            "Release Glyph Life",
            "MULTIPLY",
            g.stage("Release Glyphs Appear", p, 0.5, 0.62),
            g.m(
                "Release Glyphs Fade",
                "SUBTRACT",
                1,
                g.m(
                    "Glyph Fade",
                    "MULTIPLY",
                    g.stage("Glyphs End", p, 0.78, 0.98),
                    g.value("Fade", prop="fade"),
                ),
            ),
        )
    else:
        opacity = g.m(
            "Seal Opacity",
            "MULTIPLY",
            g.stage("Seal Appears", p, 0, 0.07),
            g.m(
                "Editable Fade",
                "SUBTRACT",
                1,
                g.m(
                    "Fade Amount",
                    "MULTIPLY",
                    g.stage("Seal Leaves", p, 0.72, 1),
                    g.value("Fade", prop="fade"),
                ),
            ),
        )
    air = g.n("ShaderNodeBsdfTransparent", "Air")
    mix = g.n("ShaderNodeMixShader", "Fading Ink")
    g.link(g.m("Visible Ink", "MULTIPLY", opacity, cutoff), mix.inputs[0])
    g.link(air.outputs[0], mix.inputs[1])
    g.link(emission.outputs[0], mix.inputs[2])
    out = g.n("ShaderNodeOutputMaterial", "Output")
    g.link(mix.outputs[0], out.inputs["Surface"])


def create(context, quality="MEDIUM"):
    if quality not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("Unknown magic circle quality")
    members = []
    for kind, color, width, strength, spin, z in (
        ("seal", (1, 0.4, 0.055), 0.024, 2.0, 16, 0.025),
        ("runes", (0.16, 0.25, 1), 0.022, 1.4, -42, 0.03),
        ("release", (1, 0.65, 0.16), 0.024, 1.5, 8, 0.04),
    ):
        root = core.create(context, "ENERGY_RING", quality)
        for key, value in dict(
            radius=1.6,
            width=width,
            strength=strength,
            noise_scale=8,
            dissolve=0,
            fade=1,
            duration=72,
            loop=False,
        ).items():
            root[key] = value
        for index, value in enumerate(color):
            root[f"color_{index}"] = value
        root["Sigil Spin"], root["Sigil Lift"] = spin, 1.7
        root.id_properties_ui("Sigil Spin").update(
            min=-720, max=720, description="Rotation in degrees during one effect cycle"
        )
        root.id_properties_ui("Sigil Lift").update(
            min=0, max=20, description="Rune travel distance along the native Release Direction"
        )
        root.name = "Magic • " + kind.title()
        root.location.z += z
        _pattern(root, kind, quality)
        root.update_tag()
        members.append(root)
    group = composition.create(context, members)
    group.name, group["vfx_quality"], group["loop"] = "Calligraphic Magic Circle", quality, False
    group.update_tag()
    context.view_layer.update()
    return group
