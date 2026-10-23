"""Exercise Blender's real undo stack; GUI clicking remains a separate check."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import asset_browser, assets, composition, core, simulation


def roots(module=None):
    return [
        o
        for o in bpy.data.objects
        if o.get("vfx_role") == "controller" and (module is None or o.get("vfx_module") == module)
    ]


def push(label):
    bpy.ops.ed.undo_push(message=label)


class UndoTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.edit.use_global_undo = True
        push("Empty Scene")

    def test_create_duplicate_delete_undo_redo_restore_native_assets(self):
        bpy.ops.vfx_studio.create()
        push("Created")
        bpy.ops.vfx_studio.duplicate()
        push("Duplicated")
        bpy.ops.vfx_studio.delete()
        push("Deleted")
        self.assertEqual(len(roots()), 1)
        bpy.ops.ed.undo()
        self.assertEqual(len(roots()), 2)
        self.assertEqual(len(bpy.data.meshes), 2)
        self.assertEqual(len({r["vfx_id"] for r in roots()}), 2)
        for root in roots():
            self.assertEqual(core.resolve(root), root)
        bpy.ops.ed.redo()
        self.assertEqual(len(roots()), 1)
        bpy.ops.ed.undo()
        bpy.ops.ed.undo()
        self.assertEqual(len(roots()), 1)
        bpy.ops.ed.undo()
        self.assertEqual(len(bpy.data.objects), 0)
        self.assertEqual(len(bpy.data.meshes), 0)
        bpy.ops.ed.redo()
        self.assertEqual(len(roots()), 1)

    def test_composition_native_id_references_survive_undo(self):
        a = core.create(bpy.context)
        b = core.create_particle(bpy.context)
        b["start"] = 7.0
        b["duration"] = 12.0
        b.update_tag()
        a.select_set(True)
        push("Independent Effects")
        bpy.ops.vfx_studio.compose()
        push("Composed")
        bpy.ops.ed.undo()
        self.assertEqual(len(roots("core.composition")), 0)
        self.assertTrue(all(r.parent is None for r in roots()))
        bpy.ops.ed.redo()
        group = roots("core.composition")[0]
        children = composition.members(group)
        self.assertEqual(len(children), 2)
        group["duration"] = 48.0
        group.update_tag()
        bpy.context.view_layer.update()
        particle = roots("particle.burst")[0]
        self.assertEqual(particle["start"], 13)
        self.assertEqual(particle["vfx_composition"], group)
        core.delete(group)
        push("Deleted Group")
        bpy.ops.ed.undo()
        self.assertEqual(len(composition.members(roots("core.composition")[0])), 2)

    def test_baked_shape_keys_and_clear_restore_with_undo(self):
        bpy.ops.vfx_studio.create_simulation()
        push("Unbaked Cloth")
        bpy.ops.vfx_studio.bake_simulation()
        push("Baked Cloth")
        self.assertEqual(simulation.state(bpy.context, roots()[0]), "BAKED")
        bpy.ops.ed.undo()
        self.assertEqual(simulation.state(bpy.context, roots()[0]), "UNBAKED")
        self.assertEqual(len(bpy.data.shape_keys), 0)
        bpy.ops.ed.redo()
        root = roots()[0]
        self.assertEqual(simulation.state(bpy.context, root), "BAKED")
        bpy.context.scene.frame_set(13)
        output = simulation.parts(root)[1]
        mesh = output.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        self.assertLess(mesh.vertices[0].co.z, 1.2)
        core.select(bpy.context, root)
        bpy.ops.vfx_studio.clear_simulation()
        push("Cleared Cloth")
        self.assertEqual(len(bpy.data.shape_keys), 0)
        bpy.ops.ed.undo()
        self.assertEqual(simulation.state(bpy.context, roots()[0]), "BAKED")

    def test_native_asset_import_undo_redo_keeps_unique_ids_and_drivers(self):
        original = core.create_shield(bpy.context)
        original_id = original["vfx_id"]
        path = ROOT / "work/undo-asset.blend"
        assets.write(path, original)
        push("Original Shield")
        bpy.ops.vfx_studio.import_asset(filepath=str(path))
        push("Imported Shield")
        imported_id = bpy.context.object["vfx_id"]
        self.assertNotEqual(imported_id, original_id)
        bpy.ops.ed.undo()
        self.assertEqual([r["vfx_id"] for r in roots()], [original_id])
        bpy.ops.ed.redo()
        self.assertEqual({r["vfx_id"] for r in roots()}, {original_id, imported_id})
        imported = next(r for r in roots() if r["vfx_id"] == imported_id)
        imported["radius"] = 3.0
        imported.update_tag()
        bpy.context.scene.frame_set(7)
        mesh = imported.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        self.assertAlmostEqual(max(v.co.length for v in mesh.vertices), 3, places=5)
        self.assertTrue(path.is_file())

    def test_asset_browser_import_undo_redo_keeps_independent_ids(self):
        original = core.create(bpy.context)
        original_id = original["vfx_id"]
        path = ROOT / "work/browser-undo-asset.blend"
        assets.write(path, original)
        push("Original Browser Effect")
        area = next(a for a in bpy.context.screen.areas if a.type == "VIEW_3D")
        area.ui_type = "ASSETS"
        try:
            with bpy.context.temp_override(area=area):
                with patch.object(
                    asset_browser, "selection", return_value=(str(path), "Shockwave")
                ):
                    bpy.ops.vfx_studio.load_browser_asset()
                push("Browser Imported Effect")
            imported_id = bpy.context.view_layer.objects.active["vfx_id"]
            self.assertNotEqual(imported_id, original_id)
            bpy.ops.ed.undo()
            self.assertEqual([r["vfx_id"] for r in roots()], [original_id])
            bpy.ops.ed.redo()
            self.assertEqual({r["vfx_id"] for r in roots()}, {original_id, imported_id})
        finally:
            # Undo can replace the screen and invalidate the old Area reference.
            for area in bpy.context.screen.areas:
                if area.type == "FILE_BROWSER":
                    area.type = "VIEW_3D"

    def test_screen_insertion_and_removal_undo_restore_scene_tree(self):
        self.assertIsNone(bpy.context.scene.compositing_node_group)
        bpy.ops.vfx_studio.create_screen()
        push("Inserted Screen")
        bpy.ops.ed.undo()
        self.assertIsNone(bpy.context.scene.compositing_node_group)
        self.assertEqual(len(roots()), 0)
        bpy.ops.ed.redo()
        root = roots("screen.glare")[0]
        self.assertEqual(root["vfx_scene"], bpy.context.scene)
        core.select(bpy.context, root)
        bpy.ops.vfx_studio.delete()
        push("Removed Screen")
        self.assertIsNone(bpy.context.scene.compositing_node_group)
        bpy.ops.ed.undo()
        self.assertIsNotNone(bpy.context.scene.compositing_node_group)
        self.assertEqual(len(roots("screen.glare")), 1)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(UndoTests)
)
addon.unregister()
if not result.wasSuccessful():
    raise RuntimeError("Undo integration failed")
print("NATIVE_UNDO_REDO_OK")
