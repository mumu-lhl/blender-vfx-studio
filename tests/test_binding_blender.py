"""Native object/bone binding without touching target animation."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import binding, core


def world(obj):
    bpy.context.view_layer.update()
    return obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.copy()


def target():
    obj = bpy.data.objects.new("Moving Target", None)
    bpy.context.scene.collection.objects.link(obj)
    for frame, x in ((1, 3), (11, 5)):
        obj.location = (x, 4, 5)
        obj.keyframe_insert(data_path="location", frame=frame)
    bpy.context.scene.frame_set(1)
    return obj


class BindingTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def assertMatrix(self, a, b):
        self.assertLess(
            max(abs(x - y) for row_a, row_b in zip(a, b) for x, y in zip(row_a, row_b)), 1e-5
        )

    def test_object_follow_preserve_transform_unbind_and_target_action(self):
        obj = target()
        action = obj.animation_data.action
        root = core.create(bpy.context)
        root.location = (1, 2, 3)
        root.rotation_euler = (0.2, 0.3, 0.4)
        original = world(root)
        binding.bind(bpy.context, root, obj)
        self.assertMatrix(world(root), original)
        bpy.context.scene.frame_set(11)
        moved = world(root)
        self.assertAlmostEqual(moved.translation.x, 3)
        binding.unbind(bpy.context, root)
        self.assertMatrix(world(root), moved)
        bpy.context.scene.frame_set(1)
        self.assertMatrix(world(root), moved)
        self.assertEqual(obj.animation_data.action, action)
        self.assertEqual(len(obj.constraints), 0)

    def test_bone_follow_rotated_scaled_target_and_duplicate(self):
        bpy.ops.object.armature_add(location=(3, 4, 5), rotation=(0.2, 0.1, 0.3))
        obj = bpy.context.object
        obj.scale = (1.2, 0.8, 1.4)
        bone = obj.pose.bones[0]
        for frame, x in ((1, 0), (11, 2)):
            bone.location.x = x
            bone.keyframe_insert(data_path="location", frame=frame)
        bpy.context.scene.frame_set(1)
        root = core.create(bpy.context)
        root.location = (1, 2, 3)
        original = world(root)
        constraint = binding.bind(bpy.context, root, obj, bone.name)
        self.assertMatrix(world(root), original)
        clone = core.duplicate(bpy.context, root)
        self.assertEqual(binding.managed(clone).target, obj)
        self.assertIsNot(binding.managed(clone), constraint)
        bpy.context.scene.frame_set(11)
        self.assertGreater((world(root).translation - original.translation).length, 1)
        self.assertMatrix(world(root), world(clone))
        binding.unbind(bpy.context, clone)
        clone_world = world(clone)
        bpy.context.scene.frame_set(1)
        self.assertMatrix(world(clone), clone_world)
        core.delete(root)
        self.assertIn(obj.name, bpy.data.objects)
        self.assertEqual(obj.pose.bones[0].name, bone.name)

    def test_invalid_targets_and_cycles_leave_controller_unchanged(self):
        root = core.create(bpy.context)
        obj = target()
        obj.constraints.new("COPY_LOCATION").target = root
        for candidate, bone in (
            (root, ""),
            (root.children[0], ""),
            (obj, ""),
            (None, ""),
            (obj, "Missing"),
        ):
            with self.assertRaises(ValueError):
                binding.bind(bpy.context, root, candidate, bone)
            self.assertEqual(len(root.constraints), 0)
            self.assertNotIn("vfx_binding_constraint", root)
        obj.constraints.clear()
        obj.scale = (0, 1, 1)
        with self.assertRaisesRegex(ValueError, "singular"):
            binding.bind(bpy.context, root, obj)
        screen = core.create_screen(bpy.context)
        with self.assertRaisesRegex(ValueError, "Screen"):
            binding.bind(bpy.context, screen, obj)

    def test_user_constraints_animation_and_renames_are_protected(self):
        root = core.create(bpy.context)
        obj = target()
        user = root.constraints.new("LIMIT_LOCATION")
        binding.bind(bpy.context, root, obj)
        with self.assertRaisesRegex(ValueError, "only"):
            binding.unbind(bpy.context, root)
        self.assertIn(user.name, root.constraints)
        root.constraints.remove(user)
        root.keyframe_insert(data_path="location", frame=1)
        with self.assertRaisesRegex(ValueError, "animation"):
            binding.unbind(bpy.context, root)
        root.animation_data_clear()
        root.keyframe_insert(data_path='["radius"]', frame=1)
        binding.unbind(bpy.context, root)
        self.assertIsNotNone(root.animation_data.action)
        binding.bind(bpy.context, root, obj)
        binding.managed(root).name = "User Rename"
        with self.assertRaisesRegex(ValueError, "renamed"):
            binding.unbind(bpy.context, root)
        self.assertEqual(len(root.constraints), 1)

    def test_operator_and_renamed_targets_use_native_id_references(self):
        obj = target()
        root = core.create(bpy.context)
        self.assertEqual(bpy.ops.vfx_studio.bind(target=obj.name), {"FINISHED"})
        obj.name = "Renamed Target"
        self.assertEqual(binding.managed(root).target, obj)
        self.assertEqual(bpy.ops.vfx_studio.unbind(), {"FINISHED"})
        self.assertNotIn("vfx_binding_constraint", root)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(BindingTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Binding integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
obj = target()
root = core.create(bpy.context)
root.name = "Persisted Bound Ring"
root.location = (1, 2, 3)
binding.bind(bpy.context, root, obj)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/binding.blend"))
print("BINDING_INTEGRATION_OK")
