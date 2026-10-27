"""Real sprite geometry, image ownership and CPU shader evaluation."""

import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import core, presets

WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)


def atlas():
    image = bpy.data.images.new("User Atlas", width=8, height=8, alpha=True)
    pixels = []
    for y in range(8):
        for x in range(8):
            # Blender pixel storage starts at the bottom; atlas cell order starts at top left.
            color = (
                ((1, 0, 0, 1) if x < 4 else (0, 1, 0, 1))
                if y >= 4
                else ((0, 0, 1, 1) if x < 4 else (1, 1, 1, 1))
            )
            pixels.extend(color)
    image.pixels[:] = pixels
    image.filepath_raw = str(WORK / "test-atlas.png")
    image.file_format = "PNG"
    image.save()
    return image


def update(root, **values):
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


def evaluated(root, frame):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data


def camera():
    scene = bpy.context.scene
    cam = bpy.data.objects.new("Test Camera", bpy.data.cameras.new("Test Camera"))
    scene.collection.objects.link(cam)
    cam.location = (0, 0, 5)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 2
    scene.camera = cam
    scene.world = bpy.data.worlds.new("Black")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 16
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.render.filepath = str(WORK / "test-flipbook-render.png")


def center_pixel(frame):
    bpy.context.scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)
    result = bpy.data.images.load(bpy.context.scene.render.filepath, check_existing=False)
    offset = (8 * 16 + 8) * 4
    color = tuple(result.pixels[offset : offset + 3])
    bpy.data.images.remove(result)
    return color


class FlipbookTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.frame_set(1)
        self.image = atlas()

    def test_native_timing_geometry_size_and_simple_drivers(self):
        root = core.create_flipbook(bpy.context, self.image, 2, 2)
        for frame, count in [(13, 4), (25, 0), (0, 0), (1, 4), (24, 4)]:
            self.assertEqual(len(evaluated(root, frame).vertices), count)
        update(root, width=3.0, height=1.5, start=3.0, duration=4.0, loop=True)
        mesh = evaluated(root, 11)
        self.assertAlmostEqual(max(v.co.x for v in mesh.vertices), 1.5)
        self.assertAlmostEqual(max(v.co.y for v in mesh.vertices), 0.75)
        layer = root.children[0]
        for data in (layer.modifiers[0].node_group, layer.data.materials[0].node_tree):
            for curve in data.animation_data.drivers:
                self.assertTrue(curve.driver.is_valid, curve.data_path)
                self.assertTrue(curve.driver.is_simple_expression, curve.driver.expression)
        ring = core.create(bpy.context)
        self.assertEqual(ring["vfx_module"], "mesh.ring")
        self.assertEqual(len(evaluated(root, 3).vertices), 4)

    def test_cpu_render_row_order_arbitrary_frames_range_speed_and_alpha(self):
        root = core.create_flipbook(bpy.context, self.image, 2, 2)
        update(root, duration=4.0)
        camera()
        cases = [
            (4, (1, 1, 1)),
            (1, (1, 0, 0)),
            (3, (0, 0, 1)),
            (2, (0, 1, 0)),
            (5, (0, 0, 0)),
            (0, (0, 0, 0)),
        ]
        for frame, expected in cases:
            with self.subTest(frame=frame):
                for actual, channel in zip(center_pixel(frame), expected):
                    self.assertAlmostEqual(actual, channel, delta=0.03)
        update(root, loop=True)
        for actual, expected in zip(center_pixel(5), (1, 0, 0)):
            self.assertAlmostEqual(actual, expected, delta=0.03)
        update(root, speed=2.0)
        for actual, expected in zip(center_pixel(4), (0, 0, 1)):
            self.assertAlmostEqual(actual, expected, delta=0.03)
        update(root, speed=1.0, first_frame=1, last_frame=2)
        for actual, expected in zip(center_pixel(1), (0, 1, 0)):
            self.assertAlmostEqual(actual, expected, delta=0.03)
        update(root, opacity=0.0)
        self.assertTrue(all(value < 0.03 for value in center_pixel(2)))
        update(root, opacity=1.0, first_frame=65000, last_frame=0)
        # Out-of-grid first and reversed range clamp to the final cell.
        self.assertTrue(all(value > 0.97 for value in center_pixel(2)))
        # The texture's alpha must matter even when the controller opacity is one.
        transparent = self.image.copy()
        pixels = list(transparent.pixels)
        for offset in range(3, len(pixels), 4):
            pixels[offset] = 0
        transparent.pixels.foreach_set(pixels)
        transparent.update()
        core.atlas_node(root).image = transparent
        self.assertTrue(all(value < 0.03 for value in center_pixel(2)))

    def test_copy_is_independent_and_never_deletes_user_image(self):
        root = core.create_flipbook(bpy.context, self.image, 2, 2)
        tree = root.children[0].data.materials[0].node_tree
        tree.nodes.new("ShaderNodeValue").label = "User Node"
        clone = core.duplicate(bpy.context, root)
        self.assertEqual(core.atlas_node(clone).image, self.image)
        self.assertIsNot(core.atlas_node(clone).id_data, tree)
        update(clone, width=4.0)
        self.assertAlmostEqual(max(v.co.x for v in evaluated(root, 2).vertices), 1.0)
        self.assertAlmostEqual(max(v.co.x for v in evaluated(clone, 2).vertices), 2.0)
        for data in (
            clone.children[0].modifiers[0].node_group,
            clone.children[0].data.materials[0].node_tree,
        ):
            self.assertTrue(
                all(
                    v.targets[0].id == clone
                    for c in data.animation_data.drivers
                    for v in c.driver.variables
                )
            )
        core.delete(root)
        core.delete(clone)
        self.assertIn(self.image.name, bpy.data.images)
        self.assertEqual(self.image.size[:], (8, 8))
        self.assertEqual(self.image.users, 0)

    def test_file_operators_preset_relative_reference(self):
        self.assertEqual(
            bpy.ops.vfx_studio.create_flipbook(filepath=self.image.filepath, columns=2, rows=2),
            {"FINISHED"},
        )
        root = bpy.context.object
        path = WORK / "flipbook-preset.json"
        self.assertEqual(bpy.ops.vfx_studio.export_preset(filepath=str(path)), {"FINISHED"})
        self.assertEqual(
            presets.loads(path.read_text(encoding="utf-8"))["assets"]["image"], "test-atlas.png"
        )
        bpy.context.scene.frame_set(50)
        self.assertEqual(bpy.ops.vfx_studio.import_preset(filepath=str(path)), {"FINISHED"})
        clone = bpy.context.object
        self.assertNotEqual(clone["vfx_id"], root["vfx_id"])
        self.assertEqual(clone["start"], 50)
        self.assertEqual(core.atlas_node(clone).image, core.atlas_node(root).image)

    def test_invalid_assets_and_settings_do_not_mutate_scene(self):
        count = len(bpy.data.objects)
        for image, columns, rows in [
            (None, 2, 2),
            (self.image, 0, 2),
            (self.image, 2.5, 2),
            (self.image, 2, 257),
        ]:
            with self.assertRaises(ValueError):
                core.create_flipbook(bpy.context, image, columns, rows)
            self.assertEqual(len(bpy.data.objects), count)
        root = core.create_flipbook(bpy.context, self.image, 2, 2)
        data = core.preset_snapshot(root)
        data["assets"]["image"] = str(WORK / "missing-atlas.png")
        count = len(bpy.data.objects)
        with self.assertRaises(ValueError):
            core.create_from_preset(bpy.context, data)
        self.assertEqual(len(bpy.data.objects), count)
        core.atlas_node(root).image = bpy.data.images.new("Unsaved Atlas", width=4, height=4)
        with self.assertRaisesRegex(ValueError, "Save the atlas"):
            core.preset_snapshot(root)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(FlipbookTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Flipbook integration tests failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.frame_set(1)
image = atlas()
image.pack()
root = core.create_flipbook(bpy.context, image, 2, 2)
root.name = "Persisted Flipbook"
update(root, duration=4.0, loop=True)
clone = core.duplicate(bpy.context, root)
clone.name = "Persisted Flipbook Copy"
clone.location.x = 4
update(clone, width=3.0)
camera()
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(WORK / "flipbook.blend"))
print("FLIPBOOK_INTEGRATION_OK")
