"""Checks for the experimental Inspire-to-Dex3 grip adapter."""
import unittest
import numpy as np
from gear_sonic.utils.inference.inspire_adapter import inspire_grip_to_dex3


class InspireAdapterTests(unittest.TestCase):
    def test_grip_endpoints_and_interpolation(self):
        closed = np.array([0, -.7, -.7, 1, 1.5, 1, 1.5])
        opened = np.array([0, 0, 0, 0, 0, .9, 0])
        shut = np.array([1, 1, 1, 1, 1, 1, 0])
        result = inspire_grip_to_dex3(np.stack([opened, (opened + shut) / 2, shut]), closed)
        np.testing.assert_allclose(result, np.stack([closed * 0, closed / 2, closed]))

    def test_pad_and_thumb_rotation_do_not_close_fingers(self):
        closed = np.ones(7)
        np.testing.assert_array_equal(inspire_grip_to_dex3([0, 0, 0, 0, 0, 1, 1], closed), np.zeros(7))

    def test_reject_invalid_input(self):
        for hand in (np.zeros(6), np.full(7, np.nan), np.full(7, np.inf)):
            with self.assertRaises(ValueError):
                inspire_grip_to_dex3(hand, np.ones(7))


if __name__ == '__main__':
    unittest.main()
