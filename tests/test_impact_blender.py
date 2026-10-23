"""Native editable impact layers, timing, duplication and standalone assets."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from particle_test_support import camera, render_pixels

import blender_vfx_studio as addon
from blender_vfx_studio import assets, composition, core


def geometry(root, frame):
    bpy.context.scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    return {
        child["vfx_id"]: [tuple(v.co) for v in child.children[0].evaluated_get(graph).data.vertices]
        for child in composition.members(root)
    }


def update(root, **values):
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


class ImpactTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_four_layers_and_cursor_placement_with_staggered_lifetimes(self):
        bpy.context.scene.cursor.location = (2, 3, 4)
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        self.assertEqual(root["vfx_module"], "core.composition")
        self.assertEqual(tuple(root.location), (2, 3, 4))
        self.assertEqual(root["duration"], 24.0)
        self.assertFalse(root["loop"])
        children = composition.members(root)
        self.assertEqual(len(children), 4)
        self.assertTrue(all(child["vfx_quality"] == "LOW" for child in children))
        wave = next(child for child in children if child["vfx_module"] == "mesh.ring")
        self.assertAlmostEqual(wave.matrix_world.translation.z, 3.95, places=5)
        self.assertTrue(all(abs(child.matrix_world.translation.x - 2) < 1e-5 for child in children))
        for frame, active in ((0, 0), (1, 2), (2, 3), (3, 4), (8, 3), (19, 2), (20, 1), (25, 0)):
            state = geometry(root, frame)
            self.assertEqual(sum(bool(points) for points in state.values()), active, frame)
            self.assertLess(sum(len(points) for points in state.values()), 1000)
        update(root, speed=2.0)
        self.assertEqual(sum(bool(p) for p in geometry(root, 5).values()), 3)
        self.assertFalse(any(geometry(root, 13).values()))
        update(root, loop=True)
        self.assertEqual(sum(bool(p) for p in geometry(root, 13).values()), 2)

    def test_wave_erosion_tracks_group_time_instead_of_absolute_keyframes(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        wave = next(
            child for child in composition.members(root) if child["vfx_module"] == "mesh.ring"
        )
        socket = wave.children[0].data.materials[0].node_tree.nodes["Dissolve Threshold"].inputs[1]
        geometry(root, 5)
        early = socket.default_value
        geometry(root, 14)
        self.assertGreater(socket.default_value, early + 0.2)
        update(root, speed=2.0)
        geometry(root, 3)
        self.assertAlmostEqual(socket.default_value, early, places=6)
        self.assertIsNone(wave.animation_data.action)

    def test_operator_duplicate_asset_and_ungroup_preserve_native_layers(self):
        self.assertEqual(
            bpy.ops.vfx_studio.create(preset="IMPACT_BURST", quality="LOW"), {"FINISHED"}
        )
        root = bpy.context.object
        path = ROOT / "work/impact-complete.blend"
        assets.write(path, root)
        loaded = assets.load(bpy.context, path)
        clone = core.duplicate(bpy.context, root)
        ids = [{r["vfx_id"] for r in composition.members(group)} for group in (root, loaded, clone)]
        self.assertTrue(ids[0].isdisjoint(ids[1]) and ids[1].isdisjoint(ids[2]))
        expected = sorted(len(p) for p in geometry(root, 5).values())
        self.assertEqual(sorted(len(p) for p in geometry(loaded, 5).values()), expected)
        core.delete(root)
        children, retained = composition.ungroup_all(bpy.context, clone)
        self.assertFalse(retained)
        self.assertEqual(len(children), 4)
        self.assertTrue(all(child.parent is None for child in children))
        for child in children:
            core.delete(child)
        core.delete(loaded)
        self.assertEqual(len(bpy.data.meshes), 0)
        self.assertEqual(len(bpy.data.materials), 0)
        self.assertEqual(len(bpy.data.node_groups), 0)

    def test_shard_side_contrast_is_editable_and_survives_complete_assets(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        camera()
        bpy.context.scene.camera.data.ortho_scale = 5.5
        bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 96
        for member in composition.members(root):
            member.children[0].hide_render = not member.name.endswith("Main Shards")
        shards = next(m for m in composition.members(root) if m.name.endswith("Main Shards"))
        contrast = shards.children[0].data.materials[0].node_tree.nodes["Side Contrast"].outputs[0]
        contrast.default_value = 0
        flat = render_pixels(5)
        contrast.default_value = 0.63
        faceted = render_pixels(5)
        # Actual pixels must change: a saved slider with no shader connection is insufficient.
        self.assertGreater(sum(flat) - sum(faceted), 0.5)
        path = ROOT / "work/impact-facets.blend"
        assets.write(path, root)
        core.delete(root)
        loaded = assets.load(bpy.context, path)
        self.assertEqual(render_pixels(5), faceted)
        clone = core.duplicate(bpy.context, loaded)
        core.delete(loaded)
        self.assertEqual(render_pixels(5), faceted)
        # Authored shading still follows the ordinary controller's color and emission.
        shards = next(m for m in composition.members(clone) if "Main Shards" in m.name)
        update(shards, color_0=0.01, color_1=0.1, color_2=1.0, strength=0.5)
        blue = render_pixels(5)
        self.assertGreater(sum(blue[2::4]), sum(blue[0::4]))
        self.assertNotEqual(blue, faceted)

    def test_core_flash_and_sparse_tail_have_distinct_rendered_stages(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        camera()
        bpy.context.scene.camera.data.ortho_scale = 5.5
        stages = [render_pixels(frame) for frame in (2, 5, 14)]

        def energy(pixels):
            return sum(pixels[i] + pixels[i + 1] + pixels[i + 2] for i in range(0, len(pixels), 4))

        self.assertGreater(energy(stages[0]), energy(stages[2]) * 2)
        self.assertGreater(energy(stages[1]), energy(stages[2]) * 2)
        center = (24 * 48 + 24) * 4
        self.assertGreater(min(stages[0][center : center + 3]), 0.25)
        self.assertLess(max(stages[2][center : center + 3]), 0.05)
        self.assertFalse(any(geometry(root, 25).values()))


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(ImpactTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Impact integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = core.create(bpy.context, "IMPACT_BURST", "LOW")
root.name = "Persisted Impact"
for frame in (2, 5, 14):
    state = geometry(root, frame)
    for child in composition.members(root):
        child[f"expected_shape_{frame}"] = [c for v in state[child["vfx_id"]] for c in v]
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/impact.blend"))
print("IMPACT_INTEGRATION_OK")
