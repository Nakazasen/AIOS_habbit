# Mẻ 79 — Điều-tra-lỗi — Q3122–Q3151 (30 cặp)

- Ngày: 2026-10-05 ~02:42 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt; preview tải thành công ngay lần đầu
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ — giữ nguyên `0L`, `OL`, `OlΩ`, `na`, `0.3`, ô trống; không tự chuẩn hóa; OK/NG chỉ gán tại bảng chính nguồn định nghĩa
- Điểm phân biệt case:
  - 3 case C6770 ĐỘC LẬP trong cùng mẻ: Q3122–3124 (KTD-2025-07-0671, C35-A2, PWB IH 100, Q1 short, bảng OK/NG: Q1 C-G=OK 0.7MΩ/NG 71Ω, C-E=OK 0.7MΩ/NG 0.1Ω, G-E=OK 30kΩ/NG 71Ω; Q2 C-G=OK 320kΩ/NG 61kΩ, C-E=OK 30kΩ/NG OL, G-E=OK 30kΩ/NG 30kΩ) vs Q3134–3136 (KTD-2025-09-1015, C33-A8.2, Q1 short, Lot=`RJH60T04 532 023`; bảng Q1/Q2 không cột OK/NG; U6 pin11=`0L`) vs Q3137–3139 (KTD-2025-05-0539, C35-A6, PWB IH 200; Q1 C-G=OK 0.7MΩ/NG 48kΩ, C-E=OK 0.7MΩ/NG 25kΩ; Q2 C-E=OK 230kΩ/NG 32kΩ; U6 pin11=OK `OlΩ`/NG `OlΩ`)
  - Case C4101 Q3128–3130 (KTD-2025-07-0710): Investigation chỉ ghi đợi kết quả phân tích từ bên JP — case chưa có kết luận, không tự thêm nguyên nhân/đối sách
  - Case Error80 Q3131–3133 (KTD-2025-08-0914): Investigation=Linh kiện C307 bị bong; Machine No.=`na`; Reappear rate giữ Raw value `0.3`, không quy đổi %
  - Case KTD-2025-03-0262 (Không lên nguồn): title block bất thường — Item name=`POWER SUPPLY TECHNOLOGY (HONG KONG)` đồng thời Supplier cũng là giá trị này, giữ nguyên không tự sửa; 5V sụt xuống 2.8V; crosscheck + làm nóng/lạnh IC201 đều không tái hiện lỗi
  - Case KTD-2025-06-0639 (Không lên nguồn): UNIT LOW VOLTAGE, mất 5V, F201 đứt; F201=OK 0.2Ω/NG OL; Q202 G-S=OK 3.1MΩ/NG OL, G-D=OK 3.2MΩ/NG OL, S-D=OK 10kΩ/NG 10kΩ; một số ô bảng IC201 bị lệch chứa chuỗi `302XD45010-8`/`UNIT LOW VOLTAGE` — không diễn giải thành số đo
  - Case Toner Container Q3149–3151 (KTD-2026-03-0262): thông báo "The tonner container is not properly installed" (giữ nguyên chính tả nguồn `tonner`) không mất; Investigation ghi Bong đầu điện cực R15 và Có dấu hiệu sửa hàng; S.No và Machine No. là ô trống
  - Case Scan NG Q3140–3142 (KTD-2025-08-0831): file tự kết luận "nguyên nhân do bản mạch highvoltage tranfer" (giữ nguyên chính tả nguồn), PC báo NG điểm 3301 và 3310, crosscheck tái hiện được lỗi
- Không suy diễn C307 bong, Q1 short, T2 bất thường, R15 bong hoặc dấu sửa hàng thành nguyên nhân sâu hơn ngoài nguồn

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 3122
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra case C6770 có bảng điện trở Q1/Q2.
- Cách hỏi: trực tiếp
- Hỏi: Q1 được file định nghĩa OK/NG thế nào tại C-G, C-E và G-E?
- Đáp: Q1: C-G=`OK 0.7MΩ / NG 71Ω`; C-E=`OK 0.7MΩ / NG 0.1Ω`; G-E=`OK 30kΩ / NG 71Ω`. Investigation ghi `Q1 bị Short`. Nguồn file: KTD-2025-07-0671-Iris2024-C35-A2-C6770.xlsx

## CÂU HỎI 3123
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师开机遇到C6770，需要查看Q2的源文件判定值。
- Cách hỏi: tình huống
- Hỏi: Q2的C-G、C-E、G-E分别怎样定义OK/NG？
- Đáp: C-G=`OK 320kΩ / NG 61kΩ`；C-E=`OK 30kΩ / NG OL`；G-E=`OK 30kΩ / NG 30kΩ`。这些OK/NG由源文件明确给出。 Nguồn file: KTD-2025-07-0671-Iris2024-C35-A2-C6770.xlsx

