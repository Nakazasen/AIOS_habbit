# Mẻ 59 — Điều-tra-lỗi: `SƠ đồ điện/` (10/84 file tiếp theo) — Q2522–Q2551

- Ngày: 2026-10-04
- Nguồn: local `~/workspace/dieuchinh_zip/dieuchinh.zip` → trích → upload Drive riêng (`chatgpt-enrichment-dieu-chinh`, anyone-reader)
- Chat: https://chatgpt.com/c/6ac21250-cce4-83ec-a85f-5456b6a23733 (ChatGPT phiên mặc định hiện tại, theo quy trình từ đầu)
- 10 file, 30 cặp. **SỰ CỐ NHẸ: phản hồi đầu tiên bị cắt sau Q2536** (chỉ có báo cáo cấu trúc + Q2522–2536); đã nhắn "tiếp tục" đúng 1 lần theo quy tắc → ChatGPT sinh tiếp Q2537–Q2551 đầy đủ. Thu hồi toàn văn 30 cặp qua copy→paste→file preview. Không giới hạn Plus, không cloudflare. Tổng thời gian 7m38s cho phần đầu + thời gian sinh tiếp.
- Ngôn ngữ: vi=10, zh=10, ja=10 — ĐÚNG mục tiêu.
- Cách hỏi: mỗi file 3 cặp dùng 3 cách khác nhau luân phiên; toàn mẻ đủ cả 5 cách.
- Chất lượng: chỉ dùng nhãn/giá trị xuất hiện trong nguồn, không bịa chi tiết; có cảnh báo "không thể kết luận linh kiện hỏng từ sơ đồ" khi phù hợp; **các file là phiên bản khác với mẻ trước được phân biệt đúng** — IH 302ND47260 (PWB IH 200 ASSY, 6 trang MAIN AC/IGBT DRIVER/EngineI/F/JUMPER) vs 302ND47341 ở mẻ 57 (IH CONTROL, 3 trang); 転写 Ver1.1 model thực tế **EUK9MQD84HA** (Drawing No. 111-EUK9MQD84HA-C01) vs Ver1.2 ở mẻ 57 là EUK9MQD85HA — không lặp cặp đã sinh; không file nào bị bỏ qua; nội dung là tài liệu mạch/sơ đồ dây, không trùng `Loi KDTPS.xlsx`.
- Tóm tắt 10 file:
1. `PA1203A_Inner Shift Tray_回路図_20190622.pdf`: 3 trang, PWB INNER SHIFT TRAY ASSY (ASSY T03TB01010, PWB TPA1203ACZ+GH01); YC1 (+3.3V_LED/GND/HP_SENS/OUT1/OUT2), YC2 (SET/3.3V/HP_SENS/IN1/IN2/24V/GND), driver TB67H450FNG; nguồn +3.3V/+24V.
2. `USB HUB_3V2XC47160.pdf`: 4 trang, P.W.BOARD ASSY USB HUB (ASSY 3V2XC47160, PWB 7PA1197BJF+GH01, ngày 2019/09/13); upstream VBUS/USBDM/USBDP, bốn nhánh downstream USBH_DN1/DP1–DN4/DP4, VBUS_USBH_1–4; clock X1 = 24.000 MHz; nguồn +3.3V13/+5.0V13_HUB; Change History ghi ASSY No. 302XC47160 → 3V2XC47160 (Việt Nam).
3. `302XD47260-03.pdf`: 4 trang, PWB CMOS SENSOR ASSY (ASSY 302XD47260, Rev. 3, PWB 7PA1329BVP+GH01); CMOS SENSOR,CAP + IF,POWER; Rev.01: bản dưới phát triển từ board trên, bỏ U3/U4, đổi YC1; Rev.03 (2021/3/24): R94 từ chưa lắp → 10kΩ; LED: LED_PWM/LED_ENABLE/LED_PWM_AND/LED_PWM_CMOS; board 181×30.0mm, dày 1.6mm, 4 lớp.
4. `302XF47060-04.pdf`: 3 trang, P.W.BOARD ASSY DRUM/DLP CONNECT (a-Si, Mono) (ASSY 302XF47060, Rev. 04, PWB 7PA1192BCZ+GH01, ngày 2019/9/12); DLP/DRUM connector, fan, heater, EEPROM; YC1: ERASER_PWM/DLP_TH/DRM_HEAT_REM/DLP_FAN_REM, 5V0_F2/24V2_F1/3.3V2; YC5: pin1 DLP_FAN_BK, pin2 24V2_F1.
5. `Iris_2ND_IH_MP_01基板回路図_302ND47260_20170116.pdf`: 6 trang, PWB IH 200 ASSY (ASSY 302ND47260, Rev. 08, PWB 7PA0860EHT+AH01); MAIN AC / IGBT DRIVER / EngineI/F_CPUI/F_Power 3.3V 15V1 / JUMPER; KHÁC file 302ND47341 ở mẻ 57.
6. `Iris2020_302XC45020(転写)_Ver1.1.pdf`: 2 trang, model thực tế **EUK9MQD84HA** (Drawing No. 111-EUK9MQD84HA-C01) — khác Ver1.2 ở mẻ 57 (EUK9MQD85HA); T1CNT(K) → T1(K), 24V, F101 250V 1.6A; T104: NC_S/NC_F, NB_S/NB_F, ND_S/ND_F, NS_S/NS_F.
7. `7PA1187DCZ 回路図.pdf`: 11 trang, PWB DP DRIVER ASSY (ASSY 303TD47030, PWB 7PA1187DCZ+GH01); CPU, ENGINE/SHD IF, INTERLOCK/SSW IF, FEED UNIT, DRIVER1–3/FAN, POWER/DEMICAP; nguồn 24V sau interlock: +R24V1 (lift/FAN), +R24V2 (convey/discharge), +R24V3 (feed/register), +3.3V3 (Sleep), +3.3V (DC/DC).
8. `3V2XC01141.pdf`: 10 trang, PRINTED W.BOARD PANEL (ASSY T02XC01140, PWB TPA1204BDS+GH01); CPU/KEY_LED/SPEAKER/MAIN IF/Touch Panel & Backlight/THCV234/LDO/FET/LCD Bias; Rev.1.0: R39,R40 100Ω→0Ω (DMT BOM); Rev.1.1 (2019/9/4): A版→B版; pull-up 10kΩ, pull-down 47kΩ (quy tắc thiết kế, không phải giá trị chẩn đoán lỗi).
9. `PF全体配線図.xlsx`: 7 sheet (表紙/変更履歴/500枚×2 PF/1500枚×2 PF/3000枚PF/ハーネス品番/memo); sơ đồ dây, harness code, connector, lịch sử thay đổi; 03V4: 303RB46050→303V446040; 03V5: 303RC46020→303V546020; sensor1 173977-3→353908-3, sensor2 173977-3→353293-3.
10. `302XC47100_03.pdf`: 3 trang, P.W.BOARD ASSY TONER SENSOR (ASSY 302XC47100, Rev. 03, PWB 7PA1178ASS+GH01); YC1: pin1=TH, pin3=3.3V2, pin4=ADR0, pin5=ADR1; 波形調整: R2=330, R3=51, C1=1u, C8=0.01u.
- Số liệu nổi bật: X1 = 24.000 MHz; R94 10kΩ (Rev.03); pull-up 10kΩ/pull-down 47kΩ; harness 303RB46050→303V446040 / 303RC46020→303V546020; R39/R40 100Ω→0Ω; phân nhóm 24V +R24V1/2/3; T104 các cặp NC_S/NC_F, NB_S/NB_F, ND_S/ND_F, NS_S/NS_F.
- Còn lại ZIP Điều tra lỗi: `SƠ đồ điện/` 57 file chưa làm; `Lịch sử lỗi/` 2022 mục chưa làm (đã upload 30 file Excel/PDF đầu tiên).
- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.

