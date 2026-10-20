# Bước 3 — Giao diện nhập tọa độ chai, Start và Reset cho Dex3

Tiếp nối [bước 1: bàn/chai vật lý](01_them_ban_va_chai_vat_ly.md) và
[bước 2: đứng dưới đất, giữ tư thế chờ](02_dex3_dung_dat_giu_tu_the_cho.md).
Dùng G1 mặc định với **bàn tay Dex3, 43 actuator**.

## 1. Kết quả và phạm vi

Thêm cửa sổ có:

- Ô nhập X/Y của chai trên mặt bàn, Z khởi tạo giữ theo bàn.
- **Apply X/Y:** đặt chai đứng tại vị trí nhập, chỉ khi robot đang chờ.
- **Start:** phối hợp VLA và SONIC để chuyển từ khóa tư thế sang điều khiển.
- **Reset robot + bottle:** khóa robot lại ngay, pause VLA, bỏ action cũ và
  đưa toàn bộ scene về trạng thái chờ, giữ X/Y chai đã Apply.
- Hiển thị trạng thái kết nối, pha khởi động, tọa độ chai và cổ tay phải.

Tọa độ hiển thị ở bước này là **trạng thái MuJoCo**, chưa phải vị trí nhận diện
bằng model. Chưa có YOLO, bộ hỗ trợ gắp, Lower, đích đặt chai hoặc thu tay.
Start cho chạy inference/controller; **không bảo đảm checkpoint tự gắp được
chai**. Bước gắp–nâng Dex3 sẽ xử lý riêng sau khi luồng Start/Reset hoạt động.

Không nhả `standby` ngay khi bấm Start: khi chưa có VLA/SONIC, robot phải tiếp
tục được giữ. Mỗi khớp chỉ nhận một luồng điều khiển từ SONIC khi đã chuyển xong.

## 2. Điều kiện trước khi thực hiện

### Bản clone đang làm tuần tự các bước

Đã áp đúng bước 1 và bản vá tối thiểu bước 2, dựa trên commit upstream:

```text
b042411fae38ee4d1af9aac82a37a1f8d14d6dd0
```

Đã có `.venv_sim`, `.venv_inference`, Isaac-GR00T server và SONIC C++ theo
[WSL_UPSTREAM_V10_SETUP.md](../WSL_UPSTREAM_V10_SETUP.md). Nếu chưa cài môi trường,
hoàn tất phần cài đặt trước, không áp lại bản vá bước 2 lên code hiện tại.

### Workspace hiện tại đã có giao diện đầy đủ

**Không áp bản vá trong tài liệu này lên workspace hiện tại.** Các file và API
đã được mở rộng cho những tính năng khác. Bản vá dưới là phiên bản tối thiểu
để người cài từ đầu có thể đi từ bước 2 sang bước 3, không phải snapshot toàn bộ
code hiện tại. Cách chạy workspace hiện tại được ghi riêng ở mục 8.

Việc tạo tài liệu này chỉ thêm Markdown; không thay code hoặc phiên simulation
đang chạy trên máy.

## 3. Giao diện và trạng thái điều khiển

```text
Bottle X [0.430]   Y [-0.110]
Initial bottle Z = 0.801 m

[ Apply X/Y ]
[ Start ]
[ Reset robot + bottle ]

State: idle / preparing / grounded / observing / running / error
VLA: connected / disconnected
Bottle XYZ: ...
Right wrist XYZ: ...
```

### 3.1. Apply X/Y

- Chỉ nhận hai số hữu hạn; không nhận NaN, vô cực hoặc vị trí ngoài mặt bàn.
- Chừa 3 cm từ mép bàn, dựa vào geometry `pickup_table_top` ở bước 1.
- Giữ Z gốc thân chai = 0,801 m; đặt quaternion đứng và xóa vận tốc chai.
- Không thay vị trí robot hoặc góc khớp.
- Sau Start, muốn đổi vị trí chai phải Reset về chờ trước.

Với scene bước 1, biên tâm chai là X = 0,28..0,72 m và Y = -0,42..0,42 m.
Đây là biên mặt bàn, chưa phải biên tầm với cánh tay.

### 3.2. Start

```text
idle: robot khóa tư thế
  ↓ Start, yêu cầu VLA prepare và chờ xác nhận
preparing: VLA pause, xóa cache, phát initial token và lệnh bật SONIC POSE
  ↓ có LowCmd mới sau lần bấm, liên tục và đã chờ ít nhất 2 giây
grounded: nhả khóa, blend torque giữ → torque SONIC trong 2 giây
  ↓ transition hoàn tất và dữ liệu còn mới
start/observing: cho VLA suy luận từ ảnh mới sau thời điểm Start
  ↓ đã phát action mới
running
```

Nút Start chỉ sáng khi client VLA đã kết nối. C++ chưa sẵn sàng thì bước
preparing vẫn giữ robot, rồi báo lỗi nếu quá thời gian chờ. Dữ liệu cũ trước
lần bấm không được dùng để xác nhận controller sẵn sàng.

### 3.3. Reset

1. Khóa robot và đưa local scene về tư thế ban đầu ngay trên thread physics.
2. Dựng chai tại X/Y đã Apply, Z ban đầu, xóa vận tốc và lực ngoài qua reset.
3. Gửi `pause` tới VLA; xóa cached chunk, hàng đợi và mốc frame của lượt trước.
4. Bỏ các phản hồi suy luận được yêu cầu trước thời điểm reset/start mới.
5. Nhận ack của lệnh đúng ID rồi trở về idle. Khi mất client, vẫn reset local;
   Start chỉ dùng lại được sau khi client kết nối và không còn lệnh chờ.

Reset là khởi tạo scene simulation, không phải quỹ đạo thu tay hay đặt chai.
Trong robot thật không có phép reset vị trí tức thời như vậy.

## 4. Những file thêm/sửa

| Loại | File | Tác dụng |
|---|---|---|
| Thêm | `gear_sonic/utils/mujoco_sim/dex3_controls.py` | State machine và panel Tkinter chạy process riêng |
| Thêm | `gear_sonic/utils/inference/simulation_controls.py` | Kênh ZMQ PAIR, lệnh/ack/status trên loopback |
| Sửa | `gear_sonic/utils/mujoco_sim/configs.py` | Cờ bật panel và port 5581 |
| Sửa | `gear_sonic/scripts/run_sim_loop.py` | Kiểm tra simulation/ground-start, truyền cấu hình |
| Sửa | `gear_sonic/utils/mujoco_sim/base_sim.py` | Poll lệnh trên physics thread, blend torque, cleanup panel |
| Sửa | `gear_sonic/utils/mujoco_sim/unitree_sdk2py_bridge.py` | Timestamp LowCmd để phát hiện lệnh cũ/mất controller |
| Sửa | `gear_sonic/scripts/run_vla_inference.py` | Prepare/start/pause, xóa cache, ảnh mới và heartbeat |
| Sửa | `gear_sonic/scripts/launch_inference.py` | Truyền port điều khiển khi chạy `--sim` |
| Sửa | `gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/input_interface/zmq_manager.hpp` | Chuyển tiếp cờ Start mạng sang operator state trong POSE mode |

