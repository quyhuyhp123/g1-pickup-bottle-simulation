#!/usr/bin/env bash
# Small display-only detector; preserve existing GR00T / Torch versions.
set -euo pipefail
DETECTOR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DETECTOR_ROOT"
test -x .venv_inference/bin/python
UV_CACHE_DIR=/tmp/sonic_detector_uv_cache uv pip install \
    --python .venv_inference/bin/python --no-deps \
    ultralytics==8.4.174 ultralytics-thop==2.2.2
mkdir -p models/detectors
if [[ ! -f models/detectors/yolo11n.pt ]]; then
    curl -fL --retry 2 \
        https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt \
        -o models/detectors/yolo11n.pt.tmp
    mv models/detectors/yolo11n.pt.tmp models/detectors/yolo11n.pt
fi
echo "Display-only detector ready: models/detectors/yolo11n.pt"
