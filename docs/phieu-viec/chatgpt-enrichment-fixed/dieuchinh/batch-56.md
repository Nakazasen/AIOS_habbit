# Mẻ 56 — Điều-tra-lỗi: thư mục `Bang ma loi/` (5/5 file) — Q2439–Q2463

- Ngày: 2026-10-04
- Nguồn: local `~/workspace/dieuchinh_zip/dieuchinh.zip` → trích 5 file → upload Drive riêng (`chatgpt-enrichment-dieu-chinh`, anyone-reader)
- Chat: https://chatgpt.com/c/6ac21250-cce4-83ec-a85f-5456b6a23733 (ChatGPT phiên mặc định hiện tại, theo quy trình từ đầu)
- 5 file, 25 cặp. **SỰ CỐ: không có** — 11m35s ("Đã hoàn tất phản hồi"; lâu hơn do phải tải/giải mã PDF 165MB 1758 trang + file .xls BIFF cũ), không cloudflare, không cắt, không hết giới hạn.
- Ngôn ngữ: vi=8, zh=8, ja=9 — ĐÚNG mục tiêu.
- Cách hỏi: đủ 5 cách ×5.
- Quy tắc Raw value giữ vững: Q2442 (detection time/monitoring của A000 là Raw value `―`, không tự đổi thành `0`); các đáp về C-code chỉ ghi điều kiện file định nghĩa.
- Cấu trúc 5 file (mở đúng 5 nguồn, không file rỗng):
  - `02XC_機能定義書_JAM一覧 (1).xls`: 11 sheet (表紙, 改訂履歴, １はじめに, các sheet ユニット00-09/10-59/60-79/90-99/A0-A9/B0-B9, ユニット一覧表, 4桁化のルール). Định nghĩa/mapping JAM theo unit, loại JAM, điều kiện phát hiện, timer, vị trí, detail code.
  - `02XC_自己診断表示一覧表-Iris2020 VN.xls`: 12 sheet; bảng Nhật + bộ サービスコール一覧 (2)/コントローラ (2) Việt hóa + sheet theo model. C-code, rank phát sinh/hủy/reboot, nội dung phát hiện, cách tái hiện, model áp dụng.
  - `02XC_自己診断表示一覧表.xls`: 10 sheet; cấu trúc tương tự nhưng bảng gốc Nhật, có cột tách lỗi Printer/Scan/Fax/EH.
  - `2xd_smkdj_jpnサービスアニュアル.pdf`: service manual 1758 trang, Version 8.0, August 2021, cho TASKalfa 2554ci/3554ci. Gồm JAM, tự chẩn đoán, maintenance mode, troubleshooting; không chỉ lặp case riêng lẻ.
  - `Iris2020_Cコール自己診断.xlsx`: 4 sheet — VN (A1:F2724), Sheet2 (A1:J27), Sheet1 (A1:H33), JP (A1:F2724). Sheet2 chứa log điều tra thực tế C1FF/C7620/C7613 → mẻ ưu tiên phần này để tránh lặp vô ích với bảng mã lỗi.
- Ghi chú trùng lặp: service manual "không chỉ lặp các case riêng lẻ"; file Iris2020_Cコール自己診断.xlsx ưu tiên log điều tra thực tế Sheet2; các cặp bám đúng file gốc, không sinh nội dung trùng lặp vô ích.
- Số liệu nổi bật: JAM9000 (không cấp giấy, retry rồi feed sensor vẫn không ON; 3TD/3TC tờ đầu → yêu cầu đặt lại bản gốc); JAM9030 (SSW double-feed, timer 40mm); B000 (3 sec, 入口センサ未達ジャム) vs B010 (用紙長+120mm/75mm, 入口センサ滞留ジャム); A000 (搬入不良JAM, detail 0Fh); quy tắc 4桁化 Unit 01-04 (0=timeout, 1=cover OPEN, 2=sequence error, 3=device); C0980 (24V: 1 sec / 100ms); C1010 (16 sec, 300ms lock, 1 sec upper-limit, lần thứ 5 sau 4 retry); C1800/C1820 (10 retry, 6 sec status ready; PF vs side PF); C1950 (EEPROM: 5ms×5, read mismatch×8); C0850 (TPM, High/Low=○, Mono=-); C1420 (2 sec / 350ms×2 / 3 lần); C1760 (ejection unit type mismatch); C2300 (LD High 1.5 sec); C0350 (rank D, -/-); C6600 (1.8 sec no belt pulse); C6050 (center thermistor) vs C6250 (edge thermistor); C6910 (1 giờ, 30 sec, 3 sec...); Paper Jam Log 1–16; log C1FF: Image→7620, ID Sensor→7620 rồi 7613, DLP(M) cross-check OK, High Volt Main cross-check OK, Thay Main Driver: NG (không giải quyết).
- Còn lại ZIP Điều tra lỗi: `Lịch sử lỗi/` 2052 mục (đã upload 30 file Excel/PDF đầu tiên), `SƠ đồ điện/` 84 file (đã upload toàn bộ, chờ share).
- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.

