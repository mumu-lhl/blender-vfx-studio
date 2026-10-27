"""Release previews preserve image contents, names and complete checksums."""

import hashlib
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.build_preview_bundle import build


class PreviewBundleTests(unittest.TestCase):
    def test_nested_images_keep_their_paths_and_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = folder / "preview"
            expected = {"examples/fire.png": b"thumbnail", "visual/fire.png": b"HD stage"}
            for name, data in expected.items():
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            (source / "private.blend").write_bytes(b"not a preview image")
            package = build(source, folder / "dist", "0.22.3")
            prefix = "blender-vfx-studio-previews-0.22.3/"
            with zipfile.ZipFile(package) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(
                    set(archive.namelist()),
                    {prefix + name for name in (*expected, "README.md", "SHA256SUMS")},
                )
                checksums = archive.read(prefix + "SHA256SUMS").decode().splitlines()
                self.assertEqual(
                    checksums,
                    [
                        f"{hashlib.sha256(data).hexdigest()}  {name}"
                        for name, data in expected.items()
                    ],
                )
                for name, data in expected.items():
                    self.assertEqual(archive.read(prefix + name), data)
                self.assertIn("不是插件安装包", archive.read(prefix + "README.md").decode())

    def test_build_is_reproducible_despite_file_timestamps(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "preview"
            source.mkdir()
            image = source / "test.png"
            image.write_bytes(b"same original bytes")
            first = build(source, Path(temporary) / "one", "0.22.3").read_bytes()
            os.utime(image, (1000000000, 1000000000))
            second = build(source, Path(temporary) / "two", "0.22.3").read_bytes()
            self.assertEqual(first, second)

    def test_invalid_input_preserves_existing_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            original = folder / "blender-vfx-studio-previews-0.22.3.zip"
            original.write_bytes(b"previous package")
            source = folder / "empty"
            source.mkdir()
            for version in ("0.22.3", "../outside"):
                with self.assertRaises(ValueError):
                    build(source, folder, version)
            self.assertEqual(original.read_bytes(), b"previous package")


if __name__ == "__main__":
    unittest.main()
