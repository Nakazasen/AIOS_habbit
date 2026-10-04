# Mẻ 51 — LSU 6thA3 Lỗi JIG BEAM (4/4 thư mục còn lại → 9/9 XONG) — Q2239–Q2278
Trạng thái: Bản thảo — chưa qua chuyên gia duyệt. Khối: LSU.

- Ngày: 2026-10-04
- Nguồn: Drive LSU → `Sirius LSU/6thA3 LSU/Lỗi JIG BEAM/`
- Chat: https://chatgpt.com/c/6ac21250-cce4-83ec-a85f-5456b6a23733 (GPT-5.6 Sol, reasoning Medium)
- 4 thư mục, 40 cặp. **SỰ CỐ: KHÔNG CÓ** — gửi thành công ngay, không cloudflare_challenge, không bị cắt (5m7s).
- **6thA3 Lỗi JIG BEAM XONG 9/9**.
- Lưu ý cấu trúc: `2021.04.08 du lieu/` chỉ có PNG (không có log CSV/XLSX) → dùng ảnh tiêu biểu `MIRROR cũ.png` (PNG 528785 bytes), chỉ lấy số/chữ nhìn rõ, không bịa chi tiết.
- `2021.04.12`/`2021.04.15` có nhiều nhánh (M1/M2/M3/M4/...) → file chọn: `M4/Log2021_4.csv`.
- Ngôn ngữ: vi=14, zh=13, ja=13 — ĐÚNG mục tiêu.
- Cách hỏi: đủ 5 cách ×8.
- Quy tắc Raw value: `0`/ô trống/`9999` giữ nguyên; Temperaturte âm chỉ ghi nhận, không suy diễn nguyên nhân.
- **NHÁNH Lens CY — cấu trúc chi tiết đã xác nhận** (chưa sinh cặp):
  - `1001-1/`: 10 file — 2025_11_Cyan_Depth_Master.csv, 2025_11_Cyan_Depth_UniteTest.csv, 2025_11_Cyan_Depth.csv, 2025_11_Error.csv, 2025_11_Master.csv, 2025_11_UniteTest.csv, 2025_11_Yellow_Depth_Master.csv, 2025_11_Yellow_Depth_UniteTest.csv, 2025_11_Yellow_Depth.csv, 2025_11.csv
  - `1002-2/`: 10 file — 2025_11_Black_Depth_Master.csv, 2025_11_Black_Depth_UniteTest.csv, 2025_11_Black_Depth.csv, 2025_11_Error.csv, 2025_11_Magenta_Depth_Master.csv, 2025_11_Magenta_Depth_UniteTest.csv, 2025_11_Magenta_Depth.csv, 2025_11_Master.csv, 2025_11_UniteTest.csv, 2025_11.csv
  - Cấp gốc: `6778_CyCav_F_2025.11.13.xlsm` (dữ liệu CyCav F 2025-11-13, có macro), `6778_CyCav_G_2025.11.13.xlsm` (CyCav G 2025-11-13), `Cy用治具の修理_6778_CyCav_F.xlsm` (nội dung liên quan sửa chữa jig dùng cho Cy, `6778_CyCav_F`).
  - Link: https://drive.google.com/drive/folders/140lKYj9520JHnuwbCFnQMCwr_q_KODJe
  - Đính chính: mẻ 50 mô tả nhánh này là "bowskew NanoScan JIG CY máy F/G" dựa trên suy đoán tên file; dùng mô tả mẻ 51 (chỉ theo tên/định dạng, không suy đoán thiết bị).
- Nhãn: LSU · Bản thảo — chưa qua chuyên gia duyệt.

---

### Thư mục 6: `2021.04.08 du lieu/MIRROR cũ.png` — Q2239–2248

## CÂU HỎI 2239
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư mở ảnh lưu màn hình JIG ngày 08/04 để xác nhận kết quả cuối.
- Cách hỏi: trực tiếp
- Hỏi: Trên `MIRROR cũ.png`, Final Test, Sel No. và Tact hiển thị gì?
- Đáp: Final Test hiển thị `NG`, Sel No. `J7N1203A1242`, Tact `107`. Nguồn file: MIRROR cũ.png

