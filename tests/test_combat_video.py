"""Incomplete playback evidence must not replace an existing review video."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.combat_review import build
from tools.combat_video import encode, sequence_digest


class VideoPreflightTests(unittest.TestCase):
    def test_review_page_excludes_stale_or_incomplete_videos(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            folder = base / "dark"
            folder.mkdir()
            settings = {
                "rendered_frames": list(range(1, 37)),
                "fps": 24,
                "resolution": [960, 540],
            }
            manifest = folder / "render-settings.json"
            manifest.write_text(json.dumps(settings))
            for frame in range(1, 37):
                (folder / f"combat-{frame:04d}.png").write_bytes(b"source image fixture")
            (folder / "combat.mp4").write_bytes(b"movie selection fixture, not decoded here")
            (folder / "video-info.json").write_text(
                json.dumps(
                    {
                        "width": 960,
                        "height": 540,
                        "r_frame_rate": "24/1",
                        "nb_frames": "36",
                        "duration": "1.500000",
                        "source_sha256": sequence_digest(folder),
                    }
                )
            )
            page = build(base)
            self.assertIn("<video controls", page.read_text(encoding="utf-8"))
            self.assertIn("连续播放尚未验收", page.read_text(encoding="utf-8"))
            (folder / "combat-0007.png").write_bytes(b"newly rendered frame")
            self.assertNotIn("<video ", build(base).read_text(encoding="utf-8"))
            settings["rendered_frames"] = [4, 8, 12, 23]
            manifest.write_text(json.dumps(settings))
            self.assertNotIn("<video ", build(base).read_text(encoding="utf-8"))
            manifest.unlink()
            with self.assertRaisesRegex(ValueError, "No completed render records"):
                build(base)

    def test_keyframes_cannot_be_mistaken_for_a_complete_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            movie = folder / "combat.mp4"
            movie.write_bytes(b"previous review video")
            (folder / "render-settings.json").write_text(
                json.dumps(
                    {
                        "rendered_frames": [4, 8, 12, 23],
                        "fps": 24,
                        "resolution": [960, 540],
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "complete 36-frame"):
                encode(folder)
            self.assertEqual(movie.read_bytes(), b"previous review video")

    def test_missing_manifest_or_frame_preserves_the_previous_video(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            movie = folder / "combat.mp4"
            movie.write_bytes(b"previous review video")
            with self.assertRaises(FileNotFoundError):
                encode(folder)
            (folder / "render-settings.json").write_text(
                json.dumps(
                    {
                        "rendered_frames": list(range(1, 37)),
                        "fps": 24,
                        "resolution": [960, 540],
                    }
                )
            )
            with self.assertRaises(FileNotFoundError):
                encode(folder)
            self.assertEqual(movie.read_bytes(), b"previous review video")
