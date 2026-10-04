# Mẻ 73 — Điều-tra-lỗi — Q2942–Q2971 (30 cặp)

- Ngày: 2026-10-05 ~02:02 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ (giữ nguyên 0, `-`, `ー`, `0L`, `OL` — không tự sửa 0L→OL; OK/NG chỉ dùng khi nguồn định nghĩa)
- Điểm phân biệt: 3 case C6770 ĐỘC LẬP trong cùng mẻ — Q2951–2953 (KTD-2025-06-0582, C35-A8, IH200, Q1 short 3 cực, Lot Q1=RJH60T04 4N2 027) vs Q2957–2959 (KTD-2025-11-1150, C35-A8, IH200, Q1 Short, Lot Q1=RJH60T04 541 017) vs Q2960–2962 (KTD-2025-07-0673, C33-A11, IH100, bảng điện trở Q1/Q2 không gán OK/NG) — không trộn
- Case C9080 DP Iris2020 mới: giữ nguyên 2 cách ghi NG=0L (text, OK=0.7V) và LED1 NG=OL (bảng, OK=0.7V), không tự thống nhất
- C6030: phán đoán tháo/lắp dây gây lỗi giữ đúng mức phán đoán của báo cáo; Error56 KTD-2025-07-0787: vị trí lỗi chưa xác định, giữ yêu cầu trả về PSTFS

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 2942
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Jig báo NG khi kiểm tra chịu áp cách điện tại Hontai.
- Cách hỏi: trực tiếp
- Hỏi: Ngoại quan phát hiện gì trong case chịu áp cách điện NG?
- Đáp: File ghi phát hiện `có vít rơi dưới Heatsink của bản mạch nguồn`. Sau đó đã liên lạc QC và chế tạo để xác nhận điều tra. Nguồn file: KTD-2025-10-1091-Iris2024-C33-Hontai-Chịu áp cách điện NG.xlsx

## CÂU HỎI 2943
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师进行绝缘耐压检查时治具显示NG。
- Cách hỏi: tình huống
- Hỏi: 该历史案例在外观检查和后续联络方面记录了什么？
- Đáp: 外观检查发现电源基板Heatsink下方有一颗螺钉；文件还记录已联系QC和制造进行确认调查。没有记录进一步的确定根因。 Nguồn file: KTD-2025-10-1091-Iris2024-C33-Hontai-Chịu áp cách điện NG.xlsx

## CÂU HỎI 2944
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 入力済み項目と記号だけの項目を区別している。
- Cách hỏi: so sánh
- Hỏi: この報告書でMachine No.とItem/Supplier関連の記載はどう違いますか。
- Đáp: Machine No.=`110C2S4US0 / 1U65X00467`。一方、Item code-Rev=`-`、Item name=`ー`、S.No=`ー`、Supplier=`ー` です。これらはソースのRaw valueとして保持します。 Nguồn file: KTD-2025-10-1091-Iris2024-C33-Hontai-Chịu áp cách điện NG.xlsx

## CÂU HỎI 2945
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Ảnh Process xuất hiện nhiều dạng bất thường nhưng báo cáo chỉ có một kết quả kiểm tra tín hiệu.
- Cách hỏi: xử lý sự cố
- Hỏi: Có thể từ tín hiệu MAG 4 màu bất thường kết luận linh kiện cụ thể nào bị hỏng không?
- Đáp: Không. File chỉ ghi `Tín hiệu MAG 4 màu đang bất thường`; không nêu linh kiện nguyên nhân hoặc đối sách cụ thể. Nguồn file: KTD-2025-11-1170-Iris2024-C35-8.2-Hình ảnh bất thường.xlsx

## CÂU HỎI 2946
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认自己是否正确理解两种图像异常。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 文件是说MC图有白色不均 (M 70%)，GY图有M/C/Y颜色的粗横线，对吗？
- Đáp: 对。调查结果另记录 `MAG 4色信号异常`。 Nguồn file: KTD-2025-11-1170-Iris2024-C35-8.2-Hình ảnh bất thường.xlsx

