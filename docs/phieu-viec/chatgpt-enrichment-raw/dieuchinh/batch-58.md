# Mẻ 58 — Điều-tra-lỗi: `SƠ đồ điện/` (10/84 file tiếp theo) — Q2492–Q2521

- Ngày: 2026-10-04
- Nguồn: local `~/workspace/dieuchinh_zip/dieuchinh.zip` → trích → upload Drive riêng (`chatgpt-enrichment-dieu-chinh`, anyone-reader)
- Chat: https://chatgpt.com/c/6ac21250-cce4-83ec-a85f-5456b6a23733 (ChatGPT phiên mặc định hiện tại, theo quy trình từ đầu)
- 10 file, 30 cặp. **SỰ CỐ: không có** — 4m49s, "Đã hoàn tất phản hồi", không cloudflare, không cắt, không hết giới hạn.
- Ngôn ngữ: vi=10, zh=10, ja=10 — ĐÚNG mục tiêu.
- Cách hỏi: mỗi file 3 cặp dùng 3 cách khác nhau luân phiên; toàn mẻ đủ cả 5 cách.
- Chất lượng: chỉ dùng nhãn/giá trị xuất hiện trong nguồn, không bịa chi tiết; có cảnh báo "không thể kết luận linh kiện hỏng từ sơ đồ" khi phù hợp; **Q2492–2494 (bản 2 của 定着) xử lý đúng: trùng hệt bản mẻ 57** (Model EUK9SQD06HA, Drawing No. 111-EUK9SQD06HA-C01, ngày 2016.2.04, 1 trang, 23645 bytes) → 3 cặp chỉ xác nhận tính trùng lặp, KHÔNG lặp lại câu FSR/T101 đã sinh ở mẻ 57. Q2510 xử lý đúng Raw value `OPEN` (C706/C503/C707 ghi OPEN — không tự chuyển thành 0/hỏng/không lắp). Không file nào bị bỏ qua; nội dung là tài liệu mạch/BOM, không trùng `Loi KDTPS.xlsx`.
- Tóm tắt 10 file:
  1. `Iris2020_302ND45060(定着).pdf` (bản 2): trùng hệt bản mẻ 57 → chỉ 3 cặp xác nhận trùng lặp, không lặp nội dung.
  2. `3V2XD47090_01.pdf`: 10 trang, PWB PANEL ASSY (ASSY 3V2XD47090, board 7PA1204BDS+GH01); INDEX: CPU, KEY_LED, SPEAKER, MAIN IF, Touch Panel & Backlight, THCV234, LDO & FET, LCD Bias; SPEAKER: SPEAKER_P/N, BEEP, AUDIO, AMP_SEL/RESET_N/CSB/BUSYB/FAULT, I2C_SCL/SDA; touch: capacitive RST/SWDIO/SDA/INT/SCL/SWDCLK, resistive XN-Left/YP-Bottom/XP-Right/YN-Top.
  3. `302XC47260-03.pdf`: 5 trang, PWB CMOS SENSOR ASSY (ASSY 302XC47260); INDEX/CHANGE_HISTORY/CMOS SENSOR,CAP/V-by-One/IF,POWER; V-by-One: TLAN/TLAP, TLBN/TLBP, TLCN/TLCP, TLCLKN/TLCLKP, TLDN/TLDP, TLEN/TLEP, CCD_VBO_N/P, 100Ω impedance control; LED: LED_PWM/LED_ENABLE/LED_PWM_AND/LED_PWM_CMOS; nguồn +12V5_LED/+5V2/+3.3V5/+1.8V5.
  4. `7PA1204BDS.pdf`: 10 trang, PWB PANEL ASSY bản mới hơn (board 7PA1204BDS+GH01, ngày 2021/4/22, ASSY 3V2ZS47040); U18 = ML22Q394-719MBZ0AHL (bản cũ 3V2XD47090_01 ghi ML22Q394_N_01 — khác thật); AMP_SEL=Low → COM-NC, High → COM-NO.
  5. `302XC47090-02.pdf`: 3 trang, PWB ERASER ASSY; ERASER: LED DL1 = RA32E1-RUT-FR (A/C), ERASER_REM, +5V0_F2, dây P1:RED / P2:BLACK (線材直付け).
  6. `Iris2020_LED DRIVE基板回路図_190624.pdf`: 3 trang, PWB LED DRIVE ASSY; U1 = MP2480DN-LF-Z (VIN/DIM/FB/BST/SW/EN/GND); LED_ENA/LED_PWM/12V/GND, LED R_A/R_C/F_A/F_C; IF setting 1.015–1.036A, input 12V.
  7. `Iris2020High_302XC45010立て基板_Ver2.1.pdf`: 1 trang, Circuit Diagram model MDKZZQ101, Drawing No. 151-MDKZZQ101-C01, ngày 2019.08.29; nhiều nhánh PWM, linh kiện OPEN (Raw value giữ nguyên); ZD701 = 3.3V 0.2W, ZD301 = 5.1V 0.2W.
  8. `Iris2020High_302XC45010_D級アンプモジュール.pdf`: 1 trang, Circuit Diagram model MCSQE101, Drawing No. 111-MCSQE101-C01; IC3: MUTE/SD/GAIN1/GAIN0/LIN/RIN/LOUT/ROUT, PVCCL/PVCCR/AVCC/GND; GAIN1 IN2/GAIN2; COM1/COM9/COM15 pinなし.
  9. `2ND-7002_Iris OPTION検査_ブロック図Ver.2.2_201223.pdf`: 1 trang, block diagram OPTION test jig Ver.2.2; POWER/DP/COIN VENDER/DF/BRIDGE(AK)/PF/STD IO/ENGINE/FEED IMAGE PWB/RS-232C; nguồn: MAIN SW, 電源 24V, INLET, POWER OUT, ACアダプタ, FGターミナル; YC13 未使用 (không được coi là đường nối hiện tại).
  10. `DP IF ASSY_7PA1153CJF.pdf`: 24 trang, P.W.BOARD ASSY DP IF (ASSY 303TC47040, board 7PA1153CJF+GH01); Panther DDRC/DDR4, MAIN IF, CLOCK GENERATOR, SHD IF, DP IF, GPIO/IO/debug/power, DC/DC; DP IF PCIe: PCIEP/N_REFCLK_DP22DP1, PCIEP/N_DP12DP2, PCIEP/N_DP22DP1; nguồn +5.0V4/+3.3V4, GND/GND_PCIERCPLL; YC5 = FX23L-40P-0.5SV10, 40-pin, LockPin LP-1/LP-2.
