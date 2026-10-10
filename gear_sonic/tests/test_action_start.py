"""Cold inference must not skip the approach while the robot holds its pose."""
import unittest

from gear_sonic.utils.inference.vla_utils import calculate_latency_compensated_index


class ActionStartTest(unittest.TestCase):
    def test_cold_start_preserves_approach(self):
        self.assertEqual(calculate_latency_compensated_index(1.86, 50, 40, False), 0)

    def test_replan_compensates_motion_already_executing(self):
        self.assertEqual(calculate_latency_compensated_index(.16, 50, 40, True), 8)

    def test_long_replan_stays_in_horizon(self):
        self.assertEqual(calculate_latency_compensated_index(1.86, 50, 40, True), 39)


if __name__ == "__main__":
    unittest.main()
