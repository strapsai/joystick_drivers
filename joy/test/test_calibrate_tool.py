"""Calibration only changes selected axes and rejects motion/incorrect axis choices."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'joy_calibrate', Path(__file__).parents[1] / 'scripts/joy_calibrate.py')
calibrate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calibrate)


class CalibrationTool(unittest.TestCase):
    def test_centers_only_selected_stick_axes(self):
        samples = [[0.1, -0.1, 1.0, 1.0, 0.8, 0.0, 0.02, -0.03]] * 100
        self.assertEqual(calibrate.estimate_centers(samples, [0, 1, 6, 7], .04, .25),
                         [0.1, -0.1, 0.0, 0.0, 0.0, 0.0, 0.02, -0.03])

    def test_rejects_motion_in_calibrated_axis(self):
        with self.assertRaises(ValueError):
            calibrate.estimate_centers([[0.0], [0.2]], [0], .04, .25)

    def test_rejects_axis_far_from_center(self):
        with self.assertRaises(ValueError):
            calibrate.estimate_centers([[1.0]] * 100, [0], .04, .25)

    def test_rejects_invalid_or_duplicate_axes(self):
        for axes in [[], [-1], [2], [0, 0]]:
            with self.assertRaises(ValueError):
                calibrate.estimate_centers([[0.0, 0.0]], axes, .04, .25)


if __name__ == '__main__':
    unittest.main()
