# Mẻ 82 — Điều-tra-lỗi — Q3212–Q3241 (30 cặp)

- Ngày: 2026-10-05 ~03:01 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt; đọc được đủ 10/10 file
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ — giữ nguyên `OL`, `Open`, `0.5`, ô trống, các giá trị `0v`; không tự chuẩn hóa; OK/NG chỉ dùng khi chính file định nghĩa
- Điểm phân biệt case:
  - 2 case C0980 ĐỘC LẬP trong cùng mẻ: Q3215–3217 (KTD-2025-04-0435, IC401 pin5 FB điện trở OK=`18kΩ`/NG=`55.5Ω`, điện áp NG=`0v`/OK=`4.1V`; pin14 NG=`10.2v`/OK=`187V`, pin15 NG=`8.8v`/OK=`178V`, pin16 NG=`8.8v`/OK=`182V`; Lot IC401=`MC25207SG A30949`) vs Q3218–3220 (KTD-2025-05-0482, thay IC401 → OK, crosscheck IC401 lỗi sang bản mạch khác → tái hiện; Lot IC401=`MCZ5207SG A30979`; IC401 đơn pin2=`OL`, pin14–16=`OL`)
  - KTD-2025-07-0664 (C6770): PWB IH 100, line=`C35-A2`, Quantity=`1`; Q1 C-G=`OK 0.7MΩ / NG 73Ω`, C-E=`OK 0.7MΩ / NG 0.1Ω`, G-E=`OK 30kΩ / NG 73Ω`; Q2 C-G=`OK 320kΩ / NG 61kΩ`, C-E=`OK 30kΩ / NG OL`, G-E=`OK 30kΩ / NG 30kΩ`
  - KTD-2025-02-0125 (WTB): không có title block trong phần đọc được — chỉ dùng đúng bảng V1–V4 (V1=`0.66–0.84V`, V2=`2.66–3.34V`, V3=`1.4–1.94V`, V4=`2.16–2.74V`); file tự ghi `Check jig NG V3 = 1.31V`; V3=`満杯の廃トナーボックス治具`
  - KTD-2025-09-0932 (NG Fax, DP Iris2020, UNIT FAX NCU (U)): kiểm tra âm thanh Fax nhưng không nghe thấy; Investigation chỉ ghi ngoại quan không bất thường — không tự thêm nguyên nhân IC/Speaker
  - KTD-2025-07-0785: PWB CCD ASSY, Quantity=`4`, bản mạch không được in Lot/No; Investigation=tổng hợp thông tin và liên lạc Partner; Contents of defect và Machine No. ô trống
  - KTD-2025-08-0931 (Jam9002): PWB ASSY CONTROLLER WITH SOFTWARE 3V2V301010-6; U9 bị cầu hàn pin 2,3,4; Serial=`05815`, Quantity=`1`, Line=`C2B`
  - KTD-2025-03-0332 (sập nguồn): mất 5V và 24V; F001 đứt; Q107 short cả 3 cực; Q107 D-G=`OK 2.5M / NG 1.9Ω`, D-S=`OK 39.5k / NG 0.1Ω`, G-S=`OK 3.3k / NG 1.9Ω`
  - KTD-2024-11-1586 (C3200): PWB ENGINE ASSY 3V2XD01540-10; `12V5_F1` bị short; C210 short=`0.2 ohm`; S.No=`D7C104YD9137`
  - KTD-2025-04-0402 (C6950): PWB IH 200; U6 pin12 bất thường `OK=240k Ohm / NG=33k Ohm`; thay U6 → OK; file ghi rõ nguyên nhân do U6; Reappear rate giữ Raw value `0.5`
- Không suy diễn NG Fax, board thiếu Lot/No, U9 cầu hàn, Q107 short hoặc C210 short thành nguyên nhân ngoài báo cáo; IC401/U6 chỉ nêu ở mức kết luận mà chính file hỗ trợ qua thay thế/crosscheck

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 3212
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C6770 và kỹ sư cần xác nhận đúng bảng điện trở Q1.
- Cách hỏi: trực tiếp
- Hỏi: Q1 được file định nghĩa OK/NG thế nào tại C-G, C-E và G-E?
- Đáp: Q1 C-G=`OK 0.7MΩ / NG 73Ω`; C-E=`OK 0.7MΩ / NG 0.1Ω`; G-E=`OK 30kΩ / NG 73Ω`. Investigation ghi Q1 bị short. Nguồn file: KTD-2025-07-0664-Iris2024-C35-A2-C6770.xlsx

