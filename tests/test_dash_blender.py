"""Pose capture preserves user data and creates portable independent native echoes."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from particle_test_support import camera, render_pixels  # noqa: E402

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


def timing_values(member):
    bpy.context.view_layer.update()
    evaluated = member.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return {key: float(evaluated[key]) for key in ("start", "duration", "speed")}


class DashTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_late_echo_surface_respects_opacity_fade_and_complete_asset_save(self):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.7)
        obj = bpy.context.object
        for frame, x in ((1, 0), (5, 2)):
            obj.location.x = x
            obj.keyframe_insert(data_path="location", frame=frame)
        root = dash.create(bpy.context, obj, 1, 5, count=2)
        obj.hide_render = True
        members = composition.members(root)
        first = members[0]
        for other in members[1:]:
            other.children[0].hide_render = True
        camera()
        scene = bpy.context.scene
        scene.render.film_transparent = True
        scene.render.resolution_x = scene.render.resolution_y = 64
        faded = render_pixels(15)
        self.assertGreater(sum(faded[3::4]), 1)
        first["opacity"] = 0.0
        first.update_tag()
        self.assertEqual(sum(render_pixels(15)[3::4]), 0)
        first["opacity"], first["fade"] = 0.82, 0.0
        first.update_tag()
        held = render_pixels(15)
        self.assertGreater(sum(held[3::4]), sum(faded[3::4]) * 1.2)
        first["dissolve"] = 1.0
        first.update_tag()
        self.assertEqual(sum(render_pixels(15)[3::4]), 0)
        first["dissolve"] = 0.04
        first["color_0"], first["color_1"], first["color_2"] = 0.8, 0.1, 0.02
        first.update_tag()
        warm = render_pixels(15)
        self.assertGreater(sum(warm[0::4]), sum(warm[2::4]))
        path = ROOT / "work/dash-surface-test.blend"
        assets.write(path, root)
        core.delete(root)
        assets.load(bpy.context, path)
        self.assertEqual(render_pixels(15), warm)

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

    def test_explicit_count_samples_subframes_without_changing_source_detail(self):
        obj = source()
        scene = bpy.context.scene
        scene.frame_set(5, subframe=0.5)
        root = dash.create(bpy.context, obj, 1, 12, "LOW", count=5)
        self.assertEqual(scene.frame_current_final, 5.5)
        frames = list(root["vfx_capture_frames"])
        self.assertEqual(frames, [1, 3.75, 6.5, 9.25, 12])
        members = composition.members(root)
        self.assertEqual(len(members), 5)
        for member, frame in zip(members, frames):
            scene.frame_set(int(frame), subframe=frame % 1)
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            expected = [evaluated.matrix_world @ v.co for v in evaluated.data.vertices]
            layer = member.children[0]
            actual = [layer.matrix_world @ v.co for v in layer.data.vertices]
            self.assertEqual(len(actual), len(expected))
            for a, b in zip(actual, expected):
                self.assertLess((a - b).length, 1e-5)
        bpy.data.objects.remove(obj, do_unlink=True)
        self.assertTrue(vertices(members[-1], 12))
        self.assertFalse(vertices(members[-1], 30))

    def test_capture_operator_uses_count_instead_of_quality(self):
        import blender_vfx_studio as addon

        addon.register()
        try:
            source()
            bpy.context.scene.frame_set(5, subframe=0.5)
            self.assertEqual(
                bpy.ops.vfx_studio.capture_dash(first=1, last=12, count=5, tail=9), {"FINISHED"}
            )
            root = bpy.context.object
            self.assertEqual(root["duration"], 20)
            self.assertEqual(len(composition.members(root)), 5)
            self.assertEqual(bpy.context.scene.frame_current_final, 5.5)
        finally:
            addon.unregister()

    def test_negative_subframes_use_the_correct_pose_time(self):
        obj = source()
        root = dash.create(bpy.context, obj, -1, 2, count=5)
        self.assertEqual(list(root["vfx_capture_frames"]), [-1, -0.25, 0.5, 1.25, 2])

    def test_invalid_capture_has_no_data_mutation(self):
        obj = source()
        bpy.context.scene.frame_set(5, subframe=0.5)
        before = set(bpy.data.all_ids)
        for first, last, quality in ((1, 1, "MEDIUM"), (13, 1, "HIGH"), (1, 13, "INVALID")):
            with self.assertRaises(ValueError):
                dash.create(bpy.context, obj, first, last, quality)
        for count in (0, 1, 33, True, 3.5):
            with self.assertRaises(ValueError):
                dash.create(bpy.context, obj, 1, 12, count=count)
        self.assertEqual(set(bpy.data.all_ids), before)
        self.assertEqual(bpy.context.scene.frame_current_final, 5.5)
        obj.hide_render = True
        with self.assertRaises(ValueError):
            dash.create(bpy.context, obj, 1, 13)
        self.assertEqual(set(bpy.data.all_ids), before)
        self.assertEqual(bpy.context.scene.frame_current_final, 5.5)

    def test_edit_tail_keeps_pose_entries_and_native_data_without_source(self):
        obj = source()
        root = dash.create(bpy.context, obj, 1, 13)
        members = sorted(composition.members(root), key=lambda m: m["vfx_capture_frame"])
        bpy.context.scene.frame_set(17, subframe=0.5)
        ids = [
            (
                m.children[0].data,
                m.children[0].data.materials[0],
                m.children[0].modifiers[0].node_group,
            )
            for m in members
        ]
        geometry = [[tuple(v.co) for v in mesh.vertices] for mesh, _, _ in ids]
        ids[0][2].nodes.new("ShaderNodeValue").name = "Artist Detail"
        bpy.data.objects.remove(obj, do_unlink=True)
        dash.set_tail(bpy.context, root, 30)
        self.assertEqual(bpy.context.scene.frame_current_final, 17.5)
        self.assertEqual(root["duration"], 42)
        self.assertAlmostEqual(dash.tail_frames(root), 30)
        for m, expected, points in zip(members, ids, geometry):
            layer = m.children[0]
            self.assertEqual(
                (layer.data, layer.data.materials[0], layer.modifiers[0].node_group), expected
            )
            self.assertEqual([tuple(v.co) for v in layer.data.vertices], points)
            evaluated = timing_values(m)
            self.assertAlmostEqual(evaluated["start"], m["vfx_capture_frame"], places=5)
            self.assertAlmostEqual(evaluated["duration"], 30, places=5)
        self.assertIn("Artist Detail", ids[0][2].nodes)
        self.assertTrue(vertices(members[0], 25))
        dash.set_tail(bpy.context, root, 3)
        self.assertFalse(vertices(members[0], 5))
        self.assertTrue(vertices(members[-1], 14))
        self.assertFalse(vertices(members[-1], 16))

    def test_edit_tail_preserves_current_retimed_spacing_and_local_speeds(self):
        root = dash.create(bpy.context, source(), 1, 13)
        members = sorted(composition.members(root), key=lambda m: m["vfx_capture_frame"])
        root["start"], root["duration"], root["speed"] = 11.0, 60.0, 2.0
        members[1]["vfx_local_speed"], members[2]["vfx_local_speed"] = 0.5, 2.0
        for member in members:
            member.update_tag()
        root.update_tag()
        bpy.context.view_layer.update()
        starts = [timing_values(m)["start"] for m in members]
        dash.set_tail(bpy.context, root, 12)
        self.assertAlmostEqual(root["duration"], 36)
        self.assertEqual([timing_values(m)["start"] for m in members], starts)
        self.assertEqual([timing_values(m)["speed"] for m in members], [2, 1, 4])
        self.assertTrue(all(abs(timing_values(m)["duration"] - 12) < 1e-5 for m in members))
        root["loop"] = True
        root.update_tag()
        self.assertEqual(vertices(members[1], 18), vertices(members[1], 36))

    def test_edit_tail_keeps_transform_animation(self):
        root = dash.create(bpy.context, source(), 1, 13)
        member = composition.members(root)[0]
        member.location.x = 1
        member.keyframe_insert(data_path="location", frame=1)
        member.location.x = 4
        member.keyframe_insert(data_path="location", frame=20)
        action = member.animation_data.action
        dash.set_tail(bpy.context, root, 24)
        self.assertEqual(member.animation_data.action, action)
        bpy.context.scene.frame_set(20)
        self.assertEqual(member.location.x, 4)

    def test_edit_tail_rejects_invalid_and_authored_timing_without_changes(self):
        root = dash.create(bpy.context, source(), 1, 13)
        members = composition.members(root)

        def timing():
            return root["duration"], [
                (m["vfx_offset_ratio"], m["vfx_duration_ratio"]) for m in members
            ]

        before = timing()
        for value in (0, -1, True, float("nan"), float("inf"), 100000):
            with self.assertRaises(ValueError):
                dash.set_tail(bpy.context, root, value)
            self.assertEqual(timing(), before)
        root.keyframe_insert(data_path='["duration"]', frame=1)
        with self.assertRaisesRegex(ValueError, "Duration is animated"):
            dash.set_tail(bpy.context, root, 12)
        self.assertEqual(timing(), before)
        root.animation_data_clear()
        member = members[0]
        member.keyframe_insert(data_path='["vfx_offset_ratio"]', frame=1)
        with self.assertRaisesRegex(ValueError, "ratios or Local Speed are animated"):
            dash.set_tail(bpy.context, root, 12)
        self.assertEqual(timing(), before)
        member.animation_data.action = None
        curve = next(c for c in member.animation_data.drivers if c.data_path == '["duration"]')
        curve.driver.expression = "7"
        with self.assertRaisesRegex(ValueError, "timing drivers were edited"):
            dash.set_tail(bpy.context, root, 12)
        self.assertEqual(timing(), before)

    def test_edit_tail_operator_and_complete_assets_stay_independent(self):
        import blender_vfx_studio as addon

        root = dash.create(bpy.context, source(), 1, 13)
        addon.register()
        try:
            self.assertEqual(bpy.ops.vfx_studio.set_echo_tail(tail=24), {"FINISHED"})
        finally:
            addon.unregister()
        path = ROOT / "work/edited-tail.blend"
        assets.write(path, root)
        loaded = assets.load(bpy.context, path)
        dash.set_tail(bpy.context, loaded, 9)
        self.assertAlmostEqual(dash.tail_frames(loaded), 9)
        self.assertAlmostEqual(dash.tail_frames(root), 24)

    def test_complete_assets_do_not_need_source_and_delete_is_safe(self):
        obj = source()
        root = dash.create(bpy.context, obj, 1, 12, count=5)
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
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = source()
    root = dash.create(bpy.context, obj, 1, 12, count=5)
    root.name = "Persisted Edited Echo Tail"
    dash.set_tail(bpy.context, root, 24)
    bpy.data.objects.remove(obj, do_unlink=True)
    for frame in (7, 19, 35, 36):
        root[f"expected_tail_points_{frame}"] = [
            component
            for member in composition.members(root)
            for point in vertices(member, frame)
            for component in point
        ] or [0.0]
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/dash-tail-native.blend"))
