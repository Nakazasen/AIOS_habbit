# Mẻ 72 — Điều-tra-lỗi — Q2912–Q2941 (30 cặp)

- Ngày: 2026-10-05 ~01:55 +07
- Nguồn: 10 file `Lịch sử lỗi/` (Excel/PDF case điều tra lỗi thật, shared link Drive)
- Model: GPT-5.6 Sol
- Không sự cố: không Cloudflare, không Unknown error, phản hồi không bị cắt
- Ngôn ngữ: vi 10 / zh 10 / ja 10
- Cách hỏi: trực tiếp=6, tình huống=6, so sánh=6, xử lý sự cố=6, hỏi ngược kiểm tra hiểu=6 (đúng nhãn đầy đủ; mỗi file 3 cách khác nhau)
- Quy tắc Raw value: tuân thủ (giữ nguyên 2.40~2.42, 2.40 (-0.1), 1, 100%, 2/3, S.No, Machine No.; không tự tính/diễn giải thêm)
- Đối chiếu phát hiện:
  - (a) XLSX C0363 XÁC NHẬN CÙNG CASE với PDF mẻ 67 — chỉ khác cách hiển thị Reappear rate (XLSX=1, PDF=100%); Q2921–2923 góc đối chiếu mới, không lặp câu cũ
  - (b) XLSX C9540 XÁC NHẬN CÙNG CASE với PDF mẻ 68 — Reappear rate XLSX=1 vs PDF=100%; Q2933–2935 góc đối chiếu mới, không lặp câu cũ
  - (c) PDF 302XD45011 XÁC NHẬN CÙNG CASE C0980/D304 (mẻ 69/71): báo cáo phân tích sâu của supplier — nguyên nhân phát sinh=DIP process偶发焊接缺陷; lọt lỗi vì ① AOI đã báo nhưng operator phán đoán sai, ② D304 vẫn tiếp xúc điểm với pad nên vượt qua characteristic test; đối sách=sửa chương trình AOI (thêm D304 + 4 vị trí diode khác vào forced check) + bổ sung kiểm tra FVI (D304/D101/D303/D305/D505), thực hiện 2026/5/11 — Q2927–2929 chỉ khai thác nội dung mới này
  - (d) THERMISTOR ASSY mẻ 72 (Rev=302J125020-2, SHIBAURA) khác case mẻ 71 (Rev=302J125020-1, KDTHK) — hai case độc lập, không trộn
- "Phán đoán là dị vật" (case Gray) giữ ở mức phán đoán của nguồn, không nâng thành kết luận chắc chắn
- Không thêm root cause/đối sách cho C846, THERMISTOR Assy, Fax IC4, C9540 khi file không xác nhận

- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
---

## CÂU HỎI 2912
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra ảnh Gray của DP Iris2020 và thấy một vạch màu bất thường.
- Cách hỏi: trực tiếp
- Hỏi: File ghi vị trí và màu sắc của vạch bất thường như thế nào?
- Đáp: File ghi phát hiện `vạch dọc màu tím ở bên lề trái` của ảnh Gray. Nguồn file: KTD-2025-10-1095-DP Iris2020-C2D-A9-Vạch tờ Gray.xlsx

## CÂU HỎI 2913
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师检查紫色纵线对应位置的CIS外观。
- Cách hỏi: tình huống
- Hỏi: 报告对图像NG位置的光导管外观记录了什么，并作了什么判断？
- Đáp: 文件记录图像NG位置的光导管外观有异常，并写明 `=> Phán đoán là dị vật`，即判断/推测为异物。保持为报告中的推测，不升级为更深层根因。 Nguồn file: KTD-2025-10-1095-DP Iris2020-C2D-A9-Vạch tờ Gray.xlsx

