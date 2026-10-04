# Mẻ 70 — Điều-tra-lỗi — Q2852–Q2881 (30 cặp)

- Ngày: 2026-10-05 ~01:43 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ (Raw value 0, `-`, ô trống giữ nguyên; OK/NG chỉ dùng khi nguồn định nghĩa, vd BAT OK=3.3V)
- Hai case Iris2020 giữ đúng Model=DP Iris2020, không đổi thành Iris2024
- Điểm phân biệt quan trọng: mẻ này có 2 case C6770 ĐỘC LẬP — Q2852–2854 (KTD-2026-01-0096, line C34-A1): Q1 bị Short; Q2876–2878 (KTD-2026-08-0790, line C35-A1, Quantity=2): hàn giả pin 4 của T1. Không trộn kết quả hai case.

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 2852
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần tra đúng case C6770 của IH100 tại C34-A1.
- Cách hỏi: trực tiếp
- Hỏi: Hiện tượng và kết quả điều tra của case này là gì?
- Đáp: Sau khi lắp đồ gá hộp mực thải và bật máy, máy báo `C6770`. Mục điều tra ghi `Linh kiện Q1 bị Short`. Nguồn file: KTD-2026-01-0096-Iris2024-C34-A1-C6770.xlsx

## CÂU HỎI 2853
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师安装废粉盒治具后出现C6770，需要参考历史报告。
- Cách hỏi: tình huống
- Hỏi: 该报告对Q1记录了什么调查结果？
- Đáp: 文件记录 `Q1がShortされた / Q1 bị Short`。没有另外记载更深层的原因或维修对策。 Nguồn file: KTD-2026-01-0096-Iris2024-C34-A1-C6770.xlsx

## CÂU HỎI 2854
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C6770ケースの入力情報と未入力項目を区別している。
- Cách hỏi: so sánh
- Hỏi: このケースで記載されている基板情報と空欄の項目は何ですか。
- Đáp: Item name=`PWB IH 100 ASSY WITH SOFTWARE`、Item code-Rev=`30C2G01090-4`、S.No=`69D005YF4677`。Machine No. は **Raw value: ô trống** です。 Nguồn file: KTD-2026-01-0096-Iris2024-C34-A1-C6770.xlsx

## CÂU HỎI 2855
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Aging phát sinh error56 trên nhiều máy và kỹ sư cần bám đúng kết quả điều tra.
- Cách hỏi: xử lý sự cố
- Hỏi: Báo cáo ghi hiện tượng sau error56 và kết quả điều tra linh kiện nào?
- Đáp: File ghi `In hình ảnh mờ nhạt` và `đứt dây đồng linh kiện T301`. Không có đối sách cụ thể khác trong phần báo cáo đọc được. Nguồn file: KTD-2026-06-0639-Iris2024-C34-C35-Error56.xlsx

## CÂU HỎI 2856
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认Error56案例的发生数量与对象产品。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 该案例对象为 `UNIT HIGH VOLTAGE MAIN`、Quantity=`7`、Line=`C34-C35`，对吗？
- Đáp: 对。Item code-Rev=`3V2L745042-2`，报告列出了7个S.No；Machine No. 为 **Raw value: ô trống**。 Nguồn file: KTD-2026-06-0639-Iris2024-C34-C35-Error56.xlsx

## CÂU HỎI 2857
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Aging時のエラー表示と調査結果を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: ラインでの発生現象とT301の調査結果は何ですか。
- Đáp: Aging中に `error56` が発生し、調査結果には `画像が薄い`、`T301部品の銅線断線` と記載されています。 Nguồn file: KTD-2026-06-0639-Iris2024-C34-C35-Error56.xlsx