Port mặc định: policy 5550; camera 5555; action 5556; telemetry 5557;
keyboard 5580; điều khiển giao diện 5581. Chỉ một phiên dùng bộ port này.

## 5. Sao lưu và áp bản vá nối tiếp bước 2

Chỉ thực hiện trên bản clone đang theo loạt bước này. Dừng simulator/client/C++
của bản clone đó trước khi sửa; server model có thể giữ nguyên.

### 5.1. Sao lưu các file sẽ sửa

```bash
cd ~/projects/GR00T-WholeBodyControl
python3 - <<'PYBACKUP'
from pathlib import Path
import shutil
files = [
    'gear_sonic/utils/mujoco_sim/configs.py',
    'gear_sonic/scripts/run_sim_loop.py',
    'gear_sonic/utils/mujoco_sim/base_sim.py',
    'gear_sonic/utils/mujoco_sim/unitree_sdk2py_bridge.py',
    'gear_sonic/scripts/run_vla_inference.py',
    'gear_sonic/scripts/launch_inference.py',
    'gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/input_interface/zmq_manager.hpp',
]
for name in files:
    p = Path(name)
    backup = p.with_name(p.name + '.before_step03')
    if not backup.exists():
        shutil.copy2(p, backup)
        print('Saved:', backup)
PYBACKUP
```

### 5.2. Trích patch từ chính tài liệu này

Lưu tài liệu vào đúng đường dẫn dưới rồi chạy. `git apply --check` kiểm tra trước
khi sửa. Nếu báo file đã tồn tại hoặc patch không áp được, kiểm tra bạn có đang
ở workspace đã sửa từ trước không. Không dùng reset hard hoặc force để áp chồng.

```bash
cd ~/projects/GR00T-WholeBodyControl
python3 - <<'PYAPPLY'
from pathlib import Path
import subprocess
p = Path('docs/source/tutorials/huong_dan_chinh_sua/03_dex3_giao_dien_toa_do_start_reset.md')
s = p.read_text()
begin = '<!-- STEP03-PATCH-BEGIN -->' + '\n```diff\n'
end = '\n```\n<!-- STEP03-PATCH-END -->'
patch = s.split(begin, 1)[1].split(end, 1)[0] + '\n'
subprocess.run(['git', 'apply', '--check', '-'], input=patch, text=True, check=True)
subprocess.run(['git', 'apply', '-'], input=patch, text=True, check=True)
print('Da ap buoc 3. Kiem tra Python va build lai C++ o muc 7.')
PYAPPLY
```

Các dòng `+/-` dưới đây là định dạng diff; dùng lệnh trích patch, không dán dấu
`+` vào Python. Đây là code đầy đủ cho phần thêm/sửa của bước 3.

<!-- STEP03-PATCH-BEGIN -->
```diff
--- a/gear_sonic/utils/mujoco_sim/configs.py
+++ b/gear_sonic/utils/mujoco_sim/configs.py
@@ -333,6 +333,12 @@
 class SimLoopConfig(BaseConfig):
     """Config for running the simulation loop."""
 
+    sim_controls: bool = True
+    """Show the basic coordinate/Start/Reset panel in simulation."""
+
+    sim_control_port: int = 5581
+    """Loopback control channel shared with the VLA client."""
+
     ground_start: bool = True
     """Start on the floor and lock the robot pose while in standby."""
 
--- a/gear_sonic/scripts/run_sim_loop.py
+++ b/gear_sonic/scripts/run_sim_loop.py
@@ -38,6 +38,10 @@
     # NOTE: we will override the interface to local if it is not specified
     wbc_config["ENV_NAME"] = config.env_name
     wbc_config["GROUND_START"] = config.ground_start
+    if config.sim_controls and (wbc_config["ENV_TYPE"] != "sim" or not config.ground_start):
+        raise ValueError("Basic controls require ground-start simulation")
+    wbc_config["SIM_CONTROLS"] = config.sim_controls
+    wbc_config["SIM_CONTROL_PORT"] = config.sim_control_port
 
     if config.enable_image_publish:
         assert (
--- a/gear_sonic/utils/mujoco_sim/base_sim.py
+++ b/gear_sonic/utils/mujoco_sim/base_sim.py
@@ -63,6 +63,7 @@
         self.elastic_band = None
         self.ground_start = bool(self.config.get("GROUND_START", False))
         self.standby = self.ground_start
+        self._control_transition_started = None
 
         self.init_scene()
         self.last_reward = 0
@@ -313,6 +314,25 @@
         data.xfrc_applied[bodies] = 0.
         mujoco.mj_forward(self.mj_model, data)
 
+    def begin_control_transition(self):
+        self._control_transition_started = float(self.mj_data.time)
+        self.standby = False
+
+    def blend_startup_torques(self, body, hands):
+        started = self._control_transition_started
+        if started is None:
+            return body, hands
+        t = float(np.clip((self.mj_data.time - started) / 2., 0., 1.))
+        blend = t*t*(3.-2.*t)
+        def hold(joints, kp, kd):
+            qa, va = self.mj_model.jnt_qposadr[joints], self.mj_model.jnt_dofadr[joints]
+            return kp*(self.initial_qpos[qa]-self.mj_data.qpos[qa]) - kd*self.mj_data.qvel[va] + self.mj_data.qfrc_bias[va]
+        body_hold = hold(self.body_joint_index, np.asarray(self.robot.MOTOR_KP), np.asarray(self.robot.MOTOR_KD))
+        hand_hold = hold(np.r_[self.left_hand_index, self.right_hand_index], 1.5, .1)
+        if t >= 1.:
+            self._control_transition_started = None
+        return (1.-blend)*body_hold+blend*body, (1.-blend)*hand_hold+blend*hands
+
     def init_renderers(self):
         self.renderers = {}
         for camera_name, camera_config in self.camera_configs.items():
@@ -492,6 +512,7 @@
                 self.mj_data.xfrc_applied[self.band_attached_link] = np.zeros(6)
         body_torques = self.compute_body_torques()
         hand_torques = self.compute_hand_torques()
+        body_torques, hand_torques = self.blend_startup_torques(body_torques, hand_torques)
         # -1: actuator array is 0-based while joint indices from the model are 1-based
         self.torques[self.body_joint_index - 1] = body_torques
         if self.num_hand_dof > 0:
@@ -602,6 +623,7 @@
         return self_collision
 
     def reset(self):
+        self._control_transition_started = None
         mujoco.mj_resetData(self.mj_model, self.mj_data)
         if self.ground_start:
             self.standby = True
@@ -655,6 +677,11 @@
 
         self.init_subscriber()
         self.init_publisher()
+        self.basic_controls = None
+        if self.config.get('SIM_CONTROLS', False):
+            from gear_sonic.utils.mujoco_sim.dex3_controls import Dex3SimulationControls
+            self.basic_controls = Dex3SimulationControls(self.sim_env,
+                port=self.config.get('SIM_CONTROL_PORT', 5581))
 
         self.sim_thread = None
 
@@ -690,6 +717,8 @@
             ):
                 step_start = time.monotonic()
 