- Số liệu nổi bật: AMP_SEL Low→COM-NC / High→COM-NO; U18 bản mới ML22Q394-719MBZ0AHL vs bản cũ ML22Q394_N_01; LED IF 1.015–1.036A; ZD701 3.3V / ZD301 5.1V (0.2W); PCIe pairs DP22DP1/DP12DP2; YC5 FX23L-40P-0.5SV10.
- Còn lại ZIP Điều tra lỗi: `SƠ đồ điện/` 67 file chưa làm; `Lịch sử lỗi/` 2022 mục chưa làm (đã upload 30 file Excel/PDF đầu tiên).
- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.

---

# `Iris2020_302ND45060(定着).pdf` (bản 2) — Q2492–2494

## CÂU HỎI 2492
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn biết bản 2 có phải tài liệu mới khác bản đã kiểm tra ở Mẻ 57 hay không.
- Cách hỏi: trực tiếp
- Hỏi: Bản 2 này có cấu trúc và thông tin title block thế nào?
- Đáp: File có `1` trang, Model=`EUK9SQD06HA`, Drawing No.=`111-EUK9SQD06HA-C01`, ngày=`2016.2.04`. Các nội dung đọc được trùng với bản đã kiểm tra ở Mẻ 57; không phát hiện điểm khác biệt mới để tạo case khác. Nguồn file: Iris2020_302ND45060(定着).pdf

## CÂU HỎI 2493
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较同名的两份定着电路图，避免把重复文件当作新版本。
- Cách hỏi: so sánh
- Hỏi: 这份"版本2"和上一批同名文件在可读的 Model、Drawing No.、日期上是否不同？
- Đáp: 没有发现不同；两者可读信息均为 Model=`EUK9SQD06HA`、Drawing No.=`111-EUK9SQD06HA-C01`、日期=`2016.2.04`。因此本批不重复生成上一批的 T101/FSR 内容。Nguồn file: Iris2020_302ND45060(定着).pdf

## CÂU HỎI 2494
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 同名ファイルを新規図面として扱わないよう確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 読み取れる範囲では新しい部品番号や改訂差分が確認できないため、Mẻ 57 と同じ回路内容を再度学習データ化しない、という扱いでよいですか。
- Đáp: はい。今回確認できた範囲では新しい差分はありません。そのため、既出の内容を新規差分として扱いません。Nguồn file: Iris2020_302ND45060(定着).pdf

# `3V2XD47090_01.pdf` — Q2495–2497

