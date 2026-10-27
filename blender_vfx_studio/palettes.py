"""Small native heat palettes; applying one edits values, never rebuilds a material."""

FIRE_STOPS = (0.22, 0.48, 0.73, 0.95, 1.0)
FIRE_PALETTES = {
    "ORANGE": (
        (0.075, 0.008, 0.002, 1),
        (0.42, 0.025, 0.002, 1),
        (1, 0.16, 0.008, 1),
        (1, 0.55, 0.035, 1),
        (1, 0.92, 0.34, 1),
    ),
    "BLUE": (
        (0.002, 0.012, 0.06, 1),
        (0.005, 0.045, 0.35, 1),
        (0.025, 0.2, 1, 1),
        (0.1, 0.65, 1, 1),
        (0.65, 1, 1, 1),
    ),
    "GREEN": (
        (0.003, 0.035, 0.008, 1),
        (0.012, 0.17, 0.025, 1),
        (0.12, 0.65, 0.05, 1),
        (0.45, 1, 0.2, 1),
        (0.85, 1, 0.6, 1),
    ),
}


def fire_ramp(root):
    if "Fire Height" not in root:
        return None
    for child in root.children:
        if child.type == "MESH":
            for material in child.data.materials:
                if material and material.node_tree:
                    node = material.node_tree.nodes.get("Painted Red Orange Yellow")
                    if node and node.type == "VALTORGB":
                        return node
    return None


def apply_fire(root, palette):
    node = fire_ramp(root)
    if palette not in FIRE_PALETTES or node is None or len(node.color_ramp.elements) != 5:
        raise ValueError(
            "Select a fire layer with the five-stop heat ramp, or edit its custom ramp directly"
        )
    # Keep positions, links, extra nodes and animation; the explicit palette choice sets colors.
    for element, color in zip(node.color_ramp.elements, FIRE_PALETTES[palette]):
        element.color = color
    for i in range(3):
        root[f"color_{i}"] = 1.0
    node.id_data.update_tag()
    root.update_tag()
    return root
