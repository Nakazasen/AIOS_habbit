# Mẻ 75 — Điều-tra-lỗi — Q3002–Q3031 (30 cặp)

- Ngày: 2026-10-05 ~02:15 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ — giữ nguyên `0L`, `OL`, `Open`, `0.5`, `OlΩ`, ô trống; không tự chuẩn hóa; OK/NG chỉ dùng khi chính file có cột/nhãn OK/NG
- Điểm phân biệt:
  - File `KTD-2025-08-0907`: filename ghi `0907` nhưng trường KTD nội bộ là `KTD-2025-08-0xxx` — giữ nguyên khác biệt, không tự sửa
  - File `The cover is open`: phần Việt ghi `C312 bất thường (380Ω)`, phần Nhật ghi `C321の抵抗値：異常380Ω` — giữ nguyên mâu thuẫn, không tự chọn mã
  - Case DP Iris2020 C9080 `KTD-2025-11-1232` là case LED1 ĐỘC LẬP: LED1 không sáng, NG=`0L` (không chuẩn hoá thành OL), Anode LED1 chưa được hàn — khác 3 case C9080 mẻ 74 (LED2) và các case C9080 mẻ 70/73
  - Q3004: Reappear rate giữ nguyên `0.5` theo nguồn (không suy diễn thành 50%)
- Không suy diễn tín hiệu K bất thường, C312/C321, U12 hay D1 thành nguyên nhân sâu hơn ngoài kết luận của báo cáo

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 3002
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy bật nguồn hiển thị F040 và kỹ sư tra case lịch sử tại C34-A6.
- Cách hỏi: trực tiếp
- Hỏi: File ghi kết quả tái hiện và ngoại quan tại YC19 như thế nào?
- Đáp: Line-out rồi OFF/ON ghi `5/10 lần NG`; đồng thời phát hiện `dị vật dạng thiếc ở chân pin21-32 YC19 trên bản mạch main`. Nguồn file: KTD-2025-09-0966-Iris2024-C34-A6-F040.xlsx

## CÂU HỎI 3003
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师在开机时看到F040，需要按原报告确认连接器附近的调查结果。
- Cách hỏi: tình huống
- Hỏi: 该报告在YC19附近确认了什么？
- Đáp: 文件记录 MAIN板 `YC19 pin21-32` 位置存在锡状异物。报告没有进一步写明该异物的产生工序或修理对策。 Nguồn file: KTD-2025-09-0966-Iris2024-C34-A6-F040.xlsx

## CÂU HỎI 3004
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 入力済み項目と空欄項目を区別している。
- Cách hỏi: so sánh
- Hỏi: この報告書で入力されている品番と、空欄の項目は何ですか。
- Đáp: Item code-Rev=`3VC2L01020`、S.No=`6HZ1058A9908`。Item name、Supplier、Machine No. は **Raw value: ô trống** です。Reappear rateはソース上 `0.5` のまま保持します。 Nguồn file: KTD-2025-09-0966-Iris2024-C34-A6-F040.xlsx

## CÂU HỎI 3005
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: DP Iris2020 báo C9080 khi scan và kỹ sư cần dùng đúng kết quả LED1.
- Cách hỏi: xử lý sự cố
- Hỏi: Báo cáo ghi gì về LED1, giá trị diode và cực Anode?
- Đáp: File ghi `LED1 không sáng`; diode được chính file định nghĩa NG=`0L`, OK=`0.7V`; ngoại quan phát hiện cực Anode của LED1 chưa được hàn. Giữ nguyên Raw value `0L`, không tự sửa thành `OL`. Nguồn file: KTD-2025-11-1232-DP Iris2020-C2D-C9080.xlsx

## CÂU HỎI 3006
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认这个C9080案例是否与之前的LED2案例不同。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 本案例异常对象是LED1，不是前面案例中的LED2，而且Anode端子未焊接，对吗？
- Đáp: 对。本文件明确记录 `LED1不亮`、NG=`0L`、OK=`0.7V`，并确认 `LED1 Anode端子未焊接`。 Nguồn file: KTD-2025-11-1232-DP Iris2020-C2D-C9080.xlsx

