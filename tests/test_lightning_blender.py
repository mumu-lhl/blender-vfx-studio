"""Complete lightning keeps native timing, saved edits and independent ownership."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import assets, composition, core  # noqa: E402
from tools.lightning_asset import create  # noqa: E402

WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)


def main_member(root):
    return next(member for member in composition.members(root) if "Main Discharges" in member.name)


def contact_member(root):
    return next(member for member in composition.members(root) if "Contact Corona" in member.name)


def points(member, frame):
    integer = int(frame)
    bpy.context.scene.frame_set(integer, subframe=frame - integer)
    obj = member.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [tuple(vertex.co) for vertex in obj.data.vertices]


class LightningTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_nonfirst_frame_creation_keeps_relative_layer_timing(self):
        bpy.context.scene.frame_set(17, subframe=0.5)
        root = create(bpy.context)
        self.assertEqual(root["start"], 17.5)
        self.assertEqual(root["duration"], 18)
        bolt = main_member(root)
        self.assertTrue(points(bolt, 19.5))
        self.assertFalse(points(bolt, 16.5))
        self.assertTrue(all(17.5 <= member["start"] < 21 for member in composition.members(root)))

    def test_discrete_strikes_and_gaps_follow_group_speed(self):
        root = create(bpy.context)
        bolt = main_member(root)
        for frame in (3, 7, 12):
            self.assertTrue(points(bolt, frame), frame)
        reference = points(bolt, 3)
        for frame in (0, 1, 6, 10, 17, 19):
            self.assertFalse(points(bolt, frame), frame)
        root["speed"] = 2.0
        root.update_tag()
        self.assertEqual(points(bolt, 2), reference)

    def test_branch_reach_preserves_trunk_and_dissolve_works(self):
        root = create(bpy.context)
        bolt = main_member(root)

        def snapshot():
            bpy.context.scene.frame_set(4)
            mesh = bolt.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            return [
                (tuple(v.co), part.value > 0)
                for v, part in zip(mesh.vertices, mesh.attributes["bolt_branch"].data)
            ]

        before = snapshot()
        tree = bolt.children[0].modifiers[0].node_group
        tree.nodes["Branch Reach"].outputs[0].default_value = 1.6
        after = snapshot()
        self.assertEqual(
            [p for p, fork in before if not fork], [p for p, fork in after if not fork]
        )
        self.assertNotEqual([p for p, fork in before if fork], [p for p, fork in after if fork])
        bolt["dissolve"] = 0.8
        bolt.update_tag()
        self.assertLess(len(points(bolt, 4)), len(after))
        bolt["dissolve"] = 1.0
        bolt.update_tag()
        self.assertFalse(points(bolt, 4))

    def test_contact_returns_repeat_and_clear_in_each_discharge_gap(self):
        root = create(bpy.context)
        contact = contact_member(root)
        for frame in (3, 8, 12):
            self.assertTrue(points(contact, frame), frame)
        reference = points(contact, 3)
        for frame in (0, 1, 2, 6, 10, 17, 19):
            self.assertFalse(points(contact, frame), frame)
        root["speed"] = 2.0
        root.update_tag()
        self.assertEqual(points(contact, 2), reference)
        root["speed"], root["duration"] = 1.0, 36.0
        root.update_tag()
        self.assertEqual(points(contact, 5), reference)

    def test_contact_shape_controls_preserve_the_main_bolt(self):
        root = create(bpy.context)
        contact = contact_member(root)
        reference = points(contact, 3)
        bolt = points(main_member(root), 3)
        for key, value in (("radius", 0.3), ("expansion", 0.0), ("width", 0.1)):
            previous = contact[key]
            contact[key] = value
            contact.update_tag()
            self.assertNotEqual(points(contact, 3), reference, key)
            self.assertEqual(points(main_member(root), 3), bolt)
            contact[key] = previous
            contact.update_tag()
        contact["width"] = 0.0
        contact.update_tag()
        bpy.context.scene.frame_set(3)
        mesh = contact.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        self.assertLess(sum(face.area for face in mesh.polygons), 1e-8)
        contact["dissolve"] = 1.0
        contact.update_tag()
        self.assertFalse(points(contact, 3))

    def test_quality_profiles_change_shape_detail(self):
        counts = []
        for quality in ("LOW", "MEDIUM", "HIGH"):
            bpy.context.scene.frame_set(1)
            root = create(bpy.context, quality)
            self.assertTrue(
                all(member["vfx_quality"] == quality for member in composition.members(root))
            )
            counts.append(len(points(main_member(root), 4)))
            core.delete(root)
        self.assertLess(counts[0], counts[1])
        self.assertLess(counts[1], counts[2])

    def test_asset_copy_and_delete_preserve_user_mesh(self):
        bpy.ops.mesh.primitive_cube_add()
        user = bpy.context.object
        original_mesh = user.data
        root = create(bpy.context)
        bolt = main_member(root)
        bolt.children[0].modifiers[0].node_group.nodes["Bolt Length"].outputs[0].default_value = 4.2
        expected = points(bolt, 4)
        expected_contact = points(contact_member(root), 8)
        path = WORK / "lightning-asset.blend"
        assets.write(path, root)
        loaded = assets.load(bpy.context, path)
        self.assertEqual(points(main_member(loaded), 4), expected)
        self.assertEqual(points(contact_member(loaded), 8), expected_contact)
        clone = core.duplicate(bpy.context, loaded)
        self.assertNotEqual(clone["vfx_id"], root["vfx_id"])
        self.assertEqual(points(main_member(clone), 4), expected)
        self.assertEqual(points(contact_member(clone), 8), expected_contact)
        main_member(clone)["radius"] = 1.2
        main_member(clone).update_tag()
        self.assertNotEqual(points(main_member(clone), 4), expected)
        self.assertEqual(points(bolt, 4), expected)
        for effect in (clone, loaded, root):
            core.delete(effect)
        self.assertIn(user.name, bpy.context.scene.objects)
        self.assertEqual(user.data, original_mesh)


result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(LightningTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Lightning asset behavior failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = create(bpy.context)
root.name = "Persisted Lightning Strike"
for frame in (3, 7, 12):
    root[f"expected_vertices_{frame}"] = len(points(main_member(root), frame))
for frame in (3, 8, 12):
    root[f"expected_contact_{frame}"] = [
        c for point in points(contact_member(root), frame) for c in point
    ]
bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "lightning-test.blend"))
print("LIGHTNING_NATIVE_BEHAVIOR_OK")