## CÂU HỎI 3213
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师需要核对同一C6770案例中Q2的判定值。
- Cách hỏi: tình huống
- Hỏi: Q2的C-G、C-E、G-E分别是多少？
- Đáp: C-G=`OK 320kΩ / NG 61kΩ`；C-E=`OK 30kΩ / NG OL`；G-E=`OK 30kΩ / NG 30kΩ`。这些OK/NG由源文件明确定义。 Nguồn file: KTD-2025-07-0664-Iris2024-C35-A2-C6770.xlsx

## CÂU HỎI 3215
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C0980, mất 24V và kỹ sư kiểm tra IC401.
- Cách hỏi: xử lý sự cố
- Hỏi: Pin5(FB) của IC401 được file ghi điện trở và điện áp thế nào?
- Đáp: Điện trở pin5(FB)=`OK 18kΩ / NG 55.5Ω`; điện áp pin5=`NG 0v / OK 4.1V`. File ghi ngoại quan không bất thường. Nguồn file: KTD-2025-04-0435-Iris2024-C33-A1-C0980.xlsx

## CÂU HỎI 3216
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认IC401高压侧测量数据。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: IC401 pin14的电压是NG=`10.2v`、OK=`187V`，pin15是NG=`8.8v`、OK=`178V`，对吗？
- Đáp: 对。pin16还记录为 NG=`8.8v`、OK=`182V`。 Nguồn file: KTD-2025-04-0435-Iris2024-C33-A1-C0980.xlsx

## CÂU HỎI 3217
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C0980ケースのIC401情報を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: IC401のLotとpin11の電圧値は何ですか。
- Đáp: Lot=`MC25207SG A30949`。pin11は NG=`0v`、OK=`4.6V` です。 Nguồn file: KTD-2025-04-0435-Iris2024-C33-A1-C0980.xlsx

## CÂU HỎI 3218
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Một case C0980 khác được crosscheck trực tiếp IC401.
- Cách hỏi: tình huống
- Hỏi: Sau khi thay và crosscheck IC401, file ghi kết quả thế nào?
- Đáp: Thay IC401 → kết quả `OK`; crosscheck IC401 lỗi sang bản mạch khác → tái hiện được lỗi. Lot IC401=`MCZ5207SG A30979`. Nguồn file: KTD-2025-05-0482-Iris2024-C33-A1.2-C0980.xlsx

## CÂU HỎI 3219
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较板上IC401电阻检查和Crosscheck结果。
- Cách hỏi: so sánh
- Hỏi: 板上电阻检查与IC401 Crosscheck结果分别是什么？
- Đáp: 文件写IC401各pin电阻检查无异常；但更换IC401后=`OK`，把原IC401 Crosscheck到其它板后=故障再现。 Nguồn file: KTD-2025-05-0482-Iris2024-C33-A1.2-C0980.xlsx

## CÂU HỎI 3220
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: IC401単品測定値から追加の故障メカニズムを作らないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: IC401単品pin2=`OL`、pin14～16=`OL`という値から、追加の故障メカニズムを作れますか。
- Đáp: できません。ファイルで確認されているのはIC401交換後=`OK`、Crosscheckで不具合再現までです。追加の内部故障メカニズムは記載されていません。 Nguồn file: KTD-2025-05-0482-Iris2024-C33-A1.2-C0980.xlsx

## CÂU HỎI 3221
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: File WTB chỉ cung cấp bảng tiêu chuẩn và giá trị jig, không có title block trong phần đọc được.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: V3 có tiêu chuẩn=`1.4–1.94V` nhưng giá trị Check jig được ghi=`1.31V`, đúng không?
- Đáp: Đúng. File tự ghi `Check jig NG V3 = 1.31V`; vì chính nguồn gắn nhãn NG nên có thể giữ nhãn này. Nguồn file: KTD-2025-02-0125-C34 Iris 2024 NG V3 jig WTB.xlsx

## CÂU HỎI 3222
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接核对WTB四种状态的电压规格。
- Cách hỏi: trực tiếp
- Hỏi: V1、V2、V3、V4的规格范围分别是多少？
- Đáp: V1=`0.66–0.84V`；V2=`2.66–3.34V`；V3=`1.4–1.94V`；V4=`2.16–2.74V`。 Nguồn file: KTD-2025-02-0125-C34 Iris 2024 NG V3 jig WTB.xlsx

