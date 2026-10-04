# Mẻ 61 — Điều-tra-lỗi — Q2582–Q2611 (30 cặp)

- Ngày: 2026-10-04 ~23:46 +07
- Nguồn: 10 file trong `SƠ đồ điện/` của ZIP Điều tra lỗi (shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, phản hồi không bị cắt, không chạm giới hạn Plus
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Quy tắc Raw value: tuân thủ (Q2605/Q2610 giữ 未実装; Q2596 không suy đoán ASSY `30xxxxxxxx`; Q2585/Q2600/Q2610 không suy diễn nguyên nhân từ tín hiệu đơn lẻ)
- Điểm khác biệt vs mẻ trước: file IH PP 2016/2/5 Rev.=07 (mẻ 59/60 đã làm bản 20170116 Rev.=08 PWB khác); file 302XC47120-06.pdf title block ghi ASSY=302XC01120 khác tên filename — giữ đúng title block

---

## CÂU HỎI 2582
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận đúng DRUM board trước khi kiểm tra EEPROM.
- Cách hỏi: trực tiếp
- Hỏi: ASSY, Rev., PWB No. và ngày của board là gì?
- Đáp: ASSY=`3V2XC47080`, Rev.=`01`, PWB No.=`7PA1181ACZ+GH01`, ngày=`2019/9/19`. Nguồn file: 3V2XC47080-01.pdf

## CÂU HỎI 2583
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师沿 DRUM EEPROM 通信线路检查元件。
- Cách hỏi: tình huống
- Hỏi: EEPROM `U1` 的型号以及 SCL/SDA 侧串联电阻是什么？
- Đáp: `U1=S-24C02DI-T8T1U5`；SCL/SDA 周边可读到 `R1=33Ω`、`R2=33Ω`。Nguồn file: 3V2XC47080-01.pdf

## CÂU HỎI 2584
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: DRUM基板の初期版とPMT版の変更を比較している。
- Cách hỏi: so sánh
- Hỏi: Rev.1.0 と Rev.1.1 の主な変更内容は何ですか。
- Đáp: Rev.1.0（`2019/6/29`）はDMT用A版発行で、ESD保護ダイオードを高速タイプへ変更。Rev.1.1（`2019/9/19`）はPMT用で、`PWB1` を正規品目へ、`C1` をHW3品目へ置き換えています。Nguồn file: 3V2XC47080-01.pdf

## CÂU HỎI 2585
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: LED trên board không sáng và kỹ sư cần lần đúng tín hiệu nguồn/điều khiển.
- Cách hỏi: xử lý sự cố
- Hỏi: Trên YC1, hai đường được ghi rõ là gì?
- Đáp: Sơ đồ ghi `JS_LED_REM` và `+5V0V1_PANEL`. Đây chỉ là các đường kết nối trong sơ đồ; không thể từ một tín hiệu đơn lẻ kết luận linh kiện gây lỗi. Nguồn file: 302XC47210-01.pdf

## CÂU HỎI 2586
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师复核 LED 新设计的部件信息。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 图中 LED 是 `DL1=NESB157AT`，串联电阻 `R1=39Ω`，对吗？
- Đáp: 对。图中同时标记 R1 的尺寸为 `3216`。Nguồn file: 302XC47210-01.pdf

## CÂU HỎI 2587
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: LED基板の図面識別情報を確認している。
- Cách hỏi: trực tiếp
- Hỏi: ASSY、Rev.、PWB No. は何ですか。
- Đáp: ASSY=`302XC47210`、Rev.=`1.0`、PWB No.=`7PA1236ALE+AH01` です。図面日付は `2019/10/24` です。Nguồn file: 302XC47210-01.pdf

## CÂU HỎI 2588
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư mở file nhưng thấy mã trong title block khác tên filename.
- Cách hỏi: tình huống
- Hỏi: Title block thực tế ghi ASSY và PWB No. nào?
- Đáp: Title block ghi `PWB CCD ASSY`, ASSY=`302XC01120`, Rev.=`06`, PWB No.=`7PA1177CVP+GH01`. Không tự sửa ASSY thành tên filename `302XC47120`. Nguồn file: 302XC47120-06.pdf

## CÂU HỎI 2589
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 CCD 板的不同改版。
- Cách hỏi: so sánh
- Hỏi: Rev.05 与 Rev.06 的记录有什么区别？
- Đáp: Rev.05（`2019/9/19`）记录 MLCC HW3 对应以及 CCD sensor 更换为高速对应品；Rev.06（`2019/10/18`）记录 C版 TP 位置移动、`回路図変更なし`，以及 PMT 用 CCD sensor ES 品变更。Nguồn file: 302XC47120-06.pdf

## CÂU HỎI 2590
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 基板仕様値から故障状態を誤判定しないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: 基板サイズ `179×30.0mm`、厚さ `1.6mm`、6層という値だけで故障判定できますか。
- Đáp: できません。これらは基板仕様であり、故障判定値ではありません。部品実装は両面実装（両面リフロー）と記載されています。Nguồn file: 302XC47120-06.pdf

## CÂU HỎI 2591
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra lại thông số LCD trước khi thay module.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: LCD này là model `SVF101000ANN`, Rev.4, kích thước 10.1 inch và độ phân giải 1024(RGB)×600, đúng không?
- Đáp: Đúng. File còn ghi panel type=`TRANSMISSIVE`, display mode=`NORMALLY WHITE`, panel maker=`BOE`, backlight=`LED`. Nguồn file: LCD 302V845023.pdf

## CÂU HỎI 2592
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 LCD 主电源的正常规格范围。
- Cách hỏi: trực tiếp
- Hỏi: TFT-LCD MODULE 的 VDD 最小、典型、最大值分别是多少？
- Đáp: VDD=`3.0 / 3.3 / 3.6 V`。Nguồn file: LCD 302V845023.pdf

## CÂU HỎI 2593
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: LEDバックライトの電圧・電流条件を確認している。
- Cách hỏi: tình huống
- Hỏi: Back-Light Unit の forward voltage と forward current は何ですか。
- Đáp: Forward voltage は `8.4 / 9.6 / 10.2 V`（MIN/TYP/MAX）、forward current は TYP=`160mA`、MAX=`200mA` です。Nguồn file: LCD 302V845023.pdf

## CÂU HỎI 2594
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh đường cảm biến nhiệt belt với đường giao tiếp EEPROM.
- Cách hỏi: so sánh
- Hỏi: Sơ đồ có các nhãn nào cho cảm biến belt và giao tiếp EEPROM?
- Đáp: Phía cảm biến có `BELT_TH`; phía giao tiếp có `BELT_SDA` và `BELT_SCL`. Sơ đồ cũng có nguồn `+3.3V2` và `+24V2_F1`. Nguồn file: PA0893D_circuit.pdf

## CÂU HỎI 2595
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师追查 EEPROM 通信异常，但不想凭单个器件直接判定原因。
- Cách hỏi: xử lý sự cố
- Hỏi: EEPROM U1 的型号是什么，SCL/SDA 周边可见什么电阻？
- Đáp: `U1=S-24C02DI-J8T1U5`；SCL/SDA 周边可见 `R3=33Ω`、`R4=33Ω`。这些连接信息本身不能证明某个单独器件已经故障。Nguồn file: PA0893D_circuit.pdf

## CÂU HỎI 2596
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: TRANSFER基板の資料識別情報を再確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 図面は `P.W.BOARD ASSY TRANSFER`、PWB No.=`7PA0893DCZ+AH01`、日付=`2015/04/20` で合っていますか。
- Đáp: はい。その記載を確認できます。ASSY欄はこのPDFの抽出では `30xxxxxxxx` と表示されるため、ここでは推測して補完しません。Nguồn file: PA0893D_circuit.pdf

## CÂU HỎI 2597
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần xác nhận đúng IH100 PP trước khi so với bản 2016/11.
- Cách hỏi: trực tiếp
- Hỏi: File ghi ASSY, Rev. và PWB No. nào?
- Đáp: `PWB IH 100 ASSY`, ASSY=`302ND47250`, Rev.=`07`, PWB No.=`7PA0859EHT+AH01`, ngày=`2016/2/5`. Nguồn file: Iris 2ND IH PP 01 302ND47250 20160205.pdf

## CÂU HỎI 2598
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看 IH100 Rev.4.0 的改版记录。
- Cách hỏi: tình huống
- Hỏi: `2016/2/5` 的 Rev.4.0 做了什么修改？
- Đáp: 记录为 `生板版数UP`，并把 `YC5` 从旧 code 替换为 `7 code`。Nguồn file: Iris 2ND IH PP 01 302ND47250 20160205.pdf

## CÂU HỎI 2599
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: IH100 のRev.3.2と4.0を比較している。
- Cách hỏi: so sánh
- Hỏi: Rev.3.2 と Rev.4.0 の変更内容はどう違いますか。
- Đáp: Rev.3.2（`2015/10/26`）は `JP1、C9、C10削除`。Rev.4.0（`2016/2/5`）は生板版数UPとYC5のコード置き換えです。Nguồn file: Iris 2ND IH PP 01 302ND47250 20160205.pdf

## CÂU HỎI 2600
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra IH200 và tránh suy diễn lỗi chỉ từ khác biệt board number.
- Cách hỏi: xử lý sự cố
- Hỏi: Board này khác IH100 ở mã nào, và có thể từ khác biệt đó kết luận nguyên nhân lỗi không?
- Đáp: Đây là `PWB IH 200 ASSY`, ASSY=`302ND47260`, PWB=`7PA0860DHT+AH01`, Rev.=`07`. Chỉ từ mã board khác IH100 không thể kết luận nguyên nhân lỗi. Nguồn file: Iris 2ND IH PP 01 302ND47260 20160205.pdf

## CÂU HỎI 2601
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师复核 IH200 的电源配置。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Power Table 包含 `+3.3V`、`+15V1`、`+24V2`、`+3.3V2`，对吗？
- Đáp: 对。Ground 栏还列有 `SGND1/FGND1/PGND1/FGND2/SGND2/PGND2/FGND3`。Nguồn file: Iris 2ND IH PP 01 302ND47260 20160205.pdf

## CÂU HỎI 2602
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: IH200 のPMT版変更日を確認している。
- Cách hỏi: trực tiếp
- Hỏi: Rev.3.0 の日付と内容は何ですか。
- Đáp: Rev.3.0 は `2015/4/2`、内容は `PMT用回路に変更` です。Nguồn file: Iris 2ND IH PP 01 302ND47260 20160205.pdf

## CÂU HỎI 2603
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư điều tra FRONT DRIVE MONO và cần chọn đúng trang chức năng.
- Cách hỏi: tình huống
- Hỏi: Tài liệu chia các mạch chính thành những trang nào?
- Đáp: Ngoài INDEX/CHANGE HISTORY, file có `HERCULES`, `PWB IMAGE DRIVE I/F`, `PWB DRUM DLP CONNECT I/F`, `PWB FUSER HVU_IH CORE`, `EXIT1`, `EXIT2`, `FAN`, `CONTAINER SOLENOID`, `DEMITAS`; tổng cộng `11` trang. Nguồn file: 3V2XF47050-06.pdf

## CÂU HỎI 2604
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 Rev.3.1 与 Rev.3.2 的定数变更。
- Cách hỏi: so sánh
- Hỏi: Rev.3.1 与 Rev.3.2 分别修改了哪些电阻和电容？
- Đáp: Rev.3.1（`2020/1/8`）将 `R83→330kΩ`，`C83/C84/C85/C86→1500pF`，并记录 `R77/R78/R79 未实装`；Rev.3.2（`2020/2/3`）将 `R84→330kΩ`、`C95/C96/C97/C98→1500pF`。Nguồn file: 3V2XF47050-06.pdf

## CÂU HỎI 2605
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 未実装部品をデータ化している。
- Cách hỏi: xử lý sự cố
- Hỏi: Rev.3.1で `R77/R78/R79：未実装` とある場合、OK/NGとして扱いますか。
- Đáp: いいえ。ソースの記載どおり「未実装」と保持し、OK/NGや故障状態を自動付与しません。Nguồn file: 3V2XF47050-06.pdf

## CÂU HỎI 2606
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận đây đúng là CURRENT AVE 100 board trước khi đo.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Board là `PWB CURRENT AVE 100 ASSY`, ASSY=`302N401190`, Rev.=`01`, đúng không?
- Đáp: Đúng. PWB No.=`7PA0727ASS+AH01`, ngày title block=`2012/08/08`. Nguồn file: ALPHARD2_2N4_CURRENTAVE_PP_01_最新回路図_302N401190.pdf

## CÂU HỎI 2607
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认 CURRENT AVE 电路中的主要 IC。
- Cách hỏi: trực tiếp
- Hỏi: 图中 `U2` 和 `U4` 的型号分别是什么？
- Đáp: `U2=LTC1966CMS8TRPBF_01`，`U4=TPS60400DBVR`。Nguồn file: ALPHARD2_2N4_CURRENTAVE_PP_01_最新回路図_302N401190.pdf

## CÂU HỎI 2608
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: CURRENT MONI 出力側を確認している。
- Cách hỏi: tình huống
- Hỏi: YC1 のどのピンに `CURRENT MONI` が記載されていますか。
- Đáp: `YC1` の pin `3` に `CURRENT MONI` と記載されています。コネクタ型番は `292207-3` です。Nguồn file: ALPHARD2_2N4_CURRENTAVE_PP_01_最新回路図_302N401190.pdf

## CÂU HỎI 2609
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư phân biệt board màu a-Si với bản Mono đã kiểm tra trước đó.
- Cách hỏi: so sánh
- Hỏi: File này ghi board/ASSY/PWB như thế nào?
- Đáp: File ghi `P.W.BOARD ASSY DRUM/DLP CONNECT (a-Si)`, ASSY=`302XC47060`, Rev.=`03`, PWB=`7PA1179BCZ+GH01`. Đây là thông tin của đúng file hiện tại, không dùng mã của bản Mono trước đó. Nguồn file: 302XC47060-03.pdf

## CÂU HỎI 2610
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师按照 DMT 变更记录检查装配/未装配部件。
- Cách hỏi: xử lý sự cố
- Hỏi: `2019/7/1` 的记录中哪些部件是实装、未实装和新增？
- Đáp: 文件记录 `R53` 实装；`R20、QD1、QD2` 未实装；新增 `R54、R55、R56、TP36、TP37`。未实装只按原始记录保存，不自行判为 NG。Nguồn file: 302XC47060-03.pdf

## CÂU HỎI 2611
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: PMT BOM版への変更内容を最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Rev.2.1 は `2019/9/13` の Iris2020 PMT BOM用で、MLCCをHW3へ置き換えた記録ですね。
- Đáp: はい。その記録があります。Rev.2.0 は `2019/6/24` のDMT用です。Nguồn file: 302XC47060-03.pdf
