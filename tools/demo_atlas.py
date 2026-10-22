"""Generate a small editable RGBA burst atlas; no binary source asset required."""

import math

import bpy


def create(filepath):
    cell = 64
    columns = rows = 4
    size = cell * columns
    image = bpy.data.images.new("Demo Burst Atlas", width=size, height=size, alpha=True)
    pixels = []
    for y in range(size):
        for x in range(size):
            frame = (rows - 1 - y // cell) * columns + x // cell
            phase = frame / 15
            u = ((x % cell + 0.5) / cell - 0.5) * 2
            v = ((y % cell + 0.5) / cell - 0.5) * 2
            radius = math.hypot(u, v)
            angle = math.atan2(v, u)
            ring = math.exp(-(((radius - (0.1 + 0.65 * phase)) / (0.1 - 0.04 * phase)) ** 2))
            rays = max(math.cos(angle * 8 + phase * 2), 0) ** 8
            flash = rays * math.exp(-radius * (3 + phase * 3)) * (1 - phase)
            alpha = min(1, (ring + flash) * (1 - phase * 0.7))
            pixels.extend((1, 0.35 + 0.45 * max(0, 1 - radius), 0.04, alpha))
    image.pixels[:] = pixels
    image.filepath_raw = str(filepath)
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image