## CÂU HỎI 2914
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 確認事実と報告書の推定を分けて整理している。
- Cách hỏi: so sánh
- Hỏi: このケースで「確認された内容」と「推定された内容」は何ですか。
- Đáp: 確認された内容は `左端の紫色縦線` と `画像NG箇所のレンズ管外観異常`。推定された内容は `異物があると推定` です。 Nguồn file: KTD-2025-10-1095-DP Iris2020-C2D-A9-Vạch tờ Gray.xlsx

## CÂU HỎI 2915
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kiểm tra âm thanh Fax không nghe thấy âm thanh nhưng lỗi không còn tái hiện sau khi thao tác IC4.
- Cách hỏi: xử lý sự cố
- Hỏi: Có thể kết luận IC4 là nguyên nhân lỗi từ kết quả thay IC4 không?
- Đáp: Không. File ghi `thay IC4 mới → kiểm tra âm thanh OK; gắn lại IC4 cũ → kiểm tra âm thanh cũng OK; hiện tại lỗi không tái hiện`. Báo cáo không kết luận IC4 là root cause. Nguồn file: KTD-2025-09-0953-Iris2024-C2B-NG Fax.xlsx

## CÂU HỎI 2916
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认NG Fax报告中的外观与IC4复测结果。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 外观检查无异常，更换新IC4后声音检查OK，再装回旧IC4后也OK，对吗？
- Đáp: 对。文件还明确记录目前在更换IC4后无法再现该故障。 Nguồn file: KTD-2025-09-0953-Iris2024-C2B-NG Fax.xlsx

## CÂU HỎI 2917
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Fax NGケースの対象品を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 対象品名、品番-Rev、Supplierは何ですか。
- Đáp: Item name=`UNIT FAX NCU (U)`、Item code-Rev=`303WN45020-1`、Supplier=`RICOH INDUSTRIAL SOLUTIONS INC` です。 Nguồn file: KTD-2025-09-0953-Iris2024-C2B-NG Fax.xlsx

## CÂU HỎI 2918
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư phát hiện lỗi cơ khí trên PWB DRUM ASSY tại công đoạn Drum.
- Cách hỏi: tình huống
- Hỏi: File mô tả hiện tượng hư hỏng của linh kiện và pattern thế nào?
- Đáp: File ghi `Linh kiện bị mẻ góc, làm đứt pattern`; tiếng Nhật ghi `部品の角欠けにより、パターンが断線しました`. Nguồn file: KTD-2026-03-0232-Iris2024-C35-Drum-Bản mạch bị nứt.xlsx

## CÂU HỎI 2919
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师区分已记录的缺损现象和后续行动。
- Cách hỏi: so sánh
- Hỏi: 文件中的故障内容与后续调查行动分别是什么？
- Đáp: 故障内容是部品角部缺损导致pattern断线；后续行动是 `汇总信息并联系Partner继续调查`。 Nguồn file: KTD-2026-03-0232-Iris2024-C35-Drum-Bản mạch bị nứt.xlsx

## CÂU HỎI 2920
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Partner調査前の報告内容だけから詳細原因を作らないようにしている。
- Cách hỏi: xử lý sự cố
- Hỏi: このファイルから角欠けの発生工程や具体的な対策を追加できますか。
- Đáp: できません。ファイルにある対応は `情報をまとめ、Partnerに連絡し調査する` までです。発生工程や具体的対策は記載されていません。 Nguồn file: KTD-2026-03-0232-Iris2024-C35-Drum-Bản mạch bị nứt.xlsx

## CÂU HỎI 2921
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đối chiếu bản XLSX với PDF của cùng case C0363 đã xử lý trước đó.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: XLSX và PDF đều cùng `KTD=2026-08-0877`, `S.No=2XC-0-6812`, `Machine No.=110C2M3NL2 / 22J6801917`, đúng không?
- Đáp: Đúng. Hai bản cũng khớp Model=`Iris2024`, Item=`PWB IMAGE DRIVE ASSY WITH SOFTWARE`, item code-Rev=`3V2XC01040-13`, line=`C34-A1` và Quantity=`1`. Nguồn file: KTD-2026-08-0877-Iris2024-C34-A1-C0363.xlsx; KTD-2026-08-0877-Iris2024-C34-A1-C0363.pdf

