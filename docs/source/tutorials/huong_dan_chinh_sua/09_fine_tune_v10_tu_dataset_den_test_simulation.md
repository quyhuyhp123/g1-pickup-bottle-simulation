# Bước 9 — Từ dataset đến fine-tune GR00T v10 và test trong MuJoCo

Tài liệu này hướng dẫn chạy lại quá trình fine-tune bằng **10 episode đã thu**,
sau đó thử checkpoint mới trong simulation. Các lệnh dựa trên script và artifact
đã có trong dự án, được đối chiếu ngày **28/10/2026**.

Tài liệu bắt đầu từ một máy đã cài môi trường của dự án. Nếu chưa có WSL,
repository và môi trường Python, làm theo
[WSL_UPSTREAM_V10_SETUP.md](../WSL_UPSTREAM_V10_SETUP.md) trước.
Chi tiết thu dữ liệu/clean/refine trước khi tạo dataset nằm ở
[bước 8](08_thu_du_lieu_rgbd_ik.md).

## 1. Hiểu đúng quá trình sẽ thực hiện

Quá trình huấn luyện:

```text
10 episode MuJoCo được thu bằng RGB-D/IK
                   ↓
Clean + tách train/validation + tạo nhãn SONIC đã kiểm tra replay
                   ↓
Dataset refined: 8 episode train / 2 episode validation
                   ↓
CloudWalk GR00T v10, checkpoint-30000
                   ↓
Fine-tune phần action head + projector G1
                   ↓
Merge thành checkpoint GR00T đầy đủ
                   ↓
Kiểm tra output trên validation → test policy trong simulation
```

Khi **test mô hình mới**, luồng điều khiển là:

```text
RGB camera + trạng thái robot + câu lệnh
                   ↓
           GR00T đã fine-tune
          ↙                  ↘
   motion token 64-D     lệnh ngón Dex3
          ↓                  ↓
    SONIC decoder         bàn tay
          ↓                  ↓
        khớp thân/tay → MuJoCo
```

Runtime test này không dùng YOLO, depth, IK hay phát lại động tác đã ghi.
Tọa độ chai từ simulator chỉ phục vụ bố trí cảnh và đo kết quả; không được
truyền vào policy làm tọa độ đích.

**Phần được học:** LoRA trong action diffusion transformer và projector
state/action cho embodiment G1. **VLM và SONIC được đóng băng.** Lượt này chưa
fine-tune VLM để hiểu thêm táo/Rubik hoặc thêm kỹ năng đặt chai.

Hoàn thành training và giảm loss chưa có nghĩa robot gắp thành công.
Checkpoint v1 đã train xong nhưng **chưa gắp và giữ chai ổn định** trong
closed-loop. Tài liệu hướng dẫn cách train và đo kết quả đó một cách riêng biệt.

## 2. Chuẩn bị thư mục và môi trường

Các lệnh bên dưới chạy từ:

```bash
cd ~/projects/GR00T-WholeBodyControl
```

Cấu trúc cần có:

```text
~/projects/
  Isaac-GR00T/
    .venv/                         # Python của train/policy server
  GR00T-WholeBodyControl/
    .venv_sim/                     # Python của MuJoCo/ONNX Runtime
    .venv_inference/               # Python của launcher tổng, nếu dùng
    gear_sonic/
    gear_sonic_deploy/
    checkpoints/
    outputs/
```

Không cần activate venv; các lệnh gọi thẳng Python phù hợp.
Lượt đã chạy dùng Isaac-GR00T revision
`51d4c89f72fda44cbf77285c6a8114b52676b8a1`.
Trên workspace đang có sửa đổi, không checkout đè code để đổi revision.

Kiểm tra môi trường train:

```bash
../Isaac-GR00T/.venv/bin/python - <<'PY'
import torch
import pandas, pyarrow, cv2, safetensors, huggingface_hub
import gr00t
from torchcodec.decoders import VideoDecoder
print('Torch:', torch.__version__)
print('CUDA:', torch.cuda.is_available())
assert torch.cuda.is_available(), 'Chưa có CUDA trong môi trường train'
print('GPU:', torch.cuda.get_device_name(0))
free, total = torch.cuda.mem_get_info()
print('VRAM trống/tổng GiB:', round(free/2**30, 2), round(total/2**30, 2))
PY
```

Kiểm tra môi trường simulation:

```bash
.venv_sim/bin/python - <<'PY'
import mujoco, numpy, scipy, cv2, onnxruntime, glfw, tkinter
import zmq, msgpack, msgpack_numpy
print('MuJoCo:', mujoco.__version__)
print('ONNX Runtime:', onnxruntime.__version__)
print('Simulation imports OK')
PY
```

Lượt v1 đã chạy trên RTX 5070 12 GB, peak CUDA allocated khoảng 6,22 GiB trong
job train. Đây không phải tổng VRAM của toàn hệ thống. Đóng cửa sổ policy
simulation/server đang chiếm GPU trước khi train hoặc đánh giá model mới.
Không chạy lại các script cài toàn bộ môi trường nếu các kiểm tra trên đã đạt.

## 3. Đăng nhập Hugging Face và lấy dataset