## CÂU HỎI 2495
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra tiếng loa và cần xác định đúng các tín hiệu Speaker IF trên panel board.
- Cách hỏi: tình huống
- Hỏi: Trang `SPEAKER` ghi các tín hiệu chính nào liên quan đến amplifier và speaker?
- Đáp: Các nhãn đọc được gồm `SPEAKER_P`, `SPEAKER_N`, `BEEP`, `AUDIO`, `AMP_SEL`, `AMP_RESET_N`, `AMP_CSB`, `AMP_BUSYB`, `AMP_FAULT`, cùng `I2C_SCL` và `I2C_SDA`. Nguồn file: 3V2XD47090_01.pdf

## CÂU HỎI 2496
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 Panel board 的文档页结构。
- Cách hỏi: trực tiếp
- Hỏi: `3V2XD47090_01.pdf` 有多少页，INDEX 中列出了哪些主要电路页？
- Đáp: 共 `10` 页；主要包括 `CPU`、`KEY_LED`、`SPEAKER`、`MAIN IF`、`Touch Panel & Backlight`、`THCV234`、`LDO & FET`、`LCD Bias`。Nguồn file: 3V2XD47090_01.pdf

## CÂU HỎI 2497
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: タッチパネル回路で静電容量方式と抵抗膜方式の信号を比較している。
- Cách hỏi: so sánh
- Hỏi: 静電容量方式側と抵抗膜方式側では、図面上どのような信号が記載されていますか。
- Đáp: 静電容量方式側には `RST/SWDIO/SDA/INT/SCL/SWDCLK` などがあり、抵抗膜方式側には `XN-Left/YP-Bottom/XP-Right/YN-Top` が記載されています。Nguồn file: 3V2XD47090_01.pdf

# `302XC47260-03.pdf` — Q2498–2500

## CÂU HỎI 2498
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy tín hiệu ảnh không ổn định và đang lần theo V-by-One nhưng chưa muốn quy kết linh kiện.
- Cách hỏi: xử lý sự cố
- Hỏi: Trang V-by-One có những cặp tín hiệu nào được ghi rõ để lần đường truyền?
- Đáp: Các cặp đọc được gồm `TLAN/TLAP`, `TLBN/TLBP`, `TLCN/TLCP`, `TLCLKN/TLCLKP`, `TLDN/TLDP`, `TLEN/TLEP`, cùng `CCD_VBO_N/CCD_VBO_P`. Sơ đồ ghi `100Ω` cho impedance control; chỉ từ một đường mất tín hiệu chưa thể kết luận linh kiện hỏng. Nguồn file: 302XC47260-03.pdf

## CÂU HỎI 2499
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 CMOS SENSOR 板的实际文件结构。
- Cách hỏi: trực tiếp
- Hỏi: 该 PDF 有多少页，主要页名称是什么？
- Đáp: 共 `5` 页：`INDEX`、`CHANGE_HISTORY`、`CMOS SENSOR,CAP`、`V-by-One`、`IF,POWER`。ASSY No.=`302XC47260`。Nguồn file: 302XC47260-03.pdf

## CÂU HỎI 2500
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: IF/POWER ページの LED 制御条件を読み直している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `IF,POWER` には `LED_PWM` と `LED_ENABLE` があり、さらに内部信号として `LED_PWM_AND` と `LED_PWM_CMOS` も記載されていますね。
- Đáp: はい。その4つの信号名が図面に記載されています。また電源側には `+12V5_LED`、`+5V2`、`+3.3V5`、`+1.8V5` も確認できます。Nguồn file: 302XC47260-03.pdf

# `7PA1204BDS.pdf` — Q2501–2503

## CÂU HỎI 2501
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận phiên bản panel board này trước khi dùng sơ đồ.
- Cách hỏi: trực tiếp
- Hỏi: File có bao nhiêu trang, PWB/board và ngày được ghi thế nào?
- Đáp: File có `10` trang, `PWB PANEL ASSY`, board=`7PA1204BDS+GH01`. Title block trên bản này ghi ngày `2021/4/22`; các trang đọc được có ASSY/PWB như `3V2ZS47040` và `3V2XD47092` tùy phần sơ đồ. Nguồn file: 7PA1204BDS.pdf

## CÂU HỎI 2502
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师检查 2021 年报知音对应后的 Speaker IF。
- Cách hỏi: tình huống
- Hỏi: Speaker IF 中 `AMP_SEL` 为 Low 和 High 时，图上分别写成什么？
- Đáp: `AMP_SEL=Low` 时标记为 `COM-NC`；`AMP_SEL=High` 时标记为 `COM-NO`。Nguồn file: 7PA1204BDS.pdf

