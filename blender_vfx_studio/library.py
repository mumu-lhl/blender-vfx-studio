"""Bounded parameter preset library; file access never executes preset content."""

import uuid
from dataclasses import dataclass
from pathlib import Path

from . import presets

MAX_ENTRIES = 256


@dataclass(frozen=True)
class Entry:
    key: str
    name: str
    module: str


def path_for(directory, key):
    directory = Path(directory).resolve()
    if not isinstance(key, str) or Path(key).name != key or not key.endswith(".json"):
        raise ValueError("Invalid library entry")
    candidate = directory / key
    if candidate.is_symlink() or candidate.resolve().parent != directory:
        raise ValueError("Library entries must be local files, not symlinks")
    return candidate


def scan(directory):
    directory = Path(directory)
    if not directory.exists():
        return [], []
    entries, errors = [], []
    # Stop on an oversized folder instead of silently offering a partial destructive view.
    paths = []
    for path in directory.iterdir():
        if path.suffix == ".json":
            paths.append(path)
            if len(paths) > MAX_ENTRIES:
                raise ValueError("Preset library exceeds 256 JSON files; archive unused entries")
    for path in paths:
        try:
            data = presets.read(path_for(directory, path.name))
            entries.append(Entry(path.name, data["name"], data["module"]))
        except (ValueError, OSError, UnicodeError) as error:
            errors.append((path.name, str(error)))
    return sorted(entries, key=lambda e: (e.name.casefold(), e.key)), errors


def save(directory, data):
    data = presets.validate(data)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    # Include invalid files in the limit; never overwrite an existing named preset.
    if sum(p.suffix == ".json" for p in directory.iterdir()) >= MAX_ENTRIES:
        raise ValueError("Preset library is full; archive or delete entries first")
    key = uuid.uuid4().hex + ".json"
    presets.write(path_for(directory, key), data)
    return key


def load(directory, key):
    return presets.read(path_for(directory, key))


def remove(directory, key):
    path_for(directory, key).unlink()


def rename(directory, key, name):
    data = load(directory, key)
    data["name"] = name
    presets.write(path_for(directory, key), data)
