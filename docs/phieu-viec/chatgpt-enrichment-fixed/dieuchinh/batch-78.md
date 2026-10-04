# Mẻ 78 — Điều-tra-lỗi — Q3092–Q3121 (30 cặp)

- Ngày: 2026-10-05 ~02:35 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt (lần đầu preview báo "Không thể tải tệp này", bấm "Thử lại" một lần thì thu hồi được toàn văn)
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ — giữ nguyên `0`, `Open`, `0L`, ô trống; không tự chuẩn hóa; OK/NG chỉ dùng khi chính file định nghĩa
- Điểm phân biệt case:
  - 2 case C6770 ĐỘC LẬP trong cùng mẻ: Q3095–3097 (KTD-2025-09-0941, C33-A3, Q1 short, Lot Q1=`RJH60T04 4N2 027`; bảng Q2/Q1 không gán OK/NG: E-G=`60Ω/29.5kΩ`, G-C=`60Ω/61.3kΩ`, C-E=`0.1Ω/3.9kΩ`) vs Q3107–3109 (KTD-2025-07-0788, C33-A9, Q1 short, Lot=`RJH6T04 521 004`; Q1=`1.1Ω/1.1Ω/0.1Ω`, Q2=`29.5kΩ/61.8kΩ/3.96kΩ`)
  - Case C9540 Q3104–3106 (KTD-2025-09-0965, C35-A1, PWB ENGINE ASSY, vỡ linh kiện C229, không ghi thêm nguyên nhân) ĐỘC LẬP — khác các C9540 mẻ 67 (U1 hỏng), 68 (C231/C229 bong), 72, 77
  - Case C6950 Q3101–3103 (KTD-2025-07-0733): Contents of defect=`C6950` nhưng Status of occurrence ghi Panel báo `C6760` — giữ nguyên mâu thuẫn, không tự sửa; Q1/Q2 short, F002 đứt, file định nghĩa F002 OK=`0.1 Ω`/NG=`Open`
  - File 9 (KTD-2024-6): filename ghi `C34 A7` nhưng title block Line=`C35-A7`; Reappear rate giữ Raw value `0`; cover=Đóng, RCOVER_OPEN=`0V`, file ghi Không vấn đề; Item code/name/S.No/Supplier là ô trống
  - Case F052 Q3119–3121 (TABLET OPERATION, 30C2G45060-1): file chỉ ghi Panel hiển thị F052 và ngoại quan không bất thường
  - Case Write DP Serial NG Q3113–3115 (DP Iris2020): chuỗi ICT=OK → FCT không Download=NG Step 003-001 → FCT + Download=OK → máy thực nghiệm=OK; không gộp kết luận bảng lịch sử nhiều case trong file vào case hiện tại
- Không suy diễn C229 vỡ, C963 bong, Q1 short, thiếu FT marking hoặc F052 thành root cause ngoài báo cáo

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 3092
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Aging phát sinh Error80 và kỹ sư cần xác nhận đúng dữ liệu đo IC101.
- Cách hỏi: trực tiếp
- Hỏi: File ghi những bất thường nào và giá trị IC101 pin3–SG là bao nhiêu?
- Đáp: File ghi ảnh màu K bất thường, tín hiệu sóng màu K bất thường; điện trở IC101 pin3–SG được định nghĩa OK=`6.6M`, NG=`3.1M`. Nguồn file: KTD-2025-06-0650-Iris2024-C35-A6-Error80.xlsx

## CÂU HỎI 3093
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: Aging过程中机器显示Error80，需要参考报告中的K色调查结果。
- Cách hỏi: tình huống
- Hỏi: 该案例对K色图像、K色信号和IC101分别记录了什么？
- Đáp: 文件记录 `K色图像异常`、`K色信号检查异常`，IC101 pin3-SG电阻为 OK=`6.6M`、NG=`3.1M`。 Nguồn file: KTD-2025-06-0650-Iris2024-C35-A6-Error80.xlsx

## CÂU HỎI 3094
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Error80表示と調査結果を区別して整理している。
- Cách hỏi: so sánh
- Hỏi: ラインでの発生現象とIC101の調査結果はそれぞれ何ですか。
- Đáp: 発生現象は Aging中の `Error80` 表示です。調査ではK色画像・K色信号が異常で、IC101 pin3-SGは OK=`6.6M`、NG=`3.1M` と記載されています。 Nguồn file: KTD-2025-06-0650-Iris2024-C35-A6-Error80.xlsx