## CÂU HỎI 2503
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 旧パネル資料と2021年版のSpeaker回路を比較している。
- Cách hỏi: so sánh
- Hỏi: 2021年版の Speaker IF で、U18 の型番は何になっていますか。
- Đáp: 2021年版では U18=`ML22Q394-719MBZ0AHL` と記載されています。旧 `3V2XD47090_01.pdf` では U18=`ML22Q394_N_01` と読めるため、ここは実際に異なる記載です。Nguồn file: 7PA1204BDS.pdf

# `302XC47090-02.pdf` — Q2504–2506

## CÂU HỎI 2504
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận cách đấu dây của ERASER board trước khi đo.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Trang ERASER ghi dây P1 là RED và P2 là BLACK, đúng không?
- Đáp: Đúng. Sơ đồ ghi `線材直付け`, `P1：RED`, `P2：BLACK`. Nguồn file: 302XC47090-02.pdf

## CÂU HỎI 2505
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认 Eraser 板上的发光元件。
- Cách hỏi: trực tiếp
- Hỏi: ERASER 页上的 LED 元件编号和型号是什么？
- Đáp: 元件编号为 `DL1`，型号标记为 `RA32E1-RUT-FR`，并标出 `A/C` 极性。Nguồn file: 302XC47090-02.pdf

## CÂU HỎI 2506
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Eraser LED が点灯しないため、図面上の供給線を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: ERASER ページで確認できる電源・制御系のラベルは何ですか。
- Đáp: `ERASER_REM` と `+5V0_F2` が確認できます。ただし、この図面だけから LED 不点灯の原因部品を断定することはできません。Nguồn file: 302XC47090-02.pdf

# `Iris2020_LED DRIVE基板回路図_190624.pdf` — Q2507–2509

## CÂU HỎI 2507
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần xác nhận IC điều khiển chính của LED DRIVE board.
- Cách hỏi: trực tiếp
- Hỏi: IC `U1` trên trang LED DRIVER/CONNECTOR là loại nào?
- Đáp: `U1 = MP2480DN-LF-Z`. Các chân đọc được gồm `VIN`, `DIM`, `FB`, `BST`, `SW`, `EN`, `GND`. Nguồn file: Iris2020_LED DRIVE基板回路図_190624.pdf

## CÂU HỎI 2508
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师检查 LED DRIVE 输入控制线。
- Cách hỏi: tình huống
- Hỏi: 图中外部接口明确列出了哪些 LED 控制和电源信号？
- Đáp: 可读到 `LED_ENA`、`LED_PWM`、`12V`、GND，以及 `LED R_A`、`LED R_C`、`LED F_A`、`LED F_C`。Nguồn file: Iris2020_LED DRIVE基板回路図_190624.pdf

## CÂU HỎI 2509
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: LED DRIVER の電流設定と入力電源を比較して確認している。
- Cách hỏi: so sánh
- Hỏi: 図面に記載された IF設定電流範囲と入力電源は何ですか。
- Đáp: IF設定は `1.015～1.036A`、入力側は `12V` と記載されています。これらは図面上の設定・電源値であり、単独では故障判定値とはされていません。Nguồn file: Iris2020_LED DRIVE基板回路図_190624.pdf

# `Iris2020High_302XC45010立て基板_Ver2.1.pdf` — Q2510–2512

## CÂU HỎI 2510
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy một số linh kiện trên sơ đồ được ghi OPEN và cần nhập dữ liệu đúng.
- Cách hỏi: xử lý sự cố
- Hỏi: Các linh kiện như `C706`, `C503`, `C707` được ghi `OPEN` phải hiểu thế nào khi tạo dữ liệu?
- Đáp: Chỉ giữ đúng nội dung nguồn là **Raw value `OPEN`**. Không tự chuyển `OPEN` thành `0`, hỏng, không lắp hay trạng thái khác nếu file không định nghĩa thêm. Nguồn file: Iris2020High_302XC45010立て基板_Ver2.1.pdf

## CÂU HỎI 2511
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认这张立板电路图的图纸信息。
- Cách hỏi: trực tiếp
- Hỏi: Model、Drawing No. 和日期分别是什么？
- Đáp: Model=`MDKZZQ101`，Drawing No.=`151-MDKZZQ101-C01`，日期=`2019.08.29`。Nguồn file: Iris2020High_302XC45010立て基板_Ver2.1.pdf

## CÂU HỎI 2512
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 保護用ツェナーの定格を比較している。
- Cách hỏi: so sánh
- Hỏi: `ZD701` と `ZD301` の記載値はどう違いますか。
- Đáp: `ZD701 = 3.3V 0.2W`、`ZD301 = 5.1V 0.2W` です。Nguồn file: Iris2020High_302XC45010立て基板_Ver2.1.pdf

