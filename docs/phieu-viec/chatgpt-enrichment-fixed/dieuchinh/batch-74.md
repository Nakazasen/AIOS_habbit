# Mẻ 74 — Điều-tra-lỗi — Q2972–Q3001 (30 cặp)

- Ngày: 2026-10-05 ~02:09 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ (`0V`, `OL`, Machine No. ô trống giữ nguyên; bảng có cột OK/NG giữ đúng định nghĩa nguồn)
- Điểm phân biệt case:
  - 2 case C0980 HOÀN TOÀN ĐỘC LẬP: KTD-2025-12-1310 (C35-A1, mất 24V, IC401 bất thường với bảng đo pin chi tiết) vs KTD-2025-08-0841 (C35-A8, F401 đứt, Q402/Q403 short 3 cực) — không trùng nhau và không trùng các C0980 trước (KTD-2026-04-0397/D304)
  - 3 case DP Iris2020 C9080 ĐỘC LẬP: Q2990–2992 (LED2 diode NG=OL, OK=0.77V; LED1 NG=OK=0.77V; 313TT45010-01) vs Q2993–2995 (LED2 NG=OL, OK=0.7V; cathode LED2 không thông từ TP đến mối hàn) vs Q2996–2998 (Anode LED2 chưa được hàn, không có bảng diode) — không trùng case C9080 mẻ 70/73
- Không suy diễn C8 short, R399 bong, R5 vỡ, LED2 bất thường, LCD tối thành nguyên nhân sâu hơn ngoài nội dung file

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 2972
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra case ảnh bị vạch ngang sau khi in Process.
- Cách hỏi: trực tiếp
- Hỏi: Hiện tượng ảnh và kết quả điều tra trong case này là gì?
- Đáp: Sau khi in `8` tờ Process, kiểm tra ảnh đến tờ MC và GY phát hiện ảnh bị vạch ngang. Investigation ghi `Bong đầu điện cực R399`. Nguồn file: KTD-2026-05-0419-Iris2024-C34-A8.4-Hình ảnh bất thường.xlsx

## CÂU HỎI 2973
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师遇到MC和GY图像横线，需要参考历史报告。
- Cách hỏi: tình huống
- Hỏi: 报告中对R399记录了什么调查结果？
- Đáp: 文件只记录 `R399电极端部剥离 / Bong đầu điện cực R399`。没有另外记录更深层原因或修理对策。 Nguồn file: KTD-2026-05-0419-Iris2024-C34-A8.4-Hình ảnh bất thường.xlsx

## CÂU HỎI 2974
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 画像現象と調査結果を区別して整理している。
- Cách hỏi: so sánh
- Hỏi: ラインでの画像現象と調査結果はそれぞれ何ですか。
- Đáp: 画像現象は `8枚Process印刷後、MC/GYで横線を確認`、調査結果は `R399電極端部の剥がれ` です。 Nguồn file: KTD-2026-05-0419-Iris2024-C34-A8.4-Hình ảnh bất thường.xlsx

## CÂU HỎI 2975
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo 0980 sau khi lắp Fax và kỹ sư kiểm tra nguồn 24V.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi trạng thái nguồn và IC401 thế nào?
- Đáp: File ghi mất điện áp `24V (0V)` và kiểm tra điện áp IC401 thấy bất thường. Bảng nguồn còn ghi tiêu đề `Có 5V, Mất 24V (NG IC401)`; đây là nhãn NG do chính file định nghĩa. Nguồn file: KTD-2025-12-1310-Iris2024-C35-A1-C0980.xlsx

## CÂU HỎI 2976
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认IC401的几个测量值。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: IC401 pin3 是 `NG=0V`、`OK=2.1V`，pin5 是 `NG=0V`、`OK=4.1V`，对吗？
- Đáp: 对。文件的OK/NG测量表明确这样记录。 Nguồn file: KTD-2025-12-1310-Iris2024-C35-A1-C0980.xlsx

