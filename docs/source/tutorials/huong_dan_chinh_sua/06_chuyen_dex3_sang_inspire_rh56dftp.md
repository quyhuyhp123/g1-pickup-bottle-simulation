# Bước 6 — Đổi Dex3 sang bàn tay Inspire RH56DFTP trong MuJoCo

Thực hiện sau [bước 5: đặt chai, thu tay và gắp lại](05_dex3_dat_chai_thu_tay_gap_lai.md).
Giữ chu trình đang sử dụng, thay model bàn tay và phần điều khiển ngón cho phù hợp
với Inspire FTP. Đây là tài liệu có bản vá để áp trên bản clone đi theo các bước;
việc tạo tài liệu này không tự thay code, khởi động simulator hay kết nối robot thật.

## 1. Mục tiêu và phạm vi

Sau bước này có thể chọn một trong hai model khi khởi động:

| Lựa chọn | Thân | Motor bàn tay | Tổng actuator |
|---|---:|---:|---:|
| Dex3, mặc định của bước 1–5 | 29 | 7 mỗi tay | 43 |
| Inspire FTP, thêm ở bước 6 | 29 | 6 mỗi tay | 41 |

Model Inspire còn có **12 khớp phụ mimic**, không có motor riêng. Với robot và
chai đều có free joint, model native có `njnt = 55`; đây không phải 55 motor.

Những chức năng giữ lại:

- Khởi động ở tư thế chờ dưới đất; Start mới bắt đầu chu trình.
- Nhập tọa độ chai, Apply và Reset.
- YOLO RGB-D xác định mục tiêu; IK đưa tâm vùng nắm đến chai.
- Khép tay, nâng, giữ; Lower đặt xuống XY được nhập.
- Bàn đỡ chai trước khi mở ngón; thu tay về và bật Start để gắp lượt tiếp.

**Bước này vẫn là chế độ có hỗ trợ RGB-D/IK, pelvis cố định.** Nó không khôi phục
quyền điều khiển động tác cho checkpoint GR00T v10. Như bước 4–5, client vẫn gọi
server nhưng thay action dự đoán bằng token đứng và lệnh tay trung tính trong chế
độ hỗ trợ; controller MuJoCo thực hiện chuyển động gắp/đặt tương ứng.

Không dùng kết quả này để kết luận v10 đã được ánh xạ chính xác sang Inspire hoặc
đã chạy được trên robot thật. Hướng GR00T/SONIC điều khiển chính sẽ là thay đổi khác.

## 2. Model bàn tay lấy từ đâu?