## CÂU HỎI 2922
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接对照XLSX与PDF的Reappear rate显示方式。
- Cách hỏi: trực tiếp
- Hỏi: 同一C0363案例的Reappear rate在XLSX和PDF中分别怎样表示？
- Đáp: `XLSX底层值为 1`；`PDF显示为 100%`。保持各自源文件的表示方式，不把它们当作两个不同的再现结果。 Nguồn file: KTD-2026-08-0877-Iris2024-C34-A1-C0363.xlsx; KTD-2026-08-0877-Iris2024-C34-A1-C0363.pdf

## CÂU HỎI 2923
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: XLSX版とPDF版で調査内容が一致するか確認している。
- Cách hỏi: tình huống
- Hỏi: XLSX版でもC7と外力痕についてPDFと同じ内容が記載されていますか。
- Đáp: はい。XLSXにも `C7の両電極側にはんだ付着` と `外力衝突の痕跡あり` が記録されており、PDFと内容が一致します。 Nguồn file: KTD-2026-08-0877-Iris2024-C34-A1-C0363.xlsx; KTD-2026-08-0877-Iris2024-C34-A1-C0363.pdf

## CÂU HỎI 2924
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: THERMISTOR ASSY khó lắp vào frame và kỹ sư đối chiếu kích thước đo với tiêu chuẩn ghi trong file.
- Cách hỏi: so sánh
- Hỏi: Kích thước đo được và kích thước tiêu chuẩn được ghi như thế nào?
- Đáp: Kích thước đo được=`2.40~2.42`; kích thước tiêu chuẩn=`2.40 (-0.1)`. Giữ nguyên biểu diễn nguồn, không tự tính thêm giới hạn nếu file không ghi. Nguồn file: KTD-2026-02-0115-Iris2024-C34-Assy-Lắp khó.xlsx

## CÂU HỎI 2925
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师只有尺寸数据，报告没有写更深层原因。
- Cách hỏi: xử lý sự cố
- Hỏi: 可以仅凭 `2.40~2.42` 与 `2.40 (-0.1)` 自行判定具体制造原因或对策吗？
- Đáp: 不可以。文件只记录装入frame困难、实测尺寸和标准尺寸，没有写明具体制造根因或对策。 Nguồn file: KTD-2026-02-0115-Iris2024-C34-Assy-Lắp khó.xlsx

## CÂU HỎI 2926
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Assy組立困難ケースの対象品を確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 対象は `THERMISTOR ASSY`、品番-Rev=`302J125020-2`、Line=`C34-Assy` ですね。
- Đáp: はい。S.No(Lot)=`G5Y5`、Quantity=`1`、Supplier=`SHIBAURA ELECTRONICS HONG KONG CO` です。 Nguồn file: KTD-2026-02-0115-Iris2024-C34-Assy-Lắp khó.xlsx

## CÂU HỎI 2927
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Supplier phát hành báo cáo phân tích sâu cho case C0980/D304 đã có trong báo cáo KTD nội bộ.
- Cách hỏi: trực tiếp
- Hỏi: File PDF này có phải cùng case C0980/D304 với KTD-2026-04-0397 đã làm trước đó không?
- Đáp: Có. PDF ghi sản phẩm `302XD45011`, `S/N=J3C0161C9943`, phát sinh ngày `April 28th`, lỗi `#C0980` và primary investigation của Kyocera xác định `insufficient soldered D304`, khớp case KTD-2026-04-0397 trước đó. Nguồn file: KTD-2026-04-0397-Iris2024-C35-302XD45011.pdf

