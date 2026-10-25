"""Compare saved impact geometry and drivers at arbitrary frames without extension code."""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from particle_test_support import render_pixels

assert not any("blender_vfx_studio" in name for name in sys.modules)
root = bpy.data.objects["Persisted Impact"]
children = [obj for obj in bpy.data.objects if obj.get("vfx_composition") == root]
assert len(children) == 4
for frame in (14, 0, 5, 2, 25, 5):
    bpy.context.scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    for child in children:
        layer = child.children[0]
        mesh = layer.evaluated_get(graph).data
        if frame in (0, 25):
            assert not mesh.vertices
        else:
            actual = [c for vertex in mesh.vertices for c in vertex.co]
            expected = child[f"expected_shape_{frame}"]
            assert len(actual) == len(expected)
            assert not actual or max(abs(a - b) for a, b in zip(actual, expected)) < 1e-5
        for data in (child, layer.modifiers[0].node_group, layer.data.materials[0].node_tree):
            assert all(
                curve.driver.is_valid and curve.driver.is_simple_expression
                for curve in (data.animation_data.drivers if data.animation_data else ())
            )
for frame in (14, 9, 2, 5):
    if f"expected_pixels_{frame}" in root:
        assert list(root[f"expected_pixels_{frame}"]) == render_pixels(frame)
print("IMPACT_NATIVE_REOPEN_OK")
