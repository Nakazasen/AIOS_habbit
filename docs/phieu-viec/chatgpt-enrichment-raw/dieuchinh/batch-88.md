# Mẻ 88 — Điều-tra-lỗi — Q3392–Q3406 (15 cặp, mẻ vét cuối)

- Ngày: 2026-10-05 ~07:20 +07
- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.
- Nguồn: 5 file case điều tra lỗi thật (upload trực tiếp từng file, không qua link Drive)
- Model: ChatGPT (browser)
- Phục hồi: tin nhắn mẻ 88 gốc (05:35 +07, 5 link Drive) kẹt "Phân tích bị lỗi" + "Unknown error"; chuyển sang upload trực tiếp từng file từ ~06:55 +07. File 3 (KTD-2025-02-1000) kẹt 2 lần do sheet 16314 dòng số liệu jig thô → tách sheet, giữ nguyên 5 sheet nội dung điều tra. File 4 (PDF service manual 164MB/1758 trang) → trích chương 7-3 自己診断 (93 trang, giữ nguyên hình ảnh/sơ đồ).
- Ngôn ngữ: vi 5 / zh 5 / ja 5
- Cách hỏi: trực tiếp=3, tình huống=4, so sánh=2, xử lý sự cố=3, hỏi ngược kiểm tra hiểu=3 (mỗi file 3 cách khác nhau)

## File 2/5: Maintenance mode 3.xlsx (upload trực tiếp, ChatGPT xử lý 1m57s)

Báo cáo kiểm tra file: Đã mở trực tiếp Maintenance mode 3.xlsx: workbook có 5 sheet — JP, VN 1, U034, Mag Laser, VN. Hai sheet JP/VN là bảng danh sách Maintenance Mode; file ghi cách vào chế độ bảo trì bằng mã 79248313, cùng các mục như U000, U001, U201, U207.

## CÂU HỎI 3395
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần vào Maintenance Mode để kiểm tra lỗi liên quan vị trí cảm ứng của bảng điều khiển.
- Cách hỏi: xử lý sự cố
- Hỏi: Theo file, cần nhập mã nào để vào Maintenance Mode và mục nào dùng để hiệu chỉnh vị trí Touch Panel?
- Đáp: Để vào Maintenance Mode, nhập 79248313 bằng bàn phím số. U201 là Khởi tạo Touch Panel, dùng để hiệu chỉnh vị trí trục X và trục Y của Touch Panel. Nguồn file: Maintenance mode 3.xlsx

## CÂU HỎI 3396
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师需要区分触摸屏位置校正和操作面板按键检查两个Maintenance Mode。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: U201用于Touch Panel的X/Y轴位置校正，而U207用于确认操作面板按键动作，对吗？
- Đáp: 对。文件中U201=タッチパネル初期化，用于校正Touch Panel的X轴和Y轴位置；U207=操作部キー確認，用于确认操作面板按键动作。 Nguồn file: Maintenance mode 3.xlsx

## CÂU HỎI 3397
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: メンテナンスモードの基本操作として、レポート出力と終了コードを確認している。
- Cách hỏi: trực tiếp
- Hỏi: U000とU001の機能は何ですか。
- Đáp: U000はメンテナンスレポート出力で、各レポートの印刷およびUSBメモリーへの出力を行います。U001はメンテナンスモード終了で、メンテナンスモードを解除します。 Nguồn file: Maintenance mode 3.xlsx

## File 5/5: Loi KDTPS.xlsx (upload trực tiếp, ChatGPT xử lý 1m27s)

Báo cáo kiểm tra file: Đã mở trực tiếp Loi KDTPS.xlsx: workbook có 2 sheet — History KDTPS (lịch sử case lỗi, gồm hiện tượng, thao tác phát sinh, điều tra, nguyên nhân/đối sách...) và Hiện trạng (bảng tổng hợp số vụ/tỷ lệ theo model, năm và phân loại lỗi).

## CÂU HỎI 3404
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Khi đo VDC trên 6th Next, LCD báo lỗi 2340 và máy được line-out để điều tra.
- Cách hỏi: tình huống
- Hỏi: Với case C2340 này, file ghi bất thường nào trên bản mạch và kết quả sau xử lý thế nào?
- Đáp: File ghi lỗi C2340：定着圧解除モータエラー（タイムアウト）, số vụ=1; điều tra phát hiện cầu chì YF2 trên bản mạch Engine bị đứt. Kiểm tra thân máy và motor không thấy bất thường, lịch sử sản xuất bản mạch=OK; thay YF2 rồi kiểm tra máy thực nghiệm=OK. Nguyên nhân đứt YF2 vẫn đang điều tra/không được xác định rõ trong case. Nguồn file: Loi KDTPS.xlsx (sheet History KDTPS)

## CÂU HỎI 3405
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较Iris机种不同年份的C CALL与ERROR发生件数。
- Cách hỏi: so sánh
- Hỏi: Iris的C CALL和ERROR在2024、2025、2026年的件数分别有什么变化？
- Đáp: C CALL：2024=184件、2025=319件、2026=211件；ERROR：2024=252件、2025=452件、2026=289件。文件同时记录对应比例：C CALL=0.18217821782178217 / 0.17712382009994448 / 0.16920609462710506，ERROR=0.2495049504950495 / 0.25097168239866741 / 0.23175621491579793。 Nguồn file: Loi KDTPS.xlsx (sheet Hiện trạng)

