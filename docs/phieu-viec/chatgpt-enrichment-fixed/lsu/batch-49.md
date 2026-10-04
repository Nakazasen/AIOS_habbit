# Mẻ 49 — LSU Ver2 vs Ver4/0 + 2 ảnh JIG cấp gốc — Q2159–Q2188

- Ngày: 2026-10-04
- Nguồn: Drive LSU → `Sirius LSU/Sirius2_linearity/Ver2 vs Ver4/0/` + cấp gốc `1 tape 40.PNG`, `2 Tape 40.PNG`
- Chat: https://chatgpt.com/c/6ac21250-cce4-83ec-a85f-5456b6a23733 (GPT-5.6 Sol, reasoning Medium)
- 3 nguồn, 30 cặp. **SỰ CỐ: KHÔNG CÓ** — gửi thành công ngay, không cloudflare_challenge, không bị cắt (4m3s).
- Ngôn ngữ: vi=10, zh=10, ja=10 — ĐÚNG mục tiêu.
- Cách hỏi: đủ 5 cách ×6.
- Hai ảnh đều là màn hình `COD-1003 Bow/Skew/Power Adjust JIG : FRONT`, Serial `6AE1053E1014`, Soft Ver `COD_1003.001.002`, Fpga Ver `2R7_1001.B01.007`. Phần chữ nhỏ đáy ảnh không đọc được → ChatGPT ghi rõ "không đọc được rõ", không bịa.
- Quy tắc Raw value: `0`/`--` giữ nguyên; không suy diễn nguyên nhân từ giá trị đơn lẻ.
- ✅ **Sirius2_linearity HOÀN TẤT** (Log tháng 02 + NanoScan + New + Step 8 + old + Ver2 vs Ver4 + xlsm/xlsx/png cấp gốc).
- Còn lại của LSU: `6thA3 LSU/Lỗi JIG BEAM` (9 thư mục theo ngày) + nhánh `ảnh hưởng độ dạt tia Beam của Lens CY` (kiểm tra cấu trúc ở mẻ 50).
- Nhãn: LSU · Bản thảo — chưa qua chuyên gia duyệt.

---

### Nguồn 1: `Ver2 vs Ver4/0/1004_1/Ver4/2025_02_UnitTest.csv` — Q2159–2168

