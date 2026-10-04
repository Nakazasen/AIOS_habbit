# Mẻ 83 — Điều-tra-lỗi — Q3242–Q3271 (30 cặp)

- Ngày: 2026-10-05 ~03:07 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi đầy đủ 30 cặp ngay lần đầu (không bị cắt, không cần "tiếp tục"); đọc được đủ 10/10 file
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ — giữ nguyên `Open`, `OL`, `OlΩ`, `0L`, ô trống; không tự chuẩn hóa; OK/NG chỉ dùng khi chính file định nghĩa
- Điểm phân biệt case:
  - KTD-2025-08-0871 (C6770): filename ghi C35-A1 nhưng title block Line=`C35-A2` — giữ theo title block. Bảng Q1/Q2 chỉ có số đo, không có nhãn OK/NG: Q1 E-G/G-C/C-E=`29.1Ω / 29.1Ω / 0.1Ω`; Q2=`30.1kΩ / 61.2kΩ / 2.9kΩ` — không tự gán OK/NG
  - KTD-2025-02-0148 (C0980, UNIT LOW VOLTAGE): F401 đứt, Q402/Q403 short 3 cực; Q402 D-G=`OK 2.9MΩ / NG 1.3Ω`, D-S=`OK 8.2kΩ / NG 1.3Ω`, G-S=`OK 2.7MΩ / NG 0.2Ω`; Q403 NG=`3.5Ω / 3.3Ω / 0.3Ω` — case C0980 độc lập với các mẻ trước
  - KTD-2024-12-1696 (C6950, Iris2020, PWB IH 100): RY1 đo=`Open`, nguồn ghi OK=`1kΩ`; file **phỏng đoán** coil bên trong RY1 bị đứt — giữ đúng mức độ, không nâng thành kết luận chắc chắn
  - KTD-2025-06-0656 (F186, PWB VIDEO ASSY): Panel báo F186 khi in RCG trước U950; tờ RCG thiếu ký tự/hình ảnh, toàn bộ ảnh màu xanh; ngoại quan board không bất thường; S.No ô trống — không có kết luận linh kiện lỗi
  - KTD-2025-01-0100 (Iris2020-kaizo, PWB PANEL ASSY): U2 nóng >`75°C` → OK, lạnh <`-20°C` → NG; từ lần kiểm tra nóng/lạnh thứ `6` trở đi lỗi biến mất; mất `5.2V_OFF`; không tự kết luận U2 là root cause
  - KTD-2025-03-0341: PWB FEED DRIVE ASSY 3V2XC01030-4; không nhận size Letter tại Cassette 1; Investigation ghi RA12 dính hàn pin 5-7
  - KTD-2025-02-0140 (UNIT LOW VOLTAGE): YC10 bị kênh, thực tế=`0.9mm`, tiêu chuẩn KDTPS=`0.5mm` — không thêm nguyên nhân/cách sửa
  - KTD-2025-05-0447 (C6770, C33-A2, Quantity=`2`): Q1 short 3 pin, Lot Q1=`RJH6T04 4N2 031`, U6=`L6491D MZGY445`; file kết luận lỗi đơn phát không xu hướng (810PCS lot board / 25748PCS tổng item / 28801PCS lot 4N2 đều không Q1 NG trong EMS)
  - KTD-2025-07-0683 (Scan SITC NG, PWB CCD ASSY): 10 điểm NG (9200, 9206, 9208, 9211, 9214, 9220, 9223, 9227, 9233, 9235), ngoại quan không bất thường, tổng hợp thông tin gửi Partner
  - KTD-2025-05-0538 (C6950, PWB IH 200): YF1 đứt, Q1/Q2 short; U6 pin11 giữ nguyên hai cách ghi khác nhau `OK OlΩ / NG OL`, pin12=`OK 236kΩ / NG 3.2Ω` — không tự chuẩn hoá; file ghi liên lạc Partner xác nhận lịch sử sản xuất
- Không thêm đối sách ngoài file cho F186, RA12, SITC NG, YC10 hay các case C6770/C6950; không suy ra nguyên nhân sâu của Q1/Q2 short từ bảng điện trở

---

## CÂU HỎI 3242
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C0980 và kỹ sư kiểm tra Q402/Q403.
- Cách hỏi: trực tiếp
- Hỏi: File ghi F401, Q402 và Q403 bất thường thế nào?
- Đáp: F401 bị đứt; Q402 và Q403 short cả 3 cực với nhau. Nguồn file: KTD-2025-02-0148-Iris2024-C34-A1-C0980.xlsx

