# Bước 4 — Nhận diện, tiếp cận, nắm và nâng chai bằng Dex3

Tiếp nối [bước 1](01_them_ban_va_chai_vat_ly.md),
[bước 2](02_dex3_dung_dat_giu_tu_the_cho.md) và
[bước 3](03_dex3_giao_dien_toa_do_start_reset.md).
Dùng **G1 + Dex3, 43 actuator**. Các bản vá phải áp đúng thứ tự.

## 1. Kết quả và giới hạn của bước này

Bấm Start sau khi Apply X/Y:

```text
Camera RGB + depth + calibration
        ↓
YOLO11n nhận diện bottle → điểm bề mặt XYZ
        ↓
Ước lượng tâm chai bằng bán kính và độ cao bàn đã biết
        ↓
IK hiệu chỉnh eo/tay phải → tiếp cận → khép Dex3
        ↓
Có tiếp xúc ngón cái và ngón đối diện → nâng khoảng 20 cm → giữ
```

GR00T v10 vẫn nhận ảnh/trạng thái/prompt và chạy inference. **Ở chế độ hỗ trợ
trong bước này, action dự đoán của GR00T không trực tiếp quyết định quỹ đạo
hoặc ngón tay:** client phát token đứng, còn controller simulation sở hữu
lệnh giữ thân, hiệu chỉnh eo/tay phải và lệnh nắm. Không huấn luyện hay sửa
trọng số v10. Kết quả gắp này không được mô tả là checkpoint tự làm toàn bộ.

Khác với bước 2 chỉ khóa lúc chờ, bước 4 thêm **fixture cố định pelvis trong
suốt động tác**. Đây là thử nghiệm thao tác trên bàn, không đánh giá robot tự
cân bằng hoặc bước tới chai. Chai vẫn là free body, không weld vào tay, không
teleport hoặc dùng lực ngoài để nâng trong chu trình.

Phạm vi lần này: gắp, nâng, giữ và Reset. Chưa thêm Lower/đích đặt/mở tay/thu tay;
phần đặt chai sẽ làm ở bước riêng. Reset khi cầm chai là reset scene tức thời,
không phải thao tác đặt chai vật lý.

**Việc tạo tài liệu chỉ thêm Markdown, không sửa code hoặc chạy lại phiên hiện tại.**
Bản vá phía dưới là phiên bản tối thiểu cho người cài từ đầu, không áp chồng
lên workspace đã có đầy đủ các tính năng.

## 2. Vì sao thêm model v10 chưa đủ để gắp được chai?

- V10 xuất motion token và kênh action bàn tay; không xuất trực tiếp XYZ chai.
- Bàn tay Dex3 và các kênh nắm của checkpoint phải được ánh xạ phù hợp.
- Sai số camera, bám khớp và tiếp xúc có thể làm tay dừng thiếu hoặc đẩy chai.
- Khép tay chỉ theo khoảng cách đầu ngón không bảo đảm chai đã vào vùng nắm.

Bước này xử lý bằng detector riêng và controller hỗ trợ, dùng **tâm vùng nắm**
gắn trên cổ tay. Điểm đó là mốc hình học, không phải COM khối lượng của bàn tay.

## 3. Các tọa độ và tiêu chí thành công

| Giá trị | Nguồn | Dùng để làm gì |
|---|---|---|
| Bottle XYZ | MuJoCo, gốc body chai | Hiển thị/đo kết quả; không dùng để tạo mục tiêu XY |
| YOLO surface XYZ | Bbox RGB + depth + camera calibration | Điểm nhìn thấy ở bề mặt chai |
| Target centre XYZ | Điểm YOLO + bán kính/chiều cao bàn đã biết | Mục tiêu tiếp cận của controller |
| Grasp centre XYZ | Site `right_hand_grasp_center` trên tay | Theo dõi vị trí vùng nắm |
| Contact ngón/chai | MuJoCo | Xác nhận đã nắm và phát hiện tuột |

Camera MuJoCo nhìn theo -Z, +X sang phải, +Y lên trên; tọa độ pixel có gốc
trên trái nên phải đổi dấu khi unproject. RGB, depth, intrinsics, extrinsics
và trạng thái robot được lấy từ cùng snapshot physics.

YOLO trả điểm bề mặt, thường ở gần thân/nhãn, không phải tâm chai. Controller
suy ra trục chai bằng bán kính đã biết 2,5 cm; Z tâm thân dùng chiều cao bàn và
chai ở bước 1. Đây là bài có giả thiết về kích thước vật và bàn, chưa phải
định vị 6D cho vật bất kỳ.

### Trình tự gắp

1. Chờ ba frame RGB-D khác nhau, tọa độ XY dao động dưới 1,5 cm.
2. Kiểm tra IK trước khi rời tư thế chờ. Ngoài tầm thì báo failed.
3. Đưa tâm vùng nắm đến trước chai, còn cách bề mặt khoảng 2 cm theo hướng tiếp cận.
4. Tiến vào vùng nắm; chỉ khép nhẹ ban đầu rồi hoàn tất khép khi chai đã vào tay.
5. Phải có ngón cái và ít nhất index/middle tiếp xúc mới nâng.
6. Nâng mục tiêu khoảng 20 cm, giữ kiểm tra 3 giây; độ nâng chai phải trên 12 cm.
7. Nếu mất tiếp xúc hoặc chai thấp xuống quá lâu khi giữ, báo failed.

Không ép điều kiện X trùng tuyệt đối/Y 2 cm theo thế giới như cách gate cũ.
Khoảng pregrasp, tư thế cổ tay, IK và contact cùng quyết định chu trình.

## 4. File thêm/sửa so với sau bước 3

| Loại | File | Nội dung |
|---|---|---|
| Sửa | `gear_sonic/data/robot_model/model_data/g1/g1_29dof_with_hand.xml` | Site tâm vùng nắm Dex3 |
| Thêm | `gear_sonic/utils/mujoco_sim/dex3_pickup.py` | Fixture pelvis, IK, nắm, nâng, giữ và kiểm tra tuột |
| Thêm | `gear_sonic/utils/perception/__init__.py`, `bottle_detector.py` | YOLO và unproject depth |
| Thêm | `gear_sonic/scripts/run_bottle_detector.py` | Detector CPU 2 Hz, phát kết quả port 5582 |
| Thêm | `gear_sonic/utils/mujoco_sim/async_camera.py` | Render RGB-D riêng, chỉ giữ snapshot gần nhất |
| Thêm | `gear_sonic/utils/mujoco_sim/process_lifecycle.py` | Worker dừng khi parent mất |
| Sửa | `gear_sonic/camera/composed_camera.py` | Giữ metadata snapshot camera khi client đọc ảnh |
| Sửa | `gear_sonic/utils/mujoco_sim/base_sim.py` | Tạo fixture, pose tránh bàn, RGB-D và một luồng torque hỗ trợ |
| Sửa | `gear_sonic/utils/mujoco_sim/dex3_controls.py` | Nhận detector, hiển thị XYZ/stage, gọi chu trình sau Start |
| Sửa | `gear_sonic/utils/mujoco_sim/configs.py`, `gear_sonic/scripts/run_sim_loop.py` | Flag và điều kiện chế độ hỗ trợ |
| Sửa | `gear_sonic/scripts/run_vla_inference.py` | Dùng state ghép với ảnh, token đứng trong chế độ hỗ trợ |
| Sửa | `gear_sonic/scripts/launch_inference.py` | Khởi động camera/depth/detector và truyền các flag |

Không sửa `scene_43dof.xml` của bước 1 và không thay model weights.
Site màu xanh thuộc group 5, chỉ bật cho viewer; policy camera không bật group đó.

## 5. Áp bản vá nối tiếp bước 3 trên bản clone mới

Dừng simulator/client/C++ của bản clone đang sửa. Giữ server model nếu nó vẫn
hoạt động đúng. Đã có giao diện/full pickup trong workspace thì **không áp lại**.

### 5.1. Sao lưu các file được sửa

```bash
cd ~/projects/GR00T-WholeBodyControl
python3 - <<'PYBACKUP'
from pathlib import Path
import shutil
files = [
 'gear_sonic/data/robot_model/model_data/g1/g1_29dof_with_hand.xml',
 'gear_sonic/utils/mujoco_sim/configs.py',
 'gear_sonic/scripts/run_sim_loop.py',
 'gear_sonic/utils/mujoco_sim/base_sim.py',
 'gear_sonic/utils/mujoco_sim/dex3_controls.py',
 'gear_sonic/scripts/run_vla_inference.py',
 'gear_sonic/scripts/launch_inference.py',
 'gear_sonic/camera/composed_camera.py',
]
for name in files:
    p = Path(name)
    backup = p.with_name(p.name + '.before_step04')
    if not backup.exists():
        shutil.copy2(p, backup)
        print('Saved:', backup)
PYBACKUP
```

### 5.2. Trích và áp patch từ tài liệu này

