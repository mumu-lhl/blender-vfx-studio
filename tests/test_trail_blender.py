"""Real animation sampling, native interpolation and non-destructive lifecycle."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import core, trail

WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)


def source():
    obj = bpy.data.objects.new("Animated Source", None)
    bpy.context.scene.collection.objects.link(obj)
    for frame, x in ((1, 0), (11, 2), (21, 8)):
        obj.location = (x, 0, 0)
        obj.keyframe_insert(data_path="location", frame=frame)
    return obj


def evaluated(root, frame, subframe=0):
    bpy.context.scene.frame_set(frame, subframe=subframe)
    return trail.layer_for(root).evaluated_get(bpy.context.evaluated_depsgraph_get()).data


def update(root, **values):
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


class TrailTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_sampling_preserves_source_action_frame_and_selection(self):
        obj = source()
        action = obj.animation_data.action
        bpy.context.scene.frame_set(7, subframe=0.25)
        original = obj.matrix_world.copy()
        points = trail.sample(bpy.context, obj, "", 1, 21, 5)
        self.assertEqual(len(points), 5)
        self.assertAlmostEqual(points[2][0], 2)
        self.assertEqual(obj.animation_data.action, action)
        self.assertEqual(bpy.context.scene.frame_current, 7)
        self.assertEqual(bpy.context.scene.frame_subframe, 0.25)
        self.assertEqual(obj.matrix_world, original)

    def test_time_interpolation_tail_retime_loop_and_width(self):
        root = trail.create(bpy.context, source(), first=1, last=21, step=5)
        update(root, length=0.5, width=0.4)
        for frame in (16, 6, 11):
            result = evaluated(root, frame, 0.5)
            # Expected head is linear interpolation of the two baked samples in time,
            # deliberately different from the source Bezier curve and arc-length reveal.
            sample = (frame + 0.5 - 1) / 5
            i = int(sample)
            data = trail.layer_for(root).data
            expected = data.vertices[2 * i].co.lerp(data.vertices[2 * (i + 1)].co, sample - i)
            head = (result.vertices[-2].co + result.vertices[-1].co) * 0.5
            self.assertLess((head - expected).length, 1e-5)
            self.assertAlmostEqual(
                (result.vertices[-2].co - result.vertices[-1].co).length, 0.4, places=5
            )
        original = [tuple(v.co) for v in evaluated(root, 11).vertices]
        update(root, speed=2.0)
        self.assertEqual([tuple(v.co) for v in evaluated(root, 6).vertices], original)
        self.assertEqual(len(evaluated(root, 11).vertices), 0)
        self.assertEqual(len(evaluated(root, 0).vertices), 0)
        update(root, loop=True)
        self.assertGreater(len(evaluated(root, 11).vertices), 0)

    def test_bone_head_sampling_uses_evaluated_world_transform(self):
        bpy.ops.object.armature_add(location=(3, 4, 5))
        obj = bpy.context.object
        bone = obj.pose.bones[0]
        for frame, x in ((1, 0), (11, 2)):
            bone.location.x = x
            bone.keyframe_insert(data_path="location", frame=frame)
        points = trail.sample(bpy.context, obj, bone.name, 1, 11, 5)
        self.assertEqual(tuple(round(v, 5) for v in points[0]), (3, 4, 5))
        self.assertEqual(tuple(round(v, 5) for v in points[-1]), (5, 4, 5))
        self.assertEqual(bone.rotation_mode, "QUATERNION")

    def test_validation_happens_before_data_creation(self):
        obj = source()
        counts = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.node_groups))
        for first, last, step, bone in (
            (1, 21, 0, ""),
            (1, 21, 3, ""),
            (1, 9999, 1, ""),
            (1, 21, 1, "Missing"),
        ):
            with self.assertRaises(ValueError):
                trail.create(bpy.context, obj, bone, first, last, step)
            self.assertEqual(
                counts, (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.node_groups))
            )
        self.assertEqual(bpy.context.scene.frame_current, 1)

    def test_duplicate_delete_preserves_source_and_manual_nodes(self):
        obj = source()
        root = trail.create(bpy.context, obj, first=1, last=21)
        layer = trail.layer_for(root)
        layer.modifiers[0].node_group.nodes.new("ShaderNodeValue").name = "User Note"
        clone = core.duplicate(bpy.context, root)
        self.assertEqual(clone["vfx_source"], obj)
        self.assertIsNot(trail.layer_for(clone).data, layer.data)
        self.assertIn("User Note", trail.layer_for(clone).modifiers[0].node_group.nodes)
        update(clone, width=1.0)
        self.assertEqual(root["width"], 0.2)
        core.delete(root)
        self.assertGreater(len(evaluated(clone, 11).vertices), 0)
        core.delete(clone)
        self.assertIn(obj.name, bpy.data.objects)
        self.assertIsNotNone(obj.animation_data.action)
        self.assertEqual(len(bpy.data.meshes), 0)
        self.assertEqual(len(bpy.data.node_groups), 0)
        with self.assertRaises(ValueError):
            core.preset_snapshot(trail.create(bpy.context, obj, first=1, last=21))

    def test_explicit_rebake_preserves_nodes_and_current_frame(self):
        obj = source()
        root = trail.create(bpy.context, obj, first=1, last=21, step=5)
        layer = trail.layer_for(root)
        group = layer.modifiers[0].node_group
        layer.data.vertices[0].co.z = 99
        self.assertEqual(layer.data.vertices[0].co.z, 99)
        bpy.context.scene.frame_set(9, subframe=0.5)
        trail.rebake(bpy.context, root)
        self.assertEqual(layer.data.vertices[0].co.z, 0)
        self.assertEqual(layer.modifiers[0].node_group, group)
        self.assertEqual(bpy.context.scene.frame_current, 9)
        self.assertEqual(bpy.context.scene.frame_subframe, 0.5)
        shared = bpy.data.objects.new("External", layer.data)
        bpy.context.scene.collection.objects.link(shared)
        with self.assertRaisesRegex(ValueError, "private"):
            trail.rebake(bpy.context, root)
        with self.assertRaisesRegex(ValueError, "shared"):
            core.delete(root)

    def test_operator_and_simple_native_drivers(self):
        obj = source()
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        self.assertEqual(bpy.ops.vfx_studio.create_trail(first=1, last=21, step=5), {"FINISHED"})
        root = bpy.context.object
        evaluated(root, 11)
        for data in (
            trail.layer_for(root).modifiers[0].node_group,
            trail.layer_for(root).data.materials[0].node_tree,
        ):
            self.assertTrue(
                all(
                    c.driver.is_valid and c.driver.is_simple_expression
                    for c in data.animation_data.drivers
                )
            )
        bpy.data.objects.remove(obj, do_unlink=True)
        self.assertGreater(len(evaluated(root, 11).vertices), 0)
        with self.assertRaisesRegex(ValueError, "source"):
            trail.rebake(bpy.context, root)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(TrailTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Trail integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = trail.create(bpy.context, source(), first=1, last=21, step=5)
root.name = "Persisted Ribbon"
update(root, length=0.5, width=0.4)
bpy.data.objects.remove(root["vfx_source"], do_unlink=True)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "trail.blend"))
print("TRAIL_INTEGRATION_OK")
