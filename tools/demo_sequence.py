"""Generate sixteen numbered RGBA frames of a growing energy burst."""

import math
from pathlib import Path

import bpy


def create(directory):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    size = 64
    for frame in range(16):
        image = bpy.data.images.new("Demo Sequence Frame", size, size, alpha=True)
        phase = frame / 15
        pixels = []
        for y in range(size):
            for x in range(size):
                u, v = (x + 0.5) / size * 2 - 1, (y + 0.5) / size * 2 - 1
                radius, angle = math.hypot(u, v), math.atan2(v, u)
                ring = math.exp(-(((radius - 0.12 - phase * 0.65) / 0.08) ** 2))
                rays = max(math.cos(angle * 6 + phase), 0) ** 6
                rays *= math.exp(-radius * 4) * (1 - phase)
                pixels.extend((1, 0.2, 0.02, min(1, ring + rays) * (1 - phase * 0.6)))
        image.pixels[:] = pixels
        image.filepath_raw = str(directory / f"burst{frame:04}.png")
        image.file_format = "PNG"
        image.save()
        bpy.data.images.remove(image)
    return directory / "burst0000.png"
