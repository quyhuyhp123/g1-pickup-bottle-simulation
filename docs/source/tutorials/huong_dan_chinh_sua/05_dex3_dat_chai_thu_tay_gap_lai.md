# Bước 5 — Đặt chai theo tọa độ, mở tay, thu tay và gắp lại bằng Dex3

Hoàn tất phần mô phỏng có hỗ trợ để có một bộ hướng dẫn có thể chia sẻ trước
khi chuyển sang phương án điều khiển khác. **Chỉ bổ sung tài liệu; không áp code
vào workspace hiện tại và không tự commit/push GitHub.**

## 1. Bộ tài liệu và phạm vi phiên bản này

| Thứ tự | Nội dung |
|---|---|
| [Bước 1](01_them_ban_va_chai_vat_ly.md) | Bàn và chai có tương tác vật lý |
| [Bước 2](02_dex3_dung_dat_giu_tu_the_cho.md) | Robot đứng dưới đất, giữ tư thế chờ |
| [Bước 3](03_dex3_giao_dien_toa_do_start_reset.md) | Nhập XY, Start và Reset |
| [Bước 4](04_dex3_nhan_dien_nam_nang_chai.md) | YOLO RGB-D, IK tiếp cận–nắm–nâng |
| **Bước 5 — tài liệu này** | Đặt theo XY, mở ngón, thu tay, Start gắp lượt tiếp |

Tất cả dùng **G1 + Dex3, 43 actuator**. Bản clone mới cần dựa trên commit
`b042411fae38ee4d1af9aac82a37a1f8d14d6dd0`, hoàn thành bước 1 rồi áp lần lượt
patch 2 → 3 → 4 → 5. Phần cài WSL/GPU/môi trường và tải v10 xem
[WSL_UPSTREAM_V10_SETUP.md](../WSL_UPSTREAM_V10_SETUP.md); chọn phần cài đặt,
sau đó dùng đúng lệnh Dex3 của loạt tài liệu này.

### Vai trò thực tế của các thành phần

**Đây là bản mô phỏng hỗ trợ, chưa phải đánh giá GR00T v10/SONIC tự gắp và đặt.**

- YOLO + depth/calibration cung cấp vị trí bề mặt chai cho bước gắp.
- RGB-D/IK và logic contact thực hiện tiếp cận, khép ngón, nâng, đặt và thu tay.
- Pelvis được cố định trong suốt động tác; thân/các khớp ngoài nhiệm vụ được giữ.
- GR00T v10 vẫn chạy suy luận, nhưng action dự đoán được thay bằng token đứng
  và lệnh tay trung tính trong chế độ hỗ trợ trước khi thực thi.
- MuJoCo áp controller hỗ trợ thay cho lệnh thân/tay tương ứng của SONIC.
- Chai không bị weld vào tay và không được teleport khi gắp/đặt. Apply/Reset là
  thao tác khởi tạo scene và có thể đặt lại tọa độ tức thời.

Giữ nguyên phạm vi này để chia sẻ phần đang có. Việc khôi phục luồng action
GR00T → SONIC làm điều khiển chính là lần sửa khác, chưa thực hiện ở bước 5.
Không dùng chu trình đặt này làm bằng chứng v10 đã học được tác vụ đặt chai.

## 2. Kết quả sau bước 5

Giao diện bổ sung:

```text
Bottle position X/Y     ← vị trí khởi tạo, Apply khi chờ
[Apply X/Y] [Start] [Reset robot + bottle]

Place destination X/Y   ← đích đặt trong lượt đang cầm
[Lower / Place on table]
```

Luồng đầy đủ:

```text
Start → detect → approach → close → lift → hold → success
                                                    ↓ nhấn Lower
transfer → lower → release → retreat → return_home → complete
                                                       ↓
                                         Start bật lại để gắp tiếp
```

Nút Lower chỉ sáng khi đang giữ grasp thành công. Nút Start sáng lại sau khi
đặt xong **và đã thu tay**, không sáng ngay khi vừa mở ngón.

## 3. Phân biệt tọa độ khởi tạo và đích đặt

| Ô nhập | Khi nào dùng | Tác dụng |
|---|---|---|
| Bottle position X/Y | Idle, sau Reset | Apply dựng chai đứng tại XY này; Reset về lại XY đã Apply |
| Place destination X/Y | Đã nâng và đang giữ chai | Lower di chuyển tay đang cầm chai để đặt xuống đích mới |

Z của vị trí khởi tạo vẫn là 0,801 m theo scene bước 1. Khi đặt vật lý, không
ấn định lại `qpos` chai; controller hạ tay và kiểm tra mặt bàn thực sự đỡ chai.

Đơn vị mét, hệ tọa độ world của scene. Ví dụ:

```text
Khởi tạo: X = 0.43, Y = -0.11
Đích đặt: X = 0.45, Y = -0.05
```

Nhập X = 0.45 và Y = -0.05 vào **Place destination**, rồi Lower. Không bấm Apply
để di chuyển một chai đang nằm trong tay. Sau khi complete, Start sẽ nhận diện
lại chai tại vị trí mới, không kéo nó về XY khởi tạo.

Biên đầu vào có chừa 3 cm từ mép bàn: X = 0,28..0,72; Y = -0,42..0,42 m.
Đích trong biên bàn vẫn có thể ngoài tầm tay: phải qua kiểm tra IK trước khi di
chuyển. Nên thử các đích gần vị trí gắp trước.

