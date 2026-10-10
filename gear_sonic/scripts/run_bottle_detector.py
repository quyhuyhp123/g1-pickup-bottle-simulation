"""Publish camera detections for display and optional simulation grip gating."""

import argparse
import base64
import json
import os
from pathlib import Path
import time
import zlib

import cv2
import msgpack
import numpy as np
import zmq

from gear_sonic.utils.mujoco_sim.sensor_server import ImageUtils
from gear_sonic.utils.perception.bottle_detector import BottleDetector


def main(args):
    os.environ.setdefault("YOLO_AUTOINSTALL", "False")
    os.environ.setdefault("YOLO_CONFIG_DIR", "/tmp/sonic_yolo_settings")
    Path(os.environ["YOLO_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
    import torch
    torch.set_num_threads(2)
    detector = BottleDetector(args.model_path, args.confidence)
    context = zmq.Context()
    camera = context.socket(zmq.SUB)
    camera.setsockopt_string(zmq.SUBSCRIBE, "")
    camera.setsockopt(zmq.CONFLATE, 1)
    camera.connect(f"tcp://127.0.0.1:{args.camera_port}")
    output = context.socket(zmq.PUB)
    output.setsockopt(zmq.LINGER, 0)
    output.bind(f"tcp://127.0.0.1:{args.output_port}")
    path = Path(args.diagnostic_path) if args.diagnostic_path else None
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[Bottle detector] YOLO11n CPU, separate perception, port {args.output_port}", flush=True)
    previous_capture = 0.
    try:
        while True:
            if not camera.poll(500):
                output.send_json({"status": "camera_disconnected", "world_point_m": None,
                                  "capture_monotonic": time.monotonic()})
                continue
            message = msgpack.unpackb(camera.recv(), raw=False)
            captured = message.get("capture_monotonic", 0.)
            if captured <= previous_capture or time.monotonic() - captured > 1.:
                continue
            previous_capture = captured
            rgb = ImageUtils.decode_image(message["images"]["ego_view"])
            sensor = message.get("depth_cameras", {}).get("ego_view")
            depth = None
            calibration = None
            if sensor:
                depth = np.frombuffer(zlib.decompress(sensor["depth_zlib"]), dtype="<f2").reshape(sensor["shape"])
                calibration = sensor["calibration"]
            start = time.monotonic()
            result = detector.detect(rgb, depth, calibration)
            result.update(image_shape=list(rgb.shape[:2]), capture_monotonic=captured, inference_ms=(time.monotonic() - start) * 1000,
                          simulation_time=message.get("simulation_time"))
            if path:
                temporary = path.with_suffix(".tmp")
                temporary.write_text(json.dumps(result, indent=2))
                temporary.replace(path)
            preview = rgb[:, :, ::-1].copy()
            if "bbox_xyxy" in result:
                x1, y1, x2, y2 = map(int, result["bbox_xyxy"])
                cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(preview, f"bottle {result['confidence']:.2f}", (x1, max(18, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 255, 0), 2)
            if "pixel_uv" in result:
                cv2.circle(preview, tuple(map(int, result["pixel_uv"])), 4, (0, 0, 255), -1)
            cv2.putText(preview, "YOLO11 - robot camera", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 2)
            preview = cv2.resize(preview, (320, 240))
            result["preview_png"] = base64.b64encode(cv2.imencode(".png", preview)[1]).decode()
            output.send_json(result, zmq.NOBLOCK)
            time.sleep(max(0., 1. / args.rate - (time.monotonic() - start)))
    except KeyboardInterrupt:
        pass
    finally:
        camera.close(linger=0)
        output.close(linger=0)
        context.term()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", default="models/detectors/yolo11n.pt")
    parser.add_argument("--camera-port", type=int, default=5555)
    parser.add_argument("--output-port", type=int, default=5582)
    parser.add_argument("--confidence", type=float, default=.25)
    parser.add_argument("--rate", type=float, default=2.)
    parser.add_argument("--diagnostic-path", default="outputs/bottle_detector/latest.json")
    main(parser.parse_args())