---

# `PA1203A_Inner Shift Tray_回路図_20190622.pdf` — Q2522–2524

## CÂU HỎI 2522
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận đúng board trước khi đo Inner Shift Tray.
- Cách hỏi: trực tiếp
- Hỏi: Board này có ASSY No., PWB No. và nguồn chính nào?
- Đáp: ASSY No.=`T03TB01010`, PWB No.=`TPA1203ACZ+GH01`; Power Table ghi `+3.3V` và `+24V`, ground=`GND`. Nguồn file: PA1203A_Inner Shift Tray_回路図_20190622.pdf

## CÂU HỎI 2523
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师检查 Shift Motor 和 HP Sensor 的单元接口。
- Cách hỏi: tình huống
- Hỏi: `YC1` 上标出的5个信号是什么？
- Đáp: `+3.3V_LED`、`GND`、`HP_SENS`、`OUT1`、`OUT2`。Nguồn file: PA1203A_Inner Shift Tray_回路図_20190622.pdf

## CÂU HỎI 2524
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: ユニット側 YC1 と Image基板側 YC2 の信号構成を比較している。
- Cách hỏi: so sánh
- Hỏi: `YC1` と `YC2` の主な信号構成はどう違いますか。
- Đáp: YC1 は `+3.3V_LED/GND/HP_SENS/OUT1/OUT2` の5系統です。YC2 は `SET/3.3V/HP_SENS/IN1/IN2/24V/GND` の7系統です。Nguồn file: PA1203A_Inner Shift Tray_回路図_20190622.pdf

