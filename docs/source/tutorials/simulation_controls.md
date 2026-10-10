# Điều khiển chai và robot trong MuJoCo

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
