"""Incomplete playback evidence must not replace an existing review video."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.combat_video import encode


class VideoPreflightTests(unittest.TestCase):
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
