# Giao diện điều khiển khớp thủ công G1 Dex3

Tài liệu đối chiếu với `gear_sonic/scripts/run_manual_joint_control.py`, cập nhật ngày 24/10/2026.

## 1. Mục đích và phạm vi

Chương trình tạo một simulation MuJoCo riêng, cho phép chọn từng bộ phận trên robot, tô xanh phần được chọn và chỉnh góc khớp bằng phím hoặc ô nhập. Có 43 khớp điều khiển: 29 khớp thân/chân/cánh tay và 14 khớp bàn tay Dex3.

Không cần server GR00T, SONIC, YOLO hoặc DDS. Chương trình không kết nối robot thật, không điều khiển cửa sổ đã chạy bằng `launch_inference.py`, không tự nhận diện/gắp chai và chưa ghi dataset. Việc chỉnh góc không sửa XML trên đĩa.

Vị trí và hướng pelvis được khóa trong simulation để robot không ngã khi chỉnh chân. Đây là công cụ chỉnh tư thế, không phải kiểm thử tự giữ thăng bằng hoặc đi bộ.

## 2. Cách chạy và sử dụng

Chạy trong môi trường đã cài của dự án, có model/mesh và màn hình đồ họa (WSLg nếu dùng WSL):

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python gear_sonic/scripts/run_manual_joint_control.py
```

Hai cửa sổ xuất hiện:

- **Tkinter:** nhóm khớp, bảng góc, ô nhập và nút điều khiển.
- **GLFW/MuJoCo:** robot 3D, chọn bộ phận và chỉnh camera.

| Phím/nút | Chức năng |
| --- | --- |
| `1` | Tay trái + ngón Dex3, 14 khớp |
| `2` | Tay phải + ngón Dex3, 14 khớp |
| `3` | Chân trái, 6 khớp |
| `4` | Chân phải, 6 khớp |
| `5` | Eo/thân: yaw, roll, pitch, 3 khớp |
| `←` / `→` | Chọn khớp trước/sau trong nhóm, quay vòng ở cuối danh sách |
| `↑` / `↓` | Tăng/giảm góc đích theo `Step` |
| `H` / Home all | Khôi phục trực tiếp toàn bộ tư thế robot và giữ Home |
| `Esc` | Đóng cả hai cửa sổ |
| Click trái | Chọn bộ phận robot, tô xanh bộ phận đó |
| Giữ chuột phải + kéo | Xoay camera |
| Giữ chuột giữa + kéo | Dịch chuyển camera |
| Cuộn con lăn | Zoom |

`Step` có đơn vị độ, mặc định 2°, chấp nhận 0,1–10°. `Target` là góc tuyệt đối theo độ; nhập rồi bấm Apply target hoặc Enter. Góc ngoài giới hạn được chặn về giới hạn MJCF.

Bảng có các cột:

| Cột | Nội dung |
| --- | --- |
| Joint | Tên khớp MuJoCo |
| Actual | Góc thực tế, đọc từ `data.qpos` |
| Target | Góc người dùng yêu cầu |
| Limits | Giới hạn góc trong model |

Khi focus ở ô nhập, các phím số/mũi tên/H phục vụ việc nhập, không gửi lệnh robot; Esc vẫn đóng chương trình. Click bảng hoặc robot để điều khiển tiếp. Click trong 3D cập nhật ô Target; chọn dòng trong bảng chỉ đổi lựa chọn/tô màu, vì vậy nên kiểm tra giá trị ô nhập trước khi Apply.

## 3. Luồng chạy tổng thể

```text
__main__ → main()
             ├─ ManualJoints(): nạp model, trạng thái và bộ điều khiển
             ├─ Tkinter: tạo bảng/nút/ô nhập
             ├─ PickingViewer(): tạo cửa sổ 3D và callback
             └─ root.mainloop()
                    └─ tick() lặp lại
                         ├─ GLFW poll_events: chuột và phím cửa sổ 3D
                         ├─ đọc hàng đợi lệnh → command()
                         ├─ step(): điều khiển + vật lý
                         ├─ cập nhật bảng góc
                         ├─ sync(): render
                         └─ root.after(8, tick)