## CÂU HỎI 3095
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Case C6770 có Q1 short và bảng đo Q1/Q2 nên cần tránh tự gán phán định cho số liệu.
- Cách hỏi: xử lý sự cố
- Hỏi: Có thể tự gán OK/NG cho các giá trị Q1 và Q2 trong bảng điện trở không?
- Đáp: Không. Bảng chỉ ghi Q2/Q1: E-G=`60Ω / 29.5kΩ`, G-C=`60Ω / 61.3kΩ`, C-E=`0.1Ω / 3.9kΩ`. Investigation riêng ghi `Q1 bị Short`, nhưng bảng Q1/Q2 không định nghĩa từng giá trị là OK/NG. Nguồn file: KTD-2025-09-0941-Iris2024-C33-A3-C6770.xlsx

## CÂU HỎI 3096
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认当前C6770案例的Q1 Lot和调查结论。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 本案例Q1被确认Short，Q1 Lot=`RJH60T04 4N2 027`，对吗？
- Đáp: 对。Item=`PWB IH 100 ASSY WITH SOFTWARE`，S.No=`69D0054B6909`，Line=`C33-A3`。 Nguồn file: KTD-2025-09-0941-Iris2024-C33-A3-C6770.xlsx

## CÂU HỎI 3097
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Q1/Q2のC-E抵抗値を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: C-Eの抵抗値はQ2とQ1でそれぞれいくつですか。
- Đáp: Q2=`0.1Ω`、Q1=`3.9kΩ` です。この表自体にはOK/NG判定は付いていません。 Nguồn file: KTD-2025-09-0941-Iris2024-C33-A3-C6770.xlsx

## CÂU HỎI 3098
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: C963 bị bong sau khi board đã được siết vít.
- Cách hỏi: tình huống
- Hỏi: Báo cáo ghi sự thật đã xác nhận và phần phán đoán thế nào?
- Đáp: File xác nhận `C963 bị bong` và `bản mạch đã được siết vít`; phần nguyên nhân chỉ ghi `phán đoán ngoại lực làm bong linh kiện`. Nguồn file: KTD-2025-09-0937-Iris2020-C35-ASSY2-Bong linh kiện.xlsx

## CÂU HỎI 3099
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师区分C963脱落事实与外力推测。
- Cách hỏi: so sánh
- Hỏi: 已确认内容与原因推测分别是什么？
- Đáp: 已确认的是 `C963部品脱落`、基板已经锁螺丝；文件中的推测是 `外力导致部品脱落`，不能升级为更具体的已确认原因。 Nguồn file: KTD-2025-09-0937-Iris2020-C35-ASSY2-Bong linh kiện.xlsx

## CÂU HỎI 3100
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 外力推定だけから追加対策を作らないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: C963剥がれについて、具体的な衝突工程や交換対策を追加できますか。
- Đáp: できません。ファイルには `外力で部品が剥がれたと推定` までしかなく、具体的な発生工程や対策は記載されていません。 Nguồn file: KTD-2025-09-0937-Iris2020-C35-ASSY2-Bong linh kiện.xlsx

## CÂU HỎI 3101
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Filename và Contents of defect là C6950 nhưng Status lại ghi mã khác.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File phải giữ nguyên việc Contents of defect=`C6950` nhưng Status of occurrence ghi Panel báo `C6760`, đúng không?
- Đáp: Đúng. Không tự sửa hoặc hợp nhất hai mã. Investigation ghi Q1, Q2 short và F002 trên UNIT LOW VOLT bị đứt. Nguồn file: KTD-2025-07-0733-Iris2024-C33-A11-C6950.xlsx

## CÂU HỎI 3102
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接查看F002的判定数据。
- Cách hỏi: trực tiếp
- Hỏi: F002的OK和NG值怎样定义？
- Đáp: 文件明确规定 F002：OK=`0.1 Ω`、NG=`Open`，并记录F002断线。 Nguồn file: KTD-2025-07-0733-Iris2024-C33-A11-C6950.xlsx

## CÂU HỎI 3103
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: RCG Copy Check時の表示と調査結果を確認している。
- Cách hỏi: tình huống
- Hỏi: RCG Copy Checkで表示されたコードと調査結果は何ですか。
- Đáp: Status欄ではPanel表示=`C6760`。調査結果は `Q1/Q2 Short` と `UNIT LOW VOLT基板のF002断線`、F002は OK=`0.1 Ω`、NG=`Open` です。 Nguồn file: KTD-2025-07-0733-Iris2024-C33-A11-C6950.xlsx

