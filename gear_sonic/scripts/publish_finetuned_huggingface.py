"""Prepare and optionally upload the Dex3 fine-tune and its 10 demonstrations.

Uses explicit file lists, hard links for large unchanged files, and private Hub
repositories by default. Does not alter the local checkpoint or recordings.
Run with ../Isaac-GR00T/.venv/bin/python; pass --upload to publish.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = 'cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-371ep-v10-finetune'
BACKBONE = 'nvidia/Cosmos-Reason2-2B'
TRAIN = ROOT / 'outputs/gr00t_g1_dex3_finetune_v1'


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    # A staged file may be a hard link. Never modify its source inode.
    if path.exists():
        path.unlink()
    path.write_text(value if isinstance(value, str) else json.dumps(value, indent=2) + '\n')


def link(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if os.path.samefile(source, target):
            return
        target.unlink()
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def tree(source, target):
    for path in sorted(source.rglob('*')):
        if path.is_file() and not any(p.startswith('.') for p in path.relative_to(source).parts):
            link(path, target / path.relative_to(source))


def portable_backbone(value):
    if isinstance(value, dict):
        return {k: BACKBONE if k == 'model_name' else portable_backbone(v) for k, v in value.items()}
    if isinstance(value, list):
        return [portable_backbone(v) for v in value]
    return value


RESTORE = '''"""Verify this release and cache its required VLM backbone before offline simulation."""
import hashlib
import json
from pathlib import Path
from huggingface_hub import snapshot_download

root = Path(__file__).resolve().parent
for entry in json.loads((root / 'manifest.json').read_text())['files']:
    digest = hashlib.sha256()
    with (root / entry['path']).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != entry['sha256']:
        raise ValueError('Checksum mismatch: ' + entry['path'])
print('All release checksums verified. Downloading/caching the required backbone...')
backbone = snapshot_download('nvidia/Cosmos-Reason2-2B')
print('Backbone cached at:', backbone)
print('Checkpoint uses the official Hub model ID; no local config edit is needed.')
'''


def model_card(model_id, dataset_id):
    return f'''---
language:
- en
- vi
license: other
license_name: nvidia-open-model-license-agreement
license_link: https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/
base_model: {BASE}
base_model_relation: finetune
datasets:
- {dataset_id}
tags:
- robotics
- gr00t
- unitree-g1
- dex3
- mujoco
- sonic
- experimental
---

# GR00T N1.7 G1 Dex3 bottle simulation fine-tune v1

Experimental merged checkpoint fine-tuned from CloudWalk v10/checkpoint-30000
on 10 locally generated MuJoCo demonstrations. **Closed-loop pickup and stable
holding have not passed. This is an experimental training result.**

## Control and training

RGB head camera + measured robot state + `grab the bottle` -> fine-tuned GR00T
-> 64-D motion token -> frozen SONIC decoder -> MuJoCo joint PD control.
GR00T also emits native Dex3 finger joint angles directly (7 per hand).
Runtime uses no YOLO, depth, IK, expert trajectory replay, or object XYZ input.
Training demonstrations were generated with RGB-D/IK assistance; labels were
refined offline through the frozen SONIC decoder. Label replay is distinct
from a learned policy succeeding in a closed-loop trial.

- Embodiment: `UNITREE_G1_SONIC`; measured state 46-D, action 78-D.
- Horizon: 40 actions at 50 Hz; source RGB recorded at 10 Hz, 640x480.
- Training: 8 train / 2 held-out validation episodes; 500 steps, accumulation 2,
  LR 1e-4, rank-8 action-head LoRA plus G1 projector slices; seed 42.
- VLM and SONIC frozen. Best adapter merged into the standard GR00T classes.
- Validation flow loss: 1.402045 -> 0.138523 (merged 0.138436).
- Open-loop validation: token RMSE 0.058964; right hand RMSE 0.162250 radians.
- Final 15s policy trial: pickup_success=false, peak bottle lift 0.001677m,
  opposed-contact holding time 0s. Full reports are under `reports/`.

## Required execution profile

`fixed_base_dex3_pd80_3_v1`: fixed pelvis, held legs and left arm; SONIC
controls waist pitch plus 7 right-arm joints. Arm PD 80/3 with bias gravity
compensation; held-joint PD 100/4; native hand PD 8/0.2; physics timestep .005s.
This checkpoint is not validated for free walking, Inspire hands, or hardware.
`simulation_profile.json` contains the mappings, home pose, scales and decoder hash.

## Download and run

Use the same prepared GR00T-WholeBodyControl + sibling Isaac-GR00T installation
as the project. The exact runtime source snapshot is included under `code/`.
Isaac-GR00T revision used: `51d4c89f72fda44cbf77285c6a8114b52676b8a1`.
Repository: https://github.com/quyhuyhp123/g1-pickup-bottle-simulation

From the GR00T-WholeBodyControl project root, using an authenticated Hugging
Face account (this repository is initially private):

```bash
../Isaac-GR00T/.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download('{model_id}',
    local_dir='outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best')
PY
../Isaac-GR00T/.venv/bin/python \\
  outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best/restore_release.py
```

The restore script checks SHA-256 and caches the upstream
`nvidia/Cosmos-Reason2-2B` backbone required by GR00T's constructor. You may need
to accept its access terms using your own Hugging Face account. This backbone
is a separate dependency; it is not duplicated in this repository.

For a checkout missing the new runtime, copy the supplied source files:

```bash
cp -a outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best/code/gear_sonic/. gear_sonic/
.venv_sim/bin/python gear_sonic/scripts/run_finetuned_sim.py \\
  --model-path outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best \\
  --prompt "grab the bottle"
```

The simulator needs MuJoCo 3.14, numpy, scipy, OpenCV, ONNX Runtime, glfw,
tkinter, pyzmq, msgpack and msgpack-numpy in `.venv_sim`. The project must have
`gear_sonic_deploy/policy/release/model_decoder.onnx`; SHA-256 is validated
against the execution profile. Obtain SONIC through the upstream project's
model installation procedure; SONIC weights are not included here.

With the updated launcher you can also run:

```bash
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \\
  --sim --sim-finetuned-policy --no-data-exporter --prompt "grab the bottle"
```

Start/F6 starts inference; Reset/F5 restores the robot, bottle and histories.
Physics waits for each predicted chunk when inference is slower than 50 Hz.
Only bottle pickup was trained. There is no learned place/lower skill yet.

## Files and provenance

- Two safetensors shards: merged fine-tuned model, not only an adapter.
- `config.json`, processor, statistics, embodiment mapping.
- Static scene + referenced mesh assets, with relative paths for portability.
- `reports/`: training, open-loop evaluation, actual closed-loop trial.
- `code/`: exact local runtime/training/evaluation source snapshot.
- `manifest.json`: file sizes and SHA-256 checksums.
- [Demonstrations and processed dataset](https://huggingface.co/datasets/{dataset_id}).

Weights derive from [CloudWalk v10](https://huggingface.co/{BASE}) and NVIDIA
GR00T N1.7. Their upstream model-license terms continue to apply. `LICENSE`
contains the upstream project's source-code/model-weight license notice.
Mesh assets originate from the project's Unitree G1 model and retain their
upstream terms. No new blanket license over third-party assets is asserted.
'''


def dataset_card(model_id, dataset_id):
    return f'''---
language:
- en
- vi
tags:
- robotics
- unitree-g1
- dex3
- mujoco
- imitation-learning
configs:
- config_name: refined
  data_files:
  - split: train
    path: refined/train/data/**/*.parquet
  - split: validation
    path: refined/validation/data/**/*.parquet
---

# G1 Dex3 bottle MuJoCo demonstrations: 10 episodes, v1

Ten simulated bottle-pickup demonstrations collected with RGB-D/IK assistance.
This repository contains the original recordings and the exact processed
dataset used for [the experimental fine-tune](https://huggingface.co/{model_id}).
It contains no real-robot data. Successful demonstration/token replay does
not imply the learned policy can grasp successfully; model v1 has not passed
closed-loop stable bottle pickup.

## Layout

- `raw/episode_*.tar.gz`: one archive per original episode, containing
  `meta.json`, `initial_state.npz`, `model.xml`, `states_*.npz`, `rgb/`,
  original `review.mp4` when present, and raw replay reports. Older experimental
  `sonic_candidate/` diagnostics are excluded from these archives.
- `previews/episode_*.mp4`: full camera video for each of the ten episodes;
  missing original review videos were encoded from the unchanged RGB PNGs.
- `raw/episodes.json`: all 10 names, counts, train/validation mapping,
  archive checksums and raw-replay status.
- `refined/train`, `refined/validation`: LeRobot v2.1-style parquet, MP4,
  and metadata; **8 train / 2 validation**, **4972 / 1188 rows**, at 50 Hz.
- `provenance/`: original export and replay reports, source selection,
  offline token refinement reports and refined tokens.
- `code/`: recording, inspection, replay, processing and training scripts.
- `manifest.json`: SHA-256 of all packaged files.

## Data semantics

Raw recordings: physics .005s (200 Hz), head-camera RGB 10 Hz at 640x480.
State chunks include pre-step qpos/qvel, clipped actuator `ctrl` commands,
applied forces, timestamps and assisted targets. `ctrl` contains actuator
commands/torques, not 43 target joint angles and not SONIC tokens. Raw episodes
remain in their original format; metadata may still say `unreviewed` or
`training_ready=false`. Separate replay/processing reports provide validation.
Depth was used by the collection controller but is not stored as depth images.

Processed state: 46-D measured joint radians + base-frame gravity. Action:
64-D offline refined SONIC token + 7 left + 7 right native Dex3 joint radians
(78 total). 40-step horizons. Each row uses the latest past RGB frame;
10 Hz source RGB is reused for 50 Hz rows, maximum recorded age .08s.
Finger state and motor-action orders differ; use `meta/modality.json` and
named features, not positional assumptions. Training normalization uses only
the training split. The two held-out episodes are 225724_55c76035 and
225821_54d8274d (full names in `raw/episodes.json`).

Tokens were fitted offline through frozen SONIC to expert arm targets. Saved
token replay passed 10/10 under **fixed_base_dex3_pd80_3_v1** only: fixed
pelvis, held legs/left arm, arm PD80/3, native Dex3 fingers. Generic reports
retain `sonic_validated=false` / `training_ready=false`; the separate
`training_ready_for_fixed_base_profile` flag has this restricted meaning.

## Download, extract and train

```bash
# From your prepared GR00T-WholeBodyControl project root:
../Isaac-GR00T/.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download('{dataset_id}', repo_type='dataset',
    local_dir='outputs/hf_g1_dex3_dataset_v1')
PY
mkdir -p outputs/ik_demonstrations
for archive in outputs/hf_g1_dex3_dataset_v1/raw/episode_*.tar.gz; do
  tar -xzf "$archive" -C outputs/ik_demonstrations
done
```

Do not overwrite modified local episodes. Archives preserve original files
byte-for-byte; their MJCF meshdir and some provenance reports reference the
collection machine. To replay on another machine, keep the original model XML
as provenance and change the extracted working copy's `<compiler meshdir>`
to your project's `gear_sonic/data/robot_model/model_data/g1/meshes` directory.
This path adjustment does not change the raw states or camera images.
Source-hash reports describe the original, unchanged data before that edit.

The processed dataset is already directly readable with the project's
LeRobot episode loader; it does not require raw archive extraction to train:

```bash
cp -a outputs/hf_g1_dex3_dataset_v1/code/gear_sonic/. gear_sonic/
PYTHONPATH=.:../Isaac-GR00T ../Isaac-GR00T/.venv/bin/python \\
  gear_sonic/scripts/finetune_gr00t_g1.py \\
  --dataset outputs/hf_g1_dex3_dataset_v1/refined \\
  --checkpoint checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000 \\
  --output outputs/gr00t_g1_dex3_new_run --steps 500
```

Install the same Isaac-GR00T training dependencies, download CloudWalk v10 and
its required backbone first. Use a new output directory for a new training run.
Ten episodes support an initial pipeline experiment; they do not establish
generalization to other objects, broad bottle positions, walking or hardware.
These data are generated by the local project; any included robot scene/code
retains its upstream license terms. See `LICENSE_UPSTREAM`.
'''


def manifest(folder):
    files = []
    for p in sorted(folder.rglob('*')):
        relative = p.relative_to(folder)
        if p.is_file() and p.name != 'manifest.json' and '.cache' not in relative.parts:
            files.append(dict(path=str(relative), size=p.stat().st_size, sha256=sha256(p)))
    write(folder / 'manifest.json', dict(files=files, total_bytes=sum(f['size'] for f in files)))
    return files


def prepare(args):
    release = Path(args.output).resolve()
    model, dataset = release / 'model', release / 'dataset'
    checkpoint = TRAIN / 'checkpoint-best'
    model_id, dataset_id = args.model_repo, args.dataset_repo
    print('Preparing portable model (large weights use hard links)...', flush=True)
    for source in sorted(checkpoint.iterdir()):
        if source.is_file():
            if source.name in ('config.json', 'processor_config.json'):
                write(model / source.name, portable_backbone(json.loads(source.read_text())))
            elif source.name == 'simulation_scene.xml':
                scene = ET.parse(source)
                scene.getroot().find('compiler').set('meshdir', 'simulation_assets/meshes')
                write(model / source.name, ET.tostring(scene.getroot(), encoding='unicode') + '\n')
            else:
                link(source, model / source.name)
    scene = ET.parse(checkpoint / 'simulation_scene.xml')
    meshdir = Path(scene.getroot().find('compiler').get('meshdir'))
    for mesh in scene.getroot().findall('./asset/mesh'):
        name = mesh.get('file')
        link(meshdir / name, model / 'simulation_assets/meshes' / name)
    for name in ('training_report.json', 'evaluation/evaluation_report.json'):
        link(TRAIN / name, model / 'reports' / Path(name).name)
    link(ROOT / 'outputs/finetuned_policy_sim/integration_final/run_report.json', model / 'reports/closed_loop_run_report.json')
    link(ROOT / 'checkpoints/cloudwalk_g1_bottle_v10/source.json', model / 'reports/base_checkpoint_source.json')
    link(ROOT / 'LICENSE', model / 'LICENSE')
    write(model / 'README.md', model_card(model_id, dataset_id))
    write(model / 'restore_release.py', RESTORE)
    model_code = ['gear_sonic/scripts/run_finetuned_sim.py', 'gear_sonic/scripts/launch_inference.py',
                  'gear_sonic/scripts/finetune_gr00t_g1.py', 'gear_sonic/scripts/evaluate_finetuned_g1.py',
                  'gear_sonic/utils/mujoco_sim/object_reset.py']
    dataset_code = model_code + ['gear_sonic/scripts/'+name+'.py' for name in (
        'inspect_sim_episode', 'replay_sim_episode', 'clean_sim_demonstrations',
        'encode_sim_episode', 'rollout_sonic_episode', 'refine_sonic_episode',
        'export_gr00t_candidate_dataset', 'validate_gr00t_candidate_dataset')]
    # Recorder source is a utility, not a standalone script.
    dataset_code += ['gear_sonic/utils/mujoco_sim/episode_recorder.py']
    for p in model_code:
        link(ROOT / p, model / 'code' / p)
    for p in dataset_code:
        link(ROOT / p, dataset / 'code' / p)
    tree(ROOT / 'outputs/gr00t_dex3_refined_v1', dataset / 'refined')
    tree(ROOT / 'outputs/sonic_rollout_fix/all_episodes', dataset / 'provenance/sonic_refinement')
    clean = ROOT / 'outputs/ik_clean_pickup_v1'
    for p in sorted(clean.glob('*.json')):
        link(p, dataset / 'provenance/cleaning' / p.name)
    link(ROOT / 'LICENSE', dataset / 'LICENSE_UPSTREAM')
    write(dataset / 'README.md', dataset_card(model_id, dataset_id))
    mapping = {e['source']: e for e in json.loads((dataset/'refined/export_report.json').read_text())['episodes']}
    episodes = sorted((ROOT/'outputs/ik_demonstrations').glob('episode_*'))
    if len(episodes) != 10 or len(mapping) != 10:
        raise ValueError('Expected exactly the ten recorded/training episodes')
    index = []
    for ep in episodes:
        meta = json.loads((ep / 'meta.json').read_text())
        replay = json.loads((ep / 'replay_report.json').read_text())
        if meta['status'] != 'complete' or not replay.get('trajectory_match'):
            raise ValueError('Episode/replay incomplete: ' + ep.name)
        archive = dataset / 'raw' / (ep.name + '.tar.gz')
        archive.parent.mkdir(parents=True, exist_ok=True)
        sources = [p for p in sorted(ep.rglob('*')) if p.is_file() and
                   'sonic_candidate' not in p.relative_to(ep).parts and
                   not any(v.startswith('.') for v in p.relative_to(ep).parts)]
        print('Archiving ' + ep.name, flush=True)
        temporary = archive.with_suffix('.tmp')
        with tarfile.open(temporary, 'w:gz', compresslevel=3) as tar:
            for p in sources:
                tar.add(p, arcname=str(Path(ep.name) / p.relative_to(ep)), recursive=False)
        temporary.replace(archive)
        preview = dataset / 'previews' / (ep.name + '.mp4')
        if (ep / 'review.mp4').exists():
            link(ep / 'review.mp4', preview)
        else:
            import cv2
            preview.parent.mkdir(parents=True, exist_ok=True)
            writer = cv2.VideoWriter(str(preview), cv2.VideoWriter_fourcc(*'mp4v'),
                                     meta['fps_requested'], tuple(meta['image_size']))
            if not writer.isOpened():
                raise RuntimeError('Cannot encode episode preview: ' + ep.name)
            try:
                for i in range(meta['frames']):
                    image = cv2.imread(str(ep / 'rgb' / f'{i:06d}.png'))
                    if image is None or list(image.shape[1::-1]) != meta['image_size']:
                        raise ValueError('Missing/invalid RGB image: '+ep.name+f'/{i:06d}.png')
                    writer.write(image)
            finally:
                writer.release()
        index.append(dict(episode=ep.name, samples=meta['samples'],
                          split=mapping[ep.name]['split'], processed_rows=mapping[ep.name]['frames'],
                          raw_replay_trajectory_match=replay['trajectory_match'],
                          archive=str(archive.relative_to(dataset)), archive_sha256=sha256(archive),
                          frames=meta['frames'], preview=str(preview.relative_to(dataset)), files=len(sources)))
    write(dataset/'raw/episodes.json', dict(episode_count=10, episodes=index))
    print('Computing SHA-256 manifests...', flush=True)
    model_files, dataset_files = manifest(model), manifest(dataset)
    report = dict(status='prepared', model_repo=model_id, dataset_repo=dataset_id, private=True,
                  model_files=len(model_files), model_bytes=sum(x['size'] for x in model_files),
                  dataset_files=len(dataset_files), dataset_bytes=sum(x['size'] for x in dataset_files),
                  episode_count=10, source_checkpoint_unchanged=True)
    write(release/'release_report.json', report)
    print(json.dumps(report, indent=2), flush=True)
    return release, report


def upload(args, release, report):
    from huggingface_hub import HfApi
    api = HfApi()
    username = api.whoami()['name']
    for rid in (args.model_repo, args.dataset_repo):
        if rid.split('/')[0] != username:
            raise ValueError('Only upload to the authenticated personal namespace')
    for kind, rid, folder in [('dataset', args.dataset_repo, release/'dataset'), ('model', args.model_repo, release/'model')]:
        # Never change an existing repo's visibility or delete its files.
        api.create_repo(repo_id=rid, repo_type=kind, private=True, exist_ok=True)
        print('Uploading ' + kind + ': ' + rid, flush=True)
        commit = api.upload_folder(repo_id=rid, repo_type=kind, folder_path=str(folder),
                                   commit_message='Upload experimental Dex3 bottle fine-tune and reproducible artifacts',
                                   ignore_patterns=['.cache/**', '*.tmp'])
        local = json.loads((folder/'manifest.json').read_text())['files']
        remote = {f.rfilename: f for f in api.repo_info(rid, repo_type=kind, revision=commit.oid, files_metadata=True).siblings}
        for f in local + [dict(path='manifest.json', size=(folder/'manifest.json').stat().st_size)]:
            entry = remote.get(f['path'])
            if entry is None or entry.size != f['size']:
                raise ValueError('Remote file missing/size mismatch: '+f['path'])
            lfs_sha = getattr(entry.lfs, 'sha256', None) if entry.lfs else None
            if lfs_sha and f.get('sha256') and lfs_sha != f['sha256']:
                raise ValueError('Remote LFS checksum mismatch: '+f['path'])
        report[kind] = dict(repo_id=rid, commit=commit.oid, url=str(commit.repo_url),
                            verified_files=len(local)+1, private=api.repo_info(rid, repo_type=kind).private)
        write(release/'release_report.json', report)
        print('Verified ' + kind + ' commit: ' + commit.oid, flush=True)
    report['status'] = 'uploaded_and_verified'
    write(release/'release_report.json', report)
    print(json.dumps(report, indent=2), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-repo', default='quyhuyhp123/gr00t-n17-g1-dex3-bottle-sim-v1')
    p.add_argument('--dataset-repo', default='quyhuyhp123/g1-dex3-bottle-mujoco-10episodes-v1')
    p.add_argument('--output', default=str(ROOT/'outputs/huggingface_release_v1'))
    p.add_argument('--upload', action='store_true')
    p.add_argument('--resume', action='store_true', help='Reuse prepared files after an interrupted upload')
    args = p.parse_args()
    if args.resume:
        release = Path(args.output).resolve()
        report = json.loads((release/'release_report.json').read_text())
        if report['model_repo'] != args.model_repo or report['dataset_repo'] != args.dataset_repo:
            raise ValueError('Prepared release repository IDs differ')
    else:
        release, report = prepare(args)
    if args.upload:
        upload(args, release, report)


if __name__ == '__main__':
    main()
