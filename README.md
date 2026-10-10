# G1 blue bottle simulation — code-only snapshot

Customized MuJoCo bottle pickup/place demo from NVIDIA GR00T-WholeBodyControl.
Upstream code commit: `b042411fae38ee4d1af9aac82a37a1f8d14d6dd0`.
Simulation source snapshot: `323211d` from the original workspace.
Original licensing/attribution files are preserved. No Git LFS/history/model binaries are shipped.

## Setup

Clone this repository to `~/projects/g1-pickup-bottle-simulation` so relative paths
match the setup guide. Clone Isaac-GR00T beside it.

```bash
git clone https://github.com/quyhuyhp123/g1-pickup-bottle-simulation.git ~/projects/g1-pickup-bottle-simulation
cd ~/projects/g1-pickup-bottle-simulation
python3 install_scripts/download_runtime_assets.py
```

Read [the setup guide for this repository](docs/source/tutorials/RUN_FROM_PERSONAL_REPOSITORY.md)
for WSL, runtime assets, CUDA/TensorRT, Python environments, models and operation.
It includes the pinned Isaac-GR00T clone and BF16 patch; WBC code is already modified.

Download SONIC models with `download_from_hf.py`, GR00T v10 using the guide,
and YOLO using `install_scripts/install_bottle_detector.sh`.

```bash
bash gear_sonic/scripts/run_cloudwalk_policy_server.sh
# In another terminal:
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter --inspire-ftp-hands \
  --sim-assisted-pickup --sim-fixed-base --prompt "grab the bottle"
```

Start → pickup → destination X/Y → Lower → retract → Start again.
This is RGB-D/IK-assisted simulation with a fixed pelvis, not pure checkpoint-controlled
pickup or validated physical robot deployment. See [controls](docs/source/tutorials/simulation_controls.md).

[Original upstream README](UPSTREAM_README.md).
