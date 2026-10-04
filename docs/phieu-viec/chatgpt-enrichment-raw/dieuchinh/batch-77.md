# Mẻ 77 — Điều-tra-lỗi — Q3062–Q3091 (30 cặp)

- Ngày: 2026-10-05 ~02:27 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ — giữ nguyên `0L`, `OlΩ`, `OL`, `2.1 oHm`, `0/100 pcs NG`, `0/120pcs`, `0/8000pcs`; không tự chuẩn hoá
- Điểm phân biệt case:
  - 2 case C6770 ĐỘC LẬP trong cùng mẻ: Q3074–3076 (KTD-2025-06-0578, C33-A2, Q1 short ba cực, Lot Q1=`RJH60T04 4N2 037`, U6=`L6491D MZ034`; file còn bảng so sánh thêm case C35) vs Q3077–3079 (KTD-2025-08-0924, C33-A3, thay U6 → OK, lắp lại U6 lỗi → NG; U6 pin11 ghi nguyên văn NG=`0L`/OK=`OlΩ`)
  - Case DP Iris2020 C9080 Q3086–3088 (KTD-2025-07-0805, CIS HIGH, LED2 cầu hàn) ĐỘC LẬP — không trùng các C9080 mẻ 70/73/74/75 (LED2 chưa hàn/diode OL/LED1 không sáng)
  - Case JAM4709 Q3089–3091 (KTD-2025-03-0215): file ghi rõ `Cause: Cap C8 shorted` — khác case JAM4709 mẻ 74 (KTD-2025-08-0853) chỉ ghi C8 short, maker Kyocera
  - Case RPS Fuser Iris Q3083–3085: Model mới `RPS Fuser Iris`, Item=THERMISTOR FUSER — không phải máy Iris/Iris2020
  - Case C4701 Q3065–3067 (Iris2020): tín hiệu `C2E_EUSS_VIDEO_INT` không thông mạch — khác case F378 mẻ 76 (tín hiệu `E2C_EUSS_SCAN_EN`)
  - Case ảnh nhạt K Q3071–3073: IC101 pin3-SG OK=`6.6M`/NG=`3.1M`; thông tin tĩnh điện chỉ là kết quả Partner của lỗi trước đó, không nâng thành root cause độc lập
- Chỉ dùng OK/NG ở nơi file tự định nghĩa; các nội dung phán đoán giữ đúng mức độ kết luận của chính nguồn

---

## CÂU HỎI 3062
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra case connector bị biến dạng trên UNIT FAX NCU.
- Cách hỏi: trực tiếp
- Hỏi: Hiện tượng connector và kết quả lọc hàng được file ghi thế nào?
- Đáp: File ghi `connector WLAN biến dạng / LANコネクターが変形された`; kết quả lọc hàng=`NG=0/120pcs`. Nguồn file: KTD-2025-07-0743-DP Iris2020-C2E-Connector NG.xlsx

## CÂU HỎI 3063
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现Connector变形后，需要按报告中的既有控制项处理。
- Cách hỏi: tình huống
- Hỏi: 文件对历史确认和LQC控制记录了什么？
- Đáp: 文件记录已联系Partner确认生产履历和发生风险；作业员会对过去发生过问题的connector位置进行外观确认，而且LQC中也已设为外观检查项目。 Nguồn file: KTD-2025-07-0743-DP Iris2020-C2E-Connector NG.xlsx

## CÂU HỎI 3064
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 現品1台と選別結果を混同しないよう比較している。
- Cách hỏi: so sánh
- Hỏi: 現品の不具合と選別結果はそれぞれ何ですか。
- Đáp: 現品は `LAN/WLAN connector変形`、Quantity=`1`。選別結果は `NG=0/120pcs` です。 Nguồn file: KTD-2025-07-0743-DP Iris2020-C2E-Connector NG.xlsx

## CÂU HỎI 3065
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C4701 và kỹ sư kiểm tra đường tín hiệu giữa Main và Engine.
- Cách hỏi: xử lý sự cố
- Hỏi: File xác nhận tín hiệu nào không thông mạch và có ghi linh kiện hỏng không?
- Đáp: File xác nhận `C2E_EUSS_VIDEO_INT` giữa Main và Engine không thông mạch. Không có linh kiện hỏng hoặc đối sách cụ thể được ghi, nên không tự bổ sung. Nguồn file: KTD-2026-01-0067-Iris2020-C34-A1-C4701.xlsx

