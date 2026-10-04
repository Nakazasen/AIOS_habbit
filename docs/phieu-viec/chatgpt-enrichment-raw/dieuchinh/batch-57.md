# Mẻ 57 — Điều-tra-lỗi: `SƠ đồ điện/` (7/84 file đầu) — Q2464–Q2491

- Ngày: 2026-10-04
- Nguồn: local `~/workspace/dieuchinh_zip/dieuchinh.zip` → trích → upload Drive riêng (`chatgpt-enrichment-dieu-chinh`, anyone-reader)
- Chat: https://chatgpt.com/c/6ac21250-cce4-83ec-a85f-5456b6a23733 (ChatGPT phiên mặc định hiện tại, theo quy trình từ đầu)
- 7 file, 28 cặp. **SỰ CỐ: không có** — 7m17s, "Đã hoàn tất phản hồi", không cloudflare, không cắt, không hết giới hạn.
- Ngôn ngữ: vi=9, zh=9, ja=10 — ĐÚNG mục tiêu.
- Cách hỏi: mỗi file 4 cặp dùng 4 cách khác nhau luân phiên; toàn mẻ đủ cả 5 cách.
- Chất lượng: cả 7 file hầu như KHÔNG có lớp text trích xuất — ChatGPT đọc từ trang sơ đồ render trực tiếp, chỉ dùng nhãn/giá trị nhìn đọc được rõ; có cảnh báo rõ "không thể kết luận nguyên nhân linh kiện từ sơ đồ" khi phù hợp; không bịa chi tiết; không file nào bị bỏ qua; nội dung là tài liệu mạch/BOM, không trùng `Loi KDTPS.xlsx`.
- Tóm tắt 7 file:
  1. `Iris2020_302ND45060(定着).pdf`: 1 trang, sơ đồ CIRCUIT DIAGRAM, model `EUK9SQD06HA`, ngày `2016.2.04`; transformer `T101`, các nhánh `NC_S/NC_F`, `NB_S/NB_F`, `ND_S/ND_F`, ngõ `FSR1`, linh kiện R/D/C.
  2. `7PA1111B_回路図_180423.pdf`: 3 trang (INDEX, CHANGE_HISTORY, HUMAN DETECT); board `P.W.B HUMAN DETECT ASSY`; sensor `NY1`, op-amp, regulator, EEPROM, connector `YC1` (HUMAN_DETECT/I²C).
  3. `Iris_2ND_IH_MP_01基板回路図_302ND47341_20170116.pdf`: 3 trang (INDEX, CHANGE HISTORY, CPU); board `PWB IH CONTROL ASSY`, ASSY `302ND47341`; tín hiệu `AVN/AVP/TH1/AIN/AIP`, nguồn `+3.3V`, connector `YC1`.
  4. `7PA0547CJF_回路図20181113_KUIO.pdf`: 3 trang (INDEX, CHANGE HISTORY, MAIN I/F and KUIO I/F); board `PWB KUIO ASSY`; `YC1/YC2/YC3/YC4`, USB DN/DP, AUDIO, WAKEUP, RESET, đường 5V.
  5. `Iris2020_302XF45020(転写)_Ver1.2.pdf`: 2 trang CIRCUIT DIAGRAM, model `EUK9MQD85HA`, ngày `2019.09.26`; đầu vào `24V`, tín hiệu `T1CNT(K)`, `T1(K)`, transformer/op-amp.
  6. `302XC47150_03.pdf`: 3 trang (INDEX, CHANGE_HISTORY, PANEL I/F); board `PWB OPERATION ASSY`, ASSY `302XC47150`; `Home Key`, Energy Saver/Attention/Processing LED, connector `YC1`.
  7. `302XC45030_sơ đồ_datasheet.pdf`: 17 trang; Circuit Diagram `OPEN FRAME`, Part No. `ETX9KC995ME`, Manufacturer P/N `PBA053220500` + nhiều trang BOM/standard-part list.
