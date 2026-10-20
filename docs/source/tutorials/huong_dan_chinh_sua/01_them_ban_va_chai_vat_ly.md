# Bước 1 — Thêm bàn và chai nước có tương tác vật lý trong MuJoCo

Tài liệu thuộc thư mục `docs/source/tutorials/huong_dan_chinh_sua/`.
Đối chiếu với repository gốc `NVlabs/GR00T-WholeBodyControl`, commit
`b042411fae38ee4d1af9aac82a37a1f8d14d6dd0` và scene hiện tại trên máy.

## 1. Mục tiêu của bước này

Toàn bộ bước này sử dụng **Unitree G1 với bàn tay Dex3 mặc định** của repository:
29 khớp thân + 7 khớp mỗi tay, tổng 43 actuator. Các bước tiếp theo vẫn giữ
cấu hình Dex3 để hoàn tất bài gắp và nâng chai trước khi chuyển loại bàn tay.

Sau bước này, scene có bàn cố định và một chai nước màu xanh:

- Chai có khối lượng và chịu trọng lực.
- Chai đứng trên bàn nhờ tiếp xúc, có thể trượt hoặc bị đẩy đổ.
- Chai có thể được nâng nếu bàn tay tạo được lực nắm và ma sát phù hợp.
- Chai không bị gắn cứng hoặc hàn vào tay robot.

Đây là bước dựng môi trường. Chưa thêm YOLO, giao diện, IK, Start/Lower hoặc
logic tự động gắp. Việc thêm chai không làm checkpoint tự hiểu được vị trí chai.
Vị trí bàn/chai là bố trí mô phỏng tham khảo, không phải scene huấn luyện gốc
được CloudWalk cung cấp.

**Nếu dùng workspace hiện tại:** file scene đã có các đối tượng này. Đọc để
hiểu/tái tạo trên bản clone mới; không chèn thêm lần nữa vì sẽ trùng tên.
Không cần dừng hay khởi động lại server GR00T chỉ để đọc tài liệu.

## 2. File cần sửa và phạm vi áp dụng

Chỉ sửa file:

```text
gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml
```

Scene này include `g1_29dof_with_hand.xml`, tức robot mặc định với bàn tay Dex3.
Bước 1 giữ nguyên URDF, mesh, actuator và cấu trúc bàn tay Dex3. Chỉ thêm bàn,
chai và vật liệu vào scene; chưa cần cài adapter hoặc model bàn tay khác.
Lệnh kiểm tra và mở viewer ở mục 6–7 nạp trực tiếp scene Dex3 này.

Đã cài `.venv_sim` theo hướng dẫn WSL trước đó. Các lệnh sau chạy trong Ubuntu
WSL, từ thư mục gốc repository. Nếu viewer đang mở scene cũ, đóng và mở lại
viewer sau khi lưu XML; MuJoCo không tự nạp lại file khi bạn lưu.

## 3. Sao lưu scene trước khi sửa trên bản clone mới

```bash
cd ~/projects/GR00T-WholeBodyControl
cp -n gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml \
  gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml.before_step01
```

`cp -n` giữ nguyên bản sao lưu nếu đã tồn tại. Không sao chép các môi trường
Python hay model lớn để làm bản sao lưu cho một bước chỉnh XML.

## 4. Thay nội dung scene bằng XML đầy đủ sau

Mở `gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml` trong VS Code,
thay toàn bộ nội dung bằng khối XML dưới rồi lưu. Không chèn thêm một khối
`<mujoco>` vào bên trong file cũ.

