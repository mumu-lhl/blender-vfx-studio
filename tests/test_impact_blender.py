"""Native editable impact layers, timing, duplication and standalone assets."""

import sys
import unittest
from pathlib import Path

import bpy
from mathutils import Vector

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

    def test_layers_and_cursor_placement_with_staggered_lifetimes(self):
        bpy.context.scene.cursor.location = (2, 3, 4)
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        self.assertEqual(root["vfx_module"], "core.composition")
        self.assertEqual(tuple(root.location), (2, 3, 4))
        self.assertEqual(root["duration"], 24.0)
        self.assertFalse(root["loop"])
        children = composition.members(root)
        self.assertEqual(len(children), 5)
        self.assertTrue(all(child["vfx_quality"] == "LOW" for child in children))
        wave = next(child for child in children if child["vfx_module"] == "mesh.ring")
        self.assertAlmostEqual(wave.matrix_world.translation.z, 3.95, places=5)
        self.assertTrue(all(abs(child.matrix_world.translation.x - 2) < 1e-5 for child in children))
        for frame, active in (
            (0, 0),
            (1, 3),
            (2, 4),
            (3, 5),
            (4, 4),
            (8, 4),
            (9, 3),
            (19, 2),
            (20, 1),
            (25, 0),
        ):
            state = geometry(root, frame)
            self.assertEqual(sum(bool(points) for points in state.values()), active, frame)
        update(root, speed=2.0)
        self.assertEqual(sum(bool(p) for p in geometry(root, 5).values()), 3)
        self.assertFalse(any(geometry(root, 13).values()))
        update(root, loop=True)
        self.assertEqual(sum(bool(p) for p in geometry(root, 13).values()), 3)

    def test_burst_core_plays_through_flash_handoff_and_retimes(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        burst = next(m for m in composition.members(root) if m.name.endswith("Burst Core"))
        key = burst["vfx_id"]

        for member in composition.members(root):
            member.children[0].hide_render = member != burst
        camera()
        bpy.context.scene.camera.data.ortho_scale = 1.5
        bpy.context.scene.render.dither_intensity = 0
        early, peak = render_pixels(1), render_pixels(3)
        self.assertGreater(sum(peak[0::4]), sum(early[0::4]) * 2)
        after_flash = geometry(root, 5)[key]
        self.assertTrue(after_flash)
        self.assertFalse(geometry(root, 9)[key])
        update(root, duration=48.0)
        self.assertEqual(geometry(root, 9)[key], after_flash)
        retimed = render_pixels(5)
        self.assertLess(max(abs(a - b) for a, b in zip(peak, retimed)), 1 / 255 + 1e-6)
        update(root, duration=24.0)
        self.assertEqual(geometry(root, 5)[key], after_flash)
        before = max(point[0] for point in geometry(root, 3)[key])
        update(burst, width=burst["width"] * 2)
        self.assertAlmostEqual(
            max(point[0] for point in geometry(root, 3)[key]), before * 2, places=5
        )

    def test_burst_sprite_faces_camera_without_exporting_camera_data(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        burst = next(m for m in composition.members(root) if m.name.endswith("Burst Core"))
        camera()
        view = bpy.context.scene.camera
        view.location = (3, -5, 4)
        view.rotation_euler = (-view.location).to_track_quat("-Z", "Y").to_euler()
        root.rotation_euler = (0.3, 0.7, 1.1)
        geometry(root, 3)
        layer = burst.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get())
        normal = layer.matrix_world.to_3x3().inverted().transposed() @ layer.data.polygons[0].normal
        expected = view.matrix_world.to_3x3() @ Vector((0, 0, 1))
        self.assertGreater(normal.normalized().dot(expected.normalized()), 0.9999)
        path = ROOT / "work/impact-billboard.blend"
        assets.write(path, root)
        with bpy.data.libraries.load(str(path), link=False) as (available, requested):
            self.assertFalse(available.cameras)
            self.assertFalse(available.scenes)

    def test_burst_core_color_and_strength_change_actual_pixels(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        burst = next(m for m in composition.members(root) if m.name.endswith("Burst Core"))
        for member in composition.members(root):
            member.children[0].hide_render = member != burst
        camera()
        bpy.context.scene.camera.data.ortho_scale = 1.5
        bpy.context.scene.render.dither_intensity = 0
        warm = render_pixels(3)
        self.assertGreater(sum(warm[0::4]), sum(warm[2::4]))
        update(burst, color_0=0.015, color_1=0.05, color_2=1.0)
        blue = render_pixels(3)
        self.assertGreater(sum(blue[2::4]), sum(blue[0::4]))
        self.assertGreater(max(abs(a - b) for a, b in zip(warm, blue)), 0.1)
        update(burst, strength=0.0)
        dark = render_pixels(3)
        self.assertLess(max(v for i, v in enumerate(dark) if i % 4 != 3), 1e-5)

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
        self.assertEqual(len(children), 5)
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

    def test_body_rim_changes_color_without_changing_coverage(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        camera()
        scene = bpy.context.scene
        # The open pressure sheets expose a viewing-angle rim. Inspect an
        # oblique view instead of requiring a dark border on their front faces.
        scene.camera.location = (3, 0, 3)
        scene.camera.rotation_euler = (-scene.camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.film_transparent = True
        scene.render.resolution_x = scene.render.resolution_y = 96
        main = next(m for m in composition.members(root) if m.name.endswith("Main Shards"))
        for member in composition.members(root):
            member.children[0].hide_render = member != main
        contrast = main.children[0].data.materials[0].node_tree.nodes["Rim Contrast"].outputs[0]
        contrast.default_value = 0
        plain = render_pixels(5)
        contrast.default_value = 0.95
        outlined = render_pixels(5)
        self.assertEqual(plain[3::4], outlined[3::4])
        plain_light = sum(v for i, v in enumerate(plain) if i % 4 != 3)
        rim_light = sum(v for i, v in enumerate(outlined) if i % 4 != 3)
        self.assertLess(rim_light, plain_light * 0.98)
        self.assertGreater(rim_light, plain_light * 0.55)
        support = (
            main.children[0].data.materials[0].node_tree.nodes["Pressure Support Value"].outputs[0]
        )
        support.default_value = 1
        equal_weight = render_pixels(5)
        support.default_value = 0.25
        separated = render_pixels(5)
        self.assertEqual(equal_weight[3::4], separated[3::4])
        self.assertGreater(sum(equal_weight), sum(separated) + 1)
        update(main, color_0=0.015, color_1=0.65, color_2=0.05)
        green = render_pixels(5)
        self.assertGreater(sum(green[1::4]), sum(green[0::4]) * 1.3)

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
        # The authored flash has a directional silhouette and a dark side;
        # verify a compact bright region instead of requiring its pivot pixel
        # to be white on every face.
        focus = [
            min(stages[0][(y * 48 + x) * 4 : (y * 48 + x) * 4 + 3])
            for y in range(18, 31)
            for x in range(18, 34)
        ]
        self.assertGreater(max(focus), 0.25)
        self.assertLess(max(stages[2][center : center + 3]), 0.05)
        self.assertFalse(any(geometry(root, 25).values()))
        settling = render_pixels(9)

        def white_count(pixels):
            return sum(min(pixels[i : i + 3]) > 0.6 for i in range(0, len(pixels), 4))

        self.assertGreater(white_count(stages[1]), 0)
        self.assertLess(white_count(settling), white_count(stages[1]) * 0.4)

    def test_flash_keeps_a_hot_focus_when_the_binding_rotates(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        flash = next(m for m in composition.members(root) if m.name.endswith("Core Flash"))
        for member in composition.members(root):
            member.children[0].hide_render = member != flash
        camera()
        scene = bpy.context.scene
        view = scene.camera
        view.location = (0, 5, 0.8)
        view.rotation_euler = (-view.location).to_track_quat("-Z", "Y").to_euler()
        view.data.ortho_scale = 2
        scene.render.resolution_x = scene.render.resolution_y = 64
        scene.render.dither_intensity = 0
        for rotation in ((0, 0, 0), (0.7, 1.1, 0.2), (1.4, 0.3, 2.2)):
            root.rotation_euler = rotation
            pixels = render_pixels(1)
            focus = [
                min(pixels[(y * 64 + x) * 4 : (y * 64 + x) * 4 + 3])
                for y in range(30, 35)
                for x in range(30, 35)
            ]
            self.assertGreater(max(focus), 0.75, rotation)
        warm = pixels
        update(flash, color_0=0.015, color_1=0.05, color_2=1.0)
        blue = render_pixels(1)
        self.assertGreater(sum(blue[2::4]), sum(blue[0::4]))
        self.assertGreater(max(abs(a - b) for a, b in zip(warm, blue)), 0.1)
        update(flash, strength=0.0)
        dark = render_pixels(1)
        self.assertLess(max(v for i, v in enumerate(dark) if i % 4 != 3), 1e-5)
        # The flash retains the same native three-frame geometry lifetime.
        self.assertTrue(geometry(root, 3)[flash["vfx_id"]])
        self.assertFalse(geometry(root, 4)[flash["vfx_id"]])

    def test_authored_pressure_controls_depth_and_retiming(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        shards = next(m for m in composition.members(root) if m.name.endswith("Main Shards"))
        expected = geometry(root, 5)
        original = expected[shards["vfx_id"]]
        self.assertGreater(max(p[2] for p in original) - min(p[2] for p in original), 0.1)
        for key, value in (
            ("size", 0.2),
            ("velocity", 1.8),
            ("seed", 19),
            ("stretch", 2),
            ("randomness", 0),
            ("motion_ease", 0),
            ("motion_seconds", 0.3),
            ("spawn_radius", 0.2),
            ("fade", 0),
        ):
            previous = shards[key]
            update(shards, **{key: value})
            self.assertNotEqual(geometry(root, 5)[shards["vfx_id"]], original, key)
            update(shards, **{key: previous})
        update(shards, planar=1.0)
        self.assertTrue(all(abs(p[2]) < 1e-6 for p in geometry(root, 5)[shards["vfx_id"]]))
        update(shards, planar=0.35)
        self.assertEqual(geometry(root, 5), expected)
        update(root, speed=2.0)
        self.assertEqual(geometry(root, 3), expected)
        update(root, speed=1.0, duration=48.0)
        self.assertEqual(geometry(root, 9), expected)

    def test_pressure_occupies_contact_while_fine_ejections_carry_the_long_reach(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        main = next(m for m in composition.members(root) if m.name.endswith("Main Shards"))
        geometry(root, 5)
        mesh = main.children[0].evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        roles = mesh.attributes["impact_lobe"].data
        along = mesh.attributes["impact_u"].data
        pressure = [v.co.length for v, role in zip(mesh.vertices, roles) if role.value < 0.5]
        rays = [v.co.length for v, role in zip(mesh.vertices, roles) if 0.5 < role.value < 1.5]
        contact = [
            v.co.length
            for v, role, u in zip(mesh.vertices, roles, along)
            if role.value < 0.5 and u.value < 0.01
        ]
        self.assertLess(max(pressure), max(rays) * 0.7)
        self.assertGreater(min(contact), max(pressure) * 0.02)

    def test_pressure_alignment_preserves_fine_and_auxiliary_paths_in_saved_assets(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        main = next(m for m in composition.members(root) if m.name.endswith("Main Shards"))
        layer = main.children[0]

        def parts():
            bpy.context.scene.frame_set(5)
            mesh = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            return {
                role: [
                    tuple(v.co)
                    for v, attr in zip(mesh.vertices, mesh.attributes["impact_lobe"].data)
                    if attr.value == role
                ]
                for role in (0, 1, 2)
            }

        before = parts()
        layer.modifiers[0].node_group.nodes["Pressure Surface Alignment"].inputs[
            "Rotation"
        ].default_value = (0.7, -0.4, 0.2)
        aligned = parts()
        self.assertNotEqual(aligned[0], before[0])
        self.assertEqual(aligned[1], before[1])
        self.assertEqual(aligned[2], before[2])
        path = ROOT / "work/impact-aligned.blend"
        assets.write(path, root)
        core.delete(root)
        loaded = assets.load(bpy.context, path)
        main = next(m for m in composition.members(loaded) if m.name.endswith("Main Shards"))
        layer = main.children[0]
        self.assertEqual(parts(), aligned)

    def test_spent_main_body_clears_before_the_ember_tail(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        camera()
        bpy.context.scene.camera.data.ortho_scale = 5.5
        bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 96
        for member in composition.members(root):
            member.children[0].hide_render = not member.name.endswith("Main Shards")
        main = next(m for m in composition.members(root) if m.name.endswith("Main Shards"))

        def light(frame):
            return sum(value for i, value in enumerate(render_pixels(frame)) if i % 4 != 3)

        peak = light(5)
        self.assertGreater(peak, 1)
        # A protected inner pole used to turn into a persistent opaque cup
        # during outward peeling, despite the keyframe-only check passing.
        # Pressure masses now retain a cooled, outward-moving afterburn;
        # the pivot must still clear instead of leaving the old opaque cup.
        self.assertLess(light(10), peak * 0.5)
        pixels = render_pixels(11)
        center = (48 * 96 + 48) * 4
        self.assertLess(max(pixels[center : center + 3]), 0.05)
        self.assertLess(light(15), peak * 0.08)
        update(main, fade=0.0)
        self.assertGreater(light(15), peak * 0.2)

    def test_pressure_front_is_fast_and_expansion_stays_editable(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        wave = next(m for m in composition.members(root) if m["vfx_module"] == "mesh.ring")

        def radius(frame):
            return max(sum(c * c for c in p) ** 0.5 for p in geometry(root, frame)[wave["vfx_id"]])

        peak = radius(5)
        self.assertGreater(peak, radius(19) * 0.32)
        update(wave, expansion=0.5)
        self.assertLess(radius(5), peak * 0.5)

    def test_fine_width_control_preserves_pressure_and_auxiliary_geometry(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        main = next(m for m in composition.members(root) if m.name.endswith("Main Shards"))
        layer = main.children[0]
        width = layer.modifiers[0].node_group.nodes["Fine Ejection Width"].outputs[0]

        def parts():
            bpy.context.scene.frame_set(5)
            mesh = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            return {
                role: [
                    tuple(v.co)
                    for v, part in zip(mesh.vertices, mesh.attributes["impact_lobe"].data)
                    if part.value == role
                ]
                for role in (0, 1, 2)
            }

        before = parts()
        width.default_value = 2.0
        after = parts()
        self.assertEqual(after[0], before[0])
        self.assertEqual(after[2], before[2])
        self.assertNotEqual(after[1], before[1])
        path = ROOT / "work/impact-fine-width.blend"
        assets.write(path, root)
        core.delete(root)
        restored = assets.load(bpy.context, path)
        main = next(m for m in composition.members(restored) if m.name.endswith("Main Shards"))
        layer = main.children[0]
        self.assertEqual(parts(), after)

    def test_pressure_unfurl_preserves_fine_and_auxiliary_paths(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        main = next(m for m in composition.members(root) if m.name.endswith("Main Shards"))
        layer = main.children[0]

        def parts():
            bpy.context.scene.frame_set(9)
            mesh = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
            return {
                role: [
                    tuple(v.co)
                    for v, attr in zip(mesh.vertices, mesh.attributes["impact_lobe"].data)
                    if attr.value == role
                ]
                for role in (0, 1, 2)
            }

        before = parts()
        layer.modifiers[0].node_group.nodes["Pressure Unfurl"].outputs[0].default_value = 0
        after = parts()
        self.assertNotEqual(before[0], after[0])
        self.assertEqual(before[1], after[1])
        self.assertEqual(before[2], after[2])

    def test_pressure_crest_height_preserves_other_layers_and_zero_width_collapses(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        wave = next(m for m in composition.members(root) if m["vfx_module"] == "mesh.ring")
        before = geometry(root, 5)
        raised = before[wave["vfx_id"]]
        self.assertGreater(max(p[2] for p in raised) - min(p[2] for p in raised), 0.01)
        layer = wave.children[0]
        layer.modifiers[0].node_group.nodes["Pressure Crest Height"].outputs[0].default_value = 0
        flat = geometry(root, 5)
        for uid, points in before.items():
            if uid != wave["vfx_id"]:
                self.assertEqual(flat[uid], points)
        points = flat[wave["vfx_id"]]
        self.assertLess(max(p[2] for p in points) - min(p[2] for p in points), 1e-6)
        layer.modifiers[0].node_group.nodes["Pressure Crest Height"].outputs[0].default_value = 0.9
        update(wave, width=0)
        bpy.context.scene.frame_set(5)
        evaluated = layer.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        self.assertLess(sum(face.area for face in evaluated.polygons), 1e-6)

    def test_pressure_crest_ink_changes_color_without_changing_coverage(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        wave = next(m for m in composition.members(root) if m["vfx_module"] == "mesh.ring")
        for member in composition.members(root):
            member.children[0].hide_render = member != wave
        camera()
        scene = bpy.context.scene
        scene.render.film_transparent = True
        scene.render.resolution_x = scene.render.resolution_y = 192
        ink = (
            wave.children[0]
            .data.materials[0]
            .node_tree.nodes["Pressure Crest Edge Contrast"]
            .outputs[0]
        )
        ink.default_value = 0
        plain = render_pixels(5)
        ink.default_value = 1
        outlined = render_pixels(5)
        self.assertEqual(plain[3::4], outlined[3::4])
        self.assertGreater(max(abs(a - b) for a, b in zip(plain, outlined)), 0.02)

    def test_dissipated_pressure_does_not_leave_black_cycles_surfaces(self):
        root = core.create(bpy.context, "IMPACT_BURST", "LOW")
        camera()
        scene = bpy.context.scene
        scene.camera.location = (3, -5, 6)
        scene.camera.rotation_euler = (-scene.camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera.data.ortho_scale = 8.2
        scene.render.resolution_x = scene.render.resolution_y = 96
        background = scene.world.node_tree.nodes["Background"]
        background.inputs["Color"].default_value = (0.18, 0.20, 0.24, 1)
        background.inputs["Strength"].default_value = 1
        main = next(m for m in composition.members(root) if m.name.endswith("Main Shards"))
        for member in composition.members(root):
            member.children[0].hide_render = member != main
        # Default Cycles transparent-ray limits must reveal the background
        # after dissipation. Invisible overlapping caps previously turned black.
        spent = render_pixels(14)
        main.children[0].hide_render = True
        empty = render_pixels(14)
        self.assertEqual(spent, empty)


addon.register()
result = unittest.TextTestRunner(verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(ImpactTests)
)
if not result.wasSuccessful():
    raise RuntimeError("Impact integration failed")
bpy.ops.wm.read_factory_settings(use_empty=True)
root = core.create(bpy.context, "IMPACT_BURST", "LOW")
root.name = "Persisted Impact"
camera()
bpy.context.scene.camera.data.ortho_scale = 5.5
for frame in (2, 5, 14):
    state = geometry(root, frame)
    for child in composition.members(root):
        child[f"expected_shape_{frame}"] = [c for v in state[child["vfx_id"]] for c in v]
for frame in (2, 5, 9, 11, 14):
    root[f"expected_pixels_{frame}"] = render_pixels(frame)
addon.unregister()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/impact.blend"))
print("IMPACT_INTEGRATION_OK")
