"""Shared native timing, group isolation and deletion preflight."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import composition, core, nodes


def update(root, **values):
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


def visible(root, frame):
    bpy.context.scene.frame_set(frame)
    layer = root.children[0]
    return bool(layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)


def create():
    a = core.create(bpy.context)
    b = core.create_particle(bpy.context)
    update(b, start=7.0, duration=12.0)
    return composition.create(bpy.context, [a, b]), a, b


class CompositionTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_shared_timing_offset_speed_and_group_loop(self):
        group, a, b = create()
        self.assertEqual(group["duration"], 24)
        self.assertEqual((a["start"], b["start"], b["duration"]), (1, 7, 12))
        update(group, duration=48.0)
        self.assertEqual((b["start"], b["duration"]), (13, 24))
        update(group, speed=2.0)
        self.assertEqual((b["start"], b["speed"]), (7, 2))
        update(group, duration=24.0, speed=1.0, loop=True)
        for frame, expected in (
            (7, True),
            (19, False),
            (25, False),
            (31, True),
            (43, False),
            (0, False),
        ):
            self.assertEqual(visible(b, frame), expected, frame)
        visible(a, 11)
        self.assertTrue(
            all(
                c.driver.is_valid and c.driver.is_simple_expression
                for c in b.animation_data.drivers
            )
        )

    def test_world_transform_preserved_and_single_member_detach(self):
        a, b = core.create(bpy.context), core.create_particle(bpy.context)
        a.location = (2, 3, 4)
        a.rotation_euler = (0.2, 0.3, 0.4)
        bpy.context.view_layer.update()
        before = a.matrix_world.copy()
        group = composition.create(bpy.context, [a, b])
        self.assertLess(
            max(abs(x - y) for ra, rb in zip(a.matrix_world, before) for x, y in zip(ra, rb)), 1e-5
        )
        group.location.x = 5
        bpy.context.view_layer.update()
        world = a.matrix_world.copy()
        composition.detach(bpy.context, a)
        self.assertIsNone(a.parent)
        self.assertLess(
            max(abs(x - y) for ra, rb in zip(a.matrix_world, world) for x, y in zip(ra, rb)), 1e-5
        )
        update(group, speed=3.0)
        self.assertEqual(a["speed"], 1)
        self.assertEqual(composition.members(group), [b])

    def test_whole_group_and_single_layer_duplicates_are_independent(self):
        group, a, b = create()
        a.keyframe_insert(data_path='["radius"]', frame=1)
        user = a.children[0].data.materials[0].node_tree.nodes.new("ShaderNodeValue")
        user.name = "User Group Duration"
        nodes.drive(user.outputs[0], "default_value", group, "p", {"p": "duration"})
        clone = core.duplicate(bpy.context, group)
        children = composition.members(clone)
        self.assertEqual(len(children), 2)
        self.assertTrue(all(child.parent == clone for child in children))
        update(clone, speed=2.0, duration=48.0)
        ring_copy = next(c for c in children if c["vfx_module"] == "mesh.ring")
        copied_user = ring_copy.children[0].data.materials[0].node_tree.nodes["User Group Duration"]
        self.assertEqual(copied_user.outputs[0].default_value, 48)
        self.assertEqual(user.outputs[0].default_value, 24)
        self.assertEqual(a["speed"], 1)
        self.assertEqual(children[0]["speed"], 2)
        single = core.duplicate(bpy.context, b)
        self.assertIsNone(single.parent)
        self.assertIsNone(single.get("vfx_composition"))
        self.assertEqual(single["start"], 7)
        core.delete(group)
        self.assertTrue(visible(children[0], 7))
        core.delete(clone)
        core.delete(single)
        self.assertEqual(len(bpy.data.meshes), 0)
        self.assertEqual(len(bpy.data.materials), 0)
        self.assertEqual(len(bpy.data.node_groups), 0)

    def test_delete_checks_every_member_before_any_mutation(self):
        group, a, b = create()
        external = bpy.data.objects.new("User Shared Mesh", b.children[0].data)
        bpy.context.scene.collection.objects.link(external)
        counts = (len(bpy.data.objects), len(bpy.data.meshes))
        with self.assertRaisesRegex(ValueError, "shared"):
            core.delete(group)
        self.assertEqual((len(bpy.data.objects), len(bpy.data.meshes)), counts)
        self.assertIn(a.name, bpy.data.objects)
        bpy.data.objects.remove(external, do_unlink=True)
        user = bpy.data.objects.new("User Child", None)
        bpy.context.scene.collection.objects.link(user)
        user.parent = group
        core.delete(group)
        self.assertIn(user.name, bpy.data.objects)
        self.assertIsNone(user.parent)

    def test_invalid_grouping_does_not_overwrite_user_data(self):
        a, b = core.create(bpy.context), core.create_particle(bpy.context)
        b.keyframe_insert(data_path='["start"]', frame=1)
        count = len(bpy.data.objects)
        with self.assertRaisesRegex(ValueError, "timing animation"):
            composition.create(bpy.context, [a, b])
        self.assertEqual(len(bpy.data.objects), count)
        self.assertIsNone(a.parent)
        b.animation_data_clear()
        b.constraints.new("LIMIT_LOCATION")
        with self.assertRaisesRegex(ValueError, "constraints"):
            composition.create(bpy.context, [a, b])
        b.constraints.clear()
        screen = core.create_screen(bpy.context)
        with self.assertRaisesRegex(ValueError, "Screen"):
            composition.create(bpy.context, [a, screen])
        group = composition.create(bpy.context, [a, b])
        with self.assertRaises(ValueError):
            core.preset_snapshot(group)
        with self.assertRaisesRegex(ValueError, "nested"):
            composition.create(bpy.context, [group, core.create(bpy.context)])

    def test_native_operators_select_edit_and_detach(self):
        a, b = core.create(bpy.context), core.create_particle(bpy.context)
        a.select_set(True)
        b.select_set(True)
        self.assertEqual(bpy.ops.vfx_studio.compose(), {"FINISHED"})
        group = bpy.context.object
        self.assertEqual(group["vfx_module"], "core.composition")
        self.assertEqual(bpy.ops.vfx_studio.select_member(uid=a["vfx_id"]), {"FINISHED"})
        self.assertEqual(bpy.context.object, a)
        self.assertEqual(bpy.ops.vfx_studio.detach_member(), {"FINISHED"})
        self.assertIsNone(a.parent)
        self.assertEqual(composition.members(group), [b])

    def test_edited_timing_and_transform_animation_are_not_erased(self):
        group, a, b = create()
        curve = a.animation_data.drivers[0]
        original = curve.driver.expression
        curve.driver.expression = "7"
        with self.assertRaisesRegex(ValueError, "edited"):
            composition.detach(bpy.context, a)
        self.assertEqual(curve.driver.expression, "7")
        curve.driver.expression = original
        a.keyframe_insert(data_path="location", frame=1)
        count = len(bpy.data.objects)
        with self.assertRaisesRegex(ValueError, "transform animation"):
            core.duplicate(bpy.context, a)
        self.assertEqual(len(bpy.data.objects), count)
        # Whole-group copying keeps the animated local transform and parent relationship.
        clone = core.duplicate(bpy.context, group)
        self.assertEqual(len(composition.members(clone)), 2)
        a.parent = None
        with self.assertRaisesRegex(ValueError, "reparented"):
            core.delete(group)
        a.animation_data.action = None
        composition.detach(bpy.context, a)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(CompositionTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Composition integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
group, a, b = create()
group.name, a.name, b.name = "Persisted Composition", "Composition Ring", "Composition Burst"
update(group, duration=48.0, loop=True)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/composition.blend"))
print("COMPOSITION_INTEGRATION_OK")
