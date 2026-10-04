# Mẻ 84 — Điều-tra-lỗi — Q3272–Q3301 (30 cặp)

- Ngày: 2026-10-05 ~03:13 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi đầy đủ 30 cặp ngay lần đầu (không bị cắt, không cần "tiếp tục"); đọc được đủ 10/10 file
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ — giữ nguyên `OPEN`, `OL`, `NA`, ô trống, `24 oHm`, và dấu `'` đầu Machine No. (`'110C2M9JP0 / 1FT5503742`); không tự chuẩn hóa; OK/NG chỉ dùng khi chính file định nghĩa
- Điểm phân biệt case:
  - KTD-2024-10-1272 (Iris2020, file ghi báo `0980` không có chữ C): D211 hàn giả/未半田; diode=`OK 0.48V / NG 1V`, resistor=`OK OL / NG 1.3M`; điện áp D211=`OK 14.5V / NG 0V`, LLC-BIAS=`OK 13.6V / NG 0V`; IC201 pin6=`OK 14.2V / NG 8.1V`, pin8=`OK 226V / NG 207V` — case C0980 độc lập với các mẻ trước
  - KTD-2024-5-05 (C0350): filename có `C35` nhưng title block Model=`IRIS2020-Low model`, Line=`C34-A6` — giữ theo title block; SPEAKER NG, OK=`7.4Ω`/NG=`OPEN` (case độc lập với các case SPEAKER mẻ 73/80); bảng C525 riêng: NG=`468Ω`, OK=`OL`
  - KTD-2024-9-1227 (C6950, Iris2020): U6 pin4 short GND với NG=`24 oHm` (Nhật=`24 OHM`); file không ghi giá trị OK, không có đối sách — giữ nguyên, không tự bổ sung
  - KTD-2024-9-1231 (Adjustment NG, DP Iris2020, PWB DP IF ASSY, Quantity=`4`): U411 FU/ChartB scan Sheet Adjustment → Mastercompare NG; DINQ0753=`NA (không có dữ liệu)` giữ nguyên không tự diễn giải; 4 case U1 nóng/lạnh: case 1-2 đều 5/5 OK, case 3 nóng 5/5 NG + lạnh 5/5 NG, case 4 nóng 5/5 NG + lạnh 5/5 OK
  - KTD-2025-07-0786 (YC11 bị kênh, PF Iris2020, PWB PF MAIN ASSY 3V3V401010-3): file chỉ ghi vượt tiêu chuẩn với giới hạn nguồn định nghĩa `OK ≤ 0.5mm`, không có giá trị đo thực tế riêng — không tự gán số đo
  - KTD-2025-03-0316 (toner sensor lắp khó, Quantity=`245`): lỗ board bị lệch; tiêu chuẩn A=`13.4–13.6`, B=`1.6–1.8`, C/D=`6.4–6.6`, E=`1.6–1.8`, F=`13.4–13.6`, G=`15.7–15.9`; pcs1 A=`13.34`/C=`6.318`/D=`6.667`/F=`13.325`, pcs2 A=`13.319`/C=`6.33`/D=`6.674`, pcs3 A=`13.394`/C=`6.262`/D=`6.754`
  - KTD-2024-11-1588 (Marking NG, PWB IMAGE DRIVE ASSY 3V2XD01040-9): vị trí marking=`ver cũ`, tổng hợp thông tin gửi EMS; S.No và Machine No. là Raw value ô trống — không thêm vị trí marking mới/cách sửa
  - KTD-2025-02-0169 (C6930, PWB FRONT DRIVE ASSY): pin7 của YC6 hàn giả/未半田; kiểm tra thao tác Assy3-S10=`Không thấy điểm bất thường khi thao tác`; không suy diễn root cause
  - KTD-2025-05-0469 (không lên nguồn, UNIT LOW VOLTAGE): máy ON `5s` rồi sập; F401 đứt, Q402/Q403 short, IC101 pin8 bất thường; 5V tụt xuống `2.8V` rồi giảm dần; IC101 pin8=`OK 4.3kΩ / NG 45Ω`; Q402 NG=`1.3Ω/1.3Ω/0.2Ω`; Q403 NG=`3.2Ω/3.2Ω/0.3Ω`; Machine No. giữ nguyên dấu `'` đầu
  - KTD-2025-01-0109 (Connector NG, C34-HONTAI, PWB RFID ASSY): Status=`YC2 chưa tháo Cab`; Investigation chỉ ghi tổng hợp thông tin và liên lạc Partner — không có kết luận nguyên nhân/linh kiện trong file