```xml
<mujoco model="g1_43dof scene">
  <include file="g1_29dof_with_hand.xml"/>
  <!-- Note that the hand model in g1_29dof_with_hand.xml is not stable for simulation. -->

  <statistic center="0 0 0.5" extent="2.0"/>

  <visual>
    <headlight diffuse="0.6 0.6 0.6" ambient="0.3 0.3 0.3" specular="0 0 0"/>
    <rgba haze="0.15 0.25 0.35 1"/>
    <global azimuth="-130" elevation="-20"/>
  </visual>

  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0 0 0" width="512" height="3072"/>
    <texture type="2d" name="groundplane" builtin="checker" mark="edge" rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3"
      markrgb="0.8 0.8 0.8" width="300" height="300"/>
    <material name="groundplane" texture="groundplane" texuniform="true" texrepeat="5 5" reflectance="0.2"/>
    <texture name="pickup_table_texture" type="2d" builtin="checker"
             rgb1="0.55 0.24 0.07" rgb2="0.75 0.36 0.10" width="256" height="256"/>
    <material name="pickup_table_material" texture="pickup_table_texture"
              texuniform="true" texrepeat="3 3"/>
  </asset>

  <worldbody>
    <light pos="0 0 1.5" dir="0 0 -1" directional="true"/>
    <geom name="floor" size="0 0 0.05" type="plane" material="groundplane"/>
    <!-- Keep the diagnostic marker hidden so it cannot be mistaken for an object. -->
    <site name="com_marker" pos="0.1 0 0" size="0.05" rgba="1 0 0 0" type="sphere"/>

    <!-- Layout estimated from checkpoint example videos; original scene unavailable.
         +X is forward and -Y is the robot's right side. Tabletop is at 0.70 m. -->
    <body name="pickup_table" pos="0.50 0 0">
      <geom name="pickup_table_top" type="box" pos="0 0 0.675"
            size="0.25 0.45 0.025" material="pickup_table_material"/>
      <geom name="pickup_table_leg_1" type="box" pos="-0.21 -0.41 0.325"
            size="0.025 0.025 0.325" rgba="0.55 0.24 0.07 1"/>
      <geom name="pickup_table_leg_2" type="box" pos="-0.21 0.41 0.325"
            size="0.025 0.025 0.325" rgba="0.55 0.24 0.07 1"/>
      <geom name="pickup_table_leg_3" type="box" pos="0.21 -0.41 0.325"
            size="0.025 0.025 0.325" rgba="0.55 0.24 0.07 1"/>
      <geom name="pickup_table_leg_4" type="box" pos="0.21 0.41 0.325"
            size="0.025 0.025 0.325" rgba="0.55 0.24 0.07 1"/>
    </body>

    <!-- Append object joints after the robot to preserve SDK joint indexing.
         A free body allows a physical grasp; there is no attachment to the hand. -->
    <!-- Move the bottle 5 cm closer to the robot along the forward axis. -->
    <body name="red_bottle" pos="0.43 -0.11 0.801">
      <freejoint name="red_bottle_free_joint"/>
      <geom name="red_bottle_body" type="cylinder" size="0.025 0.10"
            mass="0.065" rgba="0.05 0.48 0.8 1"
            condim="4" friction="1.2 0.01 0.001"/>
      <!-- Blue/cyan bottle matches the sample; legacy names retained. -->
      <geom name="bottle_label" type="cylinder" pos="0 0 0.025"
            size="0.0253 0.035" mass="0" contype="0" conaffinity="0"
            rgba="0.5 0.85 0.9 1"/>
      <geom name="bottle_shoulder" type="ellipsoid" pos="0 0 0.10"
            size="0.025 0.025 0.023" mass="0.005" rgba="0.4 0.8 0.85 1"
            condim="4" friction="1.2 0.01 0.001"/>
      <geom name="red_bottle_neck" type="cylinder" pos="0 0 0.125"
            size="0.012 0.018" mass="0.005" rgba="0.65 0.9 0.9 1"
            condim="4" friction="1.2 0.01 0.001"/>
      <geom name="red_bottle_cap" type="cylinder" pos="0 0 0.151"
            size="0.014 0.008" mass="0.005" rgba="0.02 0.02 0.02 1"/>
    </body>
  </worldbody>

  <default>
    <geom friction="1.0"/>
  </default>
</mujoco>
```

