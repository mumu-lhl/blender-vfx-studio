"""Installer verifies the downloaded bytes before any extraction is attempted."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.fetch_blender import archive_name, checksum, download


class BlenderDownloadTests(unittest.TestCase):
    def test_platform_build_selection_and_unsupported_architecture(self):
        for system, machine, suffix in (
            ("Linux", "x86_64", "linux-x64.tar.xz"),
            ("Windows", "AMD64", "windows-x64.zip"),
            ("Darwin", "arm64", "macos-arm64.dmg"),
        ):
            self.assertEqual(archive_name("5.2.2", system, machine), "blender-5.2.2-" + suffix)
        with self.assertRaises(ValueError):
            archive_name("5.2.2", "Darwin", "x86_64")
        with self.assertRaises(ValueError):
            archive_name("../5.2.2", "Linux", "x86_64")

    def test_checksum_requires_one_exact_valid_entry(self):
        value = "a" * 64
        self.assertEqual(
            checksum(value + "  wanted.zip\n" + "b" * 64 + "  other.zip", "wanted.zip"), value
        )
        for text in (value + "  other.zip", "invalid  wanted.zip", (value + "  wanted.zip\n") * 2):
            with self.assertRaises(ValueError):
                checksum(text, "wanted.zip")

    def test_download_accepts_verified_bytes_and_reuses_verified_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "source.bin", root / "archive.bin"
            source.write_bytes(b"official package fixture")
            expected = hashlib.sha256(source.read_bytes()).hexdigest()
            download(source.as_uri(), target, expected)
            self.assertEqual(target.read_bytes(), source.read_bytes())
            source.unlink()  # A verified cache must not require a second network download.
            download(source.as_uri(), target, expected)

    def test_corrupt_download_preserves_existing_file_and_removes_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "source.bin", root / "archive.bin"
            source.write_bytes(b"corrupt package")
            target.write_bytes(b"previous archive")
            with self.assertRaisesRegex(ValueError, "checksum"):
                download(source.as_uri(), target, "0" * 64)
            self.assertEqual(target.read_bytes(), b"previous archive")
            self.assertFalse(target.with_suffix(".bin.part").exists())


if __name__ == "__main__":
    unittest.main()