## 4. Cách controller đặt và thu tay

1. **Kiểm tra đích:** số hữu hạn, trong biên bàn và có nghiệm IK phù hợp cho
   cả điểm cao/điểm thấp. Nếu thất bại, từ chối lệnh; không mở tay hoặc đổi stage.
2. **Transfer:** giữ ngón khép, chuyển chai sang phía đích ở trên cao.
3. **Lower:** nội suy xuống gần mặt bàn. Nếu còn khe hở nhỏ, dò xuống tốc độ
   3 mm/s, tối đa thêm 2 cm. Không có lực đỡ bàn thì không nhả chai.
4. **Release:** chỉ mở tay sau khi contact bàn–thân chai có lực đỡ đủ lớn.
5. **Xác nhận đặt:** chai còn được bàn đỡ, hướng đứng có `Rzz > 0.95`, sai số
   XY nhỏ hơn 2,5 cm. Nếu không đạt thì failed, không bật Start như thể đã xong.
6. **Retreat:** bàn tay mở lùi khoảng 9 cm và nhích lên để tránh quệt chai.
7. **Return home:** đưa eo/cánh tay phải về cấu hình trước lượt gắp, kiểm tra
   sai số khớp dưới 0,05 rad rồi mới báo complete.
8. **Gắp tiếp:** Start xóa target/detection cũ, chờ frame mới rồi chạy lại gắp.
   Giữ scene đang có và không reset vị trí chai/robot hoặc khởi động lại server.

Nếu chai tuột khi đang giữ sau success, trạng thái chuyển failed và Lower bị
vô hiệu hóa. Reset có thể ngắt chu trình bất cứ lúc nào; đó là reset simulation,
không phải một cách đặt chai trong vật lý.

## 5. File cần thêm/sửa so với sau bước 4

| Loại | File | Nội dung |
|---|---|---|
| Sửa | `gear_sonic/utils/mujoco_sim/dex3_pickup.py` | IK đích đặt, transfer/lower/release/retreat/home/complete |
| Sửa | `gear_sonic/utils/mujoco_sim/dex3_controls.py` | Đích X/Y thứ hai, nút Lower, trạng thái Start sau complete, gắp lại |
| Thêm | `gear_sonic/utils/mujoco_sim/object_reset.py` | Kiểm tra vị trí chai trên bàn và helper reset vật tự do |

Không đổi checkpoint, không thêm model nhận diện, không sửa thêm C++ hoặc XML
ở bước này. Bước 3 vẫn phải được build C++ như hướng dẫn của nó.

## 6. Áp patch nối tiếp bước 4 trên bản clone mới

Nếu workspace hiện tại đã có Lower/đặt/thu tay, **không áp lại patch**. Các file
trong workspace hiện tại đã được mở rộng khác bản tối thiểu của bộ hướng dẫn.

Trên bản clone đang theo tuần tự bước 1–4, dừng simulator/client/C++ của bản
clone đó trước khi áp. Server v10 đang chạy đúng thì có thể giữ nguyên.

### 6.1. Sao lưu hai file được sửa

```bash
cd ~/projects/GR00T-WholeBodyControl
cp -n gear_sonic/utils/mujoco_sim/dex3_pickup.py \
  gear_sonic/utils/mujoco_sim/dex3_pickup.py.before_step05
cp -n gear_sonic/utils/mujoco_sim/dex3_controls.py \
  gear_sonic/utils/mujoco_sim/dex3_controls.py.before_step05
```

### 6.2. Trích patch từ chính tài liệu này

```bash
cd ~/projects/GR00T-WholeBodyControl
python3 - <<'PYAPPLY'
from pathlib import Path
import subprocess
p = Path('docs/source/tutorials/huong_dan_chinh_sua/05_dex3_dat_chai_thu_tay_gap_lai.md')
s = p.read_text()
begin = '<!-- STEP05-PATCH-BEGIN -->' + '\n```diff\n'
end = '\n```\n<!-- STEP05-PATCH-END -->'
patch = s.split(begin, 1)[1].split(end, 1)[0] + '\n'
subprocess.run(['git', 'apply', '--check', '-'], input=patch, text=True, check=True)
subprocess.run(['git', 'apply', '-'], input=patch, text=True, check=True)
print('Da ap buoc 5. Chay test truoc khi thu giao dien.')
PYAPPLY
```

Nếu báo file đã tồn tại hoặc patch không khớp, đối chiếu trạng thái sau bước 4;
không force/reset hard để ghi đè code. Các dòng `+/-` dưới là định dạng diff.

<!-- STEP05-PATCH-BEGIN -->
```diff
--- a/gear_sonic/utils/mujoco_sim/dex3_pickup.py
+++ b/gear_sonic/utils/mujoco_sim/dex3_pickup.py
@@ -42,7 +42,6 @@
             equality = ET.SubElement(root, 'equality')
         ET.SubElement(equality, 'weld', body1='pelvis', solref='.002 1')
         return mujoco.MjModel.from_xml_string(ET.tostring(root, encoding='unicode'))
-
 
 class Dex3Pickup:
 
@@ -84,12 +83,63 @@
         self.position_error = None
         self.orientation_error = None
         self.fraction = 0.0
+        self.placed = False
+        self.place_xy = None
         self.lost_grasp_since = None
