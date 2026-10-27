#!/usr/bin/env bash
# Start the selected CloudWalk VLA checkpoint; does not start robot control.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHECKPOINT="${CLOUDWALK_CHECKPOINT:-$REPO_ROOT/checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000}"
SERVER_PYTHON="${CLOUDWALK_SERVER_PYTHON:-$REPO_ROOT/../Isaac-GR00T/.venv/bin/python}"
SERVER_SCRIPT="$REPO_ROOT/../Isaac-GR00T/gr00t/eval/run_gr00t_server.py"
if [[ ! -x "$SERVER_PYTHON" || ! -f "$SERVER_SCRIPT" ]]; then
    echo "Isaac-GR00T server environment not found. Set CLOUDWALK_SERVER_PYTHON."
    exit 1
fi
"$REPO_ROOT/.venv_inference/bin/python" "$SCRIPT_DIR/check_cloudwalk_checkpoint.py" "$CHECKPOINT"
echo "Starting CloudWalk checkpoint: $CHECKPOINT. Select the simulated hand in launch_inference.py."
echo "Learned-action simulation: launch_inference.py --sim --sim-policy-control (experimental Dex3 adapter)."
echo "Native Inspire remains a separate assisted profile; hardware deployment is not validated."
cd "$REPO_ROOT/../Isaac-GR00T"
# Version checks are unrelated to inference and can stall startup on WSL when
# the update endpoint is unreachable.
export NO_ALBUMENTATIONS_UPDATE=1
exec "$SERVER_PYTHON" "$SERVER_SCRIPT" --model-path "$CHECKPOINT" \
    --embodiment-tag UNITREE_G1_SONIC --device cuda:0 --host 127.0.0.1 --port 5550 "$@"
