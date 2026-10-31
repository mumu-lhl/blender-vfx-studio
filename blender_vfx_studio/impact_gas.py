"""Original ray-marched gas frames, played with the existing native flipbook."""

import math
from functools import lru_cache

import bpy
import numpy as np

from . import core
from .impact_shape import _Nodes


def _noise(x, y, z):
    ix, iy, iz = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    fx, fy, fz = (f * f * (3 - 2 * f) for f in (fx, fy, fz))
    result = np.zeros_like(x)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                hashed = np.sin((ix + dx) * 127.1 + (iy + dy) * 311.7 + (iz + dz) * 74.7)
                hashed *= 43758.5453
                hashed -= np.floor(hashed)
                result += (
                    hashed
                    * (fx if dx else 1 - fx)
                    * (fy if dy else 1 - fy)
                    * (fz if dz else 1 - fz)
                )
    return result


@lru_cache(maxsize=3)
def _pixels(resolution):
    """Integrate density and heat through eight original 3D gas fields."""
    axis = np.linspace(-1, 1, resolution, dtype=np.float32)
    x, y = np.meshgrid(axis, axis)
    atlas = np.zeros((resolution * 2, resolution * 4, 4), dtype=np.float32)
    slices = 24
    for frame in range(8):
        age = frame / 7
        envelope = (1 - math.exp(-age * 18)) * (1 - age) ** 0.65
        if envelope == 0:
            continue
        travel = 1 - (1 - age) ** 3
        transmittance = np.ones_like(x)
        emitted = np.zeros_like(x)
        for depth in np.linspace(1, -1, slices):
            wx = x + 0.12 * np.sin(y * 4 + depth * 6 - age * 8)
            wy = y + 0.12 * np.sin(depth * 5 + x * 3 + age * 6)
            wz = np.full_like(x, depth) + 0.1 * np.cos(x * 4 + y * 3 - age * 5)
            detail = (
                0.65 * _noise(wx * 4 + age * 2, wy * 4, wz * 4)
                + 0.25 * _noise(wx * 8, wy * 8 - age * 3, wz * 8)
                + 0.1 * _noise(wx * 16, wy * 16, wz * 16 + age * 4)
            )
            field = 0.8 * math.exp(-age * 5) * np.exp(-(wx * wx + wy * wy + wz * wz) / 0.055)
            for angle, reach, width, z in (
                (0.7, 0.46, 0.27, 0.08),
                (3.4, 0.34, 0.22, -0.10),
                (5.1, 0.39, 0.24, 0.16),
            ):
                radius = width * (0.6 + 0.7 * math.sin(math.pi * age))
                cx, cy = math.cos(angle) * reach * travel, math.sin(angle) * reach * travel
                field += np.exp(
                    -((wx - cx) ** 2 + (wy - cy) ** 2 / 0.8 + (wz - z * travel) ** 2 / 0.65)
                    / radius**2
                )
            density = np.maximum(field - 0.35 - detail * 0.65, 0) * envelope
            absorb = 1 - np.exp(-density * (18 / slices))
            weight = transmittance * absorb
            temperature = np.clip(0.3 + detail * 0.7 + field * 0.17 - age * 0.2, 0, 1)
            emitted += weight * temperature**3
            transmittance *= 1 - absorb
        alpha = 1 - transmittance
        heat = np.clip((emitted / np.maximum(alpha, 1e-6) - 0.06) / 0.65, 0, 1)
        heat[alpha < 1e-5] = 0
        row, column = 1 - frame // 4, frame % 4
        tile = atlas[
            row * resolution : (row + 1) * resolution,
            column * resolution : (column + 1) * resolution,
        ]
        tile[:, :, :3] = heat[:, :, None]
        tile[:, :, 3] = alpha
    atlas.setflags(write=False)
    return atlas