## CÂU HỎI 3066
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认C4701报告中的空白字段。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Model=`Iris2020`、Item code=`-`，Item name、S.No、Supplier都是空白，对吗？
- Đáp: 对。Item name、S.No、Supplier保持 **Raw value: ô trống**；Machine No.=`1102YP3NLV / H566161755`。 Nguồn file: KTD-2026-01-0067-Iris2020-C34-A1-C4701.xlsx

## CÂU HỎI 3067
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C4701の発生現象と導通検査結果を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 電源ON時の表示と導通検査結果は何ですか。
- Đáp: 電源ON時に `C4701` を表示し、Main–Engine間の `C2E_EUSS_VIDEO_INT` 信号は導通しないと記載されています。 Nguồn file: KTD-2026-01-0067-Iris2020-C34-A1-C4701.xlsx

## CÂU HỎI 3068
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: LCD đổi màu bất thường và kỹ sư đo pin26 BIST so với VDD/GND.
- Cách hỏi: tình huống
- Hỏi: Ba dòng dữ liệu pin26 trong bảng đo được ghi cụ thể thế nào?
- Đáp: Mẫu `OK`: Pin26-VDD=`20M Ω`, Pin26-GND=`OL`; S/N `1176C-241218-2A0190`: `15.7kΩ / 56.6kΩ`; S/N `1176C-241206-2A0021`: `102.2kΩ / 502k Ω`. Nguồn file: KTD-2025-06-0606-Iris2024-C33-Operation-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3069
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师区分本次测量事实与报告中的原因推测。
- Cách hỏi: so sánh
- Hỏi: 本次确认事实和原因推测分别是什么？
- Đáp: 确认事实包括显示颜色异常、Pin26 BIST对VDD/GND电阻异常；报告的原因推测是 `过电流可能导致电源IC损坏`。这是文件自身的推测，不应升级为更确定的结论。 Nguồn file: KTD-2025-06-0606-Iris2024-C33-Operation-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3070
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 過去KDTCN事例を参照しつつ、今回ケースの対策範囲を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: このファイルに記載された確認指示は何ですか。
- Đáp: QCへ `ライン上の静電気を再確認` し、`FPCケーブルの接続状態を特に注意して確認` するよう指示しています。2023/8/29のKDTCN類似事例は履歴情報として記載されています。 Nguồn file: KTD-2025-06-0606-Iris2024-C33-Operation-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3071
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Case ảnh nhạt màu K có cùng dạng IC101 bất thường như một lỗi lịch sử.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File hiện tại xác nhận IC101 pin3-SG NG=`3.1M`, OK=`6.6M`, còn thông tin tĩnh điện là kết quả phân tích của lỗi trước đó, đúng không?
- Đáp: Đúng. File ghi trạng thái NG giống lỗi từng phát sinh trước đó và dẫn lại kết quả Partner trước đây rằng tĩnh điện làm hỏng IC101; không tự biến lịch sử đó thành root cause độc lập của case hiện tại. Nguồn file: KTD-2025-10-1050-Iris2024-C35-A7-Hình ảnh bất thường.xlsx

## CÂU HỎI 3072
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认本案例的图像异常和测量值。
- Cách hỏi: trực tiếp
- Hỏi: RC9图像和IC101 pin3-SG分别记录了什么？
- Đáp: RC9打印后 `K色图像变淡`；IC101 pin3-SG电阻由文件定义为 OK=`6.6M`、NG=`3.1M`。 Nguồn file: KTD-2025-10-1050-Iris2024-C35-A7-Hình ảnh bất thường.xlsx

## CÂU HỎI 3073
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 現在ケースと過去類似ケースの情報レベルを区別している。
- Cách hỏi: tình huống
- Hỏi: 現在のNG状態が過去事例と似ている場合、静電気を今回の確定原因として記載できますか。
- Đáp: できません。今回確認されているのはK色画像異常とIC101 pin3-SG=`NG 3.1M / OK 6.6M` で、静電気によるIC101破損は過去のPartner解析結果として記載されています。 Nguồn file: KTD-2025-10-1050-Iris2024-C35-A7-Hình ảnh bất thường.xlsx

## CÂU HỎI 3074
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: File chứa cả bảng case C35 và case C33 nên kỹ sư cần phân biệt đúng dữ liệu hiện tại.
- Cách hỏi: so sánh
- Hỏi: Giá trị Q1 giữa case C35 và C33 trong bảng tổng hợp khác nhau thế nào?
- Đáp: Case C35: E-G=`37.3Ω`, G-C=`37.5Ω`, C-E=`0.3Ω`; case C33: E-G=`0.2Ω`, G-C=`0.2Ω`, C-E=`0.2Ω`. Case báo cáo chính là C33-A2 với Q1 Lot=`RJH60T04 4N2 037`. Nguồn file: KTD-2025-06-0578-Iris2024-C33-A2-C6770.xlsx