## CÂU HỎI 2858
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: LCD Operation hiển thị trắng khi kiểm tra jig nhưng báo cáo chưa có kết quả điều tra.
- Cách hỏi: tình huống
- Hỏi: File ghi hiện tượng gì khi kiểm tra jig và phần điều tra có nội dung gì?
- Đáp: Hiện tượng là `Kiểm tra đồ gá, màn hình LCD Operation hiển thị màu trắng`. Trường Investigation content and results là **Raw value: ô trống**, nên không có nguyên nhân hoặc đối sách để bổ sung. Nguồn file: KTD-2026-04-0334-Iris2024-C34-Operation-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 2859
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较已填写的故障信息和未填写的调查结果。
- Cách hỏi: so sánh
- Hỏi: 该文件中哪些故障信息有填写，而调查结果是什么状态？
- Đáp: 已填写 Model=`Iris2024`、Item=`LCD OPERATION`、品号-Rev=`302XC45060-1`、Quantity=`84`，故障现象为治具检查时LCD白屏；调查结果栏为 **Raw value: ô trống**。 Nguồn file: KTD-2026-04-0334-Iris2024-C34-Operation-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 2860
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 調査結果が未入力のケースで原因を作らないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: Investigation欄が空欄の場合、LCDや基板の故障原因を推測して追加できますか。
- Đáp: できません。Investigation欄は **Raw value: ô trống** なので、ソースが記載していない原因・対策は追加しません。 Nguồn file: KTD-2026-04-0334-Iris2024-C34-Operation-Màn hình hiển thị bất thường.xlsx

## CÂU HỎI 2861
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận lại case màn hình không sáng của Main board.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Crosscheck Main không tái hiện lỗi, nhưng ngoại quan YC13 pin 4,5,6,7 được ghi bất thường, đúng không?
- Đáp: Đúng. File ghi `crosscheck main thì không tái hiện được lỗi` và `ngoại quan YC13 trên main pin 4,5,6,7 bất thường`. Nguồn file: KTD-2025-08-0912-Iris2024-C34-A1-Màn hình không sáng.xlsx

## CÂU HỎI 2862
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认该白屏案例的对象板信息。
- Cách hỏi: trực tiếp
- Hỏi: 该案例的Item、品号-Rev和S.No是什么？
- Đáp: Item=`PWB MAIN ASSY WITH SOFTWARE E`；Item code-Rev=`3VC2L01010-4`；S.No=`6HY1057E2940`。Machine No. 为 **Raw value: ô trống**。 Nguồn file: KTD-2025-08-0912-Iris2024-C34-A1-Màn hình không sáng.xlsx

## CÂU HỎI 2863
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 電源ON後にLCDが点灯しない場合、過去ケースの確認内容を参照している。
- Cách hỏi: tình huống
- Hỏi: このケースではMainをクロスチェックした結果とYC13の外観結果はどう記録されていますか。
- Đáp: Mainクロスチェックでは不具合を再現せず、`YC13の pin4,5,6,7` が異常と記録されています。これ以上の原因は記載されていません。 Nguồn file: KTD-2025-08-0912-Iris2024-C34-A1-Màn hình không sáng.xlsx

## CÂU HỎI 2864
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Ảnh RCG trước U950 bất thường và kỹ sư cần phân biệt hiện tượng ảnh với kết quả kiểm tra tín hiệu.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng ảnh và kết quả kiểm tra tín hiệu màu K được ghi khác nhau thế nào?
- Đáp: File ghi `In hình ảnh màu K bất thường`; phần kiểm tra tiếp theo ghi `Tín hiệu sóng màu K bất thường`. Đây là hai nội dung được báo cáo riêng; file không nêu linh kiện nguyên nhân. Nguồn file: KTD-2025-09-0952-Iris2024-C35-A6-Hình ảnh bất thường.xlsx

## CÂU HỎI 2865
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师不能仅凭K色信号异常自行确定损坏零件。
- Cách hỏi: xử lý sự cố
- Hỏi: 报告只写K色波形信号异常时，可以自行补充具体故障元件吗？
- Đáp: 不可以。文件只记录 `K色图像异常` 和 `K色信号检查：异常`，没有给出具体损坏元件或维修对策。 Nguồn file: KTD-2025-09-0952-Iris2024-C35-A6-Hình ảnh bất thường.xlsx