## CÂU HỎI 3223
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: WTB状態ごとのV1～V4条件を区別している。
- Cách hỏi: tình huống
- Hỏi: V3はどの条件で、V1とV4はどの条件ですか。
- Đáp: V3=`満杯の廃トナーボックス治具` を使用。V1=`廃トナーボックスなし・WTB cover開`、V4=`廃トナーボックスあり・WTB cover閉` です。 Nguồn file: KTD-2025-02-0125-C34 Iris 2024 NG V3 jig WTB.xlsx

## CÂU HỎI 3224
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Có nhiều case NG Fax nên kỹ sư cần phân biệt case này.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng Fax và kết quả Investigation của case này khác nhau thế nào?
- Đáp: Hiện tượng là kiểm tra âm thanh Fax nhưng không nghe thấy âm thanh; Investigation chỉ ghi ngoại quan không bất thường. Nguồn file: KTD-2025-09-0932-DP Iris2020-C2E-NG Fax.xlsx

## CÂU HỎI 3225
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师遇到Fax无声音，但报告只有外观结果。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以自行追加IC、Speaker或Fax板故障原因吗？
- Đáp: 不可以。文件只记录Fax声音检查时听不到声音和外观检查无异常，没有具体部品原因或维修对策。 Nguồn file: KTD-2025-09-0932-DP Iris2020-C2E-NG Fax.xlsx

## CÂU HỎI 3226
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: NG Faxケースの基本情報を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Model=`DP Iris2020`、Item=`UNIT FAX NCU (U)`、Line=`C2E`、Quantity=`1` ですね。
- Đáp: はい。S.No(Lot)は `R0027401 / 52R0027401B / 2401001749`、Machine No.は Raw value: ô trống です。 Nguồn file: KTD-2025-09-0932-DP Iris2020-C2E-NG Fax.xlsx

## CÂU HỎI 3227
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: PWB CCD ASSY không được in Lot/No tại công đoạn ISU.
- Cách hỏi: trực tiếp
- Hỏi: File ghi hiện tượng, số lượng và hành động tiếp theo thế nào?
- Đáp: Status=`Bản mạch không được in Lot/No`; Quantity=`4`; Investigation=`tổng hợp thông tin và liên lạc Partner`. Nguồn file: KTD-2025-07-0785-Iris2024-C33-ISU-.xlsx

## CÂU HỎI 3228
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现4块板没有打印Lot/No。
- Cách hỏi: tình huống
- Hỏi: 文件是否已经记录为什么没有打印Lot/No？
- Đáp: 没有。文件只记录4pcs板未打印Lot/No，后续为汇总信息并联系Partner调查，没有写明原因。 Nguồn file: KTD-2025-07-0785-Iris2024-C33-ISU-.xlsx

## CÂU HỎI 3229
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 空欄のContents of defectとMachine No.を入力済み項目と比較している。
- Cách hỏi: so sánh
- Hỏi: この報告で入力済みのS.Noと空欄項目は何ですか。
- Đáp: S.No=`2XC05616`。Contents of defectとMachine No.は Raw value: ô trống です。 Nguồn file: KTD-2025-07-0785-Iris2024-C33-ISU-.xlsx

## CÂU HỎI 3230
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kiểm tra âm thanh lạ thì máy báo Jam9002 và phát hiện cầu hàn.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi bất thường tại U9 và hành động tiếp theo thế nào?
- Đáp: Ngoại quan phát hiện U9 bị cầu hàn pin 2,3,4; hành động tiếp theo là tổng hợp thông tin liên lạc Partner. Nguồn file: KTD-2025-08-0931-DP Iris2020-C2B-Jam9002.xlsx

## CÂU HỎI 3231
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认Jam9002案例是否读对了U9位置。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 外观确认的是U9 pin2、3、4焊锡桥接，Serial=`05815`、Quantity=`1`，对吗？
- Đáp: 对。Line=`C2B`，Model=`DP Iris2020`。 Nguồn file: KTD-2025-08-0931-DP Iris2020-C2B-Jam9002.xlsx

## CÂU HỎI 3232
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Jam9002ケースの対象部品情報を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: Itemと品番-Revは何ですか。
- Đáp: Item=`PWB ASSY CONTROLLER WITH SOFTWARE`、Item code-Rev=`3V2V301010-6` です。 Nguồn file: KTD-2025-08-0931-DP Iris2020-C2B-Jam9002.xlsx

