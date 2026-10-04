# Mẻ 81 — Điều-tra-lỗi — 27 cặp (Q3182–Q3205, Q3209–Q3211; Q3206–Q3208 BỎ QUA)

- Ngày: 2026-10-05 ~02:56 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Đặc biệt: đọc được **9/10 file**; `信号 7303.xlsx` (XLSX gốc ~668349 bytes, chỉ có Sheet1, không đọc được dữ liệu ô) → **Q3206–Q3208 bỏ qua, không bịa dữ liệu** (đúng quy tắc)
- Không sự cố khác: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Phân bố 27 cặp đã sinh: vi=9 / zh=9 / ja=9
- Cách hỏi: tiếp tục đúng chu kỳ 5 nhãn (dùng đúng nhãn đầy đủ "hỏi ngược kiểm tra hiểu"); riêng 3 vị trí Q3206–Q3208 không có câu vì nguồn không đọc được
- Quy tắc Raw value: tuân thủ — giữ nguyên `OL`, `OlΩ`, `0.1`, ô trống, `0/600 pcs NG`; không tự chuẩn hóa; OK/NG chỉ dùng khi chính file định nghĩa
- Điểm phân biệt case:
  - KTD-2024-09-1192: filename ghi Iris 2024 nhưng title block Model=`IRIS 2020` — giữ theo title block; Item=`SENSOR OPT.`; cassette có giấy nhưng máy báo không có giấy; pin Vout nghiêng; QC line lọc `2/600pcs NG`, KTĐ lọc `0/600 pcs NG` (giữ riêng hai kết quả, không gộp)
  - KTD-2025-04-0364 (C6950): C65 hỏng, chân C65 bong và pattern đứt do ngoại lực; C65=`OL`, YF2=`0.2` (không gán OK/NG)
  - KTD-2025-07-0764 (C6770): ngoại quan không bất thường, YF1=`OK`, Q1 Short, Lot Q1=`RJH 60T04 4D2 002`; bảng Q1/Q2 chỉ ghi số đo, không gán OK/NG
  - KTD-2025-03-0239 (C0980): Aging báo "An error has Occurred ( Error 1）", OFF/ON → C0980; F401 đứt, Q402/Q403 short ba cực; bảng OK/NG do file định nghĩa
  - KTD-2025-06-0570 (C6950): YF1 đứt, Q1/Q2 short; bảng OK/NG; U6 pin11=OK `OlΩ`/NG `OL` (giữ nguyên hai cách ghi)
  - KTD-2025-10-1024 (JAM4012): tín hiệu CAS2_FEED_CL từ U2 ra bất thường — không suy diễn U2 hỏng
  - KTD-2026-06-0613 (Tablet xước): tiêu chuẩn `0.03 ≤ W ≤ 0.1mm`, `L < 15mm`, `< 5 line`; STT2 mặt ngoài=`OK`, STT3 và STT4 mặt ngoài=`NG`
  - KTD-2025-12-1398: Investigation=`Bong pin 2 YC1`; Reappear rate giữ Raw value `0.1`, không quy đổi %
  - KTD-2024-5 (WLAN biến dạng): A6 có thao tác cắm NETWORK nhưng không có thao tác kiểm tra NETWORK; dù biến dạng vẫn kết nối được; ICT=`NG`; không suy diễn A6 là nguyên nhân
- Không suy diễn YC1 bong, CAS2_FEED_CL bất thường, NETWORK connector biến dạng hay tablet xước thành nguyên nhân/đối sách ngoài nguồn

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 3182
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C6770 sau khi lắp đồ gá empty và kỹ sư kiểm tra Q1.
- Cách hỏi: trực tiếp
- Hỏi: File ghi kết quả ngoại quan, YF1 và Q1 như thế nào?
- Đáp: Ngoại quan=`không bất thường`; cầu chì YF1=`OK`; Q1=`Short`. Lot Q1=`RJH 60T04 4D2 002`. Nguồn file: KTD-2025-07-0764-Iris2024-C33-A1-C6770.xlsx

## CÂU HỎI 3183
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看C6770案例中的Q1/Q2电阻数据。
- Cách hỏi: tình huống
- Hỏi: Q1和Q2的E-G、G-C、C-E分别是多少？
- Đáp: Q1：E-G=`122.9Ω`、G-C=`122.9Ω`、C-E=`0.1Ω`；Q2：E-G=`29.4kΩ`、G-C=`61.18kΩ`、C-E=`3.897kΩ`。表格没有给这些值标注OK/NG。 Nguồn file: KTD-2025-07-0764-Iris2024-C33-A1-C6770.xlsx