+
+    def lower_to_table(self, data, xy=None):
+        if not self.active or self.stage != 'success':
+            return False
+        from .object_reset import BottlePlacement
+        destination = BottlePlacement(self.model, data).validate(self.target[:2] if xy is None else xy)
+        shift = np.r_[destination - self.target[:2], 0.0]
+        self.place_low_q = self.table_arm_q.copy()
+        self.place_high_q = self.arm_target.copy()
+        if np.linalg.norm(shift) > 0.001:
+            targets = []
+            for (endpoint, seed) in enumerate((self.table_arm_q, self.arm_target)):
+                scratch = self.scratch
+                scratch.qpos[:] = data.qpos
+                scratch.qpos[self.arm_q] = seed
+                mujoco.mj_kinematics(self.model, scratch)
+                position = scratch.site_xpos[self.site].copy() + shift
+                if endpoint == 0:
+                    position[2] -= 0.006
+                rotation = scratch.xmat[self.wrist].reshape(3, 3).copy()
+
+                def residual(q):
+                    scratch.qpos[self.arm_q] = q
+                    mujoco.mj_kinematics(self.model, scratch)
+                    angular = Rotation.from_matrix(rotation @ scratch.xmat[self.wrist].reshape(3, 3).T).as_rotvec()
+                    return np.r_[scratch.site_xpos[self.site] - position, 0.15 * angular, 0.002 * (q - seed)]
+                result = least_squares(residual, seed, bounds=(self.lower, self.upper), max_nfev=150)
+                if np.linalg.norm(residual(result.x)[:6]) > 0.005:
+                    raise ValueError('Place destination outside arm workspace; choose a closer X/Y.')
+                targets.append(result.x)
+            (self.place_low_q, self.place_high_q) = targets
+        self.support_probe = None
+        self.place_xy = destination
+        self.lower_start_q = self.arm_target.copy()
+        self.set_stage('transfer' if np.linalg.norm(shift) > 0.001 else 'lower', data.time)
+        return True
+
+    def table_support(self, data):
+        for (contact_id, contact) in enumerate(data.contact):
+            geoms = [int(contact.geom1), int(contact.geom2)]
+            if self.geom in geoms:
+                other = geoms[1] if geoms[0] == self.geom else geoms[0]
+                if self.model.geom(other).name == 'pickup_table_top':
+                    force = np.zeros(6)
+                    mujoco.mj_contactForce(self.model, data, contact_id, force)
+                    if force[0] > 0.05:
+                        return True
+        return False
 
     def start(self, data):
         self.reset()
         self.active = True
         self.arm_target = data.qpos[self.arm_q].copy()
+        self.home_arm_q = self.arm_target.copy()
         self.hand_target = self.opened.copy()
         self.start_pos = data.site_xpos[self.site].copy()
         self.start_rot = data.xmat[self.wrist].reshape(3, 3).copy()
@@ -201,10 +251,72 @@
             self.fraction = float(0.05 * advance + 0.95 * np.clip((elapsed - 1.5) / 1.5, 0.0, 1.0))
             self.hand_target = self.opened + (self.closed - self.opened) * self.fraction
             if elapsed > 3.5 and opposed:
+                self.table_arm_q = self.arm_target.copy()
                 self.set_stage('lift', data.time)
             elif elapsed > 5:
                 self.error = 'No opposed finger contacts; lift cancelled. Reset to retry.'
                 self.set_stage('failed', data.time)
+        elif self.stage == 'transfer':
+            t = np.clip(elapsed / 4.0, 0.0, 1.0)
+            self.arm_target = self.lower_start_q + t * t * (3.0 - 2.0 * t) * (self.place_high_q - self.lower_start_q)
+            if elapsed > 5.0:
+                self.lower_start_q = self.arm_target.copy()
+                self.set_stage('lower', data.time)
+            return
+        elif self.stage in ('lower', 'release', 'placed'):
+            if self.stage == 'lower':
+                t = np.clip(elapsed / 5.0, 0.0, 1.0)
+                if elapsed <= 5.0:
+                    self.arm_target = self.lower_start_q + t * t * (3.0 - 2.0 * t) * (self.place_low_q - self.lower_start_q)
+                else:
+                    if self.support_probe is None:
+                        self.scratch.qpos[:] = data.qpos
+                        self.scratch.qpos[self.arm_q] = self.place_low_q
+                        mujoco.mj_kinematics(self.model, self.scratch)
+                        self.support_probe = self.scratch.site_xpos[self.site].copy()
+                        self.support_probe_rot = self.scratch.xmat[self.wrist].reshape(3, 3).copy()
+                    position = self.support_probe + [0.0, 0.0, -min(0.02, 0.003 * (elapsed - 5.0))]
+                    self.solve(data, position, self.support_probe_rot)
+                if self.table_support(data):
+                    self.release_pos = data.site_xpos[self.site].copy()
+                    self.release_rot = data.xmat[self.wrist].reshape(3, 3).copy()
+                    position = self.release_pos.copy()
+                    self.set_stage('release', data.time)
+                elif elapsed > 13.0:
+                    self.error = 'No tabletop support; fingers remain closed. Reset to retry.'
+                    self.set_stage('failed', data.time)
+                return
+            else:
+                position = self.release_pos.copy()
+                rotation = self.release_rot.copy()
+                self.fraction = float(1.0 - np.clip(elapsed / 2.0, 0.0, 1.0)) if self.stage == 'release' else 0.0
+                self.hand_target = self.opened + (self.closed - self.opened) * self.fraction
+                if self.stage == 'release' and elapsed > 3.0:
+                    upright = data.xmat[self.bottle].reshape(3, 3)[2, 2] > 0.95
+                    self.placed = bool(self.table_support(data) and upright and (np.linalg.norm(data.xpos[self.bottle, :2] - self.place_xy) < 0.025))
+                    if not self.placed:
+                        self.error = 'Bottle did not settle upright within 2.5 cm of the requested destination. Reset to retry.'
+                    self.set_stage('retreat' if self.placed else 'failed', data.time)
+        elif self.stage == 'retreat':
+            t = np.clip(elapsed / 2.0, 0.0, 1.0)
+            release_offset = np.zeros(3)
+            position = self.release_pos + release_offset + np.array([-0.09, 0.0, 0.025]) * t * t * (3.0 - 2.0 * t)
+            rotation = self.release_rot.copy()
+            self.solve(data, position, rotation)
+            if elapsed > 3.0:
+                self.return_start_q = self.arm_target.copy()
+                self.set_stage('return_home', data.time)
+            return
+        elif self.stage in ('return_home', 'complete'):
+            t = np.clip(elapsed / 4.0, 0.0, 1.0) if self.stage == 'return_home' else 1.0
+            self.arm_target = self.return_start_q + t * t * (3.0 - 2.0 * t) * (self.home_arm_q - self.return_start_q)
+            if self.stage == 'return_home' and elapsed > 5.0:
+                if np.max(np.abs(data.qpos[self.arm_q] - self.home_arm_q)) < 0.05:
+                    self.set_stage('complete', data.time)
+                elif elapsed > 8.0:
+                    self.error = 'Arm could not return home. Reset to retry.'
+                    self.set_stage('failed', data.time)
+            return
         elif self.stage in ('lift', 'hold', 'success'):
             t = np.clip(elapsed / 3.0, 0.0, 1.0) if self.stage == 'lift' else 1.0
             position = self.grasp + [0.0, 0.0, 0.2 * t * t * (3.0 - 2.0 * t)]
