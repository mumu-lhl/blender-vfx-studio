"""Starter assets remain independent of preview-scene helpers and authoring code."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import assets, composition, core
from tools.build_examples import EXAMPLES, create_effect, main, preview_scene

WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)


def vertex_count(root, frame):
    bpy.context.scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    return sum(
        len(obj.evaluated_get(graph).data.vertices)
        for obj in root.children_recursive
        if obj.get("vfx_role") == "layer" and obj.type == "MESH"
    )


class StarterTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_builders_are_low_quality_bounded_and_have_native_timing(self):
        for key, layers, duration in zip(EXAMPLES, (4, 4, 1), (48, 24, 18)):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            root = create_effect(key)
            self.assertEqual(root["start"], 1)
            self.assertEqual(root["duration"], duration)
            self.assertFalse(root["loop"])
            members = (
                composition.members(root) if root["vfx_module"] == "core.composition" else [root]
            )
            self.assertEqual(len(members), layers)
            self.assertTrue(all(r["vfx_quality"] == "LOW" for r in members))
            count = vertex_count(root, 7)
            self.assertGreater(count, 0)
            self.assertLess(count, 10000)
            self.assertEqual(vertex_count(root, 0), 0)
            self.assertEqual(vertex_count(root, 61), 0)
            self.assertEqual(vertex_count(root, 7), count)
        before = set(bpy.data.all_ids)
        with self.assertRaisesRegex(ValueError, "Unknown"):
            create_effect("missing")
        self.assertEqual(set(bpy.data.all_ids), before)

    def test_generator_refuses_an_open_project_before_changing_data(self):
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.object
        bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "protected-starter-project.blend"))
        before = set(bpy.data.all_ids)
        with self.assertRaisesRegex(RuntimeError, "fresh background"):
            main()
        self.assertEqual(set(bpy.data.all_ids), before)
        self.assertIn(obj.name, bpy.data.objects)
        self.assertEqual(len(obj.data.vertices), 8)

    def test_preview_helpers_are_excluded_and_repeated_imports_are_independent(self):
        for key in EXAMPLES:
            bpy.ops.wm.read_factory_settings(use_empty=True)
            root = create_effect(key)
            preview_scene(key)
            image = bpy.data.images.new("Example Test Preview", 2, 2)
            image.generated_color = (0.1, 0.5, 1, 1)
            file = WORK / ("starter-" + key + ".blend")
            assets.write(file, root, preview_image=image)
            with bpy.data.libraries.load(str(file)) as (available, _):
                self.assertEqual(available.cameras, [])
                self.assertEqual(available.scenes, [])
                self.assertEqual(available.images, [])
                self.assertEqual(available.worlds, [])
            a, b = assets.load(bpy.context, file), assets.load(bpy.context, file)
            self.assertEqual(len({root["vfx_id"], a["vfx_id"], b["vfx_id"]}), 3)
            self.assertEqual(vertex_count(a, 7), vertex_count(b, 7))
            a["duration"] = 100.0
            a.update_tag()
            self.assertNotEqual(a["duration"], b["duration"])
            core.delete(a)
            core.delete(root)
            self.assertGreater(vertex_count(b, 7), 0)
            self.assertEqual(core.resolve(b), b)
            bundle = next(c for c in b.users_collection if c.get("vfx_bundle_version"))
            self.assertTrue(bundle.preview.is_image_custom)
            self.assertEqual(bundle.preview.image_size[:], (2, 2))


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(StarterTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Starter library integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
for key in EXAMPLES:
    root = assets.load(bpy.context, WORK / ("starter-" + key + ".blend"))
    root.name = "Persisted Starter " + key
    for frame in (7, 16):
        root[f"expected_vertices_{frame}"] = vertex_count(root, frame)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "examples.blend"))
print("STARTER_LIBRARY_INTEGRATION_OK")