## CÂU HỎI 2928
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 供应商进一步调查为何D304不良能够流出。
- Cách hỏi: tình huống
- Hỏi: 报告对D304不良的发生原因和流出原因分别怎样说明？
- Đáp: 发生原因：报告判定为 `DIP process的偶发焊接缺陷`。流出原因有两点：① `AOI已经报警，但检查员误判导致流出`；② `部品仍与pad保持点接触，因此通过了characteristic test`。 Nguồn file: KTD-2026-04-0397-Iris2024-C35-302XD45011.pdf

## CÂU HỎI 2929
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 社内KTDの簡易調査結果とSupplier 8D相当報告の対策内容を比較している。
- Cách hỏi: so sánh
- Hỏi: Supplier報告では、社内KTDの `D304未半田` よりどのような追加対策が記載されていますか。
- Đáp: `AOIプログラムを改訂`し、`D304および同じダイオードを使用する他4箇所を強制確認項目へ追加`すること、さらに`FVIでD304（D101/D303/D305/D505）位置をinspection templateで追加確認`することが記載されています。実施日は `2026/5/11` です。 Nguồn file: KTD-2026-04-0397-Iris2024-C35-302XD45011.pdf

## CÂU HỎI 2930
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Báo cáo 8D xác nhận lỗi hiển thị có liên quan đến FPC nhưng kỹ sư cần dùng đúng chuỗi bằng chứng nguồn.
- Cách hỏi: xử lý sự cố
- Hỏi: Báo cáo xác định nguyên nhân lỗi hiển thị như thế nào?
- Đáp: Báo cáo xác nhận `FPC bất thường`. Sau khi tháo FPC và kiểm tra vùng gold finger, phát hiện `dấu gấp/stress crack` và `đứt copper foil`. File kết luận lỗi hiển thị do `khu vực FPC gold finger bị uốn/gập, ép quá mức làm đứt lá đồng bên trong`. Nguồn file: 20260310 KDTVN IRIS2024 文字顯示異常03.30 (1).pdf

## CÂU HỎI 2931
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认8D报告中的错误操作方式是否为文件自身调查结论。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 文件确认作业员有时把产品竖直放置，在FPC弯折状态下撕除Mylar胶带，对吗？
- Đáp: 对。报告还说明正确方法应将玻璃与FPC平放，再用防静电镊子从玻璃位置慢慢撕除。 Nguồn file: 20260310 KDTVN IRIS2024 文字顯示異常03.30 (1).pdf

## CÂU HỎI 2932
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 8D報告の基本情報と改善内容を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: 製品型番、返却数、改善措置は何ですか。
- Đáp: Model No.=`302XC45060 / SVF101000ANN`、Return Q'ty=`2`。改善措置は、`Mylar tapeを剥がす際の正しい作業方法を作業者へ教育`し、その手順を作業看板として現場に掲示することです。 Nguồn file: 20260310 KDTVN IRIS2024 文字顯示異常03.30 (1).pdf

## CÂU HỎI 2933
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đối chiếu XLSX với PDF của cùng case C9540 đã xử lý ở Mẻ 68.
- Cách hỏi: tình huống
- Hỏi: XLSX xác nhận những metadata nào trùng với PDF?
- Đáp: Hai bản cùng `KTD=2026-08-0803`, Model=`Iris2024`, Item=`PWB ENGINE ASSY WITH SOFTWARE`, item code-Rev=`3VC2G01071-3`, S.No=`6J11167H8585`, Machine No.=`110C2K3NLV / 1Y86808683`, line=`C33-A1.1`, Quantity=`1`, Occurrence Date=`2026-08-05`. Nguồn file: KTD-2026-08-0803-Iris2024-C33-A1.1-C9540.xlsx; KTD-2026-08-0803-Iris2024-C33-A1.1-C9540.pdf

## CÂU HỎI 2934
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较XLSX与PDF的再现率表示方式。
- Cách hỏi: so sánh
- Hỏi: 同一C9540案例的Reappear rate在两个格式中有什么表示差异？
- Đáp: `XLSX保存的值为 1`，`PDF显示为 100%`。其它核心案例字段和调查内容一致，因此不把这两个表示解释为不同的再现结果。 Nguồn file: KTD-2026-08-0803-Iris2024-C33-A1.1-C9540.xlsx; KTD-2026-08-0803-Iris2024-C33-A1.1-C9540.pdf

