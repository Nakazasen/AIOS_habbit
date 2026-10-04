# Mẻ 87 — Điều-tra-lỗi — Q3362–Q3391 (30 cặp)

- Ngày: 2026-10-05 ~05:33 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel/PDF case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Phục hồi: tin nhắn mẻ 87 đã được gửi vào chat lúc ~03:29 +07 và ChatGPT đã trả lời đầy đủ, nhưng task trình duyệt đóng lại giữa chừng không trả kết quả. Đã khởi động lại kiểm tra: TRƯỜNG HỢP A — kết quả đã có sẵn trong chat, thu hồi toàn văn, không gửi lại yêu cầu (tránh trùng). Không Cloudflare, không Unknown error
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ — giữ nguyên `0L`, `-`, `A1`, ô trống, số thập phân dài trong DRBFM (không tự làm tròn); giữ nguyên khác biệt filename/title block (KTD-2025-05-0536 ↔ internal `KTD-2025-5-36`; KTD-2024-10-1295 ↔ internal `KTD-2024-10-8`, Reappear rate=`0.3`); không tự gán OK/NG nơi nguồn không định nghĩa
- Điểm phân biệt case:
- KTD-2025-05-0536 (C6770, C33-A2): Q1 E-G=`1.2Ω`, E-C=`0.1Ω`, G-C=`1.2Ω`; Investigation riêng ghi Q1 short 3 cực; bảng Q1 không gán OK/NG từng giá trị; pin11=`0L` giữ nguyên (không sửa thành `OL`); pin12=`3.9kΩ`, pin13=`3.9kΩ`; Lot Q1=`RJH60T04 4N2 027`, U6 Lot=`L6491D TL447`
- KTD-2025-06-0572 (C6000, C35-A2, PWB IH 200, Quantity=`2`): Investigation ghi `Hàn giả vị trí J56`; file không ghi điều kiện rework hay đối sách lâu dài — không tự bổ sung; 作成者 và Machine No. ô trống; S.No=`69E0055D2268 - 250430-05A` và `69E0055D2974 - 250430-05A`
- KTD-2025-07-0678 (C6770, C33-A1): bật PWB IH có `âm thanh lạ`, ngoại quan=`không bất thường`; Lot Q1=`RJH60T04 532 021`, Q2=`RJH60T04 521 005`; bảng nhiệt độ Q1=`NG 61.2°C / OK 33°C`, Q2=`NG 57.6°C / OK 31°C` (nhãn NG/OK do chính bảng nhiệt độ định nghĩa); bảng Resistance/Diode không có OK/NG — không xác định linh kiện lỗi từ đó
- KTD-2025-01-0016 (C0180): Quantity giữ nguyên Raw value=`A1` (không tự sửa thành 1); Model, Item name, S.No, Supplier, Machine No., Occurrence Date ô trống; Investigation ghi Engine đã bị ghi vào máy khác `WCJ4Z99999`, QC xác nhận Line không có máy `WCJ4Z99999` — không suy diễn công đoạn gây đăng ký nhầm
- N00137687_実行.pdf: tài liệu Nhật/Trung về thực thi thay đổi thiết kế coupling cho C6610, không phải spreadsheet KTD; đã render trực tiếp vì PDF không có text layer; Change item `302ND31540-01 ⇒ 30C2G31011-01 COUPLING CLAW`; áp dụng Iris2020/Iris2024; DRBFM=`OK`, 图面确认=`OK`, 试作确认=`OK`; yêu cầu 1 ngày trial production xác nhận C6610/định hình bất thường/âm thanh lạ; PLM No.=`N00137687`
- KTD-2024-11-1537 (C7901, Iris2020 C34-A1): `Hàn giả pin3,5 YC10` / `YC10のPin3.5が未半田`; Quantity=`1`; không tự thêm điều kiện hàn lại/đối sách; S.No=`49278 3(a) 1136 / 2XD-0-4912`, Machine No.=`19X4Y22798`
- Iris2020_C6610対応_hook_fuser_release_r.xlsx: DRBFM thiết kế, không phải báo cáo KTD; tăng vật liệu `0.4mm` để giảm độ rơ (hiện vật đo=`1.0mm`); thêm dấu `△` để dễ xác nhận trạng thái lắp Fuser Unit; 品番 `302ND25490-05→302ND25491-01` và `3V2ND25490-03→3V2ND25491-01`; 通知書No.=`N00133886`; clearance=`0.20000000000000284`, 公差=`±0.2` — giữ nguyên số thập phân dài, không tự làm tròn
- KTD-2024-10-1295 (hình ảnh bất thường, Iris2020 C33-A6): RCG trước U950 có C色 ảnh xanh bất thường; MC501 cầu hàn pin17–18; file định nghĩa OK=`3M Ohm`, NG=`0.6 Ohm`; không thêm điều kiện rework; Investigation ô trống — không suy diễn nguyên nhân
- KTD-2024-11-1610 (C3200, Iris2020 C35-A1, PWB LED DRIVE ASSY): `12V5_F1` short, C7 short=`0.2 ohm`; S.No=`2XC-0-4909`, Quantity=`1`; không suy diễn cơ chế short của C7
- Màn hình trắng Iris.xlsx: file tổng hợp hiện tượng chung, không có title block KTD đầy đủ; Case No.1 Line-out vẫn tái hiện được, thay Main mới=`OK`, lắp lại Main cũ=`OK`; các case khác Line-out=`không tái hiện 3/3 lần` — không gộp thành một trạng thái tái hiện duy nhất; nhiều case xác nhận YC13 pin2 có dị vật và thao tác YC13 SATA cable làm Panel đổi trạng thái — file chỉ "phỏng đoán" là nguyên nhân, không nâng thành root cause chắc chắn; Case No.1: U1 nóng=`OK 5/5`, lạnh lần 1=`NG`, lạnh bổ sung=`OK 10/10`

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 3362
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Sau kiểm tra hộp mực thải, máy báo C6770 và kỹ sư kiểm tra Q1.
- Cách hỏi: trực tiếp
- Hỏi: Q1 được đo các giá trị E-G, E-C và G-C bao nhiêu?
- Đáp: Q1 E-G=`1.2Ω`, E-C=`0.1Ω`, G-C=`1.2Ω`; Investigation riêng ghi Q1 short 3 cực. Bảng Q1 không gán từng giá trị là OK/NG. Nguồn file: KTD-2025-05-0536-Iris2024-C33-A2-C6770.xlsx

