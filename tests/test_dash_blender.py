"""Pose capture preserves user data and creates portable independent native echoes."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import assets, composition, core, dash  # noqa: E402


def source():
    bpy.ops.mesh.primitive_cube_add(size=0.5)
    obj = bpy.context.object
    obj.name = "User Animated Mesh"
    obj.data.materials.append(bpy.data.materials.new("User Material"))
    obj.shape_key_add(name="Basis")
    pose = obj.shape_key_add(name="User Shape")
    pose.data[6].co.z += 0.7
    for frame, x, value in ((1, -2, 0), (13, 2, 1)):
        obj.location.x = x
        obj.keyframe_insert(data_path="location", frame=frame)
        pose.value = value
        pose.keyframe_insert(data_path="value", frame=frame)
    return obj


def vertices(member, frame):
    bpy.context.scene.frame_set(frame)
    mesh = member.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    return [tuple(v.co) for v in mesh.vertices]


class DashTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_capture_restores_time_and_preserves_source_animation(self):
        obj = source()
        mesh, action, shape_action = (
            obj.data,
            obj.animation_data.action,
            obj.data.shape_keys.animation_data.action,
        )
        bpy.context.scene.frame_set(17, subframe=0.5)
        expected = obj.matrix_world.copy()
        material = obj.data.materials[0]
        root = dash.create(bpy.context, obj, 1, 13)
        self.assertEqual(
            (bpy.context.scene.frame_current, bpy.context.scene.frame_subframe), (17, 0.5)
        )
        self.assertEqual(obj.matrix_world, expected)
        self.assertEqual(
            (obj.data, obj.animation_data.action, obj.data.shape_keys.animation_data.action),
            (mesh, action, shape_action),
        )
        self.assertEqual(obj.data.materials[0], material)
        self.assertIsNone(obj.parent)
        members = composition.members(root)
        self.assertEqual(list(root["vfx_capture_frames"]), [1, 7, 13])
        self.assertNotEqual(vertices(members[0], 14), vertices(members[-1], 14))
        self.assertTrue(all(len(m.children[0].data.vertices) == 8 for m in members))

    def test_native_timing_quality_and_seek(self):
        obj = source()
        for quality, count in (("LOW", 2), ("MEDIUM", 3), ("HIGH", 4)):
            root = dash.create(bpy.context, obj, 1, 13, quality)
            self.assertEqual(root["duration"], 30)
            self.assertEqual(len(composition.members(root)), count)
            member = composition.members(root)[0]
            expected = vertices(member, 4)
            self.assertTrue(expected)
            self.assertFalse(vertices(member, 0))
            self.assertFalse(vertices(member, 31))
            self.assertEqual(vertices(member, 4), expected)
            root["speed"] = 2
            root.update_tag()
            self.assertEqual(vertices(member, 2), expected)
            core.delete(root)

    def test_negative_source_scale_keeps_outward_faces(self):
        obj = source()
        obj.scale.x = -1
        bpy.context.scene.frame_set(1)
        expected = (
            obj.matrix_world.to_3x3().inverted().transposed() @ obj.data.polygons[0].normal
        ).normalized()
        root = dash.create(bpy.context, obj, 1, 13)
        first = composition.members(root)[0].children[0].data.polygons[0].normal
        self.assertGreater(first.dot(expected), 0.99)
        self.assertEqual(obj.scale.x, -1)

    def test_invalid_capture_has_no_data_mutation(self):
        obj = source()
        bpy.context.scene.frame_set(5, subframe=0.5)
        before = set(bpy.data.all_ids)
        for first, last, quality in ((1, 1, "MEDIUM"), (1, 12, "HIGH"), (1, 13, "INVALID")):
            with self.assertRaises(ValueError):
                dash.create(bpy.context, obj, first, last, quality)
        self.assertEqual(set(bpy.data.all_ids), before)
        self.assertEqual(bpy.context.scene.frame_current_final, 5.5)
        obj.hide_render = True
        with self.assertRaises(ValueError):
            dash.create(bpy.context, obj, 1, 13)
        self.assertEqual(set(bpy.data.all_ids), before)
        self.assertEqual(bpy.context.scene.frame_current_final, 5.5)

    def test_complete_assets_do_not_need_source_and_delete_is_safe(self):
        obj = source()
        root = dash.create(bpy.context, obj, 1, 13)
        path = ROOT / "work/dash-asset-test.blend"
        assets.write(path, root)
        loaded = assets.load(bpy.context, path)
        clone = core.duplicate(bpy.context, loaded)
        a, b = composition.members(loaded)[0], composition.members(clone)[0]
        original = a.children[0].data.vertices[0].co.copy()
        b.children[0].data.vertices[0].co.x += 0.5
        b.children[0].data.update()
        self.assertEqual(a.children[0].data.vertices[0].co, original)
        core.delete(root)
        core.delete(clone)
        self.assertIn(obj, list(bpy.context.scene.objects))
        bpy.data.objects.remove(obj, do_unlink=True)
        self.assertTrue(vertices(a, 12))
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/dash-test.blend"))


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(DashTests)
    )
    if not result.wasSuccessful():
        raise RuntimeError("Dash capture behavior failed")