- Số liệu nổi bật: T101 các nhánh NC_S 1/NC_F 2/NB_S 3/NB_F 4/ND_S 5/ND_F 6 (+NS_S/NS_F); FSR1 trước có R127/R128/R129, gần có ZD104/D110; YC1 Human Detect: GND/INT_HUMAN_DETECT/HD_SDA/HD_SWCLK/+3.3V1_HD; nguồn +3.3V1_HD → +2.5V; IH CPU: AVN/AVP/TH1/AIN/AIP, TP12 (TH1), TP1 (AIN), TP2–TP11; KUIO YC1/YC2 20-pin (VBUS/USB_DN/USB_DP/GND/RESERVE/AUDIO/WAKEUP/VDD5_CUT/RESETN/VDD5), YC4 6-pin (5V_CUT1/GND/5V/GND/5V_CUT0/GND); transfer 24V, fuse F101 (250V 1.6A); panel: Home Key S1 giữa KEY2–SCAN3, LED resistor R6=1.5K (Energy Saver), R3/R4/R5=510 (Attention), R1/R2=430 (Processing); BOM: C205,C110 = 471 50V RUQ 2; C108 = 102 50V RUQ 1.
- Còn lại ZIP Điều tra lỗi: `SƠ đồ điện/` 77 file chưa làm; `Lịch sử lỗi/` 2022 mục chưa làm (đã upload 30 file Excel/PDF đầu tiên).
- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.

---

# `Iris2020_302ND45060(定着).pdf` — Q2464–2467

## CÂU HỎI 2464
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 定着関連の回路図を開き、図面の基本情報を確認している。
- Cách hỏi: trực tiếp
- Hỏi: この回路図の Model と日付は何ですか。
- Đáp: Model は `EUK9SQD06HA`、図面の日付は `2016.2.04` です。Nguồn file: Iris2020_302ND45060(定着).pdf

## CÂU HỎI 2465
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang kiểm tra các cuộn thứ cấp quanh transformer T101.
- Cách hỏi: tình huống
- Hỏi: Các đầu cuộn được ghi quanh `T101` là những nhãn nào?
- Đáp: Sơ đồ ghi các nhánh `NC_S 1`, `NC_F 2`, `NB_S 3`, `NB_F 4`, `ND_S 5`, `ND_F 6`; phía cuộn còn lại còn thấy `NS_S` và `NS_F`. Nguồn file: Iris2020_302ND45060(定着).pdf

## CÂU HỎI 2466
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 FSR 输出路径中的串联电阻。
- Cách hỏi: so sánh
- Hỏi: `FSR1` 前的三个串联电阻标号是什么？
- Đáp: 从左到右为 `R127`、`R128`、`R129`，然后连接到标记为 `FSR1` 的端点。Nguồn file: Iris2020_302ND45060(定着).pdf

## CÂU HỎI 2467
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: FSR 信号が出ないため、図面上の周辺素子を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `FSR1` 経路を図面で追う場合、R127～R129以外に直前付近で確認できるダイオードは何ですか。
- Đáp: 直前側には `ZD104` と `D110` が記載されています。図面は接続関係を示していますが、これらの単独部品を故障原因とは断定していません。Nguồn file: Iris2020_302ND45060(定着).pdf

# `7PA1111B_回路図_180423.pdf` — Q2468–2471

## CÂU HỎI 2468
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận đây có đúng là board Human Detect trước khi đo tín hiệu.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File có 3 trang gồm INDEX, CHANGE_HISTORY và HUMAN DETECT, và tên board là `P.W.B HUMAN DETECT ASSY`, đúng không?
- Đáp: Đúng. Trang INDEX liệt kê `PAGE01(INDEX)`, `PAGE02(CHANGE_HISTORY)`, `PAGE03(HUMAN DETECT)`. Nguồn file: 7PA1111B_回路図_180423.pdf