## CÂU HỎI 3363
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看C6770案例中的U6/Q6表，需要保持特殊Raw value。
- Cách hỏi: tình huống
- Hỏi: pin11在源表中记录为什么值，可以改成OL吗？
- Đáp: pin11=`0L`。这是 **Raw value `0L`**，不能自行改成`OL`。同一表还记录pin12=`3.9kΩ`、pin13=`3.9kΩ`。 Nguồn file: KTD-2025-05-0536-Iris2024-C33-A2-C6770.xlsx

## CÂU HỎI 3364
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Q1の測定結果とLot情報を分けて確認している。
- Cách hỏi: so sánh
- Hỏi: Q1の測定結果とLotはそれぞれ何ですか。
- Đáp: Q1は三端子Short、E-G=`1.2Ω`、E-C=`0.1Ω`、G-C=`1.2Ω`。Lot=`RJH60T04 4N2 027`、U6 Lot=`L6491D TL447` です。 Nguồn file: KTD-2025-05-0536-Iris2024-C33-A2-C6770.xlsx

## CÂU HỎI 3365
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Hai board báo C6000 sau khi lắp đồ gá emty.
- Cách hỏi: xử lý sự cố
- Hỏi: File xác nhận bất thường ở vị trí nào và có cho đối sách sửa chữa không?
- Đáp: Investigation ghi `Hàn giả vị trí J56`; Quantity=`2`. File không ghi điều kiện rework hay đối sách lâu dài, nên không tự bổ sung. Nguồn file: KTD-2025-06-0572-Iris2024-C35-A2-C6000.xlsx

