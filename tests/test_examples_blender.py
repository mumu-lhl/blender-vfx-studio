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
        # Sparse early strokes can miss every single-sample ray at 48 pixels.
        bpy.context.scene.render.resolution_x = bpy.context.scene.render.resolution_y = 96
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

    def test_charge_core_builds_tension_without_frame_accumulation(self):
        charge = create_effect("energy-charge")
        core_member = next(
            r for r in composition.members(charge) if r["vfx_module"] == "shader.shield"
        )

        def dimensions(frame):
            evaluated = mesh(core_member, frame)
            vertices = evaluated.vertices
            intake = [
                v
                for v, inner in zip(vertices, evaluated.attributes["charge_inner"].data)
                if inner.value < 0.5
            ]
            radial = sum(v.co.x**2 + v.co.y**2 for v in intake) / len(intake)
            height = max(v.co.z for v in vertices) - min(v.co.z for v in vertices)
            return radial, height

        early, charged = dimensions(13), dimensions(37)
        self.assertLess(charged[0], early[0] * 0.5)
        # Intake contracts while the stored center gains volume; the whole
        # effect keeps depth instead of collapsing to a flat slice.
        self.assertGreater(charged[1], early[1] * 0.35)
        self.assertLess(charged[1], early[1] * 0.85)
        # Seeking does not accumulate generated geometry. Topology counts are
        # a stability check, not a proxy for viewport or render performance.
        expected = {frame: vertex_count(charge, frame) for frame in (1, 7, 22, 37, 46, 48)}
        for frame in (37, 7, 48, 1, 46, 22):
            self.assertEqual(vertex_count(charge, frame), expected[frame])

    def test_pressure_heart_has_filled_volume_and_responds_to_stored_size(self):
        charge = create_effect("energy-charge")
        member = next(r for r in composition.members(charge) if r["vfx_module"] == "shader.shield")

        def volume(frame):
            evaluated = mesh(member, frame)
            selected = evaluated.attributes["charge_heart"].data
            evaluated.calc_loop_triangles()
            result = 0
            for triangle in evaluated.loop_triangles:
                if all(selected[i].value > 0.5 for i in triangle.vertices):
                    a, b, c = (evaluated.vertices[i].co for i in triangle.vertices)
                    result += a.dot(b.cross(c)) / 6
            return abs(result)

        early, stored = volume(13), volume(37)
        self.assertGreater(early, 0.00001)
        self.assertGreater(stored, early * 3)
        node = member.children[0].modifiers[0].node_group.nodes["Nucleus Stored Size"]
        node.outputs[0].default_value *= 0.6
        self.assertLess(volume(37), stored * 0.6)

    def test_shell_can_close_without_moving_the_heart_or_intakes(self):
        charge = create_effect("energy-charge")
        member = next(r for r in composition.members(charge) if r["vfx_module"] == "shader.shield")

        def sample():
            evaluated = mesh(member, 37)
            shells = [
                a.value > 0.5 and b.value < 0.5
                for a, b in zip(
                    evaluated.attributes["charge_inner"].data,
                    evaluated.attributes["charge_heart"].data,
                )
            ]
            area = sum(
                face.area for face in evaluated.polygons if all(shells[i] for i in face.vertices)
            )
            return [v.co.copy() for v in evaluated.vertices], shells, area

        before, shells, area = sample()
        self.assertGreater(area, 0.001)
        member.children[0].modifiers[0].node_group.nodes["Nucleus Shell Width"].outputs[
            0
        ].default_value = 0
        after, _, collapsed_area = sample()
        self.assertLess(collapsed_area, area * 0.01)
        self.assertGreater(max((a - b).length for a, b in zip(before, after)), 0.01)
        self.assertTrue(
            all((a - b).length < 1e-6 for a, b, shell in zip(before, after, shells) if not shell)
        )

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

    def test_release_pinches_only_the_nucleus_and_follows_group_speed(self):
        charge = create_effect("energy-charge")
        member = next(r for r in composition.members(charge) if r["vfx_module"] == "shader.shield")
        tree = member.children[0].modifiers[0].node_group

        def shape(frame):
            evaluated = mesh(member, frame)
            inner = evaluated.attributes["charge_inner"].data
            nucleus = [
                v.co.copy() for v, part in zip(evaluated.vertices, inner) if part.value > 0.5
            ]
            outside = [
                tuple(v.co) for v, part in zip(evaluated.vertices, inner) if part.value < 0.5
            ]
            spans = [max(v[i] for v in nucleus) - min(v[i] for v in nucleus) for i in range(3)]
            return spans[2] / max(spans[:2]), outside, [tuple(v.co) for v in evaluated.vertices]

        aspect, outside, reference = shape(43)
        pinch = tree.nodes["Release Pinch"].outputs[0]
        stretch = tree.nodes["Release Stretch"].outputs[0]
        original = pinch.default_value, stretch.default_value
        pinch.default_value = stretch.default_value = 0
        relaxed, unchanged, _ = shape(43)
        self.assertGreater(aspect, relaxed * 2)
        self.assertEqual(outside, unchanged)
        pinch.default_value, stretch.default_value = original
        charge["speed"] = 2
        charge.update_tag()
        _, _, accelerated = shape(22)
        self.assertEqual(len(reference), len(accelerated))
        self.assertLess(
            max((Vector(a) - Vector(b)).length for a, b in zip(reference, accelerated)), 1e-5
        )

    def test_native_discharge_moves_only_the_nucleus_toward_local_positive_z(self):
        charge = create_effect("energy-charge")
        member = next(r for r in composition.members(charge) if r["vfx_module"] == "shader.shield")
        tree = member.children[0].modifiers[0].node_group

        def positions():
            evaluated = mesh(member, 43)
            return {
                role: [
                    v.co.copy()
                    for v, part in zip(
                        evaluated.vertices, evaluated.attributes["charge_inner"].data
                    )
                    if (part.value > 0.5) == role
                ]
                for role in (False, True)
            }

        forward = positions()
        tree.nodes["Radius Relative Travel"].inputs[1].default_value = 0
        centered = positions()
        self.assertEqual(forward[False], centered[False])
        deltas = [a - b for a, b in zip(forward[True], centered[True])]
        self.assertGreater(min(v.z for v in deltas), 0.02)
        self.assertLess(max(abs(v.x) + abs(v.y) for v in deltas), 1e-6)

    def test_stored_compression_changes_only_nucleus_and_follows_group_time(self):
        charge = create_effect("energy-charge")
        member = next(r for r in composition.members(charge) if r["vfx_module"] == "shader.shield")
        control = member.children[0].modifiers[0].node_group.nodes["Nucleus Compression"].outputs[0]

        def shape(frame):
            evaluated = mesh(member, frame)
            points, outside = [], []
            for v, part in zip(evaluated.vertices, evaluated.attributes["charge_inner"].data):
                (points if part.value > 0.5 else outside).append(tuple(v.co))
            spans = [max(v[i] for v in points) - min(v[i] for v in points) for i in range(3)]
            return spans, outside, points

        compressed, outside, reference = shape(37)
        early = shape(13)
        discharged = shape(45)
        control.default_value = 0
        relaxed, unchanged, _ = shape(37)
        self.assertEqual(outside, unchanged)
        self.assertLess(compressed[2], relaxed[2] * 0.6)
        self.assertGreater(compressed[0], relaxed[0] * 1.3)
        volume_ratio = (compressed[0] * compressed[1] * compressed[2]) / (
            relaxed[0] * relaxed[1] * relaxed[2]
        )
        self.assertAlmostEqual(volume_ratio, 1, places=4)
        self.assertEqual(early, shape(13))
        self.assertEqual(discharged, shape(45))
        control.default_value = 0.6
        charge["speed"] = 2
        charge.update_tag()
        _, _, accelerated = shape(19)
        self.assertLess(
            max((Vector(a) - Vector(b)).length for a, b in zip(reference, accelerated)), 1e-5
        )

    def test_primary_bundle_heads_travel_toward_the_core(self):
        charge = create_effect("energy-charge")
        member = next(r for r in composition.members(charge) if r["vfx_module"] == "shader.shield")
        positions = []
        for frame in (7, 13, 19):
            evaluated = mesh(member, frame)
            rings = {}
            for vertex, role, filament, u in zip(
                evaluated.vertices,
                evaluated.attributes["charge_tongue"].data,
                evaluated.attributes["charge_filament"].data,
                evaluated.attributes["charge_core_u"].data,
            ):
                if role.value == 0 and filament.value == 0:
                    rings.setdefault(u.value, []).append(vertex.co.copy())
            sections = []
            for u, points in rings.items():
                center = sum(points, Vector()) / len(points)
                area = sum((point - center).length_squared for point in points) / len(points)
                sections.append((u, area))
            positions.append(
                sum(u * area for u, area in sections) / sum(area for _, area in sections)
            )
        self.assertGreater(positions[1], positions[0] + 0.1)
        self.assertGreater(positions[2], positions[1] + 0.1)

    def test_nucleus_stores_volume_while_the_surrounding_paths_compress(self):
        charge = create_effect("energy-charge")
        member = next(r for r in composition.members(charge) if r["vfx_module"] == "shader.shield")

        def radius(frame):
            evaluated = mesh(member, frame)
            points = [
                vertex.co.copy()
                for vertex, inner in zip(
                    evaluated.vertices, evaluated.attributes["charge_inner"].data
                )
                if inner.value > 0.5
            ]
            center = sum(points, Vector()) / len(points)
            return (sum((point - center).length_squared for point in points) / len(points)) ** 0.5

        early, charged = radius(13), radius(37)
        self.assertGreater(charged, early * 1.5)
        self.assertLess(charged, early * 3)
        tree = member.children[0].modifiers[0].node_group
        tree.nodes["Nucleus Seed Size"].outputs[0].default_value *= 1.4
        self.assertGreater(radius(13), early * 1.2)
        tree.nodes["Nucleus Seed Size"].outputs[0].default_value = 0
        self.assertLess(radius(13), 1e-6)

    def test_ground_intake_reaches_the_core_and_lift_follows_group_time(self):
        charge = create_effect("energy-charge")
        members = composition.members(charge)
        ground = next(r for r in members if r.name == "Charge • Ground Intake")
        nucleus = next(r for r in members if r["vfx_module"] == "shader.shield")
        layer = ground.children[0]
        control = layer.modifiers[0].node_group.nodes["Ground Intake Lift"].outputs[0]

        def shape(frame):
            evaluated = mesh(ground, frame)
            return [tuple(v.co) for v in evaluated.vertices]

        reference = shape(31)
        world = [layer.matrix_world @ Vector(p) for p in reference]
        self.assertAlmostEqual(
            max(v.z for v in world), nucleus.matrix_world.translation.z, places=5
        )
        self.assertLess(min(v.z for v in world), -0.7)
        core_before = [tuple(v.co) for v in mesh(nucleus, 31).vertices]
        control.default_value = 0
        lowered = [layer.matrix_world @ Vector(p) for p in shape(31)]
        self.assertLess(max(v.z for v in lowered), -0.7)
        self.assertEqual(core_before, [tuple(v.co) for v in mesh(nucleus, 31).vertices])
        control.default_value = 0.8
        charge["speed"] = 2
        charge.update_tag()
        accelerated = shape(16)
        self.assertLess(
            max((Vector(a) - Vector(b)).length for a, b in zip(reference, accelerated)), 1e-5
        )

    def test_outer_intakes_arrive_at_the_core_from_different_heights(self):
        charge = create_effect("energy-charge")
        outer = next(
            r for r in composition.members(charge) if r.name.startswith("Charge • Converging")
        )
        evaluated = mesh(outer, 31)
        phases = evaluated.attributes["charge_phase"].data
        along = evaluated.attributes["charge_u"].data
        ends, starts = {}, {}
        for vertex, phase, u in zip(evaluated.vertices, phases, along):
            if u.value == 1:
                ends.setdefault(phase.value, []).append(vertex.co.copy())
            elif u.value == 0:
                starts.setdefault(phase.value, []).append(vertex.co.copy())
        end_centers = [sum(points, Vector()) / len(points) for points in ends.values()]
        start_centers = [sum(points, Vector()) / len(points) for points in starts.values()]
        self.assertEqual(len(end_centers), 3)
        self.assertLess(max(point.length for point in end_centers), 0.2)
        self.assertGreater(max(p.z for p in start_centers) - min(p.z for p in start_centers), 1)

    def test_intake_width_changes_section_without_moving_its_path(self):
        charge = create_effect("energy-charge")
        member = next(r for r in composition.members(charge) if r["vfx_module"] == "shader.shield")
        tree = member.children[0].modifiers[0].node_group

        def centers():
            evaluated = mesh(member, 37)
            rings = {}
            for vertex, role, u in zip(
                evaluated.vertices,
                evaluated.attributes["charge_tongue"].data,
                evaluated.attributes["charge_core_u"].data,
            ):
                if round(role.value) in (0, 3):
                    key = (round(role.value), round(u.value, 5))
                    rings.setdefault(key, []).append(vertex.co.copy())
            return {key: sum(points, Vector()) / len(points) for key, points in rings.items()}

        before = centers()
        tree.nodes["Main Intake Guide Width"].outputs[0].default_value = 1.32
        after = centers()
        self.assertEqual(before.keys(), after.keys())
        self.assertLess(max((before[key] - after[key]).length for key in before), 1e-5)

    def test_core_intake_shape_and_color_follow_group_speed_together(self):
        charge = create_effect("energy-charge")
        camera()
        bpy.context.scene.render.dither_intensity = 0
        for member in composition.members(charge):
            member.children[0].hide_render = member["vfx_module"] != "shader.shield"
        original = render_pixels(31)
        self.assertGreater(sum(value for i, value in enumerate(original) if i % 4 != 3), 1)
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

    def test_intake_weight_changes_support_without_changing_the_nucleus(self):
        root = create_effect("energy-charge")
        camera()
        scene = bpy.context.scene
        scene.render.resolution_x = scene.render.resolution_y = 96
        scene.camera.data.ortho_scale = 2.4
        scene.render.dither_intensity = 0
        members = composition.members(root)
        member = next(r for r in members if r["vfx_module"] == "shader.shield")
        for other in members:
            other.children[0].hide_render = other != member
        layer = member.children[0]
        control = layer.modifiers[0].node_group.nodes["Intake Weight"].outputs[0]
        control.default_value = 1
        full = render_pixels(22)
        before_mesh = mesh(member, 22)
        before = [
            tuple(v.co)
            for v, inner in zip(before_mesh.vertices, before_mesh.attributes["charge_inner"].data)
            if inner.value > 0.5
        ]
        control.default_value = 0
        focal = render_pixels(22)
        evaluated = mesh(member, 22)
        self.assertEqual(
            before,
            [
                tuple(v.co)
                for v, inner in zip(evaluated.vertices, evaluated.attributes["charge_inner"].data)
                if inner.value > 0.5
            ],
        )
        self.assertTrue(
            all(v.value == 0 for v in evaluated.attributes["charge_support_weight"].data)
        )
        self.assertGreater(sum(focal[0::4]) + sum(focal[1::4]) + sum(focal[2::4]), 0.1)
        self.assertGreater(max(abs(a - b) for a, b in zip(full, focal)), 0.1)
        for other in members:
            if "Ground Intake" not in other.name:
                continue
            layer.hide_render = True
            other.children[0].hide_render = False
            weight = other.children[0].modifiers[0].node_group.nodes["Intake Weight"].outputs[0]
            weight.default_value = 1
            visible = render_pixels(22)
            weight.default_value = 0
            hidden = render_pixels(22)
            self.assertGreater(sum(visible), sum(hidden) + 1)
            self.assertLess(max(v for i, v in enumerate(hidden) if i % 4 != 3), 1e-5)

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
        channels = (
            member.children[0]
            .data.materials[0]
            .node_tree.nodes["Intake Channel Contrast"]
            .outputs[0]
        )
        channels.default_value = 0
        smooth = render_pixels(22)
        channels.default_value = 1
        streaked = render_pixels(22)
        self.assertEqual(smooth[3::4], streaked[3::4])
        self.assertGreater(max(abs(a - b) for a, b in zip(smooth, streaked)), 0.01)
        nucleus_white = (
            member.children[0]
            .data.materials[0]
            .node_tree.nodes["Nucleus White Threshold"]
            .outputs[0]
        )
        nucleus_white.default_value = 0
        broad_white = render_pixels(37)
        nucleus_white.default_value = 1.1
        blue_body = render_pixels(37)
        self.assertEqual(broad_white[3::4], blue_body[3::4])
        self.assertGreater(max(abs(a - b) for a, b in zip(broad_white, blue_body)), 0.1)
        nucleus_white.default_value = 0.72
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

    def test_builders_have_native_timing_and_explicit_quality(self):
        for key, layers, duration, quality in zip(
            EXAMPLES,
            (4, 4, 1, 4, 3, 2, 3, 3),
            (48, 24, 18, 18, 32, 52, 30, 72),
            ("LOW", "LOW", "LOW", "MEDIUM", "MEDIUM", "MEDIUM", "MEDIUM", "MEDIUM"),
            strict=True,
        ):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            root = create_effect(key)
            self.assertEqual(root["start"], 1)
            self.assertEqual(root["duration"], duration)
            self.assertFalse(root["loop"])
            members = (
                composition.members(root) if root["vfx_module"] == "core.composition" else [root]
            )
            self.assertEqual(len(members), layers)
            self.assertTrue(all(r["vfx_quality"] == quality for r in members))
            count = vertex_count(root, 7)
            self.assertGreater(count, 0)
            self.assertEqual(vertex_count(root, 0), 0)
            self.assertEqual(vertex_count(root, 81), 0)
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