## CÂU HỎI 2469
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认 Human Detect 板外部接口信号。
- Cách hỏi: trực tiếp
- Hỏi: `YC1` 连接器上明确标出的五个信号是什么？
- Đáp: Pin 侧标记为 `GND`、`INT_HUMAN_DETECT`、`HD_SDA`、`HD_SWCLK`、`+3.3V1_HD`。Nguồn file: 7PA1111B_回路図_180423.pdf

## CÂU HỎI 2470
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Human Detect 信号と通信信号を区別して測定している。
- Cách hỏi: tình huống
- Hỏi: 人検知の割込み信号と、通信に使われる二つの信号は図面で何と表記されていますか。
- Đáp: 割込み信号は `INT_HUMAN_DETECT`、通信側は `HD_SDA` と `HD_SWCLK` です。Nguồn file: 7PA1111B_回路図_180423.pdf

## CÂU HỎI 2471
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh hai mức nguồn thể hiện trên board Human Detect.
- Cách hỏi: so sánh
- Hỏi: Trên sơ đồ có những mức nguồn nào được ghi rõ quanh mạch nguồn và YC1?
- Đáp: Có `+3.3V1_HD` và `+2.5V`; phần regulator trên sơ đồ chuyển từ đường `+3.3V1_HD` sang rail `+2.5V`. Nguồn file: 7PA1111B_回路図_180423.pdf

# `Iris_2ND_IH_MP_01基板回路図_302ND47341_20170116.pdf` — Q2472–2475

## CÂU HỎI 2472
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师根据 IH CONTROL CPU 图检查模拟输入线路。
- Cách hỏi: xử lý sự cố
- Hỏi: 如果要沿图追踪模拟输入，图中明确标出的输入信号有哪些？
- Đáp: 图中明确标有 `AVN`、`AVP`、`TH1`、`AIN`、`AIP`。这些标签连接到 CPU/接口电路，但仅从图面不能判断哪一路已经故障。Nguồn file: Iris_2ND_IH_MP_01基板回路図_302ND47341_20170116.pdf

## CÂU HỎI 2473
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: IH CONTROL 基板の資料構成を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: この資料は3ページで、3ページ目が `CPU`、ASSY No. が `302ND47341` で合っていますか。
- Đáp: はい。INDEXには `1.INDEX / 2.CHANGE HISTORY / 3.CPU` とあり、タイトルブロックの ASSY No. は `302ND47341` です。Nguồn file: Iris_2ND_IH_MP_01基板回路図_302ND47341_20170116.pdf

## CÂU HỎI 2474
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần xác nhận các tín hiệu được đưa ra connector YC1.
- Cách hỏi: trực tiếp
- Hỏi: Connector `YC1` trên sơ đồ CPU có những nhãn tín hiệu chính nào?
- Đáp: Các nhãn đọc được gồm `AVN`, `AVP`, `TH1`, `AIN`, `AIP`, `RD`, các đường `+3.3V` và `SGND1`. Nguồn file: Iris_2ND_IH_MP_01基板回路図_302ND47341_20170116.pdf

## CÂU HỎI 2475
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师在测量 TH1 与 AIN 路径时确认测试点。
- Cách hỏi: tình huống
- Hỏi: 图中 TH1 和 AIN 附近是否标出了 Test Point？
- Đáp: 有。`TH1` 路径附近标有 `TP12`，`AIN` 路径附近可见 `TP1`；图中还分布有 TP2～TP11 等测试点。Nguồn file: Iris_2ND_IH_MP_01基板回路図_302ND47341_20170116.pdf

# `7PA0547CJF_回路図20181113_KUIO.pdf` — Q2476–2479

