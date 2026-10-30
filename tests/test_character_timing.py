"""Charge discharge follows real blade contact without changing the actor's motion."""

import sys
import unittest
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.character_scene import add_effects, setup_base  # noqa: E402


class CharacterTimingTests(unittest.TestCase):
    def test_discharge_peak_and_fast_blade_direction_match_contact(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        fixture = add_effects(setup_base())
        scene = bpy.context.scene
        hit = fixture["contact"]["frame"]
        member = bpy.data.objects["Charge • Compressed Core"]
        tree = member.children[0].modifiers[0].node_group
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