## CÂU HỎI 2977
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: IC401高電圧側の測定値を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: IC401のpin14、15、16のNG値とOK値は何ですか。
- Đáp: pin14=`NG 9.2V / OK 189V`、pin15=`NG 8.8V / OK 178V`、pin16=`NG 8.8V / OK 182V` です。 Nguồn file: KTD-2025-12-1310-Iris2024-C35-A1-C0980.xlsx

## CÂU HỎI 2978
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Có nhiều case C0980 nên kỹ sư cần phân biệt case tháng 8 với case tháng 12.
- Cách hỏi: tình huống
- Hỏi: Case này điều tra phát hiện gì tại F401, Q402 và Q403?
- Đáp: File ghi `đứt cầu chì F401`; Q402 và Q403 `short 3 cực với nhau`. Nguồn file: KTD-2025-08-0841-Iris2024-C35-A8-C0980.xlsx

## CÂU HỎI 2979
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较Q402和Q403的NG测量结果。
- Cách hỏi: so sánh
- Hỏi: Q402与Q403的D-G、D-S、G-S NG值分别有什么不同？
- Đáp: Q402：`D-G=1.3Ω`、`D-S=1.3Ω`、`G-S=0.2Ω`；Q403：`D-G=3.2Ω`、`D-S=3.2Ω`、`G-S=0.3Ω`。这些NG标签由源文件自身定义。 Nguồn file: KTD-2025-08-0841-Iris2024-C35-A8-C0980.xlsx

## CÂU HỎI 2980
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Q402/Q403の測定値から未記載の故障メカニズムを作らないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: Q402/Q403の低抵抗値だけから、ショート発生の根本原因や交換対策を追加できますか。
- Đáp: できません。ファイルには`F401断線`、`Q402/Q403三端子Short`、およびOK/NG測定値まで記載されています。根本原因や具体的対策は記載されていません。 Nguồn file: KTD-2025-08-0841-Iris2024-C35-A8-C0980.xlsx

## CÂU HỎI 2981
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: JIG ISU không điều chỉnh được và kỹ sư cần xác nhận kết quả lọc hàng.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Ngoại quan phát hiện cầu hàn tại CCD và kết quả lọc hàng là `NG=2/84 pcs`, đúng không?
- Đáp: Đúng. File ghi `Ngoại quan phát hiện cầu hàn linh kiện CCD` và `Thực hiện lọc hàng: NG=2/84 pcs`. Nguồn file: KTD-2025-10-1074-Iris2024-C33-ISU-Dính hàn.xlsx

## CÂU HỎI 2982
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认该ISU案例的对象信息。
- Cách hỏi: trực tiếp
- Hỏi: 该案例的品名、品号-Rev、数量是什么？
- Đáp: Item name=`PWB CCD ASSY`；Item code-Rev=`3V2XC01120-1`；Quantity=`2`。Machine No. 为 **Raw value: ô trống**。 Nguồn file: KTD-2025-10-1074-Iris2024-C33-ISU-Dính hàn.xlsx

## CÂU HỎI 2983
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: JIG調整不可の過去ケースを参照している。
- Cách hỏi: tình huống
- Hỏi: JIGが調整できない場合、この報告書では外観確認で何が見つかっていますか。
- Đáp: `CCD位置にはんだブリッジがある` と記載されています。選別結果は `2/84 NG` です。 Nguồn file: KTD-2025-10-1074-Iris2024-C33-ISU-Dính hàn.xlsx

## CÂU HỎI 2984
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: R5 bị vỡ vỏ nhưng phép đo điện trở lại được file đánh giá không bất thường.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng ngoại quan và kết quả đo điện trở của R5 khác nhau thế nào?
- Đáp: Ngoại quan ghi `Vỏ linh kiện R5 bị vỡ`; kiểm tra điện trở lại ghi `không bất thường: OK=99.8kΩ`. Nguồn file: KTD-2025-11-1165-Iris2024-C33-Assy2-Vỡ linh kiện.xlsx

