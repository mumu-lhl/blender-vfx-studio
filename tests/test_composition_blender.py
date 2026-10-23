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

    def test_ungroup_sixteen_layers_preserves_current_state_and_resources(self):
        roots = [core.create(bpy.context, quality="LOW") for _ in range(16)]
        for index, root in enumerate(roots):
            root.location = (index * 0.2, 1, 2)
            root.rotation_euler.z = index * 0.1
        group = composition.create(bpy.context, roots)
        bpy.context.scene.collection.objects.link(group)
        bpy.context.scene.view_layers.new("Other View Layer")
        group.location = (3, 4, 5)
        group.rotation_euler.z = 0.4
        group.scale = (1.5,) * 3
        update(group, duration=48.0, speed=2.0, loop=True)
        roots[-1].keyframe_insert(data_path='["radius"]', frame=1)
        action = roots[-1].animation_data.action
        material = roots[0].children[0].data.materials[0]
        user_node = material.node_tree.nodes.new("ShaderNodeValue")
        user_node.name = "User Edit"
        user_node.outputs[0].default_value = 0.75
        bpy.context.scene.frame_set(31, subframe=0.25)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        before = []
        for root in roots:
            layer = root.children[0]
            before.append(
                (
                    root.matrix_world.copy(),
                    tuple(root[key] for key in composition.TIME_KEYS),
                    [v.co.copy() for v in layer.evaluated_get(depsgraph).data.vertices],
                    layer.data,
                )
            )
        group_id = group["vfx_id"]
        detached, retained = composition.ungroup_all(bpy.context, group)
        self.assertFalse(retained)
        self.assertEqual(set(detached), set(roots))
        self.assertFalse(any(o.get("vfx_id") == group_id for o in bpy.data.objects))
        self.assertEqual(set(bpy.context.selected_objects), set(roots))
        self.assertEqual(bpy.context.scene.frame_current_final, 31.25)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for root, (world, timing, vertices, mesh) in zip(roots, before):
            self.assertIsNone(root.parent)
            self.assertIsNone(root.get("vfx_composition"))
            self.assertEqual(tuple(root[key] for key in composition.TIME_KEYS), timing)
            self.assertLess(
                max(abs(x - y) for a, b in zip(world, root.matrix_world) for x, y in zip(a, b)),
                1e-5,
            )
            self.assertEqual(root.children[0].data, mesh)
            actual = root.children[0].evaluated_get(depsgraph).data.vertices
            self.assertEqual(len(actual), len(vertices))
            self.assertTrue(all((a.co - b).length < 1e-5 for a, b in zip(actual, vertices)))
        self.assertEqual(roots[-1].animation_data.action, action)
        self.assertEqual(material.node_tree.nodes["User Edit"].outputs[0].default_value, 0.75)
        self.assertTrue(visible(roots[0], 31))
        self.assertFalse(visible(roots[0], 61))

    def test_ungroup_preflight_does_not_detach_any_member_on_failure(self):
        for failure in (
            "driver",
            "muted",
            "timing",
            "animation",
            "constraint",
            "shear",
            "reparent",
        ):
            with self.subTest(failure=failure):
                bpy.ops.wm.read_factory_settings(use_empty=True)
                group, a, b = create()
                # The invalid member sorts last, exposing partial-mutation errors.
                a.name, b.name = "First", "Last"
                if failure == "driver":
                    b.animation_data.drivers[-1].driver.expression = "7"
                elif failure == "muted":
                    b.animation_data.drivers[-1].mute = True
                elif failure == "timing":
                    b.keyframe_insert(data_path='["start"]', frame=1)
                elif failure == "animation":
                    b.keyframe_insert(data_path="location", frame=1)
                elif failure == "constraint":
                    b.constraints.new("LIMIT_LOCATION")
                elif failure == "shear":
                    group.scale = (2, 1, 1)
                    b.rotation_euler.z = 0.7
                else:
                    b.parent = None
                bpy.context.view_layer.update()
                before = {o.as_pointer() for o in bpy.data.objects}
                with self.assertRaises(ValueError):
                    composition.ungroup_all(bpy.context, group)
                self.assertEqual({o.as_pointer() for o in bpy.data.objects}, before)
                self.assertEqual(a.parent, group)
                self.assertEqual(a.get("vfx_composition"), group)
                self.assertEqual(len(a.animation_data.drivers), 4)
                self.assertEqual(b.get("vfx_composition"), group)

    def test_ungroup_keeps_controller_referenced_by_user_data(self):
        group, a, b = create()
        user = bpy.data.objects.new("User Child", None)
        bpy.context.scene.collection.objects.link(user)
        user.parent = group
        user.location = (2, 3, 4)
        user.keyframe_insert(data_path="location", frame=1)
        action = user.animation_data.action
        material = a.children[0].data.materials[0]
        node = material.node_tree.nodes.new("ShaderNodeValue")
        nodes.drive(node.outputs[0], "default_value", group, "p", {"p": "duration"})
        detached, retained = composition.ungroup_all(bpy.context, group)
        self.assertTrue(retained)
        self.assertEqual(set(detached), {a, b})
        self.assertEqual(user.parent, group)
        self.assertEqual(user.animation_data.action, action)
        self.assertEqual(composition.members(group), [])
        update(group, duration=60.0, speed=3.0)
        self.assertEqual(node.outputs[0].default_value, 60)
        self.assertEqual(a["duration"], 24)
        self.assertEqual(a["speed"], 1)
        bpy.data.objects.remove(user, do_unlink=True)
        material.node_tree.nodes.remove(node)
        detached, retained = composition.ungroup_all(bpy.context, group)
        self.assertFalse(retained)
        self.assertEqual(detached, [])

    def test_single_detach_also_refuses_shear_without_changing_parent(self):
        group, a, b = create()
        group.scale = (2, 1, 1)
        a.rotation_euler.z = 0.7
        with self.assertRaisesRegex(ValueError, "sheared"):
            composition.detach(bpy.context, a)
        self.assertEqual(a.parent, group)
        self.assertEqual(len(a.animation_data.drivers), 4)
        count = len(bpy.data.objects)
        with self.assertRaisesRegex(ValueError, "sheared"):
            core.duplicate(bpy.context, a)
        self.assertEqual(len(bpy.data.objects), count)

    def test_ungroup_keeps_explicit_scene_and_collection_references(self):
        for owner_kind in ("scene", "collection"):
            with self.subTest(owner=owner_kind):
                bpy.ops.wm.read_factory_settings(use_empty=True)
                group, a, b = create()
                owner = bpy.context.scene if owner_kind == "scene" else group.users_collection[0]
                owner["User Controller"] = group
                bpy.context.scene.view_layers.new("Other View Layer")
                children, retained = composition.ungroup_all(bpy.context, group)
                self.assertTrue(retained)
                self.assertEqual(owner["User Controller"], group)
                self.assertTrue(all(r.parent is None for r in children))
                del owner["User Controller"]
                self.assertFalse(composition.ungroup_all(bpy.context, group)[1])

    def test_ungroup_bound_animated_group_preserves_evaluated_pose(self):
        from blender_vfx_studio import binding

        group, a, b = create()
        target = bpy.data.objects.new("Animated Target", None)
        bpy.context.scene.collection.objects.link(target)
        target.keyframe_insert(data_path="location", frame=1)
        target.location = (4, 5, 6)
        target.keyframe_insert(data_path="location", frame=13)
        action = target.animation_data.action
        bpy.context.scene.frame_set(1)
        binding.bind(bpy.context, group, target)
        group.rotation_euler.z = 0.2
        group.keyframe_insert(data_path="rotation_euler", frame=1)
        group.rotation_euler.z = 0.8
        group.keyframe_insert(data_path="rotation_euler", frame=13)
        bpy.context.scene.frame_set(7, subframe=0.5)
        world = a.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.copy()
        children, retained = composition.ungroup_all(bpy.context, group)
        self.assertFalse(retained)
        self.assertEqual(set(children), {a, b})
        self.assertLess(
            max(abs(x - y) for ra, rb in zip(world, a.matrix_world) for x, y in zip(ra, rb)), 1e-5
        )
        bpy.context.scene.frame_set(13)
        self.assertLess(
            max(abs(x - y) for ra, rb in zip(world, a.matrix_world) for x, y in zip(ra, rb)), 1e-5
        )
        self.assertEqual(target.animation_data.action, action)

    def test_ungroup_imported_composition_can_export_independent_layers(self):
        from blender_vfx_studio import assets

        group, a, b = create()
        path = ROOT / "work/ungroup-complete.blend"
        assets.write(path, group)
        loaded = assets.load(bpy.context, path)
        children, retained = composition.ungroup_all(bpy.context, loaded)
        self.assertFalse(retained)
        self.assertEqual(len(children), 2)
        self.assertEqual(set(composition.members(group)), {a, b})
        for child in children:
            self.assertIsNone(child.parent)
            assets.write(ROOT / "work/ungroup-independent.blend", child)
            copy = assets.load(bpy.context, ROOT / "work/ungroup-independent.blend")
            self.assertNotEqual(copy["vfx_id"], child["vfx_id"])
            core.delete(copy)
            core.delete(child)
        self.assertEqual(set(composition.members(group)), {a, b})

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
ungrouped, ring, burst = create()
ring.name, burst.name = "Ungrouped Ring", "Ungrouped Burst"
update(ungrouped, duration=48.0, loop=True)
ungrouped.location = (2, 3, 4)
bpy.context.scene.frame_set(61, subframe=0.25)
composition.ungroup_all(bpy.context, ungrouped)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/composition.blend"))
print("COMPOSITION_INTEGRATION_OK")