## CÂU HỎI 3075
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看Q1三端低电阻，但不能额外推断其内部失效机理。
- Cách hỏi: xử lý sự cố
- Hỏi: 当前C33案例对Q1确认了什么？可以进一步推断Short机理吗？
- Đáp: 文件确认外观无异常，Q1三端互相Short；当前Q1三组电阻均记录为 `0.2Ω`。文件没有写Short的内部发生机理，因此不能追加。 Nguồn file: KTD-2025-06-0578-Iris2024-C33-A2-C6770.xlsx

## CÂU HỎI 3076
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C33-A2ケースのLot情報を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 今回のQ1 Lot=`RJH60T04 4N2 037`、U6 Lot=`L6491D MZ034` ですね。
- Đáp: はい。Item=`PWB IH 100 ASSY WITH SOFTWARE`、S.No=`69D0054B6614`、Line=`C33-A2` です。 Nguồn file: KTD-2025-06-0578-Iris2024-C33-A2-C6770.xlsx

## CÂU HỎI 3077
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C6770 kèm âm thanh lạ và kỹ sư crosscheck U6.
- Cách hỏi: trực tiếp
- Hỏi: Kết quả thay U6 và lắp lại U6 lỗi được file ghi thế nào?
- Đáp: File ghi `thay linh kiện U6 OK`; khi `lắp lại linh kiện U6` thì tái hiện lỗi và ghi `NG`. Ngoại quan trước đó=`không bất thường`. Nguồn file: KTD-2025-08-0924-Iris2024-C33-A3-C6770.xlsx

## CÂU HỎI 3078
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看U6表中的OK/NG数据。
- Cách hỏi: tình huống
- Hỏi: U6 pin4、pin12和pin13的NG/OK值分别是多少？
- Đáp: pin4=`NG 0.8MΩ / OK 4kΩ`；pin12=`NG 31.3kΩ / OK 236kΩ`；pin13=`NG 49.2kΩ / OK 0.5MΩ`。这些OK/NG标签由源文件自身定义。 Nguồn file: KTD-2025-08-0924-Iris2024-C33-A3-C6770.xlsx

## CÂU HỎI 3079
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: U6測定表の特殊表記をそのまま比較している。
- Cách hỏi: so sánh
- Hỏi: U6 pin11のNGとOKはどう記載されていますか。
- Đáp: NG=`0L`、OK=`OlΩ` と記載されています。表記はソースのまま保持し、`OL` 等へ自動修正しません。 Nguồn file: KTD-2025-08-0924-Iris2024-C33-A3-C6770.xlsx

## CÂU HỎI 3080
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C6950 và kỹ sư đo đường 15V1.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi kết quả nào về 15V1 và U1, và có thể suy diễn sâu hơn không?
- Đáp: File ghi `short điện áp 15V1`, giá trị=`2.1 oHm`, và `Short pin4 với 8 linh kiện U1`. Không có nguyên nhân sâu hơn hoặc đối sách cụ thể, nên không bổ sung. Nguồn file: KTD-2025-01-0010-Iris2024-C35-C6950.xlsx

## CÂU HỎI 3081
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认报告中的原始测量值。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 15V1 Short的数值在源文件中写成 `2.1 oHm`，应原样保留，对吗？
- Đáp: 对。该值保持原文 `2.1 oHm`，不能自行改单位格式或赋予额外OK/NG含义。 Nguồn file: KTD-2025-01-0010-Iris2024-C35-C6950.xlsx

## CÂU HỎI 3082
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C6950ケースの対象基板情報を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: Item、品番-Rev、S.Noは何ですか。
- Đáp: Item=`PWB IH 200 ASSY WITH SOFTWARE`、Item code-Rev=`302XC01580-03`、S.No=`62K004YP3795`。Machine No. は **Raw value: ô trống** です。 Nguồn file: KTD-2025-01-0010-Iris2024-C35-C6950.xlsx