## CÂU HỎI 2985
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师不能因为R5外壳破损而自行补充电气故障。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以把R5外壳破损直接写成电阻值异常吗？
- Đáp: 不可以。文件明确记录电阻检查 `无异常，OK=99.8kΩ`。外壳破损与该测量结果应分开保留。 Nguồn file: KTD-2025-11-1165-Iris2024-C33-Assy2-Vỡ linh kiện.xlsx

## CÂU HỎI 2986
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: R5破損ケースの後続対応を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: このファイルに記載された後続対応は、情報をまとめてPartnerへ連絡することですね。
- Đáp: はい。具体的な交換方法や修理対策は別途記載されていません。 Nguồn file: KTD-2025-11-1165-Iris2024-C33-Assy2-Vỡ linh kiện.xlsx

## CÂU HỎI 2987
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Trong khi in RCC, máy báo JAM4709.
- Cách hỏi: trực tiếp
- Hỏi: Kết quả điều tra linh kiện của case JAM4709 là gì?
- Đáp: Investigation ghi `Linh kiện C8 bị short`; file còn ghi `C8: maker Kyocera`. Nguồn file: KTD-2025-08-0853-Iris2024-C34-A8.5- Jam4709.xlsx

## CÂU HỎI 2988
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师在RCC打印过程中遇到Jam4709。
- Cách hỏi: tình huống
- Hỏi: 该案例的机器现象和调查结果分别是什么？
- Đáp: RCC打印过程中LCD显示 `JAM 4709`；调查结果为 `C8 Short`。 Nguồn file: KTD-2025-08-0853-Iris2024-C34-A8.5- Jam4709.xlsx

## CÂU HỎI 2989
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C8 Shortという結果から報告書以上の原因を断定しないようにしている。
- Cách hỏi: so sánh
- Hỏi: ファイルに記載されている確定情報と未記載情報は何ですか。
- Đáp: 確定している記載は `C8 Short` と `C8 maker Kyocera` です。Short発生メカニズムや具体的な修理対策は記載されていません。 Nguồn file: KTD-2025-08-0853-Iris2024-C34-A8.5- Jam4709.xlsx

## CÂU HỎI 2990
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: DP Iris2020 không chuyển bản thảo khi chạy U411 và báo C9080.
- Cách hỏi: xử lý sự cố
- Hỏi: File đã xác nhận gì về LED2 và giá trị diode?
- Đáp: Phân tích ghi `LED2 bất thường` và giá trị diode bất thường. Bảng nguồn định nghĩa `LED2 OK=0.77V, NG=OL`; `LED1 OK=0.77V, NG=0.77V`. Không có root cause sâu hơn trong file. Nguồn file: KTD-2025-09-1009-DP Iris2020-C2D-A1-C9080.xlsx

## CÂU HỎI 2991
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认这是DP Iris2020而不是Iris2024案例。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Model=`DP Iris2020`、Item=`CIS`、Line=`C2D-A1`，对吗？
- Đáp: 对。Item code-Rev=`313TT45010-01`，S.No=`FD2CFC-01 / 51 4030200037`。 Nguồn file: KTD-2025-09-1009-DP Iris2020-C2D-A1-C9080.xlsx

## CÂU HỎI 2992
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: LED1とLED2のダイオード測定値を直接比較している。
- Cách hỏi: trực tiếp
- Hỏi: LED1とLED2のOK/NG値は何ですか。
- Đáp: LED1は `OK=0.77V`、`NG=0.77V`。LED2は `OK=0.77V`、`NG=OL` です。OK/NGはソース自身の定義です。 Nguồn file: KTD-2025-09-1009-DP Iris2020-C2D-A1-C9080.xlsx

## CÂU HỎI 2993
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Một case C9080 khác cũng liên quan LED2 nhưng có thêm kiểm tra thông mạch.
- Cách hỏi: tình huống
- Hỏi: File ghi kết quả diode và thông mạch phía Cathode LED2 thế nào?
- Đáp: LED2 được định nghĩa `OK=0.7V`, `NG=OL`. Kiểm tra thông mạch phía Cathode LED2 từ điểm TP đến mối hàn ghi `không thông`. Nguồn file: KTD-2025-10-1089-DP Iris2020-C2D-A16-C9080.xlsx

