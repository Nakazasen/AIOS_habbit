# Mẻ 76 — Điều-tra-lỗi — Q3032–Q3061 (30 cặp)

- Ngày: 2026-10-05 ~02:21 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ — giữ nguyên `Open`, `open`, `0L`, ô trống, các giá trị bảng không có OK/NG; không tự chuẩn hóa; OK/NG chỉ dùng khi chính file định nghĩa
- Điểm phân biệt:
  - File C6770 `KTD-2025-05-0540`: cùng KTD với bản PDF đã gặp ở mẻ 67 — mẻ này dùng trực tiếp XLSX, xử lý độc lập theo nội dung XLSX (`PWB IH 100 ASSY`, Q1 short; Q1 C-G OK=`0.7MΩ`/NG=`78Ω`, C-E OK=`0.7MΩ`/NG=`0.2Ω`, G-E OK=`30kΩ`/NG=`78Ω`; Q2 C-E OK=`30kΩ`/NG=`3.9kΩ`)
  - File LCD Panel `KTD-2025-01-0018`: nội dung ghi KTD=`2025-1-18` (không định dạng YYYY-MM chuẩn), Investigation chính **ô trống**; bảng `resistance value with GND` không gán OK/NG — không tự gán
  - Case IC101: "tĩnh điện làm hỏng IC101" chỉ là **kết quả phân tích của Partner cho lỗi trước đó có trạng thái tương tự**, không nâng thành nguyên nhân đã xác nhận riêng cho case hiện tại; giá trị thực đo: IC101 pin3-SG OK=`6.6M`/NG=`3.1M`
  - Case FPC: phán đoán của chính file là `tiếp xúc FPC-Panel bị lỏng` (chạm vào thì điện trở thay đổi); giữ đúng mức phán đoán, không nâng thành kết luận nguyên nhân xác nhận
- Không suy diễn connector YC8, E2C_EUSS_SCAN_EN, YC2, board nứt/vỡ hoặc vùng sáng LCD thành nguyên nhân sâu hơn ngoài báo cáo

---

## CÂU HỎI 3032
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra case connector bị bong tại công đoạn ASSY.
- Cách hỏi: trực tiếp
- Hỏi: Hiện tượng tại line và nội dung phán đoán trong file là gì?
- Đáp: Hiện tượng tại line là `Bong YC8`. Investigation ghi `phán đoán trong quá trình kết nối làm bong connector`. Đây là phán đoán của chính báo cáo. Nguồn file: KTD-2025-04-0363-Iris2024-C34-ASSY-Bong linh kiện.xlsx

## CÂU HỎI 3033
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师在ASSY工序发现YC8脱落，需要按报告原文理解。
- Cách hỏi: tình huống
- Hỏi: 文件是否已经明确确认连接动作就是根因？
- Đáp: 文件写的是 `推测在连接过程中导致connector脱落`，因此应保持为报告中的推测，不能升级为已经确认的根因。 Nguồn file: KTD-2025-04-0363-Iris2024-C34-ASSY-Bong linh kiện.xlsx

## CÂU HỎI 3034
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 入力済みの製品情報と未入力のMachine No.を区別している。
- Cách hỏi: so sánh
- Hỏi: このケースで記載済みの品番情報と空欄情報は何ですか。
- Đáp: Item code-Rev=`3VC2L01010-4`、Item name=`PWB MAIN ASSY WITH SOFTWARE`、S.No=`6HY1053B6573`。Machine No. は **Raw value: ô trống** です。 Nguồn file: KTD-2025-04-0363-Iris2024-C34-ASSY-Bong linh kiện.xlsx

## CÂU HỎI 3035
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy Iris2020 báo F378 và kỹ sư kiểm tra đường tín hiệu giữa Main và Engine.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi kết quả kiểm tra thông mạch nào và có thể từ đó kết luận linh kiện hỏng không?
- Đáp: File ghi tín hiệu `E2C_EUSS_SCAN_EN` giữa Main và Engine `không thông mạch`. Không có linh kiện gây lỗi hoặc đối sách được ghi, nên không tự bổ sung. Nguồn file: KTD-2026-01-0068-Iris2020-C35-A1-F378.xlsx