## CÂU HỎI 2866
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 画像異常ケースの対象ユニットを確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 対象は `UNIT HIGH VOLTAGE TRANSFER`、品番-Rev=`302XC45020-5`、Line=`C35-A6` ですね。
- Đáp: はい。S.No=`J3J0057C8162`、Quantity=`1`、Machine No. は **Raw value: ô trống** です。 Nguồn file: KTD-2025-09-0952-Iris2024-C35-A6-Hình ảnh bất thường.xlsx

## CÂU HỎI 2867
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tra đúng case DP Iris2020 C9080 khi chạy U411.
- Cách hỏi: trực tiếp
- Hỏi: Model, hiện tượng và kết quả ngoại quan của case này là gì?
- Đáp: Model=`DP Iris2020`. Khi thực hiện `U411 CIS FA/Chart A` để scan Color Scanner Chart A4, Panel máy thực nghiệm báo `C9080`. Ngoại quan phát hiện `cực Anode của LED2 chưa được hàn`. Nguồn file: KTD-2025-11-1198-DP Iris2020-C2D-A10-C9080.xlsx

## CÂU HỎI 2868
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师执行U411后出现C9080，需要按报告结果检查CIS。
- Cách hỏi: tình huống
- Hỏi: 外观检查在LED2上确认了什么？
- Đáp: 文件记录 `LED2的Anode端子未进行焊接`。报告没有另外记载更深层原因或具体维修步骤。 Nguồn file: KTD-2025-11-1198-DP Iris2020-C2D-A10-C9080.xlsx

## CÂU HỎI 2869
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Iris2024のケースと取り違えないようモデル情報を確認している。
- Cách hỏi: so sánh
- Hỏi: このケースのModelと対象品は何ですか。
- Đáp: Model=`DP Iris2020`、Item name=`CIS`、Item code-Rev=`313TT45010-1` です。Iris2024へ置き換えません。 Nguồn file: KTD-2025-11-1198-DP Iris2020-C2D-A10-C9080.xlsx

## CÂU HỎI 2870
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Case LCD không sáng có điều kiện tái hiện đặc biệt nên kỹ sư cần giữ đúng dữ liệu gốc.
- Cách hỏi: xử lý sự cố
- Hỏi: Kết quả tái hiện khi bật/tắt bình thường và khi giữ SW rồi cắm AC cord khác nhau thế nào?
- Đáp: Bật/tắt bình thường `20/20` lần không tái hiện. Khi giữ nút SW và cắm AC cord: `8/10` lần LCD không sáng nhưng LED Job sáng, `2/10` lần hiển thị `F010`. Nguồn file: KTD-2025-11-1181-Iris2024-C35-A5-Màn hình không sáng.xlsx

## CÂU HỎI 2871
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师复核报告中的Raw value字段。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 该报告的Reappear rate是Raw value 0，而Item code=`-`、Item name/S.No/Supplier为空，对吗？
- Đáp: 对。Reappear rate 保留为 **Raw value 0**；Item name、S.No、Supplier 保留为 **Raw value: ô trống**，不能推测补充。 Nguồn file: KTD-2025-11-1181-Iris2024-C35-A5-Màn hình không sáng.xlsx

## CÂU HỎI 2872
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 通常操作と特殊な再現操作の結果を比較している。
- Cách hỏi: trực tiếp
- Hỏi: ファイルは再現結果からどのような操作状態だったと判断していますか。
- Đáp: `SWボタンを押し続けたままACコードを接続したと考えられる` と記載されています。これは報告書自身の判断です。 Nguồn file: KTD-2025-11-1181-Iris2024-C35-A5-Màn hình không sáng.xlsx

## CÂU HỎI 2873
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đo BAT sau khi bật máy báo C0840.
- Cách hỏi: tình huống
- Hỏi: File ghi điện áp BAT thực tế và giá trị OK là bao nhiêu?
- Đáp: Điện áp `BAT=0.6V`; file tự định nghĩa `OK: 3.3V`. Nguồn file: KTD-2026-02-0150-Iris2024-C34-A1-C0840.xlsx