## CÂU HỎI 3366
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认C6000报告中的空白字段。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 作成者和Machine No.都是空白，而S.No记录了两台，对吗？
- Đáp: 对。作成者和Machine No.保持 **Raw value: ô trống**；S.No为 `69E0055D2268 - 250430-05A` 和 `69E0055D2974 - 250430-05A`。 Nguồn file: KTD-2025-06-0572-Iris2024-C35-A2-C6000.xlsx

## CÂU HỎI 3367
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C6000ケースの対象情報を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: Item、Line、Quantityは何ですか。
- Đáp: Item=`PWB IH 200 ASSY WITH SOFTWARE`、Line=`C35-A2`、Quantity=`2` です。 Nguồn file: KTD-2025-06-0572-Iris2024-C35-A2-C6000.xlsx

## CÂU HỎI 3368
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: U155 làm máy báo C6770 và PWB IH phát ra âm thanh lạ.
- Cách hỏi: tình huống
- Hỏi: File ghi hiện tượng âm thanh và ngoại quan như thế nào?
- Đáp: Khi bật PWB IH có `âm thanh lạ`; ngoại quan=`không bất thường`. Lot Q1=`RJH60T04 532 021`, Q2=`RJH60T04 521 005`. Nguồn file: KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx

## CÂU HỎI 3369
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较Q1与Q2的温度判定数据。
- Cách hỏi: so sánh
- Hỏi: Q1和Q2的NG/OK温度分别是多少？
- Đáp: Q1=`NG 61.2°C / OK 33°C`；Q2=`NG 57.6°C / OK 31°C`。这些NG/OK标签由该温度表自身定义。 Nguồn file: KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx

## CÂU HỎI 3370
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Q1/Q2の抵抗・Diode表から未記載原因を作らないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: Q1/Q2測定値から故障部品を確定できますか。
- Đáp: できません。表にはQ1/Q2のResistance/Diode値があり、例えばE-GはQ2=`30.11kΩ / 0.473`、Q1=`29.45kΩ / 0.638` ですが、この表自体にOK/NG判定はありません。 Nguồn file: KTD-2025-07-0678-Iris2024-C33-A1-C6770.xlsx

## CÂU HỎI 3371
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: File C0180 có nhiều trường title block bất thường hoặc để trống.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Quantity của file thực tế là Raw value=`A1`, không được tự sửa thành số lượng 1, đúng không?
- Đáp: Đúng. Title block ghi Line=`C34`, Quantity=`A1`; Model, Item name, S.No, Supplier, Machine No. và Occurrence Date là **Raw value: ô trống**. Nguồn file: KTD-2025-01-0016-IRIS2024-C34-C0180.xlsx

## CÂU HỎI 3372
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认C0180调查中的机器号异常记录。
- Cách hỏi: trực tiếp
- Hỏi: Investigation中记录了哪个机器号？
- Đáp: 文件记录Engine已经被写入另一台机器号 `WCJ4Z99999`；QC同时确认Line上没有机器号 `WCJ4Z99999`。 Nguồn file: KTD-2025-01-0016-IRIS2024-C34-C0180.xlsx

## CÂU HỎI 3373
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C0180とEngine登録情報の関係を慎重に扱っている。
- Cách hỏi: tình huống
- Hỏi: `WCJ4Z99999` がLineに存在しないことから、登録ミスの発生工程まで断定できますか。
- Đáp: できません。ファイルはEngineが別Machine `WCJ4Z99999` に登録済みで、QC確認ではLine上にそのMachine No.がないことまでを記載しています。 Nguồn file: KTD-2025-01-0016-IRIS2024-C34-C0180.xlsx

## CÂU HỎI 3374
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Tài liệu thực thi thay đổi thiết kế coupling cho Iris2020/Iris2024.
- Cách hỏi: so sánh
- Hỏi: Mã COUPLING CLAW trước và sau thay đổi trong N00137687 là gì?
- Đáp: Change item được ghi `302ND31540-01 ⇒ 30C2G31011-01 COUPLING CLAW`. Đối tượng áp dụng gồm Iris2020 và Iris2024 phía trên. Nguồn file: N00137687_実行.pdf