Dataset của bạn:

<https://huggingface.co/datasets/quyhuyhp123/g1-dex3-bottle-mujoco-10episodes-v1>

Repository hiện private. Kiểm tra tài khoản:

```bash
../Isaac-GR00T/.venv/bin/hf auth whoami
```

Nếu chưa đăng nhập hoặc token không hợp lệ:

```bash
../Isaac-GR00T/.venv/bin/hf auth login
```

Dùng tài khoản `quyhuyhp123` hoặc tài khoản được cấp quyền đọc repository.
Không đưa token vào file Python hoặc Git.

Tải đúng bản dataset đã dùng trong lượt v1, khoảng 318 MB:

```bash
../Isaac-GR00T/.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
path = snapshot_download(
    repo_id='quyhuyhp123/g1-dex3-bottle-mujoco-10episodes-v1',
    repo_type='dataset',
    revision='26fbe968fe9a8d2b3633206ed9d3bf0f10c7e991',
    local_dir='outputs/hf_g1_dex3_dataset_v1',
)
print('Dataset:', path)
PY
```

Thư mục sau khi tải:

```text
outputs/hf_g1_dex3_dataset_v1/
  README.md
  manifest.json
  raw/
    episodes.json
    episode_*.tar.gz                # 10 episode gốc
  previews/
    episode_*.mp4                   # 10 video camera để xem lại
  refined/
    export_report.json
    loader_validation.json
    train/
      data/                        # parquet
      videos/                      # video dùng cho loader
      meta/                        # feature order, modality, statistics
    validation/
      data/
      videos/
      meta/
  provenance/                      # clean/refine/replay và token đã fit
  code/
    gear_sonic/                    # snapshot script đã dùng
```

Để train lại trên **máy hiện tại**, cũng có thể dùng trực tiếp
`outputs/gr00t_dex3_refined_v1`; khi đó thay mọi giá trị `--dataset` tương ứng.
Các lệnh chính của tài liệu dùng đường dẫn dataset vừa tải để nhất quán.

### 3.1. Kiểm tra checksum trước khi xử lý

```bash
../Isaac-GR00T/.venv/bin/python - <<'PY'
import hashlib, json
from pathlib import Path
root = Path('outputs/hf_g1_dex3_dataset_v1')
manifest = json.loads((root/'manifest.json').read_text())
for item in manifest['files']:
    path = root/item['path']
    assert path.is_file(), f'Thiếu file: {path}'
    assert path.stat().st_size == item['size'], f'Sai kích thước: {path}'
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(block)
    assert digest.hexdigest() == item['sha256'], f'Sai SHA-256: {path}'
index = json.loads((root/'raw/episodes.json').read_text())
assert index['episode_count'] == 10
print('PASS:', len(manifest['files']), 'file; đủ 10 episode')
PY
```

### 3.2. Có cần giải nén raw và clean lại không?

Với bộ đã tải này, **dùng thẳng `refined/` để train**, vì clean, tách tập,
refine token và replay đã được thực hiện. Không dùng `raw/` làm đầu vào trực
tiếp cho script fine-tune; không dùng `ctrl` làm góc khớp hoặc motion token.

Nếu chỉ muốn xem video, mở các file trong `previews/`.
Nếu cần xem lại raw, giải nén vào thư mục mới:

```bash
mkdir -p outputs/hf_raw_episodes_v1
for archive in outputs/hf_g1_dex3_dataset_v1/raw/episode_*.tar.gz; do
  tar -xzf "$archive" -C outputs/hf_raw_episodes_v1
done
```

Raw giữ nguyên byte của dữ liệu thu. Khi replay trên máy khác, XML gốc có
thể chứa `compiler meshdir` trỏ tới máy thu dữ liệu; điều chỉnh đường dẫn này
trong bản XML giải nén đang dùng về thư mục mesh của checkout hiện tại.
Không cần sửa XML raw để train từ `refined/`.

## 4. Chuẩn bị script và kiểm tra loader thực tế

Các file chính cần có:

| File | Chức năng |
| --- | --- |
| `gear_sonic/scripts/validate_gr00t_candidate_dataset.py` | Đọc dataset bằng loader GR00T, decode video, kiểm tra shape và tạo báo cáo/hash |
| `gear_sonic/scripts/finetune_gr00t_g1.py` | Train LoRA/projector, validation, chọn best và merge |
| `gear_sonic/scripts/evaluate_finetuned_g1.py` | Nạp checkpoint mới qua Gr00tPolicy và đo output trên validation |
| `gear_sonic/scripts/run_finetuned_sim.py` | Server và simulation: model mới → SONIC → Dex3 |
| `gear_sonic/utils/mujoco_sim/object_reset.py` | Bố trí/reset chai trong cảnh; không điều khiển tiếp cận bằng IK |

Trên máy hiện tại đã có các file này thì giữ code đang dùng. Nếu là checkout
mới chưa có, copy snapshot mã nguồn của bản dataset:

```bash
cp -a outputs/hf_g1_dex3_dataset_v1/code/gear_sonic/. gear_sonic/
```

Lệnh copy chỉ dùng khi muốn đưa snapshot này vào checkout; nó có thể thay
các file cùng tên. Không chạy trên code đang sửa dở mà chưa lưu lại.

