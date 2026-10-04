# Mẻ 55 — Điều-tra-lỗi: 3 Excel cấp gốc ZIP `Điều chỉnh` (3/3) — Q2409–Q2438

- Ngày: 2026-10-04
- Nguồn: local `~/workspace/dieuchinh_zip/dieuchinh.zip` → trích 3 file → upload Drive riêng (`chatgpt-enrichment-dieu-chinh`, anyone-reader; mỗi file <256MB nên connector ChatGPT mở được)
- Chat: https://chatgpt.com/c/6ac21250-cce4-83ec-a85f-5456b6a23733 (ChatGPT phiên mặc định hiện tại, theo quy trình từ đầu)
- 3 file, 30 cặp. **SỰ CỐ: không có** — 6m22s, "Đã hoàn tất phản hồi", không cloudflare, không cắt, không hết giới hạn.
- Ngôn ngữ: vi=10, zh=10, ja=10 — ĐÚNG mục tiêu.
- Cách hỏi: đủ 5 cách ×6.
- Quy tắc Raw value giữ vững: Q2427 (ô 解決策 ErrNo 02 trống → Raw value: ô trống, không tự bổ sung), Q2437 (F11X trống → Raw value: blank, không bổ từ F10X/F12X), Q2417 (từ chối kết luận 700 bất thường chỉ từ số đơn lẻ).
- Cấu trúc 3 file (mở đúng file được chỉ định, không mở lại CyCav):
  - `Maintenance mode 3.xlsx`: 5 sheet — `JP` (A1:D209), `VN 1` (A1:J209), `U034` (A1:O24), `Mag Laser` (A1:AL246), `VN` (A1:J209). Danh mục Maintenance Mode U-code Nhật/Việt; U034 ví dụ điều chỉnh Top margin; Mag Laser bảng giá trị U100.
  - `SCT自動調整エラーコード一覧_140221.xls`: 3 sheet — `変更履歴`, `自動調整エラーコード一覧`, `List code lỗi điều chỉnh tự động`. Cột `ErrNo / ErrDefine / 説明 / 原因 / 解決策 / 備考`; bản Nhật + bản Việt.
  - `UWCAシステムエラー(FXXX)概要.xls`: 6 sheet — `Cover`, `Change History`, `Explanation`, `List`, `List_e`, `Sheet1` (không dữ liệu). `List` bảng F-code Nhật/Anh: Code, nội dung, Team, quy trình kiểm tra, Remarks.
- Ghi chú quan trọng: ChatGPT khẳng định ba file này KHÔNG chỉ là bảng case đơn giản (chứa danh mục U-code, bảng mã lỗi tự động, tài liệu FXXX có quy trình kiểm tra) và KHÔNG dùng `Loi KDTPS.xlsx` làm nguồn — nội dung không chỉ lặp lại case đã có.
- Số liệu nổi bật: vào Maintenance Mode nhập `79248313`; U021=メモリー初期化 (Backup RAM); U024=HDD format / U026=khôi phục backup; U201=touch panel X/Y; U207=操作部キー確認 (không phải touch panel); U115=LSU駆動時間; U034=用紙タイミングデータ調整; ErrNo 00=ADJ_ERR_NON_ERR (自動調整成功); ErrNo 0e=DMA timeout; ErrNo 0f=VMAG_ERR; F10X=OS/BMC; F12X=Scanner/InputRIP; F13X=Panel/PSO; F14X=FAX/Fax; F1D4=RAM配置不良 (U340 + U021); cảnh báo U024 FULL làm mất dữ liệu người dùng.
- Còn lại ZIP Điều tra lỗi: `Lịch sử lỗi/` 2106 mục, `Bang ma loi/` 5 mục, `SƠ đồ điện/` 87 mục.
- Nhãn: Điều-tra-lỗi · Bản thảo — chưa qua chuyên gia duyệt.

---

# `Maintenance mode 3.xlsx` — Q2409–2418

## CÂU HỎI 2409
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần vào Maintenance Mode để kiểm tra máy.
- Cách hỏi: trực tiếp
- Hỏi: Theo file, cần nhập dãy số nào trên bàn phím số để vào Maintenance Mode?
- Đáp: Nhập `79248313`. Nguồn file: Maintenance mode 3.xlsx

## CÂU HỎI 2410
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师需要初始化备份 RAM，正在查找对应的 Maintenance Code。
- Cách hỏi: tình huống
- Hỏi: 用于初始化 Backup RAM 的 Maintenance Code 是什么？
- Đáp: `U021`。文件中的名称是 `メモリー初期化`，说明为初始化 Backup RAM。Nguồn file: Maintenance mode 3.xlsx

