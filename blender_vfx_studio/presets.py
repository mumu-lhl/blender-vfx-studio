"""Portable, validated parameter snapshots. JSON data never executes code."""

import json
import math
import os
import tempfile
from pathlib import Path

from .parameters import preset_parameters_for
from .registry import MODULES

FORMAT_VERSION = 2
MAX_BYTES = 65536
QUALITY = {"LOW", "MEDIUM", "HIGH"}
# Birth frame is deliberately local to the destination scene.
PRESET_PARAMETERS = preset_parameters_for("mesh.ring")
LEGACY_FIELDS = {"format_version", "module", "asset_version", "name", "quality", "parameters"}
FIELDS = LEGACY_FIELDS | {"assets"}


def validate(data):
    # Format 1 shipped only ring parameter snapshots. Keep a fixed fixture in tests.
    if (
        isinstance(data, dict)
        and type(data.get("format_version")) is int
        and data["format_version"] == 1
    ):
        if data.keys() != LEGACY_FIELDS or data.get("module") != "mesh.ring":
            raise ValueError("Invalid legacy ring preset")
        data = dict(data, format_version=2, assets={})
    if not isinstance(data, dict) or data.keys() != FIELDS:
        raise ValueError("Invalid preset fields")
    if type(data["format_version"]) is not int or data["format_version"] != FORMAT_VERSION:
        raise ValueError("Unsupported preset format version")
    module = data["module"]
    if not isinstance(module, str) or module not in MODULES:
        raise ValueError("Unknown VFX module")
    if (
        type(data["asset_version"]) is not int
        or data["asset_version"] != MODULES[module].asset_version
    ):
        raise ValueError("Unsupported module asset version")
    if module in {"trail.ribbon", "core.composition"}:
        raise ValueError("Native paths and compositions require .blend Append or Duplicate")
    name = data["name"]
    if not isinstance(name, str) or not 1 <= len(name) <= 80 or any(ord(c) < 32 for c in name):
        raise ValueError("Preset name must contain 1–80 printable characters")
    if not isinstance(data["quality"], str) or data["quality"] not in QUALITY:
        raise ValueError("Unknown quality setting")
    assets = data["assets"]
    expected_assets = {"image"} if module == "flipbook.atlas" else set()
    if not isinstance(assets, dict) or assets.keys() != expected_assets:
        raise ValueError("Preset assets are missing or unknown")
    if "image" in assets:
        path = assets["image"]
        if (
            not isinstance(path, str)
            or not 1 <= len(path) <= 4096
            or any(ord(c) < 32 for c in path)
        ):
            raise ValueError("Atlas image must be a local file path")
    specs = preset_parameters_for(module)
    parameters = data["parameters"]
    if not isinstance(parameters, dict) or parameters.keys() != specs.keys():
        raise ValueError("Preset parameters are missing or unknown")
    result = {}
    for key, (default, minimum, maximum, _) in specs.items():
        value = parameters[key]
        if type(default) is bool:
            if type(value) is not bool:
                raise ValueError(f"{key} must be a boolean")
        else:
            if type(default) is int and type(value) is not int:
                raise ValueError(f"{key} must be an integer")
            if type(value) not in (int, float) or (
                type(value) is float and not math.isfinite(value)
            ):
                raise ValueError(f"{key} must be a finite number")
            if not minimum <= value <= maximum:
                raise ValueError(f"{key} must be between {minimum} and {maximum}")
            value = int(value) if type(default) is int else float(value)
        result[key] = value
    return dict(data, parameters=result, assets=dict(assets))


def dumps(data):
    return (
        json.dumps(validate(data), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    )


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate preset field: {key}")
        result[key] = value
    return result


def loads(text):
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Preset exceeds 64 KiB")
    try:
        return validate(json.loads(text, object_pairs_hook=_unique_object))
    except (RecursionError, OverflowError) as error:
        raise ValueError("Preset nesting or numeric value is too large") from error


def read(filepath):
    with open(filepath, "rb") as stream:
        content = stream.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValueError("Preset exceeds 64 KiB")
    data = loads(content.decode("utf-8"))
    if "image" in data["assets"]:
        path = Path(data["assets"]["image"])
        data["assets"]["image"] = str((Path(filepath).resolve().parent / path).resolve())
    return data


def write(filepath, data):
    data = validate(data)
    destination = Path(filepath)
    if "image" in data["assets"]:
        path = Path(data["assets"]["image"])
        if path.is_absolute():
            try:
                data["assets"]["image"] = Path(
                    os.path.relpath(path, destination.resolve().parent)
                ).as_posix()
            except ValueError:  # Different Windows drives: retain the absolute reference.
                pass
    content = dumps(data)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=destination.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