```bash
cd ~/projects/GR00T-WholeBodyControl
python3 - <<'PYAPPLY'
from pathlib import Path
import subprocess
p = Path('docs/source/tutorials/huong_dan_chinh_sua/04_dex3_nhan_dien_nam_nang_chai.md')
s = p.read_text()
begin = '<!-- STEP04-PATCH-BEGIN -->' + '\n```diff\n'
end = '\n```\n<!-- STEP04-PATCH-END -->'
patch = s.split(begin, 1)[1].split(end, 1)[0] + '\n'
subprocess.run(['git', 'apply', '--check', '-'], input=patch, text=True, check=True)
subprocess.run(['git', 'apply', '-'], input=patch, text=True, check=True)
print('Da ap buoc 4. Cai detector va kiem tra truoc khi chay.')
PYAPPLY
```

Nếu patch không khớp, dừng để đối chiếu bước 2/3 và phiên bản code. Không force
hoặc reset hard. Phần dưới là toàn bộ dòng thêm/bỏ của bước 4.

<!-- STEP04-PATCH-BEGIN -->
```diff
--- a/gear_sonic/utils/mujoco_sim/configs.py
+++ b/gear_sonic/utils/mujoco_sim/configs.py
@@ -333,6 +333,12 @@
 class SimLoopConfig(BaseConfig):
     """Config for running the simulation loop."""
 
+    assisted_pickup: bool = False
+    """Use the Dex3 RGB-D/IK pickup controller in simulation."""
+
+    fixed_pickup_base: bool = False
+    """Anchor pelvis during assisted pickup; not a balanced locomotion test."""
+
     sim_controls: bool = True
     """Show the basic coordinate/Start/Reset panel in simulation."""
 
--- a/gear_sonic/scripts/run_sim_loop.py
+++ b/gear_sonic/scripts/run_sim_loop.py
@@ -42,6 +42,13 @@
         raise ValueError("Basic controls require ground-start simulation")
     wbc_config["SIM_CONTROLS"] = config.sim_controls
     wbc_config["SIM_CONTROL_PORT"] = config.sim_control_port
+    if config.assisted_pickup != config.fixed_pickup_base:
+        raise ValueError("Step 4 requires assisted pickup and fixed pickup base together")
+    if config.assisted_pickup and not (config.sim_controls and config.enable_image_publish and config.enable_offscreen):
+        raise ValueError("Assisted pickup requires controls and offscreen image publishing")
+    wbc_config["ASSISTED_PICKUP"] = config.assisted_pickup
+    wbc_config["FIXED_PICKUP_BASE"] = config.fixed_pickup_base
+    wbc_config["BOTTLE_DETECTION_PORT"] = 5582 if config.assisted_pickup else 0
 
     if config.enable_image_publish:
         assert (
--- a/gear_sonic/utils/mujoco_sim/base_sim.py
+++ b/gear_sonic/utils/mujoco_sim/base_sim.py
@@ -69,12 +69,20 @@
         self.last_reward = 0
 
         self.offscreen = offscreen
-        if self.offscreen:
+        self.async_image_render = bool(offscreen and enable_image_publish and self.config.get('ASSISTED_PICKUP', False))
+        if self.offscreen and not self.async_image_render:
             self.init_renderers()
         self.image_dt = self.config.get("IMAGE_DT", 0.033333)
         self.image_publish_process = None
 
     def start_image_publish_subprocess(self, start_method: str = "spawn", camera_port: int = 5555):
+        if self.async_image_render:
+            from gear_sonic.utils.mujoco_sim.async_camera import AsyncCameraProcess
+            self.image_publish_process = AsyncCameraProcess(
+                pathlib.Path(GEAR_SONIC_ROOT) / self.config['ROBOT_SCENE'],
+                self.camera_configs, port=camera_port, publish_depth=True)
+            self.image_publish_process.start_process()
+            return
         from gear_sonic.utils.mujoco_sim.image_publish_utils import ImagePublishProcess
 
         if len(self.camera_configs) == 0:
@@ -152,6 +160,9 @@
         """Initialize the default robot scene"""
         xml_path = str(pathlib.Path(GEAR_SONIC_ROOT) / self.config["ROBOT_SCENE"])
         self.mj_model = mujoco.MjModel.from_xml_path(xml_path)
+        if self.config.get('FIXED_PICKUP_BASE', False):
+            from gear_sonic.utils.mujoco_sim.dex3_pickup import load_anchored_scene
+            self.mj_model = load_anchored_scene(xml_path)
         self.mj_data = mujoco.MjData(self.mj_model)
         self.mj_model.opt.timestep = self.sim_dt
         self.torso_index = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, "torso_link")
@@ -219,6 +230,7 @@
                 self.viewer = None
 
         if self.viewer:
+            self.viewer.opt.sitegroup[5] = 1
             self.viewer.cam.azimuth = 120
             self.viewer.cam.elevation = -30
             self.viewer.cam.distance = 2.0
@@ -251,6 +263,16 @@
         self.left_hand_index = np.array(self.left_hand_index)
         self.right_hand_index = np.array(self.right_hand_index)
         self._initialize_ground_standby()
+        self.assisted_pickup = None
+        if self.config.get('ASSISTED_PICKUP', False):
+            # Keep hands away from the table in the fixture's initial pose.
+            for name, value in (('left_shoulder_pitch_joint', -.2),
+                                ('right_shoulder_pitch_joint', .35), ('left_elbow_joint', .3)):
+                self.initial_qpos[self.mj_model.joint(name).qposadr[0]] = value
+            self.mj_data.qpos[:] = self.initial_qpos
+            mujoco.mj_forward(self.mj_model, self.mj_data)
+            from gear_sonic.utils.mujoco_sim.dex3_pickup import Dex3Pickup
+            self.assisted_pickup = Dex3Pickup(self.mj_model)
 
     def _initialize_ground_standby(self):
         """Build robot-only indices; objects must keep their independent physics."""
@@ -512,6 +534,15 @@
                 self.mj_data.xfrc_applied[self.band_attached_link] = np.zeros(6)
         body_torques = self.compute_body_torques()
         hand_torques = self.compute_hand_torques()
+        if self.assisted_pickup is not None:
+            # One torque owner: fixture standing control, then right-arm/hand correction.
+            qa = self.mj_model.jnt_qposadr[self.body_joint_index]
+            va = self.mj_model.jnt_dofadr[self.body_joint_index]
+            body_torques = 100.*(self.initial_qpos[qa]-self.mj_data.qpos[qa]) - 4.*self.mj_data.qvel[va] + self.mj_data.qfrc_bias[va]
+            joints = np.r_[self.left_hand_index, self.right_hand_index]
+            qa, va = self.mj_model.jnt_qposadr[joints], self.mj_model.jnt_dofadr[joints]
+            hand_torques = 8.*(self.initial_qpos[qa]-self.mj_data.qpos[qa]) - .2*self.mj_data.qvel[va] + self.mj_data.qfrc_bias[va]
+            self.assisted_pickup.apply_torques(self.mj_data, body_torques, hand_torques, self.body_joint_index)
         body_torques, hand_torques = self.blend_startup_torques(body_torques, hand_torques)
         # -1: actuator array is 0-based while joint indices from the model are 1-based
         self.torques[self.body_joint_index - 1] = body_torques
@@ -577,6 +608,16 @@
         return {}
 
     def update_render_caches(self):
+        if self.async_image_render:
+            if self.image_publish_process is not None:
+                state = {
+                    'body_q': self.mj_data.qpos[self.mj_model.jnt_qposadr[self.body_joint_index]].tolist(),
+                    'left_hand_q': self.mj_data.qpos[self.mj_model.jnt_qposadr[self.left_hand_index]].tolist(),
+                    'right_hand_q': self.mj_data.qpos[self.mj_model.jnt_qposadr[self.right_hand_index]].tolist(),
+                    'base_quat': self.mj_data.qpos[3:7].tolist(),
+                }
+                self.image_publish_process.submit(self.mj_data, robot_state=state)
+            return {}
         render_caches = {}
         for camera_name, camera_config in self.camera_configs.items():
             renderer = self.renderers[camera_name]
@@ -624,6 +665,8 @@
 
     def reset(self):
         self._control_transition_started = None
+        if self.assisted_pickup is not None:
+            self.assisted_pickup.reset()
         mujoco.mj_resetData(self.mj_model, self.mj_data)
         if self.ground_start:
             self.standby = True
--- a/gear_sonic/scripts/run_vla_inference.py
+++ b/gear_sonic/scripts/run_vla_inference.py
@@ -114,6 +114,9 @@
     prompt: str = "demo"
     """The language prompt for the VLA policy."""
 
+    sim_stationary_body: bool = False
+    """Use the standing token while the simulated pickup controller owns motion."""
+
     sim_control_port: int = 0
     """Enable the simulation-only acknowledged Start/Reset channel (0 disables)."""
 
@@ -238,7 +241,9 @@
             return None
         if sensor_status is not None:
             sensor_status['image_timestamp'] = timestamp
-    state_msg = state_subscriber.get_msg()
+    state_msg = camera_msg.get('robot_state')
+    if state_msg is None:
+        state_msg = state_subscriber.get_msg()
     if state_msg is None:
         if log_errors:
             print("[DEBUG] prepare_observation: waiting for state msg..", flush=True)
