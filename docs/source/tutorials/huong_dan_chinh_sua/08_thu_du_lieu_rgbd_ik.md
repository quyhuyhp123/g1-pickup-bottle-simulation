# Thu dữ liệu gắp chai RGB-D + IK trong MuJoCo

## Phạm vi

Bổ sung ngày 26/10/2026. Đây là bộ ghi dữ liệu thô để chuẩn bị kiểm chứng quỹ đạo và xử lý tiếp, **chưa phải dataset LeRobot hoặc nhãn SONIC để fine-tune ngay**. Không có token giả/zero token trong bản ghi này. Giữ nguyên chương trình điều khiển thủ công.

## Những file bổ sung/sửa

| File | Thay đổi |
| --- | --- |
| `gear_sonic/utils/mujoco_sim/episode_recorder.py` | Recorder đồng bộ tại bước vật lý, ảnh camera robot và lệnh sau IK |
| `gear_sonic/utils/mujoco_sim/base_sim.py` | Gọi recorder sau giới hạn mômen, trước mj_step; kết thúc episode khi Reset/đóng |
| `gear_sonic/utils/mujoco_sim/configs.py` | Thêm cấu hình thư mục, prompt, FPS |
| `gear_sonic/scripts/run_sim_loop.py` | Truyền và kiểm tra cấu hình ghi |
| `gear_sonic/scripts/launch_inference.py` | Cờ ghi dữ liệu; tự tắt exporter C++ khi bật recorder mới |
| `gear_sonic/scripts/inspect_sim_episode.py` | Kiểm tra bản ghi, xuất MP4 xem lại, gán kết quả do người dùng đánh giá |
| `gear_sonic/tests/test_episode_recorder.py` | Kiểm tra chunk, timestamp, ctrl, ảnh và ranh giới episode |

Exporter cũ `run_data_exporter.py` lấy action/token từ C++ trước hiệu chỉnh IK trong simulation nên chưa phù hợp để gán nhãn chuyên gia IK. Giữ file đó cho luồng teleop gốc, không dùng để thu dataset này. `process_dataset.py` xử lý LeRobot/SMPL, không dùng cho định dạng raw mới. `run_blue_bottle_pickup.py` là bài IK lấy ground truth, không thay cho bài RGB-D.

## 1. Chạy

Đóng cửa sổ điều khiển thủ công và phiên simulation cũ trước. Nếu server cổng 5550 đã chạy đúng checkpoint thì giữ nguyên, không bật server thứ hai.

Terminal server:

```bash
cd ~/projects/GR00T-WholeBodyControl
bash gear_sonic/scripts/run_cloudwalk_policy_server.sh
```

Terminal simulation:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --sim-assisted-pickup --sim-fixed-base \
  --inspire-ftp-hands \
  --policy-host 127.0.0.1 --policy-port 5550 \
  --no-data-exporter \
  --record-dir outputs/ik_demonstrations \
  --record-fps 10 \
  --prompt "grab the bottle"
```

Không cần cài `.venv_data_collection` cho recorder mới. Dùng môi trường `.venv_sim` có MuJoCo, NumPy, OpenCV.

`--inspire-ftp-hands` là adapter checkpoint; không đổi bàn tay vật lý sang Inspire. Không thêm `--sim-native-inspire` nếu thu Dex3. `--record-dir` chỉ hợp lệ trong assisted simulation và tắt exporter C++ để tránh nhầm hai loại dữ liệu.

## 2. Ghi một lượt

1. Ở trạng thái chờ, đặt tọa độ chai và chuẩn bị camera/cảnh.
2. Bấm Start/F6. Recorder bắt đầu khi simulation rời standby, log `[Recorder] START ...` cho biết thư mục.
3. Để robot tiến tới, nắm, nâng và giữ ổn định vài giây. Có thể dùng Lower để ghi cả đặt/thu tay; prompt nên mô tả đúng nhiệm vụ nếu ghi cả chuỗi.
4. Bấm Reset/F5 khi hoàn tất. Recorder lưu **trước khi reset vật lý**, log `[Recorder] SAVED ...`.
5. Start lần nữa tạo thư mục episode mới. Đổi vị trí chai trong lúc chờ trước lượt tiếp theo.

Ghi được kết thúc khi chuyển về standby, Reset hoặc đóng simulator bình thường. Thay đổi cảnh/dựng lại chai khi đang chạy sẽ tách episode; nên Reset và bắt đầu lại thay vì sửa cảnh trong demonstration. Không dùng kill -9 hoặc tắt WSL khi đang ghi. Episode bị ngắt có status `recording`, công cụ kiểm tra sẽ từ chối.

Không có nút Record riêng: Start/Reset của simulation quản lý episode. Khi không muốn ghi, bỏ `--record-dir` và khởi chạy lại. Đừng để simulation chạy giữ chai quá lâu vì vẫn tiếp tục ghi mỗi bước vật lý.

## 3. Định dạng dữ liệu

```text
outputs/ik_demonstrations/episode_<date>_<id>/
  meta.json
  model.xml
  initial_state.npz
  states_000000.npz
  states_000001.npz
  ...
  rgb/000000.png
  rgb/000001.png
  ...
```

- `meta.json`: prompt, timestep, FPS yêu cầu, tên khớp/địa chỉ qpos/dof, actuator mapping, camera/FOV, số frame/sample, trạng thái và outcome. `training_ready=false` và `sonic_tokens_available=false` là chủ ý.
- `model.xml`: model snapshot có thể còn tham chiếu mesh gốc; giữ bộ assets của dự án. Không mặc định coi thư mục episode là bộ scene độc lập.
- `initial_state.npz`: qpos, qvel, act, warm-start, mocap, equality active và thời gian bắt đầu.
- Mỗi chunk chứa tối đa 200 bước vật lý, không giữ cả episode trong RAM.
- `qpos`, `qvel`: trạng thái đầy đủ bao gồm robot và chai, không chỉ 43 khớp.
- `ctrl`: **lệnh actuator thực tế sau IK và clipping**, áp dụng từ trạng thái cùng hàng đến bước kế tiếp. Đây không phải góc khớp và không phải motion_token.
- `assisted_arm_target`, `assisted_hand_target`: mục tiêu của controller, kèm joint ID mapping trong metadata; khi chưa khởi tạo controller dùng góc hiện tại.
- `stage`: giai đoạn controller. Chỉ số thành công controller là thông tin hỗ trợ, không tự gán nhãn thành công cho toàn episode.
- `qfrc_applied`, `xfrc_applied`: ngoại lực cần biết khi kiểm tra lại.
- `camera_xpos`, `camera_xmat`: vị trí và hướng camera trong world tại từng bước.
- `frame_id=-1`: bước không lấy ảnh. Nếu >=0 thì ảnh tương ứng có cùng trạng thái và timestamp `sim_time` trong hàng đó.

Ảnh RGB 640×480 từ `head_camera`, render trực tiếp ở pre-step state, độc lập camera tự do của viewer và luồng camera bất đồng bộ. Không quay bảng giao diện làm observation. Chưa lưu depth; hiện RGB, camera calibration và trạng thái vật lý được ghi để chuẩn bị train VLA/kiểm chứng. Tọa độ chai trong qpos là ground truth đánh giá, không mặc định là đầu vào VLA.

Tất cả góc trong raw là radian, tọa độ mét, thời gian giây simulation. Không lấy FPS video làm timestamp chính xác của vật lý.

## 4. Kiểm tra và tạo video

Thay đường dẫn episode bên dưới bằng đường dẫn trong log START/SAVED:

```bash
.venv_sim/bin/python gear_sonic/scripts/inspect_sim_episode.py \
  outputs/ik_demonstrations/episode_THAY_BANG_TEN_THUC_TE \
  --video
```

Công cụ kiểm tra trạng thái hoàn tất, số sample, tính hữu hạn, timestamp liên tục theo timestep, thứ tự frame, ảnh đầy đủ và kích thước. MP4 `review.mp4` chỉ để xem lại, được tạo ở FPS yêu cầu; timestamp raw mới là nguồn chính xác. Khi timestep không chia hết chu kỳ camera, video có thể lệch nhẹ thời lượng so với simulation.

Sau khi xem video và kiểm tra robot thật sự nâng/giữ chai:

```bash
.venv_sim/bin/python gear_sonic/scripts/inspect_sim_episode.py \
  outputs/ik_demonstrations/episode_THAY_BANG_TEN_THUC_TE \
  --outcome success
```

Dùng `--outcome failure` cho lượt thất bại, `--outcome discard` cho lượt thao tác/reset không hợp lệ. Các nhãn này chỉ sửa metadata, không xóa dữ liệu. Không gán success chỉ vì lệnh nâng đã được phát.

## 5. Hiệu năng và phạm vi kiểm chứng

Recorder dùng render và ghi PNG đồng bộ để giữ đúng ảnh–trạng thái, nên có thể làm simulation chậm theo thời gian thực. Bắt đầu với 10 FPS; có thể giảm `--record-fps 5`. Physics sample vẫn được ghi ở mọi bước. Dung lượng tăng theo thời gian ghi; thử một episode ngắn trước, chưa thu hàng trăm lượt.

Đã kiểm thử chunk 205 bước, giữ ctrl đúng thứ tự, tách episode, phát hiện ảnh thiếu; đã chạy render camera thật của model G1 qua EGL và xuất MP4 thử. Chưa xác nhận một lượt gắp hoàn chỉnh qua server với recorder bật trong phiên này.

Không có thay đổi thuật toán gắp/IK trong đợt bổ sung recorder. Replay qua SONIC, chuyển dataset LeRobot, nhãn motion_token, chia tập và fine-tune là bước tiếp theo sau khi có dữ liệu thử đạt kiểm tra. Việc chỉ đổi định dạng file không giải quyết được nhãn token.

## 6. Replay vật lý bằng lệnh đã ghi

Công cụ `gear_sonic/scripts/replay_sim_episode.py` chạy độc lập, không cần server,
DDS, GR00T, SONIC hoặc IK. Nó nạp XML và trạng thái ban đầu, giữ ràng buộc weld
trong model, áp dụng `ctrl` và ngoại lực từng bước. Không chép qpos từ dataset
vào robot ở các bước tiếp theo. So sánh trạng thái trước bước vật lý với hàng
pre-step tương ứng của recorder.

Chạy kiểm tra không mở cửa sổ:

```bash
.venv_sim/bin/python gear_sonic/scripts/replay_sim_episode.py \
  outputs/ik_demonstrations/episode_20261026_224629_65003197