## 5. Giải thích những phần thay đổi

### 5.1. Bàn cố định

```xml
<body name="pickup_table" pos="0.50 0 0">
  <geom name="pickup_table_top" type="box" pos="0 0 0.675"
        size="0.25 0.45 0.025" material="pickup_table_material"/>
  <!-- Các chân bàn nằm trong XML đầy đủ ở trên. -->
</body>
```

Body không có joint nên bàn gắn cố định với thế giới. `size` của box là
**nửa kích thước**: mặt bàn dài 0,50 m theo X, rộng 0,90 m theo Y, dày 0,05 m.

Tâm mặt bàn có Z = 0,675 m. Mặt trên ở:

```text
0,675 + 0,025 = 0,700 m
```

Bốn chân giúp hiển thị bàn đầy đủ và cũng là các geometry có va chạm.
Texture/material thay màu bề mặt, không thay trọng lực hay tự tạo lực nắm.

### 5.2. Chai là vật thể tự do

```xml
<body name="red_bottle" pos="0.43 -0.11 0.801">
  <freejoint name="red_bottle_free_joint"/>
  <!-- Hình học của chai nằm trong XML đầy đủ ở trên. -->
</body>
```

`freejoint` cho phép chai tịnh tiến và xoay trong không gian. Nếu bỏ joint này,
chai sẽ gắn cố định với world; robot không thể nhấc chai bằng tiếp xúc thông thường.

Tên `red_bottle` là tên nội bộ giữ lại từ bản cũ để tương thích code reset,
chẩn đoán và gắp về sau. Màu nhìn thấy do `rgba` quyết định: chai ở đây màu xanh.
Không tự đổi các tên này nếu đang dùng các script tùy chỉnh hiện có.

Joint của chai được đặt sau include robot để không đẩy joint robot sang thứ tự
khác. Những bước lập trình sau vẫn cần ánh xạ theo tên/địa chỉ joint, không
được giả định toàn bộ `qpos` đều là khớp thân robot.

### 5.3. Kích thước, khối lượng và va chạm

| Thành phần | Cấu hình và tác dụng |
|---|---|
| Thân chai | Cylinder `size="0.025 0.10"`: bán kính 2,5 cm, cao 20 cm |
| Vai, cổ và nắp | Geometry riêng, chuyển động cùng body chai |
| Tổng khối lượng | 0,065 + 0,005 + 0,005 + 0,005 = **0,080 kg** |
| Nhãn | `mass="0" contype="0" conaffinity="0"`: chỉ hiển thị, không va chạm |
| Ma sát chai | `friction="1.2 0.01 0.001"`; ma sát có hiệu lực theo cấu hình contact của MuJoCo |
| Contact | `condim="4"` cho phép contact có ma sát trượt và ma sát xoắn |
| COM marker cũ | Đặt alpha RGBA = 0 để không bị nhầm thành vật cần gắp |

`size="0.025 0.10"` chưa bao gồm phần cổ và nắp nên tổng chiều cao hình chai
lớn hơn 20 cm. `pos` của body là gốc tham chiếu thân chai, không phải tọa độ đáy
hay COM tổng hợp của toàn bộ chai.

**Không đặt `contype="0" conaffinity="0"` lên thân chai hoặc mặt bàn**: làm
vậy có thể tắt va chạm cần thiết. Không thêm equality/weld giữa chai và tay.

### 5.4. Hệ tọa độ và cách đổi vị trí chai

Đơn vị là mét. Với robot ở tư thế mặc định quay theo +X:

| Trục | Ý nghĩa |
|---|---|
| X | Phía trước robot |
| Y | Bên trái robot là +Y, bên phải là -Y |
| Z | Hướng lên |

Ví dụ trong XML đầy đủ:

```xml
<body name="red_bottle" pos="0.43 -0.11 0.801">
```

