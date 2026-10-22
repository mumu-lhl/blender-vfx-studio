"""Sequence pixels follow native VFX time, not ImageUser's default scene clock."""

import math
import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from particle_test_support import camera

import blender_vfx_studio as addon
from blender_vfx_studio import assets, core, presets, sequence

COLORS = ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0))
FOLDER = ROOT / "work/sequence-tests"


def source(base=10):
    FOLDER.mkdir(exist_ok=True)
    for index, color in enumerate(COLORS, base):
        image = bpy.data.images.new("Source", 4, 4)
        image.generated_color = (*color, 1)
        image.filepath_raw = str(FOLDER / f"burst{index:04}.png")
        image.file_format = "PNG"
        image.save()
        bpy.data.images.remove(image)
    return FOLDER / f"burst{base:04}.png"


def update(root, **values):
    for key, value in values.items():
        root[key] = value
    root.update_tag()
    bpy.context.view_layer.update()


def pixels(frame):
    bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1)
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(bpy.context.scene.render.filepath, check_existing=False)
    result = list(image.pixels)
    bpy.data.images.remove(image)
    return result


def color(frame, x=24):
    data = pixels(frame)
    return data[(24 * 48 + x) * 4 : (24 * 48 + x) * 4 + 3]


class SequenceTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.file = source()

    def assertColor(self, frame, expected, x=24):
        for actual, value in zip(color(frame, x), expected):
            self.assertAlmostEqual(actual, value, delta=0.02)

    def test_arbitrary_frames_subframes_and_scene_mapping_select_real_files(self):
        root = core.create_sequence(bpy.context, self.file, 4)
        update(root, start=7.5, duration=8.0)
        camera()
        for frame, expected in (
            (7.25, (0, 0, 0)),
            (7.5, COLORS[0]),
            (9.5, COLORS[1]),
            (13.5, COLORS[3]),
            (11.5, COLORS[2]),
            (7.5, COLORS[0]),
            (15.5, (0, 0, 0)),
        ):
            self.assertColor(frame, expected)
        update(root, start=1.0)
        bpy.context.scene.render.frame_map_new = 50
        for frame, expected in (
            (1, COLORS[0]),
            (1.5, COLORS[1]),
            (2, COLORS[1]),
            (3, COLORS[2]),
            (4, COLORS[3]),
        ):
            self.assertColor(frame, expected)
        # A new scene must use its own raw frame, not a saved reference to the first scene.
        previous = bpy.context.scene
        other = bpy.data.scenes.new("Other Scene")
        for obj in list(previous.objects):
            other.collection.objects.link(obj)
        bpy.context.window.scene = other
        camera()
        self.assertColor(3, COLORS[1])

    def test_speed_loop_range_clamp_and_negative_file_number_zero(self):
        root = core.create_sequence(bpy.context, source(0), 4)
        update(root, start=-5.5, duration=8.0, first_frame=1, last_frame=2, speed=2.0, loop=True)
        camera()
        for frame, expected in ((-5.5, COLORS[1]), (-3.5, COLORS[2]), (-1.5, COLORS[1])):
            self.assertColor(frame, expected)
        update(root, first_frame=100, last_frame=0)
        self.assertColor(1, COLORS[3])
        update(root, first_frame=2, last_frame=1)
        self.assertColor(1, COLORS[2])

    def test_duplicate_keeps_independent_image_users_and_preserves_image(self):
        root = core.create_sequence(bpy.context, self.file, 4)
        update(root, first_frame=0, last_frame=0)
        clone = core.duplicate(bpy.context, root)
        update(clone, first_frame=3, last_frame=3)
        root.location.x, clone.location.x = -1.0, 1.0
        image = sequence.texture(root).image
        self.assertIs(sequence.texture(clone).image, image)
        camera()
        self.assertColor(5, COLORS[0], 12)
        self.assertColor(5, COLORS[3], 36)
        core.delete(root)
        self.assertColor(5, COLORS[3], 36)
        core.delete(clone)
        self.assertIn(image, list(bpy.data.images))
        self.assertFalse(bpy.data.meshes)
        self.assertFalse(bpy.data.materials)

    def test_missing_files_and_invalid_counts_leave_scene_unchanged(self):
        for path, count in (
            (self.file, 5),
            (FOLDER / "plain.png", 1),
            (self.file, True),
            (self.file, 0),
            (self.file, 4097),
            (FOLDER / "burst9999999.png", 1),
        ):
            before = set(bpy.data.all_ids)
            with self.assertRaises(ValueError):
                core.create_sequence(bpy.context, path, count)
            self.assertEqual(set(bpy.data.all_ids), before)
        original = bpy.data.images.load(str(self.file), check_existing=False)
        core.create_sequence(bpy.context, self.file, 4)
        self.assertEqual(original.source, "FILE")

    def test_json_relative_paths_operator_and_simple_drivers(self):
        self.assertEqual(
            bpy.ops.vfx_studio.create_sequence(filepath=str(self.file), frame_count=4), {"FINISHED"}
        )
        root = bpy.context.object
        path = FOLDER / "effect.json"
        presets.write(path, core.preset_snapshot(root))
        self.assertEqual(
            presets.loads(path.read_text(encoding="utf-8"))["assets"]["image"], "burst0010.png"
        )
        clone = core.create_from_preset(bpy.context, presets.read(path))
        self.assertEqual(clone["vfx_sequence_count"], 4)
        tex = sequence.texture(clone)
        self.assertTrue(
            all(
                c.driver.is_valid and c.driver.is_simple_expression
                for c in tex.id_data.animation_data.drivers
            )
        )
        camera()
        update(root, width=0.001)
        self.assertColor(13, COLORS[2])
        tex.image_user.frame_duration = 3
        with self.assertRaises(ValueError):
            core.preset_snapshot(clone)

    def test_complete_asset_refuses_external_sequence_files(self):
        root = core.create_sequence(bpy.context, self.file, 4)
        before = set(bpy.data.all_ids)
        with self.assertRaisesRegex(ValueError, "sequences stay external"):
            assets.write(FOLDER / "sequence.blend", root)
        self.assertEqual(set(bpy.data.all_ids), before)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(SequenceTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Sequence integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = core.create_sequence(bpy.context, source(), 4)
root.name = "Persisted Sequence"
update(root, duration=8.0)
camera()
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/sequence.blend"))
print("SEQUENCE_INTEGRATION_OK")