## CÂU HỎI 3406
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Upsoft中にF000が発生し、Main基板を交換して切り分けを行っている。
- Cách hỏi: xử lý sự cố
- Hỏi: F000ケースでは、Main基板とU1についてどのような確認・処置が記録されていますか。
- Đáp: Line-out後にUSB Upsoftで再起動するとF000が再現し、Main基板新品ではOK、元のMain基板ではNGでした。U10位置の1.0V1_C電圧異常を確認し、EMSでI/F確認するとNG Step002、U1交換後はI/F=OK、実機へ戻して再確認しても再現なしと記録されています。 Nguồn file: Loi KDTPS.xlsx (sheet History KDTPS)

## File 1/5: Iris2020_Cコール自己診断.xlsx (upload trực tiếp, ChatGPT xử lý 1m)

Báo cáo kiểm tra file: Đã mở trực tiếp Iris2020_Cコール自己診断.xlsx: workbook có 4 sheet — VN, Sheet2, Sheet1, JP. Hai sheet VN và JP là bảng tự chẩn đoán C-call gồm khoảng 220 mục mã lỗi với cấu trúc hiện tượng → step → nguyên nhân phán đoán → xử lý; Sheet2 là ghi chú điều tra riêng, Sheet1 là bảng tính khác.

## CÂU HỎI 3392
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy phát sinh C0030 và kỹ sư cần kiểm tra đúng trình tự xử lý trong bảng tự chẩn đoán.
- Cách hỏi: trực tiếp
- Hỏi: Với C0030, file quy định 3 step xử lý nào?
- Đáp: C0030：Bất thường hệ thống bản mạch FAX; step 1=Reset nguồn điện chính: tắt nguồn điện và nguồn điện chính, sau khi vượt quá 5s thì gắn lại bản mạch FAX rồi bật lại nguồn; step 2=Version up Firmware: cài đặt lại Firmware FAX; step 3=Thay thế bản mạch FAX: thay bản mạch FAX. Nguồn file: Iris2020_Cコール自己診断.xlsx

## CÂU HỎI 3393
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 机器出现C0060 Type mismatch，需要按源文件确认SSD和UNIT连接。
- Cách hỏi: tình huống
- Hỏi: C0060发生时，文件要求先确认哪些项目？
- Đáp: C0060：Type mismatch异常表示安装了其他机种用SSD，或者无法与部分UNIT通信。Step 1是确认SSD；Step 2是确认connector和配线，并重新连接UNIT DRUM、UNIT显影、UNIT一次转写、UNIT FUSER的connector；如果connector配线不导通，文件要求更换配线。 Nguồn file: Iris2020_Cコール自己診断.xlsx

## CÂU HỎI 3394
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C0150のEEPROM異常条件と処置内容を正しく理解しているか確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: C0150は、5ms以上デバイス応答がない状態を5回連続で検出する場合や、読出しデータ不一致を8回連続で検出する場合を含み、EEPROM交換後はU169を実施するという理解でよいですか。
- Đáp: はい。C0150：ENGINE基板EEPROM読出し/書込み異常では、5ms以上応答なしを5回連続、読出しデータの2箇所不一致を8回連続、読出し/書込みデータ不一致を8回連続と記載しています。EEPROM交換時はU169を実施し、その後U000のMaintenance Report設定値を比較し、指定Maintenance Modeを実施する手順が記載されています。 Nguồn file: Iris2020_Cコール自己診断.xlsx

## File 3/5: KTD-2025-02-1000-Iris2024-WASE TONNER BOX IS NOT INSTALL.xlsx (bản làm sạch, upload trực tiếp, ChatGPT xử lý 1m9s)

> Ghi chú: file gốc kẹt 2 lần ở backend ChatGPT do sheet "2ND-8050治具データ (C35)" chứa 16314 dòng số liệu đo jig thô. Đã tách sheet này ra (có sheet GHI_CHU giải thích), 5 sheet nội dung điều tra giữ nguyên 100%.

Báo cáo kiểm tra file: Đã mở trực tiếp KTD-2025-02-1000-WASE-TONNER-BOX_cleaned.xlsx: workbook có 6 sheet — Bao cao dieu tra, giá trị sensor, まとめ, 波形, 2ND-8050治具でWTB再検査, GHI_CHU. Nội dung điều tra chính liên quan lỗi WASE TONNER BOX IS NOT INSTALL, dữ liệu U155/JIG WTB, giá trị sensor, waveform và crosscheck linh kiện.

