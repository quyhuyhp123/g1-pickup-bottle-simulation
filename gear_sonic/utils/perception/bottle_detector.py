"""Bottle recognition from RGB; 3-D comes from measured depth and camera calibration.

No object name, body ID, object pose, or robot action is an input to this module.
The reported 3-D point is a visible surface near the detected box centre.
"""

import time

import numpy as np


def pixel_depth_to_world(pixel, depth_m, calibration):
    """Unproject top-left image coordinates into MuJoCo's world frame."""
    fx, fy = float(calibration["fx"]), float(calibration["fy"])
    cx, cy = float(calibration["cx"]), float(calibration["cy"])
    rotation = np.asarray(calibration["rotation_world_from_camera"], dtype=float).reshape(3, 3)
    position = np.asarray(calibration["position_world_m"], dtype=float)
    if not np.isfinite([*pixel, depth_m, fx, fy, cx, cy, *position, *rotation.ravel()]).all():
        raise ValueError("Invalid camera/depth values")
    if depth_m <= 0 or fx <= 0 or fy <= 0:
        raise ValueError("Depth and focal lengths must be positive")
    # MuJoCo cameras face -Z, with +X to the right and +Y upwards.
    camera_point = np.array([(pixel[0] - cx) * depth_m / fx,
                             -(pixel[1] - cy) * depth_m / fy, -depth_m])
    return camera_point, rotation @ camera_point + position


def estimate_surface_point(box, depth, calibration):
    if depth.ndim != 2:
        raise ValueError("Depth must be a 2-D image")
    height, width = depth.shape
    x1, y1, x2, y2 = np.asarray(box, dtype=float)
    if not np.isfinite([x1, y1, x2, y2]).all() or x2 <= x1 or y2 <= y1:
        raise ValueError("Invalid bounding box")
    u, v = (x1 + x2) / 2, (y1 + y2) / 2
    if not 0 <= u < width or not 0 <= v < height:
        raise ValueError("Detection is outside the depth image")
    radius = max(1, min(4, int(min(x2 - x1, y2 - y1) * .08)))
    x, y = int(u), int(v)
    patch = depth[max(0, y - radius):min(height, y + radius + 1),
                  max(0, x - radius):min(width, x + radius + 1)]
    valid = patch[np.isfinite(patch) & (patch > 0) & (patch < 5)]
    if not valid.size:
        raise ValueError("No valid depth inside the detected bottle box")
    depth_m = float(np.median(valid))
    pixel = [u, v]
    camera_point, world_point = pixel_depth_to_world(pixel, depth_m, calibration)
    return {"pixel_uv": pixel, "depth_m": depth_m,
            "camera_point_m": camera_point.tolist(), "world_point_m": world_point.tolist(),
            "point_kind": "visible_surface_near_box_center"}


class BottleDetector:
    def __init__(self, model_path, confidence=.25):
        from ultralytics import YOLO
        self.model = YOLO(str(model_path))
        self.confidence = confidence
        self.bottle_class = next(k for k, v in self.model.names.items() if v == "bottle")

    def detect(self, rgb, depth=None, calibration=None):
        # Ultralytics treats ndarray inputs as BGR; simulator messages are RGB.
        result = self.model.predict(rgb[:, :, ::-1].copy(), device="cpu", imgsz=640,
                                    conf=self.confidence, classes=[self.bottle_class], verbose=False)[0]
        output = {"status": "not_detected", "source": "YOLO11 RGB + rendered depth",
                  "model": "yolo11n", "world_point_m": None}
        if len(result.boxes) == 0:
            return output
        best = int(result.boxes.conf.argmax())
        box = result.boxes.xyxy[best].cpu().numpy().tolist()
        output.update(status="detected", confidence=float(result.boxes.conf[best]), bbox_xyxy=box)
        if depth is None or calibration is None:
            output.update(status="detected_no_depth", detail="No depth/calibration available")
            return output
        try:
            output.update(estimate_surface_point(box, depth, calibration))
            output['camera_position_world_m'] = list(calibration['position_world_m'])
        except ValueError as error:
            output.update(status="detected_no_depth", detail=str(error))
        return output


def current_detection(result, scene_changed_at=0., max_age=2.):
    """Never display stale/pre-reset positions as current model detections."""
    if not result:
        return {"status": "waiting", "world_point_m": None}
    captured = result.get("capture_monotonic", 0.)
    if captured < scene_changed_at:
        return {"status": "waiting_after_scene_change", "world_point_m": None}
    if time.monotonic() - captured > max_age:
        return {"status": "stale", "world_point_m": None}
    return result
