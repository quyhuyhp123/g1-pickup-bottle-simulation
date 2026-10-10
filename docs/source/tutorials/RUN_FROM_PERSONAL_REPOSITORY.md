# Chạy G1 pickup/place từ repository quyhuyhp123

Repository: https://github.com/quyhuyhp123/g1-pickup-bottle-simulation

Tài liệu dành cho **người clone repository này lần đầu**. Code simulation đã
được chỉnh sẵn; không áp lại bản vá WBC trong tài liệu lịch sử. Repository chỉ
chứa code/config/tài liệu, còn mesh, thư viện nhị phân và model tải riêng.

Nếu đã chạy được ở `~/projects/GR00T-WholeBodyControl`, không cần cài lại hay
xóa môi trường đó. Các bước dưới tạo một thư mục mới tên
`~/projects/g1-pickup-bottle-simulation`.

## 1. Phạm vi và kết quả

Đây là **MuJoCo**, không phải Isaac Sim. Isaac-GR00T là policy server.
Chế độ chạy đã kiểm thử dùng **RGB-D/IK hỗ trợ, pelvis cố định**. GR00T vẫn
nhận ảnh/trạng thái và trả dự đoán, nhưng không được mô tả kết quả này là
checkpoint tự thực hiện toàn bộ gắp/đặt. SONIC dùng token đứng; bộ hỗ trợ
điều khiển eo, tay phải và ngón. Chai được nâng bằng tiếp xúc vật lý, không weld vào tay.
`--inspire-ftp-hands` dùng adapter lệnh bàn tay; mô hình MuJoCo vẫn là Dex3,
không phải triển khai bàn tay Inspire FTP nguyên bản.

Có: Start/Reset; vị trí chai X/Y; tọa độ tay và detector; gắp/nâng; nhập đích
đặt xuống; mở tay; thu tay; Start gắp tiếp không Reset; camera trực tiếp +
khung YOLO 2 Hz. Z theo mặt bàn. Đây là bài mô phỏng với vùng làm việc hữu hạn,
không bảo đảm mọi điểm trên bàn đều tới được.

Hướng dẫn được đối chiếu với workspace đang chạy. **Chưa cài lại từ đầu trên
một máy Windows sạch**; phiên bản driver/GPU có thể yêu cầu xử lý riêng.
Các kiểm thử vật lý dùng đầu vào nhận diện có kiểm soát; không đồng nghĩa
mọi vị trí đều đã thử với YOLO trực tiếp.

## 2. Windows, WSL và GPU

Máy tham chiếu: Ubuntu **22.04.5 LTS** trong WSL2, CUDA Toolkit **12.4**;
Python simulator 3.10, inference/server 3.12. GPU CUDA cần đủ VRAM cho model,
TensorRT và render đồng thời; phiên làm việc trước dùng GPU 12 GB, không coi
đó là bảo đảm cho mọi máy. Dự trù trên 100 GB trống nếu cài đủ các môi trường,
model và cache; tránh tải dataset huấn luyện không dùng.

PowerShell **Administrator**:

```powershell
wsl --install -d Ubuntu-22.04
# Khởi động lại Windows nếu được yêu cầu, tạo tài khoản Ubuntu.
wsl --update
wsl --set-default-version 2
wsl -l -v
```

