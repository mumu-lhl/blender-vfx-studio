"""Complete native asset reuse, repeated imports and non-destructive failures."""

import struct
import sys
import unittest
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import blender_vfx_studio as addon
from blender_vfx_studio import (
    asset_browser,
    asset_preview,
    assets,
    binding,
    composition,
    core,
    simulation,
    trail,
)

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

    def test_asset_identity_survives_collection_renaming(self):
        root = ring()
        root.name = "Blue Shockwave"
        assets.write(FILE, root)
        with bpy.data.libraries.load(str(FILE), assets_only=True) as (available, _):
            self.assertEqual(available.collections, ["Blue Shockwave"])
        imported = assets.load(bpy.context, FILE)
        bundle = next(c for c in imported.users_collection if c.get("vfx_bundle_version"))
        self.assertIn("VFX Studio", bundle.asset_data.tags)
        bundle.name = "Artist Renamed Collection"
        renamed = ROOT / "work/renamed-asset.blend"
        bpy.data.libraries.write(str(renamed), {bundle})
        loaded = assets.load(bpy.context, renamed)
        self.assertNotEqual(imported["vfx_id"], loaded["vfx_id"])
        self.assertEqual(core.resolve(loaded), loaded)

    def test_exact_selected_collection_and_foreign_asset_rollback(self):
        bundles = []
        for creator in (core.create, core.create_shield):
            assets.write(FILE, creator(bpy.context))
            imported = assets.load(bpy.context, FILE)
            bundles.append(
                next(c for c in imported.users_collection if c.get("vfx_bundle_version"))
            )
        ordinary = bpy.data.collections.new("User Collection Asset")
        ordinary.asset_mark()
        multi = ROOT / "work/multiple-assets.blend"
        bpy.data.libraries.write(str(multi), {*bundles, ordinary})
        before = set(bpy.data.all_ids)
        for name in (ordinary.name, "Missing Asset"):
            with self.assertRaises(ValueError):
                assets.load(bpy.context, multi, collection_name=name)
            self.assertEqual(set(bpy.data.all_ids), before)
        with self.assertRaisesRegex(ValueError, "one exported"):
            assets.load(bpy.context, multi)
        self.assertEqual(set(bpy.data.all_ids), before)
        a = assets.load(bpy.context, multi, collection_name=bundles[0].name)
        b = assets.load(bpy.context, multi, collection_name=bundles[1].name)
        self.assertEqual(a["vfx_module"], "mesh.ring")
        self.assertEqual(b["vfx_module"], "shader.shield")
        self.assertNotEqual(a["vfx_id"], b["vfx_id"])

    def test_browser_selection_rejects_unsupported_sources_without_file_io(self):
        values = dict(
            id_type="COLLECTION",
            local_id=None,
            is_online=False,
            full_library_path=str(FILE),
            name="Example",
        )
        self.assertEqual(asset_browser.selection(SimpleNamespace(**values)), (str(FILE), "Example"))
        for change in (
            dict(id_type="MATERIAL"),
            dict(local_id=object()),
            dict(is_online=True),
            dict(full_library_path=""),
            dict(name=""),
        ):
            with self.assertRaises(ValueError):
                asset_browser.selection(SimpleNamespace(**dict(values, **change)))
        with self.assertRaises(ValueError):
            asset_browser.selection(None)

    def test_browser_operator_imports_from_non_viewport_context(self):
        root = ring()
        assets.write(FILE, root)
        area = next(a for a in bpy.context.screen.areas if a.type == "VIEW_3D")
        area.ui_type = "ASSETS"
        try:
            with bpy.context.temp_override(area=area):
                self.assertFalse(bpy.ops.vfx_studio.load_browser_asset.poll())
                with patch.object(
                    asset_browser, "selection", return_value=(str(FILE), "Shockwave")
                ):
                    self.assertTrue(bpy.ops.vfx_studio.load_browser_asset.poll())
                    self.assertEqual(bpy.ops.vfx_studio.load_browser_asset(), {"FINISHED"})
            imported = bpy.context.view_layer.objects.active
            self.assertNotEqual(imported["vfx_id"], root["vfx_id"])
            self.assertEqual(core.resolve(imported), imported)
        finally:
            area.type = "VIEW_3D"

    def test_import_refuses_edit_mode_without_changing_existing_data(self):
        root = ring()
        assets.write(FILE, root)
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.object
        bpy.ops.object.mode_set(mode="EDIT")
        before = set(bpy.data.all_ids)
        try:
            with self.assertRaisesRegex(ValueError, "Object Mode"):
                assets.load(bpy.context, FILE)
            self.assertEqual(set(bpy.data.all_ids), before)
            self.assertEqual(obj.mode, "EDIT")
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")

    def test_embedded_preview_preserves_source_and_needs_no_image_dependency(self):
        ring()
        image = bpy.data.images.new("User Preview", 2, 2, float_buffer=True)
        pixels = [1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0.25, 0.5, 0.75, 0.5]
        image.filepath = "//untouched-preview.png"
        image.colorspace_settings.name = "Non-Color"
        image.pixels = pixels
        before = set(bpy.data.all_ids)
        state = (
            image.size[:],
            list(image.pixels),
            image.filepath,
            image.colorspace_settings.name,
            image.users,
            image.is_dirty,
            bpy.context.scene.view_settings.view_transform,
        )
        self.assertEqual(
            bpy.ops.vfx_studio.export_asset(filepath=str(FILE), preview_image=image.name),
            {"FINISHED"},
        )
        self.assertEqual(set(bpy.data.all_ids), before)
        self.assertEqual(
            (
                image.size[:],
                list(image.pixels),
                image.filepath,
                image.colorspace_settings.name,
                image.users,
                image.is_dirty,
                bpy.context.scene.view_settings.view_transform,
            ),
            state,
        )
        with bpy.data.libraries.load(str(FILE)) as (available, _):
            self.assertEqual(available.images, [])
        imported = assets.load(bpy.context, FILE)
        bundle = next(c for c in imported.users_collection if c.get("vfx_bundle_version"))
        self.assertEqual(bundle.preview.image_size[:], (2, 2))
        self.assertTrue(bundle.preview.is_image_custom)
        expected = pixels[:12] + [0.125, 0.25, 0.375, 0.5]
        for a, b in zip(bundle.preview.image_pixels_float, expected):
            self.assertAlmostEqual(a, b, delta=1 / 255)

    def test_transparent_png_preview_matches_native_custom_preview(self):
        rgba = bytes([255, 0, 0, 128, 128, 64, 192, 128, 0, 0, 255, 0, 255, 255, 255, 255])

        def chunk(tag, data):
            return (
                struct.pack(">I", len(data))
                + tag
                + data
                + struct.pack(">I", zlib.crc32(tag + data))
            )

        file = ROOT / "work/native-alpha-preview.png"
        raw = b"\x00" + rgba[:8] + b"\x00" + rgba[8:]
        file.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b"")
        )
        image = bpy.data.images.load(str(file), check_existing=False)
        native = bpy.data.collections.new("Native Custom Preview")
        with bpy.context.temp_override(id=native):
            self.assertEqual(
                bpy.ops.ed.lib_id_load_custom_preview(filepath=str(file)), {"FINISHED"}
            )
        exported = bpy.data.collections.new("Exported Custom Preview")
        original = list(image.pixels)
        asset_preview.apply(exported, asset_preview.prepare(image))
        self.assertEqual(list(image.pixels), original)
        for a, b in zip(exported.preview.image_pixels_float, native.preview.image_pixels_float):
            self.assertAlmostEqual(a, b, delta=2 / 255)

    def test_transparent_edges_are_filtered_after_premultiplication(self):
        image = bpy.data.images.new("Transparent Edge", 512, 1, alpha=True, float_buffer=True)
        image.alpha_mode = "STRAIGHT"
        original = [1, 0, 0, 1, 0, 0, 1, 0] * 256
        image.pixels = original
        size, pixels = asset_preview.prepare(image)
        self.assertEqual(size, (256, 1))
        for i in range(0, len(pixels), 4):
            self.assertEqual(list(pixels[i : i + 4]), [0.5, 0, 0, 0.5])
        self.assertEqual(list(image.pixels), original)

    def test_preview_respects_premultiplied_and_opaque_alpha_modes(self):
        image = bpy.data.images.new("Alpha Modes", 1, 1, alpha=True, float_buffer=True)
        for mode, expected in (
            ("PREMUL", [0.25, 0.125, 0, 0.5]),
            ("NONE", [0.25, 0.125, 0, 1]),
            ("CHANNEL_PACKED", [0.25, 0.125, 0, 1]),
        ):
            image.alpha_mode = mode
            image.pixels = [0.25, 0.125, 0, 0.5]
            original = list(image.pixels)
            self.assertEqual(list(asset_preview.prepare(image)[1]), expected)
            self.assertEqual(list(image.pixels), original)
            self.assertEqual(image.alpha_mode, mode)

    def test_preview_resizes_and_preserves_aspect_ratio_without_upscaling(self):
        image = bpy.data.images.new("Wide Preview", 512, 128, float_buffer=True)
        image.pixels = [0.25, 0.5, 0.75, 1] * (512 * 128)
        size, pixels = asset_preview.prepare(image)
        self.assertEqual(size, (256, 64))
        self.assertEqual(len(pixels), 256 * 64 * 4)
        self.assertEqual(list(pixels[:4]), [0.25, 0.5, 0.75, 1])
        self.assertEqual(image.size[:], (512, 128))
        self.assertEqual(list(image.pixels[:4]), [0.25, 0.5, 0.75, 1])
        small = bpy.data.images.new("Small Preview", 3, 1)
        self.assertEqual(asset_preview.prepare(small)[0], (3, 1))

    def test_preview_errors_preserve_existing_asset_and_data(self):
        root = ring()
        assets.write(FILE, root)
        original = FILE.read_bytes()
        large = bpy.data.images.new("Oversize Preview", 2049, 1)
        missing = bpy.data.images.new("Missing Preview", 2, 2)
        missing.source = "FILE"
        missing.filepath = str(ROOT / "work/missing-preview-file.png")
        sequence = bpy.data.images.new("Sequence Preview", 2, 2)
        sequence.source = "SEQUENCE"
        invalid = bpy.data.images.new("NaN Preview", 1, 1, float_buffer=True)
        invalid.pixels = [float("nan"), 0, 0, 1]
        for image in (large, missing, sequence, invalid, object()):
            before = set(bpy.data.all_ids)
            with self.assertRaises(ValueError):
                assets.write(FILE, root, preview_image=image)
            self.assertEqual(set(bpy.data.all_ids), before)
            self.assertEqual(FILE.read_bytes(), original)
        with self.assertRaisesRegex(RuntimeError, "no longer exists"):
            bpy.ops.vfx_studio.export_asset(filepath=str(FILE), preview_image="Deleted Image")
        self.assertEqual(FILE.read_bytes(), original)

    def test_packed_preview_survives_missing_file_and_failed_export_cleans_up(self):
        root = ring()
        generated = bpy.data.images.new("Preview PNG Source", 4, 2)
        generated.generated_color = (0.2, 0.4, 0.8, 1)
        generated.filepath_raw = str(ROOT / "work/packed-preview.png")
        generated.file_format = "PNG"
        generated.save()
        image = bpy.data.images.load(generated.filepath_raw, check_existing=False)
        image.pack()
        Path(image.filepath).unlink()
        assets.write(FILE, root, preview_image=image)
        original = FILE.read_bytes()
        before = set(bpy.data.all_ids)
        with patch.object(assets.os, "replace", side_effect=OSError("Disk")):
            with self.assertRaisesRegex(OSError, "Disk"):
                assets.write(FILE, root, preview_image=image)
        self.assertEqual(set(bpy.data.all_ids), before)
        self.assertEqual(FILE.read_bytes(), original)
        self.assertTrue(image.packed_file)
        self.assertEqual(image.size[:], (4, 2))
        self.assertIsNone(asset_preview.prepare(None))

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
preview = bpy.data.images.new("Fixture Preview", 2, 2, alpha=True)
preview.pixels = [1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 0, 0.5]
assets.write(FILE, original, preview_image=preview)
bpy.data.images.remove(preview)
loaded = assets.load(bpy.context, FILE)
loaded.name = "Persisted Native Asset"
core.delete(original)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/assets.blend"))
print("ASSETS_INTEGRATION_OK")
