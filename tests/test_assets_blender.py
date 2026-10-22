"""Complete native asset reuse, repeated imports and non-destructive failures."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import assets, binding, composition, core, simulation, trail

FILE = ROOT / "work/effect-asset.blend"


def mesh(root, frame):
    bpy.context.scene.frame_set(frame)
    return root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data


def ring():
    bpy.context.scene.frame_set(1)
    root = core.create(bpy.context)
    root["radius"], root["expansion"] = 1.0, 0.0
    root.update_tag()
    return root


def group():
    root = ring()
    source = bpy.data.objects.new("User Source", None)
    bpy.context.scene.collection.objects.link(source)
    for frame, x in ((1, 0), (25, 2)):
        source.location.x = x
        source.keyframe_insert(data_path="location", frame=frame)
    ribbon = trail.create(bpy.context, source, first=1, last=25)
    cloth = simulation.create(bpy.context)
    simulation.bake(bpy.context, cloth)
    result = composition.create(bpy.context, [root, ribbon, cloth])
    return result, ribbon, source


class AssetTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_repeated_import_preserves_nodes_animation_and_independence(self):
        root = ring()
        root.children[0].data.materials[0].node_tree.nodes.new(
            "ShaderNodeValue"
        ).name = "Artist Edit"
        for frame, radius in ((1, 1.0), (13, 2.0)):
            root["radius"] = radius
            root.keyframe_insert(data_path='["radius"]', frame=frame)
        for frame, x in ((1, 3.0), (13, 6.0)):
            root.location.x = x
            root.keyframe_insert(data_path="location", frame=frame)
        bpy.context.scene.frame_set(1)
        self.assertEqual(bpy.ops.vfx_studio.export_asset(filepath=str(FILE)), {"FINISHED"})
        self.assertEqual(bpy.ops.vfx_studio.import_asset(filepath=str(FILE)), {"FINISHED"})
        a = bpy.context.object
        b = assets.load(bpy.context, FILE)
        self.assertEqual(len({root["vfx_id"], a["vfx_id"], b["vfx_id"]}), 3)
        self.assertEqual(a.location.x, 3.0)
        self.assertEqual(a["start"], 1.0)
        self.assertIn("Artist Edit", a.children[0].data.materials[0].node_tree.nodes)
        self.assertAlmostEqual(max(v.co.length for v in mesh(a, 13).vertices), 2, places=5)
        self.assertAlmostEqual(a.location.x, 6.0)
        a.animation_data_clear()
        a["radius"] = 4.0
        a.update_tag()
        self.assertAlmostEqual(max(v.co.length for v in mesh(a, 7).vertices), 4, places=5)
        self.assertLess(max(v.co.length for v in mesh(b, 7).vertices), 2.1)
        for item in (a, b, root):
            core.delete(item)
        self.assertFalse(bpy.data.objects)
        self.assertFalse(bpy.data.meshes)
        self.assertFalse(bpy.data.materials)
        self.assertFalse(bpy.data.node_groups)

    def test_composition_keeps_trail_and_cloth_without_exporting_source(self):
        original, ribbon, source = group()
        original_ids = set(bpy.data.all_ids)
        assets.write(FILE, original)
        self.assertEqual(set(bpy.data.all_ids), original_ids)
        self.assertEqual(ribbon["vfx_source"], source)
        a = assets.load(bpy.context, FILE)
        children = composition.members(a)
        self.assertEqual(len(children), 3)
        self.assertEqual(len(bpy.data.objects), 17)  # 8 per group plus the user's source
        for child in children:
            self.assertEqual(core.resolve(child), child)
            self.assertEqual(child["vfx_composition"], a)
            if child["vfx_module"] == "trail.ribbon":
                self.assertIsNone(child.get("vfx_source"))
                self.assertTrue(mesh(child, 13).vertices)
            if child["vfx_module"] == "simulation.cloth":
                self.assertEqual(simulation.state(bpy.context, child), "BAKED")
                cloth_source, output, _ = simulation.parts(child)
                self.assertTrue(cloth_source.hide_get())
                self.assertEqual(len(output.data.shape_keys.key_blocks), 25)
        core.delete(original)
        clone = core.duplicate(bpy.context, a)
        core.delete(a)
        self.assertEqual(len(composition.members(clone)), 3)
        core.delete(clone)
        self.assertEqual(list(bpy.data.objects), [source])

    def test_external_dependencies_refused_and_old_file_is_preserved(self):
        root = ring()
        assets.write(FILE, root)
        previous = FILE.read_bytes()
        target = bpy.data.objects.new("User Rig", None)
        bpy.context.scene.collection.objects.link(target)
        binding.bind(bpy.context, root, target)
        before = set(bpy.data.all_ids)
        with self.assertRaisesRegex(ValueError, "external object"):
            assets.write(FILE, root)
        self.assertEqual(set(bpy.data.all_ids), before)
        self.assertEqual(FILE.read_bytes(), previous)
        binding.unbind(bpy.context, root)
        root["vfx_asset_version"] = 999
        with self.assertRaisesRegex(ValueError, "version"):
            assets.write(FILE, root)
        self.assertEqual(FILE.read_bytes(), previous)

    def test_invalid_bundle_rolls_back_only_new_data(self):
        root = ring()
        assets.write(FILE, root)
        before = set(bpy.data.all_ids)
        with patch.object(assets, "BUNDLE_VERSION", 999):
            with self.assertRaisesRegex(ValueError, "bundle version"):
                assets.load(bpy.context, FILE)
        self.assertEqual(set(bpy.data.all_ids), before)
        with patch.object(assets, "_validate", side_effect=ValueError("Rejected")):
            with self.assertRaisesRegex(ValueError, "Rejected"):
                assets.load(bpy.context, FILE)
        self.assertEqual(set(bpy.data.all_ids), before)
        # A regular project with no exported collection is not a native-effect bundle.
        ordinary = ROOT / "work/ordinary.blend"
        bpy.data.libraries.write(str(ordinary), {root})
        with self.assertRaisesRegex(ValueError, "one exported"):
            assets.load(bpy.context, ordinary)
        self.assertEqual(set(bpy.data.all_ids), before)

    def test_packed_images_roundtrip_and_unpacked_files_are_refused(self):
        image = bpy.data.images.new("User Image", 4, 4)
        image.generated_color = (0.1, 0.5, 0.8, 1)
        image.filepath_raw = str(ROOT / "work/asset-image.png")
        image.file_format = "PNG"
        image.save()
        self.assertEqual(image.source, "FILE")
        root = core.create_flipbook(bpy.context, image, 1, 1)
        with self.assertRaisesRegex(ValueError, "Pack still images"):
            assets.write(FILE, root)
        image.pack()
        assets.write(FILE, root)
        Path(image.filepath_raw).unlink()
        a = assets.load(bpy.context, FILE)
        imported_image = core.atlas_node(a).image
        self.assertIsNot(imported_image, image)
        self.assertTrue(imported_image.packed_file)
        self.assertEqual(list(imported_image.pixels), list(image.pixels))
        core.delete(a)
        self.assertIsNotNone(image.packed_file)
        self.assertIn(imported_image, list(bpy.data.images))

    def test_failed_export_restores_trail_reference_and_project_file_is_protected(self):
        original, ribbon, source = group()
        before = set(bpy.data.all_ids)
        with patch.object(assets.os, "replace", side_effect=OSError("Disk")):
            with self.assertRaisesRegex(OSError, "Disk"):
                assets.write(FILE, original)
        self.assertEqual(ribbon["vfx_source"], source)
        self.assertEqual(set(bpy.data.all_ids), before)
        project = ROOT / "work/protected-project.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(project))
        with self.assertRaisesRegex(ValueError, "current project"):
            assets.write(project, original)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(AssetTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Native assets integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
original, _, _ = group()
assets.write(FILE, original)
loaded = assets.load(bpy.context, FILE)
loaded.name = "Persisted Native Asset"
core.delete(original)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/assets.blend"))
print("ASSETS_INTEGRATION_OK")