## CÂU HỎI 3124
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Q1とQ2のC-E判定値を比較している。
- Cách hỏi: so sánh
- Hỏi: C-EのOK/NG値はQ1とQ2でどう違いますか。
- Đáp: Q1は OK=`0.7MΩ`、NG=`0.1Ω`。Q2は OK=`30kΩ`、NG=`OL` です。 Nguồn file: KTD-2025-07-0671-Iris2024-C35-A2-C6770.xlsx

## CÂU HỎI 3125
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy không lên nguồn và đường 5V bị sụt.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi 5V sụt xuống bao nhiêu và crosscheck IC201 cho kết quả thế nào?
- Đáp: Điện áp `5V` bị sụt xuống `2.8V`. Sau khi crosscheck IC201, lỗi không tái hiện; làm nóng và làm lạnh IC201 cũng không tái hiện được lỗi. Không được từ đó tự kết luận IC201 là root cause. Nguồn file: KTD-2025-03-0262-Iris2024-C33-A1-Không lên nguồn.xlsx

## CÂU HỎI 3126
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认IC201 Pin1的测量数据是否按源文件读取。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: IC201 Pin1-GND的电阻是 NG=`2.7k`、OK=`149k`，电压是 NG=`0`、OK=`0.7`，对吗？
- Đáp: 对。上述OK/NG均为文件测量表自身定义。 Nguồn file: KTD-2025-03-0262-Iris2024-C33-A1-Không lên nguồn.xlsx

## CÂU HỎI 3127
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: IC201 Pin6の抵抗値と電圧値を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: IC201 Pin6-GNDの抵抗と電圧のOK/NG値は何ですか。
- Đáp: 抵抗は NG=`4.7k`、OK=`4.7k`。電圧は NG=`8.5`、OK=`13` です。 Nguồn file: KTD-2025-03-0262-Iris2024-C33-A1-Không lên nguồn.xlsx

## CÂU HỎI 3128
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: RCG trước U950 phát sinh C4101 nhưng chưa có kết quả phân tích.
- Cách hỏi: tình huống
- Hỏi: Investigation hiện tại của case C4101 ghi gì?
- Đáp: File chỉ ghi `Đợi kết quả phân tích lỗi từ bên JP / 日本から不良分析結果待ち`. Chưa có nguyên nhân, số đo hay đối sách kỹ thuật được ghi. Nguồn file: KTD-2025-07-0710-Iris2024-C33-A5-C4101.xlsx

## CÂU HỎI 3129
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师区分已确认现象与尚未完成的分析。
- Cách hỏi: so sánh
- Hỏi: 当前已经确认的内容和仍在等待的内容分别是什么？
- Đáp: 已确认的是 `U950前打印RCG时画面显示C4101`；仍在等待的是 `日本方面的不良解析结果`。文件没有给出根因。 Nguồn file: KTD-2025-07-0710-Iris2024-C33-A5-C4101.xlsx

## CÂU HỎI 3130
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 分析待ちのケースで未記載対策を追加しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: C4101に対して部品交換や修理方法を追加できますか。
- Đáp: できません。ファイルは `日本から不良分析結果待ち` までで、原因部品や対策は記載されていません。 Nguồn file: KTD-2025-07-0710-Iris2024-C33-A5-C4101.xlsx

## CÂU HỎI 3131
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Error80 phát sinh khi Aging và Investigation chỉ có một linh kiện ngoại quan.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File ghi C307 bị bong, Machine No.=`na`, Reappear rate=`0.3`, đúng không?
- Đáp: Đúng. Model=`Iris2024`, Item=`PWB ENGINE ASSY WITH SOFTWARE`, line=`C35-A7`, Quantity=`1`. Giữ nguyên Machine No.=`na` và Raw value `0.3`. Nguồn file: KTD-2025-08-0914-Iris2024-C35-A7-Error80.xlsx

## CÂU HỎI 3132
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认Error80案例的调查结果。
- Cách hỏi: trực tiếp
- Hỏi: Investigation栏记录了哪个部品异常？
- Đáp: 文件只记录 `C307部品脱落 / Linh kiện C307 bị bong`。没有写更深层原因。 Nguồn file: KTD-2025-08-0914-Iris2024-C35-A7-Error80.xlsx

