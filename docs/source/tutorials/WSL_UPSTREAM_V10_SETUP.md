# Cài WSL, GR00T-WholeBodyControl và chạy MuJoCo với checkpoint v10

Ngày đối chiếu: 11/10/2026. Dành cho Windows + GPU NVIDIA, WSL2 Ubuntu 22.04 x86_64.


## Đang dùng workspace đã sửa trên máy này? Chạy lệnh dưới đây

Cập nhật kiểm tra ngày **20/10/2026**. Các mục 1–13 phía dưới hướng dẫn **bản
upstream nguyên gốc**. Workspace hiện tại có code gắp và Inspire tùy chỉnh;
lệnh tối giản ở mục 11 không bật bộ hỗ trợ gắp này.

Server đang chạy đúng v10 ở `127.0.0.1:5550` thì **giữ nguyên**, không nạp thêm
server. Có thể kiểm tra phản hồi (không nạp model mới):

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python - <<'PYHEALTH'
from gr00t.policy.server_client import PolicyClient
client = PolicyClient(host='127.0.0.1', port=5550, timeout_ms=3000)
try:
    print('Server ready:', client.ping())
finally:
    client.close()
PYHEALTH
```

Nếu kết quả `False` hoặc không có server, mở **terminal 1** và chạy:

```bash
cd ~/projects/GR00T-WholeBodyControl
bash gear_sonic/scripts/run_cloudwalk_policy_server.sh
```

Chờ server sẵn sàng. Nếu gặp 401 Cosmos, xử lý quyền Hugging Face ở mục 6;
đăng nhập bằng `.venv/bin/hf auth login` trong repo Isaac-GR00T, kiểm tra
`.venv/bin/hf auth whoami`. Token không hợp lệ phải thay token trước khi
kiểm tra quyền model. Không nâng package để xử lý lỗi xác thực.

**Terminal 2 — lệnh gắp với bàn tay Inspire hiện tại:**

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim \
  --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter \
  --sim-native-inspire --sim-assisted-pickup --sim-fixed-base \
  --sim-bottle-xy 0.43 -0.05 \
  --prompt "grab the bottle"
```

Launcher thay phiên `sonic_inference` cũ. Lệnh này chỉ dùng simulation, không
kết nối robot thật. Không cần thêm `--inspire-ftp-hands`: đó là adapter Dex3
của chế độ trước, không chọn bàn tay Inspire native.

Nếu báo thiếu scene native, tạo một lần rồi chạy lại launcher:

```bash
.venv_sim/bin/python gear_sonic/scripts/prepare_inspire_ftp_sim.py
```

Trong cửa sổ simulation:

1. Chờ C++/camera/VLA sẵn sàng; robot giữ tư thế chờ.
2. Bấm **Start GR00T**, chờ nhận diện → tiếp cận → nắm → nâng.
3. Khi `success`, nhập đích X/Y, bấm **Lower / Place on table**.
4. Chờ mở tay, thu tay và `complete`, rồi Start để gắp lượt tiếp.
5. Reset dùng để khởi tạo lại; không nhấn `9`, `k/i/p` xen vào chu trình
   Start/Lower của chế độ này. Không đóng viewer khi muốn giữ simulation chạy.

Đây là GR00T kết hợp điều khiển hỗ trợ RGB-D/IK, pelvis cố định; không phải
checkpoint tự sinh toàn bộ động tác. Chi tiết ở
[WSL_BLUE_BOTTLE_COMPLETE_GUIDE.md](WSL_BLUE_BOTTLE_COMPLETE_GUIDE.md).

### Kiểm tra lại ngày 20/10/2026

Đã chạy lại cấu hình Inspire ở trên: server v10 ping thành công, camera port
5555, VLA kết nối được server và SONIC đã in `Init Done`, mở telemetry 5557.
Phiên được để ở trạng thái chờ Start. Kiểm thử tự động gồm 5 kiểm tra CLI/
bootstrap, 4 kiểm tra độ mới observation và 2 kiểm tra native Inspire: đều qua.
Bài vật lý dùng đầu vào nhận diện có kiểm soát, kiểm tra bốn vị trí chai, giữ,
đặt, thu tay, gắp lại và Reset; không thay thế đánh giá YOLO/VLA trực tiếp.