## CÂU HỎI 3375
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师执行C6610相关设计变更前，需要确认既有评价结果。
- Cách hỏi: xử lý sự cố
- Hỏi: 执行前DRBFM、图面确认和试作确认的判定是什么？
- Đáp: 首页记录DRBFM确认=`OK`，图面确认=`OK`，试作确认=`OK`。文件还要求在前述确认无问题时进行1日份试生产并确认C6610、定着不良和异常音是否发生。 Nguồn file: N00137687_実行.pdf

## CÂU HỎI 3376
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 設計変更の目的と適用対象を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: PLM No.=`N00137687`、目的はC6610対策の品質改善、対象はIris2020/Iris2024ですね。
- Đáp: はい。市場で定着圧駆動カップリング外れに伴い駆動制御が正常に行われずC6610が発生しているため、部品形状を変更する内容です。 Nguồn file: N00137687_実行.pdf

## CÂU HỎI 3377
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Iris2020 bật nguồn báo C7901.
- Cách hỏi: trực tiếp
- Hỏi: Investigation xác nhận vị trí hàn bất thường nào?
- Đáp: File ghi `Hàn giả pin3,5 YC10`; phần Nhật ghi `YC10のPin3.5が未半田`. Quantity=`1`. Nguồn file: KTD-2024-11-1537-Iris2020-C34-A1-C7901.xlsx

## CÂU HỎI 3378
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师遇到C7901，需要避免追加源文件没有的维修条件。
- Cách hỏi: tình huống
- Hỏi: 可以根据YC10 pin3、5未焊自行增加补焊条件或工序对策吗？
- Đáp: 不可以。文件只确认YC10 pin3、5假焊/未焊，没有记录补焊参数或永久对策。 Nguồn file: KTD-2024-11-1537-Iris2020-C34-A1-C7901.xlsx

## CÂU HỎI 3379
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C7901ケースのS.NoとMachine No.を比較している。
- Cách hỏi: so sánh
- Hỏi: S.NoとMachine No.は何ですか。
- Đáp: S.No=`49278 3(a) 1136 / 2XD-0-4912`、Machine No.=`19X4Y22798` です。 Nguồn file: KTD-2024-11-1537-Iris2020-C34-A1-C7901.xlsx

## CÂU HỎI 3380
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: DRBFM xem xét HOOK FUSER RELEASE R để hạn chế lệch trục gây C6610.
- Cách hỏi: xử lý sự cố
- Hỏi: File đã thay đổi HOOK FUSER RELEASE R cụ thể thế nào?
- Đáp: File ghi tăng vật liệu `0.4mm` để giảm độ rơ, trong khi độ rơ hiện vật đo được=`1.0mm`; đồng thời thêm dấu `△` để dễ xác nhận trạng thái lắp Fuser Unit. Nguồn file: Iris2020_C6610対応_hook_fuser_release_r.xlsx

## CÂU HỎI 3381
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认设计变更的部品号是否正确。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: HOOK FUSER RELEASE R有两组品号变更：`302ND25490-05→302ND25491-01`和`3V2ND25490-03→3V2ND25491-01`，对吗？
- Đáp: 对。通知书No.=`N00133886`，设计变更说明书No.=`50715、50716`。 Nguồn file: Iris2020_C6610対応_hook_fuser_release_r.xlsx

## CÂU HỎI 3382
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 設計上のクリアランス値を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 設計表のクリアランスと公差は何ですか。
- Đáp: クリアランス=`0.20000000000000284`、公差=`±0.2` と記載されています。Raw valueを勝手に丸めません。 Nguồn file: Iris2020_C6610対応_hook_fuser_release_r.xlsx

## CÂU HỎI 3383
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: RCG trước U950 xuất hiện ảnh xanh bất thường.
- Cách hỏi: tình huống
- Hỏi: File xác nhận MC501 bất thường thế nào?
- Đáp: Ngoại quan phát hiện MC501 bị cầu hàn giữa pin17 và pin18; file định nghĩa OK=`3M Ohm`, NG=`0.6 Ohm`. Nguồn file: KTD-2024-10-1295-Iris2020-C33-A6-Hình ảnh bất thường.xlsx

