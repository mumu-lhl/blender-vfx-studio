"""Native emission fill, independent ages, slot reuse, deterministic motion and assets."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from emitter_test_support import mesh, particles
from particle_test_support import camera, render_pixels

import blender_vfx_studio as addon
from blender_vfx_studio import assets, composition, core, presets
from blender_vfx_studio.emitter import limits


def update(root, **values):
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


def create():
    bpy.context.scene.frame_set(1)
    root = core.create_emitter(bpy.context)
    update(
        root,
        rate=4.0,
        lifetime=1.0,
        emission_seconds=3.0,
        duration=40.0,
        velocity=2.0,
        gravity=0.0,
        spread=0.0,
        randomness=0.0,
        spawn_radius=0.0,
        size=0.1,
        fade=0.0,
    )
    return root


def snapshot(root, frame):
    return [tuple(round(c, 6) for c in v.co) for v in mesh(root, frame).vertices]


class EmitterTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_initial_fill_stop_tail_and_arbitrary_frame_motion(self):
        root = create()
        expected = {
            0: [],
            1: [0],
            6: [0, 0.5, 1],
            11: [0, 0.5, 1, 1.5],
            16: [0, 0.5, 1, 1.5],
            31: [0.5, 1, 1.5],
            36: [1.5],
            39: [],
            41: [],
        }
        for frame in (16, 0, 1, 31, 6, 41, 11, 36, 39, 6):
            actual = sorted(center.z for center, _ in particles(root, frame))
            self.assertEqual(len(actual), len(expected[frame]), frame)
            for value, wanted in zip(actual, expected[frame]):
                self.assertAlmostEqual(value, wanted, places=5)
        original = snapshot(root, 11)
        update(root, speed=2.0)
        self.assertEqual(snapshot(root, 6), original)
        update(root, speed=1.0, duration=80.0)
        self.assertEqual(snapshot(root, 21), original)
        update(root, duration=40.0, loop=True)
        self.assertEqual(snapshot(root, 41), snapshot(root, 1))

    def test_individual_size_fades_and_ballistic_ages(self):
        root = create()
        update(root, fade=1.0, size=0.2)
        for center, radius in particles(root, 6):
            age = center.z / 2
            self.assertAlmostEqual(radius, 0.2 * (1 - age), places=5)
        update(root, fade=0.0, gravity=4.0)
        # At t=0.5 the three ages are 0, .25, .5; y/z do not use effect progress as age.
        actual = sorted(center.z for center, _ in particles(root, 6))
        for value, expected in zip(actual, (0, 0.375, 0.5)):
            self.assertAlmostEqual(value, expected, places=5)

    def test_slot_reuse_has_new_random_id_and_repeated_frames_are_stable(self):
        root = create()
        update(root, rate=1.0, spread=1.0, randomness=0.5)
        first = snapshot(root, 3.5)  # age .25, birth ID 0, one reusable slot
        self.assertNotEqual(snapshot(root, 13.5), first)  # same age, birth ID 1
        self.assertEqual(snapshot(root, 3.5), first)
        update(root, seed=99)
        self.assertNotEqual(snapshot(root, 3.5), first)
        update(root, seed=1)
        self.assertEqual(snapshot(root, 3.5), first)
        update(root, rate=0.0)
        self.assertFalse(mesh(root, 6).vertices)
        update(root, rate=4.0, emission_seconds=0.0)
        self.assertFalse(mesh(root, 6).vertices)

    def test_capacity_limits_effective_rate_and_native_geometry(self):
        root = create()
        update(root, rate=10000.0, lifetime=100.0, emission_seconds=100.0, duration=200.0)
        effective, slots = limits(root["rate"], root["lifetime"])
        self.assertAlmostEqual(effective, 20.48)
        self.assertEqual(slots, 2048)
        self.assertEqual(len(mesh(root, 51).vertices), 1025 * 12)
        self.assertLessEqual(len(mesh(root, 100).vertices), 2048 * 12)
        update(root, rate=1e9, lifetime=1000.0)
        self.assertEqual(len(mesh(root, 51).vertices), 1025 * 12)
        with self.assertRaises(ValueError):
            core.preset_snapshot(root)

    def test_duplicate_materials_and_native_preset_assets(self):
        root = create()
        update(
            root,
            rate=1.0,
            emission_seconds=1.0,
            velocity=0.0,
            gravity=0.0,
            size=0.6,
            strength=1.0,
            color_0=1.0,
            color_1=0.0,
            color_2=0.0,
        )
        root.location.x = -0.8
        clone = core.duplicate(bpy.context, root)
        clone.location.x = 0.8
        update(clone, color_0=0.0, color_2=1.0)
        camera()
        pixels = render_pixels(1)
        for x, wanted in ((14, (1, 0, 0)), (34, (0, 0, 1))):
            rgb = pixels[(24 * 48 + x) * 4 : (24 * 48 + x) * 4 + 3]
            self.assertTrue(all(abs(a - b) < 0.03 for a, b in zip(rgb, wanted)))
        data = presets.loads(presets.dumps(core.preset_snapshot(root)))
        restored = core.create_from_preset(bpy.context, data)
        self.assertEqual(restored["vfx_module"], "particle.emitter")
        core.delete(restored)
        path = ROOT / "work/emitter-asset.blend"
        assets.write(path, clone)
        loaded = assets.load(bpy.context, path)
        self.assertNotEqual(loaded["vfx_id"], clone["vfx_id"])
        core.delete(root)
        core.delete(clone)
        self.assertTrue(mesh(loaded, 5).vertices)
        core.delete(loaded)
        self.assertFalse(bpy.data.meshes)
        self.assertFalse(bpy.data.materials)
        self.assertFalse(bpy.data.node_groups)

    def test_quality_operator_composition_and_simple_drivers(self):
        counts = []
        for quality in ("LOW", "MEDIUM", "HIGH"):
            self.assertEqual(bpy.ops.vfx_studio.create_emitter(quality=quality), {"FINISHED"})
            root = bpy.context.object
            update(root, rate=1.0, lifetime=1.0, emission_seconds=1.0)
            counts.append(len(mesh(root, 1).polygons))
            for data in (
                root.children[0].modifiers[0].node_group,
                root.children[0].data.materials[0].node_tree,
            ):
                self.assertTrue(
                    all(
                        c.driver.is_valid and c.driver.is_simple_expression
                        for c in data.animation_data.drivers
                    )
                )
            core.delete(root)
        self.assertEqual(counts, [20, 80, 320])
        root = create()
        original = snapshot(root, 11)
        ring = core.create(bpy.context)
        group = composition.create(bpy.context, [root, ring])
        update(group, duration=80.0)
        self.assertEqual(snapshot(root, 21), original)
        core.delete(group)
        before = set(bpy.data.all_ids)
        with self.assertRaises(ValueError):
            core.create_emitter(bpy.context, "INVALID")
        self.assertEqual(set(bpy.data.all_ids), before)

    def test_animated_rate_recalculates_current_schedule_without_accumulated_history(self):
        root = create()
        for frame, rate in ((1, 4.0), (11, 8.0)):
            root["rate"] = rate
            root.keyframe_insert(data_path='["rate"]', frame=frame)
        animated = snapshot(root, 11)
        self.assertEqual(len(animated), 8 * 12)
        snapshot(root, 6)
        self.assertEqual(snapshot(root, 11), animated)
        root.animation_data_clear()
        update(root, rate=8.0)
        self.assertEqual(snapshot(root, 11), animated)

    def test_fractional_birth_and_scene_time_mapping(self):
        bpy.context.scene.frame_set(7, subframe=0.5)
        root = core.create_emitter(bpy.context)
        self.assertEqual(root["start"], 7.5)
        update(root, rate=4.0, lifetime=1.0, emission_seconds=3.0, duration=40.0)
        self.assertFalse(mesh(root, 7.25).vertices)
        self.assertEqual(len(mesh(root, 7.5).vertices), 12)
        # A fractional boundary at age .25 births the second particle.
        self.assertEqual(len(mesh(root, 10).vertices), 24)
        bpy.context.scene.render.frame_map_new = 50
        update(root, start=1.0)
        self.assertEqual(len(mesh(root, 3).vertices), 36)  # native driver time 6 -> motion .5


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(EmitterTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Emitter integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = create()
root.name = "Persisted Emitter"
update(root, size=0.3, color_0=1.0, color_1=0.0, color_2=0.0, strength=1.0)
camera()
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/emitter.blend"))
print("EMITTER_INTEGRATION_OK")
