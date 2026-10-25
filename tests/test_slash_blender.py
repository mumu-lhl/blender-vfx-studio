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
    root = slash.create(bpy.context, asset_version=1)
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

    def test_arc_and_spin_bounds_at_arbitrary_frames(self):
        root = create()
        result = mesh(root, 1)
        self.assertGreaterEqual(min(v.co.x for v in result.vertices), -1e-5)
        self.assertAlmostEqual(max(v.co.x for v in result.vertices), 2, places=5)
        self.assertAlmostEqual(min(v.co.length for v in result.vertices), 1.5, places=5)
        halfway = points(root, 13)
        self.assertGreaterEqual(min(p[1] for p in halfway), -1e-5)
        self.assertAlmostEqual(max(p[0] for p in halfway), 2, places=5)
        self.assertEqual(points(root, 25), [])
        self.assertEqual(points(root, 0), [])
        update(root, speed=2.0)
        self.assertEqual(points(root, 7), halfway)
        update(root, loop=True)
        self.assertEqual(points(root, 13), points(root, 1))

    def test_taper_width_and_radius_stay_finite(self):
        root = create()
        area = sum(p.area for p in mesh(root, 1).polygons)
        update(root, taper=4.0)
        self.assertLess(sum(p.area for p in mesh(root, 1).polygons), area * 0.8)
        update(root, width=10.0, arc=359.0)
        result = mesh(root, 1)
        self.assertTrue(all(math.isfinite(c) for v in result.vertices for c in v.co))
        self.assertGreaterEqual(min(v.co.length for v in result.vertices), 0.00099)
        update(root, spin=-360.0, expansion=1.0)
        self.assertAlmostEqual(max(v.co.length for v in mesh(root, 13).vertices), 2.5, places=5)

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

    def test_cpu_render_contains_only_the_selected_arc(self):
        root = create()
        update(
            root,
            radius=1.5,
            width=0.6,
            spin=0.0,
            taper=0.01,
            dissolve=0.0,
            fade=0.0,
            strength=1.0,
            color_0=0.0,
            color_1=0.0,
            color_2=1.0,
        )
        camera()
        pixels = render_pixels(1)
        left, right = (24 * 48 + 10) * 4, (24 * 48 + 38) * 4
        self.assertLess(max(pixels[left : left + 3]), 0.01)
        self.assertGreater(pixels[right + 2], 0.3)
        self.assertLess(max(pixels[right : right + 2]), 0.01)

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
        self.assertTrue(0 < counts[0] < counts[1] < counts[2] < 5000)

    def test_modern_geometry_parameters_and_stateless_playback(self):
        root = slash.create(bpy.context, "LOW", asset_version=2)
        self.assertEqual(root["vfx_asset_version"], 2)
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
        self.assertLess(len(mesh(root, 5).vertices), 1000)

    def test_modern_render_has_attack_peak_release_and_editable_detail(self):
        root = slash.create(bpy.context, asset_version=2)
        camera()
        bpy.context.scene.camera.data.ortho_scale = 5.5
        frames = [render_pixels(frame) for frame in (2, 5, 13)]

        def energy(pixels):
            return sum(sum(pixels[i : i + 3]) for i in range(0, len(pixels), 4))

        self.assertGreater(energy(frames[1]), energy(frames[0]) * 1.5)
        self.assertLess(energy(frames[2]), energy(frames[1]) * 0.4)
        self.assertTrue(any(min(frames[1][i : i + 3]) > 0.3 for i in range(0, len(frames[1]), 4)))
        self.assertTrue(
            any(
                frames[1][i + 2] > 0.15 and frames[1][i + 1] < 0.12
                for i in range(0, len(frames[1]), 4)
            )
        )
        update(root, afterimage=0.0, streaks=0.0)
        plain = render_pixels(5)
        self.assertGreater(sum(abs(a - b) for a, b in zip(plain, frames[1])), 1)
        update(root, breakup=0.0)
        intact = render_pixels(13)
        update(root, breakup=1.0)
        eroded = render_pixels(13)
        self.assertLess(energy(eroded), energy(intact) * 0.8)
        update(root, dissolve=1.0)
        dissolved = render_pixels(5)
        self.assertLess(max(dissolved[i] for i in range(len(dissolved)) if i % 4 != 3), 0.01)

    def test_modern_asset_and_legacy_preset_roundtrip_preserve_versions(self):
        legacy = create()
        legacy_data = presets.loads(presets.dumps(core.preset_snapshot(legacy)))
        self.assertEqual(legacy_data["asset_version"], 1)
        old_copy = core.create_from_preset(bpy.context, legacy_data)
        self.assertEqual(old_copy["vfx_asset_version"], 1)
        self.assertNotIn("afterimage", old_copy)
        self.assertEqual(points(legacy, 7), points(old_copy, 7))
        bpy.context.scene.frame_set(1)
        modern = slash.create(bpy.context, asset_version=2)
        update(modern, attack=0.12, core_width=0.08, afterimage=0.4, breakup=0.6)
        modern.children[0].data.materials[0].node_tree.nodes.new(
            "ShaderNodeValue"
        ).name = "User Filament Edit"
        data = presets.loads(presets.dumps(core.preset_snapshot(modern)))
        restored = core.create_from_preset(bpy.context, data)
        self.assertEqual(restored["attack"], 0.12)
        self.assertEqual(restored["afterimage"], 0.4)
        file = ROOT / "work/modern-slash.blend"
        assets.write(file, modern)
        loaded = assets.load(bpy.context, file)
        self.assertEqual(points(modern, 5), points(loaded, 5))
        self.assertIn("User Filament Edit", loaded.children[0].data.materials[0].node_tree.nodes)
        self.assertNotEqual(loaded["vfx_id"], modern["vfx_id"])
        core.delete(modern)
        self.assertTrue(mesh(loaded, 5).vertices)
        for obj in (loaded, restored, legacy, old_copy):
            core.delete(obj)
        self.assertEqual(len(bpy.data.meshes), 0)
        self.assertEqual(len(bpy.data.materials), 0)

    def test_authored_shape_controls_budget_and_retiming(self):
        root = core.create(bpy.context, "ARC_SLASH", "LOW")
        self.assertEqual(root["vfx_asset_version"], 4)
        peak = points(root, 5)
        self.assertLessEqual(len(peak), 600)
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
        self.assertEqual(snapshot["asset_version"], 4)

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

    def test_version_two_preset_retains_the_flat_regular_shape(self):
        root = slash.create(bpy.context, "LOW", asset_version=2)
        update(root, spin=0.0, expansion=0.0)
        data = presets.loads(presets.dumps(core.preset_snapshot(root)))
        restored = core.create_from_preset(bpy.context, data)
        self.assertEqual(points(root, 5), points(restored, 5))
        self.assertNotIn("contour", restored)
        result = mesh(restored, 5)
        outer = [result.vertices[i].co.length for i in range(0, 198, 6)]
        self.assertLess(max(outer) - min(outer), 1e-5)
        self.assertTrue(all(abs(v.co.z) < 1e-6 for v in result.vertices))

    def test_version_three_preset_retains_its_shape_and_rendered_appearance(self):
        old = slash.create(bpy.context, "LOW", asset_version=3)
        camera()
        bpy.context.scene.camera.data.ortho_scale = 5.5
        expected_shape = points(old, 5)
        expected_pixels = render_pixels(5)
        snapshot = presets.loads(presets.dumps(core.preset_snapshot(old)))
        restored = core.create_from_preset(bpy.context, snapshot)
        update(restored, start=1.0)
        old.children[0].hide_render = True
        self.assertEqual(restored["vfx_asset_version"], 3)
        self.assertEqual(points(restored, 5), expected_shape)
        self.assertEqual(render_pixels(5), expected_pixels)

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


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(SlashTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Slash integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = create()
root.name = "Persisted Slash"
modern = slash.create(bpy.context, "LOW", asset_version=2)
modern.name = "Persisted Layered Slash"
for frame in (2, 5, 13):
    result = mesh(modern, frame)
    modern[f"expected_shape_{frame}"] = [c for vertex in result.vertices for c in vertex.co]
root.hide_render = modern.hide_render = True
root.children[0].hide_render = modern.children[0].hide_render = True
camera()
bpy.context.scene.camera.data.ortho_scale = 5.5
for version, name in ((3, "Persisted Version Three Slash"), (4, "Persisted Authored Slash")):
    authored = slash.create(bpy.context, "LOW", asset_version=version)
    authored.name = name
    # The preceding evaluation changed the scene frame; explicitly align clocks.
    update(authored, start=1.0)
    for obj in bpy.context.scene.objects:
        if obj.get("vfx_role") == "layer":
            obj.hide_render = obj != authored.children[0]
    for frame in (2, 5, 13):
        authored[f"expected_shape_{frame}"] = [
            c for point in points(authored, frame) for c in point
        ]
        authored[f"expected_pixels_{frame}"] = render_pixels(frame)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/slash.blend"))
print("SLASH_INTEGRATION_OK")