```

Mở cửa sổ để xem robot làm lại (đóng simulation khác nếu không dùng để giảm tải):

```bash
.venv_sim/bin/python gear_sonic/scripts/replay_sim_episode.py \
  outputs/ik_demonstrations/episode_20261026_224629_65003197 \
  --viewer --speed 1
```

`--speed 0.5` hiển thị chậm một nửa; timestep vật lý không thay đổi. Viewer tự
đóng khi chạy hết episode. Nếu đóng sớm, báo cáo ghi `complete=false`.

Kết quả trong thư mục episode:

- `replay_report.json`: số bước, sai lệch lớn nhất, độ nâng, thời điểm bắt đầu lệch.
- `replay_report.csv`: sai lệch từng bước.

Chạy lại ghi đè hai báo cáo này, không thay dữ liệu raw. Dùng `--report /tmp/report.json`
để chọn nơi khác. `trajectory_match=true` yêu cầu đủ số bước và sai lệch dưới
0,05 rad cho khớp hinge, 0,02 m cho vị trí chai; đây là ngưỡng chẩn đoán, không phải
chứng nhận gắp thành công hoặc token SONIC hợp lệ. Muốn đánh giá nhiệm vụ vẫn cần
xem động tác và độ nâng/giữ. Raw v1 chưa ghi thay đổi equality/mocap theo từng bước,
nên các lượt có can thiệp runtime có thể không tái hiện được chính xác.

Đã chạy headless episode `episode_20261026_224629_65003197`: đủ 3181 bước,
sai lệch lớn nhất của góc hinge và vị trí chai bằng 0 trong phép đo, độ nâng
0,18770 m. Đây là kiểm chứng replay mômen, chưa kiểm chứng encoder/decoder SONIC.

## 7. Token SONIC thử nghiệm từ quỹ đạo (27/10/2026)

Đã thêm `gear_sonic/scripts/encode_sim_episode.py`. Cần ONNX Runtime CPU:

```bash
uv pip install --python .venv_sim/bin/python onnxruntime==1.23.2
.venv_sim/bin/python gear_sonic/scripts/encode_sim_episode.py \
  outputs/ik_demonstrations/episode_20261026_224629_65003197
```

Script yêu cầu replay_report có trajectory_match=true. Nó lấy qpos/qvel thực tế,
ánh xạ 29 khớp theo thứ tự IsaacLab từ tên body/joint (không lấy 29 cột đầu của
qpos), lấy mẫu 50 Hz. Mỗi token dùng 10 mốc tương lai cách nhau 5 frame và hướng
base tương lai tương đối với base hiện tại. Giữ heading theo world của bản ghi,
không thêm offset heading. Hướng biểu diễn bằng hai cột đầu ma trận xoay, flatten
row-major như gatherer C++. Các nhánh teleop/SMPL không dùng để zero theo bộ lọc
mode g1 của deploy. Chỉ hỗ trợ layout legacy đã kiểm tra 1762 chiều.

Kết quả trong `sonic_candidate/tokens.npz` và `sonic_candidate/report.json`:

- `motion_token`: N×64, kết quả encoder thật; chưa phải nhãn đã xác nhận.
- `encoder_input`: đầu vào để kiểm toán.
- `source_row`, `sim_time`: ánh xạ về mẫu vật lý; ảnh chỉ có ở một số hàng raw.
- `full_future_window`: False ở cuối đoạn không đủ 0,9 giây tương lai; các mốc
  vượt cuối được kẹp về frame cuối như deploy.
- Metadata có hash model/config, danh sách khớp, `training_ready=false` và
  `sonic_validated=false`.

Episode 22:46:29 tạo 796 token 64 chiều. Không ghi đè raw. Chạy lại script ghi
đè thư mục sonic_candidate của cùng episode.

**Chưa chuyển thành dataset train.** Decoder hiện tại nhận 994 chiều: ngoài token
còn cần lịch sử trạng thái/actions và chuẩn hóa đúng như deployment; đầu ra là
29 actions, không phải tái tạo trực tiếp vector encoder. Bước tiếp theo cần dựng
rollout decoder đúng quy ước và kiểm tra quỹ đạo/nắm với IK tắt. Token hữu hạn
không chứng minh decoder tái hiện động tác hoặc tương thích quy ước tay v10.

## 8. Rollout decoder chẩn đoán, không dùng IK

```bash
.venv_sim/bin/python gear_sonic/scripts/rollout_sonic_episode.py \
  outputs/ik_demonstrations/episode_20261026_224629_65003197
```

Chương trình chạy headless, không kết nối DDS/robot thật. Đọc tham số góc mặc định,
scale, Kp/Kd và ánh xạ khớp từ `policy_parameters.hpp`. Input 994 chiều gồm token
64 và lịch sử 10 frame của vận tốc góc base, góc khớp trừ default, vận tốc khớp,
action trước và gravity trong base. Lịch sử xếp cũ đến mới; khởi tạo lặp trạng thái
đầu với action trước bằng 0. Decoder chạy 50 Hz; các bước vật lý vẫn theo timestep
đã ghi. Thân/cánh tay do decoder điều khiển; tay phải dùng mục tiêu ngón đã ghi,
tay trái giữ góc đầu. Không áp lại ctrl thân hoặc ngoại lực của demonstration.
Weld pelvis vẫn có trong XML; đây chưa phải thử cân bằng free-base.

Mặc định bù bias cánh tay như tùy chọn simulation; `--no-arm-bias` để tắt.
Đây là **bản chẩn đoán**, chưa chứng minh tương đương hoàn toàn với deploy:
không tái lập DDS timing/gain overrides; token ngoại tuyến dùng base của expert,
không cập nhật encoder theo base của rollout. Không dùng kết quả này để kết luận
chắc chắn model không có khả năng gắp.

Báo cáo ghi trong `sonic_candidate/rollout_report.json` và `rollout_errors.csv`.
Chạy lại ghi đè các báo cáo này. Không sửa raw hoặc tự bật training_ready.

Kết quả thử episode 22:46:29: đủ 3181 bước, sai lệch khớp tối đa 0,73037 rad,
chai lệch tối đa 2,32392 m, cuối lượt thấp hơn ban đầu 0,77504 m. Replay ctrl
trước đó khớp hoàn toàn nhưng rollout decoder này không gắp/nâng thành công.
Do đó chưa chuyển các candidate thành nhãn train được xác nhận. Cần kiểm chứng
độ tương đương với deploy, điều kiện khởi động và khả năng bám reference trước.

### Kiểm toán rollout theo khớp

`rollout_sonic_episode.py` hiện lưu thêm `rollout_joint_diagnostics_repeat.npz`
(reference/actual/target theo thứ tự joint_names) và `rollout_report_repeat.json`.
`--history-seed zero` thử đệm lịch sử khởi động bằng 0 như trường hợp thiếu mẫu
trong StateLogger, với gravity hướng xuống. Đây chỉ là thử độ nhạy vì lịch sử
thực tế trước Start chưa được ghi lại.

Với episode 22:46:29, sai lệch tối đa 0,73037 rad thuộc **left_knee_joint**,
ở khoảng 12,08 s: reference ≈0, actual=0,73037, target=0,65777 rad.
Sai lệch vượt 0,05 rad xuất hiện từ 0,02 s, không phải chỉ khi chạm chai.
Thử lịch sử zero vẫn thất bại: max error=0,79944 rad, peak lift=0,09712 m.
Tay phải cũng còn lệch: wrist_pitch tối đa 0,6187 rad, elbow 0,3083 rad.
Không thể giải thích toàn bộ lỗi chỉ bằng khớp gối.

Đã đối chiếu thứ tự history (cũ→mới), trừ default góc khớp, ánh xạ action,
scale/Kp/Kd và nguồn quaternion/gyro với gatherer/SDK bridge. Các phép kiểm tra
này chưa chứng minh tương đương toàn bộ chương trình deploy.

`audit_sonic_reference.py` chạy reference macarena 1375 frame qua encoder/decoder
với trạng thái reference cấp trực tiếp (teacher-forced):

```bash
.venv_sim/bin/python gear_sonic/scripts/audit_sonic_reference.py \
  gear_sonic_deploy/reference/example/macarena_001__A545
```

Kết quả ở `outputs/sonic_reference_audit`. Sai lệch target so với reference không
phải sai số bám vật lý vì target PD có thể cần đi trước quỹ đạo. Phép thử này chưa
phải rollout vật lý đối chứng chuyển động chuẩn; `physics_validated=false`.
Không dùng các kết quả này để đánh dấu dataset training_ready.

### Đối chứng vật lý reference và điều kiện train

Đã bổ sung `prepare_sonic_reference_probe.py`: dựng bản thử riêng trong
`outputs/sonic_reference_physics`, từ reference macarena và model G1, tắt equality
weld và va chạm props bàn/chai để không cản chuyển động. Không ghi vào dataset
expert, không tạo replay_report giả. Khởi tạo thân/base từ reference; lịch sử
trước frame đầu vẫn chưa có. FPS reference đang giả định 50 Hz theo deploy;
metadata CSV không đủ để tự chứng minh nguồn FPS/đời checkpoint khớp model hiện tại.

```bash
.venv_sim/bin/python gear_sonic/scripts/audit_sonic_reference.py \
  gear_sonic_deploy/reference/example/macarena_001__A545
.venv_sim/bin/python gear_sonic/scripts/prepare_sonic_reference_probe.py
.venv_sim/bin/python gear_sonic/scripts/rollout_sonic_episode.py \
  outputs/sonic_reference_physics --no-arm-bias
