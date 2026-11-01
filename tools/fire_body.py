"""Build a flowing painted flame body inside the existing native fire layer."""

import math
from pathlib import Path

import bpy


def geometry(g, original, material, width, height):
    """Keep the sculpted fire as a fallback when the scene has no camera."""
    camera = g.n("GeometryNodeInputActiveCamera", "Fire Body Camera")
    info = g.n("GeometryNodeObjectInfo", "Camera In Flame Space", transform_space="RELATIVE")
    g.link(camera.outputs[0], info.inputs["Object"])
    direction = g.n("ShaderNodeSeparateXYZ", "Camera Around The Fire Axis")
    g.link(info.outputs["Location"], direction.inputs[0])
    distance = g.n("ShaderNodeVectorMath", "Camera Distance From Fire Axis", operation="LENGTH")
    g.link(
        g.xyz("Camera In The Fuel Plane", direction.outputs["X"], direction.outputs["Y"], 0),
        distance.inputs[0],
    )
    available = g.m("Camera Can See The Body", "GREATER_THAN", distance.outputs["Value"], 0.00001)

    def store(name, mesh, value, *, vector=False, domain="POINT"):
        node = g.n(
            "GeometryNodeStoreNamedAttribute",
            name,
            data_type="FLOAT_VECTOR" if vector else "FLOAT",
            domain=domain,
        )
        node.inputs["Name"].default_value = name
        g.link(mesh, node.inputs["Geometry"])
        if isinstance(value, (int, float)):
            node.inputs["Value"].default_value = value
        else:
            g.link(value, node.inputs["Value"])
        return node.outputs["Geometry"]

    original = store("fire_body_available", original, available)
    body_width = g.m("Painted Body Width", "MULTIPLY", width, 2.08)
    body_height = g.m("Painted Body Height", "MULTIPLY", height, 1.10)
    grid = g.n("GeometryNodeMeshGrid", "Painted Flame Carrier")
    grid.inputs["Vertices X"].default_value = grid.inputs["Vertices Y"].default_value = 2
    g.link(body_width, grid.inputs["Size X"])
    g.link(body_height, grid.inputs["Size Y"])
    position = g.n("GeometryNodeInputPosition", "Carrier Coordinates")
    axes = g.n("ShaderNodeSeparateXYZ", "Carrier Axes")
    g.link(position.outputs[0], axes.inputs[0])
    uv = g.xyz(
        "Painted Flame UV",
        g.m("Body U", "ADD", g.m("Body U Fraction", "DIVIDE", axes.outputs["X"], body_width), 0.5),
        g.m("Body V", "ADD", g.m("Body V Fraction", "DIVIDE", axes.outputs["Y"], body_height), 0.5),
        0,
    )
    body = store("fire_body_uv", grid.outputs["Mesh"], uv, vector=True, domain="CORNER")
    body = store("fire_body", body, 1)
    move = g.n("GeometryNodeTransform", "Anchor Painted Fuel At The Root")
    g.link(body, move.inputs["Geometry"])
    # With the texture margin, the authored fuel begins near V=0.18.
    g.link(
        g.xyz("Fuel Anchor", 0, g.m("Authored Fuel Position", "MULTIPLY", body_height, 0.32), 0),
        move.inputs["Translation"],
    )
    face = g.n("GeometryNodeTransform", "Painted Flame Faces Camera")
    g.link(move.outputs[0], face.inputs["Geometry"])
    yaw = g.m(
        "Camera Heading Around Fire", "ARCTAN2", direction.outputs["Y"], direction.outputs["X"]
    )
    g.link(
        g.xyz(
            "Preserve The Fire Up Axis",
            math.pi / 2,
            0,
            g.m("Face Camera Around Fire Axis", "ADD", yaw, math.pi / 2),
        ),
        face.inputs["Rotation"],
    )
    assign = g.n("GeometryNodeSetMaterial", "Shared Editable Fire Material")
    assign.inputs["Material"].default_value = material
    g.link(face.outputs[0], assign.inputs["Geometry"])
    hide = g.n("GeometryNodeDeleteGeometry", "No Camera Uses Sculpted Flame", domain="POINT")
    g.link(assign.outputs[0], hide.inputs["Geometry"])
    g.link(g.m("No Body Camera", "SUBTRACT", 1, available), hide.inputs["Selection"])
    join = g.n("GeometryNodeJoinGeometry", "Body And Sculpted Fire Tips")
    g.link(original, join.inputs["Geometry"])
    g.link(hide.outputs[0], join.inputs["Geometry"])
    return join.outputs["Geometry"]