```

Tkinter và GLFW được xử lý trên cùng luồng chính. Hàng đợi dùng để chuyển lệnh từ callback sang vòng xử lý, không có worker điều khiển riêng.

Hai đường cập nhật không qua hàng đợi: Apply gọi trực tiếp `set_target()`; click chọn bộ phận/dòng bảng cập nhật lựa chọn trực tiếp. Chúng vẫn chạy trên luồng chính.

## 4. Dữ liệu trong ManualJoints

| Thuộc tính | Ý nghĩa |
| --- | --- |
| `model`, `data` | Mô hình MuJoCo và trạng thái vật lý hiện tại |
| `home` | Bản sao `env.initial_qpos`, là tư thế ban đầu, không nhất thiết mọi góc bằng 0 |
| `groups` | Danh sách joint ID theo nhóm |
| `offsets` | Vị trí bắt đầu của mỗi nhóm trong mảng điều khiển chung |
| `joints` | 43 joint ID, thứ tự tay trái, tay phải, chân trái, chân phải, eo |
| `qa`, `va` | Địa chỉ qpos và bậc tự do vận tốc tương ứng với các khớp |
| `targets` | Góc đích do người dùng yêu cầu, đơn vị radian |
| `setpoints` | Góc đích trung gian có giới hạn tốc độ |
| `side`, `index` | Nhóm và chỉ số trong nhóm đang chọn |
| `selected` | Chỉ số chung: `offsets[side] + index` |
| `actuators` | Actuator tương ứng từng khớp |
| `robot_q`, `robot_v` | Chỉ số trạng thái của toàn robot, dùng khi Home |
| `lock_q`, `lock_v` | Trạng thái robot ngoài 43 khớp điều khiển, dùng để khóa base |
| `kp`, `kd` | Hệ số PD |
| `home_hold` | Giữ tư thế sau Home, thoát khi đặt góc mới |
| `body_to_selection` | Ánh xạ body vật lý sang khớp điều khiển |
| `original_rgba`, `original_material` | Màu và vật liệu gốc để khôi phục sau khi đổi lựa chọn |

Không thể dùng joint ID trực tiếp để đánh chỉ số qpos cho mọi joint. Ví dụ free joint dùng nhiều phần tử qpos; code lấy `jnt_qposadr` và `jnt_dofadr` để ánh xạ đúng.

## 5. Các hàm của ManualJoints

### `__init__()` — chuẩn bị model và điều khiển

1. Nạp cấu hình bằng `SimLoopConfig(...).load_wbc_yaml()`.
2. Bật ground start; tắt policy, assisted pickup, fixed pickup base và native Inspire trong cấu hình của công cụ này.
3. Tạo `DefaultEnv` không mở viewer tích hợp, lấy model/data và tư thế ban đầu.
4. Lập nhóm khớp tay, Dex3, chân và eo.
5. Khởi tạo góc đích/setpoint từ Home; chọn tay phải, khớp đầu tiên.
6. Kiểm tra mỗi khớp có đúng một actuator; không đúng thì báo lỗi.
7. Lấy chỉ số trạng thái robot từ `_idle_robot_indices`, phân biệt robot và vật thể tự do.
8. Thiết lập PD, ánh xạ body và màu gốc.

Code phụ thuộc cấu trúc G1 Dex3 và thuộc tính nội bộ của `DefaultEnv`; thay model khác cần đối chiếu tên khớp, actuator và các chỉ số này.

### `select_body(body)` — ánh xạ click sang khớp

Bắt đầu từ body được ray picking trả về, tìm trong `body_to_selection`. Nếu body là chi tiết cố định không có khớp điều khiển riêng, đi lên body cha cho đến khi tìm được khớp tương ứng. Cập nhật nhóm/index, tô xanh và trả về True. Không tìm thấy thì trả về False; click chai/bàn/nền không đổi lựa chọn.

### `highlight()` — tô xanh bộ phận

Nếu lựa chọn không đổi thì bỏ qua để giảm công việc. Nếu đổi, khôi phục toàn bộ màu/vật liệu gốc rồi tô xanh các geom thuộc link được chọn và các chi tiết cố định của nó. Tạm đặt material ID của các geom này thành -1 để vật liệu không che màu xanh. Các link con có khớp riêng không bị tô xanh theo link cha.

### `selected` — chỉ số khớp chung

Property chỉ đọc, chuyển nhóm/index sang chỉ số trong `targets`, `setpoints`, `joints`, `qa`, `va`.

### `set_target(degrees)` — đặt góc

Từ chối NaN/Inf, đổi độ sang radian, chặn theo `model.jnt_range`, cập nhật đúng một phần tử của `targets`. Đặt `home_hold=False` để cho phép chuyển động trở lại. Không dịch chuyển trực tiếp qpos.

### `command(key)` — xử lý lệnh

- 1–5: đổi nhóm, thu index về phạm vi hợp lệ nếu nhóm mới ít khớp hơn.
- Left/Right: chuyển khớp trong nhóm theo vòng.
- Up/Down: tăng/giảm Target hiện tại theo Step.
- H/h: gọi `home_all()`.

### `home_all()` — khôi phục toàn robot

Khôi phục góc đích, setpoint và qpos của robot từ Home; bật `home_hold`. Xóa vận tốc, gia tốc robot, warm-start solver, ngoại lực áp vào các DOF/body robot và lệnh actuator. Gọi `mj_forward()` để cập nhật trạng thái dẫn xuất.

Đây là **reset trực tiếp trong simulation**, không phải quỹ đạo chuyển động về Home. Không gọi `mj_resetData()` cho toàn cảnh nên không đặt lại vị trí/vận tốc chai. Chai vẫn có thể chuyển động do vật lý sau đó, đặc biệt nếu trước Home đang được bàn tay đỡ.

Sau Home, `step()` tiếp tục giữ qpos/vận tốc robot ở tư thế ban đầu. Chọn nhóm/đổi camera không thoát giữ Home; đặt góc mới bằng Up/Down hoặc Apply mới thoát.

### `step()` — điều khiển và vật lý

1. Khóa qpos/vận tốc base theo Home, xóa warm-start tương ứng.
2. Gọi `mj_forward()` để cập nhật động học và mômen bias.
3. Dịch chuyển từng setpoint về Target với giới hạn 30°/giây theo timestep simulation.
4. Tính mômen PD cộng bias.
5. Giới hạn mômen theo actuator, ghi vào `data.ctrl`.
6. Chạy `mj_step()`.
7. Khóa lại base; nếu giữ Home thì khôi phục trạng thái toàn robot.
8. Gọi `mj_forward()` để renderer/bảng đọc trạng thái đã cập nhật.

Công thức chính:

```python
delta = np.deg2rad(30.) * model.opt.timestep
setpoints += np.clip(targets - setpoints, -delta, delta)
tau = kp * (setpoints - data.qpos[qa]) - kd * data.qvel[va] + data.qfrc_bias[va]
```

Trong phiên bản hiện tại, tên chứa `_hand_` dùng Kp=5, Kd=0,3; các khớp khác dùng Kp=60, Kd=3. `qfrc_bias` là mômen bias của hệ động lực học, bao gồm ảnh hưởng trọng lực và vận tốc; không phải đầu ra SONIC.

Actual có thể khác Target vì va chạm, giới hạn mômen và sai số bám. Giới hạn 30°/giây áp dụng cho setpoint, không phải cam kết vận tốc thực của khớp trong mọi va chạm.

## 6. Các hàm của PickingViewer

| Hàm | Mô tả |
| --- | --- |
| `__init__()` | Khởi tạo GLFW, cửa sổ 1000×800, OpenGL context, camera, scene, renderer và đăng ký callback phím/chuột |
| `scroll(window, x, y)` | Dùng cuộn dọc để gọi `mjv_moveCamera` ở chế độ zoom |
| `button(window, button, action, mods)` | Ghi vị trí nhấn; khi nhả trái và di chuyển dưới 5 pixel thì thực hiện chọn body |
| `motion(window, x, y)` | Tính độ dịch chuyển chuột chia theo chiều cao cửa sổ; chuột phải xoay, chuột giữa dịch camera |
| `on_pick()` | Hook mặc định rỗng, được `main()` thay bằng `picked()` để đồng bộ ô nhập/focus |
| `is_running()` | Gọi `glfw.poll_events()` rồi kiểm tra yêu cầu đóng cửa sổ |
| `sync()` | Cập nhật scene, vẽ 3D, tên khớp/hướng dẫn và swap buffers; bỏ qua khi framebuffer có kích thước 0 |
| `close()` | Giải phóng MjrContext, hủy cửa sổ, kết thúc GLFW |

Ray picking dùng `mjv_select()`, tọa độ chuột chuẩn hóa và tỉ lệ framebuffer. Tô màu không tách mesh hay thay collision; mỗi link điều khiển vẫn giữ cấu trúc vật lý gốc.

MuJoCo 3.14.0 trong môi trường đã kiểm thử nhận lời gọi camera với **5 tham số**:

```python
mujoco.mjv_moveCamera(model, action, reldx, reldy, camera)
```

Không thêm `scene` vào lời gọi này; đó là nguyên nhân TypeError khi kéo chuột ở phiên bản code trước. Nếu thay phiên bản MuJoCo, kiểm tra lại API thực tế trong môi trường.

## 7. main() và các callback giao diện

`main()` tạo controller, Tkinter, hàng đợi tối đa 256 lệnh và PickingViewer. Camera ban đầu nhìn về `[0.25, 0, 0.85]`, distance=2, azimuth=135°, elevation=-20°.

| Hàm lồng trong main | Vai trò |
| --- | --- |
| `send(key)` | Đưa lệnh vào queue không chặn; queue đầy thì bỏ lệnh mới |
| `viewer_key(code)` | Ánh xạ mã phím GLFW sang chuỗi lệnh |
| `apply()` | Đọc Target, chuyển sang float, gọi set_target; hiển thị lỗi nếu dữ liệu không hợp lệ |
| `picked()` | Cập nhật ô Target từ khớp vừa click trong 3D, chuyển focus về root |
| `select(event)` | Đọc dòng Treeview, kiểm tra phạm vi, đổi index và highlight |
| `keypress(event)` | Xử lý phím Tkinter, ưu tiên Esc; không điều khiển robot khi focus ở ô nhập |
| `close()` | Đặt stopped, đóng viewer và Tkinter; chặn gọi đóng lặp |
| `tick()` | Điều phối sự kiện, vật lý, cập nhật bảng và render |

Cuối file có `if __name__ == '__main__': main()`. Khi import module để kiểm thử, GUI không tự mở.

## 8. Chi tiết vòng tick và hiệu năng

1. Nếu đã stopped thì trả về.
2. Poll GLFW; đóng cả chương trình nếu cửa sổ 3D yêu cầu thoát.
3. Cộng thời gian trôi qua vào ngân sách vật lý, chặn tối đa 0,04 giây.
4. Kiểm tra Step là số hữu hạn trong 0,1–10°.
5. Xử lý queue; Step sai chỉ chặn tăng/giảm góc, không chặn Home hoặc Esc.
6. Chạy các bước vật lý theo `model.opt.timestep`; dừng bù khi đã dùng khoảng 4 ms xử lý trong lượt đó.
7. Mỗi khoảng 0,1 giây cập nhật bảng: xóa hàng thừa khi đổi nhóm, chỉ cập nhật hàng thay đổi, chỉ đổi selection khi cần.
8. Render khi đủ khoảng cách 1/30 giây; mốc render được đặt lại sau khi vẽ xong.
9. Hẹn tick tiếp bằng `root.after(8, tick)`.

8 ms là thời gian hẹn sau lượt xử lý, không phải cam kết chu kỳ 8 ms. Render tối đa 30 Hz và bảng khoảng 10 Hz; tốc độ thực phụ thuộc máy. Khi quá tải, simulation có thể chậm hơn thời gian thực do bỏ bớt thời gian bù.

Bóng đổ, phản chiếu, skybox và sương mù được tắt để giảm tải render WSLg; không thay đổi va chạm. Tô màu và cập nhật bảng cũng được tránh lặp khi không đổi.

## 9. Ví dụ luồng điều khiển

### Chỉnh gối trái

```text
Phím 3 → nhóm left_leg
Click gối trái → mjv_select → select_body → highlight
Phím ↑ → queue → command → set_target
step → setpoint tăng dần → mômen PD → mj_step
Bảng Actual và hình 3D cập nhật chuyển động thực tế
```

### Home sau khi chỉnh nhiều nhóm

```text
Home all → queue → command('h') → home_all
    ├─ reset robot qpos, qvel, Target, setpoint và lệnh cũ
    └─ home_hold=True
