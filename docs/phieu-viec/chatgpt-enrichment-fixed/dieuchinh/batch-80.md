# Mẻ 80 — Điều-tra-lỗi — Q3152–Q3181 (30 cặp)

- Ngày: 2026-10-05 ~02:48 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ — giữ nguyên các ô trống, cách ghi `01` của Quantity, `na`, `0L`/`OL`/`OlΩ`; không tự chuẩn hóa; OK/NG chỉ dùng khi chính file định nghĩa
- Điểm phân biệt case:
  - KTD-2025-10-1122: filename ghi Iris2024 nhưng title block Model=`Iris2020` — giữ theo title block; Item=`THERMISTOR ASSY`, S.No=`G578`, Quantity=`8`; phát hiện nhựa rạn khi siết vít; lọc đơn 100pcs => OK (Nhật: `0/100pcs NG`); lực siết vít=`OK 0.75N`
  - KTD-2024-5_C35_IRIS2020_C0350: Model=`IRIS2020-Low model`, Item=`SPEAKER`; C0350 sau U155 và đóng Cover Waste; Stable resistance=`7.4Ω`, NG resistor=`Open`, The circuit is broken — ĐỘC LẬP với case SPEAKER C0350 mẻ 73 Q2969–2971 (NG=`OL`/OK=`7.5Ω`)
  - KTD-2025-12-1314: filename `C6760` nhưng title block Contents of defect=`C6950` — giữ nguyên cả hai mã; Status: lắp Fax bật nguồn → C6760, line-out bật lại → C6950; YF1 đứt (OK=`0.1Ω`/NG=`OL`); Q1/Q2 short, Lot Q1=`RJH60T04 542 011`, Q2=`RJH60T04 542 017`; bảng Q1/Q2/U6 không có cột OK/NG riêng (C-G=`32Ω / 42.8Ω`, G-E=`32Ω / 42.8Ω`, U6 GND-pin11=`OL`)
  - KTD-2025-07-0677: Upsoft không vào trạng thái; U1 làm nóng `NG=5/5 lần`, làm lạnh `NG=0/5 lần`; ngoại quan không bất thường; file không ghi root cause sâu hơn — không suy diễn U1
  - KTD-2025-05-0456: C6770, PWB IH 200; đường 15V1 short GND, OK=`1.5MΩ`/NG=`34Ω`; tháo U6 đo pin4–6 đơn=`34Ω`; file kết luận lỗi bên trong U6
  - KTD-2025-05-0541: Error56, UNIT HIGH VOLTAGE TRANSFER; ảnh K và tín hiệu K bất thường; Partner trả lời lỗi do IC101 (không có chi tiết trao đổi/thay thế bổ sung)
  - KTD-2025-08-0905: in RC9 ảnh đậm màu C, Y; PWB MAIN ASSY WITH SOFTWARE E (3VC2L01010-10); ngoại quan board không bất thường; không có nguyên nhân/đối sách khác trong file
  - KTD-2025-12-1353: linh kiện rơi ra trong thùng; thùng bị gập/gãy, tác động ngoại lực; không tự xác định khâu nào chịu trách nhiệm
  - KTD-2024-8: KTD=`KTD-2024-8-1016`, Model=`Iris2020`, UNIT HIGH VOLTAGE FUSER, line=`C33-A2`, Quantity=`01`; TLBĐ LCD báo C7941; 24V short GND; T101 short pin NC–ND, OK=`4.4 kΩ`/NG=`2.3Ω`
  - KTD-2024-12-1698: Model=`Iris2020`, LCD OPERATION; màn hình vòm sáng/điểm trắng (画面に白い点がある); Investigation chỉ ghi tổng hợp thông tin và liên lạc Maker

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 3152
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy không vào trạng thái Upsoft và kỹ sư thử nhiệt trên U1.
- Cách hỏi: trực tiếp
- Hỏi: Kết quả làm nóng và làm lạnh U1 được file ghi thế nào?
- Đáp: Ngoại quan không bất thường. Làm nóng U1: `NG=5/5 lần`; làm lạnh U1: `NG=0/5 lần`. File không ghi thêm root cause sâu hơn. Nguồn file: KTD-2025-07-0677-Iris2024-C33-A1-không vào trạng thái Upsoft.xlsx

## CÂU HỎI 3153
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师遇到无法进入Upsoft状态，需要比较U1冷热测试结果。
- Cách hỏi: tình huống
- Hỏi: U1加热和冷却时，故障再现结果分别是什么？
- Đáp: U1加热=`5/5次NG`；U1冷却=`0/5次NG`。外观检查=`无异常`。 Nguồn file: KTD-2025-07-0677-Iris2024-C33-A1-không vào trạng thái Upsoft.xlsx

