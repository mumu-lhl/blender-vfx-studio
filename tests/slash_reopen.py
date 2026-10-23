"""Saved crescent mesh and shader evaluate with no extension."""

import bpy

root = bpy.data.objects["Persisted Slash"]
layer = root.children[0]
for frame, axis in ((1, 0), (13, 1), (1, 0)):
    bpy.context.scene.frame_set(frame)
    result = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    assert min(v.co[axis] for v in result.vertices) >= -1e-5
    assert abs(max(v.co.length for v in result.vertices) - 2) < 1e-5
bpy.context.scene.frame_set(25)
assert not layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
root = bpy.data.objects["Persisted Layered Slash"]
assert root["vfx_asset_version"] == 2
for frame in (13, 2, 5, 0, 17, 5):
    bpy.context.scene.frame_set(frame)
    mesh = root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    if frame in (0, 17):
        assert not mesh.vertices
    else:
        expected = root[f"expected_shape_{frame}"]
        actual = [c for vertex in mesh.vertices for c in vertex.co]
        assert len(expected) == len(actual)
        assert max(abs(a - b) for a, b in zip(actual, expected)) < 1e-5
    for data in (
        root.children[0].modifiers[0].node_group,
        root.children[0].data.materials[0].node_tree,
    ):
        assert all(
            c.driver.is_valid and c.driver.is_simple_expression for c in data.animation_data.drivers
        )
print("SLASH_NATIVE_REOPEN_OK")