## CÂU HỎI 3104
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Có nhiều case C9540 nên kỹ sư cần phân biệt case tháng 9/2025 này.
- Cách hỏi: so sánh
- Hỏi: Case này xác nhận điều gì và không cung cấp thông tin gì thêm?
- Đáp: File xác nhận bật máy báo `C9540` và Investigation=`Vỡ linh kiện C229`. File không ghi cơ chế làm vỡ, nguyên nhân sâu hơn hoặc đối sách. Nguồn file: KTD-2025-09-0965-Iris2024-C35-A1-C9540.xlsx

## CÂU HỎI 3105
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现C229破损，需要避免自行补充碰撞原因。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以根据C229破损自行判断外力或碰撞是原因吗？
- Đáp: 不可以。当前文件只写 `C229部品破损`，没有记录外力、碰撞位置或其它根因。 Nguồn file: KTD-2025-09-0965-Iris2024-C35-A1-C9540.xlsx

## CÂU HỎI 3106
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C9540ケースの基本情報を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 対象は `PWB ENGINE ASSY WITH SOFTWARE`、品番-Rev=`3VC2L01070-5`、S.No=`6J21058G2406` ですね。
- Đáp: はい。Line=`C35-A1`、Quantity=`1`、Machine No.は **Raw value: ô trống** です。 Nguồn file: KTD-2025-09-0965-Iris2024-C35-A1-C9540.xlsx

## CÂU HỎI 3107
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Case C6770 tại C33-A9 có bảng điện trở riêng cho Q1/Q2.
- Cách hỏi: trực tiếp
- Hỏi: Q1 và Q2 có các giá trị E-G, G-C, C-E lần lượt thế nào?
- Đáp: Q1: E-G=`1.1Ω`, G-C=`1.1Ω`, C-E=`0.1Ω`; Q2: E-G=`29.5kΩ`, G-C=`61.8kΩ`, C-E=`3.96kΩ`. Investigation ghi `Q1 bị Short`. Nguồn file: KTD-2025-07-0788-Iris2024-C33-A9-C6770.xlsx

## CÂU HỎI 3108
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看Q1低阻值和Short结论。
- Cách hỏi: tình huống
- Hỏi: 文件对Q1记录了什么Lot和调查结论？
- Đáp: Q1 Lot=`RJH6T04 521 004`；调查结论是 `Q1 Short`。电阻表本身没有对Q1/Q2各值标注OK/NG。 Nguồn file: KTD-2025-07-0788-Iris2024-C33-A9-C6770.xlsx

## CÂU HỎI 3109
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Q1とQ2のG-C値を比較している。
- Cách hỏi: so sánh
- Hỏi: G-C抵抗はQ1とQ2でどう違いますか。
- Đáp: Q1=`1.1Ω`、Q2=`61.8kΩ` です。表にはこれらの値に個別のOK/NG判定はありません。 Nguồn file: KTD-2025-07-0788-Iris2024-C33-A9-C6770.xlsx

## CÂU HỎI 3110
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: TLBĐ báo RFID NG nhưng Investigation chỉ có kết quả ngoại quan.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi kết quả ngoại quan nào và có thể tự thêm nguyên nhân không?
- Đáp: Ngoại quan phát hiện `thiếu dấu marking FT`. File không ghi tại sao thiếu marking FT hoặc đối sách sửa chữa, nên không tự bổ sung. Nguồn file: KTD-2025-08-0869-Iris2024-C33-A1-TLBĐ NG.xlsx

## CÂU HỎI 3111
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认PC上实际显示的NG项目。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: TLBĐ时PC显示NG `"RFID Reader Writer Version , RFID (K)"`，外观发现缺少FT marking，对吗？
- Đáp: 对。对象是 `PWB RFID ASSY WITH SOFTWARE`，S.No=`0-5731`，Quantity=`1`。 Nguồn file: KTD-2025-08-0869-Iris2024-C33-A1-TLBĐ NG.xlsx

## CÂU HỎI 3112
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: RFIDケースの基本情報と外観結果を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 品番-Revと外観確認結果は何ですか。
- Đáp: Item code-Rev=`3VC2N01040-3`、外観確認結果は `FTマーキング欠落` です。 Nguồn file: KTD-2025-08-0869-Iris2024-C33-A1-TLBĐ NG.xlsx