## CÂU HỎI 3133
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Aging時のError80表示と調査結果を整理している。
- Cách hỏi: tình huống
- Hỏi: AgingでError80が出たこのケースでは何が確認されていますか。
- Đáp: Investigationには `C307部品が剥がれた` と記載されています。Reappear rateはソース上 `0.3` のまま保持します。 Nguồn file: KTD-2025-08-0914-Iris2024-C35-A7-Error80.xlsx

## CÂU HỎI 3134
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Case C6770 tại C33-A8.2 có bảng Q1/Q2 và U6.
- Cách hỏi: so sánh
- Hỏi: Giá trị điện trở Q1 và Q2 tại E-G, G-C, C-E khác nhau thế nào?
- Đáp: Q1: E-G=`130.7Ω`, G-C=`130.9Ω`, C-E=`0.3Ω`; Q2: E-G=`29.5kΩ`, G-C=`61.3kΩ`, C-E=`3.9kΩ`. Bảng này không gán OK/NG cho Q1/Q2. Nguồn file: KTD-2025-09-1015-Iris2024-C33-A8.2-C6770.xlsx

## CÂU HỎI 3135
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看U6的NG列，需要保持特殊Raw value。
- Cách hỏi: xử lý sự cố
- Hỏi: U6 pin11在源表中怎样记录？可以自动改成OL吗？
- Đáp: 源表记录 pin11=`0L`，属于原始值，应保持 **Raw value `0L`**，不能自行改写为 `OL`。 Nguồn file: KTD-2025-09-1015-Iris2024-C33-A8.2-C6770.xlsx

## CÂU HỎI 3136
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Q1 ShortケースのLot情報を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Q1はShort、Lot=`RJH60T04 532 023`、S.No=`69D0057D0454` ですね。
- Đáp: はい。Line=`C33-A8.2`、発生時はRCG Color Regist ScanでPanelが `C6770` を表示しました。 Nguồn file: KTD-2025-09-1015-Iris2024-C33-A8.2-C6770.xlsx

## CÂU HỎI 3137
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C6770 sau kiểm tra cassette nhưng ngoại quan board không bất thường.
- Cách hỏi: trực tiếp
- Hỏi: Q1 C-G và C-E được file định nghĩa OK/NG thế nào?
- Đáp: Q1 C-G=`OK 0.7MΩ / NG 48kΩ`; C-E=`OK 0.7MΩ / NG 25kΩ`. Nguồn file: KTD-2025-05-0539-Iris2024-C35-A6- C6770.xlsx

## CÂU HỎI 3138
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师检查Q2的源文件判定值。
- Cách hỏi: tình huống
- Hỏi: Q2的C-G、C-E、G-E分别怎样定义OK/NG？
- Đáp: C-G=`OK 320kΩ / NG 320kΩ`；C-E=`OK 230kΩ / NG 32kΩ`；G-E=`OK 30kΩ / NG 30kΩ`。 Nguồn file: KTD-2025-05-0539-Iris2024-C35-A6- C6770.xlsx

## CÂU HỎI 3139
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: U6のOK/NG値が同じ箇所を比較している。
- Cách hỏi: so sánh
- Hỏi: U6 pin11のOKとNGはどう記載されていますか。
- Đáp: OK=`OlΩ`、NG=`OlΩ` です。ソース表記をそのまま保持し、別表記へ自動修正しません。 Nguồn file: KTD-2025-05-0539-Iris2024-C35-A6- C6770.xlsx

## CÂU HỎI 3140
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Scan RCG Color Regist báo hai điểm NG và crosscheck board tái hiện được lỗi.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi các điểm NG và kết luận nguyên nhân như thế nào?
- Đáp: PC báo NG tại điểm `3301` và `3310`. Crosscheck board tái hiện được lỗi; chính file kết luận `nguyên nhân do bản mạch highvoltage tranfer`. Ngoại quan board không thấy bất thường. Nguồn file: KTD-2025-08-0831-Iris2024-C35-A8.6-Scan tự động NG.xlsx

## CÂU HỎI 3141
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认报告自身是否已经给出原因结论。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Crosscheck能够再现故障，而且文件明确写原因是High Voltage Transfer板，对吗？
- Đáp: 对。文件原文明确写 `nguyên nhân do bản mạch highvoltage tranfer`，同时记录外观检查无异常。 Nguồn file: KTD-2025-08-0831-Iris2024-C35-A8.6-Scan tự động NG.xlsx

## CÂU HỎI 3142
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Scan NGケースの対象情報を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: Item、S.No、Lineは何ですか。
- Đáp: Item=`UNIT HIGH VOLTAGE TRANSFER`、S.No=`J3J0055Z7620`、Line=`C35-A8.6` です。Machine No.は **Raw value: ô trống** です。 Nguồn file: KTD-2025-08-0831-Iris2024-C35-A8.6-Scan tự động NG.xlsx