+                if self.basic_controls is not None:
+                    self.basic_controls.poll()
                 self.sim_env.sim_step()
                 now = time.time()
                 if now - ts > 1 / 10.0 and self.redis_client is not None:
@@ -726,6 +755,10 @@
         self.sim_env.reset()
 
     def close(self):
+        controls = getattr(self, 'basic_controls', None)
+        if controls is not None:
+            controls.close()
+            self.basic_controls = None
         self._running = False
         try:
             if self.sim_env.image_publish_process is not None:
--- a/gear_sonic/scripts/run_vla_inference.py
+++ b/gear_sonic/scripts/run_vla_inference.py
@@ -114,6 +114,9 @@
     prompt: str = "demo"
     """The language prompt for the VLA policy."""
 
+    sim_control_port: int = 0
+    """Enable the simulation-only acknowledged Start/Reset channel (0 disables)."""
+
     # Initial pose
     initial_pose_blend_duration: float = 1.0
     """Duration (seconds) for smooth interpolation to initial pose. The robot
@@ -215,6 +218,8 @@
     robot_model,
     language_prompt: str,
     log_errors: bool = False,
+    minimum_image_timestamp: float = 0.,
+    sensor_status: dict | None = None,
 ):
     """Read sensors and prepare observation for the VLA policy.
 
@@ -227,6 +232,12 @@
             print("[DEBUG] prepare_observation: waiting for camera msg..", flush=True)
         return None
 
+    if minimum_image_timestamp:
+        timestamp = float(camera_msg.get('timestamps', {}).get('ego_view', 0.))
+        if timestamp < minimum_image_timestamp or not 0. <= time.time()-timestamp < 1.:
+            return None
+        if sensor_status is not None:
+            sensor_status['image_timestamp'] = timestamp
     state_msg = state_subscriber.get_msg()
     if state_msg is None:
         if log_errors:
@@ -318,7 +329,7 @@
     while not stop_event.is_set():
         try:
             try:
-                inference_queue.get(timeout=0.1)
+                requested_at = inference_queue.get(timeout=0.1)
             except queue.Empty:
                 continue
 
@@ -329,7 +340,8 @@
                     print("[DEBUG] Worker thread: Observation is None, skipping", flush=True)
                     continue
 
-                inference_start_time = time.monotonic()
+                # Preserve the pre-reset request boundary even if preparing sensors blocks.
+                inference_start_time = requested_at
                 processed_action = inference_fn(observation)
 
                 if processed_action is not None:
@@ -413,7 +425,7 @@
     initial_pose_left_hand_closed = False
     initial_pose_right_hand_closed = False
 
-    def publish_initial_pose():
+    def publish_initial_pose(wait=True):
         """Publish initial pose command to move robot to starting position."""
         print("Moving to initial pose")
         left_hand = (
@@ -434,7 +446,8 @@
         )
         zmq_socket.send(zmq_message)
         print_green("Sent latent initial pose via ZMQ")
-        time.sleep(1.0)
+        if wait:
+            time.sleep(1.0)
         print("Initial pose done.")
 
     def blend_to_initial_pose(duration_s: float) -> bool:
@@ -519,6 +532,7 @@
     cached_action_chunk = None
     action_chunk_index = 0
     last_inference_time = 0.0
+    accept_results_after = time.monotonic()
     inference_interval = 1.0 / config.rate
 
     zmq_frame_counter = 0
@@ -612,6 +626,67 @@
     inference_stop_event = threading.Event()
     inference_busy_event = threading.Event()
 