Các tick sau giữ tư thế Home
Up/Down hoặc Apply → set_target → home_hold=False → tiếp tục PD
```

## 10. Kiểm thử và xử lý lỗi

```bash
.venv_sim/bin/python -m unittest gear_sonic.tests.test_manual_joint_control -v
```

Sáu kiểm thử hiện có bao phủ:

1. Chọn khớp, giới hạn góc, phím và Home.
2. Callback zoom/xoay/dịch camera gọi MuJoCo thực, không cần mở màn hình.
3. Chọn và chuyển động chân/eo, kiểm tra base được khóa.
4. Home khôi phục trạng thái thực của robot, giữ tư thế và bảo toàn trạng thái vật thể tại thời điểm reset.
5. Chọn từng link và tô xanh đúng phần tương ứng.
6. Bước vật lý làm tay chuyển động, giới hạn setpoint, giữ base và cho chai chịu vật lý.

Các kiểm thử này không chứng minh robot tự gắp chai hoặc chạy được trên phần cứng thật.

| Hiện tượng | Kiểm tra |
| --- | --- |
| Không mở được cửa sổ | Màn hình WSLg/GLFW/OpenGL và đúng môi trường `.venv_sim` |
| Phím không tác dụng | Focus có đang nằm trong ô Target/Step không? Click bảng hoặc robot rồi thử lại |
| Actual không bằng Target | Giới hạn mômen, va chạm và PD; không mặc định kết luận lệnh bị mất |
| Một khớp khó click | Vỏ che hoặc các link chồng nhau; chọn qua bảng hoặc Left/Right |
| Home không về 0° | Home là tư thế khởi tạo model, không phải tất cả góc bằng 0 |
| Chai không được dựng lại sau Home | Đúng thiết kế: Home chỉ reset robot; đóng/mở lại để tạo lại toàn scene |
| Đã sửa code nhưng hành vi cũ | Đóng tiến trình cũ và chạy lại file |

## 11. Vị trí cần sửa nếu mở rộng

- Thêm nhóm/model: `ManualJoints.__init__()`, bảng offset, phím trong command/main và các nút.
- Đổi giới hạn tốc độ/gain: `ManualJoints.step()` và khởi tạo `kp/kd`.
- Đổi cách chọn/tô màu: `select_body()`, `highlight()`, `PickingViewer.button()`.
- Đổi camera hoặc tần suất hiển thị: camera trong main, `PickingViewer`, `tick()`.
- Ghi dataset về sau: cần đồng bộ ảnh, trạng thái thực, lệnh, timestamp và vòng đời episode; file hiện tại chưa làm việc này. Trạng thái nhảy khi Home phải được coi là ranh giới/reset, không ghi thành động tác chuyên gia liên tục.