## CÂU HỎI 2411
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: HDD 関連の二つの Maintenance Code を比較している。
- Cách hỏi: so sánh
- Hỏi: `U024` と `U026` の機能はそれぞれ何ですか。
- Đáp: `U024` は HDD フォーマット、`U026` はバックアップデータ復帰です。Nguồn file: Maintenance mode 3.xlsx

## CÂU HỎI 2412
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang kiểm tra lỗi vị trí thao tác cảm ứng trên panel.
- Cách hỏi: xử lý sự cố
- Hỏi: File chỉ ra Maintenance Code nào dùng để hiệu chỉnh vị trí trục X/Y của touch panel?
- Đáp: `U201` — `タッチパネル初期化`, dùng để hiệu chỉnh vị trí trục X và Y của touch panel. Nguồn file: Maintenance mode 3.xlsx

## CÂU HỎI 2413
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 U207 与触摸屏校正是否为同一个项目。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `U207` 是触摸屏 X/Y 位置校正，对吗？
- Đáp: 不对。`U207` 是 `操作部キー確認`，用于确认操作面板按键动作；触摸屏 X/Y 校正是 `U201`。Nguồn file: Maintenance mode 3.xlsx

## CÂU HỎI 2414
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: LSU の使用時間を確認したい。
- Cách hỏi: trực tiếp
- Hỏi: LSU の駆動時間を表示する Maintenance Code は何ですか。
- Đáp: `U115` です。項目名は `LSU駆動時間` です。Nguồn file: Maintenance mode 3.xlsx

## CÂU HỎI 2415
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư đang kiểm tra ví dụ điều chỉnh Top margin trong sheet U034.
- Cách hỏi: tình huống
- Hỏi: Ví dụ `⑤ Cass (L)` trong sheet `U034` ghi Top margin trước và sau điều chỉnh là bao nhiêu?
- Đáp: Trước điều chỉnh là `20mm`, sau điều chỉnh là `17mm`; cùng vùng đó ghi giá trị trước `-0.1` và sau `+3`. Nguồn file: Maintenance mode 3.xlsx

## CÂU HỎI 2416
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 U100 的 AC Bias 与 DC Bias 补正值表。
- Cách hỏi: so sánh
- Hỏi: `U100 MC ACバイアス（K）` 与 `U100 MC DCバイアス補正後値 全速 (K)` 的表中数值分别是什么？
- Đáp: AC Bias(K) 行为代码 `02BC`、值 `700`；DC Bias 补正后值(K) 有 `00AA → 170` 和 `0208 → 520` 两行。Nguồn file: Maintenance mode 3.xlsx

## CÂU HỎI 2417
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: U100 の色別 AC Bias 表を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: K/C/M/Y の `U100 MC ACバイアス` がすべて `700` ですが、これだけで異常と判断できますか。
- Đáp: できません。ファイルには K/C/M/Y それぞれ `02BC`、値 `700` と記録されていますが、単独値 `700` を異常とする判定は示されていません。Nguồn file: Maintenance mode 3.xlsx

## CÂU HỎI 2418
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư kiểm tra lại U034 trước khi thao tác.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `U034` trong danh sách chính là mục điều chỉnh dữ liệu timing giấy, gồm timing đầu giấy và center line, đúng không?
- Đáp: Đúng. File ghi `U034 = 用紙タイミングデータ調整`, mô tả là điều chỉnh `先端タイミング` và `センターライン`. Nguồn file: Maintenance mode 3.xlsx

# `SCT自動調整エラーコード一覧_140221.xls` — Q2419–2428

## CÂU HỎI 2419
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师查看自动调整结果代码。
- Cách hỏi: trực tiếp
- Hỏi: `ErrNo 00` 对应的 ErrDefine 和说明是什么？
- Đáp: `ADJ_ERR_NON_ERR`，说明为 `自動調整成功`（自动调整成功）。原因和解决策栏均记录为原始文本 `-`。Nguồn file: SCT自動調整エラーコード一覧_140221.xls

## CÂU HỎI 2420
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: Table 読取時に原稿先端の傾き異常が出た。
- Cách hỏi: tình huống
- Hỏi: `ErrNo 01 / ADJ_ERR_SRCH_ORGERR1` の原因とファイル記載の対策は何ですか。
- Đáp: 原因は、テーブル位置調整時に原稿先端の黒帯検出位置が規定値以上ずれていることです。対策は、原稿を左上角に合わせて置き直して再実施し、ランプ点灯も確認することです。Nguồn file: SCT自動調整エラーコード一覧_140221.xls