def create(context, quality):
    resolution = {"LOW": 128, "MEDIUM": 192, "HIGH": 256}[quality]
    name = f"VFX • Original Burst Gas {resolution}"
    image = bpy.data.images.get(name)
    if image is None or image.get("vfx_burst_gas") != resolution:
        image = bpy.data.images.new(name, width=resolution * 4, height=resolution * 2, alpha=True)
        image.colorspace_settings.name = "Non-Color"
        image.alpha_mode = "STRAIGHT"
        image.pixels.foreach_set(_pixels(resolution).ravel())
        image["vfx_burst_gas"] = resolution
        image.pack()
    # Like user-supplied atlas images, this shared texture has no instance owner.
    root = core.create_flipbook(context, image, columns=4, rows=2)
    root["vfx_quality"] = quality
    root["vfx_parameter_keys"] = "width,height,opacity,fade,strength"
    layer = root.children[0]
    tree = layer.modifiers[0].node_group
    geometry = tree.nodes["Outside Lifetime"].outputs[0]
    join = tree.nodes.new("GeometryNodeJoinGeometry")
    join.name = join.label = "Three Soft Gas Views"
    join.location = (600, 200)
    tree.links.new(geometry, join.inputs[0])
    for index, rotation in enumerate(((math.pi / 2, 0, 0), (0, math.pi / 2, 0))):
        transform = tree.nodes.new("GeometryNodeTransform")
        transform.name = transform.label = f"Gas View {index + 2}"
        transform.location = (200, -350 - index * 300)
        transform.inputs["Rotation"].default_value = rotation
        tree.links.new(geometry, transform.inputs["Geometry"])
        tree.links.new(transform.outputs[0], join.inputs[0])
    tree.links.new(join.outputs[0], tree.nodes["Output"].inputs[0])
    tree.nodes["Output"].location = (850, 200)

    material = layer.data.materials[0]
    material.surface_render_method = "BLENDED"
    tree = material.node_tree
    before = set(tree.nodes)
    graph = _Nodes(tree, root)
    tree.nodes["Atlas Image"].interpolation = "Linear"
    heat = tree.nodes["Atlas Image"].outputs["Color"]
    hot = graph.node("ShaderNodeCombineXYZ", "Heat Keeps The Editable Hue")
    for index in range(3):
        graph.connect(
            graph.math(
                f"Hot Channel {index}",
                "POWER",
                graph.value(f"Gas Tint {index}", f"color_{index}"),
                0.25,
            ),
            hot.inputs[index],
        )
    color = graph.node("ShaderNodeMixRGB", "Burning Pockets And Darker Gas")
    graph.connect(graph.math("Heat Pockets", "MULTIPLY", heat, heat), color.inputs[0])
    graph.connect(
        graph.vector("Subordinate Gas Tint", "SCALE", tree.nodes["Sprite Tint"].outputs[0], 0.3),
        color.inputs[1],
    )
    graph.connect(hot.outputs[0], color.inputs[2])
    graph.connect(color.outputs[0], tree.nodes["Emission"].inputs["Color"])
    normal = graph.node("ShaderNodeNewGeometry", "Gas View Facing")
    facing = graph.node("ShaderNodeVectorMath", "Soft View Weight", operation="DOT_PRODUCT")
    graph.connect(normal.outputs["Normal"], facing.inputs[0])
    graph.connect(normal.outputs["Incoming"], facing.inputs[1])
    weight = graph.math(
        "Oblique Cards Stay Subordinate",
        "MULTIPLY",
        facing.outputs["Value"],
        facing.outputs["Value"],
    )
    graph.connect(
        graph.math(
            "Soft Gas Coverage", "MULTIPLY", tree.nodes["Lifetime Alpha"].outputs[0], weight
        ),
        tree.nodes["Sprite Surface"].inputs[0],
    )
    created = set(tree.nodes) - before
    frame = tree.nodes.new("NodeFrame")
    frame.label = "Original gas heat and soft view coverage"
    for item in created:
        item.parent = frame
    frame.location = (2300, -600)
    return root
