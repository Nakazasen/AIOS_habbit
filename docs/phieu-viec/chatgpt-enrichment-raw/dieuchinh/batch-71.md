# Mẻ 71 — Điều-tra-lỗi — Q2882–Q2911 (30 cặp)

- Ngày: 2026-10-05 ~01:49 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ (Raw value 0, `xxx`, `-`, ô trống giữ nguyên; OK/NG chỉ dùng khi nguồn định nghĩa)
- Chỉ giữ kết luận nguyên nhân khi chính báo cáo xác nhận (U1 trong case SITC NG và C6000); U21 signal, R235, YC2, C192, RA3/C18 không mở rộng thành root cause
- File gốc `KTD-2026-04-0397...C0980.xlsx` được xác nhận TRÙNG KHỚP HOÀN TOÀN nội dung với bản "Copy of" ở mẻ 69 — Q2909–2911 chỉ dùng góc đối chiếu mới, không lặp Q2846–2848

---

## CÂU HỎI 2882
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Aging phát sinh Error56 và kỹ sư cần tra đúng chuỗi kết quả điều tra trong báo cáo.
- Cách hỏi: trực tiếp
- Hỏi: File ghi hiện tượng ảnh, tín hiệu và linh kiện bất thường nào?
- Đáp: File ghi `In nhạt màu hồng`, `Tín hiệu T1(M) bất thường` và linh kiện `R235 bong đầu điện cực`. Nguồn file: KTD-2025-12-1390-Iris2024-C34-A7-Error56.xlsx

## CÂU HỎI 2883
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师在Aging时遇到Error56，需要查看历史报告的实际调查结果。
- Cách hỏi: tình huống
- Hỏi: Aging出现Error56后，文件对T1(M)和R235分别记录了什么？
- Đáp: 文件记录 `T1(M)信号异常`，并发现 `R235部品の電極端子剥離`。没有另外记载具体维修对策。 Nguồn file: KTD-2025-12-1390-Iris2024-C34-A7-Error56.xlsx

## CÂU HỎI 2884
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: ライン現象と調査結果を区別して整理している。
- Cách hỏi: so sánh
- Hỏi: ラインでの発生現象と調査結果はどう違いますか。
- Đáp: ライン現象は Aging中の `error56`。調査結果は `薄いピンク色で印刷`、`T1(M)信号異常`、`R235電極端子剥離` です。 Nguồn file: KTD-2025-12-1390-Iris2024-C34-A7-Error56.xlsx

## CÂU HỎI 2885
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Scan SITC-2 báo nhiều mã NG và kỹ sư cần sử dụng đúng kết luận trong báo cáo.
- Cách hỏi: xử lý sự cố
- Hỏi: File ghi xử lý U1 và kết luận nguyên nhân thế nào?
- Đáp: Báo cáo ghi `Thay thế linh kiện U1 => OK` và `Lỗi do U1`. Đây là kết luận trực tiếp của file, không phải suy diễn từ riêng các mã NG. Nguồn file: KTD-2026-03-0199-Iris2024-C34-A1-Scan SITC NG.xlsx

## CÂU HỎI 2886
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认自己是否正确理解Scan SITC-2案例。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Scan SITC-2时PC显示NG 9106、9108、9110，更换U1后OK，并由报告明确判定U1为原因，对吗？
- Đáp: 对。文件明确写有 `U1 was replaced → OK. The defect was caused by U1.` Nguồn file: KTD-2026-03-0199-Iris2024-C34-A1-Scan SITC NG.xlsx

## CÂU HỎI 2887
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: SITC NGケースの対象基板を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 対象品名、品番-Rev、S.Noは何ですか。
- Đáp: Item name=`PWB CCD ASSY`、Item code-Rev=`3V2XD01070-1`、S.No(Lot)=`2XD06207` です。 Nguồn file: KTD-2026-03-0199-Iris2024-C34-A1-Scan SITC NG.xlsx

