import copy
import json
import tempfile
import unittest
from pathlib import Path

from blender_vfx_studio import presets


def sample():
    return {
        "format_version": 1,
        "module": "mesh.ring",
        "asset_version": 1,
        "name": "能量环",
        "quality": "LOW",
        "parameters": {key: spec[0] for key, spec in presets.PRESET_PARAMETERS.items()},
    }


class PresetTests(unittest.TestCase):
    def test_round_trip_and_portable_time(self):
        data = sample()
        self.assertEqual(presets.loads(presets.dumps(data)), data)
        self.assertNotIn("start", data["parameters"])
        self.assertNotIn("vfx_id", presets.dumps(data))

    def test_file_roundtrip_and_invalid_export_preserves_existing_file(self):
        scratch = Path(__file__).resolve().parents[1] / "work"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            path = Path(directory) / "preset.json"
            presets.write(path, sample())
            self.assertEqual(presets.read(path), sample())
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                presets.write(path, {})
            self.assertEqual(path.read_bytes(), before)
            path.write_bytes(b"x" * (presets.MAX_BYTES + 1))
            with self.assertRaises(ValueError):
                presets.read(path)
            path.write_bytes(b"\xff")
            with self.assertRaises(ValueError):
                presets.read(path)

    def test_reject_versions_fields_and_types(self):
        for key, value in [
            ("format_version", 0),
            ("format_version", 2),
            ("format_version", True),
            ("asset_version", 999),
            ("module", "python.exec"),
            ("module", []),
            ("quality", "ULTRA"),
            ("quality", {}),
            ("name", ""),
            ("name", "bad\nname"),
        ]:
            with self.subTest(key=key, value=value):
                data = sample()
                data[key] = value
                with self.assertRaises(ValueError):
                    presets.loads(json.dumps(data))
        for data in [[], {}, dict(sample(), extra=True)]:
            with self.assertRaises(ValueError):
                presets.validate(data)

    def test_reject_invalid_parameters_before_use(self):
        original = sample()
        for key, value in [
            ("duration", 0),
            ("radius", -1),
            ("speed", True),
            ("strength", float("nan")),
            ("strength", float("inf")),
            ("strength", 10**400),
            ("loop", 1),
            ("dissolve", "0.5"),
        ]:
            data = copy.deepcopy(original)
            data["parameters"][key] = value
            with self.subTest(key=key, value=str(value)):
                with self.assertRaises(ValueError):
                    presets.loads(json.dumps(data))
        for change in ("missing", "extra"):
            data = copy.deepcopy(original)
            if change == "missing":
                del data["parameters"]["radius"]
            else:
                data["parameters"]["start"] = 10
            with self.assertRaises(ValueError):
                presets.validate(data)
        self.assertEqual(original, sample())

    def test_reject_oversize_duplicate_and_malformed_json(self):
        for text in [
            '{"format_version":1,"format_version":1}',
            "{invalid}",
            " " * (presets.MAX_BYTES + 1),
            "[" * 2000 + "]" * 2000,
        ]:
            with self.subTest(text=text[:30]):
                with self.assertRaises(ValueError):
                    presets.loads(text)