```

Phép thử 5500 bước cũng lệch: max joint error 1,49099 rad, lớn nhất ở cổ tay
trái pitch. Đây là bằng chứng công cụ/model/reference hiện tại chưa tạo được
baseline đáng tin cậy; không chứng minh nguyên nhân nằm ở demonstration chai.
Các metric chai bị loại khỏi báo cáo reference vì không có ý nghĩa trong bài này.

Môi trường train hiện có RTX 5070 12 GB. Isaac-GR00T có launcher và checkpoint v10,
nhưng chưa khởi chạy fine-tune: chưa xác nhận nhãn token qua baseline và quy ước
7 chiều Inspire của v10 không đồng nghĩa 7 góc Dex3. Không điền zero token hoặc
đổi tên các góc Dex3 thành nhãn Inspire để ép dataset hợp lệ. Cần giải quyết hợp
đồng hành động và baseline trước khi đánh dấu training_ready. Chưa tạo checkpoint
huấn luyện từ 10 episode.

### Rollout giữ chân và các khớp không tham gia gắp — 27/10/2026

`rollout_sonic_episode.py --body-control manipulation` chỉ cho SONIC điều khiển
`waist_pitch_joint` và 7 khớp cánh tay phải. Hai chân, tay trái, eo yaw/roll (21
khớp) dùng PD 100/4 cộng bias để giữ góc ban đầu của episode. Không ghi đè qpos
mỗi bước và không áp lại mục tiêu cánh tay của IK. Ngón tay phải dùng mục tiêu
đã ghi; tay trái giữ mục tiêu đầu. Weld base lấy từ model và phải đang active.
Đây là điều khiển thao tác có giữ thân, không phải toàn thân do SONIC điều khiển.

```bash
.venv_sim/bin/python gear_sonic/scripts/rollout_sonic_episode.py \
  outputs/ik_demonstrations/episode_20261026_224629_65003197 \
  --body-control manipulation
```

`--body-control auto` là mặc định: episode chai dùng manipulation; synthetic
reference probe dùng full. `--body-control full` tái hiện phép thử điều khiển
29 khớp cũ. Báo cáo mới đặt riêng trong `sonic_candidate/rollout_manipulation/`
hoặc `sonic_candidate/rollout_full/`, không ghi đè báo cáo cũ ở thư mục cha.
`target` trong NPZ là góc decoder đề xuất; `applied_target` là góc sau ghi đè
mục tiêu giữ tư thế cho 21 khớp. History last_action vẫn giữ đầu ra decoder thô
như deploy, không diễn giải nó là action thực đã áp dụng cho các khớp giữ.

Đã chạy lại hai episode và kiểm tra applied_target: 21 khớp giữ mục tiêu cố định,
8 khớp nhận đúng mục tiêu decoder. Kết quả vẫn chưa gắp thành công:

| Episode | Max error toàn thân | Khớp lệch lớn nhất | Trôi tối đa khớp giữ | Dịch base tối đa |
| --- | --- | --- | --- | --- |
| 22:46:29 | 0,62737 rad | right_wrist_pitch_joint | 0,04743 rad | 0,01769 m |
| 22:47:32 | 0,87655 rad | right_wrist_pitch_joint | 0,03771 rad | 0,01815 m |

Các khớp giữ vẫn có sai số thực tế vì PD/weld mềm và giới hạn mômen; không gọi
đây là bất động tuyệt đối. Cả hai lượt chỉ nâng tối đa khoảng 3 mm. Kết quả cho
thấy loại mục tiêu SONIC ở chân không đủ khắc phục lỗi tiếp cận/nắm ở tay.
Dataset/token vẫn chưa được đánh dấu training_ready.

## 9. Clean dữ liệu gắp–nâng, giữ raw gốc

Đã chạy `clean_sim_demonstrations.py` cho 10 episode người dùng xác nhận thành
công. Kết quả ở `outputs/ik_clean_pickup_v1`: 8 train, 2 validation, seed 42,
không chia frame cùng episode sang hai tập. Đây là split theo lượt, chưa bảo đảm
các tọa độ chai train và validation khác nhau.

```bash
.venv_sim/bin/python gear_sonic/scripts/clean_sim_demonstrations.py \
  --source outputs/ik_demonstrations \
  --output outputs/ik_clean_pickup_v2 \
  --user-confirmed-success-all
```

Cờ xác nhận chỉ dùng khi đã xem và chấp nhận toàn bộ episode trong source.
Script từ chối ghi đè thư mục output có sẵn và từ chối outcome failure/discard.
Không sửa hoặc xóa raw. Mỗi selection có hash nguồn, hash ảnh và bằng chứng
outcome là metadata hoặc xác nhận người dùng.

Cấu trúc:

```text
ik_clean_pickup_v1/
  manifest.json
  README.md
  train.txt
  validation.txt
  episodes/<episode>/
    samples.npz
    selection.json
    rgb/<frame_id_goc>.png
    source_meta.json
    source_model.xml
    source_initial_state.npz
    source_replay_report.json
```

`label_window` chọn approach/close/lift/hold và tối đa 2 giây success. Bỏ đoạn
chờ khỏi nhãn, bỏ transfer/lower/release/retreat/return_home. Giữ tối đa 0,9 giây
ngữ cảnh hai bên khi có sẵn nhưng không đi vào giai đoạn đặt chai. Không tự bù
frame thiếu ở cuối. `source_row`, timestamp và frame ID vẫn theo raw. `-1` nghĩa
là không có ảnh tại bước đó; ảnh không có tần suất 200 Hz như vật lý.

Hai lượt 22:56:31 và 22:57:24 kết thúc ở hold (2,5 s và khoảng 1,9 s), chưa đạt
stage success. Chúng được giữ dựa trên xác nhận video của người dùng; selection
có `controller_success_seen=false` và ghi chú để xem xét riêng. Không tạo nhãn
controller success giả. Validation seed42 gồm lượt 22:57:24 và 22:58:21.

Kết quả: 28.236 mẫu giữ lại, trong đó 26.421 mẫu thuộc cửa sổ nhãn, 1.413 ảnh.
Đã kiểm tra hash nguồn/ảnh và ranh giới nhãn của cả 10 lượt; 4 unit tests đạt.
`source_initial_state.npz` là trạng thái đầu raw, không phải đầu đoạn đã cắt;
replay vật lý vẫn dùng episode gốc. Không copy sonic_candidate token vào clean.
Bản clean vẫn `training_ready=false`: cần xác minh SONIC và quy ước nhãn tay
trước khi chuyển sang LeRobot/fine-tune.

## 10. Chuyển sang dataset GR00T và train thử pipeline (27/10/2026)

### 10.1. Mục tiêu và giới hạn của lượt này

Tiếp tục từ bản clean ở mục 9, chuẩn bị dữ liệu để GR00T v10 thực sự đọc được
và kiểm tra một số bước optimizer trên GPU. SONIC encoder/decoder vẫn giữ nguyên
trọng số. Các token hiện là **candidate**, vì rollout ở mục 8 chưa tái hiện được
động tác gắp. `training_ready=false`, `sonic_validated=false` vẫn được giữ.

Train thử ở đây xác nhận đường đi ảnh/state/action → loss → backward → cập nhật
trọng số → lưu file. Nó chưa xác nhận chất lượng policy hoặc tỷ lệ gắp thành công.
Không dùng loss của ba bước để kết luận model đã học được gắp chai. Chưa cần thu
lại 10 episode chỉ vì bài kiểm tra SONIC đang lệch; phải xác minh đường encoder,
decoder và controller trước.

### 10.2. Các file thêm trong lượt này

| File | Chức năng |
| --- | --- |
| `gear_sonic/scripts/export_gr00t_candidate_dataset.py` | Ghép raw đã clean với token theo `source_row`, xuất LeRobot v2.1: MP4, Parquet và metadata |
| `gear_sonic/scripts/validate_gr00t_candidate_dataset.py` | Dùng loader và video decoder thực tế của Isaac-GR00T để đọc toàn bộ train/validation, tính thống kê từng tập |
| `gear_sonic/scripts/train_gr00t_candidate_smoke.py` | Nạp v10, train thử lớp `action_head.action_decoder`, lưu trọng số riêng và báo cáo |
| `gear_sonic/tests/test_gr00t_candidate_export.py` | Kiểm tra camera quá khứ, camera stale, quaternion/gravity, thứ tự nhóm khớp giống RobotModel và cờ experimental |

Tài liệu được tổng hợp tiếp vào file số 8 này. Các thay đổi trên không tự thay
checkpoint mà chương trình simulation đang dùng.

### 10.3. Những xử lý dữ liệu đã làm

1. Tạo token ứng viên đủ 10 raw episode bằng `encode_sim_episode.py`.
2. Giữ split 8 train / 2 validation của bản clean, không chia frame cùng lượt
   sang hai tập.
3. Action lấy ở 50 Hz, chọn từ `label_window` và nối token bằng chỉ số dòng raw.
   Kiểm tra timestamp và 29 góc khớp mà encoder đã dùng trùng với raw hiện tại.
4. Bỏ token thiếu 0,9 giây cửa sổ tương lai. Đồng thời giới hạn cửa sổ trong đoạn
   clean, tránh token ở cuối động tác gắp chứa cả chuyển động đặt/hạ chai.
5. Ảnh gốc 10 Hz được giữ ảnh gần nhất đã chụp khi xuất video 50 Hz. Một ảnh có
   thể xuất hiện nhiều frame; không tạo thêm thông tin thị giác. `camera_age_s`
   trong Parquet lưu độ cũ của ảnh. Từ chối ảnh tương lai hoặc cũ hơn 0,101 s.
6. State 46 chiều: chân trái 6, chân phải 6, eo 3, tay trái 7, tay phải 7,
   bàn tay trái 7, bàn tay phải 7, projected gravity 3. Tên/thứ tự nhóm khớp đã
   đối chiếu với `g1_supplemental_info.py`. Bàn tay trong state theo thứ tự
   **index, middle, thumb**, giống `prepare_observation_for_eval`. State tay trái
   áp dụng coupling giống code suy luận hiện tại.
7. Action 78 chiều: motion token 64 + tay trái 7 + tay phải 7. Hai bàn tay dùng
   thứ tự motor **thumb, middle, index**, góc radian Dex3. Tay phải lấy
   `assisted_hand_target` đã ghi; tay trái dùng tư thế giữ ban đầu theo quy ước
   fixed-pickup controller. Đây là quy ước dữ liệu thử nghiệm được ghi trong
   `export_report.json`; chưa có kiểm thử replay toàn bộ action mới qua deploy.
8. **Không dùng `ctrl` làm action GR00T**: `ctrl` là torque thực thi trong MuJoCo,
   không phải token hay góc đích của ngón tay.
9. Tính thống kê train riêng; validation không tham gia normalization của lượt
   train. Hai episode validation chỉ dùng kiểm tra loader trong lượt này.

**Phân biệt với CloudWalk v10:** cùng hình dạng action không có nghĩa cùng ý nghĩa.
Nhãn tay của dataset này là Dex3 radian, khác grip Inspire chuẩn hóa của v10.
Khi kiểm thử policy đã fine-tune trên dữ liệu này, phải dùng đúng quy ước Dex3 và
không áp lại adapter Inspire. Script train thử hiện lưu file trọng số từng phần,
chưa nối vào launcher simulation.

### 10.4. Lệnh tái tạo

Chạy từ thư mục repository. Lệnh cần môi trường Isaac-GR00T đã cài các thư viện
của repo đó (pandas, pyarrow, OpenCV, TorchCodec, PyTorch). Không cài lại PyTorch
hoặc download một checkpoint thứ hai nếu cache đã có.

Tạo token những lượt chưa có:

```bash
cd ~/projects/GR00T-WholeBodyControl
for episode in outputs/ik_demonstrations/episode_*; do
  if [ -f "$episode/meta.json" ] && [ ! -f "$episode/sonic_candidate/tokens.npz" ]; then
    .venv_sim/bin/python gear_sonic/scripts/encode_sim_episode.py "$episode" || break
  fi
