"""Native particle playback in a fresh process, without loading the extension."""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from particle_test_support import render_pixels

assert not any("blender_vfx_studio" in name for name in sys.modules)
roots = [o for o in bpy.data.objects if o.get("vfx_module") == "particle.burst"]
assert len(roots) == 2
for frame in (13, 0, 25, 1, 7, 24):
    bpy.context.scene.frame_set(frame)
    for root in roots:
        layer = root.children[0]
        mesh = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        if frame in (0, 25):
            assert not mesh.vertices
        else:
            time = (frame - 1) / 24
            centroid = sum(v.co.z for v in mesh.vertices) / len(mesh.vertices)
            assert abs(centroid - (2 * time - 2 * time * time)) < 1e-5
        for data in (layer.modifiers[0].node_group, layer.data.materials[0].node_tree):
            assert all(
                c.driver.is_valid and c.driver.is_simple_expression
                for c in data.animation_data.drivers
            )
for frame, expected in [(13, (1, 0, 0)), (25, (0, 0, 0))]:
    result = render_pixels(frame)
    index = (24 * 48 + 24) * 4
    assert all(abs(a - b) < 0.03 for a, b in zip(result[index : index + 3], expected)), (
        frame,
        result[index : index + 3],
    )
print("PARTICLE_NATIVE_REOPEN_OK")