## CÂU HỎI 3154
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: U1の温度試験結果と原因確定の有無を区別している。
- Cách hỏi: so sánh
- Hỏi: 加熱試験と冷却試験の結果から、U1故障が確定したと記載できますか。
- Đáp: 加熱=`NG 5/5回`、冷却=`NG 0/5回` ですが、ファイルにはU1を根本原因と確定する記載はありません。 Nguồn file: KTD-2025-07-0677-Iris2024-C33-A1-không vào trạng thái Upsoft.xlsx

## CÂU HỎI 3155
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: C6770 phát sinh và đường 15V1 bị short.
- Cách hỏi: xử lý sự cố
- Hỏi: File xác định 15V1 và U6 như thế nào?
- Đáp: Đường `15V1` short với GND, file định nghĩa OK=`1.5MΩ`, NG=`34Ω`. Sau khi tháo U6, pin4–6 của U6 đơn đo=`34Ω`; file kết luận `lỗi trong linh kiện U6`. Nguồn file: KTD-2025-05-0456-Iris2024-C34-A2-C6770.xlsx

## CÂU HỎI 3156
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认报告自身是否明确判定U6内部异常。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 15V1-GND为NG=`34Ω`，拆下U6后单品pin4-6也是`34Ω`，报告明确判定U6内部不良，对吗？
- Đáp: 对。文件还定义15V1-GND的OK值=`1.5MΩ`。 Nguồn file: KTD-2025-05-0456-Iris2024-C34-A2-C6770.xlsx

## CÂU HỎI 3157
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 15V1回路とU6単品の測定値を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 15V1-GNDとU6 pin4-6の測定結果は何ですか。
- Đáp: 15V1-GNDは OK=`1.5MΩ`、NG=`34Ω`。U6単品のpin4-6は `34Ω` で、ファイルはU6内部不良と記載しています。 Nguồn file: KTD-2025-05-0456-Iris2024-C34-A2-C6770.xlsx

## CÂU HỎI 3158
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Aging báo Error56 và Partner đã trả lời kết quả phân tích.
- Cách hỏi: tình huống
- Hỏi: File ghi hiện tượng ảnh/tín hiệu và kết luận của Partner thế nào?
- Đáp: Ảnh màu K bất thường, tín hiệu sóng màu K bất thường; Partner trả lời `lỗi do linh kiện IC101`. Nguồn file: KTD-2025-05-0541-Iris2024-C35-A6-Error56.xlsx

## CÂU HỎI 3159
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师区分现场确认结果和Partner结论。
- Cách hỏi: so sánh
- Hỏi: 现场确认和Partner结论分别是什么？
- Đáp: 现场确认是 `K色图像异常`、`K色信号异常`；Partner明确回复 `故障由IC101部品导致`。 Nguồn file: KTD-2025-05-0541-Iris2024-C35-A6-Error56.xlsx

## CÂU HỎI 3160
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Partnerの回答以上の対策を追加しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: IC101故障という回答から交換方法や追加対策まで記載できますか。
- Đáp: できません。ファイルにある結論は `Partner回答：IC101部品の故障` までで、具体的な交換・恒久対策は記載されていません。 Nguồn file: KTD-2025-05-0541-Iris2024-C35-A6-Error56.xlsx

## CÂU HỎI 3161
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: In RC9 xuất hiện ảnh đậm ở hai màu nhưng ngoại quan board bình thường.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File ghi ảnh đậm màu C, Y và ngoại quan board không bất thường, đúng không?
- Đáp: Đúng. Status ghi `in hình ảnh RC9 -> Hình ảnh đậm màu C, Y`; Investigation ghi `Ngoại quan bản mạch không bất thường`. Nguồn file: KTD-2025-08-0905-Iris2024-C35-A8-Hình ảnh bất thường.xlsx

## CÂU HỎI 3162
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认图像异常案例的对象板信息。
- Cách hỏi: trực tiếp
- Hỏi: 对象板的品名、品号-Rev和S.No是什么？
- Đáp: Item=`PWB MAIN ASSY WITH SOFTWARE E`；Item code-Rev=`3VC2L01010-10`；S.No=`6HY1057E7569`。Machine No.为 **Raw value: ô trống**。 Nguồn file: KTD-2025-08-0905-Iris2024-C35-A8-Hình ảnh bất thường.xlsx