done
```

Xuất dataset vào **thư mục mới**, ví dụ khi cần tạo lại:

```bash
../Isaac-GR00T/.venv/bin/python \
  gear_sonic/scripts/export_gr00t_candidate_dataset.py \
  --clean outputs/ik_clean_pickup_v1 \
  --output outputs/gr00t_dex3_candidate_moi \
  --experimental-unvalidated-sonic
```

Bản đã kiểm tra trong lượt này nằm ở `outputs/gr00t_dex3_candidate_v3`. Các bản
v1/v2 là trung gian đã xóa sau khi chốt v3. Kiểm tra bản v3:

```bash
PYTHONPATH=../Isaac-GR00T ../Isaac-GR00T/.venv/bin/python \
  gear_sonic/scripts/validate_gr00t_candidate_dataset.py \
  outputs/gr00t_dex3_candidate_v3
```

Kết quả đọc được ghi vào `loader_validation.json`. Dataset có hai thư mục độc lập:

```text
outputs/gr00t_dex3_candidate_v3/
  export_report.json
  loader_validation.json
  train/
    meta/{info.json,modality.json,stats.json,episodes.jsonl,tasks.jsonl}
    data/chunk-000/episode_000000.parquet
    videos/chunk-000/observation.images.ego_view/episode_000000.mp4
  validation/
    meta/...
    data/...
    videos/...
```

Chạy lại một lượt optimizer thử, chọn tên output chưa tồn tại:

```bash
PYTHONPATH=../Isaac-GR00T ../Isaac-GR00T/.venv/bin/python \
  gear_sonic/scripts/train_gr00t_candidate_smoke.py \
  --dataset outputs/gr00t_dex3_candidate_v3 \
  --checkpoint checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000 \
  --output outputs/gr00t_dex3_smoke_moi \
  --steps 3 \
  --learning-rate 1e-5 \
  --experimental-unvalidated-sonic
```

Cấu hình: batch 1; backbone bfloat16; chỉ lớp xuất action trainable ở float32;
VLM, diffusion transformer và SONIC đóng băng. Chỉ nhận 1–20 bước để tránh nhầm
script smoke với một job train đầy đủ. Chạy offline bằng model đã cache. Các link
trong `source_checkpoint/` và `cached_backbone/` chỉ trỏ về model hiện có, không
copy nhiều GB trọng số.

Script tránh ba lỗi gặp khi thử môi trường hiện tại:

- Tokenizer vẫn hỏi metadata Hub dù `local_files_only`: dùng đường dẫn snapshot
  local để không yêu cầu đăng nhập/tải model lại.
- Bộ chọn backbone upstream xét chuỗi tên model: đường dẫn local vẫn giữ phần
  `nvidia/Cosmos-Reason2-2B`.
- Registry chứa embodiment khác có action horizon 50: chỉ truyền modality config
  `unitree_g1_sonic` với horizon 40 trong job này.

Output `action_decoder_only.safetensors` chỉ chứa tham số lớp đã cập nhật. Không
truyền file này vào `--model-path` của server; nó chưa phải checkpoint policy đầy
đủ. `processor/` chứa normalization mới và quy ước dataset, phải đi kèm trọng số
khi phát triển bước đóng gói/đánh giá sau.

### 10.5. Kết quả đã chạy, không phải lệnh dự kiến

- Bản dataset dùng: `outputs/gr00t_dex3_candidate_v3`, khoảng 32 MB.
- Train: **8 episode, 4.972 dòng action ở 50 Hz**.
- Validation: **2 episode, 1.188 dòng action ở 50 Hz**.
- Tổng: 6.160 dòng/video frame xuất; ảnh gốc vẫn 10 Hz. Các đuôi bị loại ở bước
  export giải thích vì sao số dòng ít hơn số physics sample trong clean.
- Loader GR00T đọc đủ 10/10 episode, giải mã MP4 thành RGB 480×640×3,
  kiểm tra các vector hữu hạn, đúng kích thước. Báo cáo:
  `outputs/gr00t_dex3_candidate_v3/loader_validation.json`.
- Train thử thành công ở `outputs/gr00t_dex3_smoke_v4/`:

| Step | Loss | Gradient norm trước clipping |
| --- | --- | --- |
| 1 | 1,644565 | 18,441229 |
| 2 | 1,460574 | 17,230026 |
| 3 | 1,563189 | 17,724670 |

Có 37.916.800 tham số trainable trong lớp xuất action (gồm các nhánh embodiment
của lớp này). Max thay đổi trọng số là `3,00705e-5`; peak CUDA allocated khoảng
6,53 GiB, không phải tổng VRAM gồm các chương trình khác. Loss chưa đơn điệu và
ba mẫu không đủ kết luận hội tụ.

```text
outputs/gr00t_dex3_smoke_v4/
  smoke_report.json
  action_decoder_only.safetensors
  processor/
  experiment_cfg/
  source_checkpoint/    # view bằng symlink tới checkpoint v10 gốc
  cached_backbone/      # view bằng symlink tới Hugging Face cache