Chai ở phía trước 43 cm, lệch phải 11 cm. Muốn gần robot hơn 3 cm theo X:

```xml
<body name="red_bottle" pos="0.40 -0.11 0.801">
```

Muốn dùng vị trí gần đây của workspace, đặt `pos="0.43 -0.05 0.801"`.
Giữ Z = 0,801 m khi vẫn dùng bàn và kích thước chai trên: đáy thân chai
ở 0,801 - 0,100 = 0,701 m, cao hơn mặt bàn 1 mm để rơi xuống ổn định.

Mặt bàn phủ X = 0,25..0,75 m, Y = -0,45..0,45 m. Đặt tâm chai cách mép đủ
bán kính chai và khoảng dự phòng; nằm trên bàn chưa có nghĩa nằm trong tầm tay.
Các giới hạn nhập X/Y của giao diện ở các bước sau có thể hẹp hơn mặt bàn.

Nếu thay độ cao mặt bàn hoặc chiều cao thân chai, tính lại:

```text
Z ban đầu của gốc thân chai = Z mặt bàn + nửa chiều cao thân chai + khe hở nhỏ
```

## 6. Kiểm tra MuJoCo đọc được scene

Không cần bật GR00T server cho kiểm tra này:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python - <<'PYLOAD'
from pathlib import Path
import mujoco

path = Path('gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml').resolve()
model = mujoco.MjModel.from_xml_path(str(path))
for name in ('pickup_table', 'red_bottle'):
    print('Body:', name, 'id:', model.body(name).id)
joint = model.joint('red_bottle_free_joint').id
assert model.jnt_type[joint] == mujoco.mjtJoint.mjJNT_FREE
assert model.nu == 43  # Robot mặc định: 29 thân + 7 khớp mỗi tay Dex3.
print('Bottle mass (kg):', float(model.body('red_bottle').mass[0]))
print('XML + meshes + freejoint: OK')
PYLOAD
```

Nếu mesh không đọc được hoặc chứa LFS pointer, kiểm tra Git LFS và các file
`g1_29dof_with_hand.xml`, `meshes/` nằm cùng cây thư mục gốc. Không di chuyển
scene sang thư mục khác rồi giữ nguyên include/mesh path.

## 7. Mở scene để xem trực quan

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python -m mujoco.viewer \
  --mjcf=gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml
```

Đây là viewer MuJoCo thuần: chưa chạy SONIC nên robot có thể đổ khi physics
chạy, không dùng cửa sổ này để đánh giá giữ thăng bằng hoặc gắp tự động.
Pause viewer khi cần quan sát bố trí. Kiểm thử ở mục 8 tách riêng bàn/chai để
không bị robot chưa điều khiển ngã vào chai.

Nếu không có cửa sổ, kiểm tra WSLg và `DISPLAY`; đó là bước kiểm tra hiển thị,
khác với việc XML đã load thành công.

## 8. Kiểm tra rơi xuống bàn và tiếp xúc, không cần GUI/model

Lệnh sau đọc chính scene vừa sửa, **chỉ trong bộ nhớ bỏ include robot**,
thả chai cao hơn vị trí ban đầu 3 cm rồi chạy 5 giây vật lý. Lệnh không sửa XML
trên đĩa, không ghi lệnh robot, không dùng YOLO và không xác nhận bài gắp.

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python - <<'PYPHYSICS'
import xml.etree.ElementTree as ET
from pathlib import Path
import mujoco
import numpy as np

path = Path('gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml')
root = ET.fromstring(path.read_text())
for node in list(root.findall('include')):
    root.remove(node)  # Tách riêng bàn/chai, không đổi file gốc.