@@ -376,6 +381,8 @@
 
 def main(config: InferenceConfig):
     pause_loop = True
+    if config.sim_stationary_body and not config.sim_control_port:
+        raise ValueError('Stationary pickup requires the simulation control channel')
 
     robot_model = instantiate_g1_robot_model(waist_location="lower_and_upper_body")
 
@@ -802,6 +809,11 @@
                     if right_hand_joints.ndim == 2:
                         right_hand_joints = right_hand_joints[current_idx]
 
+                    if config.sim_stationary_body:
+                        # GR00T was queried above; no predicted body/hand command drives this fixture.
+                        motion_token = LATENT_INITIAL_MOTION_TOKEN.copy()
+                        left_hand_joints = np.zeros(7, dtype=np.float32)
+                        right_hand_joints = np.zeros(7, dtype=np.float32)
                     frame_index = np.array([zmq_frame_counter], dtype=np.int64)
                     zmq_frame_counter += 1
 
--- a/gear_sonic/scripts/launch_inference.py
+++ b/gear_sonic/scripts/launch_inference.py
@@ -88,6 +88,12 @@
     """CLI config for the all-in-one VLA inference tmux launcher."""
 
     # Deployment mode
+    sim_assisted_pickup: bool = False
+    """Enable YOLO RGB-D and the Dex3 pickup correction; simulation only."""
+
+    sim_fixed_base: bool = False
+    """Anchor pelvis for the assisted table pickup test."""
+
     sim: bool = False
     """Run against MuJoCo sim instead of real robot."""
 
@@ -165,6 +171,12 @@
 def _check_prerequisites(config: InferenceLaunchConfig):
     """Verify that required tools and venvs exist."""
     errors = []
+    if config.sim_assisted_pickup != config.sim_fixed_base or (config.sim_assisted_pickup and not config.sim):
+        errors.append('Assisted table pickup requires --sim --sim-assisted-pickup --sim-fixed-base')
+    if config.sim_assisted_pickup:
+        repo = Path(__file__).resolve().parent.parent.parent
+        if not (repo / 'models/detectors/yolo11n.pt').is_file():
+            errors.append('Missing models/detectors/yolo11n.pt; install the detector first')
 
     if not shutil.which("tmux"):
         errors.append("tmux is not installed. Install with: sudo apt install tmux")
@@ -297,6 +309,8 @@
             f"--enable-image-publish --enable-offscreen "
             f"--camera-port {config.camera_port}"
         )