```

Các lượt smoke v1/v2/v3 là log lỗi môi trường/cấu hình trước khi sửa; lượt thành
công là **v4**. File log ngoài thư mục:
`outputs/gr00t_dex3_smoke_v4.log`.

### 10.6. Phần tiếp theo trước một job fine-tune dài

1. Đối chiếu token/decoder với deploy SONIC để replay action của expert đạt lại
   tiếp cận–nắm–nâng; xác nhận cả góc ngón tay Dex3 mới. Đây là tiêu chí action
   học được có thực thi được hay không. File format đúng không thay thế bước này.
2. Khi qua bước đó, tạo dataset chính thức có báo cáo SONIC đã xác minh; giữ
   validation tách theo episode và thêm kiểm thử tọa độ chai chưa thấy khi train.
3. Mở rộng từ train lớp xuất action sang projector/diffusion hoặc LoRA theo VRAM.
   Chọn checkpoint bằng đánh giá trên tập giữ lại và rollout simulation, không
   chỉ nhìn train loss. Chưa chạy bước này vì lỗi rollout vẫn tồn tại.
4. Đóng gói checkpoint đầy đủ, processor và quy ước Dex3; sau đó kiểm thử luồng
   ảnh + lệnh + state → GR00T → motion token/ngón tay → SONIC → MuJoCo, tắt
   hiệu chỉnh RGB-D/IK khi đo chất lượng policy.

Hiện chưa cần tự quay lại toàn bộ dữ liệu. Raw và bản clean vẫn được giữ để
có thể tái xuất token sau khi sửa đường SONIC mà không mất ảnh/trajectory gốc.

Kiểm tra cuối: 10 unit tests (6 export + 4 clean) đạt; toàn bộ hash ảnh clean
khớp; trọng số safetensors đọc lại được. Loader validation có hash các artifact;
script train từ chối dataset đã đổi sau validation. Hai bản dataset trung gian
v1/v2 do lượt này tạo đã xóa, giữ bản v3; dữ liệu raw/clean được giữ nguyên.

## 11. Khắc phục rollout bằng token khớp decoder (27/10/2026)

### 11.1. Kết quả mới

**Đã phát lại thành công 10/10 episode gắp–nâng qua SONIC decoder với token đã
hiệu chỉnh offline.** Lượt replay kiểm chứng đọc token từ file; không chạy IK,
không tối ưu token, không đưa trực tiếp target tay expert vào motor trong lượt đó.
Lệnh ngón tay Dex3 vẫn lấy từ demonstration như một phần action phải học của VLA.

Điều kiện kiểm chứng là `fixed_base_dex3_pd80_3_v1`:

- Khởi tạo **một lần** từ trạng thái đã ghi ở đầu approach; không ghi đè qpos theo
  trajectory ở các bước sau.
- Giữ fixture pelvis đã có trong model, giữ chân/tay trái và eo yaw/roll bằng
  PD 100/4 + bias. Không dùng constraint gắn chai vào tay.
- SONIC điều khiển target eo pitch + 7 khớp tay phải. Controller các khớp này dùng
  PD 80/3 + bias như lúc thu dữ liệu, thay cho gain SONIC mặc định trong deploy.
- Chai chuyển động do tiếp xúc vật lý. Không áp lực ngoài vào chai. Lực hỗ trợ
  startup chỉ được phép phục hồi trước khi tác vụ active; replay bắt đầu ở
  approach không cần lực hỗ trợ này.
- Tiêu chí pass: sai số mọi khớp thân <0,05 rad và sai số vị trí chai <0,02 m;
  chai được nâng trên 0,12 m, còn tiếp xúc ngón cái và index/middle ở hai phía,
  tương đối thẳng đứng, giữ liên tục ít nhất 1 s; cuối lượt vẫn cao hơn 0,10 m.

Đây chưa phải chứng nhận chạy whole-body tự do hoặc robot thật. Checkpoint GR00T
v10 gốc chưa thay đổi; nó chưa tự dự đoán được bộ token mới. Bước fine-tune sau
sẽ học ảnh + câu lệnh + state → token mới và lệnh ngón tay.

### 11.2. Điều tra đã làm và lỗi tìm được

Đã đối chiếu thứ tự khớp, scale/default angles, history, encoder layout với C++
và đồ thị ONNX. Thử đảo history, thay history của khớp bị giữ, cập nhật orientation
encoder theo base hiện tại và thay gain riêng lẻ đều chưa làm token encoder cũ
nâng được chai. Không kết luận lỗi X/Y hoặc buộc người dùng quay lại dữ liệu.

Một lỗi trong phép replay kiểm tra đã được xác định: raw v1 có thể giữ target
cũ khi controller còn `idle`. Áp những target này ngay từ đầu làm tay chuyển động
và đóng sai lúc. Startup cũng có lực hỗ trợ pelvis ở một số mẫu idle; nó khác
với lực tác vụ. Đã sửa gating trạng thái và phục hồi đúng warmstart khi có.

Sau khi sửa, phép kiểm tra controller với target expert cho episode 22:47:32 đạt:
max joint error khoảng 0,00233 rad, chai cuối lượt cao hơn khoảng 0,19091 m.
Phép kiểm tra này chỉ dùng xác nhận controller/vật lý; **không gọi nó là SONIC
replay thành công**, vì target arm trong phép kiểm tra đó đến trực tiếp từ expert.

Khi thay lại bằng token encoder ban đầu, decoder vẫn đưa ra target tay lệch lớn.
Vì vậy chỉ tăng stiffness hoặc khóa chân không giải quyết được toàn bộ vấn đề.

### 11.3. Phương pháp hiệu chỉnh token mới

File thêm: `gear_sonic/scripts/refine_sonic_episode.py`.

1. Đọc đúng trọng số MLP từ decoder ONNX, dựng bản tính gradient tương đương trong
   PyTorch, giữ toàn bộ trọng số đóng băng. Kiểm tra parity output với ORT ở từng
   mẫu; sai số action lớn nhất ghi nhận khoảng `7,63e-6`.
2. Lấy token encoder làm seed. Tối ưu **64 giá trị token**, dùng Jacobian của
   decoder để target 8 khớp đang hoạt động khớp target expert đã ghi. Đây là bước
   tạo nhãn offline; không fine-tune SONIC, không dùng tọa độ chai để chạy IK.
3. Chạy vật lý trong lúc tạo nhãn để history được lấy từ chính robot đang chạy;
   không thay qpos liên tục bằng state expert. Dùng token trước để warm-start,
   hạn chế bước Newton, kiểm tra lỗi target và parity.
4. Lưu token và chạy một lượt MuJoCo **mới** bằng ORT, chỉ đọc token đã lưu. Lượt
   kiểm chứng không gọi optimizer và `target_source` phải là `decoder`.
5. Chỉ chấp nhận nếu lượt đọc lại token đạt cả tracking và gắp–nâng vật lý.

Vì token đã đổi, không lấy số liệu mới để tuyên bố encoder G1 hoặc v10 cũ đã tự
được sửa. Các báo cáo cũ vẫn giữ nguyên. Nhãn mới có profile controller cụ thể,
không trộn âm thầm với token CloudWalk/Inspire hoặc whole-body tự do.

### 11.4. File đã thêm/sửa và báo cáo

| File | Thay đổi |
| --- | --- |
| `gear_sonic/scripts/rollout_sonic_episode.py` | Sửa idle/stale target, warmstart; thêm chọn phase, controller, target source, file token, output và video; kiểm tra tiếp xúc/nâng/giữ; giữ tương thích synthetic reference probe cũ |
| `gear_sonic/scripts/refine_sonic_episode.py` | Tạo token mới qua decoder đóng băng, kiểm tra parity và replay độc lập; ghi hash nguồn/token; xóa bản weights tạm sau khi dùng |
| `gear_sonic/scripts/export_gr00t_candidate_dataset.py` | Thêm `--refined-root`, chỉ dùng token có replay pass đúng profile, kiểm tra hash và nối theo source row; giữ nguyên split train/validation |
| `gear_sonic/tests/test_sonic_token_refinement.py` | Kiểm tra token tối ưu ra target đúng và từ chối gradient model không khớp decoder |

Kết quả từng episode:

| Episode (giờ) | Max lỗi khớp (rad) | Độ nâng cuối (m) | Replay |
| --- | --- | --- | --- |
| 22:38:32 | 0,011273 | 0,184182 | PASS |
| 22:46:29 | 0,012152 | 0,188880 | PASS |
| 22:47:32 | 0,011812 | 0,190850 | PASS |
| 22:48:41 | 0,006489 | 0,137567 | PASS |
| 22:56:31 | 0,011266 | 0,184303 | PASS |
| 22:57:24 | 0,010991 | 0,184056 | PASS |
| 22:58:21 | 0,000690 | 0,188829 | PASS |
| 22:59:18 | 0,008413 | 0,190059 | PASS |
| 23:00:24 | 0,004234 | 0,184431 | PASS |
| 23:02:16 | 0,008707 | 0,183921 | PASS |

Thời gian giữ chai nâng cao với tiếp xúc đối diện: khoảng 2,98–6,13 s. Sai số
lớn nhất 0,012152 rad tương đương khoảng 0,70 độ. Không dùng kết quả này thay cho
kiểm tra policy GR00T chạy closed-loop từ ảnh.

Báo cáo:

```text
outputs/sonic_rollout_fix/
  all_episodes/summary.json
  all_episodes/<episode>/
    refinement_report.json
    fit_trace.json
    fitting_rollout/executed_tokens.npz
    saved_token_replay/rollout_report.json
    saved_token_replay/rollout_errors.csv
  video_replay/rollout_report.json
  sonic_saved_token_pickup.mp4
```

Video đã quay từ lượt replay ORT của episode 22:47:32, 253 frame ở 20 FPS. Đã
xem lại frame ở giây thứ 10: robot giữ chai phía trên mặt bàn. Khi có thêm đoạn
đặt/hạ trong raw, `--pickup-only` kết thúc trước transfer/lower/release/retreat;
không coi việc đặt lại chai trong raw là thất bại của tác vụ gắp–nâng.

File đang mở cũ `outputs/sonic_reference_physics/sonic_candidate/rollout_report.json`
là benchmark synthetic whole-body/free-base khác. Không dùng nó để đánh giá lượt
gắp cố định mới; hãy mở `saved_token_replay/rollout_report.json` ở đường dẫn trên.

### 11.5. Chạy lại một lượt từ token đã lưu

Không cần GR00T server cho phép kiểm chứng action-label này:

```bash
cd ~/projects/GR00T-WholeBodyControl
PYTHONPATH=. .venv_sim/bin/python gear_sonic/scripts/rollout_sonic_episode.py \
  outputs/ik_demonstrations/episode_20261026_224732_945f99be \
  --start-stage approach \
  --controller collection \
  --pickup-only \
  --tokens-file outputs/sonic_rollout_fix/all_episodes/episode_20261026_224732_945f99be/fitting_rollout/executed_tokens.npz \
  --output-dir outputs/sonic_rollout_fix/replay_tu_kiem_tra
```

Muốn ghi video mới trong môi trường headless hỗ trợ EGL:

```bash
MUJOCO_GL=egl PYTHONPATH=. .venv_sim/bin/python \
  gear_sonic/scripts/rollout_sonic_episode.py \
  outputs/ik_demonstrations/episode_20261026_224732_945f99be \
  --start-stage approach --controller collection --pickup-only \
  --tokens-file outputs/sonic_rollout_fix/all_episodes/episode_20261026_224732_945f99be/fitting_rollout/executed_tokens.npz \
  --output-dir outputs/sonic_rollout_fix/replay_co_video \
  --video-path outputs/sonic_rollout_fix/replay_co_video/pickup.mp4
```

Để tạo lại token cho một episode vào **output mới**, cần GPU PyTorch hoạt động:

```bash
PYTHONPATH=. .venv_sim/bin/python gear_sonic/scripts/refine_sonic_episode.py \
  outputs/ik_demonstrations/episode_20261026_224732_945f99be \
  --output outputs/sonic_rollout_fix/refine_moi
```

### 11.6. Dataset dùng cho bước fine-tune tiếp theo

Đã xuất bộ mới `outputs/gr00t_dex3_refined_v1`: 8 train, 2 validation; 4.972 dòng
train và 1.188 dòng validation. Dùng ảnh/state đã clean, thay phần 64 token bằng
nhãn mới đã qua replay; góc Dex3 giữ quy ước mục 10. Không sửa raw hoặc bộ candidate
v3 trước đó.

Trong `export_report.json`, `training_ready_for_fixed_base_profile=true` cùng
`execution_profile_id=fixed_base_dex3_pd80_3_v1` xác nhận phạm vi đã kiểm chứng.
Các cờ chung `training_ready`/`sonic_validated` vẫn false để không nhầm rằng đã
kiểm chứng whole-body, mọi gain controller, robot thật hay checkpoint v10 gốc.

Lệnh tái xuất (output mới) và kiểm tra:

```bash
../Isaac-GR00T/.venv/bin/python \
  gear_sonic/scripts/export_gr00t_candidate_dataset.py \
  --clean outputs/ik_clean_pickup_v1 \
  --refined-root outputs/sonic_rollout_fix/all_episodes \
  --output outputs/gr00t_dex3_refined_moi \
  --experimental-unvalidated-sonic

