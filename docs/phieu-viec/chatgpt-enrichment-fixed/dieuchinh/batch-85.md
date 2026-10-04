# Mẻ 85 — Điều-tra-lỗi — Q3302–Q3331 (30 cặp)

- Ngày: 2026-10-05 ~03:20 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi đầy đủ 30 cặp ngay lần đầu (không bị cắt, không cần "tiếp tục"); đọc được đủ 10/10 file
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ — giữ nguyên `-`, `0`, `NG` trong trường Machine No., ô trống, `OPEN`, `OL`; không tự gán nghĩa cho Machine No.=NG; không chuyển `-` thành 0
- Điểm phân biệt case:
  - KTD-2024-12-1752 (tablet vỡ, Iris2020, C35-Operation): Status=`tablet bị vỡ`, Investigation=`có dấu hiệu của ngoại lực`; S.No=`082-1153-G84101`; Machine No. ô trống — không có kết luận về nguồn gốc ngoại lực
  - KTD-2024-5-05xx (C525 HVU transfer NG, IRIS2020-Low model, C34-A6): RCG nhạt toàn bộ 4 màu; C525 đơn NG=`468Ω`/OK=`OL` (case độc lập với các case SPEAKER mẻ 73/80/84)
  - KTD-2024-11-1632 (Connector NG, Iris2020): YC1 bị nghiêng; Investigation chỉ ghi xác nhận thao tác ngoài line + lịch sử EMS, chưa kết luận nguyên nhân; **Machine No.=NG giữ nguyên Raw value** — không tự hiểu là một phán định kiểm tra
  - KTD-2025-03-0275 (thiếc hàn dính trên cuộn cảm L3, Iris2024 C35-Hontai): phát hiện ngoại quan; kiểm tra hàng tại line=`0/100pcs NG`; Reappear rate giữ **Raw value: -** (không chuyển thành 0)
  - KTD-2024-12-1642 (motor không quay, Iris2020 C35-ASSY5, Quantity=`4`): FT không Download=`2pcs NG step006`, FT kèm Download=`2pcs OK`; hướng xử lý là gửi EMS xác nhận lại; S.No=`2XD-0-4Y14`
  - KTD-2025-03-0315 (C0980, Iris2024 C34-A6): F401 đứt, Q402/Q403 short 3 cực; Q402 NG=`1.3Ω/1.3Ω/0.2Ω`, Q403 NG=`3.2Ω/3.2Ω/0.3Ω`; IC401 pin10=`OK 4.4kΩ / NG 2.7MΩ`, pin11=`OK 4.4kΩ / NG 24.4Ω` — case C0980 độc lập
  - KTD-2024-10-1275 (maintance front): filename nói "close" nhưng nội dung thực tế báo `"maintance front is open"` — giữ nội dung thật; 24V-GND=`103Ω` short, C303 có dấu hiệu cháy
  - KTD-2024-6 (R Cover Open, Iris2020 C35-A7, Quantity=`2`): sau khi nhập `79248313` → OK, không tái hiện; Line-out kiểm tra 15 lần đều OK; Reappear rate giữ **Raw value: 0**; Cover=`Đóng`, RCOVER_OPEN=`0V`, file ghi Không vấn đề — không suy diễn nguyên nhân từ lần báo lỗi đơn phát
  - KTD-2024-12-1707 (biến dạng linh kiện, PWB DRUM DLP CONNECT ASSY): JP11=`4 mm`, JP16=`4 mm` (OK mẫu JP4=`2.1 mm`); tổng hợp thông tin gửi Maker, không ghi nguyên nhân/cách sửa
  - Iris2024 PMT 上位机C2103调查报告20240927 (không theo title block KTD thường): RCG chỉ in ~nửa tờ A3, ảnh đen trắng; log xác nhận Color developing motor dừng; NG机=`1.1A`, OK机=`1.08A`, Iris2020 phát triển=`1.1A`, 本社判断NG机波形基本正常; 暫定対策 thay motor hiển ảnh, motor cũ gửi NCC; 原因=原因不明, 恒久対策検討中; 配線・組立 Color developing motor COL～IMAGE DRIVE PWB (YC6)=異常なし; 交換後の機械確認=OK — giữ đúng mức độ "tạm thời", không nâng thành root cause
- Không suy diễn tablet vỡ, YC1 nghiêng, L3 dính thiếc, JP11/JP16 biến dạng hay R Cover Open thành nguyên nhân sâu hơn ngoài file

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 3302
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Tablet Operation bị vỡ tại line C35-Operation.
- Cách hỏi: trực tiếp
- Hỏi: File ghi hiện tượng và kết quả Investigation thế nào?
- Đáp: Status ghi `tablet bị vỡ`; Investigation ghi `có dấu hiệu của ngoại lực`. Quantity=`1`, S.No=`082-1153-G84101`, Line=`C35-Operation`. Nguồn file: KTD-2024-12-1752-Iris2020-C35-Operation-Vỡ linh kiện.xlsx