- Không suy diễn DINQ0753=`NA`, marking ver cũ, YC6 pin7, YC11 bị kênh hoặc U6 short thành nguyên nhân sâu hơn ngoài file; không tự gán OK/NG nơi nguồn không định nghĩa

---

## CÂU HỎI 3272
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra case Connector NG tại công đoạn HONTAI.
- Cách hỏi: trực tiếp
- Hỏi: File ghi hiện tượng tại YC2 và thông tin đối tượng thế nào?
- Đáp: Status ghi `YC2 chưa tháo Cab`; Item=`PWB RFID ASSY WITH SOFTWARE`, S.No=`0-4Z12`, Line=`C34-HONTAI`, Quantity=`1`. Nguồn file: KTD-2025-01-0109-Iris2024-C34-HONTAI-Connector NG.xlsx

## CÂU HỎI 3273
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现YC2状态异常，需要确认报告已有的后续动作。
- Cách hỏi: tình huống
- Hỏi: 文件对这个Connector NG记录了什么后续调查动作？
- Đáp: 文件只记录 `汇总信息并联系Partner`。Machine No.为 **Raw value: ô trống**，没有记录具体原因或修理方法。 Nguồn file: KTD-2025-01-0109-Iris2024-C34-HONTAI-Connector NG.xlsx

## CÂU HỎI 3274
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 入力済み項目と空欄項目を比較している。
- Cách hỏi: so sánh
- Hỏi: この報告でS.NoとMachine No.はどう記載されていますか。
- Đáp: S.No=`0-4Z12`、Machine No.は **Raw value: ô trống** です。Quantity=`1` です。 Nguồn file: KTD-2025-01-0109-Iris2024-C34-HONTAI-Connector NG.xlsx

## CÂU HỎI 3275
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Iris2020 báo 0980 và kỹ sư kiểm tra D211.
- Cách hỏi: xử lý sự cố
- Hỏi: D211 được file ghi các giá trị diode, điện trở và điện áp thế nào?
- Đáp: Diode D211=`OK 0.48V / NG 1V`; resistor=`OK OL / NG 1.3M`; điện áp D211=`OK 14.5V / NG 0V`. Investigation ghi phần Việt `D211 hàn giả`, phần Nhật `D211未半田`. Nguồn file: KTD-2024-10-1272-Iris2020-C34-A1-C0980.xlsx

## CÂU HỎI 3276
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师核对D211与LLC-BIAS的电压结果。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: D211电压是OK=`14.5V`、NG=`0V`，LLC-BIAS是OK=`13.6V`、NG=`0V`，对吗？
- Đáp: 对。源文件自身明确给出了这些OK/NG标签。 Nguồn file: KTD-2024-10-1272-Iris2020-C34-A1-C0980.xlsx

## CÂU HỎI 3277
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: IC201の電圧データを直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: IC201 pin6とpin8のOK/NG電圧は何ですか。
- Đáp: pin6=`OK 14.2V / NG 8.1V`、pin8=`OK 226V / NG 207V` です。 Nguồn file: KTD-2024-10-1272-Iris2020-C34-A1-C0980.xlsx