PYTHONPATH=../Isaac-GR00T ../Isaac-GR00T/.venv/bin/python \
  gear_sonic/scripts/validate_gr00t_candidate_dataset.py \
  outputs/gr00t_dex3_refined_v1
```

Cờ experimental ở đây vẫn giữ vì mới xác minh profile gắp cố định. Loader GR00T
đã đọc thành công đủ 10 episode của bản refined. Khi chuyển sang train thử tiếp,
đổi `--dataset` thành `outputs/gr00t_dex3_refined_v1`; không dùng lại candidate v3
hoặc checkpoint action-decoder-only của lượt smoke cũ để kết luận chất lượng nhãn mới.

### 11.7. Kiểm tra train sau khi đổi nhãn

Đã chạy lại 3 bước optimizer bằng **dataset refined**, output ở
`outputs/gr00t_dex3_refined_smoke_v1/smoke_report.json`:
loss lần lượt `1,386679`, `1,306291`, `1,486743`; gradient hữu hạn, max thay đổi
trọng số khoảng `3,00705e-5`. Chỉ lớp xuất action được cập nhật như mục 10; chưa
đóng gói policy GR00T đầy đủ hoặc đo tỷ lệ gắp của model đã fine-tune.

Như vậy phần kiểm tra action-label ở mục 10.6 bước 1 đã đạt trong **profile cố
định** nêu ở mục 11.1. Lộ trình tiếp theo có thể dùng nhãn refined để fine-tune và
đánh giá VLA closed-loop. Không cần quay lại toàn bộ demonstration vì lỗi token cũ.

Có thể kiểm tra lại train ngắn bằng lệnh sau, dùng output mới:

```bash
PYTHONPATH=../Isaac-GR00T ../Isaac-GR00T/.venv/bin/python \
  gear_sonic/scripts/train_gr00t_candidate_smoke.py \
  --dataset outputs/gr00t_dex3_refined_v1 \
  --output outputs/gr00t_dex3_refined_smoke_moi \
  --experimental-unvalidated-sonic
```

Kiểm tra tự động cuối lượt: 14 tests (refinement, mask giữ khớp, export và clean)
đạt; 10 replay độc lập và replay quay video đạt. Báo cáo tổng gọn:
`outputs/sonic_rollout_fix/rollout_fix_summary.json`. Trọng số SONIC gốc không đổi;
raw và clean giữ nguyên. Các file NPZ weights trích tạm khi tối ưu đã được xóa.

## 12. Fine-tune GR00T v10 trên nhãn đã kiểm chứng

### 12.1. Cấu hình lượt fine-tune đầu tiên

Script: `gear_sonic/scripts/finetune_gr00t_g1.py`.
Dataset: `outputs/gr00t_dex3_refined_v1`, giữ nguyên 8 episode train và 2 episode
validation. Khởi tạo từ `checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000`.

Cấu hình cho RTX 5070 12 GB VRAM:

- 500 optimizer steps; micro-batch 1; tích lũy gradient 2, effective batch 2.
- Learning rate ban đầu `1e-4`, warmup 20 bước, giảm cosine; seed 42.
- LoRA rank 8 trên các Linear attention/FFN trong action diffusion transformer.
- Chỉ học slice projector state/action của embodiment G1; các embodiment khác
  giữ trọng số cũ. Có 17.389.700 tham số được học trong lượt này.
- VLM và SONIC đóng băng. Đây là fine-tune VLA/action head, chưa fine-tune VLM
  để mở rộng ngôn ngữ hoặc thêm nhận diện táo/Rubik.
- Trọng số nền bfloat16, tham số cập nhật float32; checkpoint activation của
  transformer blocks để giảm bộ nhớ. Không cần cài bitsandbytes.
- Validation mỗi 50 bước trên 16 cửa sổ cố định: 8 mỗi episode validation.
  Chọn trọng số có validation flow-matching loss thấp nhất, dùng cùng seed noise
  cho các lần so sánh. Tập validation không tham gia tính normalization train.
- Không chép toàn bộ checkpoint mỗi lần lưu. Giữ adapter tốt nhất/cuối; cuối
  lượt merge LoRA và projector G1 thành checkpoint Hugging Face thông thường.

Vì action horizon là 40, training sampler có 4.660 điểm bắt đầu hợp lệ trong
4.972 dòng train. Không padding/chạy vượt cuối trajectory. Video giải mã đúng
frame được chọn, cache hữu hạn; không nạp đồng thời mọi frame 50 Hz vào RAM WSL.

### 12.2. Lệnh chạy lại

Chọn thư mục output **mới**; script từ chối ghi đè một lượt có sẵn:

```bash
cd ~/projects/GR00T-WholeBodyControl
PYTHONPATH=../Isaac-GR00T ../Isaac-GR00T/.venv/bin/python \
  gear_sonic/scripts/finetune_gr00t_g1.py \
  --dataset outputs/gr00t_dex3_refined_v1 \
  --checkpoint checkpoints/cloudwalk_g1_bottle_v10/checkpoint-30000 \
  --output outputs/gr00t_g1_dex3_finetune_moi \
  --steps 500 --accumulation 2 --rank 8 \
  --learning-rate 1e-4 --eval-every 50
```

Lượt đã chạy nằm ở `outputs/gr00t_g1_dex3_finetune_v1`. Theo dõi:

```bash
tail -f outputs/gr00t_g1_dex3_finetune_v1.log
```

`Ctrl+C` ở lệnh `tail` chỉ dừng theo dõi log. Trạng thái, loss và bước hiện tại
nằm trong `outputs/gr00t_g1_dex3_finetune_v1/training_report.json`.

### 12.3. Các file thêm cho fine-tune

| File | Chức năng |
| --- | --- |
| `gear_sonic/scripts/finetune_gr00t_g1.py` | Fine-tune LoRA + projector G1, chọn best bằng validation, merge và lưu checkpoint đầy đủ |
| `gear_sonic/scripts/evaluate_finetuned_g1.py` | Nạp checkpoint đã merge bằng Gr00tPolicy, kiểm tra output và đo lỗi action trên validation |
| `gear_sonic/tests/test_g1_finetune_layers.py` | Kiểm tra merge LoRA đúng hàm và merge projector chỉ thay embodiment G1 |

Test lớp adapter/merge:

```bash
../Isaac-GR00T/.venv/bin/python -m unittest \
  gear_sonic.tests.test_g1_finetune_layers
```

Checkpoint cuối có processor, thống kê normalization và `simulation_profile.json`
đi kèm. Giữ nguyên `cached_backbone/` của lượt train vì config trỏ tới model nền
đã cache qua đường dẫn local. Chưa tự upload lên Hugging Face/GitHub.

### 12.4. Cách đánh giá checkpoint đã lưu

```bash
PYTHONPATH=.:../Isaac-GR00T ../Isaac-GR00T/.venv/bin/python \
  gear_sonic/scripts/evaluate_finetuned_g1.py \
  --checkpoint outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best \
  --dataset outputs/gr00t_dex3_refined_v1 \
  --output outputs/gr00t_g1_dex3_finetune_v1/evaluation
```

Đánh giá này kiểm tra nạp model theo đường Gr00tPolicy đang dùng ở server, input
RGB/state/câu lệnh và output motion token 64 + hai bàn tay 7, chunk 40 bước. RMSE
token/ngón tay là phép đo open-loop so với nhãn; không quy đổi thành tỷ lệ gắp chai.
Sau đó mới thử VLA closed-loop với đúng fixture/gain và quy ước Dex3 đã train.

Model mới xuất **Dex3 joint radians**. Không dùng adapter `--inspire-ftp-hands`
cho model này. Launcher baseline CloudWalk hiện có quy ước Inspire và control
whole-body khác; không tự coi lệnh simulation cũ tương thích với checkpoint mới.
Việc nối runtime phải giữ profile `fixed_base_dex3_pd80_3_v1`, tắt RGB-D/IK và cho
lệnh ngón tay đi trực tiếp từ policy. Trọng số v10 gốc và runtime cũ không bị thay
thế tự động trong bước fine-tune này.

### 12.5. Kết quả đã chạy xong

Lượt `gr00t_g1_dex3_finetune_v1` hoàn tất 500 bước trong khoảng **5 phút 28 giây**.
Checkpoint được chọn ở bước 500:

| Chỉ số | Kết quả |
| --- | --- |
| Validation flow loss trước train | 1,402045 |
| Validation flow loss checkpoint chọn | 0,138523 |
| Validation flow loss sau merge | 0,138436 |
| Peak CUDA allocated trong job | khoảng 6,22 GiB |
| Trọng số được fine-tune | 17.389.700 tham số |
| Checkpoint đầy đủ đã lưu | khoảng 5,9 GiB |

File model để nạp:

```text
outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best/
  config.json
  model-00001-of-00002.safetensors
  model-00002-of-00002.safetensors
  model.safetensors.index.json
  processor_config.json
  statistics.json
  embodiment_id.json
  simulation_profile.json
