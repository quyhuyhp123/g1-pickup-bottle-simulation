# Bước 2 — Robot Dex3 bắt đầu dưới đất và giữ toàn bộ tư thế khi chờ

Tiếp nối [Bước 1 — Thêm bàn và chai có tương tác vật lý](01_them_ban_va_chai_vat_ly.md).
Dùng Unitree G1 mặc định: **29 khớp thân + 7 khớp mỗi tay Dex3 = 43 actuator**.

## 1. Kết quả cần đạt

Khi bật simulator:

- Robot ở vị trí khởi tạo, hai chân tiếp xúc sàn, không treo trên dây đàn hồi.
- Vị trí và hướng thân, chân, eo, cánh tay, cổ tay và các ngón được giữ nguyên.
- Chai vẫn chịu trọng lực, rơi/đổ/trượt bình thường; thời gian mô phỏng vẫn chạy.
- Simulator ở trạng thái **standby**, sẵn sàng cho bước thêm Start/Reset sau này.

“Khởi động sẵn” ở đây là simulator đã nạp và giữ tư thế chờ; chưa tự chạy policy
hoặc thực hiện động tác gắp. Bước này chưa cần GR00T server, YOLO, SONIC C++,
giao diện Start/Reset hoặc bộ điều khiển gắp.

**Chỉ viết tài liệu:** các khối code dưới là hướng dẫn tái tạo trên bản clone
ban đầu. Việc tạo file Markdown này không thay đổi code simulation đang chạy.

## 2. Phân biệt hai kiểu cố định

| Cơ chế | Thời điểm | Mục đích |
|---|---|---|
| Giữ toàn bộ robot lúc chờ — bước này | Khi `standby=True` | Robot không trôi, ngã, co ngón hoặc nhận lệnh cũ |
| Cố định pelvis suốt động tác | Một chế độ gắp được xây dựng về sau | Tạo fixture để thử tiếp cận/gắp; không phải giữ tất cả khớp |

Bước này không thêm weld pelvis và không cố định chai. Nó khôi phục trạng thái
robot trước/sau mỗi bước physics khi đang chờ. Đây là khóa trạng thái trong
simulation, **không phải chứng minh robot đã tự giữ thăng bằng bằng PD/SONIC**.
Không dùng cách gán `qpos` này để điều khiển robot thật.

Đến bước Start, cần có controller sẵn sàng, loại lệnh cũ, chuyển điều khiển êm
rồi mới nhả standby. Chỉ gán `standby=False` khi chưa có controller sẽ khiến
robot có thể ngã; bước 2 chưa cung cấp luồng bắt đầu chuyển động đó.

## 3. Bạn đang dùng bản clone mới hay workspace hiện tại?

### Bản clone mới, đã hoàn tất bước 1

Áp bản vá tối thiểu ở mục 5. Nó dựa trên commit:

```text
b042411fae38ee4d1af9aac82a37a1f8d14d6dd0
```

Bước 1 chỉ sửa scene XML; bản vá bước 2 sửa ba file Python nên có thể áp nối tiếp.
Bản vá được rút gọn cho chức năng chờ, chưa mang theo toàn bộ code gắp/giao diện
của workspace hiện tại.

### Workspace hiện tại đã có các chức năng từ trước

**Không áp lại patch.** Workspace đã có `ground_start`, `standby`,
`hold_initial_robot_pose()` cùng cơ chế chuyển điều khiển và Reset đầy đủ hơn.
Đọc giải thích và chạy phép kiểm tra ở mục 8. Các góc khởi tạo tay ở workspace
hiện tại có thể đã được điều chỉnh cho bài gắp; bản vá tối thiểu giữ góc gốc XML.

## 4. Những file cần sửa trên bản clone mới

