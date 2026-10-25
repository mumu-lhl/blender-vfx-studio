"""Stale render or native evidence must never replace a previous review package."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.handoff_bundle import ROOT, build, check_sources


class HandoffBundleTests(unittest.TestCase):
    def settings(self, folder):
        source = ROOT / "blender_vfx_studio/blender_manifest.toml"
        record = {
            "frames": list(range(1, 61)),
            "saved_frame": 31,
            "portable_render_path": "//renders/handoff-",
            "source_sha256": {
                source.relative_to(ROOT).as_posix(): hashlib.sha256(source.read_bytes()).hexdigest()
            },
        }
        (folder / "review-settings.json").write_text(json.dumps(record))
        return record

    def test_partial_sequence_preserves_the_previous_package(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            record = self.settings(folder)
            record["frames"] = [1, 7, 31, 33, 60]
            (folder / "review-settings.json").write_text(json.dumps(record))
            output = folder / "review.zip"
            output.write_bytes(b"previous package")
            with self.assertRaisesRegex(ValueError, "complete 60-frame"):
                build(folder, output)
            self.assertEqual(output.read_bytes(), b"previous package")

    def test_changed_native_scene_requires_revalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.settings(folder)
            original = b"native scene hash fixture"
            (folder / "native-check.json").write_text(
                json.dumps(
                    {
                        "native_render_verified": True,
                        "frames": [31, 33],
                        "clear_frame": 60,
                        "scene_sha256": hashlib.sha256(original).hexdigest(),
                    }
                )
            )
            (folder / "handoff.blend").write_bytes(b"edited after native comparison")
            output = folder / "review.zip"
            output.write_bytes(b"previous package")
            with self.assertRaisesRegex(ValueError, "current native scene"):
                build(folder, output)
            self.assertEqual(output.read_bytes(), b"previous package")

    def test_generator_mismatch_and_paths_outside_the_checkout_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Generator changed"):
            check_sources({"source_sha256": {"blender_vfx_studio/blender_manifest.toml": "0" * 64}})
        with self.assertRaisesRegex(ValueError, "Generator changed"):
            check_sources({"source_sha256": {"../outside.py": "0" * 64}})