Kiểm tra loader:

```bash
PYTHONPATH=.:../Isaac-GR00T ../Isaac-GR00T/.venv/bin/python \
  gear_sonic/scripts/validate_gr00t_candidate_dataset.py \
  outputs/hf_g1_dex3_dataset_v1/refined
```

Kết quả cần có `PASS train/0...7` và `PASS validation/0...1`, ảnh decode shape
`480 × 640 × 3`, output hữu hạn. Script tính lại thống kê từng split và cập
nhật `loader_validation.json` cùng hash của các artifact đang dùng. Vì có
thể viết lại file thống kê, hãy kiểm tra manifest download ở bước 3.1 **trước**
khi chạy validator; manifest gốc mô tả bản đóng gói trước các thay đổi đó.

Kiểm tra điều kiện để train:

```bash
../Isaac-GR00T/.venv/bin/python - <<'PY'
import json
from pathlib import Path
p = Path('outputs/hf_g1_dex3_dataset_v1/refined')
export = json.loads((p/'export_report.json').read_text())
valid = json.loads((p/'loader_validation.json').read_text())
assert export['training_ready_for_fixed_base_profile'] is True
assert export['execution_profile_id'] == 'fixed_base_dex3_pd80_3_v1'
assert valid['loader_validation_passed'] is True
for split, expected_episodes, expected_rows in [('train', 8, 4972), ('validation', 2, 1188)]:
    info = json.loads((p/split/'meta/info.json').read_text())
    assert info['total_episodes'] == expected_episodes
    assert info['total_frames'] == expected_rows
    print(split, info['total_episodes'], 'episodes;', info['total_frames'], 'rows')
print('PASS: dataset refined đúng profile')
PY
```

Các cờ chung `training_ready=false`/`sonic_validated=false` trong báo cáo
không thay thế cờ theo profile. Dữ liệu chỉ được kiểm chứng với
`fixed_base_dex3_pd80_3_v1`, chưa có xác nhận cho whole-body tự do hoặc robot thật.

## 5. Tải checkpoint nền v10 và cache VLM backbone

Checkpoint nền dùng trong lượt đã chạy:

<https://huggingface.co/cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-371ep-v10-finetune>

Chỉ lấy `checkpoint-30000`:

```bash
../Isaac-GR00T/.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-371ep-v10-finetune',
    revision='f980fd880c92b984d65dcc3f9dc82b98bc8009c0',
    local_dir='checkpoints/cloudwalk_g1_bottle_v10',
    allow_patterns=['checkpoint-30000/**', 'README.md'],
)
backbone = snapshot_download('nvidia/Cosmos-Reason2-2B')
print('Backbone cache:', backbone)
PY
```

Nếu repository yêu cầu quyền truy cập, đăng nhập và chấp nhận điều khoản tại
<https://huggingface.co/nvidia/Cosmos-Reason2-2B> bằng cùng tài khoản.
Script train dùng `HF_HUB_OFFLINE=1` và `local_files_only=True`, nên backbone
phải được tải vào cache **trước khi train**.

Nếu đã có đủ file và cache, lệnh download sẽ dùng dữ liệu sẵn có.
Kiểm tra shard và cache:

```bash
../Isaac-GR00T/.venv/bin/python - <<'PY'
import json
from pathlib import Path
from huggingface_hub import snapshot_download
p = Path('checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000')
for name in ['config.json', 'processor_config.json', 'statistics.json',
             'embodiment_id.json', 'model.safetensors.index.json']:
    assert (p/name).is_file(), f'Thiếu {name}'
index = json.loads((p/'model.safetensors.index.json').read_text())
for name in set(index['weight_map'].values()):
    assert (p/name).is_file() and (p/name).stat().st_size > 0, f'Thiếu shard {name}'
print('PASS: v10 checkpoint-30000')
print('Backbone:', snapshot_download('nvidia/Cosmos-Reason2-2B', local_files_only=True))
PY
```

Trong lượt này, điểm khởi đầu vẫn là **CloudWalk v10**, không dùng model v1
của bạn làm `--checkpoint`. Muốn fine-tune tiếp từ v1 là một thí nghiệm khác.

## 6. Chạy fine-tune — output mới v2

Tài liệu dùng tên `v2` cho lần chạy lại để giữ nguyên kết quả `v1`.
Nếu thư mục v2 đã tồn tại, chọn tên mới và đổi nhất quán mọi lệnh bên dưới.
Script hiện không hỗ trợ resume đầy đủ optimizer từ một lượt bị ngắt; không
chạy đè lên output cũ.

Thông số:

| Tham số | Giá trị |
| --- | --- |
| Optimizer steps | 500 |
| Micro-batch | 1 |
| Gradient accumulation | 2; effective batch 2 |
| LoRA rank | 8 |
| Learning rate | `1e-4` |
| Warmup | 20 bước |
| Validation | Mỗi 50 bước; 8 cửa sổ/episode validation |
| Seed | 42 |
| Phần đóng băng | VLM và SONIC |

Chạy trong **Terminal 1**:

```bash
cd ~/projects/GR00T-WholeBodyControl
set -o pipefail
PYTHONPATH=.:../Isaac-GR00T ../Isaac-GR00T/.venv/bin/python -u \
  gear_sonic/scripts/finetune_gr00t_g1.py \
  --dataset outputs/hf_g1_dex3_dataset_v1/refined \
  --checkpoint checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000 \
  --output outputs/gr00t_g1_dex3_finetune_v2 \
  --steps 500 \
  --accumulation 2 \
  --rank 8 \
  --learning-rate 1e-4 \
  --warmup-steps 20 \
  --eval-every 50 \
  --validation-samples-per-episode 8 \
  --seed 42 \
  2>&1 | tee outputs/gr00t_g1_dex3_finetune_v2.log
```

Script tính lại normalization từ **train**, chọn adapter tốt nhất bằng
validation, sau đó merge thành checkpoint đầy đủ. Không lấy thống kê
validation để chuẩn hóa dữ liệu train.

Lượt v1 mất khoảng 5 phút 28 giây trên cấu hình đã nêu. Thời gian v2 phụ
thuộc GPU, VRAM trống, tốc độ giải mã video và tải hệ thống.

### 6.1. Theo dõi tiến trình

Trong **Terminal 2**:

```bash
cd ~/projects/GR00T-WholeBodyControl
tail -f outputs/gr00t_g1_dex3_finetune_v2.log
```

`Ctrl+C` trong Terminal 2 chỉ dừng theo dõi log. `Ctrl+C` trong Terminal 1
sẽ dừng training. Cần thấy dòng `COMPLETE` và terminal train trả về bình thường.

Mở file để xem trạng thái/loss:

```text
outputs/gr00t_g1_dex3_finetune_v2/training_report.json
```

Các trường chính: `status`, `completed_steps`, `best_step`,
`baseline_validation_flow_loss`, `best_validation_flow_loss`,
`merged_validation_flow_loss`, `history` và `error` nếu lỗi.

## 7. Xác nhận training hoàn tất và checkpoint đầy đủ

```bash
../Isaac-GR00T/.venv/bin/python - <<'PY'
import json
from pathlib import Path
run = Path('outputs/gr00t_g1_dex3_finetune_v2')
report = json.loads((run/'training_report.json').read_text())
assert report['status'] == 'complete', report
assert report['completed_steps'] == 500
p = run/'checkpoint-best'
for name in ['config.json', 'processor_config.json', 'statistics.json',
             'embodiment_id.json', 'model.safetensors.index.json', 'simulation_profile.json']:
    assert (p/name).is_file(), f'Thiếu {name}'
index = json.loads((p/'model.safetensors.index.json').read_text())
for name in set(index['weight_map'].values()):
    assert (p/name).is_file() and (p/name).stat().st_size > 0, f'Thiếu {name}'
config = json.loads((p/'config.json').read_text())
assert Path(config['model_name']).is_dir(), 'Mất cached_backbone hoặc cache HF'
print('Best step:', report['best_step'])
print('Validation trước train:', report['baseline_validation_flow_loss'])
print('Validation best:', report['best_validation_flow_loss'])
print('Validation sau merge:', report['merged_validation_flow_loss'])
print('Checkpoint:', p.resolve())
print('PASS: training hoàn tất, đủ shard và backbone')
PY
```

Cấu trúc kết quả:

```text
outputs/gr00t_g1_dex3_finetune_v2/
  training_report.json
  best_adapter.safetensors
  last_adapter.safetensors
  cached_backbone/                  # liên kết tới cache HF
  processor/
  experiment_cfg/
  source_checkpoint/
  checkpoint-best/                 # dùng thư mục này để inference
    config.json
    model-00001-of-00002.safetensors
    model-00002-of-00002.safetensors
    model.safetensors.index.json
    processor_config.json
    statistics.json
    embodiment_id.json
    simulation_profile.json
```

`best_adapter.safetensors` chỉ chứa tham số được học, không phải checkpoint
đầy đủ để truyền vào `--model-path`. Giữ `cached_backbone` và cache HF khi
dùng checkpoint local; config của lượt train trỏ đến đường dẫn tuyệt đối đó.
Nếu chuyển máy, cần đóng gói lại đường dẫn như bản model v1 trên Hugging Face.

## 8. Bổ sung cấu hình simulation cho checkpoint vừa train

**Không bỏ qua bước này.** Script train hiện tạo `simulation_profile.json`
cơ bản nhưng chưa đóng gói scene, home pose, mapping/gain đầy đủ. Runtime
`run_finetuned_sim.py` cần các phần đó để dùng đúng profile đã tạo nhãn.

Lấy **cấu hình runtime** từ bản v1 đã upload, không tải lại hai shard model v1:

```bash
../Isaac-GR00T/.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='quyhuyhp123/gr00t-n17-g1-dex3-bottle-sim-v1',
    revision='973b899d3378c9477c9b46bf4c6b8448298bd1cc',
    local_dir='outputs/hf_g1_dex3_runtime_v1',
    allow_patterns=[
        'simulation_profile.json', 'simulation_scene.xml',
        'simulation_assets/**', 'README.md',
    ],
)
PY
```