## CÂU HỎI 3384
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较图像现象和MC501测量结果。
- Cách hỏi: so sánh
- Hỏi: Line图像异常与MC501调查结果分别是什么？
- Đáp: Line上U950前RCG出现C色异常蓝色图像；调查发现MC501 pin17-pin18焊锡桥接，阻值定义为OK=`3M Ohm`、NG=`0.6 Ohm`。 Nguồn file: KTD-2024-10-1295-Iris2020-C33-A6-Hình ảnh bất thường.xlsx

## CÂU HỎI 3385
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: MC501ブリッジ確認後に未記載対策を追加しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: MC501 pin17-18のはんだブリッジに対して修正条件まで追加できますか。
- Đáp: できません。ファイルにはブリッジ確認とOK=`3M Ohm`、NG=`0.6 Ohm` までで、リワーク条件や恒久対策は記載されていません。 Nguồn file: KTD-2024-10-1295-Iris2020-C33-A6-Hình ảnh bất thường.xlsx

## CÂU HỎI 3386
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: C3200 phát sinh trên PWB LED DRIVE ASSY.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File xác nhận `12V5_F1` short và C7 short=`0.2 ohm`, đúng không?
- Đáp: Đúng. Model=`Iris2020`, Item=`PWB LED DRIVE ASSY`, S.No=`2XC-0-4909`, Quantity=`1`. Nguồn file: KTD-2024-11-1610-Iris2020-C35-A1-C3200.xlsx

## CÂU HỎI 3387
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认C3200的调查结果。
- Cách hỏi: trực tiếp
- Hỏi: C7和12V5_F1分别记录了什么？
- Đáp: `12V5_F1电压Short`；C7=`Short 0.2 ohm`。Machine No.为 **Raw value: ô trống**。 Nguồn file: KTD-2024-11-1610-Iris2020-C35-A1-C3200.xlsx

## CÂU HỎI 3388
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C7 Shortから未記載の内部原因を推定しないようにしている。
- Cách hỏi: tình huống
- Hỏi: C7=`0.2 ohm` Shortから、C7がShortした発生メカニズムまで特定できますか。
- Đáp: できません。ファイルは12V5_F1 ShortとC7=`0.2 ohm` Shortまでで、それ以上の原因や対策は記載していません。 Nguồn file: KTD-2024-11-1610-Iris2020-C35-A1-C3200.xlsx

## CÂU HỎI 3389
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Nhiều máy có Panel trắng khi USB Up Soft và kết quả Line-out không hoàn toàn giống nhau.
- Cách hỏi: so sánh
- Hỏi: Case No.1 và các case Line-out không tái hiện 3/3 khác nhau thế nào?
- Đáp: Case No.1 Line-out vẫn tái hiện được lỗi; thay Main mới=`OK`, lắp lại Main cũ=`OK`. Trong nhiều case khác, Line-out bật máy=`không tái hiện 3/3 lần`. File không cho phép gộp tất cả case thành một trạng thái tái hiện duy nhất. Nguồn file: Màn hình trắng Iris.xlsx

## CÂU HỎI 3390
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理白屏群发案例，需要按文件中的共同调查事实继续判断。
- Cách hỏi: xử lý sự cố
- Hỏi: 多个案例共同确认了YC13哪些现象？
- Đáp: 多个案例确认YC13 pin2内部有异物，并且操作PWB Main与Operation Unit之间的YC13 SATA cable时Panel状态会变化。文件仅"推测"该异常可能是原因，不能升级为全部案例的确定根因。 Nguồn file: Màn hình trắng Iris.xlsx

## CÂU HỎI 3391
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Case No.1のU1温度試験とYC13確認結果を正しく理解しているか確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: No.1ではU1加熱=`OK 5/5`、冷却1回目=`NG`、追加冷却=`OK 10/10`で、YC13 pin2異物を確認したという記録ですね。
- Đáp: はい。またYC13 SATA cableを操作するとPanel状態が変化し、ファイルはこの異常が原因の可能性があると判断していますが、確定原因とはしていません。 Nguồn file: Màn hình trắng Iris.xlsx