## CÂU HỎI 2476
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: KUIO I/F の二系統USBコネクターを比較している。
- Cách hỏi: so sánh
- Hỏi: `YC1` と `YC2` にはどのような共通信号がありますか。
- Đáp: 両方とも20ピン構成で、`VBUS`、`USB_DN`、`USB_DP`、`GND`、`RESERVE`、`AUDIO`、`WAKEUP`、`VDD5_CUT`、`RESETN`、`VDD5` などが同じ並びで記載されています。Nguồn file: 7PA0547CJF_回路図20181113_KUIO.pdf

## CÂU HỎI 2477
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra đường USB nhưng chưa có tín hiệu ở đầu connector.
- Cách hỏi: xử lý sự cố
- Hỏi: Trên `YC3`, những đường USB nào được ghi cho kênh 1 và kênh 0?
- Đáp: Kênh 1 có `VBUS1`, `USB_DN1`, `USB_DP1`; kênh 0 có `VBUS0`, `USB_DM0`, `USB_DP0`. Sơ đồ còn ghi `AUDIO1/0`, `WAKEUP1/0` và `RESETN1/0`; chỉ từ việc mất một tín hiệu chưa thể kết luận nguyên nhân linh kiện. Nguồn file: 7PA0547CJF_回路図20181113_KUIO.pdf

## CÂU HỎI 2478
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 KUIO 板的辅助 5V 接口。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `YC4` 是6 pin，依次包含 `5V_CUT1/GND/5V/GND/5V_CUT0/GND`，对吗？
- Đáp: 对。图中 YC4 的6个位置正是按这一组信号标注。Nguồn file: 7PA0547CJF_回路図20181113_KUIO.pdf

## CÂU HỎI 2479
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: KUIO 基板の図面情報を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: この基板の ASSY No.、Rev.、日付は何ですか。
- Đáp: ASSY No.=`302K947270`、Rev.=`03`、日付=`2018/11/13` です。Nguồn file: 7PA0547CJF_回路図20181113_KUIO.pdf

# `Iris2020_302XF45020(転写)_Ver1.2.pdf` — Q2480–2483

## CÂU HỎI 2480
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra đầu vào nguồn của mạch chuyển transfer.
- Cách hỏi: tình huống
- Hỏi: Trang 1 cho thấy đầu vào nguồn chính nào và fuse nào nằm ngay sau đầu vào?
- Đáp: Đầu vào được ghi `24V`; ngay trên đường này có fuse `F101` với ghi chú `250V 1.6A`. Nguồn file: Iris2020_302XF45020(転写)_Ver1.2.pdf

## CÂU HỎI 2481
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较第一页控制端与右侧输出端的信号名称。
- Cách hỏi: so sánh
- Hỏi: 控制输入和右侧输出分别标成什么？
- Đáp: 左侧控制信号标为 `T1CNT(K)`，右侧输出端标为 `T1(K)`。Nguồn file: Iris2020_302XF45020(転写)_Ver1.2.pdf

## CÂU HỎI 2482
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: T1系統の出力異常を回路図で追っている。
- Cách hỏi: xử lý sự cố
- Hỏi: `T1(K)` へ至る回路に、トランスと複数の抵抗・ダイオードが描かれていますが、この図だけで特定部品を故障原因と断定できますか。
- Đáp: できません。図面ではトランス、抵抗、ダイオード、コンデンサなどの接続が確認できますが、故障判定値や特定部品の故障確定条件は記載されていません。Nguồn file: Iris2020_302XF45020(転写)_Ver1.2.pdf

## CÂU HỎI 2483
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận thông tin title block trước khi dùng sơ đồ.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Model trên bản vẽ là `EUK9MQD85HA`, ngày `2019.09.26`, đúng không?
- Đáp: Đúng. Title block ghi `EUK9MQD85HA`, `CIRCUIT DIAGRAM` và ngày `2019.09.26`. Nguồn file: Iris2020_302XF45020(転写)_Ver1.2.pdf

# `302XC47150_03.pdf` — Q2484–2487

