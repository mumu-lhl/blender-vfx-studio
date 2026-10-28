"""Build editable silhouette and depth fields; playback uses native nodes only."""

from .nodes import drive, node


def shape(tree, root, u, across, band, progress, radius, offset, width_profile):
    link = tree.links.new
    count = 0

    def mathn(name, operation, a, b=0):
        nonlocal count
        n = node(
            tree,
            "ShaderNodeMath",
            name,
            count % 6 * 220,
            2700 + count // 6 * 180,
            operation=operation,
        )
        count += 1
        for socket, source in zip(n.inputs, (a, b)):
            if isinstance(source, (int, float)):
                socket.default_value = source
            else:
                link(source, socket)
        return n.outputs[0]

    def value(name, prop):
        n = node(tree, "ShaderNodeValue", name, -400, 2700 + count * 20)
        drive(n.outputs[0], "default_value", root, "p", {"p": prop})
        return n.outputs[0]

    contour = value("Contour", "contour")
    envelope = mathn("Contour End Taper", "SINE", mathn("Arc Half Turn", "MULTIPLY", u, 3.14159265))
    envelope = mathn("Nonnegative Contour", "MAXIMUM", envelope, 0)
    edge_phase = mathn("Broad Edge Phase", "MULTIPLY", u, 11)
    edge_phase = mathn(
        "Contour Follows Sweep",
        "SUBTRACT",
        edge_phase,
        mathn("Contour Clock", "MULTIPLY", progress, 4),
    )
    wave = mathn("Uneven Broad Edge", "SINE", edge_phase)
    wave = mathn("Broad Edge Depth", "MULTIPLY", wave, 0.045)
    hook = mathn("Hook Center", "SUBTRACT", u, 0.79)
    hook = mathn("Hook Distance", "ABSOLUTE", hook)
    hook = mathn("Hook Span", "MULTIPLY", hook, 7)
    hook = mathn("Hook Triangle", "SUBTRACT", 1, hook)
    hook = mathn("Hook Limits", "MAXIMUM", hook, 0)
    hook = mathn("Pointed Hook", "POWER", hook, 1.5)
    hook = mathn("Hook Reach", "MULTIPLY", hook, 0.3)
    hook = mathn("Editable Leading Hook", "MULTIPLY", hook, value("Hook", "hook"))
    contour_field = mathn("Authored Edge", "ADD", wave, hook)
    contour_field = mathn("Tapered Edge", "MULTIPLY", contour_field, envelope)
    contour_field = mathn("Contour Amount", "MULTIPLY", contour_field, contour)
    wake_contour = mathn("Wake Contour Reduction", "MULTIPLY", band, 0.32)
    wake_contour = mathn("Wake Contour Weight", "SUBTRACT", 1, wake_contour)
    contour_field = mathn("Subordinate Wake Shape", "MULTIPLY", contour_field, wake_contour)
    contour_field = mathn("Radius Relative Contour", "MULTIPLY", contour_field, radius)
    outer = mathn("Irregular Outer Edge", "ADD", radius, contour_field)
    tooth = 0
    for index, (center, span, depth) in enumerate(
        ((0.2, 0.1, 0.22), (0.49, 0.05, 0.5), (0.64, 0.07, 0.3))
    ):
        label = f"Inner Opening {index + 1}"
        distance = mathn(label + " Center", "SUBTRACT", u, center)
        distance = mathn(label + " Distance", "ABSOLUTE", distance)
        distance = mathn(label + " Span", "DIVIDE", distance, span)
        opening = mathn(label + " Shape", "SUBTRACT", 1, distance)
        opening = mathn(label + " Bounds", "MAXIMUM", opening, 0)
        opening = mathn(label + " Depth", "MULTIPLY", opening, depth)
        pulse = mathn(label + " Clock", "MULTIPLY", progress, 8)
        pulse = mathn(label + " Phase", "ADD", pulse, index * 1.7)
        pulse = mathn(label + " Pulse", "SINE", pulse)
        pulse = mathn(label + " Variation", "MULTIPLY", pulse, 0.25)
        pulse = mathn(label + " Retained Depth", "ADD", pulse, 0.75)
        opening = mathn(label + " Moving Tear", "MULTIPLY", opening, pulse)
        tooth = mathn(label + " Contribution", "ADD", tooth, opening)
    tooth = mathn("Editable Teeth", "MULTIPLY", tooth, contour)
    tooth = mathn(
        "Independent Inner Notches", "MULTIPLY", tooth, value("Inner Notches", "inner_notches")
    )
    tooth = mathn("Full Inner Width", "ADD", 1, tooth)
    offset = mathn("Torn Inner Edge", "MULTIPLY", offset, tooth)
    depth_phase = mathn("Bank Along Arc", "MULTIPLY", u, 3.8)
    depth_phase = mathn("Depth Curve", "SINE", depth_phase)
    across = mathn("Blade Fold Line", "SUBTRACT", across, 0.18)
    depth = mathn("Fold Across Body", "MULTIPLY", depth_phase, across)
    # A zero-width tip must also close in depth. This includes the moving
    # reveal front and the individually narrowed/fractured wake sections.
    depth = mathn("Fold Follows Ribbon Width", "MULTIPLY", depth, width_profile)
    wake = mathn("Wake Depth Separation", "MULTIPLY", band, 0.32)
    wake = mathn("Wake Depth Over Life", "MULTIPLY", wake, progress)
    depth = mathn("Layer Depth", "ADD", depth, wake)
    depth = mathn("Bank Amount", "MULTIPLY", depth, value("Bank", "bank"))
    depth = mathn("Radius Relative Bank", "MULTIPLY", depth, radius)
    return (outer, offset, depth)
