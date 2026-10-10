"""Post-reset policy inputs must be fresh and paired with their camera state."""

import queue
import threading
import time
import unittest

import numpy as np

from gear_sonic.scripts.run_vla_inference import prepare_observation_from_sensors, _inference_worker_loop
from gear_sonic.data.robot_model.instantiation.g1 import instantiate_g1_robot_model


class ObservationFreshnessTest(unittest.TestCase):
    def test_reject_old_frame_before_touching_robot_state(self):
        class Camera:
            def read(self):
                return {"capture_monotonic": time.monotonic() - 2.}
        status = {}
        self.assertIsNone(prepare_observation_from_sensors(
            Camera(), None, None, "grab the bottle", minimum_capture_monotonic=0., sensor_status=status))
        self.assertFalse(status["input_ready"])
        self.assertIsNone(prepare_observation_from_sensors(
            Camera(), None, None, "grab the bottle", minimum_capture_monotonic=time.monotonic()))

    def test_fresh_frame_uses_its_state_snapshot(self):
        robot = instantiate_g1_robot_model(waist_location="lower_and_upper_body")
        boundary = time.monotonic() - .1
        class Camera:
            def read(self):
                return {"capture_monotonic": time.monotonic(),
                        "images": {"ego_view": np.zeros((480, 640, 3), dtype=np.uint8)},
                        "timestamps": {"ego_view": time.time()},
                        "robot_state": {"body_q": [.1] * 29, "left_hand_q": [0.] * 7,
                                        "right_hand_q": [0.] * 7, "base_quat": [1., 0., 0., 0.]}}
        class OldDDS:
            def get_msg(self):
                raise AssertionError("Must use the state paired with the new RGB frame")
        status = {}
        obs = prepare_observation_from_sensors(Camera(), OldDDS(), robot, "grab the bottle",
                                              minimum_capture_monotonic=boundary, sensor_status=status)
        self.assertTrue(status["input_ready"])
        np.testing.assert_allclose(obs["state"]["right_arm"], .1)
        np.testing.assert_array_equal(obs["state"]["projected_gravity"], [[[0., 0., -1.]]])
        self.assertEqual(obs["language"]["annotation.human.task_description"], [["grab the bottle"]])

    def test_inflight_result_keeps_pre_reset_request_boundary(self):
        requests, results = queue.Queue(), queue.Queue()
        stop, busy, entered, release = (threading.Event() for _ in range(4))
        def prepare():
            entered.set()
            release.wait(timeout=2)
            return {"observation": True}
        thread = threading.Thread(target=_inference_worker_loop,
            args=(requests, results, stop, busy, prepare, lambda obs: {"action": True}))
        requested_at = time.monotonic()
        requests.put(requested_at)
        thread.start()
        try:
            self.assertTrue(entered.wait(timeout=2))
            reset_boundary = time.monotonic()
            release.set()
            _, result_boundary = results.get(timeout=2)
            self.assertEqual(result_boundary, requested_at)
            self.assertLess(result_boundary, reset_boundary)
        finally:
            stop.set()
            release.set()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