@@ -222,7 +334,7 @@
                             self.lost_grasp_since = float(data.time)
                         elif data.time - self.lost_grasp_since > 0.3:
                             self.success = False
-                            self.error = 'Bottle slipped from grasp; lift invalidated. Reset to retry.'
+                            self.error = 'Bottle slipped from grasp; placement cancelled. Reset to retry.'
                             self.set_stage('failed', data.time)
                     else:
                         self.lost_grasp_since = None
@@ -241,4 +353,4 @@
         hand[len(self.hand):] = 8.0 * (self.hand_target - data.qpos[self.hand_q]) - 0.2 * data.qvel[self.hand_v] + data.qfrc_bias[self.hand_v]
 
     def snapshot(self):
-        return {'hand_model': 'dex3', 'stage': self.stage, 'active': self.active, 'success': self.success, 'target_source': 'YOLO RGB-D surface + known radius and tabletop height', 'target_center_world_m': self.target.tolist() if self.target is not None else None, 'position_error_m': self.position_error, 'orientation_error_rad': self.orientation_error, 'finger_contacts': self.contacts, 'closure_fraction': self.fraction, 'minimum_hold_lift_m': self.min_hold_lift if self.min_hold_lift is not None and np.isfinite(self.min_hold_lift) else None, 'error': self.error}
+        return {'hand_model': 'dex3', 'stage': self.stage, 'active': self.active, 'success': self.success, 'placed': self.placed, 'place_target_xy_m': self.place_xy.tolist() if self.place_xy is not None else None, 'target_source': 'YOLO RGB-D surface + known radius and tabletop height', 'target_center_world_m': self.target.tolist() if self.target is not None else None, 'position_error_m': self.position_error, 'orientation_error_rad': self.orientation_error, 'finger_contacts': self.contacts, 'closure_fraction': self.fraction, 'minimum_hold_lift_m': self.min_hold_lift if self.min_hold_lift is not None and np.isfinite(self.min_hold_lift) else None, 'error': self.error}
--- a/gear_sonic/utils/mujoco_sim/dex3_controls.py
+++ b/gear_sonic/utils/mujoco_sim/dex3_controls.py
@@ -75,6 +75,11 @@
         self.serial += 1
         self.channel.send({'command': 'pause', 'id': self.serial})
 
+    def can_repeat_pickup(self):
+        pickup = getattr(self.env, 'assisted_pickup', None)
+        return (self.phase == 'running' and pickup is not None
+                and pickup.active and pickup.stage == 'complete')
+
     def handle(self, message):
         command = message.get('command')
         if command == 'reset':
@@ -96,7 +101,30 @@
                 self.place(message['xy'])
             except (KeyError, TypeError, ValueError) as error:
                 self.error = str(error)
+        elif command == 'lower':
+            pickup = getattr(self.env, 'assisted_pickup', None)
+            if self.phase != 'running' or pickup is None or not self.connected():
+                self.error = 'Lower requires a connected, successful pickup'
+                return
+            try:
+                xy = np.asarray(message.get('xy'), dtype=float)
+                if xy.shape != (2,) or not np.isfinite(xy).all():
+                    raise ValueError('Place X/Y must be two finite numbers')
+                if np.any(xy < self.bounds[:, 0]) or np.any(xy > self.bounds[:, 1]):
+                    raise ValueError('Place X/Y is outside the tabletop margin')
+                if not pickup.lower_to_table(self.env.mj_data, xy):
+                    self.error = 'Lower is available only while holding a successful grasp'
+            except (TypeError, ValueError) as error:
+                self.error = str(error)
         elif command == 'start':