## CÂU HỎI 3036
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认本案例的Model和空白字段。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Model是 `Iris2020`，Item code=`-`，而Item name、S.No、Supplier和Machine No.都是空白，对吗？
- Đáp: 对。上述未填写字段保持 **Raw value: ô trống**，不能根据F378自行补充产品信息。 Nguồn file: KTD-2026-01-0068-Iris2020-C35-A1-F378.xlsx

## CÂU HỎI 3037
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: F378発生時の確認内容を直接参照している。
- Cách hỏi: trực tiếp
- Hỏi: 電源ON時の表示と導通検査結果は何ですか。
- Đáp: 電源ON時に `F378` を表示し、MainとEngine間の `E2C_EUSS_SCAN_EN` 信号は導通しないと記載されています。 Nguồn file: KTD-2026-01-0068-Iris2020-C35-A1-F378.xlsx

## CÂU HỎI 3038
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C6770 và kỹ sư cần kiểm tra bảng điện trở Q1 của case này.
- Cách hỏi: tình huống
- Hỏi: Q1 được file định nghĩa OK/NG thế nào tại C-G, C-E và G-E?
- Đáp: Q1: `C-G=OK 0.7MΩ / NG 78Ω`; `C-E=OK 0.7MΩ / NG 0.2Ω`; `G-E=OK 30kΩ / NG 78Ω`. Investigation chính ghi `Q1 bị Short`. Nguồn file: KTD-2025-05-0540-Iris2024-C34-A1- C6770.xlsx

## CÂU HỎI 3039
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较Q1和Q403... Q1和Q2的C-E测量值。
- Cách hỏi: so sánh
- Hỏi: Q1与Q2的C-E OK/NG值分别是什么？
- Đáp: Q1 C-E=`OK 0.7MΩ / NG 0.2Ω`；Q2 C-E=`OK 30kΩ / NG 3.9kΩ`。这些OK/NG标签由源文件自身定义。 Nguồn file: KTD-2025-05-0540-Iris2024-C34-A1- C6770.xlsx

## CÂU HỎI 3040
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 表内の値から報告書にないShort発生原因を作らないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: Q1の抵抗値からShortの根本原因や交換対策まで追加できますか。
- Đáp: できません。ファイルはQ1 ShortとOK/NG抵抗値を記録していますが、Short発生の根本原因や具体的対策は記載していません。 Nguồn file: KTD-2025-05-0540-Iris2024-C34-A1- C6770.xlsx

## CÂU HỎI 3041
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Tablet không cảm ứng và kỹ sư xác nhận lại kết quả đo FPC.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: FPC 1-3 đo `Open` với OK=`240Ω`, còn 2-4 đo `open` với OK=`0.8kΩ`, đúng không?
- Đáp: Đúng. Đây là các giá trị được file tự ghi và định nghĩa OK tương ứng. Nguồn file: KTD-2025-03-0230-Iris2024-C34-Operation-Cảm ứng bất thường.xlsx

## CÂU HỎI 3042
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认报告对FPC与Panel接触的判断。
- Cách hỏi: trực tiếp
- Hỏi: 文件对FPC与触摸Panel连接作出了什么判断？
- Đáp: 报告记录检查 `2/4pcs` 时，触碰FPC与Panel连接附近后电阻值发生变化，因此 `判断FPC与Panel接触不良`。 Nguồn file: KTD-2025-03-0230-Iris2024-C34-Operation-Cảm ứng bất thường.xlsx

## CÂU HỎI 3043
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: タッチ反応不良時に外観と抵抗変化を順番に確認している。
- Cách hỏi: tình huống
- Hỏi: このケースでは外観とFPC付近を触った時の抵抗値について何が記載されていますか。
- Đáp: 外観は `異常なし`。確認した2/4pcsではFPCとPanel接続付近に触れると抵抗値が変化し、ファイルは接触不良と判断しています。 Nguồn file: KTD-2025-03-0230-Iris2024-C34-Operation-Cảm ứng bất thường.xlsx

## CÂU HỎI 3044
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: LCD không hiển thị size giấy trên ISU và kỹ sư phân biệt hiện tượng với kết quả ngoại quan.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng trên máy và kết quả điều tra tại YC2 là gì?
- Đáp: Hiện tượng là `LCD không hiển thị Size giấy trên ISU`; Investigation ghi `có dị vật dạng thiếc trong YC2`. Nguồn file: KTD-2025-07-0802-Iris2024-C34-A6-Không nhận biết size giấy.xlsx

