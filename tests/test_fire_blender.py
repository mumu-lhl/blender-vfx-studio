"""Flames animate with native nodes and preserve independent complete assets."""

import sys
import unittest
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from particle_test_support import camera, render_pixels  # noqa: E402

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

    def test_flow_can_stop_during_sustained_burning_without_changing_the_envelope(self):
        member = main_member(create(bpy.context))
        member["Fire Flow Speed"] = 0
        member.update_tag()
        still = points(member, 12)
        self.assertEqual(points(member, 20), still)
        member["Fire Flow Speed"] = 22
        member.update_tag()
        self.assertNotEqual(points(member, 12), points(member, 20))

    def test_material_flow_stops_with_geometry_and_fade_keeps_its_meaning(self):
        root = create(bpy.context)
        member = main_member(root)
        for other in composition.members(root):
            other.children[0].hide_render = other != member
        camera()
        scene = bpy.context.scene
        scene.camera.location = (4, -6, 3.5)
        scene.camera.rotation_euler = (
            (Vector((0, 0, 1)) - scene.camera.location).to_track_quat("-Z", "Y").to_euler()
        )
        scene.camera.data.ortho_scale = 4
        scene.render.resolution_x = scene.render.resolution_y = 96
        scene.render.dither_intensity = 0
        member["Fire Flow Speed"] = 0
        member.update_tag()
        still = render_pixels(12)
        self.assertEqual(render_pixels(20), still)
        member["Fire Flow Speed"] = 22
        member.update_tag()
        self.assertGreater(sum(abs(a - b) for a, b in zip(render_pixels(12), render_pixels(20))), 1)
        faded = render_pixels(44)
        self.assertGreater(max(faded[0::4]), 0.02, "Late flame wisps must not vanish prematurely")
        member["fade"] = 0
        member.update_tag()
        held = render_pixels(44)
        self.assertGreater(sum(held[0::4]), sum(faded[0::4]) * 1.5)

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