+            if self.can_repeat_pickup():
+                if not self.connected():
+                    self.error = 'VLA disconnected; cannot begin the next pickup'
+                    return
+                self.scene_changed_at = self.clock()
+                self.detection = None
+                self.env.assisted_pickup.start(self.env.mj_data)
+                return
             if self.phase != 'idle':
                 return
             if not self.connected():
@@ -187,7 +215,8 @@
                 'phase': self.phase, 'error': self.error,
                 'bottle': data.qpos[self.qa:self.qa + 3].tolist(),
                 'wrist': data.xpos[model.body('right_wrist_yaw_link').id].tolist(),
-                'can_start': self.phase == 'idle' and self.connected() and self.pending is None,
+                'can_start': (self.phase == 'idle' or self.can_repeat_pickup()) and self.connected() and self.pending is None,
+                'can_lower': self.phase == 'running' and pickup is not None and pickup.stage == 'success' and pickup.success and self.connected() and self.pending is None,
                 'can_place': self.phase == 'idle' and self.pending is None,
                 'client': 'connected' if self.connected() else 'disconnected'}
 
@@ -259,6 +288,8 @@
             msg = {'command': command}
             if command == 'place':
                 msg['xy'] = [float(x.get()), float(y.get())]
+            elif command == 'lower':
+                msg['xy'] = [float(place_x.get()), float(place_y.get())]
             commands.put_nowait(msg)
         except (ValueError, queue.Full):
             error.set('Enter numeric X/Y, or wait for the previous command')
@@ -268,10 +299,21 @@
     start_button = ttk.Button(frame, text='Start', command=lambda: send('start'), state='disabled')
     start_button.pack(fill='x', pady=6)
     ttk.Button(frame, text='Reset robot + bottle', command=lambda: send('reset')).pack(fill='x', pady=6)
+    ttk.Label(frame, text='Place destination X/Y (metres)').pack(anchor='w')
+    place_row = ttk.Frame(frame)
+    place_row.pack(pady=8)
+    place_x = tk.StringVar(value=f'{xyz[0]:.3f}')
+    place_y = tk.StringVar(value=f'{xyz[1]:.3f}')
+    for label, value in (('X', place_x), ('Y', place_y)):
+        ttk.Label(place_row, text=label).pack(side='left', padx=4)
+        ttk.Entry(place_row, textvariable=value, width=10).pack(side='left', padx=4)
+    lower_button = ttk.Button(frame, text='Lower / Place on table', command=lambda: send('lower'), state='disabled')
+    lower_button.pack(fill='x', pady=6)
     ttk.Label(frame, textvariable=info, justify='left').pack(anchor='w', pady=8)
     ttk.Label(frame, textvariable=error, foreground='red', wraplength=420).pack(anchor='w')
     ttk.Label(frame, text='Bottle XYZ = physics; YOLO XYZ = visible surface.').pack(anchor='w')
-    ttk.Label(frame, text='Pickup uses RGB-D/IK in a fixed-pelvis simulation.').pack(anchor='w')
+    ttk.Label(frame, text='Pickup/place use RGB-D/IK with the pelvis fixed.').pack(anchor='w')
+    ttk.Label(frame, text='After complete: Start picks again; Reset restores the applied initial XY.').pack(anchor='w')
 
     def refresh():
         if stop.is_set():
@@ -297,6 +339,7 @@
             error.set(state['error'])
             start_button.configure(state='normal' if state['can_start'] else 'disabled')
             apply_button.configure(state='normal' if state['can_place'] else 'disabled')
+            lower_button.configure(state='normal' if state.get('can_lower', False) else 'disabled')
         root.after(75, refresh)
 
     refresh()
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/object_reset.py
@@ -0,0 +1,58 @@
+"""Reset a free object's pose without resetting the robot or simulation clock."""
+
+import mujoco
+import numpy as np
+
+
+def reset_free_object(model, data, joint_name="red_bottle_free_joint", xy=None):
+    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
+    if joint_id < 0:
+        return False
+    if model.jnt_type[joint_id] != mujoco.mjtJoint.mjJNT_FREE:
+        raise ValueError(f"{joint_name} must be a free joint")
+    qpos_start = model.jnt_qposadr[joint_id]
+    dof_start = model.jnt_dofadr[joint_id]
+    data.qpos[qpos_start:qpos_start + 7] = model.qpos0[qpos_start:qpos_start + 7]
+    if xy is not None:
+        data.qpos[qpos_start:qpos_start + 2] = xy
+    data.qvel[dof_start:dof_start + 6] = 0
+    data.qacc_warmstart[dof_start:dof_start + 6] = 0
+    data.qfrc_applied[dof_start:dof_start + 6] = 0
+    data.xfrc_applied[model.jnt_bodyid[joint_id]] = 0
+    mujoco.mj_forward(model, data)
+    return True
+
+
+class BottlePlacement:
+    """Upright bottle placement, with a fixed Z and footprint inside the table."""
+
+    def __init__(self, model, data):
+        joint = model.joint("red_bottle_free_joint")
+        self.address = int(joint.qposadr[0])
+        self.xy = model.qpos0[self.address:self.address + 2].copy()
+        self.z = float(model.qpos0[self.address + 2])
+        top = model.geom("pickup_table_top").id
+        rotation = data.geom_xmat[top].reshape(3, 3)
+        if not np.allclose(rotation, np.eye(3)):
+            raise ValueError("Bottle XY controls require an axis-aligned tabletop")
+        radius = float(model.geom("red_bottle_body").size[0]) + .001
+        self.bounds = np.column_stack((
+            data.geom_xpos[top, :2] - model.geom_size[top, :2] + radius,
+            data.geom_xpos[top, :2] + model.geom_size[top, :2] - radius,
+        ))
+
+    def validate(self, xy):
+        values = np.asarray(xy, dtype=float)
+        if values.shape != (2,) or not np.isfinite(values).all():
+            raise ValueError("X and Y must be finite numbers in metres")
+        if np.any(values < self.bounds[:, 0]) or np.any(values > self.bounds[:, 1]):
+            raise ValueError(
+                f"On table: X {self.bounds[0, 0]:.3f}..{self.bounds[0, 1]:.3f}, "
+                f"Y {self.bounds[1, 0]:.3f}..{self.bounds[1, 1]:.3f} m"
+            )
+        return values.copy()
+
+    def reset(self, model, data, xy=None):
+        if xy is not None:
+            self.xy = self.validate(xy)
+        return reset_free_object(model, data, xy=self.xy)
```
<!-- STEP05-PATCH-END -->

## 7. Chạy toàn bộ chu trình

Không cần cài thêm dependency của bước 5. Dùng đúng môi trường và weights đã
cài ở bước 4. Chỉ một server và một phiên simulation dùng các port này.

### Terminal 1 — server v10

Nếu server đúng checkpoint đã chạy ở 5550 thì giữ nguyên. Nếu chưa có:

```bash
cd ~/projects/Isaac-GR00T
.venv/bin/python gr00t/eval/run_gr00t_server.py \
  --model-path "$HOME/projects/GR00T-WholeBodyControl/checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000" \
  --embodiment-tag UNITREE_G1_SONIC \
  --device cuda:0 --host 127.0.0.1 --port 5550