## CÂU HỎI 2935
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 接触リスクの記載を確定した衝突原因へ変換しないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `C231/C229剥がれ` と `該当位置に接触リスクあり` から、衝突が確定原因だったと記載できますか。
- Đáp: できません。ファイルは部品剥がれを確認し、位置に接触リスクがあると記録し、QCと製造へ作業再確認を依頼しています。具体的な衝突原因の確定までは記載していません。 Nguồn file: KTD-2026-08-0803-Iris2024-C33-A1.1-C9540.xlsx

## CÂU HỎI 2936
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư xác nhận mình đang tra đúng case mất nguồn của Main board.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Đối tượng là `PWB MAIN ASSY WITH SOFTWARE E`, item code-Rev=`3VC2L01010-9`, hiện tượng là bật máy không lên nguồn, đúng không?
- Đáp: Đúng. Line=`C35-A1`, S.No=`6HY1065K9911`, Machine No.=`110C2M3NL0 / 1FV6648828`, Quantity=`1`. Nguồn file: KTD-2026-06-0547-Iris2024-C35-A1-Không lên nguồn.xlsx

## CÂU HỎI 2937
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接确认无法上电案例的调查结果。
- Cách hỏi: trực tiếp
- Hỏi: 文件对C846记录了什么异常？
- Đáp: Investigation栏只记录 `Vỡ đầu điện cực C846`，即C846电极端部破损。没有记录更深层原因或修理对策。 Nguồn file: KTD-2026-06-0547-Iris2024-C35-A1-Không lên nguồn.xlsx

## CÂU HỎI 2938
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 電源が入らない現象とC846確認結果を分けて扱っている。
- Cách hỏi: tình huống
- Hỏi: 電源が入らない場合、この過去ケースでは調査結果として何が記載されていますか。
- Đáp: `C846の電極端部破損` に相当する内容が記載されています。それ以上の故障メカニズムや対策はファイルにありません。 Nguồn file: KTD-2026-06-0547-Iris2024-C35-A1-Không lên nguồn.xlsx

## CÂU HỎI 2939
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Có nhiều case CIS của DP Iris2020 nên kỹ sư cần phân biệt case SITC NG này với các case C9080/vạch Gray trước đó.
- Cách hỏi: so sánh
- Hỏi: Hiện tượng và kết quả điều tra chính của case này là gì?
- Đáp: Model=`DP Iris2020`. Khi chạy `SITC 2 CIS` để scan bản thảo SITC2, sau khi bản thảo chuyển xong thì PC báo NG. Ngoại quan phát hiện `phần LENS có dị vật`; sau đó file ghi tổng hợp thông tin và liên lạc Partner. Nguồn file: KTD-2025-12-1288-DP Iris2020-C2D-A2-Scan SITC NG.xlsx

## CÂU HỎI 2940
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师发现LENS内异物，需要严格按照文件已有对策处理。
- Cách hỏi: xử lý sự cố
- Hỏi: 文件已经记录了什么后续措施？可以自行追加清洁或更换LENS吗？
- Đáp: 文件记录 `汇总信息并联系Partner`。没有写具体清洁方法或更换LENS，因此不能自行追加。 Nguồn file: KTD-2025-12-1288-DP Iris2020-C2D-A2-Scan SITC NG.xlsx

## CÂU HỎI 2941
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: DP Iris2020のSITC NGケース基本情報を最終確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Model=`DP Iris2020`、Item=`CIS`、品番-Rev=`313TT45010-1`、Line=`C2D-A2` ですね。
- Đáp: はい。S.No(Lot)=`FD2CFC-01 / 52 5102300759`、Quantity=`1` です。 Nguồn file: KTD-2025-12-1288-DP Iris2020-C2D-A2-Scan SITC NG.xlsx