Cài NVIDIA driver hỗ trợ WSL trên **Windows**. Không cài Linux NVIDIA display
driver vào WSL. WSLg cung cấp cửa sổ Linux; dùng Windows/WSL cập nhật.
Xem nguồn chính thức: [Microsoft — Install WSL](https://learn.microsoft.com/en-us/windows/wsl/install),
[Microsoft — GUI apps](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps),
[NVIDIA — CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html).

Trong Ubuntu:

```bash
nvidia-smi
printf '%s\n' "$DISPLAY" "$WAYLAND_DISPLAY"
sudo apt update
sudo apt install -y git git-lfs curl wget build-essential cmake ninja-build \
  pkg-config tmux unzip python3-dev python3-tk libgl1 libegl1 libglfw3 \
  libglib2.0-0 ffmpeg
mkdir -p ~/projects
cd ~/projects
git lfs install
```

Lưu dự án trong `~/projects` của Linux, tránh chạy môi trường Python/build
trong `/mnt/c` để giảm I/O: [Microsoft — WSL development environment](https://learn.microsoft.com/en-us/windows/wsl/setup/environment).
Nếu dùng VS Code, mở bằng `code .` trong WSL và chọn interpreter tương ứng.

## 3. Clone repository của tác giả và tải tài nguyên runtime

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/quyhuyhp123/g1-pickup-bottle-simulation.git
cd g1-pickup-bottle-simulation
python3 install_scripts/download_runtime_assets.py
```

Không chạy `git lfs pull` ở repository này. Script đọc
`runtime_assets_manifest.json`, tải tài nguyên từ upstream được pin commit và
kiểm tra SHA256. Mặc định chỉ tải nhóm runtime/simulation; không thêm `--all`
nếu không cần các demo/training khác. Chạy lại sẽ bỏ qua file đã đúng checksum.
Nếu lỗi mạng/404/checksum, dừng để xử lý, không bỏ qua mesh/thư viện rồi chạy tiếp.
Script này chưa thay việc tải SONIC ONNX, GR00T và YOLO ở mục 7.

## 4. Isaac-GR00T server: clone và áp bản vá BF16

Đặt Isaac-GR00T cạnh repository simulation:

```bash
cd ~/projects
git clone https://github.com/NVIDIA/Isaac-GR00T.git
cd Isaac-GR00T
git checkout 51d4c89f72fda44cbf77285c6a8114b52676b8a1
cd ../g1-pickup-bottle-simulation
```

Nếu thư mục Isaac-GR00T đã có và đang dùng, kiểm tra phiên bản/thay đổi trước
khi checkout; không ghi đè môi trường đang làm việc. Có thể bố trí hai repo
trong một thư mục cha khác để tránh xung đột, miễn chúng vẫn cạnh nhau.

Trích **chỉ bản vá GR00T** đã có trong tài liệu đi kèm repository:

```bash
python3 - <<'PYBF16'
from pathlib import Path
import hashlib
text = Path('docs/source/tutorials/WSL_BLUE_BOTTLE_COMPLETE_GUIDE.md').read_text()
prefix = '<!-- PATCH-GR00T-BEGIN -->\n```diff\n'
payload = text.split(prefix, 1)[1].split('```\n<!-- PATCH-GR00T-END -->', 1)[0]
expected = text.split('SHA256-GR00T: `', 1)[1].split('`', 1)[0]
assert hashlib.sha256(payload.encode()).hexdigest() == expected
Path('/tmp/gr00t-bf16.patch').write_text(payload)
PYBF16
git -C ../Isaac-GR00T apply --check /tmp/gr00t-bf16.patch
git -C ../Isaac-GR00T apply /tmp/gr00t-bf16.patch
```

Chỉ áp một lần trên phiên bản server đã pin. Bản vá nạp model thẳng BF16 để
tránh cấp phát FP32 tạm. Không cần chỉnh lại code WBC/Dex3/IK vì repository
cá nhân đã chứa tất cả chức năng này.

## 5. CUDA, TensorRT và C++ SONIC

C++ deploy cần CUDA Toolkit riêng, không chỉ Torch CUDA wheel. Cài CUDA Toolkit
12.4 theo hướng dẫn WSL của NVIDIA; chọn **toolkit-only**, không chọn gói
`cuda`, `cuda-12-x` hoặc `cuda-drivers` kéo Linux driver vào WSL.
Tải TensorRT **10.13 x86_64 TAR** tương thích CUDA theo yêu cầu của commit WBC
này và giải nén vào `~/TensorRT`. Đây là SDK C++ khác với gói TensorRT Python
mà Isaac-GR00T có thể cài phiên bản khác trong venv.

```bash
export CUDA_HOME=/usr/local/cuda
export PATH="$CUDA_HOME/bin:$PATH"
export TensorRT_ROOT="$HOME/TensorRT"
export LD_LIBRARY_PATH="$TensorRT_ROOT/lib:$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
nvcc --version
ls "$TensorRT_ROOT/include/NvInfer.h" "$TensorRT_ROOT/lib/libnvinfer.so"
cd ~/projects/g1-pickup-bottle-simulation/gear_sonic_deploy
bash scripts/install_deps.sh
source scripts/setup_env.sh
just build
cd ..
```

Nếu `just` chưa có, cài theo công cụ được nêu trong README/install_deps của
repo trước khi build. Không sao chép TensorRT engine từ GPU khác; build lại
trên GPU đích. Không chạy `deploy.sh` không tham số: mặc định script có thể là
robot thật; toàn bộ hướng dẫn này chỉ dùng launcher **`--sim`** và loopback.

## 6. Các môi trường Python

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
cd ~/projects/Isaac-GR00T
uv sync --python 3.12
cd ../g1-pickup-bottle-simulation
bash install_scripts/install_mujoco_sim.sh
```

Script simulator tạo `.venv_sim` Python 3.10 và cài Unitree SDK. Các script
install có thể **xóa và tạo lại venv cùng tên**; chỉ chạy lúc setup, không chạy
mỗi lần mô phỏng. Máy mới cần Internet để tải Python/packages.

Để không để dependency `gr00t @ git+...` lấy HEAD khác phiên bản server,
tạm pin URL trong pyproject trước khi cài inference:

```bash
python3 - <<'PYPIN'
from pathlib import Path
p = Path('gear_sonic/pyproject.toml')
s = p.read_text().replace(
    'gr00t @ git+https://github.com/NVIDIA/Isaac-GR00T.git"',
    'gr00t @ git+https://github.com/NVIDIA/Isaac-GR00T.git@51d4c89f72fda44cbf77285c6a8114b52676b8a1"')
p.write_text(s)
PYPIN
bash install_scripts/install_inference.sh
bash install_scripts/install_bottle_detector.sh
# scipy cần cho IK; kiểm tra cả simulator và inference.
.venv_sim/bin/python -c 'import mujoco, scipy, tkinter; print(mujoco.__version__)'
.venv_inference/bin/python -c 'import torch, cv2, ultralytics; print(torch.__version__, torch.cuda.is_available())'
../Isaac-GR00T/.venv/bin/python -c 'import torch; print(torch.__version__, torch.cuda.is_available())'
```

YOLO installer dùng `--no-deps` để tránh nâng Torch của môi trường hiện có.
Trên máy mới nếu thiếu dependency, đối chiếu metadata `ultralytics` và cài
gói thiếu trong `.venv_inference`, không nâng toàn bộ Torch/NumPy tùy ý.
Workspace tham chiếu: Torch **2.9.0+cu128**, NumPy **1.26.4**, SciPy **1.15.3**,
OpenCV **4.11.0.86**, Ultralytics **8.4.174**. Phiên bản này là số đo môi trường,
không phải lockfile toàn bộ dependencies.

## 7. Tải model

Từ thư mục g1-pickup-bottle-simulation, tải ONNX/planner SONIC, không tải training dataset:

```bash
.venv_inference/bin/python download_from_hf.py
.venv_inference/bin/python - <<'PYMODEL'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-371ep-v10-finetune',
    revision='f980fd880c92b984d65dcc3f9dc82b98bc8009c0',
    local_dir='checkpoints/cloudwalk_g1_bottle_v10',
    allow_patterns=['checkpoint-30000/**', 'README.md'],
)
PYMODEL
.venv_inference/bin/python gear_sonic/scripts/check_cloudwalk_checkpoint.py \
  checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000
```

YOLO11n tải bằng `install_bottle_detector.sh`. Nếu HF yêu cầu quyền, đăng nhập
bằng tài khoản có quyền và chấp nhận license; không gửi token trong tài liệu.
Checkpoint hiện tại là **v10, 371ep, checkpoint-30000**, không phải v6/502ep.
Script tải SONIC của upstream lấy release hiện tại; để tái lập từng byte
ONNX cần lưu revision/model manifest riêng. Tài liệu pin nguồn code và v10,
không khẳng định đã pin mọi artifact upstream.

## 8. Chạy

Terminal 1 (thư mục g1-pickup-bottle-simulation):

```bash
bash gear_sonic/scripts/run_cloudwalk_policy_server.sh
```

Chờ server sẵn sàng. Patch BF16 trong phụ lục giảm cấp phát FP32 tạm khi nạp
model; không loại bỏ nhu cầu VRAM. Terminal 2:

```bash
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter --inspire-ftp-hands \
  --sim-assisted-pickup --sim-fixed-base \
  --prompt "grab the bottle"
```

Có thể thêm `--sim-bottle-xy 0.43 -0.11`. Không thay hai flag assisted/fixed-base
bằng `--sim-grasp-distance`: đó chỉ là ngưỡng khép tay của chế độ cũ.

## 9. Thao tác giao diện

1. Khi mở: robot giữ tư thế, chưa tự gắp. Không cần bấm 9.
2. X/Y ban đầu → Apply X/Y / Reset bottle để dựng chai. Z theo bàn.
3. Start GR00T → chờ nhận diện, tiếp cận, nắm, nâng (`success`).
4. Nhập **Place destination X/Y** (ví dụ 0.45, -0.05).
5. Lower / Place on table → chuyển ngang → hạ → mở tay → lùi → thu tay.
6. Khi `complete`, Start sáng lại. Bấm để nhận diện chai tại vị trí mới và gắp
   tiếp. Không Reset nên chai không dịch về ban đầu.
7. Reset robot + bottle ngắt lượt, xóa mục tiêu/lệnh cũ, đưa robot về tư thế
   ban đầu và dựng chai tại X/Y ban đầu đã chọn. F5 Reset, F6 Start, F2 mở panel.

Tâm chai ban đầu Z khoảng 0.801 m; mặt bàn 0.700 m. X/Y thế giới, đơn vị mét.
Bàn có giới hạn X 0.276..0.724, Y -0.424..0.424 m nhưng tầm tay nhỏ hơn.
Sai số xác nhận đặt dưới 2.5 cm. Hạ dò 3 mm/s tối đa 2 cm nếu chưa tiếp xúc bàn.
YOLO là detector riêng; checkpoint không xuất XYZ chai. Không nhầm tọa độ
bề mặt YOLO với tâm chai MuJoCo. Điểm xanh là tâm vùng nắm, không phải đầu ngón.
Camera góc phải nhận ảnh trực tiếp, khung YOLO 2 Hz có tuổi kết quả riêng,
tự ẩn khi quá 750 ms. Giảm Hz giảm tải, không làm detector đo nhanh hơn.

## 10. Kiểm tra và xử lý lỗi

```bash
ss -ltnp 'sport = :5550'
tmux list-sessions
tmux attach -t sonic_inference
.venv_sim/bin/python -m unittest \
  gear_sonic.tests.test_assisted_pickup \
  gear_sonic.tests.test_simulation_controls \
  gear_sonic.tests.test_viewer_overlay \
  gear_sonic.tests.test_async_camera
```

| Hiện tượng | Kiểm tra / xử lý |
|---|---|
| Tay đưa ra nhưng không nâng | Lệnh phải có assisted-pickup và fixed-base; xem stage/error |
| Start không hoạt động | Server 5550, C++/SONIC ready, camera mới; đọc tmux inference/sim |
| Hạ rồi giữ nguyên | Không có lực đỡ bàn hoặc IK ngoài tầm; xem error, chọn đích gần hơn |
| Đặt xong muốn gắp tiếp | Chờ complete; Start, không Reset |
| Không thấy nút mới | Đóng phiên cũ và chạy lại launcher để nạp code mới |
| CUDA OOM | Kiểm tra nvidia-smi, model BF16, các tiến trình GPU khác |
| Không có GUI | Kiểm tra WSLg/DISPLAY và driver Windows, không tự đặt DISPLAY ngẫu nhiên |
| Preview stale | Xem camera process, EGL và tải CPU/GPU; tuổi YOLO khác tuổi camera |
| Build không tìm NvInfer | Kiểm tra TensorRT_ROOT, CUDA, source setup_env.sh |
| Dung lượng tăng | venv, HF/uv cache, CUDA/TensorRT và model chiếm lớn; không xóa model đang dùng |

Các test camera cần socket localhost/EGL; môi trường sandbox có thể chặn,
không nên kết luận lỗi robot chỉ từ PermissionError của socket.
Không dùng kết quả simulator để suy ra an toàn triển khai robot thật.

## 11. Cập nhật repository và chia sẻ

Để nhận code mới, dừng simulation rồi chạy `git pull` trong bản clone cá nhân.
Nếu có chỉnh sửa local, kiểm tra `git status` trước; không tự reset/xóa thay đổi.
Cập nhật thường không cần cài lại venv hoặc tải model. Chỉ cài lại dependencies
khi pyproject/install scripts thay đổi và hướng dẫn release yêu cầu.

Nếu bạn là chủ repository và muốn đăng tài liệu này từ bản export hiện tại:

```bash
cd ~/projects/GR00T-WholeBodyControl/share_code_only
git add README.md docs/source/tutorials/RUN_FROM_PERSONAL_REPOSITORY.md
git commit -m "Document setup and operation from personal repository"
git push origin main
```

Đây là đường dẫn trên máy tác giả; người clone chỉ cần đọc hướng dẫn, không
cần thư mục share_code_only. Không chạy các script install mỗi lần mở robot:
chúng có thể xóa và tạo lại venv.

## 12. Tài liệu liên quan

- [Điều khiển simulation](simulation_controls.md): các nút và ý nghĩa tọa độ.
- [Bản ghi đầy đủ thay đổi/code](WSL_BLUE_BOTTLE_COMPLETE_GUIDE.md): phụ lục patch
  lịch sử. Không áp WBC patch vào repository cá nhân lần nữa.
- [README upstream](../../../UPSTREAM_README.md): bối cảnh dự án NVIDIA gốc.

Repository cá nhân giữ license/ghi nhận nguồn upstream. Hướng dẫn này chưa
được kiểm chứng bằng một lượt cài Windows sạch; bản simulator đang chạy và các
kiểm thử là bằng chứng chức năng, không thay cho kiểm thử cài mới trên mọi GPU.