## CÂU HỎI 2947
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 画像異常ケースの対象ユニットを直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 対象品名、品番-Rev、Lineは何ですか。
- Đáp: Item name=`UNIT HIGH VOLTAGE MAIN`、Item code-Rev=`3V2L745040-1`、Line=`C35-8.2` です。 Nguồn file: KTD-2025-11-1170-Iris2024-C35-8.2-Hình ảnh bất thường.xlsx

## CÂU HỎI 2948
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: C6030 xuất hiện khi chạy U155 với Empty TonerBox jig.
- Cách hỏi: tình huống
- Hỏi: Khi làm lại thao tác, báo cáo ghi kết quả tái hiện như thế nào?
- Đáp: Bật/tắt khi có hộp mực thải `15/15` lần → OK, không tái hiện; thực hiện lại U155 `10/10` lần → OK, cũng không tái hiện. Reappear rate của workbook giữ **Raw value 0**. Nguồn file: KTD-2025-11-1196-Iris2024-C33-A2-C6030.xlsx

## CÂU HỎI 2949
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师区分已确认的连接线异常与报告中的原因判断。
- Cách hỏi: so sánh
- Hỏi: 已确认的事实和文件中的推断分别是什么？
- Đáp: 已确认的是：对conncord施加动作时，从Fuser Unit到PWB Image的导通出现异常，并发现conncord端部pin变形。文件进一步 `判断/推测操作过程中拆装线材导致错误`。后者保持为报告中的判断，不扩大为其它原因。 Nguồn file: KTD-2025-11-1196-Iris2024-C33-A2-C6030.xlsx

## CÂU HỎI 2950
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C6030報告に記載された対応範囲だけを使用している。
- Cách hỏi: xử lý sự cố
- Hỏi: ファイルにない交換部品や修理方法を追加してよいですか。
- Đáp: いいえ。記載された対応は `QCと製造へ連絡して確認し、作業に注意する` までです。部品交換や追加修理方法は記載されていません。 Nguồn file: KTD-2025-11-1196-Iris2024-C33-A2-C6030.xlsx

## CÂU HỎI 2951
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Có nhiều case C6770 nên kỹ sư cần phân biệt case IH200 này.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Case này là `PWB IH 200 ASSY WITH SOFTWARE`, in Check Black báo C6770 và Q1 short cả 3 cực với nhau, đúng không?
- Đáp: Đúng. Item code-Rev=`302C2G01100-4`, line=`C35-A8`, S.No=`69E0054C8386`. Nguồn file: KTD-2025-06-0582-Iris2024-C35-A8-C6770.xlsx

## CÂU HỎI 2952
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接核对Q1和U6的Lot。
- Cách hỏi: trực tiếp
- Hỏi: 报告记录的Q1和U6 Lot分别是什么？
- Đáp: Q1 Lot=`RJH60T04 4N2 027`；U6 Lot=`L6491D MZ6Y445`。 Nguồn file: KTD-2025-06-0582-Iris2024-C35-A8-C6770.xlsx

## CÂU HỎI 2953
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Check Black印刷でC6770が出た過去ケースを確認している。
- Cách hỏi: tình huống
- Hỏi: このケースでは外観とQ1検査結果をどう記載していますか。
- Đáp: 外観は `異常なし`、Q1検査では `3ピンがショート` と記載されています。 Nguồn file: KTD-2025-06-0582-Iris2024-C35-A8-C6770.xlsx

## CÂU HỎI 2954
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh hiện tượng trên máy với dữ liệu lịch sử công đoạn của supplier.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng hàng lỗi và kết quả kiểm tra lịch sử công đoạn được ghi thế nào?
- Đáp: Hàng lỗi: `Aging báo Error56`, `ảnh màu K bất thường` và `tín hiệu K bất thường`. Phân tích supplier ghi `lịch sử công đoạn không bất thường`, `không có lịch sử sửa chữa`; từ `2025/1~2025/7` sản xuất `101584PCS` mà không phát sinh lỗi output K tương tự. Nguồn file: KTD-2025-07-0787-Iris2024-C34-A6-Error56.xlsx

