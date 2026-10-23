"""Read evaluated emitter meshes without importing the extension."""

import math

import bpy
from mathutils import Vector


def mesh(root, frame):
    bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1)
    return root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data


def particles(root, frame):
    """Read connected mesh components, independent of native vertex ordering."""
    result = mesh(root, frame)
    adjacent = [[] for _ in result.vertices]
    for edge in result.edges:
        a, b = edge.vertices
        adjacent[a].append(b)
        adjacent[b].append(a)
    pending = set(range(len(result.vertices)))
    components = []
    while pending:
        indices = [pending.pop()]
        queue = list(indices)
        while queue:
            for neighbor in adjacent[queue.pop()]:
                if neighbor in pending:
                    pending.remove(neighbor)
                    indices.append(neighbor)
                    queue.append(neighbor)
        points = [result.vertices[i].co.copy() for i in indices]
        center = sum(points, Vector()) / len(points)
        radius = sum((point - center).length for point in points) / len(points)
        components.append((center, radius))
    return components