## CÂU HỎI 3278
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: C0350 xuất hiện sau U155 và đóng Cover Waste.
- Cách hỏi: tình huống
- Hỏi: File ghi kết quả kiểm tra SPEAKER thế nào?
- Đáp: File ghi `SPEAKER NG`; điện trở OK=`7.4Ω`, điện trở NG=`OPEN`. Title block ghi Model=`IRIS2020-Low model`, Line=`C34-A6`, Quantity=`1`. Nguồn file: KTD-2024-5-05_C35_IRIS2020_C0350 .xlsx

## CÂU HỎI 3279
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较Speaker与C525单品测量。
- Cách hỏi: so sánh
- Hỏi: Speaker和C525表中的OK/NG值分别是什么？
- Đáp: Speaker：OK=`7.4Ω`、NG=`OPEN`；C525单品表：NG=`468Ω`、OK=`OL`。 Nguồn file: KTD-2024-5-05_C35_IRIS2020_C0350 .xlsx

## CÂU HỎI 3280
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: ファイル名とtitle blockのLineが異なるケースを扱っている。
- Cách hỏi: xử lý sự cố
- Hỏi: ファイル名にC35とあってもLineをC35として扱ってよいですか。
- Đáp: いいえ。title blockでは Line=`C34-A6` です。Model=`IRIS2020-Low model`、S.No=`29-04 402` をそのまま使用します。 Nguồn file: KTD-2024-5-05_C35_IRIS2020_C0350 .xlsx

## CÂU HỎI 3281
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C6950 và U6 pin4 được xác nhận short GND.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File ghi U6 pin4 short GND với NG=`24 oHm`, đúng không?
- Đáp: Đúng. Phần Nhật ghi `NG：24 OHM`; nguồn không ghi giá trị OK tương ứng, nên không tự bổ sung. Nguồn file: KTD-2024-9-1227-Iris 2020-C34-C6950.xlsx

## CÂU HỎI 3282
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认C6950案例的对象信息。
- Cách hỏi: trực tiếp
- Hỏi: Model、Item和S.No是什么？
- Đáp: Model=`Iris 2020`；Item=`PWB IH 200 ASSY WITH SOFTWARE`；S.No=`EUF0146Y3439`；Line=`C34-A3`。 Nguồn file: KTD-2024-9-1227-Iris 2020-C34-C6950.xlsx

## CÂU HỎI 3283
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: U6 pin4の測定結果と未記載情報を区別している。
- Cách hỏi: tình huống
- Hỏi: U6 pin4-GND Shortが確認された場合、この報告から内部故障メカニズムまで特定できますか。
- Đáp: できません。記載は U6 pin4-GND Short、NG=`24 oHm/24 OHM` までです。追加の原因や対策はありません。 Nguồn file: KTD-2024-9-1227-Iris 2020-C34-C6950.xlsx

## CÂU HỎI 3284
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: U411 FU/ChartB báo Mastercompare NG và file có 4 case kiểm tra nóng/lạnh U1.
- Cách hỏi: so sánh
- Hỏi: Kết quả nóng/lạnh U1 của 4 case khác nhau thế nào?
- Đáp: Case 1 và 2: nóng=`5/5 OK`, lạnh=`5/5 OK`; case 3: nóng=`5/5 NG`, lạnh=`5/5 NG`; case 4: nóng=`5/5 NG`, lạnh=`5/5 OK`. Nguồn file: KTD-2024-9-1231-DP Iris2020-C2D- Adjustment NG.xlsx

## CÂU HỎI 3285
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理Adjustment NG，需要读取DINQ0753原始状态。
- Cách hỏi: xử lý sự cố
- Hỏi: DINQ0753在主调查栏中记录为什么状态？可以自行解释其原因吗？
- Đáp: DINQ0753=`NA（没有数据）`。这是源文件记录，不能自行解释为什么无数据或把它扩展为某个部品故障。 Nguồn file: KTD-2024-9-1231-DP Iris2020-C2D- Adjustment NG.xlsx

## CÂU HỎI 3286
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 4件のAdjustment NGの基本情報を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Model=`DP Iris2020`、Item=`PWB DP IF ASSY`、Quantity=`4`、Line=`C2D` ですね。
- Đáp: はい。主現象はU411 FU/ChartBでSheet AdjustmentをScanするとPCが `Mastercompare NG` を表示することです。 Nguồn file: KTD-2024-9-1231-DP Iris2020-C2D- Adjustment NG.xlsx