## CÂU HỎI 2874
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较报告中的实际BAT电压和OK参考值。
- Cách hỏi: so sánh
- Hỏi: BAT测量值与文件定义的OK值分别是多少？
- Đáp: 实际记录=`0.6V`，文件定义的OK值=`3.3V`。文件没有进一步写明具体损坏元件。 Nguồn file: KTD-2026-02-0150-Iris2024-C34-A1-C0840.xlsx

## CÂU HỎI 2875
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: BAT 0.6Vという単一測定から原因部品を決めないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `BAT=0.6V` だけからBatteryやMAIN基板の特定部品を原因と判断できますか。
- Đáp: できません。ファイルには `BAT=0.6V`、`OK=3.3V` と記載されているだけで、原因部品や対策は記載されていません。 Nguồn file: KTD-2026-02-0150-Iris2024-C34-A1-C0840.xlsx

## CÂU HỎI 2876
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Có nhiều báo cáo C6770 nên kỹ sư cần phân biệt case có Quantity=2.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Case này có Quantity=`2` và kết quả điều tra là hàn giả pin4 của T1, đúng không?
- Đáp: Đúng. Model=`Iris2024`, Item=`PWB IH 100 ASSY WITH SOFTWARE`, line=`C35-A1`; kết quả ghi `Hàn giả pin 4 của linh kiện T1`. Nguồn file: KTD-2026-08-0790-Iris2024-C35-A1-C6770.xlsx

## CÂU HỎI 2877
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认本次C6770报告中的两个S.No。
- Cách hỏi: trực tiếp
- Hỏi: 报告列出的两个S.No是什么？
- Đáp: `69D0066J5191` 和 `69D0066J2032`。Quantity=`2`。 Nguồn file: KTD-2026-08-0790-Iris2024-C35-A1-C6770.xlsx

## CÂU HỎI 2878
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 同じC6770でも以前のQ1 Shortケースと今回のT1半田不良ケースを区別している。
- Cách hỏi: tình huống
- Hỏi: 今回のC6770では何が調査結果として記載されていますか。
- Đáp: `T1の4ピンが半田不良` と記載されています。Q1 Shortは別ケースの結果なので、このファイルには混在させません。 Nguồn file: KTD-2026-08-0790-Iris2024-C35-A1-C6770.xlsx

## CÂU HỎI 2879
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần phân biệt case Scan tự động NG của DP Iris2020 với case C9080 khác.
- Cách hỏi: so sánh
- Hỏi: Case này ghi hiện tượng và kết quả crosscheck CIS như thế nào?
- Đáp: Model=`DP Iris2020`. Scan Color Scanner Chart A4 thì PC báo NG; khi crosscheck CIS thì lỗi không tái hiện, sau đó gửi linh kiện CIS sang Partner điều tra. Nguồn file: KTD-2025-10-1075-DP Iris2020-C2D-Scan tự động NG.xlsx

## CÂU HỎI 2880
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师遇到自动Scan NG，但crosscheck没有再现故障。
- Cách hỏi: xử lý sự cố
- Hỏi: 文件已经记录了什么后续处理？可以自行判定CIS故障吗？
- Đáp: 文件记录 `CIS crosscheck不再现故障`，并 `将CIS送往PARTNER调查`。没有明确写CIS就是故障根因，因此不能自行判定。 Nguồn file: KTD-2025-10-1075-DP Iris2020-C2D-Scan tự động NG.xlsx

## CÂU HỎI 2881
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: DP Iris2020ケースの未入力項目を推測で補わないよう確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Model=`DP Iris2020`、Quantity=`3` で、Machine No. とReappear rateは空欄ですね。
- Đáp: はい。Machine No. とReappear rateは **Raw value: ô trống** のまま保持します。Item name=`CIS`、Item code-Rev=`313TT45010-1` です。 Nguồn file: KTD-2025-10-1075-DP Iris2020-C2D-Scan tự động NG.xlsx