## CÂU HỎI 3243
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师遇到C0980，需要查看Q402的OK/NG阻值。
- Cách hỏi: tình huống
- Hỏi: Q402的D-G、D-S、G-S分别怎样定义OK/NG？
- Đáp: D-G=`OK 2.9MΩ / NG 1.3Ω`；D-S=`OK 8.2kΩ / NG 1.3Ω`；G-S=`OK 2.7MΩ / NG 0.2Ω`。 Nguồn file: KTD-2025-02-0148-Iris2024-C34-A1-C0980.xlsx

## CÂU HỎI 3244
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Q402とQ403のNG抵抗値を比較している。
- Cách hỏi: so sánh
- Hỏi: D-G、D-S、G-SのNG値はQ402とQ403でどう違いますか。
- Đáp: Q402=`1.3Ω / 1.3Ω / 0.2Ω`、Q403=`3.5Ω / 3.3Ω / 0.3Ω` です。 Nguồn file: KTD-2025-02-0148-Iris2024-C34-A1-C0980.xlsx

## CÂU HỎI 3245
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: C6950 phát sinh cùng YF1 đứt và Q1/Q2 short.
- Cách hỏi: xử lý sự cố
- Hỏi: Có thể tự suy ra nguyên nhân sâu hơn của Q1/Q2 short từ bảng điện trở không?
- Đáp: Không. File ghi YF1 đứt, Q1/Q2 short và các giá trị đo; đồng thời liên lạc Partner để xác nhận lịch sử sản xuất và hướng điều tra thêm. Không có root cause sâu hơn trong file. Nguồn file: KTD-2025-05-0538-Iris2024-C35-A1- C6950.xlsx

## CÂU HỎI 3246
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认Q1/Q2的电阻判定是否读对。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Q1 C-G和C-E都是 `OK 0.7MΩ / NG 0.2Ω`，Q2 C-E=`OK 230kΩ / NG 0.3Ω`，对吗？
- Đáp: 对。Q1 G-E=`OK 30kΩ / NG 0.2Ω`；Q2 C-G=`OK 230kΩ / NG 19Ω`、G-E=`OK 30kΩ / NG 19Ω`。 Nguồn file: KTD-2025-05-0538-Iris2024-C35-A1- C6950.xlsx

## CÂU HỎI 3247
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: U6の特殊表記を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: U6 pin11とpin12のOK/NG値は何ですか。
- Đáp: pin11=`OK OlΩ / NG OL`、pin12=`OK 236kΩ / NG 3.2Ω` です。`OlΩ` と `OL` はソース表記のまま保持します。 Nguồn file: KTD-2025-05-0538-Iris2024-C35-A1- C6950.xlsx

## CÂU HỎI 3248
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: RCG trước U950 xuất hiện lỗi F186.
- Cách hỏi: tình huống
- Hỏi: Khi F186 xảy ra, tờ RCG và ngoại quan board được ghi thế nào?
- Đáp: Tờ RCG bị thiếu ký tự và hình ảnh, toàn bộ tờ ảnh bị màu xanh; ngoại quan bản mạch=`không bất thường`. Nguồn file: KTD-2025-06-0656-Iris2024-C33-A6-F186.xlsx

## CÂU HỎI 3249
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师区分画面错误码与RCG图像异常。
- Cách hỏi: so sánh
- Hỏi: Line发生现象和调查中的图像现象分别是什么？
- Đáp: Line上打印U950前RCG时Panel显示 `F186`；调查中RCG显示字符/图像不完整，而且整张图像为蓝色。 Nguồn file: KTD-2025-06-0656-Iris2024-C33-A6-F186.xlsx

## CÂU HỎI 3250
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: F186と青色画像だけから未記載の原因部品を作らないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: このファイルから故障部品や交換対策を特定できますか。
- Đáp: できません。記載は `F186`、RCG文字・画像不足、画像全体が青色、基板外観異常なしまでです。原因部品や対策は記載されていません。 Nguồn file: KTD-2025-06-0656-Iris2024-C33-A6-F186.xlsx

## CÂU HỎI 3251
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Cassette 1 không nhận biết được giấy Letter.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File ghi RA12 dính hàn pin `5-7`, đối tượng là PWB FEED DRIVE ASSY, đúng không?
- Đáp: Đúng. Item code-Rev=`3V2XC01030-4`, S.No=`2XC-0-5314`, Line=`C35-A6`, Quantity=`1`. Nguồn file: KTD-2025-03-0341-Iris2024-C35-A6-Không nhận biết size giấy.xlsx

## CÂU HỎI 3252
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认纸张尺寸识别不良的调查结果。
- Cách hỏi: trực tiếp
- Hỏi: 文件确认哪个部品的哪些pin发生焊锡桥接？
- Đáp: `RA12` 的 pin `5-7` 发生焊锡桥接。 Nguồn file: KTD-2025-03-0341-Iris2024-C35-A6-Không nhận biết size giấy.xlsx

