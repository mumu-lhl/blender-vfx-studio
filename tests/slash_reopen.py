"""The current saved slash seeks and renders without the extension."""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from particle_test_support import render_pixels

assert "blender_vfx_studio" not in sys.modules
root = bpy.data.objects["Persisted Slash"]
for frame in (13, 2, 5, 17, 5):
    bpy.context.scene.frame_set(frame)
    mesh = root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    if frame == 17:
        assert not mesh.vertices
        continue
    actual = [c for vertex in mesh.vertices for c in vertex.co]
    expected = root[f"expected_shape_{frame}"]
    assert len(actual) == len(expected)
    assert max(abs(a - b) for a, b in zip(actual, expected)) < 1e-5
    assert list(root[f"expected_pixels_{frame}"]) == render_pixels(frame)
for data in (
    root.children[0].modifiers[0].node_group,
    root.children[0].data.materials[0].node_tree,
):
    assert all(
        c.driver.is_valid and c.driver.is_simple_expression for c in data.animation_data.drivers
    )
print("SLASH_NATIVE_REOPEN_OK")