## CÂU HỎI 2888
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo C3100 và kỹ sư kiểm tra tín hiệu điều khiển motor.
- Cách hỏi: tình huống
- Hỏi: Báo cáo ghi kết quả điều tra nào liên quan đến U21?
- Đáp: File chỉ ghi `Tín hiệu điều khiển motor từ U21 bất thường`. Không có linh kiện nguyên nhân sâu hơn hoặc đối sách cụ thể trong nội dung nguồn. Nguồn file: KTD-2026-06-0527-Iris2024-C33-A1.2-C3100.xlsx

## CÂU HỎI 2889
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师需要区分机器错误码和信号调查结果。
- Cách hỏi: so sánh
- Hỏi: 该案例的机器现象与调查结果分别是什么？
- Đáp: 机器现象是开机显示 `C3100`；调查结果是 `来自U21的Motor控制信号异常`。文件没有写明U21本体就是故障根因。 Nguồn file: KTD-2026-06-0527-Iris2024-C33-A1.2-C3100.xlsx

## CÂU HỎI 2890
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: U21からの信号異常だけで原因部品を断定しないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `U21からのMotor制御信号が異常` という結果だけで、U21故障や交換を追加できますか。
- Đáp: できません。ソースには信号異常までしか記載されておらず、U21故障の確定や交換対策は記載されていません。 Nguồn file: KTD-2026-06-0527-Iris2024-C33-A1.2-C3100.xlsx

## CÂU HỎI 2891
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận case FUSER đứt vỏ dây có đúng là THERMISTOR ASSY hay không.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Đối tượng là `THERMISTOR ASSY`, mã `302J125020-1`, Quantity=`2`, đúng không?
- Đáp: Đúng. Line=`C34-FUSER`, S.No(Lot)=`G640`, Supplier=`KDTHK FOR KDTVN`. Nguồn file: KTD-2026-08-0861-Iris2024-C34-FUSER-đứt vỏ.xlsx

## CÂU HỎI 2892
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接查看FUSER线材外皮破损案例的调查栏。
- Cách hỏi: trực tiếp
- Hỏi: 调查结果栏实际写了什么？
- Đáp: 文件只写 `linh kiện đã được lắp lên assy / 部品はASSYに実装済みです`。没有记载破皮原因或对策。 Nguồn file: KTD-2026-08-0861-Iris2024-C34-FUSER-đứt vỏ.xlsx

## CÂU HỎI 2893
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: リード線被覆破れの現品について、報告書の記載範囲だけを使用している。
- Cách hỏi: tình huống
- Hỏi: 部品リード線の被覆破れが見つかった場合、この報告書から原因をどこまで説明できますか。
- Đáp: 発生内容は `部品リード線の被覆破れ`、調査欄は `部品はASSYに実装済み` までです。破れの原因や対策は記載されていません。 Nguồn file: KTD-2026-08-0861-Iris2024-C34-FUSER-đứt vỏ.xlsx

## CÂU HỎI 2894
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Có nhiều case JAM4212 nên kỹ sư cần phân biệt case tại C33-A11.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng line và kết quả ngoại quan của case này là gì?
- Đáp: Khi `In RCG Copy check`, LCD báo `Jam 4212`; ngoại quan phát hiện linh kiện `C192` bị bong. Nguồn file: KTD-2025-12-1326-Iris2024-C33-A11-JAM4212.xlsx

## CÂU HỎI 2895
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现C192脱落，但文件没有进一步分析脱落原因。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以根据C192脱落自行补充外力、焊接不良或更换对策吗？
- Đáp: 不可以。文件仅记录 `外观检查发现C192部品脱落`，没有记录脱落机制或维修对策。 Nguồn file: KTD-2025-12-1326-Iris2024-C33-A11-JAM4212.xlsx

## CÂU HỎI 2896
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: JAM4212ケースの対象基板情報を再確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 対象は `PWB FRONT DRIVE ASSY`、品番-Rev=`3V2XC01050-5`、Line=`C33-A11` ですね。
- Đáp: はい。S.No=`2XC-0-5Y17`、Quantity=`1` です。 Nguồn file: KTD-2025-12-1326-Iris2024-C33-A11-JAM4212.xlsx

