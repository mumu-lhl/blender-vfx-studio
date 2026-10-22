import copy
import json
import tempfile
import unittest
from pathlib import Path

from blender_vfx_studio import presets
from blender_vfx_studio.parameters import preset_parameters_for


def sample():
    return {
        "format_version": 2,
        "assets": {},
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

    def test_historical_v1_ring_migrates_without_mutating_input(self):
        path = Path(__file__).parent / "fixtures/ring-preset-v1.json"
        historical = json.loads(path.read_text())
        before = copy.deepcopy(historical)
        migrated = presets.validate(historical)
        self.assertEqual(historical, before)
        self.assertEqual(migrated["format_version"], 2)
        self.assertEqual(migrated["assets"], {})
        self.assertEqual(migrated["parameters"], before["parameters"])
        self.assertEqual(presets.loads(presets.dumps(migrated)), migrated)
        historical["module"] = "flipbook.atlas"
        with self.assertRaisesRegex(ValueError, "legacy"):
            presets.validate(historical)

    def test_flipbook_assets_integer_parameters_and_relative_paths(self):
        data = dict(
            sample(),
            module="flipbook.atlas",
            assets={"image": "atlas.png"},
            parameters={
                key: spec[0] for key, spec in preset_parameters_for("flipbook.atlas").items()
            },
        )
        self.assertEqual(presets.loads(presets.dumps(data)), data)
        for key, value in [
            ("columns", 2.5),
            ("rows", True),
            ("first_frame", -1),
            ("last_frame", 65536),
            ("opacity", 1.5),
        ]:
            invalid = copy.deepcopy(data)
            invalid["parameters"][key] = value
            with self.assertRaises(ValueError):
                presets.validate(invalid)
        for assets in [
            {},
            {"image": ""},
            {"image": []},
            {"image": "bad\npath"},
            {"image": "atlas.png", "script": "exec"},
        ]:
            with self.assertRaises(ValueError):
                presets.validate(dict(data, assets=assets))
        scratch = Path(__file__).resolve().parents[1] / "work"
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            directory = Path(directory)
            (directory / "presets").mkdir()
            source = directory / "atlas.png"
            data["assets"]["image"] = str(source)
            before = copy.deepcopy(data)
            path = directory / "presets/effect.json"
            presets.write(path, data)
            self.assertEqual(data, before)
            self.assertEqual(presets.loads(path.read_text())["assets"]["image"], "../atlas.png")
            self.assertEqual(presets.read(path)["assets"]["image"], str(source))

    def test_screen_module_roundtrip_and_asset_isolation(self):
        data = dict(
            sample(),
            module="screen.glare",
            parameters={k: spec[0] for k, spec in preset_parameters_for("screen.glare").items()},
        )
        self.assertEqual(presets.loads(presets.dumps(data)), data)
        with self.assertRaises(ValueError):
            presets.validate(dict(data, assets={"image": "unused.png"}))
        invalid = copy.deepcopy(data)
        invalid["parameters"]["glow_size"] = 1.01
        with self.assertRaises(ValueError):
            presets.validate(invalid)

    def test_reject_versions_fields_and_types(self):
        for key, value in [
            ("format_version", 0),
            ("format_version", 3),
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