```

### Terminal 2 — simulation Dex3 có hỗ trợ

Lệnh này dùng cho bản clone đã áp đủ các bước và workspace hiện tại có chức
năng tương ứng; không áp chồng patch lên workspace hiện tại.

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter \
  --sim-assisted-pickup --sim-fixed-base \
  --prompt "grab the bottle"
```

Bản launcher tối thiểu còn prompt xác nhận ở pane C++: trả lời `y` nếu được hỏi
và chờ `Init Done`. Camera/detector cần có ảnh mới. Không trộn nút panel với phím
`k/i/p/9` khi chạy chu trình quản lý này.

### Thao tác trên panel

1. Nhập Bottle position X = 0.43, Y = -0.11 → **Apply X/Y**.
2. **Start**, chờ pickup = success và chai được giữ trên cao.
3. Nhập Place destination X = 0.45, Y = -0.05.
4. **Lower / Place on table**, chờ transfer → lower → release → retreat → return_home.
5. Khi complete, **Start** sáng lại. Bấm để nhận diện/gắp chai ở vị trí đã đặt.
6. Muốn về trạng thái khởi tạo, **Reset robot + bottle**. Reset về XY đã Apply
   ở bước 1, không phải đích đặt lần cuối. Target và trạng thái chu trình được xóa;
   nội dung ô nhập đích có thể còn để tiện nhập lại.

Ô tọa độ/chữ số trên panel không phải bằng chứng chai đã được bàn đỡ. Nút
Lower/Start được bật theo trạng thái và phép kiểm tra vật lý, không chỉ theo
thời gian chạy animation.

## 8. Kiểm thử tự động trước khi mở GUI

### Bản clone đã áp đủ bước 1–5

Phép thử dùng perception/bridge/channel giả, không cần GUI, GPU model VLA hoặc
DDS. Nó kiểm tra physics và điều phối nút; không thay thế đánh giá YOLO/VLA live.

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python - <<'PYTEST'
from pathlib import Path
from types import SimpleNamespace
import importlib.util,sys,unittest
import numpy as np
from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
from gear_sonic.utils.mujoco_sim import dex3_controls as controls_module

class Channel:
 def __init__(self):self.sent=[]
 def receive(self):return None
 def send(self,message):self.sent.append(message);return True
 def close(self):pass