## CÂU HỎI 3163
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 画像濃度異常から未記載の原因部品を作らないようにしている。
- Cách hỏi: tình huống
- Hỏi: C/Y画像が濃い場合、このファイルから原因部品を特定できますか。
- Đáp: できません。ファイルにはRC9でC/Y画像が濃いことと、基板外観異常なしまでしか記載されていません。 Nguồn file: KTD-2025-08-0905-Iris2024-C35-A8-Hình ảnh bất thường.xlsx

## CÂU HỎI 3164
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Linh kiện rơi trong thùng và thùng có dấu hiệu hư hỏng cơ khí.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng tại line và kết quả kiểm tra thùng được ghi thế nào?
- Đáp: Status ghi `Linh kiện rơi ra trong thùng`; Investigation ghi `thùng bị gập gẫy, có tác động của ngoại lực`. Nguồn file: KTD-2025-12-1353-Iris2024-C35-assy2-Bong linh kiện.xlsx

## CÂU HỎI 3165
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现包装箱受外力，但文件没有说明具体发生环节。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以自行判断外力发生在运输、仓库还是ASSY工序吗？
- Đáp: 不可以。文件只确认 `箱子弯折/破损并有外力作用`，没有写明具体发生工序或责任环节。 Nguồn file: KTD-2025-12-1353-Iris2024-C35-assy2-Bong linh kiện.xlsx

## CÂU HỎI 3166
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 空欄情報を推測で補完しないよう確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Item=`PWB MAIN ASSY WITH SOFTWARE E`、Quantity=`1` で、S.NoとMachine No.は空欄ですね。
- Đáp: はい。S.NoとMachine No.は **Raw value: ô trống**。Line=`C35-assy2` です。 Nguồn file: KTD-2025-12-1353-Iris2024-C35-assy2-Bong linh kiện.xlsx

## CÂU HỎI 3167
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Filename ghi Iris2024 nhưng kỹ sư phải dùng đúng title block bên trong.
- Cách hỏi: trực tiếp
- Hỏi: Model thực tế trong title block và thông tin đối tượng là gì?
- Đáp: Model trong title block=`Iris2020`, Item=`THERMISTOR ASSY`, item code-Rev=`302J125020-2`, S.No=`G578`, Quantity=`8`. Không đổi thành Iris2024 theo filename. Nguồn file: KTD-2025-10-1122-Iris2024-C3A-K2-.xlsx

## CÂU HỎI 3168
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: Thermistor树脂开裂后，工程师确认筛选和锁螺丝力。
- Cách hỏi: tình huống
- Hỏi: 文件记录的单品筛选结果和螺丝锁付力是多少？
- Đáp: 单品筛选 `100pcs => OK`，日文栏写 `0/100pcs NG`；螺丝锁付力确认=`OK (0.75N)`。 Nguồn file: KTD-2025-10-1122-Iris2024-C3A-K2-.xlsx

## CÂU HỎI 3169
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 発生品8pcsと100pcs選別結果を比較している。
- Cách hỏi: so sánh
- Hỏi: 報告対象数量と単品選別結果はどう記載されていますか。
- Đáp: 報告対象Quantity=`8`。単品選別は `100pcs => OK`、日本語欄では `0/100pcs NG`。ビス締め力は `OK 0.75N` です。 Nguồn file: KTD-2025-10-1122-Iris2024-C3A-K2-.xlsx

## CÂU HỎI 3170
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: TLBĐ báo C7941 và kỹ sư kiểm tra short tại UHV FUSER.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi đường nguồn và T101 bị short thế nào?
- Đáp: File ghi `24V bị Short với GND`; T101 short giữa pin `NC` và `ND`. Giá trị được file định nghĩa OK=`4.4 kΩ`, NG=`2.3Ω`. Nguồn file: KTD-2024-8-Iris2020-C33 T101 UHV FUSER SHORT .xlsx

## CÂU HỎI 3171
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认title block中的数量和Model。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Title block是Model=`Iris2020`、Quantity=`01`、Line=`C33-A2`，对吗？
- Đáp: 对。Item=`UNIT HIGH VOLTAGE FUSER`，KTD=`KTD-2024-8-1016`。Quantity保持源文件写法 `01`。 Nguồn file: KTD-2024-8-Iris2020-C33 T101 UHV FUSER SHORT .xlsx

## CÂU HỎI 3172
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C7941発生時のT101測定値を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: T101のNC-ND間のOK/NG値は何ですか。
- Đáp: OK=`4.4 kΩ`、NG=`2.3Ω` です。ファイルはNC-ND間Shortと記載しています。 Nguồn file: KTD-2024-8-Iris2020-C33 T101 UHV FUSER SHORT .xlsx

