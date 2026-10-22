"""Native image users follow stored timing with script execution disabled."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from particle_test_support import render_pixels

expected = {1: (1, 0, 0), 3: (0, 1, 0), 5: (0, 0, 1), 7: (1, 1, 0), 9: (0, 0, 0)}
for frame in (3, 1, 7, 5, 9):
    data = render_pixels(frame)
    rgb = data[(24 * 48 + 24) * 4 : (24 * 48 + 24) * 4 + 3]
    assert all(abs(a - b) < 0.02 for a, b in zip(rgb, expected[frame])), (frame, rgb)
print("SEQUENCE_NATIVE_REOPEN_OK")
