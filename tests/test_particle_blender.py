"""Native ballistic motion, stable randomness and private material references."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from particle_test_support import camera, render_pixels

import blender_vfx_studio as addon
from blender_vfx_studio import core, presets

WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)


def update(root, **parameters):
    for key, value in parameters.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


def mesh(root, frame):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data


def points(root, frame):
    return [tuple(round(c, 6) for c in v.co) for v in mesh(root, frame).vertices]


class ParticleTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.frame_set(1)

    def test_analytic_motion_at_arbitrary_frames_and_playback_speed(self):
        root = core.create_particle(bpy.context)
        update(
            root,
            count=4,
            spread=0.0,
            randomness=0.0,
            spawn_radius=0.0,
            motion_seconds=1.0,
            velocity=2.0,
            gravity=4.0,
        )
        for frame in (13, 1, 24, 7, 25, 0, 19):
            result = mesh(root, frame)
            if frame in (0, 25):
                self.assertEqual(len(result.vertices), 0)
            else:
                time = (frame - 1) / 24
                self.assertAlmostEqual(
                    sum(v.co.z for v in result.vertices) / len(result.vertices),
                    2 * time - 2 * time * time,
                    places=5,
                )
        original = points(root, 13)
        update(root, speed=2.0)
        self.assertEqual(points(root, 7), original)
        update(root, loop=True)
        self.assertGreater(len(mesh(root, 13).vertices), 0)

    def test_deterministic_seed_count_and_evaluation_budget(self):
        root = core.create_particle(bpy.context)
        update(root, count=8)
        original = points(root, 7)
        points(root, 20)
        self.assertEqual(points(root, 7), original)
        update(root, seed=99)
        self.assertNotEqual(points(root, 7), original)
        update(root, seed=1)
        self.assertEqual(points(root, 7), original)
        update(root, count=4)
        self.assertEqual(len(mesh(root, 7).vertices) * 2, len(original))
        update(root, count=2048)
        maximum = len(mesh(root, 7).vertices)
        update(root, count=3000)
        self.assertEqual(len(mesh(root, 7).vertices), maximum)
        with self.assertRaises(ValueError):
            core.preset_snapshot(root)

    def test_duplicate_materials_are_independent_in_actual_render(self):
        root = core.create_particle(bpy.context)
        update(
            root,
            count=1,
            spawn_radius=0.0,
            velocity=0.0,
            gravity=0.0,
            size=0.6,
            randomness=0.0,
            color_0=1.0,
            color_1=0.0,
            color_2=0.0,
            strength=1.0,
        )
        root.location.x = -0.8
        clone = core.duplicate(bpy.context, root)
        clone.location.x = 0.8
        update(clone, color_0=0.0, color_2=1.0)
        camera()
        result = render_pixels(1)
        for x, expected in [(14, (1, 0, 0)), (34, (0, 0, 1))]:
            index = (24 * 48 + x) * 4
            self.assertTrue(
                all(abs(a - b) < 0.03 for a, b in zip(result[index : index + 3], expected))
            )
        core.delete(root)
        self.assertGreater(len(mesh(clone, 7).vertices), 0)
        core.delete(clone)
        self.assertEqual(len(bpy.data.materials), 0)

    def test_quality_operators_presets_and_simple_drivers(self):
        counts = []
        for quality in ("LOW", "MEDIUM", "HIGH"):
            self.assertEqual(bpy.ops.vfx_studio.create_particle(quality=quality), {"FINISHED"})
            root = bpy.context.object
            update(root, count=2)
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
            data = presets.loads(presets.dumps(core.preset_snapshot(root)))
            clone = core.create_from_preset(bpy.context, data)
            self.assertEqual(clone["count"], 2)
            self.assertEqual(clone["vfx_quality"], quality)
            self.assertNotEqual(root["vfx_id"], clone["vfx_id"])
            core.delete(root)
            core.delete(clone)
        self.assertLess(counts[0], counts[1])
        self.assertLess(counts[1], counts[2])

    def test_external_material_users_still_block_deletion(self):
        root = core.create_particle(bpy.context)
        material = root.children[0].data.materials[0]
        external = bpy.data.meshes.new("User Mesh")
        external.materials.append(material)
        root.children[0].data.materials.clear()  # GN still uses this generated material.
        with self.assertRaisesRegex(ValueError, "shared"):
            core.delete(root)
        external.materials.clear()
        core.delete(root)
        self.assertIn(external.name, bpy.data.meshes)
        self.assertEqual(len(bpy.data.materials), 0)

    def test_shard_shape_stretch_plane_and_motion_controls_change_native_geometry(self):
        root = core.create_particle(bpy.context)
        update(
            root,
            count=1,
            shape=1,
            stretch=6.0,
            spread=0.0,
            randomness=0.0,
            velocity=0.0,
            gravity=0.0,
            size=0.1,
        )
        result = mesh(root, 1)

        def extent(axis):
            return max(v.co[axis] for v in result.vertices) - min(
                v.co[axis] for v in result.vertices
            )

        self.assertGreater(extent(2), extent(0) * 20)
        self.assertLess(len(result.vertices), 20)
        update(root, count=12, spread=1.0, velocity=3.0, planar=1.0)
        flat = points(root, 7)
        update(root, planar=0.0)
        self.assertNotEqual(points(root, 7), flat)
        update(root, motion_ease=0.9)
        eased = points(root, 7)
        points(root, 19)
        self.assertEqual(points(root, 7), eased)
        update(root, speed=2.0)
        self.assertEqual(points(root, 4), eased)
        update(root, count=3000)
        self.assertLessEqual(len(mesh(root, 4).vertices), 2048 * 20)

    def test_legacy_and_shard_presets_keep_their_versions_and_private_data(self):
        legacy = core.create_particle(bpy.context, asset_version=1)
        snapshot = core.preset_snapshot(legacy)
        self.assertEqual(snapshot["asset_version"], 1)
        restored = core.create_from_preset(bpy.context, snapshot)
        self.assertNotIn("shape", restored)
        self.assertEqual(points(legacy, 7), points(restored, 7))
        bpy.context.scene.frame_set(1)
        root = core.create_particle(bpy.context)
        update(root, shape=1, stretch=8.0, planar=0.8, motion_ease=0.7)
        snapshot = presets.loads(presets.dumps(core.preset_snapshot(root)))
        restored = core.create_from_preset(bpy.context, snapshot)
        self.assertEqual(restored["shape"], 1)
        self.assertEqual(restored["stretch"], 8.0)
        clone = core.duplicate(bpy.context, root)
        self.assertEqual(points(root, 5), points(clone, 5))
        update(clone, stretch=2.0)
        self.assertNotEqual(points(root, 5), points(clone, 5))
        core.delete(root)
        self.assertTrue(mesh(clone, 5).vertices)
        counts = len(bpy.data.objects)
        with self.assertRaises(ValueError):
            core.create_particle(bpy.context, asset_version=99)
        self.assertEqual(len(bpy.data.objects), counts)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(ParticleTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Particle integration tests failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.frame_set(1)
root = core.create_particle(bpy.context)
root.name = "Persisted Burst"
update(
    root,
    count=2,
    spread=0.0,
    randomness=0.0,
    spawn_radius=0.0,
    velocity=2.0,
    gravity=4.0,
    size=0.5,
    fade=0.0,
    color_0=1.0,
    color_1=0.0,
    color_2=0.0,
    strength=1.0,
)
clone = core.duplicate(bpy.context, root)
clone.name = "Persisted Burst Copy"
clone.location.x = 4
camera()
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "particle.blend"))
print("PARTICLE_INTEGRATION_OK")
