"""Verify depth geometry and suppression of stale/missing detections."""

import time
import unittest

import numpy as np

from gear_sonic.utils.perception.bottle_detector import (
    current_detection, estimate_surface_point, pixel_depth_to_world,
)


class BottleDetectionGeometryTest(unittest.TestCase):
    def setUp(self):
        self.calibration = {"fx": 100., "fy": 100., "cx": 50., "cy": 50.,
            "position_world_m": [1., 2., 3.],
            "rotation_world_from_camera": np.eye(3).tolist()}

    def test_camera_axes_and_world_transform(self):
        camera, world = pixel_depth_to_world([60., 40.], 2., self.calibration)
        np.testing.assert_allclose(camera, [.2, .2, -2.])
        np.testing.assert_allclose(world, [1.2, 2.2, 1.])
        self.calibration["rotation_world_from_camera"] = [[0, 0, -1], [0, 1, 0], [1, 0, 0]]
        _, world = pixel_depth_to_world([50., 50.], 2., self.calibration)
        np.testing.assert_allclose(world, [3., 2., 3.])

    def test_depth_outlier_does_not_move_detected_point(self):
        depth = np.full((100, 100), 2., dtype=np.float32)
        depth[50, 50] = np.nan
        depth[50, 51] = 4.5
        result = estimate_surface_point([40, 40, 60, 60], depth, self.calibration)
        np.testing.assert_allclose(result["world_point_m"], [1, 2, 1])
        self.assertEqual(result["point_kind"], "visible_surface_near_box_center")
        with self.assertRaises(ValueError):
            estimate_surface_point([40, 40, 60, 60], depth * 0, self.calibration)

    def test_reset_and_staleness_clear_xyz(self):
        now = time.monotonic()
        result = {"status": "detected", "capture_monotonic": now, "world_point_m": [1, 2, 3]}
        self.assertEqual(current_detection(result)["world_point_m"], [1, 2, 3])
        self.assertIsNone(current_detection(result, scene_changed_at=now + .1)["world_point_m"])
        result["capture_monotonic"] = now - 3
        self.assertIsNone(current_detection(result)["world_point_m"])
        self.assertIsNone(current_detection(None)["world_point_m"])

    def test_no_detection_never_has_previous_xyz(self):
        result = {"status": "not_detected", "capture_monotonic": time.monotonic(), "world_point_m": None}
        self.assertEqual(current_detection(result)["status"], "not_detected")
        self.assertIsNone(current_detection(result)["world_point_m"])


if __name__ == "__main__":
    unittest.main()
