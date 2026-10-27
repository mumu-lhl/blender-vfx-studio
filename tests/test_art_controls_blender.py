"""Art controls change native results without rebuilding edited nodes."""

import copy
import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon  # noqa: E402
from blender_vfx_studio import assets, core, presets, slash  # noqa: E402
from blender_vfx_studio.animation import curves  # noqa: E402
from blender_vfx_studio.parameters import SLASH_ART_PARAMETERS  # noqa: E402


def points(root, frame):
    bpy.context.scene.frame_set(frame)
    return [
        tuple(v.co)
        for v in root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    ]


class ArtControlsTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_style_preserves_nodes_palette_dimensions_and_timing(self):
        root = slash.create(bpy.context, "LOW")
        root.vfx_primary_color = (1, 0.2, 0.03)
        root.vfx_blade_color = (1, 0.75, 0.08)
        geometry = root.children[0].modifiers[0].node_group
        material = root.children[0].data.materials[0].node_tree
        material.nodes.new("ShaderNodeValue").name = "Artist Note"
        pointers = (geometry.as_pointer(), material.as_pointer())
        values = {
            k: root[k]
            for k in ("radius", "width", "start", "duration", "speed", "color_0", "blade_color_1")
        }
        shaped = points(root, 5)
        self.assertEqual(bpy.ops.vfx_studio.slash_style(style="CLEAN"), {"FINISHED"})
        self.assertTrue(all(abs(p[2]) < 1e-7 for p in points(root, 5)))
        self.assertEqual(values, {k: root[k] for k in values})
        self.assertEqual((geometry.as_pointer(), material.as_pointer()), pointers)
        self.assertIn("Artist Note", material.nodes)
        bpy.ops.vfx_studio.slash_style(style="STYLIZED")
        self.assertEqual(points(root, 5), shaped)

    def test_color_picker_keys_native_channels(self):
        root = slash.create(bpy.context, "LOW")
        root.vfx_primary_color = (1, 0.2, 0.03)
        root.vfx_blade_color = (1, 0.75, 0.08)
        self.assertAlmostEqual(root["color_1"], 0.2, places=6)
        self.assertAlmostEqual(root["blade_color_1"], 0.75, places=6)
        self.assertFalse(root.bl_rna.properties["vfx_primary_color"].is_animatable)
        for palette in ("BODY", "BLADE"):
            self.assertEqual(bpy.ops.vfx_studio.key_color(palette=palette), {"FINISHED"})
        paths = {f.data_path for f in curves(root)}
        self.assertEqual(
            paths, {f'["{prefix}_{i}"]' for prefix in ("color", "blade_color") for i in range(3)}
        )
        data = presets.loads(presets.dumps(core.preset_snapshot(root)))
        loaded = core.create_from_preset(bpy.context, data)
        self.assertAlmostEqual(loaded["blade_color_1"], 0.75, places=6)

    def test_accepted_snapshot_gets_safe_art_defaults_without_mutation(self):
        root = slash.create(bpy.context, "LOW")
        data = core.preset_snapshot(root)
        for key in SLASH_ART_PARAMETERS:
            data["parameters"].pop(key)
        before = copy.deepcopy(data)
        loaded = core.create_from_preset(bpy.context, data)
        self.assertEqual(data, before)
        self.assertEqual(points(root, 5), points(loaded, 5))
        self.assertEqual(loaded["surface_cuts"], 1)
        self.assertEqual(loaded["fragment_release"], 1)

    def test_custom_complete_asset_keeps_its_saved_shader(self):
        root = slash.create(bpy.context, "LOW")
        material = root.children[0].data.materials[0].node_tree
        # A manually authored material is preserved, with no forced new controls.
        material.nodes.clear()
        emit = material.nodes.new("ShaderNodeEmission")
        emit.name = "Artist Surface"
        out = material.nodes.new("ShaderNodeOutputMaterial")
        material.links.new(emit.outputs[0], out.inputs["Surface"])
        for key in SLASH_ART_PARAMETERS:
            del root[key]
        root.vfx_primary_color = (0.8, 0.3, 0.1)
        core.preset_snapshot(root)
        path = ROOT / "work/custom-art-slash.blend"
        path.parent.mkdir(exist_ok=True)
        assets.write(path, root)
        loaded = assets.load(bpy.context, path)
        self.assertIn("Artist Surface", loaded.children[0].data.materials[0].node_tree.nodes)
        self.assertNotIn("surface_cuts", loaded)
        with self.assertRaises(ValueError):
            slash.apply_style(loaded, "CLEAN")
        self.assertIn("Artist Surface", loaded.children[0].data.materials[0].node_tree.nodes)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(ArtControlsTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Art control behavior failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = slash.create(bpy.context, "LOW")
root.name = "Persisted Art Slash"
slash.apply_style(root, "CLEAN")
for frame, color in ((1, (0.2, 0.1, 0.05)), (8, (1, 0.3, 0.03))):
    bpy.context.scene.frame_set(frame)
    root.vfx_primary_color = color
    root.vfx_blade_color = (1, 0.75, 0.08)
    bpy.ops.vfx_studio.key_color(palette="BODY")
    bpy.ops.vfx_studio.key_color(palette="BLADE")
for frame in (2, 5, 11):
    root[f"expected_shape_{frame}"] = [c for p in points(root, frame) for c in p]
    root[f"expected_color_{frame}"] = [root[f"color_{i}"] for i in range(3)]
addon.unregister()
assert not hasattr(bpy.types.Object, "vfx_primary_color")
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/art-controls.blend"))
print("ART_CONTROLS_BEHAVIOR_OK")
