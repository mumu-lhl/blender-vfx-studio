"""Art controls change native results without rebuilding edited nodes."""

import copy
import sys
import unittest
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from particle_test_support import camera, render_pixels  # noqa: E402

import blender_vfx_studio as addon  # noqa: E402
from blender_vfx_studio import assets, composition, core, palettes, presets, slash, ui  # noqa: E402
from blender_vfx_studio.animation import curves  # noqa: E402
from blender_vfx_studio.parameters import SLASH_ART_PARAMETERS  # noqa: E402
from tools.build_examples import create_effect  # noqa: E402
from tools.fire_asset import create as create_fire  # noqa: E402


def points(root, frame):
    bpy.context.scene.frame_set(frame)
    return [
        tuple(v.co)
        for v in root.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    ]


def freeze_optional_geometry_controls(root, keys):
    paths = {f'["{key}"]' for key in keys}
    tree = root.children[0].modifiers[0].node_group
    for curve in list(tree.animation_data.drivers):
        if any(
            t.id == root and t.data_path in paths for v in curve.driver.variables for t in v.targets
        ):
            tree.driver_remove(curve.data_path)


def wrap_geometry(tree):
    # Like grouping nodes inside the existing tree, retain modifier socket identifiers.
    wrapper = tree.copy()
    wrapper.name = "Artist Geometry Wrapper"
    wrapper.animation_data_clear()
    wrapper.nodes.clear()
    inp = wrapper.nodes.new("NodeGroupInput")
    out = wrapper.nodes.new("NodeGroupOutput")
    group = wrapper.nodes.new("GeometryNodeGroup")
    group.node_tree = tree
    for socket in group.inputs:
        wrapper.links.new(inp.outputs[socket.name], socket)
    wrapper.links.new(group.outputs["Geometry"], out.inputs["Geometry"])
    return wrapper


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

    def test_hook_and_inner_geometry_are_independent_with_contour_as_master(self):
        root = slash.create(bpy.context, "LOW")
        root["bank"] = 0.0
        root.update_tag()
        before = points(root, 5)
        edge = [
            i
            for i, item in enumerate(root.children[0].data.attributes["vfx_inner"].data)
            if item.value == 0
        ]
        root["inner_notches"] = 0.0
        root.update_tag()
        no_notches = points(root, 5)
        self.assertNotEqual(no_notches, before)
        self.assertEqual([no_notches[i] for i in edge], [before[i] for i in edge])
        root["hook"] = 0.0
        root.update_tag()
        no_hook = points(root, 5)
        self.assertNotEqual([no_hook[i] for i in edge], [no_notches[i] for i in edge])
        root["contour"] = 0.0
        root.update_tag()
        plain = points(root, 5)
        root["hook"], root["inner_notches"] = 1.0, 1.0
        root.update_tag()
        self.assertEqual(points(root, 5), plain)
        self.assertTrue(all(p[2] == 0 for p in plain))

    def test_saved_slash_keeps_styles_without_adding_shape_controls(self):
        root = slash.create(bpy.context, "LOW")
        freeze_optional_geometry_controls(root, ("hook", "inner_notches"))
        del root["hook"], root["inner_notches"]
        slash.apply_style(root, "CLEAN")
        self.assertNotIn("hook", root)
        self.assertNotIn("inner_notches", root)
        self.assertTrue(all(p[2] == 0 for p in points(root, 5)))
        slash.apply_style(root, "STYLIZED")
        self.assertNotIn("hook", root)

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
        freeze_optional_geometry_controls(root, SLASH_ART_PARAMETERS)
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

    def test_fire_palette_edits_colors_and_preserves_artist_nodes(self):
        flame = next(
            m for m in composition.members(create_fire(bpy.context)) if palettes.fire_ramp(m)
        )
        core.select(bpy.context, flame)
        ramp = palettes.fire_ramp(flame)
        tree = ramp.id_data
        tree.nodes.new("ShaderNodeValue").name = "Artist Heat Detail"
        ramp.color_ramp.elements[1].position = 0.42
        positions = [e.position for e in ramp.color_ramp.elements]
        links = len(tree.links)
        geometry = points(flame, 12)
        for name in palettes.FIRE_PALETTES:
            self.assertEqual(bpy.ops.vfx_studio.fire_palette(palette=name), {"FINISHED"})
            for actual, expected in zip(ramp.color_ramp.elements, palettes.FIRE_PALETTES[name]):
                for a, b in zip(actual.color, expected):
                    self.assertAlmostEqual(a, b, places=6)
            self.assertEqual([e.position for e in ramp.color_ramp.elements], positions)
            self.assertEqual(len(tree.links), links)
            self.assertIn("Artist Heat Detail", tree.nodes)
            self.assertEqual(points(flame, 12), geometry)
            self.assertEqual([flame[f"color_{i}"] for i in range(3)], [1, 1, 1])

    def test_custom_fire_ramp_is_not_replaced_by_palette(self):
        flame = next(
            m for m in composition.members(create_fire(bpy.context)) if palettes.fire_ramp(m)
        )
        ramp = palettes.fire_ramp(flame)
        ramp.color_ramp.elements.new(0.1).color = (0.2, 0.3, 0.4, 1)
        before = [tuple(e.color) for e in ramp.color_ramp.elements]
        with self.assertRaises(ValueError):
            palettes.apply_fire(flame, "BLUE")
        self.assertEqual([tuple(e.color) for e in ramp.color_ramp.elements], before)

    def test_existing_core_focus_values_change_native_geometry(self):
        group = create_effect("energy-charge")
        member = next(m for m in composition.members(group) if "Compressed Core" in m.name)
        modifier = member.children[0].modifiers[0]
        modifier.node_group = wrap_geometry(modifier.node_group)
        values = ui._native_shape_values(member)
        for name, frame, a, b in (
            ("Nucleus Stored Size", 36, 1.9, 2.8),
            ("Nucleus Compression", 36, 0, 0.85),
            ("Release Stretch", 44, 0, 2),
        ):
            socket = values[name][1]
            socket.default_value = a
            before = points(member, frame)
            socket.default_value = b
            self.assertNotEqual(points(member, frame), before, name)
        path = ROOT / "work/artist-grouped-charge.blend"
        assets.write(path, group)
        loaded = assets.load(bpy.context, path)
        loaded_core = next(m for m in composition.members(loaded) if "Compressed Core" in m.name)
        self.assertEqual(points(loaded_core, 44), points(member, 44))
        # A hand-written driver owns this value; do not offer a misleading editable field.
        socket = values["Nucleus Stored Size"][1]
        socket.driver_add("default_value").driver.expression = "2.8"
        self.assertNotIn("Nucleus Stored Size", ui._native_shape_values(member))

    def test_native_bolt_values_change_length_and_branch_span(self):
        group = create_effect("lightning-strike")
        member = next(
            m for m in composition.members(group) if "Bolt Length" in ui._native_shape_values(m)
        )
        values = ui._native_shape_values(member)
        before = points(member, 3)
        values["Bolt Length"][1].default_value = 4.8
        after = points(member, 3)
        self.assertGreater(max(v[2] for v in after), max(v[2] for v in before) * 1.2)
        values["Branch Reach"][1].default_value = 0.2
        short = points(member, 3)
        values["Branch Reach"][1].default_value = 1.8
        wide = points(member, 3)
        self.assertGreater(max(abs(v[0]) for v in wide), max(abs(v[0]) for v in short))

    def test_impact_controls_change_only_their_named_geometry(self):
        group = create_effect("impact-burst")
        members = composition.members(group)
        body = next(m for m in members if m.name.endswith("Main Shards"))
        wave = next(m for m in members if m.name.endswith("Shockwave"))
        values = ui._native_shape_values(body)
        self.assertTrue(
            {
                "Pressure Unfurl",
                "Fine Ejection Width",
                "Pressure Fracture",
                "Pressure Support Value",
            }
            <= values.keys()
        )

        def parts():
            bpy.context.scene.frame_set(5)
            mesh = body.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            roles = mesh.attributes["impact_lobe"].data
            return {
                role: [tuple(v.co) for v, r in zip(mesh.vertices, roles) if r.value == role]
                for role in (0, 1, 2)
            }

        width = values["Fine Ejection Width"][1]
        width.default_value = 0
        thin = parts()
        width.default_value = 1.5
        thick = parts()
        self.assertEqual(thin[0], thick[0])
        self.assertEqual(thin[2], thick[2])
        self.assertNotEqual(thin[1], thick[1])
        curl = values["Pressure Unfurl"][1]
        curl.default_value = 0
        straight = parts()
        curl.default_value = 1.8
        curled = parts()
        self.assertNotEqual(straight[0], curled[0])
        self.assertEqual(straight[1], curled[1])
        self.assertEqual(straight[2], curled[2])
        crest = ui._native_shape_values(wave)["Pressure Crest Height"][1]
        crest.default_value = 0
        flat = points(wave, 5)
        crest.default_value = 1.8
        raised = points(wave, 5)
        self.assertEqual([v[:2] for v in flat], [v[:2] for v in raised])
        self.assertGreater(max(v[2] for v in raised), max(v[2] for v in flat) + 0.1)
        path = ROOT / "work/impact-art-controls.blend"
        assets.write(path, group)
        loaded = assets.load(bpy.context, path)
        other = next(
            m
            for m in composition.members(loaded)
            if "Fine Ejection Width" in ui._native_shape_values(m)
        )
        self.assertEqual(points(other, 5), points(body, 5))
        self.assertEqual(
            ui._native_shape_values(other)["Fine Ejection Width"][1].default_value, 1.5
        )
        ui._native_shape_values(other)["Fine Ejection Width"][1].default_value = 0.25
        self.assertEqual(width.default_value, 1.5)

    def test_impact_material_controls_change_the_rendered_body(self):
        group = create_effect("impact-burst")
        body = next(m for m in composition.members(group) if m.name.endswith("Main Shards"))
        for member in composition.members(group):
            member.children[0].hide_render = member != body
        camera()
        scene = bpy.context.scene
        scene.camera.data.ortho_scale = 5.5
        scene.render.resolution_x = scene.render.resolution_y = 96
        scene.render.film_transparent = True
        scene.render.dither_intensity = 0
        values = ui._native_shape_values(body)
        fracture = values["Pressure Fracture"][1]
        fracture.default_value = 0
        intact = render_pixels(5)
        fracture.default_value = 1
        broken = render_pixels(5)
        self.assertNotEqual(intact[3::4], broken[3::4])
        fracture.default_value = 0.35
        tone = values["Pressure Support Value"][1]
        tone.default_value = 0
        dark = render_pixels(5)
        tone.default_value = 1
        light = render_pixels(5)
        self.assertEqual(dark[3::4], light[3::4])
        self.assertGreater(max(abs(a - b) for a, b in zip(dark, light)), 0.1)

    def test_impact_material_controls_hide_driven_or_disconnected_values(self):
        group = create_effect("impact-burst")
        body = next(m for m in composition.members(group) if m.name.endswith("Main Shards"))
        values = ui._native_shape_values(body)
        fracture = values["Pressure Fracture"][1]
        fracture.driver_add("default_value").driver.expression = "0.35"
        self.assertNotIn("Pressure Fracture", ui._native_shape_values(body))
        tone = values["Pressure Support Value"][1]
        for link in list(tone.links):
            tone.id_data.links.remove(link)
        self.assertNotIn("Pressure Support Value", ui._native_shape_values(body))

    def test_custom_profile_hides_controls_its_saved_nodes_do_not_read(self):
        flame = next(
            m for m in composition.members(create_fire(bpy.context)) if palettes.fire_ramp(m)
        )
        # Keep the artist's static flow value and all graph links; it no longer reads this property.
        for child in flame.children:
            for modifier in child.modifiers:
                if modifier.type == "NODES":
                    tree = modifier.node_group
                    for curve in list(tree.animation_data.drivers):
                        if any(
                            t.id == flame and t.data_path == '["Fire Flow Speed"]'
                            for v in curve.driver.variables
                            for t in v.targets
                        ):
                            tree.driver_remove(curve.data_path)
        drawn = []
        modifier = flame.children[0].modifiers[0]
        modifier.node_group = wrap_geometry(modifier.node_group)

        class Layout:
            def panel(self, *args, **kwargs):
                return self, self

            def prop(self, owner, path, **kwargs):
                drawn.append(path)

            def __getattr__(self, name):
                return lambda *a, **kw: self

        ui._draw_art_parameters(Layout(), bpy.context, flame, ("width", "Fire Flow Speed"))
        self.assertIn('["width"]', drawn)
        self.assertNotIn('["Fire Flow Speed"]', drawn)


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
fire = create_fire(bpy.context, "LOW")
fire.name = "Persisted Blue Fire"
flame = next(m for m in composition.members(fire) if palettes.fire_ramp(m))
palettes.apply_fire(flame, "BLUE")
fire["expected_heat_colors"] = [
    c for e in palettes.fire_ramp(flame).color_ramp.elements for c in e.color
]
for frame in (8, 20, 44):
    fire[f"expected_shape_{frame}"] = [c for p in points(flame, frame) for c in p]