## CÂU HỎI 2421
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh giới hạn ghi chú của lỗi nghiêng phía đầu và phía trái khi đọc Table.
- Cách hỏi: so sánh
- Hỏi: Ghi chú ngưỡng của ErrNo `01` và `02` khác nhau thế nào giữa scanner A3 và A4?
- Đáp: ErrNo `01`: A3 `≥1.5mm`, A4 `≥1.0mm`. ErrNo `02`: A3 `≥1.0mm`, A4 `≥1.5mm`. Nguồn file: SCT自動調整エラーコード一覧_140221.xls

## CÂU HỎI 2422
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师遇到 DP 左基准位置无法检测。
- Cách hỏi: xử lý sự cố
- Hỏi: `ErrNo 08 / ADJ_ERR_SRCH_NOPOINT5` 文件建议检查哪些项目？
- Đáp: 文件建议：确认 DP 安装位置；调整 guide 使原稿直线读取；确认灯是否点亮；确认调整原稿正反面是否放置正确。Nguồn file: SCT自動調整エラーコード一覧_140221.xls

## CÂU HỎI 2423
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: DMA 関連コードを再確認している。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `ErrNo 0e` は `ADJ_ERR_SRCH_DMAERR`、説明は DMA タイムアウト、原因は DMA 転送が行われない、で合っていますか。
- Đáp: はい。解決策として電源を OFF/ON して再実施することも記載されています。Nguồn file: SCT自動調整エラーコード一覧_140221.xls

## CÂU HỎI 2424
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư cần tra mã khi không nhận biết được dải đen đầu bản thảo trong Table.
- Cách hỏi: trực tiếp
- Hỏi: Mã lỗi nào tương ứng với việc không nhận biết được vị trí chuẩn phần đầu bản thảo khi đọc Table?
- Đáp: `ErrNo 04`, ErrDefine=`ADJ_ERR_SRCH_NOPOINT1`. Nguyên nhân ghi là khi điều chỉnh vị trí Table, không thể nhận biết dải đen phần đầu bản thảo. Nguồn file: SCT自動調整エラーコード一覧_140221.xls

## CÂU HỎI 2425
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师遇到副扫描倍率异常。
- Cách hỏi: tình huống
- Hỏi: `ErrNo 0f / ADJ_ERR_VMAG_ERR` 的原因和建议处理是什么？
- Đáp: 原因是调整所得的副扫描等倍度补正值超出范围。文件建议确认 Scanner Unit 或 DP Unit，并 OFF/ON 电源后重试；也可手动使用 `U065～U067`、`U070～U072` 调整。Nguồn file: SCT自動調整エラーコード一覧_140221.xls

## CÂU HỎI 2426
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: 同じ ErrNo 03 の二つの記載を比較している。
- Cách hỏi: so sánh
- Hỏi: `ErrNo 03 / ADJ_ERR_SRCH_ORGERR3` は A3 と A4 でどのように記載が違いますか。
- Đáp: A3 用では `Table読取時の原稿右縦線傾き異常`、A4 用では `Table読取時の原稿後端傾き異常` と記載されています。どちらも検出位置が `1.0mm以上` ずれる内容です。Nguồn file: SCT自動調整エラーコード一覧_140221.xls

## CÂU HỎI 2427
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư gặp ErrNo 02 nhưng cột giải pháp không có nội dung.
- Cách hỏi: xử lý sự cố
- Hỏi: Có được tự bổ sung phương án xử lý cho ErrNo `02` từ lỗi tương tự không?
- Đáp: Không. Trong file, ô `解決策/Đối sách giải quyết` của ErrNo `02` là **Raw value: ô trống**; không được tự thêm phương án không có trong nguồn. Nguồn file: SCT自動調整エラーコード一覧_140221.xls

## CÂU HỎI 2428
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师确认 `0d` 的白带说明，避免误解。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `ErrNo 0d` 是检测原稿本身的白带，对吗？
- Đáp: 不对。备注明确写着不是检测原稿白带；它也不是 DP 偏差调整项目，而是余白设定功能的确认项目。Nguồn file: SCT自動調整エラーコード一覧_140221.xls

# `UWCAシステムエラー(FXXX)概要.xls` — Q2429–2438

## CÂU HỎI 2429
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: FXXX 資料の用途を確認している。
- Cách hỏi: trực tiếp
- Hỏi: `Explanation` シートでは、この資料をどのような目的で使うよう記載されていますか。
- Đáp: サービスマニュアルに記載されていない FXXX エラーの概要要因を記載し、要因確認時や、電源 OFF/ON で復帰しない・頻発する場合の対処参考として使うよう記載されています。Nguồn file: UWCAシステムエラー(FXXX)概要.xls