## CÂU HỎI 3303
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现Tablet破裂有外力痕迹，但文件没有说明外力来源。
- Cách hỏi: tình huống
- Hỏi: 文件是否写明外力发生在运输、仓库还是具体生产工序？
- Đáp: 没有。文件只记录Tablet破裂和有外力痕迹，没有说明外力发生在运输、仓库或具体生产工序。 Nguồn file: KTD-2024-12-1752-Iris2020-C35-Operation-Vỡ linh kiện.xlsx

## CÂU HỎI 3304
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 入力済み項目と空欄項目を比較している。
- Cách hỏi: so sánh
- Hỏi: S.NoとMachine No.はどう記載されていますか。
- Đáp: S.No=`082-1153-G84101`、Machine No.は **Raw value: ô trống** です。Item=`TABLET OPERATION`、Quantity=`1`です。 Nguồn file: KTD-2024-12-1752-Iris2020-C35-Operation-Vỡ linh kiện.xlsx

## CÂU HỎI 3305
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: RC9 trước U950 bị nhạt toàn bộ bốn màu.
- Cách hỏi: xử lý sự cố
- Hỏi: File xác nhận gì tại C525 và giá trị đo đơn là bao nhiêu?
- Đáp: Investigation ghi `tụ C525 điện trở bất thường`; bảng đo linh kiện đơn định nghĩa C525 NG=`468Ω`, OK=`OL`. Nguồn file: KTD-2024-5-05xx_C34_IRIS2020_Hình ảnh bất thường_C525 HVU transfer NG.xlsx

## CÂU HỎI 3306
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认图像异常与C525测量之间的关系。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: RC9图像是4色全部变淡，C525单品测量由文件定义为NG=`468Ω`、OK=`OL`，对吗？
- Đáp: 对。Model=`IRIS2020-Low model`，Item=`HIGH VOLTAGE TRANSFER`，Line=`C34-A6`。 Nguồn file: KTD-2024-5-05xx_C34_IRIS2020_Hình ảnh bất thường_C525 HVU transfer NG.xlsx

## CÂU HỎI 3307
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 発生画像とC525の測定値を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 発生画像とC525の測定値は何ですか。
- Đáp: RCG画像は4色すべて薄い。C525単品は NG=`468Ω`、OK=`OL`と記載されています。 Nguồn file: KTD-2024-5-05xx_C34_IRIS2020_Hình ảnh bất thường_C525 HVU transfer NG.xlsx

## CÂU HỎI 3308
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: YC1 bị nghiêng nhưng báo cáo chưa xác định nguyên nhân.
- Cách hỏi: tình huống
- Hỏi: File ghi hiện tượng và hướng điều tra tiếp theo thế nào?
- Đáp: Status ghi `Nghiêng YC1`; Investigation ghi `Xác nhận thao tác ngoài line và lịch sử sản xuất bên EMS`; chưa có kết luận nguyên nhân. Nguồn file: KTD-2024-11-1632-Iris2020-C34-Connector NG.xlsx

## CÂU HỎI 3309
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: Machine No.字段里出现了特殊值NG。
- Cách hỏi: so sánh
- Hỏi: Machine No.=NG是否可以解释为某项检查结果NG？
- Đáp: 不可以。NG位于Machine No.字段，应作为 **Raw value: NG** 保留；文件没有说明它代表某项测量判定。 Nguồn file: KTD-2024-11-1632-Iris2020-C34-Connector NG.xlsx

## CÂU HỎI 3310
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: YC1傾きからEMS工程原因と断定しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: YC1傾きからEMS工程原因と断定できますか。
- Đáp: できません。ファイルはライン外作業とEMS生産履歴を確認すると記載しているだけで、原因確定はありません。 Nguồn file: KTD-2024-11-1632-Iris2020-C34-Connector NG.xlsx

## CÂU HỎI 3311
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Ngoại quan phát hiện thiếc hàn bám trên cuộn cảm L3.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Reappear rate của file là Raw value=-, còn kết quả kiểm tra line=0/100pcs NG, đúng không?
- Đáp: Đúng. Không chuyển `-` thành 0 hoặc một tỷ lệ khác. Status ghi phát hiện thiếc hàn trên cuộn L3. Nguồn file: KTD-2025-03-0275-Iris2024-C35-Hontai-Thiếc hàn dính trên cuộn cảm L3..xlsx

