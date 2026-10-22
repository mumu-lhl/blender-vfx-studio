"""Library filesystem behavior with isolated directories, never user preferences."""

import tempfile
import unittest
from pathlib import Path

from blender_vfx_studio import library, presets

FIXTURE = Path(__file__).parent / "fixtures/ring-preset-v1.json"


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "library"
        self.data = presets.read(FIXTURE)

    def test_roundtrip_duplicate_names_and_missing_directory(self):
        self.assertEqual(library.scan(self.directory), ([], []))
        a = library.save(self.directory, self.data)
        b = library.save(self.directory, self.data)
        self.assertNotEqual(a, b)
        entries, errors = library.scan(self.directory)
        self.assertEqual(len(entries), 2)
        self.assertEqual(errors, [])
        self.assertEqual(library.load(self.directory, a), self.data)
        library.remove(self.directory, a)
        self.assertEqual(len(library.scan(self.directory)[0]), 1)
        self.assertTrue((self.directory / b).exists())

    def test_invalid_files_are_reported_without_hiding_valid_entries(self):
        key = library.save(self.directory, self.data)
        (self.directory / "bad.json").write_text("not json")
        (self.directory / "huge.json").write_text(" " * (presets.MAX_BYTES + 1))
        (self.directory / "binary.json").write_bytes(b"\xff")
        entries, errors = library.scan(self.directory)
        self.assertEqual([e.key for e in entries], [key])
        self.assertEqual({e[0] for e in errors}, {"bad.json", "huge.json", "binary.json"})

    def test_traversal_and_symlinks_cannot_read_or_delete_external_files(self):
        self.directory.mkdir()
        external = self.directory.parent / "external.json"
        presets.write(external, self.data)
        for key in ("../external.json", str(external), "", "x.txt"):
            for operation in (library.load, library.remove):
                with self.assertRaises(ValueError):
                    operation(self.directory, key)
        (self.directory / "link.json").symlink_to(external)
        for operation in (library.load, library.remove):
            with self.assertRaises(ValueError):
                operation(self.directory, "link.json")
        self.assertTrue(external.exists())
        self.assertEqual(len(library.scan(self.directory)[1]), 1)

    def test_capacity_includes_invalid_entries(self):
        self.directory.mkdir()
        for i in range(library.MAX_ENTRIES):
            (self.directory / f"{i}.json").write_text("invalid")
        with self.assertRaisesRegex(ValueError, "full"):
            library.save(self.directory, self.data)
        (self.directory / "extra.json").write_text("invalid")
        with self.assertRaisesRegex(ValueError, "exceeds"):
            library.scan(self.directory)

    def test_rename_is_validated_and_atomic(self):
        key = library.save(self.directory, self.data)
        library.rename(self.directory, key, "Energy A")
        self.assertEqual(library.load(self.directory, key)["name"], "Energy A")
        with self.assertRaises(ValueError):
            library.rename(self.directory, key, "")
        self.assertEqual(library.load(self.directory, key)["name"], "Energy A")

    def test_invalid_save_leaves_existing_library_untouched(self):
        key = library.save(self.directory, self.data)
        original = (self.directory / key).read_bytes()
        data = dict(self.data, format_version=100)
        with self.assertRaises(ValueError):
            library.save(self.directory, data)
        self.assertEqual((self.directory / key).read_bytes(), original)
        self.assertEqual(len(list(self.directory.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
