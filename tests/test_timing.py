import unittest
from math import floor

from blender_vfx_studio.timing import ACTIVE, PROGRESS, phase


class TimingTests(unittest.TestCase):
    def test_boundaries_and_driver_contract(self):
        for start, duration, speed in [(1, 24, 1), (-8, 10, 2), (3, 0, 0)]:
            for loop in (False, True):
                for frame in (-20, -8, 0, 1, 3, 7.5, 13, 25, 49, 100):
                    scope = dict(frame=frame, s=start, d=duration, v=speed, l=loop, floor=floor)
                    expected, active = phase(frame, start, duration, speed, loop)
                    self.assertAlmostEqual(eval(PROGRESS, scope), expected)
                    self.assertEqual(bool(eval(ACTIVE, scope)), active)
        self.assertEqual(phase(25), (1, False))
        self.assertEqual(phase(25, loop=True), (0, True))
        self.assertEqual(phase(0, loop=True)[1], False)