## CÂU HỎI 3045
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现YC2内部有锡状异物，但报告未给出后续维修方法。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以根据YC2内有锡状异物自行增加清洁或更换Connector对策吗？
- Đáp: 不可以。文件只记录 `YC2内部有异物`，没有写清洁方法、Connector更换或其它对策。 Nguồn file: KTD-2025-07-0802-Iris2024-C34-A6-Không nhận biết size giấy.xlsx

## CÂU HỎI 3046
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 紙Size表示不良ケースの対象基板を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 対象は `PWB CCD ASSY`、品番-Rev=`302XD01410-1`、Line=`C34-A6` ですね。
- Đáp: はい。S.No=`2XD-0-5618`、Supplier=`TAISHODO HONG KONG CO LIMITED`、Quantity=`1` です。 Nguồn file: KTD-2025-07-0802-Iris2024-C34-A6-Không nhận biết size giấy.xlsx

## CÂU HỎI 3047
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Báo cáo có 7 LCD không sáng nhưng trường Investigation chính chưa được điền.
- Cách hỏi: trực tiếp
- Hỏi: File ghi số lượng và nội dung lỗi chính như thế nào?
- Đáp: Model=`IRIS 2024`, Item=`LCD OPERATION`, Quantity=`7`; Contents of defect và Status đều ghi `Màn hình Panel không sáng / Panel画面が不点灯`. Trường Investigation chính là **Raw value: ô trống**. Nguồn file: KTD-2025-01-0018-IRIS2024-C34-operation màn hình k sáng.xlsx

## CÂU HỎI 3048
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看附表中的GND电阻，但表格没有OK/NG定义。
- Cách hỏi: tình huống
- Hỏi: S/N `1176C-240811-2A0120` 的pin14和pin15记录值是多少？
- Đáp: pin14=`100,7`，pin15=`9,3`。源表只写 `resistance value with GND`，没有给这些值标注OK/NG，因此不能自行赋值判定。 Nguồn file: KTD-2025-01-0018-IRIS2024-C34-operation màn hình k sáng.xlsx

## CÂU HỎI 3049
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Investigation空欄と後段の測定表を混同しないよう整理している。
- Cách hỏi: so sánh
- Hỏi: メインのInvestigation欄と後段の抵抗測定表はどう扱うべきですか。
- Đáp: Investigation欄は **Raw value: ô trống** です。一方、後段には各S/N・pinのGND間抵抗値がありますが、OK/NG定義や原因結論はありません。測定値だけから原因を追加しません。 Nguồn file: KTD-2025-01-0018-IRIS2024-C34-operation màn hình k sáng.xlsx

## CÂU HỎI 3050
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Ảnh trên giấy dày và bì thư bị nhạt màu đen, đồng thời file có thông tin lịch sử từ Partner.
- Cách hỏi: xử lý sự cố
- Hỏi: Có thể kết luận tĩnh điện là nguyên nhân của chính case hiện tại không?
- Đáp: Không nên nâng thành kết luận riêng cho case hiện tại. File ghi IC101 pin3-SG bất thường với OK=`6.6M`, NG=`3.1M`, rồi nêu trạng thái NG giống lỗi từng phát sinh trước đó và **kết quả phân tích từ Partner của lỗi trước đó** là tĩnh điện làm hỏng IC101. Nguồn file: KTD-2025-07-0745-Iris2024-C35-A8.5-Hình ảnh bất thường.xlsx

## CÂU HỎI 3051
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认IC101测量值和历史原因信息的层级。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 当前报告实测是IC101 pin3-SG `OK=6.6M、NG=3.1M`，而“静电损坏IC101”来自以前类似故障的Partner分析，对吗？
- Đáp: 对。应保持这个信息层级，不能把历史分析自动改写成本案例已经独立确认的根因。 Nguồn file: KTD-2025-07-0745-Iris2024-C35-A8.5-Hình ảnh bất thường.xlsx

## CÂU HỎI 3052
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 画像異常の発生条件を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: どのような印刷条件で、どのような画像異常が出ていますか。
- Đáp: `厚紙や封筒に印刷すると、画像が薄い黒で表示された` と記載されています。 Nguồn file: KTD-2025-07-0745-Iris2024-C35-A8.5-Hình ảnh bất thường.xlsx