## CÂU HỎI 2159
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận record đầu của Ver4 ở điều kiện 0 trước khi so sánh các lần UnitTest.
- Cách hỏi: trực tiếp
- Hỏi: Record đầu có ngày giờ, S/N, Mode, totalTakt và UnitSet bao nhiêu?
- Đáp: `2025/02/06 15:13:02`, S/N `6AE10ZXA9910`, Mode `UnitTest`, totalTakt `23.1 sec`, UnitSet `9.6 sec`. Nguồn file: Ver2 vs Ver4/0/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2160
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看 Ver4/0 第一条记录的 Black 与 Cyan Bow/Skew。
- Cách hỏi: tình huống
- Hỏi: `15:13:02` 的 Black/Cyan Bow `-45/0/+45` 和 Skew 分别是多少？
- Đáp: Black Bow=`20/-4/10 um`、Skew=`-91 um`；Cyan Bow=`18/0/21 um`、Skew=`-90 um`。其中 Cyan Bow:0 为 **Raw value `0`**。Nguồn file: Ver2 vs Ver4/0/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2161
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: NG 記録から OK 記録への変化を比較している。
- Cách hỏi: so sánh
- Hỏi: `15:24:07` と `15:28:39` の Black/Cyan Skew と TotalJudge はそれぞれ何ですか。
- Đáp: `15:24:07` は Black `-16 um`、Cyan `-4 um`、TotalJudge `NG`。`15:28:39` は Black `19 um`、Cyan `22 um`、TotalJudge `OK` です。Nguồn file: Ver2 vs Ver4/0/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2162
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra record có Skew thay đổi rất lớn nhưng cần tránh kết luận nguyên nhân từ một giá trị.
- Cách hỏi: xử lý sự cố
- Hỏi: Record `15:36:45` có Black/Cyan Bow, Skew và Timing bao nhiêu?
- Đáp: Black Bow `34/6/15 um`, Skew `-958 um`, Timing `-1.501 mm`; Cyan Bow `9/0/24 um`, Skew `2019 um`, Timing `-2.565 mm`. Cyan Bow:0 là **Raw value `0`**; file không định nghĩa nguyên nhân cho các giá trị Skew này. Nguồn file: Ver2 vs Ver4/0/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2163
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认未测颜色的原始值处理方式。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Magenta/Yellow 的 Current=`0`、Judge=`--` 时，都不能自行转换成 OK/NG，对吗？
- Đáp: 对。Current 保存为 **Raw value `0`**，Judge 保存为 **Raw value `--`**。Nguồn file: Ver2 vs Ver4/0/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2164
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: OK レコードの電気・環境条件を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: `15:28:39` の Black/Cyan Current、Voltage、Temperature、Humidity は何ですか。
- Đáp: Black `158.75 mA`、Cyan `166.25 mA`、Voltage `3.35 V`、Temperature `21.7`、Humidity `50.6%` です。Nguồn file: Ver2 vs Ver4/0/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2165
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra record ngay sau lần OK để xem các thông số Bow/Skew.
- Cách hỏi: tình huống
- Hỏi: Record `15:32:19` có Black và Cyan Bow/Skew bao nhiêu?
- Đáp: Black Bow `24/0/13 um`, Skew `59 um`; Cyan Bow `17/-1/18 um`, Skew `81 um`. Black Bow:0 là **Raw value `0`**. Nguồn file: Ver2 vs Ver4/0/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2166
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较第一条与第七条记录的 Timing。
- Cách hỏi: so sánh
- Hỏi: `15:13:02` 和 `15:40:51` 的 Black/Cyan Timing 分别是多少？
- Đáp: `15:13:02 = -0.742/-1.434 mm`；`15:40:51 = -0.689/-1.841 mm`。Nguồn file: Ver2 vs Ver4/0/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2167
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 0 値を学習データに取り込む際のルールを確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `15:28:39` の Black Bow:0=`0` を別の数値へ補完してもよいですか。
- Đáp: いいえ。**Raw value `0`** のまま保持し、別の測定値や状態へ置き換えません。Nguồn file: Ver2 vs Ver4/0/1004_1/Ver4/2025_02_UnitTest.csv

## CÂU HỎI 2168
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy Cyan Skew `2019 um` trong một record NG.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Dù Cyan Skew=`2019 um` và TotalJudge=`NG`, không được chỉ từ giá trị `2019` mà kết luận nguyên nhân cụ thể, đúng không?
- Đáp: Đúng. File ghi giá trị `2019 um` và Judge nhưng không định nghĩa giá trị đơn lẻ này là nguyên nhân cụ thể. Nguồn file: Ver2 vs Ver4/0/1004_1/Ver4/2025_02_UnitTest.csv

---

### Nguồn 2: `1 tape 40.PNG` (ảnh cấp gốc) — Q2169–2178

Ảnh là màn hình `COD-1003 Bow/Skew/Power Adjust JIG : FRONT`; chỉ dùng giá trị đọc rõ trong ảnh.

## CÂU HỎI 2169
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看保存的 JIG 画面截图，确认软件版本。
- Cách hỏi: trực tiếp
- Hỏi: `1 tape 40.PNG` 顶部显示的 Soft Ver 和 Fpga Ver 是什么？
- Đáp: Soft Ver 显示为 `COD_1003.001.002`，Fpga Ver 显示为 `2R7_1001.B01.007`。Nguồn file: 1 tape 40.PNG

## CÂU HỎI 2170
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Magenta 調整画面で Camera Position ごとの大きな表示値を確認している。
- Cách hỏi: tình huống
- Hỏi: Camera Pos `-45/0/+45/+90` の大きな表示値はそれぞれ何ですか。
- Đáp: `-45 = 18`、`0 = -4`、`+45 = 10`、`+90 = -2` です。`-90` の同じ位置には明確な大きな数値表示を確認できません。Nguồn file: 1 tape 40.PNG