## CÂU HỎI 2955
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师尚未拿到供应商进一步解析结果。
- Cách hỏi: xử lý sự cố
- Hỏi: 当前文件是否已经确定具体故障位置或根因？
- Đáp: 没有。附加分析栏中的 `不具合箇所特定` 仍为空，文件要求 `将不良品退回PSTFS进一步解析`。不能自行补充具体故障位置。 Nguồn file: KTD-2025-07-0787-Iris2024-C34-A6-Error56.xlsx

## CÂU HỎI 2956
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Error56ケースの数量とS/Nを再確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Quantity=`2` で、S/Nは `J3J0056A5227` と `J3J0056A5294` ですね。
- Đáp: はい。両方とも追加資料では `2025/6/15 PSTFS生産品` と記載されています。 Nguồn file: KTD-2025-07-0787-Iris2024-C34-A6-Error56.xlsx

## CÂU HỎI 2957
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư phân biệt một case C6770 khác cũng thuộc IH200.
- Cách hỏi: trực tiếp
- Hỏi: Case này phát sinh C6770 trong thao tác nào và kết quả điều tra là gì?
- Đáp: File ghi `in 8 tờ Process máy báo C6770`; Investigation ghi `Linh kiện Q1 bị Short`. Nguồn file: KTD-2025-11-1150-Iris2024-C35-A8-C6770.xlsx

## CÂU HỎI 2958
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师根据Lot区分本次Q1 Short案例。
- Cách hỏi: tình huống
- Hỏi: 本次C6770案例中Q1的Lot是什么？
- Đáp: 文件记录 `LOT: RJH60T04 541 017`。 Nguồn file: KTD-2025-11-1150-Iris2024-C35-A8-C6770.xlsx

## CÂU HỎI 2959
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 6月のIH200 C6770ケースと11月ケースを区別している。
- Cách hỏi: so sánh
- Hỏi: 今回とKTD-2025-06-0582ではQ1 Lotは同じですか。
- Đáp: 同じではありません。今回のLot=`RJH60T04 541 017`、KTD-2025-06-0582は `RJH60T04 4N2 027` です。両ケースともQ1 Shortを記録していますが、Lotは別です。 Nguồn file: KTD-2025-11-1150-Iris2024-C35-A8-C6770.xlsx; KTD-2025-06-0582-Iris2024-C35-A8-C6770.xlsx

## CÂU HỎI 2960
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Bảng điện trở có nhiều giá trị khác nhau nhưng không gán cột OK/NG.
- Cách hỏi: xử lý sự cố
- Hỏi: Có thể tự gán các giá trị Q1/Q2 trong bảng là OK hay NG không?
- Đáp: Không. Bảng chỉ ghi Q1/Q2 theo từng cặp chân: `G-C=0.7Ω / 61.43kΩ`, `G-E=0.7Ω / 30.06kΩ`, `E-C=0.1Ω / 0L`; bảng không tự định nghĩa các giá trị này là OK/NG. Nguồn file: KTD-2025-07-0673-Iris2024-C33-A11-C6770.xlsx

## CÂU HỎI 2961
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认表格中的 0L 是否应保持原样。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Q2的E-C在源表中写的是 `0L`，应该原样保留而不是自动改成 OL，对吗？
- Đáp: 对。该表的原始记录是 **Raw value 0L**。不能自行修正或赋予OK/NG含义。 Nguồn file: KTD-2025-07-0673-Iris2024-C33-A11-C6770.xlsx

## CÂU HỎI 2962
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Q1 Shortケースの抵抗値を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: Q1のG-C、G-E、E-Cの値は何ですか。
- Đáp: `G-C=0.7Ω`、`G-E=0.7Ω`、`E-C=0.1Ω` です。別途、調査欄にはQ1 Shortと記載されています。 Nguồn file: KTD-2025-07-0673-Iris2024-C33-A11-C6770.xlsx

## CÂU HỎI 2963
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: DP Iris2020 báo C9080 khi chạy U411 và LED1 không sáng.
- Cách hỏi: tình huống
- Hỏi: Báo cáo ghi những kết quả nào cho LED1 và mối hàn cực Cathode?
- Đáp: File ghi `LED1 không sáng`; ngoại quan và kiểm tra thông mạch `mối hàn cực Cathode có bất thường`. Linh kiện thuộc LOT đối tượng đã được lọc hàng. Nguồn file: KTD-2025-12-1325-DP Iris2020-C2D-A6-C9080.xlsx