```

Đây là checkpoint đầy đủ đã merge, khác các file action-decoder-only của lượt
smoke ở mục 10/11. Các file `best_adapter.safetensors` và `last_adapter.safetensors`
trong thư mục cha là phần tham số học, không dùng chúng làm `--model-path`.

Đã nạp checkpoint trên bằng **Gr00tPolicy** trong tiến trình mới và suy luận 16
cửa sổ của hai episode validation. Output đúng shape, giá trị hữu hạn. Đo open-loop:

- RMSE motion token: khoảng **0,05896** (đơn vị latent, không phải mét/radian).
- RMSE 7 khớp bàn tay phải: khoảng **0,16225 rad**.
- Báo cáo: `outputs/gr00t_g1_dex3_finetune_v1/evaluation/evaluation_report.json`.
- Dự đoán/nhãn đối chiếu: cùng thư mục, `predictions.npz`.

Các giá trị này không phải độ chính xác nhận diện và không chứng minh model đã
nâng chai thành công. `closed_loop_pickup_validated=false` được giữ cho đến khi
thử policy mới với đúng controller profile trong MuJoCo.

### 12.6. Chạy server với checkpoint đã fine-tune

Dùng cổng 5551 để tách khỏi server v10 cũ có thể đang chiếm 5550:

```bash
cd ~/projects/GR00T-WholeBodyControl
HF_HUB_OFFLINE=1 PYTHONPATH=../Isaac-GR00T \
  ../Isaac-GR00T/.venv/bin/python ../Isaac-GR00T/gr00t/eval/run_gr00t_server.py \
  --model-path "$PWD/outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best" \
  --embodiment-tag UNITREE_G1_SONIC \
  --device cuda:0 \
  --host 127.0.0.1 --port 5551
```

Client test tương ứng phải dùng `--policy-port 5551`, bàn tay Dex3 radians và
profile `fixed_base_dex3_pd80_3_v1`. Không dùng lại adapter Inspire hoặc controller
whole-body mặc định rồi quy sai lệch của cấu hình khác thành lỗi checkpoint.
Lệnh trên khởi động inference server; phần nối vào nút Start/Reset và đánh giá
pickup closed-loop là bước tiếp theo, chưa được đánh dấu hoàn tất ở lượt này.

Toàn bộ việc đã làm ở bước fine-tune: kiểm tra dataset/hash, chọn cấu hình VRAM,
train 500 bước, đánh giá định kỳ trên validation tách biệt, chọn best, merge,
lưu đầy đủ model/processor, nạp lại và suy luận validation. Model nguồn, raw,
SONIC và cấu hình simulation đang chạy không bị thay thế tự động.

## 13. Tích hợp model mới → SONIC → simulation, không RGB-D/IK

### 13.1. Lệnh chạy có giao diện

Đã thêm chế độ riêng cho checkpoint đã fine-tune. Chạy từ repository:

```bash
cd ~/projects/GR00T-WholeBodyControl
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim \
  --sim-finetuned-policy \
  --no-data-exporter \
  --prompt "grab the bottle"
```

**Chỉ cần lệnh này.** Nó tự mở server model mới và simulation. Không cần bật
server v10 riêng. Nếu đang chạy một server model cũ ở terminal khác, dừng nó trước
để dành VRAM cho model mới. Server chế độ này mặc định dùng cổng riêng 5551; nếu
cổng đó đang có tiến trình khác, launcher chọn cổng trống tiếp theo cho cả client
và server mà nó sở hữu, không tắt tiến trình của người dùng.

Có hai cửa sổ: viewer robot và panel Start/Reset/tọa độ chai.

1. Đợi panel xác minh và nạp model; trong lúc chờ robot giữ nguyên tư thế.
2. Có thể nhập Bottle X/Y rồi bấm **Apply bottle X/Y** khi đang chờ. Z cố định
   theo mặt bàn. Giá trị được kiểm tra trong giới hạn mặt bàn.
3. Bấm **Start** hoặc **F6** để model bắt đầu điều khiển.
4. Bấm **Reset all** hoặc **F5** để đưa robot, chai và trạng thái điều khiển về
   đầu lượt. Reset giữ X/Y đã Apply, xóa action chunk, last-action và history SONIC;
   kết quả suy luận đang chạy thuộc lượt cũ bị loại bằng generation ID.
5. Chuột phải kéo để xoay góc nhìn, giữ nút giữa kéo để pan, lăn chuột để zoom.
   Đóng viewer hoặc bấm Esc để dừng; launcher đóng cả server mà nó tự mở.

Không dùng `--inspire-ftp-hands`, `--sim-assisted-pickup`, `--sim-fixed-base` hay
proximity override cùng chế độ này. Những tổ hợp đó bị từ chối để tránh trộn các
luồng điều khiển. Fixture/gain của model mới được lấy từ profile checkpoint,
không chọn bằng các cờ của bộ điều khiển IK cũ.

Chọn checkpoint hoặc vị trí chai khác, ví dụ:

```bash
.venv_inference/bin/python gear_sonic/scripts/launch_inference.py \
  --sim --sim-finetuned-policy --no-data-exporter \
  --finetuned-model-path outputs/gr00t_g1_dex3_finetune_v1/checkpoint-best \
  --sim-bottle-xy 0.40 -0.05 \
  --prompt "grab the bottle"
```

Model v1 chỉ được train với số lượng ít trajectory; việc nhập X/Y mới không bảo
đảm gắp được ở mọi vị trí. X/Y này chỉ đặt vật trong MuJoCo, không truyền vào
policy hoặc dùng để tính target tay.

### 13.2. Luồng điều khiển thực tế

```text
MuJoCo head_camera RGB 640×480 + các góc khớp/gravity + prompt
                           ↓ ZMQ
              GR00T checkpoint-best đã fine-tune
                  ↙                       ↘
       motion_token 64                7+7 góc Dex3 (radian)
              ↓                              ↓
     SONIC model_decoder.onnx          motor target trực tiếp
     history 10 frame, 50 Hz                  ↓
              ↓                              ↓
       29 target khớp                    PD bàn tay
              ↓                              ↓
 profile cố định: 8 khớp theo SONIC, 21 khớp giữ tư thế chờ
              ↓                              ↓
                         MuJoCo
```

- RGB/state cùng một trạng thái vật lý: gọi `mj_forward` trước khi render và đóng
  gói observation. Input chỉ có `video`, `state`, `language`; không có depth,
  bbox, object XYZ, goal XYZ hoặc target từ detector.
- Lệnh ngón tay đi thẳng từ model, không đổi grip Inspire sang Dex3, không tự đóng
  khi đến gần chai, không chốt đóng/mở theo tọa độ.
- SONIC là decoder ONNX đã dùng trong kiểm chứng mục 11, chạy qua ONNX Runtime.
  Kiểm tra SHA256 decoder để tránh dùng nhầm phiên bản SONIC có cùng kích thước.
- Đây là runtime Python/ONNX riêng cho profile đã train; không chạy tmux stack
  C++/DDS và các adapter baseline CloudWalk trong chế độ này.
- Profile `fixed_base_dex3_pd80_3_v1`: pelvis weld, 21 khớp giữ home bằng PD,
  eo pitch + 7 khớp tay phải lấy target SONIC, PD 80/3+bias. Ngón tay PD 8/0,2+bias.
  Đây là low-level actuation/fixture, không phải bộ lập kế hoạch nắm.
- Runtime không đọc raw episode, NPZ token expert, file replay hoặc optimizer.
  Chai vẫn free body; không weld vào tay, không tạo lực ngoài nâng chai.

Checkpoint đã được đóng gói thêm `simulation_scene.xml` và cấu hình tư thế chờ,
nhóm khớp, action scale/default angles vào `simulation_profile.json`. Đây là
**cảnh tĩnh và một tư thế ban đầu**; không có chuỗi chuyển động mẫu để phát lại.
Mesh asset của robot vẫn nằm trong repository. Đổi camera góc nhìn ở viewer không
đổi `head_camera` mà policy nhận. Model v1 được train cho gắp chai; panel này chỉ
Start/Reset, không nối tác vụ Lower của controller IK cũ vào luồng model.

Server có endpoint metadata riêng. Client kiểm tra fingerprint config/processor/
statistics/index/profile và contract native Dex3 trước khi cho phép Start, tránh
vô tình nối vào server v10 hoặc checkpoint khác đang mở ở cổng cũ.

### 13.3. Timing suy luận và GUI

Model xuất 40 bước action, runtime thực thi 10 bước ở 50 Hz trước khi lấy ảnh và
state mới để suy luận tiếp. Mặc định dùng 16 bước diffusion và seed sampling 42
để các lượt có thể tái lập. Đây là thiết lập lấy mẫu của model, không thêm bộ nắm.

Ở ranh giới chunk, bước vật lý tạm chờ kết quả mới; GUI vẫn xử lý sự kiện trên
main thread. Cách này giữ đúng thời điểm ảnh/state/action thay vì bỏ qua đoạn
approach khi inference chậm. Thời gian simulation có thể chạy chậm hơn thời gian
thực. Panel hiển thị thời gian simulation và latency để phân biệt việc chờ model
với lỗi đơ giao diện.

Viewer mới dùng GLFW trên main thread và giải phóng tài nguyên OpenGL đúng thứ
tự trước khi đóng cửa sổ. Đã sửa lỗi segfault khi đóng passive viewer đồng thời
với offscreen renderer. Camera pan/zoom dùng API `mjv_moveCamera` 5 tham số của
MuJoCo hiện có, đã có test cho thao tác nút giữa.

### 13.4. Những file đã sửa/thêm

| File | Nội dung |
| --- | --- |
| `gear_sonic/scripts/launch_inference.py` | Thêm `--sim-finetuned-policy` và `--finetuned-model-path`; chuyển thẳng sang runtime mới, từ chối trộn các override cũ |
| `gear_sonic/scripts/run_finetuned_sim.py` | Launcher/server/client MuJoCo cho checkpoint mới; native Dex3, SONIC ONNX, Start/Reset, scene X/Y, viewer, trace và báo cáo |
| `gear_sonic/tests/test_finetuned_sim_integration.py` | Kiểm tra chặn chế độ trộn, metadata checkpoint/hand, Reset bỏ chunk cũ, camera pan và object position chỉ ảnh hưởng input qua RGB |
| `outputs/.../checkpoint-best/simulation_profile.json` | Bổ sung cấu hình controller, home, state joint groups, scale/default và SHA SONIC |
| `outputs/.../checkpoint-best/simulation_scene.xml` | Snapshot cảnh tĩnh của robot/bàn/chai đúng cấu hình vật lý lúc train |

Không thêm một file MD riêng; toàn bộ hướng dẫn tiếp tục ghi trong tài liệu số 8.

### 13.5. Kiểm tra đã chạy và giới hạn của checkpoint v1

Đã chạy headless closed-loop và GUI thực tế. Kiểm tra tích hợp + regression liên
quan: **19 tests đạt**. GUI chạy model, hiển thị và đóng sạch với exit code 0.

Lượt cuối: `outputs/finetuned_policy_sim/integration_final/`:

- 15 giây simulation, 75 lần gọi model và 750 bước SONIC.
- `forbidden_modules_loaded=[]`: không nạp assisted pickup, detector, optimizer
  token hay bộ IK mẫu trong tiến trình simulation.
- `ik_enabled=false`, `detector_enabled=false`, `recorded_actions_used=false`,
  `hand_adapter="none / native Dex3 radians"`.
- Token và góc ngón tay thay đổi theo output model, không dùng standing token cố
  định. Trace có metadata server, input state và hash RGB của từng lần hỏi model.
- Lượt cuối **chưa đạt nắm–nâng–giữ** (`pickup_success=false`). Chai bị đổ; độ nâng
  lớn nhất khoảng 0,00168 m. Một lượt cấu hình lấy mẫu trước đó có nâng thoáng qua
  khoảng 9,5 cm rồi rơi, vẫn không được tính là thành công.

Vì vậy kết luận đúng là **đã tích hợp và chạy được luồng model mới → SONIC →
robot**, còn chất lượng closed-loop của checkpoint v1 chưa ổn định. Kết quả
10/10 ở mục 11 là replay **nhãn token đã hiệu chỉnh**, không phải 10/10 của VLA.
Không sử dụng thuật toán RGB-D/IK để thay output model trong các lượt trên.

Trong quá trình kiểm tra, giả thuyết “góc ngón 0 nghĩa là tay chưa mở” đã được
đối chiếu lại: với cấu hình Dex3 trong dữ liệu này, 0 là pose mở. Không coi giả
thuyết đó là nguyên nhân đã sửa thành công. Tư thế startup được đóng gói chính
xác để khớp đầu approach; lỗi chất lượng còn lại cần xử lý ở model/đánh giá dữ liệu.

### 13.6. Log, video và lệnh kiểm tra không có GUI

Mỗi lần chạy bình thường tạo thư mục:

```text
outputs/finetuned_policy_sim/session_YYYYMMDD_HHMMSS/
  server.log
  run_report.json
  actions.jsonl
