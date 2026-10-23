"""Bounded, CPU-only copies of still-image pixels for native asset previews."""

import math
from array import array
from pathlib import Path

import bpy

MAX_INPUT_SIDE = 2048
MAX_PREVIEW_SIDE = 256


def prepare(image):
    """Return (size, RGBA pixels), without editing or creating Blender data."""
    if image is None:
        return None
    if not isinstance(image, bpy.types.Image) or image.source not in {"FILE", "GENERATED"}:
        raise ValueError("Choose a loaded still image, not a sequence, movie or render result")
    if image.source == "FILE" and not image.packed_file:
        path = bpy.path.abspath(image.filepath, library=image.library)
        if not Path(path).is_file():
            raise ValueError("The preview image file is missing; reload or pack the image")
    width, height = image.size
    if not (1 <= width <= MAX_INPUT_SIDE and 1 <= height <= MAX_INPUT_SIDE):
        raise ValueError("Preview source dimensions must be between 1 and 2048 pixels per side")
    if len(image.pixels) != width * height * 4:
        raise ValueError("The preview image has no readable RGBA pixels")
    source = array("f", [0]) * (width * height * 4)
    image.pixels.foreach_get(source)
    scale = min(1.0, MAX_PREVIEW_SIDE / max(width, height))
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    result = array("f")
    # Pixel-center bilinear sampling preserves aspect ratio without upscaling.
    # Work on copied pixels: Image.copy()/scale() need not retain unsaved source buffers.
    for y in range(size[1]):
        sy = max(0.0, min(height - 1, (y + 0.5) * height / size[1] - 0.5))
        y0, fy = int(sy), sy - int(sy)
        y1 = min(y0 + 1, height - 1)
        for x in range(size[0]):
            sx = max(0.0, min(width - 1, (x + 0.5) * width / size[0] - 0.5))
            x0, fx = int(sx), sx - int(sx)
            x1 = min(x0 + 1, width - 1)
            for channel in range(4):
                a, b = (
                    source[(y0 * width + x0) * 4 + channel],
                    source[(y0 * width + x1) * 4 + channel],
                )
                c, d = (
                    source[(y1 * width + x0) * 4 + channel],
                    source[(y1 * width + x1) * 4 + channel],
                )
                value = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
                if not math.isfinite(value):
                    raise ValueError("The preview contains non-finite pixel values")
                result.append(min(max(value, 0.0), 1.0))
    return size, result


def apply(collection, prepared):
    if prepared is None:
        return
    size, pixels = prepared
    preview = collection.preview_ensure()
    preview.image_size = size
    preview.image_pixels_float = pixels
