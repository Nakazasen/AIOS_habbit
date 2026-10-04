# Mẻ 65 — Điều-tra-lỗi — Q2702–Q2731 (30 cặp)

- Ngày: 2026-10-05 ~00:30 +07
- Nguồn: 6 file `SƠ đồ điện/` cuối cùng + 4 file `Lịch sử lỗi/` đầu tiên (shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược=6 (mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ (未採番, Not Mount/未実装 giữ nguyên; phần mojibake không phục dựng; không suy diễn nguyên nhân từ revision đơn lẻ; không nâng thông tin lịch sử thành nguyên nhân case hiện tại)
- **SƠ đồ điện/ XONG 100%** — 84/84 file đã xử lý
- Case KTD-2026-08-0872 (C4001): PDF và XLSX đối chiếu như cùng case, Reappear rate=100%, không thêm nguyên nhân/đối sách ngoài file
- Case C6950: kết luận Q3不良 theo đúng file (bảng đo Q3 cụ thể), không suy luận thêm
- Case hình ảnh bất thường: không nâng "lỗi trước đây do tĩnh điện" thành nguyên nhân case hiện tại

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 2702
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tra lại thay đổi IMAGE2 của bản wiring lower từ chính PDF.
- Cách hỏi: trực tiếp
- Hỏi: Ngày 2019/07/12, harness của motor trung chuyển CL được đổi từ mã nào sang mã nào?
- Đáp: Ngày `2019/07/12`, mục `4 IMAGE2` ghi harness được sửa từ `302ND46550-04 → 302XC46380-01`; đồng thời motor trung chuyển CL được đổi sang linh kiện mới nhưng ghi `未採番` — chưa có mã. Nguồn file: 全体配線図_下位_DMT機.pdf

## CÂU HỎI 2703
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看后续版本，确认IMAGE2的临时变更是否又被恢复。
- Cách hỏi: tình huống
- Hỏi: `2019/07/25` 的 IMAGE2 记录如何处理此前的中转CL马达和线束？
- Đáp: 文件记录中转CL马达改回旧品 `302ND44060`，线束从 `302XC46380-01 → 302ND46550-04`。这是文件中的版本变更记录，不能据此自行判断某一版本为NG。 Nguồn file: 全体配線図_下位_DMT機.pdf

## CÂU HỎI 2704
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: IMAGE2の7月12日版と7月25日版を比較している。
- Cách hỏi: so sánh
- Hỏi: 2019/07/12 と 2019/07/25 でハーネス品番はどう変化していますか。
- Đáp: `2019/07/12` は `302ND46550-04 → 302XC46380-01`、`2019/07/25` は逆に `302XC46380-01 → 302ND46550-04` と記載されています。 Nguồn file: 全体配線図_下位_DMT機.pdf

## CÂU HỎI 2705
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra một thay đổi mã quạt làm mát container trên wiring mono.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi sửa mã quạt làm mát container như thế nào, và có thể coi mã cũ là linh kiện lỗi không?
- Đáp: Ngày `2019/05/27`, file ghi mã quạt làm mát container bị ghi sai và sửa `302K944510 → 302K944520`. Đây là sửa mã trong tài liệu; không được tự kết luận `302K944510` là linh kiện NG. Nguồn file: 全体配線図_モノクロ_DMT機 MONO.pdf

## CÂU HỎI 2706
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师复核ENGINE的YC6连接器名称变更。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `2019/05/29` 是把 ENGINE YC6 从 `B11B-CZWHK-B-1` 修正为 `B11B-CZBKK-B-1(LF)(SN)`，对吗？
- Đáp: 对。文件明确说明这是 YC6 连接器名称记载错误的修正。 Nguồn file: 全体配線図_モノクロ_DMT機 MONO.pdf

## CÂU HỎI 2707
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: モノクロ配線図のIMAGEハーネス変更を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 2019/10/12 のIMAGEでは、ハーネス品番は何から何へ変更されていますか。
- Đáp: コストダウン目的の新規品への変更として、`302ND46260 → 302XC46450` と記載されています。 Nguồn file: 全体配線図_モノクロ_DMT機 MONO.pdf

## CÂU HỎI 2708
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đối chiếu specification nguồn 24V thay vì chỉ xem trang mạch đơn lẻ.
- Cách hỏi: tình huống
- Hỏi: Trong revision của specification, giá trị peak current phía 24V được ghi sửa thành bao nhiêu?
- Đáp: Phần revision đọc được ghi `24V: Peak current*1.2 (Amin) → 17Amin`. Đây là giá trị specification trong tài liệu, không phải một kết quả đo lỗi cụ thể. Nguồn file: 302XD45010-full.pdf

## CÂU HỎI 2709
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较5V与24V的峰值电流修订值。
- Cách hỏi: so sánh
- Hỏi: 文件修订记录中的5V和24V peak current分别是多少？
- Đáp: 5V 侧记录为 `Peak current*1.1 → 14Amin`；24V 侧记录为 `Peak current*1.2 → 17Amin`。 Nguồn file: 302XD45010-full.pdf

## CÂU HỎI 2710
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 入力電圧の改訂記録を不具合実測値と混同しないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: 仕様書にある `275V → 276V` の修正だけで電源不良と判断できますか。
- Đáp: できません。ソースでは `2.2項 突入電流の入力電圧誤記訂正` として `275V → 276V` が記載されています。これは仕様書の誤記訂正であり、単独の不具合測定結果ではありません。 Nguồn file: 302XD45010-full.pdf

## CÂU HỎI 2711
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Filename và mã trong title block không hoàn toàn giống nhau nên kỹ sư kiểm tra lại trước khi dùng.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Dù filename là `IMAGE_V2XC47040-02.pdf`, title block thực tế ghi ASSY=`3V2XC47040`, PWB=`7PA1171CCZ+GH01`, Rev.=`02`, đúng không?
- Đáp: Đúng. Title block ghi `PWB IMAGE DRIVE ASSY`, ASSY=`3V2XC47040`, Model=`2XC`, PWB=`7PA1171CCZ+GH01`, Rev.=`02`, ngày=`2019/11/3`; file có `18` trang. Nguồn file: IMAGE_V2XC47040-02.pdf

## CÂU HỎI 2712
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认PMT用C版发行时的主要电源变更。
- Cách hỏi: trực tiếp
- Hỏi: Rev.2.0 在 `2019/9/5` 记录了哪些主要变更？
- Đáp: 记录包括 `PWB1 PA1171B→PA1171C`、POWER TABLE 增加 `24V4_F2`、在 drum motor 电源线上增加 fuse `YF12`，以及因电源平面变更删除 `C207/C208`。 Nguồn file: IMAGE_V2XC47040-02.pdf

## CÂU HỎI 2713
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 回路図アップロード時の品番変更を確認している。
- Cách hỏi: tình huống
- Hỏi: 2019/11/3 の記録では品番をどのように修正していますか。
- Đáp: `回路図アップロードのため品番修正` として、`TV2XC01040 → 3V2XC47040` と記載されています。 Nguồn file: IMAGE_V2XC47040-02.pdf

## CÂU HỎI 2714
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh các revision đọc được rõ trong specification High Voltage Unit.
- Cách hỏi: so sánh
- Hỏi: R0 và R1 của tài liệu được ghi với ngày nào?
- Đáp: Phần revision đọc được ghi `R0` ngày `2015/7/15` và `R1` ngày `2018/10/3`. Các phần chữ bị mojibake khác không được suy đoán bổ sung. Nguồn file: 302L745040.pdf

## CÂU HỎI 2715
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师看到外形图的孔径修改记录，需要避免把设计修改误认为故障。
- Cách hỏi: xử lý sự cố
- Hỏi: 文件中"增加φ18mm孔"的记录可以直接解释为原产品故障吗？
- Đáp: 不可以。可读内容记录的是 `概要図変更（φ18mmの穴追加）`，属于图纸/结构修订；文件没有据此给出单件产品NG结论。 Nguồn file: 302L745040.pdf

## CÂU HỎI 2716
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 文字化け部分を補完せず、読める製品識別だけ確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 読み取れる製品名は `High Voltage Unit EUK9MQC68HA` ですね。
- Đáp: はい。ソース上で `High Voltage Unit EUK9MQC68HA` を確認できます。判読できない周辺文字は推測して補完しません。 Nguồn file: 302L745040.pdf

## CÂU HỎI 2717
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra revision liên quan đến mã khách hàng của unit.
- Cách hỏi: trực tiếp
- Hỏi: Customer part number được sửa từ mã nào sang mã nào?
- Đáp: Revision đọc được ghi `302XC45030 → 302XC45030-02`. Nguồn file: 302XC45030 full.pdf

## CÂU HỎI 2718
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认C004在规格修订中的容量变化。
- Cách hỏi: tình huống
- Hỏi: C004 的修订值从多少变成多少？
- Đáp: 文件记录 `C004: 0.1uF → 0.22uF`。这是文件明确记载的设计变更值。 Nguồn file: 302XC45030 full.pdf

## CÂU HỎI 2719
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: R118/R518の抵抗公差表記を新旧で比較している。
- Cách hỏi: so sánh
- Hỏi: R118、R518 の公差はどのように訂正されていますか。
- Đáp: `1%（F）→ 5%（J）` と訂正されています。 Nguồn file: 302XC45030 full.pdf

## CÂU HỎI 2720
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Line C33-A1 phát sinh C4001 khi thử in và kỹ sư tra đúng kết quả điều tra trong báo cáo.
- Cách hỏi: xử lý sự cố
- Hỏi: Hiện tượng C4001 của case KTD-2026-08-0872 được ghi thế nào và kết quả điều tra là gì?
- Đáp: Hiện tượng được ghi `in tờ White thử 1 => LCD báo C4001`; mục Investigation ghi `pin1-YC3 hàn giả`. Chỉ phản ánh đúng kết luận trong file, không bổ sung cơ chế hỏng ngoài báo cáo. Nguồn file: KTD-2026-08-0872-Iris2024-C33-A1-C4001.xlsx

## CÂU HỎI 2721
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师复核该C4001案例的发生条件。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 该案例发生在 `C33-A1`，数量 `1`，发生日 `2026-08-18`，对吗？
- Đáp: 对。报告记录 Line=`C33-A1`、Quantity=`1`、Occurrence Date=`2026-08-18`。 Nguồn file: KTD-2026-08-0872-Iris2024-C33-A1-C4001.xlsx

## CÂU HỎI 2722
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 調査結果と対策を混同しないよう、報告書の記載範囲を確認している。
- Cách hỏi: trực tiếp
- Hỏi: このXLSXには独立した対策内容が記載されていますか。
- Đáp: 独立した対策欄・対策内容は確認できません。記載されている調査結果は `pin1-YC3 hàn giả` です。対策を推測して追加しません。 Nguồn file: KTD-2026-08-0872-Iris2024-C33-A1-C4001.xlsx

## CÂU HỎI 2723
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư mở bản PDF của cùng case để đối chiếu cách hiển thị tỷ lệ tái hiện.
- Cách hỏi: tình huống
- Hỏi: Bản PDF hiển thị Reappear rate của case C4001 là bao nhiêu?
- Đáp: PDF hiển thị `Reappear rate = 100%`. Nguồn file: KTD-2026-08-0872-Iris2024-C33-A1-C4001.pdf

## CÂU HỎI 2724
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较同一KTD案例的XLSX与PDF表示。
- Cách hỏi: so sánh
- Hỏi: XLSX与PDF中的核心案例内容是否一致，Reappear rate的表现有什么不同？
- Đáp: 核心内容一致：都是 Iris2024、C33-A1、PWB APC ASSY、试印White时LCD显示 `C4001`、调查结果 `pin1-YC3 hàn giả`。XLSX提取出的底层数值为 `1`，PDF显示为 `100%`。 Nguồn file: KTD-2026-08-0872-Iris2024-C33-A1-C4001.pdf; KTD-2026-08-0872-Iris2024-C33-A1-C4001.xlsx

## CÂU HỎI 2725
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: PDF側にXLSXより詳しい故障原因・対策が追加されていないか確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: PDFから `pin1-YC3 hàn giả` 以上の原因や対策を追加してよいですか。
- Đáp: いいえ。PDFでも調査結果は `pin1-YC3 hàn giả` までです。別の根本原因や対策は記載されていないため追加しません。 Nguồn file: KTD-2026-08-0872-Iris2024-C33-A1-C4001.pdf

## CÂU HỎI 2726
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận lại case C6950 trước khi xem bảng đo Q3.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Báo cáo ghi bật máy xuất hiện `C6950`, linh kiện điều tra là Q3 và sau khi thay Q3 thì OK, đúng không?
- Đáp: Đúng. File ghi `cực E-C Q3 giá trị điện trở bất thường`, `Thay linh kiện Q3 -> OK`, `Lỗi do Q3`; phần tiếng Nhật cũng ghi `Q3のE-C間の抵抗値が異常`, `Q3部品交換 → OK`, `Q3不良`. Nguồn file: KTD-2026-05-0428-Iris2024-C35-A1-C6950.xlsx

## CÂU HỎI 2727
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接查看Q3测量表中的OK/NG数据。
- Cách hỏi: trực tiếp
- Hỏi: Q3的diode和E-C电阻测量中，OK与NG分别记录什么值？
- Đáp: Diode：`pin E-C` 为 OK=`OL`、NG=`OL`；反向 `C-E` 为 OK=`1.3V`、NG=`OL`。电阻：`E-C` 为 OK=`6MΩ`、NG=`491kΩ`。这些OK/NG标签是源文件本身定义的。 Nguồn file: KTD-2026-05-0428-Iris2024-C35-A1-C6950.xlsx

## CÂU HỎI 2728
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C6950発生品の処置と確認結果を報告書どおり説明する必要がある。
- Cách hỏi: tình huống
- Hỏi: Q3交換後の結果と、報告書が記載している原因判定は何ですか。
- Đáp: 報告書には `Q3部品交換 → OK`、`Q3不良` と記載されています。これはソースが明示した判定であり、ここからさらに別の原因を推測しません。 Nguồn file: KTD-2026-05-0428-Iris2024-C35-A1-C6950.xlsx

## CÂU HỎI 2729
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư phân biệt hiện tượng nhìn thấy trên bản in với kết quả kiểm tra tín hiệu.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng sản phẩm và kết quả điều tra tín hiệu trong case này khác nhau thế nào?
- Đáp: Hiện tượng được ghi `Hình ảnh nhạt, loang, bẩn mép (màu K)`; phần điều tra ghi `Tín hiệu T1(K) bất thường`. Hai nội dung này là hiện tượng và kết quả điều tra riêng biệt trong cùng báo cáo. Nguồn file: KTD-2026-06-0526-Iris2024-C35-A8.4-Hình ảnh bất thường.xlsx

## CÂU HỎI 2730
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师看到报告提到以前曾发生静电损坏，需要避免把历史信息当成本次已确认根因。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以根据这份报告直接判定本次异常图像的原因就是静电吗？
- Đáp: 不可以。本次报告明确记录的是 `Tín hiệu T1(K) bất thường`；另外一句只是说"以前曾发生过因静电导致元件损坏的故障"。文件没有明确确认本次案例的根因就是静电，因此不能自行提升为本次结论。 Nguồn file: KTD-2026-06-0526-Iris2024-C35-A8.4-Hình ảnh bất thường.xlsx

## CÂU HỎI 2731
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 異常画像ケースの対象部品と発生ラインを確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 対象は `UNIT HIGH VOLTAGE TRANSFER`、品番-Rev=`3V2XC45021-1`、ライン=`C35-A8.4` で合っていますか。
- Đáp: はい。Model=`Iris2024`、S.No(Lot)=`6T31165F0084`、Supplier=`POWER SUPPLY TECHNOLOGY (HONG KONG)` と記載されています。 Nguồn file: KTD-2026-06-0526-Iris2024-C35-A8.4-Hình ảnh bất thường.xlsx
