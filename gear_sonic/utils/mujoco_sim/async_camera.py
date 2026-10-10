"""Render camera snapshots in a separate process without stalling physics."""

import multiprocessing as mp
import os
import queue
import time
import zlib

import numpy as np


class AsyncCameraProcess:
    def __init__(self, xml_path, camera_configs, port=5555, publish_depth=False):
        self.xml_path = str(xml_path)
        self.camera_configs = camera_configs
        self.port = port
        context = mp.get_context("spawn")
        self.states = context.Queue(maxsize=1)
        self.status = context.Queue(maxsize=1)
        self.stop_event = context.Event()
        self.process = context.Process(
            target=_render_worker,
            args=(self.xml_path, camera_configs, port, self.states, self.status, self.stop_event, publish_depth, os.getpid()),
            daemon=True,
        )
        self._stopped = False

    def start_process(self):
        # The spawned interpreter must choose its GL backend before importing
        # MuJoCo. The parent viewer keeps its existing GLFW context.
        previous = os.environ.get("MUJOCO_GL")
        os.environ["MUJOCO_GL"] = "egl"
        try:
            self.process.start()
        finally:
            if previous is None:
                os.environ.pop("MUJOCO_GL", None)
            else:
                os.environ["MUJOCO_GL"] = previous
        try:
            state, detail = self.status.get(timeout=30)
            if state != "ready":
                raise RuntimeError(detail)
        except Exception:
            self.stop()
            raise
        print(f"[Camera] Async renderer ready on port {self.port}", flush=True)

    def submit(self, data, robot_state=None):
        if not self.process.is_alive():
            raise RuntimeError("Camera renderer exited; refusing to continue with stale images")
        packet = (data.qpos.copy(), data.mocap_pos.copy(), data.mocap_quat.copy(),
                  float(data.time), time.time(), robot_state, time.monotonic())
        # Keep only the most recent snapshot. Never wait for the renderer.
        try:
            self.states.put_nowait(packet)
        except queue.Full:
            try:
                self.states.get_nowait()
            except queue.Empty:
                return
            try:
                self.states.put_nowait(packet)
            except queue.Full:
                pass

    def stop(self):
        if self._stopped:
            return
        self._stopped = True
        self.stop_event.set()
        if self.process.pid is not None:
            self.process.join(timeout=3)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=2)
        for channel in (self.states, self.status):
            channel.cancel_join_thread()
            channel.close()


def _render_worker(xml_path, camera_configs, port, states, status, stop_event, publish_depth=False, parent_pid=None):
    from gear_sonic.utils.mujoco_sim.process_lifecycle import follow_parent
    if parent_pid is not None and not follow_parent(parent_pid):
        return
    import mujoco
    from gear_sonic.utils.mujoco_sim.sensor_server import ImageMessageSchema, SensorServer

    renderers = {}
    server = None
    try:
        model = mujoco.MjModel.from_xml_path(xml_path)
        data = mujoco.MjData(model)
        for name, config in camera_configs.items():
            renderers[name] = mujoco.Renderer(model, height=config["height"], width=config["width"])
        server = SensorServer()
        server.start_server(port=port)
        status.put(("ready", ""))
        while not stop_event.is_set():
            if parent_pid is not None and os.getppid() != parent_pid:
                break
            try:
                qpos, mocap_pos, mocap_quat, sim_time, capture_time, robot_state, capture_monotonic = states.get(timeout=.1)
            except queue.Empty:
                continue
            data.qpos[:] = qpos
            data.mocap_pos[:] = mocap_pos
            data.mocap_quat[:] = mocap_quat
            data.time = sim_time
            mujoco.mj_forward(model, data)
            images = {}
            depth_cameras = {}
            for name, renderer in renderers.items():
                config = camera_configs[name]
                renderer.update_scene(data, camera=config.get("params", config.get("mjcf_name", name)))
                images[name] = renderer.render()
                if publish_depth and "mjcf_name" in config:
                    # RGB, depth and camera extrinsics share this same physics
                    # snapshot. No object pose/segmentation IDs are exported.
                    renderer.enable_depth_rendering()
                    try:
                        depth = renderer.render()
                    finally:
                        renderer.disable_depth_rendering()
                    camera_id = model.camera(config["mjcf_name"]).id
                    height, width = depth.shape
                    focal = height / (2 * np.tan(np.deg2rad(model.cam_fovy[camera_id]) / 2))
                    depth_cameras[name] = {
                        "depth_zlib": zlib.compress(depth.astype("<f2").tobytes(), level=1),
                        "shape": [height, width], "dtype": "<f2",
                        "calibration": {"fx": float(focal), "fy": float(focal),
                            "cx": width / 2., "cy": height / 2.,
                            "position_world_m": data.cam_xpos[camera_id].tolist(),
                            "rotation_world_from_camera": data.cam_xmat[camera_id].reshape(3, 3).tolist()},
                    }
            message = ImageMessageSchema(
                timestamps={name: capture_time for name in images}, images=images,
            ).serialize()
            message["simulation_time"] = sim_time
            message["capture_monotonic"] = capture_monotonic
            if depth_cameras:
                message["depth_cameras"] = depth_cameras
            if robot_state is not None:
                message["robot_state"] = robot_state
            server.send_message(message)
    except Exception as error:
        try:
            status.put_nowait(("error", repr(error)))
        except queue.Full:
            pass
        raise
    finally:
        for renderer in renderers.values():
            renderer.close()
        if server is not None:
            server.stop_server()
