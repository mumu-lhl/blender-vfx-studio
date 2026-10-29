"""Dash poses and dust follow the animated character's actual ground contact."""

import hashlib
import json
import sys
import unittest
from array import array
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.dash_landing_preview import setup  # noqa: E402


def snapshot(frame):
    bpy.context.scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    result = {}
    for obj in bpy.context.scene.objects:
        if obj.get("vfx_role") == "layer":
            evaluated = obj.evaluated_get(graph)
            values = array("f", [c for v in evaluated.data.vertices for c in v.co])
            values.extend(c for row in evaluated.matrix_world for c in row)
            result[obj.name] = hashlib.sha256(values.tobytes()).hexdigest()
    return result


class LandingSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        cls.record = setup()

    def test_dust_waits_for_evaluated_foot_contact(self):
        hit = self.record["frame"]
        trace = {r["frame"]: r["lowest_foot_z"] for r in self.record["foot_trace"]}
        self.assertGreater(trace[hit - 1], 0.02)
        self.assertLessEqual(trace[hit], 0.02)
        self.assertGreater(trace[hit], -0.02)
        dust = bpy.data.objects["Dash Landing • Dust"]
        self.assertEqual(dust["start"], hit)
        bpy.context.scene.frame_set(hit - 1)
        graph = bpy.context.evaluated_depsgraph_get()
        self.assertFalse(
            any(
                len(o.evaluated_get(graph).data.vertices)
                for o in dust.children_recursive
                if o.get("vfx_role") == "layer"
            )
        )
        bpy.context.scene.frame_set(hit + 8)
        self.assertTrue(
            any(
                len(o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices)
                for o in dust.children_recursive
                if o.get("vfx_role") == "layer"
            )
        )

    def test_captured_poses_and_complete_recovery_seek(self):
        self.assertEqual(self.record["sample_frames"], [6, 15, 24])
        expected = snapshot(35)
        snapshot(84)
        snapshot(9)
        self.assertEqual(snapshot(35), expected)
        bpy.context.scene.frame_set(84)
        graph = bpy.context.evaluated_depsgraph_get()
        self.assertFalse(
            any(
                len(o.evaluated_get(graph).data.vertices)
                for o in bpy.context.scene.objects
                if o.get("vfx_role") == "layer"
            )
        )
        rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
        posed = rig.evaluated_get(graph)
        self.assertGreater(
            max(
                abs(p.matrix[i][j] - p.bone.matrix_local[i][j])
                for p in posed.pose.bones
                for i in range(4)
                for j in range(4)
            ),
            0.01,
        )


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(LandingSceneTests)
    )
    if not result.wasSuccessful():
        raise RuntimeError("Dash/landing scene behavior failed")
    scene = bpy.context.scene
    scene["dash_landing_expected"] = json.dumps(
        {str(f): snapshot(f) for f in (52, 18, 35, 44, 76, 84)}
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "work/dash-landing-test.blend"))
    print("DASH_LANDING_BEHAVIOR_OK")