## CÂU HỎI 3312
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认L3异物案例的筛选数据。
- Cách hỏi: trực tiếp
- Hỏi: Line筛选结果和发生数量是多少？
- Đáp: Line筛选=`0/100pcs NG`；本报告Quantity=`1`。 Nguồn file: KTD-2025-03-0275-Iris2024-C35-Hontai-Thiếc hàn dính trên cuộn cảm L3..xlsx

## CÂU HỎI 3313
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: L3のはんだ付着から発生原因を推測しないようにしている。
- Cách hỏi: tình huống
- Hỏi: L3にはんだが付着していた場合、この報告から発生原因まで特定できますか。
- Đáp: できません。確認事項はL3上のはんだ付着とLine選別=`0/100pcs NG`までで、発生原因や対策は記載されていません。 Nguồn file: KTD-2025-03-0275-Iris2024-C35-Hontai-Thiếc hàn dính trên cuộn cảm L3..xlsx

## CÂU HỎI 3314
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Jig check cho thấy motor không quay và kỹ sư kiểm tra phần mềm.
- Cách hỏi: so sánh
- Hỏi: Kết quả FT khi không Download và khi có Download khác nhau thế nào?
- Đáp: FT không kèm Download=`2pcs NG step006`; FT kèm Download=`2pcs OK`. File ghi nguyên trạng là không Download mà lắp máy, và sau khi Download lại thì xác nhận đã có software motor. Nguồn file: KTD-2024-12-1642-Iris2020-C35-ASSY5-motor không quay.xlsx

## CÂU HỎI 3315
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理Motor不转，需要按文件已有流程确认。
- Cách hỏi: xử lý sự cố
- Hỏi: 文件记录的下一步动作是什么？
- Đáp: 文件记录向EMS发送信息重新确认；FT不Download=`2pcs NG step006`，FT+Download=`2pcs OK`，完成Download后重新装机确认已有Motor软件。 Nguồn file: KTD-2024-12-1642-Iris2020-C35-ASSY5-motor không quay.xlsx

## CÂU HỎI 3316
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Motor不転ケースの対象情報を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Quantity=`4`、Item=`PWB IMAGE DRIVE ASSY WITH SOFTWARE`、Line=`C35-ASSY5`ですね。
- Đáp: はい。S.No=`2XD-0-4Y14`、Machine No.は **Raw value: ô trống** です。 Nguồn file: KTD-2024-12-1642-Iris2020-C35-ASSY5-motor không quay.xlsx

## CÂU HỎI 3317
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Nhấn Connect trên PC thì máy báo C0980.
- Cách hỏi: trực tiếp
- Hỏi: Investigation chính ghi các bất thường nào?
- Đáp: File ghi `đứt cầu chì F401`; Q402 và Q403 `short 3 cực với nhau`. Nguồn file: KTD-2025-03-0315-Iris2024-C34-A6-C0980.xlsx

## CÂU HỎI 3318
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师核对Q402和Q403三组阻值。
- Cách hỏi: tình huống
- Hỏi: Q402与Q403的D-G、D-S、G-S OK/NG值分别是什么？
- Đáp: Q402：OK=`2.9MΩ / 8.2kΩ / 2.7MΩ`，NG=`1.3Ω / 1.3Ω / 0.2Ω`；Q403的OK值相同，NG=`3.2Ω / 3.2Ω / 0.3Ω`。 Nguồn file: KTD-2025-03-0315-Iris2024-C34-A6-C0980.xlsx

## CÂU HỎI 3319
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: IC401表のOK/NG値を比較している。
- Cách hỏi: so sánh
- Hỏi: IC401 pin10とpin11のOK/NG抵抗値はどう違いますか。
- Đáp: pin10=OK `4.4kΩ` / NG `2.7MΩ`、pin11=OK `4.4kΩ` / NG `24.4Ω`です。 Nguồn file: KTD-2025-03-0315-Iris2024-C34-A6-C0980.xlsx

## CÂU HỎI 3320
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Filename nói close nhưng nội dung máy thực tế báo front open.
- Cách hỏi: xử lý sự cố
- Hỏi: Hiện tượng thật và Investigation được ghi thế nào?
- Đáp: Nội dung nguồn ghi bật máy báo `"maintance front is open"`; Investigation ghi 24V short với GND=`103Ω`, C303 có dấu hiệu cháy. Nguồn file: KTD-2024-10-1275-Iris2020-C34-A1-Maintance front is close.xlsx

## CÂU HỎI 3321
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 文件名与实际现象文字不同，需要按报告内容保留。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 虽然文件名写Maintance front is close，报告实际现象是maintance front is open，对吗？
- Đáp: 对。应保留报告内容；同时确认24V-GND=`103Ω`并且C303有烧焦痕迹。 Nguồn file: KTD-2024-10-1275-Iris2020-C34-A1-Maintance front is close.xlsx