## CÂU HỎI 3398
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy báo WASE TONNER BOX IS NOT INSTALL nhưng sau Line-out và bật lại nguồn không tái hiện.
- Cách hỏi: tình huống
- Hỏi: Với các máy được tổng hợp trong sheet まとめ, giá trị U155 và kết quả tháo/lắp lại DUMMY WASETONNER được ghi thế nào?
- Đáp: Ví dụ máy 1FV5201907 có U155 Non=218, EMTY=188, FULL=113; tháo DUMMY WASETONNER rồi lắp lại 20 lần đều OK, không tái hiện thông báo. Máy 1FV502118 có Non=233, EMTY=194, FULL=119 và cũng 20 lần OK, không tái hiện. Nguồn file: KTD-2025-02-1000-WASE-TONNER-BOX_cleaned.xlsx

## CÂU HỎI 3399
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较CN与VN的WTB JIG对None和Empty状态的识别范围。
- Cách hỏi: so sánh
- Hỏi: CN和VN对None、Empty的电压范围有什么差异？
- Đáp: CN记录：None=3.2~3.3V，Empty=≤2.8V；VN记录：None=2.6~3.3V，Empty=≤2.7V。文件明确写CN的None与Empty区分清楚，而VN存在重叠，并判断WTB对NONE/EMPTY的识别能力原本较低。 Nguồn file: KTD-2025-02-1000-WASE-TONNER-BOX_cleaned.xlsx

## CÂU HỎI 3400
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: WTB誤認識について、JIG再検査と部品Crosscheckの結果を使って切り分けている。
- Cách hỏi: xử lý sự cố
- Hỏi: 2ND-8050治具再検査と部品Crosscheckでは、どの結果が記録されていますか。
- Đáp: 2ND-8050治具でWTB再検査ではNG UNITでもV1=0.79/0.79/0.79V、V2=2.81/2.8/2.89V、V3=1.51/1.41/1.5V、V4=2.61/2.49/2.49Vで、各値は記載基準範囲内です。部品Crosscheckは SPRING WTB→CASE WASE ASSY→SENSOR EDGE→ACTUATOR/SPRING EDGE の順で行い、302K901170 SENSOR EDGE の影響が大きいと記録されています。 Nguồn file: KTD-2025-02-1000-WASE-TONNER-BOX_cleaned.xlsx

## File 4/5: 2xd_smkdj_jpnサービスアニュアル.pdf — chương 7-3 自己診断 (upload trực tiếp, giữ nguyên hình ảnh/sơ đồ)

> Ghi chú: file gốc 164MB/1758 trang không upload trực tiếp được. Đã trích chương 7-3 自己診断 (Tự chẩn đoán, p1119–p1211, 93 trang, 0.7MB) — phần liên quan nhất tới điều tra lỗi, giữ nguyên hình ảnh và sơ đồ vector (bản rút text thuần 2.9MB đã loại bỏ vì mất ~161MB hình/sơ đồ).

Báo cáo kiểm tra file: Đã mở trực tiếp 2xd_chuong7-3_tu-chan-doan.pdf: file có 93 trang, đúng chương 7-3 自己診断, gồm bảng danh sách mã C-call và phần chi tiết từng mã theo cấu trúc Step / 確認内容 / 想定原因 / 処置 / 参照. Nội dung đọc được trực tiếp từ text layer và đối chiếu với trang render.

## CÂU HỎI 3401
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy phát sinh C0980 và kỹ sư cần xác nhận chính xác điều kiện tự chẩn đoán của mã lỗi.
- Cách hỏi: trực tiếp
- Hỏi: Service manual định nghĩa C0980 phát sinh theo những điều kiện thời gian nào?
- Đáp: C0980 là 24V電源断検知. File ghi hai điều kiện: phát hiện liên tục tín hiệu mất nguồn 24V trong 1 giây; hoặc sau 0.1 giây kể từ khi phát hiện tín hiệu mất 24V thì phát sinh service call khác, sau đó nguồn 24V phục hồi. Nguồn file: 2xd_smkdj_jpnサービスアニュアル.pdf — chương 7-3 自己診断

## CÂU HỎI 3402
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认C0150的EEPROM读写异常判定条件。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: C0150包含“设备超过5ms无响应连续5次”以及“数据不一致连续8次”的判定，对吗？
- Đáp: 对。C0150为ENGINE基板EEPROM读写异常：读/写时设备超过5ms无响应连续5次；两个位置读取的数据连续8次不一致；或者写入数据与读取数据连续8次不一致。 Nguồn file: 2xd_smkdj_jpnサービスアニュアル.pdf — chương 7-3 自己診断

## CÂU HỎI 3403
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 電源ON時にMAIN側とENGINE側の機械シリアル番号が一致しないC0180が発生している。
- Cách hỏi: tình huống
- Hỏi: C0180発生時、サービスマニュアルでは最初にどのMaintenance Modeで何を確認しますか。
- Đáp: C0180：機械シリアル番号不一致では、電源ON時にMAIN側とENGINE側の機械シリアル番号が一致しない状態です。最初にU004でMAINとENGINEの機械シリアル番号を確認し、MAIN側の番号が異なる場合は正規のメイン基板を装着します。ENGINE側の番号が異なる場合は、エンジン基板に正規のEEPROMを装着する手順です。 Nguồn file: 2xd_smkdj_jpnサービスアニュアル.pdf — chương 7-3 自己診断
