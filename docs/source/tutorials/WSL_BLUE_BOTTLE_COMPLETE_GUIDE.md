# G1 gắp chai — hướng dẫn và tổng hợp thay đổi trong một file

Tài liệu chính duy nhất cho phần tùy biến gắp/nâng/đặt chai, bàn tay Inspire và
cài đặt repository cá nhân. Nội dung từ 5 tài liệu riêng đã được gom vào đây.
Các tài liệu teleop gốc của dự án vẫn giữ riêng vì thuộc chức năng khác.
Các file Python/C++/XML vẫn phải tồn tại đúng vị trí để simulation chạy;
phụ lục code trong Markdown là bản ghi để xem/chia sẻ, không thay thế source.

## Điều khiển khớp thủ công Dex3 — 24/10/2026

Chạy một simulation riêng để chỉnh từng khớp bằng phím hoặc nút bấm:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_sim/bin/python gear_sonic/scripts/run_manual_joint_control.py
```

Không cần server GR00T, SONIC hoặc DDS. Cửa sổ này không kết nối robot thật và
không điều khiển cửa sổ simulation đã mở bằng `launch_inference.py`. Nên đóng
cửa sổ cũ để tránh nhầm. Model/XML trên đĩa không bị thay đổi.

| Phím | Tác vụ |
| --- | --- |
| `1` / `2` | Chọn tay trái / phải |
| `3` / `4` | Chọn chân trái / phải (6 khớp mỗi chân) |
| `5` | Chọn eo/thân (yaw, roll, pitch) |
| `←` / `→` | Chọn khớp trước / tiếp theo trong nhóm |
| `↑` / `↓` | Tăng / giảm góc đích theo Step |
| `H` | Khôi phục ngay toàn bộ 43 khớp và giữ tư thế ban đầu |
| `Esc` | Dừng và đóng cả bảng điều khiển lẫn viewer |

Trong cửa sổ 3D, **click trái một lần vào bộ phận tay, chân hoặc thân** để chọn khớp của đốt đó.
Đốt được chọn chuyển xanh lá; đốt trước trở lại màu gốc. Dùng ↑/↓ hoặc nút
Increase/Decrease để chỉnh đúng khớp đang chọn. Không di chuyển cả cánh tay như
một khối: mỗi đốt cánh tay/ngón có khớp riêng trong model. Đốt con vẫn chuyển
động theo khớp cha đúng cấu trúc vật lý của robot.

Chuột phải kéo để xoay camera, con lăn để zoom, nút giữa kéo để di chuyển camera.
Phóng to trước khi click từng đốt ngón nhỏ. Click bàn/chai/nền không đổi khớp.
Các khớp bị che bởi vỏ hoặc link khác có thể chọn qua bảng hoặc ←/→; lựa chọn
qua bảng cũng tô xanh phần tương ứng. Không thay đổi topology hoặc collision
của model, chỉ thay màu hiển thị trong bộ nhớ.

Mỗi tay gồm 7 khớp cánh tay và 7 khớp Dex3. Mỗi chân có 6 khớp
hông/gối/cổ chân, eo có 3 khớp yaw/roll/pitch; tổng cộng 43 khớp. Click một dòng trong bảng để chọn
khớp; bảng cập nhật góc thực tế, góc đích và giới hạn theo độ. Có nút tương ứng
cho mọi phím tắt. `Step` cho phép 0,1–10 độ, mặc định 2 độ. Nhập `Target` rồi
bấm `Apply target` hoặc Enter để đặt góc; góc được chặn trong giới hạn MJCF.
Trong lúc nhập số, các phím mũi tên/1–5/H chỉ phục vụ ô nhập, không phát lệnh tay;
Esc vẫn dừng chương trình. Click bảng để dùng lại phím tắt.

Chỉ base tự do (vị trí và hướng pelvis) được khóa bằng ràng buộc trạng thái
simulation để robot không ngã khi chỉnh chân. Tay, ngón, chân và eo dùng PD
+ bù mômen bias; góc đích trung gian giới hạn 30 độ/giây. Chai và
bàn vẫn có va chạm vật lý. Đây là công cụ chỉnh tư thế có thân cố định, không
phải thử nghiệm cân bằng SONIC hoặc tự gắp chai bằng VLA. `H` khôi phục trực tiếp góc thực tế, góc đích và setpoint của toàn bộ robot,
xóa vận tốc/lệnh cũ rồi giữ tư thế cho đến khi bạn chỉnh góc tiếp;
không dựng lại chai. Đóng rồi mở lại chương trình để reset toàn bộ scene.

Source: `gear_sonic/scripts/run_manual_joint_control.py`.
Test: `.venv_sim/bin/python -m unittest gear_sonic.tests.test_manual_joint_control -v`.
Sáu kiểm thử kiểm tra chọn nhóm/khớp, chọn link và tô xanh, giới hạn, Home,
giới hạn tốc độ setpoint, chuyển động tay/chân/eo, khóa base, vật lý chai và
callback camera với MuJoCo đang cài.
Chưa có chức năng ghi dataset ở chế độ này.

Để giảm lag trên WSLg, cửa sổ điều khiển thủ công tắt bóng đổ, phản chiếu,
skybox và sương mù; các thiết lập này không thay đổi vật lý va chạm.
Render giới hạn tối đa 30 Hz, bảng góc cập nhật 10 Hz và chỉ ghi lại các hàng
thay đổi. Mỗi lượt xử lý giới hạn thời gian bù bước vật lý để giao diện không
bị kẹt khi render chậm; khi quá tải, thời gian mô phỏng có thể chậm hơn thời gian thực.
Đo cùng góc camera trên RTX 5070 qua WSLg: thời gian render trung bình giảm
từ 86,9 ms xuống 25,9 ms; đây không phải cam kết FPS trên mọi máy.
Đóng cửa sổ cũ và chạy lại lệnh trên để áp dụng thay đổi.

## Khóa khởi động policy — cập nhật 22/10/2026

Trong profile `--sim-policy-control`, robot giữ nguyên base và toàn bộ khớp từ lúc
mở simulation đến khi có action mới sau Start. Trình tự hiện tại:

1. Khóa tư thế dưới đất, vật trên bàn vẫn có vật lý riêng.
2. Start khởi tạo SONIC nhưng chưa mở khóa để thực thi token tư thế ban đầu.
3. Yêu cầu ảnh/state mới và suy luận GR00T trong khi robot vẫn khóa.
4. Khi có action mới và controller sẵn sàng, chuyển mômen trong 2 giây rồi nhả
   hỗ trợ đứng. Từ đây SONIC điều khiển chuyển động; không khóa chân suốt tác vụ.
5. Nếu chờ action quá 15 giây, giữ khóa và báo lỗi. Reset trở về tư thế chờ và
   xóa action cũ. Cần khởi động lại simulator để nạp thay đổi này.

Thay đổi nằm trong `gear_sonic/utils/mujoco_sim/interactive_controls.py`;
kiểm thử tại `gear_sonic/tests/test_simulation_controls.py`. 12 kiểm thử gồm
standby, chuyển trạng thái và PD đã đạt; chưa xác nhận loại bỏ mọi dao động khi
policy đang thực thi và chưa xác nhận gắp chai thành công.

### Checkpoint thay thế đã tra cứu

- [CloudWalk v10](https://huggingface.co/cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-371ep-v10-finetune):
  đúng tác vụ chai và SONIC, nhưng dữ liệu dùng Inspire; chưa chạy thành công
  trên cảnh Dex3 hiện tại.
- [NVIDIA GR00T-N1.6-G1-PnPAppleToPlate](https://huggingface.co/nvidia/GR00T-N1.6-G1-PnPAppleToPlate):
  có checkpoint và hướng dẫn cho tác vụ gắp táo vào đĩa, sử dụng `UNITREE_G1`
  cùng sim policy wrapper. Không thay trực tiếp cho `UNITREE_G1_SONIC` v10.
- [NVIDIA GN1x-Tuned-Arena-G1-Static-PickNPlace](https://huggingface.co/nvidia/GN1x-Tuned-Arena-G1-Static-PickNPlace):
  model N1.7 cho static pick-and-place trong IsaacLab Arena. Cần môi trường,
  embodiment và giao diện action đi kèm; không có bằng chứng chạy ngay gắp chai
  trong scene MuJoCo này. [Workflow chính thức](https://developer.nvidia.com/blog/develop-humanoid-robot-policies-end-to-end-with-nvidia-isaac-gr00t/)
  mô tả tác vụ táo và bộ điều khiển AGILE.

Chưa tải thêm weights hoặc thay server sang các checkpoint khác. Tìm thấy model
không đồng nghĩa đã kiểm thử thành công trên máy này.

## Chế độ GR00T v10 → SONIC — cập nhật 20/10/2026

Chọn chế độ này để kiểm tra chính sách đã học thay cho controller gắp RGB-D/IK.
Server hiện dùng `cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-371ep-v10-finetune`,
`checkpoint-30000`, revision `f980fd880c92b984d65dcc3f9dc82b98bc8009c0`.
Metadata local xác nhận horizon 40, token 64 chiều, hai vector hand 7 chiều;
hai nhóm observation hand của dữ liệu huấn luyện đều hằng 0.

Nếu server v10 đang chạy tại cổng 5550, giữ nguyên. Nếu chưa chạy:

```bash
cd ~/projects/GR00T-WholeBodyControl
bash gear_sonic/scripts/run_cloudwalk_policy_server.sh
```

Terminal khác:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --sim-policy-control \
  --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter --prompt "grab the bottle"
```

Luồng đang thực thi:

```text
RGB camera + prompt + robot state -> GR00T v10
   motion_token không thay đổi -> SONIC C++ -> 29 lệnh khớp thân -> MuJoCo
   ý định đóng/mở hand -> adapter thử nghiệm Dex3 -> motor ngón -> MuJoCo
YOLO tắt; không có nhánh RGB-D/IK điều khiển robot
```

`--sim-policy-control` chọn baseline **Dex3**, bật adapter grip CloudWalk hiện có,
đưa hand observation về 0 như thống kê huấn luyện và tắt proximity gate 2 cm.
Lệnh `--sim` thông thường cũng tự chọn profile này nếu không yêu cầu chế độ hỗ trợ,
fixed-base, native Inspire hoặc proximity. Profile luôn tắt detector YOLO, kể cả
khi tùy chọn detector mặc định đang bật. Các lệnh assisted trong phần lịch sử bên
dưới thuộc phương án cũ, không dùng để đánh giá năng lực checkpoint.
PD cánh tay giữ bù gravity/Coriolis của MuJoCo để giảm sai số bám; phần này không
đổi góc khớp đích mà SONIC phát ra. Có thể thử baseline không bù bằng cờ
`--no-sim-arm-gravity-compensation`. Không bật `--sim-stationary-body`, không tạo IK gắp,
không weld pelvis, không giữ các khớp thân bằng controller fixture sau Start.
Các tùy chọn xung đột bị từ chối trước khi thay phiên tmux đang chạy.

Robot vẫn đứng yên khi chờ; bấm Start để chuyển sang SONIC, Reset để khởi tạo lại
và xóa action cũ. Nút Lower/Place bị vô hiệu hóa vì nó thuộc controller hỗ trợ.
Không coi việc đổi prompt thành lệnh đặt là đủ để checkpoint gắp một tác vụ học
được thao tác đặt tại XY tùy ý.

**Giới hạn bàn tay:** adapter chỉ giữ ý định khép/mở và thời điểm từ model, không
phục dựng kinematics Inspire. `--sim-native-inspire` hiện vẫn thuộc chế độ hỗ trợ;
không dùng kèm profile policy. Cần xác minh mapper 6 kênh CloudWalk → 6 motor native
trước khi mở nhánh Inspire thuần policy. Không cắt bỏ kênh thứ 7 rồi gán trực tiếp
các số chuẩn hóa thành radian.

### Hướng phát triển nhiều vật và nhiều câu lệnh

GR00T v10 là checkpoint VLA đã fine-tune cho gắp chai. Nó nhận RGB, câu lệnh và
trạng thái robot rồi dự đoán motion token và hand actions; không có đầu ra tọa độ
chai XYZ để truyền cho SONIC. SONIC nhận motion token và trạng thái robot để tạo
lệnh chuyển động. Việc model dùng thông tin thị giác không đồng nghĩa nó cung cấp
một bộ nhận diện vật có tọa độ đọc được.

Để học `grab the apple` hoặc `grab the Rubik's cube`, giữ đường điều khiển này
và chuẩn bị dữ liệu mới:

1. Xác minh bàn tay và action mapping khớp robot thu thập dữ liệu. Adapter Dex3
   hiện tại chỉ là baseline, không coi là chuyển đổi Inspire chính xác.
2. Ghi demonstration đồng bộ RGB, prompt, trạng thái robot, motion token theo
   encoder SONIC phù hợp và lệnh bàn tay. Không dùng góc khớp hoặc tọa độ IK
   thay trực tiếp cho motion token.
3. Thu nhiều vị trí, hướng vật, ánh sáng và cả cảnh nhiều vật với câu lệnh chỉ
   rõ vật cần gắp. Tách tập kiểm thử theo cảnh/vị trí để tránh chỉ học thuộc.
4. Fine-tune VLA bằng cấu hình dữ liệu/action tương thích. Fine-tune VLM riêng
   cho nhận diện có thể hữu ích nhưng không tự tạo kỹ năng điều khiển nắm/nâng.
5. Đánh giá đúng vật theo prompt, tiếp cận, đóng tay, nâng và giữ vật tại vị trí
   chưa gặp trong dữ liệu. Không bật trợ giúp IK trong lượt đánh giá policy.

Nếu cần một model xuất XYZ tường minh rồi lập kế hoạch đến XYZ, đó là kiến trúc
khác cần thiết kế đầu ra và bộ chuyển mục tiêu sang điều khiển; không phải giao
diện sẵn có của checkpoint v10 và SONIC. Thay đổi hiện tại chưa thực hiện
fine-tune và chưa bảo đảm gắp thành công vật mới.

Hai file diagnostic mặc định:

- `outputs/gr00t_policy/actions.jsonl`: raw chunk, input state, raw/published token,
  raw/published hand và nguồn điều khiển. Logger có giới hạn dung lượng.
- `outputs/gr00t_policy/reach.json` và `.jsonl`: vị trí đo được, target khớp SONIC,
  lỗi tracking, contact và độ nâng chai. Các số này là measurement trong simulation.

Để chứng minh model đóng góp, đối chiếu token đã gửi với đúng raw chunk/index;
không chỉ nhìn tay có đưa ra. Pipeline hoạt động không đồng nghĩa đã gắp thành công.
Tỉ lệ thành công cần được đo lại trên cảnh mô phỏng, camera và embodiment hiện tại.
Model card cũng ghi nhận động tác nắm khi không có chai, nên không suy ra robot
đã detect đúng chỉ từ chuyển động tay.
[Nguồn checkpoint](https://huggingface.co/cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-371ep-v10-finetune),
[luồng VLA chính thức](https://nvlabs.github.io/GR00T-WholeBodyControl/tutorials/vla_inference.html).

Đọc log để đối chiếu với đúng chunk/index được chọn:

```bash
.venv_inference/bin/python gear_sonic/scripts/check_policy_control_trace.py \
  outputs/gr00t_policy/actions.jsonl \
  --output outputs/gr00t_policy/routing_report.json
```

Kết quả kiểm tra trực tiếp ngày 20/10/2026 lưu trong
`outputs/gr00t_policy/validation_report.json` (không commit log/model lên GitHub):

- Server v10 `checkpoint-30000`, SONIC C++ và MuJoCo thực sự chạy qua loopback.
- Lượt bật bù mômen PD có 99 raw chunk, 2.809 action đối chiếu đúng chunk/index;
  không có token bị thay, không có khép tay bằng khoảng cách hay IK gắp.
- Trong khoảng 56,65 giây mô phỏng đã đo, sai số bám tâm nắm trung vị 1,83 cm.
- **Chưa gắp được chai**: mức grip từ checkpoint tối đa khoảng 1,48%, không có
  contact tay–chai hoặc lift đạt điều kiện. Đây là baseline hoạt động của luồng
  suy luận, không phải một lượt pickup thành công.
- Frame đầu vào thực tế được lưu ở `outputs/gr00t_policy/policy_camera.jpg`.
  Cảnh, camera và bàn tay Dex3 khác dữ liệu thật, nên vẫn cần xác minh mapping
  Inspire, controller SONIC của bên thu thập dữ liệu và đánh giá độ lệch đầu vào.
  Chưa thể quy nguyên nhân duy nhất cho detector hoặc tọa độ chai.

Cập nhật kiểm tra ngày 21/10/2026 — lịch phát action trong profile policy:

- Ảnh RGB và state simulation được chụp cùng lúc. Client giữ thời điểm đó riêng
  với thời điểm request để bù cả tuổi ảnh lẫn thời gian suy luận; metadata đồng hồ
  không gửi vào model. Kết quả request trước Reset vẫn bị loại bỏ.
- Chỉ số bước action chạy theo đồng hồ monotonic 50 Hz, thay vì cộng một bước mỗi
  vòng Python. Đoạn đầu sau Start vẫn bắt đầu từ bước 0 khi robot đang giữ tư thế.
- Client yêu cầu đoạn kế tiếp trước khi hết horizon, căn theo độ trễ vừa đo và
  biên hai chu kỳ. Không nội suy hay thay giá trị motion token bằng token đứng yên.
- 21 kiểm thử inference/config/freshness/adapter đạt. Lượt thử đầu sau sửa đồng hồ
  có 3.112 action đúng nguồn nhưng chưa có contact hoặc nâng chai; không coi việc
  sửa thời gian là đã giải quyết tương thích embodiment hoặc sim-to-real.
- Kiểm thử server v10 với mẫu tham chiếu v2 episode 0 (cùng dòng dữ liệu, **không
  phải tập đánh giá độc lập v10**) cho grip đầu frame 480 khoảng 0,329 so với mẫu
  0,30, sau đó gần 1,0. Model có dự đoán đóng tay trên mẫu này. Báo cáo nằm tại
  `outputs/gr00t_policy/v10_reference_check.json`; phép thử không gửi lệnh robot.

Lượt thử sau khi sửa lịch refresh: 3.432 action đối chiếu đúng raw chunk/index,
không override. Kết quả tổng hợp tại `outputs/gr00t_policy/clock_refresh_validation.json`.
Robot đã Reset về standby sau kiểm thử; chưa xác nhận pickup thành công.

Để đánh giá lượt sửa này, xem `clock_refresh_actions.jsonl` và
`clock_reach.jsonl` trong `outputs/gr00t_policy/`. Chỉ đối chiếu các đoạn có trạng
thái `running`; file reach chứa cả hai lượt thử và các đoạn Reset/chờ.

Kiểm tra đóng tay sớm với Dex3 (21/10/2026):

- Giữ nguyên Dex3 theo yêu cầu, không bật IK/gate khoảng cách. Khi grip lần đầu
  vượt 0,5 trong lượt đo, khoảng cách hình học tay–chai là 6,04 cm và sai số bám
  tâm nắm so với đích SONIC là 1,56 cm. Chưa có contact hoặc lift.
- Thử 3 lần cho mỗi tổ hợp ảnh/state tại một mẫu: với cùng state simulation,
  RGB simulation cho grip tối đa 0,007–0,024; đổi sang RGB tham chiếu pha nắm
  cho grip lên 1,0. Các cặp ảnh/state hoán đổi không đồng bộ về mặt vật lý,
  chỉ dùng kiểm tra độ nhạy của policy, không dùng điều khiển robot hoặc đánh giá
  thành công. Không thể từ phép thử này suy ra một camera offset sửa được mọi lỗi.
- Báo cáo: `outputs/gr00t_policy/grip_audit_summary.json` và
  `outputs/gr00t_policy/grip_input_ablation.json`. Ảnh thực tế:
  `outputs/gr00t_policy/grip_live_rgb.png`. Checkpoint vẫn chưa được fine-tune
  cho Dex3 và cảnh simulation hiện tại. Luồng policy đúng không đồng nghĩa
  checkpoint đã có khả năng gắp thành công trong môi trường mới.

Các test cấu hình/action/freshness dùng môi trường inference, test PD dùng môi
trường simulation (hai môi trường có dependency khác nhau):

```bash
.venv_inference/bin/python -m unittest \
  gear_sonic.tests.test_policy_control \
  gear_sonic.tests.test_sim_grasp_defaults \
  gear_sonic.tests.test_observation_freshness \
  gear_sonic.tests.test_inspire_adapter -v

.venv_sim/bin/python -m unittest gear_sonic.tests.test_policy_body_tracking -v
```

File sửa/thêm cho nhánh policy: `launch_inference.py`, `run_vla_inference.py`,
`run_sim_loop.py`, `configs.py`, `base_sim.py`, `interactive_controls.py`,
`policy_control.py`, `check_policy_control_trace.py` và các test tương ứng.
Backup các file vốn đã tùy biến trước lần chuyển này nằm trong
`outputs/backups/before_gr00t_policy_20261020_225237/`; không dùng `git reset --hard`
để quay lại vì workspace còn nhiều thay đổi chưa commit từ trước.

Để quay lại bản Inspire đã gắp/đặt bằng hỗ trợ, dùng lệnh native ở phần dưới với
`--sim-assisted-pickup --sim-fixed-base`, bỏ `--sim-policy-control`. Các hướng dẫn
MD bước 1–6 đã push mô tả bản hỗ trợ đó và vẫn giữ nguyên.

## Đọc phần nào trước?

- [Chạy Inspire và pickup/place hiện tại](#inspire-native).
- [Cài WSL/môi trường/repository cá nhân](#personal-repository).
- [Start, Reset, tọa độ chai và Lower](#simulation-controls).
- [Dọn dung lượng và thu hồi ổ C](#disk-cleanup).
- [Bản vá code mới nhất](#current-code-patch).
- [Bản chụp WSL/code cũ để đối chiếu](#legacy-wsl-snapshot).

Ưu tiên profile GR00T–SONIC ở trên cho nhánh policy; lệnh Inspire bên dưới dành
cho bản hỗ trợ đã có. Những phần Dex3/checkpoint cũ bên dưới được giữ
để tra cứu, không dùng chúng để suy ra rằng `--inspire-ftp-hands` chọn bàn tay
native. Flag chọn native là `--sim-native-inspire`; thao tác đang dùng GR00T
kết hợp bộ hiệu chỉnh MuJoCo, chưa phải triển khai robot thật.


<a id="inspire-native"></a>

## Chạy bàn tay Inspire native

# G1 với Inspire RH56DFTP: mô hình native trong MuJoCo

Cấu hình người dùng: G1 EDU Ultimate C-U6, hai bàn tay Inspire RH56DFTP-2L/2R.
Ảnh thông số ghi 41 DoF, tương ứng 29 khớp thân + 6 motor mỗi bàn tay.

## Nguồn mô hình

Dùng URDF `g1_29dof_rev_1_0_with_inspire_hand_FTP.urdf` từ
[Unitree Robotics](https://github.com/unitreerobotics/unitree_ros/tree/5994d4faef0a9cadd3287f8de0199a67eeb2a259/robots/g1_description),
revision `5994d4faef0a9cadd3287f8de0199a67eeb2a259`.
Đây là mô hình FTP chính thức; cần đối chiếu lại serial/revision cơ khí thực tế
trước khi coi nó trùng hoàn toàn phiên bản RH56DFTP-2R/2L đang sở hữu.
Mỗi tay có 12 khớp chuyển động nhưng chỉ 6 motor; 6 khớp còn lại phụ thuộc mimic.
Tổng 41 actuator, 53 khớp hinge, thêm free joint của robot và chai.

## Chạy nắm → nâng → đặt → thu tay với Inspire

Chạy từ thư mục gốc repository, sau khi cài môi trường theo
[RUN_FROM_PERSONAL_REPOSITORY.md](#personal-repository).

**Bước 1 — tạo/cập nhật cả hai scene** (chạy lại sau khi cập nhật code generator):

```bash
.venv_sim/bin/python gear_sonic/scripts/prepare_inspire_ftp_sim.py
```

Lệnh tải URDF/mesh vào `models/g1_inspire_ftp`, lưu nguồn/SHA256 ở `source.json`,
tạo `g1_inspire_ftp.xml` cho preview và `g1_inspire_ftp_pickup.xml` cho luồng gắp.
Model tải riêng, không nhúng mesh binary vào code. File sinh ra không nên chỉnh
trực tiếp; sửa generator rồi chạy lại để tái lập được kết quả.

**Bước 2 — server GR00T, terminal thứ nhất:**

```bash
bash gear_sonic/scripts/run_cloudwalk_policy_server.sh
```

Nếu server đang chạy và dùng đúng checkpoint thì giữ nguyên, không mở thêm server
trên cùng cổng 5550. Bản này không thay hoặc fine-tune checkpoint v10.

**Bước 3 — simulator, terminal thứ hai:**

Đóng phiên simulator cũ trước khi chạy; mỗi lần chỉ mở một phiên dùng các cổng này.

```bash
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter \
  --sim-native-inspire --sim-assisted-pickup --sim-fixed-base \
  --prompt "grab the bottle"
```

Tên cửa sổ phải là `G1 Inspire RH56DFTP - 41 active joints`, có bàn tay 5 ngón.
`--sim-native-inspire` mới chọn model thật trong MuJoCo. Flag cũ
`--inspire-ftp-hands` chỉ là adapter đầu ra checkpoint sang Dex3; không cần thêm
flag đó trong lệnh native ở trên. Không thêm cổng/driver để kết nối robot thật.

1. Robot giữ nguyên toàn bộ tư thế chờ; pelvis cố định trong simulation.
2. Nhập `Bottle position X/Y`, bấm **Apply XY / Reset bottle**. Z theo mặt bàn.
3. Bấm **Start GR00T** (hoặc F6 khi focus cửa sổ MuJoCo). Bộ gắp chờ các quan sát
   YOLO RGB-D mới, ổn định rồi tiếp cận, khép tay và nâng chai khoảng 20 cm.
4. Khi trạng thái `success`, nhập `Place destination X/Y`, bấm
   **Lower / Place on table**. Tay chuyển đến vị trí đó, hạ tới tiếp xúc bàn,
   mở ngón đồng thời lùi lòng bàn tay để tránh ngón duỗi đẩy chai.
5. Sau khi xác nhận chai đứng trên bàn, tay thu về; `complete` bật lại nút Start
   để gắp chai ở vị trí mới mà không Reset.
6. **Reset robot + bottle** / F5 dừng chu trình và khôi phục toàn bộ trạng thái,
   giữ XY chai đã chọn bằng Apply. Không dùng Reset để thay cho Lower khi đang cầm.

Workspace trên panel là biên mặt bàn, không phải bảo đảm tay với tới mọi điểm.
IK từ chối đích không với tới. Nếu mất vật khi giữ, trạng thái chuyển `failed`
và không cho đặt một chai không còn nằm trong tay.

## Luồng điều khiển thực tế

```text
Camera RGB + trạng thái khớp + prompt → GR00T → SONIC (standing token)
Camera RGB-D → YOLO → tâm chai ước lượng → IK cánh tay / máy trạng thái pickup-place
                                              ↓
                              6 motor Inspire + 6 khớp mimic mỗi tay
                                              ↓
                                      tiếp xúc vật lý MuJoCo
```

Đây là **GR00T kết hợp điều khiển hiệu chỉnh trong simulation**, không phải chứng
minh checkpoint tự điều khiển Inspire thành công. Ở chế độ fixed-base assisted,
bộ IK/tiếp xúc điều khiển tay và thao tác; GR00T vẫn nhận ảnh và chạy inference.
Chai là free body, không gắn weld vào tay và không nhận lực nâng bên ngoài.

Schema trạng thái policy hiện vẫn là Dex3 7 kênh. Camera xuất đủ 6 góc motor
Inspire và nhãn `inspire_ftp_motor_radians`; client chuyển sang quan sát Dex3
**xấp xỉ độ gập** trước khi gọi policy. Đây chưa phải mapping CloudWalk/Inspire
được hiệu chuẩn. Lệnh DDS Dex3 không được áp vào 6 motor native; thao tác ngón
native do bộ assisted quản lý. Không dùng mapping này để điều khiển tay thật.

## Preview bàn tay riêng (không server)

```bash
.venv_sim/bin/python gear_sonic/scripts/run_inspire_ftp_sim.py
```

Space đóng/mở hai tay; L/R từng tay; Backspace reset. Đây chỉ là preview với
position actuator, khác scene runtime dùng motor torque và các nút pickup/place.

## Phần đã chuyển đổi và kiểm tra

- Hình học và inertia G1/FTP từ URDF chính thức, giữ các link fixed để không mất
  khối lượng lòng bàn tay khi chuyển đổi; mỗi base link là 0.62266 kg.
- 12 equality joint constraints cho mimic; không tạo thêm motor cho khớp phụ thuộc.
- 41 position actuator trong bản kiểm tra; lực giới hạn theo URDF. Gain dùng cho
  kiểm tra simulation, không phải thông số điều khiển phần cứng.
- Loại riêng cặp va chạm palm–thumb_2 của mỗi tay vì convex collision mesh chồng
  lên phần bản lề bên trong. Va chạm ngón với chai/bàn vẫn được giữ.
- Mesh cảm biến được giữ, nhưng **không mô phỏng 17 cảm biến xúc giác/pressure
  map điện tử mỗi tay**. Không suy diễn dữ liệu tactile từ hình mesh.

## Kết quả kiểm tra ngày 11/10/2026

- Kiểm thử vật lý có kiểm soát qua 4 vị trí: `(0.43, -0.11)`, `(0.40, -0.15)`,
  `(0.46, -0.08)`, `(0.43, -0.05)`. Mỗi lượt giữ 60 giây simulation,
  đặt tại XY mới, thu tay, gắp lại không reset; kiểm tra mất vật cũng khóa Lower.
- Lượt live chạy **đúng launcher + server GR00T + YOLO RGB-D**, bắt đầu ở
  `(0.43, -0.05)`: giữ chai cao hơn vị trí ban đầu tối thiểu khoảng **18,17 cm**.
- Bấm Lower với đích `(0.45, -0.05)`: chai đứng tại khoảng `(0.4441, -0.0541)`,
  sai số XY khoảng **7,2 mm**; trạng thái `complete`, tay về home.
- Bấm Start tiếp, không Reset: detector cập nhật tâm chai mới khoảng
  `(0.4447, -0.0553)` và gắp/nâng lại thành công, giữ cao tối thiểu **18,15 cm**.
- Kiểm thử Dex3 cũ, topology Inspire và schema observation đều qua. Đây là
  các trường hợp đã đo, không phải bảo đảm thành công ở mọi XY trên mặt bàn.

## Kiểm thử và các file thay đổi

```bash
.venv_sim/bin/python -m unittest \
  gear_sonic.tests.test_inspire_ftp_model \
  gear_sonic.tests.test_native_inspire_pickup
.venv_inference/bin/python -m unittest \
  gear_sonic.tests.test_observation_freshness \
  gear_sonic.tests.test_sim_grasp_defaults
```

Test vật lý cấp tọa độ RGB-D có kiểm soát để tách lỗi tiếp xúc khỏi lỗi detector:
kiểm tra nâng >12 cm, giữ 60 giây simulation, đặt chai đứng sai số XY <2,5 cm,
thu tay, gắp lần hai không reset, rồi reset tất cả. Test bỏ qua model nếu chưa
build; kết quả skipped không phải đã kiểm tra vật lý. Kiểm tra live YOLO/server
cần chạy riêng bằng lệnh launcher phía trên.

| File | Thay đổi |
|---|---|
| `gear_sonic/scripts/prepare_inspire_ftp_sim.py` | Tải nguồn pinned, tạo scene preview và torque runtime, mimic, camera, tâm nắm Inspire |
| `gear_sonic/scripts/run_inspire_ftp_sim.py` | Preview đóng/mở bàn tay native |
| `gear_sonic/scripts/launch_inference.py` | Flag `--sim-native-inspire`, kiểm tra scene và chế độ hỗ trợ |
| `gear_sonic/scripts/run_sim_loop.py`, `gear_sonic/utils/mujoco_sim/configs.py` | Chọn scene native, 6 motor/tay, không lấy lệnh DDS Dex3 cho ngón |
| `gear_sonic/utils/mujoco_sim/base_sim.py` | Dùng địa chỉ qpos/dof/actuator thay cho phép trừ joint ID, tư thế chờ Inspire, xuất trạng thái camera |
| `gear_sonic/utils/mujoco_sim/assisted_pickup.py` | Profile nắm 6 khớp, nhả/lùi tay Inspire, phát hiện mất vật khi giữ |
| `gear_sonic/utils/mujoco_sim/inspire_hand.py`, `gear_sonic/scripts/run_vla_inference.py` | Quan sát policy xấp xỉ, có nhãn rõ ràng, tránh đọc quá 6 khớp |
| `gear_sonic/utils/mujoco_sim/palm_proximity.py`, `reach_diagnostics.py` | Nhận đúng lòng bàn tay và các ngón native trong đo tiếp xúc |
| `gear_sonic/tests/test_native_inspire_pickup.py`, `test_inspire_ftp_model.py`, `test_observation_freshness.py` | Kiểm thử topology, physics, observation |

Model mặc định Dex3 vẫn giữ nguyên. Để quay về, bỏ `--sim-native-inspire` và dùng
lệnh Dex3 trong hướng dẫn cũ. Các gain/tư thế/fixture trong bản này chỉ được kiểm
tra ở MuJoCo; chưa phải cấu hình triển khai robot thật.


<a id="personal-repository"></a>

## Cài đặt từ repository cá nhân

# Chạy G1 pickup/place từ repository quyhuyhp123

> **Bàn tay Inspire RH56DFTP:** xem [hướng dẫn native Inspire](#inspire-native)
> để build model và chạy pickup/place bằng `--sim-native-inspire --sim-assisted-pickup --sim-fixed-base`.
> Các lệnh chỉ có `--inspire-ftp-hands` bên dưới vẫn dùng hình học Dex3.


Repository: https://github.com/quyhuyhp123/g1-pickup-bottle-simulation

Tài liệu **clone repository này lần đầu**. Code simulation đã
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
git add README.md docs/source/tutorials/WSL_BLUE_BOTTLE_COMPLETE_GUIDE.md
git commit -m "Document setup and operation from personal repository"
git push origin main
```

Đây là đường dẫn trên máy tác giả; người clone chỉ cần đọc hướng dẫn, không
cần thư mục share_code_only. Không chạy các script install mỗi lần mở robot:
chúng có thể xóa và tạo lại venv.

## 12. Tài liệu liên quan

- [Điều khiển simulation](#simulation-controls): các nút và ý nghĩa tọa độ.
- [Bản ghi đầy đủ thay đổi/code](#legacy-wsl-snapshot): phụ lục patch
  lịch sử. Không áp WBC patch vào repository cá nhân lần nữa.
- [README upstream](../../../UPSTREAM_README.md): bối cảnh dự án NVIDIA gốc.

Repository cá nhân giữ license/ghi nhận nguồn upstream. Hướng dẫn này chưa
được kiểm chứng bằng một lượt cài Windows sạch; bản simulator đang chạy và các
kiểm thử là bằng chứng chức năng, không thay cho kiểm thử cài mới trên mọi GPU.


<a id="simulation-controls"></a>

## Các nút điều khiển và tọa độ

# Điều khiển chai và robot trong MuJoCo

> Với bàn tay 5 ngón **Inspire RH56DFTP native**, dùng
> [hướng dẫn Inspire](#inspire-native) và thêm
> `--sim-native-inspire --sim-assisted-pickup --sim-fixed-base`.
> Flag `--inspire-ftp-hands` bên dưới chỉ là adapter cho mô hình Dex3.


Giữ policy server v10 đang chạy, hoặc mở terminal riêng và chạy:

```bash
bash gear_sonic/scripts/run_cloudwalk_policy_server.sh
```

Detector riêng đã được cài trong môi trường hiện tại. Khi cài lại dự án, chạy
một lần `bash install_scripts/install_bottle_detector.sh`. Script tải YOLO11n
khoảng **5.4 MiB** và giữ nguyên các phiên bản Torch/GR00T đã cài.

Từ thư mục gốc dự án, khởi động simulation:

```bash
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim \
  --policy-host 127.0.0.1 \
  --policy-port 5550 \
  --no-data-exporter \
  --inspire-ftp-hands \
  --sim-assisted-pickup \
  --sim-fixed-base \
  --prompt "grab the bottle"
```

Launcher mở cửa sổ MuJoCo và bảng **Bottle / Robot Controls**. C++ deploy được
xác nhận tự động chỉ khi `deploy.sh` báo simulation và interface loopback `lo`.
Robot giữ cố định vị trí thân và tất cả khớp trên mặt đất ngay khi mở.
Chỉ khi bấm **Start GR00T**, hệ thống mới chuẩn bị SONIC và chuyển điều khiển
dần trong 2 giây; sau đó hỗ trợ khởi động tự tắt. Không cần bấm `9`.
Khóa tư thế chỉ áp dụng khi chờ/reset, không áp dụng trong lúc nắm/nâng.

**Chế độ gắp tại bàn dùng cả `--sim-assisted-pickup --sim-fixed-base`.**
Đế/pelvis được cố định bằng ràng buộc MuJoCo; các khớp không tham gia gắp giữ
tư thế chờ. Bộ hiệu chỉnh eo và cánh tay phải dùng ba lần
nhận diện RGB-D ổn định, bán kính chai và chiều cao bàn để tính tâm mục tiêu,
tiếp cận, khép ngón và nâng. Overlay **ASSISTED PICKUP - RGB-D + IK** hiển thị
giai đoạn thực tế. Chai được nâng bằng tiếp xúc vật lý, không gắn vào tay.
Server GR00T vẫn nhận ảnh/trạng thái và trả dự đoán để theo dõi; chế độ hỗ trợ
giữ token đứng của SONIC, còn quỹ đạo gắp được bộ điều khiển RGB-D/IK thực thi.
Đây là chế độ gắp hỗ trợ với đế cố định, không phải đánh giá checkpoint tự gắp.
Chạy hỗ trợ nhưng bỏ `--sim-fixed-base` sẽ dùng robot tự do; khả năng giữ
thăng bằng trong chế độ đó chưa ổn định.
Nếu bỏ `--sim-assisted-pickup` (và `--sim-fixed-base`), lệnh cũ chỉ dùng quỹ đạo checkpoint và điều kiện khép ngón;
điều kiện khép ngón không tự đưa tay đến chai.

Launcher bật bù mô-men trọng lực/Coriolis của MuJoCo cho vai, khuỷu và cổ tay.
SONIC gửi `tau_ff=0`; với Kp thấp, tay có thể võng đáng kể so với góc yêu cầu.
Bù này cộng `qfrc_bias` vào mô-men các khớp tay, giữ nguyên `q/dq` do SONIC
yêu cầu và giới hạn lực của simulator. Không áp dụng cho chân, eo hoặc robot
thật. Overlay **Arm gravity compensation** ghi ON/OFF. Để so sánh hành vi cũ,
thêm `--no-sim-arm-gravity-compensation` vào launcher.

Bù mô-men riêng lẻ chỉ sửa việc bám lệnh. Trong chế độ hỗ trợ nắm ở trên,
tọa độ RGB-D còn được dùng để hiệu chỉnh tiếp cận; không truyền XYZ vào GR00T.

YOLO11n chạy trên CPU trong tmux window **vision**, tự đọc camera ngay khi
simulation mở, kể cả trước khi bấm Start. Ảnh camera trực tiếp xuất
hiện ở góc phải trên cửa sổ MuJoCo, cập nhật độc lập với YOLO (không chờ
suy luận 2 Hz). Khung xanh YOLO dùng kết quả gần nhất, có tuổi nhận diện
riêng và tự ẩn sau 750 ms; đây không phải tracking liên tục. Dòng `Camera | age`
cho biết tuổi ảnh theo mili giây; quá 1 giây hiển thị `STALE CAMERA`.
Tọa độ nhận diện vẫn cập nhật theo detector; ô thông tin bên trái và bảng điều khiển
hiển thị **Detector surface XYZ / YOLO surface** cùng confidence.

## Thao tác

Sau khi nâng chai thành công (`success`), nút **Lower / Place on table**
(Hạ xuống / Đặt lên bàn) sẽ bật. Bấm một lần để robot hạ chậm về tư thế nắm
trên bàn, giữ ngón tay khép cho tới khi có tiếp xúc đỡ giữa chai và mặt bàn,
rồi mở ngón trong 2 giây. Sau khi xác nhận chai đứng trên bàn, robot tự
lùi bàn tay khỏi chai (`retreat`), thu cánh tay và eo về tư thế lúc bắt đầu
(`return_home`), rồi giữ nguyên tại `complete`. Không cần bấm thêm nút;
Reset vẫn có thể ngắt quá trình. Khi đạt `complete`, nút **Start GR00T**
sáng lại: bấm để nhận diện và gắp chai tại vị trí vừa đặt, không cần Reset.
Lượt mới xóa mục tiêu cũ và chờ ảnh nhận diện mới; giữ nguyên cảnh và vị trí
chai. Trong lúc đang gắp/đặt/thu tay, Start vẫn bị khóa.
Nếu hết quỹ đạo hạ mà chai chưa chạm bàn, robot dò xuống chậm 3 mm/s,
tối đa thêm 2 cm, và dừng ngay khi có tiếp xúc đỡ. Nếu vẫn không có tiếp xúc,
hệ thống giữ tay khép và báo lỗi thay vì thả chai.
Nút này dành cho `--sim-assisted-pickup`; Reset vẫn có thể ngắt thao tác.
Khởi động lại simulation sau khi cập nhật code để thấy nút mới.

Để đặt sang vị trí khác, nhập **Place destination X/Y** ngay phía trên nút
**Lower / Place on table**, rồi bấm nút này. Đây là tọa độ thế giới theo mét
của tâm chai khi đặt; Z vẫn theo mặt bàn. Ví dụ gắp ở `(0.43, -0.11)` rồi
đặt ở `(0.43, -0.08)`. Robot giữ chai khép trong tay, di chuyển ngang khi còn
nâng cao, sau đó hạ và mở tay. Đích nằm ngoài bàn hoặc không giải được IK
sẽ bị từ chối; giữ chai và chọn đích gần hơn. Xác nhận đặt thành công yêu cầu chai
đứng trên bàn, sai lệch XY dưới 2.5 cm; không bảo đảm chính xác tuyệt đối.
Hai ô vị trí chai ban đầu/Apply ở trên vẫn chỉ dùng đặt cảnh trước Start.
Đích đặt xuống không thay đổi tọa độ chai dùng cho Reset.

1. Nhập **X**, **Y** theo mét, dùng dấu chấm thập phân. Bấm
   **Apply X/Y / Reset bottle** để đặt/dựng lại chai.
2. Bấm **Start GR00T**. Robot giữ tư thế trong khi chờ SONIC sẵn sàng, chuyển
   điều khiển dần rồi lấy ảnh mới để suy luận và xác định mục tiêu nắm.
3. Bấm **Reset robot + bottle** để dừng suy luận, loại bỏ động tác còn tồn,
   đưa robot về tư thế/địa điểm khởi động và dựng chai tại X/Y đã chọn.
   Sau reset, robot chờ lần bấm Start tiếp theo. Reset này đặt lại cả đồng hồ
   simulation.
4. Để đổi X/Y khi robot đang chạy, bấm Reset trước. Đóng riêng bảng điều khiển
   không tắt simulation; bấm **F2** trong cửa sổ MuJoCo để mở lại.

Sau mỗi Reset, mục tiêu nhận diện, tiến trình nắm/nâng, vận tốc và hàng đợi
hành động cũ được xóa. X/Y đã chọn của chai được giữ lại để lặp lượt thử.
Muốn thử vị trí mới: **Reset → nhập X/Y → Apply X/Y → Start**. Bộ hiệu chỉnh
ước lượng lại mục tiêu từ camera mỗi lượt. Vị trí phải nằm trong tầm tay phải
và nhìn thấy được; nằm trên bàn chưa chắc đã nằm trong tầm với.
Có thể đặt vị trí ngay trong lệnh khởi động bằng cách thêm
`--sim-bottle-xy 0.40 -0.15`. Reset vẫn giữ X/Y đã chọn; khi mở bảng điều khiển,
các ô X/Y hiển thị đúng vị trí này.

Đã kiểm thử camera + server với chế độ hỗ trợ/đế cố định tại ba vị trí
`(0.43, -0.11)`, `(0.40, -0.15)` và `(0.46, -0.08)` m: chai được giữ bằng
tiếp xúc ngón tay và nâng tối thiểu lần lượt khoảng **18.2, 18.2 và 13.5 cm**
trong giai đoạn giữ. Báo cáo nằm ở `outputs/assisted_audit/final_live_*.json`.
Đây là các vị trí đã đo, không bảo đảm mọi điểm trên bàn đều gắp được.

Phím tắt trong cửa sổ MuJoCo: **F5** reset robot + chai, **F6** Start.
**R** chỉ dựng lại chai ở X/Y đã chọn, giữ robot và đồng hồ; nên dừng lượt chạy
trước khi dùng R. Luồng terminal `k`, `i`, `p` vẫn được hỗ trợ, nhưng bảng điều
khiển xử lý trình tự bắt đầu và reset đầy đủ hơn.

X/Y được kiểm tra để thân chai nằm trong mặt bàn. Với scene hiện tại:
X từ **0.276 đến 0.724 m**, Y từ **-0.424 đến 0.424 m**.
Z lúc đặt chai cố định **0.801 m** tại tâm hình trụ thân chai, mặt bàn cao
**0.700 m**. Khi vật lý chạy, chai có thể đổ hoặc được nâng nên Z đo được
thực tế sẽ thay đổi. Các thay đổi X/Y chỉ tồn tại trong phiên simulation;
khởi động lại đọc vị trí từ XML hoặc `--sim-bottle-xy` nếu được truyền vào.

## Các tọa độ hiển thị

Overlay trong MuJoCo và bảng điều khiển cập nhật liên tục:

- **Bottle centre / Bottle MuJoCo**: tâm thân chai do MuJoCo cung cấp.
- **Right wrist**, **Left wrist**: gốc khung tọa độ hai cổ tay,
  không phải đầu ngón tay hay tâm vùng kẹp.
- Tất cả dùng hệ tọa độ thế giới, đơn vị mét: +X hướng về phía trước của robot
  lúc khởi động, -Y về phía tay phải.
  +Y hướng về phía tay trái, +Z hướng lên. Xoay góc nhìn MuJoCo không đổi
  các trục này; khi robot quay người, hướng trước của robot có thể khác +X.
- **Ground support** cho biết hỗ trợ đang bật lúc chờ/reset hay đã tắt.
- **Published actions** tăng khi VLA gửi hành động tới SONIC.
- **Detector surface XYZ / YOLO surface**: tọa độ nhận diện ước lượng bằng
  YOLO11n từ RGB, kết hợp depth camera và thông số camera để đổi sang hệ thế giới.
  Đây là một điểm nhìn thấy trên bề mặt gần tâm khung nhận diện, **không phải
  tâm thân chai**. Vì vậy Z có thể khác 0.801 m, kể cả khi chai đứng trên bàn.
- **YOLO bottle confidence**: độ tin cậy nhận diện lớp `bottle`; ngưỡng mặc định
  0.25. Chấm đỏ trong ảnh camera là điểm dùng để ước lượng XYZ.

Checkpoint hiện tại xuất `motion_token` và lệnh tay, **không xuất tọa độ XYZ,
bounding box hoặc kết quả detect chai riêng**. Dòng **GR00T detected XYZ** vì
vậy ghi `unavailable in checkpoint output`. Tọa độ từ detector mới được ghi
riêng với nguồn **YOLO**, không được gắn nhãn GR00T. Detector không đọc body ID
hay vị trí chai thật; input của nó là RGB, depth và thông số camera. Khi không
bật `--sim-assisted-pickup`, tọa độ YOLO chỉ để quan sát/xác nhận có chai.
Chế độ khép tay theo khoảng
cách bên dưới dùng hình học MuJoCo làm điều kiện khép ngón, nhưng vẫn không
đưa XYZ vào policy làm tọa độ mục tiêu.
Nút Start bắt đầu suy luận từ ảnh mới; không có bước xác nhận detect XYZ riêng.
Các thao tác giao diện này không bảo đảm checkpoint gắp/nâng chai thành công.

Nếu không thấy chai, có che khuất hoặc mất camera, tọa độ detector bị xóa và
hiện trạng thái `not_detected`, `waiting` hoặc `stale`; không dùng lại XYZ cũ.
YOLO vẫn có thể nhận diện sai hoặc điểm depth nằm trên vật che phía trước.

Để tắt detector và ảnh depth, thêm `--no-bottle-detection` vào lệnh launcher.
Kết quả mới nhất được lưu ở `outputs/bottle_detector/latest.json`.
Nguồn model và API: [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/),
[Predict](https://docs.ultralytics.com/modes/predict/).

Nếu camera ngắt hoặc ảnh quá cũ, VLA tự tạm dừng thay vì tiếp tục động tác cũ.
Kiểm tra pane inference rồi bấm Reset và Start để chạy lại.

Các nhãn giao diện dùng tiếng Anh vì Tk trong môi trường WSL hiện tại chỉ có
font bitmap không hiển thị đầy đủ tiếng Việt.

## Khép tay theo tâm vùng nắm và hai trục X/Y

Phần này mô tả chế độ cũ khi **không bật `--sim-assisted-pickup`**.
Chế độ hỗ trợ ở lệnh đầu trang thay thế bộ kích hoạt này bằng tiếp cận theo X,
khép ngón và nâng, có kiểm tra tiếp xúc đối diện và giữ chai trong 3 giây.

Lệnh launcher `--sim` với detector đang bật tự dùng khoảng hở Y **2 cm** và
sai số X **±5 mm**. Thêm `--sim-grasp-distance 0` để dùng lại lệnh tay GR00T.

Điểm tham chiếu là **tâm vùng nắm giữa bàn tay**, site
`right_hand_grasp_center`, gắn cố định vào `right_wrist_yaw_link` tại tọa độ
cục bộ `(0.120, 0.050, 0.000) m` của bàn tay Dex3 hiện tại. Đây là điểm quy ước
trong khoảng ôm vật của bàn tay. Tọa độ thế giới được tính bằng
`grasp_world = wrist_world + wrist_rotation @ grasp_local`.
Không dùng đầu ngón tay, trọng tâm khối lượng COM hay gốc cổ tay làm điều kiện.
Gập các ngón không làm điểm tham chiếu này di chuyển trong khung bàn tay.
Offset này dành cho hình học Dex3; nếu thay bàn tay cần hiệu chỉnh site theo
vùng nắm của bàn tay mới.

**Chấm xanh** trong cửa sổ MuJoCo đánh dấu điểm đang kiểm tra. Marker thuộc
site group 5, không có khối lượng/va chạm và bị ẩn khỏi ảnh camera đầu vào GR00T.
Bảng điều khiển và overlay **GRASP CENTRE - X/Y** hiển thị XYZ của điểm này,
X error, Y surface gap, ngưỡng và trạng thái chờ/khép/giữ.
Dòng **Wrist origin** là gốc cổ tay, khác điểm nắm; không so trực tiếp tọa độ
cổ tay với tâm chai để kết luận tay đã tới vật.

Sau Start và nhận diện chai bằng YOLO, hai điều kiện phải đúng cùng lúc:

- `abs(grasp_center.x - bottle_body_center.x) <= 0.005 m`.
- Khoảng hở từ tâm vùng nắm đến bề mặt thân chai theo Y còn **0 đến 0.02 m**.

Với chai đứng, tại X trùng và Z trong thân chai,
`Y_gap = abs(grasp_center.y - bottle_center.y) - bottle_radius`.
Bán kính chai **2.5 cm**, nên khoảng hở 2 cm tương ứng chênh lệch Y với tâm chai
**4.5 cm**. Ví dụ chai `(0.430, -0.110, 0.801)`, điểm nắm tại
`(0.430, -0.155, 0.840)` đạt ngưỡng. Khi chai có độ nghiêng, phép đo dùng
hướng hình trụ hiện tại. X/Z ngoài tiết diện thân chai hiện `--` và không khép.

Điều kiện hiện tại là **tiếp cận ngang theo Y**: X trùng chai, Y còn hở 2 cm.
Nếu muốn **tiếp cận từ trước robot theo X**, điều kiện tương ứng sẽ là
Y trùng chai, X còn hở 2 cm. Ví dụ cùng chai ở trên, điểm nắm
`(0.385, -0.110, 0.840)` cách bề mặt 2 cm theo X. Đây là cách đối chiếu trục,
không phải một chế độ tự đổi hướng trong code. Cả hai cách đều cần điểm nắm
nằm trong chiều cao thân chai; đổi X/Y không sửa được quỹ đạo tay còn xa hoặc
cao hơn thân chai. Ngưỡng khép ngón chỉ quyết định thời điểm nắm, không đặt
tọa độ mục tiêu cho cánh tay.

Tay phải giữ mở trước ngưỡng, khép dần trong **0.3 giây** khi đạt cả hai điều
kiện, rồi giữ khép tới Reset. Chai nghiêng quá 30 độ không kích hoạt.
Nhận diện được ghi nhớ trong lượt để việc tay che camera không làm mất xác
nhận; Reset hoặc đặt lại chai xóa xác nhận này.

Nguồn khoảng cách là hình học MuJoCo; YOLO chỉ xác nhận có chai. GR00T/SONIC
vẫn điều khiển quỹ đạo thân/cánh tay/nâng. Ô **SONIC grasp (FK)** hiển thị vị trí
điểm nắm theo lệnh khớp SONIC tại vị trí thân hiện tại; **Grasp tracking error**
cho biết bàn tay thực tế lệch bao xa so với lệnh. Đây là tọa độ tính bằng FK,
không phải tọa độ mục tiêu XYZ do GR00T xuất.
Nếu cả lệnh và vị trí thực đều thiếu X, điều kiện khép không tự đưa cánh tay tới
chai. Nếu lệnh đã tới nhưng tay thực chưa tới, cần xử lý việc bám lệnh khớp.

**Không dùng chế độ ngưỡng cũ để chạy bài gắp/nâng/đặt chai đã kiểm thử.**
Hai tham số `--sim-grasp-distance 0.02 --sim-grasp-x-tolerance 0.005`
chỉ kiểm tra thời điểm khép ngón; chúng không bật hiệu chỉnh tiếp cận hay nâng.
Để chạy bài gắp tại bàn, dùng lệnh ở đầu tài liệu có cả
`--sim-assisted-pickup --sim-fixed-base`. Nút Lower cũng cần chế độ hỗ trợ này.

Log `proximity_grasp_trigger` ghi `grasp_center_world_m`, `x_error_m`,
`y_surface_gap_m` và nguồn phép đo. COM khối lượng chỉ còn là dữ liệu chẩn
đoán riêng, không được dùng để kích hoạt nắm. Khi chạy robot thật hoặc tắt
detector, launcher không bật bộ điều khiển khép tay bổ sung này.


<a id="standalone-pickup"></a>

## Demo gắp độc lập

# Assisted blue bottle pickup in MuJoCo

Run from the repository root:

```bash
.venv_sim/bin/python gear_sonic/scripts/run_blue_bottle_pickup.py
```

This opens an independent MuJoCo demo and automatically approaches, closes the
right Dex3 hand, lifts the blue bottle, and holds it. Close the viewer to finish.
No GR00T server, SONIC process, DDS, tmux launcher, or keyboard commands are needed.
It does not connect to a physical robot.

This is an **assisted inverse-kinematics grasp**, using the bottle pose from
MuJoCo. It is not a successful evaluation of the GR00T checkpoint. The pelvis is
anchored to the world to stabilize manipulation. The bottle remains a free body
and is held through physical finger contacts and friction, with no hand-object
weld, object teleportation, or external lifting force.

The CloudWalk checkpoint's training dataset uses Inspire FTP hands:
https://huggingface.co/datasets/cloudwalk-research/gr00t-g1-grab-bottle-right-hand-v2
The scene uses Dex3. Converting normalized grip level to a Dex3 closed pose does
not reproduce Inspire grasp geometry or reach/grip timing. A task-trained Dex3
checkpoint or a separately validated VLA/IK hybrid is needed for autonomous
vision-conditioned pickup with this embodiment.

The demo solves wrist position and orientation with waist pitch and the right
arm, applies PD joint control with gravity compensation, gradually closes the
hand, and lifts 18 cm. Joint limits and actuator effort limits remain enforced.
The initial arm pregrasp pose is set before simulation begins. Current grasp
geometry is tuned for this scene's cylindrical bottle, not arbitrary objects.

Validation and video recording:

```bash
MUJOCO_GL=egl .venv_sim/bin/python gear_sonic/scripts/run_blue_bottle_pickup.py \
  --headless --record
```

Outputs are written to `outputs/blue_bottle_pickup/`: `report.json`,
`third_person.mp4`, `ego_view.mp4`, and images of the held bottle. Success requires
at least 12 cm lift throughout a 3-second hold and persistent contact from both
thumb and index/middle fingers. Reports contain actual bottle/wrist coordinates
and finger contacts, not model-predicted object coordinates.

Small workspace perturbations can be checked using `--bottle-offset X Y` in
meters. IK raises an error if it cannot reach the requested grasp pose.


<a id="checkpoint-notes"></a>

## Checkpoint và adapter: thông tin đối chiếu

# CloudWalk checkpoint and Inspire FTP compatibility

The local `~/models/g1_sonic_grab_bottle` identifies itself as a deployment export
of a 4-GPU, batch-64, 10k-step run. It is not the official v2 `checkpoint-20000`
(6-GPU, batch-48 training recipe). Both have the same embodiment name; that does
not imply identical training or interchangeable hand kinematics.

Official v2 source:
https://huggingface.co/cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-210ep-v2-finetune
Dataset:
https://huggingface.co/datasets/cloudwalk-research/gr00t-g1-grab-bottle-right-hand-v2

The official weights are stored separately at
`checkpoints/cloudwalk_g1_bottle_v2/checkpoint-20000`. The existing weights are
not modified. Audit tensor headers, shard completeness and hand statistics:

```bash
.venv_inference/bin/python gear_sonic/scripts/check_cloudwalk_checkpoint.py \
  checkpoints/cloudwalk_g1_bottle_v2/checkpoint-20000
```

After stopping the existing policy server on port 5550, start the official one:

```bash
bash gear_sonic/scripts/run_cloudwalk_policy_server.sh
```

The server still emits motion tokens plus Inspire FTP hand channels. This is not
an Inspire hand simulator. The experimental `--inspire-ftp-hands` client option
maps aggregate grip intent to a Dex3 pose; it does not emulate the original hand.

Native deployment still requires the CloudWalk `InspireFTPGripMapper` (or a
validated equivalent) and an Inspire-compatible simulator/DDS bridge. The
official Unitree repository does provide a G1 Inspire FTP URDF and meshes:
https://github.com/unitreerobotics/unitree_ros/blob/master/robots/g1_description/g1_29dof_rev_1_0_with_inspire_hand_FTP.urdf
The hand URDFs also define passive finger mimic joints. These must be preserved
as constraints in MuJoCo; replacing a filename does not convert the current
seven-motor Dex3 bridge into the six-motor Inspire interface. The CloudWalk repository
linked in the dataset (`cloudwalk-research/GR00T-WholeBodyControl`) returned 404
when inspected. The two supplied NVIDIA repositories contain the server and
Dex3 control stack. Isaac-GR00T includes RoboCasa references to `InspireRightHand`
for Fourier GR1, which do not establish the correct G1 RH56DFTP mount or channel
mapping. Upstream compatibility discussion:
https://github.com/NVlabs/GR00T-WholeBodyControl/issues/121

Do not reinterpret seven FTP channels as seven Dex3 joint angles or rename the
Dex3 scene as Inspire. Needed next: original hand model + mapper, or task data
and fine-tuning collected with the actual Dex3 embodiment.

The official model card also reports grasp anticipation even with an absent
bottle; successful reach motion alone is not proof of reliable object detection.
The simulation task must be evaluated closed loop after hand compatibility is
resolved. Neither checkpoint download nor a successful server query demonstrates
physical pickup.

## Recorded-input verification

`outputs/input_audit/training_inference.json` records calls to the running
checkpoint-20000 server using synchronized RGB frames and joint states from
episode 0 of the training dataset. At frame 480, the source grip begins at 0.30
and reaches 1.00 in the next 40 frames; the model predicts 0.307 to 1.00.
At frame 500, source grip begins at 0.70; the model predicts 0.676 to 1.00.
This checks the server's ability to emit a closing sequence without sending any
action to the robot. It does not demonstrate simulated pickup.

`outputs/input_audit/input_ablation.json` contains three inference trials per
combination of recorded/live image and recorded/live body state. Grip predictions
vary, and even a simulation image without the bottle in view can elicit closing
with recorded grasp-phase body state. Therefore neither reaching nor closing is
evidence of object detection. The experiment cannot attribute failure to only
the image or only the body state.

The model card's success rates describe the physical G1 + Inspire stack, not
this MuJoCo scene. Preserve that distinction when evaluating a port.

## Bottle position and manual reset

The blue bottle's initial body position in `scene_43dof.xml` is
`0.43 -0.11 0.801` metres, 5 cm closer to the initial robot position than before.
Restart the simulation stack to load XML/Python changes and reconnect deploy;
the policy server does not need restarting.

Focus the MuJoCo window and press **R** to restore only the bottle's initial
position and upright orientation, with zero object velocity. The reset is
queued onto the physics thread and does not reset the robot, controls, or clock.
To repeat a trial, first send **i** + Enter in the keyboard publisher pane to
pause the policy and return to the initial open-hand pose, then press **R** in
MuJoCo and send **p** + Enter in the keyboard pane to resume inference. The
MuJoCo key is separate from the keyboard publisher's policy controls.


<a id="disk-cleanup"></a>

## Dọn dung lượng đã thực hiện

Đã xóa **6.828 GiB** dung lượng file được cấp phát trong WSL:

- Cache model gốc `~/.cache/huggingface/hub/models--nvidia--GR00T-N1.7-3B`:
  job hiện tại dùng checkpoint CloudWalk v10 nằm riêng trong `checkpoints/`.
- Log `.jsonl`, log xoay vòng và `.log` không còn được process mở trong `outputs/`.
- Log Xet không dùng và file ảnh/trạng thái/log test Inspire tạm trong `/tmp`.

Giữ checkpoint v10, cache `Cosmos-Reason2-2B` (backbone được code nạp khi khởi động),
cache SONIC, model/mesh, ba môi trường Python, Git, bản sao repository để push,
report JSON và toàn bộ mã chạy simulation. Muốn dùng model GR00T gốc lại sau này
thì phải tải lại cache vừa dọn.

### Thu hồi dung lượng vật lý trên ổ C

WSL dùng VHDX; dung lượng trống trong Linux không nhất thiết lập tức trở thành
dung lượng trống ổ C. Đĩa đã xác định từ registry cho `Ubuntu-22.04`:

```text
C:\Users\Admin\AppData\Local\wsl\{78e88ad2-f985-4dce-b6a5-f381f0e1894a}\ext4.vhdx
```

Khi đã lưu công việc và dừng simulation/server, chạy trong WSL:

```bash
sudo fstrim -v /
```

Sau đó **đóng VS Code WSL**, mở PowerShell **Run as administrator**:

```powershell
wsl --shutdown
diskpart
```

Trong cửa sổ `DISKPART>`:

```text
select vdisk file="C:\Users\Admin\AppData\Local\wsl\{78e88ad2-f985-4dce-b6a5-f381f0e1894a}\ext4.vhdx"
compact vdisk
exit
```

Đường dẫn trên chỉ dành cho máy này; trên máy khác phải xác định lại. Đĩa cần
ở trạng thái detached hoặc attached read-only khi compact. Không dùng lệnh
`clean`, `format`, hoặc xóa file VHDX. Chưa thực hiện shutdown/compact trong lượt
dọn này vì thao tác đó ngắt chính phiên WSL đang làm việc.

Nguồn: [Microsoft: WSL disk space](https://learn.microsoft.com/en-us/windows/wsl/disk-space),
[Microsoft: compact vdisk](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/compact-vdisk).

### Danh sách đã xóa

```text
6594.61 MiB  /home/huy123/.cache/huggingface/hub/models--nvidia--GR00T-N1.7-3B
5.73 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/grasp_center_final/reach.jsonl
11.19 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/grasp_center_final/actions.jsonl
7.79 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/arm_compensation_trial/reach.jsonl
16.67 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/arm_compensation_trial/actions.jsonl
17.16 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/fixed_actions.jsonl
1.25 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/stationary_actions.jsonl
7.59 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/stationary_reach.jsonl
16.09 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/final_reach.jsonl
23.90 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/far_reach.jsonl
12.07 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/startup_actions.jsonl
9.47 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/live_actions.jsonl
29.15 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/fixed_reach.jsonl
6.82 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/live_reach.jsonl
11.26 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/final_actions.jsonl
32.00 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/final_actions.jsonl.1
13.06 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/near_reach.jsonl
32.00 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/final_reach.jsonl.1
32.00 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/fixed_actions.jsonl.1
10.34 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/assisted_audit/startup_reach.jsonl
7.18 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/hand_com_final/reach.jsonl
8.58 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/hand_com_final/actions.jsonl
0.00 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/input_audit/meta/tasks.jsonl
8.05 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/cleanup_validation/reach.jsonl
14.46 MiB  /home/huy123/projects/GR00T-WholeBodyControl/outputs/cleanup_validation/actions.jsonl
0.00 MiB  /home/huy123/.cache/huggingface/xet/logs/xet_20261006T223854206+0700_1557.log
17.45 MiB  /home/huy123/.cache/huggingface/xet/logs/xet_20261004T100427718+0700_3031.log
0.08 MiB  /home/huy123/.cache/huggingface/xet/logs/xet_20261002T005802981+0700_8771.log
10.45 MiB  /home/huy123/.cache/huggingface/xet/logs/xet_20261004T101720620+0700_7135.log
13.71 MiB  /tmp/native_resume_reach.jsonl
21.18 MiB  /tmp/native_live_reach.jsonl
0.01 MiB  /tmp/native_trial.log
0.00 MiB  /tmp/native_observation_tests.log
0.00 MiB  /tmp/native_hold_grid.log
0.00 MiB  /tmp/native_longhold_regression.log
0.00 MiB  /tmp/native_grid2.log
0.00 MiB  /tmp/native_resume_launch.log
0.01 MiB  /tmp/native_case2.log
0.00 MiB  /tmp/native_regression2.log
0.00 MiB  /tmp/native_regression.log
0.00 MiB  /tmp/native_final_physics.log
0.00 MiB  /tmp/native_launch2.log
0.01 MiB  /tmp/native_trial3.log
0.00 MiB  /tmp/native_ready_launch.log
0.00 MiB  /tmp/native_regression3.log
0.01 MiB  /tmp/native_trial2.log
0.00 MiB  /tmp/native_launch.log
0.01 MiB  /tmp/native_trial4.log
0.00 MiB  /tmp/native_grid.log
0.00 MiB  /tmp/native_release_2360.npz
0.00 MiB  /tmp/native_release_2080.npz
0.00 MiB  /tmp/native_release_1320.npz
0.00 MiB  /tmp/native_release_2160.npz
0.00 MiB  /tmp/native_release_1600.npz
0.00 MiB  /tmp/native_release_2320.npz
0.00 MiB  /tmp/native_release_1720.npz
0.00 MiB  /tmp/native_release_1440.npz
0.00 MiB  /tmp/native_release_2040.npz
0.00 MiB  /tmp/native_release_1400.npz
0.00 MiB  /tmp/native_release_1240.npz
0.00 MiB  /tmp/native_release_1640.npz
0.00 MiB  /tmp/native_release_1920.npz
0.00 MiB  /tmp/native_release_1880.npz
0.00 MiB  /tmp/native_release_1520.npz
0.00 MiB  /tmp/native_release_1680.npz
0.00 MiB  /tmp/native_release_1120.npz
0.00 MiB  /tmp/native_release_2280.npz
0.00 MiB  /tmp/native_release_1840.npz
0.00 MiB  /tmp/native_release_1160.npz
0.00 MiB  /tmp/native_release_2240.npz
0.00 MiB  /tmp/native_release_1280.npz
0.00 MiB  /tmp/native_release_2120.npz
0.00 MiB  /tmp/native_release_2200.npz
0.00 MiB  /tmp/native_end.npz
0.00 MiB  /tmp/native_release_1560.npz
0.00 MiB  /tmp/native_release_2000.npz
0.00 MiB  /tmp/native_release_1480.npz
0.00 MiB  /tmp/native_release_1960.npz
0.00 MiB  /tmp/native_release_1360.npz
0.00 MiB  /tmp/native_release_2400.npz
0.00 MiB  /tmp/native_release_1200.npz
0.20 MiB  /tmp/native_release.png
0.04 MiB  /tmp/native_panel.png
```

<a id="current-code-patch"></a>

## Bản vá code hiện tại

Bản vá so với Git HEAD `323211ddd5012b0f377e3ee5bc788d634765191e`; bao gồm file mới chưa commit.
Chỉ chứa mã chạy và test; không chứa model binary hoặc môi trường Python.
Không áp lại patch lên workspace hiện tại vì các sửa đổi đã nằm trong file.

```diff
diff --git a/gear_sonic/scripts/launch_inference.py b/gear_sonic/scripts/launch_inference.py
index 00504a1..e167715 100644
--- a/gear_sonic/scripts/launch_inference.py
+++ b/gear_sonic/scripts/launch_inference.py
@@ -55,6 +55,8 @@ def _bootstrap_venv():
         pass
 
     repo_root = Path(__file__).resolve().parent.parent.parent
+    if config.sim_native_inspire and not (repo_root / 'models/g1_inspire_ftp/g1_inspire_ftp_pickup.xml').exists():
+        errors.append('Build native hands first: .venv_sim/bin/python gear_sonic/scripts/prepare_inspire_ftp_sim.py')
     venv_python = repo_root / ".venv_inference" / "bin" / "python"
     if not venv_python.exists():
         print(
@@ -104,6 +106,9 @@ class InferenceLaunchConfig:
     sim_assisted_pickup: bool = False
     """Use RGB-D target correction for right-arm approach, physical grasp and lift; SONIC controls the body. Simulation only."""
 
+    sim_native_inspire: bool = False
+    """Native Inspire FTP hand model, requires assisted fixed-base simulation."""
+
     sim_fixed_base: bool = False
     """Anchor the simulated pelvis and hold unused joints for repeatable table pickup. Requires --sim-assisted-pickup."""
 
@@ -211,6 +216,8 @@ def _check_prerequisites(config: InferenceLaunchConfig):
     errors = []
     if config.sim_bottle_xy is not None and not config.sim:
         errors.append("--sim-bottle-xy requires --sim")
+    if config.sim_native_inspire and not (config.sim and config.sim_assisted_pickup and config.sim_fixed_base):
+        errors.append('--sim-native-inspire requires --sim --sim-assisted-pickup --sim-fixed-base')
     if config.sim_fixed_base and (not config.sim or not config.sim_assisted_pickup):
         errors.append("--sim-fixed-base requires --sim --sim-assisted-pickup")
     if config.sim_assisted_pickup and (not config.sim or not config.bottle_detection):
@@ -363,6 +370,9 @@ def main(config: InferenceLaunchConfig):
         print(f"  Hand closure:    grasp-region centre | X +/- {config.sim_grasp_x_tolerance * 100:.1f} cm | "
               f"Y surface gap <= {config.sim_grasp_distance * 100:.1f} cm")
     if config.sim:
+        print(f"  Hand model:      {'Native Inspire FTP (six motors per hand)' if config.sim_native_inspire else 'Dex3'}")
+        if config.sim_native_inspire:
+            print("  Policy state:    approximate Dex3-compatible projection; native hand motion owned by assisted controller")
         print(f"  Arm feedforward: {'ON' if config.sim_arm_gravity_compensation else 'OFF'} (MuJoCo bias)")
         if config.sim_assisted_pickup:
             print("  Pickup:          RGB-D waist/right-arm correction; SONIC standing token")
@@ -403,6 +413,8 @@ def main(config: InferenceLaunchConfig):
             sim_cmd += " --arm-gravity-compensation"
         if config.sim_assisted_pickup:
             sim_cmd += " --assisted-pickup"
+        if config.sim_native_inspire:
+            sim_cmd += " --native-inspire"
         if config.sim_fixed_base:
             sim_cmd += " --fixed-pickup-base"
         if config.sim_bottle_xy is not None:
diff --git a/gear_sonic/scripts/run_cloudwalk_policy_server.sh b/gear_sonic/scripts/run_cloudwalk_policy_server.sh
index 14ab162..a7d38e6 100755
--- a/gear_sonic/scripts/run_cloudwalk_policy_server.sh
+++ b/gear_sonic/scripts/run_cloudwalk_policy_server.sh
@@ -11,8 +11,8 @@ if [[ ! -x "$SERVER_PYTHON" || ! -f "$SERVER_SCRIPT" ]]; then
     exit 1
 fi
 "$REPO_ROOT/.venv_inference/bin/python" "$SCRIPT_DIR/check_cloudwalk_checkpoint.py" "$CHECKPOINT"
-echo "Starting CloudWalk checkpoint: $CHECKPOINT. Simulator uses Dex3."
-echo "Native Inspire FTP hand deployment has not been implemented or validated."
+echo "Starting CloudWalk checkpoint: $CHECKPOINT. Select the simulated hand in launch_inference.py."
+echo "Native Inspire simulation requires --sim-native-inspire --sim-assisted-pickup --sim-fixed-base. Hardware deployment is not validated."
 cd "$REPO_ROOT/../Isaac-GR00T"
 # Version checks are unrelated to inference and can stall startup on WSL when
 # the update endpoint is unreachable.
diff --git a/gear_sonic/scripts/run_sim_loop.py b/gear_sonic/scripts/run_sim_loop.py
index d3ca87f..604a7f4 100644
--- a/gear_sonic/scripts/run_sim_loop.py
+++ b/gear_sonic/scripts/run_sim_loop.py
@@ -53,6 +53,11 @@ def main(config: ArgsConfig):
     if config.fixed_pickup_base and not config.assisted_pickup:
         raise ValueError("Fixed pickup base requires assisted pickup")
     wbc_config["FIXED_PICKUP_BASE"] = config.fixed_pickup_base
+    if config.native_inspire:
+        if not config.fixed_pickup_base or not config.assisted_pickup:
+            raise ValueError('Native Inspire requires --assisted-pickup --fixed-pickup-base')
+        wbc_config.update(NATIVE_INSPIRE=True, NUM_HAND_JOINTS=6, NUM_HAND_MOTORS=0, ASYNC_IMAGE_RENDER=True,
+            ROBOT_SCENE='models/g1_inspire_ftp/g1_inspire_ftp_pickup.xml')
     wbc_config["BOTTLE_XY"] = config.bottle_xy
     wbc_config["GROUND_START"] = config.ground_start
     wbc_config["ENABLE_DEPTH_PUBLISH"] = config.enable_depth_publish
diff --git a/gear_sonic/scripts/run_vla_inference.py b/gear_sonic/scripts/run_vla_inference.py
index d7bb646..76fe75c 100644
--- a/gear_sonic/scripts/run_vla_inference.py
+++ b/gear_sonic/scripts/run_vla_inference.py
@@ -267,6 +267,14 @@ def prepare_observation_from_sensors(
             print("[DEBUG] prepare_observation: waiting for state msg..", flush=True)
         return None
 
+    state_msg = dict(state_msg)
+    hand_format = state_msg.pop('hand_state_format', 'dex3_joint_radians')
+    if hand_format == 'inspire_ftp_motor_radians':
+        from gear_sonic.utils.mujoco_sim.inspire_hand import dex3_observation_from_inspire
+        for side in ('left', 'right'):
+            state_msg[side+'_hand_q'] = dex3_observation_from_inspire(state_msg[side+'_hand_q'], side)
+    elif hand_format != 'dex3_joint_radians':
+        raise ValueError(f'Unsupported hand observation format: {hand_format}')
     state_msg = {key: np.asarray(value).copy() for key, value in state_msg.items()}
 
     cam_img = camera_msg["images"]["ego_view"]
diff --git a/gear_sonic/tests/test_observation_freshness.py b/gear_sonic/tests/test_observation_freshness.py
index 6541d91..2d0efd9 100644
--- a/gear_sonic/tests/test_observation_freshness.py
+++ b/gear_sonic/tests/test_observation_freshness.py
@@ -44,6 +44,23 @@ class ObservationFreshnessTest(unittest.TestCase):
         np.testing.assert_array_equal(obs["state"]["projected_gravity"], [[[0., 0., -1.]]])
         self.assertEqual(obs["language"]["annotation.human.task_description"], [["grab the bottle"]])
 
+    def test_native_inspire_frame_projects_six_motors_without_index_error(self):
+        robot = instantiate_g1_robot_model(waist_location="lower_and_upper_body")
+        class Camera:
+            def read(self):
+                return {"capture_monotonic": time.monotonic(),
+                        "images": {"ego_view": np.zeros((480, 640, 3), dtype=np.uint8)},
+                        "timestamps": {"ego_view": time.time()},
+                        "robot_state": {"body_q": [0.] * 29,
+                            "left_hand_q": [1., 0., 0., 0., 0., 0.],
+                            "right_hand_q": [1., .4, .85, .85, .85, .85],
+                            "hand_state_format": "inspire_ftp_motor_radians",
+                            "base_quat": [1., 0., 0., 0.]}}
+        observation = prepare_observation_from_sensors(Camera(), None, robot, "grab the bottle")
+        self.assertIsNotNone(observation)
+        self.assertTrue(np.isfinite(observation['q']).all())
+        self.assertEqual(observation['state']['right_hand'].shape[-1], 7)
+
     def test_inflight_result_keeps_pre_reset_request_boundary(self):
         requests, results = queue.Queue(), queue.Queue()
         stop, busy, entered, release = (threading.Event() for _ in range(4))
diff --git a/gear_sonic/utils/mujoco_sim/assisted_pickup.py b/gear_sonic/utils/mujoco_sim/assisted_pickup.py
index 978236a..d5022f9 100644
--- a/gear_sonic/utils/mujoco_sim/assisted_pickup.py
+++ b/gear_sonic/utils/mujoco_sim/assisted_pickup.py
@@ -1,4 +1,4 @@
-"""Opt-in visual pickup correction for the simulated right arm and Dex3 hand.
+"""Opt-in visual pickup correction for the simulated right arm and Dex3/Inspire hand.
 
 SONIC retains the floating base, legs and left arm. This controller only
 sets joint torques; it never attaches, teleports or applies a force to the bottle.
@@ -36,8 +36,13 @@ class AssistedPickup:
         self.arm = np.array([m.joint('waist_pitch_joint').id] + [m.joint('right_' + name + '_joint').id for name in
             ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow',
              'wrist_roll', 'wrist_pitch', 'wrist_yaw')])
-        self.hand = np.array([m.joint('right_hand_' + name + '_joint').id for name in
-            ('thumb_0', 'thumb_1', 'thumb_2', 'middle_0', 'middle_1', 'index_0', 'index_1')])
+        self.native_inspire = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, 'right_thumb_1_joint') >= 0
+        if self.native_inspire:
+            from gear_sonic.scripts.prepare_inspire_ftp_sim import HAND_NAMES
+            self.hand = np.array([m.joint('right_'+n+'_joint').id for n in HAND_NAMES])
+        else:
+            self.hand = np.array([m.joint('right_hand_' + name + '_joint').id for name in
+                ('thumb_0', 'thumb_1', 'thumb_2', 'middle_0', 'middle_1', 'index_0', 'index_1')])
         self.arm_q, self.arm_v = m.jnt_qposadr[self.arm], m.jnt_dofadr[self.arm]
         self.hand_q, self.hand_v = m.jnt_qposadr[self.hand], m.jnt_dofadr[self.hand]
         self.site = m.site('right_hand_grasp_center').id
@@ -49,6 +54,13 @@ class AssistedPickup:
         self.scratch = mujoco.MjData(m)
         self.jp, self.jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
         self.closed = np.array([0., -.7, -.7, 1., 1.5, 1., 1.5])
+        if self.native_inspire:
+            # Opposition stays preshaped during release; flexion must hold the
+            # bottle for long waits, not only the first few seconds after lift.
+            self.closed = np.array([1.0, .5, .95, .95, .95, .95])
+        self.opened = np.zeros(len(self.hand))
+        if self.native_inspire:
+            self.opened[0] = 1.0
         self.lower = m.jnt_range[self.arm, 0].copy() + .002
         self.upper = m.jnt_range[self.arm, 1].copy() - .002
         # Keep the right upper arm outside the torso. The redundant 8-DOF IK
@@ -75,6 +87,7 @@ class AssistedPickup:
         self.fraction = 0.
         self.placed = False
         self.place_xy = None
+        self.lost_grasp_since = None
 
     def lower_to_table(self, data, xy=None):
         if not self.active or self.stage != 'success':
@@ -129,7 +142,7 @@ class AssistedPickup:
         self.active = True
         self.arm_target = data.qpos[self.arm_q].copy()
         self.home_arm_q = self.arm_target.copy()
-        self.hand_target = np.zeros(7)
+        self.hand_target = self.opened.copy()
         self.start_pos = data.site_xpos[self.site].copy()
         self.start_rot = data.xmat[self.wrist].reshape(3, 3).copy()
         self.set_stage('detecting', data.time)
@@ -144,7 +157,8 @@ class AssistedPickup:
             a, b = self.model.geom_bodyid[[contact.geom1, contact.geom2]]
             if a == self.bottle or b == self.bottle:
                 name = self.model.body(int(b if a == self.bottle else a)).name
-                if name.startswith('right_hand_'):
+                if name.startswith('right_hand_') or (self.native_inspire and name.startswith(
+                        ('right_thumb', 'right_index', 'right_middle', 'right_ring', 'right_little'))):
                     names.add(name)
         return sorted(names)
 
@@ -244,7 +258,7 @@ class AssistedPickup:
             # once the bottle is inside the grasp region. Closing fully while
             # still advancing makes the index finger sweep the bottle away.
             self.fraction = float(.05 * advance + .95 * np.clip((elapsed - 1.5) / 1.5, 0., 1.))
-            self.hand_target = self.closed * self.fraction
+            self.hand_target = self.opened + (self.closed - self.opened) * self.fraction
             if elapsed > 3.5 and opposed:
                 self.table_arm_q = self.arm_target.copy()
                 self.set_stage('lift', data.time)
@@ -286,8 +300,14 @@ class AssistedPickup:
             else:
                 position = self.release_pos.copy()
                 rotation = self.release_rot.copy()
+                if self.native_inspire:
+                    # Uncurling FTP fingers extend forward. Withdraw the palm
+                    # as they clear the supported bottle instead of sweeping it.
+                    clearance = float(np.clip((elapsed - .5) / 1.5, 0., 1.))
+                    clearance = clearance*clearance*(3.-2.*clearance)
+                    position += np.array([-.05, -.02, 0.]) * clearance
                 self.fraction = float(1. - np.clip(elapsed / 2., 0., 1.)) if self.stage == 'release' else 0.
-                self.hand_target = self.closed * self.fraction
+                self.hand_target = self.opened + (self.closed - self.opened) * self.fraction
                 if self.stage == 'release' and elapsed > 3.:
                     upright = data.xmat[self.bottle].reshape(3, 3)[2, 2] > .95
                     self.placed = bool(self.table_support(data) and upright
@@ -297,7 +317,8 @@ class AssistedPickup:
                     self.set_stage('retreat' if self.placed else 'failed', data.time)
         elif self.stage == 'retreat':
             t = np.clip(elapsed / 2., 0., 1.)
-            position = self.release_pos + np.array([-.09, 0., .025]) * t*t*(3.-2.*t)
+            release_offset = np.array([-.05, -.02, 0.]) if self.native_inspire else np.zeros(3)
+            position = self.release_pos + release_offset + np.array([-.09, 0., .025]) * t*t*(3.-2.*t)
             rotation = self.release_rot.copy()
             self.solve(data, position, rotation)
             if elapsed > 3.:
@@ -325,6 +346,16 @@ class AssistedPickup:
                 lift = float(data.xpos[self.bottle, 2] - self.centre_height)
                 self.min_hold_lift = min(self.min_hold_lift, lift)
                 self.hold_contacts &= opposed
+                if self.stage == 'success':
+                    if lift < .12 or not opposed:
+                        if self.lost_grasp_since is None:
+                            self.lost_grasp_since = float(data.time)
+                        elif data.time - self.lost_grasp_since > .3:
+                            self.success = False
+                            self.error = 'Bottle slipped from grasp; placement cancelled. Reset to retry.'
+                            self.set_stage('failed', data.time)
+                    else:
+                        self.lost_grasp_since = None
                 if self.stage == 'hold' and elapsed > 3.:
                     self.success = bool(self.min_hold_lift > .12 and self.hold_contacts)
                     if not self.success:
@@ -338,11 +369,11 @@ class AssistedPickup:
         indices = [int(np.flatnonzero(body_joint_indices == joint)[0]) for joint in self.arm]
         body[indices] = (80. * (self.arm_target - data.qpos[self.arm_q])
                          - 3. * data.qvel[self.arm_v] + data.qfrc_bias[self.arm_v])
-        hand[7:] = (8. * (self.hand_target - data.qpos[self.hand_q])
+        hand[len(self.hand):] = (8. * (self.hand_target - data.qpos[self.hand_q])
                     - .2 * data.qvel[self.hand_v] + data.qfrc_bias[self.hand_v])
 
     def snapshot(self):
-        return {'stage': self.stage, 'active': self.active, 'success': self.success, 'placed': self.placed,
+        return {'hand_model': 'inspire_ftp' if self.native_inspire else 'dex3', 'stage': self.stage, 'active': self.active, 'success': self.success, 'placed': self.placed,
                 'place_target_xy_m': self.place_xy.tolist() if self.place_xy is not None else None,
                 'target_source': 'YOLO RGB-D surface + known radius and tabletop height',
                 'target_center_world_m': self.target.tolist() if self.target is not None else None,
diff --git a/gear_sonic/utils/mujoco_sim/base_sim.py b/gear_sonic/utils/mujoco_sim/base_sim.py
index c3004ac..531ada8 100644
--- a/gear_sonic/utils/mujoco_sim/base_sim.py
+++ b/gear_sonic/utils/mujoco_sim/base_sim.py
@@ -75,6 +75,7 @@ class DefaultEnv:
         self._preview_capture = 0.
         self._viewer_overlay_worker = None
 
+        self.native_inspire = self.config.get("NATIVE_INSPIRE", False)
         self.init_scene()
         self.assisted_pickup = None
         if self.config.get('ASSISTED_PICKUP', False):
@@ -218,6 +219,11 @@ class DefaultEnv:
                 joint = self.mj_model.joint(f'{side}_shoulder_pitch_joint')
                 self.initial_qpos[int(joint.qposadr[0])] = pitch
             self.initial_qpos[int(self.mj_model.joint('left_elbow_joint').qposadr[0])] = .3
+            if self.native_inspire:
+                for side in ('left', 'right'):
+                    self.initial_qpos[self.mj_model.joint(side+'_shoulder_pitch_joint').qposadr[0]] = .35
+                    self.initial_qpos[self.mj_model.joint(side+'_elbow_joint').qposadr[0]] = -.7
+                    self.initial_qpos[self.mj_model.joint(side+'_thumb_1_joint').qposadr[0]] = 1.0
             self.mj_data.qpos[:] = self.initial_qpos
             mujoco.mj_forward(self.mj_model, self.mj_data)
 
@@ -314,6 +320,10 @@ class DefaultEnv:
             elif "right_hand" in name:
                 self.right_hand_index.append(i)
 
+        if self.native_inspire:
+            from gear_sonic.scripts.prepare_inspire_ftp_sim import HAND_NAMES
+            self.left_hand_index = [self.mj_model.joint('left_'+n+'_joint').id for n in HAND_NAMES]
+            self.right_hand_index = [self.mj_model.joint('right_'+n+'_joint').id for n in HAND_NAMES]
         assert len(self.body_joint_index) == self.robot.NUM_JOINTS
         assert len(self.left_hand_index) == self.robot.NUM_HAND_JOINTS
         assert len(self.right_hand_index) == self.robot.NUM_HAND_JOINTS
@@ -325,6 +335,14 @@ class DefaultEnv:
         self.left_hand_index = np.array(self.left_hand_index)
         self.right_hand_index = np.array(self.right_hand_index)
 
+        # Passive finger joints mean joint IDs are no longer actuator IDs.
+        self.joint_actuator = {int(j): i for i, j in enumerate(self.mj_model.actuator_trnid[:, 0])}
+        self.body_actuator = np.array([self.joint_actuator[int(j)] for j in self.body_joint_index])
+        self.left_hand_actuator = np.array([self.joint_actuator[int(j)] for j in self.left_hand_index])
+        self.right_hand_actuator = np.array([self.joint_actuator[int(j)] for j in self.right_hand_index])
+        if self.native_inspire:
+            self.torques = np.zeros(self.mj_model.nu)
+            self.torque_limit = self.mj_model.actuator_forcerange[:, 1].copy()
         if mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, "red_bottle") >= 0:
             from gear_sonic.utils.mujoco_sim.object_reset import BottlePlacement
             self.bottle_placement = BottlePlacement(self.mj_model, self.mj_data)
@@ -378,12 +396,12 @@ class DefaultEnv:
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
         if (self.config.get("ARM_GRAVITY_COMPENSATION", False)
@@ -470,12 +488,12 @@ class DefaultEnv:
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
@@ -483,12 +501,12 @@ class DefaultEnv:
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
@@ -533,19 +551,19 @@ class DefaultEnv:
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
 
@@ -599,11 +617,11 @@ class DefaultEnv:
             hand_torques = 8. * (self.initial_qpos[qa] - self.mj_data.qpos[qa]) - .2 * self.mj_data.qvel[va] + self.mj_data.qfrc_bias[va]
         if self.assisted_pickup is not None and not self.standby:
             self.assisted_pickup.apply_torques(self.mj_data, body_torques, hand_torques, self.body_joint_index)
-        # -1: actuator array is 0-based while joint indices from the model are 1-based
-        self.torques[self.body_joint_index - 1] = body_torques
+        # Map active joints to motor slots; passive Inspire joints have no slot.
+        self.torques[self.body_actuator - (6 if self.config["FREE_BASE"] else 0)] = body_torques
         if self.num_hand_dof > 0:
-            self.torques[self.left_hand_index - 1] = hand_torques[: self.num_hand_dof]
-            self.torques[self.right_hand_index - 1] = hand_torques[self.num_hand_dof :]
+            self.torques[self.left_hand_actuator - (6 if self.config["FREE_BASE"] else 0)] = hand_torques[: self.num_hand_dof]
+            self.torques[self.right_hand_actuator - (6 if self.config["FREE_BASE"] else 0)] = hand_torques[self.num_hand_dof :]
 
         self.torques = np.clip(self.torques, -self.torque_limit, self.torque_limit)
 
@@ -811,11 +829,13 @@ class DefaultEnv:
                 # Pair proprioception with the image exposure, not with the
                 # later time at which rendering/network delivery completes.
                 state = {
-                    "body_q": self.mj_data.qpos[self.body_joint_index + self.qpos_offset - 1].tolist(),
-                    "left_hand_q": self.mj_data.qpos[self.left_hand_index + self.qpos_offset - 1].tolist(),
-                    "right_hand_q": self.mj_data.qpos[self.right_hand_index + self.qpos_offset - 1].tolist(),
+                    "body_q": self.mj_data.qpos[self.mj_model.jnt_qposadr[self.body_joint_index]].tolist(),
+                    "left_hand_q": self.mj_data.qpos[self.mj_model.jnt_qposadr[self.left_hand_index]].tolist(),
+                    "right_hand_q": self.mj_data.qpos[self.mj_model.jnt_qposadr[self.right_hand_index]].tolist(),
                     "base_quat": self.mj_data.qpos[3:7].tolist(),
                 }
+                if self.native_inspire:
+                    state['hand_state_format'] = 'inspire_ftp_motor_radians'
                 self.image_publish_process.submit(self.mj_data, robot_state=state)
             return {}
         render_caches = {}
diff --git a/gear_sonic/utils/mujoco_sim/configs.py b/gear_sonic/utils/mujoco_sim/configs.py
index 618adaf..29989d3 100644
--- a/gear_sonic/utils/mujoco_sim/configs.py
+++ b/gear_sonic/utils/mujoco_sim/configs.py
@@ -354,6 +354,9 @@ class SimLoopConfig(BaseConfig):
     assisted_pickup: bool = False
     """Correct right-arm pickup with RGB-D bottle target; requires simulation controls and detector."""
 
+    native_inspire: bool = False
+    """Native six-motor Inspire FTP hands, fixed-base assisted simulation only."""
+
     fixed_pickup_base: bool = False
     """Anchor pelvis and hold unused joints during the assisted table task; simulation only."""
 
diff --git a/gear_sonic/utils/mujoco_sim/palm_proximity.py b/gear_sonic/utils/mujoco_sim/palm_proximity.py
index f850194..92718b9 100644
--- a/gear_sonic/utils/mujoco_sim/palm_proximity.py
+++ b/gear_sonic/utils/mujoco_sim/palm_proximity.py
@@ -15,7 +15,8 @@ def cylinder_surface_distance(point, radius, half_height):
 
 class PalmProximity:
     def __init__(self, model):
-        mesh = model.mesh("right_hand_palm_link").id
+        native = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_MESH, "right_base_link") >= 0
+        mesh = model.mesh("right_base_link" if native else "right_hand_palm_link").id
         self.palm = next(i for i in range(model.ngeom)
             if model.geom_type[i] == mujoco.mjtGeom.mjGEOM_MESH
             and model.geom_dataid[i] == mesh and (model.geom_contype[i] or model.geom_conaffinity[i]))
diff --git a/gear_sonic/utils/mujoco_sim/reach_diagnostics.py b/gear_sonic/utils/mujoco_sim/reach_diagnostics.py
index 661c274..aa8a4f0 100644
--- a/gear_sonic/utils/mujoco_sim/reach_diagnostics.py
+++ b/gear_sonic/utils/mujoco_sim/reach_diagnostics.py
@@ -14,10 +14,7 @@ def measure_reach(model, data, joint_targets=None):
     bottle = model.body('red_bottle').id
     wrist = model.body('right_wrist_yaw_link').id
     grasp_site = model.site('right_hand_grasp_center').id
-    palm_mesh = model.mesh('right_hand_palm_link').id
-    palm = next(i for i in range(model.ngeom) if model.geom_type[i] == mujoco.mjtGeom.mjGEOM_MESH
-                and model.geom_dataid[i] == palm_mesh
-                and (model.geom_contype[i] or model.geom_conaffinity[i]))
+    palm = PalmProximity(model).palm
     def pose(d):
         return {'wrist_world_m': d.xpos[wrist].tolist(),
                 'grasp_center_world_m': d.site_xpos[grasp_site].tolist(),
@@ -35,9 +32,12 @@ def measure_reach(model, data, joint_targets=None):
     result['bottle_lift_from_initial_m'] = float(actual.xpos[bottle, 2] - model.qpos0[bottle_adr + 2])
     bottle_geoms = [i for i in range(model.ngeom) if model.geom_bodyid[i] == bottle
                     and (model.geom_contype[i] or model.geom_conaffinity[i])]
+    hand_bodies = {wrist}
+    for body in range(wrist + 1, model.nbody):
+        if int(model.body_parentid[body]) in hand_bodies:
+            hand_bodies.add(body)
     hand_geoms = [i for i in range(model.ngeom)
-                  if (model.body(int(model.geom_bodyid[i])).name.startswith('right_hand_')
-                      or i == palm)
+                  if int(model.geom_bodyid[i]) in hand_bodies
                   and (model.geom_contype[i] or model.geom_conaffinity[i])]
     distances = [mujoco.mj_geomDistance(model, actual, a, b, 2.0, None)
                  for a in bottle_geoms for b in hand_geoms]
diff --git a/gear_sonic/scripts/prepare_inspire_ftp_sim.py b/gear_sonic/scripts/prepare_inspire_ftp_sim.py
new file mode 100644
index 0000000..c40893c
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
diff --git a/gear_sonic/scripts/run_inspire_ftp_sim.py b/gear_sonic/scripts/run_inspire_ftp_sim.py
new file mode 100644
index 0000000..c8b678b
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
diff --git a/gear_sonic/tests/test_inspire_ftp_model.py b/gear_sonic/tests/test_inspire_ftp_model.py
new file mode 100644
index 0000000..58ad78a
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
diff --git a/gear_sonic/tests/test_native_inspire_pickup.py b/gear_sonic/tests/test_native_inspire_pickup.py
new file mode 100644
index 0000000..c3288c6
--- /dev/null
+++ b/gear_sonic/tests/test_native_inspire_pickup.py
@@ -0,0 +1,118 @@
+"""Contact-based Inspire pickup/place/repeat regression with controlled perception.
+
+No policy server/detector required. Synthetic RGB-D targets isolate physics;
+these tests must not be presented as learned-policy or live-perception success.
+"""
+from pathlib import Path
+from types import SimpleNamespace
+import unittest
+
+import mujoco
+import numpy as np
+
+from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
+from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
+from gear_sonic.utils.mujoco_sim.inspire_hand import dex3_observation_from_inspire
+
+ROOT = Path(__file__).resolve().parents[2]
+SCENE = ROOT / 'models/g1_inspire_ftp/g1_inspire_ftp_pickup.xml'
+
+
+class NativeObservationTest(unittest.TestCase):
+    def test_projection_is_explicit_finite_and_does_not_modify_input(self):
+        measured = np.array([1., .2, .4, .5, .6, .7])
+        before = measured.copy()
+        for side in ('left', 'right'):
+            projected = dex3_observation_from_inspire(measured, side)
+            self.assertEqual(projected.shape, (7,))
+            self.assertTrue(np.isfinite(projected).all())
+        np.testing.assert_array_equal(measured, before)
+        with self.assertRaises(ValueError):
+            dex3_observation_from_inspire([0.] * 7, 'right')
+
+
+@unittest.skipUnless(SCENE.exists(), 'Build the native Inspire pickup model first')
+class NativeInspirePickupTest(unittest.TestCase):
+    def test_pickup_place_home_repeat_and_reset(self):
+        for xy, destination in (([.43, -.11], [.45, -.05]),
+                                ([.4, -.15], [.42, -.12]),
+                                ([.46, -.08], [.43, -.11]),
+                                ([.43, -.05], [.45, -.05])):
+            with self.subTest(xy=xy, destination=destination):
+                config = SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
+                config.update(GROUND_START=True, ASSISTED_PICKUP=True, FIXED_PICKUP_BASE=True,
+                              NATIVE_INSPIRE=True, NUM_HAND_JOINTS=6, NUM_HAND_MOTORS=0,
+                              ROBOT_SCENE=str(SCENE))
+                env = DefaultEnv(config)
+                env.unitree_bridge = SimpleNamespace(PublishLowState=lambda _: None,
+                    joystick=None, low_cmd=None, low_cmd_received=False)
+                model, data, pickup = env.mj_model, env.mj_data, env.assisted_pickup
+                self.assertEqual(model.nu, 41)
+                self.assertEqual(len(pickup.hand), 6)
+                self.assertEqual(len(set(env.joint_actuator.values())), 41)
+                self.assertNotIn(pickup.bottle, model.eq_obj1id)
+                self.assertNotIn(pickup.bottle, model.eq_obj2id)
+                env.bottle_placement.reset(model, data, xy)
+                for _ in range(100):
+                    env.sim_step()
+                robot_q = np.r_[model.jnt_qposadr[env.body_joint_index],
+                                model.jnt_qposadr[env.left_hand_index], model.jnt_qposadr[env.right_hand_index]]
+                np.testing.assert_array_equal(data.qpos[robot_q], env.initial_qpos[robot_q])
+                env.begin_control_transition()
+
+                def grasp(centre_xy):
+                    pickup.start(data)
+                    for step in range(6000):
+                        pickup.update(data, {'status': 'detected',
+                            'world_point_m': [centre_xy[0]-.025, centre_xy[1], .85],
+                            'camera_position_world_m': [0., centre_xy[1], 1.2],
+                            'capture_monotonic': step // 20})
+                        env.sim_step()
+                        if pickup.stage in ('success', 'failed'):
+                            break
+                    self.assertTrue(pickup.success, pickup.snapshot())
+                    self.assertGreater(pickup.min_hold_lift, .12)
+                    np.testing.assert_array_equal(data.xfrc_applied[pickup.bottle], 0.)
+
+                grasp(xy)
+                # Users may leave a lifted bottle waiting before pressing Lower.
+                for _ in range(12000):  # 60 simulated seconds at 200 Hz
+                    pickup.update(data, {})
+                    env.sim_step()
+                    if pickup.stage == 'failed':
+                        break
+                self.assertEqual(pickup.stage, 'success', pickup.snapshot())
+                self.assertGreater(data.xpos[pickup.bottle, 2] - pickup.centre_height, .12)
+                self.assertTrue(pickup.lower_to_table(data, destination))
+                for _ in range(9000):
+                    pickup.update(data, {})
+                    env.sim_step()
+                    if pickup.stage in ('complete', 'failed'):
+                        break
+                self.assertEqual(pickup.stage, 'complete', pickup.snapshot())
+                self.assertTrue(pickup.placed)
+                self.assertTrue(pickup.table_support(data))
+                self.assertLess(np.linalg.norm(data.xpos[pickup.bottle, :2]-destination), .025)
+                self.assertGreater(data.xmat[pickup.bottle].reshape(3, 3)[2, 2], .95)
+                np.testing.assert_allclose(data.qpos[pickup.arm_q], pickup.home_arm_q, atol=.05)
+                # A fresh detector would observe the settled bottle, not the requested XY.
+                grasp(data.xpos[pickup.bottle, :2].copy())
+                self.assertFalse(any(w.number for w in data.warning))
+                # Inject loss of the held object: Lower must no longer be enabled.
+                env.bottle_placement.reset(model, data, xy)
+                for _ in range(100):
+                    pickup.update(data, {})
+                    env.sim_step()
+                self.assertEqual(pickup.stage, 'failed')
+                self.assertFalse(pickup.success)
+                self.assertFalse(pickup.lower_to_table(data, destination))
+                env.reset()
+                self.assertTrue(env.standby)
+                self.assertFalse(pickup.active)
+                self.assertEqual(pickup.stage, 'idle')
+                np.testing.assert_array_equal(data.qvel, 0.)
+                np.testing.assert_allclose(env.coordinate_snapshot()['bottle'], [*xy, .801])
+
+
+if __name__ == '__main__':
+    unittest.main()
diff --git a/gear_sonic/utils/mujoco_sim/inspire_hand.py b/gear_sonic/utils/mujoco_sim/inspire_hand.py
new file mode 100644
index 0000000..7afb450
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
```

<a id="legacy-wsl-snapshot"></a>

## Bản chụp hướng dẫn WSL/code trước khi chuyển Inspire native

Phần lưu trữ để đối chiếu và lấy bản vá ban đầu. Các mô tả “chỉ Dex3” ở đây
không phải trạng thái native mới nhất; xem phần đầu tài liệu để chạy hiện tại.

# Hướng dẫn WSL: Unitree G1 gắp, đặt chai và lặp lại

Bản chụp mã nguồn: **11/10/2026**. Tài liệu có cả hướng dẫn và toàn bộ bản vá
các file sửa/thêm trong workspace, không cần gửi từng file code riêng.

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

## 3. Clone đúng phiên bản

```bash
cd ~/projects
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/NVlabs/GR00T-WholeBodyControl.git
cd GR00T-WholeBodyControl
git checkout b042411fae38ee4d1af9aac82a37a1f8d14d6dd0
git lfs pull --exclude='motionbricks/out/**'
cd ..
git clone https://github.com/NVIDIA/Isaac-GR00T.git
cd Isaac-GR00T
git checkout 51d4c89f72fda44cbf77285c6a8114b52676b8a1
cd ../GR00T-WholeBodyControl
```

Hai repository phải đặt cạnh nhau vì launcher server tham chiếu `../Isaac-GR00T`.
Không checkout `main` mới nhất rồi áp patch này: context/phụ thuộc có thể khác.

## 4. Áp dụng code đính kèm trong chính file Markdown này

Lưu tài liệu này thành `~/WSL_BLUE_BOTTLE_COMPLETE_GUIDE.md`. Chạy từ repo WBC:

```bash
python3 - <<'PYEXTRACT'
from pathlib import Path
import hashlib
text = (Path.home() / 'WSL_BLUE_BOTTLE_COMPLETE_GUIDE.md').read_text()
for name in ('wbc', 'gr00t'):
    prefix = '<!-- PATCH-' + name.upper() + '-BEGIN -->\n```diff\n'
    payload = text.split(prefix, 1)[1].split('```\n<!-- PATCH-' + name.upper() + '-END -->', 1)[0]
    expected = text.split('SHA256-' + name.upper() + ': `', 1)[1].split('`', 1)[0]
    assert hashlib.sha256(payload.encode()).hexdigest() == expected, 'Patch changed during sharing'
    Path('/tmp/' + name + '-simulation.patch').write_text(payload)
PYEXTRACT
git apply --check /tmp/wbc-simulation.patch
git apply /tmp/wbc-simulation.patch
git -C ../Isaac-GR00T apply --check /tmp/gr00t-simulation.patch
git -C ../Isaac-GR00T apply /tmp/gr00t-simulation.patch
```

Chỉ áp một lần trên clone sạch đúng commit. Nếu `--check` thất bại, dừng và
kiểm tra phiên bản; không dùng force/reset để ghi đè code người khác.
Patch chứa cả thay đổi đã tồn tại trong workspace, không quy tất cả cho một
lượt sửa. Dòng `-` là code bỏ, `+` là code thêm; file mới chứa đủ nội dung.
Không có trọng số model, cache, venv, log, TensorRT engine hay token trong patch.

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
cd ~/projects/GR00T-WholeBodyControl/gear_sonic_deploy
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
cd ../GR00T-WholeBodyControl
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

Từ WBC, tải ONNX/planner SONIC, không tải training dataset:

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

Terminal 1 (thư mục WBC):

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

## 11. Bản đồ thay đổi

Bảng dưới kê chính xác file đổi/thêm so với commit WBC đã pin. Phụ lục là
code thực tế, đủ cả dòng bị bỏ và dòng thêm. Không có file tracked bị xóa
nguyên file ở snapshot này (nếu bảng ghi D thì theo bảng). Các file lịch sử
v2/checkpoint và demo vẫn được giữ để tra cứu; hướng dẫn chạy hiện tại là mục 8.

| Loại | File | SHA256 nội dung hiện tại |
|---|---|---|
| Sửa | `.gitignore` | `36806bbe9944a87410a83d6df32d62b5ef9422d2e6831d90c0f250f278c4eb9e` |
| Sửa | `gear_sonic/camera/composed_camera.py` | `98ec6e1c17dcaf6af4ccaf211fd21145b8c278d7afa0a3870015ac5ba5b5b14b` |
| Sửa | `gear_sonic/data/robot_model/model_data/g1/g1_29dof_with_hand.xml` | `715a95b2245a84e00dc865399df3c85b9036ea8662bcacf8882362c0ad4a2e44` |
| Sửa | `gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml` | `ff153fc3d86594c875b53ecb2293683e9fbe786dd8d023cdb409763ac2084c9f` |
| Sửa | `gear_sonic/pyproject.toml` | `71a2347ff0d35ddf97775c8758e75036670e6794cf30443a4b983cf77853a6f1` |
| Sửa | `gear_sonic/scripts/launch_inference.py` | `22b3717f06e7ef80276144b627f7eab38e4cde13889774a08821724d4c66b280` |
| Sửa | `gear_sonic/scripts/run_sim_loop.py` | `6804773402dacd8609837cd380b87032cec56b410ed70f74fc85893a0f6930b1` |
| Sửa | `gear_sonic/scripts/run_vla_inference.py` | `f65926db99360a1880ba2888da55c62f022f16600e7f32fafa592a4daf9b1117` |
| Sửa | `gear_sonic/utils/inference/vla_utils.py` | `610dafa83279e33ff305d41180d6b821ea92c1321a3487fe109a6188042232de` |
| Sửa | `gear_sonic/utils/mujoco_sim/base_sim.py` | `787636ee596f962b76a3fc7b8c66d21d3a606fe540ec6e707a70b3612e8f221e` |
| Sửa | `gear_sonic/utils/mujoco_sim/configs.py` | `c9d1d9bc9e7f95374bd21c50fe1f7237958916f4e67c7b8a5f9304c749687326` |
| Sửa | `gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/input_interface/zmq_manager.hpp` | `0f50712eed4f816d6e919794d1aae776cc0192ee51c618144c81b5627bca08d6` |
| Sửa | `install_scripts/install_inference.sh` | `23c409c60cf695d878fb21234705ccd05e622986c05d1ff989cdce2a4f5d2ab4` |
| Thêm | `docs/source/tutorials/blue_bottle_pickup.md` | `c74ef65cd8818b5d9cc37c3bac34e26023e19f00ac9bb54a0c4d2b4d3ec2b3f4` |
| Thêm | `docs/source/tutorials/cloudwalk_inspire_checkpoint.md` | `24211b8cf421dd3834eb383e84cd37564229ff67195551c4d7dc4d1d10837740` |
| Thêm | `docs/source/tutorials/simulation_controls.md` | `f1d7929a321ff87e74b05b15f1cfcd96d8c15d472268797f51a2d97c7fc58bd3` |
| Thêm | `gear_sonic/scripts/check_cloudwalk_checkpoint.py` | `410e8695d1b00204f4c767b978e4ec46ad690248f4ab6b5d6f1453ed56c48415` |
| Thêm | `gear_sonic/scripts/convert_inspire_ftp_hand.py` | `3ca445e5c25d49e678d08ac549b022c028dfe553def53b23c295d58eecbfe1d8` |
| Thêm | `gear_sonic/scripts/run_blue_bottle_pickup.py` | `876337f9bea2cf213abbf004f94f22a58312707e60a02ad38bc0d92fded10d6c` |
| Thêm | `gear_sonic/scripts/run_bottle_detector.py` | `65b7bd9fd2b7ac1ebd00cbd30766de2da0c8252eaea62efef5a5728dc8481665` |
| Thêm | `gear_sonic/scripts/run_cloudwalk_policy_server.sh` | `7aa73bde1c97e858ba30a2e3d1a6329053e484934e65d818acd045a67b93b9d3` |
| Thêm | `gear_sonic/scripts/summarize_pickup_trial.py` | `4d587a55394193364bb26efc7d0b4ed614d698492698af2182e3cb9c2009b04f` |
| Thêm | `gear_sonic/tests/test_action_start.py` | `0f1b12711c45c3c051835b580f7dc922fbb7bd675587c42bfccd8b7e67eae0f0` |
| Thêm | `gear_sonic/tests/test_arm_tracking.py` | `233650b160aafc12a2085cba56c6b255b7d0890e65956388221c5d3e4c101b48` |
| Thêm | `gear_sonic/tests/test_assisted_pickup.py` | `e355b840b09dbf4f04c4eb387b525d72043084eb710a99b91aaf6bf6ce430d56` |
| Thêm | `gear_sonic/tests/test_async_camera.py` | `37cfa28a1ed99804e7ac75e1d7ea86c6837e6c8c5bbbe3eb30c49654d8bf8ed1` |
| Thêm | `gear_sonic/tests/test_bottle_detection.py` | `0b8d51a94323d29282057ba71769deb39e4ee1c31061d6cb4d7673ab8724d02a` |
| Thêm | `gear_sonic/tests/test_diagnostic_writer.py` | `5dc78d10cc97dd5e23f0f10104860a15c3ecbade75e783dd4ee242d8aecb8388` |
| Thêm | `gear_sonic/tests/test_inspire_adapter.py` | `024b020d8369ff972e7be7ece3f1d68ca31daaad37e9075aa02a5424fb0bb13f` |
| Thêm | `gear_sonic/tests/test_observation_freshness.py` | `1389ac3dddd9ac8b47fc54bbfffb7caf15085d1dbc6f2baa51275dd1978c5330` |
| Thêm | `gear_sonic/tests/test_palm_grasp.py` | `003af302c2387922d6f1bb7afc7ac1153130ded3ec9049e152e6b500645c3a17` |
| Thêm | `gear_sonic/tests/test_sim_grasp_defaults.py` | `305aa5459610a832c86745a4d813ef7dbb7010a5fd14d66a3ae1fa4543a2a492` |
| Thêm | `gear_sonic/tests/test_simulation_controls.py` | `3094a932a275cb112f5f786ee15ca93ea6c5d1034a943a8ac153d5a75a76eb0c` |
| Thêm | `gear_sonic/tests/test_viewer_overlay.py` | `5534c2a618814d1e56fa4e77491fe8593cf1622db616f8217d7250b3717ccf04` |
| Thêm | `gear_sonic/utils/diagnostic_writer.py` | `623da33a40ea8121a3c5a96eac0b57fba8b85ccb5fb8c70a2be05d593b292737` |
| Thêm | `gear_sonic/utils/inference/inspire_adapter.py` | `364989fab6c2bfec1c248083c1c19a06b5a63701b539709751447d9a52a4ad1d` |
| Thêm | `gear_sonic/utils/inference/proximity_hand.py` | `55c53832a313764c5cdb04c866205eb308ff8d5005707f38fbcafb09755e5f09` |
| Thêm | `gear_sonic/utils/inference/simulation_controls.py` | `b55b20071d38e53157e195f2a2e9836bca7f0441bd444b339f956936aab3cb67` |
| Thêm | `gear_sonic/utils/mujoco_sim/assisted_pickup.py` | `2524b138af4570e5d23ef3c071b08e46e4da5e152efbba766118ac0d077462ea` |
| Thêm | `gear_sonic/utils/mujoco_sim/async_camera.py` | `80513c9c50b2500e92758998fdb03069333464aaecde4455f193c0463ba50eb1` |
| Thêm | `gear_sonic/utils/mujoco_sim/control_panel.py` | `4b9f77f607fcc52808ff2c43592fe1a25525a1526733145e158d2d9c803bef8c` |
| Thêm | `gear_sonic/utils/mujoco_sim/hand_alignment.py` | `94d829d7085d9b86faeb95520e8a62467968b844228eccf8292c5e05cffa6254` |
| Thêm | `gear_sonic/utils/mujoco_sim/interactive_controls.py` | `155c445d0e4a6414e99a1c25ce2bde6a6bc1b7ce14772be2198bf4eb9b68c217` |
| Thêm | `gear_sonic/utils/mujoco_sim/object_reset.py` | `a5f1f5675ba206546becc2e591ceaa10c25903a10922907f3817c3b41b958d3b` |
| Thêm | `gear_sonic/utils/mujoco_sim/palm_proximity.py` | `accf3600f6652af6dd5e3962c2c8f255faa5b0e401b189dfb4e4bc34ffe92441` |
| Thêm | `gear_sonic/utils/mujoco_sim/process_lifecycle.py` | `afd49cd77af8861e4114fae17d8fd7a23255c449f39ba825a560af28d0f82a58` |
| Thêm | `gear_sonic/utils/mujoco_sim/reach_diagnostics.py` | `d4d0d4bf4205ae345618606eecd8bc1141bdd1d6b325200c09aa028bfb4e94a2` |
| Thêm | `gear_sonic/utils/mujoco_sim/viewer_overlay.py` | `16787250da1f821dae273d4a248e6ac977d8ef3cc29ad5ba3ecc571104373060` |
| Thêm | `gear_sonic/utils/perception/bottle_detector.py` | `97a056f66b0df9d0bc7f4ef0ad5af7bb4b7c7c2e1ef4238851890f4aca96baf7` |
| Thêm | `install_scripts/install_bottle_detector.sh` | `9fa3c88a82ace39107e47075314aa29843279bdba8998bc37f4fc64fbf6f6f78` |

### Nhóm chức năng

- `assisted_pickup.py`: RGB-D/IK, nắm/nâng/đặt, dò tiếp xúc, thu tay.
- `interactive_controls.py`, `control_panel.py`: Start/Reset, X/Y đích, gắp lại.
- `base_sim.py`, `configs.py`, `run_sim_loop.py`: tư thế chờ, fixed pelvis, mô-men và physics.
- `launch_inference.py`, `run_vla_inference.py`, `vla_utils.py`, `zmq_manager.hpp`: luồng server/SONIC, đồng bộ hành động, token đứng.
- XML robot/scene: bàn, chai tự do, marker vùng nắm, cấu hình robot.
- `async_camera.py`, `composed_camera.py`, `viewer_overlay.py`: camera tách physics, ảnh trực tiếp, khung YOLO.
- `bottle_detector.py`, `run_bottle_detector.py`: YOLO + depth, tọa độ bề mặt, 2 Hz.
- `inspire_adapter.py`, `proximity_hand.py`, `palm_proximity.py`: adapter/ngưỡng nắm; assisted mode không dùng gate cũ để điều khiển quỹ đạo.
- `diagnostic_writer.py`, `reach_diagnostics.py`, `process_lifecycle.py`: log, chẩn đoán, vòng đời tiến trình.
- Tests: kiểm thử vật lý và điều khiển; setup scripts/pyproject: môi trường.
- Repository Isaac-GR00T: `gr00t/policy/gr00t_policy.py` nạp thẳng BF16 với low_cpu_mem_usage.

## 12. Phụ lục code — bản vá WBC đầy đủ

SHA256-WBC: `1be84e7534656aee86d2ebf6d91a61e858c9afeb87b9469f49fe54bc9d4c2034`

<!-- PATCH-WBC-BEGIN -->
```diff
diff --git a/.gitignore b/.gitignore
index 5efb48e..8cf10d2 100644
--- a/.gitignore
+++ b/.gitignore
@@ -219,3 +219,7 @@ models/
 # Downloaded from HuggingFace (hf download)
 sample_data/
 sonic_release/
+
+# Official CloudWalk checkpoints downloaded for local server evaluation
+checkpoints/cloudwalk_g1_bottle_v2/
+checkpoints/cloudwalk_g1_bottle_v10/
diff --git a/gear_sonic/camera/composed_camera.py b/gear_sonic/camera/composed_camera.py
index d5f5607..8b8edb7 100644
--- a/gear_sonic/camera/composed_camera.py
+++ b/gear_sonic/camera/composed_camera.py
@@ -529,6 +529,11 @@ class ComposedCameraClientSensor(Sensor, SensorClient):
         if message is not None:
             self.idx += 1
             self._latest_message = ImageMessageSchema.deserialize(message).asdict()
+            # Simulated cameras can carry proprioception from the same physics
+            # snapshot. Real camera messages retain the existing DDS state path.
+            for key in ("robot_state", "simulation_time", "capture_monotonic"):
+                if key in message:
+                    self._latest_message[key] = message[key]
             self._last_new_message_time = current_time
 
             if self.idx % 10 == 0:
diff --git a/gear_sonic/data/robot_model/model_data/g1/g1_29dof_with_hand.xml b/gear_sonic/data/robot_model/model_data/g1/g1_29dof_with_hand.xml
index 76110b5..ccfdbc9 100644
--- a/gear_sonic/data/robot_model/model_data/g1/g1_29dof_with_hand.xml
+++ b/gear_sonic/data/robot_model/model_data/g1/g1_29dof_with_hand.xml
@@ -452,6 +452,10 @@
                           rgba="0.7 0.7 0.7 1" mesh="right_wrist_pitch_link" />
                         <geom type="mesh" rgba="0.7 0.7 0.7 1" mesh="right_wrist_pitch_link" />
                         <body name="right_wrist_yaw_link" pos="0.046 0 0">
+                          <!-- Dex3 grasp-region reference in the wrist frame.
+                               No collision/mass; group 5 is hidden from policy cameras. -->
+                          <site name="right_hand_grasp_center" pos="0.12 0.05 0"
+                            type="sphere" size="0.007" rgba="0.2 1 0.2 0.8" group="5" />
                           <inertial pos="0.0885506 -0.00212216 0.000573742"
                             quat="0.507224 0.511377 0.494292 0.486717" mass="0.457415"
                             diaginertia="0.0010598 0.000895373 0.0003238" />
@@ -748,4 +752,4 @@
     <framepos name="frame_pos" objtype="site" objname="imu" />
     <framelinvel name="frame_vel" objtype="site" objname="imu" />
   </sensor>
-</mujoco>
\ No newline at end of file
+</mujoco>
diff --git a/gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml b/gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml
index d66b23d..c66484e 100644
--- a/gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml
+++ b/gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml
@@ -15,13 +15,54 @@
     <texture type="2d" name="groundplane" builtin="checker" mark="edge" rgb1="0.2 0.3 0.4" rgb2="0.1 0.2 0.3"
       markrgb="0.8 0.8 0.8" width="300" height="300"/>
     <material name="groundplane" texture="groundplane" texuniform="true" texrepeat="5 5" reflectance="0.2"/>
+    <texture name="pickup_table_texture" type="2d" builtin="checker"
+             rgb1="0.55 0.24 0.07" rgb2="0.75 0.36 0.10" width="256" height="256"/>
+    <material name="pickup_table_material" texture="pickup_table_texture"
+              texuniform="true" texrepeat="3 3"/>
   </asset>
 
   <worldbody>
     <light pos="0 0 1.5" dir="0 0 -1" directional="true"/>
     <geom name="floor" size="0 0 0.05" type="plane" material="groundplane"/>
-    <!-- Site -->
-    <site name="com_marker" pos="0.1 0 0" size="0.05" rgba="1 0 0 1" type="sphere"/>
+    <!-- Keep the diagnostic marker hidden so it cannot be mistaken for an object. -->
+    <site name="com_marker" pos="0.1 0 0" size="0.05" rgba="1 0 0 0" type="sphere"/>
+
+    <!-- Layout estimated from checkpoint example videos; original scene unavailable.
+         +X is forward and -Y is the robot's right side. Tabletop is at 0.70 m. -->
+    <body name="pickup_table" pos="0.50 0 0">
+      <geom name="pickup_table_top" type="box" pos="0 0 0.675"
+            size="0.25 0.45 0.025" material="pickup_table_material"/>
+      <geom name="pickup_table_leg_1" type="box" pos="-0.21 -0.41 0.325"
+            size="0.025 0.025 0.325" rgba="0.55 0.24 0.07 1"/>
+      <geom name="pickup_table_leg_2" type="box" pos="-0.21 0.41 0.325"
+            size="0.025 0.025 0.325" rgba="0.55 0.24 0.07 1"/>
+      <geom name="pickup_table_leg_3" type="box" pos="0.21 -0.41 0.325"
+            size="0.025 0.025 0.325" rgba="0.55 0.24 0.07 1"/>
+      <geom name="pickup_table_leg_4" type="box" pos="0.21 0.41 0.325"
+            size="0.025 0.025 0.325" rgba="0.55 0.24 0.07 1"/>
+    </body>
+
+    <!-- Append object joints after the robot to preserve SDK joint indexing.
+         A free body allows a physical grasp; there is no attachment to the hand. -->
+    <!-- Move the bottle 5 cm closer to the robot along the forward axis. -->
+    <body name="red_bottle" pos="0.43 -0.11 0.801">
+      <freejoint name="red_bottle_free_joint"/>
+      <geom name="red_bottle_body" type="cylinder" size="0.025 0.10"
+            mass="0.065" rgba="0.05 0.48 0.8 1"
+            condim="4" friction="1.2 0.01 0.001"/>
+      <!-- Blue/cyan bottle matches the sample; legacy names retained. -->
+      <geom name="bottle_label" type="cylinder" pos="0 0 0.025"
+            size="0.0253 0.035" mass="0" contype="0" conaffinity="0"
+            rgba="0.5 0.85 0.9 1"/>
+      <geom name="bottle_shoulder" type="ellipsoid" pos="0 0 0.10"
+            size="0.025 0.025 0.023" mass="0.005" rgba="0.4 0.8 0.85 1"
+            condim="4" friction="1.2 0.01 0.001"/>
+      <geom name="red_bottle_neck" type="cylinder" pos="0 0 0.125"
+            size="0.012 0.018" mass="0.005" rgba="0.65 0.9 0.9 1"
+            condim="4" friction="1.2 0.01 0.001"/>
+      <geom name="red_bottle_cap" type="cylinder" pos="0 0 0.151"
+            size="0.014 0.008" mass="0.005" rgba="0.02 0.02 0.02 1"/>
+    </body>
   </worldbody>
 
   <default>
diff --git a/gear_sonic/pyproject.toml b/gear_sonic/pyproject.toml
index b7d645f..6b47360 100644
--- a/gear_sonic/pyproject.toml
+++ b/gear_sonic/pyproject.toml
@@ -78,7 +78,7 @@ camera = [
     "depthai",
     "requests",
 ]
-# Inference: VLA inference client for running Isaac-GR00T policies
+# Inference: VLA inference client for running gr00t policies
 # Usage: pip install -e "gear_sonic[inference]"
 inference = [
     "pyzmq",
@@ -88,7 +88,7 @@ inference = [
     "tyro",
     "opencv-python",
     "scipy",
-    "Isaac-GR00T @ git+https://github.com/NVIDIA/Isaac-GR00T.git",
+    "gr00t @ git+https://github.com/NVIDIA/Isaac-GR00T.git",
 ]
 # Training: full RL training stack (Isaac Lab must be installed separately)
 # Usage: pip install -e "gear_sonic[training]"
diff --git a/gear_sonic/scripts/launch_inference.py b/gear_sonic/scripts/launch_inference.py
index ef036ef..00504a1 100644
--- a/gear_sonic/scripts/launch_inference.py
+++ b/gear_sonic/scripts/launch_inference.py
@@ -35,6 +35,7 @@ Usage (from repo root — no venv activation needed):
 from dataclasses import dataclass
 from pathlib import Path
 import os
+import re
 import shutil
 import signal
 import socket
@@ -91,6 +92,36 @@ class InferenceLaunchConfig:
     sim: bool = False
     """Run against MuJoCo sim instead of real robot."""
 
+    sim_grasp_distance: float | None = None
+    """Grasp-region centre Y surface gap (m). Default: 0.02 in simulation with detector, otherwise 0. Set 0 for checkpoint-only hand control."""
+
+    sim_grasp_x_tolerance: float = .005
+    """World-X matching tolerance for grasp-region centre vs bottle centre (metres)."""
+
+    sim_arm_gravity_compensation: bool = True
+    """Add arm bias feedforward in MuJoCo to reduce sag relative to SONIC joint targets; simulation only."""
+
+    sim_assisted_pickup: bool = False
+    """Use RGB-D target correction for right-arm approach, physical grasp and lift; SONIC controls the body. Simulation only."""
+
+    sim_fixed_base: bool = False
+    """Anchor the simulated pelvis and hold unused joints for repeatable table pickup. Requires --sim-assisted-pickup."""
+
+    sim_bottle_xy: tuple[float, float] | None = None
+    """Initial bottle X/Y in metres; can also be changed in the simulation panel."""
+
+    bottle_detection: bool = True
+    """Show YOLO detections; optional proximity mode also requires bottle recognition."""
+
+    detector_model: str = "models/detectors/yolo11n.pt"
+    """Local YOLO bottle detector checkpoint; its XYZ is never fed into GR00T."""
+
+    reach_diagnostic_path: str = ""
+    """Optional simulator reach diagnostics JSON path (requires --sim)."""
+
+    action_diagnostic_path: str = ""
+    """Optional JSONL recording of policy chunks and published actions."""
+
     # C++ deploy options
     deploy_input_type: str = "zmq_manager"
     """Input type for the C++ deploy."""
@@ -138,6 +169,9 @@ class InferenceLaunchConfig:
     action_horizon: int = 40
     """Action horizon of the VLA policy."""
 
+    inspire_ftp_hands: bool = False
+    """Experimental CloudWalk Inspire FTP hand adapter; requires --sim."""
+
     # Camera
     camera_host: str = "localhost"
     """Camera server host."""
@@ -162,9 +196,33 @@ class InferenceLaunchConfig:
 SESSION_NAME = "sonic_inference"
 
 
+def _resolve_sim_grasp_config(config: InferenceLaunchConfig):
+    # Resolve after CLI parsing so --sim is known; hardware never inherits
+    # a simulation-only hand override from the launcher's defaults.
+    if config.sim_grasp_distance is None:
+        config.sim_grasp_distance = .02 if config.sim and config.bottle_detection else 0.
+    if config.sim_assisted_pickup:
+        # The assisted controller owns right-hand closure throughout its motion.
+        config.sim_grasp_distance = 0.
+
+
 def _check_prerequisites(config: InferenceLaunchConfig):
     """Verify that required tools and venvs exist."""
     errors = []
+    if config.sim_bottle_xy is not None and not config.sim:
+        errors.append("--sim-bottle-xy requires --sim")
+    if config.sim_fixed_base and (not config.sim or not config.sim_assisted_pickup):
+        errors.append("--sim-fixed-base requires --sim --sim-assisted-pickup")
+    if config.sim_assisted_pickup and (not config.sim or not config.bottle_detection):
+        errors.append("--sim-assisted-pickup requires --sim and the bottle detector")
+    if not 0 <= config.sim_grasp_distance <= .1:
+        errors.append("--sim-grasp-distance must be between 0 and 0.1 metres")
+    if not 0 <= config.sim_grasp_x_tolerance <= .02:
+        errors.append("--sim-grasp-x-tolerance must be between 0 and 0.02 metres")
+    if config.sim_grasp_distance and (not config.sim or not config.bottle_detection):
+        errors.append("--sim-grasp-distance requires --sim and the bottle detector")
+    if config.inspire_ftp_hands and not config.sim:
+        errors.append("--inspire-ftp-hands requires --sim (experimental Dex3 adapter)")
 
     if not shutil.which("tmux"):
         errors.append("tmux is not installed. Install with: sudo apt install tmux")
@@ -195,6 +253,22 @@ def _check_prerequisites(config: InferenceLaunchConfig):
             ".venv_sim not found. Set up the simulation venv first."
         )
 
+    if config.sim and config.bottle_detection:
+        detector_path = Path(config.detector_model).expanduser()
+        if not detector_path.is_absolute():
+            detector_path = repo_root / detector_path
+        if not detector_path.is_file():
+            errors.append("Bottle detector missing. Run: bash install_scripts/install_bottle_detector.sh "
+                          "(or disable it with --no-bottle-detection)")
+        python = repo_root / ".venv_inference" / "bin" / "python"
+        if python.is_file():
+            check = subprocess.run([str(python), "-c",
+                "import importlib.util,sys;sys.exit(importlib.util.find_spec('ultralytics') is None)"],
+                capture_output=True)
+            if check.returncode:
+                errors.append("Ultralytics missing in .venv_inference. "
+                              "Run: bash install_scripts/install_bottle_detector.sh")
+
     if errors:
         print("ERROR: Prerequisites not met:\n")
         for e in errors:
@@ -211,10 +285,18 @@ def _kill_existing_session():
 
 
 def _create_tmux_session():
-    subprocess.run(
-        ["tmux", "new-session", "-d", "-s", SESSION_NAME],
-        check=True,
-    )
+    # Killing the last session asynchronously shuts down the tmux server.
+    # Allow that server to exit before retrying creation on its socket.
+    for attempt in range(5):
+        result = subprocess.run(
+            ["tmux", "new-session", "-d", "-s", SESSION_NAME],
+            capture_output=True, text=True,
+        )
+        if result.returncode == 0:
+            break
+        if "server exited unexpectedly" not in result.stderr or attempt == 4:
+            raise RuntimeError(f"Cannot create tmux session: {result.stderr.strip()}")
+        time.sleep(0.2)
     subprocess.run(
         ["tmux", "set-option", "-t", SESSION_NAME, "-g", "mouse", "on"],
     )
@@ -260,6 +342,7 @@ def _check_pane_alive(pane_index: int) -> bool:
 def main(config: InferenceLaunchConfig):
     repo_root = Path(__file__).resolve().parent.parent.parent
 
+    _resolve_sim_grasp_config(config)
     _check_prerequisites(config)
     _kill_existing_session()
 
@@ -276,6 +359,17 @@ def main(config: InferenceLaunchConfig):
     print(f"  Action horizon:  {config.action_horizon}")
     print(f"  Camera:          {config.camera_host}:{config.camera_port}")
     print(f"  Data exporter:   {'Yes' if config.data_exporter else 'No'}")
+    if config.sim_grasp_distance:
+        print(f"  Hand closure:    grasp-region centre | X +/- {config.sim_grasp_x_tolerance * 100:.1f} cm | "
+              f"Y surface gap <= {config.sim_grasp_distance * 100:.1f} cm")
+    if config.sim:
+        print(f"  Arm feedforward: {'ON' if config.sim_arm_gravity_compensation else 'OFF'} (MuJoCo bias)")
+        if config.sim_assisted_pickup:
+            print("  Pickup:          RGB-D waist/right-arm correction; SONIC standing token")
+            print(f"  Pelvis:          {'FIXED simulation fixture' if config.sim_fixed_base else 'Free / SONIC balance'}")
+        else:
+            print("  Pickup:          GR00T/SONIC trajectory only; assisted approach/lift OFF")
+            print("  Table pickup:    add --sim-assisted-pickup --sim-fixed-base")
     if config.data_exporter:
         print(f"    DC frequency:  {config.data_exporter_frequency} Hz")
         print(f"    Task prompt:   {exporter_prompt}")
@@ -297,6 +391,22 @@ def main(config: InferenceLaunchConfig):
             f"--enable-image-publish --enable-offscreen "
             f"--camera-port {config.camera_port}"
         )
+        if config.reach_diagnostic_path:
+            import shlex
+            sim_cmd += " --reach-diagnostic-path " + shlex.quote(config.reach_diagnostic_path)
+        if config.bottle_detection:
+            sim_cmd += " --enable-depth-publish --bottle-detection-port 5582"
+        if config.sim_grasp_distance:
+            sim_cmd += f" --sim-grasp-distance {config.sim_grasp_distance}"
+            sim_cmd += f" --sim-grasp-x-tolerance {config.sim_grasp_x_tolerance}"
+        if config.sim_arm_gravity_compensation:
+            sim_cmd += " --arm-gravity-compensation"
+        if config.sim_assisted_pickup:
+            sim_cmd += " --assisted-pickup"
+        if config.sim_fixed_base:
+            sim_cmd += " --fixed-pickup-base"
+        if config.sim_bottle_xy is not None:
+            sim_cmd += f" --bottle-xy {config.sim_bottle_xy[0]} {config.sim_bottle_xy[1]}"
         sim_target = f"{SESSION_NAME}:sim"
         subprocess.run(
             ["tmux", "send-keys", "-t", sim_target, sim_cmd, "C-m"],
@@ -335,6 +445,26 @@ def main(config: InferenceLaunchConfig):
     print("Starting C++ deploy (pane 0)...")
     _send_to_pane(0, deploy_cmd, wait=3.0)
 
+    if config.sim:
+        # The user requested simulation. Confirm only after deploy.sh has
+        # explicitly resolved loopback and printed its simulation confirmation.
+        deadline = time.monotonic() + 90
+        while time.monotonic() < deadline:
+            result = subprocess.run(
+                ["tmux", "capture-pane", "-p", "-J", "-t", f"{SESSION_NAME}:inference.0", "-S", "-1000"],
+                capture_output=True, text=True,
+            )
+            output = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", result.stdout)
+            if ("This will start the simulation control system." in output
+                    and re.search(r"(?:Resolved interface|Network Interface):\s+lo(?:0)?\b", output)
+                    and "Proceed with deployment?" in output):
+                _send_to_pane(0, "y", wait=.2)
+                print("Simulation deploy confirmed on loopback; use the Start button in the control panel.")
+                break
+            time.sleep(.2)
+        else:
+            print("Simulation deploy did not reach its loopback confirmation. Check pane 0.")
+
     if not _check_pane_alive(0):
         print("WARNING: C++ deploy pane may have failed to start.")
 
@@ -397,9 +527,34 @@ def main(config: InferenceLaunchConfig):
         f"--camera-port {config.camera_port}"
     )
 
+    if config.inspire_ftp_hands:
+        inference_cmd += " --inspire-ftp-hands"
+    if config.sim:
+        inference_cmd += " --sim-control-port 5581"
+    if config.sim_grasp_distance:
+        inference_cmd += f" --sim-grasp-distance {config.sim_grasp_distance}"
+        inference_cmd += f" --sim-grasp-x-tolerance {config.sim_grasp_x_tolerance}"
+    if config.sim_assisted_pickup:
+        inference_cmd += " --sim-stationary-body"
+    if config.action_diagnostic_path:
+        import shlex
+        inference_cmd += " --action-diagnostic-path " + shlex.quote(config.action_diagnostic_path)
+
     print("Starting VLA inference (pane 1)...")
     _send_to_pane(2, inference_cmd, wait=1.0)
 
+    if config.sim and config.bottle_detection:
+        import shlex
+        detector_command = (
+            f"cd {shlex.quote(str(repo_root))} && "
+            f".venv_inference/bin/python gear_sonic/scripts/run_bottle_detector.py "
+            f"--model-path {shlex.quote(config.detector_model)} --camera-port {config.camera_port}"
+        )
+        subprocess.run(["tmux", "new-window", "-t", SESSION_NAME, "-n", "vision"])
+        subprocess.run(["tmux", "send-keys", "-t", f"{SESSION_NAME}:vision", detector_command, "C-m"])
+        subprocess.run(["tmux", "select-window", "-t", f"{SESSION_NAME}:inference"])
+        print("Starting YOLO bottle detector (window: vision)...")
+
     # Select the VLA inference pane
     subprocess.run(
         ["tmux", "select-pane", "-t", f"{SESSION_NAME}:0.2"],
@@ -422,8 +577,16 @@ def main(config: InferenceLaunchConfig):
     if config.data_exporter:
         print("    Pane 3 (bottom-right): Data Exporter")
     print()
-    print("  ** deploy.sh (pane 0) is waiting for confirmation --")
-    print("     click on pane 0 and press Enter to proceed **")
+    if config.sim:
+        print("  Simulation panel: enter bottle X/Y, Reset robot + bottle, Start GR00T.")
+        print("  Robot starts on the ground; startup support releases automatically.")
+        if config.bottle_detection:
+            print("  YOLO surface XYZ and a camera preview show separate bottle detections.")
+        if config.sim_grasp_distance:
+            print(f"  Grasp-region centre: |X error| <= {config.sim_grasp_x_tolerance * 100:.1f} cm and Y surface gap <= {config.sim_grasp_distance * 100:.1f} cm, then close.")
+    else:
+        print("  ** deploy.sh (pane 0) is waiting for confirmation --")
+        print("     click on pane 0 and press Enter to proceed **")
     print()
     print("  Keyboard controls (type in pane 1):")
     print("    p        - Pause / resume inference")
@@ -432,6 +595,11 @@ def main(config: InferenceLaunchConfig):
     print("    [        - Toggle left hand open/closed (initial pose)")
     print("    ]        - Toggle right hand open/closed (initial pose)")
     print("    t <text> - Change inference prompt")
+    if config.sim:
+        print("    F2       - Reopen simulation control panel (viewer focus)")
+        print("    F5 / F6  - Reset robot / Start GR00T (viewer focus)")
+        print("    9        - Manually toggle support (optional)")
+        print("    r        - Reset bottle only (pause with i before repeating a trial)")
     if config.data_exporter:
         print("    c        - Start recording episode")
         print("    s        - Stop recording (success)")
diff --git a/gear_sonic/scripts/run_sim_loop.py b/gear_sonic/scripts/run_sim_loop.py
index 9115e77..d3ca87f 100644
--- a/gear_sonic/scripts/run_sim_loop.py
+++ b/gear_sonic/scripts/run_sim_loop.py
@@ -34,9 +34,29 @@ class SimWrapper:
 
 
 def main(config: ArgsConfig):
+    if not 0 <= config.sim_grasp_distance <= .1 or not 0 <= config.sim_grasp_x_tolerance <= .02:
+        raise ValueError("Invalid simulation grasp Y gap or X tolerance")
     wbc_config = config.load_wbc_yaml()
     # NOTE: we will override the interface to local if it is not specified
     wbc_config["ENV_NAME"] = config.env_name
+    wbc_config["REACH_DIAGNOSTIC_PATH"] = config.reach_diagnostic_path
+    wbc_config["ASYNC_IMAGE_RENDER"] = config.async_image_render
+    wbc_config["SIM_KEYBOARD_ZMQ_PORT"] = 5580
+    wbc_config["SIM_CONTROLS"] = config.sim_controls
+    wbc_config["SIM_CONTROL_PORT"] = config.sim_control_port
+    wbc_config["SIM_GRASP_DISTANCE"] = config.sim_grasp_distance
+    wbc_config["SIM_GRASP_X_TOLERANCE"] = config.sim_grasp_x_tolerance
+    wbc_config["ARM_GRAVITY_COMPENSATION"] = config.arm_gravity_compensation
+    if config.assisted_pickup and (not config.sim_controls or not config.bottle_detection_port):
+        raise ValueError("Assisted pickup requires simulation controls and the RGB-D detector")
+    wbc_config["ASSISTED_PICKUP"] = config.assisted_pickup
+    if config.fixed_pickup_base and not config.assisted_pickup:
+        raise ValueError("Fixed pickup base requires assisted pickup")
+    wbc_config["FIXED_PICKUP_BASE"] = config.fixed_pickup_base
+    wbc_config["BOTTLE_XY"] = config.bottle_xy
+    wbc_config["GROUND_START"] = config.ground_start
+    wbc_config["ENABLE_DEPTH_PUBLISH"] = config.enable_depth_publish
+    wbc_config["BOTTLE_DETECTION_PORT"] = config.bottle_detection_port
 
     if config.enable_image_publish:
         assert (
@@ -65,4 +85,4 @@ def main(config: ArgsConfig):
 
 if __name__ == "__main__":
     config = tyro.cli(ArgsConfig)
-    main(config)
\ No newline at end of file
+    main(config)
diff --git a/gear_sonic/scripts/run_vla_inference.py b/gear_sonic/scripts/run_vla_inference.py
index 7a5792d..d7bb646 100644
--- a/gear_sonic/scripts/run_vla_inference.py
+++ b/gear_sonic/scripts/run_vla_inference.py
@@ -41,6 +41,7 @@ from gear_sonic.utils.data_collection.keyboard_subscriber import (
 from gear_sonic.utils.data_collection.telemetry import Telemetry
 from gear_sonic.utils.data_collection.transforms import compute_projected_gravity
 from gear_sonic.utils.data_collection.zmq_state_subscriber import ZMQStateSubscriber
+from gear_sonic.utils.diagnostic_writer import DiagnosticWriter
 from gear_sonic.utils.inference.initial_poses import LATENT_INITIAL_MOTION_TOKEN
 from gear_sonic.utils.inference.vla_utils import (
     calculate_latency_compensated_index,
@@ -68,6 +69,18 @@ class InferenceConfig:
     port: int = 5550
     """The port of the Isaac-GR00T PolicyServer."""
 
+    action_diagnostic_path: str = ""
+    """Optional JSONL recording of raw policy chunks and published actions."""
+
+    sim_control_port: int = 0
+    """Enable simulation reset/start/status channel; 0 disables it for hardware."""
+
+    sim_grasp_distance: float = 0.
+    """Optional right-hand closure at grasp-region centre X alignment and Y surface gap (m)."""
+
+    sim_grasp_x_tolerance: float = .005
+    """Maximum X error between grasp-region centre and bottle centre (m)."""
+
     # Control
     action_publish_rate: int = 50
     """Rate at which individual actions are published to the C++ control loop (Hz)."""
@@ -114,6 +127,13 @@ class InferenceConfig:
     prompt: str = "demo"
     """The language prompt for the VLA policy."""
 
+    inspire_ftp_hands: bool = False
+    """Experimental simulation adapter for CloudWalk Inspire FTP checkpoints.
+    Maps grip levels to Dex3 poses and uses zero hand observations as in training."""
+
+    sim_stationary_body: bool = False
+    """Simulation assisted pickup: hold SONIC's standing token while the RGB-D controller corrects waist/right arm."""
+
     # Initial pose
     initial_pose_blend_duration: float = 1.0
     """Duration (seconds) for smooth interpolation to initial pose. The robot
@@ -215,6 +235,8 @@ def prepare_observation_from_sensors(
     robot_model,
     language_prompt: str,
     log_errors: bool = False,
+    minimum_capture_monotonic: float | None = None,
+    sensor_status: dict | None = None,
 ):
     """Read sensors and prepare observation for the VLA policy.
 
@@ -227,12 +249,26 @@ def prepare_observation_from_sensors(
             print("[DEBUG] prepare_observation: waiting for camera msg..", flush=True)
         return None
 
-    state_msg = state_subscriber.get_msg()
+    if minimum_capture_monotonic is not None:
+        captured = camera_msg.get("capture_monotonic", 0.)
+        age = time.monotonic() - captured
+        if captured < minimum_capture_monotonic or not 0 <= age < 1.:
+            if sensor_status is not None:
+                sensor_status.update(input_ready=False, error="Waiting for a fresh post-start camera frame")
+            return None
+        if sensor_status is not None:
+            sensor_status.update(input_ready=True, camera_capture_monotonic=captured, error="")
+
+    state_msg = camera_msg.get("robot_state")
+    if state_msg is None:
+        state_msg = state_subscriber.get_msg()
     if state_msg is None:
         if log_errors:
             print("[DEBUG] prepare_observation: waiting for state msg..", flush=True)
         return None
 
+    state_msg = {key: np.asarray(value).copy() for key, value in state_msg.items()}
+
     cam_img = camera_msg["images"]["ego_view"]
 
     # Copy index finger data to middle finger (hardware coupling)
@@ -318,7 +354,7 @@ def _inference_worker_loop(
     while not stop_event.is_set():
         try:
             try:
-                inference_queue.get(timeout=0.1)
+                requested_at = inference_queue.get(timeout=0.1)
             except queue.Empty:
                 continue
 
@@ -329,7 +365,9 @@ def _inference_worker_loop(
                     print("[DEBUG] Worker thread: Observation is None, skipping", flush=True)
                     continue
 
-                inference_start_time = time.monotonic()
+                # Keep the request boundary, so an in-flight result from before
+                # Reset cannot be accepted even if observation preparation ended later.
+                inference_start_time = requested_at
                 processed_action = inference_fn(observation)
 
                 if processed_action is not None:
@@ -363,7 +401,24 @@ def _compute_closed_hand_joints(side: str) -> np.ndarray:
 
 
 def main(config: InferenceConfig):
+    if config.sim_stationary_body and not config.sim_control_port:
+        raise ValueError("Stationary body mode requires the simulation control channel")
+    if not 0 <= config.sim_grasp_distance <= .1:
+        raise ValueError("sim_grasp_distance must be between 0 and 0.1 metres")
+    if not 0 <= config.sim_grasp_x_tolerance <= .02:
+        raise ValueError("sim_grasp_x_tolerance must be between 0 and 0.02 metres")
+    if config.sim_grasp_distance and not config.sim_control_port:
+        raise ValueError("Proximity hand closure requires the simulation control channel")
     pause_loop = True
+    diagnostic_writer = (DiagnosticWriter(config.action_diagnostic_path)
+                         if config.action_diagnostic_path else None)
+
+    def record_action(event, **fields):
+        if diagnostic_writer is not None:
+            diagnostic_writer.submit({"event": event, "monotonic": time.monotonic(),
+                                      "wall_time_unix_s": time.time(), **fields})
+
+    chunk_id = 0
 
     robot_model = instantiate_g1_robot_model(waist_location="lower_and_upper_body")
 
@@ -386,6 +441,25 @@ def main(config: InferenceConfig):
     camera_subscriber = ComposedCameraClientSensor(
         server_ip=config.camera_host, port=config.camera_port
     )
+    # Separate socket on the control thread: the inference worker cannot refresh
+    # its last observation while waiting for a slow/warm-up policy response.
+    camera_monitor = (ComposedCameraClientSensor(server_ip=config.camera_host, port=config.camera_port)
+                      if config.sim_control_port else None)
+    live_camera_capture = 0.
+    last_camera_health_check = 0.
+
+    if config.inspire_ftp_hands:
+        from gear_sonic.utils.inference.inspire_adapter import inspire_grip_to_dex3
+        closed_left = _compute_closed_hand_joints("L")
+        print("Experimental Inspire FTP -> Dex3 grip adapter enabled (simulation only).")
+    if config.inspire_ftp_hands or config.sim_grasp_distance:
+        closed_right = _compute_closed_hand_joints("R")
+    hand_closure = None
+    if config.sim_grasp_distance:
+        from gear_sonic.utils.inference.proximity_hand import ProximityHandClosure
+        hand_closure = ProximityHandClosure(closed_right)
+        print(f"Grasp-region centre closure: |X error| <= {config.sim_grasp_x_tolerance * 100:.1f} cm, Y surface gap <= {config.sim_grasp_distance * 100:.1f} cm.")
+    last_sent_right_hand = np.zeros(7, dtype=np.float32)
 
     zmq_context = zmq.Context()
     zmq_socket = zmq_context.socket(zmq.PUB)
@@ -400,6 +474,17 @@ def main(config: InferenceConfig):
         port=config.keyboard_zmq_port, host=config.keyboard_zmq_host
     )
 
+    simulation_channel = None
+    if config.sim_control_port:
+        from gear_sonic.utils.inference.simulation_controls import SimulationControlChannel
+        simulation_channel = SimulationControlChannel(port=config.sim_control_port)
+    sensor_status = {"input_ready": False, "camera_capture_monotonic": 0., "error": ""}
+    minimum_capture_monotonic = [0.]
+    simulation_preparing = False
+    last_initial_pose_publish = 0.
+    actions_published = 0
+    last_status_publish = 0.
+
     telemetry = Telemetry(window_size=100)
 
     loop_rate = config.action_publish_rate
@@ -413,9 +498,10 @@ def main(config: InferenceConfig):
     initial_pose_left_hand_closed = False
     initial_pose_right_hand_closed = False
 
-    def publish_initial_pose():
+    def publish_initial_pose(wait=True):
         """Publish initial pose command to move robot to starting position."""
-        print("Moving to initial pose")
+        if wait:
+            print("Moving to initial pose")
         left_hand = (
             _compute_closed_hand_joints("L")
             if initial_pose_left_hand_closed
@@ -433,9 +519,10 @@ def main(config: InferenceConfig):
             right_hand_joints=right_hand,
         )
         zmq_socket.send(zmq_message)
-        print_green("Sent latent initial pose via ZMQ")
-        time.sleep(1.0)
-        print("Initial pose done.")
+        if wait:
+            print_green("Sent latent initial pose via ZMQ")
+            time.sleep(1.0)
+            print("Initial pose done.")
 
     def blend_to_initial_pose(duration_s: float) -> bool:
         """Smoothly interpolate from the last sent motion token to the initial pose.
@@ -519,6 +606,7 @@ def main(config: InferenceConfig):
     cached_action_chunk = None
     action_chunk_index = 0
     last_inference_time = 0.0
+    accept_results_after = time.monotonic()
     inference_interval = 1.0 / config.rate
 
     zmq_frame_counter = 0
@@ -530,11 +618,13 @@ def main(config: InferenceConfig):
         nonlocal pause_loop, cpp_loop_running, cpp_mode
         nonlocal initial_pose_left_hand_closed, initial_pose_right_hand_closed
         nonlocal cached_action_chunk, action_chunk_index, last_inference_time
+        nonlocal accept_results_after
         nonlocal zmq_frame_counter, last_sent_motion_token
 
         key = keyboard_listener.read_msg()
         if key is None:
             return
+        record_action("keyboard", key=key)
 
         if key.startswith(PROMPT_MSG_PREFIX):
             new_prompt = key[len(PROMPT_MSG_PREFIX):]
@@ -553,6 +643,8 @@ def main(config: InferenceConfig):
         elif key == "f":
             print("Keyboard: 'f' (stop recording failure -- handled by data exporter)")
         elif key == "i":
+            clear_policy_actions()
+            accept_results_after = time.monotonic()
             if cpp_loop_running and cpp_mode == "PLANNER":
                 if send_cpp_control_command(start=True, planner=False):
                     print("Switched to POSE mode (from PLANNER mode)")
@@ -573,6 +665,13 @@ def main(config: InferenceConfig):
             print("Cleared cached action chunk, reset frame counter")
         elif key == "p":
             pause_loop = not pause_loop
+            clear_policy_actions()
+            # A result computed before a pause/reset must not drive the next
+            # trial. Request a fresh observation when resuming.
+            accept_results_after = time.monotonic()
+            cached_action_chunk = None
+            action_chunk_index = 0
+            last_inference_time = 0.0
             print(f"{'Paused' if pause_loop else 'Resumed'} policy loop")
             if pause_loop:
                 print("Policy loop paused (C++ loop still running - press 'k' to stop)")
@@ -612,6 +711,95 @@ def main(config: InferenceConfig):
     inference_stop_event = threading.Event()
     inference_busy_event = threading.Event()
 
+    def clear_policy_actions():
+        nonlocal cached_action_chunk, action_chunk_index, last_inference_time
+        nonlocal accept_results_after, zmq_frame_counter, last_sent_right_hand
+        accept_results_after = time.monotonic()
+        cached_action_chunk = None
+        action_chunk_index = 0
+        last_inference_time = 0.
+        zmq_frame_counter = 0
+        sensor_status.pop("policy_action", None)
+        if hand_closure is not None:
+            hand_closure.reset()
+        last_sent_right_hand = np.zeros(7, dtype=np.float32)
+        for channel in (inference_queue, result_queue):
+            while True:
+                try:
+                    channel.get_nowait()
+                except queue.Empty:
+                    break
+
+    def check_simulation_input():
+        nonlocal pause_loop, simulation_preparing, last_initial_pose_publish
+        nonlocal last_status_publish, last_sent_motion_token
+        nonlocal initial_pose_left_hand_closed, initial_pose_right_hand_closed
+        if simulation_channel is None:
+            return
+        while (message := simulation_channel.receive()) is not None:
+            command = message.get("command")
+            ok, error = True, ""
+            if command in ("pause", "prepare"):
+                pause_loop = True
+                simulation_preparing = command == "prepare"
+                clear_policy_actions()
+                last_sent_motion_token = None
+                initial_pose_left_hand_closed = initial_pose_right_hand_closed = False
+                sensor_status.update(input_ready=False, error="")
+                publish_initial_pose(wait=False)
+                if simulation_preparing:
+                    ok = send_cpp_control_command(start=True, planner=False)
+                    last_initial_pose_publish = time.monotonic()
+            elif command == "start":
+                simulation_preparing = False
+                clear_policy_actions()
+                minimum_capture_monotonic[0] = time.monotonic()
+                sensor_status.update(input_ready=False, error="Waiting for a fresh post-start camera frame")
+                pause_loop = False
+            elif command == "close_right_hand":
+                from gear_sonic.utils.inference.proximity_hand import ready_to_close
+                # No MuJoCo import is needed in VLA; validate both gates from
+                # the physics-thread sample rather than accepting the old gap-only command.
+                distance = message.get("y_surface_gap_m")
+                x_error = message.get("x_error_m")
+                if hand_closure is None or pause_loop or simulation_preparing:
+                    ok, error = False, "Proximity closure is disabled or policy is paused"
+                elif (not isinstance(distance, (int, float)) or not isinstance(x_error, (int, float))
+                      or not ready_to_close(message, config.sim_grasp_distance, config.sim_grasp_x_tolerance, True, True)):
+                    ok, error = False, "Grasp-region centre is not aligned with bottle X/Y"
+                else:
+                    hand_closure.activate(last_sent_right_hand, time.monotonic(), distance, x_error=x_error)
+                    record_action("proximity_grasp_trigger", y_surface_gap_m=distance, x_error_m=x_error,
+                                  grasp_center_world_m=message.get("grasp_center_world_m"), source=message.get("source"))
+            else:
+                ok, error = False, "Unknown simulation command"
+            record_action("simulation_command", command=command, id=message.get("id"))
+            simulation_channel.send({"type": "ack", "id": message.get("id"), "ok": ok, "error": error})
+            print(f"[Simulation controls] {command}: {'OK' if ok else error}", flush=True)
+        now = time.monotonic()
+        if simulation_preparing and now - last_initial_pose_publish > .5:
+            # Re-send while INIT/WAIT_FOR_CONTROL; the operator start signal and
+            # initial token must both arrive before the simulation releases support.
+            publish_initial_pose(wait=False)
+            send_cpp_control_command(start=True, planner=False)
+            last_initial_pose_publish = now
+        if now - last_status_publish > .1:
+            simulation_channel.send({"type": "status", "paused": pause_loop,
+                "cpp_loop_running": cpp_loop_running, "actions_published": actions_published,
+                **sensor_status})
+            last_status_publish = now
+
+    def infer_observation(obs):
+        if config.inspire_ftp_hands:
+            for key in ("left_hand", "right_hand"):
+                obs["state"][key] = np.zeros_like(obs["state"][key])
+        class RecordingPolicy:
+            def get_action(self, observation):
+                action, info = n1_policy.get_action(observation)
+                record_action("raw_chunk", action={k: np.asarray(v).tolist() for k, v in action.items()})
+                return action, info
+        return run_policy_inference_and_process(RecordingPolicy(), obs, robot_model)
+
     inference_worker_thread = threading.Thread(
         target=_inference_worker_loop,
         args=(
@@ -625,12 +813,10 @@ def main(config: InferenceConfig):
                 robot_model=robot_model,
                 language_prompt=language_prompt_ref[0],
                 log_errors=True,
+                minimum_capture_monotonic=minimum_capture_monotonic[0] if simulation_channel else None,
+                sensor_status=sensor_status,
             ),
-            lambda obs: run_policy_inference_and_process(
-                policy=n1_policy,
-                observation=obs,
-                robot_model=robot_model,
-            ),
+            lambda obs: infer_observation(obs),
         ),
         daemon=True,
     )
@@ -640,15 +826,21 @@ def main(config: InferenceConfig):
         while True:
             t_start = time.monotonic()
             check_keyboard_input()
+            check_simulation_input()
 
             # Consume result first so last_inference_time is fresh before trigger check
             try:
                 processed_action, inference_start_time = result_queue.get_nowait()
+                if pause_loop or inference_start_time < accept_results_after:
+                    continue
                 inference_delay = time.monotonic() - inference_start_time
                 action_chunk_index = calculate_latency_compensated_index(
-                    inference_delay, config.action_publish_rate, config.action_horizon
+                    inference_delay, config.action_publish_rate, config.action_horizon,
+                    has_previous_chunk=cached_action_chunk is not None,
                 )
                 cached_action_chunk = processed_action
+                chunk_id += 1
+                record_action("chunk_selected", chunk_id=chunk_id, start_index=action_chunk_index, latency=inference_delay)
                 last_inference_time = time.monotonic()
                 print_green(
                     f'New action chunk (prompt: "{language_prompt_ref[0]}", '
@@ -665,18 +857,35 @@ def main(config: InferenceConfig):
                 inference_interval=inference_interval,
             )
 
-            if should_start:
+            if should_start and not pause_loop and not worker_is_busy:
                 try:
-                    inference_queue.put_nowait(None)
+                    inference_queue.put_nowait(time.monotonic())
                 except queue.Full:
                     pass
 
             if pause_loop:
-                print("Pausing...", end="", flush=True)
-                time.sleep(0.2)
-                print(".", end="", flush=True)
+                _sleep_remaining(t_start, loop_period)
                 continue
 
+            if simulation_channel is not None:
+                now = time.monotonic()
+                if now - last_camera_health_check >= .1:
+                    latest_frame = camera_monitor.read()
+                    if latest_frame is not None:
+                        live_camera_capture = latest_frame.get("capture_monotonic", 0.)
+                    last_camera_health_check = now
+                captured = live_camera_capture
+                waiting_for_first_frame = captured < minimum_capture_monotonic[0]
+                stale = (now - minimum_capture_monotonic[0] > 5. if waiting_for_first_frame
+                         else now - captured > 1.)
+                if stale:
+                    pause_loop = True
+                    clear_policy_actions()
+                    sensor_status.update(input_ready=False, error="Camera stale/disconnected. Reset before restarting.")
+                    record_action("automatic_pause", reason="camera_stale")
+                    print("[Simulation controls] Camera stale/disconnected; policy paused.", flush=True)
+                    continue
+
             with telemetry.timer("total_loop"):
                 if cached_action_chunk is None:
                     print("[DEBUG] No cached chunk yet, waiting...", flush=True)
@@ -720,6 +929,16 @@ def main(config: InferenceConfig):
                     if right_hand_joints.ndim == 2:
                         right_hand_joints = right_hand_joints[current_idx]
 
+                    raw_right_hand = right_hand_joints.copy()
+                    if config.sim_stationary_body:
+                        motion_token = np.asarray(LATENT_INITIAL_MOTION_TOKEN, dtype=np.float32).reshape(64).copy()
+                    if config.inspire_ftp_hands:
+                        left_hand_joints = inspire_grip_to_dex3(left_hand_joints, closed_left)
+                        right_hand_joints = inspire_grip_to_dex3(right_hand_joints, closed_right)
+                    closure_fraction = None
+                    if hand_closure is not None:
+                        right_hand_joints, closure_fraction = hand_closure.apply(right_hand_joints, time.monotonic())
+
                     frame_index = np.array([zmq_frame_counter], dtype=np.int64)
                     zmq_frame_counter += 1
 
@@ -730,6 +949,25 @@ def main(config: InferenceConfig):
                         right_hand_joints=right_hand_joints,
                     )
                     zmq_socket.send(zmq_message)
+                    actions_published += 1
+                    last_sent_right_hand = right_hand_joints.copy()
+                    sensor_status["policy_action"] = {
+                        "frame": int(frame_index[0]), "chunk": chunk_id, "index": current_idx,
+                        "output": "motion_token + hand joints (no XYZ target)",
+                        "body_source": "SONIC standing token" if config.sim_stationary_body else "GR00T",
+                        "right_grip": float(np.clip(raw_right_hand[:5].mean(), 0., 1.))
+                            if config.inspire_ftp_hands else None,
+                        "published_monotonic": time.monotonic(),
+                        "hand_source": ("grasp_center_alignment_override" if closure_fraction is not None else
+                                        "grasp_center_alignment_wait" if hand_closure else "GR00T"),
+                        "closure_fraction": closure_fraction,
+                        "grasp_trigger_y_gap_m": hand_closure.trigger_distance if hand_closure else None,
+                        "grasp_trigger_x_error_m": hand_closure.trigger_x_error if hand_closure else None,
+                    }
+                    record_action("published", chunk_id=chunk_id, index=current_idx, frame=int(frame_index[0]),
+                                  right_hand=right_hand_joints.tolist(), left_hand=left_hand_joints.tolist(),
+                                  motion_token=motion_token.tolist(), closure_fraction=closure_fraction,
+                                  hand_source=sensor_status["policy_action"]["hand_source"])
                     last_sent_motion_token = motion_token.copy()
                     if zmq_frame_counter % 50 == 0:
                         print_green(
@@ -757,6 +995,12 @@ def main(config: InferenceConfig):
     finally:
         inference_stop_event.set()
         inference_worker_thread.join(timeout=1.0)
+        if diagnostic_writer is not None:
+            diagnostic_writer.close()
+        if simulation_channel is not None:
+            simulation_channel.close()
+        if camera_monitor is not None:
+            camera_monitor.close()
         zmq_socket.close()
         zmq_context.term()
         state_subscriber.close()
diff --git a/gear_sonic/utils/inference/vla_utils.py b/gear_sonic/utils/inference/vla_utils.py
index 3165a31..533d44e 100644
--- a/gear_sonic/utils/inference/vla_utils.py
+++ b/gear_sonic/utils/inference/vla_utils.py
@@ -63,7 +63,8 @@ def prepare_observation_for_eval(robot_model: RobotModel, obs: dict) -> dict:
 
 
 def calculate_latency_compensated_index(
-    inference_delay: float, control_freq: float, action_horizon: int
+    inference_delay: float, control_freq: float, action_horizon: int,
+    has_previous_chunk: bool = True,
 ) -> int:
     """Calculate the starting action index compensating for inference latency.
 
@@ -78,6 +79,10 @@ def calculate_latency_compensated_index(
     Returns:
         Starting index (0 to action_horizon-1) for the action chunk.
     """
+    # At startup/resume the controller is holding its pose, rather than
+    # executing an earlier plan. Skipping actions here skips the approach.
+    if not has_previous_chunk:
+        return 0
     raw_index = np.round(inference_delay * control_freq)
     return int(np.clip(raw_index, 0, action_horizon - 1))
 
diff --git a/gear_sonic/utils/mujoco_sim/base_sim.py b/gear_sonic/utils/mujoco_sim/base_sim.py
index fe8f4a0..c3004ac 100644
--- a/gear_sonic/utils/mujoco_sim/base_sim.py
+++ b/gear_sonic/utils/mujoco_sim/base_sim.py
@@ -10,7 +10,8 @@ import pathlib
 from pathlib import Path
 import pickle
 import tempfile
-from threading import Lock, Thread
+from queue import Queue
+from threading import Event, Lock, Thread
 import time
 from typing import Dict
 import xml.etree.ElementTree as ET
@@ -25,6 +26,7 @@ from gear_sonic.utils.mujoco_sim.metric_utils import check_contact, check_height
 from gear_sonic.utils.mujoco_sim.sim_utils import get_subtree_body_names
 from gear_sonic.utils.mujoco_sim.unitree_sdk2py_bridge import ElasticBand, UnitreeSdk2Bridge
 from gear_sonic.utils.mujoco_sim.robot import Robot
+from gear_sonic.utils.diagnostic_writer import DiagnosticWriter
 
 GEAR_SONIC_ROOT = Path(__file__).resolve().parent.parent.parent.parent
 
@@ -60,17 +62,53 @@ class DefaultEnv:
         self.reward_lock = Lock()
         self.unitree_bridge = None
         self.onscreen = onscreen
+        self.elastic_band = None
+        self._bottle_reset_requested = Event()
+        self.ui_commands = Queue()
+        self.ui_snapshot = {}
+        self.ground_start = self.config.get("GROUND_START", False)
+        self.standby = self.ground_start
+        self._control_transition_started = None
+        self.bottle_placement = None
+        self.scene_changed_at = time.monotonic()
+        self.detection_preview = None
+        self._preview_capture = 0.
+        self._viewer_overlay_worker = None
 
         self.init_scene()
+        self.assisted_pickup = None
+        if self.config.get('ASSISTED_PICKUP', False):
+            from gear_sonic.utils.mujoco_sim.assisted_pickup import AssistedPickup
+            self.assisted_pickup = AssistedPickup(self.mj_model)
+        if self.viewer is not None:
+            from gear_sonic.utils.mujoco_sim.viewer_overlay import ViewerOverlayWorker
+            self._viewer_overlay_worker = ViewerOverlayWorker(self.viewer)
         self.last_reward = 0
 
         self.offscreen = offscreen
-        if self.offscreen:
+        self.async_image_render = bool(offscreen and enable_image_publish
+                                       and self.config.get("ASYNC_IMAGE_RENDER", False))
+        if self.offscreen and not self.async_image_render:
             self.init_renderers()
         self.image_dt = self.config.get("IMAGE_DT", 0.033333)
         self.image_publish_process = None
+        diagnostic_path = self.config.get("REACH_DIAGNOSTIC_PATH", "")
+        self.reach_diagnostic_writer = (DiagnosticWriter(
+            Path(diagnostic_path).with_suffix(".jsonl"), latest_path=diagnostic_path
+        ) if diagnostic_path else None)
 
     def start_image_publish_subprocess(self, start_method: str = "spawn", camera_port: int = 5555):
+        if self._viewer_overlay_worker is not None:
+            self._viewer_overlay_worker.camera_port = camera_port
+        if self.async_image_render:
+            from gear_sonic.utils.mujoco_sim.async_camera import AsyncCameraProcess
+            self.image_publish_process = AsyncCameraProcess(
+                pathlib.Path(GEAR_SONIC_ROOT) / self.config["ROBOT_SCENE"],
+                self.camera_configs, port=camera_port,
+                publish_depth=self.config.get("ENABLE_DEPTH_PUBLISH", False),
+            )
+            self.image_publish_process.start_process()
+            return
         from gear_sonic.utils.mujoco_sim.image_publish_utils import ImagePublishProcess
 
         if len(self.camera_configs) == 0:
@@ -148,11 +186,40 @@ class DefaultEnv:
         """Initialize the default robot scene"""
         xml_path = str(pathlib.Path(GEAR_SONIC_ROOT) / self.config["ROBOT_SCENE"])
         self.mj_model = mujoco.MjModel.from_xml_path(xml_path)
+        if self.config.get('FIXED_PICKUP_BASE', False):
+            from gear_sonic.scripts.run_blue_bottle_pickup import load_anchored_scene
+            self.mj_model = load_anchored_scene(xml_path)
         self.mj_data = mujoco.MjData(self.mj_model)
+        mujoco.mj_forward(self.mj_model, self.mj_data)
         self.mj_model.opt.timestep = self.sim_dt
         self.torso_index = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, "torso_link")
         self.root_body = "pelvis"
         self.root_body_id = self.mj_model.body(self.root_body).id
+        if self.ground_start:
+            floor = self.mj_model.geom('floor').id
+            foot_geoms = [g for g in range(self.mj_model.ngeom)
+                          if 'ankle' in self.mj_model.body(int(self.mj_model.geom_bodyid[g])).name
+                          and self.mj_model.geom_contype[g]]
+            if foot_geoms:
+                clearance = min(mujoco.mj_geomDistance(self.mj_model, self.mj_data, floor, g, 1., np.zeros(6))
+                                for g in foot_geoms)
+                # The XML pose has a ~1 mm sole gap. Seat the locked startup
+                # pose on the floor instead of suspending it above contact.
+                if 0. < clearance < .05:
+                    self.mj_model.qpos0[2] -= clearance + 1e-5
+                    self.mj_data.qpos[:] = self.mj_model.qpos0
+                    mujoco.mj_forward(self.mj_model, self.mj_data)
+        self.initial_qpos = self.mj_model.qpos0.copy()
+        if self.ground_start:
+            # Retract the right palm before an object is placed; keep the left
+            # fingers above the tabletop when the waist leans forward.
+            # Keep qpos0 (joint reference angles) unchanged.
+            for side, pitch in (('left', -.2), ('right', .35)):
+                joint = self.mj_model.joint(f'{side}_shoulder_pitch_joint')
+                self.initial_qpos[int(joint.qposadr[0])] = pitch
+            self.initial_qpos[int(self.mj_model.joint('left_elbow_joint').qposadr[0])] = .3
+            self.mj_data.qpos[:] = self.initial_qpos
+            mujoco.mj_forward(self.mj_model, self.mj_data)
 
         self.joint_class_map = self._get_dof_indices_by_class()
 
@@ -194,11 +261,15 @@ class DefaultEnv:
             else:
                 self.band_attached_link = self.mj_model.body("base_link").id
 
+            if self.ground_start:
+                self._ground_support_point = self.mj_data.xpos[self.band_attached_link].copy()
+                self.elastic_band.point = self._ground_support_point.copy()
+
             if self.onscreen:
                 self.viewer = mujoco.viewer.launch_passive(
                     self.mj_model,
                     self.mj_data,
-                    key_callback=self.elastic_band.MujuocoKeyCallback,
+                    key_callback=self._viewer_key_callback,
                     show_left_ui=False,
                     show_right_ui=False,
                 )
@@ -208,13 +279,17 @@ class DefaultEnv:
         else:
             if self.onscreen:
                 self.viewer = mujoco.viewer.launch_passive(
-                    self.mj_model, self.mj_data, show_left_ui=False, show_right_ui=False
+                    self.mj_model, self.mj_data, key_callback=self._viewer_key_callback,
+                    show_left_ui=False, show_right_ui=False
                 )
             else:
                 mujoco.mj_forward(self.mj_model, self.mj_data)
                 self.viewer = None
 
         if self.viewer:
+            # The green grasp-reference marker is for the human viewer only.
+            # Offscreen cameras keep default sitegroup[5] = 0.
+            self.viewer.opt.sitegroup[5] = 1
             self.viewer.cam.azimuth = 120
             self.viewer.cam.elevation = -30
             self.viewer.cam.distance = 2.0
@@ -244,9 +319,30 @@ class DefaultEnv:
         assert len(self.right_hand_index) == self.robot.NUM_HAND_JOINTS
 
         self.body_joint_index = np.array(self.body_joint_index)
+        self.arm_motor_indices = np.asarray([i for i, joint in enumerate(self.body_joint_index)
+            if any(part in self.mj_model.joint(int(joint)).name for part in ("shoulder", "elbow", "wrist"))], dtype=int)
+        self.arm_dof_addresses = self.mj_model.jnt_dofadr[self.body_joint_index[self.arm_motor_indices]]
         self.left_hand_index = np.array(self.left_hand_index)
         self.right_hand_index = np.array(self.right_hand_index)
 
+        if mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, "red_bottle") >= 0:
+            from gear_sonic.utils.mujoco_sim.object_reset import BottlePlacement
+            self.bottle_placement = BottlePlacement(self.mj_model, self.mj_data)
+            if self.config.get('BOTTLE_XY') is not None:
+                self.bottle_placement.reset(self.mj_model, self.mj_data, self.config['BOTTLE_XY'])
+
+    def restore_ground_support(self):
+        if self.ground_start and self.elastic_band is not None:
+            self.elastic_band.point = self._ground_support_point.copy()
+            self.elastic_band.length = 0
+            self.elastic_band.enable = True
+
+    def release_ground_support(self):
+        if self.ground_start and self.elastic_band is not None:
+            self.elastic_band.enable = False
+            self.mj_data.xfrc_applied[self.band_attached_link] = 0
+            print("[Simulation] Ground support released automatically.", flush=True)
+
     def init_renderers(self):
         self.renderers = {}
         for camera_name, camera_config in self.camera_configs.items():
@@ -257,6 +353,11 @@ class DefaultEnv:
 
     def compute_body_torques(self) -> np.ndarray:
         # PD control: tau = tau_ff + kp * (q_des - q) + kd * (dq_des - dq)
+        if self.standby:
+            addresses = self.mj_model.jnt_qposadr[self.body_joint_index]
+            dofs = self.mj_model.jnt_dofadr[self.body_joint_index]
+            return (np.asarray(self.robot.MOTOR_KP) * (self.initial_qpos[addresses] - self.mj_data.qpos[addresses])
+                    - np.asarray(self.robot.MOTOR_KD) * self.mj_data.qvel[dofs])
         body_torques = np.zeros(self.num_body_dof)
         if self.unitree_bridge is not None and self.unitree_bridge.low_cmd:
             for i in range(self.unitree_bridge.num_body_motor):
@@ -285,8 +386,65 @@ class DefaultEnv:
                             - self.mj_data.qvel[self.body_joint_index[i] + self.qvel_offset - 1]
                         )
                     )
+        if (self.config.get("ARM_GRAVITY_COMPENSATION", False)
+                and self.unitree_bridge is not None
+                and getattr(self.unitree_bridge, "low_cmd_received", False)):
+            # SONIC's C++ deployment sends tau_ff=0. Without feedforward the
+            # weak arm PD gains need a large position error to hold gravity.
+            # qfrc_bias includes gravity and Coriolis; mj_step already computes
+            # it. Compensate arms only; keep body balance and all q/dq targets.
+            body_torques[self.arm_motor_indices] += self.mj_data.qfrc_bias[self.arm_dof_addresses]
         return body_torques
 
+    def begin_control_transition(self):
+        self._control_transition_started = float(self.mj_data.time)
+        self.standby = False
+
+    def hold_initial_robot_pose(self):
+        """Lock robot joints/base only while idle; leave objects free to settle."""
+        if not self.standby:
+            return
+        model, data = self.mj_model, self.mj_data
+        if not hasattr(self, '_idle_robot_indices'):
+            bodies = {self.root_body_id}
+            for body in range(self.root_body_id + 1, model.nbody):
+                if int(model.body_parentid[body]) in bodies:
+                    bodies.add(body)
+            positions, velocities = [], []
+            for joint in range(model.njnt):
+                if int(model.jnt_bodyid[joint]) not in bodies:
+                    continue
+                kind = int(model.jnt_type[joint])
+                nq = 7 if kind == int(mujoco.mjtJoint.mjJNT_FREE) else 4 if kind == int(mujoco.mjtJoint.mjJNT_BALL) else 1
+                nv = nq - 1 if nq > 1 else nq
+                qa, va = int(model.jnt_qposadr[joint]), int(model.jnt_dofadr[joint])
+                positions.extend(range(qa, qa + nq))
+                velocities.extend(range(va, va + nv))
+            self._idle_robot_indices = np.array(positions), np.array(velocities), list(bodies)
+        positions, velocities, bodies = self._idle_robot_indices
+        data.qpos[positions] = self.initial_qpos[positions]
+        data.qvel[velocities] = 0.
+        data.qacc_warmstart[velocities] = 0.
+        data.qfrc_applied[velocities] = 0.
+        data.xfrc_applied[bodies] = 0.
+        mujoco.mj_forward(model, data)
+
+    def blend_startup_torques(self, body, hands):
+        started = self._control_transition_started
+        if started is None:
+            return body, hands
+        t = float(np.clip((self.mj_data.time - started) / 2., 0., 1.))
+        blend = t*t*(3.-2.*t)
+        def hold(joints, kp, kd):
+            qa, va = self.mj_model.jnt_qposadr[joints], self.mj_model.jnt_dofadr[joints]
+            return (kp * (self.initial_qpos[qa] - self.mj_data.qpos[qa])
+                    - kd * self.mj_data.qvel[va] + self.mj_data.qfrc_bias[va])
+        body_hold = hold(self.body_joint_index, np.asarray(self.robot.MOTOR_KP), np.asarray(self.robot.MOTOR_KD))
+        hand_hold = hold(np.r_[self.left_hand_index, self.right_hand_index], 1.5, .1)
+        if t >= 1.:
+            self._control_transition_started = None
+        return (1.-blend)*body_hold + blend*body, (1.-blend)*hand_hold + blend*hands
+
     def get_head_pose(self) -> np.ndarray:
         root_pos = self.mj_data.body("torso_link").xpos.copy()
         # Reorder quaternion from MuJoCo [w,x,y,z] to scipy [x,y,z,w]
@@ -298,6 +456,11 @@ class DefaultEnv:
         return self.mj_data.qvel[:6]
 
     def compute_hand_torques(self) -> np.ndarray:
+        if self.standby:
+            indices = np.concatenate((self.left_hand_index, self.right_hand_index))
+            addresses = self.mj_model.jnt_qposadr[indices]
+            dofs = self.mj_model.jnt_dofadr[indices]
+            return 1.5 * (self.initial_qpos[addresses] - self.mj_data.qpos[addresses]) - .1 * self.mj_data.qvel[dofs]
         left_hand_torques = np.zeros(self.num_hand_dof)
         right_hand_torques = np.zeros(self.num_hand_dof)
         if self.unitree_bridge is not None and self.unitree_bridge.low_cmd:
@@ -387,6 +550,15 @@ class DefaultEnv:
         return obs
 
     def sim_step(self):
+        self.hold_initial_robot_pose()
+        # Viewer callbacks run on a different thread; mutate physics only here.
+        if self._bottle_reset_requested.is_set():
+            self._bottle_reset_requested.clear()
+            if self.bottle_placement and self.bottle_placement.reset(self.mj_model, self.mj_data):
+                self.scene_changed_at = time.monotonic()
+                print("[Simulation] Bottle reset to its initial pose.", flush=True)
+            else:
+                print("[Simulation] No free bottle found in this scene.", flush=True)
         self.obs = self.prepare_obs()
         self.unitree_bridge.PublishLowState(self.obs)
         if self.unitree_bridge.joystick:
@@ -414,6 +586,19 @@ class DefaultEnv:
                 self.mj_data.xfrc_applied[self.band_attached_link] = np.zeros(6)
         body_torques = self.compute_body_torques()
         hand_torques = self.compute_hand_torques()
+        body_torques, hand_torques = self.blend_startup_torques(body_torques, hand_torques)
+        if self.config.get('FIXED_PICKUP_BASE', False) and not self.standby:
+            # Explicit stationary manipulation mode: model inference remains
+            # observable, while only the RGB-D waist/right-arm correction moves
+            # robot joints. The bottle has no constraint or external force.
+            qa = self.mj_model.jnt_qposadr[self.body_joint_index]
+            va = self.mj_model.jnt_dofadr[self.body_joint_index]
+            body_torques = 100. * (self.initial_qpos[qa] - self.mj_data.qpos[qa]) - 4. * self.mj_data.qvel[va] + self.mj_data.qfrc_bias[va]
+            joints = np.r_[self.left_hand_index, self.right_hand_index]
+            qa, va = self.mj_model.jnt_qposadr[joints], self.mj_model.jnt_dofadr[joints]
+            hand_torques = 8. * (self.initial_qpos[qa] - self.mj_data.qpos[qa]) - .2 * self.mj_data.qvel[va] + self.mj_data.qfrc_bias[va]
+        if self.assisted_pickup is not None and not self.standby:
+            self.assisted_pickup.apply_torques(self.mj_data, body_torques, hand_torques, self.body_joint_index)
         # -1: actuator array is 0-based while joint indices from the model are 1-based
         self.torques[self.body_joint_index - 1] = body_torques
         if self.num_hand_dof > 0:
@@ -428,8 +613,37 @@ class DefaultEnv:
         else:
             self.mj_data.ctrl = self.torques
         mujoco.mj_step(self.mj_model, self.mj_data)
+        self.hold_initial_robot_pose()
 
         self.check_fall()
+        if self.reach_diagnostic_writer and time.monotonic() - getattr(self, "_last_reach_diagnostic", 0) > 0.1:
+            from gear_sonic.utils.mujoco_sim.reach_diagnostics import measure_reach
+            targets = {}
+            with self.unitree_bridge.low_cmd_lock:
+                if self.unitree_bridge.low_cmd_received:
+                    for i, jid in enumerate(self.body_joint_index):
+                        targets[int(jid)] = self.unitree_bridge.low_cmd.motor_cmd[i].q
+            for indices, cmd, lock, received in (
+                (self.left_hand_index, self.unitree_bridge.left_hand_cmd,
+                 self.unitree_bridge.left_hand_cmd_lock, self.unitree_bridge.left_hand_cmd_received),
+                (self.right_hand_index, self.unitree_bridge.right_hand_cmd,
+                 self.unitree_bridge.right_hand_cmd_lock, self.unitree_bridge.right_hand_cmd_received),
+            ):
+                with lock:
+                    if received:
+                        for i, jid in enumerate(indices):
+                            targets[int(jid)] = cmd.motor_cmd[i].q
+            report = measure_reach(self.mj_model, self.mj_data, targets)
+            report["wall_time_unix_s"] = time.time()
+            report["monotonic_s"] = time.monotonic()
+            report["elastic_band_enabled"] = bool(self.elastic_band and self.elastic_band.enable)
+            report["arm_gravity_compensation"] = self.config.get("ARM_GRAVITY_COMPENSATION", False)
+            report["assisted_pickup"] = self.assisted_pickup.snapshot() if self.assisted_pickup else None
+            report['fixed_pickup_base'] = self.config.get('FIXED_PICKUP_BASE', False)
+            report["proximity_grasp"] = {key: self.ui_snapshot.get(key) for key in
+                ("grasp_threshold_m", "grasp_x_tolerance_m", "grasp_latched", "bottle_seen", "grasp_status", "policy_action", "phase")}
+            self.reach_diagnostic_writer.submit(report)
+            self._last_reach_diagnostic = time.monotonic()
 
     def apply_perturbation(self, key):
         perturbation_x_body = 0.0
@@ -454,8 +668,122 @@ class DefaultEnv:
 
     def update_viewer(self):
         if self.viewer is not None:
+            snapshot = self.coordinate_snapshot()
+            labels, values = ["WORLD XYZ (m)"], ["X       Y       Z"]
+            for label, key in (("Bottle centre", "bottle"), ("Hand grasp centre (green)", "right_grasp_center"),
+                               ("Right wrist origin", "right_wrist"), ("Left wrist origin", "left_wrist")):
+                if snapshot.get(key) is not None:
+                    labels.append(label)
+                    values.append("  ".join(f"{v:+.3f}" for v in snapshot[key]))
+            target = self.ui_snapshot.get("right_wrist_target")
+            if target is not None:
+                labels.extend(["SONIC wrist command (FK)", "Wrist tracking error"])
+                values.extend(["  ".join(f"{v:+.3f}" for v in target),
+                               f"{self.ui_snapshot['wrist_tracking_error_m'] * 100:.1f} cm"])
+            grasp_target = self.ui_snapshot.get("right_grasp_target")
+            if grasp_target is not None:
+                labels.extend(["SONIC grasp centre (FK)", "Grasp tracking error"])
+                values.extend(["  ".join(f"{v:+.3f}" for v in grasp_target),
+                               f"{self.ui_snapshot['grasp_tracking_error_m'] * 100:.1f} cm"])
+            policy_action = self.ui_snapshot.get("policy_action", {})
+            alignment = self.ui_snapshot.get("hand_alignment", {})
+            grasp = alignment.get("grasp_center_world_m")
+            gap = alignment.get("y_surface_gap_m")
+            gap_text = f"{gap * 100:.2f} cm" if gap is not None else "-- (outside profile)"
+            x_error = alignment.get("x_error_m")
+            if grasp is not None:
+                labels.extend(["Grasp centre (fixed in hand)", "X error (grasp - bottle)", "Y gap to bottle surface", "Hand closure"])
+                values.extend(["  ".join(f"{v:+.3f}" for v in grasp),
+                               f"{x_error * 100:+.2f} cm", gap_text + " (MuJoCo)", self.ui_snapshot.get("grasp_status", "")])
+            grip = policy_action.get("right_grip")
+            labels.extend(["GR00T right grip", "GR00T actions sent"])
+            values.extend([f"{grip * 100:.1f}%" if grip is not None else "--",
+                           str(self.ui_snapshot.get("actions_published", 0))])
+            detection = self.ui_snapshot.get("detection", {})
+            point = detection.get("world_point_m")
+            labels.extend(["Detector surface XYZ", "YOLO bottle confidence", "GR00T detected XYZ", "Run state", "Ground support", "Controls"])
+            values.extend(["  ".join(f"{v:+.3f}" for v in point) if point is not None else detection.get("status", "disabled"),
+                           f"{detection['confidence']:.2f}" if "confidence" in detection else "--",
+                           "Unavailable in checkpoint output", self.ui_snapshot.get("phase", "keyboard"),
+                           "ON (standby)" if self.elastic_band and self.elastic_band.enable else "OFF",
+                           "F2 panel | R bottle reset | F5 robot reset | F6 start"])
+            labels.append("Arm gravity compensation")
+            values.append("ON" if self.config.get("ARM_GRAVITY_COMPENSATION", False) else "OFF")
+            assisted = self.ui_snapshot.get('assisted_pickup')
+            if assisted:
+                labels.extend(['Assisted pickup (RGB-D + IK)', 'Visual bottle centre target'])
+                target = assisted.get('target_center_world_m')
+                values.extend([assisted['stage'], '  '.join(f'{v:+.3f}' for v in target) if target else '--'])
+                labels.append('Pelvis / body mode')
+                values.append('FIXED (simulation fixture)' if self.config.get('FIXED_PICKUP_BASE', False) else 'Free / SONIC')
+                error = assisted.get('position_error_m')
+                labels.append('Assisted arm target error')
+                values.append(f'{error * 100:.2f} cm' if error is not None else '--')
+            # set_texts forwards its font argument directly to mjr_overlay:
+            # valid values are mjtFont (0..2), NOT mjtFontScale (50..300).
+            # A scale value indexes native font tables outside their bounds.
+            detector_text = (f"X {point[0]:+.3f}    Y {point[1]:+.3f}    Z {point[2]:+.3f} m"
+                             if point is not None else detection.get("status", "disabled"))
+            confidence_text = f"Confidence {detection['confidence']:.2f}" if "confidence" in detection else ""
+            texts = [(mujoco.mjtFont.mjFONT_SHADOW,
+                                   mujoco.mjtGridPos.mjGRID_TOPLEFT,
+                                   "\n".join(labels), "\n".join(values)),
+                                  (mujoco.mjtFont.mjFONT_BIG, mujoco.mjtGridPos.mjGRID_BOTTOMLEFT,
+                                   "DETECTED BOTTLE - YOLO (RGB + DEPTH)\n" + detector_text
+                                   + "\n" + confidence_text, "")]
+            if assisted:
+                texts.append((mujoco.mjtFont.mjFONT_BIG, mujoco.mjtGridPos.mjGRID_BOTTOMRIGHT,
+                    'ASSISTED PICKUP - RGB-D + IK\n' + assisted['stage'] + '\n' + assisted.get('error', ''), ''))
+            if self.ui_snapshot.get("grasp_threshold_m") and grasp is not None:
+                texts.append((mujoco.mjtFont.mjFONT_BIG, mujoco.mjtGridPos.mjGRID_BOTTOMRIGHT,
+                    f"GRASP CENTRE - X/Y\nX error {x_error * 100:+.2f} cm | tol {self.ui_snapshot.get('grasp_x_tolerance_m', .005) * 100:.1f}\n"
+                    f"Y gap {gap_text} | target {self.ui_snapshot['grasp_threshold_m'] * 100:.1f}\n"
+                    + self.ui_snapshot.get("grasp_status", ""), ""))
+            if self._viewer_overlay_worker is not None:
+                self._viewer_overlay_worker.submit(texts, detection)
+            else:
+                self.viewer.set_texts(texts)
             self.viewer.sync()
 
+    def coordinate_snapshot(self):
+        result = {}
+        site = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_SITE, "right_hand_grasp_center")
+        if site >= 0:
+            result["right_grasp_center"] = self.mj_data.site_xpos[site].tolist()
+        for key, name in (("bottle", "red_bottle"), ("right_wrist", "right_wrist_yaw_link"),
+                          ("left_wrist", "left_wrist_yaw_link")):
+            body = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, name)
+            if body >= 0:
+                result[key] = self.mj_data.xpos[body].tolist()
+        return result
+
+    def command_coordinate_snapshot(self):
+        """FK of SONIC joint commands at the current base; display only."""
+        if self.config.get('FIXED_PICKUP_BASE', False):
+            # These proposed SONIC targets are not executed by the fixed-base
+            # fixture. Displaying their tracking error would be misleading.
+            return {}
+        bridge = self.unitree_bridge
+        if self.standby or bridge is None or not getattr(bridge, "low_cmd_received", False):
+            return {}
+        if not hasattr(self, "_command_fk"):
+            self._command_fk = mujoco.MjData(self.mj_model)
+        target = self._command_fk
+        target.qpos[:] = self.mj_data.qpos
+        with bridge.low_cmd_lock:
+            for i, joint in enumerate(self.body_joint_index):
+                target.qpos[self.mj_model.jnt_qposadr[joint]] = bridge.low_cmd.motor_cmd[i].q
+        mujoco.mj_forward(self.mj_model, target)
+        wrist = self.mj_model.body("right_wrist_yaw_link").id
+        commanded = target.xpos[wrist].copy()
+        result = {"right_wrist_target": commanded.tolist(),
+                  "wrist_tracking_error_m": float(np.linalg.norm(commanded - self.mj_data.xpos[wrist]))}
+        site = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_SITE, "right_hand_grasp_center")
+        if site >= 0:
+            result.update(right_grasp_target=target.site_xpos[site].tolist(),
+                          grasp_tracking_error_m=float(np.linalg.norm(target.site_xpos[site] - self.mj_data.site_xpos[site])))
+        return result
+
     def update_viewer_camera(self):
         if self.viewer is not None:
             if self.viewer.cam.type == mujoco.mjtCamera.mjCAMERA_TRACKING:
@@ -478,6 +806,18 @@ class DefaultEnv:
         return {}
 
     def update_render_caches(self):
+        if self.async_image_render:
+            if self.image_publish_process is not None:
+                # Pair proprioception with the image exposure, not with the
+                # later time at which rendering/network delivery completes.
+                state = {
+                    "body_q": self.mj_data.qpos[self.body_joint_index + self.qpos_offset - 1].tolist(),
+                    "left_hand_q": self.mj_data.qpos[self.left_hand_index + self.qpos_offset - 1].tolist(),
+                    "right_hand_q": self.mj_data.qpos[self.right_hand_index + self.qpos_offset - 1].tolist(),
+                    "base_quat": self.mj_data.qpos[3:7].tolist(),
+                }
+                self.image_publish_process.submit(self.mj_data, robot_state=state)
+            return {}
         render_caches = {}
         for camera_name, camera_config in self.camera_configs.items():
             renderer = self.renderers[camera_name]
@@ -494,12 +834,24 @@ class DefaultEnv:
 
         return render_caches
 
+    def _viewer_key_callback(self, key):
+        # GLFW F2 / F5 / F6; commands are processed on the physics thread.
+        if key in (291, 294, 295):
+            self.ui_commands.put({"command": {291: "open_panel", 294: "reset", 295: "start"}[key]})
+            return
+        if key == ord("R"):
+            self._bottle_reset_requested.set()
+        elif self.elastic_band:
+            self.elastic_band.MujuocoKeyCallback(key)
+
     def handle_keyboard_button(self, key):
         if self.elastic_band:
             self.elastic_band.handle_keyboard_button(key)
 
         if key == "backspace":
             self.reset()
+        if key.lower() == "r":
+            self._bottle_reset_requested.set()
         if key == "v":
             self.update_viewer_camera()
         if key in ["up", "down", "left", "right"]:
@@ -512,7 +864,12 @@ class DefaultEnv:
             print(f"Warning: Robot has fallen, height: {self.mj_data.qpos[2]:.3f} m")
 
         if self.fall:
-            self.reset()
+            if self.config.get("SIM_CONTROLS", False):
+                self.ui_commands.put({"command": "reset"})
+                # Hold the reset pose while awaiting the policy pause acknowledgement.
+                self.reset()
+            else:
+                self.reset()
 
     def check_self_collision(self):
         robot_bodies = get_subtree_body_names(self.mj_model, self.mj_model.body(self.root_body).id)
@@ -524,7 +881,17 @@ class DefaultEnv:
         return self_collision
 
     def reset(self):
+        self._control_transition_started = None
+        if getattr(self, 'assisted_pickup', None) is not None:
+            self.assisted_pickup.reset()
         mujoco.mj_resetData(self.mj_model, self.mj_data)
+        self.mj_data.qpos[:] = self.initial_qpos
+        self.standby = self.ground_start
+        self.restore_ground_support()
+        mujoco.mj_forward(self.mj_model, self.mj_data)
+        if self.bottle_placement:
+            self.bottle_placement.reset(self.mj_model, self.mj_data)
+        self.scene_changed_at = time.monotonic()
 
 
 class BaseSimulator:
@@ -573,6 +940,12 @@ class BaseSimulator:
         self.init_subscriber()
         self.init_publisher()
 
+        self.interactive_controls = None
+        if self.config.get("SIM_CONTROLS", False):
+            from gear_sonic.utils.mujoco_sim.interactive_controls import InteractiveSimulationControls
+            self.interactive_controls = InteractiveSimulationControls(
+                self.sim_env, port=self.config.get("SIM_CONTROL_PORT", 5581))
+
         self.sim_thread = None
 
     def start_as_thread(self):
@@ -583,7 +956,10 @@ class BaseSimulator:
         self.sim_env.start_image_publish_subprocess(start_method, camera_port)
 
     def init_subscriber(self):
-        pass
+        self.keyboard_subscriber = None
+        if self.config.get("SIM_KEYBOARD_ZMQ_PORT"):
+            from gear_sonic.utils.data_collection.keyboard_subscriber import ZMQKeyboardSubscriber
+            self.keyboard_subscriber = ZMQKeyboardSubscriber(port=self.config["SIM_KEYBOARD_ZMQ_PORT"])
 
     def init_publisher(self):
         pass
@@ -599,13 +975,22 @@ class BaseSimulator:
         """Main simulation loop"""
         sim_cnt = 0
         ts = time.time()
+        next_step = time.monotonic()
 
         try:
             while self._running and (
                 (self.sim_env.viewer and self.sim_env.viewer.is_running())
                 or (self.sim_env.viewer is None)
             ):
-                step_start = time.monotonic()
+                if self.keyboard_subscriber is not None:
+                    key = self.keyboard_subscriber.read_msg()
+                    if key in ("r", "R", "9"):
+                        self.sim_env.handle_keyboard_button(key.lower())
+                    elif key in ("k", "i", "p") and self.interactive_controls is not None:
+                        self.interactive_controls.handle_keyboard(key)
+
+                if self.interactive_controls is not None:
+                    self.interactive_controls.poll()
 
                 self.sim_env.sim_step()
                 now = time.time()
@@ -624,9 +1009,13 @@ class BaseSimulator:
                 if sim_cnt % int(self.image_dt / self.sim_dt) == 0:
                     self.sim_env.update_render_caches()
 
-                # Simple rate limiter (replaces ROS rate)
-                elapsed = time.monotonic() - step_start
-                sleep_time = self.sim_dt - elapsed
+                # Absolute deadlines avoid accumulating sleep/scheduling jitter.
+                # Bound catch-up after a long stall (e.g. moving the viewer).
+                next_step += self.sim_dt
+                now_monotonic = time.monotonic()
+                if now_monotonic - next_step > 0.1:
+                    next_step = now_monotonic
+                sleep_time = next_step - now_monotonic
                 if sleep_time > 0:
                     time.sleep(sleep_time)
 
@@ -645,9 +1034,19 @@ class BaseSimulator:
     def close(self):
         self._running = False
         try:
+            if getattr(self, "interactive_controls", None) is not None:
+                self.interactive_controls.close()
+                self.interactive_controls = None
+            if getattr(self, "keyboard_subscriber", None) is not None:
+                self.keyboard_subscriber.close()
+                self.keyboard_subscriber = None
+            if getattr(self.sim_env, "reach_diagnostic_writer", None) is not None:
+                self.sim_env.reach_diagnostic_writer.close()
             if self.sim_env.image_publish_process is not None:
                 self.sim_env.image_publish_process.stop()
             if self.sim_env.viewer is not None:
+                if self.sim_env._viewer_overlay_worker is not None:
+                    self.sim_env._viewer_overlay_worker.close()
                 self.sim_env.viewer.close()
         except Exception as e:
             print(f"Warning during close: {e}")
diff --git a/gear_sonic/utils/mujoco_sim/configs.py b/gear_sonic/utils/mujoco_sim/configs.py
index 5ec03fa..618adaf 100644
--- a/gear_sonic/utils/mujoco_sim/configs.py
+++ b/gear_sonic/utils/mujoco_sim/configs.py
@@ -336,9 +336,48 @@ class SimLoopConfig(BaseConfig):
     mp_start_method: str = "spawn"
     """Multiprocessing start method"""
 
+    sim_controls: bool = True
+    """Show native bottle/reset/start controls and world-coordinate overlay."""
+
+    sim_control_port: int = 5581
+    """Local acknowledged command/status channel between simulation and VLA."""
+
+    sim_grasp_distance: float = 0.
+    """Close when grasp-region centre aligns with bottle X and Y surface gap reaches this many metres; 0 disables."""
+
+    sim_grasp_x_tolerance: float = .005
+    """Allowed world-X mismatch between grasp-region centre and bottle centre (metres)."""
+
+    arm_gravity_compensation: bool = False
+    """Add MuJoCo bias feedforward on shoulder/elbow/wrist motors; preserve SONIC joint targets."""
+
+    assisted_pickup: bool = False
+    """Correct right-arm pickup with RGB-D bottle target; requires simulation controls and detector."""
+
+    fixed_pickup_base: bool = False
+    """Anchor pelvis and hold unused joints during the assisted table task; simulation only."""
+
+    bottle_xy: Optional[tuple[float, float]] = None
+    """Initial bottle placement on the table; Reset preserves the selected X/Y."""
+
+    ground_start: bool = True
+    """Start/reset on the ground with standby support; release automatically on Start."""
+
+    enable_depth_publish: bool = False
+    """Publish depth/calibration with RGB for the separate display-only detector."""
+
+    bottle_detection_port: int = 0
+    """Detector result port; 0 disables it when running the simulator directly."""
+
     enable_image_publish: bool = False
     """Enable image publishing in simulation"""
 
+    async_image_render: bool = True
+    """Render streamed cameras in a separate process to keep physics responsive."""
+
+    reach_diagnostic_path: str = ""
+    """Optional JSON file for live bottle/hand coordinates and command tracking."""
+
     camera_port: int = 5555
     """Camera port for image publishing"""
 
diff --git a/gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/input_interface/zmq_manager.hpp b/gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/input_interface/zmq_manager.hpp
index 6917e59..1b94a14 100644
--- a/gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/input_interface/zmq_manager.hpp
+++ b/gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/input_interface/zmq_manager.hpp
@@ -370,6 +370,11 @@ class ZMQManager : public InputInterface {
                           current_motion_mutex);
       } else {
         // Streamed motion mode: delegate to pose interface
+        // Network command flags belong to the manager. The pose interface
+        // only sees its own keyboard flags, so it cannot forward this start.
+        if (start_control_ && !stop_control_) {
+          operator_state.start = true;
+        }
         if (pose_interface_) {
           pose_interface_->handle_input(motion_reader, current_motion, current_frame,
                                        operator_state, reinitialize_heading,
diff --git a/install_scripts/install_inference.sh b/install_scripts/install_inference.sh
index 0f98903..5c83ed6 100755
--- a/install_scripts/install_inference.sh
+++ b/install_scripts/install_inference.sh
@@ -40,10 +40,10 @@ if ! command -v uv &>/dev/null; then
 fi
 echo "[OK] uv $(uv --version)"
 
-# ── 2. Install a uv-managed Python 3.10 (includes dev headers / Python.h) ────
-echo "[INFO] Installing uv-managed Python 3.10 (includes development headers) …"
-uv python install 3.10
-MANAGED_PY="$(uv python find --no-project 3.10)"
+# ── 2. Install a uv-managed Python 3.12 (includes dev headers / Python.h) ────
+echo "[INFO] Installing uv-managed Python 3.12 (includes development headers) …"
+uv python install 3.12
+MANAGED_PY="$(uv python find --no-project 3.12)"
 echo "[OK] Using Python: $MANAGED_PY"
 
 # ── 3. Clean previous venv (if any) ──────────────────────────────────────────
@@ -52,7 +52,7 @@ echo "[INFO] Removing old .venv_inference (if present) …"
 rm -rf .venv_inference
 
 # ── 4. Create venv & install inference extra ─────────────────────────────────
-echo "[INFO] Creating .venv_inference with uv-managed Python 3.10 …"
+echo "[INFO] Creating .venv_inference with uv-managed Python 3.12 …"
 uv venv .venv_inference --python "$MANAGED_PY" --prompt gear_sonic_inference
 # shellcheck disable=SC1091
 source .venv_inference/bin/activate
diff --git a/docs/source/tutorials/blue_bottle_pickup.md b/docs/source/tutorials/blue_bottle_pickup.md
new file mode 100644
--- /dev/null
+++ b/docs/source/tutorials/blue_bottle_pickup.md
@@ -0,0 +1,47 @@
+# Assisted blue bottle pickup in MuJoCo
+
+Run from the repository root:
+
+```bash
+.venv_sim/bin/python gear_sonic/scripts/run_blue_bottle_pickup.py
+```
+
+This opens an independent MuJoCo demo and automatically approaches, closes the
+right Dex3 hand, lifts the blue bottle, and holds it. Close the viewer to finish.
+No GR00T server, SONIC process, DDS, tmux launcher, or keyboard commands are needed.
+It does not connect to a physical robot.
+
+This is an **assisted inverse-kinematics grasp**, using the bottle pose from
+MuJoCo. It is not a successful evaluation of the GR00T checkpoint. The pelvis is
+anchored to the world to stabilize manipulation. The bottle remains a free body
+and is held through physical finger contacts and friction, with no hand-object
+weld, object teleportation, or external lifting force.
+
+The CloudWalk checkpoint's training dataset uses Inspire FTP hands:
+https://huggingface.co/datasets/cloudwalk-research/gr00t-g1-grab-bottle-right-hand-v2
+The scene uses Dex3. Converting normalized grip level to a Dex3 closed pose does
+not reproduce Inspire grasp geometry or reach/grip timing. A task-trained Dex3
+checkpoint or a separately validated VLA/IK hybrid is needed for autonomous
+vision-conditioned pickup with this embodiment.
+
+The demo solves wrist position and orientation with waist pitch and the right
+arm, applies PD joint control with gravity compensation, gradually closes the
+hand, and lifts 18 cm. Joint limits and actuator effort limits remain enforced.
+The initial arm pregrasp pose is set before simulation begins. Current grasp
+geometry is tuned for this scene's cylindrical bottle, not arbitrary objects.
+
+Validation and video recording:
+
+```bash
+MUJOCO_GL=egl .venv_sim/bin/python gear_sonic/scripts/run_blue_bottle_pickup.py \
+  --headless --record
+```
+
+Outputs are written to `outputs/blue_bottle_pickup/`: `report.json`,
+`third_person.mp4`, `ego_view.mp4`, and images of the held bottle. Success requires
+at least 12 cm lift throughout a 3-second hold and persistent contact from both
+thumb and index/middle fingers. Reports contain actual bottle/wrist coordinates
+and finger contacts, not model-predicted object coordinates.
+
+Small workspace perturbations can be checked using `--bottle-offset X Y` in
+meters. IK raises an error if it cannot reach the requested grasp pose.
diff --git a/docs/source/tutorials/cloudwalk_inspire_checkpoint.md b/docs/source/tutorials/cloudwalk_inspire_checkpoint.md
new file mode 100644
--- /dev/null
+++ b/docs/source/tutorials/cloudwalk_inspire_checkpoint.md
@@ -0,0 +1,89 @@
+# CloudWalk checkpoint and Inspire FTP compatibility
+
+The local `~/models/g1_sonic_grab_bottle` identifies itself as a deployment export
+of a 4-GPU, batch-64, 10k-step run. It is not the official v2 `checkpoint-20000`
+(6-GPU, batch-48 training recipe). Both have the same embodiment name; that does
+not imply identical training or interchangeable hand kinematics.
+
+Official v2 source:
+https://huggingface.co/cloudwalk-research/gr00t-n17-g1-grab-bottle-rh-210ep-v2-finetune
+Dataset:
+https://huggingface.co/datasets/cloudwalk-research/gr00t-g1-grab-bottle-right-hand-v2
+
+The official weights are stored separately at
+`checkpoints/cloudwalk_g1_bottle_v2/checkpoint-20000`. The existing weights are
+not modified. Audit tensor headers, shard completeness and hand statistics:
+
+```bash
+.venv_inference/bin/python gear_sonic/scripts/check_cloudwalk_checkpoint.py \
+  checkpoints/cloudwalk_g1_bottle_v2/checkpoint-20000
+```
+
+After stopping the existing policy server on port 5550, start the official one:
+
+```bash
+bash gear_sonic/scripts/run_cloudwalk_policy_server.sh
+```
+
+The server still emits motion tokens plus Inspire FTP hand channels. This is not
+an Inspire hand simulator. The experimental `--inspire-ftp-hands` client option
+maps aggregate grip intent to a Dex3 pose; it does not emulate the original hand.
+
+Native deployment still requires the CloudWalk `InspireFTPGripMapper` (or a
+validated equivalent) and an Inspire-compatible simulator/DDS bridge. The
+official Unitree repository does provide a G1 Inspire FTP URDF and meshes:
+https://github.com/unitreerobotics/unitree_ros/blob/master/robots/g1_description/g1_29dof_rev_1_0_with_inspire_hand_FTP.urdf
+The hand URDFs also define passive finger mimic joints. These must be preserved
+as constraints in MuJoCo; replacing a filename does not convert the current
+seven-motor Dex3 bridge into the six-motor Inspire interface. The CloudWalk repository
+linked in the dataset (`cloudwalk-research/GR00T-WholeBodyControl`) returned 404
+when inspected. The two supplied NVIDIA repositories contain the server and
+Dex3 control stack. Isaac-GR00T includes RoboCasa references to `InspireRightHand`
+for Fourier GR1, which do not establish the correct G1 RH56DFTP mount or channel
+mapping. Upstream compatibility discussion:
+https://github.com/NVlabs/GR00T-WholeBodyControl/issues/121
+
+Do not reinterpret seven FTP channels as seven Dex3 joint angles or rename the
+Dex3 scene as Inspire. Needed next: original hand model + mapper, or task data
+and fine-tuning collected with the actual Dex3 embodiment.
+
+The official model card also reports grasp anticipation even with an absent
+bottle; successful reach motion alone is not proof of reliable object detection.
+The simulation task must be evaluated closed loop after hand compatibility is
+resolved. Neither checkpoint download nor a successful server query demonstrates
+physical pickup.
+
+## Recorded-input verification
+
+`outputs/input_audit/training_inference.json` records calls to the running
+checkpoint-20000 server using synchronized RGB frames and joint states from
+episode 0 of the training dataset. At frame 480, the source grip begins at 0.30
+and reaches 1.00 in the next 40 frames; the model predicts 0.307 to 1.00.
+At frame 500, source grip begins at 0.70; the model predicts 0.676 to 1.00.
+This checks the server's ability to emit a closing sequence without sending any
+action to the robot. It does not demonstrate simulated pickup.
+
+`outputs/input_audit/input_ablation.json` contains three inference trials per
+combination of recorded/live image and recorded/live body state. Grip predictions
+vary, and even a simulation image without the bottle in view can elicit closing
+with recorded grasp-phase body state. Therefore neither reaching nor closing is
+evidence of object detection. The experiment cannot attribute failure to only
+the image or only the body state.
+
+The model card's success rates describe the physical G1 + Inspire stack, not
+this MuJoCo scene. Preserve that distinction when evaluating a port.
+
+## Bottle position and manual reset
+
+The blue bottle's initial body position in `scene_43dof.xml` is
+`0.43 -0.11 0.801` metres, 5 cm closer to the initial robot position than before.
+Restart the simulation stack to load XML/Python changes and reconnect deploy;
+the policy server does not need restarting.
+
+Focus the MuJoCo window and press **R** to restore only the bottle's initial
+position and upright orientation, with zero object velocity. The reset is
+queued onto the physics thread and does not reset the robot, controls, or clock.
+To repeat a trial, first send **i** + Enter in the keyboard publisher pane to
+pause the policy and return to the initial open-hand pose, then press **R** in
+MuJoCo and send **p** + Enter in the keyboard pane to resume inference. The
+MuJoCo key is separate from the keyboard publisher's policy controls.
diff --git a/docs/source/tutorials/simulation_controls.md b/docs/source/tutorials/simulation_controls.md
new file mode 100644
--- /dev/null
+++ b/docs/source/tutorials/simulation_controls.md
@@ -0,0 +1,249 @@
+# Điều khiển chai và robot trong MuJoCo
+
+Giữ policy server v10 đang chạy, hoặc mở terminal riêng và chạy:
+
+```bash
+bash gear_sonic/scripts/run_cloudwalk_policy_server.sh
+```
+
+Detector riêng đã được cài trong môi trường hiện tại. Khi cài lại dự án, chạy
+một lần `bash install_scripts/install_bottle_detector.sh`. Script tải YOLO11n
+khoảng **5.4 MiB** và giữ nguyên các phiên bản Torch/GR00T đã cài.
+
+Từ thư mục gốc dự án, khởi động simulation:
+
+```bash
+.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
+  --sim \
+  --policy-host 127.0.0.1 \
+  --policy-port 5550 \
+  --no-data-exporter \
+  --inspire-ftp-hands \
+  --sim-assisted-pickup \
+  --sim-fixed-base \
+  --prompt "grab the bottle"
+```
+
+Launcher mở cửa sổ MuJoCo và bảng **Bottle / Robot Controls**. C++ deploy được
+xác nhận tự động chỉ khi `deploy.sh` báo simulation và interface loopback `lo`.
+Robot giữ cố định vị trí thân và tất cả khớp trên mặt đất ngay khi mở.
+Chỉ khi bấm **Start GR00T**, hệ thống mới chuẩn bị SONIC và chuyển điều khiển
+dần trong 2 giây; sau đó hỗ trợ khởi động tự tắt. Không cần bấm `9`.
+Khóa tư thế chỉ áp dụng khi chờ/reset, không áp dụng trong lúc nắm/nâng.
+
+**Chế độ gắp tại bàn dùng cả `--sim-assisted-pickup --sim-fixed-base`.**
+Đế/pelvis được cố định bằng ràng buộc MuJoCo; các khớp không tham gia gắp giữ
+tư thế chờ. Bộ hiệu chỉnh eo và cánh tay phải dùng ba lần
+nhận diện RGB-D ổn định, bán kính chai và chiều cao bàn để tính tâm mục tiêu,
+tiếp cận, khép ngón và nâng. Overlay **ASSISTED PICKUP - RGB-D + IK** hiển thị
+giai đoạn thực tế. Chai được nâng bằng tiếp xúc vật lý, không gắn vào tay.
+Server GR00T vẫn nhận ảnh/trạng thái và trả dự đoán để theo dõi; chế độ hỗ trợ
+giữ token đứng của SONIC, còn quỹ đạo gắp được bộ điều khiển RGB-D/IK thực thi.
+Đây là chế độ gắp hỗ trợ với đế cố định, không phải đánh giá checkpoint tự gắp.
+Chạy hỗ trợ nhưng bỏ `--sim-fixed-base` sẽ dùng robot tự do; khả năng giữ
+thăng bằng trong chế độ đó chưa ổn định.
+Nếu bỏ `--sim-assisted-pickup` (và `--sim-fixed-base`), lệnh cũ chỉ dùng quỹ đạo checkpoint và điều kiện khép ngón;
+điều kiện khép ngón không tự đưa tay đến chai.
+
+Launcher bật bù mô-men trọng lực/Coriolis của MuJoCo cho vai, khuỷu và cổ tay.
+SONIC gửi `tau_ff=0`; với Kp thấp, tay có thể võng đáng kể so với góc yêu cầu.
+Bù này cộng `qfrc_bias` vào mô-men các khớp tay, giữ nguyên `q/dq` do SONIC
+yêu cầu và giới hạn lực của simulator. Không áp dụng cho chân, eo hoặc robot
+thật. Overlay **Arm gravity compensation** ghi ON/OFF. Để so sánh hành vi cũ,
+thêm `--no-sim-arm-gravity-compensation` vào launcher.
+
+Bù mô-men riêng lẻ chỉ sửa việc bám lệnh. Trong chế độ hỗ trợ nắm ở trên,
+tọa độ RGB-D còn được dùng để hiệu chỉnh tiếp cận; không truyền XYZ vào GR00T.
+
+YOLO11n chạy trên CPU trong tmux window **vision**, tự đọc camera ngay khi
+simulation mở, kể cả trước khi bấm Start. Ảnh camera trực tiếp xuất
+hiện ở góc phải trên cửa sổ MuJoCo, cập nhật độc lập với YOLO (không chờ
+suy luận 2 Hz). Khung xanh YOLO dùng kết quả gần nhất, có tuổi nhận diện
+riêng và tự ẩn sau 750 ms; đây không phải tracking liên tục. Dòng `Camera | age`
+cho biết tuổi ảnh theo mili giây; quá 1 giây hiển thị `STALE CAMERA`.
+Tọa độ nhận diện vẫn cập nhật theo detector; ô thông tin bên trái và bảng điều khiển
+hiển thị **Detector surface XYZ / YOLO surface** cùng confidence.
+
+## Thao tác
+
+Sau khi nâng chai thành công (`success`), nút **Lower / Place on table**
+(Hạ xuống / Đặt lên bàn) sẽ bật. Bấm một lần để robot hạ chậm về tư thế nắm
+trên bàn, giữ ngón tay khép cho tới khi có tiếp xúc đỡ giữa chai và mặt bàn,
+rồi mở ngón trong 2 giây. Sau khi xác nhận chai đứng trên bàn, robot tự
+lùi bàn tay khỏi chai (`retreat`), thu cánh tay và eo về tư thế lúc bắt đầu
+(`return_home`), rồi giữ nguyên tại `complete`. Không cần bấm thêm nút;
+Reset vẫn có thể ngắt quá trình. Khi đạt `complete`, nút **Start GR00T**
+sáng lại: bấm để nhận diện và gắp chai tại vị trí vừa đặt, không cần Reset.
+Lượt mới xóa mục tiêu cũ và chờ ảnh nhận diện mới; giữ nguyên cảnh và vị trí
+chai. Trong lúc đang gắp/đặt/thu tay, Start vẫn bị khóa.
+Nếu hết quỹ đạo hạ mà chai chưa chạm bàn, robot dò xuống chậm 3 mm/s,
+tối đa thêm 2 cm, và dừng ngay khi có tiếp xúc đỡ. Nếu vẫn không có tiếp xúc,
+hệ thống giữ tay khép và báo lỗi thay vì thả chai.
+Nút này dành cho `--sim-assisted-pickup`; Reset vẫn có thể ngắt thao tác.
+Khởi động lại simulation sau khi cập nhật code để thấy nút mới.
+
+Để đặt sang vị trí khác, nhập **Place destination X/Y** ngay phía trên nút
+**Lower / Place on table**, rồi bấm nút này. Đây là tọa độ thế giới theo mét
+của tâm chai khi đặt; Z vẫn theo mặt bàn. Ví dụ gắp ở `(0.43, -0.11)` rồi
+đặt ở `(0.43, -0.08)`. Robot giữ chai khép trong tay, di chuyển ngang khi còn
+nâng cao, sau đó hạ và mở tay. Đích nằm ngoài bàn hoặc không giải được IK
+sẽ bị từ chối; giữ chai và chọn đích gần hơn. Xác nhận đặt thành công yêu cầu chai
+đứng trên bàn, sai lệch XY dưới 2.5 cm; không bảo đảm chính xác tuyệt đối.
+Hai ô vị trí chai ban đầu/Apply ở trên vẫn chỉ dùng đặt cảnh trước Start.
+Đích đặt xuống không thay đổi tọa độ chai dùng cho Reset.
+
+1. Nhập **X**, **Y** theo mét, dùng dấu chấm thập phân. Bấm
+   **Apply X/Y / Reset bottle** để đặt/dựng lại chai.
+2. Bấm **Start GR00T**. Robot giữ tư thế trong khi chờ SONIC sẵn sàng, chuyển
+   điều khiển dần rồi lấy ảnh mới để suy luận và xác định mục tiêu nắm.
+3. Bấm **Reset robot + bottle** để dừng suy luận, loại bỏ động tác còn tồn,
+   đưa robot về tư thế/địa điểm khởi động và dựng chai tại X/Y đã chọn.
+   Sau reset, robot chờ lần bấm Start tiếp theo. Reset này đặt lại cả đồng hồ
+   simulation.
+4. Để đổi X/Y khi robot đang chạy, bấm Reset trước. Đóng riêng bảng điều khiển
+   không tắt simulation; bấm **F2** trong cửa sổ MuJoCo để mở lại.
+
+Sau mỗi Reset, mục tiêu nhận diện, tiến trình nắm/nâng, vận tốc và hàng đợi
+hành động cũ được xóa. X/Y đã chọn của chai được giữ lại để lặp lượt thử.
+Muốn thử vị trí mới: **Reset → nhập X/Y → Apply X/Y → Start**. Bộ hiệu chỉnh
+ước lượng lại mục tiêu từ camera mỗi lượt. Vị trí phải nằm trong tầm tay phải
+và nhìn thấy được; nằm trên bàn chưa chắc đã nằm trong tầm với.
+Có thể đặt vị trí ngay trong lệnh khởi động bằng cách thêm
+`--sim-bottle-xy 0.40 -0.15`. Reset vẫn giữ X/Y đã chọn; khi mở bảng điều khiển,
+các ô X/Y hiển thị đúng vị trí này.
+
+Đã kiểm thử camera + server với chế độ hỗ trợ/đế cố định tại ba vị trí
+`(0.43, -0.11)`, `(0.40, -0.15)` và `(0.46, -0.08)` m: chai được giữ bằng
+tiếp xúc ngón tay và nâng tối thiểu lần lượt khoảng **18.2, 18.2 và 13.5 cm**
+trong giai đoạn giữ. Báo cáo nằm ở `outputs/assisted_audit/final_live_*.json`.
+Đây là các vị trí đã đo, không bảo đảm mọi điểm trên bàn đều gắp được.
+
+Phím tắt trong cửa sổ MuJoCo: **F5** reset robot + chai, **F6** Start.
+**R** chỉ dựng lại chai ở X/Y đã chọn, giữ robot và đồng hồ; nên dừng lượt chạy
+trước khi dùng R. Luồng terminal `k`, `i`, `p` vẫn được hỗ trợ, nhưng bảng điều
+khiển xử lý trình tự bắt đầu và reset đầy đủ hơn.
+
+X/Y được kiểm tra để thân chai nằm trong mặt bàn. Với scene hiện tại:
+X từ **0.276 đến 0.724 m**, Y từ **-0.424 đến 0.424 m**.
+Z lúc đặt chai cố định **0.801 m** tại tâm hình trụ thân chai, mặt bàn cao
+**0.700 m**. Khi vật lý chạy, chai có thể đổ hoặc được nâng nên Z đo được
+thực tế sẽ thay đổi. Các thay đổi X/Y chỉ tồn tại trong phiên simulation;
+khởi động lại đọc vị trí từ XML hoặc `--sim-bottle-xy` nếu được truyền vào.
+
+## Các tọa độ hiển thị
+
+Overlay trong MuJoCo và bảng điều khiển cập nhật liên tục:
+
+- **Bottle centre / Bottle MuJoCo**: tâm thân chai do MuJoCo cung cấp.
+- **Right wrist**, **Left wrist**: gốc khung tọa độ hai cổ tay,
+  không phải đầu ngón tay hay tâm vùng kẹp.
+- Tất cả dùng hệ tọa độ thế giới, đơn vị mét: +X hướng về phía trước của robot
+  lúc khởi động, -Y về phía tay phải.
+  +Y hướng về phía tay trái, +Z hướng lên. Xoay góc nhìn MuJoCo không đổi
+  các trục này; khi robot quay người, hướng trước của robot có thể khác +X.
+- **Ground support** cho biết hỗ trợ đang bật lúc chờ/reset hay đã tắt.
+- **Published actions** tăng khi VLA gửi hành động tới SONIC.
+- **Detector surface XYZ / YOLO surface**: tọa độ nhận diện ước lượng bằng
+  YOLO11n từ RGB, kết hợp depth camera và thông số camera để đổi sang hệ thế giới.
+  Đây là một điểm nhìn thấy trên bề mặt gần tâm khung nhận diện, **không phải
+  tâm thân chai**. Vì vậy Z có thể khác 0.801 m, kể cả khi chai đứng trên bàn.
+- **YOLO bottle confidence**: độ tin cậy nhận diện lớp `bottle`; ngưỡng mặc định
+  0.25. Chấm đỏ trong ảnh camera là điểm dùng để ước lượng XYZ.
+
+Checkpoint hiện tại xuất `motion_token` và lệnh tay, **không xuất tọa độ XYZ,
+bounding box hoặc kết quả detect chai riêng**. Dòng **GR00T detected XYZ** vì
+vậy ghi `unavailable in checkpoint output`. Tọa độ từ detector mới được ghi
+riêng với nguồn **YOLO**, không được gắn nhãn GR00T. Detector không đọc body ID
+hay vị trí chai thật; input của nó là RGB, depth và thông số camera. Khi không
+bật `--sim-assisted-pickup`, tọa độ YOLO chỉ để quan sát/xác nhận có chai.
+Chế độ khép tay theo khoảng
+cách bên dưới dùng hình học MuJoCo làm điều kiện khép ngón, nhưng vẫn không
+đưa XYZ vào policy làm tọa độ mục tiêu.
+Nút Start bắt đầu suy luận từ ảnh mới; không có bước xác nhận detect XYZ riêng.
+Các thao tác giao diện này không bảo đảm checkpoint gắp/nâng chai thành công.
+
+Nếu không thấy chai, có che khuất hoặc mất camera, tọa độ detector bị xóa và
+hiện trạng thái `not_detected`, `waiting` hoặc `stale`; không dùng lại XYZ cũ.
+YOLO vẫn có thể nhận diện sai hoặc điểm depth nằm trên vật che phía trước.
+
+Để tắt detector và ảnh depth, thêm `--no-bottle-detection` vào lệnh launcher.
+Kết quả mới nhất được lưu ở `outputs/bottle_detector/latest.json`.
+Nguồn model và API: [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/),
+[Predict](https://docs.ultralytics.com/modes/predict/).
+
+Nếu camera ngắt hoặc ảnh quá cũ, VLA tự tạm dừng thay vì tiếp tục động tác cũ.
+Kiểm tra pane inference rồi bấm Reset và Start để chạy lại.
+
+Các nhãn giao diện dùng tiếng Anh vì Tk trong môi trường WSL hiện tại chỉ có
+font bitmap không hiển thị đầy đủ tiếng Việt.
+
+## Khép tay theo tâm vùng nắm và hai trục X/Y
+
+Phần này mô tả chế độ cũ khi **không bật `--sim-assisted-pickup`**.
+Chế độ hỗ trợ ở lệnh đầu trang thay thế bộ kích hoạt này bằng tiếp cận theo X,
+khép ngón và nâng, có kiểm tra tiếp xúc đối diện và giữ chai trong 3 giây.
+
+Lệnh launcher `--sim` với detector đang bật tự dùng khoảng hở Y **2 cm** và
+sai số X **±5 mm**. Thêm `--sim-grasp-distance 0` để dùng lại lệnh tay GR00T.
+
+Điểm tham chiếu là **tâm vùng nắm giữa bàn tay**, site
+`right_hand_grasp_center`, gắn cố định vào `right_wrist_yaw_link` tại tọa độ
+cục bộ `(0.120, 0.050, 0.000) m` của bàn tay Dex3 hiện tại. Đây là điểm quy ước
+trong khoảng ôm vật của bàn tay. Tọa độ thế giới được tính bằng
+`grasp_world = wrist_world + wrist_rotation @ grasp_local`.
+Không dùng đầu ngón tay, trọng tâm khối lượng COM hay gốc cổ tay làm điều kiện.
+Gập các ngón không làm điểm tham chiếu này di chuyển trong khung bàn tay.
+Offset này dành cho hình học Dex3; nếu thay bàn tay cần hiệu chỉnh site theo
+vùng nắm của bàn tay mới.
+
+**Chấm xanh** trong cửa sổ MuJoCo đánh dấu điểm đang kiểm tra. Marker thuộc
+site group 5, không có khối lượng/va chạm và bị ẩn khỏi ảnh camera đầu vào GR00T.
+Bảng điều khiển và overlay **GRASP CENTRE - X/Y** hiển thị XYZ của điểm này,
+X error, Y surface gap, ngưỡng và trạng thái chờ/khép/giữ.
+Dòng **Wrist origin** là gốc cổ tay, khác điểm nắm; không so trực tiếp tọa độ
+cổ tay với tâm chai để kết luận tay đã tới vật.
+
+Sau Start và nhận diện chai bằng YOLO, hai điều kiện phải đúng cùng lúc:
+
+- `abs(grasp_center.x - bottle_body_center.x) <= 0.005 m`.
+- Khoảng hở từ tâm vùng nắm đến bề mặt thân chai theo Y còn **0 đến 0.02 m**.
+
+Với chai đứng, tại X trùng và Z trong thân chai,
+`Y_gap = abs(grasp_center.y - bottle_center.y) - bottle_radius`.
+Bán kính chai **2.5 cm**, nên khoảng hở 2 cm tương ứng chênh lệch Y với tâm chai
+**4.5 cm**. Ví dụ chai `(0.430, -0.110, 0.801)`, điểm nắm tại
+`(0.430, -0.155, 0.840)` đạt ngưỡng. Khi chai có độ nghiêng, phép đo dùng
+hướng hình trụ hiện tại. X/Z ngoài tiết diện thân chai hiện `--` và không khép.
+
+Điều kiện hiện tại là **tiếp cận ngang theo Y**: X trùng chai, Y còn hở 2 cm.
+Nếu muốn **tiếp cận từ trước robot theo X**, điều kiện tương ứng sẽ là
+Y trùng chai, X còn hở 2 cm. Ví dụ cùng chai ở trên, điểm nắm
+`(0.385, -0.110, 0.840)` cách bề mặt 2 cm theo X. Đây là cách đối chiếu trục,
+không phải một chế độ tự đổi hướng trong code. Cả hai cách đều cần điểm nắm
+nằm trong chiều cao thân chai; đổi X/Y không sửa được quỹ đạo tay còn xa hoặc
+cao hơn thân chai. Ngưỡng khép ngón chỉ quyết định thời điểm nắm, không đặt
+tọa độ mục tiêu cho cánh tay.
+
+Tay phải giữ mở trước ngưỡng, khép dần trong **0.3 giây** khi đạt cả hai điều
+kiện, rồi giữ khép tới Reset. Chai nghiêng quá 30 độ không kích hoạt.
+Nhận diện được ghi nhớ trong lượt để việc tay che camera không làm mất xác
+nhận; Reset hoặc đặt lại chai xóa xác nhận này.
+
+Nguồn khoảng cách là hình học MuJoCo; YOLO chỉ xác nhận có chai. GR00T/SONIC
+vẫn điều khiển quỹ đạo thân/cánh tay/nâng. Ô **SONIC grasp (FK)** hiển thị vị trí
+điểm nắm theo lệnh khớp SONIC tại vị trí thân hiện tại; **Grasp tracking error**
+cho biết bàn tay thực tế lệch bao xa so với lệnh. Đây là tọa độ tính bằng FK,
+không phải tọa độ mục tiêu XYZ do GR00T xuất.
+Nếu cả lệnh và vị trí thực đều thiếu X, điều kiện khép không tự đưa cánh tay tới
+chai. Nếu lệnh đã tới nhưng tay thực chưa tới, cần xử lý việc bám lệnh khớp.
+
+**Không dùng chế độ ngưỡng cũ để chạy bài gắp/nâng/đặt chai đã kiểm thử.**
+Hai tham số `--sim-grasp-distance 0.02 --sim-grasp-x-tolerance 0.005`
+chỉ kiểm tra thời điểm khép ngón; chúng không bật hiệu chỉnh tiếp cận hay nâng.
+Để chạy bài gắp tại bàn, dùng lệnh ở đầu tài liệu có cả
+`--sim-assisted-pickup --sim-fixed-base`. Nút Lower cũng cần chế độ hỗ trợ này.
+
+Log `proximity_grasp_trigger` ghi `grasp_center_world_m`, `x_error_m`,
+`y_surface_gap_m` và nguồn phép đo. COM khối lượng chỉ còn là dữ liệu chẩn
+đoán riêng, không được dùng để kích hoạt nắm. Khi chạy robot thật hoặc tắt
+detector, launcher không bật bộ điều khiển khép tay bổ sung này.
diff --git a/gear_sonic/scripts/check_cloudwalk_checkpoint.py b/gear_sonic/scripts/check_cloudwalk_checkpoint.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/scripts/check_cloudwalk_checkpoint.py
@@ -0,0 +1,74 @@
+"""Audit the CloudWalk Inspire FTP checkpoint against this Dex3 simulator.
+
+Does not load GPU weights or infer that equal dimensionality means compatibility.
+"""
+import argparse
+import json
+from pathlib import Path
+import struct
+
+
+def audit(path):
+    path = Path(path).expanduser().resolve()
+    processor = json.loads((path / 'processor_config.json').read_text())
+    modalities = processor['processor_kwargs']['modality_configs']['unitree_g1_sonic']
+    stats = json.loads((path / 'statistics.json').read_text())['unitree_g1_sonic']
+    index = json.loads((path / 'model.safetensors.index.json').read_text())['weight_map']
+    missing = []
+    for shard in sorted(set(index.values())):
+        file = path / shard
+        if not file.is_file():
+            missing.append(shard)
+            continue
+        with file.open('rb') as stream:
+            raw = stream.read(8)
+            if len(raw) != 8:
+                raise ValueError('Truncated safetensors shard: ' + shard)
+            size = struct.unpack('<Q', raw)[0]
+            if size > 100_000_000:
+                raise ValueError('Invalid safetensors header: ' + shard)
+            header = json.loads(stream.read(size))
+        if any(name not in header for name, owner in index.items() if owner == shard):
+            raise ValueError('Shard does not contain tensors declared in index: ' + shard)
+        for name, tensor in header.items():
+            if name != '__metadata__' and 8 + size + tensor['data_offsets'][1] > file.stat().st_size:
+                raise ValueError('Incomplete tensor data: ' + name)
+    hand_zero = all(all(v == 0 for v in stats['state'][key]['min']) and
+                    all(v == 0 for v in stats['state'][key]['max'])
+                    for key in ['left_hand', 'right_hand'])
+    source_file = path.parent / 'source.json'
+    source = json.loads(source_file.read_text()) if source_file.exists() else None
+    return {'checkpoint': str(path), 'missing_shards': missing,
+            'source': source,
+            'weight_files_complete': not missing,
+            'embodiment': 'unitree_g1_sonic',
+            'action_keys': modalities['action']['modality_keys'],
+            'action_horizon': len(modalities['action']['delta_indices']),
+            'training_hand_observations_constant_zero': hand_zero,
+            'source_hand': 'Normalized grip channels; native joint mapping requires dataset verification',
+            'right_hand_action_statistics': stats['action']['right_hand_joints'],
+            'current_simulator_hand': 'Unitree Dex3',
+            'native_hand_compatibility': False,
+            'dex3_adapter_status': 'Experimental grip-intent mapping; not Inspire geometry',
+            'required_for_native_deployment': ['Inspire FTP URDF/MJCF and collision meshes',
+                'InspireFTPGripMapper channel order/ranges',
+                'matching SONIC controller checkpoint and deployment configuration']}
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('checkpoint', type=Path)
+    parser.add_argument('--output', type=Path)
+    args = parser.parse_args()
+    report = audit(args.checkpoint)
+    text = json.dumps(report, indent=2)
+    print(text)
+    if args.output:
+        args.output.parent.mkdir(parents=True, exist_ok=True)
+        args.output.write_text(text + '\n')
+    if report['missing_shards']:
+        raise SystemExit(1)
+
+
+if __name__ == '__main__':
+    main()
diff --git a/gear_sonic/scripts/convert_inspire_ftp_hand.py b/gear_sonic/scripts/convert_inspire_ftp_hand.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/scripts/convert_inspire_ftp_hand.py
@@ -0,0 +1,67 @@
+"""Convert an official Inspire FTP hand URDF to a standalone MuJoCo model.
+
+This prepares geometry and mimic constraints; it does not replace the G1 DDS
+bridge or establish the CloudWalk channel-to-motor mapping.
+"""
+import argparse
+from pathlib import Path
+import tempfile
+import xml.etree.ElementTree as ET
+
+import mujoco
+
+
+def convert(source: Path, destination: Path):
+    urdf = ET.parse(source)
+    root = urdf.getroot()
+    compiler = root.find("mujoco/compiler")
+    if compiler is None:
+        raise ValueError("Expected the official URDF's MuJoCo compiler element")
+    compiler.set("meshdir", str((source.parent / "meshes").resolve()))
+    for mesh in root.findall(".//mesh"):
+        mesh.set("filename", Path(mesh.get("filename")).name)
+    destination.parent.mkdir(parents=True, exist_ok=True)
+    with tempfile.TemporaryDirectory() as temporary:
+        imported = Path(temporary) / "hand.urdf"
+        urdf.write(imported)
+        model = mujoco.MjModel.from_xml_path(str(imported))
+        mujoco.mj_saveLastXML(str(destination), model)
+    tree = ET.parse(destination)
+    xml = tree.getroot()
+    equality = xml.find("equality")
+    if equality is None:
+        equality = ET.SubElement(xml, "equality")
+    existing_mimics = {joint.get("joint1") for joint in equality.findall("joint")}
+    actuators = ET.SubElement(xml, "actuator")
+    for joint in root.findall("joint"):
+        if joint.get("type") not in ("revolute", "continuous"):
+            continue
+        mimic = joint.find("mimic")
+        if mimic is not None:
+            if joint.get("name") not in existing_mimics:
+                ET.SubElement(equality, "joint", {
+                    "joint1": joint.get("name"), "joint2": mimic.get("joint"),
+                    "polycoef": f"{mimic.get('offset', '0')} {mimic.get('multiplier', '1')} 0 0 0",
+                })
+        else:
+            limit = joint.find("limit")
+            ET.SubElement(actuators, "position", {
+                "name": joint.get("name") + "_act", "joint": joint.get("name"),
+                "kp": "20", "kv": "0.5", "forcerange": "-10 10",
+                "ctrllimited": "true", "ctrlrange": limit.get("lower") + " " + limit.get("upper"),
+            })
+    ET.indent(tree)
+    tree.write(destination)
+    model = mujoco.MjModel.from_xml_path(str(destination))
+    if (model.nu, model.njnt, model.neq) != (6, 12, 6):
+        raise ValueError(f"Unexpected FTP topology: {model.nu=}, {model.njnt=}, {model.neq=}")
+    return model
+
+
+if __name__ == "__main__":
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("source", type=Path)
+    parser.add_argument("destination", type=Path)
+    args = parser.parse_args()
+    model = convert(args.source, args.destination)
+    print(f"Compiled {args.destination}: {model.nu} motors, {model.njnt} joints, {model.neq} mimic constraints")
diff --git a/gear_sonic/scripts/run_blue_bottle_pickup.py b/gear_sonic/scripts/run_blue_bottle_pickup.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/scripts/run_blue_bottle_pickup.py
@@ -0,0 +1,215 @@
+"""Physical, assisted Dex3 bottle pickup in MuJoCo.
+
+This is an IK grasp primitive using simulator ground truth, not GR00T inference.
+The pelvis is anchored to the world for this manipulation test. The bottle
+remains a free body: no weld, teleport, or external lifting force is applied.
+
+Run from repository root with .venv_sim/bin/python. Use --headless for validation.
+"""
+import argparse
+import json
+from pathlib import Path
+import tempfile
+import time
+import xml.etree.ElementTree as ET
+
+import mujoco
+import numpy as np
+from scipy.optimize import least_squares
+from scipy.spatial.transform import Rotation
+
+ROOT = Path(__file__).resolve().parents[2]
+SCENE = ROOT / 'gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml'
+
+
+def load_anchored_scene(scene=SCENE):
+    scene = Path(scene)
+    original = mujoco.MjModel.from_xml_path(str(scene))
+    with tempfile.TemporaryDirectory() as directory:
+        expanded = Path(directory) / 'scene.xml'
+        mujoco.mj_saveLastXML(str(expanded), original)
+        tree = ET.parse(expanded)
+        root = tree.getroot()
+        root.find('compiler').set('meshdir', str(scene.parent / 'meshes'))
+        equality = root.find('equality')
+        if equality is None:
+            equality = ET.SubElement(root, 'equality')
+        ET.SubElement(equality, 'weld', body1='pelvis', solref='.002 1')
+        model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding='unicode'))
+    model.opt.timestep = .001
+    return model
+
+
+class BottlePickup:
+    def __init__(self, offset=(0., 0.)):
+        self.model = m = load_anchored_scene()
+        self.data = d = mujoco.MjData(m)
+        self.arm = [m.joint('waist_pitch_joint').id] + [m.joint('right_' + name + '_joint').id for name in
+            ['shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow', 'wrist_roll', 'wrist_pitch', 'wrist_yaw']]
+        self.arm_adr = m.jnt_qposadr[self.arm]
+        self.hand = [m.joint('right_hand_' + name + '_joint').id for name in
+                     ['thumb_0', 'thumb_1', 'thumb_2', 'middle_0', 'middle_1', 'index_0', 'index_1']]
+        self.hand_adr = m.jnt_qposadr[self.hand]
+        self.closed = np.array([0., -.7, -.7, 1., 1.5, 1., 1.5])
+        self.wrist = m.body('right_wrist_yaw_link').id
+        self.bottle = m.body('red_bottle').id
+        bottle_adr = m.joint('red_bottle_free_joint').qposadr[0]
+        d.qpos[bottle_adr:bottle_adr + 2] += offset
+        mujoco.mj_forward(m, d)
+        self.initial_bottle_z = float(d.xpos[self.bottle, 2])
+        # Dex3 grasp center lies about 12 cm forward and 5 cm left of wrist.
+        # Grasp the straight cylindrical section, 4 cm above the body origin.
+        self.goal = d.xpos[self.bottle].copy() + np.array([-.12, -.05, .04])
+        guess = np.array([.3, 0., -.2, 0., .8, 0., 0., 0.])
+        self.grasp_q = self.ik(self.goal, guess)
+        pre = self.ik(self.goal + np.array([-.10, 0., .08]), self.grasp_q)
+        d.qpos[self.arm_adr] = pre
+        self.target = d.qpos.copy()
+        act_joints = m.actuator_trnid[:, 0]
+        self.act_q = m.jnt_qposadr[act_joints]
+        self.act_v = m.jnt_dofadr[act_joints]
+        hand_mask = np.array(['hand_' in m.joint(int(j)).name for j in act_joints])
+        self.kp = np.where(hand_mask, 8., 100.)
+        self.kd = np.where(hand_mask, .2, 4.)
+        self.trace = []
+
+    def ik(self, position, guess):
+        m = self.model
+        scratch = mujoco.MjData(m)
+        scratch.qpos[:] = self.data.qpos
+        lower = m.jnt_range[self.arm, 0] + .001
+        upper = m.jnt_range[self.arm, 1] - .001
+        def residual(q):
+            scratch.qpos[self.arm_adr] = q
+            mujoco.mj_forward(m, scratch)
+            rotation_error = Rotation.from_matrix(scratch.xmat[self.wrist].reshape(3, 3).T).as_rotvec()
+            return np.r_[scratch.xpos[self.wrist] - position, .1 * rotation_error]
+        solution = least_squares(residual, np.clip(guess, lower, upper), bounds=(lower, upper),
+                                 max_nfev=150, ftol=1e-8, xtol=1e-8, gtol=1e-8)
+        if np.linalg.norm(residual(solution.x)) > .005:
+            raise RuntimeError('Bottle is outside this assisted grasp primitive workspace')
+        return solution.x
+
+    def hand_contacts(self):
+        m, d = self.model, self.data
+        fingers = set()
+        for c in d.contact:
+            a, b = int(m.geom_bodyid[c.geom1]), int(m.geom_bodyid[c.geom2])
+            if a == self.bottle or b == self.bottle:
+                other = b if a == self.bottle else a
+                name = m.body(other).name
+                if name.startswith('right_hand_'):
+                    fingers.add(name)
+        return sorted(fingers)
+
+    def step(self):
+        m, d = self.model, self.data
+        mujoco.mj_forward(m, d)
+        torque = self.kp * (self.target[self.act_q] - d.qpos[self.act_q])
+        torque -= self.kd * d.qvel[self.act_v]
+        torque += d.qfrc_bias[self.act_v]
+        d.ctrl[:] = np.clip(torque, m.actuator_ctrlrange[:, 0], m.actuator_ctrlrange[:, 1])
+        mujoco.mj_step(m, d)
+
+    def run(self, frame_callback=None):
+        m, d = self.model, self.data
+        for stage, seconds in [('approach', 2.), ('close', 2.5), ('lift', 2.), ('hold', 3.)]:
+            start = self.target[self.arm_adr].copy()
+            end = self.grasp_q if stage == 'approach' else start
+            if stage == 'lift':
+                end = self.ik(self.goal + np.array([0., 0., .18]), self.grasp_q)
+            count = int(seconds / m.opt.timestep)
+            for index in range(count):
+                fraction = min((index + 1) / (count * .75), 1.)
+                fraction = fraction * fraction * (3 - 2 * fraction)
+                self.target[self.arm_adr] = start + fraction * (end - start)
+                if stage == 'close':
+                    self.target[self.hand_adr] = self.closed * fraction
+                self.step()
+                if index % 40 == 0:
+                    mujoco.mj_forward(m, d)
+                    sample = {'stage': stage, 'time_s': float(d.time),
+                              'bottle_world_m': d.xpos[self.bottle].tolist(),
+                              'wrist_world_m': d.xpos[self.wrist].tolist(),
+                              'hand_contacts': self.hand_contacts()}
+                    self.trace.append(sample)
+                    if frame_callback:
+                        frame_callback(stage)
+            print(stage, 'bottle height:', round(float(d.xpos[self.bottle, 2]), 4), flush=True)
+        holds = [s for s in self.trace if s['stage'] == 'hold']
+        minimum_lift = min(s['bottle_world_m'][2] for s in holds) - self.initial_bottle_z
+        opposed = all(any('thumb' in n for n in s['hand_contacts']) and
+                      any('index' in n or 'middle' in n for n in s['hand_contacts']) for s in holds)
+        return {'success': bool(minimum_lift > .12 and opposed),
+                'mode': 'assisted IK; pelvis anchored; physical free-body grasp',
+                'minimum_lift_during_hold_m': minimum_lift, 'hold_duration_s': 3.,
+                'opposed_finger_contacts_throughout_hold': opposed, 'trace': self.trace}
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument('--headless', action='store_true')
+    parser.add_argument('--record', action='store_true', help='Save third-person and ego videos')
+    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs/blue_bottle_pickup')
+    parser.add_argument('--bottle-offset', nargs=2, type=float, default=[0., 0.], metavar=('X', 'Y'))
+    args = parser.parse_args()
+    args.output_dir.mkdir(parents=True, exist_ok=True)
+    pickup = BottlePickup(args.bottle_offset)
+    m, d = pickup.model, pickup.data
+    viewer = renderer = None
+    writers = {}
+    if not args.headless:
+        import mujoco.viewer as mjviewer
+        viewer = mjviewer.launch_passive(m, d)
+        viewer.cam.azimuth = 130
+        viewer.cam.elevation = -20
+        viewer.cam.distance = 2.2
+        viewer.cam.lookat[:] = [.25, 0., .8]
+    camera = mujoco.MjvCamera()
+    camera.azimuth, camera.elevation, camera.distance = 130, -20, 2.2
+    camera.lookat[:] = [.25, 0., .8]
+    if args.record:
+        import cv2
+        renderer = mujoco.Renderer(m, height=480, width=640)
+        for name in ['third_person', 'ego_view']:
+            writers[name] = cv2.VideoWriter(str(args.output_dir / (name + '.mp4')),
+                                            cv2.VideoWriter_fourcc(*'mp4v'), 25., (640, 480))
+            if not writers[name].isOpened():
+                raise RuntimeError('Video writer could not open ' + name)
+    def frame(stage):
+        if viewer:
+            if not viewer.is_running():
+                raise KeyboardInterrupt
+            viewer.sync()
+            time.sleep(.04)
+        if renderer:
+            for name, cam in [('third_person', camera), ('ego_view', 'head_camera')]:
+                renderer.update_scene(d, camera=cam)
+                rgb = renderer.render()
+                writers[name].write(rgb[:, :, ::-1])
+                if stage == 'hold':
+                    cv2.imwrite(str(args.output_dir / (name + '_held.jpg')), rgb[:, :, ::-1])
+    try:
+        report = pickup.run(frame)
+        (args.output_dir / 'report.json').write_text(json.dumps(report, indent=2))
+        print(json.dumps({k: v for k, v in report.items() if k != 'trace'}, indent=2))
+        if not report['success']:
+            raise SystemExit('Grasp failed physical lift/contact checks')
+        if viewer:
+            print('Pickup succeeded. Close the viewer to finish.', flush=True)
+            while viewer.is_running():
+                for _ in range(40):
+                    pickup.step()
+                viewer.sync()
+                time.sleep(.04)
+    finally:
+        if viewer:
+            viewer.close()
+        if renderer:
+            renderer.close()
+        for writer in writers.values():
+            writer.release()
+
+
+if __name__ == '__main__':
+    main()
diff --git a/gear_sonic/scripts/run_bottle_detector.py b/gear_sonic/scripts/run_bottle_detector.py
new file mode 100644
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
diff --git a/gear_sonic/scripts/run_cloudwalk_policy_server.sh b/gear_sonic/scripts/run_cloudwalk_policy_server.sh
new file mode 100755
--- /dev/null
+++ b/gear_sonic/scripts/run_cloudwalk_policy_server.sh
@@ -0,0 +1,21 @@
+#!/usr/bin/env bash
+# Start the selected CloudWalk VLA checkpoint; does not start robot control.
+set -euo pipefail
+SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
+REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
+CHECKPOINT="${CLOUDWALK_CHECKPOINT:-$REPO_ROOT/checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000}"
+SERVER_PYTHON="${CLOUDWALK_SERVER_PYTHON:-$REPO_ROOT/../Isaac-GR00T/.venv/bin/python}"
+SERVER_SCRIPT="$REPO_ROOT/../Isaac-GR00T/gr00t/eval/run_gr00t_server.py"
+if [[ ! -x "$SERVER_PYTHON" || ! -f "$SERVER_SCRIPT" ]]; then
+    echo "Isaac-GR00T server environment not found. Set CLOUDWALK_SERVER_PYTHON."
+    exit 1
+fi
+"$REPO_ROOT/.venv_inference/bin/python" "$SCRIPT_DIR/check_cloudwalk_checkpoint.py" "$CHECKPOINT"
+echo "Starting CloudWalk checkpoint: $CHECKPOINT. Simulator uses Dex3."
+echo "Native Inspire FTP hand deployment has not been implemented or validated."
+cd "$REPO_ROOT/../Isaac-GR00T"
+# Version checks are unrelated to inference and can stall startup on WSL when
+# the update endpoint is unreachable.
+export NO_ALBUMENTATIONS_UPDATE=1
+exec "$SERVER_PYTHON" "$SERVER_SCRIPT" --model-path "$CHECKPOINT" \
+    --embodiment-tag UNITREE_G1_SONIC --device cuda:0 --host 127.0.0.1 --port 5550 "$@"
diff --git a/gear_sonic/scripts/summarize_pickup_trial.py b/gear_sonic/scripts/summarize_pickup_trial.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/scripts/summarize_pickup_trial.py
@@ -0,0 +1,71 @@
+"""Evaluate recorded MuJoCo contact/lift evidence; never controls the robot."""
+import argparse
+import json
+from pathlib import Path
+
+
+def summarize(samples, lift_threshold=.12, hold_seconds=3.):
+    if not samples:
+        raise ValueError("No diagnostic samples in the selected interval")
+    longest = 0.
+    held_since = None
+    previous = None
+    for sample in samples:
+        now = sample["monotonic_s"]
+        bodies = {c["hand_body"] for c in sample["contacts"] if c["normal_force_n"] > .01}
+        pinch = any("thumb" in b for b in bodies) and any(
+            "index" in b or "middle" in b for b in bodies)
+        held = sample["bottle_lift_from_initial_m"] >= lift_threshold and pinch
+        if previous is not None and (now - previous["monotonic_s"] > .25 or
+                                     sample["sim_time_s"] < previous["sim_time_s"]):
+            held_since = None
+        if held:
+            if held_since is None:
+                held_since = now
+            longest = max(longest, now - held_since)
+        else:
+            held_since = None
+        previous = sample
+    elapsed = samples[-1]["monotonic_s"] - samples[0]["monotonic_s"]
+    reset = any(b["sim_time_s"] < a["sim_time_s"] for a, b in zip(samples, samples[1:]))
+    return {
+        "samples": len(samples), "duration_s": elapsed,
+        "max_lift_m": max(s["bottle_lift_from_initial_m"] for s in samples),
+        "max_tilt_deg": max(s["bottle_tilt_deg"] for s in samples),
+        "contact_bodies": sorted({c["hand_body"] for s in samples for c in s["contacts"]}),
+        "lift_threshold_m": lift_threshold, "required_hold_s": hold_seconds,
+        "longest_lift_with_opposing_finger_contacts_s": longest,
+        "simulation_reset_detected": reset,
+        "realtime_factor": None if reset or elapsed <= 0 else (
+            samples[-1]["sim_time_s"] - samples[0]["sim_time_s"]) / elapsed,
+        "success": longest >= hold_seconds,
+    }
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("trace", type=Path)
+    parser.add_argument("--actions", type=Path, help="Select last policy-resume interval")
+    parser.add_argument("--output", type=Path)
+    args = parser.parse_args()
+    samples = [json.loads(line) for line in args.trace.read_text().splitlines() if line.strip()]
+    if args.actions:
+        actions = [json.loads(line) for line in args.actions.read_text().splitlines() if line.strip()]
+        published = [a for a in actions if a["event"] == "published"]
+        if not published:
+            raise ValueError("No checkpoint actions published")
+        # Every new trial resets frame numbering; pauses need not reset it.
+        start = max((a["monotonic"] for a in published if a["frame"] == 0),
+                    default=published[0]["monotonic"])
+        end = published[-1]["monotonic"]
+        samples = [s for s in samples if start <= s["monotonic_s"] <= end]
+    report = summarize(samples)
+    text = json.dumps(report, indent=2) + "\n"
+    print(text, end="")
+    if args.output:
+        args.output.parent.mkdir(parents=True, exist_ok=True)
+        args.output.write_text(text)
+
+
+if __name__ == "__main__":
+    main()
diff --git a/gear_sonic/tests/test_action_start.py b/gear_sonic/tests/test_action_start.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_action_start.py
@@ -0,0 +1,19 @@
+"""Cold inference must not skip the approach while the robot holds its pose."""
+import unittest
+
+from gear_sonic.utils.inference.vla_utils import calculate_latency_compensated_index
+
+
+class ActionStartTest(unittest.TestCase):
+    def test_cold_start_preserves_approach(self):
+        self.assertEqual(calculate_latency_compensated_index(1.86, 50, 40, False), 0)
+
+    def test_replan_compensates_motion_already_executing(self):
+        self.assertEqual(calculate_latency_compensated_index(.16, 50, 40, True), 8)
+
+    def test_long_replan_stays_in_horizon(self):
+        self.assertEqual(calculate_latency_compensated_index(1.86, 50, 40, True), 39)
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/gear_sonic/tests/test_arm_tracking.py b/gear_sonic/tests/test_arm_tracking.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_arm_tracking.py
@@ -0,0 +1,69 @@
+"""Arm bias feedforward must improve physical tracking without changing targets."""
+
+from types import SimpleNamespace
+import unittest
+
+import mujoco
+import numpy as np
+
+from gear_sonic.scripts.run_blue_bottle_pickup import load_anchored_scene
+from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
+
+
+class ArmTrackingTest(unittest.TestCase):
+    def hold_pose(self, compensate):
+        # Fix the pelvis only in this isolated tracking test, so balance and
+        # foot movement cannot mask the arm servo error. Production stays free.
+        model = load_anchored_scene()
+        data = mujoco.MjData(model)
+        body = np.array([j for j in range(model.njnt) if any(
+            part in model.joint(j).name for part in ("hip", "knee", "ankle", "waist", "shoulder", "elbow", "wrist"))])
+        arm = np.array([i for i, j in enumerate(body) if any(
+            part in model.joint(int(j)).name for part in ("shoulder", "elbow", "wrist"))])
+        q_target = data.qpos[model.jnt_qposadr[body]].copy()
+        for name, value in (("right_shoulder_pitch_joint", -.1), ("right_elbow_joint", -.2)):
+            q_target[np.flatnonzero(body == model.joint(name).id)[0]] = value
+        arm_kp = .003609725 * (2 * np.pi * 10) ** 2
+        arm_kd = 4 * .003609725 * 2 * np.pi * 10
+        commands = [SimpleNamespace(q=q, dq=0., tau=0., kp=arm_kp if i in arm else 100.,
+                                    kd=arm_kd if i in arm else 4.) for i, q in enumerate(q_target)]
+        env = DefaultEnv.__new__(DefaultEnv)
+        env.config = {"ARM_GRAVITY_COMPENSATION": compensate}
+        env.standby = False
+        env.num_body_dof = len(body)
+        env.body_joint_index = body
+        env.arm_motor_indices = arm
+        env.arm_dof_addresses = model.jnt_dofadr[body[arm]]
+        env.qpos_offset, env.qvel_offset = 7, 6
+        env.mj_model, env.mj_data = model, data
+        env.unitree_bridge = SimpleNamespace(low_cmd_received=True, use_sensor=False,
+            num_body_motor=len(body), low_cmd=SimpleNamespace(motor_cmd=commands))
+        target = mujoco.MjData(model)
+        site = model.site("right_hand_grasp_center").id
+        errors = []
+        mujoco.mj_forward(model, data)
+        for frame in range(3000):
+            data.ctrl[:] = 0.
+            data.ctrl[body - 1] = env.compute_body_torques()
+            data.ctrl[:] = np.clip(data.ctrl, model.actuator_ctrlrange[:, 0], model.actuator_ctrlrange[:, 1])
+            mujoco.mj_step(model, data)
+            if frame >= 2700 and frame % 10 == 0:
+                target.qpos[:] = data.qpos
+                # Measure the arm servo at the same actual waist/base pose;
+                # gravity compensation intentionally does not alter the waist.
+                target.qpos[model.jnt_qposadr[body[arm]]] = q_target[arm]
+                mujoco.mj_forward(model, target)
+                errors.append(np.linalg.norm(target.site_xpos[site] - data.site_xpos[site]))
+        np.testing.assert_array_equal([c.q for c in commands], q_target)
+        return float(np.mean(errors))
+
+    def test_arm_feedforward_reduces_sag_for_identical_sonic_commands(self):
+        baseline = self.hold_pose(False)
+        compensated = self.hold_pose(True)
+        self.assertGreater(baseline, .08)
+        self.assertLess(compensated, .025)
+        self.assertLess(compensated, baseline * .25)
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/gear_sonic/tests/test_assisted_pickup.py b/gear_sonic/tests/test_assisted_pickup.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_assisted_pickup.py
@@ -0,0 +1,93 @@
+"""Physical grasp regression with controlled RGB-D target inputs, without GUI/server."""
+
+from types import SimpleNamespace
+import unittest
+
+import numpy as np
+
+from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
+from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
+
+
+class AssistedPickupTest(unittest.TestCase):
+    def test_free_bottle_lifts_with_small_target_changes_and_reset_clears_target(self):
+        for xy, offset in (([.43, -.11], [0., .03]), ([.4, -.15], [0., .03]),
+                           ([.4007882341, -.1492650940], [0., .03]), ([.46, -.08], [0., .03]),
+                           ([.43, -.11], [.02, 0.]), ([.43, -.11], [0., 0.]), ([.43, -.11], [.02, .06]),
+                           ([.43, -.08], [.02, .03])):
+            with self.subTest(xy=xy):
+                config = SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
+                config.update(GROUND_START=True, ASSISTED_PICKUP=True, FIXED_PICKUP_BASE=True)
+                env = DefaultEnv(config, onscreen=False)
+                env.unitree_bridge = SimpleNamespace(PublishLowState=lambda _: None,
+                    joystick=None, low_cmd=None, low_cmd_received=False)
+                env.bottle_placement.reset(env.mj_model, env.mj_data, xy)
+                for _ in range(100):
+                    env.sim_step()
+                np.testing.assert_allclose(env.coordinate_snapshot()['bottle'][:2], xy, atol=.001)
+                env.begin_control_transition()
+                pickup = env.assisted_pickup
+                pickup.start(env.mj_data)
+                for step in range(6000):
+                    # Controlled perception input isolates contact/control from
+                    # detector uncertainty; separate live trials exercise YOLO.
+                    detection = {'status': 'detected', 'world_point_m': [xy[0]-.025, xy[1], .85],
+                        'camera_position_world_m': [0., xy[1], 1.2], 'capture_monotonic': step // 20}
+                    pickup.update(env.mj_data, detection)
+                    env.sim_step()
+                    if pickup.stage in ('success', 'failed'):
+                        break
+                self.assertTrue(pickup.success, pickup.snapshot())
+                self.assertGreater(pickup.min_hold_lift, .12)
+                self.assertTrue(pickup.hold_contacts)
+                np.testing.assert_array_equal(env.mj_data.xfrc_applied[pickup.bottle], 0.)
+                self.assertNotIn(pickup.bottle, env.mj_model.eq_obj1id)
+                self.assertNotIn(pickup.bottle, env.mj_model.eq_obj2id)
+                destination = (np.array(xy) + offset).tolist()
+                with self.assertRaises(ValueError):
+                    pickup.lower_to_table(env.mj_data, [float('nan'), 0.])
+                self.assertEqual(pickup.stage, 'success')
+                self.assertTrue(pickup.lower_to_table(env.mj_data, destination))
+                self.assertFalse(pickup.lower_to_table(env.mj_data))
+                for _ in range(9000):
+                    pickup.update(env.mj_data, {})
+                    env.sim_step()
+                    if pickup.placed:
+                        self.assertGreater(env.mj_data.xmat[pickup.bottle].reshape(3, 3)[2, 2], .95)
+                    if pickup.stage in ('complete', 'failed'):
+                        break
+                self.assertTrue(pickup.placed, (pickup.snapshot(), env.mj_data.xpos[pickup.bottle].copy(), env.mj_data.xmat[pickup.bottle].reshape(3,3)[2,2]))
+                self.assertEqual(pickup.stage, 'complete', pickup.snapshot())
+                np.testing.assert_allclose(env.mj_data.qpos[pickup.arm_q], pickup.home_arm_q, atol=.05)
+                self.assertEqual(pickup.fraction, 0.)
+                for _ in range(500):
+                    pickup.update(env.mj_data, {})
+                    env.sim_step()
+                self.assertTrue(pickup.table_support(env.mj_data))
+                np.testing.assert_allclose(env.mj_data.xpos[pickup.bottle, :2], destination, atol=.025)
+                self.assertGreater(env.mj_data.xmat[pickup.bottle].reshape(3, 3)[2, 2], .95)
+                # Next Start uses the newly placed bottle, without a scene reset.
+                pickup.start(env.mj_data)
+                for step in range(6000):
+                    detection = {'status': 'detected',
+                        'world_point_m': [destination[0]-.025, destination[1], .85],
+                        'camera_position_world_m': [0., destination[1], 1.2],
+                        'capture_monotonic': step // 20}
+                    pickup.update(env.mj_data, detection)
+                    env.sim_step()
+                    if pickup.stage in ('success', 'failed'):
+                        break
+                self.assertTrue(pickup.success, pickup.snapshot())
+                self.assertGreater(pickup.min_hold_lift, .12)
+                env.reset()
+                self.assertTrue(env.standby)
+                self.assertFalse(pickup.active)
+                self.assertIsNone(pickup.target)
+                self.assertEqual(pickup.samples, [])
+                self.assertEqual(pickup.stage, 'idle')
+                np.testing.assert_allclose(env.coordinate_snapshot()['bottle'], [*xy, .801])
+                np.testing.assert_array_equal(env.mj_data.qvel, 0.)
+
+
+if __name__ == '__main__':
+    unittest.main()
diff --git a/gear_sonic/tests/test_async_camera.py b/gear_sonic/tests/test_async_camera.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_async_camera.py
@@ -0,0 +1,91 @@
+"""Integration check for non-blocking, current-state camera publishing."""
+import socket
+import time
+import unittest
+import zlib
+from pathlib import Path
+
+import msgpack
+import mujoco
+import numpy as np
+import zmq
+
+from gear_sonic.utils.mujoco_sim.async_camera import AsyncCameraProcess
+from gear_sonic.utils.mujoco_sim.sensor_server import ImageMessageSchema
+from gear_sonic.utils.perception.bottle_detector import pixel_depth_to_world
+
+
+class AsyncCameraTest(unittest.TestCase):
+    def test_snapshot_delivery_and_shutdown(self):
+        root = Path(__file__).resolve().parents[2]
+        scene = root / "gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml"
+        model = mujoco.MjModel.from_xml_path(str(scene))
+        data = mujoco.MjData(model)
+        with socket.socket() as reserve:
+            reserve.bind(("127.0.0.1", 0))
+            port = reserve.getsockname()[1]
+        camera = AsyncCameraProcess(scene, {
+            "ego_view": {"height": 480, "width": 640, "mjcf_name": "head_camera"},
+        }, port=port, publish_depth=True)
+        context = zmq.Context()
+        sub = context.socket(zmq.SUB)
+        sub.setsockopt_string(zmq.SUBSCRIBE, "")
+        sub.connect(f"tcp://127.0.0.1:{port}")
+        try:
+            camera.start_process()
+            images = []
+            address = model.joint("red_bottle_free_joint").qposadr[0]
+            for frame, y in enumerate((-.11, .15), start=1):
+                data.qpos[address + 1] = y
+                data.time = float(frame)
+                original_qpos = data.qpos.copy()
+                state = {"body_q": [float(frame)] * 29, "base_quat": [1., 0., 0., 0.]}
+                deadline = time.monotonic() + 10
+                found = None
+                while time.monotonic() < deadline:
+                    camera.submit(data, robot_state=state)
+                    if sub.poll(100):
+                        message = msgpack.unpackb(sub.recv(), raw=False)
+                        if message.get("simulation_time") == frame:
+                            found = message
+                            break
+                self.assertIsNotNone(found, "Missing current snapshot")
+                self.assertLess(time.time() - found["timestamps"]["ego_view"], 2)
+                self.assertLess(time.monotonic() - found["capture_monotonic"], 2)
+                self.assertEqual(found["robot_state"], state)
+                sensor = found["depth_cameras"]["ego_view"]
+                depth = np.frombuffer(zlib.decompress(sensor["depth_zlib"]), dtype="<f2").reshape(sensor["shape"])
+                self.assertEqual(depth.shape, (480, 640))
+                calibration = sensor["calibration"]
+                # A known tabletop point verifies depth registration, camera
+                # axes and world transform independently of detector accuracy.
+                # Keep the sample beyond the robot's hands and away from both
+                # tested bottle poses; nearer tabletop rays are occluded.
+                table = np.array([.6, .30, .7])
+                rotation = np.asarray(calibration["rotation_world_from_camera"])
+                local = rotation.T @ (table - np.asarray(calibration["position_world_m"]))
+                u = calibration["cx"] + calibration["fx"] * local[0] / -local[2]
+                v = calibration["cy"] - calibration["fy"] * local[1] / -local[2]
+                self.assertTrue(0 <= u < 640 and 0 <= v < 480)
+                _, world = pixel_depth_to_world([int(u) + .5, int(v) + .5],
+                                               float(depth[int(v), int(u)]), calibration)
+                self.assertAlmostEqual(world[2], .7, delta=.003)
+                rgb = ImageMessageSchema.deserialize(found).images["ego_view"]
+                self.assertEqual(rgb.shape, (480, 640, 3))
+                self.assertEqual(rgb.dtype, np.uint8)
+                images.append(rgb)
+                np.testing.assert_array_equal(data.qpos, original_qpos)
+            self.assertGreater(np.abs(images[0].astype(float) - images[1]).mean(), .5)
+            start = time.monotonic()
+            for _ in range(100):
+                camera.submit(data)
+            self.assertLess(time.monotonic() - start, .5, "Submitting blocks on rendering")
+        finally:
+            camera.stop()
+            sub.close()
+            context.term()
+        self.assertFalse(camera.process.is_alive())
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/gear_sonic/tests/test_bottle_detection.py b/gear_sonic/tests/test_bottle_detection.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_bottle_detection.py
@@ -0,0 +1,53 @@
+"""Verify depth geometry and suppression of stale/missing detections."""
+
+import time
+import unittest
+
+import numpy as np
+
+from gear_sonic.utils.perception.bottle_detector import (
+    current_detection, estimate_surface_point, pixel_depth_to_world,
+)
+
+
+class BottleDetectionGeometryTest(unittest.TestCase):
+    def setUp(self):
+        self.calibration = {"fx": 100., "fy": 100., "cx": 50., "cy": 50.,
+            "position_world_m": [1., 2., 3.],
+            "rotation_world_from_camera": np.eye(3).tolist()}
+
+    def test_camera_axes_and_world_transform(self):
+        camera, world = pixel_depth_to_world([60., 40.], 2., self.calibration)
+        np.testing.assert_allclose(camera, [.2, .2, -2.])
+        np.testing.assert_allclose(world, [1.2, 2.2, 1.])
+        self.calibration["rotation_world_from_camera"] = [[0, 0, -1], [0, 1, 0], [1, 0, 0]]
+        _, world = pixel_depth_to_world([50., 50.], 2., self.calibration)
+        np.testing.assert_allclose(world, [3., 2., 3.])
+
+    def test_depth_outlier_does_not_move_detected_point(self):
+        depth = np.full((100, 100), 2., dtype=np.float32)
+        depth[50, 50] = np.nan
+        depth[50, 51] = 4.5
+        result = estimate_surface_point([40, 40, 60, 60], depth, self.calibration)
+        np.testing.assert_allclose(result["world_point_m"], [1, 2, 1])
+        self.assertEqual(result["point_kind"], "visible_surface_near_box_center")
+        with self.assertRaises(ValueError):
+            estimate_surface_point([40, 40, 60, 60], depth * 0, self.calibration)
+
+    def test_reset_and_staleness_clear_xyz(self):
+        now = time.monotonic()
+        result = {"status": "detected", "capture_monotonic": now, "world_point_m": [1, 2, 3]}
+        self.assertEqual(current_detection(result)["world_point_m"], [1, 2, 3])
+        self.assertIsNone(current_detection(result, scene_changed_at=now + .1)["world_point_m"])
+        result["capture_monotonic"] = now - 3
+        self.assertIsNone(current_detection(result)["world_point_m"])
+        self.assertIsNone(current_detection(None)["world_point_m"])
+
+    def test_no_detection_never_has_previous_xyz(self):
+        result = {"status": "not_detected", "capture_monotonic": time.monotonic(), "world_point_m": None}
+        self.assertEqual(current_detection(result)["status"], "not_detected")
+        self.assertIsNone(current_detection(result)["world_point_m"])
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/gear_sonic/tests/test_diagnostic_writer.py b/gear_sonic/tests/test_diagnostic_writer.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_diagnostic_writer.py
@@ -0,0 +1,72 @@
+"""Exercise disk limits and stalled/failing storage on the control path."""
+
+import json
+from pathlib import Path
+import tempfile
+from threading import Event
+import time
+import unittest
+from unittest.mock import patch
+
+from gear_sonic.utils.diagnostic_writer import DiagnosticWriter
+
+
+class DiagnosticWriterTest(unittest.TestCase):
+    def test_rotated_trace_stays_bounded_and_latest_survives_shutdown(self):
+        with tempfile.TemporaryDirectory() as directory:
+            trace = Path(directory) / "actions.jsonl"
+            latest = Path(directory) / "latest.json"
+            writer = DiagnosticWriter(trace, latest_path=latest, max_bytes=256)
+            for index in range(80):
+                writer.submit({"index": index, "payload": "test" * 12})
+            self.assertTrue(writer.close())
+            self.assertIsNone(writer.error)
+            files = list(Path(directory).glob("actions.jsonl*"))
+            self.assertEqual(len(files), 2)
+            self.assertLessEqual(sum(p.stat().st_size for p in files), 512)
+            for path in files:
+                for line in path.read_text().splitlines():
+                    json.loads(line)
+            self.assertEqual(json.loads(latest.read_text())["index"], 79)
+            self.assertEqual(json.loads(trace.read_text().splitlines()[-1])["index"], 79)
+            self.assertFalse(writer.submit({"index": 80}))
+
+    def test_stalled_disk_does_not_block_producer_or_grow_backlog(self):
+        entered, release = Event(), Event()
+        original_write = DiagnosticWriter._write_record
+        def stalled_write(writer, stream, line, record):
+            entered.set()
+            release.wait(3.)
+            original_write(writer, stream, line, record)
+        with tempfile.TemporaryDirectory() as directory:
+            trace = Path(directory) / "trace.jsonl"
+            with patch.object(DiagnosticWriter, "_write_record", stalled_write):
+                writer = DiagnosticWriter(trace, queue_size=8)
+                try:
+                    writer.submit({"index": 0})
+                    self.assertTrue(entered.wait(1.))
+                    start = time.monotonic()
+                    for index in range(1, 1001):
+                        writer.submit({"index": index})
+                    self.assertLess(time.monotonic() - start, .1)
+                    self.assertEqual(writer.pending.qsize(), 8)
+                    self.assertGreater(writer.dropped_records, 900)
+                    self.assertFalse(writer.close(timeout=.01))
+                finally:
+                    release.set()
+                    self.assertTrue(writer.close())
+            self.assertEqual(json.loads(trace.read_text().splitlines()[-1])["index"], 1000)
+
+    def test_storage_error_disables_only_diagnostics(self):
+        with tempfile.TemporaryDirectory() as directory:
+            parent = Path(directory) / "file_not_directory"
+            parent.write_text("occupied")
+            writer = DiagnosticWriter(parent / "trace.jsonl")
+            writer.submit({"event": "action"})
+            self.assertTrue(writer.close())
+            self.assertIsNotNone(writer.error)
+            self.assertFalse(writer.submit({"event": "next action"}))
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/gear_sonic/tests/test_inspire_adapter.py b/gear_sonic/tests/test_inspire_adapter.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_inspire_adapter.py
@@ -0,0 +1,26 @@
+"""Checks for the experimental Inspire-to-Dex3 grip adapter."""
+import unittest
+import numpy as np
+from gear_sonic.utils.inference.inspire_adapter import inspire_grip_to_dex3
+
+
+class InspireAdapterTests(unittest.TestCase):
+    def test_grip_endpoints_and_interpolation(self):
+        closed = np.array([0, -.7, -.7, 1, 1.5, 1, 1.5])
+        opened = np.array([0, 0, 0, 0, 0, .9, 0])
+        shut = np.array([1, 1, 1, 1, 1, 1, 0])
+        result = inspire_grip_to_dex3(np.stack([opened, (opened + shut) / 2, shut]), closed)
+        np.testing.assert_allclose(result, np.stack([closed * 0, closed / 2, closed]))
+
+    def test_pad_and_thumb_rotation_do_not_close_fingers(self):
+        closed = np.ones(7)
+        np.testing.assert_array_equal(inspire_grip_to_dex3([0, 0, 0, 0, 0, 1, 1], closed), np.zeros(7))
+
+    def test_reject_invalid_input(self):
+        for hand in (np.zeros(6), np.full(7, np.nan), np.full(7, np.inf)):
+            with self.assertRaises(ValueError):
+                inspire_grip_to_dex3(hand, np.ones(7))
+
+
+if __name__ == '__main__':
+    unittest.main()
diff --git a/gear_sonic/tests/test_observation_freshness.py b/gear_sonic/tests/test_observation_freshness.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_observation_freshness.py
@@ -0,0 +1,74 @@
+"""Post-reset policy inputs must be fresh and paired with their camera state."""
+
+import queue
+import threading
+import time
+import unittest
+
+import numpy as np
+
+from gear_sonic.scripts.run_vla_inference import prepare_observation_from_sensors, _inference_worker_loop
+from gear_sonic.data.robot_model.instantiation.g1 import instantiate_g1_robot_model
+
+
+class ObservationFreshnessTest(unittest.TestCase):
+    def test_reject_old_frame_before_touching_robot_state(self):
+        class Camera:
+            def read(self):
+                return {"capture_monotonic": time.monotonic() - 2.}
+        status = {}
+        self.assertIsNone(prepare_observation_from_sensors(
+            Camera(), None, None, "grab the bottle", minimum_capture_monotonic=0., sensor_status=status))
+        self.assertFalse(status["input_ready"])
+        self.assertIsNone(prepare_observation_from_sensors(
+            Camera(), None, None, "grab the bottle", minimum_capture_monotonic=time.monotonic()))
+
+    def test_fresh_frame_uses_its_state_snapshot(self):
+        robot = instantiate_g1_robot_model(waist_location="lower_and_upper_body")
+        boundary = time.monotonic() - .1
+        class Camera:
+            def read(self):
+                return {"capture_monotonic": time.monotonic(),
+                        "images": {"ego_view": np.zeros((480, 640, 3), dtype=np.uint8)},
+                        "timestamps": {"ego_view": time.time()},
+                        "robot_state": {"body_q": [.1] * 29, "left_hand_q": [0.] * 7,
+                                        "right_hand_q": [0.] * 7, "base_quat": [1., 0., 0., 0.]}}
+        class OldDDS:
+            def get_msg(self):
+                raise AssertionError("Must use the state paired with the new RGB frame")
+        status = {}
+        obs = prepare_observation_from_sensors(Camera(), OldDDS(), robot, "grab the bottle",
+                                              minimum_capture_monotonic=boundary, sensor_status=status)
+        self.assertTrue(status["input_ready"])
+        np.testing.assert_allclose(obs["state"]["right_arm"], .1)
+        np.testing.assert_array_equal(obs["state"]["projected_gravity"], [[[0., 0., -1.]]])
+        self.assertEqual(obs["language"]["annotation.human.task_description"], [["grab the bottle"]])
+
+    def test_inflight_result_keeps_pre_reset_request_boundary(self):
+        requests, results = queue.Queue(), queue.Queue()
+        stop, busy, entered, release = (threading.Event() for _ in range(4))
+        def prepare():
+            entered.set()
+            release.wait(timeout=2)
+            return {"observation": True}
+        thread = threading.Thread(target=_inference_worker_loop,
+            args=(requests, results, stop, busy, prepare, lambda obs: {"action": True}))
+        requested_at = time.monotonic()
+        requests.put(requested_at)
+        thread.start()
+        try:
+            self.assertTrue(entered.wait(timeout=2))
+            reset_boundary = time.monotonic()
+            release.set()
+            _, result_boundary = results.get(timeout=2)
+            self.assertEqual(result_boundary, requested_at)
+            self.assertLess(result_boundary, reset_boundary)
+        finally:
+            stop.set()
+            release.set()
+            thread.join(timeout=2)
+        self.assertFalse(thread.is_alive())
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/gear_sonic/tests/test_palm_grasp.py b/gear_sonic/tests/test_palm_grasp.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_palm_grasp.py
@@ -0,0 +1,184 @@
+"""Validate a fixed grasp region, COM diagnostics, X/Y gates and hand blending."""
+
+from pathlib import Path
+from types import SimpleNamespace
+import time
+import unittest
+
+import mujoco
+import numpy as np
+
+from gear_sonic.utils.inference.proximity_hand import ProximityHandClosure, ready_to_close
+from gear_sonic.utils.mujoco_sim.palm_proximity import (
+    PalmProximity, cylinder_surface_distance,
+)
+from gear_sonic.utils.mujoco_sim.hand_alignment import HandGraspAlignment, cylinder_y_surface_gap
+from gear_sonic.utils.mujoco_sim.interactive_controls import InteractiveSimulationControls
+
+SCENE = Path(__file__).resolve().parents[2] / "gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml"
+
+
+class PalmDistanceTest(unittest.TestCase):
+    def test_distance_is_from_surface_including_cylinder_ends(self):
+        self.assertAlmostEqual(cylinder_surface_distance([.045, 0, 0], .025, .1), .02)
+        self.assertAlmostEqual(cylinder_surface_distance([0, 0, .12], .025, .1), .02)
+        self.assertAlmostEqual(cylinder_surface_distance([.045, 0, .12], .025, .1), np.sqrt(2) * .02)
+        self.assertAlmostEqual(cylinder_surface_distance([0, 0, 0], .025, .1), -.025)
+
+    def test_world_distance_uses_palm_centre_and_bottle_rotation(self):
+        model = mujoco.MjModel.from_xml_path(str(SCENE))
+        data = mujoco.MjData(model)
+        proximity = PalmProximity(model)
+        rotation = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
+        bottle_position = np.array([.43, -.11, .801])
+        data.geom_xmat[proximity.bottle] = rotation.ravel()
+        data.geom_xpos[proximity.bottle] = bottle_position
+        data.geom_xpos[proximity.palm] = bottle_position + rotation @ [.045, 0., 0.]
+        # A wrist position elsewhere cannot affect this clearance.
+        data.xpos[model.body("right_wrist_yaw_link").id] = [3, 4, 5]
+        sample = proximity.measure(data)
+        self.assertAlmostEqual(sample["palm_surface_distance_m"], .02)
+        np.testing.assert_allclose(sample["palm_center_world_m"], [.43, -.065, .801])
+        self.assertAlmostEqual(sample["bottle_tilt_deg"], 0.)
+
+
+class WholeHandAlignmentTest(unittest.TestCase):
+    def test_grasp_reference_is_fixed_in_hand_frame_not_com_or_fingertips(self):
+        model = mujoco.MjModel.from_xml_path(str(SCENE))
+        data = mujoco.MjData(model)
+        alignment = HandGraspAlignment(model)
+        mujoco.mj_forward(model, data)
+        sample = alignment.measure(data)
+        rotation = data.xmat[alignment.root].reshape(3, 3)
+        expected = data.xpos[alignment.root] + rotation @ [.12, .05, 0.]
+        np.testing.assert_allclose(sample["grasp_center_world_m"], expected)
+        self.assertGreater(np.linalg.norm(expected - sample["whole_hand_com_world_m"]), .04)
+        self.assertEqual(model.site_group[alignment.grasp_site], 5)
+        self.assertFalse(mujoco.MjvOption().sitegroup[5], "Marker must be hidden from default policy camera")
+        address = model.joint("red_bottle_free_joint").qposadr[0]
+        data.qpos[address:address + 3] = [expected[0], expected[1] + .044, .801]
+        mujoco.mj_forward(model, data)
+        sample = alignment.measure(data)
+        self.assertTrue(ready_to_close(sample, .02, .005, True, True))
+        com_before = np.asarray(sample["whole_hand_com_world_m"])
+        for name in ("right_hand_middle_0_joint", "right_hand_index_0_joint"):
+            data.qpos[model.joint(name).qposadr[0]] = 1.
+        mujoco.mj_forward(model, data)
+        after = alignment.measure(data)
+        np.testing.assert_allclose(after["grasp_center_world_m"], expected)
+        self.assertGreater(np.linalg.norm(np.asarray(after["whole_hand_com_world_m"]) - com_before), .001)
+        self.assertTrue(ready_to_close(after, .02, .005, True, True))
+        # Wrist rotation must rotate the same reference rather than a world offset.
+        data.qpos[model.joint("right_wrist_yaw_joint").qposadr[0]] = .5
+        mujoco.mj_forward(model, data)
+        expected = data.xpos[alignment.root] + data.xmat[alignment.root].reshape(3, 3) @ [.12, .05, 0.]
+        np.testing.assert_allclose(alignment.measure(data)["grasp_center_world_m"], expected)
+
+    def test_com_includes_palm_and_all_finger_masses_excludes_arm(self):
+        model = mujoco.MjModel.from_xml_path(str(SCENE))
+        data = mujoco.MjData(model)
+        mujoco.mj_forward(model, data)
+        alignment = HandGraspAlignment(model)
+        expected_bodies = [b for b in range(model.nbody)
+                           if model.body(b).name == "right_wrist_yaw_link"
+                           or model.body(b).name.startswith("right_hand_")]
+        self.assertEqual(set(alignment.bodies), set(expected_bodies))
+        self.assertEqual(len(alignment.bodies), 8)
+        expected = sum(model.body_mass[b] * data.xipos[b] for b in expected_bodies) / sum(model.body_mass[b] for b in expected_bodies)
+        before = alignment.measure(data)["whole_hand_com_world_m"]
+        np.testing.assert_allclose(before, expected)
+        np.testing.assert_allclose(before, data.subtree_com[alignment.root])
+        # Moving an arm's inertial position cannot be mistaken for hand COM.
+        data.xipos[model.body("right_elbow_link").id] = [100, 100, 100]
+        np.testing.assert_allclose(alignment.measure(data)["whole_hand_com_world_m"], expected)
+        # Bending a finger moves the whole-hand COM while palm geometry stays fixed.
+        palm = PalmProximity(model)
+        palm_before = data.geom_xpos[palm.palm].copy()
+        for name in ("right_hand_middle_0_joint", "right_hand_index_0_joint"):
+            data.qpos[model.joint(name).qposadr[0]] = 1.
+        mujoco.mj_forward(model, data)
+        np.testing.assert_allclose(data.geom_xpos[palm.palm], palm_before)
+        self.assertGreater(np.linalg.norm(np.asarray(alignment.measure(data)["whole_hand_com_world_m"]) - before), .001)
+
+    def test_y_gap_uses_world_y_surface_and_actual_bottle_profile(self):
+        centre = np.array([.43, -.11, .801])
+        rotation = np.eye(3)
+        gap = lambda point: cylinder_y_surface_gap(point, centre, rotation, .025, .1)
+        self.assertAlmostEqual(gap([.43, -.155, .801]), .02)
+        self.assertAlmostEqual(gap([.43, -.065, .801]), .02)
+        self.assertAlmostEqual(gap([.434, -.155, .801]), .045 - np.sqrt(.025 ** 2 - .004 ** 2))
+        self.assertIsNone(gap([.46, -.155, .801]))
+        self.assertIsNone(gap([.43, -.155, 1.]))
+        self.assertLess(gap(centre), 0.)
+        angle = np.pi / 6
+        tilted = np.array([[1., 0., 0.], [0., np.cos(angle), -np.sin(angle)], [0., np.sin(angle), np.cos(angle)]])
+        self.assertAlmostEqual(cylinder_y_surface_gap([.43, -.155, .801], centre, tilted, .025, .1), .045 - .025 / np.cos(angle))
+
+    def test_both_x_and_y_must_match_with_detection_and_upright_bottle(self):
+        sample = {"x_error_m": .004, "y_surface_gap_m": .019, "bottle_tilt_deg": 0.}
+        self.assertTrue(ready_to_close(sample, .02, .005, True, True))
+        self.assertTrue(ready_to_close({**sample, "x_error_m": -.005, "y_surface_gap_m": .02}, .02, .005, True, True))
+        self.assertFalse(ready_to_close(sample, .02, .005, False, True))
+        self.assertFalse(ready_to_close(sample, .02, .005, True, False))
+        for fields in ({"x_error_m": .0051}, {"x_error_m": np.nan}, {"y_surface_gap_m": .0201},
+                       {"y_surface_gap_m": -.001}, {"y_surface_gap_m": None}, {"bottle_tilt_deg": 31.},
+                       {"y_surface_gap_m": np.nan}, {"x_error_m": .1, "palm_surface_distance_m": .001}):
+            self.assertFalse(ready_to_close({**sample, **fields}, .02, .005, True, True))
+
+
+class HandClosureTest(unittest.TestCase):
+    def test_smooth_close_hold_and_reset(self):
+        closed = np.array([0., -.7, -.7, 1., 1.5, 1., 1.5], dtype=np.float32)
+        closure = ProximityHandClosure(closed, duration=.3)
+        policy = closed * .1
+        original = policy.copy()
+        np.testing.assert_array_equal(closure.apply(policy, 0.)[0], np.zeros(7))
+        closure.activate(policy, 10., .019)
+        closure.activate(closed, 11., 0.)  # Repeated triggers do not restart the blend.
+        blended, fraction = closure.apply(np.zeros(7), 10.15)
+        self.assertAlmostEqual(fraction, .5)
+        np.testing.assert_allclose(blended, (original + closed) / 2., atol=1e-6)
+        np.testing.assert_array_equal(policy, original)
+        np.testing.assert_allclose(closure.apply(np.zeros(7), 12.)[0], closed)
+        closure.reset()
+        np.testing.assert_array_equal(closure.apply(np.zeros(7), 13.)[0], 0.)
+        self.assertIsNone(closure.trigger_distance)
+
+
+class TriggerChannelTest(unittest.TestCase):
+    def test_one_right_hand_request_per_trial_only_while_running(self):
+        sent = []
+        controls = InteractiveSimulationControls.__new__(InteractiveSimulationControls)
+        controls.env = SimpleNamespace(mj_data=None, scene_changed_at=0., config={"SIM_GRASP_DISTANCE": .02})
+        sample = {"x_error_m": .004, "y_surface_gap_m": .019, "bottle_tilt_deg": 0., "distance_source": "MuJoCo"}
+        controls.hand_alignment = SimpleNamespace(measure=lambda _: sample)
+        controls.channel = SimpleNamespace(send=lambda message: sent.append(message) or True)
+        controls.detector_socket = True
+        controls.detector_result = {"status": "detected", "capture_monotonic": time.monotonic()}
+        controls.recognition_scene = 0.
+        controls.client_seen = time.monotonic()
+        controls.pending = None
+        controls.serial = 0
+        controls.grasp_latched = False
+        controls.bottle_seen = False
+        controls.phase = "idle"
+        controls.check_hand_alignment()
+        self.assertEqual(sent, [])
+        self.assertTrue(controls.bottle_seen)
+        controls.phase = "running"
+        sample["x_error_m"] = .008
+        controls.check_hand_alignment()
+        self.assertEqual(sent, [])
+        sample["x_error_m"] = .004
+        controls.check_hand_alignment()
+        self.assertEqual(sent, [{"command": "close_right_hand", "id": 1, "source": "MuJoCo", **sample}])
+        controls.pending = None
+        controls.check_hand_alignment()
+        self.assertEqual(len(sent), 1)
+        controls.env.scene_changed_at = time.monotonic() + 1.
+        controls.check_hand_alignment()
+        self.assertFalse(controls.bottle_seen)
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/gear_sonic/tests/test_sim_grasp_defaults.py b/gear_sonic/tests/test_sim_grasp_defaults.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_sim_grasp_defaults.py
@@ -0,0 +1,37 @@
+"""The normal simulation command enables grasp-centre gating; hardware stays unchanged."""
+
+import unittest
+
+import tyro
+
+from gear_sonic.scripts.launch_inference import InferenceLaunchConfig, _resolve_sim_grasp_config
+
+
+class SimGraspDefaultsTest(unittest.TestCase):
+    def parse(self, args):
+        config = tyro.cli(InferenceLaunchConfig, args=args)
+        _resolve_sim_grasp_config(config)
+        return config
+
+    def test_user_simulation_command_enables_grasp_centre_gate(self):
+        config = self.parse(["--sim", "--policy-host", "127.0.0.1", "--policy-port", "5550",
+                             "--no-data-exporter", "--inspire-ftp-hands", "--prompt", "grab the bottle"])
+        self.assertEqual(config.sim_grasp_distance, .02)
+        self.assertEqual(config.sim_grasp_x_tolerance, .005)
+
+    def test_explicit_checkpoint_only_hand_control_is_preserved(self):
+        self.assertEqual(self.parse(["--sim", "--sim-grasp-distance", "0"]).sim_grasp_distance, 0.)
+
+    def test_assisted_command_owns_closure_and_parses_bottle_xy(self):
+        config = self.parse(['--sim', '--sim-assisted-pickup', '--sim-fixed-base', '--sim-bottle-xy', '.40', '-.15'])
+        self.assertTrue(config.sim_fixed_base)
+        self.assertEqual(config.sim_grasp_distance, 0.)
+        self.assertEqual(config.sim_bottle_xy, (.40, -.15))
+
+    def test_hardware_and_disabled_detector_have_no_com_override(self):
+        self.assertEqual(self.parse([]).sim_grasp_distance, 0.)
+        self.assertEqual(self.parse(["--sim", "--no-bottle-detection"]).sim_grasp_distance, 0.)
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/gear_sonic/tests/test_simulation_controls.py b/gear_sonic/tests/test_simulation_controls.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_simulation_controls.py
@@ -0,0 +1,212 @@
+"""Verify scene edits, ground standby, and reset sequencing without a display."""
+
+from pathlib import Path
+from types import SimpleNamespace
+import time
+import unittest
+
+import mujoco
+import numpy as np
+
+from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
+from gear_sonic.utils.mujoco_sim.configs import SimLoopConfig
+from gear_sonic.utils.mujoco_sim.object_reset import BottlePlacement
+from gear_sonic.utils.mujoco_sim.interactive_controls import InteractiveSimulationControls
+
+
+SCENE = Path(__file__).resolve().parents[2] / "gear_sonic/data/robot_model/model_data/g1/scene_43dof.xml"
+
+
+class BottlePlacementTest(unittest.TestCase):
+    def setUp(self):
+        self.model = mujoco.MjModel.from_xml_path(str(SCENE))
+        self.data = mujoco.MjData(self.model)
+        mujoco.mj_forward(self.model, self.data)
+        self.placement = BottlePlacement(self.model, self.data)
+
+    def test_place_and_reset_preserve_robot_and_time(self):
+        self.data.time = 123.
+        self.data.qpos[0] = .02
+        self.data.qvel[0] = .2
+        robot_q = self.data.qpos[:self.placement.address].copy()
+        self.placement.reset(self.model, self.data, [.4, -.15])
+        self.data.qpos[self.placement.address + 3:self.placement.address + 7] = [0, 1, 0, 0]
+        dof = self.model.joint("red_bottle_free_joint").dofadr[0]
+        self.data.qvel[dof:dof + 6] = 1
+        self.placement.reset(self.model, self.data)
+        np.testing.assert_array_equal(self.data.qpos[:self.placement.address], robot_q)
+        self.assertEqual(self.data.time, 123.)
+        self.assertEqual(self.data.qvel[0], .2)
+        np.testing.assert_array_equal(self.data.qvel[dof:dof + 6], 0)
+        np.testing.assert_allclose(self.data.qpos[self.placement.address:self.placement.address + 7],
+                                   [.4, -.15, .801, 1, 0, 0, 0])
+
+    def test_invalid_xy_does_not_move_scene(self):
+        original = self.data.qpos.copy()
+        for xy in ([np.nan, 0], [np.inf, 0], [.1, 0], [.5, .5], [1, 2, 3]):
+            with self.assertRaises(ValueError):
+                self.placement.reset(self.model, self.data, xy)
+            np.testing.assert_array_equal(self.data.qpos, original)
+        np.testing.assert_array_equal(self.placement.xy, [.43, -.11])
+
+
+class GroundStandbyTest(unittest.TestCase):
+    def setUp(self):
+        config = SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
+        config["GROUND_START"] = True
+        self.env = DefaultEnv(config, onscreen=False)
+        self.env.unitree_bridge = SimpleNamespace(PublishLowState=lambda obs: None, joystick=None)
+
+    def test_idle_robot_has_floor_contacts_without_lifting(self):
+        for _ in range(1000):
+            self.env.sim_step()
+        self.assertTrue(self.env.standby)
+        self.assertLess(abs(self.env.mj_data.qpos[2] - .793), .02)
+        self.assertLess(np.linalg.norm(self.env.mj_data.qvel[:6]), .02)
+        model, data = self.env.mj_model, self.env.mj_data
+        floor = model.geom("floor").id
+        foot_contacts = 0
+        for contact in data.contact:
+            other = contact.geom2 if contact.geom1 == floor else contact.geom1 if contact.geom2 == floor else None
+            if other is not None and "ankle" in model.body(int(model.geom_bodyid[other])).name:
+                foot_contacts += 1
+        self.assertGreater(foot_contacts, 0)
+        positions, velocities, _ = self.env._idle_robot_indices
+        np.testing.assert_array_equal(data.qpos[positions], self.env.initial_qpos[positions])
+        np.testing.assert_array_equal(data.qvel[velocities], 0.)
+        self.assertLess(data.xpos[model.body('red_bottle').id, 2], .801)
+
+    def test_lock_ignores_robot_disturbance_and_preserves_bottle_velocity(self):
+        env = self.env
+        env.hold_initial_robot_pose()
+        positions, velocities, _ = env._idle_robot_indices
+        env.mj_data.qpos[0] = .3
+        env.mj_data.qvel[velocities] = 2.
+        bottle_v = int(env.mj_model.joint('red_bottle_free_joint').dofadr[0])
+        env.mj_data.qvel[bottle_v] = .1
+        env.hold_initial_robot_pose()
+        np.testing.assert_array_equal(env.mj_data.qpos[positions], env.initial_qpos[positions])
+        np.testing.assert_array_equal(env.mj_data.qvel[velocities], 0.)
+        self.assertEqual(env.mj_data.qvel[bottle_v], .1)
+        env.begin_control_transition()
+        self.assertFalse(env.standby)
+        env.mj_data.qpos[0] = .2
+        env.hold_initial_robot_pose()
+        self.assertEqual(env.mj_data.qpos[0], .2)
+
+    def test_startup_torque_transfer_has_smooth_endpoints_and_reset_clears_it(self):
+        env = self.env
+        env.begin_control_transition()
+        body, hands = np.full(29, 4.), np.full(14, 2.)
+        initial, _ = env.blend_startup_torques(body, hands)
+        env.mj_data.time = 1.
+        middle, _ = env.blend_startup_torques(body, hands)
+        np.testing.assert_allclose(middle, .5 * (initial + body))
+        env.mj_data.time = 2.
+        final, fingers = env.blend_startup_torques(body, hands)
+        np.testing.assert_array_equal(final, body)
+        np.testing.assert_array_equal(fingers, hands)
+        self.assertIsNone(env._control_transition_started)
+        env.begin_control_transition()
+        env.reset()
+        self.assertIsNone(env._control_transition_started)
+        self.assertTrue(env.standby)
+
+    def test_robot_reset_restores_ground_and_selected_bottle(self):
+        self.env.bottle_placement.reset(self.env.mj_model, self.env.mj_data, [.4, -.15])
+        self.env.standby = False
+        self.env.release_ground_support()
+        self.env.mj_data.qpos[:3] = [1, 1, .3]
+        self.env.mj_data.qvel[:] = 3
+        self.env.reset()
+        self.assertTrue(self.env.standby)
+        self.assertTrue(self.env.elastic_band.enable)
+        np.testing.assert_array_equal(self.env.mj_data.qpos[:7], self.env.mj_model.qpos0[:7])
+        np.testing.assert_array_equal(self.env.mj_data.qvel, 0)
+        np.testing.assert_allclose(self.env.coordinate_snapshot()["bottle"], [.4, -.15, .801])
+
+    def test_initial_bottle_xy_is_used_by_reset_and_panel_state(self):
+        config = SimLoopConfig(enable_onscreen=False).load_wbc_yaml()
+        config.update(GROUND_START=True, BOTTLE_XY=(.4, -.15))
+        env = DefaultEnv(config, onscreen=False)
+        np.testing.assert_allclose(env.bottle_placement.xy, [.4, -.15])
+        np.testing.assert_allclose(env.coordinate_snapshot()['bottle'], [.4, -.15, .801])
+        env.reset()
+        np.testing.assert_allclose(env.coordinate_snapshot()['bottle'], [.4, -.15, .801])
+
+    def test_start_after_complete_restarts_pickup_without_resetting_scene(self):
+        from unittest.mock import Mock
+        pickup = SimpleNamespace(active=True, stage='complete', start=Mock())
+        self.env.assisted_pickup = pickup
+        controls = InteractiveSimulationControls.__new__(InteractiveSimulationControls)
+        controls.env = self.env
+        controls.phase = 'running'
+        controls.pending = None
+        controls.client_seen = time.monotonic()
+        controls.detector_result = {'status': 'detected'}
+        self.env.bottle_placement.reset(self.env.mj_model, self.env.mj_data, [.45, -.08])
+        before = self.env.mj_data.qpos.copy()
+        self.assertTrue(controls.can_repeat_pickup())
+        controls.handle({'command': 'start'})
+        pickup.start.assert_called_once_with(self.env.mj_data)
+        np.testing.assert_array_equal(self.env.mj_data.qpos, before)
+        self.assertEqual(controls.phase, 'running')
+        self.assertIsNone(controls.detector_result)
+        self.assertFalse(controls.bottle_seen)
+        pickup.stage = 'detecting'
+        self.assertFalse(controls.can_repeat_pickup())
+        controls.handle({'command': 'start'})
+        self.assertEqual(pickup.start.call_count, 1)
+
+    def test_reset_waits_for_policy_ack_and_ignores_old_ack(self):
+        messages = []
+        class Channel:
+            def send(self, message):
+                messages.append(message)
+                return True
+            def receive(self):
+                return acknowledgements.pop(0) if acknowledgements else None
+        controls = InteractiveSimulationControls.__new__(InteractiveSimulationControls)
+        controls.env = self.env
+        controls.channel = Channel()
+        controls.controller_state = SimpleNamespace(get_msg=lambda: None)
+        controls.controller_seen = 0.
+        controls.client_seen = time.monotonic()
+        controls.client_status = {"paused": False}
+        controls.pending = None
+        controls.serial = 0
+        controls.phase = "running"
+        controls.phase_since = time.monotonic()
+        controls.error = ""
+        controls.panel = None
+        controls.detector_socket = None
+        controls.detector_result = None
+        controls.last_ui_update = time.monotonic()
+        self.env.mj_data.qpos[0] = .12
+        controls.handle({"command": "reset"})
+        self.assertEqual(controls.phase, "resetting")
+        self.assertEqual(self.env.mj_data.qpos[0], .12)
+        self.assertEqual(messages[-1]["command"], "pause")
+        acknowledgements = [{"type": "ack", "id": 0, "ok": True}]
+        controls.poll()
+        self.assertEqual(self.env.mj_data.qpos[0], .12)
+        acknowledgements.append({"type": "ack", "id": 1, "ok": True})
+        controls.poll()
+        self.assertEqual(controls.phase, "idle")
+        self.assertEqual(self.env.mj_data.qpos[0], 0.)
+        # Reset must also supersede a Start still waiting for its prepare ACK.
+        controls.pending = ({'command': 'prepare', 'id': 99}, time.monotonic())
+        controls.phase = 'preparing'
+        self.env.standby = False
+        controls.handle({'command': 'reset'})
+        self.assertTrue(self.env.standby)
+        self.assertEqual(controls.phase, 'resetting')
+        self.assertEqual(messages[-1]['command'], 'pause')
+        acknowledgements.extend([{'type': 'ack', 'id': 99, 'ok': True},
+                                 {'type': 'ack', 'id': messages[-1]['id'], 'ok': True}])
+        controls.poll()
+        self.assertEqual(controls.phase, 'idle')
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/gear_sonic/tests/test_viewer_overlay.py b/gear_sonic/tests/test_viewer_overlay.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/tests/test_viewer_overlay.py
@@ -0,0 +1,165 @@
+"""Check the native renderer font contract and visible detector status."""
+
+import base64
+from types import SimpleNamespace
+from threading import Event
+import time
+import unittest
+
+import mujoco
+import numpy as np
+
+from gear_sonic.utils.mujoco_sim.base_sim import DefaultEnv
+from gear_sonic.utils.mujoco_sim.viewer_overlay import ViewerOverlayWorker
+
+
+class ViewerOverlayTest(unittest.TestCase):
+    def test_live_camera_updates_without_detector_results(self):
+        import msgpack
+        import zmq
+        from gear_sonic.utils.mujoco_sim.sensor_server import ImageMessageSchema
+        context = zmq.Context()
+        publisher = context.socket(zmq.PUB)
+        port = publisher.bind_to_random_port('tcp://127.0.0.1')
+        displayed = Event()
+        frames = []
+        def show(images):
+            frames.append(images[0][1].copy())
+            displayed.set()
+        viewer = SimpleNamespace(is_running=lambda: True, viewport=mujoco.MjrRect(0, 0, 800, 600),
+            set_texts=lambda _: None, clear_images=lambda: None, set_images=show)
+        worker = ViewerOverlayWorker(viewer)
+        worker.camera_port = port
+        try:
+            for value in (40, 180):
+                deadline = time.monotonic() + 2.
+                while time.monotonic() < deadline:
+                    packet = ImageMessageSchema(timestamps={'ego_view': time.time()},
+                        images={'ego_view': np.full((240, 320, 3), value, dtype=np.uint8)}).serialize()
+                    packet['capture_monotonic'] = time.monotonic()
+                    publisher.send(msgpack.packb(packet))
+                    displayed.wait(.05)
+                    displayed.clear()
+                    if frames and abs(float(frames[-1][150:, :, :].mean())-value) < 3:
+                        break
+                else:
+                    self.fail('Live preview did not update independently of YOLO')
+        finally:
+            worker.close()
+            publisher.close(linger=0)
+            context.term()
+
+    def test_detection_box_scales_and_expires(self):
+        from gear_sonic.utils.mujoco_sim.viewer_overlay import draw_detection
+        detection = {'status': 'detected', 'capture_monotonic': 10.,
+            'image_shape': [480, 640], 'bbox_xyxy': [200, 200, 400, 400], 'confidence': .8}
+        frame = np.zeros((240, 320, 3), dtype=np.uint8)
+        draw_detection(frame, detection, 10.5)
+        np.testing.assert_array_equal(frame[100, 100], [0, 255, 0])
+        stale = np.zeros_like(frame)
+        draw_detection(stale, detection, 10.8)
+        self.assertFalse(stale[80:].any())
+
+    def preview_detection(self):
+        import cv2
+        ok, encoded = cv2.imencode(".png", np.zeros((240, 320, 3), dtype=np.uint8))
+        self.assertTrue(ok)
+        return {"preview_png": base64.b64encode(encoded).decode(), "capture_monotonic": 1.}
+
+    def test_preview_resumes_when_viewport_becomes_available(self):
+        first, displayed = Event(), Event()
+        viewer = SimpleNamespace(is_running=lambda: True, viewport=None,
+            set_texts=lambda _: first.set(), clear_images=lambda: None,
+            set_images=lambda _: displayed.set())
+        worker = ViewerOverlayWorker(viewer)
+        try:
+            detection = self.preview_detection()
+            worker.submit([], detection)
+            self.assertTrue(first.wait(1.))
+            self.assertFalse(displayed.wait(.2))
+            self.assertTrue(worker.thread.is_alive())
+            viewer.viewport = mujoco.MjrRect(0, 0, 800, 600)
+            worker.submit([], detection)
+            self.assertTrue(displayed.wait(1.))
+        finally:
+            worker.close()
+
+    def test_viewer_can_close_during_overlay_submission(self):
+        entered, displayed = Event(), Event()
+        viewer = SimpleNamespace(running=True, viewport=mujoco.MjrRect(0, 0, 800, 600),
+                                 clear_images=lambda: None, set_images=lambda _: displayed.set())
+        viewer.is_running = lambda: viewer.running
+        def close_while_setting_texts(_):
+            viewer.viewport = None
+            viewer.running = False
+            entered.set()
+        viewer.set_texts = close_while_setting_texts
+        worker = ViewerOverlayWorker(viewer)
+        try:
+            worker.submit([], self.preview_detection())
+            self.assertTrue(entered.wait(1.))
+            worker.thread.join(timeout=1.)
+            self.assertFalse(worker.thread.is_alive())
+            self.assertFalse(displayed.is_set())
+        finally:
+            worker.close()
+
+    def test_slow_native_overlay_never_blocks_physics_submissions(self):
+        entered, release = Event(), Event()
+        def slow_set_texts(texts):
+            entered.set()
+            release.wait(2.)
+        viewer = SimpleNamespace(is_running=lambda: True, set_texts=slow_set_texts,
+                                 clear_images=lambda: None)
+        worker = ViewerOverlayWorker(viewer)
+        try:
+            worker.submit([], {})
+            self.assertTrue(entered.wait(1.))
+            start = time.monotonic()
+            for _ in range(100):
+                worker.submit([], {})
+            self.assertLess(time.monotonic() - start, .1)
+            self.assertEqual(worker.pending.qsize(), 1)
+        finally:
+            release.set()
+            worker.close()
+
+    def test_native_font_and_prominent_detector_coordinates(self):
+        texts = []
+        env = DefaultEnv.__new__(DefaultEnv)
+        env.config = {}
+        env.viewer = SimpleNamespace(set_texts=lambda value: texts.extend(value),
+                                     clear_images=lambda: None, sync=lambda: None)
+        env.coordinate_snapshot = lambda: {"bottle": [.43, -.11, .8],
+                                           "right_wrist": [.2, -.2, .8], "right_grasp_center": [.43, -.156, .8]}
+        env.ui_snapshot = {"detection": {"world_point_m": [.407, -.102, .872], "confidence": .85},
+            "hand_alignment": {"grasp_center_world_m": [.43, -.156, .8], "y_surface_gap_m": .021, "x_error_m": .001},
+            "grasp_threshold_m": .02, "grasp_x_tolerance_m": .005, "grasp_status": "Waiting for Y gap <= 2.0 cm"}
+        env.elastic_band = None
+        env.detection_preview = None
+        env._viewer_overlay_worker = None
+        env.update_viewer()
+        # mjr_overlay indexes its font tables using mjtFont, NOT mjtFontScale.
+        valid = {int(value) for value in mujoco.mjtFont.__members__.values()}
+        self.assertTrue(all(int(font) in valid for font, *_ in texts))
+        detector = next(row for row in texts if "DETECTED BOTTLE" in row[2])
+        self.assertEqual(detector[0], mujoco.mjtFont.mjFONT_BIG)
+        for coordinate in ("+0.407", "-0.102", "+0.872"):
+            self.assertIn(coordinate, detector[2])
+        grasp = next(row for row in texts if "GRASP CENTRE - X/Y" in row[2])
+        self.assertEqual(grasp[1], mujoco.mjtGridPos.mjGRID_BOTTOMRIGHT)
+        self.assertIn("Y gap 2.10 cm | target 2.0", grasp[2])
+        self.assertIn("X error +0.10 cm | tol 0.5", grasp[2])
+        world_labels = next(row[2] for row in texts if "WORLD XYZ" in row[2])
+        self.assertIn("Right wrist origin", world_labels)
+        self.assertLess(world_labels.index("Hand grasp centre"), world_labels.index("Right wrist origin"))
+        texts.clear()
+        env.ui_snapshot = {"detection": {"world_point_m": None, "status": "not_detected"}}
+        env.update_viewer()
+        detector = next(row for row in texts if "DETECTED BOTTLE" in row[2])
+        self.assertIn("not_detected", detector[2])
+        self.assertNotIn("+0.407", detector[2])
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/gear_sonic/utils/diagnostic_writer.py b/gear_sonic/utils/diagnostic_writer.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/utils/diagnostic_writer.py
@@ -0,0 +1,106 @@
+"""Bounded diagnostic traces without disk I/O on control/physics threads."""
+
+import json
+from pathlib import Path
+from queue import Empty, Full, Queue
+import sys
+from threading import Event, Lock, Thread
+import time
+
+
+class DiagnosticWriter:
+    """Write JSONL on a worker, retaining one backup and optional latest JSON.
+
+    Submission never waits for storage. If storage cannot keep up, discard the
+    oldest pending records. Callers must not mutate a record after submitting it.
+    These traces are diagnostics, not a lossless data collection interface.
+    """
+
+    def __init__(self, path, *, latest_path=None, max_bytes=32 * 1024 * 1024,
+                 queue_size=128):
+        if max_bytes < 1 or queue_size < 1:
+            raise ValueError("Diagnostic size limits must be positive")
+        self.path = Path(path)
+        self.latest_path = Path(latest_path) if latest_path else None
+        self.max_bytes = max_bytes
+        self.pending = Queue(maxsize=queue_size)
+        self.dropped_records = 0
+        self.written_records = 0
+        self.error = None
+        self._closing = Event()
+        self._submit_lock = Lock()
+        self._thread = Thread(target=self._run, name="diagnostic-writer", daemon=True)
+        self._thread.start()
+
+    def submit(self, record):
+        with self._submit_lock:
+            if self._closing.is_set():
+                return False
+            try:
+                self.pending.put_nowait(record)
+            except Full:
+                try:
+                    self.pending.get_nowait()
+                    self.dropped_records += 1
+                except Empty:
+                    pass
+                self.pending.put_nowait(record)
+            return True
+
+    def close(self, timeout=2.):
+        with self._submit_lock:
+            self._closing.set()
+        self._thread.join(timeout)
+        return not self._thread.is_alive()
+
+    def _run(self):
+        stream = None
+        try:
+            self.path.parent.mkdir(parents=True, exist_ok=True)
+            size = self.path.stat().st_size if self.path.exists() else 0
+            # A trace from an older unlimited logger must not become a huge
+            # backup when this bounded writer takes over.
+            if size > self.max_bytes:
+                self.path.unlink()
+                size = 0
+            backup = self.path.with_name(self.path.name + ".1")
+            if backup.exists() and backup.stat().st_size > self.max_bytes:
+                backup.unlink()
+            stream = self.path.open("ab")
+            last_flush = time.monotonic()
+            while not self._closing.is_set() or not self.pending.empty():
+                try:
+                    record = self.pending.get(timeout=.1)
+                except Empty:
+                    stream.flush()
+                    continue
+                line = (json.dumps(record) + "\n").encode("utf-8")
+                if len(line) > self.max_bytes:
+                    self.dropped_records += 1
+                    continue
+                if size + len(line) > self.max_bytes:
+                    stream.close()
+                    self.path.replace(backup)
+                    stream = self.path.open("wb")
+                    size = 0
+                self._write_record(stream, line, record)
+                size += len(line)
+                self.written_records += 1
+                if time.monotonic() - last_flush >= .5:
+                    stream.flush()
+                    last_flush = time.monotonic()
+        except (OSError, TypeError, ValueError) as exc:
+            self.error = str(exc)
+            self._closing.set()
+            print(f"[Diagnostics] Recording disabled for {self.path}: {exc}", file=sys.stderr)
+        finally:
+            if stream is not None:
+                stream.close()
+
+    def _write_record(self, stream, line, record):
+        stream.write(line)
+        if self.latest_path is not None:
+            self.latest_path.parent.mkdir(parents=True, exist_ok=True)
+            temporary = self.latest_path.with_suffix(self.latest_path.suffix + ".tmp")
+            temporary.write_text(json.dumps(record, indent=2))
+            temporary.replace(self.latest_path)
diff --git a/gear_sonic/utils/inference/inspire_adapter.py b/gear_sonic/utils/inference/inspire_adapter.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/utils/inference/inspire_adapter.py
@@ -0,0 +1,16 @@
+"""Experimental Inspire FTP grip-to-Dex3 adapter for simulation.
+
+Source: https://huggingface.co/datasets/cloudwalk-research/gr00t-g1-grab-bottle-right-hand-v2
+The source describes hand vectors whose sum is 0.9 open and 6.0 closed.
+The first five channels range 0..1, channel 5 ranges .9..1, and channel 6
+is a grip pad. This preserves grip intent, not Inspire finger kinematics.
+"""
+import numpy as np
+
+
+def inspire_grip_to_dex3(hand, closed_pose):
+    hand = np.asarray(hand, dtype=np.float32)
+    if hand.shape[-1] != 7 or not np.isfinite(hand).all():
+        raise ValueError("Expected finite Inspire hand vectors with seven channels")
+    grip = np.clip(hand[..., :5].mean(axis=-1, keepdims=True), 0.0, 1.0)
+    return grip * np.asarray(closed_pose, dtype=np.float32)
diff --git a/gear_sonic/utils/inference/proximity_hand.py b/gear_sonic/utils/inference/proximity_hand.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/utils/inference/proximity_hand.py
@@ -0,0 +1,48 @@
+"""Optional simulation hand closure; body motion stays with GR00T/SONIC."""
+
+import numpy as np
+
+
+def ready_to_close(sample, y_threshold, x_tolerance, running, bottle_seen):
+    """Both world-X alignment and nonnegative world-Y surface clearance must hold."""
+    error = sample.get("x_error_m")
+    gap = sample.get("y_surface_gap_m")
+    return bool(running and bottle_seen and error is not None and gap is not None
+                and np.isfinite(error) and np.isfinite(gap)
+                and abs(error) <= x_tolerance + 1e-9
+                and -1e-9 <= gap <= y_threshold + 1e-9
+                and sample.get("bottle_tilt_deg", 180.) < 30.)
+
+
+class ProximityHandClosure:
+    def __init__(self, closed_pose, duration=.3):
+        self.closed_pose = np.asarray(closed_pose, dtype=np.float32)
+        if (self.closed_pose.shape != (7,) or not np.isfinite(self.closed_pose).all()
+                or not np.isfinite(duration) or duration <= 0):
+            raise ValueError("Expected a finite seven-joint pose and positive closure duration")
+        self.duration = duration
+        self.reset()
+
+    def reset(self):
+        self.started = None
+        self.start_pose = None
+        self.trigger_distance = None
+        self.trigger_x_error = None
+
+    def activate(self, current_pose, now, distance, x_error=None):
+        if self.started is not None:
+            return
+        self.start_pose = np.asarray(current_pose, dtype=np.float32).copy()
+        if self.start_pose.shape != (7,) or not np.isfinite(self.start_pose).all():
+            raise ValueError("Invalid current hand pose")
+        self.started = now
+        self.trigger_distance = distance
+        self.trigger_x_error = x_error
+
+    def apply(self, policy_pose, now):
+        if self.started is None:
+            # In this opt-in mode closure must start at the distance trigger,
+            # even when a policy chunk would close the fingers earlier.
+            return np.zeros(7, dtype=np.float32), None
+        fraction = float(np.clip((now - self.started) / self.duration, 0., 1.))
+        return (self.start_pose + fraction * (self.closed_pose - self.start_pose)), fraction
diff --git a/gear_sonic/utils/inference/simulation_controls.py b/gear_sonic/utils/inference/simulation_controls.py
new file mode 100644
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
diff --git a/gear_sonic/utils/mujoco_sim/assisted_pickup.py b/gear_sonic/utils/mujoco_sim/assisted_pickup.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/assisted_pickup.py
@@ -0,0 +1,352 @@
+"""Opt-in visual pickup correction for the simulated right arm and Dex3 hand.
+
+SONIC retains the floating base, legs and left arm. This controller only
+sets joint torques; it never attaches, teleports or applies a force to the bottle.
+Target XY comes from RGB-D recognition plus the known bottle radius/table height.
+MuJoCo object pose/contact is used only to measure the outcome.
+"""
+
+import mujoco
+import numpy as np
+from scipy.spatial.transform import Rotation
+from scipy.optimize import least_squares
+
+
+def visual_bottle_center(detection, radius, centre_height):
+    if detection.get("status") != "detected":
+        return None
+    point = np.asarray(detection.get("world_point_m"), dtype=float)
+    camera = np.asarray(detection.get("camera_position_world_m"), dtype=float)
+    if point.shape != (3,) or camera.shape != (3,) or not np.isfinite([point, camera]).all():
+        return None
+    # A box-centre depth point lies on the near cylindrical surface. Correct
+    # horizontally to its axis; Z comes from the known tabletop and bottle size.
+    if not centre_height - .07 < point[2] < centre_height + .095:
+        return None
+    direction = point[:2] - camera[:2]
+    length = np.linalg.norm(direction)
+    if length < .05:
+        return None
+    return np.r_[point[:2] + radius * direction / length, centre_height]
+
+
+class AssistedPickup:
+    def __init__(self, model):
+        self.model = m = model
+        self.arm = np.array([m.joint('waist_pitch_joint').id] + [m.joint('right_' + name + '_joint').id for name in
+            ('shoulder_pitch', 'shoulder_roll', 'shoulder_yaw', 'elbow',
+             'wrist_roll', 'wrist_pitch', 'wrist_yaw')])
+        self.hand = np.array([m.joint('right_hand_' + name + '_joint').id for name in
+            ('thumb_0', 'thumb_1', 'thumb_2', 'middle_0', 'middle_1', 'index_0', 'index_1')])
+        self.arm_q, self.arm_v = m.jnt_qposadr[self.arm], m.jnt_dofadr[self.arm]
+        self.hand_q, self.hand_v = m.jnt_qposadr[self.hand], m.jnt_dofadr[self.hand]
+        self.site = m.site('right_hand_grasp_center').id
+        self.wrist = m.body('right_wrist_yaw_link').id
+        self.bottle = m.body('red_bottle').id
+        self.geom = m.geom('red_bottle_body').id
+        self.radius, self.half_height = m.geom_size[self.geom, :2]
+        self.centre_height = float(m.body_pos[self.bottle, 2])
+        self.scratch = mujoco.MjData(m)
+        self.jp, self.jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
+        self.closed = np.array([0., -.7, -.7, 1., 1.5, 1., 1.5])
+        self.lower = m.jnt_range[self.arm, 0].copy() + .002
+        self.upper = m.jnt_range[self.arm, 1].copy() - .002
+        # Keep the right upper arm outside the torso. The redundant 8-DOF IK
+        # otherwise changes elbow branches for millimetre-scale RGB-D noise.
+        self.lower[0], self.upper[0] = 0., min(self.upper[0], .5)
+        self.upper[2] = min(self.upper[2], -.05)
+        self.lower[3], self.upper[3] = max(self.lower[3], -.6), min(self.upper[3], .6)
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
+        self.fraction = 0.
+        self.placed = False
+        self.place_xy = None
+
+    def lower_to_table(self, data, xy=None):
+        if not self.active or self.stage != 'success':
+            return False
+        from .object_reset import BottlePlacement
+        destination = BottlePlacement(self.model, data).validate(self.target[:2] if xy is None else xy)
+        shift = np.r_[destination - self.target[:2], 0.]
+        self.place_low_q = self.table_arm_q.copy()
+        self.place_high_q = self.arm_target.copy()
+        if np.linalg.norm(shift) > .001:
+            # Solve both endpoints before moving; reject unreachable destinations.
+            targets = []
+            for endpoint, seed in enumerate((self.table_arm_q, self.arm_target)):
+                scratch = self.scratch
+                scratch.qpos[:] = data.qpos
+                scratch.qpos[self.arm_q] = seed
+                mujoco.mj_kinematics(self.model, scratch)
+                position = scratch.site_xpos[self.site].copy() + shift
+                if endpoint == 0:
+                    position[2] -= .006  # Contact stops descent before this small support margin.
+                rotation = scratch.xmat[self.wrist].reshape(3, 3).copy()
+                def residual(q):
+                    scratch.qpos[self.arm_q] = q
+                    mujoco.mj_kinematics(self.model, scratch)
+                    angular = Rotation.from_matrix(rotation @ scratch.xmat[self.wrist].reshape(3, 3).T).as_rotvec()
+                    return np.r_[scratch.site_xpos[self.site] - position, .15*angular, .002*(q-seed)]
+                result = least_squares(residual, seed, bounds=(self.lower, self.upper), max_nfev=150)
+                if np.linalg.norm(residual(result.x)[:6]) > .005:
+                    raise ValueError('Place destination outside arm workspace; choose a closer X/Y.')
+                targets.append(result.x)
+            self.place_low_q, self.place_high_q = targets
+        self.support_probe = None
+        self.place_xy = destination
+        self.lower_start_q = self.arm_target.copy()
+        self.set_stage('transfer' if np.linalg.norm(shift) > .001 else 'lower', data.time)
+        return True
+
+    def table_support(self, data):
+        for contact_id, contact in enumerate(data.contact):
+            geoms = [int(contact.geom1), int(contact.geom2)]
+            if self.geom in geoms:
+                other = geoms[1] if geoms[0] == self.geom else geoms[0]
+                if self.model.geom(other).name == 'pickup_table_top':
+                    force = np.zeros(6)
+                    mujoco.mj_contactForce(self.model, data, contact_id, force)
+                    if force[0] > .05:
+                        return True
+        return False
+
+    def start(self, data):
+        self.reset()
+        self.active = True
+        self.arm_target = data.qpos[self.arm_q].copy()
+        self.home_arm_q = self.arm_target.copy()
+        self.hand_target = np.zeros(7)
+        self.start_pos = data.site_xpos[self.site].copy()
+        self.start_rot = data.xmat[self.wrist].reshape(3, 3).copy()
+        self.set_stage('detecting', data.time)
+
+    def set_stage(self, stage, now):
+        self.stage, self.stage_since = stage, float(now)
+        print(f'[Assisted pickup] {stage}', flush=True)
+
+    def finger_contacts(self, data):
+        names = set()
+        for contact in data.contact:
+            a, b = self.model.geom_bodyid[[contact.geom1, contact.geom2]]
+            if a == self.bottle or b == self.bottle:
+                name = self.model.body(int(b if a == self.bottle else a)).name
+                if name.startswith('right_hand_'):
+                    names.add(name)
+        return sorted(names)
+
+    def solve(self, data, position, rotation):
+        m, scratch = self.model, self.scratch
+        scratch.qpos[:] = data.qpos
+        scratch.qpos[self.arm_q] = self.arm_target
+        for _ in range(8):
+            mujoco.mj_kinematics(m, scratch)
+            mujoco.mj_comPos(m, scratch)
+            linear = position - scratch.site_xpos[self.site]
+            angular = Rotation.from_matrix(rotation @ scratch.xmat[self.wrist].reshape(3, 3).T).as_rotvec()
+            if np.linalg.norm(linear) < .001 and np.linalg.norm(angular) < .015:
+                break
+            mujoco.mj_jacSite(m, scratch, self.jp, self.jr, self.site)
+            jac = np.vstack((self.jp[:, self.arm_v], .15 * self.jr[:, self.arm_v]))
+            error = np.r_[linear, .15 * angular]
+            delta = jac.T @ np.linalg.solve(jac @ jac.T + .00002 * np.eye(6), error)
+            scratch.qpos[self.arm_q] = np.clip(scratch.qpos[self.arm_q] + np.clip(delta, -.12, .12),
+                self.lower, self.upper)
+        # Bound commanded joint velocity even if a new IK branch is selected.
+        self.arm_target += np.clip(scratch.qpos[self.arm_q] - self.arm_target, -.025, .025)
+        self.position_error = float(np.linalg.norm(data.site_xpos[self.site] - position))
+        self.orientation_error = float(np.linalg.norm(Rotation.from_matrix(
+            rotation @ data.xmat[self.wrist].reshape(3, 3).T).as_rotvec()))
+
+    def plan_pregrasp(self, data):
+        """Choose a feasible IK branch before leaving the retracted home pose."""
+        m, scratch = self.model, self.scratch
+        scratch.qpos[:] = data.qpos
+        lower, upper = self.lower, self.upper
+        seed = np.array([.3, 0., -.2, 0., .8, 0., 0., 0.])
+        def residual(q):
+            scratch.qpos[self.arm_q] = q
+            mujoco.mj_kinematics(m, scratch)
+            rotation = Rotation.from_matrix(scratch.xmat[self.wrist].reshape(3, 3)).as_rotvec()
+            return np.r_[scratch.site_xpos[self.site] - self.pregrasp, .15 * rotation, .003 * (q - seed)]
+        result = least_squares(residual, np.clip(seed, lower, upper), bounds=(lower, upper), max_nfev=150)
+        if np.linalg.norm(residual(result.x)[:6]) > .006:
+            self.error = 'Visual bottle target outside the arm workspace. Move bottle closer and Reset.'
+            self.set_stage('failed', data.time)
+            return False
+        self.approach_start_q = data.qpos[self.arm_q].copy()
+        self.pregrasp_q = result.x
+        return True
+
+    def update(self, data, detection):
+        if not self.active or data.time - self.last_update < .019:
+            return
+        self.last_update = float(data.time)
+        elapsed = data.time - self.stage_since
+        self.contacts = self.finger_contacts(data)
+        opposed = (any('thumb' in name for name in self.contacts)
+                   and any('index' in name or 'middle' in name for name in self.contacts))
+        if self.stage == 'detecting':
+            captured = detection.get('capture_monotonic')
+            centre = visual_bottle_center(detection, self.radius, self.centre_height)
+            if centre is not None and captured != self.last_capture:
+                self.samples.append(centre)
+                self.last_capture = captured
+            if len(self.samples) >= 3:
+                sample = np.array(self.samples[-3:])
+                if np.max(np.ptp(sample[:, :2], axis=0)) < .015:
+                    self.target = np.median(sample, axis=0)
+                    self.grasp = self.target + [0., 0., .04]
+                    self.pregrasp = self.grasp + [-self.radius - .02, 0., 0.]
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
+        position, rotation = self.pregrasp.copy(), np.eye(3)
+        if self.stage == 'approach':
+            t = np.clip(elapsed / 3., 0., 1.)
+            blend = t*t*(3.-2.*t)
+            position = self.start_pos + blend * (self.pregrasp - self.start_pos)
+            rotation = Rotation.from_rotvec((1.-blend) * Rotation.from_matrix(self.start_rot).as_rotvec()).as_matrix()
+            self.arm_target = self.approach_start_q + blend * (self.pregrasp_q - self.approach_start_q)
+            self.position_error = float(np.linalg.norm(data.site_xpos[self.site] - self.pregrasp))
+            self.orientation_error = float(np.linalg.norm(Rotation.from_matrix(data.xmat[self.wrist].reshape(3, 3)).as_rotvec()))
+            if elapsed > 3. and self.position_error is not None and self.position_error < .012 and self.orientation_error < .08:
+                self.set_stage('close', data.time)
+            elif elapsed > 10:
+                self.error = 'Arm could not reach the visual pregrasp target.'
+                self.set_stage('failed', data.time)
+            return
+        elif self.stage == 'close':
+            advance = np.clip(elapsed / 1.5, 0., 1.)
+            advance = advance*advance*(3.-2.*advance)
+            position = self.pregrasp + advance * (self.grasp - self.pregrasp)
+            # Begin a small closure at the 2 cm surface gap, then complete it
+            # once the bottle is inside the grasp region. Closing fully while
+            # still advancing makes the index finger sweep the bottle away.
+            self.fraction = float(.05 * advance + .95 * np.clip((elapsed - 1.5) / 1.5, 0., 1.))
+            self.hand_target = self.closed * self.fraction
+            if elapsed > 3.5 and opposed:
+                self.table_arm_q = self.arm_target.copy()
+                self.set_stage('lift', data.time)
+            elif elapsed > 5:
+                self.error = 'No opposed finger contacts; lift cancelled. Reset to retry.'
+                self.set_stage('failed', data.time)
+        elif self.stage == 'transfer':
+            t = np.clip(elapsed / 4., 0., 1.)
+            self.arm_target = self.lower_start_q + t*t*(3.-2.*t)*(self.place_high_q-self.lower_start_q)
+            if elapsed > 5.:
+                self.lower_start_q = self.arm_target.copy()
+                self.set_stage('lower', data.time)
+            return
+        elif self.stage in ('lower', 'release', 'placed'):
+            if self.stage == 'lower':
+                t = np.clip(elapsed / 5., 0., 1.)
+                if elapsed <= 5.:
+                    self.arm_target = self.lower_start_q + t*t*(3.-2.*t) * (self.place_low_q - self.lower_start_q)
+                else:
+                    # Small tracking/grasp offsets can leave the bottle just
+                    # above the table. Search downward at 3 mm/s, at most 2 cm.
+                    if self.support_probe is None:
+                        self.scratch.qpos[:] = data.qpos
+                        self.scratch.qpos[self.arm_q] = self.place_low_q
+                        mujoco.mj_kinematics(self.model, self.scratch)
+                        self.support_probe = self.scratch.site_xpos[self.site].copy()
+                        self.support_probe_rot = self.scratch.xmat[self.wrist].reshape(3, 3).copy()
+                    position = self.support_probe + [0., 0., -min(.02, .003*(elapsed-5.))]
+                    self.solve(data, position, self.support_probe_rot)
+                if self.table_support(data):
+                    self.release_pos = data.site_xpos[self.site].copy()
+                    self.release_rot = data.xmat[self.wrist].reshape(3, 3).copy()
+                    position = self.release_pos.copy()
+                    self.set_stage('release', data.time)
+                elif elapsed > 13.:
+                    self.error = 'No tabletop support; fingers remain closed. Reset to retry.'
+                    self.set_stage('failed', data.time)
+                return
+            else:
+                position = self.release_pos.copy()
+                rotation = self.release_rot.copy()
+                self.fraction = float(1. - np.clip(elapsed / 2., 0., 1.)) if self.stage == 'release' else 0.
+                self.hand_target = self.closed * self.fraction
+                if self.stage == 'release' and elapsed > 3.:
+                    upright = data.xmat[self.bottle].reshape(3, 3)[2, 2] > .95
+                    self.placed = bool(self.table_support(data) and upright
+                        and np.linalg.norm(data.xpos[self.bottle, :2] - self.place_xy) < .025)
+                    if not self.placed:
+                        self.error = 'Bottle did not settle upright within 2.5 cm of the requested destination. Reset to retry.'
+                    self.set_stage('retreat' if self.placed else 'failed', data.time)
+        elif self.stage == 'retreat':
+            t = np.clip(elapsed / 2., 0., 1.)
+            position = self.release_pos + np.array([-.09, 0., .025]) * t*t*(3.-2.*t)
+            rotation = self.release_rot.copy()
+            self.solve(data, position, rotation)
+            if elapsed > 3.:
+                self.return_start_q = self.arm_target.copy()
+                self.set_stage('return_home', data.time)
+            return
+        elif self.stage in ('return_home', 'complete'):
+            t = np.clip(elapsed / 4., 0., 1.) if self.stage == 'return_home' else 1.
+            self.arm_target = self.return_start_q + t*t*(3.-2.*t)*(self.home_arm_q-self.return_start_q)
+            if self.stage == 'return_home' and elapsed > 5.:
+                if np.max(np.abs(data.qpos[self.arm_q]-self.home_arm_q)) < .05:
+                    self.set_stage('complete', data.time)
+                elif elapsed > 8.:
+                    self.error = 'Arm could not return home. Reset to retry.'
+                    self.set_stage('failed', data.time)
+            return
+        elif self.stage in ('lift', 'hold', 'success'):
+            t = np.clip(elapsed / 3., 0., 1.) if self.stage == 'lift' else 1.
+            position = self.grasp + [0., 0., .20*t*t*(3.-2.*t)]
+            if self.stage == 'lift' and elapsed > 3.:
+                self.min_hold_lift = np.inf
+                self.set_stage('hold', data.time)
+                elapsed = 0.
+            if self.stage in ('hold', 'success'):
+                lift = float(data.xpos[self.bottle, 2] - self.centre_height)
+                self.min_hold_lift = min(self.min_hold_lift, lift)
+                self.hold_contacts &= opposed
+                if self.stage == 'hold' and elapsed > 3.:
+                    self.success = bool(self.min_hold_lift > .12 and self.hold_contacts)
+                    if not self.success:
+                        self.error = 'Bottle was not lifted and held with opposed contacts.'
+                    self.set_stage('success' if self.success else 'failed', data.time)
+        self.solve(data, position, rotation)
+
+    def apply_torques(self, data, body, hand, body_joint_indices):
+        if not self.active:
+            return
+        indices = [int(np.flatnonzero(body_joint_indices == joint)[0]) for joint in self.arm]
+        body[indices] = (80. * (self.arm_target - data.qpos[self.arm_q])
+                         - 3. * data.qvel[self.arm_v] + data.qfrc_bias[self.arm_v])
+        hand[7:] = (8. * (self.hand_target - data.qpos[self.hand_q])
+                    - .2 * data.qvel[self.hand_v] + data.qfrc_bias[self.hand_v])
+
+    def snapshot(self):
+        return {'stage': self.stage, 'active': self.active, 'success': self.success, 'placed': self.placed,
+                'place_target_xy_m': self.place_xy.tolist() if self.place_xy is not None else None,
+                'target_source': 'YOLO RGB-D surface + known radius and tabletop height',
+                'target_center_world_m': self.target.tolist() if self.target is not None else None,
+                'position_error_m': self.position_error, 'orientation_error_rad': self.orientation_error,
+                'finger_contacts': self.contacts, 'closure_fraction': self.fraction,
+                'minimum_hold_lift_m': self.min_hold_lift if self.min_hold_lift is not None and np.isfinite(self.min_hold_lift) else None,
+                'error': self.error}
diff --git a/gear_sonic/utils/mujoco_sim/async_camera.py b/gear_sonic/utils/mujoco_sim/async_camera.py
new file mode 100644
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
diff --git a/gear_sonic/utils/mujoco_sim/control_panel.py b/gear_sonic/utils/mujoco_sim/control_panel.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/control_panel.py
@@ -0,0 +1,191 @@
+"""Native bottle/run controls in a separate process, leaving physics responsive."""
+
+import multiprocessing as mp
+import os
+import queue
+
+
+class SimulationControlPanel:
+    def __init__(self, xy, z, bounds):
+        context = mp.get_context("spawn")
+        self.commands = context.Queue(maxsize=16)
+        self.snapshots = context.Queue(maxsize=1)
+        self.stop_event = context.Event()
+        self.process = context.Process(
+            target=_panel_worker,
+            args=(list(xy), z, bounds.tolist(), self.commands, self.snapshots, self.stop_event, os.getpid()),
+            daemon=True,
+        )
+        self.process.start()
+
+    def read(self):
+        try:
+            return self.commands.get_nowait()
+        except queue.Empty:
+            return None
+
+    def update(self, snapshot):
+        try:
+            self.snapshots.put_nowait(snapshot)
+        except queue.Full:
+            try:
+                self.snapshots.get_nowait()
+            except queue.Empty:
+                return
+            try:
+                self.snapshots.put_nowait(snapshot)
+            except queue.Full:
+                pass
+
+    def close(self):
+        self.stop_event.set()
+        self.process.join(timeout=2)
+        if self.process.is_alive():
+            self.process.terminate()
+            self.process.join(timeout=1)
+        for channel in (self.commands, self.snapshots):
+            channel.cancel_join_thread()
+            channel.close()
+
+
+def _panel_worker(xy, z, bounds, commands, snapshots, stop_event, parent_pid=None):
+    from gear_sonic.utils.mujoco_sim.process_lifecycle import follow_parent
+    if parent_pid is not None and not follow_parent(parent_pid):
+        return
+    import tkinter as tk
+    from tkinter import ttk
+
+    try:
+        root = tk.Tk()
+    except tk.TclError as error:
+        print(f"[Simulation controls] Cannot open control panel: {error}", flush=True)
+        return
+    root.title("MuJoCo - Bottle / Robot Controls")
+    root.geometry("540x850+20+70")
+    root.minsize(490, 700)
+    root.attributes("-topmost", True)
+    frame = ttk.Frame(root, padding=14)
+    frame.pack(fill="both", expand=True)
+    detector_coordinates = tk.StringVar(value="DETECTED BOTTLE - YOLO\nWaiting for camera...")
+    tk.Label(frame, textvariable=detector_coordinates, background="#073b45", foreground="#79ffb1",
+             font=("TkFixedFont", 12, "bold"), justify="left", anchor="w", padx=12, pady=14).pack(fill="x", pady=(0, 12))
+    # Some WSL Tk builds expose only the X11 bitmap font (no Vietnamese glyphs).
+    # ASCII labels keep the native controls readable without extra dependencies.
+    ttk.Label(frame, text="Bottle position on table (metres, world frame)").pack(anchor="w")
+    entries = ttk.Frame(frame)
+    entries.pack(fill="x", pady=8)
+    x, y = tk.StringVar(value=f"{xy[0]:.3f}"), tk.StringVar(value=f"{xy[1]:.3f}")
+    for label, variable in (("X", x), ("Y", y)):
+        ttk.Label(entries, text=label).pack(side="left", padx=4)
+        ttk.Entry(entries, textvariable=variable, width=10).pack(side="left", padx=4)
+    ttk.Label(frame, text=f"Placement Z = {z:.3f} m (fixed, bottle body centre)").pack(anchor="w")
+    ttk.Label(frame, text=(f"X: {bounds[0][0]:.3f}..{bounds[0][1]:.3f}   "
+                           f"Y: {bounds[1][0]:.3f}..{bounds[1][1]:.3f}")).pack(anchor="w")
+    error_text = tk.StringVar()
+    status = tk.StringVar(value="Connecting to simulation...")
+    coordinates = tk.StringVar()
+    detector_status = tk.StringVar()
+    inference = tk.StringVar()
+
+    def send(command):
+        try:
+            payload = {"command": command}
+            if command == "place":
+                payload["xy"] = [float(x.get()), float(y.get())]
+            if command == "lower":
+                payload["xy"] = [float(place_x.get()), float(place_y.get())]
+            commands.put_nowait(payload)
+            error_text.set("")
+        except ValueError:
+            error_text.set("X/Y must be numbers; use a decimal point.")
+        except queue.Full:
+            error_text.set("Please wait for the previous command.")
+
+    apply_button = ttk.Button(frame, text="Apply X/Y / Reset bottle", command=lambda: send("place"))
+    apply_button.pack(fill="x", pady=(10, 5))
+    ttk.Button(frame, text="Reset robot + bottle", command=lambda: send("reset")).pack(fill="x", pady=5)
+    start_button = ttk.Button(frame, text="Start GR00T", command=lambda: send("start"))
+    start_button.pack(fill="x", pady=5)
+    ttk.Label(frame, text="Place destination X/Y (metres, world frame)").pack(anchor="w")
+    place_entries = ttk.Frame(frame)
+    place_entries.pack(fill="x", pady=4)
+    place_x, place_y = tk.StringVar(value=f"{xy[0]:.3f}"), tk.StringVar(value=f"{xy[1]:.3f}")
+    for label, variable in (("X", place_x), ("Y", place_y)):
+        ttk.Label(place_entries, text=label).pack(side="left", padx=4)
+        ttk.Entry(place_entries, textvariable=variable, width=10).pack(side="left", padx=4)
+    lower_button = ttk.Button(frame, text="Lower / Place on table", command=lambda: send("lower"), state="disabled")
+    lower_button.pack(fill="x", pady=5)
+    grasp_text = tk.StringVar(value="GRASP CENTRE\nWaiting for X/Y measurements...")
+    tk.Label(frame, textvariable=grasp_text, background="#163553", foreground="#ffffff",
+             font=("TkFixedFont", 11, "bold"), anchor="w", justify="left", padx=10, pady=10).pack(fill="x", pady=5)
+    ttk.Label(frame, textvariable=error_text, foreground="#b00020", wraplength=455).pack(anchor="w")
+    ttk.Separator(frame).pack(fill="x", pady=10)
+    ttk.Label(frame, textvariable=status, wraplength=455).pack(anchor="w")
+    ttk.Label(frame, textvariable=coordinates, font=("TkFixedFont", 10), justify="left").pack(anchor="w", pady=10)
+    ttk.Label(frame, textvariable=detector_status, wraplength=455).pack(anchor="w", pady=(0, 10))
+    ttk.Label(frame, textvariable=inference, wraplength=455).pack(anchor="w")
+    ttk.Label(frame, text="MuJoCo = scene bottle centre.\n"
+              "YOLO = estimated visible surface point from RGB + depth.\n"
+              "Arm: GR00T/SONIC; assisted mode corrects right-arm pickup.\n"
+              "Reset clears the motion. Change X/Y, Apply, then Start.",
+              wraplength=455, foreground="#555555").pack(anchor="w", pady=10)
+
+    def poll():
+        if stop_event.is_set() or (parent_pid is not None and os.getppid() != parent_pid):
+            root.destroy()
+            return
+        latest = None
+        while True:
+            try:
+                latest = snapshots.get_nowait()
+            except queue.Empty:
+                break
+        if latest is not None:
+            status.set(latest["status"])
+            error_text.set(latest.get("error", ""))
+            lines = []
+            for label, key in (("Bottle centre", "bottle"), ("GRASP CENTRE", "right_grasp_center"),
+                               ("SONIC grasp", "right_grasp_target"), ("Wrist origin", "right_wrist")):
+                pos = latest.get(key)
+                if pos is not None:
+                    lines.append(f"{label:13s} X {pos[0]:+.3f}\n"
+                                 f"              Y {pos[1]:+.3f} Z {pos[2]:+.3f}")
+            alignment = latest.get("hand_alignment", {})
+            grasp = alignment.get("grasp_center_world_m")
+            gap = alignment.get("y_surface_gap_m")
+            x_error = alignment.get("x_error_m")
+            x_text = f"{x_error * 100:+.2f}" if x_error is not None else "--"
+            gap_text = f"{gap * 100:.2f}" if gap is not None else "--"
+            position_text = (f"X {grasp[0]:+.3f} Y {grasp[1]:+.3f} Z {grasp[2]:+.3f} m\n" if grasp is not None else "")
+            grasp_text.set("GRASP CENTRE - green marker (MuJoCo)\n" + position_text
+                + f"X error {x_text} cm | tolerance {latest.get('grasp_x_tolerance_m', .005) * 100:.1f} cm\n"
+                + f"Y surface gap {gap_text} cm | target {latest.get('grasp_threshold_m', 0.) * 100:.1f} cm\n"
+                + latest.get("grasp_status", "Disabled"))
+            detection = latest.get("detection", {})
+            point = detection.get("world_point_m")
+            if point is not None:
+                detector_coordinates.set("DETECTED BOTTLE - YOLO (world, metres)\n"
+                    f"X {point[0]:+.3f}    Y {point[1]:+.3f}    Z {point[2]:+.3f}\n"
+                    f"Confidence {detection.get('confidence', 0.):.2f} | visible surface")
+            else:
+                detector_coordinates.set("DETECTED BOTTLE - YOLO\n"
+                    + detection.get("status", "disabled") + "\nX --    Y --    Z --")
+            detector_status.set("YOLO bottle: " + detection.get("status", "disabled")
+                + (f" | confidence {detection['confidence']:.2f}" if "confidence" in detection else ""))
+            coordinates.set("\n".join(lines))
+            action = latest.get("policy_action", {})
+            grip = action.get("right_grip")
+            details = "\nGR00T right grip: " + (f"{grip * 100:.1f}%" if grip is not None else "--")
+            if "wrist_tracking_error_m" in latest:
+                details += f"\nSONIC wrist tracking error: {latest['wrist_tracking_error_m'] * 100:.1f} cm"
+            if "grasp_tracking_error_m" in latest:
+                details += f"\nSONIC grasp tracking error: {latest['grasp_tracking_error_m'] * 100:.1f} cm"
+            inference.set(latest["inference"] + details)
+            start_button.configure(state="normal" if latest["can_start"] else "disabled")
+            lower_button.configure(state="normal" if latest.get("can_lower", False) else "disabled")
+            apply_button.configure(state="normal" if latest["can_place"] else "disabled")
+        root.after(100, poll)
+
+    # Closing this optional panel does not stop physics; F2 reopens it.
+    root.after(100, poll)
+    root.mainloop()
diff --git a/gear_sonic/utils/mujoco_sim/hand_alignment.py b/gear_sonic/utils/mujoco_sim/hand_alignment.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/hand_alignment.py
@@ -0,0 +1,79 @@
+"""Fixed grasp-region centre and independent world-X/world-Y grasp gates."""
+
+import mujoco
+import numpy as np
+
+
+def cylinder_y_surface_gap(point, centre, rotation, radius, half_height):
+    """Signed world-Y clearance at this point's X/Z; None outside the profile.
+
+    Intersect a line parallel to world Y with the finite cylinder. This measures
+    only Y clearance, rather than Euclidean distance or centre-to-centre Y.
+    """
+    local = rotation.T @ (np.asarray(point) - centre)
+    direction = rotation.T @ np.array([0., 1., 0.])
+    a = float(direction[:2] @ direction[:2])
+    b = float(2. * (local[:2] @ direction[:2]))
+    c = float(local[:2] @ local[:2] - radius ** 2)
+    if a > 1e-12:
+        discriminant = b * b - 4. * a * c
+        if discriminant < -1e-12:
+            return None
+        root = np.sqrt(max(discriminant, 0.))
+        low, high = (-b - root) / (2. * a), (-b + root) / (2. * a)
+    elif c <= 1e-12:
+        low, high = -np.inf, np.inf
+    else:
+        return None
+    if abs(direction[2]) > 1e-12:
+        ends = sorted(((-half_height - local[2]) / direction[2],
+                       (half_height - local[2]) / direction[2]))
+        low, high = max(low, ends[0]), min(high, ends[1])
+    elif abs(local[2]) > half_height + 1e-12:
+        return None
+    if low > high + 1e-12:
+        return None
+    return float(max(low, -high))
+
+
+class HandGraspAlignment:
+    def __init__(self, model):
+        # The palm inertia is fused into the wrist-yaw body in this MJCF.
+        # Its descendants are all finger links; wrist pitch/roll and forearm
+        # are ancestors and must not contribute to the whole-hand COM.
+        self.root = model.body("right_wrist_yaw_link").id
+        bodies = [self.root]
+        for body in range(self.root + 1, model.nbody):
+            if int(model.body_parentid[body]) in bodies:
+                bodies.append(body)
+        self.bodies = np.asarray(bodies, dtype=int)
+        self.masses = model.body_mass[self.bodies].copy()
+        self.mass = float(self.masses.sum())
+        if not np.isfinite(self.mass) or self.mass <= 0.:
+            raise ValueError("Whole hand must have positive finite mass")
+        self.grasp_site = model.site("right_hand_grasp_center").id
+        if model.site_bodyid[self.grasp_site] != self.root:
+            raise ValueError("Grasp centre must attach to the wrist/palm, not a finger")
+        self.grasp_local = model.site_pos[self.grasp_site].copy()
+        self.bottle = model.geom("red_bottle_body").id
+        if model.geom_type[self.bottle] != mujoco.mjtGeom.mjGEOM_CYLINDER:
+            raise ValueError("Hand alignment expects the cylindrical bottle body")
+        self.radius, self.half_height = model.geom_size[self.bottle, :2]
+
+    def measure(self, data):
+        # Finger flexion must not move the reference used to start closing.
+        # Keep the physical COM as a separate diagnostic only.
+        hand = data.site_xpos[self.grasp_site]
+        hand_com = np.average(data.xipos[self.bodies], axis=0, weights=self.masses)
+        centre = data.geom_xpos[self.bottle]
+        rotation = data.geom_xmat[self.bottle].reshape(3, 3)
+        gap = cylinder_y_surface_gap(hand, centre, rotation, self.radius, self.half_height)
+        tilt = float(np.degrees(np.arccos(np.clip(rotation[2, 2], -1., 1.))))
+        return {"grasp_center_world_m": hand.tolist(),
+                "grasp_center_wrist_local_m": self.grasp_local.tolist(),
+                "whole_hand_com_world_m": hand_com.tolist(), "hand_mass_kg": self.mass,
+                "bottle_body_center_world_m": centre.tolist(),
+                "x_error_m": float(hand[0] - centre[0]),
+                "y_center_offset_m": float(hand[1] - centre[1]),
+                "y_surface_gap_m": gap, "bottle_tilt_deg": tilt,
+                "distance_source": "MuJoCo fixed grasp-region centre: X alignment and Y surface gap"}
diff --git a/gear_sonic/utils/mujoco_sim/interactive_controls.py b/gear_sonic/utils/mujoco_sim/interactive_controls.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/interactive_controls.py
@@ -0,0 +1,347 @@
+"""Simulation UI state machine. All physics changes happen on the sim thread."""
+
+import time
+import zmq
+
+from gear_sonic.utils.inference.simulation_controls import SimulationControlChannel
+from gear_sonic.utils.data_collection.zmq_state_subscriber import ZMQStateSubscriber
+
+
+class InteractiveSimulationControls:
+    def __init__(self, env, port=5581):
+        self.env = env
+        self.channel = SimulationControlChannel(port=port, bind=True)
+        self.controller_state = ZMQStateSubscriber()
+        self.controller_seen = 0.
+        self.client_seen = 0.
+        self.client_status = {}
+        self.pending = None
+        self.serial = 0
+        self.phase = "idle"
+        self.phase_since = time.monotonic()
+        self.error = ""
+        self.panel = None
+        self.last_ui_update = 0.
+        self._first_action_count = 0
+        self.detector_socket = None
+        self.detector_result = None
+        from gear_sonic.utils.mujoco_sim.hand_alignment import HandGraspAlignment
+        self.hand_alignment = HandGraspAlignment(env.mj_model) if env.bottle_placement is not None else None
+        self.grasp_sample = {}
+        self.grasp_latched = False
+        self.bottle_seen = False
+        self.recognition_scene = env.scene_changed_at
+        if self.env.config.get("BOTTLE_DETECTION_PORT"):
+            self.detector_socket = self.channel.context.socket(zmq.SUB)
+            self.detector_socket.setsockopt_string(zmq.SUBSCRIBE, "")
+            self.detector_socket.setsockopt(zmq.CONFLATE, 1)
+            self.detector_socket.connect(f"tcp://127.0.0.1:{self.env.config['BOTTLE_DETECTION_PORT']}")
+        self.open_panel()
+
+    def open_panel(self):
+        if self.env.viewer is None or self.env.bottle_placement is None:
+            return
+        if self.panel is not None:
+            if self.panel.process.is_alive():
+                return
+            self.panel.close()
+        from gear_sonic.utils.mujoco_sim.control_panel import SimulationControlPanel
+        bottle = self.env.bottle_placement
+        self.panel = SimulationControlPanel(bottle.xy, bottle.z, bottle.bounds)
+
+    def connected(self):
+        return time.monotonic() - self.client_seen < 2.
+
+    def request(self, command, **fields):
+        self.serial += 1
+        message = {"command": command, "id": self.serial, **fields}
+        if not self.channel.send(message):
+            self.error = "VLA disconnected. Check inference pane / policy server."
+            return False
+        self.pending = (message, time.monotonic())
+        return True
+
+    def can_repeat_pickup(self):
+        pickup = getattr(self.env, 'assisted_pickup', None)
+        return (self.phase == 'running' and pickup is not None
+                and pickup.active and pickup.stage == 'complete')
+
+    def handle(self, message):
+        command = message["command"]
+        if command == "open_panel":
+            self.open_panel()
+            return
+        if self.pending is not None and command != 'reset':
+            self.error = "Please wait for the previous command."
+            return
+        self.error = ""
+        if command == "place":
+            if self.phase != "idle":
+                self.error = "Click Reset robot + bottle before changing X/Y."
+                return
+            try:
+                self.env.bottle_placement.reset(self.env.mj_model, self.env.mj_data, message["xy"])
+                self.env.scene_changed_at = time.monotonic()
+                self.bottle_seen = False
+                self.grasp_latched = False
+                print(f"[Simulation] Bottle XY = {self.env.bottle_placement.xy.tolist()}", flush=True)
+            except (TypeError, ValueError) as error:
+                self.error = str(error)
+        elif command == "reset":
+            self.pending = None  # Reset supersedes an unfinished Start/prepare.
+            self.env.standby = True
+            pickup = getattr(self.env, 'assisted_pickup', None)
+            if pickup is not None:
+                pickup.reset()
+            if self.connected():
+                if self.request("pause"):
+                    self.phase = "resetting"
+            else:
+                # Local standby ignores stale DDS targets even without a VLA client.
+                self.reset_scene()
+        elif command == "lower":
+            pickup = getattr(self.env, 'assisted_pickup', None)
+            try:
+                if self.phase != 'running' or pickup is None or not pickup.lower_to_table(self.env.mj_data, message.get('xy')):
+                    self.error = 'Lower is available only after a successful assisted pickup.'
+            except (TypeError, ValueError) as error:
+                self.error = str(error)
+        elif command == "start":
+            if self.can_repeat_pickup():
+                if not self.connected():
+                    self.error = "VLA disconnected. Check inference pane / policy server."
+                    return
+                # Keep the live scene and standing controller. Only restart the
+                # visual pickup state machine, requiring observations after this click.
+                self.env.scene_changed_at = time.monotonic()
+                self.detector_result = None
+                self.bottle_seen = False
+                self.grasp_latched = False
+                self.env.assisted_pickup.start(self.env.mj_data)
+                return
+            if self.phase not in ("idle", "paused"):
+                return
+            if not self.connected():
+                self.error = "VLA disconnected. Check inference pane / policy server."
+                return
+            if self.env.viewer is not None:
+                # F6 also toggles MuJoCo's native body-frame drawing. Keep
+                # that built-in shortcut from obscuring the pickup scene.
+                with self.env.viewer.lock():
+                    self.env.viewer.opt.frame = 0
+            if self.request("prepare"):
+                self.grasp_latched = False
+                self.phase = "preparing"
+                self.phase_since = time.monotonic()
+                self.controller_seen = 0.
+                self.controller_state.get_msg()  # Discard a pre-reset queued state.
+                self.env.standby = True
+                self.env.restore_ground_support()
+
+    def handle_keyboard(self, key):
+        """Keep the existing k/i/p terminal workflow usable alongside the panel."""
+        if self.pending is not None:
+            return
+        if key in ("k", "i"):
+            self.env.standby = False
+            self.phase = "paused"
+        elif key == "p":
+            if self.client_status.get("paused", True):
+                if time.monotonic() - self.controller_seen < .5:
+                    self.env.release_ground_support()
+                self.phase = "observing"
+                self._first_action_count = self.client_status.get("actions_published", 0)
+            else:
+                self.phase = "paused"
+
+    def reset_scene(self):
+        self.env.reset()
+        self.grasp_latched = False
+        self.bottle_seen = False
+        self.grasp_sample = {}
+        self.phase = "idle"
+        self.phase_since = time.monotonic()
+        self.error = ""
+        print("[Simulation] Robot + bottle reset; policy paused, ground standby active.", flush=True)
+
+    def poll(self):
+        now = time.monotonic()
+        if self.detector_socket is not None:
+            try:
+                self.detector_result = self.detector_socket.recv_json(zmq.NOBLOCK)
+            except zmq.Again:
+                pass
+        if self.controller_state.get_msg() is not None:
+            self.controller_seen = now
+        while (message := self.channel.receive()) is not None:
+            if message.get("type") == "status":
+                self.client_status = message
+                self.client_seen = now
+            elif message.get("type") == "ack" and self.pending is not None:
+                request, _ = self.pending
+                if message.get("id") != request["id"]:
+                    continue
+                self.pending = None
+                if not message.get("ok", False):
+                    self.error = message.get("error", "VLA command failed.")
+                    self.phase = "paused"
+                elif request["command"] == "pause":
+                    self.reset_scene()
+                elif request["command"] == "start":
+                    self.phase = "observing"
+                    self.phase_since = now
+                    self._first_action_count = self.client_status.get("actions_published", 0)
+        if self.pending is not None and now - self.pending[1] > 10:
+            self.error = "VLA command timed out. Check logs, then click Reset."
+            self.pending = None
+            self.phase = "paused"
+        if self.phase == "preparing" and self.pending is None:
+            if (now - self.controller_seen < .5 and now - self.phase_since >= 2.
+                    and getattr(self.env.unitree_bridge, 'low_cmd_received', False)):
+                self.env.begin_control_transition()
+                self.phase = "grounded"
+                self.phase_since = now
+            elif now - self.phase_since > 15:
+                self.error = "SONIC not ready. Check C++ deploy (Init Done / LowState)."
+        elif self.phase == "grounded" and self.env._control_transition_started is None:
+            if now - self.controller_seen < .5 and self.request("start"):
+                self.env.release_ground_support()
+                self.phase = "starting"
+        elif self.phase == "observing":
+            if self.client_status.get("actions_published", 0) > self._first_action_count:
+                self.phase = "running"
+            elif self.client_status.get("paused", False) and now - self.phase_since > .3:
+                self.phase = "paused"
+        elif self.phase == "running" and self.client_status.get("paused", False):
+            self.phase = "paused"
+
+        # Queue events from Tk/viewer; no callbacks are allowed to modify MjData.
+        while not self.env.ui_commands.empty():
+            self.handle(self.env.ui_commands.get_nowait())
+        if self.panel is not None:
+            while (command := self.panel.read()) is not None:
+                self.handle(command)
+        self.check_hand_alignment()
+        pickup = getattr(self.env, 'assisted_pickup', None)
+        if pickup is not None:
+            from gear_sonic.utils.perception.bottle_detector import current_detection
+            if self.phase == 'running':
+                if not pickup.active:
+                    pickup.start(self.env.mj_data)
+                pickup.update(self.env.mj_data, current_detection(self.detector_result, self.env.scene_changed_at))
+            elif pickup.active:
+                pickup.reset()
+        if now - self.last_ui_update >= .1:
+            snapshot = self.snapshot()
+            self.env.ui_snapshot = snapshot
+            if self.panel is not None and self.panel.process.is_alive():
+                self.panel.update(snapshot)
+            self.last_ui_update = now
+
+    def check_hand_alignment(self):
+        proximity = getattr(self, "hand_alignment", None)
+        if proximity is None:
+            return
+        from gear_sonic.utils.perception.bottle_detector import current_detection
+        from gear_sonic.utils.inference.proximity_hand import ready_to_close
+        self.grasp_sample = proximity.measure(self.env.mj_data)
+        if self.recognition_scene != self.env.scene_changed_at:
+            self.bottle_seen = False
+            self.recognition_scene = self.env.scene_changed_at
+        # Recognition may precede approach and then be occluded by the hand.
+        # A reset/place invalidates this trial's recognition latch.
+        if self.detector_socket and current_detection(self.detector_result, self.env.scene_changed_at).get("status") == "detected":
+            self.bottle_seen = True
+        threshold = self.env.config.get("SIM_GRASP_DISTANCE", 0.)
+        tolerance = self.env.config.get("SIM_GRASP_X_TOLERANCE", .005)
+        if (threshold > 0 and not self.grasp_latched and self.pending is None and self.connected()
+                and ready_to_close(self.grasp_sample, threshold, tolerance, self.phase == "running", self.bottle_seen)):
+            if self.request("close_right_hand", source=self.grasp_sample["distance_source"], **self.grasp_sample):
+                self.grasp_latched = True
+                print(f"[Simulation] Grasp-region centre: X error {self.grasp_sample['x_error_m'] * 100:.2f} cm, "
+                      f"Y surface gap {self.grasp_sample['y_surface_gap_m'] * 100:.2f} cm: closing right hand.", flush=True)
+
+    def snapshot(self):
+        snapshot = self.env.coordinate_snapshot()
+        snapshot.update(self.env.command_coordinate_snapshot())
+        from gear_sonic.utils.perception.bottle_detector import current_detection
+        detection = current_detection(self.detector_result, self.env.scene_changed_at) if self.detector_socket else {"status": "disabled"}
+        labels = {
+            "idle": "Robot pose locked. Enter bottle X/Y, then click Start.",
+            "resetting": "Pausing GR00T before reset...",
+            "preparing": "Pose locked. Waiting for fresh SONIC commands...",
+            "grounded": "Smoothly transferring joint control to SONIC...",
+            "starting": "Requesting a new camera frame...",
+            "observing": "Waiting for GR00T: fresh RGB + prompt + robot state...",
+            "running": "GR00T is controlling the robot. Click Reset to repeat.",
+            "paused": "Paused. Click Reset to return to the initial position.",
+        }
+        snapshot.update(
+            hand_alignment=getattr(self, "grasp_sample", {}),
+            grasp_threshold_m=self.env.config.get("SIM_GRASP_DISTANCE", 0.),
+            grasp_x_tolerance_m=self.env.config.get("SIM_GRASP_X_TOLERANCE", .005),
+            grasp_latched=getattr(self, "grasp_latched", False),
+            bottle_seen=getattr(self, "bottle_seen", False),
+            detection=detection,
+            policy_action=self.client_status.get("policy_action", {}),
+            actions_published=self.client_status.get("actions_published", 0),
+            phase=self.phase, status=labels[self.phase], error=self.error,
+            can_start=self.connected() and (self.phase in ("idle", "paused") or self.can_repeat_pickup()) and self.pending is None,
+            can_place=self.phase == "idle" and self.pending is None,
+            inference=(f"VLA: {'connected' if self.connected() else 'disconnected'} | "
+                       f"Published actions: {self.client_status.get('actions_published', 0)}\n"
+                       "GR00T detected XYZ: unavailable in checkpoint output.\n"
+                       + self.client_status.get("error", "")),
+        )
+        sample = snapshot["hand_alignment"]
+        action = snapshot["policy_action"]
+        fraction = action.get("closure_fraction")
+        if not snapshot["grasp_threshold_m"]:
+            grasp_status = "Disabled (GR00T hand commands)"
+        elif fraction is not None:
+            grasp_status = "Holding closed" if fraction >= 1. else f"Closing {fraction * 100:.0f}%"
+        elif snapshot["grasp_latched"]:
+            grasp_status = "Closure requested"
+        elif self.phase != "running":
+            grasp_status = "Waiting for Start"
+        elif not snapshot["bottle_seen"]:
+            grasp_status = "Waiting for YOLO recognition"
+        elif sample.get("bottle_tilt_deg", 0.) >= 30.:
+            grasp_status = "Bottle tipped - Reset to retry"
+        elif abs(sample.get("x_error_m", float("inf"))) > snapshot["grasp_x_tolerance_m"] + 1e-9:
+            grasp_status = "Waiting for X alignment"
+        elif sample.get("y_surface_gap_m") is None:
+            grasp_status = "Grasp centre outside bottle profile"
+        elif sample["y_surface_gap_m"] < -1e-9:
+            grasp_status = "Grasp centre inside bottle - Reset"
+        else:
+            grasp_status = f"Waiting for Y gap <= {snapshot['grasp_threshold_m'] * 100:.1f} cm"
+        snapshot["grasp_status"] = grasp_status
+        pickup = getattr(self.env, 'assisted_pickup', None)
+        snapshot['can_lower'] = bool(pickup is not None and pickup.active
+            and pickup.stage == 'success' and self.phase == 'running' and self.pending is None)
+        if pickup is not None:
+            snapshot['assisted_pickup'] = pickup.snapshot()
+            snapshot['grasp_status'] = 'Assisted RGB-D pickup: ' + pickup.stage
+            if self.env.config.get('FIXED_PICKUP_BASE', False):
+                snapshot['inference'] += '\nExecuted motion: RGB-D/IK, pelvis fixed in simulation.'
+                if self.phase == 'running':
+                    snapshot['status'] = ('Arm home. Click Start to pick up the bottle again at its current position.'
+                        if pickup.stage == 'complete' else
+                        'Assisted table pickup: ' + pickup.stage + '. Reset to stop or change scene X/Y.')
+        return snapshot
+
+    def close(self):
+        if self.connected() and self.request("pause"):
+            deadline = time.monotonic() + .5
+            while time.monotonic() < deadline:
+                message = self.channel.receive()
+                if message and message.get("type") == "ack" and message.get("id") == self.serial:
+                    break
+                time.sleep(.005)
+        if self.panel is not None:
+            self.panel.close()
+        if self.detector_socket is not None:
+            self.detector_socket.close(linger=0)
+        self.channel.close()
+        self.controller_state.close()
diff --git a/gear_sonic/utils/mujoco_sim/object_reset.py b/gear_sonic/utils/mujoco_sim/object_reset.py
new file mode 100644
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
diff --git a/gear_sonic/utils/mujoco_sim/palm_proximity.py b/gear_sonic/utils/mujoco_sim/palm_proximity.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/palm_proximity.py
@@ -0,0 +1,34 @@
+"""Measure palm-centre clearance from the graspable bottle body in MuJoCo."""
+
+import mujoco
+import numpy as np
+
+
+def cylinder_surface_distance(point, radius, half_height):
+    """Signed shortest distance from a point to a finite cylinder's surface."""
+    point = np.asarray(point, dtype=float)
+    radial = np.linalg.norm(point[:2])
+    delta = np.array([radial - radius, abs(point[2]) - half_height])
+    distance = np.linalg.norm(np.maximum(delta, 0.)) + min(max(delta), 0.)
+    return float(distance)
+
+
+class PalmProximity:
+    def __init__(self, model):
+        mesh = model.mesh("right_hand_palm_link").id
+        self.palm = next(i for i in range(model.ngeom)
+            if model.geom_type[i] == mujoco.mjtGeom.mjGEOM_MESH
+            and model.geom_dataid[i] == mesh and (model.geom_contype[i] or model.geom_conaffinity[i]))
+        self.bottle = model.geom("red_bottle_body").id
+        if model.geom_type[self.bottle] != mujoco.mjtGeom.mjGEOM_CYLINDER:
+            raise ValueError("Palm proximity expects the scene's cylindrical bottle body")
+        self.radius, self.half_height = model.geom_size[self.bottle, :2]
+
+    def measure(self, data):
+        palm = data.geom_xpos[self.palm].copy()
+        rotation = data.geom_xmat[self.bottle].reshape(3, 3)
+        local = rotation.T @ (palm - data.geom_xpos[self.bottle])
+        distance = cylinder_surface_distance(local, self.radius, self.half_height)
+        tilt = float(np.degrees(np.arccos(np.clip(rotation[2, 2], -1., 1.))))
+        return {"palm_center_world_m": palm.tolist(), "palm_surface_distance_m": distance,
+                "bottle_tilt_deg": tilt, "distance_source": "MuJoCo palm centre to bottle-body surface"}
diff --git a/gear_sonic/utils/mujoco_sim/process_lifecycle.py b/gear_sonic/utils/mujoco_sim/process_lifecycle.py
new file mode 100644
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
diff --git a/gear_sonic/utils/mujoco_sim/reach_diagnostics.py b/gear_sonic/utils/mujoco_sim/reach_diagnostics.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/reach_diagnostics.py
@@ -0,0 +1,72 @@
+"""Measure reach geometry directly in the simulator's world frame."""
+import mujoco
+import numpy as np
+from gear_sonic.utils.mujoco_sim.palm_proximity import PalmProximity
+from gear_sonic.utils.mujoco_sim.hand_alignment import HandGraspAlignment
+
+
+def measure_reach(model, data, joint_targets=None):
+    # Use a separate data object so diagnostics never change the running physics.
+    actual = mujoco.MjData(model)
+    actual.qpos[:] = data.qpos
+    actual.qvel[:] = data.qvel
+    mujoco.mj_forward(model, actual)
+    bottle = model.body('red_bottle').id
+    wrist = model.body('right_wrist_yaw_link').id
+    grasp_site = model.site('right_hand_grasp_center').id
+    palm_mesh = model.mesh('right_hand_palm_link').id
+    palm = next(i for i in range(model.ngeom) if model.geom_type[i] == mujoco.mjtGeom.mjGEOM_MESH
+                and model.geom_dataid[i] == palm_mesh
+                and (model.geom_contype[i] or model.geom_conaffinity[i]))
+    def pose(d):
+        return {'wrist_world_m': d.xpos[wrist].tolist(),
+                'grasp_center_world_m': d.site_xpos[grasp_site].tolist(),
+                'palm_world_m': d.geom_xpos[palm].tolist(),
+                'palm_to_bottle_center_m': float(np.linalg.norm(d.geom_xpos[palm] - actual.xpos[bottle]))}
+    result = {'sim_time_s': float(data.time), 'bottle_world_m': actual.xpos[bottle].tolist(),
+              'robot_base_quat_wxyz': actual.qpos[3:7].tolist(),
+              'robot_base_world_m': actual.qpos[:3].tolist(), 'actual': pose(actual)}
+    result['actual'].update(PalmProximity(model).measure(actual))
+    result['whole_hand_alignment'] = HandGraspAlignment(model).measure(actual)
+    result['bottle_quat_wxyz'] = actual.xquat[bottle].tolist()
+    result['bottle_tilt_deg'] = float(np.degrees(np.arccos(np.clip(actual.xmat[bottle].reshape(3, 3)[2, 2], -1, 1))))
+    bottle_joint = model.joint('red_bottle_free_joint').id
+    bottle_adr = model.jnt_qposadr[bottle_joint]
+    result['bottle_lift_from_initial_m'] = float(actual.xpos[bottle, 2] - model.qpos0[bottle_adr + 2])
+    bottle_geoms = [i for i in range(model.ngeom) if model.geom_bodyid[i] == bottle
+                    and (model.geom_contype[i] or model.geom_conaffinity[i])]
+    hand_geoms = [i for i in range(model.ngeom)
+                  if (model.body(int(model.geom_bodyid[i])).name.startswith('right_hand_')
+                      or i == palm)
+                  and (model.geom_contype[i] or model.geom_conaffinity[i])]
+    distances = [mujoco.mj_geomDistance(model, actual, a, b, 2.0, None)
+                 for a in bottle_geoms for b in hand_geoms]
+    result['nearest_hand_bottle_surface_m'] = float(min(distances)) if distances else None
+    result['hand_bottle_contacts'] = sum(
+        (c.geom1 in bottle_geoms and c.geom2 in hand_geoms) or
+        (c.geom2 in bottle_geoms and c.geom1 in hand_geoms) for c in actual.contact)
+    result['contacts'] = []
+    # Solver forces come from the running physics step, not the FK-only copy.
+    for i, contact in enumerate(data.contact):
+        hand = contact.geom2 if contact.geom1 in bottle_geoms else contact.geom1 if contact.geom2 in bottle_geoms else None
+        if hand is None or hand not in hand_geoms:
+            continue
+        force = np.zeros(6)
+        mujoco.mj_contactForce(model, data, i, force)
+        result['contacts'].append({'hand_body': model.body(int(model.geom_bodyid[hand])).name,
+                                   'normal_force_n': float(force[0])})
+    if joint_targets:
+        target = mujoco.MjData(model)
+        target.qpos[:] = actual.qpos
+        errors = {}
+        for joint_id, value in joint_targets.items():
+            adr = model.jnt_qposadr[joint_id]
+            target.qpos[adr] = value
+            errors[model.joint(joint_id).name] = float(value - actual.qpos[adr])
+        mujoco.mj_forward(model, target)
+        result['command_at_current_base'] = pose(target)
+        result['joint_target_minus_actual_rad'] = errors
+        result['actual_joint_q_rad'] = {model.joint(jid).name: float(actual.qpos[model.jnt_qposadr[jid]]) for jid in joint_targets}
+        result['palm_tracking_error_m'] = float(np.linalg.norm(target.geom_xpos[palm] - actual.geom_xpos[palm]))
+        result['grasp_tracking_error_m'] = float(np.linalg.norm(target.site_xpos[grasp_site] - actual.site_xpos[grasp_site]))
+    return result
diff --git a/gear_sonic/utils/mujoco_sim/viewer_overlay.py b/gear_sonic/utils/mujoco_sim/viewer_overlay.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/utils/mujoco_sim/viewer_overlay.py
@@ -0,0 +1,121 @@
+"""Submit native viewer overlays without waiting on the physics thread."""
+
+import base64
+import queue
+import time
+from threading import Event, Thread
+
+import mujoco
+import numpy as np
+
+
+def draw_detection(frame, detection, now):
+    """Overlay a recent measurement, never claim it tracks the current frame."""
+    import cv2
+    age = now - detection.get('capture_monotonic', 0.)
+    shape = detection.get('image_shape')
+    box = detection.get('bbox_xyxy')
+    if detection.get('status') != 'detected' or not 0 <= age <= .75 or shape is None or box is None:
+        cv2.putText(frame, 'YOLO: waiting / stale', (6, 36), cv2.FONT_HERSHEY_SIMPLEX,
+                    .4, (255, 220, 80), 1)
+        return
+    height, width = shape
+    scale = np.array([frame.shape[1]/width, frame.shape[0]/height]*2)
+    x1, y1, x2, y2 = np.rint(np.asarray(box)*scale).astype(int)
+    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
+    cv2.putText(frame, f"YOLO bottle {detection.get('confidence', 0.):.2f} | {age*1000:.0f} ms",
+                (6, 36), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 0), 1)
+
+
+class ViewerOverlayWorker:
+    def __init__(self, viewer):
+        self.viewer = viewer
+        self.camera_port = None
+        self.pending = queue.Queue(maxsize=1)
+        self.stopped = Event()
+        self.thread = Thread(target=self._run, name="viewer-overlays", daemon=True)
+        self.thread.start()
+
+    def submit(self, texts, detection):
+        try:
+            self.pending.put_nowait((texts, detection))
+        except queue.Full:
+            try:
+                self.pending.get_nowait()
+            except queue.Empty:
+                return
+            try:
+                self.pending.put_nowait((texts, detection))
+            except queue.Full:
+                pass
+
+    def _run(self):
+        import zmq
+        context = zmq.Context()
+        camera = None
+        self._camera_socket = None
+        try:
+            self._run_loop(context, camera)
+        finally:
+            if self._camera_socket is not None:
+                self._camera_socket.close(linger=0)
+            context.destroy(linger=0)
+
+    def _run_loop(self, context, camera):
+        import cv2
+        import msgpack
+        import zmq
+        from gear_sonic.utils.mujoco_sim.sensor_server import ImageUtils
+        preview, capture = None, None
+        texts, detection = [], {}
+        while not self.stopped.is_set() and self.viewer.is_running():
+            try:
+                texts, detection = self.pending.get(timeout=.02)
+            except queue.Empty:
+                pass
+            if camera is None and self.camera_port is not None:
+                camera = context.socket(zmq.SUB)
+                self._camera_socket = camera
+                camera.setsockopt(zmq.CONFLATE, 1)
+                camera.setsockopt_string(zmq.SUBSCRIBE, '')
+                camera.connect(f'tcp://127.0.0.1:{self.camera_port}')
+            # MuJoCo waits for its render thread to consume an overlay request.
+            # Only this worker may wait; DDS/physics must continue at 200 Hz.
+            self.viewer.set_texts(texts)
+            encoded = detection.get("preview_png") if camera is None else None
+            if camera is not None and camera.poll(0):
+                message = msgpack.unpackb(camera.recv(), raw=False)
+                capture = message.get('capture_monotonic', 0.)
+                rgb = ImageUtils.decode_image(message['images']['ego_view'])
+                preview = cv2.resize(rgb, (320, 240))
+            if camera is not None and preview is not None:
+                age = max(0., time.monotonic() - capture)
+                frame = preview.copy()
+                draw_detection(frame, detection, time.monotonic())
+                cv2.putText(frame, f'Camera | age {age*1000:.0f} ms', (6, 18),
+                            cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 255, 255), 1)
+                if age > 1.:
+                    cv2.putText(frame, 'STALE CAMERA', (6, 54), cv2.FONT_HERSHEY_SIMPLEX,
+                                .55, (255, 80, 80), 2)
+            else:
+                frame = None
+            if encoded and capture != detection.get("capture_monotonic"):
+                import cv2
+                decoded = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8), cv2.IMREAD_COLOR)
+                preview = decoded[:, :, ::-1].copy() if decoded is not None else None
+                capture = detection.get("capture_monotonic")
+            if (encoded or camera is not None) and preview is not None:
+                viewport = self.viewer.viewport
+                # The native viewer can disappear after is_running() above,
+                # for example while set_texts waits for the render thread.
+                # Its handle then returns None instead of a viewport.
+                if viewport is not None:
+                    self.viewer.set_images([(mujoco.MjrRect(viewport.left + max(0, viewport.width - 330),
+                        viewport.bottom + max(0, viewport.height - 250), 320, 240), frame if frame is not None else preview)])
+            else:
+                self.viewer.clear_images()
+            self.stopped.wait(.01)
+
+    def close(self):
+        self.stopped.set()
+        self.thread.join(timeout=1.)
diff --git a/gear_sonic/utils/perception/bottle_detector.py b/gear_sonic/utils/perception/bottle_detector.py
new file mode 100644
--- /dev/null
+++ b/gear_sonic/utils/perception/bottle_detector.py
@@ -0,0 +1,91 @@
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
+    if captured < scene_changed_at:
+        return {"status": "waiting_after_scene_change", "world_point_m": None}
+    if time.monotonic() - captured > max_age:
+        return {"status": "stale", "world_point_m": None}
+    return result
diff --git a/install_scripts/install_bottle_detector.sh b/install_scripts/install_bottle_detector.sh
new file mode 100644
--- /dev/null
+++ b/install_scripts/install_bottle_detector.sh
@@ -0,0 +1,17 @@
+#!/usr/bin/env bash
+# Small display-only detector; preserve existing GR00T / Torch versions.
+set -euo pipefail
+DETECTOR_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
+cd "$DETECTOR_ROOT"
+test -x .venv_inference/bin/python
+UV_CACHE_DIR=/tmp/sonic_detector_uv_cache uv pip install \
+    --python .venv_inference/bin/python --no-deps \
+    ultralytics==8.4.174 ultralytics-thop==2.2.2
+mkdir -p models/detectors
+if [[ ! -f models/detectors/yolo11n.pt ]]; then
+    curl -fL --retry 2 \
+        https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt \
+        -o models/detectors/yolo11n.pt.tmp
+    mv models/detectors/yolo11n.pt.tmp models/detectors/yolo11n.pt
+fi
+echo "Display-only detector ready: models/detectors/yolo11n.pt"
```
<!-- PATCH-WBC-END -->

## 13. Phụ lục code — bản vá Isaac-GR00T

SHA256-GR00T: `4430dac5912dc138ea92a70225885ff243107716580aa81c746a61a23899131a`

<!-- PATCH-GR00T-BEGIN -->
```diff
diff --git a/gr00t/policy/gr00t_policy.py b/gr00t/policy/gr00t_policy.py
index 6f5a46b..1af2433 100644
--- a/gr00t/policy/gr00t_policy.py
+++ b/gr00t/policy/gr00t_policy.py
@@ -106,7 +106,11 @@ class Gr00tPolicy(BasePolicy):
         model_dir = Path(model_path)
 
         # Load the pretrained model and move to target device with bfloat16 precision
-        model = AutoModel.from_pretrained(model_dir)
+        # Load at inference precision to avoid a full FP32 allocation followed
+        # by a BF16 copy while transferring the model to CUDA on WSL.
+        model = AutoModel.from_pretrained(
+            model_dir, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True
+        )
         model.eval()  # Set model to evaluation mode
         model.to(device=device, dtype=torch.bfloat16)
         self.model = model
```
<!-- PATCH-GR00T-END -->