## CÂU HỎI 3287
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Connector YC11 bị kênh trên PF Iris2020.
- Cách hỏi: trực tiếp
- Hỏi: Tiêu chuẩn độ kênh và số lượng lỗi được ghi thế nào?
- Đáp: File ghi độ kênh vượt tiêu chuẩn và chính nguồn định nghĩa `OK ≤ 0.5mm`; Quantity=`3`, bảng bổ sung cũng ghi `3pcs`. Nguồn file: KTD-2025-07-0786-PF Iris2020-A2D-Kênh chân connector.xlsx

## CÂU HỎI 3288
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现YC11翘起超过标准。
- Cách hỏi: tình huống
- Hỏi: 文件记录的后续动作是什么？有没有实际翘起测量值？
- Đáp: 后续为 `汇总信息并联系Partner`。文件只写超过标准 `OK ≤ 0.5mm`，没有给出具体实际测量值，因此不能自行补数值。 Nguồn file: KTD-2025-07-0786-PF Iris2020-A2D-Kênh chân connector.xlsx

## CÂU HỎI 3289
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: PF Iris2020の対象基板情報を比較確認している。
- Cách hỏi: so sánh
- Hỏi: title blockと補足表の品番・数量は一致していますか。
- Đáp: title blockは Item code-Rev=`3V3V401010-3`、Quantity=`3`。補足表は `3V3V401010 - 03`、`3pcs` と記載されています。 Nguồn file: KTD-2025-07-0786-PF Iris2020-A2D-Kênh chân connector.xlsx

## CÂU HỎI 3290
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Toner Sensor board không lắp được vào Unit và có bảng đo kích thước.
- Cách hỏi: xử lý sự cố
- Hỏi: File kết luận lý do không lắp được và Quantity là bao nhiêu?
- Đáp: File ghi `lỗ bản mạch bị lệch nên không thể lắp vào Assy`; Quantity=`245`. S.No gồm `0-5106`, `0-5210`, `0-5225`. Nguồn file: KTD-2025-03-0316-Iris2024-C35-DLP- toner sensor lắp khó.xlsx

## CÂU HỎI 3291
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师用尺寸表确认pcs1的偏差情况。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: pcs1的A=`13.34`低于标准`13.4–13.6`，C=`6.318`低于`6.4–6.6`，D=`6.667`高于`6.4–6.6`，对吗？
- Đáp: 对。pcs1的F=`13.325`也低于标准`13.4–13.6`；G=`15.79`处于标准`15.7–15.9`。 Nguồn file: KTD-2025-03-0316-Iris2024-C35-DLP- toner sensor lắp khó.xlsx

## CÂU HỎI 3292
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: pcs1～pcs3の寸法を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: pcs2とpcs3のA、C、Dの値は何ですか。
- Đáp: pcs2は A=`13.319`、C=`6.33`、D=`6.674`。pcs3は A=`13.394`、C=`6.262`、D=`6.754` です。 Nguồn file: KTD-2025-03-0316-Iris2024-C35-DLP- toner sensor lắp khó.xlsx

## CÂU HỎI 3293
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Marking sai vị trí tại ASSY3.
- Cách hỏi: tình huống
- Hỏi: Investigation ghi gì về vị trí marking và hành động tiếp theo?
- Đáp: File ghi `vị trí marking là ver cũ`; sau đó `tổng hợp thông tin gửi EMS`. Quantity=`1`. Nguồn file: KTD-2024-11-1588-Iris2020-C35-ASSY3-Marking NG.xlsx

## CÂU HỎI 3294
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较已填写信息与空白字段。
- Cách hỏi: so sánh
- Hỏi: 该报告哪些识别字段为空，哪些字段有值？
- Đáp: S.No和Machine No.都是 **Raw value: ô trống**；Item code-Rev=`3V2XD01040-9`、Line=`C35-ASSY3`、Quantity=`1`。 Nguồn file: KTD-2024-11-1588-Iris2020-C35-ASSY3-Marking NG.xlsx