## CÂU HỎI 3184
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Q1 Shortという調査結果と抵抗表の扱いを区別している。
- Cách hỏi: so sánh
- Hỏi: Q1の調査結論と抵抗表の判定情報はどう違いますか。
- Đáp: 調査欄には `Q1 Short` と明記されています。一方、抵抗表はQ1/Q2の数値だけで、個別のOK/NG判定はありません。 Nguồn file: KTD-2025-07-0764-Iris2024-C33-A1-C6770.xlsx

## CÂU HỎI 3185
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C6950 và kiểm tra thấy C65 bị hư hỏng cơ khí.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi C65 và pattern bị hỏng như thế nào?
- Đáp: Ngoại quan thấy tụ C65 bị hỏng; phần chân pin C65 bị bong và pattern bị đứt do ngoại lực. Bảng điện trở ghi C65=`OL`, YF2=`0.2`. Nguồn file: KTD-2025-04-0364-Iris2024-C34-A1-C6950.xlsx

## CÂU HỎI 3186
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认C65测量表是否定义了OK/NG。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: C65=`OL`、YF2=`0.2`只是源表测量值，没有单独OK/NG标签，对吗？
- Đáp: 对。不能自行给这两个数值增加OK/NG判定；文件另外明确记录C65受外力造成pin剥离和pattern断线。 Nguồn file: KTD-2025-04-0364-Iris2024-C34-A1-C6950.xlsx

## CÂU HỎI 3187
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C6950ケースの対象情報を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: Item、S.No、Machine No.は何ですか。
- Đáp: Item=`PWB IH 200 ASSY WITH SOFTWARE`、S.No=`69E0052A3189`、Machine No.=`110C2M3UT0- 1FX5402358` です。 Nguồn file: KTD-2025-04-0364-Iris2024-C34-A1-C6950.xlsx

## CÂU HỎI 3188
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Filename ghi Iris 2024 nhưng kỹ sư cần giữ đúng title block.
- Cách hỏi: tình huống
- Hỏi: Model thực tế và hiện tượng của case cassette này là gì?
- Đáp: Title block ghi Model=`IRIS 2020`, không phải Iris2024. Hiện tượng là cassette có giấy nhưng máy báo không có giấy. Nguồn file: KTD-2024-09-1192-Iris 2024 cassette báo không có giấy.xlsx

## CÂU HỎI 3189
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较两次筛选结果。
- Cách hỏi: so sánh
- Hỏi: QC在线筛选和KTĐ筛选结果有什么不同？
- Đáp: QC在线筛选=`2/600pcs NG`；KTĐ筛选=`0/600 pcs NG`。保持源文件中的两个结果，不重新计算或合并。 Nguồn file: KTD-2024-09-1192-Iris 2024 cassette báo không có giấy.xlsx

## CÂU HỎI 3190
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Vout pinの異常から未記載の修理方法を追加しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: Vout pin異常に対してConnector交換などの対策を追加できますか。
- Đáp: できません。ファイルにある確認結果は `Vout信号pinが斜めになり、connector外側へ出ている`、選別=`2/600pcs NG` と `0/600pcs NG` までです。 Nguồn file: KTD-2024-09-1192-Iris 2024 cassette báo không có giấy.xlsx

## CÂU HỎI 3191
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Cổng WLAN/NETWORK biến dạng nhưng vẫn có thể kết nối.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File ghi connector biến dạng nhưng vẫn kết nối được, và A6 có thao tác cắm NETWORK nhưng không kiểm tra NETWORK, đúng không?
- Đáp: Đúng. File còn ghi công đoạn hoàn thiện có hạng mục xác nhận cổng NETWORK không biến dạng. Nguồn file: KTD-2024-5_Iris2020_C34_A11.2 Cong WLAN bien dang.xlsx

## CÂU HỎI 3192
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认ICT结果和控制位置。
- Cách hỏi: trực tiếp
- Hỏi: ICT结果以及ICT控制的部品位置是什么？
- Đáp: 文件记录 `ICT NG`；ICT对 `YC5、YC6` 位置进行short/open控制。 Nguồn file: KTD-2024-5_Iris2020_C34_A11.2 Cong WLAN bien dang.xlsx

