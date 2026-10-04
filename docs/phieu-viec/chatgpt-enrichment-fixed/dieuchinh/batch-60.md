# Mẻ 60 — Điều-tra-lỗi — Q2552–Q2581 (30 cặp)

- Ngày: 2026-10-04 ~23:34 +07
- Nguồn: 10 file trong `SƠ đồ điện/` của ZIP Điều tra lỗi (shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không cloudflare_challenge, phản hồi không bị cắt, không chạm giới hạn Plus
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Quy tắc Raw value: tuân thủ (Q2560, Q2565 giữ OPEN; Q2568 giữ 未実装; Q2574/Q2580 không suy diễn nguyên nhân)

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 2552
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần xác nhận đúng revision Human Detect PP trước khi tra mạch.
- Cách hỏi: trực tiếp
- Hỏi: ASSY No., Rev., PWB No. và ngày của bản Human Detect PP này là gì?
- Đáp: ASSY No.=302V847060, Rev.=06, PWB No.=7PA1111BSS+GH01, ngày=2018/10/15. Nguồn file: IRIS2_2V8_HUMAN DETECT_PP_01基板回路図.pdf

## CÂU HỎI 2553
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师检查 PLM 联动后 U1-3 的连接修正记录。
- Cách hỏi: tình huống
- Hỏi: Rev.1.7 对 U1-3 做了什么修正，日期是什么？
- Đáp: Rev.1.7 日期为 2018/6/22，记录为 U1-3 9pin-10pin入れ替え。说明中写明在 PLM 联动时连接有误，因此进行了修正。Nguồn file: IRIS2_2V8_HUMAN DETECT_PP_01基板回路図.pdf

## CÂU HỎI 2554
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 以前の Human Detect 回路図と PP版を取り違えないよう比較している。
- Cách hỏi: so sánh
- Hỏi: 旧版 7PA1111B_回路図_180423.pdf と今回のPP版で、ASSY/Rev/日付はどう変わっていますか。
- Đáp: 旧版は ASSY=T02V801060、Rev.=01、日付=2018/4/23。今回のPP版は ASSY=302V847060、Rev.=06、日付=2018/10/15 です。PWB No. は両方 7PA1111BSS+GH01 です。Nguồn file: IRIS2_2V8_HUMAN DETECT_PP_01基板回路図.pdf

## CÂU HỎI 2555
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang lần đường FSR_TH_PRESS giữa hai connector của FUSER board.
- Cách hỏi: xử lý sự cố
- Hỏi: FSR_TH_PRESS xuất hiện ở pin nào của YC1 và YC2?
- Đáp: Trên YC1, FSR_TH_PRESS nằm ở pin 5; trên YC2, tín hiệu cùng tên nằm ở pin 12. Đây chỉ là quan hệ wiring trong sơ đồ, không tự suy ra linh kiện gây lỗi. Nguồn file: Iris_FUSER_PP_01基板回路図.pdf

## CÂU HỎI 2556
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师复核 PMT 用 Rev.2.0 的部件变更。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Rev.2.0 在 2015/8/25 把 DZ1 改为 DF5A6.8LF，并把 R3、R4 从 15K 改为 3.3K，对吗？
- Đáp: 对。Change History 正是这样记录的。Nguồn file: Iris_FUSER_PP_01基板回路図.pdf

## CÂU HỎI 2557
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: FUSER基板の資料識別情報を確認している。
- Cách hỏi: trực tiếp
- Hỏi: この基板の ASSY No.、Rev.、PWB No. は何ですか。
- Đáp: ASSY No.=302ND01150、Rev.=04、PWB No.=7PA0847CCZ+RH01 です。Nguồn file: Iris_FUSER_PP_01基板回路図.pdf

## CÂU HỎI 2558
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư nhận một bản Ver2.0 và cần phân biệt với Ver2.1 đã lưu trước đó.
- Cách hỏi: tình huống
- Hỏi: Bản Ver2.0 ghi Model, Drawing No. và ngày nào?
- Đáp: Model=MDKZZQ101, Drawing No.=151-MDKZZQ101-C01, ngày=2019.07.03. Nguồn file: Iris2020High_302XC45010_縦基板_Ver2.0.pdf

## CÂU HỎI 2559
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 Ver2.0 与之前处理的 Ver2.1。
- Cách hỏi: so sánh
- Hỏi: 两个版本在可读的 Model、Drawing No. 和图纸日期上有什么差异？
- Đáp: 两者的 Model 都是 MDKZZQ101，Drawing No. 都是 151-MDKZZQ101-C01；Ver2.0 日期为 2019.07.03，Ver2.1 为 2019.08.29。Nguồn file: Iris2020High_302XC45010_縦基板_Ver2.0.pdf

## CÂU HỎI 2560
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Ver2.0 の未実装表記を学習データに取り込んでいる。
- Cách hỏi: xử lý sự cố
- Hỏi: C706、C503、C707、D502、D702 に OPEN とある場合、どう扱いますか。
- Đáp: すべて Raw value OPEN として保持します。OPEN を自動的に故障、0、OK/NGなどへ変換しません。Nguồn file: Iris2020High_302XC45010_縦基板_Ver2.0.pdf

## CÂU HỎI 2561
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận cấu trúc RX board trước khi đo nguồn.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File có 4 trang gồm INDEX, CHANGE_HISTORY, CPU và AMP; ASSY là T03TD47010, đúng không?
- Đáp: Đúng. Rev.=T_01, PWB No.=7PA1207ASS+GH01, ngày=2019/6/25. Nguồn file: RX ASSY_303TD01010.pdf

## CÂU HỎI 2562
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接核对 RX 板 Power Table。
- Cách hỏi: trực tiếp
- Hỏi: Power Table 中列出的电源有哪些？
- Đáp: +24V、+3.3V1 (DDC)、+4.2V (DDC)、+3.3V_CIS (LDO)、+3.3V_AFE (LDO)、+1.8V_VBO (LDO)、+1.8V_AFE (LDO)、+1.2V (LDO)。Nguồn file: RX ASSY_303TD01010.pdf

## CÂU HỎI 2563
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: RX基板のYC1で通信線とパルス線を確認している。
- Cách hỏi: tình huống
- Hỏi: YC1 では SCL、SDA、TX_PULSE は何番ピンに記載されていますか。
- Đáp: SCL=10、SDA=8、TX_PULSE=1 と記載されています。Nguồn file: RX ASSY_303TD01010.pdf

## CÂU HỎI 2564
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư phân biệt các đường điều khiển DC của màu/mạch trên sơ đồ Low.
- Cách hỏi: so sánh
- Hỏi: Các nhãn BK MAGDC CNT, BM MAGDC CNT, BC MAGDC CNT, BY MAGDC CNT đi kèm số nào?
- Đáp: BK MAGDC CNT14, BM MAGDC CNT12, BC MAGDC CNT9, BY MAGDC CNT2. Đây là nhãn/số xuất hiện trên sơ đồ, không tự diễn giải thành trạng thái. Nguồn file: Iris2020Low_302L745040.pdf

## CÂU HỎI 2565
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师在图纸上看到未使用/开放位置，需要规范录入。
- Cách hỏi: xử lý sự cố
- Hỏi: 图中出现 OPEN 时能否自动解释成故障或数值0？
- Đáp: 不能。必须保留为 Raw value OPEN；文件没有定义它等于故障、0、OK 或 NG。Nguồn file: Iris2020Low_302L745040.pdf

## CÂU HỎI 2566
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Low側回路図の識別情報を再確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: この資料の Model は EUK9MQC68HA、Drawing No. は 111-EUK9MQC68HA-C01 で合っていますか。
- Đáp: はい。その通りです。資料は全 3 ページです。Nguồn file: Iris2020Low_302L745040.pdf

## CÂU HỎI 2567
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần xác nhận đúng DP Driver bản dành cho cơ cấu đảo trước khi điều tra.
- Cách hỏi: trực tiếp
- Hỏi: ASSY, Rev. và PWB No. của PWB DRIVE DP.pdf là gì?
- Đáp: ASSY=303V347020, Rev.=01, PWB No.=7PA1240CCZ+GH01; tài liệu ghi メカ反転上位用 DP DRIVER基板 và có 11 trang. Nguồn file: PWB DRIVE DP.pdf

## CÂU HỎI 2568
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师检查初版中机种判别用 pull-up 的配置。
- Cách hỏi: tình huống
- Hỏi: Change History 对 R600 和 R601 是怎样记录的？
- Đáp: 文件记录为"增加机种判别用 pull-up：R600、R601"，并明确注明 R601は未実装。因此 R601 应按源文件的"未実装"记录，不自行赋予故障含义。Nguồn file: PWB DRIVE DP.pdf

## CÂU HỎI 2569
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: DP Driver の電源分類を比較している。
- Cách hỏi: so sánh
- Hỏi: 入力電源、インターロック後、Sleep/内部生成の電源はそれぞれどう表記されていますか。
- Đáp: 入力は +24V、インターロック後は +R24V、Sleep電源は +3.3V3、DCDC生成は +3.3V と記載されています。Nguồn file: PWB DRIVE DP.pdf

## CÂU HỎI 2570
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tra wiring tổng thể nhưng cần tránh suy ra lỗi từ một đường dây đơn lẻ.
- Cách hỏi: xử lý sự cố
- Hỏi: Cover của file chia wiring thành những nhóm chính nào để chọn đúng trang điều tra?
- Đáp: Cover chia thành HVU, LSU, IMAGE1, 4 IMAGE・FRONT, FEED1, FEED2, DRUM・DLP, FUSER, LVU, PANEL, ISU, AK・DF, OPTION. Cần dùng đúng nhóm để lần wiring; danh sách này không tự xác định nguyên nhân lỗi. Nguồn file: 全体配線図_上位_DMT.pdf

## CÂU HỎI 2571
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认封面的机型映射，避免把 Color 与 Mono 混用。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: COLOR 70/70 对应 02XC，而 MONO 70 对应 02XF，对吗？
- Đáp: 对。Cover 中还列出 COLOR 60/60=02YL、50/50=02YM、40/40=02YN，MONO 60=02YR、50=02YS、40=02YT。Nguồn file: 全体配線図_上位_DMT.pdf

## CÂU HỎI 2572
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 全体配線図のページ構成を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: PDFは何ページあり、配線グループは何番までありますか。
- Đáp: PDFは 18 ページです。表紙では ALL WIRING DIAGRAM [1/13] から [13/13] までの13グループが列挙されています。Nguồn file: 全体配線図_上位_DMT.pdf

## CÂU HỎI 2573
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang dùng IH100 và cần tránh nhầm với IH200 đã kiểm tra trước đó.
- Cách hỏi: tình huống
- Hỏi: Bản 302ND47250 là board gì và có các trang chức năng nào?
- Đáp: Đây là PWB IH 100 ASSY, gồm MAIN AC, IGBT DRIVER, EngineI/F_CPUI/F_Power 3.3V 15V1 và JUMPER, ngoài INDEX/CHANGE HISTORY. Nguồn file: Iris_2ND_IH_MP_01基板回路図_302ND47250_20170116.pdf

## CÂU HỎI 2574
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 302ND47250 与之前的 302ND47260，避免混用板号。
- Cách hỏi: so sánh
- Hỏi: 两份 IH 文件的 ASSY/PWB 和板类型有什么区别？
- Đáp: 302ND47250 是 PWB IH 100 ASSY、PWB=7PA0859FHT+AH01；之前的 302ND47260 是 PWB IH 200 ASSY、PWB=7PA0860EHT+AH01。两者都是6页，但板型不同。Nguồn file: Iris_2ND_IH_MP_01基板回路図_302ND47250_20170116.pdf

## CÂU HỎI 2575
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: IH100 のインターフェース信号を確認しているが、単独信号から故障原因を決めないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: Engine/CPU I/F 部で確認できる代表的な信号・電源には何がありますか。
- Đáp: 資料上では 3.3V、15V1 の電源系と、Engine/CPU I/F 関連信号が記載されています。ただし、特定の1信号だけで故障部品を断定する条件はこの回路図にはありません。Nguồn file: Iris_2ND_IH_MP_01基板回路図_302ND47250_20170116.pdf

## CÂU HỎI 2576
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận workbook nguồn có đúng các sheet của wiring tổng thể hay không.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Workbook có 17 sheet và có riêng ba sheet LVU là 9 LVU 1コンver, 9 LVU カレントver, 9 LVU 2コンver, đúng không?
- Đáp: Đúng. Workbook có tổng cộng 17 sheet; ba sheet LVU đúng là 9 LVU 1コンver, 9 LVU カレントver, 9 LVU 2コンver. Nguồn file: 全体配線図_上位_DMT.xlsx

## CÂU HỎI 2577
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接查看 2019/9/3 的 FEED1 变更记录。
- Cách hỏi: trực tiếp
- Hỏi: Change History 中 FEED1 的两个 harness 品号是怎样修改的？
- Đáp: 302ND46280-01 → 302XC46280-01，以及 302ND46290-01 → 302XC46290-01；同一记录还写有 302XC46290-01 的排出冷却 FAN pin 排列变更。Nguồn file: 全体配線図_上位_DMT.xlsx

## CÂU HỎI 2578
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: PDF版と同じ一般構成ではなく、Excelの変更履歴から具体的な改訂内容を確認している。
- Cách hỏi: tình huống
- Hỏi: 2019/10/12 の 3 IMAGE ではコストダウン目的でどのハーネス品番が変更されていますか。
- Đáp: 302ND46260 → 302XC46450、302ND46300 → 302XC46460 に変更されています。Nguồn file: 全体配線図_上位_DMT.xlsx

## CÂU HỎI 2579
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh IH100 Iris2020 với board Iris 302ND47250 làm nền.
- Cách hỏi: so sánh
- Hỏi: File 302XC47220-04 ghi rõ quan hệ với 302ND47250 như thế nào, và board mới có mã gì?
- Đáp: Change History ghi Iris 302ND47250をベースにIris2020新規. Board mới là PWB IH 100 ASSY, ASSY=302XC47220, Rev.=04, PWB=7PA0859FHT+AH01. Nguồn file: 302XC47220-04.pdf

## CÂU HỎI 2580
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师根据 Rev.3.0 记录排查电阻版本差异。
- Cách hỏi: xử lý sự cố
- Hỏi: Rev.3.0 对 R12 做了什么变更？能否仅凭这个变更认定某个故障原因？
- Đáp: Rev.3.0（2020/2/26）记录 R12 47Ω → 2.2kΩ。这只是设计变更记录，不能仅凭该数值变化认定某个实际故障原因。Nguồn file: 302XC47220-04.pdf

## CÂU HỎI 2581
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 最新Rev.の変更理由を再確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Rev.4.0 は 2020/6/4 で、フェライトコアの2NDソース 7YBC35353301H01 を追加した記録ですね。
- Đáp: はい。さらに「フェライトコアは回路図上には無いが、Rev.Up理由を履歴に残す」と明記されています。Nguồn file: 302XC47220-04.pdf