## CÂU HỎI 3253
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 発生現象と調査結果を区別している。
- Cách hỏi: tình huống
- Hỏi: Cassette 1でLetterサイズを認識しない場合、この報告では何が確認されていますか。
- Đáp: 発生現象は `Cassette 1でLetterサイズを認識しない`、調査結果は `RA12 pin5-7のはんだブリッジ` です。 Nguồn file: KTD-2025-03-0341-Iris2024-C35-A6-Không nhận biết size giấy.xlsx

## CÂU HỎI 3254
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Filename ghi C35-A1 nhưng title block bên trong cần được ưu tiên.
- Cách hỏi: so sánh
- Hỏi: Line trong filename và title block khác nhau thế nào?
- Đáp: Filename có `C35-A1`, nhưng title block bên trong ghi Line=`C35-A2`. Khi dùng dữ liệu phải giữ Line=`C35-A2` theo nội dung file. Nguồn file: KTD-2025-08-0871-Iris2024-C35-A1-C6770.xlsx

## CÂU HỎI 3255
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看Q1/Q2电阻表，但表格没有OK/NG列。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以把Q1/Q2的电阻值自行标成OK或NG吗？
- Đáp: 不可以。表格只记录Q1：E-G=`29.1Ω`、G-C=`29.1Ω`、C-E=`0.1Ω`；Q2：`30.1kΩ / 61.2kΩ / 2.9kΩ`。调查栏另外写Q1 Short，但表格本身没有OK/NG判定。 Nguồn file: KTD-2025-08-0871-Iris2024-C35-A1-C6770.xlsx

## CÂU HỎI 3256
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C6770ケースの調査内容を再確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 外観異常なし、YF1=`OK`、Q1 Short、Q1 Lot=`RJH 60T04 4D2 001` ですね。
- Đáp: はい。S.No=`69D0056C4061`、Quantity=`1` です。 Nguồn file: KTD-2025-08-0871-Iris2024-C35-A1-C6770.xlsx

## CÂU HỎI 3257
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Scan SITC-2 báo nhiều điểm NG.
- Cách hỏi: trực tiếp
- Hỏi: Những điểm NG nào được Panel hiển thị?
- Đáp: `9200, 9206, 9208, 9211, 9214, 9220, 9223, 9227, 9233, 9235`. Nguồn file: KTD-2025-07-0683-Iris2024-C34-A6-Scan SITC NG.xlsx

## CÂU HỎI 3258
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师遇到多个SITC NG点，但外观检查没有发现异常。
- Cách hỏi: tình huống
- Hỏi: 调查结果和后续行动是什么？
- Đáp: 外观检查=`无异常`；后续为 `汇总信息并联系Partner`。文件没有记录具体故障部品。 Nguồn file: KTD-2025-07-0683-Iris2024-C34-A6-Scan SITC NG.xlsx

## CÂU HỎI 3259
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: NG点の多さと原因確定の有無を比較している。
- Cách hỏi: so sánh
- Hỏi: 10個のNG点が出ていますが、原因部品は特定されていますか。
- Đáp: いいえ。NG点は10個記録されていますが、外観は異常なしで、対応はPartnerへの情報連絡までです。 Nguồn file: KTD-2025-07-0683-Iris2024-C34-A6-Scan SITC NG.xlsx

## CÂU HỎI 3260
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: C6950 phát sinh và RY1 đo Open.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi giá trị RY1 và kết luận ở mức nào?
- Đáp: Điện trở coil Relay RY1 đo=`Open`, trong khi nguồn ghi OK=`1kΩ`. File **phỏng đoán** coil bên trong RY1 bị đứt; không phải mô tả ở mức chắc chắn hơn. Nguồn file: KTD-2024-12-1696-Iris2020-C34-C6950 RL1.xlsx

## CÂU HỎI 3261
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认RY1的测量与推测是否区分正确。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: RY1实测=`Open`，文件给出的正常值是`1kΩ`，并"推测"内部coil断线，对吗？
- Đáp: 对。外观检查另外记录为 `无异常`。 Nguồn file: KTD-2024-12-1696-Iris2020-C34-C6950 RL1.xlsx

## CÂU HỎI 3262
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: RY1ケースの対象情報を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: Model、Item、S.No、Lineは何ですか。
- Đáp: Model=`Iris2020`、Item=`PWB IH 100 ASSY WITH SOFTWARE`、S.No=`62J004XK7611`、Line=`C34-A1` です。 Nguồn file: KTD-2024-12-1696-Iris2020-C34-C6950 RL1.xlsx