## CÂU HỎI 2171
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh dữ liệu RC-9 Skew trước và hiện tại trên màn hình.
- Cách hỏi: so sánh
- Hỏi: RC-9 Skew của Cyan ở dòng `Before` và `Current` là bao nhiêu?
- Đáp: Cả `Before` và `Current` đều hiển thị Cyan=`-0.45 dot`. Ngày/giờ lần lượt là `26/2/2025 15:18:50` và `7/3/2025 15:58:12`. Nguồn file: 1 tape 40.PNG

## CÂU HỎI 2172
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现两次 Skew Offset 的 Magenta 数值不同，正在核对截图。
- Cách hỏi: xử lý sự cố
- Hỏi: `Before` 与 `Current` 的 Magenta Skew Offset 分别是多少？
- Đáp: `Before = 272 um`，`Current = 318 um`。截图只显示这些数值，不能仅凭差异推断变化原因。Nguồn file: 1 tape 40.PNG

## CÂU HỎI 2173
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 電気条件の表示を正しく読み取れたか確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 画面右側の Current は `165 mA`、Voltage は `3.36 V` で合っていますか。
- Đáp: はい。画面には Current `165 mA`、Voltage `3.36 V` と表示されています。Nguồn file: 1 tape 40.PNG

## CÂU HỎI 2174
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接查看截图中的生产识别信息。
- Cách hỏi: trực tiếp
- Hỏi: 画面上的 Serial Number 和 Takt 是什么？
- Đáp: Serial Number 为 `6AE1053E1014`，Takt 为 `59.5 sec`。Nguồn file: 1 tape 40.PNG

## CÂU HỎI 2175
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tra Light Path của Magenta tại năm vị trí camera trên màn hình.
- Cách hỏi: tình huống
- Hỏi: Light Path Magenta ở Camera `-90/-45/0/+45/+90` hiển thị bao nhiêu?
- Đáp: Lần lượt `0.77 / 0.80 / 0.79 / 0.82 / 0.83 mm`. Nguồn file: 1 tape 40.PNG

## CÂU HỎI 2176
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Magenta の座標値を画面両端で比較している。
- Cách hỏi: so sánh
- Hỏi: Camera `-90` と `+90` の Magenta X/Y/Y' はそれぞれ何ですか。
- Đáp: `-90` は `X=1426.8, Y=2013.0, Y'=0.0`、`+90` は `X=1385.0, Y=2005.5, Y'=61.5` です。Nguồn file: 1 tape 40.PNG

## CÂU HỎI 2177
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra màn hình nhưng một số vùng nhỏ phía dưới bị khó đọc.
- Cách hỏi: xử lý sự cố
- Hỏi: Có nên tự suy đoán toàn bộ chữ nhỏ ở phần đáy ảnh nếu không đọc chắc chắn không?
- Đáp: Không. Các phần đọc rõ gồm Serial `6AE1053E1014`, Takt `59.5`, Current `165`, Voltage `3.36`, Motor Address `1349/1273/1215/1177/1328`; những chữ nhỏ khác không đọc chắc chắn phải ghi là **không đọc được rõ**, không bịa nội dung. Nguồn file: 1 tape 40.PNG

## CÂU HỎI 2178
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认截图右下角当前对话内容。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 截图右下角的 Dialog 显示 `Adjust Bow/Skew Magenta`，对吗？
- Đáp: 对。Dialog 区域清楚显示 `Adjust Bow/Skew Magenta`；右侧 Adjust Takt 的 Magenta Power 还显示 `38.8`。Nguồn file: 1 tape 40.PNG

---

### Nguồn 3: `2 Tape 40.PNG` (ảnh cấp gốc) — Q2179–2188

Cùng giao diện JIG và cùng Serial Number với ảnh 1, nhưng giá trị Magenta/Bow-Light Path/Takt khác.

