"""Native playback of packed sprites in a new process, without extension imports."""

import sys

import bpy

assert not any("blender_vfx_studio" in name for name in sys.modules)
roots = [o for o in bpy.data.objects if o.get("vfx_role") == "controller"]
assert len(roots) == 2
for root in roots:
    image = root.children[0].data.materials[0].node_tree.nodes["Atlas Image"].image
    assert image.packed_file is not None
for frame in (5, 0, 3, 1, 4, 2, 13):
    bpy.context.scene.frame_set(frame)
    for root in roots:
        layer = root.children[0]
        mesh = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        assert len(mesh.vertices) == (4 if frame >= 1 else 0)
        if mesh.vertices:
            expected = 1.5 if root.name.endswith("Copy") else 1
            assert abs(max(v.co.x for v in mesh.vertices) - expected) < 1e-6
        for data in (layer.modifiers[0].node_group, layer.data.materials[0].node_tree):
            assert all(
                c.driver.is_valid and c.driver.is_simple_expression
                for c in data.animation_data.drivers
            )
# Check actual shader sampling after reload, including backwards seeking and a loop wrap.
for frame, expected in [
    (3, (0, 0, 1)),
    (1, (1, 0, 0)),
    (4, (1, 1, 1)),
    (2, (0, 1, 0)),
    (5, (1, 0, 0)),
]:
    bpy.context.scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(bpy.context.scene.render.filepath, check_existing=False)
    pixel = image.pixels[(8 * 16 + 8) * 4 : (8 * 16 + 8) * 4 + 3]
    assert all(abs(a - b) < 0.03 for a, b in zip(pixel, expected)), (frame, tuple(pixel))
    bpy.data.images.remove(image)
print("FLIPBOOK_NATIVE_REOPEN_OK")