## CÂU HỎI 3263
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: YC10 bị kênh và kỹ sư cần so với tiêu chuẩn KDTPS.
- Cách hỏi: tình huống
- Hỏi: Giá trị thực tế và tiêu chuẩn được ghi bao nhiêu?
- Đáp: YC10 bị kênh=`0.9mm`; tiêu chuẩn KDTPS=`0.5mm`. Nguồn file: KTD-2025-02-0140-Iris2024-C35-Hontai1-Kênh chân connector.xlsx

## CÂU HỎI 3264
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较Connector浮起实测值和标准值。
- Cách hỏi: so sánh
- Hỏi: YC10的实际浮起量与KDTPS标准分别是多少？
- Đáp: 实际值=`0.9mm`；KDTPS标准=`0.5mm`。 Nguồn file: KTD-2025-02-0140-Iris2024-C35-Hontai1-Kênh chân connector.xlsx

## CÂU HỎI 3265
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: YC10浮き量だけから未記載の原因を作らないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: `0.9mm` 浮きという結果から発生原因や修理方法まで追加できますか。
- Đáp: できません。ファイルは実測=`0.9mm`、KDTPS標準=`0.5mm` までで、発生原因や対策は記載していません。 Nguồn file: KTD-2025-02-0140-Iris2024-C35-Hontai1-Kênh chân connector.xlsx

## CÂU HỎI 3266
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Empty TonerBox jig làm Panel báo C6770 và file có lịch sử sản xuất chi tiết.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Q1 bị short 3 pin, Lot Q1=`RJH6T04 4N2 031`, Lot U6=`L6491D MZGY445`, đúng không?
- Đáp: Đúng. Quantity=`2`, S.No=`69D0053B0428`, Line=`C33-A2`. Nguồn file: KTD-2025-05-0447-Iris2024-C33-A2-C6770.xlsx

## CÂU HỎI 3267
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认Q1的OK/NG电阻数据。
- Cách hỏi: trực tiếp
- Hỏi: Q1的C-G、G-E、E-C分别怎样定义OK/NG？
- Đáp: C-G=`OK 61.56kΩ / NG 170.5Ω`；G-E=`OK 30.09kΩ / NG 170.5Ω`；E-C=`OK 3.9kΩ / NG 0.2Ω`。 Nguồn file: KTD-2025-05-0447-Iris2024-C33-A2-C6770.xlsx

## CÂU HỎI 3268
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 現品不良とEMS生産履歴を比較している。
- Cách hỏi: tình huống
- Hỏi: Q1 Shortが1件出た一方で、EMS履歴はどう記載されていますか。
- Đáp: 対象Lotは `810PCS` 生産で工程内Q1不良なし、対象品番は合計 `25748PCS` 生産でQ1不良なし、Q1 LOT=`4N2` は `28801PCS` 投入でEMS工程内不良なしです。ファイルは `単発不良・不良傾向なし` と判定しています。 Nguồn file: KTD-2025-05-0447-Iris2024-C33-A2-C6770.xlsx

## CÂU HỎI 3269
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Màn hình không sáng và kỹ sư thử nhiệt U2.
- Cách hỏi: so sánh
- Hỏi: Kết quả làm nóng và làm lạnh U2 khác nhau thế nào?
- Đáp: Làm nóng U2 ở nhiệt độ trên `75°C` → `OK`; làm lạnh U2 ở nhiệt độ dưới `-20°C` → `NG`. File còn ghi mất điện áp tín hiệu `5.2V_OFF`. Nguồn file: KTD-2025-01-0100-Iris2020-kaizo-C35-A1-Màn hình không sáng.xlsx

## CÂU HỎI 3270
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师做U2冷热测试后，故障状态发生变化。
- Cách hỏi: xử lý sự cố
- Hỏi: 第6次以后文件记录了什么？可以直接把U2写成确定根因吗？
- Đáp: 文件记录从第 `6` 次冷热检查以后，故障状态消失。虽然U2加热>`75°C`=`OK`、冷却<`-20°C`=`NG`，但文件没有明确写"U2为确定根因"，因此不自行升级结论。 Nguồn file: KTD-2025-01-0100-Iris2020-kaizo-C35-A1-Màn hình không sáng.xlsx

## CÂU HỎI 3271
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Iris2020-kaizoケースの基本情報と温度条件を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Model=`Iris2020-kaizo`、Item=`PWB PANEL ASSY WITH SOFTWARE`、U2加熱>`75°C`でOK、冷却<`-20°C`でNGですね。
- Đáp: はい。S.No=`2XD-0-5103`、Line=`C35-A1`、Machine No.は **Raw value: ô trống** です。 Nguồn file: KTD-2025-01-0100-Iris2020-kaizo-C35-A1-Màn hình không sáng.xlsx
