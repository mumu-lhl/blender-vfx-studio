"""The complete cast keeps the preparation, release and recovery separate."""

import hashlib
import json
import sys
import unittest
from array import array
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.spell_preview import setup  # noqa: E402


def snapshot(frame):
    scene = bpy.context.scene
    scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    result = {}
    for obj in scene.objects:
        if obj.get("vfx_role") != "layer":
            continue
        evaluated = obj.evaluated_get(graph)
        values = array("f", [c for v in evaluated.data.vertices for c in v.co])
        values.extend(c for row in evaluated.matrix_world for c in row)
        result[obj.name] = hashlib.sha256(values.tobytes()).hexdigest()
    return result


class SpellSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        setup()

    def test_preparation_release_and_clear(self):
        scene = bpy.context.scene
        magic = bpy.data.objects["Spell • Magic Circle"]
        fire = bpy.data.objects["Spell • Fire Release"]

        def visible(root, frame):
            scene.frame_set(frame)
            graph = bpy.context.evaluated_depsgraph_get()
            return any(
                len(obj.evaluated_get(graph).data.vertices)
                for obj in root.children_recursive
                if obj.get("vfx_role") == "layer"
            )

        self.assertTrue(visible(magic, 40))
        self.assertFalse(visible(fire, 51))
        self.assertTrue(visible(fire, 56))
        self.assertTrue(visible(fire, 64))
        self.assertFalse(visible(magic, 73))
        self.assertFalse(visible(fire, 104))
        self.assertFalse(visible(magic, 0))

    def test_jump_frames_and_recovery_pose(self):
        expected = snapshot(64)
        snapshot(108)
        snapshot(16)
        self.assertEqual(snapshot(64), expected)
        rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
        for frame in (96, 104, 108):
            bpy.context.scene.frame_set(frame)
            posed = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
            self.assertGreater(
                max(
                    abs(p.matrix[i][j] - p.bone.matrix_local[i][j])
                    for p in posed.pose.bones
                    for i in range(4)
                    for j in range(4)
                ),
                0.01,
                f"Character returned to bind pose at frame {frame}",
            )

    def test_recovery_does_not_restart_idle_phase(self):
        rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
        poses = []
        for frame in (94, 95, 96, 97, 98, 99):
            bpy.context.scene.frame_set(frame)
            posed = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
            poses.append([c for p in posed.pose.bones for row in p.matrix for c in row])
        changes = [max(abs(x - y) for x, y in zip(a, b)) for a, b in zip(poses, poses[1:])]
        self.assertLess(changes[2], 3 * max(changes[1], changes[3]))


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(SpellSceneTests)
    )
    if not result.wasSuccessful():
        raise RuntimeError("Spell sequence behavior failed")
    scene = bpy.context.scene
    scene["spell_expected_snapshots"] = json.dumps(
        {str(frame): snapshot(frame) for frame in (64, 16, 96, 40, 104, 108)}
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/spell-test.blend"))
    print("SPELL_SCENE_BEHAVIOR_OK")
