"""Bounded, CPU-only copies of still-image pixels for native asset previews."""

import math
from array import array
from pathlib import Path

import bpy

MAX_INPUT_SIDE = 2048
MAX_PREVIEW_SIDE = 256


def _pixel(source, index, alpha_mode):
    pixel = source[index : index + 4]
    if not all(math.isfinite(value) for value in pixel):
        raise ValueError("The preview contains non-finite pixel values")
    pixel = [min(max(value, 0.0), 1.0) for value in pixel]
    if alpha_mode in {"NONE", "CHANNEL_PACKED"}:
        pixel[3] = 1.0
    elif alpha_mode == "STRAIGHT":
        for channel in range(3):
            pixel[channel] *= pixel[3]
    return pixel


def prepare(image):
    """Return (size, premultiplied RGBA pixels), without editing or creating Blender data."""
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
    alpha_mode = image.alpha_mode
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
            # Native previews use premultiplied RGB. Convert before filtering so
            # invisible color cannot bleed into a neighboring opaque pixel.
            a, b, c, d = (
                _pixel(source, (py * width + px) * 4, alpha_mode)
                for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))
            )
            for channel in range(4):
                top = a[channel] * (1 - fx) + b[channel] * fx
                bottom = c[channel] * (1 - fx) + d[channel] * fx
                result.append(top * (1 - fy) + bottom * fy)
    return size, result


def apply(collection, prepared):
    if prepared is None:
        return
    size, pixels = prepared
    preview = collection.preview_ensure()
    preview.image_size = size
    preview.image_pixels_float = pixels
