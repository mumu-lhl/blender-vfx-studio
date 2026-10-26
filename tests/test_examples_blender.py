"""Starter assets remain independent of preview-scene helpers and authoring code."""

import sys
import unittest
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from emitter_test_support import mesh, particles
from particle_test_support import camera, render_pixels

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

    def test_charge_motes_gather_without_crossing_center_and_generic_emitter_is_unchanged(self):
        charge = create_effect("energy-charge")
        motes = next(
            r for r in composition.members(charge) if r["vfx_module"] == "particle.emitter"
        )
        for key, value in dict(
            rate=0.1, lifetime=1.0, emission_seconds=3.0, velocity=1.0, spawn_radius=1.4
        ).items():
            motes[key] = value
        motes.update_tag()
        bpy.context.view_layer.update()
        centers = []
        for frame in (1, 4, 7, 10):
            actual = particles(motes, frame)
            self.assertEqual(len(actual), 1)
            centers.append(actual[0][0])
        distances = [c.length for c in centers]
        self.assertTrue(all(a > b for a, b in zip(distances, distances[1:])))
        travel = [a - b for a, b in zip(distances, distances[1:])]
        self.assertGreater(travel[2], travel[1])
        self.assertGreater(travel[1], travel[0])
        self.assertGreater(centers[0].cross(centers[1]).length, 0.01)
        repeated = particles(motes, 7)[0][0]
        self.assertLess((repeated - centers[2]).length, 1e-5)
        motes["velocity"] = 3.0
        motes.update_tag()
        for frame in (7, 10):
            self.assertAlmostEqual(particles(motes, frame)[0][0].length, 0, places=5)
        bpy.context.scene.frame_set(1)
        ordinary = core.create_emitter(bpy.context)
        for key in (
            "rate",
            "lifetime",
            "emission_seconds",
            "duration",
            "velocity",
            "gravity",
            "spread",
            "randomness",
            "spawn_radius",
        ):
            ordinary[key] = motes[key]
        ordinary.update_tag()
        bpy.context.view_layer.update()
        self.assertGreater(particles(ordinary, 7)[0][0].length, particles(ordinary, 1)[0][0].length)

    def test_charge_motes_follow_their_curved_velocity_with_less_geometry(self):
        charge = create_effect("energy-charge")
        motes = next(
            r for r in composition.members(charge) if r["vfx_module"] == "particle.emitter"
        )
        for key, value in dict(rate=0.1, lifetime=1.0, emission_seconds=3.0).items():
            motes[key] = value
        motes.update_tag()
        for frame in (4, 7, 4):
            before_center = particles(motes, frame - 0.02)[0][0]
            after_center = particles(motes, frame + 0.02)[0][0]
            centers = particles(motes, frame)
            self.assertEqual(len(centers), 1)
            center = centers[0][0]
            vertices = mesh(motes, frame).vertices
            self.assertLess(len(vertices), 12)
            tangent = (after_center - before_center).normalized()
            offsets = [v.co - center for v in vertices]
            length = max(abs(v.dot(tangent)) for v in offsets)
            width = max((v - tangent * v.dot(tangent)).length for v in offsets)
            self.assertGreater(length, width * 5)
        before = particles(motes, 7)[0][1]
        motes["size"] *= 2
        motes.update_tag()
        self.assertAlmostEqual(particles(motes, 7)[0][1], before * 2, places=5)

    def test_charge_streams_ignite_and_follow_group_speed(self):
        charge = create_effect("energy-charge")
        camera()
        bpy.context.scene.render.dither_intensity = 0
        for member in composition.members(charge):
            if member["vfx_module"] != "mesh.ring":
                member.children[0].hide_render = True

        def energy(pixels):
            return sum(sum(pixels[i : i + 3]) for i in range(0, len(pixels), 4))

        born = energy(render_pixels(1))
        early = energy(render_pixels(7))
        opened = energy(render_pixels(16))
        self.assertLess(born, 1e-5)
        self.assertGreater(early, 0.01)
        self.assertLess(early, opened)
        reference = render_pixels(7)
        self.assertEqual(render_pixels(7), reference)
        charge["speed"] = 2.0
        charge.update_tag()
        self.assertEqual(render_pixels(4), reference)
        for obj in list(bpy.context.scene.objects):
            if obj.get("vfx_role") == "layer":
                obj.hide_render = True
        bpy.context.scene.frame_set(1)
        core.create(bpy.context, "ENERGY_RING", "LOW")
        self.assertGreater(energy(render_pixels(1)), 1)

    def test_charge_core_builds_tension_within_a_bounded_geometry_budget(self):
        charge = create_effect("energy-charge")
        core_member = next(
            r for r in composition.members(charge) if r["vfx_module"] == "shader.shield"
        )

        def dimensions(frame):
            vertices = mesh(core_member, frame).vertices
            radial = sum(v.co.x**2 + v.co.y**2 for v in vertices) / len(vertices)
            height = max(v.co.z for v in vertices) - min(v.co.z for v in vertices)
            return radial, height

        early, charged = dimensions(13), dimensions(37)
        self.assertLess(charged[0], early[0] * 0.5)
        # Pressure contracts all three axes while retaining a visible depth.
        self.assertGreater(charged[1], early[1] * 0.35)
        self.assertLess(charged[1], early[1] * 0.85)
        for frame in (1, 7, 22, 37, 46, 48):
            self.assertLessEqual(
                vertex_count(charge, frame), 900
            )  # Includes the 54-vertex inner kernel.

    def test_auxiliary_intake_width_preserves_main_paths_and_survives_assets(self):
        charge = create_effect("energy-charge")
        core_member = next(
            r for r in composition.members(charge) if r["vfx_module"] == "shader.shield"
        )
        guide = (
            core_member.children[0]
            .modifiers[0]
            .node_group.nodes["Auxiliary Guide Width"]
            .outputs[0]
        )

        def paths():
            evaluated = mesh(core_member, 13)
            return {
                role: [
                    tuple(v.co)
                    for v, part in zip(
                        evaluated.vertices, evaluated.attributes["charge_tongue"].data
                    )
                    if part.value == role
                ]
                for role in range(7)
            }

        before = paths()
        guide.default_value = 0.16
        after = paths()
        for role in (0, 3, 6):
            self.assertEqual(len(before[role]), len(after[role]))
            self.assertLess(
                max((Vector(a) - Vector(b)).length for a, b in zip(before[role], after[role])), 1e-5
            )
        self.assertTrue(any(before[role] != after[role] for role in (1, 2, 4, 5)))
        path = WORK / "charge-intake-controls.blend"
        assets.write(path, charge)
        core.delete(charge)
        loaded = assets.load(bpy.context, path)
        core_member = next(
            r for r in composition.members(loaded) if r["vfx_module"] == "shader.shield"
        )
        self.assertEqual(paths(), after)
        tree = core_member.children[0].modifiers[0].node_group
        tree.nodes["Auxiliary Guide Width"].outputs[0].default_value = 0
        tree.nodes["Auxiliary Packet Width"].outputs[0].default_value = 0
        collapsed = mesh(core_member, 31)
        roles = collapsed.attributes["charge_tongue"].data
        auxiliary_area = sum(
            face.area
            for face in collapsed.polygons
            if int(roles[face.vertices[0]].value) in (1, 2, 4, 5)
        )
        self.assertLess(auxiliary_area, 1e-6)

    def test_core_intake_shape_and_color_follow_group_speed_together(self):
        charge = create_effect("energy-charge")
        camera()
        bpy.context.scene.render.dither_intensity = 0
        for member in composition.members(charge):
            member.children[0].hide_render = member["vfx_module"] != "shader.shield"
        original = render_pixels(31)
        self.assertGreater(sum(original), 1)
        charge["speed"] = 2.0
        charge.update_tag()
        self.assertEqual(render_pixels(16), original)

    def test_authored_core_opacity_dissolve_and_strength_control_all_surfaces(self):
        charge = create_effect("energy-charge")
        camera()
        bpy.context.scene.render.dither_intensity = 0
        members = composition.members(charge)
        core_member = next(r for r in members if r["vfx_module"] == "shader.shield")
        for member in members:
            if member != core_member:
                member.children[0].hide_render = True

        def energy():
            pixels = render_pixels(31)
            return sum(sum(pixels[i : i + 3]) for i in range(0, len(pixels), 4))

        self.assertGreater(energy(), 0.01)
        for key, value in (("opacity", 0), ("dissolve", 1), ("strength", 0)):
            old = core_member[key]
            core_member[key] = value
            core_member.update_tag()
            self.assertLess(energy(), 1e-5, key)
            core_member[key] = old
            core_member.update_tag()

        # The compressed tail is only a few pixels in the emitter-wide framing.
        # Inspect the core at a useful scale so erosion cannot hide in sampling.
        bpy.context.scene.camera.data.ortho_scale = 1
        bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 96

        def coverage():
            pixels = render_pixels(44)
            return sum(max(pixels[i : i + 3]) > 1e-5 for i in range(0, len(pixels), 4))

        eroded = coverage()
        core_member["fade"] = 0
        core_member.update_tag()
        self.assertGreater(coverage(), eroded)

    def test_charge_core_contour_changes_color_without_expanding_coverage(self):
        charge = create_effect("energy-charge")
        camera()
        scene = bpy.context.scene
        scene.camera.data.ortho_scale = 2.4
        scene.render.resolution_x = scene.render.resolution_y = 96
        scene.render.film_transparent = True
        scene.render.dither_intensity = 0
        member = next(r for r in composition.members(charge) if r["vfx_module"] == "shader.shield")
        for other in composition.members(charge):
            other.children[0].hide_render = other != member
        contrast = (
            member.children[0].data.materials[0].node_tree.nodes["Core Edge Contrast"].outputs[0]
        )
        contrast.default_value = 0
        plain = render_pixels(22)
        contrast.default_value = 0.85
        outlined = render_pixels(22)
        self.assertEqual(plain[3::4], outlined[3::4])
        self.assertLess(sum(outlined), sum(plain) - 1)
        for index, value in enumerate((1.0, 0.05, 0.01)):
            member[f"color_{index}"] = value
        member.update_tag()
        warm = render_pixels(22)
        self.assertGreater(sum(warm[0::4]), sum(warm[2::4]))

    def test_hidden_charge_core_reveals_a_light_background(self):
        root = create_effect("energy-charge")
        camera()
        scene = bpy.context.scene
        scene.render.dither_intensity = 0
        background = scene.world.node_tree.nodes["Background"]
        background.inputs["Strength"].default_value = 1
        background.inputs["Color"].default_value = (0.55, 0.60, 0.68, 1)
        scene.cycles.transparent_max_bounces = 8
        scene.render.resolution_x = scene.render.resolution_y = 96
        view = scene.camera
        view.location = (4, -6, 3.5)
        view.rotation_euler = (
            (Vector((0, 0, 0.1)) - view.location).to_track_quat("-Z", "Y").to_euler()
        )
        members = composition.members(root)
        core_member = next(r for r in members if r["vfx_module"] == "shader.shield")
        core_member.children[0].hide_render = True
        empty = render_pixels(31)
        core_member.children[0].hide_render = False
        for key, value in (("opacity", 0), ("dissolve", 1)):
            old = core_member[key]
            core_member[key] = value
            core_member.update_tag()
            actual = render_pixels(31)
            self.assertLess(max(abs(a - b) for a, b in zip(actual, empty)), 1e-6, key)
            core_member[key] = old
            core_member.update_tag()
        view.data.ortho_scale = 1.2
        core_member.children[0].hide_render = True
        empty = render_pixels(46)
        core_member.children[0].hide_render = False
        tail = render_pixels(46)
        self.assertLess(max(abs(a - b) for a, b in zip(tail, empty)), 1e-6, "core release complete")

    def test_charge_fades_before_its_native_lifetime_cutoff(self):
        root = create_effect("energy-charge")
        camera()
        bpy.context.scene.render.dither_intensity = 0
        bpy.context.scene.camera.data.ortho_scale = 4.8

        def energy(frame):
            pixels = render_pixels(frame)
            return sum(sum(pixels[i : i + 3]) for i in range(0, len(pixels), 4))

        middle, tail, ended = (energy(frame) for frame in (22, 48, 49))
        self.assertGreater(middle, 5)
        self.assertLess(tail, middle * 0.2)
        self.assertLess(ended, 1e-5)
        self.assertGreater(vertex_count(root, 48), 0)
        self.assertEqual(vertex_count(root, 49), 0)

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
            if key == "energy-charge":
                for instance in (a, b):
                    for member in composition.members(instance):
                        self.assertIsInstance(member.get("vfx_parameter_keys"), str)
                        self.assertTrue(
                            set(member["vfx_parameter_keys"].split(",")).issubset(member.keys())
                        )

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
