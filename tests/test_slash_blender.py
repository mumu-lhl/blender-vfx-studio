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
        root = core.create(bpy.context, "ARC_SLASH", "LOW")
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
        root = core.create(bpy.context, "ARC_SLASH")
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
        modern = core.create(bpy.context, "ARC_SLASH")
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


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(SlashTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Slash integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = create()
root.name = "Persisted Slash"
modern = core.create(bpy.context, "ARC_SLASH", "LOW")
modern.name = "Persisted Layered Slash"
for frame in (2, 5, 13):
    result = mesh(modern, frame)
    modern[f"expected_shape_{frame}"] = [c for vertex in result.vertices for c in vertex.co]
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/slash.blend"))
print("SLASH_INTEGRATION_OK")