## CÂU HỎI 3083
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Fuser Unit kiểm tra chức năng báo THERM TEMP ERROR.
- Cách hỏi: tình huống
- Hỏi: Báo cáo ghi giá trị điện trở, ngoại quan và kết quả lọc hàng Partner thế nào?
- Đáp: Điện trở được file định nghĩa OK=`225k Ohm`, NG=`OL`; ngoại quan phát hiện cảm biến nhiệt độ bị vỡ; lọc hàng phía Partner=`NG=0/8000pcs`. Nguồn file: KTD-2025-12-1275-RPS Fuser Iris-C3A-JIG báo NG.xlsx

## CÂU HỎI 3084
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师区分已确认的外观现象和文件中的破损原因判断。
- Cách hỏi: so sánh
- Hỏi: 已确认事实与报告判断分别是什么？
- Đáp: 已确认的是温度sensor破损、Thermistor tape变形、阻值 NG=`OL`。报告判断为可能受到夹压或冲击造成sensor破损，并推测需要较强外力。 Nguồn file: KTD-2025-12-1275-RPS Fuser Iris-C3A-JIG báo NG.xlsx

## CÂU HỎI 3085
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: KDTVN工程とPartner側確認結果を踏まえて、記載範囲内で原因を扱っている。
- Cách hỏi: xử lý sự cố
- Hỏi: KDTVN作業が原因だったと断定できますか。
- Đáp: できません。ファイルは `KDTVNでの作業を確認したが、NGが発生する可能性はなかった` と記載しています。Partner側には `3工程の機能検査` があり、選別結果=`NG=0/8000pcs` です。 Nguồn file: KTD-2025-12-1275-RPS Fuser Iris-C3A-JIG báo NG.xlsx

## CÂU HỎI 3086
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Có nhiều case C9080 nên kỹ sư cần xác nhận đúng case CIS HIGH.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Case này là Model=`DP Iris2020`, Item=`CIS HIGH`, scan tờ 7 màu báo C9080 và LED2 bị cầu hàn, đúng không?
- Đáp: Đúng. Item code-Rev=`303TC45010-2`, S.No=`FA8CFC-01 / 51 5060500264`, Quantity=`1`. Nguồn file: KTD-2025-07-0805-DP Iris2020-C2D-C9080.xlsx

## CÂU HỎI 3087
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认该C9080案例的调查结果。
- Cách hỏi: trực tiếp
- Hỏi: LED2记录了什么异常？
- Đáp: 文件明确记录 `LED2发生焊锡桥接 / LED2 bị cầu hàn`。 Nguồn file: KTD-2025-07-0805-DP Iris2020-C2D-C9080.xlsx

## CÂU HỎI 3088
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 7色紙ScanでC9080が出た際、他のC9080事例と混同しないようにしている。
- Cách hỏi: tình huống
- Hỏi: このケースで確認されたLED異常は何ですか。
- Đáp: `LED2のはんだブリッジ` です。他ケースのLED2未半田、diode=`OL`、LED1異常などはこのファイルの結果として追加しません。 Nguồn file: KTD-2025-07-0805-DP Iris2020-C2D-C9080.xlsx

## CÂU HỎI 3089
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: RC9 in OK nhưng RCC kế tiếp phát sinh JAM4709.
- Cách hỏi: so sánh
- Hỏi: Trạng thái trước khi lỗi và kết quả điều tra sau khi lỗi được ghi thế nào?
- Đáp: `Print RC9 page: OK`; lần in RCC tiếp theo máy báo `JAM 4709`. Điều tra ghi `+24V2_F1 shorted to GND` và chính file kết luận `Cause: Cap C8 shorted`. Nguồn file: KTD-2025-03-0215-Iris2024-C35-C4709-.xlsx

## CÂU HỎI 3090
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理JAM4709，并严格使用报告中已有的后续行动。
- Cách hỏi: xử lý sự cố
- Hỏi: 文件记录了什么筛选结果和后续要求？
- Đáp: Line检查结果=`0/100 pcs NG`；文件要求 `向Partner获取部品LOT/NO`。由于源文件明确写了 `Cause: Cap C8 shorted`，可以保留C8为该报告的原因结论。 Nguồn file: KTD-2025-03-0215-Iris2024-C35-C4709-.xlsx

## CÂU HỎI 3091
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: JAM4709ケースの原因記載が報告書自身の結論か確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: このケースでは `+24V2_F1-GND Short` を確認し、ファイル自身が `Cause: Cap C8 shorted` と明記していますね。
- Đáp: はい。その通りです。選別結果は `0/100 pcs NG`、後続対応はPartnerへ部品LOT/NOの提示を依頼することです。 Nguồn file: KTD-2025-03-0215-Iris2024-C35-C4709-.xlsx