## CÂU HỎI 2240
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师从旧 Mirror 截图确认 JIG 软件版本。
- Cách hỏi: tình huống
- Hỏi: 画面中的 Apli、FPGA、EDIT 版本分别是什么？
- Đáp: Apli=`2P7_1001.001.014`，FPGA=`2P7_1001.B01.010`，EDIT=`2P7-1001.001.009`。Nguồn file: MIRROR cũ.png

## CÂU HỎI 2241
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: XY Camera-XY ref の複数座標を比較している。
- Cách hỏi: so sánh
- Hỏi: XY ref の上段と中段の X/Y はそれぞれいくつですか。
- Đáp: 上段は `X=3059, Y=1970`、中段は `X=3025, Y=1925` です。Nguồn file: MIRROR cũ.png

## CÂU HỎI 2242
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy Bow/Skew trên ảnh và cần tránh suy diễn nguyên nhân.
- Cách hỏi: xử lý sự cố
- Hỏi: Bow và Skew hiển thị bao nhiêu, và có thể từ hai giá trị này kết luận nguyên nhân NG không?
- Đáp: Bow=`145.56`, Skew=`-56.40`. Không thể chỉ từ hai giá trị này kết luận nguyên nhân NG vì ảnh không nêu quan hệ nguyên nhân. Nguồn file: MIRROR cũ.png

## CÂU HỎI 2243
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师复核屏幕右下侧的电气信息。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Voltage=`5.02`、Current=`53.75`，对吗？
- Đáp: 对。截图中显示 Volt=`5.02`、Current=`53.75`。Nguồn file: MIRROR cũ.png

## CÂU HỎI 2244
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: +130 Beam Position の Beam Size を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: `+130 Beam Position` の LD1/LD2 HBeam・VBeam は何ですか。
- Đáp: LD1 HBeam=`90`、LD1 VBeam=`94`、LD2 HBeam=`91`、LD2 VBeam=`96` です。Nguồn file: MIRROR cũ.png

## CÂU HỎI 2245
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra Beam Size tại vị trí +50 trên ảnh JIG.
- Cách hỏi: tình huống
- Hỏi: `+50 Beam Position` có LD1 H/V và LD2 H/V bao nhiêu?
- Đáp: LD1 H/V=`83/87`; LD2 H/V=`84/87`. Nguồn file: MIRROR cũ.png

## CÂU HỎI 2246
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 +130 与 -140 两个位置的 LD1 Beam Size。
- Cách hỏi: so sánh
- Hỏi: `+130` 与 `-140` 的 LD1 HBeam/VBeam 分别是多少？
- Đáp: `+130 = 90/94`；`-140 = 86/88`。Nguồn file: MIRROR cũ.png

## CÂU HỎI 2247
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Beam Pitch の Xpoint に 0 が表示されているため保存方法を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: Beam Pitch の Xpoint=`0` はどう扱いますか。
- Đáp: **Raw value `0`** として保持します。0 だけから OK/NG や状態を推定しません。Nguồn file: MIRROR cũ.png

## CÂU HỎI 2248
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra lại trạng thái cuối màn hình trước khi lưu ảnh.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Ảnh hiển thị Jig No. `#1`, Master Unit `OK` và Dialog `Unit Check End!!`, đúng không?
- Đáp: Đúng. Ba nội dung đọc được trên màn hình là Jig No. `#1`, Master Unit `OK` và `Unit Check End!!`. Nguồn file: MIRROR cũ.png

---

### Thư mục 7: `2021.04.12 du lieu/M4/Log2021_4.csv` — Q2249–2258

## CÂU HỎI 2249
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 4月12日当天第一条基准测试。
- Cách hỏi: trực tiếp
- Hỏi: `07:22:34` 的 SelNo、FinTest、FinVolt 和 FinCurrent 是什么？
- Đáp: SelNo=`E9L119174234`，FinTest=`NG`，FinVolt=`5.03`，FinCurrent=`1.25`。Nguồn file: Log2021_4.csv