---

# `02XC_機能定義書_JAM一覧 (1).xls` — Q2439–2443

## CÂU HỎI 2439
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần tra điều kiện phát hiện JAM9000 ở cụm DP.
- Cách hỏi: trực tiếp
- Hỏi: `JAM9000` được định nghĩa với điều kiện nào, và file ghi chú gì cho 3TD/3TC ở tờ đầu tiên?
- Đáp: `JAM9000` là trường hợp không cấp giấy: dù đã retry cấp giấy số lần quy định nhưng feed sensor vẫn không ON. Với 3TD/3TC, nếu tờ đầu tiên thỏa điều kiện JAM9000 thì file ghi thực hiện yêu cầu đặt lại bản gốc thay vì phát hiện JAM. Nguồn file: 02XC_機能定義書_JAM一覧 (1).xls

## CÂU HỎI 2440
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师在 3TD 上确认重送检测相关 JAM。
- Cách hỏi: tình huống
- Hỏi: SSW 检测到重送时对应哪个 JAM，文件记录的检测距离是多少？
- Đáp: 对应 `JAM9030`，名称栏说明 SSW 检测到重送；JAM timer 值为累计 `40 mm`，3TD 重送检测栏标记为 `○`。Nguồn file: 02XC_機能定義書_JAM一覧 (1).xls

## CÂU HỎI 2441
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Z折りユニットの入口センサ未達と滞留JAMを比較している。
- Cách hỏi: so sánh
- Hỏi: `B000` と `B010` の検知条件はどう違いますか。
- Đáp: `B000` は本体から排紙ONコマンドを受信してから `3 sec` 経過しても入口センサがONしない「入口センサ未達ジャム」です。`B010` は入口センサON後、スルー搬送では用紙長+`120 mm`、折り処理では用紙長+`75 mm` 搬送しても入口センサを抜けない「入口センサ滞留ジャム」です。Nguồn file: 02XC_機能定義書_JAM一覧 (1).xls

## CÂU HỎI 2442
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thấy `A000` trong log của inserter và cần đọc đúng điều kiện gốc.
- Cách hỏi: xử lý sự cố
- Hỏi: `A000` được phát hiện khi nào và các trường detection time/monitoring ghi gì?
- Đáp: `A000` là `搬入不良JAM`: entry switch ON trước khi nhận lệnh discharge ON. Vị trí phát hiện là thân inserter, detail code=`0Fh`; detection time và monitoring đều ghi **Raw value `―`**, không tự đổi thành `0` hay trạng thái khác. Nguồn file: 02XC_機能定義書_JAM一覧 (1).xls

## CÂU HỎI 2443
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认四位 JAM 编码规则，避免误读第三位。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: 对 Unit 01～04，第三位 `0/1/2/3` 分别表示 timeout、cover OPEN、sequence error、device，对吗？
- Đáp: 对。文件的 `4桁化のルール` 表中依次定义为 `0=タイムアウト`、`1=カバーOPEN`、`2=シーケンスエラー`、`3=デバイス`。Nguồn file: 02XC_機能定義書_JAM一覧 (1).xls

# `02XC_自己診断表示一覧表-Iris2020 VN.xls` — Q2444–2448

## CÂU HỎI 2444
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 24V 電源断検知の条件を直接確認している。
- Cách hỏi: trực tiếp
- Hỏi: `C0980` はどの条件で検知されますか。
- Đáp: ①24V断検知信号が低下して `1 sec` 経過した場合、または②信号低下から `100 ms` 経過後に他のCコールが発生し、その後24V電源が復帰した場合です。Nguồn file: 02XC_自己診断表示一覧表-Iris2020 VN.xls

## CÂU HỎI 2445
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Cassette 1 không nâng đúng và kỹ sư cần kiểm tra điều kiện C1010.
- Cách hỏi: tình huống
- Hỏi: `C1010` được phát hiện theo các mốc thời gian nào trong file?
- Đáp: File ghi các điều kiện gồm: sau khi đưa Cassette 1 vào `16 sec` vẫn không phát hiện lift SW ON; sau khi lift motor ON, lock signal không được giải phóng trong `300 ms`; hoặc trong khi in, sau điều khiển nâng `1 sec` vẫn không ON upper-limit sensor. Nếu các điều kiện này tiếp tục sau `4` lần retry thì lần phát sinh thứ `5` được nhận là bất thường. Nguồn file: 02XC_自己診断表示一覧表-Iris2020 VN.xls

