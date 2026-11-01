"""Check the directed shot's real contact, planted body and portable animation."""

import sys
import unittest
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blender_vfx_studio import assets, binding, composition, core  # noqa: E402
from tools.character_scene import add_effects, setup_base  # noqa: E402
from tools.combat_direction import direct_effects  # noqa: E402


def matrix_values(matrix):
    return tuple(v for row in matrix for v in row)


def fixture():
    result = add_effects(setup_base(directed=True))
    direct_effects(result)
    return result


class DirectedCombatTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_contact_hold_keeps_both_poses_still(self):
        shot = fixture()
        self.assertEqual(shot["contact"]["frame"], 49)
        self.assertTrue(shot["contact"]["verified_intersection"])
        poses = []
        for frame in (49, 50, 51):
            bpy.context.scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            poses.append(
                tuple(
                    v
                    for key in ("caster", "defender")
                    for b in shot[key]["rig"].evaluated_get(graph).pose.bones
                    for v in matrix_values(b.matrix)
                )
            )
        for actual in poses[1:]:
            self.assertLess(max(abs(a - b) for a, b in zip(poses[0], actual)), 1e-5)

    def test_preparation_stays_grounded_and_recovers(self):
        minima = []
        recovery = []
        for directed in (False, True):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            shot = setup_base(directed=directed)
            body = [
                o
                for o in shot["caster"]["rig"].children
                if o.type == "MESH" and o.parent_type != "BONE"
            ]
            lowest = float("inf")
            for frame in range(1, 76):
                bpy.context.scene.frame_set(frame)
                graph = bpy.context.evaluated_depsgraph_get()
                lowest = min(
                    lowest,
                    *(
                        min((o.matrix_world @ v.co).z for v in o.evaluated_get(graph).data.vertices)
                        for o in body
                    ),
                )
            minima.append(lowest)
            bpy.context.scene.frame_set(80)
            recovery.append(
                matrix_values(
                    shot["caster"]["weapon"]
                    .evaluated_get(bpy.context.evaluated_depsgraph_get())
                    .matrix_world
                )
            )
        self.assertGreaterEqual(minima[1], min(minima[0], 0) - 0.005)
        self.assertLess(max(abs(a - b) for a, b in zip(*recovery)), 1e-5)
        print("DIRECTED_GROUND_MINIMA", minima)

    def test_body_load_moves_hips_while_both_soles_stay_planted(self):
        shot = setup_base(directed=True)
        rig = shot["caster"]["rig"]
        constraints = [c for bone in rig.pose.bones for c in bone.constraints]
        for frame in (12, 28, 32, 39, 43, 46):
            states = []
            for muted in (True, False):
                for constraint in constraints:
                    constraint.mute = muted
                bpy.context.scene.frame_set(frame)
                bpy.context.view_layer.update()
                evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
                states.append(
                    {
                        name: rig.matrix_world @ evaluated.pose.bones[name].matrix
                        for name in ("hips", "foot.l", "foot.r")
                    }
                )
            for name in ("foot.l", "foot.r"):
                self.assertLess(
                    (states[0][name].translation - states[1][name].translation).length,
                    0.001,
                    f"The planted foot slid at {frame}",
                )
                self.assertLess(
                    states[0][name]
                    .to_quaternion()
                    .rotation_difference(states[1][name].to_quaternion())
                    .angle,
                    0.001,
                )
            if frame in (28, 32, 39):
                self.assertLess(
                    states[1]["hips"].translation.z, states[0]["hips"].translation.z - 0.04
                )

    def test_energy_reaches_contact_and_slash_contains_blade(self):
        shot = fixture()
        scene = bpy.context.scene
        scene.frame_set(49)
        graph = bpy.context.evaluated_depsgraph_get()
        center = shot["effects"][0].evaluated_get(graph).matrix_world.translation
        self.assertLess((center - Vector(shot["contact"]["hits"][0]["position"])).length, 1e-5)
        for frame in (47, 49, 50, 51):
            scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            blade = shot["caster"]["weapon"].evaluated_get(graph).matrix_world
            direction = (blade @ shot["tip_local"] - blade.translation).normalized()
            slash = shot["effects"][1].evaluated_get(graph).matrix_world
            normal = (slash.to_3x3() @ Vector((0, 0, 1))).normalized()
            self.assertLess(abs(normal.dot(direction)), 1e-5)

    def test_complete_charge_keeps_node_animation_and_artist_edit(self):
        shot = fixture()
        bpy.context.scene.frame_set(32)
        clone = core.duplicate(bpy.context, shot["effects"][0])
        binding.unbind(bpy.context, clone)
        member = next(o for o in composition.members(clone) if o["vfx_module"] == "shader.shield")
        tree = member.children[0].modifiers[0].node_group
        tree.nodes.new("NodeReroute").name = "Artist retained"
        path = ROOT / "work/directed-charge.blend"
        path.parent.mkdir(exist_ok=True)
        assets.write(path, clone)
        loaded = assets.load(bpy.context, path)
        member = next(o for o in composition.members(loaded) if o["vfx_module"] == "shader.shield")
        tree = member.children[0].modifiers[0].node_group
        self.assertIn("Artist retained", tree.nodes)
        for frame, expected in ((32, 2.65), (49, 0.9), (32, 2.65)):
            bpy.context.scene.frame_set(frame)
            self.assertAlmostEqual(
                tree.nodes["Nucleus Stored Size"].outputs[0].default_value, expected, places=5
            )


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(DirectedCombatTests)
    )
    if not result.wasSuccessful():
        raise RuntimeError("Directed combat behavior failed")
    print("DIRECTED_COMBAT_BEHAVIOR_OK")