def shader(g, p, clock):
    """Return heat, coverage and the two native geometry attributes."""
    uv = g.n("ShaderNodeAttribute", "Fire Body UV", attribute_name="fire_body_uv")
    axes = g.n("ShaderNodeSeparateXYZ", "Fire Body UV Axes")
    g.link(uv.outputs["Vector"], axes.inputs[0])
    y = axes.outputs["Y"]
    noise = g.n("ShaderNodeTexNoise", "Rising Painted Folds")
    g.link(
        g.xyz(
            "Painted Fold Sampling",
            g.m("Painted Fold Across", "MULTIPLY", axes.outputs["X"], 2),
            g.m(
                "Painted Fold Rises",
                "SUBTRACT",
                g.m("Painted Fold Height", "MULTIPLY", y, 3),
                g.m("Painted Fold Advection", "MULTIPLY", clock, 0.14),
            ),
            0,
        ),
        noise.inputs["Vector"],
    )
    g.link(
        g.m(
            "Painted Fold Detail", "MULTIPLY", g.value("Body Noise Scale", prop="noise_scale"), 0.5
        ),
        noise.inputs["Scale"],
    )
    noise.inputs["Detail"].default_value = 1
    channels = g.n("ShaderNodeSeparateXYZ", "Painted Fold Directions")
    g.link(noise.outputs["Color"], channels.inputs[0])
    curl = g.m("Painted Curl", "MULTIPLY", g.value("Body Curl", prop="Fire Curl"), 0.4)
    curl = g.m("Painted Crown Bends More", "MULTIPLY", curl, y)
    warped = g.xyz(
        "Flowing Painted UV",
        g.m(
            "Painted Distorted U",
            "ADD",
            axes.outputs["X"],
            g.m(
                "Painted Side Fold",
                "MULTIPLY",
                g.m("Signed Painted Side", "SUBTRACT", channels.outputs["X"], 0.5),
                curl,
            ),
        ),
        g.m(
            "Painted Distorted V",
            "ADD",
            y,
            g.m(
                "Painted Vertical Fold",
                "MULTIPLY",
                g.m("Signed Painted Rise", "SUBTRACT", channels.outputs["Y"], 0.5),
                curl,
            ),
        ),
        0,
    )
    sample = g.v(
        "Painted Tip Margin",
        "ADD",
        g.v("Painted UV Margin", "SCALE", warped, 1.5),
        (-0.25, -0.25, 0),
    )
    path = Path(__file__).resolve().parents[1] / "blender_vfx_studio/assets/fire_density.png"
    image = bpy.data.images.load(str(path), check_existing=False)
    image.name = "VFX • Original Flame Density"
    image.colorspace_settings.name = "Non-Color"
    image["vfx_fire_density"] = 1
    image.pack()
    phase = g.m(
        "Painted Updraft Cycle", "FRACT", g.m("Painted Updraft Time", "MULTIPLY", clock, 0.20)
    )
    other = g.m("Painted Staggered Cycle", "FRACT", g.m("Painted Other Phase", "ADD", phase, 0.5))
    flow = g.xyz(
        "Painted Upward Travel",
        0,
        g.m(
            "Root Anchored Painted Flow",
            "MULTIPLY",
            g.m("Painted Flow Above Fuel", "MULTIPLY", y, 0.30),
            g.stage("Painted Flow Starts Above Fuel", y, 0.18, 0.45),
        ),
        0,
    )
    textures = []
    for index, cycle in enumerate((phase, other)):
        texture = g.n("ShaderNodeTexImage", f"Original Flame Density {index}")
        texture.image, texture.extension = image, "CLIP"
        g.link(
            g.v(
                f"Painted Advected UV {index}",
                "SUBTRACT",
                sample,
                g.v(f"Painted Flow Distance {index}", "SCALE", flow, cycle),
            ),
            texture.inputs["Vector"],
        )
        textures.append(texture.outputs["Color"])
    signed = g.m("Painted Signed Cycle", "MULTIPLY_ADD", phase, 2)
    signed.node.inputs[2].default_value = -1
    weight = g.m(
        "Painted Continuous Flow Weight",
        "SUBTRACT",
        1,
        g.m("Painted Flow Triangle", "ABSOLUTE", signed),
    )
    blend = g.n("ShaderNodeMixRGB", "Continuous Painted Density")
    g.link(weight, blend.inputs[0])
    g.link(textures[1], blend.inputs[1])
    g.link(textures[0], blend.inputs[2])
    density = blend.outputs["Color"]
    retirement = g.m(
        "Painted Editable Retirement",
        "MULTIPLY",
        g.stage("Painted Fuel Ends", p, 0.64, 1),
        g.value("Body Fade", prop="fade"),
    )
    threshold = g.m(
        "Painted Fuel Stops From Root",
        "MULTIPLY",
        retirement,
        g.m(
            "Painted Crown Retains Heat",
            "SUBTRACT",
            0.9,
            g.m("Painted Height", "MULTIPLY", y, 0.35),
        ),
    )
    threshold = g.m(
        "Painted Editable Dissolve", "ADD", threshold, g.value("Body Dissolve", prop="dissolve")
    )
    threshold = g.m("Painted Cool Edge", "ADD", threshold, 0.045)
    coverage = g.stage(
        "Painted Density Coverage",
        g.m("Painted Remaining Density", "SUBTRACT", density, threshold),
        0,
        0.07,
    )
    coverage = g.m(
        "Painted Fuel Catches", "MULTIPLY", coverage, g.stage("Painted Ignition", p, 0.01, 0.1)
    )
    coverage = g.m(
        "Painted Flow Leaves The Crown",
        "MULTIPLY",
        coverage,
        g.m(
            "Painted Crown Drifts Away",
            "SUBTRACT",
            1,
            g.stage("Painted Crown Boundary", y, 0.94, 1),
        ),
    )
    heat = g.m("Painted Density Into Heat", "MULTIPLY_ADD", density, 1.15)
    heat.node.inputs[2].default_value = 0.04
    flag = g.n("ShaderNodeAttribute", "Painted Body Identity", attribute_name="fire_body").outputs[
        "Fac"
    ]
    available = g.n(
        "ShaderNodeAttribute", "Body Camera Available", attribute_name="fire_body_available"
    ).outputs["Fac"]
    return heat, coverage, flag, available