## CÂU HỎI 2964
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较正文和附表对LED1 NG值的写法。
- Cách hỏi: so sánh
- Hỏi: 正文和表格对LED1 NG值的写法有什么差异？
- Đáp: 正文写 `NG=0L (OK=0.7V)`；下方表格写 `LED1 NG=OL、OK=0.7V`。两种写法均按源文件原样保留，不自行统一。 Nguồn file: KTD-2025-12-1325-DP Iris2020-C2D-A6-C9080.xlsx

## CÂU HỎI 2965
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: LED1の値だけから未記載の原因を追加しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: LED1のNG値とカソードはんだ異常だけから、追加の根本原因や対策を作れますか。
- Đáp: できません。ファイルには`LED1不点灯`、`測定値`、`カソード側はんだ接合/導通異常`、`対象LOTが選別済み`という内容までです。追加対策は記載されていません。 Nguồn file: KTD-2025-12-1325-DP Iris2020-C2D-A6-C9080.xlsx

## CÂU HỎI 2966
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần xác nhận lại giá trị Q6 và kết quả kiểm tra line trước khi kết luận.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Q6 pin1–3 được file định nghĩa `NG=6.63MΩ`, `OK=32.98kΩ`, FCT=`OK`, còn kiểm tra tĩnh điện trên line không bất thường, đúng không?
- Đáp: Đúng. Đây đều là kết quả được ghi trực tiếp trong báo cáo. Không được từ đó tự kết luận tĩnh điện là nguyên nhân. Nguồn file: KTD-2025-11-1244-Iris2024-C33-ISU-JIG báo NG.xlsx

## CÂU HỎI 2967
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接核对Q6的Pin1–Pin3电阻值。
- Cách hỏi: trực tiếp
- Hỏi: 文件定义的Q6 Pin1–Pin3电阻OK和NG值分别是多少？
- Đáp: `NG=6.63MΩ`，`OK=32.98kΩ`。这里的OK/NG是源文件自身明确给出的。 Nguồn file: KTD-2025-11-1244-Iris2024-C33-ISU-JIG báo NG.xlsx

## CÂU HỎI 2968
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: ISU調整時に数値と波形が変化しない過去ケースを参照している。
- Cách hỏi: tình huống
- Hỏi: このケースでは外観、Q6、FCT、静電気確認はそれぞれどう記録されていますか。
- Đáp: 外観=`異常なし`、Q6 pin1–3抵抗=`NG 6.63MΩ / OK 32.98kΩ`、FCT=`OK`、ライン静電気再確認=`異常なし` です。 Nguồn file: KTD-2025-11-1244-Iris2024-C33-ISU-JIG báo NG.xlsx

## CÂU HỎI 2969
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Có nhiều case C0350 nên kỹ sư so sánh hiện tượng và phép đo của case Speaker này.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng máy và kết quả đo điện trở trong case này là gì?
- Đáp: Khi thực hiện `U155`, Panel báo `C0350`. Kiểm tra điện trở được file định nghĩa `NG=OL`, `OK=7.5 Ω`. Nguồn file: KTD-2025-12-1332-Iris2024-C33-A2-C0350.xlsx

## CÂU HỎI 2970
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师只有电阻测量结果，报告没有更深层原因。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以根据`NG=OL、OK=7.5 Ω` 自行补充Speaker内部断线位置或修理方法吗？
- Đáp: 不可以。文件只定义该电阻测量为 `NG=OL、OK=7.5 Ω`，没有写明内部断线位置或维修对策。 Nguồn file: KTD-2025-12-1332-Iris2024-C33-A2-C0350.xlsx

## CÂU HỎI 2971
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C0350 Speakerケースの基本情報を最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 対象は `SPEAKER`、品番-Rev=`302ND45070-1`、Line=`C33-A2`、S.No=`29-04-520` ですね。
- Đáp: はい。Quantity=`1`、Supplier=`KDTHK FOR KDTVN`、Machine No.=`110C2K2US0 / 1FN5Z11533` です。 Nguồn file: KTD-2025-12-1332-Iris2024-C33-A2-C0350.xlsx