## CÂU HỎI 2897
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tra case Error80 để kiểm tra đúng vị trí connector bất thường.
- Cách hỏi: trực tiếp
- Hỏi: Ngoại quan phát hiện bất thường nào tại YC2?
- Đáp: File ghi `pin1-YC2 bị thụt/biến dạng chân pin` và `bong pattern phía sau chân pin`; tiếng Nhật ghi `YC2の1ピン...変形, ランド剥離（ピン裏）`. Nguồn file: KTD-2026-01-0114-Iris2024-C33-A6-Error80.xlsx

## CÂU HỎI 2898
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师在Aging中遇到Error80，参考YC2外观检查结果。
- Cách hỏi: tình huống
- Hỏi: Aging显示Error80后，YC2 pin1检查发现了什么？
- Đáp: 文件记录 `YC2 pin1` 发生变形/下陷，并在pin背面发现 land/pattern剥离。 Nguồn file: KTD-2026-01-0114-Iris2024-C33-A6-Error80.xlsx

## CÂU HỎI 2899
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Error80の画面表示と外観確認結果を区別している。
- Cách hỏi: so sánh
- Hỏi: 発生現象とYC2の外観確認結果はそれぞれ何ですか。
- Đáp: 発生現象は Aging中にPanelが `Error80` を表示。外観結果は `YC2 pin1の変形` と `ピン裏のランド剥離` です。 Nguồn file: KTD-2026-01-0114-Iris2024-C33-A6-Error80.xlsx

## CÂU HỎI 2900
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Báo cáo Eva không điền trường Contents of defect nhưng có mô tả trong Status/Investigation.
- Cách hỏi: xử lý sự cố
- Hỏi: Có thể tự điền tên lỗi vào trường Contents of defect dựa trên mô tả keo dính tray không?
- Đáp: Không. Contents of defect là **Raw value: ô trống**. Chỉ có thể giữ mô tả nguồn: keo dán dính rất chắc vào tray; khi lấy linh kiện ra, keo `KE-3424-G` (Shin-Etsu Chemical) dính vào khay đóng gói. Nguồn file: KTD-2026-01-0011-Iris2024-Eva-.xlsx

## CÂU HỎI 2901
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认该Eva案例中胶粘剂与包装托盘的情况。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 文件记录在从tray取出SPEAKER时，KE-3424-G (Shin-Etsu Chemical) 胶粘剂附着在包装tray上，对吗？
- Đáp: 对。文件还记录现象为胶粘剂非常牢固地粘在tray上。 Nguồn file: KTD-2026-01-0011-Iris2024-Eva-.xlsx

## CÂU HỎI 2902
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Evaケースの対象品と数量を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: Item name、Quantity、S.No(Lot)は何ですか。
- Đáp: Item name=`SPEAKER`、Quantity=`4`。S.No(Lot)は `3pcs: 28-4-528`、`1pcs: 29-4-532` と記載されています。 Nguồn file: KTD-2026-01-0011-Iris2024-Eva-.xlsx

## CÂU HỎI 2903
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Chạy U098 in 5 tờ White thì máy jam ngay tờ đầu.
- Cách hỏi: tình huống
- Hỏi: File mô tả diễn biến jam trước và sau khi OFF/ON thế nào?
- Đáp: Khi chạy `U098` (In 5 tờ White), máy jam tại tờ đầu tiên và giấy in ra được `2/3` tờ. Sau khi OFF/ON và in lại, máy báo `Jam 4212`. Nguồn file: KTD-2026-06-0647-Iris2024-C33-A-JAM4212.xlsx

## CÂU HỎI 2904
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较JAM4212机器现象和外观检查发现。
- Cách hỏi: so sánh
- Hỏi: 机器现象与外观检查结果分别是什么？
- Đáp: 机器现象是首次打印时纸张输出约 `2/3` 后Jam，OFF/ON再打印显示 `Jam4212`；外观发现 `RA3` 和 `C18` 破损，并有外力碰撞痕迹。 Nguồn file: KTD-2026-06-0647-Iris2024-C33-A-JAM4212.xlsx