Copy cấu hình cảnh/controller sang checkpoint **v2**:

```bash
../Isaac-GR00T/.venv/bin/python - <<'PY'
import json, shutil
from pathlib import Path
source = Path('outputs/hf_g1_dex3_runtime_v1')
run = Path('outputs/gr00t_g1_dex3_finetune_v2')
target = run/'checkpoint-best'
assert json.loads((run/'training_report.json').read_text())['status'] == 'complete'
trained = json.loads((target/'simulation_profile.json').read_text())
profile = json.loads((source/'simulation_profile.json').read_text())
assert profile['execution_profile_id'] == trained['execution_profile_id'] == 'fixed_base_dex3_pd80_3_v1'
assert profile['hand_format'] == trained['hand_format'] == 'dex3_joint_radians'
profile['policy_pickup_success_validated'] = False
(target/'simulation_profile.json').write_text(json.dumps(profile, indent=2)+'\n')
shutil.copyfile(source/'simulation_scene.xml', target/'simulation_scene.xml')
shutil.copytree(source/'simulation_assets', target/'simulation_assets', dirs_exist_ok=True)
print('Đã bổ sung scene, mesh và profile Dex3 cho:', target)
print('Trọng số fine-tune v2 không bị thay thế.')
PY
```

Thao tác này chỉ sao chép static scene, robot home pose, ánh xạ khớp, gain,
action scale và thông tin controller. Không chép trọng số v1 hoặc động tác
expert vào v2. Chỉ áp dụng khi train bằng chính dataset/profile này; nếu đổi
bàn tay/controller hoặc cách tạo nhãn thì phải xây dựng profile tương ứng.

### 8.1. Kiểm tra SONIC và scene

Decoder cần có tại:

```text
gear_sonic_deploy/policy/release/model_decoder.onnx
```