# `Iris2020High_302XC45010_D級アンプモジュール.pdf` — Q2513–2515

## CÂU HỎI 2513
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận IC khuếch đại chính trong module Class-D.
- Cách hỏi: trực tiếp
- Hỏi: `IC3` có những chân điều khiển và output chính nào được ghi trên sơ đồ?
- Đáp: Các nhãn đọc được gồm `MUTE`, `SD`, `GAIN1`, `GAIN0`, `LIN`, `RIN`, `LOUT`, `ROUT`, cùng các chân nguồn `PVCCL/PVCCR`, `AVCC` và GND. Nguồn file: Iris2020High_302XC45010_D級アンプモジュール.pdf

## CÂU HỎI 2514
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师排查放大器无输出，先确认图中的控制信号。
- Cách hỏi: tình huống
- Hỏi: 图上与启停、静音和增益相关的信号标签是什么？
- Đáp: 可读到 `SD`、`MUTE`、`GAIN1`、`GAIN0`；外围接口还标有 `GAIN1 IN2`、`GAIN2`。仅从某一控制线状态不能直接判定 IC 故障。Nguồn file: Iris2020High_302XC45010_D級アンプモジュール.pdf

## CÂU HỎI 2515
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 図面のCOM端子表記を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 図面には `COM1, COM9, COM15 はピンなし` と明記されていますか。
- Đáp: はい。その注記が明記されています。Nguồn file: Iris2020High_302XC45010_D級アンプモジュール.pdf

# `2ND-7002_Iris OPTION検査_ブロック図Ver.2.2_201223.pdf` — Q2516–2518

## CÂU HỎI 2516
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh các nhánh OPTION được nối vào jig.
- Cách hỏi: so sánh
- Hỏi: Sơ đồ block thể hiện những nhóm option chính nào quanh jig box?
- Đáp: Các khối được ghi rõ gồm `DP`, `COIN VENDER`, `DF`, `BRIDGE (AK)`, `PF`, cùng `POWER`, `STD IO`, `ENGINE`, `FEED IMAGE PWB` và `RS-232C`. Nguồn file: 2ND-7002_Iris OPTION検査_ブロック図Ver.2.2_201223.pdf

## CÂU HỎI 2517
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现图上 YC13，但担心误认为当前使用接口。
- Cách hỏi: xử lý sự cố
- Hỏi: `YC13` 在图中应如何处理？
- Đáp: 图上明确写有 `※YC13 未使用`，因此只能按"未使用"的原始备注处理，不能把它当作当前有效连接路径。Nguồn file: 2ND-7002_Iris OPTION検査_ブロック図Ver.2.2_201223.pdf

## CÂU HỎI 2518
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: OPTION検査治具の電源構成を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 電源系ブロックにはどのようなラベルが記載されていますか。
- Đáp: `MAIN SW`、`電源 24V`、`INLET`、`POWER OUT`、`ACアダプタ`、`FGターミナル` が記載されています。Nguồn file: 2ND-7002_Iris OPTION検査_ブロック図Ver.2.2_201223.pdf

# `DP IF ASSY_7PA1153CJF.pdf` — Q2519–2521

## CÂU HỎI 2519
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra đường PCIe của DP interface và cần xác định đúng tín hiệu ở trang DP IF.
- Cách hỏi: tình huống
- Hỏi: Trang `DP IF` ghi những cặp tín hiệu PCIe vi sai nào?
- Đáp: Các cặp đọc được gồm `PCIEP_REFCLK_DP22DP1 / PCIEN_REFCLK_DP22DP1`, `PCIEP_DP12DP2 / PCIEN_DP12DP2` và `PCIEP_DP22DP1 / PCIEN_DP22DP1`. Nguồn file: DP IF ASSY_7PA1153CJF.pdf

## CÂU HỎI 2520
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 DP IF 页面使用的主要电源。
- Cách hỏi: so sánh
- Hỏi: `DP IF` 页面主要出现哪两种正电源？
- Đáp: 主要可见 `+5.0V4` 和 `+3.3V4`；同时有多处 `GND` 与 `GND_PCIERCPLL`。Nguồn file: DP IF ASSY_7PA1153CJF.pdf

## CÂU HỎI 2521
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: DP IF のコネクタ仕様を再確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: DP IF ページの `YC5` は `FX23L-40P-0.5SV10`、40ピンで、LockPin 1/2 も記載されていますね。
- Đáp: はい。YC5 は `FX23L-40P-0.5SV10`、ピン番号 `1～40` が記載され、`LockPin(1) LP-1` と `LockPin(2) LP-2` もあります。Nguồn file: DP IF ASSY_7PA1153CJF.pdf