## CÂU HỎI 3113
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Write DP Serial NG nhưng kết quả thay đổi theo chế độ Download của FCT.
- Cách hỏi: tình huống
- Hỏi: Chuỗi kết quả ICT/FCT của case hiện tại được ghi cụ thể thế nào?
- Đáp: `ICT => OK`; `FCT ở chế độ không Download => NG Step 003-001`; `FCT + Download => OK`; đưa board quay lại máy thực nghiệm kiểm tra => `OK`. Ngoại quan=`không bất thường`. Nguồn file: KTD-2025-08-0866-DP Iris2020-C2B- Write DP Serial NG.xlsx

## CÂU HỎI 3114
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较不Download和Download条件下的FCT结果。
- Cách hỏi: so sánh
- Hỏi: 两种FCT条件的结果有什么不同？
- Đáp: 不Download时=`NG Step 003-001`；重新进行 `FCT + Download` 后=`OK`。随后回到实际机器检查也=`OK`。 Nguồn file: KTD-2025-08-0866-DP Iris2020-C2B- Write DP Serial NG.xlsx

## CÂU HỎI 3115
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: ICT/FCT結果だけから原因を断定しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: FCT非Download時にStep 003-001 NGだったことから、故障部品を特定できますか。
- Đáp: できません。現在ケースでは外観異常なし、ICT=`OK`、FCT非Download=`NG Step 003-001`、FCT+Download=`OK`、実機確認=`OK` までです。原因部品は記載されていません。 Nguồn file: KTD-2025-08-0866-DP Iris2020-C2B- Write DP Serial NG.xlsx

## CÂU HỎI 3116
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Filename và title block/Line của báo cáo 2024 không hoàn toàn giống nhau.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Dù filename ghi `C34 A7`, nội dung bên trong phải giữ Line=`C35-A7`, Reappear rate Raw value=`0`, đúng không?
- Đáp: Đúng. Không tự đổi Line theo filename. Model=`Iris2020`, Quantity=`2`; Item code, Item name, S.No và Supplier là **Raw value: ô trống**. Nguồn file: KTD-2024-6_Iris2020 C34 A7 máy báo Close cover front bất thường.xlsx

## CÂU HỎI 3117
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认故障复现检查的数据。
- Cách hỏi: trực tiếp
- Hỏi: OFF/ON和Line-out重复操作的结果分别是什么？
- Đáp: OFF/ON后输入 `79248313`：`OK，不再现`；Line-out后重复输入 `79248313` 共 `15次`：全部 `OK`。 Nguồn file: KTD-2024-6_Iris2020 C34 A7 máy báo Close cover front bất thường.xlsx

## CÂU HỎI 3118
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 発生時のCover状態とRCOVER_OPEN電圧を確認している。
- Cách hỏi: tình huống
- Hỏi: エラー発生時のCover状態とRCOVER_OPEN電圧はどう記録されていますか。
- Đáp: Cover状態=`Đóng`、RCOVER_OPEN=`0V`。ファイル自身が `Không vấn đề` と記載しています。 Nguồn file: KTD-2024-6_Iris2020 C34 A7 máy báo Close cover front bất thường.xlsx

## CÂU HỎI 3119
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: TABLET OPERATION kiểm tra bằng jig thì Panel hiển thị F052.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng trên jig và kết quả Investigation khác nhau thế nào?
- Đáp: Khi check jig, Panel hiển thị `F052`; Investigation chỉ ghi `Ngoại quan không bất thường`. File không cung cấp nguyên nhân linh kiện. Nguồn file: KTD-2025-08-0851-Iris2024-Operation -K4-F052.xlsx

## CÂU HỎI 3120
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师遇到F052，但报告只完成了外观确认。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以根据F052代码自行增加部品故障或维修对策吗？
- Đáp: 不可以。文件只记录 `Check jig时Panel显示F052` 和 `外观检查无异常`，没有具体原因或对策。 Nguồn file: KTD-2025-08-0851-Iris2024-Operation -K4-F052.xlsx

## CÂU HỎI 3121
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: F052ケースの対象情報を最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 対象は `TABLET OPERATION`、品番-Rev=`30C2G45060-1`、Line=`Operation -K4`、Quantity=`1` ですね。
- Đáp: はい。S.No(Lot)=`T101GG005601 / NHP24120233`、Machine No.=`110C2S2US0` です。 Nguồn file: KTD-2025-08-0851-Iris2024-Operation -K4-F052.xlsx
