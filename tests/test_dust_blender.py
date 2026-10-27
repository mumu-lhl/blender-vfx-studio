"""Dust assets preserve native controls, timing, ownership and saved edits."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import assets, composition, core  # noqa: E402
from tools.dust_asset import create  # noqa: E402


def body(root):
    return next(o for o in composition.members(root) if "Rolling Banks" in o.name)


def bounds(member, frame):
    bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
    obj = member.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [tuple(v.co) for v in obj.data.vertices]


class DustTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_relative_start_and_arbitrary_frame_timing(self):
        bpy.context.scene.frame_set(17, subframe=0.5)
        root = create(bpy.context)
        self.assertEqual(root["start"], 17.5)
        self.assertEqual(root["duration"], 32)
        self.assertTrue(all(m["start"] == 17.5 for m in composition.members(root)))
        member = body(root)
        reference = bounds(member, 29.5)
        self.assertTrue(reference)
        self.assertFalse(bounds(member, 16.5))
        self.assertFalse(bounds(member, 49.5))
        self.assertEqual(bounds(member, 29.5), reference)
        root["speed"] = 2.0
        root.update_tag()
        self.assertEqual(bounds(member, 23.5), reference)

    def test_spread_height_and_density_are_editable(self):
        member = body(create(bpy.context))
        before = bounds(member, 12)
        member["expansion"] *= 2
        member["Dust Rise Height"] *= 2
        member.update_tag()
        after = bounds(member, 12)
        self.assertGreater(max(v[0] for v in after), max(v[0] for v in before))
        self.assertGreater(max(v[2] for v in after), max(v[2] for v in before))
        member["Dust Density"] = 0
        member.update_tag()
        self.assertFalse(bounds(member, 12))
        member["Dust Density"] = 8
        member["dissolve"] = 1
        member.update_tag()
        self.assertFalse(bounds(member, 12))

    def test_quality_and_invalid_creation(self):
        counts = []
        for quality in ("LOW", "MEDIUM", "HIGH"):
            bpy.context.scene.frame_set(1)
            root = create(bpy.context, quality)
            self.assertTrue(all(m["vfx_quality"] == quality for m in composition.members(root)))
            grit = next(m for m in composition.members(root) if "Small Grit" in m.name)
            counts.append(grit["count"])
            self.assertTrue(bounds(body(root), 12))
            core.delete(root)
        self.assertEqual(counts, sorted(set(counts)))
        before = set(bpy.data.objects)
        with self.assertRaises(ValueError):
            create(bpy.context, "INVALID")
        self.assertEqual(set(bpy.data.objects), before)

    def test_complete_save_clone_and_safe_delete(self):
        bpy.ops.mesh.primitive_cube_add()
        user = bpy.context.object
        root = create(bpy.context)
        member = body(root)
        member["Dust Rise Height"] = 1.4
        member.update_tag()
        saved = ROOT / "work/test-dust.blend"
        saved.parent.mkdir(exist_ok=True)
        assets.write(saved, root)
        loaded = assets.load(bpy.context, saved)
        clone = core.duplicate(bpy.context, root)
        self.assertFalse(body(loaded).children[0].visible_shadow)
        self.assertFalse(body(clone).children[0].visible_shadow)
        self.assertEqual(body(loaded)["Dust Rise Height"], 1.4)
        self.assertEqual(body(clone)["Dust Rise Height"], 1.4)
        body(clone)["Dust Rise Height"] = 2.2
        body(clone).update_tag()
        self.assertEqual(member["Dust Rise Height"], 1.4)
        self.assertNotEqual(bounds(body(clone), 12), bounds(member, 12))
        core.delete(clone)
        self.assertIn(user, list(bpy.context.scene.objects))
        self.assertTrue(bounds(body(loaded), 12))
        core.delete(root)
        self.assertTrue(bounds(body(loaded), 12))


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(DustTests)
    )
    if not result.wasSuccessful():
        raise SystemExit(1)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    root = create(bpy.context)
    root.name = "Persisted Dust Impact"
    for frame in (7, 16):
        root[f"expected_bounds_{frame}"] = [
            coordinate for vertex in bounds(body(root), frame) for coordinate in vertex
        ]
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/dust-test.blend"))
    print("DUST_NATIVE_BEHAVIOR_OK")