| File | Thay đổi |
|---|---|
| `gear_sonic/utils/mujoco_sim/configs.py` | Thêm `ground_start=True` vào `SimLoopConfig` |
| `gear_sonic/scripts/run_sim_loop.py` | Truyền cờ thành `wbc_config["GROUND_START"]` |
| `gear_sonic/utils/mujoco_sim/base_sim.py` | Xác định vị trí chân/sàn, giữ riêng robot, nhánh standby và khôi phục khi reset |

Không đổi `scene_43dof.xml` ở bước này. Giữ scene bàn/chai đã làm ở bước 1.

## 5. Bản vá đầy đủ cho ba file Python

### 5.1. Sao lưu trên bản clone mới

```bash
cd ~/projects/GR00T-WholeBodyControl
cp -n gear_sonic/utils/mujoco_sim/configs.py \
  gear_sonic/utils/mujoco_sim/configs.py.before_step02
cp -n gear_sonic/scripts/run_sim_loop.py \
  gear_sonic/scripts/run_sim_loop.py.before_step02
cp -n gear_sonic/utils/mujoco_sim/base_sim.py \
  gear_sonic/utils/mujoco_sim/base_sim.py.before_step02
```

### 5.2. Áp code được nhúng ngay trong file Markdown này

Lưu tài liệu tại đúng đường dẫn trong repository rồi chạy lệnh sau. Lệnh kiểm
tra `git apply --check` trước, chỉ sửa file khi patch hợp lệ. Không chạy trên
workspace đã có standby. Nếu kiểm tra thất bại, đối chiếu phiên bản/nội dung
file; không dùng `git reset --hard` hoặc ghi đè thay đổi đang làm.

```bash
cd ~/projects/GR00T-WholeBodyControl
python3 - <<'PYAPPLY'
from pathlib import Path
import subprocess

p = Path('docs/source/tutorials/huong_dan_chinh_sua/02_dex3_dung_dat_giu_tu_the_cho.md')
s = p.read_text()
begin = '<!-- STEP02-PATCH-BEGIN -->' + '\n```diff\n'
end = '\n```\n<!-- STEP02-PATCH-END -->'
patch = s.split(begin, 1)[1].split(end, 1)[0] + '\n'
subprocess.run(['git', 'apply', '--check', '-'], input=patch, text=True, check=True)
subprocess.run(['git', 'apply', '-'], input=patch, text=True, check=True)
print('Da ap patch buoc 2. Chay kiem tra o muc 8 truoc khi mo viewer.')
PYAPPLY
```

Khối dưới là unified diff: dòng `+` được thêm, dòng `-` bị bỏ. Không dán trực
tiếp các dấu `+/-` vào Python; dùng lệnh trích patch ở trên hoặc sửa tương ứng.

<!-- STEP02-PATCH-BEGIN -->
```diff
--- a/gear_sonic/utils/mujoco_sim/configs.py
+++ b/gear_sonic/utils/mujoco_sim/configs.py
@@ -333,6 +333,9 @@
 class SimLoopConfig(BaseConfig):
     """Config for running the simulation loop."""
 
+    ground_start: bool = True
+    """Start on the floor and lock the robot pose while in standby."""
+
     mp_start_method: str = "spawn"
     """Multiprocessing start method"""
 
--- a/gear_sonic/scripts/run_sim_loop.py
+++ b/gear_sonic/scripts/run_sim_loop.py
@@ -37,6 +37,7 @@
     wbc_config = config.load_wbc_yaml()
     # NOTE: we will override the interface to local if it is not specified
     wbc_config["ENV_NAME"] = config.env_name