Dùng mô tả G1 có sẵn bàn tay FTP trong repository chính thức
[Unitree Robotics — unitree_ros](https://github.com/unitreerobotics/unitree_ros).

- Commit cố định: `5994d4faef0a9cadd3287f8de0199a67eeb2a259`.
- URDF: `robots/g1_description/g1_29dof_rev_1_0_with_inspire_hand_FTP.urdf`.
- [Đọc trực tiếp URDF tại commit này](https://raw.githubusercontent.com/unitreerobotics/unitree_ros/5994d4faef0a9cadd3287f8de0199a67eeb2a259/robots/g1_description/g1_29dof_rev_1_0_with_inspire_hand_FTP.urdf).
- SHA256 URDF: `63097d7366e1903b595c6adbdb187b205f5c1b1189088ca5aea32d25622415cb`.

Script chỉ tải URDF và các mesh mà URDF tham chiếu, không clone toàn bộ repository
Unitree và không tải lại checkpoint v10/YOLO. Bộ nguồn đã kiểm tra tại máy này có
94 file, khoảng 44,55 MiB, chưa tính XML sinh ra. `source.json` ghi revision và
SHA256 các file để đối chiếu.

Đây là model FTP do Unitree tích hợp, dùng làm mô hình gần với cấu hình
RH56DFTP-2R/2L người dùng có. Tên FTP không chứng minh hình học, firmware hoặc
calibration đã khớp hoàn toàn phần cứng cụ thể. Mesh cảm biến và contact vật lý
không tự tạo SDK đọc 17 cảm biến xúc giác trên bàn tay thật.

## 3. Vì sao không thể chỉ thay XML?

### 3.1. Sáu motor và các khớp phụ

Thứ tự motor native mà bộ điều khiển dùng cho **mỗi tay**:

```python
HAND_NAMES = ('thumb_1', 'thumb_2', 'index_1', 'middle_1', 'ring_1', 'little_1')
```

Đọc motor theo tên joint và tìm slot actuator qua `actuator_trnid`. Không lấy
`joint_id - 1`: khớp phụ có joint ID nhưng không có actuator, nên cách đó có thể
ghi nhầm motor hoặc vượt kích thước mảng. Tương tự, đọc `qpos/qvel` qua
`jnt_qposadr/jnt_dofadr`, không dựa vào offset của Dex3.

### 3.2. Tâm vùng nắm và tư thế ban đầu

Native model tạo site `right_hand_grasp_center` tại `[0.165, 0.045, 0]` trong hệ
`right_wrist_yaw_link`. Tay trái dùng `[0.165, -0.045, 0]`. Đây là điểm tham chiếu
vùng nắm được hiệu chỉnh cho controller này, không phải COM khối lượng.

Các số này ở **hệ cổ tay**, không phải tọa độ world của chai. Đừng sao chép nguyên
site Dex3 `[0.12, 0.05, 0]` hoặc dùng cùng vector ngón cho hai loại bàn tay.
Marker xanh thuộc site group 5; camera nhận diện mặc định không vẽ marker này.

Tư thế native chờ đặt shoulder pitch = `0.35`, elbow = `-0.7`, thumb opposition
= `1.0` rad ở cả hai bên. Bộ giữ tư thế và Reset dùng cấu hình native này.

### 3.3. Khép/mở và tránh quệt chai lúc nhả

Mục tiêu motor thử nghiệm trong simulation, đơn vị rad:

```python
opened = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
closed = [1.0, 0.5, 0.95, 0.95, 0.95, 0.95]
```

Motor opposition giữ preshape khi nhả; năm motor còn lại mở dần. Khi chai được
bàn đỡ, bàn tay dịch lùi khoảng `[-0.05, -0.02, 0]` m đồng thời duỗi ngón, sau đó
mới thực hiện retreat và return home. Cách này tránh quệt chai bằng các ngón đang
duỗi của FTP. Lift vẫn yêu cầu contact ở các phía đối diện và chai thực sự đi lên.

Đây là góc mô phỏng, không phải giá trị thanh ghi hoặc lệnh SDK cho bàn tay thật.

### 3.4. Schema VLA vẫn đang tương thích Dex3

Camera gửi trạng thái thật của 6 motor với nhãn:

```python
state['hand_state_format'] = 'inspire_ftp_motor_radians'
```

Client chuyển **observation** thành 7 giá trị gần đúng để giữ schema cũ hoạt động.
Đây là phép chiếu tương thích cho simulation, không phải mapping chính thức của
dataset CloudWalk; không có chiều chuyển lệnh Dex3 → native Inspire trong bản vá.

`NUM_HAND_MOTORS=0` vô hiệu hóa số motor bàn tay mà bridge Dex3 xử lý, không có
nghĩa model vật lý thiếu motor. Controller local vẫn điều khiển đủ 12 motor native.
Client lấy trạng thái tay native ghép cùng frame camera để chuyển schema; dữ liệu
hand trên topic Dex3 cũ không được dùng làm phản hồi native đã hiệu chuẩn.

## 4. Danh sách file cần thêm/sửa sau bước 5

| Loại | File | Nội dung |
|---|---|---|
| Thêm | `gear_sonic/scripts/prepare_inspire_ftp_sim.py` | Tải model cố định revision, chuyển URDF sang preview/runtime XML |
| Thêm | `gear_sonic/scripts/run_inspire_ftp_sim.py` | Preview đóng/mở tay riêng, không server/DDS |
| Thêm | `gear_sonic/utils/mujoco_sim/inspire_hand.py` | Chiếu observation 6 motor sang schema Dex3 cũ |
| Sửa | `gear_sonic/utils/mujoco_sim/configs.py` | Cờ `native_inspire` |
| Sửa | `gear_sonic/scripts/run_sim_loop.py` | Chọn runtime scene 41 actuator và cấu hình hand bridge |
| Sửa | `gear_sonic/scripts/launch_inference.py` | Cờ `--sim-native-inspire`, kiểm tra file và chuyển cờ cho sim |
| Sửa | `gear_sonic/utils/mujoco_sim/base_sim.py` | Index motor/địa chỉ trạng thái, giới hạn lực, native standby, metadata camera |
| Sửa | `gear_sonic/utils/mujoco_sim/dex3_pickup.py` | Nhận cả Dex3/FTP, góc ngón và chuyển động nhả phù hợp |
| Sửa | `gear_sonic/utils/mujoco_sim/dex3_controls.py` | Chấp nhận cả scene 43 và 41 actuator |
| Sửa | `gear_sonic/scripts/run_vla_inference.py` | Đọc nhãn native, đổi observation trước khi xử lý schema cũ |
| Thêm | `gear_sonic/tests/test_inspire_ftp_model.py` | Topology, inertia, đóng/mở độc lập hai tay |
| Thêm | `gear_sonic/tests/test_native_inspire_guide.py` | Gắp/giữ/đặt/thu/gắp lại, Reset và observation native |

Tên `Dex3Pickup` và `dex3_controls.py` được giữ để patch nối tiếp bước 5; từ bước
này chúng chấp nhận cả hai model. Không cần đổi tên file hoặc sửa C++ ở bước 6.
C++ và checkpoint vẫn nằm trong phạm vi chế độ hỗ trợ đã giải thích ở trên.

Không sửa `scene_43dof.xml` hoặc ghi đè `g1_29dof_with_hand.xml`. Script tạo model
native riêng và sao chép bàn/chai/visual từ scene bước 1 vào model đó.

## 5. Áp bản vá trên bản clone theo tuần tự bước 1–5

**Không áp lại lên workspace hiện tại nếu đã có native Inspire.** Code hiện tại
có thêm các chức năng khác so với bản tối thiểu của bộ hướng dẫn. Bản vá dưới đây
được kiểm tra với trạng thái cuối bước 5 của loạt tài liệu, không phải `main` bất kỳ.

Dừng simulator/client/C++ của bản clone sẽ sửa; server v10 đúng vẫn có thể giữ.
Lệnh sau kiểm tra patch trước, sao lưu những file sửa và áp patch. Tên backup kết
thúc `.before_step06`; không thêm các backup này vào GitHub.

```bash
cd ~/projects/GR00T-WholeBodyControl
python3 - <<'PYAPPLY'
from pathlib import Path
import re
import shutil
import subprocess

document = Path('docs/source/tutorials/huong_dan_chinh_sua/06_chuyen_dex3_sang_inspire_rh56dftp.md').read_text()
begin = '<!-- STEP06-PATCH-BEGIN -->' + '\n```diff\n'
end = '\n```\n<!-- STEP06-PATCH-END -->'
patch = document.split(begin, 1)[1].split(end, 1)[0] + '\n'
subprocess.run(['git', 'apply', '--check', '-'], input=patch, text=True, check=True)
paths = [Path(name) for name in re.findall(r'^--- a/(.+)$', patch, re.M)]
backups = [p.with_name(p.name + '.before_step06') for p in paths]
if any(p.exists() for p in backups):
    raise SystemExit('Backup already exists; inspect your previous attempt before applying again.')
for source, backup in zip(paths, backups):
    shutil.copy2(source, backup)
subprocess.run(['git', 'apply', '-'], input=patch, text=True, check=True)
print('Applied step 6. Build the native model and run tests next.')
PYAPPLY
```

Nếu patch không khớp, kiểm tra đã hoàn tất đúng bước 5 và chưa áp bước 6. Không
dùng `reset --hard`, ép patch hoặc chép đè cả thư mục code đang chạy để vượt lỗi.

<!-- STEP06-PATCH-BEGIN -->
```diff
--- /dev/null
+++ b/gear_sonic/scripts/prepare_inspire_ftp_sim.py
@@ -0,0 +1,143 @@
+"""Build a separate G1 + native Inspire FTP scene from pinned Unitree URDFs.
+
+Downloads only model descriptions/meshes. Never starts a hardware connection.
+"""
+import argparse
+from concurrent.futures import ThreadPoolExecutor
+import copy
+import hashlib
+import json
+from pathlib import Path
+import tempfile
+import urllib.request
+import xml.etree.ElementTree as ET
+
+import mujoco
+
+REVISION = '5994d4faef0a9cadd3287f8de0199a67eeb2a259'
+BASE = f'https://raw.githubusercontent.com/unitreerobotics/unitree_ros/{REVISION}/robots/g1_description/'
+ROOT = Path(__file__).resolve().parents[2]
+URDF = 'g1_29dof_rev_1_0_with_inspire_hand_FTP.urdf'
+HAND_NAMES = ('thumb_1', 'thumb_2', 'index_1', 'middle_1', 'ring_1', 'little_1')
+
+
+def download(output):
+    output.mkdir(parents=True, exist_ok=True)
+    def fetch(relative):
+        path = output / relative
+        path.parent.mkdir(parents=True, exist_ok=True)
+        if not path.exists():
+            with urllib.request.urlopen(BASE + relative, timeout=60) as response:
+                blob = response.read()
+            temporary = path.with_suffix(path.suffix + '.download')
+            temporary.write_bytes(blob)
+            temporary.replace(path)
+        return path
+    source = fetch(URDF)
+    names = sorted({Path(m.get('filename')).name for m in ET.parse(source).findall('.//mesh')})
+    with ThreadPoolExecutor(max_workers=6) as pool:
+        paths = list(pool.map(fetch, ['meshes/' + name for name in names]))
+    manifest = {'repository': 'https://github.com/unitreerobotics/unitree_ros',
+        'revision': REVISION, 'files': {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
+                                      for p in [source, *paths]}}
+    (output/'source.json').write_text(json.dumps(manifest, indent=2))
+    return source
+
+
+def build(source, output):
+    output.mkdir(parents=True, exist_ok=True)
+    urdf = ET.parse(source)
+    compiler = urdf.find('mujoco/compiler')
+    compiler.set('meshdir', str((source.parent/'meshes').resolve()))
+    # Preserve fixed palm/sensor link inertias. Fusing a fixed root into world
+    # otherwise discards its mass when a standalone hand is later attached.
+    compiler.set('fusestatic', 'false')
+    for mesh in urdf.findall('.//mesh'):
+        mesh.set('filename', Path(mesh.get('filename')).name)
+    with tempfile.TemporaryDirectory() as tmp:
+        converted = Path(tmp)/'g1.urdf'
+        urdf.write(converted)
+        imported = mujoco.MjModel.from_xml_path(str(converted))
+        mjcf = output/'g1_inspire_ftp.xml'
+        mujoco.mj_saveLastXML(str(mjcf), imported)
+    tree = ET.parse(mjcf)
+    root = tree.getroot()
+    root.set('model', 'G1 Inspire RH56DFTP - 41 active joints')
+    ET.SubElement(root, 'option', timestep='0.002', integrator='implicitfast')
+    pelvis = root.find("worldbody/body[@name='pelvis']")
+    pelvis.set('pos', '0 0 0.793')
+    ET.SubElement(pelvis, 'freejoint', name='floating_base_joint')
+    equality = root.find('equality')
+    if equality is None:
+        equality = ET.SubElement(root, 'equality')
+    # Explicit preview fixture. There is no standing/balance controller here.
+    ET.SubElement(equality, 'weld', name='preview_pelvis_fixture', body1='pelvis')
+    contact = ET.SubElement(root, 'contact')
+    for side in ('left', 'right'):
+        # Convex palm mesh overlaps the internal thumb hinge at zero angle.
+        # Exclude only this mechanical neighbour, keeping finger/object contacts.
+        ET.SubElement(contact, 'exclude', body1=side+'_base_link', body2=side+'_thumb_2')
+    actuators = ET.SubElement(root, 'actuator')
+    for joint in urdf.findall('joint'):
+        if joint.get('type') not in ('revolute', 'continuous'):
+            continue
+        name = joint.get('name')
+        mimic = joint.find('mimic')
+        if mimic is not None:
+            for old in list(equality):
+                if old.get('joint1') == name:
+                    equality.remove(old)
+            ET.SubElement(equality, 'joint', name=name+'_mimic', joint1=name,
+                joint2=mimic.get('joint'), polycoef=f"{mimic.get('offset', '0')} {mimic.get('multiplier', '1')} 0 0 0",
+                solref='0.004 1')
+        else:
+            hand = any(name == side+'_'+finger+'_joint' for side in ('left', 'right') for finger in HAND_NAMES)
+            limit = joint.find('limit')
+            effort = limit.get('effort')
+            ET.SubElement(actuators, 'position', name=name+'_act', joint=name,
+                kp='4' if hand else '150', kv='.08' if hand else '6',
+                forcelimited='true', forcerange=f'-{effort} {effort}',
+                ctrllimited='true', ctrlrange=f"{limit.get('lower')} {limit.get('upper')}")
+        mj_joint = root.find(f".//joint[@name='{name}']")
+        mj_joint.set('armature', '.001' if any(f in name for f in ('thumb', 'index', 'middle', 'ring', 'little')) else '.01')
+        mj_joint.set('damping', '.02')
+    # The hand's numerous welded tactile mesh pieces belong to one rigid link.
+    # Native MuJoCo contact filtering excludes welded bodies automatically.
+    scene = ET.parse(ROOT/'gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml').getroot()
+    for section in ('visual', 'statistic'):
+        root.append(copy.deepcopy(scene.find(section)))
+    root.find('asset').extend(copy.deepcopy(list(scene.find('asset'))))
+    root.find('worldbody').extend(copy.deepcopy(list(scene.find('worldbody'))))
+    ET.indent(tree)
+    tree.write(mjcf)
+    model = mujoco.MjModel.from_xml_path(str(mjcf))
+    if model.nu != 41 or model.njnt != 55 or model.neq != 13:
+        raise ValueError(f'Unexpected topology: {model.nu=}, {model.njnt=}, {model.neq=}')
+    # Runtime variant uses torque actuators; DefaultEnv supplies PD control.
+    runtime = copy.deepcopy(root)
+    runtime.find("equality").remove(runtime.find("equality/weld[@name='preview_pelvis_fixture']"))
+    for actuator in runtime.find('actuator'):
+        actuator.tag = 'motor'
+        for key in ('kp', 'kv', 'ctrllimited', 'ctrlrange'):
+            actuator.attrib.pop(key, None)
+    torso = runtime.find(".//body[@name='torso_link']")
+    ET.SubElement(torso, 'camera', name='head_camera', pos='0.06 0 0.45', euler='0 -0.8 -1.57')
+    for side in ('left', 'right'):
+        wrist = runtime.find(f".//body[@name='{side}_wrist_yaw_link']")
+        ET.SubElement(wrist, 'site', name=side+'_hand_grasp_center',
+                      pos='0.165 0.045 0' if side == 'right' else '0.165 -0.045 0',
+                      size='.005', rgba='0 1 0 1', group='5')
+    runtime_path = output/'g1_inspire_ftp_pickup.xml'
+    ET.indent(runtime)
+    ET.ElementTree(runtime).write(runtime_path)
+    mujoco.MjModel.from_xml_path(str(runtime_path))
+    return mjcf
+
+
+if __name__ == '__main__':
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('--output', type=Path, default=ROOT/'models/g1_inspire_ftp')
+    args = parser.parse_args()
+    source = download(args.output)
+    result = build(source, args.output)
+    print(f'Built {result}: 29 body + 12 active hand joints; 12 passive mimic joints.')
--- /dev/null
+++ b/gear_sonic/scripts/run_inspire_ftp_sim.py
@@ -0,0 +1,81 @@
+"""Preview native Inspire FTP hands on G1 (simulation only, no DDS/policy server).
+
+Space toggles both hands; L/R toggle a side; Backspace restores the scene.
+Position sliders in MuJoCo's Control panel expose all 41 active joints.
+"""
+import argparse
+from pathlib import Path
+import time
+import threading
+
+import mujoco
+import mujoco.viewer
+import numpy as np
+
+from gear_sonic.scripts.prepare_inspire_ftp_sim import HAND_NAMES, ROOT
+
+
+def initialize(model, data):
+    mujoco.mj_resetData(model, data)
+    home = {'left_shoulder_pitch_joint': -.3, 'right_shoulder_pitch_joint': -.3,
+            'left_elbow_joint': 1.1, 'right_elbow_joint': 1.1}
+    for name, value in home.items():
+        data.qpos[model.joint(name).qposadr[0]] = value
+    for i in range(model.nu):
+        joint = model.actuator_trnid[i, 0]
+        data.ctrl[i] = data.qpos[model.jnt_qposadr[joint]]
+    mujoco.mj_forward(model, data)
+
+
+def hand_actuators(model, side):
+    return np.array([model.actuator(side+'_'+name+'_joint_act').id for name in HAND_NAMES])
+
+
+def main(args):
+    if not args.scene.exists():
+        raise SystemExit('Run .venv_sim/bin/python gear_sonic/scripts/prepare_inspire_ftp_sim.py first.')
+    model = mujoco.MjModel.from_xml_path(str(args.scene))
+    data = mujoco.MjData(model)
+    initialize(model, data)
+    closed = {'left': False, 'right': False}
+    lock = threading.Lock()
+    reset = threading.Event()
+    def key(code):
+        with lock:
+            if code == 32:
+                closed['left'] = closed['right'] = not closed['right']
+            elif code in (ord('L'), ord('R')):
+                side = 'left' if code == ord('L') else 'right'
+                closed[side] = not closed[side]
+            elif code == 259:
+                reset.set()
+    print('Native Inspire FTP preview: SPACE both hands; L/R one hand; Backspace reset. Pelvis fixed.')
+    print('This preview does not connect to GR00T/SONIC or robot hardware.')
+    with mujoco.viewer.launch_passive(model, data, key_callback=key) as viewer:
+        viewer.cam.lookat[:] = [.1, 0, .9]
+        viewer.cam.distance = 2.
+        viewer.cam.azimuth = 130
+        viewer.cam.elevation = -15
+        last_view = 0.
+        while viewer.is_running():
+            start = time.monotonic()
+            with lock:
+                if reset.is_set():
+                    initialize(model, data)
+                    closed = {'left': False, 'right': False}
+                    reset.clear()
+                for side in closed:
+                    indices = hand_actuators(model, side)
+                    target = model.actuator_ctrlrange[indices, 1] * (.85 if closed[side] else 0.)
+                    data.ctrl[indices] += np.clip(target-data.ctrl[indices], -.0008, .0008)
+            mujoco.mj_step(model, data)
+            if start-last_view >= 1/60:
+                viewer.sync()
+                last_view = start
+            time.sleep(max(0., model.opt.timestep-(time.monotonic()-start)))
+
+
+if __name__ == '__main__':
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('--scene', type=Path, default=ROOT/'models/g1_inspire_ftp/g1_inspire_ftp.xml')
+    main(parser.parse_args())
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/inspire_hand.py
@@ -0,0 +1,19 @@
+"""Simulation-only compatibility for native FTP hands and the legacy Dex3 policy schema.
+
+The VLA/SONIC transport still expects seven Dex3 angles per hand. This projection
+preserves measured flexion approximately; it is NOT a calibrated CloudWalk or
+hardware Inspire observation/action mapping. The native assisted controller owns
+all six real simulated motors, and never consumes projected Dex3 commands.
+"""
+import numpy as np
+
+
+def dex3_observation_from_inspire(joints, side):
+    q = np.asarray(joints, dtype=float)
+    if q.shape != (6,) or not np.isfinite(q).all() or side not in ('left', 'right'):
+        raise ValueError('Expected six finite native Inspire motor angles and a hand side')
+    # Native order: thumb opposition, thumb flexion, index, middle, ring, little.
+    flex = np.clip(q[1:4] / np.array([.5864, 1.4381, 1.4381]), 0., 1.)
+    thumb, index, middle = flex
+    right = np.array([0., -.7*thumb, -.7*thumb, middle, 1.5*middle, index, 1.5*index])
+    return right if side == 'right' else -right
--- /dev/null
+++ b/gear_sonic/tests/test_inspire_ftp_model.py
@@ -0,0 +1,41 @@
+"""Topology/inertia and independent finger-control checks for the downloaded FTP model."""
+from pathlib import Path
+import unittest
+import mujoco
+import numpy as np
+from gear_sonic.scripts.run_inspire_ftp_sim import initialize, hand_actuators, ROOT
+
+SCENE = ROOT/'models/g1_inspire_ftp/g1_inspire_ftp.xml'
+
+@unittest.skipUnless(SCENE.exists(), 'Run prepare_inspire_ftp_sim.py to download native Inspire model')
+class InspireFTPModelTest(unittest.TestCase):
+    def test_native_topology_and_open_close(self):
+        model = mujoco.MjModel.from_xml_path(str(SCENE))
+        data = mujoco.MjData(model)
+        initialize(model, data)
+        self.assertEqual(model.nu, 41)
+        self.assertEqual(model.njnt, 55)  # 53 hinges + robot and bottle free joints
+        self.assertEqual(sum(model.eq_type == mujoco.mjtEq.mjEQ_JOINT), 12)
+        for side in ('left', 'right'):
+            self.assertAlmostEqual(float(model.body(side+'_base_link').mass[0]), .62266)
+        right = hand_actuators(model, 'right')
+        left = hand_actuators(model, 'left')
+        right_q = model.jnt_qposadr[model.actuator_trnid[right, 0]]
+        left_q = model.jnt_qposadr[model.actuator_trnid[left, 0]]
+        for step in range(3000):
+            target = model.actuator_ctrlrange[right, 1]*.5
+            data.ctrl[right] += np.clip(target-data.ctrl[right], -.0008, .0008)
+            mujoco.mj_step(model, data)
+        self.assertGreater(float(np.mean(data.qpos[right_q])), .2)
+        self.assertLess(float(np.max(np.abs(data.qpos[left_q]))), .1)
+        for _ in range(3000):
+            data.ctrl[right] += np.clip(-data.ctrl[right], -.0008, .0008)
+            mujoco.mj_step(model, data)
+        self.assertLess(float(np.max(np.abs(data.qpos[right_q]))), .1)
+        self.assertTrue(np.isfinite(data.qpos).all())
+        self.assertFalse(any(w.number for w in data.warning))
+        initialize(model, data)
+        np.testing.assert_array_equal(data.qvel, 0.)
+
+if __name__ == '__main__':
+    unittest.main()
--- a/gear_sonic/utils/mujoco_sim/dex3_pickup.py
+++ b/gear_sonic/utils/mujoco_sim/dex3_pickup.py
@@ -1,9 +1,7 @@
-"""Opt-in visual pickup correction for the simulated right arm and Dex3 hand.
-
-SONIC retains the floating base, legs and left arm. This controller only
-sets joint torques; it never attaches, teleports or applies a force to the bottle.
-Target XY comes from RGB-D recognition plus the known bottle radius/table height.
-MuJoCo object pose/contact is used only to measure the outcome.
+"""Simulation-only pickup/place controller for Dex3 or native Inspire hands.
+
+The fixed-base RGB-D/IK controller owns the corresponding arm/hand torques.
+The bottle remains a free physical body; this is not learned VLA control.
 """
 import mujoco
 import numpy as np
@@ -36,7 +34,11 @@
         expanded = Path(directory) / 'scene.xml'
         mujoco.mj_saveLastXML(str(expanded), original)
         root = ET.parse(expanded).getroot()
-        root.find('compiler').set('meshdir', str(scene.parent / 'meshes'))
+        compiler = root.find('compiler')
+        meshdir = Path(compiler.get('meshdir', 'meshes'))
+        if not meshdir.is_absolute():
+            meshdir = (scene.parent / meshdir).resolve()
+        compiler.set('meshdir', str(meshdir))
         equality = root.find('equality')
         if equality is None:
             equality = ET.SubElement(root, 'equality')
@@ -48,7 +50,12 @@
     def __init__(self, model):
         self.model = m = model
         self.arm = np.array([m.joint('waist_pitch_joint').id] + [m.joint('right_' + name + '_joint').id for name in ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow', 'wrist_roll', 'wrist_pitch', 'wrist_yaw')])
-        self.hand = np.array([m.joint('right_hand_' + name + '_joint').id for name in ('thumb_0', 'thumb_1', 'thumb_2', 'middle_0', 'middle_1', 'index_0', 'index_1')])
+        self.native_inspire = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, 'right_thumb_1_joint') >= 0
+        if self.native_inspire:
+            from gear_sonic.scripts.prepare_inspire_ftp_sim import HAND_NAMES
+            self.hand = np.array([m.joint('right_' + n + '_joint').id for n in HAND_NAMES])
+        else:
+            self.hand = np.array([m.joint('right_hand_' + name + '_joint').id for name in ('thumb_0', 'thumb_1', 'thumb_2', 'middle_0', 'middle_1', 'index_0', 'index_1')])
         (self.arm_q, self.arm_v) = (m.jnt_qposadr[self.arm], m.jnt_dofadr[self.arm])
         (self.hand_q, self.hand_v) = (m.jnt_qposadr[self.hand], m.jnt_dofadr[self.hand])
         self.site = m.site('right_hand_grasp_center').id
@@ -60,7 +67,11 @@
         self.scratch = mujoco.MjData(m)
         (self.jp, self.jr) = (np.zeros((3, m.nv)), np.zeros((3, m.nv)))
         self.closed = np.array([0.0, -0.7, -0.7, 1.0, 1.5, 1.0, 1.5])
+        if self.native_inspire:
+            self.closed = np.array([1.0, 0.5, 0.95, 0.95, 0.95, 0.95])
         self.opened = np.zeros(len(self.hand))
+        if self.native_inspire:
+            self.opened[0] = 1.0
         self.lower = m.jnt_range[self.arm, 0].copy() + 0.002
         self.upper = m.jnt_range[self.arm, 1].copy() - 0.002
         (self.lower[0], self.upper[0]) = (0.0, min(self.upper[0], 0.5))
@@ -155,7 +166,7 @@
             (a, b) = self.model.geom_bodyid[[contact.geom1, contact.geom2]]
             if a == self.bottle or b == self.bottle:
                 name = self.model.body(int(b if a == self.bottle else a)).name
-                if name.startswith('right_hand_'):
+                if name.startswith('right_hand_') or (self.native_inspire and name.startswith(('right_thumb', 'right_index', 'right_middle', 'right_ring', 'right_little'))):
                     names.add(name)
         return sorted(names)
 
@@ -289,6 +300,10 @@
             else:
                 position = self.release_pos.copy()
                 rotation = self.release_rot.copy()
+                if self.native_inspire:
+                    clearance = float(np.clip((elapsed - 0.5) / 1.5, 0.0, 1.0))
+                    clearance = clearance * clearance * (3.0 - 2.0 * clearance)
+                    position += np.array([-0.05, -0.02, 0.0]) * clearance
                 self.fraction = float(1.0 - np.clip(elapsed / 2.0, 0.0, 1.0)) if self.stage == 'release' else 0.0
                 self.hand_target = self.opened + (self.closed - self.opened) * self.fraction
                 if self.stage == 'release' and elapsed > 3.0:
@@ -299,7 +314,7 @@
                     self.set_stage('retreat' if self.placed else 'failed', data.time)
         elif self.stage == 'retreat':
             t = np.clip(elapsed / 2.0, 0.0, 1.0)
-            release_offset = np.zeros(3)
+            release_offset = np.array([-0.05, -0.02, 0.0]) if self.native_inspire else np.zeros(3)
             position = self.release_pos + release_offset + np.array([-0.09, 0.0, 0.025]) * t * t * (3.0 - 2.0 * t)
             rotation = self.release_rot.copy()
             self.solve(data, position, rotation)
@@ -353,4 +368,4 @@
         hand[len(self.hand):] = 8.0 * (self.hand_target - data.qpos[self.hand_q]) - 0.2 * data.qvel[self.hand_v] + data.qfrc_bias[self.hand_v]
 
     def snapshot(self):
-        return {'hand_model': 'dex3', 'stage': self.stage, 'active': self.active, 'success': self.success, 'placed': self.placed, 'place_target_xy_m': self.place_xy.tolist() if self.place_xy is not None else None, 'target_source': 'YOLO RGB-D surface + known radius and tabletop height', 'target_center_world_m': self.target.tolist() if self.target is not None else None, 'position_error_m': self.position_error, 'orientation_error_rad': self.orientation_error, 'finger_contacts': self.contacts, 'closure_fraction': self.fraction, 'minimum_hold_lift_m': self.min_hold_lift if self.min_hold_lift is not None and np.isfinite(self.min_hold_lift) else None, 'error': self.error}
+        return {'hand_model': 'inspire_ftp' if self.native_inspire else 'dex3', 'stage': self.stage, 'active': self.active, 'success': self.success, 'placed': self.placed, 'place_target_xy_m': self.place_xy.tolist() if self.place_xy is not None else None, 'target_source': 'YOLO RGB-D surface + known radius and tabletop height', 'target_center_world_m': self.target.tolist() if self.target is not None else None, 'position_error_m': self.position_error, 'orientation_error_rad': self.orientation_error, 'finger_contacts': self.contacts, 'closure_fraction': self.fraction, 'minimum_hold_lift_m': self.min_hold_lift if self.min_hold_lift is not None and np.isfinite(self.min_hold_lift) else None, 'error': self.error}
--- a/gear_sonic/utils/mujoco_sim/configs.py
+++ b/gear_sonic/utils/mujoco_sim/configs.py
@@ -333,6 +333,9 @@
 class SimLoopConfig(BaseConfig):
     """Config for running the simulation loop."""
 
+    native_inspire: bool = False
+    """Select the native six-motor FTP model; assisted fixed-base simulation only."""
+
     assisted_pickup: bool = False
     """Use the Dex3 RGB-D/IK pickup controller in simulation."""
 
--- a/gear_sonic/scripts/run_sim_loop.py
+++ b/gear_sonic/scripts/run_sim_loop.py
@@ -49,6 +49,11 @@
     wbc_config["ASSISTED_PICKUP"] = config.assisted_pickup
     wbc_config["FIXED_PICKUP_BASE"] = config.fixed_pickup_base
     wbc_config["BOTTLE_DETECTION_PORT"] = 5582 if config.assisted_pickup else 0
+    if config.native_inspire:
+        if not (config.assisted_pickup and config.fixed_pickup_base):
+            raise ValueError('Native Inspire requires assisted fixed-base simulation')
+        wbc_config.update(NATIVE_INSPIRE=True, NUM_HAND_JOINTS=6, NUM_HAND_MOTORS=0,
+                          ROBOT_SCENE='models/g1_inspire_ftp/g1_inspire_ftp_pickup.xml')
 
     if config.enable_image_publish:
         assert (
--- a/gear_sonic/scripts/launch_inference.py
+++ b/gear_sonic/scripts/launch_inference.py
@@ -88,6 +88,9 @@
     """CLI config for the all-in-one VLA inference tmux launcher."""
 
     # Deployment mode
+    sim_native_inspire: bool = False
+    """Use native Inspire FTP in the assisted fixed-base simulation."""
+
     sim_assisted_pickup: bool = False
     """Enable YOLO RGB-D and the Dex3 pickup correction; simulation only."""
 
@@ -171,6 +174,12 @@
 def _check_prerequisites(config: InferenceLaunchConfig):
     """Verify that required tools and venvs exist."""
     errors = []
+    if config.sim_native_inspire:
+        if not (config.sim and config.sim_assisted_pickup and config.sim_fixed_base):
+            errors.append('--sim-native-inspire requires --sim --sim-assisted-pickup --sim-fixed-base')
+        scene = Path(__file__).resolve().parents[2] / 'models/g1_inspire_ftp/g1_inspire_ftp_pickup.xml'
+        if not scene.is_file():
+            errors.append('Build the native model with .venv_sim/bin/python gear_sonic/scripts/prepare_inspire_ftp_sim.py first')
     if config.sim_assisted_pickup != config.sim_fixed_base or (config.sim_assisted_pickup and not config.sim):
         errors.append('Assisted table pickup requires --sim --sim-assisted-pickup --sim-fixed-base')
     if config.sim_assisted_pickup:
@@ -281,6 +290,7 @@
     print("  SONIC VLA Inference Launcher")
     print("=" * 60)
     print(f"  Mode:            {'Simulation' if config.sim else 'Real Robot'}")
+    print(f"  Hand model:      {'Native Inspire FTP, six motors per hand' if config.sim_native_inspire else 'Dex3'}")
     print(f"  PolicyServer:    {config.policy_host}:{config.policy_port}")
     print(f"  Embodiment:      {config.embodiment_tag}")
     print(f"  Prompt:          {config.prompt}")
@@ -311,6 +321,8 @@
         )
         if config.sim_assisted_pickup:
             sim_cmd += " --assisted-pickup --fixed-pickup-base"
+        if config.sim_native_inspire:
+            sim_cmd += " --native-inspire"
         sim_target = f"{SESSION_NAME}:sim"
         subprocess.run(
             ["tmux", "send-keys", "-t", sim_target, sim_cmd, "C-m"],
--- a/gear_sonic/utils/mujoco_sim/base_sim.py
+++ b/gear_sonic/utils/mujoco_sim/base_sim.py
@@ -65,6 +65,9 @@
         self.standby = self.ground_start
         self._control_transition_started = None
 
+        self.native_inspire = bool(self.config.get('NATIVE_INSPIRE', False))
+        if self.native_inspire and not (self.config.get('ASSISTED_PICKUP') and self.config.get('FIXED_PICKUP_BASE')):
+            raise ValueError('Native Inspire is supported only by the assisted fixed-base controller')
         self.init_scene()
         self.last_reward = 0
 
@@ -255,6 +258,10 @@
             elif "right_hand" in name:
                 self.right_hand_index.append(i)
 
+        if self.native_inspire:
+            from gear_sonic.scripts.prepare_inspire_ftp_sim import HAND_NAMES
+            self.left_hand_index = [self.mj_model.joint('left_'+n+'_joint').id for n in HAND_NAMES]
+            self.right_hand_index = [self.mj_model.joint('right_'+n+'_joint').id for n in HAND_NAMES]
         assert len(self.body_joint_index) == self.robot.NUM_JOINTS
         assert len(self.left_hand_index) == self.robot.NUM_HAND_JOINTS
         assert len(self.right_hand_index) == self.robot.NUM_HAND_JOINTS
@@ -262,6 +269,14 @@
         self.body_joint_index = np.array(self.body_joint_index)
         self.left_hand_index = np.array(self.left_hand_index)
         self.right_hand_index = np.array(self.right_hand_index)
+        # Passive mimic joints have no actuator. Never use joint_id - 1 here.
+        self.joint_actuator = {int(j): i for i, j in enumerate(self.mj_model.actuator_trnid[:, 0])}
+        self.body_actuator = np.array([self.joint_actuator[int(j)] for j in self.body_joint_index])
+        self.left_hand_actuator = np.array([self.joint_actuator[int(j)] for j in self.left_hand_index])
+        self.right_hand_actuator = np.array([self.joint_actuator[int(j)] for j in self.right_hand_index])
+        if self.native_inspire:
+            self.torques = np.zeros(self.mj_model.nu)
+            self.torque_limit = self.mj_model.actuator_forcerange[:, 1].copy()
         self._initialize_ground_standby()
         self.assisted_pickup = None
         if self.config.get('ASSISTED_PICKUP', False):
@@ -269,6 +284,10 @@
             for name, value in (('left_shoulder_pitch_joint', -.2),
                                 ('right_shoulder_pitch_joint', .35), ('left_elbow_joint', .3)):
                 self.initial_qpos[self.mj_model.joint(name).qposadr[0]] = value
+            if self.native_inspire:
+                for side in ('left', 'right'):
+                    for joint, value in (('shoulder_pitch', .35), ('elbow', -.7), ('thumb_1', 1.0)):
+                        self.initial_qpos[self.mj_model.joint(side+'_'+joint+'_joint').qposadr[0]] = value
             self.mj_data.qpos[:] = self.initial_qpos
             mujoco.mj_forward(self.mj_model, self.mj_data)
             from gear_sonic.utils.mujoco_sim.dex3_pickup import Dex3Pickup
@@ -385,12 +404,12 @@
                         + self.unitree_bridge.low_cmd.motor_cmd[i].kp
                         * (
                             self.unitree_bridge.low_cmd.motor_cmd[i].q
-                            - self.mj_data.qpos[self.body_joint_index[i] + self.qpos_offset - 1]
+                            - self.mj_data.qpos[self.mj_model.jnt_qposadr[self.body_joint_index[i]]]
                         )
                         + self.unitree_bridge.low_cmd.motor_cmd[i].kd
                         * (
                             self.unitree_bridge.low_cmd.motor_cmd[i].dq
-                            - self.mj_data.qvel[self.body_joint_index[i] + self.qvel_offset - 1]
+                            - self.mj_data.qvel[self.mj_model.jnt_dofadr[self.body_joint_index[i]]]
                         )
                     )
         return body_torques
@@ -415,12 +434,12 @@
                     + self.unitree_bridge.left_hand_cmd.motor_cmd[i].kp
                     * (
                         self.unitree_bridge.left_hand_cmd.motor_cmd[i].q
-                        - self.mj_data.qpos[self.left_hand_index[i] + self.qpos_offset - 1]
+                        - self.mj_data.qpos[self.mj_model.jnt_qposadr[self.left_hand_index[i]]]
                     )
                     + self.unitree_bridge.left_hand_cmd.motor_cmd[i].kd
                     * (
                         self.unitree_bridge.left_hand_cmd.motor_cmd[i].dq
-                        - self.mj_data.qvel[self.left_hand_index[i] + self.qvel_offset - 1]
+                        - self.mj_data.qvel[self.mj_model.jnt_dofadr[self.left_hand_index[i]]]
                     )
                 )
                 right_hand_torques[i] = (
@@ -428,12 +447,12 @@
                     + self.unitree_bridge.right_hand_cmd.motor_cmd[i].kp
                     * (
                         self.unitree_bridge.right_hand_cmd.motor_cmd[i].q
-                        - self.mj_data.qpos[self.right_hand_index[i] + self.qpos_offset - 1]
+                        - self.mj_data.qpos[self.mj_model.jnt_qposadr[self.right_hand_index[i]]]
                     )
                     + self.unitree_bridge.right_hand_cmd.motor_cmd[i].kd
                     * (
                         self.unitree_bridge.right_hand_cmd.motor_cmd[i].dq
-                        - self.mj_data.qvel[self.right_hand_index[i] + self.qvel_offset - 1]
+                        - self.mj_data.qvel[self.mj_model.jnt_dofadr[self.right_hand_index[i]]]
                     )
                 )
         return np.concatenate((left_hand_torques, right_hand_torques))
@@ -478,19 +497,19 @@
         )
         obs["secondary_imu_vel"] = pose[7:13]
 
-        obs["body_q"] = self.mj_data.qpos[self.body_joint_index + 7 - 1]
-        obs["body_dq"] = self.mj_data.qvel[self.body_joint_index + 6 - 1]
-        obs["body_ddq"] = self.mj_data.qacc[self.body_joint_index + 6 - 1]
-        obs["body_tau_est"] = self.mj_data.actuator_force[self.body_joint_index - 1]
+        obs["body_q"] = self.mj_data.qpos[self.mj_model.jnt_qposadr[self.body_joint_index]]
+        obs["body_dq"] = self.mj_data.qvel[self.mj_model.jnt_dofadr[self.body_joint_index]]
+        obs["body_ddq"] = self.mj_data.qacc[self.mj_model.jnt_dofadr[self.body_joint_index]]
+        obs["body_tau_est"] = self.mj_data.actuator_force[self.body_actuator]
         if self.num_hand_dof > 0:
-            obs["left_hand_q"] = self.mj_data.qpos[self.left_hand_index + self.qpos_offset - 1]
-            obs["left_hand_dq"] = self.mj_data.qvel[self.left_hand_index + self.qvel_offset - 1]
-            obs["left_hand_ddq"] = self.mj_data.qacc[self.left_hand_index + self.qvel_offset - 1]
-            obs["left_hand_tau_est"] = self.mj_data.actuator_force[self.left_hand_index - 1]
-            obs["right_hand_q"] = self.mj_data.qpos[self.right_hand_index + self.qpos_offset - 1]
-            obs["right_hand_dq"] = self.mj_data.qvel[self.right_hand_index + self.qvel_offset - 1]
-            obs["right_hand_ddq"] = self.mj_data.qacc[self.right_hand_index + self.qvel_offset - 1]
-            obs["right_hand_tau_est"] = self.mj_data.actuator_force[self.right_hand_index - 1]
+            obs["left_hand_q"] = self.mj_data.qpos[self.mj_model.jnt_qposadr[self.left_hand_index]]
+            obs["left_hand_dq"] = self.mj_data.qvel[self.mj_model.jnt_dofadr[self.left_hand_index]]
+            obs["left_hand_ddq"] = self.mj_data.qacc[self.mj_model.jnt_dofadr[self.left_hand_index]]
+            obs["left_hand_tau_est"] = self.mj_data.actuator_force[self.left_hand_actuator]
+            obs["right_hand_q"] = self.mj_data.qpos[self.mj_model.jnt_qposadr[self.right_hand_index]]
+            obs["right_hand_dq"] = self.mj_data.qvel[self.mj_model.jnt_dofadr[self.right_hand_index]]
+            obs["right_hand_ddq"] = self.mj_data.qacc[self.mj_model.jnt_dofadr[self.right_hand_index]]
+            obs["right_hand_tau_est"] = self.mj_data.actuator_force[self.right_hand_actuator]
         obs["time"] = self.mj_data.time
         return obs
 
@@ -545,10 +564,10 @@
             self.assisted_pickup.apply_torques(self.mj_data, body_torques, hand_torques, self.body_joint_index)
         body_torques, hand_torques = self.blend_startup_torques(body_torques, hand_torques)
         # -1: actuator array is 0-based while joint indices from the model are 1-based
-        self.torques[self.body_joint_index - 1] = body_torques
+        self.torques[self.body_actuator - (6 if self.config["FREE_BASE"] else 0)] = body_torques
         if self.num_hand_dof > 0:
-            self.torques[self.left_hand_index - 1] = hand_torques[: self.num_hand_dof]
-            self.torques[self.right_hand_index - 1] = hand_torques[self.num_hand_dof :]
+            self.torques[self.left_hand_actuator - (6 if self.config["FREE_BASE"] else 0)] = hand_torques[: self.num_hand_dof]
+            self.torques[self.right_hand_actuator - (6 if self.config["FREE_BASE"] else 0)] = hand_torques[self.num_hand_dof :]
 
         self.torques = np.clip(self.torques, -self.torque_limit, self.torque_limit)
 
@@ -616,6 +635,8 @@
                     'right_hand_q': self.mj_data.qpos[self.mj_model.jnt_qposadr[self.right_hand_index]].tolist(),
                     'base_quat': self.mj_data.qpos[3:7].tolist(),
                 }
+                if self.native_inspire:
+                    state['hand_state_format'] = 'inspire_ftp_motor_radians'
                 self.image_publish_process.submit(self.mj_data, robot_state=state)
             return {}
         render_caches = {}
--- a/gear_sonic/scripts/run_vla_inference.py
+++ b/gear_sonic/scripts/run_vla_inference.py
@@ -248,6 +248,17 @@
         if log_errors:
             print("[DEBUG] prepare_observation: waiting for state msg..", flush=True)
         return None
+
+    # Convert only the observation schema. Native motor commands stay local.
+    state_msg = dict(state_msg)
+    hand_format = state_msg.pop('hand_state_format', 'dex3_joint_radians')
+    if hand_format == 'inspire_ftp_motor_radians':
+        from gear_sonic.utils.mujoco_sim.inspire_hand import dex3_observation_from_inspire
+        for side in ('left', 'right'):
+            state_msg[side+'_hand_q'] = dex3_observation_from_inspire(state_msg[side+'_hand_q'], side)
+    elif hand_format != 'dex3_joint_radians':
+        raise ValueError(f'Unsupported hand observation format: {hand_format}')
+    state_msg = {key: np.asarray(value).copy() for key, value in state_msg.items()}
 
     cam_img = camera_msg["images"]["ego_view"]
 
--- a/gear_sonic/utils/mujoco_sim/dex3_controls.py
+++ b/gear_sonic/utils/mujoco_sim/dex3_controls.py
@@ -8,8 +8,9 @@
 
 class Dex3SimulationControls:
     def __init__(self, env, port=5581, panel=True, channel=None, clock=time.monotonic):
-        if env.mj_model.nu != 43 or not env.ground_start:
-            raise ValueError('Step 3 requires the ground-start Dex3 scene')
+        expected_motors = 41 if env.native_inspire else 43
+        if env.mj_model.nu != expected_motors or not env.ground_start:
+            raise ValueError('Controls require a matching ground-start Dex3/Inspire scene')
         self.env, self.clock = env, clock
         self.channel = channel if channel is not None else SimulationControlChannel(port, bind=True)
         self.serial, self.pending = 0, None
@@ -269,7 +270,7 @@
     except tk.TclError as error:
         print('Cannot open simulation panel:', error, flush=True)
         return
-    root.title('Dex3 - Bottle / Start / Reset')
+    root.title('G1 Dex3 / Inspire FTP - Bottle / Start / Reset')
     frame = ttk.Frame(root, padding=16)
     frame.pack(fill='both', expand=True)
     ttk.Label(frame, text='Bottle X/Y on table (metres)').pack(anchor='w')
--- /dev/null
+++ b/gear_sonic/tests/test_native_inspire_guide.py
@@ -0,0 +1,126 @@
+"""Simulation-only regression; controlled perception, no learned-policy claims."""
+from pathlib import Path
+from types import SimpleNamespace
+import importlib.util,sys,unittest
+import numpy as np
+from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
+from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
+from gear_sonic.utils.mujoco_sim import dex3_controls as controls_module
+
+class Channel:
+ def __init__(self):self.sent=[]
+ def receive(self):return None
+ def send(self,message):self.sent.append(message);return True
+ def close(self):pass
+
+class NativePickupPlaceCycleTest(unittest.TestCase):
+ def make_env(self):
+  config=SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
+  config.update(GROUND_START=True,ASSISTED_PICKUP=True,FIXED_PICKUP_BASE=True,SIM_CONTROLS=False,BOTTLE_DETECTION_PORT=0,
+   NATIVE_INSPIRE=True,NUM_HAND_JOINTS=6,NUM_HAND_MOTORS=0,
+   ROBOT_SCENE=str(Path(__file__).resolve().parents[2]/'models/g1_inspire_ftp/g1_inspire_ftp_pickup.xml'))
+  env=DefaultEnv(config,onscreen=False)
+  env.set_unitree_bridge(SimpleNamespace(PublishLowState=lambda _:None,joystick=None,
+   low_cmd=None,low_cmd_received=False,last_low_cmd_time=100.,reset=lambda:None))
+  return env
+ def grasp(self,env,xy,start=True):
+  p=env.assisted_pickup;d=env.mj_data
+  if start:p.start(d)
+  for step in range(6000):
+   p.update(d,{'status':'detected','world_point_m':[xy[0]-.025,xy[1],.85],
+    'camera_position_world_m':[0.,xy[1],1.2],'capture_monotonic':step//100})
+   env.sim_step()
+   if p.stage in ('success','failed'):break
+  self.assertTrue(p.success,p.snapshot())
+  self.assertGreater(p.min_hold_lift,.12)
+ def test_four_place_targets_home_and_second_pickup(self):
+  for xy,destination in (([.43,-.11],[.45,-.05]),([.40,-.15],[.42,-.12]),
+                          ([.46,-.08],[.43,-.11]),([.43,-.05],[.45,-.05])):
+   with self.subTest(xy=xy,destination=destination):
+    env=self.make_env();m,d,p=env.mj_model,env.mj_data,env.assisted_pickup
+    self.assertEqual(m.nu,41);self.assertEqual(len(p.hand),6)
+    self.assertEqual(len(set(env.joint_actuator.values())),41)
+    ui=controls_module.Dex3SimulationControls(env,panel=False,channel=Channel(),clock=lambda:100.)
+    ui.handle({'command':'place','xy':xy})
+    for _ in range(100):env.sim_step()
+    env.begin_control_transition();self.grasp(env,xy)
+    # Hold for 60 simulated seconds before requesting Lower.
+    for _ in range(12000):
+     p.update(d,{});env.sim_step()
+     if p.stage=='failed':break
+    self.assertEqual(p.stage,'success',p.snapshot())
+    self.assertGreater(d.xpos[p.bottle,2]-p.centre_height,.12)
+    ui.phase='running';ui.seen=100.
+    self.assertTrue(ui.snapshot()['can_lower'])
+    # Invalid/unreachable requests must keep the held bottle and stage.
+    for invalid in ([float('nan'),0.],[2.,2.],[.70,.35]):
+     ui.handle({'command':'lower','xy':invalid})
+     self.assertTrue(ui.error)
+     self.assertEqual(p.stage,'success')
+    ui.handle({'command':'lower','xy':destination})
+    self.assertFalse(ui.error,ui.error)
+    self.assertFalse(ui.snapshot()['can_lower'])
+    self.assertFalse(ui.snapshot()['can_start'])
+    for _ in range(9000):
+     p.update(d,{});env.sim_step()
+     if p.stage in ('complete','failed'):break
+    self.assertEqual(p.stage,'complete',p.snapshot())
+    self.assertTrue(p.placed)
+    self.assertTrue(p.table_support(d))
+    self.assertLess(np.linalg.norm(d.xpos[p.bottle,:2]-destination),.025)
+    self.assertGreater(d.xmat[p.bottle].reshape(3,3)[2,2],.95)
+    np.testing.assert_allclose(d.qpos[p.arm_q],p.home_arm_q,atol=.05)
+    self.assertTrue(ui.snapshot()['can_start'])
+    self.assertFalse(ui.snapshot()['can_lower'])
+    settled_xy=d.xpos[p.bottle,:2].copy()
+    bottle_before=d.qpos[ui.qa:ui.qa+7].copy()
+    ui.handle({'command':'start'})
+    np.testing.assert_array_equal(d.qpos[ui.qa:ui.qa+7],bottle_before)
+    self.assertEqual(p.stage,'detecting')
+    self.assertEqual(ui.phase,'running')
+    self.grasp(env,settled_xy,start=False)
+    np.testing.assert_array_equal(d.xfrc_applied[p.bottle],0.)
+    self.assertNotIn(p.bottle,m.eq_obj1id)
+    self.assertNotIn(p.bottle,m.eq_obj2id)
+    ui.handle({'command':'reset'})
+    self.assertTrue(env.standby)
+    self.assertEqual(p.stage,'idle')
+    self.assertIsNone(p.place_xy)
+    self.assertFalse(ui.snapshot()['can_lower'])
+    np.testing.assert_allclose(d.qpos[ui.qa:ui.qa+3],[*xy,.801])
+    np.testing.assert_array_equal(d.qvel,0.)
+    self.assertFalse(any(w.number for w in d.warning))
+ def test_lower_unavailable_without_grasp_and_after_loss(self):
+  env=self.make_env();m,d,p=env.mj_model,env.mj_data,env.assisted_pickup
+  ui=controls_module.Dex3SimulationControls(env,panel=False,channel=Channel(),clock=lambda:100.)
+  ui.seen=100.;ui.phase='running'
+  ui.handle({'command':'lower','xy':[.45,-.05]})
+  self.assertTrue(ui.error);self.assertEqual(p.stage,'idle')
+  env.begin_control_transition();self.grasp(env,[.43,-.11])
+  qa=m.jnt_qposadr[m.joint('red_bottle_free_joint').id]
+  d.qpos[qa:qa+3]=[.43,-.11,.801]
+  for _ in range(150):p.update(d,{});env.sim_step()
+  self.assertEqual(p.stage,'failed')
+  self.assertFalse(ui.snapshot()['can_lower'])
+  ui.handle({'command':'lower','xy':[.45,-.05]})
+  self.assertTrue(ui.error)
+
+ def test_native_camera_state_and_observation_projection(self):
+  from gear_sonic.utils.mujoco_sim.inspire_hand import dex3_observation_from_inspire
+  env=self.make_env()
+  frames=[]
+  env.async_image_render=True
+  env.image_publish_process=SimpleNamespace(submit=lambda data,robot_state:frames.append(robot_state))
+  env.update_render_caches()
+  state=frames[0]
+  self.assertEqual(state['hand_state_format'],'inspire_ftp_motor_radians')
+  self.assertEqual(len(state['body_q']),29)
+  for side in ('left','right'):
+   q=np.asarray(state[side+'_hand_q']);before=q.copy()
+   self.assertEqual(q.shape,(6,))
+   projected=dex3_observation_from_inspire(q,side)
+   self.assertEqual(projected.shape,(7,));self.assertTrue(np.isfinite(projected).all())
+   np.testing.assert_array_equal(q,before)
+  with self.assertRaises(ValueError):dex3_observation_from_inspire([0.]*7,'right')
+
+if __name__=='__main__':unittest.main()
```
<!-- STEP06-PATCH-END -->

## 6. Tải và tạo model native

Chạy bằng môi trường simulation đã cài ở các bước trước:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python gear_sonic/scripts/prepare_inspire_ftp_sim.py
```

Lần đầu cần mạng tới `raw.githubusercontent.com`. File tồn tại được dùng lại; script
không kiểm chứng lại từng file cache trước khi build. Có thể kiểm tra manifest sau
khi tải bằng lệnh sau. Manifest ghi checksum của dữ liệu đã tải, còn checksum URDF
cố định dưới đây là đối chiếu thêm với bản nguồn đã kiểm tra.

```bash
python3 - <<'PYCHECK'
from pathlib import Path
import hashlib
import json
p = Path('models/g1_inspire_ftp')
manifest = json.loads((p / 'source.json').read_text())
assert manifest['revision'] == '5994d4faef0a9cadd3287f8de0199a67eeb2a259'
for name, digest in manifest['files'].items():
    assert hashlib.sha256((p / name).read_bytes()).hexdigest() == digest, name
source = p / 'g1_29dof_rev_1_0_with_inspire_hand_FTP.urdf'
assert hashlib.sha256(source.read_bytes()).hexdigest() == '63097d7366e1903b595c6adbdb187b205f5c1b1189088ca5aea32d25622415cb'
print('Source manifest and pinned URDF checksum: OK')
PYCHECK
```

Kết quả:

```text
models/g1_inspire_ftp/
  g1_29dof_rev_1_0_with_inspire_hand_FTP.urdf
  meshes/...
  source.json
  g1_inspire_ftp.xml          # preview: position actuators, pelvis fixture
  g1_inspire_ftp_pickup.xml   # runtime: torque actuators, camera, grasp sites
```

Preview đã có pelvis weld; runtime XML chưa có weld này. Khi chạy fixed-base,
helper thêm fixture pelvis cho runtime. Chai vẫn là free body và không có weld tay–chai.

XML sinh ra chứa đường dẫn mesh tuyệt đối. Khi chuyển máy hoặc chuyển thư mục,
chạy lại script để tái tạo model, không chỉ copy XML sang máy mới.

## 7. Kiểm thử trước khi mở cả stack

### 7.1. Kiểm tra vật lý không giao diện

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python -m unittest \
  gear_sonic.tests.test_inspire_ftp_model \
  gear_sonic.tests.test_native_inspire_guide -v
```

Phải thấy **4 test chạy và OK**, không phải chỉ `skipped`: test bỏ qua topology khi
chưa build model không chứng minh chuyển tay thành công. Test native pickup cần
runtime XML; thiếu file sẽ báo lỗi. Không cần server v10, YOLO hoặc robot thật.

Các trường hợp được kiểm tra:

| Chai ban đầu XY | Đích đặt XY |
|---|---|
| `(0.43, -0.11)` | `(0.45, -0.05)` |
| `(0.40, -0.15)` | `(0.42, -0.12)` |
| `(0.46, -0.08)` | `(0.43, -0.11)` |
| `(0.43, -0.05)` | `(0.45, -0.05)` |

Ở mỗi cặp: nâng thật trên 12 cm, giữ 60 giây **thời gian simulation**, đặt chai
đứng với sai số XY dưới 2,5 cm, thu tay, Start gắp lượt tiếp không Reset; sau đó
kiểm tra Reset. Đích NaN/ngoài bàn/ngoài tầm tay phải bị từ chối. Tuột chai làm
Lower bị khóa. Camera phải gửi nhãn native với 6 góc và phép chiếu phải tạo 7 góc.

Các test đưa vào quan sát có kiểm soát để tách lỗi vật lý/điều khiển. Chúng không
đo chất lượng YOLO trên video live và không đánh giá khả năng hành động của v10.

### 7.2. Preview bàn tay riêng

```bash
.venv_sim/bin/python gear_sonic/scripts/run_inspire_ftp_sim.py
```

- `Space`: đóng/mở hai tay.
- `L`, `R`: đóng/mở riêng từng bên.
- `Backspace`: reset preview.

Đây là cửa sổ kiểm tra model, không có nút Start/Lower của tác vụ và không kết
nối GR00T/SONIC. Đóng preview trước khi mở stack chính. Nếu WSL không hiện cửa
sổ, xử lý WSLg/driver như hướng dẫn cài đặt trước, không đổi code nắm để chữa GUI.

## 8. Chạy đầy đủ qua server v10

### Terminal 1 — server

Nếu server `127.0.0.1:5550` đã sẵn sàng thì giữ nguyên. Nếu chưa chạy:

```bash
cd ~/projects/Isaac-GR00T
.venv/bin/python gr00t/eval/run_gr00t_server.py \
  --model-path "$HOME/projects/GR00T-WholeBodyControl/checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000" \
  --embodiment-tag UNITREE_G1_SONIC \
  --device cuda:0 --host 127.0.0.1 --port 5550
```

Checkpoint vẫn là `cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-371ep-v10-finetune`.
Không tải checkpoint khác chỉ vì đổi model MuJoCo. Nếu gặp `Address already in use`,
kiểm tra server đang dùng cổng 5550; không nạp thêm một bản model vào GPU.

### Terminal 2 — native Inspire và giao diện đã có

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter \
  --sim-native-inspire --sim-assisted-pickup --sim-fixed-base \
  --prompt "grab the bottle"
```

Log launcher phải ghi `Native Inspire FTP, six motors per hand`; model vật lý có
5 ngón mỗi bàn tay. Không thêm `--inspire-ftp-hands`: đó không phải cờ chọn native
XML trong loạt tài liệu này. Bản tối thiểu sau bước 1–6 không thêm adapter cũ đó.

Theo bước 3, C++ deploy có thể cần xác nhận trong pane của nó trước khi sẵn sàng.
Xác nhận C++ không bắt đầu tác vụ: robot vẫn phải chờ bạn bấm **Start** trên panel.
Không nhấn phím thả dây để thay cho trình tự Start.

## 9. Thao tác một lượt và gắp lại

1. Chờ camera, detector, VLA và C++ sẵn sàng; robot đứng yên ở native home pose.
2. Khi chờ, nhập Bottle position X/Y, ví dụ `0.43`, `-0.11`, rồi Apply.
3. Bấm Start; controller chờ ảnh/target mới rồi approach → close → lift → success.
4. Khi giữ chai thành công, nhập Place destination `0.45`, `-0.05`, bấm Lower.
5. Chờ transfer → lower → release → retreat → return_home → complete.
6. Start sáng lại: bấm để nhận diện/gắp chai tại vị trí vừa đặt, không cần Reset.
7. Reset đưa robot và chai về native home pose cùng XY ban đầu đã Apply.

Giữ phân biệt tọa độ bề mặt YOLO, tọa độ trục chai đã hiệu chỉnh bán kính và tâm
vùng nắm của bàn tay. Chúng không phải ba điểm phải trùng XYZ hoàn toàn. Z đích
gắp vẫn dùng kích thước chai và mặt bàn đã biết, không phải ước lượng 6D pose tổng quát.

## 10. Lỗi thường gặp khi chuyển tay

| Biểu hiện | Kiểm tra |
|---|---|
| Vẫn thấy bàn tay Dex3 | Thiếu `--sim-native-inspire` hoặc chạy launcher chưa áp bước 6 |
| Cờ native không được nhận | Đang chạy code bước 5; áp patch đúng bản clone, không đổi môi trường ngẫu nhiên |
| Runtime XML không tồn tại | Chạy `prepare_inspire_ftp_sim.py` bằng `.venv_sim/bin/python` |
| Thiếu mesh hoặc XML trỏ máy khác | Build lại model tại đúng vị trí trên máy đang chạy |
| Lỗi kích thước 6/7, index 6 | Thiếu nhãn camera/khâu chiếu observation hoặc áp thiếu patch client |
| Joint ID vượt mảng torque | Kiểm tra ánh xạ `actuator_trnid`, không dùng lại `joint_id - 1` |
| Tay đặt xong quệt đổ chai | Kiểm tra nhánh native release/retreat và file runtime đúng model |
| Cầm lâu tuột, Lower không sáng | Không cưỡng bức Lower; kiểm tra contact và góc ngón, Reset để thử lại |
| Đích hợp lệ trên bàn nhưng không tới | Bị kiểm tra IK từ chối; chọn XY gần hơn trong vùng đã thử |
| Chờ mãi ở detecting | Xem cửa sổ detector và ảnh mới sau Apply/Start, không thay bằng tọa độ thật để giấu lỗi |

Không bỏ kiểm tra contact, weld chai vào tay hoặc teleport đến đích để làm test
qua. Những việc đó thay đổi ý nghĩa của kết quả vật lý đang kiểm tra.

## 11. Quay lại Dex3

Giữ nguyên code hỗ trợ cả hai model, bỏ cờ native khi khởi động:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter --sim-assisted-pickup --sim-fixed-base \
  --prompt "grab the bottle"
```

Không xóa asset Inspire để đổi tay. Không áp ngược từng patch bước 2–5. Mặc định
vẫn dùng scene Dex3 cũ; chỉ cờ native mới chọn runtime scene 41 actuator.

## 12. Đưa tài liệu lên branch riêng trên GitHub

Branch tài liệu đã tạo là `docs/dex3-simulation-guide`, trong bản repo chỉ chứa
code ở `share_code_only`. Copy **file MD này** sang đó; không copy model/mesh,
environment, checkpoint hay lịch sử `.git` của repo upstream.

```bash
cd ~/projects/GR00T-WholeBodyControl
cp docs/source/tutorials/huong_dan_chinh_sua/06_chuyen_dex3_sang_inspire_rh56dftp.md \
  share_code_only/docs/source/tutorials/huong_dan_chinh_sua/

cd share_code_only
git branch --show-current
git remote -v
```

Phải đúng branch `docs/dex3-simulation-guide` và remote `origin` là
`https://github.com/quyhuyhp123/g1-pickup-bottle-simulation.git`. Khi đúng:

```bash
git add docs/source/tutorials/huong_dan_chinh_sua/06_chuyen_dex3_sang_inspire_rh56dftp.md
git diff --cached --check
git diff --cached --stat
git commit -m "Document native Inspire FTP simulation migration"
git push -u origin docs/dex3-simulation-guide
```

Lệnh trên chia sẻ hướng dẫn có code nhúng; nó không có nghĩa đã áp code đó lên
branch hay kiểm thử `main` của repository cá nhân. Để dựng từ đầu, người đọc vẫn
phải dùng nền upstream đúng commit và tuần tự các bước 1 → 6.

Nếu áp patch trên clone để thử, giữ các thư mục sau ngoài commit:

```gitignore
models/g1_inspire_ftp/
*.before_step06
```

Các dòng trống có một khoảng trắng trong khối diff là context của patch. Branch
chia sẻ đã có `.gitattributes` cho `huong_dan_chinh_sua/*.md` để giữ nguyên chúng;
không chạy công cụ xóa toàn bộ khoảng trắng cuối dòng rồi làm hỏng patch.

## 13. Phạm vi kiểm chứng của tài liệu

Bản vá được kiểm tra áp nối tiếp bước 2 → 3 → 4 → 5 → 6; Python compile và các
khối shell được kiểm tra cú pháp. Model được dựng lại từ cache URDF đã ghim
revision, checksum nguồn khớp manifest. Kiểm thử vật lý không giao diện kiểm tra
native topology, observation, bốn cặp vị trí cùng chu trình giữ–đặt–gắp lại/Reset;
các test Dex3 của bước 5 cũng được chạy lại sau khi thêm hỗ trợ native.

Các kết quả này tách khỏi lượt chạy GUI + camera live + YOLO + VLA + C++ toàn bộ
stack trên máy clone mới; tài liệu không tuyên bố đã kiểm thử toàn bộ stack đó ở
một bản cài Windows/WSL sạch. Không có lệnh điều khiển robot thật trong bước 6.