## CÂU HỎI 3053
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Khi mở túi linh kiện CIS, kỹ sư phát hiện phần chốt cố định bị gãy.
- Cách hỏi: tình huống
- Hỏi: Ngoại quan và kết quả lọc hàng được ghi như thế nào?
- Đáp: Ngoại quan phát hiện `1 đầu chốt bị gãy rơi bên trong túi bóng đựng linh kiện`; kết quả lọc hàng tại KDTVN=`NG=0/80 pcs`. Nguồn file: KTD-2025-10-1148-DP Iris2020-C2D-Assy-.xlsx

## CÂU HỎI 3054
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较单个不良现品与库存筛选结果。
- Cách hỏi: so sánh
- Hỏi: 当前不良品与库存筛选结果分别是什么？
- Đáp: 当前不良品确认树脂固定pin前端有 `1处折断`；KDTVN筛选结果为 `NG=0/80 pcs`。这个`0`保持源文件原始结果，不重新推算其它不良率。 Nguồn file: KTD-2025-10-1148-DP Iris2020-C2D-Assy-.xlsx

## CÂU HỎI 3055
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 樹脂ストッパー破損の後続対応をソースどおり確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: ファイルに記載された後続対応は何ですか。
- Đáp: `不具合情報をまとめてPartnerへ連絡し、在庫を管理する` 内容です。破損原因や修理方法は記載されていません。 Nguồn file: KTD-2025-10-1148-DP Iris2020-C2D-Assy-.xlsx

## CÂU HỎI 3056
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy không lên nguồn và ngoại quan thấy board bị hư hỏng cơ khí.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File xác nhận mất 5V và góc board bị nứt/vỡ, nhưng chưa kết luận thao tác hay vận chuyển là nguyên nhân, đúng không?
- Đáp: Đúng. File chỉ ghi liên lạc QC để xác nhận lại `thao tác và vận chuyển trong kho`; chưa xác định một trong hai là nguyên nhân đã được chứng minh. Nguồn file: KTD-2025-07-0784-Iris2024-C33-A1-Không lên nguồn.xlsx

## CÂU HỎI 3057
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认低压单元的不良现象。
- Cách hỏi: trực tiếp
- Hỏi: 调查中确认了哪两项主要异常？
- Đáp: 确认 `5V电压消失`，并在外观检查中发现 `基板角部有裂纹/破损`。 Nguồn file: KTD-2025-07-0784-Iris2024-C33-A1-Không lên nguồn.xlsx

## CÂU HỎI 3058
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 基板角破損を確認した後、報告書に記載された確認依頼だけを参照している。
- Cách hỏi: tình huống
- Hỏi: このケースではQCへ何を確認するよう依頼していますか。
- Đáp: `作業手順および倉庫内での搬送状況` を再確認するよう依頼しています。どちらが原因かは確定していません。 Nguồn file: KTD-2025-07-0784-Iris2024-C33-A1-Không lên nguồn.xlsx

## CÂU HỎI 3059
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: LCD có vùng sáng bất thường nhưng báo cáo chưa có phân tích linh kiện.
- Cách hỏi: so sánh
- Hỏi: File ghi gì ở phần hiện tượng và phần Investigation?
- Đáp: Hiện tượng là `Vòm sáng màn hình / 画面は光点がある`; Investigation chỉ ghi `tổng hợp thông tin và liên lạc với partner để điều tra`. Không có nguyên nhân linh kiện được xác định. Nguồn file: KTD-2025-07-0680-Iris2024-C34-Operation-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3060
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理LCD亮点/光斑，但Partner分析尚未写入报告。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以自行补充LCD内部故障原因或更换对策吗？
- Đáp: 不可以。文件只有 `画面有光点` 和 `汇总信息并联系Partner调查`，没有具体根因或维修对策。 Nguồn file: KTD-2025-07-0680-Iris2024-C34-Operation-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 3061
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: LCD表示異常ケースの基本情報を最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 対象は `LCD OPERATION`、品番-Rev=`302XC45060-1`、Line=`C34-Operation`、Machine No.は空欄ですね。
- Đáp: はい。Machine No. は **Raw value: ô trống**。S.No=`1176C-250216-2A0122`、Quantity=`1` です。 Nguồn file: KTD-2025-07-0680-Iris2024-C34-Operation-Màn hình hiển thị bất thường.xlsx
