"""Check the native renderer font contract and visible detector status."""

import base64
from types import SimpleNamespace
from threading import Event
import time
import unittest

import mujoco
import numpy as np

from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
from gear_sonic.utils.mujoco_sim.viewer_overlay import ViewerOverlayWorker


class ViewerOverlayTest(unittest.TestCase):
    def test_live_camera_updates_without_detector_results(self):
        import msgpack
        import zmq
        from gear_sonic.utils.mujoco_sim.sensor_server import ImageMessageSchema
        context = zmq.Context()
        publisher = context.socket(zmq.PUB)
        port = publisher.bind_to_random_port('tcp://127.0.0.1')
        displayed = Event()
        frames = []
        def show(images):
            frames.append(images[0][1].copy())
            displayed.set()
        viewer = SimpleNamespace(is_running=lambda: True, viewport=mujoco.MjrRect(0, 0, 800, 600),
            set_texts=lambda _: None, clear_images=lambda: None, set_images=show)
        worker = ViewerOverlayWorker(viewer)
        worker.camera_port = port
        try:
            for value in (40, 180):
                deadline = time.monotonic() + 2.
                while time.monotonic() < deadline:
                    packet = ImageMessageSchema(timestamps={'ego_view': time.time()},
                        images={'ego_view': np.full((240, 320, 3), value, dtype=np.uint8)}).serialize()
                    packet['capture_monotonic'] = time.monotonic()
                    publisher.send(msgpack.packb(packet))
                    displayed.wait(.05)
                    displayed.clear()
                    if frames and abs(float(frames[-1][150:, :, :].mean())-value) < 3:
                        break
                else:
                    self.fail('Live preview did not update independently of YOLO')
        finally:
            worker.close()
            publisher.close(linger=0)
            context.term()

    def test_detection_box_scales_and_expires(self):
        from gear_sonic.utils.mujoco_sim.viewer_overlay import draw_detection
        detection = {'status': 'detected', 'capture_monotonic': 10.,
            'image_shape': [480, 640], 'bbox_xyxy': [200, 200, 400, 400], 'confidence': .8}
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        draw_detection(frame, detection, 10.5)
        np.testing.assert_array_equal(frame[100, 100], [0, 255, 0])
        stale = np.zeros_like(frame)
        draw_detection(stale, detection, 10.8)
        self.assertFalse(stale[80:].any())

    def preview_detection(self):
        import cv2
        ok, encoded = cv2.imencode(".png", np.zeros((240, 320, 3), dtype=np.uint8))
        self.assertTrue(ok)
        return {"preview_png": base64.b64encode(encoded).decode(), "capture_monotonic": 1.}

    def test_preview_resumes_when_viewport_becomes_available(self):
        first, displayed = Event(), Event()
        viewer = SimpleNamespace(is_running=lambda: True, viewport=None,
            set_texts=lambda _: first.set(), clear_images=lambda: None,
            set_images=lambda _: displayed.set())
        worker = ViewerOverlayWorker(viewer)
        try:
            detection = self.preview_detection()
            worker.submit([], detection)
            self.assertTrue(first.wait(1.))
            self.assertFalse(displayed.wait(.2))
            self.assertTrue(worker.thread.is_alive())
            viewer.viewport = mujoco.MjrRect(0, 0, 800, 600)
            worker.submit([], detection)
            self.assertTrue(displayed.wait(1.))
        finally:
            worker.close()

    def test_viewer_can_close_during_overlay_submission(self):
        entered, displayed = Event(), Event()
        viewer = SimpleNamespace(running=True, viewport=mujoco.MjrRect(0, 0, 800, 600),
                                 clear_images=lambda: None, set_images=lambda _: displayed.set())
        viewer.is_running = lambda: viewer.running
        def close_while_setting_texts(_):
            viewer.viewport = None
            viewer.running = False
            entered.set()
        viewer.set_texts = close_while_setting_texts
        worker = ViewerOverlayWorker(viewer)
        try:
            worker.submit([], self.preview_detection())
            self.assertTrue(entered.wait(1.))
            worker.thread.join(timeout=1.)
            self.assertFalse(worker.thread.is_alive())
            self.assertFalse(displayed.is_set())
        finally:
            worker.close()

    def test_slow_native_overlay_never_blocks_physics_submissions(self):
        entered, release = Event(), Event()
        def slow_set_texts(texts):
            entered.set()
            release.wait(2.)
        viewer = SimpleNamespace(is_running=lambda: True, set_texts=slow_set_texts,
                                 clear_images=lambda: None)
        worker = ViewerOverlayWorker(viewer)
        try:
            worker.submit([], {})
            self.assertTrue(entered.wait(1.))
            start = time.monotonic()
            for _ in range(100):
                worker.submit([], {})
            self.assertLess(time.monotonic() - start, .1)
            self.assertEqual(worker.pending.qsize(), 1)
        finally:
            release.set()
            worker.close()

    def test_native_font_and_prominent_detector_coordinates(self):
        texts = []
        env = DefaultEnv.__new__(DefaultEnv)
        env.config = {}
        env.viewer = SimpleNamespace(set_texts=lambda value: texts.extend(value),
                                     clear_images=lambda: None, sync=lambda: None)
        env.coordinate_snapshot = lambda: {"bottle": [.43, -.11, .8],
                                           "right_wrist": [.2, -.2, .8], "right_grasp_center": [.43, -.156, .8]}
        env.ui_snapshot = {"detection": {"world_point_m": [.407, -.102, .872], "confidence": .85},
            "hand_alignment": {"grasp_center_world_m": [.43, -.156, .8], "y_surface_gap_m": .021, "x_error_m": .001},
            "grasp_threshold_m": .02, "grasp_x_tolerance_m": .005, "grasp_status": "Waiting for Y gap <= 2.0 cm"}
        env.elastic_band = None
        env.detection_preview = None
        env._viewer_overlay_worker = None
        env.update_viewer()
        # mjr_overlay indexes its font tables using mjtFont, NOT mjtFontScale.
        valid = {int(value) for value in mujoco.mjtFont.__members__.values()}
        self.assertTrue(all(int(font) in valid for font, *_ in texts))
        detector = next(row for row in texts if "DETECTED BOTTLE" in row[2])
        self.assertEqual(detector[0], mujoco.mjtFont.mjFONT_BIG)
        for coordinate in ("+0.407", "-0.102", "+0.872"):
            self.assertIn(coordinate, detector[2])
        grasp = next(row for row in texts if "GRASP CENTRE - X/Y" in row[2])
        self.assertEqual(grasp[1], mujoco.mjtGridPos.mjGRID_BOTTOMRIGHT)
        self.assertIn("Y gap 2.10 cm | target 2.0", grasp[2])
        self.assertIn("X error +0.10 cm | tol 0.5", grasp[2])
        world_labels = next(row[2] for row in texts if "WORLD XYZ" in row[2])
        self.assertIn("Right wrist origin", world_labels)
        self.assertLess(world_labels.index("Hand grasp centre"), world_labels.index("Right wrist origin"))
        texts.clear()
        env.ui_snapshot = {"detection": {"world_point_m": None, "status": "not_detected"}}
        env.update_viewer()
        detector = next(row for row in texts if "DETECTED BOTTLE" in row[2])
        self.assertIn("not_detected", detector[2])
        self.assertNotIn("+0.407", detector[2])


if __name__ == "__main__":
    unittest.main()