## CÂU HỎI 2484
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 Operation board 的 Panel I/F 构成。
- Cách hỏi: trực tiếp
- Hỏi: `YC1` 上标出的主要控制信号有哪些？
- Đáp: 可读到 `KEY2`、`SCAN3`、`LED_ENERGYSAVER_N`、`LED_ATTENTION_N`、`+5.0V1_PANEL`、`LED_PROCESSING_N`。Nguồn file: 302XC47150_03.pdf

## CÂU HỎI 2485
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Home Key が反応しないため、図面上の接続を確認している。
- Cách hỏi: tình huống
- Hỏi: `Home Key` と記載された S1 はどの二つの信号間に接続されていますか。
- Đáp: S1 `Home Key` は `KEY2` と `SCAN3` の間に接続されています。Nguồn file: 302XC47150_03.pdf

## CÂU HỎI 2486
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh điện trở hạn dòng của ba nhóm LED trên panel.
- Cách hỏi: so sánh
- Hỏi: Giá trị resistor của Energy Saver LED, Attention LED và Processing LED khác nhau thế nào?
- Đáp: Energy Saver LED dùng `R6=1.5K`; Attention LED dùng `R3/R4/R5=510`; Processing LED dùng `R1/R2=430`. Nguồn file: 302XC47150_03.pdf

## CÂU HỎI 2487
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师排查 Panel LED 不亮，先根据原图确认颜色分组。
- Cách hỏi: xử lý sự cố
- Hỏi: 图中三个 LED 功能组分别标注什么颜色？
- Đáp: `ENERGY_SAVER_LED` 标注为青色，`ATTENTION_LED` 标注为橙色，`PROCESSING_LED` 标注为青色。仅凭 LED 不亮不能从该图确定具体故障元件。Nguồn file: 302XC47150_03.pdf

# `302XC45030_sơ đồ_datasheet.pdf` — Q2488–2491

## CÂU HỎI 2488
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 17ページ資料の構成を確認してから部品表を参照している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: このPDFは回路図だけではなく、`OPEN FRAME` の回路図と部品BOM/標準部品表を含む資料ですね。
- Đáp: はい。PDFは17ページで、回路図ページに `OPEN FRAME`、Part No. `ETX9KC995ME`、Manufacturer P/N `PBA053220500` があり、その後に部品表ページが続きます。Nguồn file: 302XC45030_sơ đồ_datasheet.pdf

## CÂU HỎI 2489
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận metadata in ngay trên trang circuit diagram.
- Cách hỏi: trực tiếp
- Hỏi: Trang Circuit Diagram ghi Customer, Part No., Manufacturer P/N và ngày nào?
- Đáp: Customer=`SA00998`, Part No.=`ETX9KC995ME`, Manufacturer P/N=`PBA053220500`, ngày=`2021-09-29`. Nguồn file: 302XC45030_sơ đồ_datasheet.pdf

## CÂU HỎI 2490
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师在 BOM 中核对 C205 和 C110 的电容规格。
- Cách hỏi: tình huống
- Hỏi: `C205,C110` 对应的 CERAMIC CHIP CAPACITOR 的 Rating 和 RUQ 是什么？
- Đáp: Rating=`471 50V`，RUQ=`2`。BOM 同时列出 MURATA、SAMSUNG ELECTRO-MECHANICS、WALSIN、DARFON 等可对应的制造商料号。Nguồn file: 302XC45030_sơ đồ_datasheet.pdf

## CÂU HỎI 2491
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: BOM内で C108 と C205/C110 のコンデンサ条件を比較している。
- Cách hỏi: so sánh
- Hỏi: `C108` と `C205,C110` の Rating/RUQ はどう違いますか。
- Đáp: `C108` は Rating=`102 50V`、RUQ=`1`。`C205,C110` は Rating=`471 50V`、RUQ=`2` です。Nguồn file: 302XC45030_sơ đồ_datasheet.pdf