## CÂU HỎI 2179
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 2枚目のスクリーンショットで基本情報を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: `2 Tape 40.PNG` の Serial Number、Takt、Current、Voltage は何ですか。
- Đáp: Serial Number `6AE1053E1014`、Takt `32.3 sec`、Current `165 mA`、Voltage `3.36 V` です。Nguồn file: 2 Tape 40.PNG

## CÂU HỎI 2180
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra các giá trị Bow/Skew lớn hiển thị dưới năm cửa sổ camera.
- Cách hỏi: tình huống
- Hỏi: Ở Camera `-45/0/+45/+90`, các giá trị lớn hiển thị lần lượt là bao nhiêu?
- Đáp: `-45 = 5`, `0 = -27`, `+45 = -19`, `+90 = 26`. Ở vị trí `-90` không thấy một giá trị lớn tương ứng đọc được rõ. Nguồn file: 2 Tape 40.PNG

## CÂU HỎI 2181
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较截图两端的 Magenta Light Path。
- Cách hỏi: so sánh
- Hỏi: Camera `-90` 与 `+90` 的 Magenta Light Path 分别是多少？
- Đáp: `-90 = -0.92 mm`，`+90 = -0.83 mm`。Nguồn file: 2 Tape 40.PNG

## CÂU HỎI 2182
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Magenta の中央 Camera 付近で Bow と Light Path を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: Camera `0` の大きな Bow 表示と Light Path は何ですか。
- Đáp: Bow 表示は `-27`、Light Path は `-0.90 mm` です。これらの単独値だけから原因は推定しません。Nguồn file: 2 Tape 40.PNG

## CÂU HỎI 2183
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra lại bảng RC-9 Skew ở ảnh thứ hai.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: RC-9 Skew Cyan vẫn là `-0.45` ở cả Before và Current, đúng không?
- Đáp: Đúng. Hai dòng đều hiển thị Cyan=`-0.45`; Skew Offset Magenta thay đổi từ `272` ở Before thành `318` ở Current. Nguồn file: 2 Tape 40.PNG

## CÂU HỎI 2184
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Magenta の各 Camera 座標を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: Camera `0` と `+45` の X/Y/Y' はそれぞれ何ですか。
- Đáp: Camera `0` は `X=1414.3, Y=290.0, Y'=18.0`、`+45` は `X=1157.3, Y=287.5, Y'=48.5` です。Nguồn file: 2 Tape 40.PNG

## CÂU HỎI 2185
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra công suất và BD Timing trên giao diện điều chỉnh Magenta.
- Cách hỏi: tình huống
- Hỏi: Power và BD Timing hiển thị trên hàng Magenta là bao nhiêu?
- Đáp: Power hiển thị `560.0 uW`; BD Timing hiển thị `0.142 mm`. Bên cạnh Power còn thấy các giá trị `572` và `528`. Nguồn file: 2 Tape 40.PNG

## CÂU HỎI 2186
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较两个 Camera Position 的 X/Y 数据。
- Cách hỏi: so sánh
- Hỏi: Camera `-90` 与 `+90` 的 Magenta X/Y/Y' 分别是多少？
- Đáp: `-90 = 1457.9/324.9/0.0`；`+90 = 1435.6/345.4/89.5`。Nguồn file: 2 Tape 40.PNG

## CÂU HỎI 2187
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: スクリーンショットの細かい文字が一部読みづらいため、データ化の範囲を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: 読み取れない小さい文字を推測して Q&A に入れてもよいですか。
- Đáp: いいえ。明確に読める値、例えば Takt `32.3`、Power `560.0`、Current `165`、Voltage `3.36`、Serial `6AE1053E1014` のみ使用し、不鮮明な部分は **読み取れない** と扱います。Nguồn file: 2 Tape 40.PNG

## CÂU HỎI 2188
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认第二张图当前执行的对话功能。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `2 Tape 40.PNG` 右下角的 Dialog 是 `Adjust Power Magenta`，而不是 `Adjust Bow/Skew Magenta`，对吗？
- Đáp: 对。第二张图清楚显示 `Adjust Power Magenta`。Nguồn file: 2 Tape 40.PNG