## CÂU HỎI 3233
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Khi kiểm tra Cassette, máy sập nguồn và mất cả hai đường điện áp.
- Cách hỏi: tình huống
- Hỏi: File ghi những bất thường nào về nguồn, F001 và Q107?
- Đáp: Mất điện áp `5V` và `24V`; F001 bị đứt; Q107 short cả 3 cực với nhau. Ngoại quan=`không bất thường`. Nguồn file: KTD-2025-03-0332-Iris2024-C33-A5-Máy sập nguồn.xlsx

## CÂU HỎI 3234
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较Q107三个组合的OK/NG阻值。
- Cách hỏi: so sánh
- Hỏi: Q107的D-G、D-S、G-S分别怎样定义OK/NG？
- Đáp: D-G=`OK 2.5M / NG 1.9Ω`；D-S=`OK 39.5k / NG 0.1Ω`；G-S=`OK 3.3k / NG 1.9Ω`。 Nguồn file: KTD-2025-03-0332-Iris2024-C33-A5-Máy sập nguồn.xlsx

## CÂU HỎI 3235
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Q107 Shortの測定値から未記載の発生原因を作らないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: Q107が三端子Shortだったことから、Short発生の根本原因まで追加できますか。
- Đáp: できません。ファイルは5V/24V消失、F001断線、Q107三端子Short、およびOK/NG抵抗値までを記載しています。 Nguồn file: KTD-2025-03-0332-Iris2024-C33-A5-Máy sập nguồn.xlsx

## CÂU HỎI 3236
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Iris2020 bật máy báo C3200 và kỹ sư cần xác nhận đúng kết quả short.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: File ghi `12V5_F1` bị short và C210 short=`0.2 ohm`, còn ngoại quan không bất thường, đúng không?
- Đáp: Đúng. Đây là các kết quả Investigation được ghi trực tiếp trong file. Machine No. là Raw value: ô trống. Nguồn file: KTD-2024-11-1586-Iris2020-C34-A1-C3200.xlsx

## CÂU HỎI 3237
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接核对C3200案例的对象基板。
- Cách hỏi: trực tiếp
- Hỏi: Item、品号-Rev和S.No是什么？
- Đáp: Item=`PWB ENGINE ASSY WITH SOFTWARE`；Item code-Rev=`3V2XD01540-10`；S.No=`D7C104YD9137`。 Nguồn file: KTD-2024-11-1586-Iris2020-C34-A1-C3200.xlsx

## CÂU HỎI 3238
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 12V5_F1とC210の確認結果をライン現象と分けて整理している。
- Cách hỏi: tình huống
- Hỏi: 電源ONでC3200が出た場合、この報告では何を確認していますか。
- Đáp: `12V5_F1 Short`、外観=`異常なし`、C210=`Short 0.2 ohm` を確認しています。 Nguồn file: KTD-2024-11-1586-Iris2020-C34-A1-C3200.xlsx

## CÂU HỎI 3239
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Case C6950 có kết quả thay U6 và kết luận nguyên nhân rõ trong file.
- Cách hỏi: so sánh
- Hỏi: Trước và sau khi thay U6, file ghi gì?
- Đáp: Trước thay, U6 pin12 bất thường với `OK=240k Ohm / NG=33k Ohm`; sau khi thay U6 → `OK`. File ghi rõ nguyên nhân do U6. Nguồn file: KTD-2025-04-0402-Iris2024-C35-A3-C6950.xlsx

## CÂU HỎI 3240
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师处理连接Option治具后出现C6950的案例。
- Cách hỏi: xử lý sự cố
- Hỏi: 本案例是否可以把U6作为报告明确结论，而不是推测？
- Đáp: 可以。源文件明确记录 U6 pin12=`OK 240k Ohm / NG 33k Ohm`，更换U6后=`OK`，并直接写明原因是U6部品。 Nguồn file: KTD-2025-04-0402-Iris2024-C35-A3-C6950.xlsx

## CÂU HỎI 3241
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C6950ケースのRaw valueと基本情報を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Reappear rate=`0.5`、Machine No.は空欄、S.No=`69E0052A9562` ですね。
- Đáp: はい。Reappear rateは Raw value `0.5` です。Machine No.は Raw value: ô trống です。 Nguồn file: KTD-2025-04-0402-Iris2024-C35-A3-C6950.xlsx