# `USB HUB_3V2XC47160.pdf` — Q2525–2527

## CÂU HỎI 2525
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: USB downstream không giao tiếp và kỹ sư cần lần đúng tín hiệu trên sơ đồ.
- Cách hỏi: xử lý sự cố
- Hỏi: Theo sơ đồ, nên lần những nhãn nào từ phía upstream sang bốn nhánh downstream?
- Đáp: Phía upstream có `VBUS`, `USBDM`, `USBDP`; phía downstream có các cặp `USBH_DN1/DP1` đến `USBH_DN4/DP4` và các đường `VBUS_USBH_1` đến `VBUS_USBH_4`. Sơ đồ chỉ cho đường kết nối; không đủ để kết luận nguyên nhân hỏng từ một tín hiệu riêng lẻ. Nguồn file: USB HUB_3V2XC47160.pdf

## CÂU HỎI 2526
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认正在使用的是越南品号版本。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 文件的 ASSY No. 是 `3V2XC47160`，PWB 是 `7PA1197BJF+GH01`，日期为 `2019/09/13`，对吗？
- Đáp: 对。Change History 还记载 ASSY No. 从 `302XC47160` 替换为越南品号 `3V2XC47160`。Nguồn file: USB HUB_3V2XC47160.pdf

## CÂU HỎI 2527
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: USB HUB の基準クロックを確認している。
- Cách hỏi: trực tiếp
- Hỏi: `X1` に記載されたクロック周波数はいくつですか。
- Đáp: `24.000 MHz` です。Nguồn file: USB HUB_3V2XC47160.pdf

# `302XD47260-03.pdf` — Q2528–2530

## CÂU HỎI 2528
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận thông số cơ bản của CMOS Sensor board bản 02XD.
- Cách hỏi: tình huống
- Hỏi: Board có kích thước, độ dày và số lớp được ghi thế nào?
- Đáp: Kích thước board=`181 mm × 30.0 mm`, độ dày=`1.6 mm`, số lớp=`4 lớp`; lắp linh kiện hai mặt bằng reflow hai mặt. Nguồn file: 302XD47260-03.pdf

## CÂU HỎI 2529
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较初版与 Rev.03 的变更内容。
- Cách hỏi: so sánh
- Hỏi: Rev.01 与 Rev.03 的主要变更分别是什么？
- Đáp: Rev.01 记录为基于上位 CMOS SENSOR 板制作下位用板，删除 `U3/U4` 等周边部件并更改 `YC1`；Rev.03 在 `2021/3/24` 将 `R94` 从未安装改为 `10kΩ`。Nguồn file: 302XD47260-03.pdf

## CÂU HỎI 2530
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: LED 制御系を追っているが、単一信号だけで原因を決めないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: LED系で図面上確認できる制御信号は何ですか。
- Đáp: `LED_PWM`、`LED_ENABLE`、`LED_PWM_AND`、`LED_PWM_CMOS` が確認できます。どれか1信号の状態だけから故障原因を断定することはできません。Nguồn file: 302XD47260-03.pdf

# `302XF47060-04.pdf` — Q2531–2533

## CÂU HỎI 2531
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra đúng revision của board DLP/DRUM trước khi đối chiếu dây.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File này là `P.W.BOARD ASSY DRUM/DLP CONNECT (a-Si, Mono)`, ASSY `302XF47060`, Rev. `04`, đúng không?
- Đáp: Đúng. PWB No. là `7PA1192BCZ+GH01`, ngày title block là `2019/9/12`. Nguồn file: 302XF47060-04.pdf

## CÂU HỎI 2532
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接检查 Image board 接口的控制信号。
- Cách hỏi: trực tiếp
- Hỏi: `YC1` 一侧能读到哪些与 DLP/DRUM 相关的主要信号？
- Đáp: 可读到 `ERASER_PWM`、`DLP_TH`、`DRM_HEAT_REM`、`DLP_FAN_REM`，以及 `5V0_F2`、`24V2_F1`、`3.3V2` 等。Nguồn file: 302XF47060-04.pdf

## CÂU HỎI 2533
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: DLP FAN 系統の配線を確認している。
- Cách hỏi: tình huống
- Hỏi: `YC5` には DLP FAN 関連で何が記載されていますか。
- Đáp: `YC5` では pin 1 に `DLP_FAN_BK`、pin 2 に `24V2_F1` が記載されています。Nguồn file: 302XF47060-04.pdf