## CÂU HỎI 3007
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C9080ケースの基本情報を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: Model、Item、S.Noは何ですか。
- Đáp: Model=`DP Iris2020`、Item=`CIS`、S.No(Lot)=`FD2CFC -01 / 52 5101500814` です。 Nguồn file: KTD-2025-11-1232-DP Iris2020-C2D-C9080.xlsx

## CÂU HỎI 3008
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy không lên nguồn và kỹ sư kiểm tra chuỗi xử lý RF001 trong báo cáo.
- Cách hỏi: tình huống
- Hỏi: Báo cáo ghi trạng thái RF001 trước và sau khi thay thế thế nào?
- Đáp: Trước thay, RF001 được ghi `bị đứt`, với giá trị do file định nghĩa OK=`7,6 Ω`, NG=`Open`; sau khi thay RF001, kiểm tra lại máy=`OK`. File cũng ghi mất điện áp `5V`, K001=`OK`, F001=`OK`. Nguồn file: KTD-2025-08-0907-Iris2024-C33-A8-Không lên nguồn..xlsx

## CÂU HỎI 3009
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 文件名和报告内部KTD编号并不一致，需要保留原始信息。
- Cách hỏi: so sánh
- Hỏi: 文件名中的KTD编号与报告内部字段有什么差异？
- Đáp: 文件名是 `KTD-2025-08-0907...`，但报告内部实际写的是 `KTD-2025-08-0xxx`。不能擅自把内部值改成0907。 Nguồn file: KTD-2025-08-0907-Iris2024-C33-A8-Không lên nguồn..xlsx

## CÂU HỎI 3010
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: RF001交換結果から、ファイル以上の故障原因を追加しないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: RF001交換後に装置がOKになったことから、RF001断線の根本原因まで追加できますか。
- Đáp: できません。ファイルはRF001断線、OK=`7,6 Ω`／NG=`Open`、交換後装置OK、Partnerへ連絡することまでを記載しています。断線の根本原因は記載されていません。 Nguồn file: KTD-2025-08-0907-Iris2024-C33-A8-Không lên nguồn..xlsx

## CÂU HỎI 3011
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Cùng một ô Investigation có mã linh kiện khác nhau giữa tiếng Việt và tiếng Nhật.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Phần Việt ghi C312 nhưng phần Nhật ghi C321, và cả hai đều kèm giá trị `380Ω`, đúng không?
- Đáp: Đúng. Nguyên văn nguồn là `Linh kiện C312 bất thường (380Ω)` và `C321の抵抗値：異常380Ω`. Không tự chọn C312 hay C321 là mã đúng. Nguồn file: KTD-2025-08-0854-Iris2024-C34-A1-The cover is open.xlsx

## CÂU HỎI 3012
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师需要直接确认报告中的画面提示。
- Cách hỏi: trực tiếp
- Hỏi: 开机时画面显示了什么？
- Đáp: 文件记录 `maintance cover front is open`。Contents of defect=`The cover is open`。 Nguồn file: KTD-2025-08-0854-Iris2024-C34-A1-The cover is open.xlsx

## CÂU HỎI 3013
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 同じ調査欄に部品番号の不一致があるため、勝手に補正せず参照している。
- Cách hỏi: tình huống
- Hỏi: このケースを参照する際、C312とC321のどちらを確定部品番号として扱えばよいですか。
- Đáp: ソースだけでは確定できません。ベトナム語は `C312`、日本語は `C321` と記載しており、値はいずれも `380Ω` です。記載差異をそのまま保持します。 Nguồn file: KTD-2025-08-0854-Iris2024-C34-A1-The cover is open.xlsx

## CÂU HỎI 3014
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư phân biệt hiện tượng nhận biết giấy với kết quả ngoại quan U1.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng trên máy và kết quả điều tra U1 khác nhau thế nào?
- Đáp: Hiện tượng là `Không nhận biết được size giấy trong cassette2`; Investigation ghi `U1 dính hàn pin 82-83-84`. Nguồn file: KTD-2025-12-1384-Iris2024-C35-A6-Không nhận biết size giấy.xlsx

