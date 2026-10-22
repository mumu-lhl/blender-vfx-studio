"""Run with Blender --background --factory-startup --python-exit-code 1."""

import math
import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import core, presets


def radius(root, frame):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    mesh = root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    return max((math.hypot(v.co.x, v.co.y) for v in mesh.vertices), default=0)


def update(root, **values):
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


class BlenderTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.frame_set(1)

    def test_register_operators_and_quality(self):
        for quality, count in [("LOW", 64), ("MEDIUM", 128), ("HIGH", 256)]:
            self.assertEqual(bpy.ops.vfx_studio.create(quality=quality), {"FINISHED"})
            root = core.resolve(bpy.context.object)
            self.assertEqual(len(root.children[0].data.vertices), count)
            self.assertEqual(bpy.ops.vfx_studio.duplicate(), {"FINISHED"})
            self.assertEqual(bpy.ops.vfx_studio.delete(), {"FINISHED"})
            core.delete(root)
        self.assertEqual(len(bpy.data.objects), 0)
        self.assertEqual(len(bpy.data.meshes), 0)
        self.assertEqual(len(bpy.data.node_groups), 0)
        self.assertEqual(len(bpy.data.materials), 0)

    def test_scrub_parameters_and_independent_instances(self):
        root = core.create(bpy.context)
        second = core.create(bpy.context, "ENERGY_RING")
        for frame in (13, 1, 24, 0, 25, 7, 100, 12):
            expected = 0.2 + (frame - 1) / 24 * 3 if 1 <= frame < 25 else 0
            self.assertAlmostEqual(radius(root, frame), expected, places=5)
        update(root, start=5.0, duration=10.0, speed=2.0, loop=True, radius=1.0)
        self.assertAlmostEqual(radius(root, 4), 0)
        self.assertAlmostEqual(radius(root, 10), 1, places=5)
        self.assertAlmostEqual(radius(root, 12), 2.2, places=5)
        self.assertAlmostEqual(radius(second, 12), 1.5, places=5)
        layer = root.children[0]
        for data in (layer, layer.data.materials[0].node_tree):
            for curve in data.animation_data.drivers:
                self.assertTrue(curve.driver.is_valid, curve.data_path)
                self.assertTrue(curve.driver.is_simple_expression, curve.driver.expression)
        update(root, dissolve=0.8, strength=3.0)
        radius(root, 13)
        tree = layer.data.materials[0].node_tree
        self.assertAlmostEqual(tree.nodes["Dissolve Threshold"].inputs[1].default_value, 0.8)
        self.assertAlmostEqual(tree.nodes["Emission"].inputs["Strength"].default_value, 3.0)

    def test_duplicate_preserves_edits_and_animation_independently(self):
        root = core.create(bpy.context)
        root["radius"] = 1.0
        root.keyframe_insert('["radius"]', frame=1)
        root["radius"] = 2.0
        root.keyframe_insert('["radius"]', frame=13)
        layer = root.children[0]
        material = layer.data.materials[0]
        material.node_tree.nodes.new("ShaderNodeValue").label = "User Edit"
        copy = core.duplicate(bpy.context, root)
        self.assertNotEqual(root["vfx_id"], copy["vfx_id"])
        self.assertIsNot(root.animation_data.action, copy.animation_data.action)
        self.assertIsNot(layer.data, copy.children[0].data)
        self.assertIsNot(material, copy.children[0].data.materials[0])
        self.assertTrue(
            any(n.label == "User Edit" for n in copy.children[0].data.materials[0].node_tree.nodes)
        )
        update(copy, expansion=5.0)
        self.assertAlmostEqual(radius(root, 13), 3.5, places=5)
        self.assertAlmostEqual(radius(copy, 13), 4.5, places=5)
        for data in (copy.children[0], copy.children[0].data.materials[0].node_tree):
            for curve in data.animation_data.drivers:
                for var in curve.driver.variables:
                    self.assertEqual(var.targets[0].id, copy)
        core.delete(root)
        self.assertAlmostEqual(radius(copy, 13), 4.5, places=5)

    def test_duplicate_with_user_material_without_nodes(self):
        root = core.create(bpy.context)
        plain = bpy.data.materials.new("Plain User Material")
        root.children[0].data.materials.append(plain)
        clone = core.duplicate(bpy.context, root)
        self.assertEqual(len(clone.children[0].data.materials), 2)
        self.assertIsNot(clone.children[0].data.materials[1], plain)
        core.delete(clone)
        self.assertIn(plain.name, bpy.data.materials)

    def test_safe_delete_foreign_children_shared_assets_and_collection(self):
        root = core.create(bpy.context)
        layer = root.children[0]
        collection = root.users_collection[0]
        user = bpy.data.objects.new("User Object", layer.data)
        collection.objects.link(user)
        user.parent = layer
        user.location = (2, 3, 4)
        bpy.context.view_layer.update()
        before = user.matrix_world.copy()
        group = layer.modifiers[0].node_group
        mod = user.modifiers.new("User GN", "NODES")
        mod.node_group = group
        with self.assertRaisesRegex(ValueError, "shared"):
            core.delete(root)
        user.data = user.data.copy()
        del user.data["vfx_id"]
        with self.assertRaisesRegex(ValueError, "material is shared"):
            core.delete(root)
        foreign = bpy.data.materials.new("User Material")
        user.data.materials.clear()
        user.data.materials.append(foreign)
        with self.assertRaisesRegex(ValueError, "node group is shared"):
            core.delete(root)
        user.modifiers.remove(mod)
        # User-created nodes/materials assigned to a VFX layer must survive.
        layer.data.materials.append(foreign)
        core.delete(root)
        self.assertIsNone(user.parent)
        self.assertEqual(user.matrix_world, before)
        self.assertEqual(len(user.data.vertices), 128)
        self.assertEqual(user.data.materials[0], foreign)
        self.assertIn(user.name, collection.objects)

    def test_preset_file_operators_and_invalid_import_are_isolated(self):
        root = core.create(bpy.context, quality="LOW")
        update(root, radius=0.8, speed=2.0, loop=True)
        (ROOT / "work").mkdir(exist_ok=True)
        filepath = str(ROOT / "work" / "roundtrip.json")
        self.assertEqual(bpy.ops.vfx_studio.export_preset(filepath=filepath), {"FINISHED"})
        data = presets.read(filepath)
        self.assertNotIn("start", data["parameters"])
        bpy.context.scene.frame_set(50)
        self.assertEqual(bpy.ops.vfx_studio.import_preset(filepath=filepath), {"FINISHED"})
        imported = bpy.context.object
        self.assertNotEqual(root["vfx_id"], imported["vfx_id"])
        self.assertEqual(imported["start"], 50)
        self.assertEqual(imported["vfx_quality"], "LOW")
        self.assertEqual(imported["loop"], True)
        self.assertAlmostEqual(radius(imported, 56), 2.3, places=5)
        count = len(bpy.data.objects)
        data["parameters"]["radius"] = -1
        with self.assertRaises(ValueError):
            core.create_from_preset(bpy.context, data)
        self.assertEqual(len(bpy.data.objects), count)
        self.assertEqual(root["radius"], 0.8)

    def test_manual_duplicate_identity_and_future_schema_rejected(self):
        root = core.create(bpy.context)
        copy = root.copy()
        bpy.context.scene.collection.objects.link(copy)
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            core.delete(root)
        bpy.data.objects.remove(copy, do_unlink=True)
        root["vfx_schema"] = 999
        with self.assertRaisesRegex(ValueError, "schema"):
            core.duplicate(bpy.context, root)
        root["vfx_schema"] = 1
        root["vfx_asset_version"] = 999
        with self.assertRaisesRegex(ValueError, "asset version"):
            core.duplicate(bpy.context, root)
        with self.assertRaisesRegex(ValueError, "asset version"):
            core.delete(root)
        self.assertIn(root.name, bpy.data.objects)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(BlenderTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Blender integration tests failed")
# Persist a deterministic fixture, then strip the Python UI before saving.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.frame_set(1)
root = core.create(bpy.context)
copy = core.duplicate(bpy.context, root)
copy.name = "Persisted Copy"
update(copy, radius=1.0)
imported = core.create_from_preset(bpy.context, core.preset_snapshot(copy))
imported.name = "Persisted Preset"
addon.unregister()
addon.register()
addon.unregister()
bpy.context.scene.frame_set(13)
(ROOT / "work").mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work" / "native.blend"))
print("BLENDER_INTEGRATION_OK", bpy.app.version_string)