model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding='unicode'))
data = mujoco.MjData(model)
bottle = model.body('red_bottle').id
table = model.geom('pickup_table_top').id
joint = model.joint('red_bottle_free_joint').id
address = int(model.jnt_qposadr[joint])
data.qpos[address + 2] += 0.03
mujoco.mj_forward(model, data)
start_z = float(data.xpos[bottle, 2])
for _ in range(int(np.ceil(5.0 / model.opt.timestep))):
    mujoco.mj_step(model, data)
mujoco.mj_forward(model, data)

supported = False
for contact in data.contact:
    a, b = int(contact.geom1), int(contact.geom2)
    supported |= ((a == table and model.geom_bodyid[b] == bottle)
                  or (b == table and model.geom_bodyid[a] == bottle))
z = float(data.xpos[bottle, 2])
upright = float(data.xmat[bottle].reshape(3, 3)[2, 2])
print('Start Z:', start_z, 'Final Z:', z)
print('Table contact:', supported, 'Upright:', upright)
print('Final speed:', float(np.linalg.norm(data.qvel)))
assert np.isfinite(data.qpos).all()
assert supported, 'Chai khong co tiep xuc voi mat ban'
assert z < start_z - 0.02, 'Chai khong roi tu vi tri tha'
assert abs(z - 0.800) < 0.005, 'Do cao sau khi roi khong dung mat ban'
assert upright > 0.99, 'Chai bi nghieng sau khi tha'
assert np.linalg.norm(data.qvel) < 0.01, 'Chai chua dung yen'
assert not any(w.number for w in data.warning), 'MuJoCo co canh bao vat ly'
print('PASS: Chai tu do, roi xuong va duoc mat ban do.')
PYPHYSICS
```

Các assertion chiều cao dùng nguyên kích thước trong XML ở mục 4. Nếu bạn tự
đổi chiều cao bàn/thân chai thì sửa giá trị kỳ vọng tương ứng.

## 9. Lỗi thường gặp

| Hiện tượng | Kiểm tra |
|---|---|
| Chai đứng yên trong không khí | Chai có `freejoint` không; viewer có pause không |
| Chai xuyên bàn | Collision mask, vị trí spawn, geometry mặt bàn |
| Chai bật/đổ ngay lúc chạy | Spawn có xuyên mặt bàn/robot không; thử kiểm tra bàn/chai riêng ở mục 8 |
| Màu xanh nhưng tên `red_bottle` | Tên legacy được giữ để tương thích code; màu là RGBA |
| Lỗi duplicate name | Đã chèn bàn/chai hai lần; thay file bằng XML đầy đủ, không thêm khối trùng |
| Không thấy bàn/chai sau khi sửa | Xác nhận viewer nạp đúng `scene_43dof.xml`, lưu file rồi đóng/mở lại viewer |
| Robot ngã trong viewer thuần | Chưa có SONIC/điều khiển tư thế; không phải phép kiểm tra gắp |
| Không tìm XML/mesh | Chạy từ repo root, giữ include và thư mục meshes đúng, kiểm tra LFS |

## 10. Hoàn tất và xem phần thay đổi

Bước 1 hoàn thành khi XML load được, viewer hiển thị bàn/chai và phép thử rơi
báo `PASS`. Chưa yêu cầu robot nắm hoặc nâng chai.

Xem những gì khác với bản gốc:

```bash
git diff b042411fae38ee4d1af9aac82a37a1f8d14d6dd0 -- \
  gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml
```

Muốn khôi phục bản sao lưu đã tạo ở mục 3, đóng viewer rồi chạy:

```bash
cp gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml.before_step01 \
  gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml
```

Lộ trình tiếp theo vẫn dùng Dex3: bổ sung nhận diện, tiếp cận, nắm và nâng chai;
giao diện được bổ sung ở bước riêng. Chỉ sau khi bài gắp–nâng bằng Dex3 hoạt
động ổn định mới thực hiện bước chuyển loại bàn tay ở cuối loạt hướng dẫn.
Không cần sao chép toàn bộ code hiện tại chỉ để hoàn thành phần bàn/chai này.