## CÂU HỎI 2905
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 外力衝突痕はあるが、報告書以上の発生工程を断定しないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: RA3/C18に外力衝突痕があることから、具体的な作業や工程を原因として追加できますか。
- Đáp: できません。ファイルには `RA3とC18が破損`、`外力衝突の痕跡あり` と記載されていますが、具体的な発生工程や作業者は特定していません。 Nguồn file: KTD-2026-06-0647-Iris2024-C33-A-JAM4212.xlsx

## CÂU HỎI 2906
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Có Raw value 0 trong trường Reappear rate nhưng báo cáo đồng thời có kết luận sau thay U1.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Reappear rate phải giữ Raw value 0, còn file vẫn ghi thay U1 → OK và lỗi do U1, đúng không?
- Đáp: Đúng. Reappear rate=`0` phải giữ nguyên **Raw value 0**. Investigation ghi `Ngoại quan không bất thường`, `Thay thế U1 => OK`, `Lỗi do U1`. Nguồn file: KTD-2026-01-0030-Iris2024-C34-A4-C6000.xlsx

## CÂU HỎI 2907
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认C6000的发生操作。
- Cách hỏi: trực tiếp
- Hỏi: C6000是在什么操作后出现的？
- Đáp: 文件记录将 `A3` 纸放入 `Cassette 2`，关闭 `Cassette 2` 后，Panel 显示 `C6000`。 Nguồn file: KTD-2026-01-0030-Iris2024-C34-A4-C6000.xlsx

## CÂU HỎI 2908
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 外観異常がない状態で部品交換結果を確認している。
- Cách hỏi: tình huống
- Hỏi: 外観異常がないこのケースでは、U1交換後の結果と報告書の原因判定は何ですか。
- Đáp: `U1を交換 ⇒ OK`、`不具合の原因はU1です` と明記されています。これはファイル自身の原因判定です。 Nguồn file: KTD-2026-01-0030-Iris2024-C34-A4-C6000.xlsx

## CÂU HỎI 2909
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Bản gốc và bản Copy of của cùng KTD đều đã được mở để đối chiếu.
- Cách hỏi: so sánh
- Hỏi: Nội dung bản gốc này có khác bản `Copy of KTD-2026-04-0397...` ở Mẻ 69 không?
- Đáp: Không thấy khác biệt trong toàn bộ các trường nội dung đọc được: cả hai cùng `KTD=2026-04-0397`, Model=`Iris2024`, Item=`UNIT LOW VOLTAGE`, item code-Rev=`302XD45011-1`, S.No=`J3C0161C9943`, Machine No.=`110C2M3UT0 / 1FX6418473`, line=`C35-A1`, Quantity=`1`, hiện tượng `C0980`, và Investigation=`Hàn giả linh kiện D304 / D304未半田発見`. Nguồn file: KTD-2026-04-0397-Iris2024-C35-A1-C0980.xlsx; Copy of KTD-2026-04-0397-Iris2024-C35-A1-C0980.xlsx

## CÂU HỎI 2910
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认原始文件是否提供了D304未焊之外的修理对策。
- Cách hỏi: xử lý sự cố
- Hỏi: 原始文件记录 `D304未半田` 后，是否还能补充具体修理或根因？
- Đáp: 不可以。原始文件的调查结果只有 `Hàn giả linh kiện D304 / D304未半田発見`，没有进一步记录维修方法或更深层根因。 Nguồn file: KTD-2026-04-0397-Iris2024-C35-A1-C0980.xlsx

## CÂU HỎI 2911
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 元ファイルとCopy版が同一ケースであることを最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 元ファイルもCopy版も、電源ONで `C0980`、調査結果=`D304未半田発見` で一致していますね。
- Đáp: はい。読み取れる各フィールドは一致しています。Copy版だから別のRevisionや別ケースとは扱いません。 Nguồn file: KTD-2026-04-0397-Iris2024-C35-A1-C0980.xlsx; Copy of KTD-2026-04-0397-Iris2024-C35-A1-C0980.xlsx