for key, saved_name, changes, frames in (
    (
        "energy-charge",
        "Persisted Adjustable Charge",
        {"Nucleus Stored Size": 2.8, "Nucleus Compression": 0.8, "Release Stretch": 2.0},
        (18, 36, 44),
    ),
    (
        "lightning-strike",
        "Persisted Adjustable Lightning",
        {"Bolt Length": 4.8, "Branch Reach": 1.4},
        (3, 8, 12),
    ),
    (
        "impact-burst",
        "Persisted Adjustable Impact",
        {
            "Pressure Unfurl": 0.45,
            "Fine Ejection Width": 0.9,
            "Pressure Fracture": 0.35,
            "Pressure Support Value": 0.45,
        },
        (3, 5, 12),
    ),
):
    bpy.context.scene.frame_set(1)
    group = create_effect(key)
    group.name = saved_name
    member = next(
        m for m in composition.members(group) if set(changes) <= ui._native_shape_values(m).keys()
    )
    group["expected_member_name"] = member.name
    modifier = member.children[0].modifiers[0]
    modifier.node_group = wrap_geometry(modifier.node_group)
    values = ui._native_shape_values(member)
    for name, value in changes.items():
        values[name][1].default_value = value
        group[f"expected_native_{name}"] = float(values[name][1].default_value)
    for frame in frames:
        group[f"expected_shape_{frame}"] = [c for p in points(member, frame) for c in p]
addon.unregister()
assert not hasattr(bpy.types.Object, "vfx_primary_color")
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/art-controls.blend"))
print("ART_CONTROLS_BEHAVIOR_OK")