Đã sửa `gear_sonic/scripts/launch_inference.py`: kiểm tra scene native được
chuyển từ bootstrap sang kiểm tra prerequisite, tránh dùng `config/errors`
trước khi chúng tồn tại và báo thiếu scene trước khi thay phiên tmux.

### Log đã xác nhận trong lần kiểm tra

- Server v10 ping thành công; các shard checkpoint hiện đủ file.
- Phiên đang lỗi được chạy không có assisted/native/fixed-base.
- Log MuJoCo kết thúc bằng `++++closing simulator ++++`, sau đó SONIC báo
  `Lost LowState data connection` và dừng. Log này chưa cho biết lý do viewer
  đóng; không quy kết là lỗi model hoặc người dùng thao tác.
- Dòng loopback không hỗ trợ multicast và lần thử tạo DDS Domain bị lỗi cũng
  có trong log. Phiên đó vẫn đã gửi ảnh/action sau đó; chưa đủ bằng chứng để
  coi cảnh báo này là nguyên nhân dừng. Nếu lặp lại mà không nhận LowState,
  cần đọc log startup DDS đầy đủ, không chuyển interface simulation sang LAN.

## 1. Kết quả và phạm vi

Hướng dẫn này cài repository gốc [NVlabs/GR00T-WholeBodyControl](https://github.com/NVlabs/GR00T-WholeBodyControl), Isaac-GR00T policy server và checkpoint CloudWalk v10. Kết quả cần đạt là mở robot G1 trong MuJoCo, nhận ảnh camera/trạng thái robot và chạy suy luận v10 qua SONIC.

**Chưa bao gồm** giao diện tùy chỉnh, YOLO, bàn/chai tùy chỉnh, bộ hỗ trợ IK gắp–nâng–đặt hay bàn tay Inspire native. Cảnh gốc không phải cảnh gắp chai hoàn chỉnh đã sửa trên máy hiện tại. Chạy được inference không đồng nghĩa đã gắp được chai: còn phụ thuộc cảnh, camera, bàn tay và controller phù hợp với dữ liệu huấn luyện.

Luồng chạy:

```text
Ảnh camera MuJoCo + prompt + trạng thái robot
                    ↓
            Isaac-GR00T v10, cổng 5550
                    ↓
       motion token + lệnh khớp bàn tay
                    ↓
            SONIC C++ + MuJoCo
```

Đây là MuJoCo; không cần cài Isaac Sim cho hướng dẫn này. Chỉ chạy simulation.
Hướng dẫn được đối chiếu với mã nguồn và môi trường hiện có; chưa kiểm thử một lượt cài sạch toàn bộ trên Windows mới.

## 2. Chuẩn bị máy và dung lượng

- Windows có WSL2/WSLg; Windows 11 là lựa chọn thuận tiện cho cửa sổ MuJoCo.
- GPU NVIDIA và driver Windows hỗ trợ CUDA trong WSL.
- Cần đủ VRAM cho VLA, SONIC/TensorRT và render đồng thời. Không coi kích thước checkpoint trên đĩa là lượng VRAM cần dùng.
- Dự trù trên 100 GB dung lượng trống cho môi trường, CUDA/TensorRT, model và cache; đây là dự trù, không phải yêu cầu tối thiểu đã đo.
- Nếu ổ C gần đầy, bố trí WSL trên ổ có đủ dung lượng trước khi tải model. Thư mục Linux `~/projects` vẫn nằm trong đĩa ảo của bản WSL, không tự chuyển ra khỏi ổ C.

Chỉ tải checkpoint-30000, không tải dataset, model v6 hay các checkpoint-10000/20000.

## 3. Cài WSL

Mở **PowerShell với quyền Administrator**:

```powershell
wsl --install -d Ubuntu-22.04
```

Khởi động lại nếu được yêu cầu. Mở Ubuntu, tạo tên người dùng và mật khẩu Linux. Tiếp tục trong PowerShell:

```powershell
wsl --update
wsl --set-default-version 2
wsl -l -v
```

Ubuntu-22.04 phải có VERSION 2. Nếu đang là 1:

```powershell
wsl --set-version Ubuntu-22.04 2
```

Các bước cài WSL dựa trên [hướng dẫn Microsoft](https://learn.microsoft.com/en-us/windows/wsl/install).

Cài/cập nhật NVIDIA driver **trên Windows**. Không cài Linux display driver trong WSL; tham khảo [CUDA on WSL của NVIDIA](https://docs.nvidia.com/cuda/wsl-user-guide/index.html).

Tất cả lệnh `bash` bên dưới chạy trong **Ubuntu WSL**, không chạy trong PowerShell.

```bash
nvidia-smi
printf 'DISPLAY=%s\nWAYLAND_DISPLAY=%s\n' "$DISPLAY" "$WAYLAND_DISPLAY"
sudo apt update
sudo apt install -y git git-lfs curl wget build-essential cmake ninja-build \
  pkg-config tmux unzip python3-dev python3-tk libgl1 libegl1 libglfw3 \
  libglib2.0-0 ffmpeg mesa-utils
mkdir -p ~/projects
git lfs install
```

Nếu `nvidia-smi` không có trong PATH, thử `/usr/lib/wsl/lib/nvidia-smi`. Chưa thấy GPU thì xử lý driver/WSL trước khi tiếp tục. `glxinfo -B` giúp kiểm tra OpenGL/WSLg khi không mở được cửa sổ.

## 4. Clone hai repository và chốt phiên bản

Các lệnh sau dành cho **máy/thư mục mới**. Trên máy đang chạy, không checkout đè repository có code sửa và không cài lại môi trường chỉ để đọc hướng dẫn này.

```bash
cd ~/projects
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/NVlabs/GR00T-WholeBodyControl.git
cd GR00T-WholeBodyControl
git checkout b042411fae38ee4d1af9aac82a37a1f8d14d6dd0
git submodule update --init --recursive
git lfs pull --exclude='motionbricks/out/**'

cd ~/projects
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/NVIDIA/Isaac-GR00T.git
cd Isaac-GR00T
git checkout 51d4c89f72fda44cbf77285c6a8114b52676b8a1
GIT_LFS_SKIP_SMUDGE=1 git submodule update --init --recursive
```

Bỏ tải LFS tự động của Isaac-GR00T để tránh lấy demo dataset không dùng cho suy luận. Robot assets của WBC vẫn cần `git lfs pull` ở trên.

Cấu trúc:

```text
~/projects/
├── GR00T-WholeBodyControl/
└── Isaac-GR00T/
```

Chốt hai commit để tránh `main` thay đổi API/phụ thuộc. Không áp các bản vá giao diện từ tài liệu khác trong quá trình này.

## 5. CUDA Toolkit và TensorRT C++

PyTorch có CUDA runtime riêng, nhưng phần C++ SONIC còn cần CUDA Toolkit và TensorRT SDK.

Trên Ubuntu 22.04 x86_64, cài Toolkit 12.4 dùng cho C++ theo cấu hình máy tham chiếu:

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/cuda-keyring.deb
sudo dpkg -i /tmp/cuda-keyring.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-4
```

Chỉ dùng gói Toolkit; không thay bằng meta-package `cuda`/`cuda-drivers` có thể kéo driver Linux vào WSL.

Tải **TensorRT 10.13, Linux x86_64, CUDA 12.x, định dạng TAR** từ [NVIDIA TensorRT downloads](https://developer.nvidia.com/tensorrt/download/10x). Giải nén vào `~/TensorRT` sao cho có trực tiếp `~/TensorRT/include/NvInfer.h` và `~/TensorRT/lib/libnvinfer.so`. Tên archive tùy bản tải, không dùng đường dẫn ví dụ như tên file thật.

Thêm ba dòng sau vào `~/.bashrc` bằng trình soạn thảo:

```bash
export CUDA_HOME=/usr/local/cuda-12.4
export PATH="$CUDA_HOME/bin:$PATH"
export TensorRT_ROOT="$HOME/TensorRT"
```

Nạp và kiểm tra:

```bash
source ~/.bashrc
nvcc --version
ls "$TensorRT_ROOT/include/NvInfer.h" "$TensorRT_ROOT/lib/libnvinfer.so"
```

TensorRT SDK C++ này tách biệt với TensorRT Python mà Isaac-GR00T cài trong venv. PyTorch ở commit đã chốt dùng CUDA 12.8 wheels; driver Windows cần hỗ trợ runtime đó, dù Toolkit C++ là 12.4. `nvidia-smi` không cho biết Toolkit nào đã cài.

## 6. Cài uv và môi trường policy server

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv --version

cd ~/projects/Isaac-GR00T
uv sync --python 3.12
.venv/bin/python -c "import torch, gr00t; print(torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

CUDA phải là `True`. Lần cài đầu tải nhiều gói lớn; không ngắt chỉ vì đang tải Torch/FlashAttention/TensorRT.

Backbone `nvidia/Cosmos-Reason2-2B` có kiểm soát quyền truy cập. Truy cập [trang model](https://huggingface.co/nvidia/Cosmos-Reason2-2B), chấp nhận điều khoản/yêu cầu quyền, sau đó đăng nhập tài khoản đó:

```bash
cd ~/projects/Isaac-GR00T
.venv/bin/hf auth login
```

Không ghi token vào tài liệu hoặc commit Git. Có v10 trên ổ đĩa vẫn cần backbone/processor khi server nạp model.

## 7. Build SONIC C++ và cài simulator

```bash
cd ~/projects/GR00T-WholeBodyControl/gear_sonic_deploy
bash scripts/install_deps.sh
source scripts/setup_env.sh
just build

cd ~/projects/GR00T-WholeBodyControl
bash install_scripts/install_mujoco_sim.sh
.venv_sim/bin/python -c "import mujoco, unitree_sdk2py; print('MuJoCo:', mujoco.__version__)"
```

Script tạo `.venv_sim` Python 3.10. Script install có thể xóa và tạo lại venv cùng tên: chỉ dùng lúc cài đặt, không chạy mỗi lần bật simulator.

Nếu build hết RAM, giảm số job build theo `gear_sonic_deploy/justfile`; không mở thêm một lượt build song song. Không sao chép TensorRT engine từ máy/GPU khác.

## 8. Cài môi trường inference tương thích Python 3.12

Ở commit WBC đã chốt, `install_inference.sh` còn dùng Python 3.10 và tên dependency `Isaac-GR00T`; server đã chốt yêu cầu Python 3.12 và package tên `gr00t`. Vì vậy dùng các lệnh dưới thay cho script đó.

Tạo môi trường client từ cùng project/lock của server, sau đó bổ sung WBC và các thư viện client. Cách này cài đầy đủ phụ thuộc GR00T nên tốn đĩa hơn một client tối giản, nhưng tránh tự đoán các dependency import gián tiếp.

```bash
cd ~/projects/GR00T-WholeBodyControl
UV_PROJECT_ENVIRONMENT="$PWD/.venv_inference" \
  uv sync --project ../Isaac-GR00T --python 3.12

uv pip install --python .venv_inference/bin/python \
  -e gear_sonic pin pyzmq msgpack msgpack-numpy tyro 'opencv-python<4.13'

.venv_inference/bin/python -c "from gr00t.policy.server_client import PolicyClient; import pinocchio, cv2, gear_sonic; print('Client imports OK')"
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py --help
.venv_inference/bin/python gear_sonic/scripts/run_vla_inference.py --help
```

Không chạy lại `uv sync` cho client mỗi lần khởi động: sync có thể loại các gói WBC vừa thêm. Nếu đã sync lại, chạy lại lệnh `uv pip install` ngay trên.

Có ba môi trường: Isaac-GR00T `.venv` (server), WBC `.venv_inference` (client), WBC `.venv_sim` (MuJoCo). Lệnh chạy bên dưới gọi Python đúng môi trường, không phụ thuộc venv đang activate.

## 9. Tải SONIC và CloudWalk v10

### 9.1. SONIC

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python download_from_hf.py
ls gear_sonic_deploy/policy/release/model_encoder.onnx \
   gear_sonic_deploy/policy/release/model_decoder.onnx \
   gear_sonic_deploy/policy/release/observation_config.yaml
```

Lệnh mặc định tải controller và planner phục vụ deploy. Không thêm `--training`: phần này không cần dataset huấn luyện. Dùng controller mặc định làm baseline; không tự đổi sang `--sonic-v1-1` chỉ vì mới hơn, vì motion token phụ thuộc controller được dùng khi tạo dữ liệu. Revision SONIC do script/manifest quản lý, hướng dẫn không khẳng định mọi artifact upstream đã được pin theo byte.

### 9.2. Chỉ tải checkpoint-30000 của v10

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-371ep-v10-finetune',
    revision='f980fd880c92b984d65dcc3f9dc82b98bc8009c0',
    local_dir='checkpoints/cloudwalk_g1_bottle_v10',
    allow_patterns=['checkpoint-30000/**', 'README.md'],
)
PY
```

Kiểm tra đủ shard trọng số:

```bash
.venv_inference/bin/python - <<'PY'
import json
from pathlib import Path
p = Path('checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000')
for name in ('config.json', 'processor_config.json', 'statistics.json',
             'embodiment_id.json', 'model.safetensors.index.json'):
    assert (p/name).is_file(), f'Thieu {name}'
index = json.loads((p/'model.safetensors.index.json').read_text())
for name in sorted(set(index['weight_map'].values())):
    assert (p/name).is_file() and (p/name).stat().st_size > 0, f'Thieu shard {name}'
    print(name, (p/name).stat().st_size)
print('Du file theo index; day khong phai kiem tra checksum tung tensor.')
PY
```

Checkpoint được chọn là v10/371ep/30000, khác v6/502ep. Theo [model card CloudWalk](https://huggingface.co/cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-371ep-v10-finetune), đây là policy gắp chai tay phải, dùng embodiment `UNITREE_G1_SONIC`, action gồm motion token và khớp tay. Model không cung cấp trực tiếp tọa độ XYZ chai cho người dùng.

## 10. Chạy policy server — Terminal 1

Kiểm tra cổng trước khi nạp model:

```bash
ss -ltnp 'sport = :5550'
```

Nếu đã có server đúng model chạy ở 5550, dùng server đó. Nếu cần thay model, dừng đúng server cũ bằng Ctrl+C trong terminal của nó rồi mới chạy. Không khởi động hai server cùng cổng.

```bash
cd ~/projects/Isaac-GR00T
.venv/bin/python gr00t/eval/run_gr00t_server.py \
  --model-path "$HOME/projects/GR00T-WholeBodyControl/checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000" \
  --embodiment-tag UNITREE_G1_SONIC \
  --device cuda:0 \
  --host 127.0.0.1 \
  --port 5550
```

Lần đầu có thể tải thêm Cosmos/processor. Chờ log server sẵn sàng và không có traceback; riêng dòng `Loading checkpoint shards: 100%` chưa chứng minh server đã bind cổng thành công.

Nếu thiếu RAM/VRAM khi nạp, trước hết kiểm tra `nvidia-smi`. Tùy chọn giảm cấp phát FP32 trung gian: trong `Isaac-GR00T/gr00t/policy/gr00t_policy.py`, thay đúng dòng:

```python
model = AutoModel.from_pretrained(model_dir)
```

bằng:

```python
model = AutoModel.from_pretrained(
    model_dir, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True
)
```

Đây là sửa tương thích bộ nhớ tùy chọn, không phải code giao diện; giữ nguyên lệnh `model.to(... dtype=torch.bfloat16)` phía sau. `torch_dtype` có thể phát cảnh báo deprecated ở phiên bản này; cảnh báo không đồng nghĩa suy luận thất bại. BF16 không bảo đảm model vừa mọi GPU.

## 11. Chạy mô phỏng upstream nguyên gốc — Terminal 2

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim \
  --policy-host 127.0.0.1 \
  --policy-port 5550 \
  --no-data-exporter \
  --prompt "grab the bottle"
```

Launcher tạo tmux chạy C++ controller, keyboard publisher, VLA client và một cửa sổ tmux cho MuJoCo/camera. Lần đầu TensorRT tạo engine có thể lâu hơn các lần sau.

Thao tác theo [hướng dẫn VLA upstream](https://nvlabs.github.io/GR00T-WholeBodyControl/tutorials/vla_inference.html):

1. Chờ các thành phần khởi động, kiểm tra pane nào có traceback.
2. Trong pane C++ deploy, nhấn Enter nếu có yêu cầu xác nhận.
3. Chuyển sang pane Keyboard Publisher, nhấn `k` bật điều khiển.
4. Nhấn `i` chuyển và blend về tư thế ban đầu; chờ hoàn tất.
5. Nếu robot còn được dây đàn hồi giữ, nhấn `9` trong cửa sổ MuJoCo để bật/tắt dây khi controller đã sẵn sàng.
6. Trong Keyboard Publisher, nhấn `p` để bỏ pause suy luận.
7. Nhấn `p` để pause suy luận, `k` để ngừng controller khi cần.

Các phím keyboard publisher phải gửi đúng pane, không gõ vào terminal server. `9` thuộc viewer MuJoCo, không phải nút Start của giao diện tùy chỉnh.

Dùng `Ctrl+B` rồi `w` chọn cửa sổ tmux; `Ctrl+B` rồi phím mũi tên chuyển pane. `Ctrl+B` rồi `d` chỉ detach, các tiến trình vẫn chạy. Xem và vào lại phiên:

```bash
tmux list-sessions
tmux attach -t sonic_inference
```

Kết quả kiểm tra thành công ở phạm vi hướng dẫn: cửa sổ G1 mở; C++ nhận state; client nhận ảnh và phản hồi policy; robot thực thi khi bỏ pause. **Không dùng việc tay chuyển động làm bằng chứng robot đã nhận diện/gắp đúng chai.** Cảnh gốc thiếu cấu hình bài gắp chai đã làm riêng.

## 12. Khởi động lại những lần sau

Không cần clone, build hoặc cài môi trường lại. Chạy Terminal 1 ở mục 10 nếu server chưa chạy, rồi Terminal 2 ở mục 11.

Để dừng hẳn simulation, pause/ngừng điều khiển rồi kết thúc đúng phiên tmux sau khi kiểm tra tên:

```bash
tmux list-sessions
tmux kill-session -t sonic_inference
```

Lệnh này kết thúc tất cả process thuộc phiên đó. Server ở Terminal 1 dừng riêng bằng Ctrl+C. Không dùng `tmux kill-server` vì có thể đóng các job khác.

## 13. Lỗi thường gặp

| Hiện tượng | Cách kiểm tra |
|---|---|
| `Address already in use ...5550` | `ss -ltnp 'sport = :5550'`; dùng server cũ hoặc dừng đúng process cũ. Nếu đổi sang 5551, đổi cả server `--port` và launcher `--policy-port`. |
| `torch_dtype` / `compute_dtype` FutureWarning | Cảnh báo API; tìm traceback cuối log trước khi kết luận lỗi. |
| `401`, `403`, `GatedRepoError` | Kiểm tra quyền Cosmos và tài khoản HF dùng trong WSL. |
| Python 3.10 không cài được GR00T | Dùng cách tạo `.venv_inference` Python 3.12 ở mục 8. |
| Không tìm `PolicyClient`, `pinocchio` | Kiểm tra đúng Python của client và chạy các import check ở mục 8. |
| `NvInfer.h` / `libnvinfer.so` không tìm thấy | Kiểm tra TensorRT_ROOT, SDK 10.13, source setup_env.sh và build lại. |
| XML/mesh lỗi hoặc file chỉ vài dòng LFS pointer | Chạy lại `git lfs pull --exclude='motionbricks/out/**'` trong WBC. |
| Không có cửa sổ MuJoCo | Kiểm tra WSLg, DISPLAY, `glxinfo -B`, driver Windows; không tự đặt DISPLAY ngẫu nhiên. |
| Robot đứng im | Kiểm tra `k`, `i`, `p` đúng pane, client không pause, camera và state đang có dữ liệu. |
| Tay chuyển động nhưng không gắp | Chưa thể kết luận detector lỗi; kiểm tra cảnh, phân phối ảnh, schema tay và SONIC đúng với checkpoint. Bài gắp hoàn chỉnh ngoài phạm vi bản gốc này. |
| GPU OOM / WSL bị kill | Xem `nvidia-smi`, RAM/đĩa; tránh hai server, xem tùy chọn BF16 mục 10. |
| Không có `--sim-assisted-pickup` hoặc `--sim-native-inspire` | Đúng với bản upstream đã chốt; đây là flag của code tùy chỉnh, không dùng trong hướng dẫn này. |

Không cần cài YOLO, camera phần cứng, ROS2, Isaac Sim hoặc tải training dataset để hoàn thành các bước trên.
