"""Native cloth solver, portable baked poses and explicit stale-state handling."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import composition, core, simulation


def coordinates(root, frame):
    bpy.context.scene.frame_set(frame)
    _, output, _ = simulation.parts(root)
    mesh = output.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    return [tuple(v.co) for v in mesh.vertices]


def update(root, **values):
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


class SimulationTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_real_cloth_deformation_native_retime_and_loop(self):
        root = simulation.create(bpy.context)
        self.assertEqual(simulation.state(bpy.context, root), "UNBAKED")
        simulation.bake(bpy.context, root)
        self.assertEqual(simulation.state(bpy.context, root), "BAKED")
        start, middle = coordinates(root, 1), coordinates(root, 13)
        self.assertLess(middle[0][2], start[0][2] - 0.3)
        self.assertLess(abs(middle[-1][2] - start[-1][2]), 1e-5)  # Pinned edge.
        coordinates(root, 20)
        self.assertEqual(coordinates(root, 13), middle)
        update(root, speed=2.0)
        self.assertEqual(coordinates(root, 7), middle)
        self.assertEqual(simulation.state(bpy.context, root), "BAKED")
        self.assertEqual(coordinates(root, 13), [])
        update(root, loop=True)
        self.assertEqual(coordinates(root, 13), start)
        _, output, _ = simulation.parts(root)
        self.assertTrue(
            all(
                c.driver.is_valid and c.driver.is_simple_expression
                for c in output.data.shape_keys.animation_data.drivers
            )
        )

    def test_source_edits_mark_stale_and_rebake_preserves_frame_and_visibility(self):
        root = simulation.create(bpy.context)
        simulation.bake(bpy.context, root)
        before = coordinates(root, 13)
        source, output, cloth = simulation.parts(root)
        cloth.settings.mass *= 2
        self.assertEqual(simulation.state(bpy.context, root), "STALE")
        self.assertEqual(coordinates(root, 13), before)
        bpy.context.scene.frame_set(7, subframe=0.25)
        parent, hidden = source.parent, source.hide_get()
        simulation.bake(bpy.context, root)
        self.assertEqual(simulation.state(bpy.context, root), "BAKED")
        self.assertEqual(bpy.context.scene.frame_current, 7)
        self.assertEqual(bpy.context.scene.frame_subframe, 0.25)
        self.assertEqual(source.parent, parent)
        self.assertEqual(source.hide_get(), hidden)
        source.data.vertices[0].co.z += 0.2
        self.assertEqual(simulation.state(bpy.context, root), "STALE")
        source.data.vertices[0].co.z -= 0.2
        bpy.context.scene.gravity.z = -4
        self.assertEqual(simulation.state(bpy.context, root), "STALE")
        self.assertIsNotNone(output.data.shape_keys)

    def test_repeat_bake_is_deterministic_and_controller_transform_is_playback_only(self):
        root = simulation.create(bpy.context)
        simulation.bake(bpy.context, root)
        before = coordinates(root, 17)
        root.location = (3, 4, 5)
        root.rotation_euler = (0.3, 0.2, 0.1)
        root.scale = (1.2, 0.8, 1.0)
        bpy.context.view_layer.update()
        simulation.bake(bpy.context, root)
        after = coordinates(root, 17)
        self.assertLess(max(abs(x - y) for a, b in zip(before, after) for x, y in zip(a, b)), 1e-5)
        self.assertEqual(tuple(root.location), (3, 4, 5))
        self.assertEqual(simulation.parts(root)[0].parent, root)

    def test_independent_shape_key_copy_composition_and_safe_delete(self):
        root = simulation.create(bpy.context)
        simulation.bake(bpy.context, root)
        before = coordinates(root, 13)
        original_output = simulation.parts(root)[1]
        value = original_output.data.materials[0].node_tree.nodes.new("ShaderNodeValue")
        value.name = "Stored Pose Time"
        curve = value.outputs[0].driver_add("default_value")
        var = curve.driver.variables.new()
        var.name, var.type = "t", "SINGLE_PROP"
        var.targets[0].id_type = "KEY"
        var.targets[0].id = original_output.data.shape_keys
        var.targets[0].data_path = "eval_time"
        curve.driver.expression = "t"
        clone = core.duplicate(bpy.context, root)
        source, output, cloth = simulation.parts(clone)
        self.assertEqual(simulation.state(bpy.context, clone), "BAKED")
        self.assertIsNot(output.data.shape_keys, simulation.parts(root)[1].data.shape_keys)
        update(clone, speed=2.0)
        self.assertEqual(coordinates(clone, 7), before)
        self.assertNotEqual(coordinates(root, 7), before)
        copied_value = output.data.materials[0].node_tree.nodes["Stored Pose Time"]
        self.assertAlmostEqual(copied_value.outputs[0].default_value, 120, places=4)
        self.assertAlmostEqual(value.outputs[0].default_value, 60, places=4)
        group = composition.create(bpy.context, [root, core.create(bpy.context)])
        copied_group = core.duplicate(bpy.context, group)
        copied_sim = next(
            o for o in composition.members(copied_group) if o["vfx_module"] == "simulation.cloth"
        )
        self.assertEqual(simulation.state(bpy.context, copied_sim), "BAKED")
        core.delete(group)
        core.delete(copied_group)
        self.assertTrue(coordinates(clone, 7))
        core.delete(clone)
        self.assertEqual(len(bpy.data.shape_keys), 0)
        self.assertEqual(len(bpy.data.meshes), 0)
        self.assertEqual(len(bpy.data.materials), 0)

    def test_failed_bake_keeps_previous_result_and_external_users(self):
        root = simulation.create(bpy.context)
        simulation.bake(bpy.context, root)
        source, output, cloth = simulation.parts(root)
        old = output.data
        update(root, vfx_sim_last=1000)
        with self.assertRaisesRegex(ValueError, "121"):
            simulation.bake(bpy.context, root)
        self.assertEqual(output.data, old)
        update(root, vfx_sim_last=25)
        cloth.collision_settings.use_collision = True
        with self.assertRaisesRegex(ValueError, "external collisions"):
            simulation.bake(bpy.context, root)
        self.assertEqual(output.data, old)
        cloth.collision_settings.use_collision = False
        external = bpy.data.objects.new("User Shared Output", old)
        bpy.context.scene.collection.objects.link(external)
        with self.assertRaisesRegex(ValueError, "private"):
            simulation.bake(bpy.context, root)
        with self.assertRaisesRegex(ValueError, "shared"):
            core.delete(root)
        self.assertIn(external.name, bpy.data.objects)
        self.assertEqual(output.data, old)

    def test_interrupted_sampling_restores_scene_and_keeps_old_bake(self):
        root = simulation.create(bpy.context)
        simulation.bake(bpy.context, root)
        source, output, _ = simulation.parts(root)
        old = output.data
        bpy.context.scene.frame_set(7, subframe=0.25)
        counts = len(bpy.data.objects), len(bpy.data.meshes)

        class InterruptedContext:
            calls = 0

            def __getattr__(self, name):
                return getattr(bpy.context, name)

            def evaluated_depsgraph_get(self):
                self.calls += 1
                if self.calls == 5:
                    raise RuntimeError("interrupted solver evaluation")
                return bpy.context.evaluated_depsgraph_get()

        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            simulation.bake(InterruptedContext(), root)
        self.assertEqual(output.data, old)
        self.assertEqual((len(bpy.data.objects), len(bpy.data.meshes)), counts)
        self.assertEqual(bpy.context.scene.frame_current, 7)
        self.assertEqual(bpy.context.scene.frame_subframe, 0.25)
        self.assertEqual(source.parent, root)
        self.assertTrue(source.hide_get())

    def test_shape_key_external_driver_prevents_deletion_and_clear(self):
        root = simulation.create(bpy.context)
        simulation.bake(bpy.context, root)
        _, output, _ = simulation.parts(root)
        key = output.data.shape_keys
        user = bpy.data.objects.new("User Driver", None)
        bpy.context.scene.collection.objects.link(user)
        user["value"] = 0.0
        curve = user.driver_add('["value"]')
        var = curve.driver.variables.new()
        var.name = "time"
        var.type = "SINGLE_PROP"
        var.targets[0].id_type = "KEY"
        var.targets[0].id = key
        var.targets[0].data_path = "eval_time"
        curve.driver.expression = "time"
        with self.assertRaisesRegex(ValueError, "shared"):
            simulation.clear(root)
        with self.assertRaisesRegex(ValueError, "shape keys are shared"):
            core.delete(root)
        user.driver_remove('["value"]')
        core.delete(root)
        self.assertIn(user.name, bpy.data.objects)

    def test_operator_clear_and_unsupported_parameter_presets(self):
        self.assertEqual(bpy.ops.vfx_studio.create_simulation(), {"FINISHED"})
        root = bpy.context.object
        self.assertEqual(bpy.ops.vfx_studio.bake_simulation(), {"FINISHED"})
        self.assertEqual(simulation.state(bpy.context, root), "BAKED")
        with self.assertRaises(ValueError):
            core.preset_snapshot(root)
        self.assertEqual(bpy.ops.vfx_studio.clear_simulation(), {"FINISHED"})
        self.assertEqual(simulation.state(bpy.context, root), "UNBAKED")
        self.assertEqual(len(bpy.data.shape_keys), 0)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(SimulationTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Simulation integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = simulation.create(bpy.context)
simulation.bake(bpy.context, root)
root.name = "Persisted Cloth"
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/simulation.blend"))
print("SIMULATION_INTEGRATION_OK")