## CÂU HỎI 2994
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较LED1和LED2在该报告中的二极管值。
- Cách hỏi: so sánh
- Hỏi: LED1和LED2的NG/OK测量结果有什么不同？
- Đáp: LED1：`NG=0.7V`、`OK=0.7V`；LED2：`NG=OL`、`OK=0.7V`。 Nguồn file: KTD-2025-10-1089-DP Iris2020-C2D-A16-C9080.xlsx

## CÂU HỎI 2995
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: LED2導通不良の報告に対し、記載済みの後続対応だけを確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: このファイルに記載された後続対応は何ですか。LED2交換を追加してよいですか。
- Đáp: 記載されている対応は `情報をまとめてPartnerへ連絡する` ことです。LED2交換は記載されていないため追加しません。 Nguồn file: KTD-2025-10-1089-DP Iris2020-C2D-A16-C9080.xlsx

## CÂU HỎI 2996
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Có ba case DP Iris2020 C9080 trong cùng mẻ nên cần phân biệt kết quả điều tra.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Case này không phải lỗi diode OL mà là ngoại quan phát hiện cực Anode LED2 chưa được hàn, đúng không?
- Đáp: Đúng. Investigation ghi `mối hàn cực Anode của LED2 chưa được hàn`; file này không có bảng diode như hai case C9080 trước. Nguồn file: KTD-2025-11-1163-DP Iris2020-C2D-C9080.xlsx

## CÂU HỎI 2997
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认当前C9080案例的外观结果。
- Cách hỏi: trực tiếp
- Hỏi: LED2的哪个端子被确认未焊接？
- Đáp: `Anode端子`。文件原文记录外观检查确认LED2的Anode端子未进行焊接。 Nguồn file: KTD-2025-11-1163-DP Iris2020-C2D-C9080.xlsx

## CÂU HỎI 2998
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 同じC9080でも各ケースの確認内容を混同しないようにしている。
- Cách hỏi: tình huống
- Hỏi: このケースでU411後にC9080が出た場合、何を外観で確認していますか。
- Đáp: `LED2のアノード端子が未はんだ` であることを確認しています。他ケースのLED2 diode=`OL` やCathode導通不良は、このファイルの結果として混在させません。 Nguồn file: KTD-2025-11-1163-DP Iris2020-C2D-C9080.xlsx

## CÂU HỎI 2999
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: LCD có vùng tối nhưng trước đó đã qua JIG OK.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng hiện tại và lịch sử kiểm tra trước đó được ghi thế nào?
- Đáp: Hiện tượng hiện tại là `Góc dưới màn hình bị tối`; Investigation ghi `trước đó đã qua JIG OK`. Hai thông tin này cùng tồn tại trong báo cáo, không suy diễn thêm nguyên nhân. Nguồn file: KTD-2025-06-0599-Iris2024-C35-A2-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3000
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理LCD下方变暗，但报告没有零件级原因。
- Cách hỏi: xử lý sự cố
- Hỏi: 文件已经记录了什么后续行动？可以自行补充LCD内部故障原因吗？
- Đáp: 文件记录 `汇总信息并联系Partner`。没有记录LCD内部具体故障原因，因此不能自行补充。 Nguồn file: KTD-2025-06-0599-Iris2024-C35-A2-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3001
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: LCD異常ケースの基本情報を最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 対象は `LCD OPERATION`、品番-Rev=`302XC45060-1`、Line=`C35-A2`、Machine No.は空欄ですね。
- Đáp: はい。Machine No.は **Raw value: ô trống**。S.No(Lot)=`SVF10100ANN 03 / 25.02.26`、Quantity=`1` です。 Nguồn file: KTD-2025-06-0599-Iris2024-C35-A2-Màn hình hiển thị bất thường.xlsx
