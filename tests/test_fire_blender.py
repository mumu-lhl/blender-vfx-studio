"""Flames animate with native nodes and preserve independent complete assets."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import assets, composition, core  # noqa: E402
from tools.fire_asset import create  # noqa: E402


def main_member(root):
    return next(m for m in composition.members(root) if "Sculpted Tongues" in m.name)


def points(member, frame):
    bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
    layer = member.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [tuple(v.co) for v in layer.data.vertices]


class FireTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_relative_timing_and_native_seek(self):
        bpy.context.scene.frame_set(17, subframe=0.5)
        root = create(bpy.context)
        self.assertEqual(root["start"], 17.5)
        self.assertEqual(root["duration"], 52)
        flame = main_member(root)
        a = points(flame, 25.5)
        self.assertTrue(a)
        self.assertNotEqual(points(flame, 40.5), a)
        self.assertFalse(points(flame, 16.5))
        self.assertFalse(points(flame, 65.5))
        self.assertEqual(points(flame, 25.5), a)
        root["speed"] = 2
        root.update_tag()
        self.assertEqual(points(flame, 21.5), a)

    def test_shape_controls_and_dissolve(self):
        member = main_member(create(bpy.context))
        before = points(member, 12)
        member["Fire Height"] *= 1.7
        member["width"] *= 1.4
        member.update_tag()
        after = points(member, 12)
        self.assertGreater(max(v[2] for v in after), max(v[2] for v in before) * 1.5)
        self.assertGreater(max(v[0] for v in after), max(v[0] for v in before))
        member["Fire Flow Speed"] = 40
        member.update_tag()
        self.assertNotEqual(points(member, 12), after)
        member["dissolve"] = 1
        member.update_tag()
        self.assertFalse(points(member, 12))

    def test_quality_and_no_mutation_on_invalid_quality(self):
        counts = []
        for quality in ("LOW", "MEDIUM", "HIGH"):
            bpy.context.scene.frame_set(1)
            root = create(bpy.context, quality)
            counts.append(len(points(main_member(root), 12)))
            self.assertTrue(all(m["vfx_quality"] == quality for m in composition.members(root)))
            core.delete(root)
        self.assertEqual(counts, sorted(set(counts)))
        before = set(bpy.data.all_ids)
        with self.assertRaises(ValueError):
            create(bpy.context, "INVALID")
        self.assertEqual(set(bpy.data.all_ids), before)

    def test_complete_asset_edits_clone_and_delete(self):
        bpy.ops.mesh.primitive_cube_add()
        user = bpy.context.object
        root = create(bpy.context)
        flame = main_member(root)
        flame["Fire Curl"] = 0.9
        flame.update_tag()
        expected = points(flame, 12)
        path = ROOT / "work/fire-asset-test.blend"
        path.parent.mkdir(exist_ok=True)
        assets.write(path, root)
        loaded = assets.load(bpy.context, path)
        clone = core.duplicate(bpy.context, loaded)
        self.assertEqual(points(main_member(clone), 12), expected)
        self.assertEqual(points(main_member(loaded), 12), expected)
        main_member(clone)["width"] *= 1.8
        main_member(clone).update_tag()
        self.assertNotEqual(points(main_member(clone), 12), expected)
        self.assertEqual(points(flame, 12), expected)
        for effect in (clone, loaded, root):
            core.delete(effect)
        self.assertIn(user, list(bpy.context.scene.objects))


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(FireTests)
    )
    if not result.wasSuccessful():
        raise RuntimeError("Fire behavior failed")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    root = create(bpy.context)
    root.name = "Persisted Stylized Fire"
    for frame in (8, 20, 44):
        root[f"expected_vertices_{frame}"] = len(points(main_member(root), frame))
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/fire-test.blend"))
    print("FIRE_NATIVE_BEHAVIOR_OK")
