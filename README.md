# G1 blue bottle simulation — code-only snapshot

Customized MuJoCo bottle pickup/place demo from NVIDIA GR00T-WholeBodyControl.
Upstream code commit: `b042411fae38ee4d1af9aac82a37a1f8d14d6dd0`.
Simulation source snapshot: `323211d` from the original workspace.
Original licensing/attribution files are preserved. No Git LFS/history/model binaries are shipped.

## GR00T v10 fine-tuning test branch

Branch: `test_finetune_Gr00Tv10`. This branch includes the demonstration
recorder, data cleaning/export, offline SONIC token refinement, action-head
LoRA fine-tuning, evaluation and native Dex3 policy simulation runtime.

- [Data collection, processing and experiment reports (Vietnamese)](docs/source/tutorials/huong_dan_chinh_sua/08_thu_du_lieu_rgbd_ik.md)
- [Download dataset, fine-tune v10 and test in simulation (Vietnamese)](docs/source/tutorials/huong_dan_chinh_sua/09_fine_tune_v10_tu_dataset_den_test_simulation.md)
- [Fine-tuned model v1 on Hugging Face](https://huggingface.co/quyhuyhp123/gr00t-n17-g1-dex3-bottle-sim-v1)
- [10 demonstrations and processed training dataset on Hugging Face](https://huggingface.co/datasets/quyhuyhp123/g1-dex3-bottle-mujoco-10episodes-v1)

The Hugging Face repositories are private; sign in with an authorized account.
Model weights, recorded episodes and virtual environments are downloaded or
created separately. The model runtime is RGB + state + instruction -> GR00T
-> SONIC -> MuJoCo, with native Dex3 hand commands. VLM and SONIC weights
remain frozen during the included action-head fine-tuning recipe.
**Experimental v1 has not achieved reliable closed-loop bottle pickup.**

After setting up the environments and downloading the checkpoint as described
in the guide, run from this repository's root:

```bash
.venv_sim/bin/python gear_sonic/scripts/run_finetuned_sim.py \
  --model-path outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best \
  --prompt "grab the bottle"
```

This command starts its own policy server and simulator. Start/F6 begins
inference; Reset/F5 restores the initial state. Section 16 of the guide also
shows separate server/client commands and video recording. The setup and
assisted pickup commands below describe the earlier RGB-D/IK demo.

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