## CÂU HỎI 2446
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较普通 PF 与侧边供纸单元的通信异常。
- Cách hỏi: so sánh
- Hỏi: `C1800` 与 `C1820` 的检测逻辑有什么共同点和区别？
- Đáp: 两者都涉及通信异常，并在连续重试 `10` 次后判断异常；也都检查开始通信后 `6 sec` 内是否收到 status ready。区别是 `C1800` 对应 PF，`C1820` 对应侧边供纸单元。Nguồn file: 02XC_自己診断表示一覧表-Iris2020 VN.xls

## CÂU HỎI 2447
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 中間転写ベルトユニット EEPROM のアクセス異常を切り分けている。
- Cách hỏi: xử lý sự cố
- Hỏi: `C1950` の検知条件として、EEPROMアクセスについて何回・何msが記載されていますか。
- Đáp: R/W時に `5 ms` 以上応答がない状態を `5回` 繰り返す、2回Readしたデータ不一致を `8回` 繰り返す、またはWrite後Readの不一致を `8回` 繰り返す条件が記載されています。再現方法欄には転写ベルトモーターと本体のコネクターを外したまま起動するとあります。Nguồn file: 02XC_自己診断表示一覧表-Iris2020 VN.xls

## CÂU HỎI 2448
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra lại phạm vi model của C0850.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `C0850` là lỗi TPM security chip, với cột High/Low là `○` và Mono là `-`, đúng không?
- Đáp: Đúng. Dòng `0850` ghi tên `TPMセキュリティチップ異常`; High=`○`, Low=`○`, Mono=`-`. Nguồn file: 02XC_自己診断表示一覧表-Iris2020 VN.xls

# `02XC_自己診断表示一覧表.xls` — Q2449–2453

## CÂU HỎI 2449
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查询内置 shift tray 的自诊断条件。
- Cách hỏi: trực tiếp
- Hỏi: `C1420` 的异常检测条件是什么？
- Đáp: 文件定义为 inner shift tray 异常：动作开始后 `2 sec` 仍检测不到 sensor 变化，或连续 `2` 次在 `350 ms` 未满时检测到 sensor 变化；上述异常连续检测 `3` 次时判定。Nguồn file: 02XC_自己診断表示一覧表.xls

## CÂU HỎI 2450
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 起動時に期待と異なる排出ユニットを検出した。
- Cách hỏi: tình huống
- Hỏi: `C1760` はどのような条件のエラーですか。
- Đáp: 起動時に期待値と異なる排出ユニットの搭載を検知した場合の `排出ユニットタイプミスマッチ異常` です。期待値は本体生産ラインで治具から書き込むと記載されています。Nguồn file: 02XC_自己診断表示一覧表.xls

## CÂU HỎI 2451
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh lỗi lift motor Cassette 1 và Cassette 2.
- Cách hỏi: so sánh
- Hỏi: Điểm khác nhau đáng chú ý giữa điều kiện `C1010` và `C1020` là gì?
- Đáp: Cả hai đều có điều kiện `16 sec` sau khi đưa cassette vào và điều kiện upper-limit sensor sau `1 sec`. Điểm khác ở điều kiện motor: `C1010` kiểm tra lock signal chưa được giải phóng trong `300 ms`; `C1020` kiểm tra giá trị AD phát hiện dòng motor vượt ngưỡng liên tục từ `300 ms` trở lên. Nguồn file: 02XC_自己診断表示一覧表.xls

## CÂU HỎI 2452
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师排查定影电机运行中的 C2300。
- Cách hỏi: xử lý sự cố
- Hỏi: `C2300` 的检测条件和文件给出的再现方法是什么？
- Đáp: 检测条件是电机驱动过程中 LD 信号连续 `1.5 sec` 为 High。再现方法栏记录为拔掉定影电机的 connector。Nguồn file: 02XC_自己診断表示一覧表.xls

## CÂU HỎI 2453
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: パネル通信系 C0350 のランクを確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `C0350` は発生ランクDで、解除とリブート欄はどちらも `-` ですか。
- Đáp: はい。`C0350` は `パネル基板通信デバイス異常`、発生ランク=`D`、解除=`-`、リブート=`-` と記載されています。Nguồn file: 02XC_自己診断表示一覧表.xls

# `2xd_smkdj_jpnサービスアニュアル.pdf` — Q2454–2458

## CÂU HỎI 2454
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư tra điều kiện tự chẩn đoán của cụm định hình.
- Cách hỏi: trực tiếp
- Hỏi: Service manual định nghĩa `C6600` như thế nào?
- Đáp: `C6600` là lỗi quay belt định hình; điều kiện ghi trong manual là không có belt rotation pulse được nhập liên tục trong `1.8 sec`. Nguồn file: 2xd_smkdj_jpnサービスアニュアル.pdf