## CÂU HỎI 3173
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: LCD xuất hiện vòm sáng nhưng chưa có phân tích linh kiện.
- Cách hỏi: tình huống
- Hỏi: Hiện tượng và hành động tiếp theo trong file là gì?
- Đáp: File ghi `Màn hình hiển thị vòm sáng bất thường`; phần Nhật mô tả `画面に白い点がある`. Investigation chỉ ghi `Tổng hợp thông tin liên lạc Maker / Makerに連絡`. Nguồn file: KTD-2024-12-1698-Iris2020-C34-Operation-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3174
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较故障现象与调查完成程度。
- Cách hỏi: so sánh
- Hỏi: 文件已经确认了什么，尚未确认什么？
- Đáp: 已确认显示有异常光斑/白点；后续仅记录 `联系Maker`。文件没有给出具体故障部品、原因或测量值。 Nguồn file: KTD-2024-12-1698-Iris2020-C34-Operation-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3175
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Maker解析前に未記載対策を追加しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: LCD交換や内部部品原因を追加できますか。
- Đáp: できません。ファイルに記載された対応はMakerへの連絡までで、交換方法や内部原因は記載されていません。 Nguồn file: KTD-2024-12-1698-Iris2020-C34-Operation-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3176
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: C0350 phát sinh sau U155 và đóng Cover Waste.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Title block ghi Model=`IRIS2020-Low model`, Item=`SPEAKER`, Stable resistance=`7.4Ω`, NG resistor=`Open`, đúng không?
- Đáp: Đúng. File còn ghi `NG speakers` và `The circuit is broken`. Machine No. là **Raw value: ô trống**. Nguồn file: KTD-2024-5_C35_IRIS2020_C0350 .xlsx

## CÂU HỎI 3177
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认Speaker的电阻结果。
- Cách hỏi: trực tiếp
- Hỏi: 正常稳定阻值和NG阻值分别是什么？
- Đáp: Stable resistance=`7.4Ω`；NG resistor=`Open`。文件同时写有 `The circuit is broken`。 Nguồn file: KTD-2024-5_C35_IRIS2020_C0350 .xlsx

## CÂU HỎI 3178
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C0350表示とSpeaker調査結果を整理している。
- Cách hỏi: tình huống
- Hỏi: U155後にCover Wasteを閉めてC0350が出た場合、この報告では何が確認されていますか。
- Đáp: SPEAKERがNGで、Stable resistance=`7.4Ω`、NG resistor=`Open`、`The circuit is broken` と記載されています。 Nguồn file: KTD-2024-5_C35_IRIS2020_C0350 .xlsx

## CÂU HỎI 3179
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Filename là C6760 nhưng title block và diễn biến có cả C6760/C6950.
- Cách hỏi: so sánh
- Hỏi: Contents of defect và hai trạng thái phát sinh được ghi khác nhau thế nào?
- Đáp: Title block ghi `Contents of defect=C6950`. Status ghi `Lắp Fax bật nguồn máy báo C6760`; sau `Line out bật máy báo C6950`. Giữ nguyên cả hai mã, không tự sửa hoặc gộp. Nguồn file: KTD-2025-12-1314-Iris2024-C33-A1-C6760.xlsx

## CÂU HỎI 3180
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理YF1断线和Q1/Q2 Short，并核对Lot数据。
- Cách hỏi: xử lý sự cố
- Hỏi: YF1和Q1/Q2的调查结果以及Lot分别是什么？
- Đáp: YF1断线，文件定义 OK=`0.1Ω`、NG=`OL`；Q1和Q2 Short。Q1 Lot=`RJH60T04 542 011`，Q2 Lot=`RJH60T04 542 017`。 Nguồn file: KTD-2025-12-1314-Iris2024-C33-A1-C6760.xlsx

## CÂU HỎI 3181
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: EMS履歴とQ1/Q2測定値を正しく理解できているか確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Q1/Q2の対象LOT=`542` は `7960PCS` 投入済みでEMS工程内不良なし、測定表ではQ1/Q2 E-C=`0.1Ω / 0.1Ω` ですね。
- Đáp: はい。追加表にはC-G=`32Ω / 42.8Ω`、G-E=`32Ω / 42.8Ω`、U6 GND-pin11=`OL` も記載されています。この測定表には個別のOK/NG列はありません。 Nguồn file: KTD-2025-12-1314-Iris2024-C33-A1-C6760.xlsx