+    wbc_config["GROUND_START"] = config.ground_start
 
     if config.enable_image_publish:
         assert (
--- a/gear_sonic/utils/mujoco_sim/base_sim.py
+++ b/gear_sonic/utils/mujoco_sim/base_sim.py
@@ -60,6 +60,9 @@
         self.reward_lock = Lock()
         self.unitree_bridge = None
         self.onscreen = onscreen
+        self.elastic_band = None
+        self.ground_start = bool(self.config.get("GROUND_START", False))
+        self.standby = self.ground_start
 
         self.init_scene()
         self.last_reward = 0
@@ -246,6 +249,69 @@
         self.body_joint_index = np.array(self.body_joint_index)
         self.left_hand_index = np.array(self.left_hand_index)
         self.right_hand_index = np.array(self.right_hand_index)
+        self._initialize_ground_standby()
+
+    def _initialize_ground_standby(self):
+        """Build robot-only indices; objects must keep their independent physics."""
+        model, data = self.mj_model, self.mj_data
+        self.initial_qpos = model.qpos0.copy()
+        bodies = {self.root_body_id}
+        for body in range(self.root_body_id + 1, model.nbody):
+            if int(model.body_parentid[body]) in bodies:
+                bodies.add(body)
+        positions, velocities = [], []
+        for joint in range(model.njnt):
+            if int(model.jnt_bodyid[joint]) not in bodies:
+                continue
+            kind = int(model.jnt_type[joint])
+            nq = 7 if kind == int(mujoco.mjtJoint.mjJNT_FREE) else 4 if kind == int(mujoco.mjtJoint.mjJNT_BALL) else 1
+            nv = nq - 1 if nq > 1 else nq
+            qa = int(model.jnt_qposadr[joint])
+            va = int(model.jnt_dofadr[joint])
+            positions.extend(range(qa, qa + nq))
+            velocities.extend(range(va, va + nv))
+        self._standby_indices = (np.array(positions, dtype=int),
+                                 np.array(velocities, dtype=int),
+                                 np.array(sorted(bodies), dtype=int))
+        if not self.ground_start:
+            return
+        if not self.use_floating_root_link:
+            raise ValueError("Ground standby requires the floating-base G1 scene")
+        mujoco.mj_forward(model, data)
+        floor = model.geom('floor').id
+        feet = [g for g in range(model.ngeom)
+                if 'ankle' in model.body(int(model.geom_bodyid[g])).name
+                and model.geom_contype[g]]
+        if not feet:
+            raise ValueError("No ankle collision geometry found")
+        clearance = min(mujoco.mj_geomDistance(model, data, floor, g, 1., np.zeros(6))
+                        for g in feet)
+        if abs(clearance) > .05:
+            raise ValueError("Foot/floor distance exceeds 5 cm; check the initial pose")
+        root_joint = model.joint('floating_base_joint').id
+        root_address = int(model.jnt_qposadr[root_joint])
+        self.initial_qpos[root_address + 2] -= clearance + 1e-5
+        # Keep qpos0 (joint reference angles) unchanged.
+        data.qpos[:] = self.initial_qpos
+        self._disable_standby_band()
+        self.hold_initial_robot_pose()
+
+    def _disable_standby_band(self):
+        if self.elastic_band is not None:
+            self.elastic_band.enable = False
+            self.elastic_band.point = self.mj_data.xpos[self.band_attached_link].copy()
+
+    def hold_initial_robot_pose(self):
+        if not self.standby:
+            return
+        positions, velocities, bodies = self._standby_indices
+        data = self.mj_data
+        data.qpos[positions] = self.initial_qpos[positions]
+        data.qvel[velocities] = 0.
+        data.qacc_warmstart[velocities] = 0.
+        data.qfrc_applied[velocities] = 0.
+        data.xfrc_applied[bodies] = 0.
+        mujoco.mj_forward(self.mj_model, data)
 
     def init_renderers(self):
         self.renderers = {}
@@ -387,6 +453,18 @@
         return obs
 
     def sim_step(self):
+        if self.standby:
+            self._disable_standby_band()
+            self.hold_initial_robot_pose()
+            self.mj_data.ctrl[:] = 0.
+            mujoco.mj_step(self.mj_model, self.mj_data)
+            self.hold_initial_robot_pose()
+            self.obs = self.prepare_obs()
+            if self.unitree_bridge is not None:
+                self.unitree_bridge.PublishLowState(self.obs)
+                if self.unitree_bridge.joystick:
+                    self.unitree_bridge.PublishWirelessController()
+            return
         self.obs = self.prepare_obs()
         self.unitree_bridge.PublishLowState(self.obs)
         if self.unitree_bridge.joystick:
@@ -525,6 +603,11 @@
 
     def reset(self):
         mujoco.mj_resetData(self.mj_model, self.mj_data)
+        if self.ground_start:
+            self.standby = True
+            self.mj_data.qpos[:] = self.initial_qpos
+            self._disable_standby_band()
+            self.hold_initial_robot_pose()
 
 
 class BaseSimulator:
```
<!-- STEP02-PATCH-END -->

## 6. Cơ chế trong patch

### 6.1. Đặt bàn chân xuống sàn

Sau khi MuJoCo nạp model, code gọi `mj_forward()` để có vị trí geometry,
tìm các geometry va chạm của bàn chân và đo khoảng cách tới `floor` bằng
`mj_geomDistance()`.

Chỉ hạ/nâng Z của floating base đủ để chân chạm sàn với khe xuyên rất nhỏ
10 micromet. Không ép cứng một độ cao pelvis theo phỏng đoán. Nếu khoảng cách
vượt 5 cm, patch báo lỗi để kiểm tra scene/tư thế thay vì di chuyển robot quá xa.

Bản vá tối thiểu giữ các góc khớp từ XML. `initial_qpos` chứa tư thế khởi tạo
sau khi đặt chân xuống sàn; `model.qpos0` không bị sửa để tránh đổi mốc joint.

### 6.2. Chỉ giữ các bậc tự do thuộc robot

Code lấy cây body bắt đầu tại `pelvis`, sau đó tìm các joint nằm trong cây đó.
Từ `jnt_qposadr` và `jnt_dofadr`, lấy đúng địa chỉ cần giữ cho:

- Floating base: 7 giá trị vị trí/quaternion và 6 vận tốc.
- 43 khớp thân và bàn tay: mỗi hinge 1 tọa độ và 1 vận tốc.

Chai là body riêng trong `worldbody`, nằm ngoài cây `pelvis`, nên không bị giữ.
Không dùng `data.qpos[:] = initial_qpos` mỗi frame vì cách đó cũng kéo chai
về chỗ cũ và làm mất tương tác vật lý. Phép gán toàn scene chỉ dùng lúc khởi tạo
hoặc reset toàn bộ.

### 6.3. Khóa tư thế khi chờ

Trong mỗi `sim_step()` khi `standby=True`:

1. Tắt lực dây đàn hồi và khôi phục tư thế robot.
2. Xóa vận tốc, lực ngoài và warm-start thuộc robot.
3. Đặt lệnh actuator bằng 0, chạy một bước MuJoCo cho chai/cảnh tiếp tục tiến triển.
4. Khôi phục robot lần nữa sau bước physics, cập nhật forward kinematics.
5. Xuất observation qua bridge nếu có, rồi kết thúc nhánh chờ.

Vì nhánh này không đọc lệnh motor cũ, robot không tự cử động ngay khi có DDS
command tồn đọng. Khi ghép với Start ở bước sau, vẫn phải xử lý riêng action
cache của VLA và điều kiện controller sẵn sàng.

Đây không phải pause toàn bộ MuJoCo: `data.time` vẫn tăng và chai vẫn có contact.

### 6.4. Không còn cần phím 9 để đứng dưới đất

Dây đàn hồi bị tắt trong standby; vị trí robot được giữ bởi cơ chế khóa trạng
thái, không phải lực kéo lên cao. Nếu bật dây bằng phím 9 khi vẫn chờ, nhánh
standby sẽ tắt lại ở bước tiếp theo. Không dùng phím 9 làm Start.

### 6.5. Reset ở phạm vi bước 2

`DefaultEnv.reset()` xóa trạng thái MuJoCo và đưa robot về `initial_qpos`,
vận tốc bằng 0, `standby=True`. Chai cũng về giá trị khởi tạo XML.

Đây là API nội bộ được kiểm tra trong mục 8; chưa có nút Reset và chưa hứa
Backspace trong viewer thực hiện reset. Khi đã có client VLA ở bước sau,
Reset phải kết hợp pause/xóa lệnh cũ, không chỉ reset physics.

## 7. Chạy để quan sát

### Trên bản clone mới đã áp patch mục 5

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python gear_sonic/scripts/run_sim_loop.py --ground-start
```

Simulator dùng interface simulation/loopback mặc định. Không đổi thành interface
Ethernet robot thật. Không cần policy server, C++ deploy hay inference client.
Dừng bằng Ctrl+C trong terminal hoặc đóng viewer khi kiểm tra xong.

### Trên workspace hiện tại đã có giao diện từ trước

Có thể tắt panel để kiểm tra riêng bước 2:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python gear_sonic/scripts/run_sim_loop.py \
  --ground-start --no-sim-controls
```

`--no-sim-controls` chỉ có trong workspace hiện tại, không có trong bản vá tối
thiểu ở mục 5. Nếu có phiên simulator khác đang chạy, đóng đúng phiên đó trước;
không mở hai simulator cùng DDS domain khi kiểm tra.

Không dùng `python -m mujoco.viewer --mjcf=...` cho bước 2: viewer thuần chỉ nạp
XML, không chạy nhánh khóa trạng thái trong `DefaultEnv.sim_step()`.

## 8. Kiểm tra tự động: đứng dưới đất, khớp không đổi, chai vẫn rơi

Phép thử headless sau chạy được trên bản clone đã áp patch và workspace hiện
tại. Nó dùng bridge giả trong bộ nhớ, **không tạo DDS socket và không gửi lệnh
robot thật**. Không cần GUI hoặc model GR00T.

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python - <<'PYVERIFY'
from types import SimpleNamespace
import mujoco
import numpy as np
from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig

config = SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
config['GROUND_START'] = True
# Dùng scene Dex3 ở bước 1, không dùng chế độ gắp hoặc fixture.
config['ROBOT_SCENE'] = 'gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml'
config['ASSISTED_PICKUP'] = False
config['FIXED_PICKUP_BASE'] = False
config['SIM_CONTROLS'] = False
env = DefaultEnv(config, onscreen=False)
env.set_unitree_bridge(SimpleNamespace(
    PublishLowState=lambda obs: None, joystick=None, low_cmd=None,
    low_cmd_received=False))
model, data = env.mj_model, env.mj_data
assert model.nu == 43
assert env.standby

bodies = {model.body('pelvis').id}
for body in range(min(bodies) + 1, model.nbody):
    if int(model.body_parentid[body]) in bodies:
        bodies.add(body)
positions, velocities = [], []
for joint in range(model.njnt):
    if int(model.jnt_bodyid[joint]) not in bodies:
        continue
    kind = int(model.jnt_type[joint])
    nq = 7 if kind == int(mujoco.mjtJoint.mjJNT_FREE) else 4 if kind == int(mujoco.mjtJoint.mjJNT_BALL) else 1
    nv = nq - 1 if nq > 1 else nq
    qa, va = int(model.jnt_qposadr[joint]), int(model.jnt_dofadr[joint])
    positions.extend(range(qa, qa + nq))
    velocities.extend(range(va, va + nv))
positions, velocities = np.array(positions), np.array(velocities)
reference = env.initial_qpos.copy()

bottle_joint = model.joint('red_bottle_free_joint').id
bottle_q = int(model.jnt_qposadr[bottle_joint])
bottle_v = int(model.jnt_dofadr[bottle_joint])
assert bottle_q not in positions and bottle_v not in velocities
# Gây sai lệch robot và thả chai cao thêm 3 cm.
data.qpos[positions[0]] += .2
data.qvel[velocities] = 2.
data.qpos[bottle_q + 2] += .03
start_z = float(data.qpos[bottle_q + 2])
for _ in range(int(np.ceil(5. / model.opt.timestep))):
    env.sim_step()

np.testing.assert_allclose(data.qpos[positions], reference[positions], atol=1e-12)
np.testing.assert_allclose(data.qvel[velocities], 0., atol=1e-12)
assert data.time >= 5. - model.opt.timestep
assert data.qpos[bottle_q + 2] < start_z - .02
assert abs(data.qpos[bottle_q + 2] - .800) < .005
floor = model.geom('floor').id
foot_contacts = 0
for contact in data.contact:
    a, b = int(contact.geom1), int(contact.geom2)
    other = b if a == floor else a if b == floor else None
    if other is not None and 'ankle' in model.body(int(model.geom_bodyid[other])).name:
        foot_contacts += 1
assert foot_contacts > 0, 'Ban chan chua cham san'
assert not any(w.number for w in data.warning)
print('Robot root Z:', data.qpos[2], 'Foot contacts:', foot_contacts)
print('Bottle final Z:', data.qpos[bottle_q + 2], 'Simulation time:', data.time)

# Hàm giữ robot không được xóa vận tốc của chai.
data.qvel[bottle_v] = .1
env.hold_initial_robot_pose()
assert data.qvel[bottle_v] == .1
# Kiểm tra reset khôi phục toàn bộ trạng thái chờ.
env.reset()
assert env.standby
np.testing.assert_allclose(data.qpos, reference, atol=1e-12)
np.testing.assert_allclose(data.qvel, 0., atol=1e-12)
print('PASS: Robot giu tu the, chan cham san, chai van roi, reset hop le.')
PYVERIFY
```

Kết quả tham khảo khi kiểm tra bản vá tối thiểu với scene bước 1:

```text
Robot root Z: khoảng 0.79185 m
Foot contacts: lớn hơn 0
Bottle final Z: khoảng 0.79987 m
Simulation time: khoảng 5 giây
PASS
```

Số contact có thể thay đổi theo phiên bản MuJoCo; không dùng con số contact
cố định làm điều kiện. Kết quả này xác nhận khóa trạng thái lúc chờ, không
xác nhận cân bằng động, nhận diện, inference hoặc nắm chai thành công.

## 9. Lỗi thường gặp

| Hiện tượng | Kiểm tra |
|---|---|
| Robot vẫn bị treo | Đang dùng viewer thuần hoặc simulator chưa có patch; kiểm tra đúng venv, `GROUND_START` và `standby` |
| Robot đứng yên nhưng chai cũng đứng giữa không khí | Đã khóa nhầm toàn bộ qpos hoặc pause viewer; xem nhánh chỉ giữ subtree pelvis |
| Bàn chân không chạm sàn | Scene/góc ban đầu đã đổi; kiểm tra geometry collision của ankle và khoảng cách sàn |
| Python báo không có `--ground-start` | Chưa sửa `SimLoopConfig` hoặc đang dùng code/interpreter khác |
| Patch không áp được | File không còn ở phiên bản gốc hoặc đã có standby; không áp chồng patch |
| Robot không thực hiện gắp | Đúng phạm vi bước 2: chưa có Start/controller/inference |
| Đã sửa XML nhưng viewer thuần vẫn ngã | Chức năng giữ chờ nằm trong Python, phải chạy `run_sim_loop.py` |
| Standby giữ robot dù đã bật C++ | Cần luồng Start chuyển quyền điều khiển ở bước 3; chưa được thực hiện ở bước 2 |

## 10. Hoàn tất bước 2

Bước này hoàn tất khi robot Dex3 đứng dưới đất, thân và toàn bộ khớp giữ nguyên
trong thời gian chờ, chai tiếp tục tương tác vật lý và kiểm tra Reset qua API
thành công. Chưa nhả khóa để gắp.

Bước tiếp theo là thêm giao diện Start/Reset và quy trình chuyển từ standby
sang controller. Sau đó mới bổ sung nhận diện, tiếp cận, nắm và nâng bằng Dex3.
