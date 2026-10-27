"""Calligraphic seals preserve native formation, layered release and complete edits."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import assets, composition, core  # noqa: E402
from tools.magic_asset import create  # noqa: E402


def member(root, kind="Seal"):
    return next(m for m in composition.members(root) if m.name.startswith("Magic • " + kind))


def points(obj, frame):
    bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
    mesh = obj.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    return [tuple(v.co) for v in mesh.vertices]


class MagicTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_native_formation_and_later_release(self):
        root = create(bpy.context)
        seal, release = member(root), member(root, "Release")
        self.assertLess(len(points(seal, 8)), len(points(seal, 30)))
        self.assertFalse(points(release, 30))
        self.assertTrue(points(release, 50))
        self.assertGreater(
            max(v[2] for v in points(release, 65)), max(v[2] for v in points(release, 50))
        )
        expected = points(seal, 31)
        self.assertFalse(points(seal, 0))
        self.assertFalse(points(seal, 73))
        self.assertEqual(points(seal, 31), expected)
        root["speed"] = 2
        root.update_tag()
        self.assertEqual(points(seal, 16), expected)

    def test_real_dimensions_spin_and_dissolve(self):
        obj = member(create(bpy.context))
        before = points(obj, 35)
        obj["radius"] *= 1.5
        obj.update_tag()
        after = points(obj, 35)
        self.assertGreater(max(v[0] for v in after), max(v[0] for v in before) * 1.4)
        obj["Sigil Spin"] = 160
        obj.update_tag()
        self.assertNotEqual(points(obj, 35), after)
        obj["fade"] = 0
        obj.update_tag()
        self.assertTrue(points(obj, 72.75))
        obj["dissolve"] = 1
        obj.update_tag()
        self.assertFalse(points(obj, 35))

    def test_quality_and_relative_start(self):
        counts = []
        for quality in ("LOW", "MEDIUM", "HIGH"):
            bpy.context.scene.frame_set(17)
            root = create(bpy.context, quality)
            self.assertEqual(root["start"], 17)
            self.assertEqual(root["duration"], 72)
            self.assertTrue(
                all(
                    m["start"] == 17 and m["vfx_quality"] == quality
                    for m in composition.members(root)
                )
            )
            counts.append(len(points(member(root), 46)))
            core.delete(root)
        self.assertEqual(counts, sorted(set(counts)))
        before = set(bpy.data.all_ids)
        with self.assertRaises(ValueError):
            create(bpy.context, "INVALID")
        self.assertEqual(set(bpy.data.all_ids), before)

    def test_complete_asset_and_independent_edits(self):
        bpy.ops.mesh.primitive_cube_add()
        user = bpy.context.object
        root = create(bpy.context)
        member(root)["Sigil Spin"] = 44
        member(root).update_tag()
        expected = points(member(root), 40)
        path = ROOT / "work/magic-asset-test.blend"
        path.parent.mkdir(exist_ok=True)
        assets.write(path, root)
        loaded = assets.load(bpy.context, path)
        duplicate = core.duplicate(bpy.context, loaded)
        self.assertEqual(points(member(loaded), 40), expected)
        self.assertEqual(points(member(duplicate), 40), expected)
        member(duplicate)["radius"] = 2.1
        member(duplicate).update_tag()
        self.assertNotEqual(points(member(duplicate), 40), expected)
        self.assertEqual(points(member(root), 40), expected)
        for effect in (root, loaded, duplicate):
            core.delete(effect)
        self.assertIn(user, list(bpy.context.scene.objects))


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(MagicTests)
    )
    if not result.wasSuccessful():
        raise RuntimeError("Magic circle behavior failed")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    root = create(bpy.context)
    root.name = "Persisted Magic Circle"
    for frame in (8, 35, 60):
        root[f"expected_vertices_{frame}"] = len(points(member(root), frame))
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/magic-test.blend"))
    print("MAGIC_NATIVE_BEHAVIOR_OK")