# `Iris_2ND_IH_MP_01基板回路図_302ND47260_20170116.pdf` — Q2534–2536

## CÂU HỎI 2534
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư muốn phân biệt các khối chính trong IH 200 board.
- Cách hỏi: so sánh
- Hỏi: Các trang mạch chính được tách thế nào giữa AC, IGBT và interface/power?
- Đáp: Trang 3 là `MAIN AC`, trang 4 là `IGBT DRIVER`, trang 5 là `EngineI/F_CPUI/F_Power 3.3V 15V1`, và trang 6 là `JUMPER`. Nguồn file: Iris_2ND_IH_MP_01基板回路図_302ND47260_20170116.pdf

## CÂU HỎI 2535
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师排查 IH 板电源，但只想按原图追踪。
- Cách hỏi: xử lý sự cố
- Hỏi: 图纸中明确把哪些电源写在 Engine/CPU I/F 页标题里？
- Đáp: 标题明确写有 `Power 3.3V 15V1`。因此可按 `3.3V` 与 `15V1` 相关线路追踪，但不能仅凭某一路异常直接断定故障元件。Nguồn file: Iris_2ND_IH_MP_01基板回路図_302ND47260_20170116.pdf

## CÂU HỎI 2536
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 前回の IH CONTROL 資料と取り違えないよう、今回の基板番号を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 今回の資料は `PWB IH 200 ASSY`、ASSY=`302ND47260`、Rev.=`08`、PWB=`7PA0860EHT+AH01` ですね。
- Đáp: はい。その通りです。資料は全 `6` ページです。Nguồn file: Iris_2ND_IH_MP_01基板回路図_302ND47260_20170116.pdf

# `Iris2020_302XC45020(転写)_Ver1.1.pdf` — Q2537–2539

## CÂU HỎI 2537
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư phân biệt Ver1.1 với bản transfer đã dùng ở mẻ trước.
- Cách hỏi: trực tiếp
- Hỏi: Ver1.1 này ghi Model và Drawing No. nào?
- Đáp: Model=`EUK9MQD84HA`, Drawing No.=`111-EUK9MQD84HA-C01`; file có `2` trang. Nguồn file: Iris2020_302XC45020(転写)_Ver1.1.pdf

## CÂU HỎI 2538
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师沿 Transfer K 通道追踪控制输入到输出。
- Cách hỏi: tình huống
- Hỏi: 图中 K 通道的控制输入和高压输出分别标为什么？
- Đáp: 控制输入标为 `T1CNT(K)`，输出标为 `T1(K)`；输入侧还标有 `24V`，并可见 `F101 250V 1.6A`。Nguồn file: Iris2020_302XC45020(転写)_Ver1.1.pdf

## CÂU HỎI 2539
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Ver1.1 の T104 二次側端子を比較している。
- Cách hỏi: so sánh
- Hỏi: T104 の端子にはどのようなペア名が記載されていますか。
- Đáp: `NC_S/NC_F`、`NB_S/NB_F`、`ND_S/ND_F`、`NS_S/NS_F` が記載されています。Nguồn file: Iris2020_302XC45020(転写)_Ver1.1.pdf

# `7PA1187DCZ 回路図.pdf` — Q2540–2542

## CÂU HỎI 2540
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra DP Driver nhưng muốn chọn đúng nhóm nguồn theo tải.
- Cách hỏi: xử lý sự cố
- Hỏi: Power table phân chia các nguồn 24V sau interlock thế nào?
- Đáp: File ghi `+R24V1` cho lift/FAN, `+R24V2` cho convey/discharge, `+R24V3` cho feed/register; ngoài ra có `+3.3V3` cho Sleep và `+3.3V` tạo bởi DC/DC. Đây là phân nhóm nguồn trong sơ đồ, không phải kết luận lỗi. Nguồn file: 7PA1187DCZ 回路図.pdf

## CÂU HỎI 2541
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 DP DRIVER 文档的页面分类。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 文件共有11页，并包含 `FEED_UNIT`、`DRIVER1`、`DRIVER2`、`DRIVER3/FAN`、`POWER/DEMICAP`，对吗？
- Đáp: 对。前面还包括 `CPU`、`ENGINE_IF/SHD_IF`、`INTERLOCK/SSW_IF`、`TABLE_UNIT/SPLASH_SW` 等页面。Nguồn file: 7PA1187DCZ 回路図.pdf