class PickupPlaceCycleTest(unittest.TestCase):
 def make_env(self):
  config=SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
  config.update(GROUND_START=True,ASSISTED_PICKUP=True,FIXED_PICKUP_BASE=True,SIM_CONTROLS=False,BOTTLE_DETECTION_PORT=0)
  env=DefaultEnv(config,onscreen=False)
  env.set_unitree_bridge(SimpleNamespace(PublishLowState=lambda _:None,joystick=None,
   low_cmd=None,low_cmd_received=False,last_low_cmd_time=100.,reset=lambda:None))
  return env
 def grasp(self,env,xy,start=True):
  p=env.assisted_pickup;d=env.mj_data
  if start:p.start(d)
  for step in range(6000):
   p.update(d,{'status':'detected','world_point_m':[xy[0]-.025,xy[1],.85],
    'camera_position_world_m':[0.,xy[1],1.2],'capture_monotonic':step//100})
   env.sim_step()
   if p.stage in ('success','failed'):break
  self.assertTrue(p.success,p.snapshot())
  self.assertGreater(p.min_hold_lift,.12)
 def test_four_place_targets_home_and_second_pickup(self):
  for xy,destination in (([.43,-.11],[.45,-.05]),([.40,-.15],[.42,-.12]),
                          ([.46,-.08],[.43,-.11]),([.43,-.05],[.45,-.05])):
   with self.subTest(xy=xy,destination=destination):
    env=self.make_env();m,d,p=env.mj_model,env.mj_data,env.assisted_pickup
    ui=controls_module.Dex3SimulationControls(env,panel=False,channel=Channel(),clock=lambda:100.)
    ui.handle({'command':'place','xy':xy})
    for _ in range(100):env.sim_step()
    env.begin_control_transition();self.grasp(env,xy)
    ui.phase='running';ui.seen=100.
    self.assertTrue(ui.snapshot()['can_lower'])
    # Invalid/unreachable requests must keep the held bottle and stage.
    for invalid in ([float('nan'),0.],[2.,2.],[.70,.35]):
     ui.handle({'command':'lower','xy':invalid})
     self.assertTrue(ui.error)
     self.assertEqual(p.stage,'success')
    ui.handle({'command':'lower','xy':destination})
    self.assertFalse(ui.error,ui.error)
    self.assertFalse(ui.snapshot()['can_lower'])
    self.assertFalse(ui.snapshot()['can_start'])
    for _ in range(9000):
     p.update(d,{});env.sim_step()
     if p.stage in ('complete','failed'):break
    self.assertEqual(p.stage,'complete',p.snapshot())
    self.assertTrue(p.placed)
    self.assertTrue(p.table_support(d))
    self.assertLess(np.linalg.norm(d.xpos[p.bottle,:2]-destination),.025)
    self.assertGreater(d.xmat[p.bottle].reshape(3,3)[2,2],.95)
    np.testing.assert_allclose(d.qpos[p.arm_q],p.home_arm_q,atol=.05)
    self.assertTrue(ui.snapshot()['can_start'])
    self.assertFalse(ui.snapshot()['can_lower'])
    settled_xy=d.xpos[p.bottle,:2].copy()
    bottle_before=d.qpos[ui.qa:ui.qa+7].copy()
    ui.handle({'command':'start'})
    np.testing.assert_array_equal(d.qpos[ui.qa:ui.qa+7],bottle_before)
    self.assertEqual(p.stage,'detecting')
    self.assertEqual(ui.phase,'running')
    self.grasp(env,settled_xy,start=False)
    np.testing.assert_array_equal(d.xfrc_applied[p.bottle],0.)
    self.assertNotIn(p.bottle,m.eq_obj1id)
    self.assertNotIn(p.bottle,m.eq_obj2id)
    ui.handle({'command':'reset'})
    self.assertTrue(env.standby)
    self.assertEqual(p.stage,'idle')
    self.assertIsNone(p.place_xy)
    self.assertFalse(ui.snapshot()['can_lower'])
    np.testing.assert_allclose(d.qpos[ui.qa:ui.qa+3],[*xy,.801])
    np.testing.assert_array_equal(d.qvel,0.)
    self.assertFalse(any(w.number for w in d.warning))
 def test_lower_unavailable_without_grasp_and_after_loss(self):
  env=self.make_env();m,d,p=env.mj_model,env.mj_data,env.assisted_pickup
  ui=controls_module.Dex3SimulationControls(env,panel=False,channel=Channel(),clock=lambda:100.)
  ui.seen=100.;ui.phase='running'
  ui.handle({'command':'lower','xy':[.45,-.05]})
  self.assertTrue(ui.error);self.assertEqual(p.stage,'idle')
  env.begin_control_transition();self.grasp(env,[.43,-.11])
  qa=m.jnt_qposadr[m.joint('red_bottle_free_joint').id]
  d.qpos[qa:qa+3]=[.43,-.11,.801]
  for _ in range(150):p.update(d,{});env.sim_step()
  self.assertEqual(p.stage,'failed')
  self.assertFalse(ui.snapshot()['can_lower'])
  ui.handle({'command':'lower','xy':[.45,-.05]})
  self.assertTrue(ui.error)

if __name__=='__main__':unittest.main()
PYTEST
```

### Workspace hiện tại đã có các tính năng này

Không dùng test của API tối thiểu nếu chưa áp các patch vào một bản clone riêng.
Dùng test hiện có trong workspace:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python -m unittest gear_sonic.tests.test_assisted_pickup
```

### Phạm vi đã kiểm tra khi viết tài liệu

- Chuỗi patch 2 → 3 → 4 → 5 áp nối tiếp lên source gốc, không cần chép code từ
  workspace đã sửa vào bản clone. Bước 1 cung cấp scene và tài nguyên mesh gốc
  vẫn phải được tải theo hướng dẫn cài đặt.
- **Hai bài kiểm thử headless đã qua**, gồm bốn cặp điểm gắp/đặt, mở ngón, bàn
  đỡ chai, sai số đích, thu tay, Start gắp lại không Reset, Reset và mất grasp.
- Các đích không hợp lệ/ngoài tầm bị từ chối mà không tự mở tay hoặc đổi stage.
- Chưa cài lại từ đầu toàn bộ trên Windows sạch và chưa chạy trọn GUI + VLA +
  C++ trong bản clone tối thiểu này. Không mô tả test có perception giả là
  GR00T tự hoàn thành gắp–đặt.

Các cặp điểm đại diện đã kiểm tra:

| XY gắp | XY đặt |
|---|---|
| 0.43, -0.11 | 0.45, -0.05 |
| 0.40, -0.15 | 0.42, -0.12 |
| 0.46, -0.08 | 0.43, -0.11 |
| 0.43, -0.05 | 0.45, -0.05 |

Biên mặt bàn không phải cam kết mọi XY trong đó đều với tới hoặc đều đã thử.

## 9. Lỗi thường gặp

| Hiện tượng | Kiểm tra |
|---|---|
| Lower không sáng | Pickup đã success chưa; còn giữ chai không; VLA/SONIC còn kết nối không |
| Hạ một lúc rồi giữ nguyên | Chưa có contact bàn đủ lực; không được tự mở tay; xem stage/error và chọn đích gần hơn |
| Đích hợp lệ trên bàn nhưng bị từ chối | Nghiệm IK không đạt cho điểm cao hoặc thấp; biên bàn rộng hơn tầm tay |
| Đặt xong Start chưa sáng | Chưa complete/thu tay chưa đạt sai số; đọc error, không dùng Reset để che lỗi |
| Start gắp lượt hai nhưng nhìn chỗ cũ | Phải xóa target/detection khi repeat và đợi frame mới; xem code `can_repeat_pickup` |
| Reset đưa chai về vị trí khác đích vừa đặt | Đúng: Reset dùng XY đã Apply ban đầu; Start sau complete mới giữ vị trí vừa đặt |
| Chai đổ sau khi mở | Kiểm tra upright/sai số/contact, khoảng lùi tay và tốc độ; không báo placed chỉ vì ngón mở |
| Không thấy nút mới | Chưa áp bước 5 vào đúng bản clone hoặc chưa khởi động lại simulator để nạp code |

## 10. Chuẩn bị chia sẻ trên GitHub

Bộ năm Markdown chứa code dạng patch, nên có thể chia sẻ phần hướng dẫn trước
mà không đính kèm model/cache/môi trường. Nói rõ trong mô tả repository:

> G1 Dex3 MuJoCo assisted pickup/place demo. YOLO RGB-D and IK control the grasp
> and placement with a fixed pelvis. GR00T inference runs, but predicted actions
> do not directly execute the assisted motion. Native GR00T–SONIC evaluation is
> planned separately.

Nếu dùng GitHub repository code-only của bạn, có thể chép thư mục
`docs/source/tutorials/huong_dan_chinh_sua/` và tài liệu cài đặt sang đúng
checkout đó. Chỉ sửa/chạy Git trong checkout bạn muốn upload; không coi thư mục
con `share_code_only/` là cache và không xóa nó để dọn dung lượng.

### 10.1. Bỏ qua model và bản sao lưu

Trước khi chia sẻ code, kiểm tra `.gitignore`. Có thể thêm các mẫu sau nếu thiếu:

```gitignore
checkpoints/cloudwalk_g1_bottle_v10/
models/
outputs/
.venv*/
*.before_step01
*.before_step02
*.before_step03
*.before_step04
*.before_step05
```

Ignore không tự gỡ file đã được track hoặc xóa binary khỏi lịch sử Git. Kiểm
tra danh sách staged trước khi commit; không chạy `git add .` khi chưa rà soát.
Weights tải theo link trong tài liệu, không cần push lên GitHub cùng code.

### 10.2. Giữ định dạng patch trong Markdown

Unified diff có các dòng context rỗng mang đúng một dấu cách. Không tự xóa mọi
trailing space trong các tài liệu chứa patch vì có thể làm sai bản vá. Có thể
thêm ngoại lệ hẹp vào `.gitattributes` trước khi commit tài liệu:

```gitattributes
docs/source/tutorials/huong_dan_chinh_sua/*.md whitespace=-blank-at-eol
```

Ngoại lệ chỉ áp dụng tài liệu ở thư mục này; không tắt kiểm tra whitespace cho
Python/C++ hoặc toàn repository.

### 10.3. Kiểm tra và commit tài liệu trong checkout đích

```bash
git remote -v
git branch --show-current
git status --short

git add docs/source/tutorials/huong_dan_chinh_sua/ \
  docs/source/tutorials/WSL_UPSTREAM_V10_SETUP.md

git diff --cached --stat
git diff --cached --name-status
git diff --cached --check
```

Nếu đã sửa `.gitignore`/`.gitattributes` theo trên, stage riêng hai file đó sau
khi xem diff. Đọc lại toàn bộ staged diff để chắc không có nội dung khác từ
một thao tác `git add` trước đó. Khi staged đúng những gì bạn muốn chia sẻ:

```bash
git commit -m "Document Dex3 assisted pickup and placement workflow"
```

Sau đó push vào **remote cá nhân và nhánh đã kiểm tra**; không push nhầm remote
NVlabs upstream. Tài liệu không tự đăng nhập, tạo commit hoặc push cho bạn.
Nếu upload cả code đã áp patch, cần kiểm tra thêm các file Python/XML thay đổi;
những lệnh stage ở trên chỉ chọn tài liệu, không mang theo source đã sửa.

## 11. Mốc hoàn tất phiên bản hỗ trợ

Bạn có một bộ hướng dẫn từ dựng cảnh, giữ tư thế chờ, giao diện, nhận diện/gắp
đến đặt–thu tay–gắp lại bằng Dex3. Để người khác đánh giá đúng, giữ thông tin
rõ ràng về fixture, RGB-D/IK và phạm vi test.

Sau khi bạn chia sẻ bản này, lần sửa tiếp theo sẽ bám phương án bạn chọn.
Chưa chuyển sang điều khiển mô hình trực tiếp và chưa triển khai robot thật
trong bộ bước 5 này.