## CÂU HỎI 2250
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: J7N1014A9015 の実測 Beam と Bow/Skew を確認している。
- Cách hỏi: tình huống
- Hỏi: `08:01:45` の LD1 H/V、Bow、Skew は何ですか。
- Đáp: LD1 H=`90/86/85/86`、V=`98/92/88/92`、Bow=`59.72`、Skew=`27.90` です。Nguồn file: Log2021_4.csv

## CÂU HỎI 2251
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh hai lần kiểm tra liên tiếp của SelNo chuẩn.
- Cách hỏi: so sánh
- Hỏi: Record `07:22:34` và `07:23:49` khác nhau thế nào về FinTest và FinCurrent?
- Đáp: `07:22:34`: FinTest=`NG`, FinCurrent=`1.25`; `07:23:49`: FinTest=`OK`, FinCurrent=`52.5`. Nguồn file: Log2021_4.csv

## CÂU HỎI 2252
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师看到 J7N1014A9008 的 XY 为特殊数值。
- Cách hỏi: xử lý sự cố
- Hỏi: `07:59:34` 的 Xy_X/Xy_Y=`9999/9999`、Bow/Skew 为空时怎么保存？
- Đáp: Xy_X 和 Xy_Y 分别保存为 **Raw value `9999`**；Bow/Skew 保存为 **Raw value：空白**，不自行赋予状态意义。Nguồn file: Log2021_4.csv

## CÂU HỎI 2253
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: A9015 の Bow/Skew 読み取りを再確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: J7N1014A9015 の Bow=`59.72`、Skew=`27.90` で合っていますか。
- Đáp: はい。`08:01:45` の記録にその値があります。Nguồn file: Log2021_4.csv

## CÂU HỎI 2254
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đọc trực tiếp Y-position của J7N1014A9006.
- Cách hỏi: trực tiếp
- Hỏi: LD1Yp M140/M50/P50/P130 của A9006 là bao nhiêu?
- Đáp: `-374.1 / -430.6 / -431.2 / -360.1`. Nguồn file: Log2021_4.csv

## CÂU HỎI 2255
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看 A9008 第二次记录的 LD2 Y-position。
- Cách hỏi: tình huống
- Hỏi: `08:05:38` 的 LD2Yp M140/M50/P50/P130 是多少？
- Đáp: `-249.5 / -303.9 / -304.2 / -234.5`。Nguồn file: Log2021_4.csv

## CÂU HỎI 2256
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: A9005 と A9004 の Bow/Skew を比較している。
- Cách hỏi: so sánh
- Hỏi: 二つの記録の Bow/Skew はそれぞれ何ですか。
- Đáp: A9005=`67.01/32.70`、A9004=`81.73/34.20` です。Nguồn file: Log2021_4.csv

## CÂU HỎI 2257
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư chuẩn hóa record đầu ngày có nhiều số 0 và ô trống.
- Cách hỏi: xử lý sự cố
- Hỏi: LD1Yp và LD2 của record `07:22:34` đều bằng 0, còn Bow/Skew trống; lưu thế nào?
- Đáp: Các số `0` giữ là **Raw value `0`**; Bow và Skew giữ là **Raw value: ô trống**. Nguồn file: Log2021_4.csv

## CÂU HỎI 2258
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 4月12日记录的软件版本。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Version=`2P7_1001.001.014`、FPGA=`2P7_1001.B01.010`、EditData=`2P7-1001.001.009`，对吗？
- Đáp: 对。所检查的记录中均显示这些版本。Nguồn file: Log2021_4.csv

---

### Thư mục 8: `2021.04.15 du lieu/M4/Log2021_4.csv` — Q2259–2268

## CÂU HỎI 2259
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 4月15日の最初の基準記録を確認している。
- Cách hỏi: trực tiếp
- Hỏi: `07:31:10` の SelNo、FinTest、FinVolt、FinCurrent は何ですか。
- Đáp: SelNo=`E9L119174234`、FinTest=`OK`、FinVolt=`5.03`、FinCurrent=`52.5` です。Nguồn file: Log2021_4.csv