## CÂU HỎI 3295
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 旧ver markingという記載から余計な対策を追加しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: markingが旧ver位置だったことから、新しいmarking位置や修正方法まで追加できますか。
- Đáp: できません。ファイルは `marking位置が旧ver` と `EMSへ情報送付` までで、新位置の数値や修正方法は記載していません。 Nguồn file: KTD-2024-11-1588-Iris2020-C35-ASSY3-Marking NG.xlsx

## CÂU HỎI 3296
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: TLBĐ báo C6930 và YC6 pin7 có bất thường hàn.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File ghi YC6 pin7 hàn giả/chưa hàn và kiểm tra thao tác Assy3-S10 không thấy bất thường, đúng không?
- Đáp: Đúng. Investigation ghi `pin7 của YC6 hàn giả / YC6のPin7未半田`; phần Assy3-S10 kết luận `Không thấy điểm bất thường khi thao tác`. Quantity=`1`. Nguồn file: KTD-2025-02-0169-Iris2024-C35-A1-C6930.xlsx

## CÂU HỎI 3297
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认C6930案例的对象信息。
- Cách hỏi: trực tiếp
- Hỏi: Item、S.No和Line是什么？
- Đáp: Item=`PWB FRONT DRIVE ASSY`；S.No=`2XD-0-5207`；Line=`C35-A1`。Machine No.为 **Raw value: ô trống**。 Nguồn file: KTD-2025-02-0169-Iris2024-C35-A1-C6930.xlsx

## CÂU HỎI 3298
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: YC6 pin7異常と作業確認結果を区別している。
- Cách hỏi: tình huống
- Hỏi: 作業確認で異常が見つからなかった場合、ライン作業が原因ではないと断定できますか。
- Đáp: 断定できません。ファイルはYC6 pin7の未半田/はんだ異常を確認し、Assy3-S10操作では `異常点なし` と記載していますが、根本原因までは記載していません。 Nguồn file: KTD-2025-02-0169-Iris2024-C35-A1-C6930.xlsx

## CÂU HỎI 3299
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy sáng màn hình 5 giây rồi sập nguồn tại A2.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng nguồn và các kết quả điện áp/linh kiện được ghi như thế nào?
- Đáp: Máy ON được `5s` rồi sập nguồn; F401 đứt, Q402/Q403 short, IC101 pin8 bất thường. Điện áp `5V` tụt xuống `2.8V` rồi giảm dần. Nguồn file: KTD-2025-05-0469-Iris2024-C34-A2-Không lên nguồn.xlsx

## CÂU HỎI 3300
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师根据源表检查IC101 pin8和Q402/Q403。
- Cách hỏi: xử lý sự cố
- Hỏi: IC101 pin8以及Q402/Q403三组阻值怎样定义OK/NG？
- Đáp: IC101 pin8=`OK 4.3kΩ / NG 45Ω`。Q402 D-G/D-S/G-S=`OK 2.9MΩ/8.2kΩ/2.7MΩ`、NG=`1.3Ω/1.3Ω/0.2Ω`；Q403的OK值相同，NG=`3.2Ω/3.2Ω/0.3Ω`。 Nguồn file: KTD-2025-05-0469-Iris2024-C34-A2-Không lên nguồn.xlsx

## CÂU HỎI 3301
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Machine No.の原文と主要測定結果を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Machine No.は先頭に`'`を含む原文で、5Vは`2.8V`まで低下、IC101 pin8はNG=`45Ω`ですね。
- Đáp: はい。Machine No.はソース上 `'110C2M9JP0 / 1FT5503742` と記載されています。先頭の`'`を勝手に削除せず保持します。 Nguồn file: KTD-2025-05-0469-Iris2024-C34-A2-Không lên nguồn.xlsx
