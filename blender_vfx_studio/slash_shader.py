"""Native blade shading and wakes, with preserved older asset versions."""

import bpy

from .nodes import PROGRESS, TIME_PROPS, drive, node


def shader(root, uid):
    material = bpy.data.materials.new("VFX • Layered Slash")
    material["vfx_id"] = uid
    material.use_nodes = True
    material.surface_render_method = "BLENDED"
    tree = material.node_tree
    tree.nodes.clear()
    link = tree.links.new
    count = 0

    def make(kind, name, **attrs):
        nonlocal count
        result = node(tree, kind, name, (count % 7) * 220, -(count // 7) * 230, **attrs)
        count += 1
        return result

    def connect(socket, source):
        if isinstance(source, (int, float)):
            socket.default_value = source
        else:
            link(source, socket)

    def mathn(name, operation, a, b=0, clamp=False):
        n = make("ShaderNodeMath", name, operation=operation)
        connect(n.inputs[0], a)
        connect(n.inputs[1], b)
        n.use_clamp = clamp
        return n.outputs[0]

    def value(name, prop=None):
        n = make("ShaderNodeValue", name)
        drive(
            n.outputs[0],
            "default_value",
            root,
            "p" if prop else PROGRESS,
            {"p": prop} if prop else TIME_PROPS,
        )
        return n.outputs[0]

    def scale(name, vector, amount):
        n = make("ShaderNodeVectorMath", name, operation="SCALE")
        link(vector, n.inputs[0])
        connect(n.inputs["Scale"], amount)
        return n.outputs[0]

    uv = make("ShaderNodeTexCoord", "Slash UV")
    separate = make("ShaderNodeSeparateXYZ", "Along Arc / Across Body")
    link(uv.outputs["UV"], separate.inputs[0])
    u, v = separate.outputs["X"], separate.outputs["Y"]
    progress = value("Progress")
    global_progress = progress
    shaped = root["vfx_asset_version"] >= 3
    layered = root["vfx_asset_version"] >= 4
    attr = make("ShaderNodeAttribute", "Wake Index", attribute_name="vfx_wake")
    band = attr.outputs["Fac"]
    primary = mathn("Primary Ribbon", "LESS_THAN", band, 0.5)
    wake = mathn("Auxiliary Ribbons", "SUBTRACT", 1, primary)
    if layered:
        delay = mathn("Layer Birth Delay", "MULTIPLY", band, 0.06)
        age = mathn("Time Since Layer Birth", "SUBTRACT", progress, delay)
        age = mathn("Nonnegative Layer Age", "MAXIMUM", age, 0)
        span = mathn("Wake Life Extension", "MULTIPLY", band, 0.1)
        span = mathn("Independent Layer Span", "ADD", span, 1)
        progress = mathn("Layer Local Clock", "DIVIDE", age, span)

    attack = value("Attack", "attack")
    front = mathn("Reveal Front", "DIVIDE", progress, attack, clamp=True)
    distance = mathn("Distance Behind Tip", "SUBTRACT", front, u)
    reveal = mathn("Soft Moving Tip", "MULTIPLY", distance, 35, clamp=True)
    remaining = mathn("Remaining Life", "SUBTRACT", 1, progress)
    release = mathn("Release Curve", "POWER", remaining, 1.6)
    fade = value("Fade", "fade")
    loss = mathn("Release Loss", "SUBTRACT", 1, release)
    loss = mathn("Fade Amount", "MULTIPLY", loss, fade)
    envelope = mathn("Attack / Release", "SUBTRACT", 1, loss)
    envelope = mathn("Revealed Envelope", "MULTIPLY", envelope, reveal)

    core_width = value("Core Width", "core_width")
    center = mathn("Blade Center", "MULTIPLY", core_width, 0.5)
    blade = mathn("Blade Distance", "SUBTRACT", v, center)
    blade = mathn("Absolute Blade Distance", "ABSOLUTE", blade)
    blade = mathn("Normalized Blade Distance", "DIVIDE", blade, center)
    blade = mathn("Blade Profile", "SUBTRACT", 1, blade, clamp=True)
    blade = mathn("Sharp Blade", "POWER", blade, 0.65)
    white = mathn("Primary Highlight Only", "MULTIPLY", blade, primary)
    if layered:
        focus = mathn("Head Light Start", "SUBTRACT", u, 0.35, clamp=True)
        focus = mathn("Head Light Concentration", "MULTIPLY", focus, 2, clamp=True)
        focus = mathn("Head Light Range", "MULTIPLY", focus, 0.85)
        focus = mathn("Faint Trailing Edge", "ADD", focus, 0.15)
    else:
        focus = mathn("Leading Highlight", "POWER", u, 2)
        focus = mathn("Highlight Range", "MULTIPLY", focus, 0.65)
        focus = mathn("Tail Highlight", "ADD", focus, 0.35)
    white = mathn("Highlight Focus", "MULTIPLY", white, focus)
    if shaped:
        spent = mathn("Spent Blade Light", "SUBTRACT", progress, 0.32, clamp=True)
        spent = mathn("Blade Light Release", "MULTIPLY", spent, 2, clamp=True)
        white = mathn(
            "Blade Light Remaining",
            "MULTIPLY",
            white,
            mathn("Light Envelope", "SUBTRACT", 1, spent),
        )

    # Stretch noise along the arc: long filaments, narrow variation across width.
    coordinates = make("ShaderNodeCombineXYZ", "Stretched Flow Coordinates")
    along_flow = mathn("Along Flow", "MULTIPLY", u, 0.8 if layered else 1.8)
    if layered:
        along_flow = mathn(
            "Flow Along The Sweep",
            "SUBTRACT",
            along_flow,
            mathn("Sweep Flow Clock", "MULTIPLY", progress, 0.9),
        )
    link(along_flow, coordinates.inputs["X"])
    link(mathn("Across Filaments", "MULTIPLY", v, 1.2 if layered else 5.5), coordinates.inputs["Y"])
    link(mathn("Flow Over Life", "MULTIPLY", progress, 0.8), coordinates.inputs["Z"])
    noise = make("ShaderNodeTexNoise", "Directional Filament Noise")
    noise.inputs["Detail"].default_value = 1 if layered else 2
    link(coordinates.outputs[0], noise.inputs["Vector"])
    link(value("Noise Scale", "noise_scale"), noise.inputs["Scale"])
    late = mathn("After Strike", "SUBTRACT", progress, 0.28, clamp=True)
    late = mathn("Release Erosion", "MULTIPLY", late, 1.35)
    late = mathn("Breakup Amount", "MULTIPLY", late, value("Breakup", "breakup"))
    tail = mathn("Trailing Coordinates", "SUBTRACT", 1, u)
    tail = mathn("Trailing Erosion", "MULTIPLY", tail, late)
    tail = mathn("Tail Breakup Weight", "MULTIPLY", tail, 0.35)
    late = mathn("Tail First Release", "ADD", late, tail)
    cutoff = mathn("Dissolve Over Life", "ADD", value("Dissolve", "dissolve"), late)
    inward = mathn("Inner Edge Erosion", "MULTIPLY", v, 0.22)
    cutoff = mathn("Directional Cutoff", "ADD", cutoff, inward)
    protection = mathn("Blade Erodes Last", "MULTIPLY", blade, 0.3)
    protection = mathn("Blade Protection Fades", "MULTIPLY", protection, remaining)
    cutoff = mathn("Protected Blade Cutoff", "SUBTRACT", cutoff, protection)
    erode = mathn("Noise Minus Cutoff", "SUBTRACT", noise.outputs["Fac"], cutoff)
    erode = mathn("Soft Erosion", "MULTIPLY", erode, 16, clamp=True)
    # A cutoff of one must always remove the entire material, including the blade.
    visible = mathn("Not Fully Dissolved", "LESS_THAN", value("Dissolve Limit", "dissolve"), 1)
    erode = mathn("Dissolve Mask", "MULTIPLY", erode, visible)
    if shaped:
        # Hard illustrated cutouts remove spatial pieces instead of leaving a
        # faint complete crescent. Keep the old shader path unchanged for v2.
        erode = mathn("Illustrated Cutout", "GREATER_THAN", erode, 0.22)

    filament = mathn("Filament Phase", "MULTIPLY", v, 22 if layered else 80)
    distortion = mathn("Noise Distortion", "MULTIPLY", noise.outputs["Fac"], 5 if layered else 14)
    filament = mathn("Distorted Filaments", "ADD", filament, distortion)
    filament = mathn("Filament Bands", "SINE", filament)
    filament = mathn("Filament Contrast", "MULTIPLY", filament, 0.35)
    filament = mathn("Filament Brightness", "ADD", filament, 0.65)
    contrast = mathn("Streak Contrast", "MULTIPLY", value("Streaks", "streaks"), 0.75)
    lost = mathn("Filament Gaps", "SUBTRACT", 1, filament)
    lost = mathn("Streak Modulation", "MULTIPLY", lost, contrast)
    detail = mathn("Body Detail", "SUBTRACT", 1, lost)
    # Preserve a continuous blade while allowing the body to split into strands.
    detail = mathn("Continuous Blade", "MAXIMUM", detail, blade)
    edge = mathn("Outer Soft Edge", "MULTIPLY", v, 90, clamp=True)
    inner = mathn("Inner Soft Edge", "SUBTRACT", 1, v)
    inner = mathn("Body Softness", "POWER", inner, 0.65)
    alpha = mathn("Body Edges", "MULTIPLY", edge, inner)
    for name, factor in (("Filaments", detail), ("Erosion", erode), ("Envelope", envelope)):
        alpha = mathn(name + " Opacity", "MULTIPLY", alpha, factor)
    if shaped:
        alpha = mathn("Solid Body Edge", "LESS_THAN", v, 0.98)
        alpha = mathn("Blade Outer Edge", "MULTIPLY", alpha, edge)
        alpha = mathn("Cutout Body", "MULTIPLY", alpha, erode)
        alpha = mathn("Revealed Body", "MULTIPLY", alpha, reveal)
        cut_phase = mathn("Tear Along Arc", "MULTIPLY", u, 17 if layered else 26)
        cut_phase = mathn(
            "Diagonal Tears",
            "ADD",
            cut_phase,
            mathn("Tear Across", "MULTIPLY", v, 3 if layered else 7),
        )
        cut_phase = mathn(
            "Moving Tears", "SUBTRACT", cut_phase, mathn("Tear Clock", "MULTIPLY", progress, 4)
        )
        cuts = mathn("Tear Pattern", "SINE", cut_phase)
        cuts = mathn("Open Tears", "GREATER_THAN", cuts, 0.78)
        cuts = mathn("Protect Edge", "MULTIPLY", cuts, mathn("Body Only", "GREATER_THAN", v, 0.24))
        cuts = mathn(
            "Trailing Tears Only", "MULTIPLY", cuts, mathn("Tail Region", "LESS_THAN", u, 0.7)
        )
        alpha = mathn(
            "Broken Tail", "MULTIPLY", alpha, mathn("Intact Regions", "SUBTRACT", 1, cuts)
        )
        release_phase = mathn("Release Fragment Phase", "MULTIPLY", u, 11 if layered else 19)
        release_phase = mathn(
            "Irregular Fragment Boundaries",
            "ADD",
            release_phase,
            mathn("Fragment Variation", "MULTIPLY", noise.outputs["Fac"], 1.2 if layered else 3),
        )
        if layered:
            release_phase = mathn(
                "Separate Layer Fragments",
                "ADD",
                release_phase,
                mathn("Layer Fragment Phase", "MULTIPLY", band, 1.4),
            )
        islands = mathn("Release Islands", "SINE", release_phase)
        islands = mathn("Island Range", "MULTIPLY", islands, 0.5)
        islands = mathn("Positive Islands", "ADD", islands, 0.5)
        threshold = mathn("After Peak", "SUBTRACT", progress, 0.30, clamp=True)
        threshold = mathn("Fragment Release", "MULTIPLY", threshold, 3, clamp=True)
        threshold = mathn("Editable Fragment Fade", "MULTIPLY", threshold, fade)
        islands = mathn("Surviving Pieces", "GREATER_THAN", islands, threshold)
        alpha = mathn("Separated Release Pieces", "MULTIPLY", alpha, islands)
    wake_distance = mathn("Wake Layer Distance", "MULTIPLY", band, 0.35) if layered else band
    wake_weight = mathn("Wake Distance", "ADD", wake_distance, 0.75 if layered else 1)
    wake_weight = mathn("Wake Opacity", "DIVIDE", value("Afterimage", "afterimage"), wake_weight)
    delay = mathn("Wake Delay", "MULTIPLY", band, 0.06)
    arrived = mathn(
        "Wake Has Arrived", "GREATER_THAN", global_progress if layered else progress, delay
    )
    if shaped:
        packet = mathn("Wake Segments", "MULTIPLY", u, 15)
        packet = mathn(
            "Wake Phase", "ADD", packet, mathn("Separate Wake Phase", "MULTIPLY", band, 1.7)
        )
        packet = mathn(
            "Wake Segment Motion", "SUBTRACT", packet, mathn("Wake Clock", "MULTIPLY", progress, 6)
        )
        packet = mathn("Wake Islands", "SINE", packet)
        packet = mathn("Separate Wake Islands", "GREATER_THAN", packet, -0.25)
        arrived = mathn("Broken Wakes", "MULTIPLY", arrived, packet)
    wake_weight = mathn("Delayed Wake", "MULTIPLY", wake_weight, arrived)
    wake_weight = mathn("Subordinate Wake", "MULTIPLY", wake_weight, wake)
    layer_weight = mathn("Layer Hierarchy", "ADD", primary, wake_weight)
    alpha = mathn("Final Opacity", "MULTIPLY", alpha, layer_weight)

    tint = make("ShaderNodeCombineXYZ", "Editable Body Color")
    for index in range(3):
        drive(tint.inputs[index], "default_value", root, "c", {"c": f"color_{index}"})
    body = mathn("Body Gradient", "POWER", inner, 1.4)
    body = mathn("Body Weight", "MULTIPLY", body, 0.65)
    body = mathn("Dark Inner Color", "ADD", body, 0.08)
    body = mathn("Gradient Filaments", "MULTIPLY", body, detail)
    if shaped:
        mid = mathn("Middle Color Band", "LESS_THAN", v, 0.64)
        outer = mathn("Outer Color Band", "LESS_THAN", v, 0.22)
        body = mathn("Middle Violet", "MULTIPLY", mid, 0.3)
        body = mathn("Outer Violet", "ADD", body, mathn("Bright Violet", "MULTIPLY", outer, 0.4))
        body = mathn("Ink Inner Body", "ADD", body, 0.045)
        body = mathn(
            "Subtle Brush Detail",
            "MULTIPLY",
            body,
            mathn("Brush Floor", "ADD", mathn("Brush Contrast", "MULTIPLY", detail, 0.2), 0.8),
        )
    body_color = scale("Tinted Body", tint.outputs[0], body)
    if layered:
        along_value = mathn("Value Toward Leading Head", "MULTIPLY", u, 0.4)
        along_value = mathn("Trailing Color Value", "ADD", along_value, 0.6)
        body_color = scale("Color Mass Follows Head", body_color, along_value)
        channel = mathn("Broad Flow Channel", "SUBTRACT", noise.outputs["Fac"], 0.48)
        channel = mathn("Flow Channel Edge", "MULTIPLY", channel, 8, clamp=True)
        middle = mathn("Inner Channel Center", "SUBTRACT", v, 0.4)
        middle = mathn("Inner Channel Distance", "ABSOLUTE", middle)
        middle = mathn("Inner Channel Width", "DIVIDE", middle, 0.24)
        middle = mathn("Channel Stays Inside Body", "SUBTRACT", 1, middle, clamp=True)
        channel = mathn("Pointed Inner Flow", "MULTIPLY", channel, middle)
        channel = mathn(
            "Editable Flow Detail", "MULTIPLY", channel, value("Flow Streaks", "streaks")
        )
        channel = mathn("Subordinate Inner Channel", "MULTIPLY", channel, 0.6)
        flow = make("ShaderNodeMixRGB", "Moving Colored Flow Beneath White Edge")
        link(channel, flow.inputs[0])
        link(body_color, flow.inputs[1])
        link(scale("Saturated Inner Flow", tint.outputs[0], 0.9), flow.inputs[2])
        body_color = flow.outputs[0]
    highlight = make("ShaderNodeCombineXYZ", "Cool Blade White")
    for socket, component in zip(highlight.inputs, (0.8, 0.9, 1.0)):
        socket.default_value = component
    highlight_color = scale("Blade Highlight", highlight.outputs[0], white)
    color = make("ShaderNodeVectorMath", "Blade Plus Body", operation="ADD")
    link(body_color, color.inputs[0])
    link(highlight_color, color.inputs[1])
    emission = make("ShaderNodeEmission", "Layered Emission")
    link(color.outputs[0], emission.inputs["Color"])
    link(value("Emission", "strength"), emission.inputs["Strength"])
    transparent = make("ShaderNodeBsdfTransparent", "Transparent")
    mix = make("ShaderNodeMixShader", "Blade Surface")
    link(alpha, mix.inputs[0])
    link(transparent.outputs[0], mix.inputs[1])
    link(emission.outputs[0], mix.inputs[2])
    output = make("ShaderNodeOutputMaterial", "Surface")
    link(mix.outputs[0], output.inputs["Surface"])
    return material