## CÂU HỎI 2260
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra C161014A3833 sau khi vào sản xuất.
- Cách hỏi: tình huống
- Hỏi: A3833 có Bow, Skew, final XY và first XY bao nhiêu?
- Đáp: Bow=`149.41`, Skew=`-48.00`, final XY=`3044/1970`, first XY=`3064/1945`. Nguồn file: Log2021_4.csv

## CÂU HỎI 2261
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 A3833 与 A3837 的 Beam 调整结果。
- Cách hỏi: so sánh
- Hỏi: 两台的 Bow、Skew、FinCurrent 分别是多少？
- Đáp: A3833=`149.41/-48.00/55`；A3837=`144.14/-57.30/52.5`。Nguồn file: Log2021_4.csv

## CÂU HỎI 2262
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 基準記録に 0 と空白が多いため取込ルールを確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `07:31:10` の LD1Yp/LD2=`0`、Bow/Skew が空白の場合はどうしますか。
- Đáp: 各 `0` は **Raw value `0`**、Bow/Skew は **Raw value：空白** として保持します。Nguồn file: Log2021_4.csv

## CÂU HỎI 2263
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra lại Beam của A3835 trước khi ghi nhận.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: A3835 có LD1 H=`85/85/85/90` và V=`89/90/89/95`, đúng không?
- Đáp: Đúng. Đây là bốn giá trị H và bốn giá trị V trong record `08:05:08`. Nguồn file: Log2021_4.csv

## CÂU HỎI 2264
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接查看 A3834 的 LD2 Y-position。
- Cách hỏi: trực tiếp
- Hỏi: A3834 的 LD2Yp M140/M50/P50/P130 是多少？
- Đáp: `301.8 / 164.1 / 121.3 / 241.0`。Nguồn file: Log2021_4.csv

## CÂU HỎI 2265
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: A3836 の Pitch をライン上で確認している。
- Cách hỏi: tình huống
- Hỏi: A3836 の M140/M50/P50/P130 Pitch は何ですか。
- Đáp: `38.7757462021553 / 40.4562193677937 / 39.5678336822836 / 37.4485368534951` です。Nguồn file: Log2021_4.csv

## CÂU HỎI 2266
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh A3838 và A3839 để xem Bow/Skew thay đổi.
- Cách hỏi: so sánh
- Hỏi: Bow/Skew của hai máy lần lượt bao nhiêu?
- Đáp: A3838=`138.26/-36.40`; A3839=`143.70/-37.80`. Nguồn file: Log2021_4.csv

## CÂU HỎI 2267
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现 A3841 的 Temperature 为负值。
- Cách hỏi: xử lý sự cố
- Hỏi: A3841 的 Temperaturte=`-19.2` 时，能否仅凭这个值判断传感器或产品异常？
- Đáp: 不能。文件只记录 `-19.2`；不能从单个值自行推断异常原因。Nguồn file: Log2021_4.csv

## CÂU HỎI 2268
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Offset とバージョンを最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: A3833～A3841 の確認記録では Apc/Col Offset が `3050/1940`、Version が `2P7_1001.001.014` で合っていますか。
- Đáp: はい。確認した各レコードは ApcX/ApcY=`3050/1940`、ColX/ColY=`3050/1940`、Version=`2P7_1001.001.014` です。Nguồn file: Log2021_4.csv

---

### Thư mục 9: `2021.04.20 du lieu/Log2021_4.csv` — Q2269–2278

## CÂU HỎI 2269
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận lần kiểm tra chuẩn đầu ngày 20/04.
- Cách hỏi: trực tiếp
- Hỏi: Record `07:21:33` có SelNo, FinTest, FinVolt và FinCurrent bao nhiêu?
- Đáp: SelNo=`E9L119174234`, FinTest=`NG`, FinVolt=`5.04`, FinCurrent=`1.25`. Nguồn file: Log2021_4.csv