## CÂU HỎI 3193
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Network connector変形がどの工程で発生したかを慎重に扱っている。
- Cách hỏi: tình huống
- Hỏi: このファイルだけでA6作業が変形原因だったと断定できますか。
- Đáp: できません。A6でNETWORK接続作業があること、変形状態でも接続できたこと、ICT NGおよびYC5/YC6 short/open管理が記載されていますが、発生原因の確定記載はありません。 Nguồn file: KTD-2024-5_Iris2020_C34_A11.2 Cong WLAN bien dang.xlsx

## CÂU HỎI 3194
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Tablet bị xước và kỹ sư đối chiếu tiêu chuẩn đánh giá trong báo cáo.
- Cách hỏi: so sánh
- Hỏi: Tiêu chuẩn về chiều rộng, chiều dài và số line xước được ghi thế nào?
- Đáp: Tiêu chuẩn nguồn là `0.03 ≤ W ≤ 0.1mm`, `L < 15mm`, `< 5 line`, trong đó W là chiều rộng và L là chiều dài. Nguồn file: KTD-2026-06-0613-Iris2024-C34-operation-Tablet xước.xlsx

## CÂU HỎI 3195
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看照片表中的明确判定。
- Cách hỏi: xử lý sự cố
- Hỏi: 表中哪些外侧照片明确标为OK或NG？
- Đáp: STT=`2`、位置=`Mặt ngoài` 被标为 `OK`；STT=`3` 和 `4`、位置均为 `Mặt ngoài`，被标为 `NG`。其它未显示判定的行不自行补充。 Nguồn file: KTD-2026-06-0613-Iris2024-C34-operation-Tablet xước.xlsx

## CÂU HỎI 3196
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Tablet傷ケースの空欄項目を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Quantity=`6` で、S.NoとMachine No.は空欄ですね。
- Đáp: はい。S.NoとMachine No.は **Raw value: ô trống**。Item=`TABLET OPERATION`、Line=`C34-operation` です。 Nguồn file: KTD-2026-06-0613-Iris2024-C34-operation-Tablet xước.xlsx

## CÂU HỎI 3197
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Aging báo Error 1, sau OFF/ON chuyển thành C0980.
- Cách hỏi: trực tiếp
- Hỏi: Investigation chính ghi những bất thường nào?
- Đáp: File ghi F401 bị đứt, ngoại quan không bất thường, Q402 và Q403 short cả 3 cực với nhau. Nguồn file: KTD-2025-03-0239-Iris2024-C35-A7-C0980.xlsx

## CÂU HỎI 3198
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理Q402/Q403三端Short，需要查看源文件定义的电阻。
- Cách hỏi: tình huống
- Hỏi: Q402和Q403的D-G、D-S、G-S OK/NG值分别是多少？
- Đáp: Q402：D-G=`OK 2.9MΩ / NG 1.3Ω`、D-S=`OK 8.2kΩ / NG 1.3Ω`、G-S=`OK 2.7MΩ / NG 0.2Ω`；Q403对应为 NG=`3.2Ω / 3.2Ω / 0.3Ω`，OK值同样为 `2.9MΩ / 8.2kΩ / 2.7MΩ`。 Nguồn file: KTD-2025-03-0239-Iris2024-C35-A7-C0980.xlsx

## CÂU HỎI 3199
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Aging中の最初の表示とOFF/ON後の表示を比較している。
- Cách hỏi: so sánh
- Hỏi: エラー表示はOFF/ON前後でどう変わりましたか。
- Đáp: Aging中は `"An error has Occurred ( Error 1）"`、電源OFF/ON後は `C0980` を表示しました。 Nguồn file: KTD-2025-03-0239-Iris2024-C35-A7-C0980.xlsx

## CÂU HỎI 3200
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: C6950 phát sinh cùng YF1 đứt và Q1/Q2 short.
- Cách hỏi: xử lý sự cố
- Hỏi: Q1 và Q2 được file định nghĩa OK/NG thế nào?
- Đáp: Q1: C-G=`OK 0.7MΩ / NG 0.2Ω`, C-E=`OK 0.7MΩ / NG 0.2Ω`, G-E=`OK 30kΩ / NG 0.2Ω`. Q2: C-G=`OK 230kΩ / NG 19Ω`, C-E=`OK 230kΩ / NG 0.3Ω`, G-E=`OK 30kΩ / NG 19Ω`. Nguồn file: KTD-2025-06-0570-Iris2024-C34-A1-C6950.xlsx