## CÂU HỎI 2455
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师安装定影单元后发现锁定可能不到位。
- Cách hỏi: tình huống
- Hỏi: Manual 对定影单元后侧锁定不良和前侧锁定不良分别说明了什么影响？
- Đáp: 后侧锁定不良会导致后侧驱动无法传递，并成为 `C6600` 定影热带旋转异常的因素；前侧锁定不良会因斜送纸成为图像直角度不良的因素。Nguồn file: 2xd_smkdj_jpnサービスアニュアル.pdf

## CÂU HỎI 2456
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 定着系の低温エラーを区別している。
- Cách hỏi: so sánh
- Hỏi: `C6050` と `C6250` はそれぞれ何の低温異常ですか。
- Đáp: `C6050` は `定着センターサーミスター低温異常`、`C6250` は `定着端部サーミスター低温異常` です。Nguồn file: 2xd_smkdj_jpnサービスアニュアル.pdf

## CÂU HỎI 2457
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư gặp C6910 và cần dựa đúng các điều kiện định nghĩa trong manual.
- Cách hỏi: xử lý sự cố
- Hỏi: Manual liệt kê những điều kiện nào cho `C6910`?
- Đáp: Các điều kiện được liệt kê gồm: engine stabilization kéo dài `1 giờ`; backup task không được xử lý trong `30 sec` ở timeout processing; khi drum motor hoặc developing K/transfer-belt motor chạy mà sau `3 sec` feed motor vẫn không chạy; drum đang dừng nhưng chỉ remote signal cao áp ON; hoặc charge bias OFF trong khi developing bias đang ON. Đây là các điều kiện do manual định nghĩa, không phải suy diễn từ một giá trị riêng lẻ. Nguồn file: 2xd_smkdj_jpnサービスアニュアル.pdf

## CÂU HỎI 2458
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 Paper Jam Log 的记录容量。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Paper Jam Log 最多按 `1～16` 次记录；不足16次时显示全部已有记录，对吗？
- Đáp: 对。Manual 明确写有 `1～16回まで記録`；过去 jam 次数不足16次时显示全部 log。Nguồn file: 2xd_smkdj_jpnサービスアニュアル.pdf

# `Iris2020_Cコール自己診断.xlsx` — Q2459–2463

## CÂU HỎI 2459
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Sheet2 の C1FF 調査履歴で Image 交換後の結果を確認している。
- Cách hỏi: trực tiếp
- Hỏi: Image を交換して Process を8枚印刷した後と、その後の Calibration では LCD に何が表示されましたか。
- Đáp: Image交換後に Process を `8枚` 印刷すると LCD は `7620`、続けて Calibration を実施しても `7620` と記録されています。Nguồn file: Iris2020_Cコール自己診断.xlsx

## CÂU HỎI 2460
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư thay ID Sensor mới trong quá trình điều tra C1FF/C7620.
- Cách hỏi: tình huống
- Hỏi: Sau khi thay ID Sensor mới, hai lần Calibration liên tiếp hiển thị mã gì?
- Đáp: Lần đầu LCD báo `7620`; lần Calibration thứ hai báo `7613`. Nguồn file: Iris2020_Cコール自己診断.xlsx

## CÂU HỎI 2461
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 DLP(M) cross-check 的组合结果。
- Cách hỏi: so sánh
- Hỏi: DLP(M) cross-check 与 "DLP OK + NG machine / DLP NG + OK machine" 的结果分别是什么？
- Đáp: DLP(M) cross-check 时两台机器都 `OK`，记录为 Calibration `5次`、U089 图像各打印 `5张`。之后 `DLP(OK)+NG machine` 打印 Process `8张` 时 LCD=`7620`；`DLP(NG)+OK machine` 的结果为 `OK`。Nguồn file: Iris2020_Cコール自己診断.xlsx

## CÂU HỎI 2462
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 5月16日の追加切り分けから原因を早計に断定しないよう確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: 5月16日の High Volt Main cross-check と最終確認結果はどう記録されていますか。
- Đáp: Calibration `5回OK`、U089 `10枚OK`、Aging=`OK`、導通=`OK`。High Volt Main の cross-check は2台とも `OK`（`20枚OK`、Calibration `5回OK`）。ただし `NG machine + High Volt Main OK` ではマゼンタ濃度 `100%` がNGと記録されています。その後、元の構成に戻すと濃度測定=`OK`、波形=`OK`、最後は `OK` です。ファイルは単一部品を根本原因とは断定していません。Nguồn file: Iris2020_Cコール自己診断.xlsx

## CÂU HỎI 2463
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: C1FF 調査中の Main Driver 交換結果を再確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Main Driver を交換した時点で問題は解消して `OK` になった、という記録ですか。
- Đáp: いいえ。Sheet2 には `Thay Main Driver: NG` と記録されています。したがって Main Driver 交換だけで解消したとは扱えません。Nguồn file: Iris2020_Cコール自己診断.xlsx