+        if config.sim_assisted_pickup:
+            sim_cmd += " --assisted-pickup --fixed-pickup-base"
         sim_target = f"{SESSION_NAME}:sim"
         subprocess.run(
             ["tmux", "send-keys", "-t", sim_target, sim_cmd, "C-m"],
@@ -400,8 +414,18 @@
     if config.sim:
         inference_cmd += " --sim-control-port 5581"
 
+    if config.sim_assisted_pickup:
+        inference_cmd += " --sim-stationary-body"
+
     print("Starting VLA inference (pane 1)...")
     _send_to_pane(2, inference_cmd, wait=1.0)
+
+    if config.sim_assisted_pickup:
+        subprocess.run(['tmux', 'new-window', '-t', SESSION_NAME, '-n', 'vision'])
+        detector_cmd = (f'cd {repo_root} && .venv_inference/bin/python '
+                        'gear_sonic/scripts/run_bottle_detector.py --rate 2')
+        subprocess.run(['tmux', 'send-keys', '-t', f'{SESSION_NAME}:vision', detector_cmd, 'C-m'])
+        subprocess.run(['tmux', 'select-window', '-t', f'{SESSION_NAME}:inference'])
 
     # Select the VLA inference pane
     subprocess.run(
--- a/gear_sonic/data/robot_model/model_data/g1/g1_29dof_with_hand.xml
+++ b/gear_sonic/data/robot_model/model_data/g1/g1_29dof_with_hand.xml
@@ -452,6 +452,8 @@
                           rgba="0.7 0.7 0.7 1" mesh="right_wrist_pitch_link" />
                         <geom type="mesh" rgba="0.7 0.7 0.7 1" mesh="right_wrist_pitch_link" />
                         <body name="right_wrist_yaw_link" pos="0.046 0 0">
+                          <site name="right_hand_grasp_center" pos="0.12 0.05 0"
+                            type="sphere" size="0.007" rgba="0.2 1 0.2 0.8" group="5" />
                           <inertial pos="0.0885506 -0.00212216 0.000573742"
                             quat="0.507224 0.511377 0.494292 0.486717" mass="0.457415"
                             diaginertia="0.0010598 0.000895373 0.0003238" />
--- a/gear_sonic/camera/composed_camera.py
+++ b/gear_sonic/camera/composed_camera.py
@@ -529,6 +529,9 @@
         if message is not None:
             self.idx += 1
             self._latest_message = ImageMessageSchema.deserialize(message).asdict()
+            for key in ('robot_state', 'simulation_time', 'capture_monotonic'):
+                if key in message:
+                    self._latest_message[key] = message[key]
             self._last_new_message_time = current_time
 
             if self.idx % 10 == 0:
--- a/gear_sonic/utils/mujoco_sim/dex3_controls.py
+++ b/gear_sonic/utils/mujoco_sim/dex3_controls.py
@@ -26,6 +26,14 @@
         self.bounds = np.c_[centre - half, centre + half]
         self.panel = BasicDex3Panel(self.xyz, self.bounds) if panel else None
         self.last_ui = -float('inf')
+        self.scene_changed_at = self.clock()
+        self.detection, self.detector_socket = None, None
+        if self.env.config.get('BOTTLE_DETECTION_PORT'):
+            import zmq
+            self.detector_socket = self.channel.context.socket(zmq.SUB)
+            self.detector_socket.setsockopt_string(zmq.SUBSCRIBE, '')
+            self.detector_socket.setsockopt(zmq.CONFLATE, 1)
+            self.detector_socket.connect(f"tcp://127.0.0.1:{self.env.config['BOTTLE_DETECTION_PORT']}")
 
     def connected(self):
         return self.clock() - self.seen < 2.
@@ -40,6 +48,8 @@
         data = self.env.mj_data
         data.qpos[self.qa:self.qa + 7] = [*self.xyz, 1., 0., 0., 0.]
         data.qvel[self.va:self.va + 6] = 0.
+        self.scene_changed_at = self.clock()
+        self.detection = None
 
     def local_reset(self):
         self.env.reset()
@@ -99,6 +109,12 @@
 
     def poll(self):
         now = self.clock()
+        if self.detector_socket is not None:
+            import zmq
+            try:
+                self.detection = self.detector_socket.recv_json(zmq.NOBLOCK)
+            except zmq.Again:
+                pass
         while (msg := self.channel.receive()) is not None:
             if msg.get('type') == 'status':
                 self.status, self.seen = msg, now
@@ -148,13 +164,27 @@
                 self.abort('VLA/SONIC data stale; robot reset to standby')
             elif self.phase == 'running' and self.status.get('paused', False):
                 self.abort('Policy paused; Reset to retry')
+        pickup = getattr(self.env, 'assisted_pickup', None)
+        if self.phase == 'running' and pickup is not None:
+            from gear_sonic.utils.perception.bottle_detector import current_detection
+            if not pickup.active:
+                self.scene_changed_at = now
+                pickup.start(self.env.mj_data)
+            pickup.update(self.env.mj_data, current_detection(self.detection, self.scene_changed_at, max_age=1.))
+            if pickup.error:
+                self.error = pickup.error
         if self.panel is not None and now - self.last_ui > .1:
             self.panel.update(self.snapshot())
             self.last_ui = now
 
     def snapshot(self):
         data, model = self.env.mj_data, self.env.mj_model
-        return {'phase': self.phase, 'error': self.error,
+        from gear_sonic.utils.perception.bottle_detector import current_detection
+        detection = current_detection(self.detection, self.scene_changed_at, max_age=1.)
+        pickup = getattr(self.env, 'assisted_pickup', None)
+        grasp = data.site_xpos[model.site('right_hand_grasp_center').id].tolist() if pickup else None
+        return {'grasp_centre': grasp, 'pickup': pickup.snapshot() if pickup else {}, 'detection': detection,
+                'phase': self.phase, 'error': self.error,
                 'bottle': data.qpos[self.qa:self.qa + 3].tolist(),
                 'wrist': data.xpos[model.body('right_wrist_yaw_link').id].tolist(),
                 'can_start': self.phase == 'idle' and self.connected() and self.pending is None,
@@ -164,6 +194,8 @@
     def close(self):
         if self.panel is not None:
             self.panel.close()
+        if self.detector_socket is not None:
+            self.detector_socket.close(linger=0)
         self.channel.close()
 
 
@@ -238,8 +270,8 @@
     ttk.Button(frame, text='Reset robot + bottle', command=lambda: send('reset')).pack(fill='x', pady=6)
     ttk.Label(frame, textvariable=info, justify='left').pack(anchor='w', pady=8)
     ttk.Label(frame, textvariable=error, foreground='red', wraplength=420).pack(anchor='w')
-    ttk.Label(frame, text='Bottle XYZ is simulation state, not model detection.').pack(anchor='w')
-    ttk.Label(frame, text='Start runs the controller; automatic pickup comes later.').pack(anchor='w')
+    ttk.Label(frame, text='Bottle XYZ = physics; YOLO XYZ = visible surface.').pack(anchor='w')
+    ttk.Label(frame, text='Pickup uses RGB-D/IK in a fixed-pelvis simulation.').pack(anchor='w')
 
     def refresh():
         if stop.is_set():
@@ -255,6 +287,13 @@
             fmt = lambda values: ' '.join(f'{v:+.3f}' for v in values)
             info.set(f"State: {state['phase']} | VLA: {state['client']}\n"
                      f"Bottle XYZ: {fmt(state['bottle'])}\nRight wrist XYZ: {fmt(state['wrist'])}")
+            pickup, detection = state.get('pickup', {}), state.get('detection', {})
+            point = detection.get('world_point_m')
+            xyz_text = fmt(point) if point is not None else detection.get('status', 'waiting')
+            grasp = state.get('grasp_centre')
+            grasp_text = fmt(grasp) if grasp is not None else 'disabled'
+            info.set(info.get() + f"\nYOLO surface XYZ: {xyz_text}\nGrasp centre XYZ: {grasp_text}\nPickup: {pickup.get('stage', 'disabled')}"
+                     + f" | closure: {pickup.get('closure_fraction', 0.)*100:.0f}%")
             error.set(state['error'])
             start_button.configure(state='normal' if state['can_start'] else 'disabled')
             apply_button.configure(state='normal' if state['can_place'] else 'disabled')
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/async_camera.py
@@ -0,0 +1,156 @@
+"""Render camera snapshots in a separate process without stalling physics."""
+
+import multiprocessing as mp
+import os
+import queue
+import time
+import zlib
+
+import numpy as np
+
+
+class AsyncCameraProcess:
+    def __init__(self, xml_path, camera_configs, port=5555, publish_depth=False):
+        self.xml_path = str(xml_path)
+        self.camera_configs = camera_configs
+        self.port = port
+        context = mp.get_context("spawn")
+        self.states = context.Queue(maxsize=1)
+        self.status = context.Queue(maxsize=1)
+        self.stop_event = context.Event()
+        self.process = context.Process(
+            target=_render_worker,
+            args=(self.xml_path, camera_configs, port, self.states, self.status, self.stop_event, publish_depth, os.getpid()),
+            daemon=True,
+        )
+        self._stopped = False
+
+    def start_process(self):
+        # The spawned interpreter must choose its GL backend before importing
+        # MuJoCo. The parent viewer keeps its existing GLFW context.
+        previous = os.environ.get("MUJOCO_GL")
+        os.environ["MUJOCO_GL"] = "egl"
+        try:
+            self.process.start()
+        finally:
+            if previous is None:
+                os.environ.pop("MUJOCO_GL", None)
+            else:
+                os.environ["MUJOCO_GL"] = previous
+        try:
+            state, detail = self.status.get(timeout=30)
+            if state != "ready":
+                raise RuntimeError(detail)
+        except Exception:
+            self.stop()
+            raise
+        print(f"[Camera] Async renderer ready on port {self.port}", flush=True)
+
+    def submit(self, data, robot_state=None):
+        if not self.process.is_alive():
+            raise RuntimeError("Camera renderer exited; refusing to continue with stale images")
+        packet = (data.qpos.copy(), data.mocap_pos.copy(), data.mocap_quat.copy(),
+                  float(data.time), time.time(), robot_state, time.monotonic())
+        # Keep only the most recent snapshot. Never wait for the renderer.
+        try:
+            self.states.put_nowait(packet)
+        except queue.Full:
+            try:
+                self.states.get_nowait()
+            except queue.Empty:
+                return
+            try:
+                self.states.put_nowait(packet)
+            except queue.Full:
+                pass
+
+    def stop(self):
+        if self._stopped:
+            return
+        self._stopped = True
+        self.stop_event.set()
+        if self.process.pid is not None:
+            self.process.join(timeout=3)
+            if self.process.is_alive():
+                self.process.terminate()
+                self.process.join(timeout=2)
+        for channel in (self.states, self.status):
+            channel.cancel_join_thread()
+            channel.close()
+
+
+def _render_worker(xml_path, camera_configs, port, states, status, stop_event, publish_depth=False, parent_pid=None):
+    from gear_sonic.utils.mujoco_sim.process_lifecycle import follow_parent
+    if parent_pid is not None and not follow_parent(parent_pid):
+        return
+    import mujoco
+    from gear_sonic.utils.mujoco_sim.sensor_server import ImageMessageSchema, SensorServer
+
+    renderers = {}
+    server = None
+    try:
+        model = mujoco.MjModel.from_xml_path(xml_path)
+        data = mujoco.MjData(model)
+        for name, config in camera_configs.items():
+            renderers[name] = mujoco.Renderer(model, height=config["height"], width=config["width"])
+        server = SensorServer()
+        server.start_server(port=port)
+        status.put(("ready", ""))
+        while not stop_event.is_set():
+            if parent_pid is not None and os.getppid() != parent_pid:
+                break
+            try:
+                qpos, mocap_pos, mocap_quat, sim_time, capture_time, robot_state, capture_monotonic = states.get(timeout=.1)
+            except queue.Empty:
+                continue
+            data.qpos[:] = qpos
+            data.mocap_pos[:] = mocap_pos
+            data.mocap_quat[:] = mocap_quat
+            data.time = sim_time
+            mujoco.mj_forward(model, data)
+            images = {}
+            depth_cameras = {}
+            for name, renderer in renderers.items():
+                config = camera_configs[name]
+                renderer.update_scene(data, camera=config.get("params", config.get("mjcf_name", name)))
+                images[name] = renderer.render()
+                if publish_depth and "mjcf_name" in config:
+                    # RGB, depth and camera extrinsics share this same physics
+                    # snapshot. No object pose/segmentation IDs are exported.
+                    renderer.enable_depth_rendering()
+                    try:
+                        depth = renderer.render()
+                    finally:
+                        renderer.disable_depth_rendering()
+                    camera_id = model.camera(config["mjcf_name"]).id
+                    height, width = depth.shape
+                    focal = height / (2 * np.tan(np.deg2rad(model.cam_fovy[camera_id]) / 2))
+                    depth_cameras[name] = {
+                        "depth_zlib": zlib.compress(depth.astype("<f2").tobytes(), level=1),
+                        "shape": [height, width], "dtype": "<f2",
+                        "calibration": {"fx": float(focal), "fy": float(focal),
+                            "cx": width / 2., "cy": height / 2.,
+                            "position_world_m": data.cam_xpos[camera_id].tolist(),
+                            "rotation_world_from_camera": data.cam_xmat[camera_id].reshape(3, 3).tolist()},
+                    }
+            message = ImageMessageSchema(
+                timestamps={name: capture_time for name in images}, images=images,
+            ).serialize()
+            message["simulation_time"] = sim_time
+            message["capture_monotonic"] = capture_monotonic
+            if depth_cameras:
+                message["depth_cameras"] = depth_cameras
+            if robot_state is not None:
+                message["robot_state"] = robot_state
+            server.send_message(message)
+    except Exception as error:
+        try:
+            status.put_nowait(("error", repr(error)))
+        except queue.Full:
+            pass
+        raise
+    finally:
+        for renderer in renderers.values():
+            renderer.close()
+        if server is not None:
+            server.stop_server()
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/process_lifecycle.py
@@ -0,0 +1,16 @@
+"""Keep simulator workers from holding sockets after their parent crashes."""
+
+import os
+import signal
+import sys
+
+
+def follow_parent(parent_pid):
+    if sys.platform == "linux":
+        import ctypes
+        # The death signal is set in the child; also close the race where the
+        # parent died before this child had a chance to set PR_SET_PDEATHSIG.
+        libc = ctypes.CDLL(None, use_errno=True)
+        if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
+            raise OSError(ctypes.get_errno(), "Cannot set simulator parent death signal")
+    return os.getppid() == parent_pid
--- /dev/null
+++ b/gear_sonic/utils/perception/bottle_detector.py
@@ -0,0 +1,93 @@
+"""Bottle recognition from RGB; 3-D comes from measured depth and camera calibration.
+
+No object name, body ID, object pose, or robot action is an input to this module.
+The reported 3-D point is a visible surface near the detected box centre.
+"""
+
+import time
+
+import numpy as np
+
+
+def pixel_depth_to_world(pixel, depth_m, calibration):
+    """Unproject top-left image coordinates into MuJoCo's world frame."""
+    fx, fy = float(calibration["fx"]), float(calibration["fy"])
+    cx, cy = float(calibration["cx"]), float(calibration["cy"])
+    rotation = np.asarray(calibration["rotation_world_from_camera"], dtype=float).reshape(3, 3)
+    position = np.asarray(calibration["position_world_m"], dtype=float)
+    if not np.isfinite([*pixel, depth_m, fx, fy, cx, cy, *position, *rotation.ravel()]).all():
+        raise ValueError("Invalid camera/depth values")
+    if depth_m <= 0 or fx <= 0 or fy <= 0:
+        raise ValueError("Depth and focal lengths must be positive")
+    # MuJoCo cameras face -Z, with +X to the right and +Y upwards.
+    camera_point = np.array([(pixel[0] - cx) * depth_m / fx,
+                             -(pixel[1] - cy) * depth_m / fy, -depth_m])
+    return camera_point, rotation @ camera_point + position
+
+
+def estimate_surface_point(box, depth, calibration):
+    if depth.ndim != 2:
+        raise ValueError("Depth must be a 2-D image")
+    height, width = depth.shape
+    x1, y1, x2, y2 = np.asarray(box, dtype=float)
+    if not np.isfinite([x1, y1, x2, y2]).all() or x2 <= x1 or y2 <= y1:
+        raise ValueError("Invalid bounding box")
+    u, v = (x1 + x2) / 2, (y1 + y2) / 2
+    if not 0 <= u < width or not 0 <= v < height:
+        raise ValueError("Detection is outside the depth image")
+    radius = max(1, min(4, int(min(x2 - x1, y2 - y1) * .08)))
+    x, y = int(u), int(v)
+    patch = depth[max(0, y - radius):min(height, y + radius + 1),
+                  max(0, x - radius):min(width, x + radius + 1)]
+    valid = patch[np.isfinite(patch) & (patch > 0) & (patch < 5)]
+    if not valid.size:
+        raise ValueError("No valid depth inside the detected bottle box")
+    depth_m = float(np.median(valid))
+    pixel = [u, v]
+    camera_point, world_point = pixel_depth_to_world(pixel, depth_m, calibration)
+    return {"pixel_uv": pixel, "depth_m": depth_m,
+            "camera_point_m": camera_point.tolist(), "world_point_m": world_point.tolist(),
+            "point_kind": "visible_surface_near_box_center"}
+
+
+class BottleDetector:
+    def __init__(self, model_path, confidence=.25):
+        from ultralytics import YOLO
+        self.model = YOLO(str(model_path))
+        self.confidence = confidence
+        self.bottle_class = next(k for k, v in self.model.names.items() if v == "bottle")
+
+    def detect(self, rgb, depth=None, calibration=None):
+        # Ultralytics treats ndarray inputs as BGR; simulator messages are RGB.
+        result = self.model.predict(rgb[:, :, ::-1].copy(), device="cpu", imgsz=640,
+                                    conf=self.confidence, classes=[self.bottle_class], verbose=False)[0]
+        output = {"status": "not_detected", "source": "YOLO11 RGB + rendered depth",
+                  "model": "yolo11n", "world_point_m": None}
+        if len(result.boxes) == 0:
+            return output
+        best = int(result.boxes.conf.argmax())
+        box = result.boxes.xyxy[best].cpu().numpy().tolist()
+        output.update(status="detected", confidence=float(result.boxes.conf[best]), bbox_xyxy=box)
+        if depth is None or calibration is None:
+            output.update(status="detected_no_depth", detail="No depth/calibration available")
+            return output
+        try:
+            output.update(estimate_surface_point(box, depth, calibration))
+            output['camera_position_world_m'] = list(calibration['position_world_m'])
+        except ValueError as error:
+            output.update(status="detected_no_depth", detail=str(error))
+        return output
+
+
+def current_detection(result, scene_changed_at=0., max_age=2.):
+    """Never display stale/pre-reset positions as current model detections."""
+    if not result:
+        return {"status": "waiting", "world_point_m": None}
+    captured = result.get("capture_monotonic", 0.)
+    if not isinstance(captured, (int, float)) or not np.isfinite(captured):
+        return {"status": "invalid_timestamp", "world_point_m": None}
+    if captured < scene_changed_at:
+        return {"status": "waiting_after_scene_change", "world_point_m": None}
+    if not 0. <= time.monotonic() - captured <= max_age:
+        return {"status": "stale", "world_point_m": None}
+    return result
--- /dev/null
+++ b/gear_sonic/scripts/run_bottle_detector.py
@@ -0,0 +1,95 @@
+"""Publish camera detections for display and optional simulation grip gating."""
+
+import argparse
+import base64
+import json
+import os
+from pathlib import Path
+import time
+import zlib
+
+import cv2
+import msgpack
+import numpy as np
+import zmq
+
+from gear_sonic.utils.mujoco_sim.sensor_server import ImageUtils
+from gear_sonic.utils.perception.bottle_detector import BottleDetector
+
+
+def main(args):
+    os.environ.setdefault("YOLO_AUTOINSTALL", "False")
+    os.environ.setdefault("YOLO_CONFIG_DIR", "/tmp/sonic_yolo_settings")
+    Path(os.environ["YOLO_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
+    import torch
+    torch.set_num_threads(2)
+    detector = BottleDetector(args.model_path, args.confidence)
+    context = zmq.Context()
+    camera = context.socket(zmq.SUB)
+    camera.setsockopt_string(zmq.SUBSCRIBE, "")
+    camera.setsockopt(zmq.CONFLATE, 1)
+    camera.connect(f"tcp://127.0.0.1:{args.camera_port}")
+    output = context.socket(zmq.PUB)
+    output.setsockopt(zmq.LINGER, 0)
+    output.bind(f"tcp://127.0.0.1:{args.output_port}")
+    path = Path(args.diagnostic_path) if args.diagnostic_path else None
+    if path:
+        path.parent.mkdir(parents=True, exist_ok=True)
+    print(f"[Bottle detector] YOLO11n CPU, separate perception, port {args.output_port}", flush=True)
+    previous_capture = 0.
+    try:
+        while True:
+            if not camera.poll(500):
+                output.send_json({"status": "camera_disconnected", "world_point_m": None,
+                                  "capture_monotonic": time.monotonic()})
+                continue
+            message = msgpack.unpackb(camera.recv(), raw=False)
+            captured = message.get("capture_monotonic", 0.)
+            if captured <= previous_capture or time.monotonic() - captured > 1.:
+                continue
+            previous_capture = captured
+            rgb = ImageUtils.decode_image(message["images"]["ego_view"])
+            sensor = message.get("depth_cameras", {}).get("ego_view")
+            depth = None
+            calibration = None
+            if sensor:
+                depth = np.frombuffer(zlib.decompress(sensor["depth_zlib"]), dtype="<f2").reshape(sensor["shape"])
+                calibration = sensor["calibration"]
+            start = time.monotonic()
+            result = detector.detect(rgb, depth, calibration)
+            result.update(image_shape=list(rgb.shape[:2]), capture_monotonic=captured, inference_ms=(time.monotonic() - start) * 1000,
+                          simulation_time=message.get("simulation_time"))
+            if path:
+                temporary = path.with_suffix(".tmp")
+                temporary.write_text(json.dumps(result, indent=2))
+                temporary.replace(path)
+            preview = rgb[:, :, ::-1].copy()
+            if "bbox_xyxy" in result:
+                x1, y1, x2, y2 = map(int, result["bbox_xyxy"])
+                cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 2)
+                cv2.putText(preview, f"bottle {result['confidence']:.2f}", (x1, max(18, y1 - 8)),
+                            cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 255, 0), 2)
+            if "pixel_uv" in result:
+                cv2.circle(preview, tuple(map(int, result["pixel_uv"])), 4, (0, 0, 255), -1)
+            cv2.putText(preview, "YOLO11 - robot camera", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 2)
+            preview = cv2.resize(preview, (320, 240))
+            result["preview_png"] = base64.b64encode(cv2.imencode(".png", preview)[1]).decode()
+            output.send_json(result, zmq.NOBLOCK)
+            time.sleep(max(0., 1. / args.rate - (time.monotonic() - start)))
+    except KeyboardInterrupt:
+        pass
+    finally:
+        camera.close(linger=0)
+        output.close(linger=0)
+        context.term()
+
+
+if __name__ == "__main__":
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--model-path", default="models/detectors/yolo11n.pt")
+    parser.add_argument("--camera-port", type=int, default=5555)
+    parser.add_argument("--output-port", type=int, default=5582)
+    parser.add_argument("--confidence", type=float, default=.25)
+    parser.add_argument("--rate", type=float, default=2.)
+    parser.add_argument("--diagnostic-path", default="outputs/bottle_detector/latest.json")
+    main(parser.parse_args())
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/dex3_pickup.py
@@ -0,0 +1,244 @@
+"""Opt-in visual pickup correction for the simulated right arm and Dex3 hand.
+
+SONIC retains the floating base, legs and left arm. This controller only
+sets joint torques; it never attaches, teleports or applies a force to the bottle.
+Target XY comes from RGB-D recognition plus the known bottle radius/table height.
+MuJoCo object pose/contact is used only to measure the outcome.
+"""
+import mujoco
+import numpy as np
+from scipy.spatial.transform import Rotation
+from scipy.optimize import least_squares
+
+def visual_bottle_center(detection, radius, centre_height):
+    if detection.get('status') != 'detected':
+        return None
+    point = np.asarray(detection.get('world_point_m'), dtype=float)
+    camera = np.asarray(detection.get('camera_position_world_m'), dtype=float)
+    if point.shape != (3,) or camera.shape != (3,) or (not np.isfinite([point, camera]).all()):
+        return None
+    if not centre_height - 0.07 < point[2] < centre_height + 0.095:
+        return None
+    direction = point[:2] - camera[:2]
+    length = np.linalg.norm(direction)
+    if length < 0.05:
+        return None
+    return np.r_[point[:2] + radius * direction / length, centre_height]
+
+def load_anchored_scene(scene):
+    """Simulation fixture: weld pelvis only. Bottle stays a free body."""
+    import tempfile
+    from pathlib import Path
+    import xml.etree.ElementTree as ET
+    scene = Path(scene)
+    original = mujoco.MjModel.from_xml_path(str(scene))
+    with tempfile.TemporaryDirectory() as directory:
+        expanded = Path(directory) / 'scene.xml'
+        mujoco.mj_saveLastXML(str(expanded), original)
+        root = ET.parse(expanded).getroot()
+        root.find('compiler').set('meshdir', str(scene.parent / 'meshes'))
+        equality = root.find('equality')
+        if equality is None:
+            equality = ET.SubElement(root, 'equality')
+        ET.SubElement(equality, 'weld', body1='pelvis', solref='.002 1')
+        return mujoco.MjModel.from_xml_string(ET.tostring(root, encoding='unicode'))
+
+
+class Dex3Pickup:
+
+    def __init__(self, model):
+        self.model = m = model
+        self.arm = np.array([m.joint('waist_pitch_joint').id] + [m.joint('right_' + name + '_joint').id for name in ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow', 'wrist_roll', 'wrist_pitch', 'wrist_yaw')])
+        self.hand = np.array([m.joint('right_hand_' + name + '_joint').id for name in ('thumb_0', 'thumb_1', 'thumb_2', 'middle_0', 'middle_1', 'index_0', 'index_1')])
+        (self.arm_q, self.arm_v) = (m.jnt_qposadr[self.arm], m.jnt_dofadr[self.arm])
+        (self.hand_q, self.hand_v) = (m.jnt_qposadr[self.hand], m.jnt_dofadr[self.hand])
+        self.site = m.site('right_hand_grasp_center').id
+        self.wrist = m.body('right_wrist_yaw_link').id
+        self.bottle = m.body('red_bottle').id
+        self.geom = m.geom('red_bottle_body').id
+        (self.radius, self.half_height) = m.geom_size[self.geom, :2]
+        self.centre_height = float(m.body_pos[self.bottle, 2])
+        self.scratch = mujoco.MjData(m)
+        (self.jp, self.jr) = (np.zeros((3, m.nv)), np.zeros((3, m.nv)))
+        self.closed = np.array([0.0, -0.7, -0.7, 1.0, 1.5, 1.0, 1.5])
+        self.opened = np.zeros(len(self.hand))
+        self.lower = m.jnt_range[self.arm, 0].copy() + 0.002
+        self.upper = m.jnt_range[self.arm, 1].copy() - 0.002
+        (self.lower[0], self.upper[0]) = (0.0, min(self.upper[0], 0.5))
+        self.upper[2] = min(self.upper[2], -0.05)
+        (self.lower[3], self.upper[3]) = (max(self.lower[3], -0.6), min(self.upper[3], 0.6))
+        self.reset()
+
+    def reset(self):
+        self.active = False
+        self.stage = 'idle'
+        self.error = ''
+        self.target = None
+        self.samples = []
+        self.last_capture = None
+        self.last_update = -np.inf
+        self.success = False
+        self.min_hold_lift = None
+        self.hold_contacts = True
+        self.contacts = []
+        self.position_error = None
+        self.orientation_error = None
+        self.fraction = 0.0
+        self.lost_grasp_since = None
+
+    def start(self, data):
+        self.reset()
+        self.active = True
+        self.arm_target = data.qpos[self.arm_q].copy()
+        self.hand_target = self.opened.copy()
+        self.start_pos = data.site_xpos[self.site].copy()
+        self.start_rot = data.xmat[self.wrist].reshape(3, 3).copy()
+        self.set_stage('detecting', data.time)
+
+    def set_stage(self, stage, now):
+        (self.stage, self.stage_since) = (stage, float(now))
+        print(f'[Assisted pickup] {stage}', flush=True)
+
+    def finger_contacts(self, data):
+        names = set()
+        for contact in data.contact:
+            (a, b) = self.model.geom_bodyid[[contact.geom1, contact.geom2]]
+            if a == self.bottle or b == self.bottle:
+                name = self.model.body(int(b if a == self.bottle else a)).name
+                if name.startswith('right_hand_'):
+                    names.add(name)
+        return sorted(names)
+
+    def solve(self, data, position, rotation):
+        (m, scratch) = (self.model, self.scratch)
+        scratch.qpos[:] = data.qpos
+        scratch.qpos[self.arm_q] = self.arm_target
+        for _ in range(8):
+            mujoco.mj_kinematics(m, scratch)
+            mujoco.mj_comPos(m, scratch)
+            linear = position - scratch.site_xpos[self.site]
+            angular = Rotation.from_matrix(rotation @ scratch.xmat[self.wrist].reshape(3, 3).T).as_rotvec()
+            if np.linalg.norm(linear) < 0.001 and np.linalg.norm(angular) < 0.015:
+                break
+            mujoco.mj_jacSite(m, scratch, self.jp, self.jr, self.site)
+            jac = np.vstack((self.jp[:, self.arm_v], 0.15 * self.jr[:, self.arm_v]))
+            error = np.r_[linear, 0.15 * angular]
+            delta = jac.T @ np.linalg.solve(jac @ jac.T + 2e-05 * np.eye(6), error)
+            scratch.qpos[self.arm_q] = np.clip(scratch.qpos[self.arm_q] + np.clip(delta, -0.12, 0.12), self.lower, self.upper)
+        self.arm_target += np.clip(scratch.qpos[self.arm_q] - self.arm_target, -0.025, 0.025)
+        self.position_error = float(np.linalg.norm(data.site_xpos[self.site] - position))
+        self.orientation_error = float(np.linalg.norm(Rotation.from_matrix(rotation @ data.xmat[self.wrist].reshape(3, 3).T).as_rotvec()))
+
+    def plan_pregrasp(self, data):
+        """Choose a feasible IK branch before leaving the retracted home pose."""
+        (m, scratch) = (self.model, self.scratch)
+        scratch.qpos[:] = data.qpos
+        (lower, upper) = (self.lower, self.upper)
+        seed = np.array([0.3, 0.0, -0.2, 0.0, 0.8, 0.0, 0.0, 0.0])
+
+        def residual(q):
+            scratch.qpos[self.arm_q] = q
+            mujoco.mj_kinematics(m, scratch)
+            rotation = Rotation.from_matrix(scratch.xmat[self.wrist].reshape(3, 3)).as_rotvec()
+            return np.r_[scratch.site_xpos[self.site] - self.pregrasp, 0.15 * rotation, 0.003 * (q - seed)]
+        result = least_squares(residual, np.clip(seed, lower, upper), bounds=(lower, upper), max_nfev=150)
+        if np.linalg.norm(residual(result.x)[:6]) > 0.006:
+            self.error = 'Visual bottle target outside the arm workspace. Move bottle closer and Reset.'
+            self.set_stage('failed', data.time)
+            return False
+        self.approach_start_q = data.qpos[self.arm_q].copy()
+        self.pregrasp_q = result.x
+        return True
+
+    def update(self, data, detection):
+        if not self.active or data.time - self.last_update < 0.019:
+            return
+        self.last_update = float(data.time)
+        elapsed = data.time - self.stage_since
+        self.contacts = self.finger_contacts(data)
+        opposed = any(('thumb' in name for name in self.contacts)) and any(('index' in name or 'middle' in name for name in self.contacts))
+        if self.stage == 'detecting':
+            captured = detection.get('capture_monotonic')
+            centre = visual_bottle_center(detection, self.radius, self.centre_height)
+            if centre is not None and captured != self.last_capture:
+                self.samples.append(centre)
+                self.last_capture = captured
+            if len(self.samples) >= 3:
+                sample = np.array(self.samples[-3:])
+                if np.max(np.ptp(sample[:, :2], axis=0)) < 0.015:
+                    self.target = np.median(sample, axis=0)
+                    self.grasp = self.target + [0.0, 0.0, 0.04]
+                    self.pregrasp = self.grasp + [-self.radius - 0.02, 0.0, 0.0]
+                    self.start_pos = data.site_xpos[self.site].copy()
+                    self.start_rot = data.xmat[self.wrist].reshape(3, 3).copy()
+                    if self.plan_pregrasp(data):
+                        self.set_stage('approach', data.time)
+            if elapsed > 15:
+                self.error = 'No stable RGB-D bottle target. Reset and retry.'
+                self.set_stage('failed', data.time)
+            return
+        if self.stage == 'failed':
+            return
+        (position, rotation) = (self.pregrasp.copy(), np.eye(3))
+        if self.stage == 'approach':
+            t = np.clip(elapsed / 3.0, 0.0, 1.0)
+            blend = t * t * (3.0 - 2.0 * t)
+            position = self.start_pos + blend * (self.pregrasp - self.start_pos)
+            rotation = Rotation.from_rotvec((1.0 - blend) * Rotation.from_matrix(self.start_rot).as_rotvec()).as_matrix()
+            self.arm_target = self.approach_start_q + blend * (self.pregrasp_q - self.approach_start_q)
+            self.position_error = float(np.linalg.norm(data.site_xpos[self.site] - self.pregrasp))
+            self.orientation_error = float(np.linalg.norm(Rotation.from_matrix(data.xmat[self.wrist].reshape(3, 3)).as_rotvec()))
+            if elapsed > 3.0 and self.position_error is not None and (self.position_error < 0.012) and (self.orientation_error < 0.08):
+                self.set_stage('close', data.time)
+            elif elapsed > 10:
+                self.error = 'Arm could not reach the visual pregrasp target.'
+                self.set_stage('failed', data.time)
+            return
+        elif self.stage == 'close':
+            advance = np.clip(elapsed / 1.5, 0.0, 1.0)
+            advance = advance * advance * (3.0 - 2.0 * advance)
+            position = self.pregrasp + advance * (self.grasp - self.pregrasp)
+            self.fraction = float(0.05 * advance + 0.95 * np.clip((elapsed - 1.5) / 1.5, 0.0, 1.0))
+            self.hand_target = self.opened + (self.closed - self.opened) * self.fraction
+            if elapsed > 3.5 and opposed:
+                self.set_stage('lift', data.time)
+            elif elapsed > 5:
+                self.error = 'No opposed finger contacts; lift cancelled. Reset to retry.'
+                self.set_stage('failed', data.time)
+        elif self.stage in ('lift', 'hold', 'success'):
+            t = np.clip(elapsed / 3.0, 0.0, 1.0) if self.stage == 'lift' else 1.0
+            position = self.grasp + [0.0, 0.0, 0.2 * t * t * (3.0 - 2.0 * t)]
+            if self.stage == 'lift' and elapsed > 3.0:
+                self.min_hold_lift = np.inf
+                self.set_stage('hold', data.time)
+                elapsed = 0.0
+            if self.stage in ('hold', 'success'):
+                lift = float(data.xpos[self.bottle, 2] - self.centre_height)
+                self.min_hold_lift = min(self.min_hold_lift, lift)
+                self.hold_contacts &= opposed
+                if self.stage == 'success':
+                    if lift < 0.12 or not opposed:
+                        if self.lost_grasp_since is None:
+                            self.lost_grasp_since = float(data.time)
+                        elif data.time - self.lost_grasp_since > 0.3:
+                            self.success = False
+                            self.error = 'Bottle slipped from grasp; lift invalidated. Reset to retry.'
+                            self.set_stage('failed', data.time)
+                    else:
+                        self.lost_grasp_since = None
+                if self.stage == 'hold' and elapsed > 3.0:
+                    self.success = bool(self.min_hold_lift > 0.12 and self.hold_contacts)
+                    if not self.success:
+                        self.error = 'Bottle was not lifted and held with opposed contacts.'
+                    self.set_stage('success' if self.success else 'failed', data.time)
+        self.solve(data, position, rotation)
+
+    def apply_torques(self, data, body, hand, body_joint_indices):
+        if not self.active:
+            return
+        indices = [int(np.flatnonzero(body_joint_indices == joint)[0]) for joint in self.arm]
+        body[indices] = 80.0 * (self.arm_target - data.qpos[self.arm_q]) - 3.0 * data.qvel[self.arm_v] + data.qfrc_bias[self.arm_v]
+        hand[len(self.hand):] = 8.0 * (self.hand_target - data.qpos[self.hand_q]) - 0.2 * data.qvel[self.hand_v] + data.qfrc_bias[self.hand_v]
+
+    def snapshot(self):
+        return {'hand_model': 'dex3', 'stage': self.stage, 'active': self.active, 'success': self.success, 'target_source': 'YOLO RGB-D surface + known radius and tabletop height', 'target_center_world_m': self.target.tolist() if self.target is not None else None, 'position_error_m': self.position_error, 'orientation_error_rad': self.orientation_error, 'finger_contacts': self.contacts, 'closure_fraction': self.fraction, 'minimum_hold_lift_m': self.min_hold_lift if self.min_hold_lift is not None and np.isfinite(self.min_hold_lift) else None, 'error': self.error}
--- /dev/null
+++ b/gear_sonic/utils/perception/__init__.py
@@ -0,0 +1 @@
+"""RGB-D perception helpers used by the simulated pickup demo."""
```
<!-- STEP04-PATCH-END -->

## 6. Cài YOLO mà giữ các phiên bản cốt lõi của GR00T

Simulator dùng `.venv_sim` Python 3.10, VLA/detector dùng `.venv_inference`
Python 3.12. Detector chạy CPU, giới hạn Torch 2 thread và mặc định 2 Hz.
Không cài lại môi trường hoặc nâng toàn bộ Torch/NumPy.

Trước khi cài, tạo constraint từ các phiên bản đang dùng:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python - <<'PYCONSTRAINT'
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
names = ('torch', 'torchvision', 'numpy', 'transformers', 'diffusers', 'opencv-python')
lines = []
for name in names:
    try:
        lines.append(f'{name}=={version(name)}')
    except PackageNotFoundError:
        pass
Path('/tmp/step04_keep_core.txt').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
PYCONSTRAINT

uv pip install --python .venv_inference/bin/python \
  --constraint /tmp/step04_keep_core.txt 'ultralytics==8.4.174' 'ultralytics-thop==2.2.2'

mkdir -p models/detectors
curl -fL --retry 2 \
  https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt \
  -o models/detectors/yolo11n.pt.tmp
mv models/detectors/yolo11n.pt.tmp models/detectors/yolo11n.pt

.venv_inference/bin/python -c "from ultralytics import YOLO; m=YOLO('models/detectors/yolo11n.pt'); print(m.names)"
```

Nếu đã có đúng weights thì bỏ hai lệnh curl/mv để tránh tải lại. SHA256 file
weights tham chiếu đã dùng để kiểm tra:

```text
0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1
```

Có thể so bằng `sha256sum models/detectors/yolo11n.pt`. Cài bằng constraint sẽ
báo conflict nếu phiên bản không phù hợp, thay vì tự đổi các gói cốt lõi. Nếu
conflict, đọc tên gói và đối chiếu môi trường; không bỏ constraint rồi nâng hàng loạt.

Không cần tải dataset hoặc checkpoint VLA khác cho bước này.

## 7. Chạy chu trình trên bản clone đã áp bước 4

Đã build SONIC với sửa header của bước 3. Bước 4 không sửa thêm C++ nên không
cần build lại nếu bước 3 đã build thành công.

Terminal 1 — server v10, giữ server cũ nếu đúng model và đang chạy:

```bash
cd ~/projects/Isaac-GR00T
.venv/bin/python gr00t/eval/run_gr00t_server.py \
  --model-path "$HOME/projects/GR00T-WholeBodyControl/checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000" \
  --embodiment-tag UNITREE_G1_SONIC \
  --device cuda:0 --host 127.0.0.1 --port 5550
```

Terminal 2 — launcher Dex3:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter \
  --sim-assisted-pickup --sim-fixed-base \
  --prompt "grab the bottle"
```

Launcher tạo window `vision` để chạy YOLO và dùng port 5582. Không chạy thêm một
detector thứ hai cùng port. Bản tối thiểu vẫn cần trả lời `y` ở pane C++ deploy
nếu có prompt, sau đó chờ `Init Done`.

Trong panel:

1. Thử vị trí ban đầu X = 0.43, Y = -0.11; Apply khi đang idle.
2. Chờ VLA/SONIC/camera; Start một lần.
3. Quan sát `detecting → approach → close → lift → hold → success`.
4. Khi success, chai được giữ trên cao; Reset để khởi tạo lượt khác.
5. Có thể thử X = 0.40, Y = -0.15 sau Reset. Không coi mọi điểm nhập được trên
   mặt bàn đều là vị trí tay có thể gắp.

Để đọc log: `tmux list-sessions`, `tmux attach -t sonic_inference`, Ctrl+B rồi
`w` chọn window `vision` hoặc `sim`. Nếu bấm đóng viewer thì simulator dừng,
SONIC sẽ mất LowState; không tiếp tục chờ policy như thể simulation còn chạy.

### Workspace hiện tại đã có đầy đủ tính năng

Không áp patch trong tài liệu này. Dùng cùng lệnh launcher Dex3 ở trên với
server đã chạy. Giao diện hiện tại có thêm Lower/đích đặt; đó là phần về sau,
không thuộc bản vá tối thiểu bước 4. Reset/Start vẫn dùng các nút, không trộn
với phím `k/i/p/9`.

## 8. Kiểm tra bằng code, không nạp model VLA

### 8.1. Kiểm thử vật lý với đầu vào nhận diện có kiểm soát

Phép thử sau dành cho **bản clone đã áp đủ bước 1–4**. Nó bypass GUI/VLA/DDS và
cấp tọa độ bề mặt giả lập để tách lỗi grasp khỏi lỗi detector. Không được dùng
kết quả này làm bằng chứng policy hoặc YOLO đã chạy được toàn bộ chu trình.

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python - <<'PYTEST'
from pathlib import Path
from types import SimpleNamespace
import importlib.util,sys,unittest,time
import numpy as np
import mujoco
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
from gear_sonic.utils.perception import bottle_detector as perception

class Dex3PickupPhysicsTest(unittest.TestCase):
 def make_env(self):
  config=SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
  config.update(GROUND_START=True,ASSISTED_PICKUP=True,FIXED_PICKUP_BASE=True,SIM_CONTROLS=False,BOTTLE_DETECTION_PORT=0)
  env=DefaultEnv(config,onscreen=False)
  env.set_unitree_bridge(SimpleNamespace(PublishLowState=lambda _:None,joystick=None,low_cmd=None,low_cmd_received=False))
  return env
 def test_four_targets_lift_hold_and_reset(self):
  for xy in ([.43,-.11],[.40,-.15],[.46,-.08],[.43,-.05]):
   with self.subTest(xy=xy):
    env=self.make_env();m,d,p=env.mj_model,env.mj_data,env.assisted_pickup
    qa=m.jnt_qposadr[m.joint('red_bottle_free_joint').id]
    d.qpos[qa:qa+2]=xy
    for _ in range(100):env.sim_step()
    env.begin_control_transition();p.start(d)
    for step in range(6000):
     p.update(d,{'status':'detected','world_point_m':[xy[0]-.025,xy[1],.85],
      'camera_position_world_m':[0.,xy[1],1.2],'capture_monotonic':step//100})
     env.sim_step()
     if p.stage in ('success','failed'):break
    self.assertTrue(p.success,p.snapshot())
    self.assertGreater(p.min_hold_lift,.12)
    for _ in range(1000):p.update(d,{});env.sim_step()
    self.assertEqual(p.stage,'success',p.snapshot())
    np.testing.assert_array_equal(d.xfrc_applied[p.bottle],0.)
    self.assertNotIn(p.bottle,m.eq_obj1id)
    self.assertNotIn(p.bottle,m.eq_obj2id)
    self.assertFalse(any(w.number for w in d.warning))
    env.reset();self.assertTrue(env.standby);self.assertEqual(p.stage,'idle');self.assertIsNone(p.target)
 def test_surface_unprojection_and_timestamp_rejection(self):
  calibration={'fx':100.,'fy':100.,'cx':50.,'cy':50.,'position_world_m':[1.,2.,3.],'rotation_world_from_camera':np.eye(3).tolist()}
  _,point=perception.pixel_depth_to_world([50,50],1.,calibration)
  np.testing.assert_allclose(point,[1,2,2])
  for stamp in (time.monotonic()-5.,time.monotonic()+5.,float('nan')):
   self.assertNotEqual(perception.current_detection({'status':'detected','capture_monotonic':stamp})['status'],'detected')
  self.assertEqual(perception.current_detection({'status':'detected','capture_monotonic':time.monotonic()-1.},scene_changed_at=time.monotonic())['status'],'waiting_after_scene_change')
 def test_detecting_requires_distinct_frames_and_lost_grasp_fails(self):
  env=self.make_env();m,d,p=env.mj_model,env.mj_data,env.assisted_pickup
  env.begin_control_transition();p.start(d)
  detection={'status':'detected','world_point_m':[.405,-.11,.85],'camera_position_world_m':[0.,-.11,1.2],'capture_monotonic':1.}
  for _ in range(50):p.update(d,detection);env.sim_step()
  self.assertEqual(p.stage,'detecting');self.assertEqual(len(p.samples),1)
  for step in range(6000):
   p.update(d,{**detection,'capture_monotonic':2+step//100});env.sim_step()
   if p.stage in ('success','failed'):break
  self.assertTrue(p.success,p.snapshot())
  qa=m.jnt_qposadr[m.joint('red_bottle_free_joint').id]
  d.qpos[qa:qa+3]=[.43,-.11,.801]
  for _ in range(150):p.update(d,{});env.sim_step()
  self.assertEqual(p.stage,'failed');self.assertFalse(p.success)

if __name__=='__main__': unittest.main()
PYTEST
```

Trên workspace hiện tại, dùng test đã có thay cho khối trên:

```bash
.venv_sim/bin/python -m unittest gear_sonic.tests.test_assisted_pickup
```

Test hiện tại còn kiểm tra cả đặt/thu tay từ các bước sau nên tốn thời gian hơn.
Nếu chưa có `dex3_pickup.py` ở bản clone, bạn chưa áp đúng patch; không chép một
file controller riêng vào vì còn cần site, camera, torque và điều phối Start.

### 8.2. Kiểm tra detector đang thực sự nhận RGB-D

Sau khi chạy launcher, đọc file mà detector ghi:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python - <<'PYREPORT'
from pathlib import Path
import json, time
p = Path('outputs/bottle_detector/latest.json')
if not p.exists():
    raise SystemExit('Chua co ket qua: xem pane vision, camera va detector')
r = json.loads(p.read_text())
print('Status:', r.get('status'))
print('Confidence:', r.get('confidence'))
print('Surface XYZ:', r.get('world_point_m'))
print('Inference ms:', r.get('inference_ms'))
print('Age s:', time.monotonic() - r.get('capture_monotonic', 0.))
PYREPORT
```

File này có thể là kết quả từ phiên cũ. Chỉ dùng nếu timestamp còn mới; panel
cũng loại kết quả trước Apply/Reset/Start và kết quả cũ hơn 1 giây. Kết quả
`not_detected` hoặc `detected_no_depth` không được dùng làm mục tiêu 3D.

## 9. Những gì đã kiểm chứng khi viết tài liệu

- Python của bản vá được kiểm tra cú pháp và chuỗi patch 2 → 3 → 4 được kiểm
  tra áp nối tiếp trên source gốc.
- **Ba bài kiểm thử headless đã qua** khi chạy chính code test nhúng trong
  tài liệu với cây source đã áp patch: nâng/giữ/reset tại bốn XY, yêu cầu frame khác nhau,
  phát hiện mất grasp và phép chiếu depth/từ chối timestamp cũ hoặc không hợp lệ.
- Kiểm tra render RGB-D bằng EGL và YOLO CPU trên một frame camera đầu robot:
  có bbox bottle, confidence khoảng 0,52 và điểm bề mặt XYZ hợp lệ. Đây là kiểm
  tra một frame, không phải đánh giá detector liên tục trong chu trình.
- Chưa chạy trọn GUI + server v10 + C++ trên bản clone tối thiểu của loạt tài
  liệu này. Test physics dùng perception có kiểm soát, không thay thế lượt live.

Bộ điều khiển, fixture và gain ở đây chỉ được dùng cho MuJoCo. Không bỏ `--sim`
để thử trên robot thật.

## 10. Lỗi thường gặp và cách phân biệt

| Hiện tượng | Kiểm tra |
|---|---|
| `waiting`/`not_detected` | Window vision, weights, ảnh chai có trong camera không, ánh sáng/hình dáng |
| `detected_no_depth` | Đang bật chế độ hỗ trợ để camera phát depth/calibration chưa |
| Có bbox nhưng detecting mãi | Age timestamp, ba frame khác nhau, XYZ đủ ổn định, Z điểm nằm ở vùng thân chai |
| Camera lỗi EGL | Driver Windows/WSL GPU, libEGL, log process renderer; không ép backend GLFW cho worker headless |
| Ngoài tầm IK | Chọn XY gần hơn, ví dụ 0.43/-0.11 hoặc 0.40/-0.15; không tăng bước nhảy khớp |
| Close nhưng không lift | Chưa có tiếp xúc ngón đối diện; xem hướng bàn tay, sai số target và contact |
| Tay đã nâng nhưng chai không lên | Chưa xác nhận grasp; success dựa trên độ nâng chai và contact, không dựa trên tay lên cao |
| Tuột sau success | Giới hạn lực/ma sát/vị trí nắm; trạng thái phải chuyển failed, không giữ báo success giả |
| Robot không bước đến chai xa | Pelvis đang fixture; đây là vùng làm việc tay hữu hạn |
| Thấy XYZ YOLO khác Bottle XYZ | YOLO là điểm bề mặt; Bottle XYZ là gốc body MuJoCo, không phải cùng đại lượng |
| Thay XY nhưng vẫn hướng chỗ cũ | Reset, Apply, chờ frame mới rồi Start; không dùng detection/action cache của lượt trước |
| Chỉ chạy lệnh ngắn không gắp | Phải có cả `--sim-assisted-pickup --sim-fixed-base` cho bài hỗ trợ này |

Bước 4 hoàn tất khi chu trình nhận diện–tiếp cận–nắm–nâng–giữ hoạt động trong
vùng thử nghiệm, có xác nhận contact và báo lỗi khi không nắm được. Bước tiếp
theo có thể bổ sung đặt chai xuống, mở ngón, thu tay và gắp lại.