## CÂU HỎI 3015
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现U1三个pin焊锡桥接，但不能扩大报告结论。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以根据U1 pin82-83-84焊锡桥接自行补充返修方法吗？
- Đáp: 不可以。文件只记录 `U1 pin82、83、84发生焊锡桥接`，没有记载具体返修方法或追加对策。 Nguồn file: KTD-2025-12-1384-Iris2024-C35-A6-Không nhận biết size giấy.xlsx

## CÂU HỎI 3016
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 紙サイズ検知NGケースの基板情報を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 対象は `PWB FEED DRIVE ASSY`、品番-Rev=`3V2XC01030-4`、Line=`C35-A6` ですね。
- Đáp: はい。S.No=`2XC-0-5Z10`、Supplier=`KATOLEC VIET NAM CORPORATION`、Quantity=`1` です。 Nguồn file: KTD-2025-12-1384-Iris2024-C35-A6-Không nhận biết size giấy.xlsx

## CÂU HỎI 3017
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Aging báo Error56 và kỹ sư tra đúng kết quả kiểm tra ảnh/tín hiệu màu K.
- Cách hỏi: trực tiếp
- Hỏi: Investigation của case Error56 này ghi những gì?
- Đáp: File ghi `In hình ảnh màu K bất thường` và `Kiểm tra Tín hiệu sóng màu K bất thường`. Không có linh kiện nguyên nhân cụ thể trong nội dung nguồn. Nguồn file: KTD-2025-08-0902-Iris2024-C35-A6-Error56.xlsx

## CÂU HỎI 3018
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师在Aging时出现Error56，需要严格按报告范围调查。
- Cách hỏi: tình huống
- Hỏi: 报告有没有确定具体损坏元件或修理对策？
- Đáp: 没有。文件只记录 `K色图像异常` 和 `K色信号检查异常`，没有写具体损坏元件或维修措施。 Nguồn file: KTD-2025-08-0902-Iris2024-C35-A6-Error56.xlsx

## CÂU HỎI 3019
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Error56の発生現象と調査結果を比較している。
- Cách hỏi: so sánh
- Hỏi: 発生現象と調査結果はどう違いますか。
- Đáp: 発生現象は Aging中の `Error56` 表示。調査結果は `K色画像異常` と `K色信号検査：異常` です。 Nguồn file: KTD-2025-08-0902-Iris2024-C35-A6-Error56.xlsx

## CÂU HỎI 3020
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: TESTER báo NG khi đo thông mạch Drum Heater và kỹ sư cần theo đúng đối sách có sẵn.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi kết quả ngoại quan và hành động tiếp theo thế nào?
- Đáp: Ngoại quan phát hiện `linh kiện R14 chưa được hàn`; hành động ghi trong file là `Tổng hợp thông tin liên lạc Partner điều tra`. Không thêm phương pháp sửa chữa ngoài nguồn. Nguồn file: KTD-2026-08-0857-Iris2024-C33-Hontai1-Kiểm tra thông mạch NG.xlsx

## CÂU HỎI 3021
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认这个导通NG案例的对象板。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 对象是 `PWB DRUM HEATER ASSY`、品号-Rev=`3V2XC01190-2`、Line=`C33-Hontai1`，对吗？
- Đáp: 对。S.No=`2XC06626`，Quantity=`1`。 Nguồn file: KTD-2026-08-0857-Iris2024-C33-Hontai1-Kiểm tra thông mạch NG.xlsx

## CÂU HỎI 3022
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Drum Heater導通検査NGの外観結果を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 外観検査で何が確認されていますか。
- Đáp: `R14部品が未半田` であることを確認しています。 Nguồn file: KTD-2026-08-0857-Iris2024-C33-Hontai1-Kiểm tra thông mạch NG.xlsx