+    from gear_sonic.utils.inference.simulation_controls import SimulationControlChannel
+    simulation_channel = SimulationControlChannel(config.sim_control_port) if config.sim_control_port else None
+    minimum_image_timestamp = [0.]
+    sensor_status = {}
+    simulation_preparing = False
+    last_initial_pose_publish = 0.
+    last_status_publish = 0.
+
+    def clear_policy_actions():
+        nonlocal cached_action_chunk, action_chunk_index, last_inference_time
+        nonlocal accept_results_after, zmq_frame_counter, last_sent_motion_token
+        accept_results_after = time.monotonic()
+        cached_action_chunk, action_chunk_index, last_inference_time = None, 0, 0.
+        zmq_frame_counter, last_sent_motion_token = 0, None
+        sensor_status.clear()
+        for channel in (inference_queue, result_queue):
+            while True:
+                try:
+                    channel.get_nowait()
+                except queue.Empty:
+                    break
+
+    def check_simulation_input():
+        nonlocal pause_loop, simulation_preparing, last_initial_pose_publish, last_status_publish
+        nonlocal initial_pose_left_hand_closed, initial_pose_right_hand_closed
+        if simulation_channel is None:
+            return
+        while (message := simulation_channel.receive()) is not None:
+            command, ok, error = message.get('command'), True, ''
+            if command in ('pause', 'prepare', 'start'):
+                pause_loop = True
+                clear_policy_actions()
+                simulation_preparing = command == 'prepare'
+                if simulation_preparing:
+                    initial_pose_left_hand_closed = initial_pose_right_hand_closed = False
+                    publish_initial_pose(wait=False)
+                    ok = send_cpp_control_command(start=True, planner=False)
+                    last_initial_pose_publish = time.monotonic()
+                elif command == 'start':
+                    minimum_image_timestamp[0] = time.time()
+                    pause_loop = False
+            else:
+                ok, error = False, 'Unknown simulation command'
+            simulation_channel.send({'type': 'ack', 'id': message.get('id'), 'ok': ok, 'error': error})
+        now = time.monotonic()
+        if simulation_preparing and now-last_initial_pose_publish > .5:
+            publish_initial_pose(wait=False)
+            send_cpp_control_command(start=True, planner=False)
+            last_initial_pose_publish = now
+        if not pause_loop:
+            last_image = sensor_status.get('image_timestamp', 0.)
+            stale = (last_image and time.time()-last_image > 1.)
+            waiting_too_long = not last_image and time.time()-minimum_image_timestamp[0] > 5.
+            if stale or waiting_too_long:
+                pause_loop = True
+                clear_policy_actions()
+        if now-last_status_publish > .1:
+            simulation_channel.send({'type': 'status', 'paused': pause_loop,
+                'actions_published': zmq_frame_counter, **sensor_status})
+            last_status_publish = now
+
     inference_worker_thread = threading.Thread(
         target=_inference_worker_loop,
         args=(
@@ -625,6 +700,8 @@
                 robot_model=robot_model,
                 language_prompt=language_prompt_ref[0],
                 log_errors=True,
+                minimum_image_timestamp=minimum_image_timestamp[0] if simulation_channel else 0.,
+                sensor_status=sensor_status,
             ),
             lambda obs: run_policy_inference_and_process(
                 policy=n1_policy,
@@ -639,15 +716,20 @@
     try:
         while True:
             t_start = time.monotonic()
-            check_keyboard_input()
+            check_simulation_input()
+            if simulation_channel is None:
+                check_keyboard_input()
 
             # Consume result first so last_inference_time is fresh before trigger check
             try:
                 processed_action, inference_start_time = result_queue.get_nowait()
+                if pause_loop or inference_start_time < accept_results_after:
+                    _sleep_remaining(t_start, loop_period)
+                    continue
                 inference_delay = time.monotonic() - inference_start_time
-                action_chunk_index = calculate_latency_compensated_index(
+                action_chunk_index = (calculate_latency_compensated_index(
                     inference_delay, config.action_publish_rate, config.action_horizon
-                )
+                ) if cached_action_chunk is not None else 0)
                 cached_action_chunk = processed_action
                 last_inference_time = time.monotonic()
                 print_green(
@@ -665,9 +747,9 @@
                 inference_interval=inference_interval,
             )
 
-            if should_start:
+            if should_start and not pause_loop:
                 try:
-                    inference_queue.put_nowait(None)
+                    inference_queue.put_nowait(time.monotonic())
                 except queue.Full:
                     pass
 
@@ -755,6 +837,8 @@
         print("VLA inference loop terminated by user")
 
     finally:
+        if simulation_channel is not None:
+            simulation_channel.close()
         inference_stop_event.set()
         inference_worker_thread.join(timeout=1.0)
         zmq_socket.close()
--- a/gear_sonic/scripts/launch_inference.py
+++ b/gear_sonic/scripts/launch_inference.py
@@ -397,6 +397,9 @@
         f"--camera-port {config.camera_port}"
     )
 
+    if config.sim:
+        inference_cmd += " --sim-control-port 5581"
+
     print("Starting VLA inference (pane 1)...")
     _send_to_pane(2, inference_cmd, wait=1.0)
 
--- a/gear_sonic/utils/mujoco_sim/unitree_sdk2py_bridge.py
+++ b/gear_sonic/utils/mujoco_sim/unitree_sdk2py_bridge.py
@@ -7,6 +7,7 @@
 
 import sys
 import threading
+import time
 from typing import Dict, Tuple
 
 import numpy as np
@@ -131,6 +132,7 @@
 
     def reset(self):
         with self.low_cmd_lock:
+            self.last_low_cmd_time = 0.
             self.low_cmd_received = False
             self.new_low_cmd = False
         with self.left_hand_cmd_lock:
@@ -143,6 +145,7 @@
     def LowCmdHandler(self, msg):
         with self.low_cmd_lock:
             self.low_cmd = msg
+            self.last_low_cmd_time = time.monotonic()
             self.low_cmd_received = True
             self.new_low_cmd = True
 
--- a/gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/input_interface/zmq_manager.hpp
+++ b/gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/input_interface/zmq_manager.hpp
@@ -370,6 +370,9 @@
                           current_motion_mutex);
       } else {
         // Streamed motion mode: delegate to pose interface
+        if (start_control_ && !stop_control_) {
+          operator_state.start = true;
+        }
         if (pose_interface_) {
           pose_interface_->handle_input(motion_reader, current_motion, current_frame,
                                        operator_state, reinitialize_heading,
--- /dev/null
+++ b/gear_sonic/utils/inference/simulation_controls.py
@@ -0,0 +1,33 @@
+"""Acknowledged simulation commands; independent of policy observations/actions."""
+
+import zmq
+
+
+class SimulationControlChannel:
+    def __init__(self, port=5581, bind=False):
+        self.context = zmq.Context()
+        self.socket = self.context.socket(zmq.PAIR)
+        self.socket.setsockopt(zmq.LINGER, 0)
+        self.socket.setsockopt(zmq.IMMEDIATE, 1)
+        endpoint = f"tcp://127.0.0.1:{port}"
+        if bind:
+            self.socket.bind(endpoint)
+        else:
+            self.socket.connect(endpoint)
+
+    def send(self, message):
+        try:
+            self.socket.send_json(message, zmq.NOBLOCK)
+            return True
+        except zmq.Again:
+            return False
+
+    def receive(self):
+        try:
+            return self.socket.recv_json(zmq.NOBLOCK)
+        except zmq.Again:
+            return None
+
+    def close(self):
+        self.socket.close()
+        self.context.term()
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/dex3_controls.py
@@ -0,0 +1,264 @@
+"""Basic Dex3 simulation panel; physics changes run only on the sim thread."""
+import multiprocessing as mp
+import queue
+import time
+import numpy as np
+from gear_sonic.utils.inference.simulation_controls import SimulationControlChannel
+
+
+class Dex3SimulationControls:
+    def __init__(self, env, port=5581, panel=True, channel=None, clock=time.monotonic):
+        if env.mj_model.nu != 43 or not env.ground_start:
+            raise ValueError('Step 3 requires the ground-start Dex3 scene')
+        self.env, self.clock = env, clock
+        self.channel = channel if channel is not None else SimulationControlChannel(port, bind=True)
+        self.serial, self.pending = 0, None
+        self.phase, self.error = 'idle', ''
+        self.status, self.seen = {}, -float('inf')
+        self.started = self.clock()
+        self.joint = env.mj_model.joint('red_bottle_free_joint').id
+        self.qa = int(env.mj_model.jnt_qposadr[self.joint])
+        self.va = int(env.mj_model.jnt_dofadr[self.joint])
+        self.xyz = env.initial_qpos[self.qa:self.qa + 3].copy()
+        top = env.mj_model.geom('pickup_table_top').id
+        centre = env.mj_data.geom_xpos[top, :2]
+        half = env.mj_model.geom_size[top, :2] - .03
+        self.bounds = np.c_[centre - half, centre + half]
+        self.panel = BasicDex3Panel(self.xyz, self.bounds) if panel else None
+        self.last_ui = -float('inf')
+
+    def connected(self):
+        return self.clock() - self.seen < 2.
+
+    def place(self, xy):
+        xy = np.asarray(xy, dtype=float)
+        if xy.shape != (2,) or not np.isfinite(xy).all():
+            raise ValueError('X/Y must be two finite numbers')
+        if np.any(xy < self.bounds[:, 0]) or np.any(xy > self.bounds[:, 1]):
+            raise ValueError('X/Y is outside the tabletop margin')
+        self.xyz[:2] = xy
+        data = self.env.mj_data
+        data.qpos[self.qa:self.qa + 7] = [*self.xyz, 1., 0., 0., 0.]
+        data.qvel[self.va:self.va + 6] = 0.
+
+    def local_reset(self):
+        self.env.reset()
+        self.place(self.xyz[:2].copy())
+        if self.env.unitree_bridge is not None:
+            self.env.unitree_bridge.reset()
+        self.phase = 'idle'
+
+    def request(self, command):
+        self.serial += 1
+        msg = {'command': command, 'id': self.serial}
+        if not self.channel.send(msg):
+            self.abort('VLA connection unavailable; click Reset')
+            return False
+        self.pending = (msg, self.clock())
+        return True
+
+    def abort(self, error):
+        self.pending = None
+        self.local_reset()
+        self.phase, self.error = 'error', error
+        # Best effort: local standby already blocks every motor command.
+        self.serial += 1
+        self.channel.send({'command': 'pause', 'id': self.serial})
+
+    def handle(self, message):
+        command = message.get('command')
+        if command == 'reset':
+            self.pending = None
+            self.local_reset()  # Lock immediately, even if VLA is disconnected.
+            self.error = ''
+            if self.connected() and self.request('pause'):
+                self.phase = 'resetting'
+            return
+        if self.pending is not None:
+            self.error = 'Wait for the previous command, or click Reset'
+            return
+        self.error = ''
+        if command == 'place':
+            if self.phase != 'idle' or not self.env.standby:
+                self.error = 'Click Reset before changing bottle X/Y'
+                return
+            try:
+                self.place(message['xy'])
+            except (KeyError, TypeError, ValueError) as error:
+                self.error = str(error)
+        elif command == 'start':
+            if self.phase != 'idle':
+                return
+            if not self.connected():
+                self.error = 'Start requires the VLA client; check server/client logs'
+                return
+            self.env.unitree_bridge.reset()  # Only post-click LowCmd can count as ready.
+            self.started = self.clock()
+            self.phase = 'preparing'
+            self.request('prepare')
+
+    def poll(self):
+        now = self.clock()
+        while (msg := self.channel.receive()) is not None:
+            if msg.get('type') == 'status':
+                self.status, self.seen = msg, now
+            elif msg.get('type') == 'ack' and self.pending is not None:
+                request, _ = self.pending
+                if msg.get('id') != request['id']:
+                    continue
+                self.pending = None
+                if not msg.get('ok', False):
+                    self.abort(msg.get('error', 'VLA rejected command'))
+                elif request['command'] == 'pause':
+                    self.local_reset()
+                elif request['command'] == 'start':
+                    self.phase, self.started = 'observing', now
+        if self.panel is not None:
+            for _ in range(16):
+                message = self.panel.read()
+                if message is None:
+                    break
+                self.handle(message)
+        if self.pending is not None and now - self.pending[1] > 10.:
+            self.abort('VLA acknowledgement timed out; Reset to retry')
+        if self.phase in ('grounded', 'starting', 'observing', 'running') and self.env.standby:
+            self.abort('Robot returned to standby; Reset before retrying')
+        bridge = self.env.unitree_bridge
+        last_cmd = getattr(bridge, 'last_low_cmd_time', 0.)
+        if self.phase == 'preparing' and self.pending is None:
+            fresh = last_cmd >= self.started and now - last_cmd < .5
+            if self.connected() and fresh and now - self.started >= 2.:
+                self.env.begin_control_transition()
+                self.phase, self.started = 'grounded', now
+            elif now - self.started > 15.:
+                self.abort('SONIC not ready: check Init Done, LowState and LowCmd')
+        elif self.phase == 'grounded' and self.env._control_transition_started is None:
+            if self.connected() and now - last_cmd < .5:
+                if self.request('start'):
+                    self.phase, self.started = 'starting', now
+            else:
+                self.abort('Controller disconnected during startup')
+        elif self.phase == 'observing':
+            if self.status.get('actions_published', 0) > 0 and not self.status.get('paused', True):
+                self.phase = 'running'
+            elif now - self.started > 10.:
+                self.abort('No fresh policy actions; check camera/model/client')
+        if self.phase in ('grounded', 'starting', 'observing', 'running'):
+            if not self.connected() or now - last_cmd > .5:
+                self.abort('VLA/SONIC data stale; robot reset to standby')
+            elif self.phase == 'running' and self.status.get('paused', False):
+                self.abort('Policy paused; Reset to retry')
+        if self.panel is not None and now - self.last_ui > .1:
+            self.panel.update(self.snapshot())
+            self.last_ui = now
+
+    def snapshot(self):
+        data, model = self.env.mj_data, self.env.mj_model
+        return {'phase': self.phase, 'error': self.error,
+                'bottle': data.qpos[self.qa:self.qa + 3].tolist(),
+                'wrist': data.xpos[model.body('right_wrist_yaw_link').id].tolist(),
+                'can_start': self.phase == 'idle' and self.connected() and self.pending is None,
+                'can_place': self.phase == 'idle' and self.pending is None,
+                'client': 'connected' if self.connected() else 'disconnected'}
+
+    def close(self):
+        if self.panel is not None:
+            self.panel.close()
+        self.channel.close()
+
+
+class BasicDex3Panel:
+    def __init__(self, xyz, bounds):
+        context = mp.get_context('spawn')
+        self.commands = context.Queue(maxsize=16)
+        self.snapshots = context.Queue(maxsize=1)
+        self.stop = context.Event()
+        self.process = context.Process(target=_panel_worker,
+            args=(xyz.tolist(), bounds.tolist(), self.commands, self.snapshots, self.stop), daemon=True)
+        self.process.start()
+
+    def read(self):
+        try:
+            return self.commands.get_nowait()
+        except queue.Empty:
+            return None
+
+    def update(self, state):
+        try:
+            self.snapshots.put_nowait(state)
+        except queue.Full:
+            pass
+
+    def close(self):
+        self.stop.set()
+        self.process.join(timeout=2.)
+        if self.process.is_alive():
+            self.process.terminate()
+            self.process.join(timeout=1.)
+        for q in (self.commands, self.snapshots):
+            q.cancel_join_thread()
+            q.close()
+
+
+def _panel_worker(xyz, bounds, commands, snapshots, stop):
+    import tkinter as tk
+    from tkinter import ttk
+    try:
+        root = tk.Tk()
+    except tk.TclError as error:
+        print('Cannot open simulation panel:', error, flush=True)
+        return
+    root.title('Dex3 - Bottle / Start / Reset')
+    frame = ttk.Frame(root, padding=16)
+    frame.pack(fill='both', expand=True)
+    ttk.Label(frame, text='Bottle X/Y on table (metres)').pack(anchor='w')
+    row = ttk.Frame(frame)
+    row.pack(pady=8)
+    x, y = tk.StringVar(value=f'{xyz[0]:.3f}'), tk.StringVar(value=f'{xyz[1]:.3f}')
+    for label, value in (('X', x), ('Y', y)):
+        ttk.Label(row, text=label).pack(side='left', padx=4)
+        ttk.Entry(row, textvariable=value, width=10).pack(side='left', padx=4)
+    ttk.Label(frame, text=f'Initial bottle Z = {xyz[2]:.3f} m (table-fixed)').pack(anchor='w')
+    ttk.Label(frame, text=f'X: {bounds[0]}   Y: {bounds[1]}').pack(anchor='w')
+    info, error = tk.StringVar(value='Waiting for simulation...'), tk.StringVar()
+
+    def send(command):
+        try:
+            msg = {'command': command}
+            if command == 'place':
+                msg['xy'] = [float(x.get()), float(y.get())]
+            commands.put_nowait(msg)
+        except (ValueError, queue.Full):
+            error.set('Enter numeric X/Y, or wait for the previous command')
+
+    apply_button = ttk.Button(frame, text='Apply X/Y', command=lambda: send('place'))
+    apply_button.pack(fill='x', pady=6)
+    start_button = ttk.Button(frame, text='Start', command=lambda: send('start'), state='disabled')
+    start_button.pack(fill='x', pady=6)
+    ttk.Button(frame, text='Reset robot + bottle', command=lambda: send('reset')).pack(fill='x', pady=6)
+    ttk.Label(frame, textvariable=info, justify='left').pack(anchor='w', pady=8)
+    ttk.Label(frame, textvariable=error, foreground='red', wraplength=420).pack(anchor='w')
+    ttk.Label(frame, text='Bottle XYZ is simulation state, not model detection.').pack(anchor='w')
+    ttk.Label(frame, text='Start runs the controller; automatic pickup comes later.').pack(anchor='w')
+
+    def refresh():
+        if stop.is_set():
+            root.destroy()
+            return
+        state = None
+        while True:
+            try:
+                state = snapshots.get_nowait()
+            except queue.Empty:
+                break
+        if state is not None:
+            fmt = lambda values: ' '.join(f'{v:+.3f}' for v in values)
+            info.set(f"State: {state['phase']} | VLA: {state['client']}\n"
+                     f"Bottle XYZ: {fmt(state['bottle'])}\nRight wrist XYZ: {fmt(state['wrist'])}")
+            error.set(state['error'])
+            start_button.configure(state='normal' if state['can_start'] else 'disabled')
+            apply_button.configure(state='normal' if state['can_place'] else 'disabled')
+        root.after(75, refresh)
+
+    refresh()
+    root.mainloop()
```
<!-- STEP03-PATCH-END -->

## 6. Vì sao tách UI khỏi physics và dùng ack?

Panel chỉ gửi `place/start/reset` qua queue. `BaseSimulator.start()` nhận lệnh
rồi mới thay dữ liệu MuJoCo. Tkinter không chạm trực tiếp `mj_data` từ thread
khác. Đóng panel không đóng viewer; muốn mở lại panel ở bản vá tối thiểu này,
khởi động lại simulator. Cleanup simulator dừng process panel và đóng socket.

Kênh 5581 dùng ID cho từng request; Reset có thể thay thế một Start chưa xong,
và ack cũ không được hoàn tất lệnh mới. VLA phát heartbeat; controller được
kiểm tra bằng timestamp LowCmd. Chưa có dữ liệu mới thì giữ robot, không giả
định kết nối thành công chỉ vì socket đã được tạo.

Trong VLA, mốc request được lưu **trước khi chuẩn bị observation**, vì worker
có thể đang chờ sensor khi người dùng Reset. Kết quả cũ không được đổi nhãn
thành kết quả mới chỉ vì inference bắt đầu muộn hơn. Chunk đầu sau Start phát
từ action đầu tiên, không bù trễ bỏ mất đoạn tiếp cận khi trước đó robot đang chờ.

Ảnh phải mới hơn thời điểm Start, tuổi dưới 1 giây. Bản tối thiểu dùng timestamp
wall-clock của camera và giả định simulator/camera/client cùng PC. Đồng bộ ảnh
với snapshot proprioception chính xác hơn là cải tiến riêng ở bước sau.

Khi panel đang quản lý, VLA bỏ qua phím keyboard publisher để tránh trộn
Start/Reset với `k/i/p`. Không bấm phím 9 để bắt đầu. Dây đàn hồi vẫn tắt.

Nếu quá hạn ack, mất VLA, LowCmd cũ hoặc robot tự trở về standby vì ngã, phần
điều khiển trở về local reset/standby và hiện lỗi. Đây là hành vi simulation,
không phải cơ chế dừng khẩn dùng được cho robot thật.

## 7. Kiểm tra môi trường và build C++ sau khi áp patch

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python -c "import tkinter, mujoco, zmq; print('Simulator dependencies OK')"
.venv_inference/bin/python -c "import zmq; from gr00t.policy.server_client import PolicyClient; print('VLA dependencies OK')"
.venv_sim/bin/python gear_sonic/scripts/run_sim_loop.py --help
.venv_inference/bin/python gear_sonic/scripts/run_vla_inference.py --help
```

Nếu thiếu Tkinter trên Ubuntu, cài `sudo apt install python3-tk`; với Python do
uv quản lý vẫn cần kiểm tra import như trên, không coi apt cài xong là đủ.

**Có sửa header C++, cần build lại:**

```bash
cd ~/projects/GR00T-WholeBodyControl/gear_sonic_deploy
source scripts/setup_env.sh
just build
```

Không chỉ sửa Python rồi dùng binary C++ cũ: luồng bật POSE từ Start cần phần
chuyển tiếp cờ đã sửa trong `zmq_manager.hpp`.

## 8. Các lệnh chạy

### 8.1. Xem panel và thử Apply/Reset mà chưa bật policy

Trên bản clone đã áp bước 3:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python gear_sonic/scripts/run_sim_loop.py --ground-start
```

Panel hiện, robot giữ tư thế. Nhập ví dụ X = 0.40, Y = -0.15 rồi Apply. Reset
dựng lại chai tại XY đã Apply. **Start bị vô hiệu hóa khi chưa có VLA client**;
đây là hành vi đúng, không phải giao diện hỏng. Z hiển thị trong ô mô tả là Z
khởi tạo; Z thực tế có thể thấp hơn một chút khi chai ổn định trên mặt bàn.

### 8.2. Chạy đầy đủ luồng Start/Reset trên bản clone đã áp patch

Đóng lượt chỉ xem panel ở trên để tránh hai simulator cùng port/domain.
Terminal 1 — server v10 đã cài theo hướng dẫn WSL (nếu server đúng model đã chạy,
giữ nguyên, không nạp thêm):

```bash
cd ~/projects/Isaac-GR00T
.venv/bin/python gr00t/eval/run_gr00t_server.py \
  --model-path "$HOME/projects/GR00T-WholeBodyControl/checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000" \
  --embodiment-tag UNITREE_G1_SONIC \
  --device cuda:0 --host 127.0.0.1 --port 5550
```

Terminal 2 — launcher của bản clone đã áp bước 3:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter --prompt "grab the bottle"
```

Trong pane C++ deploy, trả lời `y` nếu được hỏi `Proceed with deployment?`.
Chờ **Init Done**. Bản vá tối thiểu chưa thêm tự xác nhận prompt của launcher.
Sau đó:

1. Nhập X/Y và Apply trong panel khi robot đang idle.
2. Start sáng khi VLA kết nối. Bấm một lần, chờ preparing → grounded → running.
3. Robot bắt đầu nhận action checkpoint. Chưa có logic hỗ trợ nắm/nâng chai.
4. Reset để dừng lượt và quay lại tư thế chờ, rồi có thể đổi XY và Start lại.
5. Nếu báo SONIC/camera không sẵn sàng, đọc pane tương ứng rồi Reset để thử lại;
   không bấm `k/i/p` để vượt qua trạng thái lỗi.

Khi làm tiếp bước gắp, phải kiểm chứng tương thích action bàn tay của checkpoint
với Dex3. Giao diện hoạt động không phải bằng chứng ánh xạ bàn tay đã đúng.

### 8.3. Chạy trên workspace hiện tại đã có giao diện đầy đủ

Không áp patch mục 5. Để kiểm tra panel với robot Dex3 và chưa bật các phần gắp:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter --no-bottle-detection --sim-grasp-distance 0 \
  --prompt "grab the bottle"
```

Hai cờ `--no-bottle-detection --sim-grasp-distance 0` là của workspace hiện tại,
không có trong bản vá tối thiểu bước 3. Giao diện hiện tại có thêm mục từ các
bước về sau; ở bước 3 chỉ kiểm tra nhập XY, Start và Reset. Luôn có `--sim`.

## 9. Kiểm thử headless cho bản clone đã áp patch bước 3

Các phép thử dưới không chạy GUI, không nạp trọng số, không tạo kết nối robot.
Chúng dùng bridge/channel giả để kiểm tra tính hợp lệ của XY, Start chờ dữ liệu,
blend 2 giây, Reset, timeout, ảnh cũ và request cũ. Đây không phải kiểm thử
chuyển động gắp hay kiểm thử live YOLO/VLA/C++.

Trên **bản clone đã áp patch bước 3**, chạy:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python - <<'PYTEST'
from pathlib import Path
from types import SimpleNamespace
import sys, unittest, importlib.util
import mujoco
import numpy as np
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig

from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
from gear_sonic.utils.mujoco_sim.dex3_controls import Dex3SimulationControls as Controls

class Channel:
    def __init__(self): self.messages=[]; self.sent=[]; self.closed=False
    def receive(self): return self.messages.pop(0) if self.messages else None
    def send(self,msg): self.sent.append(msg); return True
    def close(self): self.closed=True

class Bridge:
    joystick=None; last_low_cmd_time=0.; low_cmd_received=False; low_cmd=None
    def reset(self): self.last_low_cmd_time=0.; self.low_cmd_received=False
    def PublishLowState(self,obs): pass

class PanelLogicTest(unittest.TestCase):
    def setUp(self):
        config=SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
        config.update(GROUND_START=True,ASSISTED_PICKUP=False,FIXED_PICKUP_BASE=False,SIM_CONTROLS=False)
        self.env=DefaultEnv(config,onscreen=False)
        self.env.set_unitree_bridge(Bridge())
        self.now=100.
        self.channel=Channel()
        self.ui=Controls(self.env,panel=False,channel=self.channel,clock=lambda:self.now)
    def status(self, **kw):
        self.channel.messages.append({'type':'status','paused':True,'actions_published':0,**kw})
    def ack(self):
        self.channel.messages.append({'type':'ack','id':self.ui.pending[0]['id'],'ok':True})
    def test_place_checks_limits_and_keeps_robot_and_z(self):
        data=self.env.mj_data
        robot=data.qpos[:self.ui.qa].copy()
        self.ui.handle({'command':'place','xy':[.40,-.15]})
        np.testing.assert_array_equal(data.qpos[:self.ui.qa],robot)
        np.testing.assert_allclose(data.qpos[self.ui.qa:self.ui.qa+3],[.40,-.15,.801])
        for xy in ([float('nan'),0.],[.2,-.1],[.4,5.]):
            self.ui.handle({'command':'place','xy':xy})
            self.assertTrue(self.ui.error)
        self.assertEqual(self.ui.xyz[0],.40)
    def test_start_without_client_or_controller_does_not_release_robot(self):
        self.ui.handle({'command':'start'})
        self.assertTrue(self.env.standby)
        self.assertIn('requires',self.ui.error)
        self.status(); self.ui.poll()
        self.ui.handle({'command':'start'})
        self.assertEqual(self.ui.phase,'preparing')
        self.ack(); self.ui.poll()
        self.now+=16.; self.status(); self.ui.poll()
        self.assertTrue(self.env.standby)
        self.assertEqual(self.ui.phase,'error')
    def test_prepare_ramp_start_and_reset_supersedes_old_ack(self):
        self.status(); self.ui.poll()
        self.env.unitree_bridge.last_low_cmd_time=99.  # old commands must be cleared.
        self.ui.handle({'command':'start'})
        self.assertEqual(self.env.unitree_bridge.last_low_cmd_time,0.)
        self.ack(); self.ui.poll()
        self.now+=2.1
        self.env.unitree_bridge.last_low_cmd_time=self.now
        self.status(); self.ui.poll()
        self.assertEqual(self.ui.phase,'grounded')
        self.assertFalse(self.env.standby)
        body,hands=np.full(29,4.),np.full(14,2.)
        start,_=self.env.blend_startup_torques(body,hands)
        self.env.mj_data.time+=1.
        middle,_=self.env.blend_startup_torques(body,hands)
        np.testing.assert_allclose(middle,.5*(start+body))
        self.env.mj_data.time+=1.1
        final,_=self.env.blend_startup_torques(body,hands)
        np.testing.assert_allclose(final,body)
        self.status(); self.ui.poll()
        self.assertEqual(self.ui.pending[0]['command'],'start')
        self.ack(); self.ui.poll()
        self.status(paused=False,actions_published=1); self.ui.poll()
        self.assertEqual(self.ui.phase,'running')
        self.ui.handle({'command':'reset'})
        pause_id=self.ui.pending[0]['id']
        self.assertTrue(self.env.standby)
        self.channel.messages.append({'type':'ack','id':pause_id-1,'ok':True})
        self.ui.poll()
        self.assertIsNotNone(self.ui.pending)
        self.ack(); self.ui.poll()
        self.assertEqual(self.ui.phase,'idle')
        self.assertIsNone(self.env._control_transition_started)
    def test_reset_disconnected_keeps_applied_xy_and_physics_free(self):
        self.ui.handle({'command':'place','xy':[.40,-.15]})
        self.env.mj_data.qpos[self.ui.qa+3:self.ui.qa+7]=[0.,1.,0.,0.]
        self.ui.handle({'command':'reset'})
        self.assertTrue(self.env.standby)
        np.testing.assert_allclose(self.env.mj_data.qpos[self.ui.qa:self.ui.qa+7],[.4,-.15,.801,1,0,0,0])
        self.env.mj_data.qpos[self.ui.qa+2]+=.03
        for _ in range(1000): self.env.sim_step()
        np.testing.assert_array_equal(self.env.mj_data.qpos[:self.ui.qa],self.env.initial_qpos[:self.ui.qa])
        self.assertLess(self.env.mj_data.qpos[self.ui.qa+2],.805)
    def test_pending_timeout_and_runtime_disconnect_return_to_standby(self):
        self.status(); self.ui.poll(); self.ui.handle({'command':'start'})
        self.now+=11.; self.ui.poll()
        self.assertTrue(self.env.standby)
        self.assertEqual(self.ui.phase,'error')
        self.ui.phase='running'; self.env.standby=False
        self.now+=3.; self.ui.poll()
        self.assertTrue(self.env.standby)
        self.assertEqual(self.ui.phase,'error')

if __name__ == '__main__': unittest.main()
PYTEST
```

Kiểm tra riêng VLA bằng môi trường inference (không cần MuJoCo trong venv này):

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python - <<'PYTESTVLA'
import unittest
import numpy as np

import queue, threading, time
from gear_sonic.data.robot_model.instantiation.g1 import instantiate_g1_robot_model
from gear_sonic.scripts import run_vla_inference as vla

class VLAStartResetTest(unittest.TestCase):
    def test_old_camera_is_rejected_before_state_read(self):
        class Camera:
            def read(self):
                return {'timestamps':{'ego_view':time.time()-2.}}
        class State:
            def get_msg(self): raise AssertionError('stale camera must not read state')
        self.assertIsNone(vla.prepare_observation_from_sensors(Camera(),State(),None,'grab the bottle',minimum_image_timestamp=time.time()))
    def test_fresh_camera_after_start_builds_observation(self):
        robot=instantiate_g1_robot_model(waist_location='lower_and_upper_body')
        boundary=time.time()-.1
        class Camera:
            def read(self):
                return {'images':{'ego_view':np.zeros((480,640,3),np.uint8)},'timestamps':{'ego_view':time.time()}}
        class State:
            def get_msg(self):
                return {'body_q':[0.]*29,'left_hand_q':[0.]*7,'right_hand_q':[0.]*7,'base_quat':[1.,0.,0.,0.]}
        status={}
        result=vla.prepare_observation_from_sensors(Camera(),State(),robot,'grab the bottle',minimum_image_timestamp=boundary,sensor_status=status)
        self.assertIsNotNone(result)
        self.assertGreater(status['image_timestamp'],boundary)
        self.assertEqual(result['state']['right_hand'].shape[-1],7)
    def test_reset_cannot_relabel_inflight_request_as_fresh(self):
        requests,results=queue.Queue(),queue.Queue()
        stop,busy,entered,release=(threading.Event() for _ in range(4))
        def prepare():
            entered.set(); release.wait(timeout=2.)
            return {'frame':True}
        thread=threading.Thread(target=vla._inference_worker_loop,args=(requests,results,stop,busy,prepare,lambda o:{'action':True}))
        requested_at=time.monotonic(); requests.put(requested_at); thread.start()
        try:
            self.assertTrue(entered.wait(timeout=2.))
            reset_at=time.monotonic(); release.set()
            _,boundary=results.get(timeout=2.)
            self.assertEqual(boundary,requested_at)
            self.assertLess(boundary,reset_at)
        finally:
            stop.set();release.set();thread.join(timeout=2.)
        self.assertFalse(thread.is_alive())

if __name__=='__main__': unittest.main()
PYTESTVLA
```

Trên workspace hiện tại, API khác bản vá tối thiểu; dùng các kiểm thử hiện có
thay cho khối trên:

```bash
.venv_sim/bin/python -m unittest gear_sonic.tests.test_simulation_controls
.venv_inference/bin/python -m unittest gear_sonic.tests.test_observation_freshness
```

### Phạm vi kiểm chứng của tài liệu

- Patch áp nối tiếp được lên code gốc đã có đúng bản vá bước 2; các file Python
  được kiểm tra cú pháp.
- **8 kiểm thử headless đã qua**: 5 kiểm tra panel/physics với channel và DDS
  bridge giả, 3 kiểm tra observation/inference worker. Đã chạy chính code test
  nhúng trong tài liệu với các module từ cây source thử nghiệm đã áp patch.
- Ảnh cũ và kết quả inference đang xử lý trước Reset được kiểm tra riêng.
- Chưa kiểm thử một lượt GUI + server v10 + C++ từ đầu trong bản clone tối thiểu
  này; không coi các test headless là xác nhận robot sẽ chạy/gắp thành công.
- Các gain, pose và phần khóa trạng thái chỉ dành cho simulation.

## 10. Lỗi thường gặp

| Hiện tượng | Cách kiểm tra |
|---|---|
| Không có cửa sổ panel | Tkinter, WSLg/DISPLAY; chạy đúng simulator Python, không dùng viewer XML thuần |
| Start không sáng | Chưa chạy client, client lỗi import/model hoặc port 5581 chưa kết nối |
| Preparing rồi báo SONIC not ready | Đã xác nhận C++ prompt chưa; có Init Done và LowCmd mới chưa; đã build header sửa chưa |
| Báo camera không có action mới | Camera 5555, timestamp mới sau Start, server 5550, lỗi model trong pane VLA |
| Đổi XY khi đang chạy bị từ chối | Reset về idle, chờ ack rồi Apply lại |
| X/Y từ chối | Dùng dấu chấm thập phân, kiểm tra biên mặt bàn; không nhập NaN/inf |
| Reset khi mất client | Local scene vẫn được khóa/reset; nối lại VLA rồi chờ trạng thái kết nối |
| Port đã được dùng | Kiểm tra `ss -ltnp`, chỉ một simulator/client/launcher cho bộ port |
| Robot chuyển động nhưng chưa gắp | Đúng phạm vi: bước 3 chỉ nối giao diện và luồng điều khiển; chưa có bài gắp hoàn chỉnh |
| `git apply` báo file đã tồn tại | Có thể đang dùng workspace đã có phần UI; không áp chồng |

Bước 3 hoàn thành khi có thể nhập XY, Start theo điều kiện sẵn sàng và Reset
trở lại chờ; chai giữ vị trí đã Apply. Bước sau mới thêm nhận diện và hoàn thiện
động tác tiếp cận–nắm–nâng bằng Dex3.
