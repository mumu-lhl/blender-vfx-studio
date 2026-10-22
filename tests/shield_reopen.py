"""Fresnel and native lifetime work after reopening without the extension."""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from particle_test_support import render_pixels

root = bpy.data.objects["Persisted Shield"]
layer = root.children[0]
for frame, radius in ((13, 1.5), (1, 1.0), (13, 1.5)):
    bpy.context.scene.frame_set(frame)
    mesh = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    assert abs(max(v.co.length for v in mesh.vertices) - radius) < 1e-5
pixels = render_pixels(13)
center = (24 * 48 + 24) * 4 + 3
rim = (24 * 48 + 40) * 4 + 3
assert pixels[rim] > 0.18 and pixels[rim] > pixels[center] * 2
bpy.context.scene.frame_set(25)
assert not layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
print("SHIELD_NATIVE_REOPEN_OK")