## CÂU HỎI 3322
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Front open表示と電気的確認結果を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 24V-GNDとC303について何が記載されていますか。
- Đáp: 24V-GNDは`103Ω`でShort、C303は焦げた跡があると記載されています。 Nguồn file: KTD-2024-10-1275-Iris2020-C34-A1-Maintance front is close.xlsx

## CÂU HỎI 3323
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: R Cover Open từng xuất hiện nhưng không tái hiện lại.
- Cách hỏi: tình huống
- Hỏi: Kết quả OFF/ON và kiểm tra lặp lại 15 lần thế nào?
- Đáp: Tắt/bật máy rồi nhập `79248313` → OK, không tái hiện; sau Line-out thực hiện lại thao tác `15 lần` → tất cả OK, Reappear rate là **Raw value: 0**. Nguồn file: KTD-2024-6_Iris2020 C35 A7 R Cover Open.xlsx

## CÂU HỎI 3324
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较发生时的Cover状态与后续复现结果。
- Cách hỏi: so sánh
- Hỏi: 发生时的Cover状态和RCOVER_OPEN电压是多少？
- Đáp: 发生时Cover=`Đóng`、RCOVER_OPEN=`0V`，文件写`Không vấn đề`；后续OFF/ON及Line-out15次均未再现。 Nguồn file: KTD-2024-6_Iris2020 C35 A7 R Cover Open.xlsx

## CÂU HỎI 3325
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 再現率0から原因を推測しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: Reappear rate=0なので原因なしと判断できますか。
- Đáp: できません。**Raw value: 0**、15回再現なし、RCOVER_OPEN=`0V`、Cover=`閉`という記録までで、根本原因は記載されていません。 Nguồn file: KTD-2024-6_Iris2020 C35 A7 R Cover Open.xlsx

## CÂU HỎI 3326
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: JP11 và JP16 bị biến dạng tại Hontai.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File ghi JP11=`4 mm`, JP16=`4 mm`, còn mẫu OK JP4=`2.1 mm`, đúng không?
- Đáp: Đúng. Quantity=`2`; S.No liên quan JP11=`'49443 3(a) 4446 2XD-0-4924`, JP16=`49443 3(a) 2840 2XD-0-4924`. Nguồn file: KTD-2024-12-1707-Iris2020-C35-Hontai-Biến dạng linh kiện.xlsx

## CÂU HỎI 3327
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认JP11和JP16的变形记录。
- Cách hỏi: trực tiếp
- Hỏi: JP11和JP16的记录尺寸是多少？
- Đáp: JP11=`4 mm`；JP16=`4 mm`。补充表还记录OK示例JP4=`2.1 mm`。 Nguồn file: KTD-2024-12-1707-Iris2020-C35-Hontai-Biến dạng linh kiện.xlsx

## CÂU HỎI 3328
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 変形から原因や修理方法を作らないようにしている。
- Cách hỏi: tình huống
- Hỏi: 変形が確認された場合、この報告では次の動作は何ですか。
- Đáp: 情報をまとめてMakerへ連絡することです。変形原因や修理方法は記載されていません。 Nguồn file: KTD-2024-12-1707-Iris2020-C35-Hontai-Biến dạng linh kiện.xlsx

## CÂU HỎI 3329
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Iris2024 PMT phát sinh C2103 giữa quá trình in RCG trước U950.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng ảnh và kết quả log về Color developing motor được ghi thế nào?
- Đáp: RCG chỉ in đến khoảng nửa tờ A3 và phần đã in là ảnh đen trắng. Log xác nhận Color developing motor đã dừng. Nguồn file: Iris2024 PMT 上位机C2103调查报告20240927.xlsx

## CÂU HỎI 3330
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理C2103，需要核对电流波形和既有临时措施。
- Cách hỏi: xử lý sự cố
- Hỏi: NG机与OK机的电流是多少，报告采用了什么临时处理？
- Đáp: NG机正常时=`1.1A`，OK机=`1.08A`，Iris2020开发时结果=`1.1A`；本社判断NG机波形基本正常。临时处理是更换显像Motor，旧Motor返供应商调查。 Nguồn file: Iris2024 PMT 上位机C2103调查报告20240927.xlsx

## CÂU HỎI 3331
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C2103報告書の結論と恒久対策を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 原因は原因不明、暫定対策はMotor交換、恒久対策は検討中ですね。
- Đáp: はい。さらに現像Motor COL～IMAGE DRIVE PWB (YC6)間の配線・組立状態は異常なし、交換後の機械確認はOKと記載されています。 Nguồn file: Iris2024 PMT 上位机C2103调查报告20240927.xlsx