```

`run_report.json` phân biệt `status` (luồng chạy có kết thúc đúng hay không) và
`pickup_success` (kết quả vật lý). `status=complete` không có nghĩa gắp thành công.

Chạy kiểm tra tự động và ghi video:

```bash
PYTHONPATH=. .venv_sim/bin/python gear_sonic/scripts/run_finetuned_sim.py \
  --headless --auto-start --duration 15 --video \
  --output outputs/finetuned_policy_sim/test_moi
```

Đọc `run_report.json`, `actions.jsonl` và `policy_simulation.mp4` trong output đó.
Bản được dùng cho test cuối hiện có:
`outputs/finetuned_policy_sim/integration_final/run_report.json` và video cùng
thư mục. Lệnh dùng GPU của PC; không kết nối hoặc phát lệnh đến robot thật.

Đã mở thử bằng đúng lệnh launcher có `--sim-finetuned-policy`: server được xác
minh (`server_verified=true`), robot đang standby tại thời gian 0 với 0 lượt
inference trước Start. Phiên GUI xác minh trong lượt tích hợp này:
`outputs/finetuned_policy_sim/session_20261027_235000/`.

## 14. Đưa checkpoint và 10 episode lên Hugging Face

Script đóng gói và upload:
`gear_sonic/scripts/publish_finetuned_huggingface.py`.
Hai repository được tạo ở chế độ **private** trong tài khoản `quyhuyhp123`:

- Model: <https://huggingface.co/quyhuyhp123/gr00t-n17-g1-dex3-bottle-sim-v1>.
- Dataset: <https://huggingface.co/datasets/quyhuyhp123/g1-dex3-bottle-mujoco-10episodes-v1>.

Đã upload và kiểm tra hoàn tất ngày 28/10/2026:

- Model commit: `973b899d3378c9477c9b46bf4c6b8448298bd1cc`, 72 file được
  kiểm tra (gồm manifest), khoảng 6,32 GB.
- Dataset commit: `26fbe968fe9a8d2b3633206ed9d3bf0f10c7e991`, 203 file được
  kiểm tra (gồm manifest), khoảng 318 MB.
- Đã đối chiếu kích thước/checksum LFS và tải lại index episode, config,
  processor và simulation profile từ đúng commit để so sánh với bản local.

Có thể truyền `revision='<commit ở trên>'` vào `snapshot_download` để lấy
đúng bản này ngay cả khi repository được cập nhật sau đó. Phải đăng nhập
`quyhuyhp123` hoặc tài khoản được cấp quyền khi mở các link private.

Model gồm checkpoint đã merge, cấu hình/processor/statistics, home pose,
scene/mesh với đường dẫn tương đối, báo cáo train/eval/closed-loop, mã nguồn
runtime và hướng dẫn tải lại. `model_name` trong **bản đóng gói** trỏ đến
`nvidia/Cosmos-Reason2-2B` thay cho đường dẫn tuyệt đối của máy thu dữ liệu.
Các file checkpoint đang dùng tại máy và trọng số SONIC không bị sửa.
SONIC vẫn phải được cài qua dự án gốc; không được tải lại trong gói này.

Dataset gồm:

- `raw/episode_*.tar.gz`: 10 episode gốc, từng archive có ảnh RGB, trạng thái
  vật lý, pose ban đầu, XML và báo cáo replay; giữ nguyên byte của dữ liệu.
- `previews/episode_*.mp4`: 10 video camera. Bốn video review có sẵn được
  giữ lại; sáu video còn thiếu được encode từ PNG vào riêng gói upload.
- `refined/train` và `refined/validation`: đúng dataset đã dùng để train,
  8/2 episode, 4.972/1.188 dòng. Không cần giải nén raw để dùng dataset này.
- `provenance/`: báo cáo clean/refine/replay và token offline đã kiểm chứng.
- `code/`: mã thu, kiểm tra, replay, xử lý dữ liệu và fine-tune.
- `manifest.json`: kích thước và SHA-256 của từng file đóng gói.

Hai model/dataset card ghi rõ: demo được thu bằng RGB-D/IK; runtime của model
mới chỉ dùng GR00T → SONIC → robot; model v1 chưa đạt nắm/nâng ổn định trong
closed-loop. Không dùng kết quả replay 10/10 để khẳng định policy đạt 10/10.

### 14.1. Chuẩn bị hoặc tiếp tục upload

```bash
cd ~/projects/GR00T-WholeBodyControl

# Chỉ chuẩn bị gói local, chưa upload:
../Isaac-GR00T/.venv/bin/python \
  gear_sonic/scripts/publish_finetuned_huggingface.py

# Upload gói đã chuẩn bị; chạy lại lệnh này nếu mạng gián đoạn:
../Isaac-GR00T/.venv/bin/python \
  gear_sonic/scripts/publish_finetuned_huggingface.py --resume --upload
```

Đọc kết quả ở `outputs/huggingface_release_v1/release_report.json`.
Chỉ khi `status` là `uploaded_and_verified` thì cả hai repo đã hoàn tất và
được kiểm tra danh sách file/kích thước/checksum LFS. Các commit ID được ghi
trong báo cáo để tải lại đúng phiên bản. Log upload của lượt thực hiện:
`outputs/huggingface_upload_v1.log`.

Gói local dùng hard link cho trọng số lớn để tránh sao chép thêm khoảng
5,9 GiB; không sửa file trọng số trong thư mục đóng gói vì hard link dùng
chung inode với nguồn. Archive/video mới chiếm thêm khoảng 300 MB.

### 14.2. Tải lại model và dataset

Đăng nhập đúng tài khoản đã được cấp quyền bằng `hf auth login` trước khi
tải các repository private. Không gửi token vào chat hoặc commit vào Git.

```bash
cd ~/projects/GR00T-WholeBodyControl
../Isaac-GR00T/.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    'quyhuyhp123/gr00t-n17-g1-dex3-bottle-sim-v1',
    local_dir='outputs/hf_gr00t_g1_dex3_v1',
)
snapshot_download(
    'quyhuyhp123/g1-dex3-bottle-mujoco-10episodes-v1',
    repo_type='dataset',
    local_dir='outputs/hf_g1_dex3_dataset_v1',
)
PY

# Kiểm tra checksum model và cache backbone trước khi chạy offline:
../Isaac-GR00T/.venv/bin/python \
  outputs/hf_gr00t_g1_dex3_v1/restore_release.py

# Trên checkout chưa có runtime mới, copy code được đóng gói:
cp -a outputs/hf_gr00t_g1_dex3_v1/code/gear_sonic/. gear_sonic/
.venv_sim/bin/python gear_sonic/scripts/run_finetuned_sim.py \
  --model-path outputs/hf_gr00t_g1_dex3_v1 \
  --prompt "grab the bottle"
```

Vẫn cần môi trường `.venv_sim`, sibling `../Isaac-GR00T/.venv` và decoder
SONIC đúng hash như mục 13. Lệnh restore có thể cần bạn chấp nhận điều khoản
truy cập backbone NVIDIA trên Hugging Face bằng tài khoản riêng.

Đọc `README.md` trong dataset để biết lệnh giải nén và fine-tune. Các archive
raw giữ XML gốc nên nếu replay trên máy khác phải sửa `compiler meshdir`
trong **bản XML giải nén đang dùng** về thư mục mesh của checkout đó; không
sửa các ảnh/trạng thái đã thu. Các báo cáo provenance giữ đường dẫn gốc và
checksum trước khi điều chỉnh đường dẫn XML.
