"""Submit native viewer overlays without waiting on the physics thread."""

import base64
import queue
import time
from threading import Event, Thread

import mujoco
import numpy as np


def draw_detection(frame, detection, now):
    """Overlay a recent measurement, never claim it tracks the current frame."""
    import cv2
    age = now - detection.get('capture_monotonic', 0.)
    shape = detection.get('image_shape')
    box = detection.get('bbox_xyxy')
    if detection.get('status') != 'detected' or not 0 <= age <= .75 or shape is None or box is None:
        cv2.putText(frame, 'YOLO: waiting / stale', (6, 36), cv2.FONT_HERSHEY_SIMPLEX,
                    .4, (255, 220, 80), 1)
        return
    height, width = shape
    scale = np.array([frame.shape[1]/width, frame.shape[0]/height]*2)
    x1, y1, x2, y2 = np.rint(np.asarray(box)*scale).astype(int)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
    cv2.putText(frame, f"YOLO bottle {detection.get('confidence', 0.):.2f} | {age*1000:.0f} ms",
                (6, 36), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 0), 1)


class ViewerOverlayWorker:
    def __init__(self, viewer):
        self.viewer = viewer
        self.camera_port = None
        self.pending = queue.Queue(maxsize=1)
        self.stopped = Event()
        self.thread = Thread(target=self._run, name="viewer-overlays", daemon=True)
        self.thread.start()

    def submit(self, texts, detection):
        try:
            self.pending.put_nowait((texts, detection))
        except queue.Full:
            try:
                self.pending.get_nowait()
            except queue.Empty:
                return
            try:
                self.pending.put_nowait((texts, detection))
            except queue.Full:
                pass

    def _run(self):
        import zmq
        context = zmq.Context()
        camera = None
        self._camera_socket = None
        try:
            self._run_loop(context, camera)
        finally:
            if self._camera_socket is not None:
                self._camera_socket.close(linger=0)
            context.destroy(linger=0)

    def _run_loop(self, context, camera):
        import cv2
        import msgpack
        import zmq
        from gear_sonic.utils.mujoco_sim.sensor_server import ImageUtils
        preview, capture = None, None
        texts, detection = [], {}
        while not self.stopped.is_set() and self.viewer.is_running():
            try:
                texts, detection = self.pending.get(timeout=.02)
            except queue.Empty:
                pass
            if camera is None and self.camera_port is not None:
                camera = context.socket(zmq.SUB)
                self._camera_socket = camera
                camera.setsockopt(zmq.CONFLATE, 1)
                camera.setsockopt_string(zmq.SUBSCRIBE, '')
                camera.connect(f'tcp://127.0.0.1:{self.camera_port}')
            # MuJoCo waits for its render thread to consume an overlay request.
            # Only this worker may wait; DDS/physics must continue at 200 Hz.
            self.viewer.set_texts(texts)
            encoded = detection.get("preview_png") if camera is None else None
            if camera is not None and camera.poll(0):
                message = msgpack.unpackb(camera.recv(), raw=False)
                capture = message.get('capture_monotonic', 0.)
                rgb = ImageUtils.decode_image(message['images']['ego_view'])
                preview = cv2.resize(rgb, (320, 240))
            if camera is not None and preview is not None:
                age = max(0., time.monotonic() - capture)
                frame = preview.copy()
                draw_detection(frame, detection, time.monotonic())
                cv2.putText(frame, f'Camera | age {age*1000:.0f} ms', (6, 18),
                            cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 255, 255), 1)
                if age > 1.:
                    cv2.putText(frame, 'STALE CAMERA', (6, 54), cv2.FONT_HERSHEY_SIMPLEX,
                                .55, (255, 80, 80), 2)
            else:
                frame = None
            if encoded and capture != detection.get("capture_monotonic"):
                import cv2
                decoded = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8), cv2.IMREAD_COLOR)
                preview = decoded[:, :, ::-1].copy() if decoded is not None else None
                capture = detection.get("capture_monotonic")
            if (encoded or camera is not None) and preview is not None:
                viewport = self.viewer.viewport
                # The native viewer can disappear after is_running() above,
                # for example while set_texts waits for the render thread.
                # Its handle then returns None instead of a viewport.
                if viewport is not None:
                    self.viewer.set_images([(mujoco.MjrRect(viewport.left + max(0, viewport.width - 330),
                        viewport.bottom + max(0, viewport.height - 250), 320, 240), frame if frame is not None else preview)])
            else:
                self.viewer.clear_images()
            self.stopped.wait(.01)

    def close(self):
        self.stopped.set()
        self.thread.join(timeout=1.)