## CÂU HỎI 3023
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: LCD chuyển tím sau khi in Process và kỹ sư cần xác nhận điều kiện tái hiện.
- Cách hỏi: tình huống
- Hỏi: File ghi khi nào màn hình chuyển sang màu tím?
- Đáp: Tại line, sau khi in `8` tờ Process thì LCD chuyển màu tím bất thường; Investigation ghi màn hình chuyển màu tím sau `60p` hoạt động. Nguồn file: KTD-2025-10-1119-Iris2024-C34-A8.5-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3024
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较现场发生条件和调查栏中的时间条件。
- Cách hỏi: so sánh
- Hỏi: Line发生状况和Investigation栏分别怎样描述紫屏条件？
- Đáp: Line状况写 `打印8张Process后LCD异常变紫`；Investigation写 `启动60分钟后画面变紫`。两条记录都按源文件保留，不自行合并成新的条件。 Nguồn file: KTD-2025-10-1119-Iris2024-C34-A8.5-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3025
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 紫色表示異常の原因がまだ特定されていない報告を扱っている。
- Cách hỏi: xử lý sự cố
- Hỏi: この報告からLCD内部の故障部品を追加できますか。
- Đáp: できません。ファイルは紫色表示の発生条件と `情報をまとめてPartnerへ送る` ことまでで、原因部品は記載していません。 Nguồn file: KTD-2025-10-1119-Iris2024-C34-A8.5-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3026
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Đây là case DP Iris2020 nên kỹ sư cần tránh nhầm sang Iris2024.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Model=`DP Iris2020`, đối tượng=`PWB DRIVER ASSY WITH SOFTWARE`, và U12 bị vỡ có dấu hiệu ngoại lực, đúng không?
- Đáp: Đúng. Item code-Rev=`3V3V301010-5`, line=`C2C-A4`; Investigation ghi U12 bị vỡ và có dấu hiệu tác động ngoại lực. Nguồn file: KTD-2026-04-0359-DP Iris2020-C2C-A4-Không nhận biết size giấy.xlsx

## CÂU HỎI 3027
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认ISU的故障现象。
- Cách hỏi: trực tiếp
- Hỏi: 该案例的实际故障现象是什么？
- Đáp: `ISU无法识别A4纸张尺寸 / Không nhận biết size giấy A4 trên ISU`。 Nguồn file: KTD-2026-04-0359-DP Iris2020-C2C-A4-Không nhận biết size giấy.xlsx

## CÂU HỎI 3028
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: U12破損と外力痕を確認した後、ソースにある対応だけを実施範囲として扱っている。
- Cách hỏi: tình huống
- Hỏi: このファイルに記載された後続対応は何ですか。
- Đáp: `QCと製造へ連絡して追加確認`、日本語欄では `ラインの作業注意` と記載されています。具体的なU12交換方法などは記載されていません。 Nguồn file: KTD-2026-04-0359-DP Iris2020-C2C-A4-Không nhận biết size giấy.xlsx

## CÂU HỎI 3029
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Case C6950 có cả kết quả YF1/D1 và bảng đo nhiều linh kiện nên cần phân biệt rõ.
- Cách hỏi: so sánh
- Hỏi: Investigation chính và bảng đo bổ sung ghi những nội dung nào?
- Đáp: Investigation chính ghi `đứt cầu chì YF1` và `D1 short pin 2-3-4`; phần Nhật ghi `BridgeDiode D1内部壊れたのため`. Bảng bổ sung ghi các giá trị OK/NG của U6, Q1, Q2 và các giá trị riêng của D1. Không dùng riêng một giá trị bảng để tạo thêm nguyên nhân. Nguồn file: KTD-2025-07-0789-Iris2024-C35-A6-C6950.xlsx

## CÂU HỎI 3030
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看D1的电阻测量结果，需要保持源文件原值。
- Cách hỏi: xử lý sự cố
- Hỏi: D1各pin组合的电阻值怎样记录？可以自行赋予OK/NG吗？
- Đáp: 文件记录 D1：`2-4=0.2Ω`、`4-3=0.2Ω`、`2-1=OL`、`1-3=OL`。这些D1行没有单独标注OK/NG列，因此不能自行赋予OK/NG。 Nguồn file: KTD-2025-07-0789-Iris2024-C35-A6-C6950.xlsx

## CÂU HỎI 3031
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C6950ケースのQ1/Q2測定値を正しく読み取れているか確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Q1のC-Eは OK=`0.7MΩ`、NG=`257kΩ`、Q2のC-Gは OK=`230kΩ`、NG=`0.56MΩ` ですね。
- Đáp: はい。これらのOK/NGはファイル自身の表で定義されています。なおU6 pin11はソース上 `OlΩ` と記載されているため、別の表記へ勝手に修正しません。 Nguồn file: KTD-2025-07-0789-Iris2024-C35-A6-C6950.xlsx