## CÂU HỎI 3201
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师核对U6的特殊阻值表示。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: U6 pin11在源表中是OK=`OlΩ`、NG=`OL`，不能自动统一写法，对吗？
- Đáp: 对。必须保留源文件的两种原始表示；另外pin12是 OK=`236kΩ`、NG=`3.2Ω`。 Nguồn file: KTD-2025-06-0570-Iris2024-C34-A1-C6950.xlsx

## CÂU HỎI 3202
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C6950ケースの主要調査結果を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: YF1、Q1、Q2について何が確認されていますか。
- Đáp: `YF1断線`、`Q1 Short`、`Q2 Short` と記載されています。Machine No.は **Raw value: ô trống** です。 Nguồn file: KTD-2025-06-0570-Iris2024-C34-A1-C6950.xlsx

## CÂU HỎI 3203
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: In RCG Color Regist thì Panel báo JAM4012.
- Cách hỏi: tình huống
- Hỏi: File ghi kết quả ngoại quan và tín hiệu CAS2_FEED_CL như thế nào?
- Đáp: Ngoại quan=`không bất thường`; kiểm tra tín hiệu `CAS2_FEED_CL` từ linh kiện U2 ra=`bất thường`. Nguồn file: KTD-2025-10-1024-Iris2024-C33-A8.4-JAM4012.xlsx

## CÂU HỎI 3204
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师区分机器现象与U2信号调查结果。
- Cách hỏi: so sánh
- Hỏi: Line现象和调查结果分别是什么？
- Đáp: Line现象是打印RCG Color Regist时Panel显示 `JAM4012`；调查结果是外观无异常，但来自U2的 `CAS2_FEED_CL` 信号异常。 Nguồn file: KTD-2025-10-1024-Iris2024-C33-A8.4-JAM4012.xlsx

## CÂU HỎI 3205
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: U2信号異常だけから原因部品を断定しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: CAS2_FEED_CL信号異常からU2故障や交換対策まで追加できますか。
- Đáp: できません。ファイルにはU2からのCAS2_FEED_CL信号異常と外観異常なしまでで、U2故障確定や交換対策は記載されていません。 Nguồn file: KTD-2025-10-1024-Iris2024-C33-A8.4-JAM4012.xlsx

### Q3206–Q3208 — BỎ QUA (không đọc được nguồn)

File `信号 7303.xlsx` (XLSX gốc ~668349 bytes, chỉ có Sheet1, không đọc được dữ liệu ô) → không xác minh được nội dung → **bỏ qua Q3206–Q3208, không sinh cặp, không bịa dữ liệu**.

## CÂU HỎI 3209
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: RCG trước U950 cho hình ảnh bất thường và kỹ sư kiểm tra YC1.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng tại line và kết quả Investigation được ghi như thế nào?
- Đáp: Hiện tượng là `In hình ảnh RCG trước U950 -> hình ảnh bất thường`; Investigation ghi `Bong pin 2 YC1`. Reappear rate giữ Raw value=`0.1`. Nguồn file: KTD-2025-12-1398-Iris2024-C35-A6-Hình ảnh bất thường.xlsx

## CÂU HỎI 3210
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现YC1 pin2剥离，但文件没有更深层解析。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以根据YC1 pin2剥离自行增加发生原因或修理对策吗？
- Đáp: 不可以。文件只记录 `YC1 pin2剥离`，没有记载剥离原因或具体维修对策；Reappear rate保持原始值 `0.1`。 Nguồn file: KTD-2025-12-1398-Iris2024-C35-A6-Hình ảnh bất thường.xlsx

## CÂU HỎI 3211
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 画像異常ケースの基本情報とRaw valueを確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Item=`UNIT HIGH VOLTAGE TRANSFER`、S.No=`6T3105ZA4426`、Line=`C35-A6`、Reappear rate=`0.1` ですね。
- Đáp: はい。Machine No.=`110C2M3UT0 / 1FX5Z17423`、Quantity=`1` です。Reappear rateはRaw value `0.1` のまま保持します。 Nguồn file: KTD-2025-12-1398-Iris2024-C35-A6-Hình ảnh bất thường.xlsx
