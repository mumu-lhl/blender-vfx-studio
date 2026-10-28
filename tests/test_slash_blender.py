"""Procedural slash geometry, native timing and parameter preset reuse."""

import math
import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from particle_test_support import camera, render_pixels

import blender_vfx_studio as addon
from blender_vfx_studio import assets, core, presets, slash


def update(root, **values):
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


def mesh(root, frame):
    bpy.context.scene.frame_set(frame)
    return root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data


def points(root, frame):
    return [tuple(v.co) for v in mesh(root, frame).vertices]


def create():
    root = slash.create(bpy.context)
    update(
        root,
        start=1.0,
        duration=24.0,
        arc=180.0,
        spin=180.0,
        radius=2.0,
        width=0.5,
        expansion=0.0,
        taper=1.0,
    )
    return root


class SlashTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_preset_roundtrip_and_independent_duplicate(self):
        root = create()
        root.children[0].data.materials[0].node_tree.nodes.new("ShaderNodeValue").name = "User Edit"
        data = presets.loads(presets.dumps(core.preset_snapshot(root)))
        restored = core.create_from_preset(bpy.context, data)
        self.assertEqual(restored["vfx_module"], "mesh.slash")
        self.assertEqual(restored["arc"], 180)
        clone = core.duplicate(bpy.context, root)
        update(clone, arc=90.0)
        self.assertEqual(root["arc"], 180)
        self.assertIn("User Edit", clone.children[0].data.materials[0].node_tree.nodes)
        core.delete(root)
        self.assertTrue(mesh(clone, 7).vertices)
        core.delete(clone)
        core.delete(restored)
        self.assertEqual(len(bpy.data.meshes), 0)
        self.assertEqual(len(bpy.data.materials), 0)

    def test_creation_quality_operator_and_simple_drivers(self):
        counts = []
        for quality in ("LOW", "MEDIUM", "HIGH"):
            self.assertEqual(
                bpy.ops.vfx_studio.create(preset="ARC_SLASH", quality=quality), {"FINISHED"}
            )
            root = bpy.context.object
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
        self.assertTrue(0 < counts[0] < counts[1] < counts[2])

    def test_geometry_parameters_and_stateless_playback(self):
        root = slash.create(bpy.context, "LOW")
        peak = points(root, 5)
        update(root, motion_ease=0.0)
        self.assertNotEqual(points(root, 5), peak)
        update(root, motion_ease=0.85, head_bias=0.0)
        self.assertNotEqual(points(root, 5), peak)
        update(root, head_bias=0.7)
        self.assertEqual(points(root, 5), peak)
        self.assertEqual(points(root, 0), [])
        self.assertEqual(points(root, 17), [])
        self.assertEqual(points(root, 5), peak)
        update(root, speed=2.0)
        self.assertEqual(points(root, 3), peak)
        update(root, speed=1.0, loop=True)
        self.assertEqual(points(root, 21), peak)

    def test_shape_controls_and_retiming(self):
        root = core.create(bpy.context, "ARC_SLASH", "LOW")
        peak = points(root, 5)
        self.assertGreater(max(p[2] for p in peak) - min(p[2] for p in peak), 0.1)
        for key in ("contour", "bank", "wake_spread"):
            original = root[key]
            update(root, **{key: 0.0})
            self.assertNotEqual(points(root, 5), peak, key)
            update(root, **{key: original})
            self.assertEqual(points(root, 5), peak)
        update(root, bank=0.0)
        self.assertTrue(all(abs(p[2]) < 1e-6 for p in points(root, 5)))
        update(root, bank=0.22, speed=2.0)
        self.assertEqual(points(root, 3), peak)
        self.assertEqual(points(root, 9), [])
        update(root, speed=1.0)
        self.assertEqual(points(root, 0), [])
        self.assertEqual(points(root, 5), peak)
        clone = core.duplicate(bpy.context, root)
        update(clone, contour=0.0)
        self.assertEqual(points(root, 5), peak)
        snapshot = presets.loads(presets.dumps(core.preset_snapshot(root)))
        restored = core.create_from_preset(bpy.context, snapshot)
        update(restored, start=1.0)
        self.assertEqual(points(restored, 5), peak)

    def test_pointed_ends_close_in_depth_with_banking_and_colored_wakes(self):
        root = slash.create(bpy.context, "LOW")
        update(root, bank=0.8, contour=0.0)
        for frame in (2, 5, 11):
            vertices = points(root, frame)
            band_size = len(vertices) // 3
            for band in range(3):
                for section in (0, 32):
                    row = vertices[
                        band * band_size + section * 6 : band * band_size + (section + 1) * 6
                    ]
                    self.assertLess(max(p[2] for p in row) - min(p[2] for p in row), 1e-5)

    def test_head_bias_moves_body_mass_forward_without_changing_the_radius(self):
        root = core.create(bpy.context, "ARC_SLASH", "LOW")
        update(root, duration=18.0, spin=0.0, bank=0.0, contour=0.0, head_bias=1.0)

        def widths():
            vertices = mesh(root, 5).vertices
            return [vertices[i * 6].co.length - vertices[i * 6 + 5].co.length for i in (8, 24)]

        tail, head = widths()
        self.assertGreater(head, tail * 3)
        update(root, head_bias=0.0)
        tail, head = widths()
        self.assertAlmostEqual(tail, head, places=5)

    def test_wakes_remain_after_the_main_blade_and_follow_group_speed(self):
        root = core.create(bpy.context, "ARC_SLASH", "LOW")
        update(root, duration=18.0)
        camera()
        bpy.context.scene.camera.data.ortho_scale = 5.5
        bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 96
        bpy.context.scene.render.dither_intensity = 0
        wake = render_pixels(13)
        self.assertGreater(sum(wake[0::4]), 0.01)
        update(root, speed=2.0)
        self.assertEqual(render_pixels(7), wake)
        update(root, afterimage=0.0)
        self.assertLess(max(render_pixels(7)[0::4]), 1e-5)

    def test_reversing_sweep_keeps_the_leading_mass_and_wakes_on_the_leading_side(self):
        root = core.create(bpy.context, "ARC_SLASH", "LOW")
        positive = points(root, 5)
        update(root, spin=-root["spin"])
        negative = points(root, 5)
        for a, b in zip(positive, negative):
            self.assertAlmostEqual(a[0], b[0], places=5)
            self.assertAlmostEqual(a[1], -b[1], places=5)
            self.assertAlmostEqual(a[2], b[2], places=5)

    def test_authored_surface_controls_and_release(self):
        root = core.create(bpy.context, "ARC_SLASH", "LOW")
        camera()
        bpy.context.scene.camera.data.ortho_scale = 5.5
        peak = render_pixels(5)
        update(root, afterimage=0.0, streaks=0.0, core_width=0.3)
        changed = render_pixels(5)
        self.assertGreater(sum(abs(a - b) for a, b in zip(peak, changed)), 1)
        update(root, dissolve=1.0)
        hidden = render_pixels(5)
        self.assertLess(max(c for i, c in enumerate(hidden) if i % 4 != 3), 0.01)
        update(root, dissolve=0.15)
        tail = render_pixels(13)
        self.assertLess(sum(tail[::4]), sum(peak[::4]) * 0.3)
        # Isolate fragment fading from noise erosion and resolve the narrow
        # surviving bands, rather than asserting on a single 48px sample.
        bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 96
        update(root, breakup=0.0, dissolve=0.0)
        tail = render_pixels(11)
        update(root, fade=0.0)
        held = render_pixels(11)
        self.assertGreater(sum(held[::4]), sum(tail[::4]) * 1.5)

    def test_colored_wake_area_preserves_the_main_blade(self):
        root = slash.create(bpy.context, "LOW")
        band_size = len(root.children[0].data.vertices) // 3
        peak = points(root, 5)
        update(root, afterimage=0.0)
        hidden = points(root, 5)
        self.assertEqual(hidden[:band_size], peak[:band_size])
        self.assertNotEqual(hidden[band_size:], peak[band_size:])
        for band in (1, 2):
            for section in range(33):
                row = hidden[band * band_size + section * 6 : band * band_size + (section + 1) * 6]
                radii = [math.hypot(p[0], p[1]) for p in row]
                self.assertLess(max(radii) - min(radii), 1e-5)

    def test_complete_asset_keeps_manual_nodes_and_independent_ids(self):
        root = slash.create(bpy.context)
        update(root, attack=0.12, afterimage=0.4)
        root.children[0].data.materials[0].node_tree.nodes.new("ShaderNodeValue").name = "User Edit"
        data = presets.loads(presets.dumps(core.preset_snapshot(root)))
        restored = core.create_from_preset(bpy.context, data)
        self.assertEqual(restored["attack"], 0.12)
        self.assertEqual(points(root, 5), points(restored, 5))
        path = ROOT / "work/current-slash.blend"
        path.parent.mkdir(exist_ok=True)
        assets.write(path, root)
        loaded = assets.load(bpy.context, path)
        self.assertEqual(points(root, 5), points(loaded, 5))
        self.assertIn("User Edit", loaded.children[0].data.materials[0].node_tree.nodes)
        self.assertNotEqual(loaded["vfx_id"], root["vfx_id"])
        core.delete(root)
        self.assertTrue(mesh(loaded, 5).vertices)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(SlashTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Slash behavior failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = slash.create(bpy.context, "LOW")
root.name = "Persisted Slash"
camera()
bpy.context.scene.camera.data.ortho_scale = 5.5
for frame in (2, 5, 13):
    root[f"expected_shape_{frame}"] = [c for point in points(root, frame) for c in point]
    root[f"expected_pixels_{frame}"] = render_pixels(frame)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/slash.blend"))
print("SLASH_INTEGRATION_OK")
