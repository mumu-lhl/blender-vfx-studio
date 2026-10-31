"""Native preparation preserves the original cut, contact and VFX alignment."""

import sys
import unittest
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.character_scene import add_effects, setup_base, shift_actor_timeline  # noqa: E402


class CharacterTimingTests(unittest.TestCase):
    def test_lightning_timeline_shift_preserves_both_actors_at_contact(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        fixture = setup_base()
        scene = bpy.context.scene
        offset = fixture["contact"]["frame"] - 3

        def pose(frame):
            scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            return [
                component
                for actor in (fixture["caster"], fixture["defender"])
                for bone in actor["rig"].evaluated_get(graph).pose.bones
                for row in bone.matrix
                for component in row
            ]

        expected = {frame: pose(frame) for frame in (49, 52, 63)}
        shift_actor_timeline(fixture, offset)
        for frame, before in expected.items():
            actual = pose(frame - offset)
            self.assertEqual(len(actual), len(before))
            self.assertLess(max(abs(a - b) for a, b in zip(actual, before)), 1e-5)
        scene.frame_set(3)
        weapon = fixture["caster"]["weapon"].evaluated_get(bpy.context.evaluated_depsgraph_get())
        self.assertLess(
            (weapon.matrix_world.translation - Vector(fixture["contact"]["hilt"])).length,
            1e-5,
        )

    def test_preparation_preserves_the_original_cut_and_recovery(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        fixture = setup_base()
        scene = bpy.context.scene
        caster = fixture["caster"]
        strip = next(
            strip
            for track in caster["rig"].animation_data.nla_tracks
            for strip in track.strips
            if "2H_Melee_Attack_Slice" in strip.name
        )
        frames = (16, 32, 43, 47, 49, 51, 57, 65, 69)

        def blade_poses():
            matrices = {}
            for frame in frames:
                scene.frame_set(frame)
                graph = bpy.context.evaluated_depsgraph_get()
                matrices[frame] = caster["weapon"].evaluated_get(graph).matrix_world.copy()
            return matrices

        prepared = blade_poses()
        # Compare with the original cut using the same rig, action and idle.
        strip.use_animated_time = False
        strip.blend_in = 4
        strip.frame_start = 37
        strip.scale = 32 / (strip.action_frame_end - strip.action_frame_start)
        original = blade_poses()
        errors = {
            frame: max(
                abs(prepared[frame][row][column] - original[frame][row][column])
                for row in range(4)
                for column in range(4)
            )
            for frame in frames
        }
        self.assertGreater(errors[32], 0.05, "Preparation must actually move the blade")
        for frame in frames:
            if frame >= 43:
                self.assertLess(errors[frame], 1e-5, f"The original cut changed at {frame}")
        self.assertEqual(fixture["contact"]["frame"], 49)

    def test_discharge_peak_and_fast_blade_direction_match_contact(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        fixture = add_effects(setup_base())
        scene = bpy.context.scene
        hit = fixture["contact"]["frame"]
        member = bpy.data.objects["Charge • Compressed Core"]
        tree = member.children[0].modifiers[0].node_group
        for frame, height in ((16, 0.12), (37, 0.12), (43, 0.048), (47, 0), (49, 0), (16, 0.12)):
            scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            socket = bpy.data.objects["Charge socket • world up"].evaluated_get(graph)
            midpoint = bpy.data.objects["Charge socket • blade midpoint"].evaluated_get(graph)
            offset = socket.matrix_world.translation - midpoint.matrix_world.translation
            self.assertLess((offset - Vector((0, 0, height))).length, 1e-6)
            self.assertLess(
                (
                    fixture["effects"][0].matrix_world.translation - socket.matrix_world.translation
                ).length,
                1e-6,
            )
        peak = tree.nodes["Release Pinch Begins"].inputs["From Max"].default_value
        scene.frame_set(hit - 2)
        self.assertLess(tree.nodes["Charge Clock"].outputs[0].default_value, peak - 0.02)
        scene.frame_set(hit)
        self.assertAlmostEqual(tree.nodes["Charge Clock"].outputs[0].default_value, peak, places=5)
        self.assertAlmostEqual(
            member.children[0]
            .data.materials[0]
            .node_tree.nodes["Charge Clock"]
            .outputs[0]
            .default_value,
            peak,
            places=5,
        )
        for frame in range(hit - 2, hit + 3):
            scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            blade = fixture["caster"]["weapon"].evaluated_get(graph)
            sample = next(q for q in fixture["trace"] if q["frame"] == frame)
            self.assertLess((blade.matrix_world.translation - Vector(sample["hilt"])).length, 1e-6)
            self.assertLess(
                (blade.matrix_world @ fixture["tip_local"] - Vector(sample["tip"])).length, 1e-6
            )
            direction = (Vector(sample["tip"]) - Vector(sample["hilt"])).normalized()
            socket = bpy.data.objects["Charge socket • world up"].evaluated_get(graph)
            aim = (socket.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
            self.assertGreater(aim.dot(direction), 0.999999)
            slash = bpy.data.objects["Combat • Arc Slash"].children[0].evaluated_get(graph)
            data = slash.data
            phase = (frame - slash.parent["start"]) / slash.parent["duration"]
            front = min(phase / slash.parent["attack"], 1)
            edge = [
                slash.matrix_world @ v.co
                for v in data.vertices
                if data.attributes["vfx_wake"].data[v.index].value < 0.01
                and data.attributes["vfx_inner"].data[v.index].value < 0.001
                and abs(data.attributes["vfx_arc"].data[v.index].value - front) < 0.04
            ]
            tip = Vector(sample["tip"])
            self.assertLess(
                min((p - tip).length for p in edge),
                0.07 if front < 1 else 1e-5,
                f"Slash front must meet the real blade at frame {frame}",
            )
        scene["timing_contact"] = hit
        scene["timing_peak"] = peak
        scene["timing_weapon"] = fixture["caster"]["weapon"].name
        scene["timing_tip"] = tuple(fixture["tip_local"])
        (ROOT / "work").mkdir(exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/character-timing-test.blend"))


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(CharacterTimingTests)
    )
    if not result.wasSuccessful():
        raise RuntimeError("Character charge timing failed")
    print("CHARACTER_CHARGE_CONTACT_TIMING_OK")
