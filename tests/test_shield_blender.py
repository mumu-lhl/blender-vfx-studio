"""Observable shield geometry, ownership, presets and CPU-rendered Fresnel opacity."""

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
from blender_vfx_studio import core, presets


def update(root, **values):
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


def mesh(root, frame):
    bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1)
    return root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data


def render_setup(root):
    update(
        root,
        dissolve=0.0,
        fade=0.0,
        opacity=1.0,
        strength=1.0,
        color_0=0.0,
        color_1=0.0,
        color_2=1.0,
    )
    camera()
    bpy.context.scene.cycles.samples = 32
    bpy.context.scene.render.film_transparent = True


class ShieldTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_radius_lifetime_subframe_speed_and_loop(self):
        bpy.context.scene.frame_set(7, subframe=0.5)
        root = core.create_shield(bpy.context)
        self.assertEqual(root["start"], 7.5)
        update(root, radius=1.0, expansion=2.0, duration=12.0, loop=False)
        self.assertFalse(mesh(root, 7.25).vertices)
        self.assertAlmostEqual(max(v.co.length for v in mesh(root, 7.5).vertices), 1, places=5)
        self.assertAlmostEqual(max(v.co.length for v in mesh(root, 13.5).vertices), 2, places=5)
        self.assertFalse(mesh(root, 19.5).vertices)
        update(root, speed=2.0)
        self.assertAlmostEqual(max(v.co.length for v in mesh(root, 10.5).vertices), 2, places=5)
        update(root, loop=True)
        self.assertAlmostEqual(max(v.co.length for v in mesh(root, 13.5).vertices), 1, places=5)

    def test_preset_duplicate_edited_nodes_and_safe_delete(self):
        root = core.create_shield(bpy.context)
        update(root, ior=1.7, rim_power=2.0, radius=2.25, flow=-1.0)
        tree = root.children[0].data.materials[0].node_tree
        tree.nodes.new("ShaderNodeValue").name = "Artist Note"
        data = presets.loads(presets.dumps(core.preset_snapshot(root)))
        restored = core.create_from_preset(bpy.context, data)
        self.assertEqual(restored["vfx_module"], "shader.shield")
        self.assertEqual(restored["ior"], 1.7)
        clone = core.duplicate(bpy.context, root)
        update(clone, radius=1.0, ior=1.2, strength=7.0)
        mesh(clone, 1)
        self.assertAlmostEqual(
            clone.children[0]
            .data.materials[0]
            .node_tree.nodes["Shield Emission"]
            .inputs["Strength"]
            .default_value,
            7.0,
        )
        self.assertAlmostEqual(tree.nodes["Shield Emission"].inputs["Strength"].default_value, 3.0)
        self.assertIn("Artist Note", clone.children[0].data.materials[0].node_tree.nodes)
        self.assertAlmostEqual(max(v.co.length for v in mesh(root, 1).vertices), 2.25, places=5)
        self.assertAlmostEqual(max(v.co.length for v in mesh(clone, 1).vertices), 1, places=5)
        foreign = bpy.data.objects.new("User mesh", root.children[0].data)
        bpy.context.scene.collection.objects.link(foreign)
        with self.assertRaises(ValueError):
            core.delete(root)
        self.assertIsNotNone(core.resolve(root))
        bpy.data.objects.remove(foreign, do_unlink=True)
        for item in (root, clone, restored):
            core.delete(item)
        self.assertFalse(bpy.data.meshes)
        self.assertFalse(bpy.data.materials)
        self.assertFalse(bpy.data.node_groups)

    def test_quality_operator_simple_drivers_and_normals(self):
        counts = []
        for quality in ("LOW", "MEDIUM", "HIGH"):
            self.assertEqual(bpy.ops.vfx_studio.create_shield(quality=quality), {"FINISHED"})
            root = bpy.context.object
            layer = root.children[0]
            counts.append(len(mesh(root, 1).polygons))
            self.assertTrue(all(p.normal.dot(p.center) > 0 for p in layer.data.polygons))
            for data in (layer.modifiers[0].node_group, layer.data.materials[0].node_tree):
                self.assertTrue(
                    all(
                        c.driver.is_valid and c.driver.is_simple_expression
                        for c in data.animation_data.drivers
                    )
                )
            core.delete(root)
        self.assertEqual(counts, [128, 512, 2048])
        with self.assertRaises(ValueError):
            core.create_shield(bpy.context, "INVALID")
        self.assertFalse(bpy.data.objects)

    def test_cpu_render_rim_opacity_dissolve_and_inside_surface(self):
        root = core.create_shield(bpy.context)
        render_setup(root)
        pixels = render_pixels(1)
        center = (24 * 48 + 24) * 4
        rim = (24 * 48 + 40) * 4
        self.assertLess(pixels[center + 3], 0.16)
        self.assertGreater(pixels[rim + 3], 0.18)
        self.assertGreater(pixels[rim + 3], pixels[center + 3] * 2)
        self.assertGreater(pixels[rim + 2], 0.5)
        self.assertLess(max(pixels[rim : rim + 2]), 0.01)
        update(root, dissolve=1.0)
        self.assertLess(max(render_pixels(1)[3::4]), 0.01)
        update(root, dissolve=0.0, loop=False)
        self.assertLess(max(render_pixels(25)[3::4]), 0.01)
        bpy.context.scene.camera.location.z = 0
        self.assertLess(max(render_pixels(1)[3::4]), 0.01)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(ShieldTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Shield integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = core.create_shield(bpy.context)
root.name = "Persisted Shield"
render_setup(root)
update(root, radius=1.0, expansion=1.0, loop=False)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/shield.blend"))
print("SHIELD_INTEGRATION_OK")