## CÂU HỎI 2430
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Máy đứng ở màn hình Welcome hoặc logo khởi động và kỹ sư cần theo trình tự kiểm tra của file.
- Cách hỏi: tình huống
- Hỏi: Với trường hợp màn hình Welcome/logo bị treo, tài liệu yêu cầu kiểm tra những gì đầu tiên?
- Đáp: Trình tự bắt đầu bằng kiểm tra harness/connector giữa Panel–Main và, với model HDD tiêu chuẩn, Main–HDD; sau đó kiểm tra tiếp xúc DDR memory. File còn liệt kê HDD initialization, U021, thay PanelMain/Main board và lấy USBLOG nếu có thể. Nguồn file: UWCAシステムエラー(FXXX)概要.xls

## CÂU HỎI 2431
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师比较 F10X 与 F12X 的错误分类。
- Cách hỏi: so sánh
- Hỏi: `F10X` 与 `F12X` 的内容和 Team 有什么区别？
- Đáp: `F10X` 是 OS/Device Driver 部异常，Team=`OS/BMC`；`F12X` 是 Scan 控制部异常，Team=`Scanner/InputRIP`。Nguồn file: UWCAシステムエラー(FXXX)概要.xls

## CÂU HỎI 2432
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: F12X が発生し、Scan 系統を確認している。
- Cách hỏi: xử lý sự cố
- Hỏi: `F12X` の確認手順には何が記載されていますか。
- Đáp: Scan/DP⇔Main 基板間のハーネス・コネクタ確認、HDD 初期化（U024 FULL、HDD標準モデルのみ）、U021、Scan/DP 基板交換、Main 基板交換、USBLOG取得とサービス本部への連絡が記載されています。Nguồn file: UWCAシステムエラー(FXXX)概要.xls

## CÂU HỎI 2433
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư chuẩn bị chạy U024 theo hướng dẫn FXXX.
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: Chạy `U024 FULL` không ảnh hưởng dữ liệu người dùng, đúng không?
- Đáp: Không đúng. File cảnh báo rằng thực hiện U024 sẽ làm mất dữ liệu người dùng và phần mềm đã cài đặt; cần cài đặt lại. Nguồn file: UWCAシステムエラー(FXXX)概要.xls

## CÂU HỎI 2434
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师直接查询 F000 的定义。
- Cách hỏi: trực tiếp
- Hỏi: `F000` 的主要内容是什么？
- Đáp: 文件写明：Welcome 画面经过规定时间后可显示 `CF000`；涉及 Panel–Main 基板间通信异常，以及适用 Dual Core CPU 型号时的 Panel Core–Main Core 通信异常。Nguồn file: UWCAシステムエラー(FXXX)概要.xls

## CÂU HỎI 2435
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: FAX 制御部のエラーが発生している。
- Cách hỏi: tình huống
- Hỏi: `F14X` の確認手順に `U671` は含まれていますか。
- Đáp: はい。FAX⇔Main のハーネス確認、HDD 初期化、U021 に加え、対象モデルでは `U671` で DIMM Clear を行う手順が記載されています。受信データが残っている場合は消えるため注意が必要です。Nguồn file: UWCAシステムエラー(FXXX)概要.xls

## CÂU HỎI 2436
- Khối: Điều-tra-lỗi
- Ngôn ngữ: vi
- Bối cảnh: Kỹ sư so sánh F13X và F14X để chọn vùng điều tra ban đầu.
- Cách hỏi: so sánh
- Hỏi: F13X và F14X tương ứng với vùng điều khiển nào và Team nào?
- Đáp: `F13X`: bất thường phần điều khiển Panel, Team=`PSO`. `F14X`: bất thường phần điều khiển FAX, Team=`Fax`. Nguồn file: UWCAシステムエラー(FXXX)概要.xls

## CÂU HỎI 2437
- Khối: Điều-tra-lỗi
- Ngôn ngữ: zh
- Bối cảnh: 工程师看到 List 中 F11X 行没有详细说明。
- Cách hỏi: xử lý sự cố
- Hỏi: `F11X` 行的内容、Team 和确认步骤为空时，可以从 F10X 或 F12X 自动补充吗？
- Đáp: 不可以。`F11X` 对应这些字段为 **Raw value：空白**；不能从相邻代码自行补造内容。Nguồn file: UWCAシステムエラー(FXXX)概要.xls

## CÂU HỎI 2438
- Khối: Điều-tra-lỗi
- Ngôn ngữ: ja
- Bối cảnh: F1D4 の備考を確認し、一般 F1DX と混同しないようにしている。
- Cách hỏi: hỏi ngược kiểm tra hiểu
- Hỏi: `F1D4` の備考には RAM 配置不良について `U340` 確認と `U021` で設定値初期化が記載されていますか。
- Đáp: はい。`F1D4：RAMの配置不良` の備考として、①U340 の確認、②設定値の初期化（U021）が記載されています。Nguồn file: UWCAシステムエラー(FXXX)概要.xls