Nếu thiếu SONIC, làm bước tải model trong mục 9 của
[hướng dẫn cài đặt](../WSL_UPSTREAM_V10_SETUP.md#91-sonic).
Không đổi sang phiên bản decoder khác vì cùng kích thước token.

Kiểm tra bằng MuJoCo và hash thực tế:

```bash
PYTHONPATH=. .venv_sim/bin/python - <<'PY'
import hashlib
from pathlib import Path
import mujoco
from gear_sonic.scripts.run_finetuned_sim import checkpoint_metadata
p = Path('outputs/gr00t_g1_dex3_finetune_v2/checkpoint-best')
meta = checkpoint_metadata(p)
profile = meta['profile']
decoder = Path('gear_sonic_deploy/policy/release/model_decoder.onnx')
assert hashlib.sha256(decoder.read_bytes()).hexdigest() == profile['sonic_decoder_sha256']
m = mujoco.MjModel.from_xml_path(str(p/profile['scene_file']))
assert m.nu == 43
print('PASS: checkpoint/profile, decoder SHA-256 và scene MJCF')
print('Profile:', profile['execution_profile_id'])
print('MJCF nq/nu:', m.nq, m.nu)
PY
```

Profile này cố định pelvis, giữ chân/tay trái; SONIC điều khiển waist pitch
và 7 khớp tay phải. Ngón tay nhận góc Dex3 từ model mới. Không thêm
`--inspire-ftp-hands` hoặc các cờ assisted pickup cho checkpoint này.

## 9. Test output của model trên validation

Bước này thực sự nạp checkpoint đã merge qua `Gr00tPolicy`, suy luận từ
ảnh/state/câu lệnh trên hai episode validation và so sánh action với nhãn.
Đây là **đánh giá open-loop**, chưa đưa robot chạy vật lý.

```bash
PYTHONPATH=.:../Isaac-GR00T ../Isaac-GR00T/.venv/bin/python -u \
  gear_sonic/scripts/evaluate_finetuned_g1.py \
  --checkpoint outputs/gr00t_g1_dex3_finetune_v2/checkpoint-best \
  --dataset outputs/hf_g1_dex3_dataset_v1/refined \
  --samples-per-episode 8 \
  --output outputs/gr00t_g1_dex3_finetune_v2/evaluation
```

Kết quả nằm tại:

```text
outputs/gr00t_g1_dex3_finetune_v2/evaluation/
  evaluation_report.json
  predictions.npz
```

Cần kiểm tra:

- `policy_reload_passed=true`: checkpoint đã nạp được.
- `finite_action_shapes_passed=true`: chunk đúng shape, không NaN/Inf.
- `samples=16`, `validation_episodes=2`.
- `motion_token_rmse`: đơn vị latent, không phải sai số tọa độ mét.
- `right_hand_rmse_rad`: sai số góc ngón tay, đơn vị radian.
- `closed_loop_pickup_validated=false` vẫn đúng ở bước này.

Action được kiểm tra có shape `(1,40,64)`, `(1,40,7)`, `(1,40,7)`.
Script evaluation dùng số bước diffusion trong config model; runtime simulation
bên dưới đặt rõ 16 bước. Vì vậy không đồng nhất hai phép thử này thành cùng
một rollout vật lý.

## 10. Test trong simulation có giao diện

Chỉ chạy sau khi lệnh evaluation đã kết thúc, để tránh hai bản model cùng
chiếm VRAM. Lệnh dưới tự mở server riêng và simulator; không cần mở thêm
`run_gr00t_server.py` trước.

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python gear_sonic/scripts/run_finetuned_sim.py \
  --model-path outputs/gr00t_g1_dex3_finetune_v2/checkpoint-best \
  --policy-host 127.0.0.1 \
  --policy-port 5551 \
  --prompt "grab the bottle" \
  --execute-steps 10 \
  --diffusion-steps 16 \
  --sampling-seed 42 \
  --video \
  --output outputs/finetuned_policy_sim/v2_gui
```

Chờ server nạp model và xác minh đúng checkpoint. Khi mới mở, robot giữ
tư thế chờ và thời gian physics chưa chạy. Thao tác:

| Điều khiển | Chức năng |
| --- | --- |
| Start / `F6` | Bắt đầu nhận action từ model và chạy robot |
| Reset all / `F5` | Reset robot, chai, chunk và lịch sử SONIC về trạng thái chờ |
| Bottle X/Y + Apply | Đổi vị trí chai khi đang chờ; Z theo mặt bàn |
| Kéo chuột phải | Xoay góc nhìn |
| Kéo chuột giữa | Dịch góc nhìn |
| Con lăn | Zoom |
| `Esc` trong cửa sổ robot | Đóng simulation; launcher đóng server do nó tạo |

Bắt đầu bằng vị trí chai mặc định để đo baseline, sau đó mới thử các X/Y
khác trên bàn. Việc nhập được X/Y không chứng minh policy đã học gắp ở mọi
vị trí đó. Lượt reset làm mất các số đo của lượt trước trong `run_report.json`;
muốn giữ kết quả riêng, đóng phiên và dùng `--output` mới cho lượt kế tiếp.

Output:

```text
outputs/finetuned_policy_sim/v2_gui/
  server.log
  run_report.json
  actions.jsonl
  policy_simulation.mp4
```

Video là góc nhìn ngoài của robot; model vẫn nhận RGB từ `head_camera`.
Đóng chương trình bình thường để hoàn tất file MP4. Runtime chờ action chunk
mới khi suy luận chậm hơn physics, nên tốc độ theo thời gian thực có thể thấp
hơn 1×. Mỗi chunk thực hiện 10/40 action rồi chụp ảnh/state mới để suy luận tiếp.

## 11. Test tự động 15 giây và ghi video

Đóng GUI của bước 10 trước. Đây là lượt test tự động trong physics, không
phải phát lại episode. Chương trình tự Start, chạy 15 giây simulation rồi thoát:

```bash
.venv_sim/bin/python gear_sonic/scripts/run_finetuned_sim.py \
  --model-path outputs/gr00t_g1_dex3_finetune_v2/checkpoint-best \
  --headless --auto-start --duration 15 \
  --max-wall-seconds 300 \
  --execute-steps 10 --diffusion-steps 16 --sampling-seed 42 \
  --prompt "grab the bottle" \
  --video \
  --output outputs/finetuned_policy_sim/v2_headless
```

Headless tự chọn EGL và không hiện cửa sổ. Nếu WSL/GPU chưa hỗ trợ EGL,
dùng GUI ở bước 10. `--duration` là giây simulation; `--max-wall-seconds`
là giới hạn thời gian thật cho cả quá trình headless.

Muốn đo vị trí khác, dùng output khác và thêm, ví dụ:

```text
--bottle-xy 0.40 -0.05
```

Không bật đồng thời nhiều lượt test trên GPU 12 GB. Giữ cùng prompt, seed,
diffusion steps, số action/chunk và vị trí chai khi so sánh hai checkpoint.

## 12. Đọc kết quả: model có thật sự điều khiển và gắp thành công không?

```bash
../Isaac-GR00T/.venv/bin/python - <<'PY'
import json
from pathlib import Path
p = Path('outputs/finetuned_policy_sim/v2_headless/run_report.json')
r = json.loads(p.read_text())
for key in ['status', 'model_path', 'server_verified', 'model_calls',
            'decoder_steps', 'simulation_time_s', 'peak_bottle_lift_m',
            'final_bottle_lift_m', 'opposed_contact_hold_s', 'pickup_success', 'error']:
    print(key, ':', r.get(key))
assert r['server_verified'] is True
assert r['model_calls'] > 0 and r['decoder_steps'] > 0
assert r['rgb_depth_ik'] is False and r['ik_enabled'] is False
assert r['detector_enabled'] is False and r['recorded_actions_used'] is False
assert r['forbidden_modules_loaded'] == []
assert Path(r['model_path']).resolve() == Path('outputs/gr00t_g1_dex3_finetune_v2/checkpoint-best').resolve()
print('PASS: đúng checkpoint v2 → SONIC, không RGB-D/IK/replay')
print('Kết quả gắp thực tế:', r['pickup_success'])
PY
```

Ý nghĩa các trường:

| Trường | Cách hiểu |
| --- | --- |
| `status=complete` | Lượt simulation kết thúc bình thường; không tự đồng nghĩa gắp thành công |
| `server_verified=true` | Runtime xác minh metadata/fingerprint của đúng checkpoint được yêu cầu |
| `model_calls > 0` | Có gọi model suy luận |
| `decoder_steps > 0` | Có đưa motion token qua SONIC để điều khiển |
| `peak_bottle_lift_m` | Độ cao nâng chai lớn nhất so với Z ban đầu |
| `final_bottle_lift_m` | Độ cao còn giữ được ở cuối lượt |
| `opposed_contact_hold_s` | Thời gian giữ liên tục lâu nhất thỏa điều kiện tiếp xúc và nâng |
| `pickup_success=true` | Đạt tiêu chí nắm/nâng/giữ của runtime |

Tiêu chí giữ hiện tại: chai cao hơn ban đầu **12 cm**, tiếp xúc ngón cái
và ngón trỏ hoặc giữa, trục chai đủ thẳng (`Rzz > 0.85`). Để đánh dấu thành
công, phải giữ liên tục ít nhất **1 giây** và cuối lượt chai vẫn cao hơn ban
đầu **10 cm**. Đối chiếu thêm video để phân biệt nắm thật với va chạm làm chai bật lên.

`model_calls>0` và `pickup_success=false` nghĩa là inference đã chạy nhưng
policy chưa hoàn tất tác vụ. Không sửa cờ báo cáo thành true chỉ vì training
loss thấp hoặc video replay của dữ liệu gốc đẹp.

## 13. Mốc tham khảo của lượt v1 đã thực hiện

Các giá trị này mô tả **v1**, không phải kết quả đảm bảo cho v2:

| Phép đo | Kết quả v1 |
| --- | --- |
| Training | 500 bước, 8 train / 2 validation |
| Validation flow loss trước train | 1,402045 |
| Validation flow loss best | 0,138523 |
| Validation flow loss sau merge | 0,138436 |
| Open-loop motion-token RMSE | 0,058964 |
| Open-loop right-hand RMSE | 0,162250 rad |
| Replay nhãn token offline | 10/10 đạt trong profile cố định |
| Test policy cuối, 15 giây | 75 model calls, 750 decoder steps |
| Peak bottle lift trong lượt test policy cuối | khoảng 0,001677 m |
| Closed-loop pickup | `false` |

Báo cáo tương ứng trên máy hiện tại:

```text
outputs/gr00t_g1_dex3_finetune_v1/training_report.json
outputs/gr00t_g1_dex3_finetune_v1/evaluation/evaluation_report.json
outputs/finetuned_policy_sim/integration_final/run_report.json
```

File `outputs/sonic_reference_physics/sonic_candidate/rollout_report.json`
là thử nghiệm cũ khác, không dùng nó để kết luận cho lượt v2 vừa chạy.
Đổi tên output từ v1 sang v2 chỉ giúp lưu riêng thí nghiệm; bản thân việc
train lại cùng dữ liệu/thông số chưa bảo đảm cải thiện chất lượng gắp.

## 14. Lỗi thường gặp và bước xử lý

| Hiện tượng | Kiểm tra/xử lý |
| --- | --- |
| Hugging Face 401/403/404 | Kiểm tra `hf auth whoami`, quyền repo private và quyền backbone; không tải lại bằng token đã báo invalid |
| Không tìm thấy backbone khi train | Chạy `snapshot_download('nvidia/Cosmos-Reason2-2B')` ở bước 5 trước; train đang offline |
| `Choose a new output directory` | Chọn tên output chưa tồn tại; script không resume optimizer |
| `Dataset changed: ...` | Kiểm tra có sửa parquet/video/stats sau validation không; khôi phục hoặc xác minh dữ liệu rồi chạy lại validator |
| CUDA out of memory | Đóng policy server/GUI cũ, xem `nvidia-smi`; kiểm tra đúng môi trường và gradient checkpointing trong script |
| `Requires verified refined labels` | Dùng dataset `refined/` có cờ profile, không dùng raw/candidate cũ |
| `Checkpoint is missing its static simulation scene/home configuration` | Làm đầy đủ bước 8 sau training |
| `SONIC decoder differs...` | Decoder không khớp SHA-256 của profile; lấy đúng artifact đã dùng tạo nhãn |
| Không hiện cửa sổ robot | Bước 11 là headless nên không có GUI; với bước 10 kiểm tra DISPLAY/WSLg và runtime đã có sửa GLFW VISIBLE |
| Start bị mờ | Server chưa xác minh xong hoặc có lỗi nạp model; đọc `server.log` và trạng thái panel |
| Sai checkpoint/hand format | Dùng `checkpoint-best` v2, native Dex3 và runtime bước 10; không ghép server v10/Inspire cũ |
| `Address already in use` | Orchestrator thường chọn cổng trống kế tiếp; đừng mở thêm server thủ công cho lệnh một bước này |
| MP4 chưa xem được | Đóng simulator bình thường để writer hoàn tất; xem đúng thư mục `--output` vừa chạy |
| Model đưa tay/khép tay sớm nhưng không gắp | Xem video, action và validation; đây có thể là lỗi policy, không chỉ lỗi kết nối hoặc vị trí chai |

## 15. Checklist kết thúc một lượt

- [ ] Dataset download đúng commit, kiểm tra checksum trước khi xử lý.
- [ ] Loader đọc đủ 8 train và 2 validation, decode được RGB.
- [ ] Base là CloudWalk v10 `checkpoint-30000`, backbone đã cache.
- [ ] Training report `status=complete`, đủ 500 bước và checkpoint đầy đủ.
- [ ] Bổ sung scene, mesh, home pose và profile cố định cho checkpoint mới.
- [ ] Evaluation nạp được model, output đúng shape và hữu hạn.
- [ ] Simulation xác minh đúng v2, `model_calls` và `decoder_steps` tăng.
- [ ] RGB-D/IK/detector/replay đều tắt trong runtime model.
- [ ] Đọc `pickup_success` và xem video trước khi kết luận robot đã gắp được.
- [ ] Giữ lại report, log, checkpoint, dataset commit và tham số test để so sánh lần sau.

Nếu chỉ muốn thử ngay **model v1 đã train sẵn**, không cần train lại: dùng
hướng dẫn tải model ở mục 14 của [bước 8](08_thu_du_lieu_rgbd_ik.md#14-đưa-checkpoint-và-10-episode-lên-hugging-face).
Model sẵn có vẫn mang giới hạn chất lượng đã nêu ở trên.

## 16. Lệnh chạy lại model v1 đã fine-tune — server và simulation

Mục này dùng **checkpoint v1 đã có trên máy**, không cần train lại:

```text
outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best
```

Chọn **một** trong hai cách bên dưới. Cách 16.1 tự mở server; cách 16.2
tách server và simulation thành hai terminal.

### 16.1. Một lệnh tự mở server và simulation

Đây là lệnh chạy lại nhanh, tự nạp checkpoint vào server và mở robot:

```bash
cd ~/projects/GR00T-WholeBodyControl

.venv_sim/bin/python gear_sonic/scripts/run_finetuned_sim.py \
  --model-path outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best \
  --prompt "grab the bottle"
```

Không cần mở server riêng trước lệnh này. Chờ model tải và xác minh xong,
sau đó nhấn **Start/F6**. **Reset/F5** đưa robot/chai về trạng thái chờ;
**Esc** trong cửa sổ robot đóng simulation và server mà lệnh đã tạo.

### 16.2. Mở server riêng rồi chạy simulation

**Terminal 1 — khởi động server của model fine-tune v1:**

```bash
cd ~/projects/GR00T-WholeBodyControl

HF_HUB_OFFLINE=1 PYTHONPATH=.:../Isaac-GR00T \
  ../Isaac-GR00T/.venv/bin/python -u \
  gear_sonic/scripts/run_finetuned_sim.py \
  --mode server \
  --model-path "$PWD/outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best" \
  --device cuda:0 \
  --policy-host 127.0.0.1 \
  --policy-port 5551 \
  --diffusion-steps 16 \
  --sampling-seed 42
```

Giữ Terminal 1 chạy. Server này có endpoint `get_policy_metadata` để
simulation xác minh checkpoint và quy ước native Dex3 trước khi cho Start.
Backbone phải có trong cache như bước 5.

**Terminal 2 — kết nối simulation tới server vừa mở:**

```bash
cd ~/projects/GR00T-WholeBodyControl

.venv_sim/bin/python gear_sonic/scripts/run_finetuned_sim.py \
  --external-server \
  --model-path outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best \
  --policy-host 127.0.0.1 \
  --policy-port 5551 \
  --prompt "grab the bottle"
```

`--external-server` yêu cầu dùng server đã mở ở Terminal 1. Model path,
host và port phải khớp ở cả hai terminal. Sau khi đóng simulation, server
mở riêng vẫn chạy; nhấn **Ctrl+C tại Terminal 1** để dừng server và giải phóng GPU.

### 16.3. Chạy lại và lưu video

Lệnh sau là biến thể của cách 16.1, tự mở server và lưu video vào thư mục
mới theo ngày/giờ:

```bash
cd ~/projects/GR00T-WholeBodyControl

.venv_sim/bin/python gear_sonic/scripts/run_finetuned_sim.py \
  --model-path outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best \
  --prompt "grab the bottle" \
  --video \
  --output "outputs/finetuned_policy_sim/video_$(date +%Y%m%d_%H%M%S)"
```

Nếu đang dùng server riêng theo cách 16.2, thêm `--external-server
--policy-host 127.0.0.1 --policy-port 5551` vào lệnh quay video.

Nhấn **Start/F6** để bắt đầu. Nhấn **Esc** để đóng bình thường và hoàn tất MP4.
Terminal in đường dẫn output thực tế; mở file:

```text
outputs/finetuned_policy_sim/video_<ngày_giờ>/policy_simulation.mp4
```

Cùng thư mục có `run_report.json` và `actions.jsonl`. Với server tự mở còn
có `server.log`; với server riêng, log server hiển thị ở Terminal 1.
Video ghi góc nhìn ngoài; model nhận ảnh từ camera `head_camera`.
Luồng vẫn là **model fine-tune v1 → SONIC → robot**, với lệnh ngón tay Dex3
đi từ model đến bàn tay; RGB-D/IK và detector không tham gia điều khiển.