## CÂU HỎI 2270
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师调查 J7N1014A9575 第一次 NG 测量。
- Cách hỏi: tình huống
- Hỏi: `07:32:35` 的 LD1 H/V 四点分别是多少？
- Đáp: H=`98/92/86/96`，V=`98/96/90/99`，FinTest=`NG`。Nguồn file: Log2021_4.csv

## CÂU HỎI 2271
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 同じ A9575 の NG と再測定 OK を比較している。
- Cách hỏi: so sánh
- Hỏi: `07:32:35` と `07:35:09` の FinTest、FinCurrent、XY はどう違いますか。
- Đáp: `07:32:35` は `NG / 57.5 / 3050,1935`、`07:35:09` は `OK / 56.25 / 3076,1978` です。Nguồn file: Log2021_4.csv

## CÂU HỎI 2272
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xử lý record đầu ngày có nhiều 0 và trường môi trường trống.
- Cách hỏi: xử lý sự cố
- Hỏi: LD1Yp/LD2=`0`, Bow/Skew và Temperature/Humidity trống ở `07:21:33` phải lưu thế nào?
- Đáp: Các `0` giữ là **Raw value `0`**; Bow, Skew, Temperature và Humidity giữ là **Raw value: ô trống**. Nguồn file: Log2021_4.csv

## CÂU HỎI 2273
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师复核 A9575 第二次测量的 Bow/Skew。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `07:35:09` 的 Bow=`125.60`、Skew=`-109.90`，对吗？
- Đáp: 对。该记录 FinTest=`OK`，Bow 和 Skew 分别为 `125.60` 与 `-109.90`。Nguồn file: Log2021_4.csv

## CÂU HỎI 2274
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: Kỹ sư đọc trực tiếp Y-position của A9563.
- Cách hỏi: trực tiếp
- Hỏi: A9563 の LD2Yp M140/M50/P50/P130 は何ですか。
- Đáp: `33.2 / -106.2 / -153.6 / -49.9` です。Nguồn file: Log2021_4.csv

## CÂU HỎI 2275
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra lần NG đầu của J7N1014A9576.
- Cách hỏi: tình huống
- Hỏi: A9576 lúc `07:38:38` có Bow, Skew, FinCurrent và LD1 H bao nhiêu?
- Đáp: Bow=`127.44`, Skew=`-89.70`, FinCurrent=`52.5`, LD1 H=`88/87/85/92`; FinTest=`NG`. Nguồn file: Log2021_4.csv

## CÂU HỎI 2276
- Khối: LSU
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 A9576 的 NG 与后续 OK 记录。
- Cách hỏi: so sánh
- Hỏi: `07:38:38` 和 `07:41:50` 的 FinTest、Bow、Skew 分别是什么？
- Đáp: `07:38:38 = NG / 127.44 / -89.70`；`07:41:50 = OK / 127.76 / -90.40`。两条记录 FinCurrent 都是 `52.5`。Nguồn file: Log2021_4.csv

## CÂU HỎI 2277
- Khối: LSU
- Ngôn ngữ: ja
- Bối cảnh: 再測定 OK レコードに負の Temperature が記録されている。
- Cách hỏi: xử lý sự cố
- Hỏi: `07:41:50` の Temperaturte=`-20.6` だけから測定異常原因を判断できますか。
- Đáp: できません。ファイルに記録されている値は `-20.6` ですが、単独値から原因を推定する定義はありません。Nguồn file: Log2021_4.csv

## CÂU HỎI 2278
- Khối: LSU
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận thiết lập offset và software trước khi kết thúc đối chiếu.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Các record sản phẩm được kiểm tra dùng Apc/Col offset `3050/1940` và Version `2P7_1001.001.014`, đúng không?
- Đáp: Đúng. ApcX/ApcY=`3050/1940`, ColX/ColY=`3050/1940`; Version=`2P7_1001.001.014`, FPGA=`2P7_1001.B01.010`, EditData=`2P7-1001.001.009`. Nguồn file: Log2021_4.csv
