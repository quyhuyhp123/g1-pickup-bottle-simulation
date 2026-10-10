"""Integration check for non-blocking, current-state camera publishing."""
import socket
import time
import unittest
import zlib
from pathlib import Path

import msgpack
import mujoco
import numpy as np
import zmq

from gear_sonic.utils.mujoco_sim.async_camera import AsyncCameraProcess
from gear_sonic.utils.mujoco_sim.sensor_server import ImageMessageSchema
from gear_sonic.utils.perception.bottle_detector import pixel_depth_to_world


class AsyncCameraTest(unittest.TestCase):
    def test_snapshot_delivery_and_shutdown(self):
        root = Path(__file__).resolve().parents[2]
        scene = root / "gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml"
        model = mujoco.MjModel.from_xml_path(str(scene))
        data = mujoco.MjData(model)
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            port = reserve.getsockname()[1]
        camera = AsyncCameraProcess(scene, {
            "ego_view": {"height": 480, "width": 640, "mjcf_name": "head_camera"},
        }, port=port, publish_depth=True)
        context = zmq.Context()
        sub = context.socket(zmq.SUB)
        sub.setsockopt_string(zmq.SUBSCRIBE, "")
        sub.connect(f"tcp://127.0.0.1:{port}")
        try:
            camera.start_process()
            images = []
            address = model.joint("red_bottle_free_joint").qposadr[0]
            for frame, y in enumerate((-.11, .15), start=1):
                data.qpos[address + 1] = y
                data.time = float(frame)
                original_qpos = data.qpos.copy()
                state = {"body_q": [float(frame)] * 29, "base_quat": [1., 0., 0., 0.]}
                deadline = time.monotonic() + 10
                found = None
                while time.monotonic() < deadline:
                    camera.submit(data, robot_state=state)
                    if sub.poll(100):
                        message = msgpack.unpackb(sub.recv(), raw=False)
                        if message.get("simulation_time") == frame:
                            found = message
                            break
                self.assertIsNotNone(found, "Missing current snapshot")
                self.assertLess(time.time() - found["timestamps"]["ego_view"], 2)
                self.assertLess(time.monotonic() - found["capture_monotonic"], 2)
                self.assertEqual(found["robot_state"], state)
                sensor = found["depth_cameras"]["ego_view"]
                depth = np.frombuffer(zlib.decompress(sensor["depth_zlib"]), dtype="<f2").reshape(sensor["shape"])
                self.assertEqual(depth.shape, (480, 640))
                calibration = sensor["calibration"]
                # A known tabletop point verifies depth registration, camera
                # axes and world transform independently of detector accuracy.
                # Keep the sample beyond the robot's hands and away from both
                # tested bottle poses; nearer tabletop rays are occluded.
                table = np.array([.6, .30, .7])
                rotation = np.asarray(calibration["rotation_world_from_camera"])
                local = rotation.T @ (table - np.asarray(calibration["position_world_m"]))
                u = calibration["cx"] + calibration["fx"] * local[0] / -local[2]
                v = calibration["cy"] - calibration["fy"] * local[1] / -local[2]
                self.assertTrue(0 <= u < 640 and 0 <= v < 480)
                _, world = pixel_depth_to_world([int(u) + .5, int(v) + .5],
                                               float(depth[int(v), int(u)]), calibration)
                self.assertAlmostEqual(world[2], .7, delta=.003)
                rgb = ImageMessageSchema.deserialize(found).images["ego_view"]
                self.assertEqual(rgb.shape, (480, 640, 3))
                self.assertEqual(rgb.dtype, np.uint8)
                images.append(rgb)
                np.testing.assert_array_equal(data.qpos, original_qpos)
            self.assertGreater(np.abs(images[0].astype(float) - images[1]).mean(), .5)
            start = time.monotonic()
            for _ in range(100):
                camera.submit(data)
            self.assertLess(time.monotonic() - start, .5, "Submitting blocks on rendering")
        finally:
            camera.stop()
            sub.close()
            context.term()
        self.assertFalse(camera.process.is_alive())


if __name__ == "__main__":
    unittest.main()