## CÂU HỎI 3143
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: UNIT LOW VOLTAGE mất 5V và bảng đo xác nhận F201 đứt.
- Cách hỏi: tình huống
- Hỏi: F201 và Q202 được file định nghĩa các giá trị nào?
- Đáp: F201=`OK 0.2Ω / NG OL`. Q202: G-S=`OK 3.1MΩ / NG OL`; G-D=`OK 3.2MΩ / NG OL`; S-D=`OK 10kΩ / NG 10kΩ`. Nguồn file: KTD-2025-06-0639-Iris2024-C35-A1-Không lên nguồn.xlsx

## CÂU HỎI 3144
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较主调查结论和测量表。
- Cách hỏi: so sánh
- Hỏi: 主调查结果与F201测量表分别怎样记录？
- Đáp: 主调查记录 `5V电压消失、F201断线`；测量表定义F201为 OK=`0.2Ω`、NG=`OL`。两者均可按源文件保留。 Nguồn file: KTD-2025-06-0639-Iris2024-C35-A1-Không lên nguồn.xlsx

## CÂU HỎI 3145
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 表のずれたセルを数値として誤読しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: IC201表に `302XD45010-8` や `UNIT LOW VOLTAGE` が見える場合、それを抵抗値として扱えますか。
- Đáp: できません。これは抽出上ずれた非数値セルなので、抵抗値として解釈しません。確認できる測定値だけを使用します。 Nguồn file: KTD-2025-06-0639-Iris2024-C35-A1-Không lên nguồn.xlsx

## CÂU HỎI 3146
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Process image bị loang nhưng ngoại quan linh kiện không bất thường.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File ghi ảnh MC/GY bị loang sau 8 tờ Process, tín hiệu T2 bất thường và ngoại quan không bất thường, đúng không?
- Đáp: Đúng. Đây là toàn bộ kết quả điều tra được ghi; file không xác định linh kiện root cause. Nguồn file: KTD-2025-08-0860-Iris2024-C34-A8-Hình ảnh bất thường.xlsx

## CÂU HỎI 3147
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认图像异常条件。
- Cách hỏi: trực tiếp
- Hỏi: 打印多少张Process后，哪些图像出现什么异常？
- Đáp: 打印 `8张 Process` 后，MC和GY图像出现异常，文件描述为 `loang / 滲む`。 Nguồn file: KTD-2025-08-0860-Iris2024-C34-A8-Hình ảnh bất thường.xlsx

## CÂU HỎI 3148
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: T2信号異常から未記載の部品原因を作らないようにしている。
- Cách hỏi: tình huống
- Hỏi: T2信号が異常の場合、このファイルから故障部品まで特定できますか。
- Đáp: できません。ファイルは `T2信号異常` と `外観異常なし` までで、具体的な原因部品は記載していません。 Nguồn file: KTD-2025-08-0860-Iris2024-C34-A8-Hình ảnh bất thường.xlsx

## CÂU HỎI 3149
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Thông báo Toner Container không mất và kỹ sư cần phân biệt hai dấu hiệu trên board.
- Cách hỏi: so sánh
- Hỏi: Investigation ghi hai dấu hiệu nào?
- Đáp: File ghi `Bong đầu điện cực R15` và `Có dấu hiệu sửa hàng`. Không có số đo hoặc nguyên nhân sâu hơn được ghi. Nguồn file: KTD-2026-03-0262-Iris2024-C35-A1-The Toner Container Is not Properly Installed.xlsx

## CÂU HỎI 3150
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理Toner Container提示无法消失的问题。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以根据R15电极脱落和有维修痕迹，自行判断是谁维修或追加维修方法吗？
- Đáp: 不可以。文件只记录 `R15电极端脱落` 和 `有改造/维修痕迹`，没有记录维修人员、发生原因或具体对策。 Nguồn file: KTD-2026-03-0262-Iris2024-C35-A1-The Toner Container Is not Properly Installed.xlsx

## CÂU HỎI 3151
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 空欄フィールドを推測で補完しないよう確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Item=`PWB FRONT DRIVE ASSY`、品番-Rev=`3V2XD01050-5` で、S.NoとMachine No.は空欄ですね。
- Đáp: はい。S.NoとMachine No.は **Raw value: ô trống**。Line=`C35-A1`、Quantity=`1` です。 Nguồn file: KTD-2026-03-0262-Iris2024-C35-A1-The Toner Container Is not Properly Installed.xlsx