## CÂU HỎI 2542
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: DP Driver 基板の識別情報を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: ASSY No. と PWB No. は何ですか。
- Đáp: ASSY No.=`303TD47030`、PWB No.=`7PA1187DCZ+GH01` です。Nguồn file: 7PA1187DCZ 回路図.pdf

# `3V2XC01141.pdf` — Q2543–2545

## CÂU HỎI 2543
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra panel và cần biết nên mở trang nào theo chức năng.
- Cách hỏi: tình huống
- Hỏi: File phân tách các chức năng panel thành những trang chính nào?
- Đáp: Có `CPU`, `KEY_LED`, `SPEAKER`, `MAIN IF`, `Touch Panel & Backlight`, `THCV234`, `LDO & FET`, `LCD Bias`, ngoài INDEX và CHANGE_HISTORY. Nguồn file: 3V2XC01141.pdf

## CÂU HỎI 2544
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较初版与 1.1 版的 PCB 变更。
- Cách hỏi: so sánh
- Hỏi: Change History 中 Rev.1.0 与 Rev.1.1 的主要区别是什么？
- Đáp: Rev.1.0 为初版，并记录 DMT BOM 修正，包括 `R39,R40 100Ω→0Ω` 等；Rev.1.1 在 `2019/9/4` 记录生板版数从 `A版→B版`。Nguồn file: 3V2XC01141.pdf

## CÂU HỎI 2545
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: パネル不具合を調べているが、図面だけで原因部品を決めないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: この資料の基本 Pull-up/Pull-down 値は何ですか。また、その値だけで故障判定できますか。
- Đáp: 基本 Pull-up は `10 kΩ`、Pull-down は `47 kΩ` と記載されています。これらは回路設計ルールであり、単独で故障判定値にはできません。Nguồn file: 3V2XC01141.pdf

# `PF全体配線図.xlsx` — Q2546–2548

## CÂU HỎI 2546
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận workbook có đủ sơ đồ cho ba loại PF trước khi tra harness.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Workbook có riêng sheet cho PF `500枚×2`, `1500枚×2` và `3000枚`, đúng không?
- Đáp: Đúng. Ba sheet lần lượt là `Iris2020 A3 MFP用 500枚×2 PF`, `Iris2020 A3 MFP用 1500枚×2 PF`, và `Iris A3 MFP用 3000枚PF`. Nguồn file: PF全体配線図.xlsx

## CÂU HỎI 2547
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查询 03V4 与 03V5 的新 harness 品号。
- Cách hỏi: trực tiếp
- Hỏi: Change History 记录 03V4 和 03V5 分别把哪两个 harness 品号改成新号码？
- Đáp: 03V4：`303RB46050 → 303V446040`；03V5：`303RC46020 → 303V546020`。Nguồn file: PF全体配線図.xlsx

## CÂU HỎI 2548
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 03V4 の垂直搬送センサ用コネクタ変更を確認している。
- Cách hỏi: tình huống
- Hỏi: 変更履歴では垂直搬送センサ1/2のコネクタはどのように修正されていますか。
- Đáp: 03V4 ではセンサ1が `173977-3 → 353908-3`、センサ2が `173977-3 → 353293-3` に修正されています。Nguồn file: PF全体配線図.xlsx

# `302XC47100_03.pdf` — Q2549–2551

## CÂU HỎI 2549
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh các chân nguồn, địa chỉ và sensor trên YC1 của toner sensor board.
- Cách hỏi: so sánh
- Hỏi: Trên `YC1`, các nhãn `3.3V2`, `ADR0`, `ADR1` và `TH` nằm ở những pin nào đọc được?
- Đáp: Sơ đồ ghi pin `1=TH`, pin `3=3.3V2`, pin `4=ADR0`, pin `5=ADR1`; các pin còn lại tiếp tục nối tới các đường khác trên YC1. Nguồn file: 302XC47100_03.pdf

## CÂU HỎI 2550
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师检查 Toner Sensor 波形，但不想从单个元件值直接判断故障。
- Cách hỏi: xử lý sự cố
- Hỏi: 图中"波形調整"附近可读到哪些元件和值？
- Đáp: 可读到 `R2=330`，以及波形调整处 `R3=51`；旁边还有 `C1=1u`、`C8=0.01u`。这些数值本身不能单独证明某个元件故障。Nguồn file: 302XC47100_03.pdf

## CÂU HỎI 2551
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Toner Sensor 基板の識別情報を最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: この資料は `P.W.BOARD ASSY TONER SENSOR`、ASSY=`302XC47100`、Rev.=`03`、PWB=`7PA1178ASS+GH01` で合っていますか。
- Đáp: はい。その通りです。資料は全 `3` ページです。Nguồn file: 302XC47100_03.pdf
