"""Individual particle births and lifetimes survive native, addon-free playback."""

import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from emitter_test_support import particles
from particle_test_support import render_pixels

assert not any("blender_vfx_studio" in name for name in sys.modules)
root = bpy.data.objects["Persisted Emitter"]
expected = {
    0: [],
    1: [0],
    6: [0, 0.5, 1],
    11: [0, 0.5, 1, 1.5],
    31: [0.5, 1, 1.5],
    36: [1.5],
    39: [],
}
for frame in (31, 1, 0, 11, 6, 36, 39, 11):
    z = sorted(center.z for center, _ in particles(root, frame))
    assert len(z) == len(expected[frame]), (frame, len(z))
    assert all(abs(a - b) < 1e-5 for a, b in zip(z, expected[frame]))
for frame, color in ((11, (1, 0, 0)), (39, (0, 0, 0))):
    pixels = render_pixels(frame)
    rgb = pixels[(24 * 48 + 24) * 4 : (24 * 48 + 24) * 4 + 3]
    assert all(abs(a - b) < 0.03 for a, b in zip(rgb, color)), (frame, rgb)
print("EMITTER_NATIVE_REOPEN_OK")
