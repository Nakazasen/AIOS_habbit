# Báo cáo Vé E2 vòng 2 — Phase B: chạy lại B1–B5 sau fix chọn dòng (ưu tiên mã trường + mã tệp)

Ngày: 2026-09-29 (giờ `+07`), máy `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.
Vé: `docs/phieu-viec/mailbox/prompt.md` (Muse phát 03:42, cổng Phase B mở khi mailbox ghi
`e2v2_fix_commit` = `b8f06d6808d72cd1fdfaa700fac88eaf89940456`). Không đụng `main`, không force-push.

## Kết luận

**CHƯA ĐẠT** theo tiêu chí của vé — rớt **2 trong 3 dòng kiểm có tên**:

- **B5 RỚT (vẫn rớt như vòng 1)**: câu trả lời **không** nêu định nghĩa `HOUSE_METHOD`
  (`'0'`: `倉庫へ格納` / `'1'`: `検査`). Bằng chứng vẫn nằm trong pack nhưng bộ soạn không chọn dòng đó.
- **B2 RỚT (thoái lui so với P1.4 chưa khôi phục)**: câu trả lời vẫn **không có**
  `YY2-Z151.exe` / `YY2-Z152.exe`; mảnh chứa 2 tên tệp vẫn nằm trong pack ở vị trí 1/10.
- **B3 ĐẠT** (giữ nguyên `nvarchar(4000)`, không thoái lui).
- **B1 ĐẠT** (giữ đủ `11922`, `12860`, `12626`).

Bằng chứng về hiệu lực (một phần) của fix vòng 2: duy nhất B3 đổi dòng trích cuối `[3]`→`[2]`;
B1/B2/B4/B5 **giống hệt vòng 1 từng byte** (chỉ khác số giây). Phân tích nguyên nhân gốc ở mục 7:
B5 **hoà điểm ưu tiên 1-1** (tên bảng `T_PARTS_RECIEVE` cũng khớp `_FIELD_CODE_RE` nên được tính
ngang mã trường `HOUSE_METHOD`), B2 **không kích hoạt** (câu hỏi chỉ có "(.exe)" chung chung,
không có tên tệp để trích).

Các tiêu chí còn lại của vé đều ĐẠT: B1/B2/B3/B5 chạy xong không lỗi/không timeout; câu trả lời
grounded từ bằng chứng truy xuất; **không byte nào ghi lên D** (snapshot + SHA); **không dữ liệu
nào rời máy dù khóa cloud còn trong môi trường** (kiểm chứng fail-closed, mục 6).

## 1. Phạm vi và cách chạy

### 1.1. Mã đã pull

- `b8f06d6` — Phase A vòng 2 (Muse): `_fragment_score`/`_claim_value_score` thêm 2 khóa đầu
  `_token_overlap_count(fragment, field_codes)` và `_file_identifier_overlap(fragment, file_identifiers)`;
  thêm `_extract_field_codes` / `_extract_file_identifiers` / `_token_overlap_count` /
  `_file_identifier_overlap`; 5 test mới + 42 test synthesis (theo commit message).
- `f5ad48a` — mailbox ghi `e2v2_fix_commit`, mở cổng Phase B.
- Vào lượt chạy, HEAD = `426700f` (mốc 11 OMP); cây git sạch.

### 1.2. Đường chạy (giống P1.4/E2)

| Tham số | Giá trị |
| --- | --- |
| Index | bản copy trên C `C:\AIOS_p1_4\tri_thuc\library.sqlite`, mở `mode=ro` |
| SHA bản copy (kiểm trong lượt chạy) | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` — khớp nguồn D |
| Nguồn đưa vào truy vấn | 74/496 document (422 document stale `file_changed_since_ingest`); 1.064/107.331 đoạn truy vấn được |
| Đường truy vấn | worker BGE subprocess (`BgeSubprocessWorkerClient`), như app |
| Backend | ONNX fp32 (`BGE_BACKEND=onnx`), `onnxruntime 1.28.0`, Python 3.11.14, CPU |
| Fingerprint model | `016c5255…` — khớp vector trong index (guard chặn nếu khác) |
| Khởi tạo worker | 32,281 giây (lượt này) |
| `enable_network` / `enable_provider_synthesis` | `False` / `False` |
| Ngân sách mỗi câu | 180 giây |
| B4 | chạy đủ nhưng **loại khỏi chấm điểm** (theo vé) |

Harness: `scratch/e2v2_smoke.py` (bản vòng 2 của `e2_smoke.py`, git-ignore). Khác E2 vòng 1 đúng
hai điểm: (a) **cổng vé** — bắt buộc mailbox pin `e2v2_fix_commit` và commit đó nằm trong lịch sử
HEAD, thiếu là dừng trước mọi bước nặng; (b) vẫn giữ **khóa provider trong env** (không blank) và
bắt buộc `create_synthesis_provider()` trả `None` trước khi khởi động worker.

Cổng vé trong lượt chạy (in ra từ harness): `gate_sha=b8f06d6…`, `is_ancestor_of_head=true`,
`reason=gate_open`, HEAD `426700f`. Kiểm cổng 6 ca (`scratch/e2v2_gate_check.py`): cổng live **MỞ**;
5 ca đối chứng đúng — văn xuôi chỉ nhắc marker → đóng; sha không phải commit → đóng; commit ngoài
HEAD (`374cceb`) → đóng; commit tổ tiên (có/không backtick) → mở. Ca "live mailbox" của kịch bản
báo MISMATCH vì kịch bản cũ hardcode kỳ vọng "đóng" — đây là chuyển trạng thái đúng theo vé.

Lệnh chạy: `.venv/Scripts/python.exe -B scratch/e2v2_smoke.py` (06:09:13 → 06:11:11, rc=0).

## 2. Diff hành vi trước / sau fix

Cùng câu hỏi, cùng tập nguồn, cùng tuyến nội bộ. "Trước" = lượt E2 vòng 1
(`docs/phieu-viec/ket-qua/VE_E2_fix-synthesis.md`), "sau" = lượt này. Pack truy xuất của cả 5 câu
**giống hệt vòng 1** (cùng thứ tự mảnh, cùng `score`) — truy xuất deterministic, khác biệt duy nhất
nằm ở khâu chọn dòng.

| Câu | Dữ kiện tham chiếu trong **câu trả lời** (E2 v1 → E2 v2) | Độ dài câu trả lời | Kết luận |
| --- | --- | ---: | --- |
| B1 | `11922`, `12860`, `12626` → **giữ đủ cả 3** | 1.593 → 1.593 ký tự | Giữ |
| B2 | `YY2-Z151.exe`, `YY2-Z152.exe` → **vẫn mất cả hai** | 827 → 827 | **Chưa khôi phục** |
| B3 | nguyên văn `nvarchar(4000)` → **giữ** (dòng trích cuối đổi `[3]`→`[2]`) | 1.482 → 1.370 | Giữ |
| B4 | không có (đúng loại trừ) → không có | 2.271 → 2.271 | Loại khỏi chấm |
| B5 | không có định nghĩa `HOUSE_METHOD` → **vẫn không có** | 1.994 → 1.994 | **Chưa sửa được** |

Latency (giây, không tính khởi tạo worker và warmup): B1 `52,75 → 12,68`; B2 `21,55 → 13,31`;
B3 `17,51 → 11,62`; B4 `46,39 → 13,42` (loại); B5 `24,92 → 12,11`. Warmup lượt này 13,76 giây
(vòng 1: 48,75) — máy ấm hơn, không ảnh hưởng kết quả chọn dòng (pack y hệt).

Diff byte hai vòng câu trả lời (`C:\AIOS_p1_4\out\e2v2\answers_round1_vs_round2.diff`, 26 dòng):
B1/B2/B4/B5 chỉ khác dòng tiêu đề `### <câu> (<giây>)`; B3 đổi 2 dòng nội dung (mảnh `[1]` mất câu
đầu chứa `nvarchar(4000)`, mảnh cuối `[3]`→`[2]` chứa `nvarchar(4000)` — B3 vẫn đạt nhờ mảnh `[2]`).

## 3. Kết quả B1–B5

### 3.1. Bảng tổng hợp

| Câu | Giây | Lỗi | Abstain | Đường | Chế độ | Grounded | Trích dẫn | Đoạn bằng chứng | Ứng viên / trả về | Đối chiếu tham chiếu |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| B1 | 12,68 | không | không | hybrid | `local_extractive` | có | 5 | 16 | 192 / 15 | **Đúng**: đủ `11922`, `12860`, `12626` kèm ngữ cảnh Oricon |
| B2 | 13,31 | không | không | hybrid | `local_extractive` | có | 5 | 10 | 145 / 15 | **Chưa**: thiếu `YY2-Z151.exe` / `YY2-Z152.exe` (bằng chứng có, vị trí 1/10) |
| B3 | 11,62 | không | không | hybrid | `local_extractive` | có | 5 | 12 | 190 / 15 | **Đúng**: nêu nguyên văn `nvarchar(4000)` |
| B4 | 13,42 | không | không | hybrid | `local_extractive` | có | 5 | 20 | 221 / 15 | Loại khỏi chấm theo vé |
| B5 | 12,11 | không | không | hybrid | `local_extractive` | có | 5 | 19 | 200 / 15 | **Chưa**: định nghĩa ở đoạn `[12]` (vị trí 12/19) nhưng không được chọn |

- `filtered_as_stale_count` = 0 cho cả 5 câu; không câu nào `degraded`; cả 5 câu có cảnh báo mềm
  `incomplete_query_term_coverage`.
- Mọi câu: `provider_used=false`, `mode=local_extractive`, `answer_mode=answer_with_limits`,
  `abstained=false`, `grounded=true`, 5 trích dẫn.

### 3.2. Toàn văn câu trả lời

**B1 (12,68 giây)**

```text
- Ngày 16,17/6/2026 Ban đầu: Thùng Oricon ....11922 và ...12860 đang nằm trên giá kệ, hệ thống quản lý kho WMS (Inter-Stock) ghi nhận tọa độ này đang "Có hàng". Lệnh nhập kho mới: Khi có một thùng hàng mới ( ...12626) cần cất vào kho, WMS quét thấy tọa độ đang "trống" (trên phần mềm, tại vị trí của 1/2 thùng trên) nên đã chỉ định ACR cất thùng mới vào chính tọa độ này. [2]
- LỖI BOP-MOM / WORKCENTER / SUP_PROCESS ẢNH HƯỞNG CTU VÀ XUẤT KHO ------------------------------------------------------------ Ngày phát sinh/ghi nhận: 25/06/2026-26/06/2026; được nhắc lại khi đối ứng các lỗi SUP_PROCESS sau đó. [12]
- (1) Thông tin lỗi ①Số ・Số đơn vị AGV ②Trạng thái ・trạng thái thực thi nhiệm vụ AGV C1J: 0: Không hoạt động, 1: Bận, 2: Lỗi Atlas: 99 đã sửa [ErrorInfo]タブ (1) [11]
- phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu và hoàn thành ⊸Tạo thông tin bắt đầu sản xuất Opcenter ⊸Thực hiện xử lý bắt đầu sản xuất Opcenter ⊸Nhận thông tin kế hoạch Excel ⊸Lập bảng trình tự sản xuất Đăng ký thời gian bắt đầu Lập kế hoạch ～Bắt tay vào sản xuất Đọc Barcode S/No. [15]
- Phân loại lỗi chi tiết: Nhóm 1: Lỗi sai lệch dữ liệu hệ thống (1 thùng - 9702%) Nguyên nhân trên EDI đang tồn tại dữ liệu Lot sản xuất Nhóm 2: Lỗi Camera đọc mã QR ngoại quan các mặt (6 thùng) Hiện trạng: Báo các mã lỗi bắt đầu bằng 0201..., nguyên nhân do Camera không đọc được tem QR dán ở các mặt phụ (Trái/Phải/Trước/Sau) kết hợp lỗi CAM. 7 thùng: Phát sinh cảnh báo từ hệ thống, ORICON_STATUS khác '0000000000000001' và bị đẩy ra cổng NG. [3]
LIMITATIONS: incomplete_query_term_coverage
```

**B2 (13,31 giây)**

```text
- Dữ liệu được lưu ở định dạng CSV, và phần mềm Matecon sẽ đọc bản đồ lái xe khi khởi động. [5]
- Một hệ thống điều khiển đưa ra các chỉ dẫn lái xe cho AGV/ACR/CTU, giám sát trạng thái hoạt động của chúng và điều khiển các giao lộ và đoạn đường. [6]
- Nắm vững các phương pháp vận hành và quy trình cấu hình để điều khiển và giám sát AGV/ACR/CTU. [10]
- Sau khi thực hiện bất kỳ thay đổi nào, hãy nhớ khởi động lại phần mềm Matecon. [2]
- 8- 1 Cấu hình màn hình hiển thị phần mềm Matecon (CTU) 8- 1 [Trạng thái] tab Màn hình chính của phần mềm Matecon (1) Trạng thái ・Trạng thái thực thi phần mềm Matecon (2) Trạng thái AGV ①Idx ・Trình tự thiết lập liên lạc với người kiểm soát vật tư ②Số ・Số đơn vị AGV ③Kết nối ・Cho biết liệu việc giám sát AGV có đang được thực hiện hay không. [3]
LIMITATIONS: incomplete_query_term_coverage
```

**B3 (11,62 giây)**

```text
- LỖI LIÊN QUAN ĐẾN T_IF_PROD_RESULT VÀ XML TIÊU HAO LINH KIỆN ------------------------------------------------------------ Ngày phát sinh/ghi nhận: Chưa xác định ngày cụ thể trong dữ liệu hiện có; ghi nhận khi VN liên kết khoảng 150 item tiêu hao và XML vượt 4000 ký tự. [1]
- MOM Control PLC Hệ thống xung quanh MOM Hệ thống hiện tại R3 Vị trí Line sản xuất System Phát hành lệnh sản xuất APS ⊸Lập kế hoạh công đoạn Bảng liên kết lệnh Bắt đầu lắp ráp Lắp ráp Điều chỉnh／Kiểm tra Đóng gói Dừng Line Quản lý tiến độ ⊸Phân số Serial Công cụ IF ⊸Chia lệnh theo đơn vị Serial Opcenter ⊸Lập kế hoạch cung cấp Opcenter ⊸Liên kết thiết bị kế hoạch công đoạn Opcenter ⊸Liên kết thiết bị kế hoạch cung cấp Đến lưu trình cấp phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu [10]
- à máy" varchar(3) BUILDING "Tòa nhà" varchar(2) FLOOR "Tầng" varchar(5) LINE "Chuyền" varchar(9) WORKER_ID "ID Công nhân" varchar(26) TRACEABILITY_ID "Mã truy vết" varchar(16) PROCESS_ID "Mã công đoạn" varchar(3) PROCESS_NUMBER "Số thứ tự CĐ" varch... [12]
- Dữ liệu LINE cần tải lên bảng mã liên kết ⑥ [9]
- Sau khi XML vào T_IF_PROD_RESULT, phía SAP/R3 sẽ tách dữ liệu theo cấu trúc GOODS_MOVE theo từng linh kiện. Điểm cần kiểm tra là stored procedure hoặc chương trình tạo XML có giới hạn nvarchar(4000) hay không. [2]
LIMITATIONS: incomplete_query_term_coverage
```

**B4 (13,42 giây — loại khỏi chấm điểm)**

```text
- Quản lý sản xuất PLM Opcenter MOM VPS MFG Chuẩn bị digital CN4T (Liên kết ECN Thông báo thay đổi <p:cNvPr id="183" name="図 182" descr="文字が書かれている 中程度の精度で自動的に生成された説明"> <a:bodyPr rot="0" spcFirstLastPara="0" vert="horz" wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" numCol="1" spcCol="0" rtlCol="0" fromWordArt="0" anchor="ctr" anchorCtr="1" forceAA="0" compatLnSpc="1"> M aster Thực hiện chế tạo / lập kế hoạch công đoạn Định nghĩa master công đoạn chế tạo Quản lý phẩm ・ Thiết kế thiết bị NX CAD Địa điểm X 100%BOP [3]
- làm việc APS - QLSX công đoạn kết APS→MOM (qua web Opcenter ) - QLSX Hoàn thành nhập Oricon - Kho, KTCT báo (= phần mềm <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"> Đăng ký quản lý tiến độ (MES) lên MES nhưng lệnh SX thông thường biểu thứ tự sản xuất Mở file excel “ 生産順位表 ( 本番サーバ )Ver_06.xlsm” ở trong link: \\fstvn01\Data\10_Production [8]
- Ngày 16,17/6/2026 Ban đầu: Thùng Oricon ....11922 và ...12860 đang nằm trên giá kệ, hệ thống quản lý kho WMS (Inter-Stock) ghi nhận tọa độ này đang "Có hàng". Lệnh nhập kho mới: Khi có một thùng hàng mới ( ...12626) cần cất vào kho, WMS quét thấy tọa độ đang "trống" (trên phần mềm, tại vị trí của 1/2 thùng trên) nên đã chỉ định ACR cất thùng mới vào chính tọa độ này. [11]
- 変更管理 指図登録 ／発行 PR (Problem Report) 部品調達 生産日程 計画 ECR PL→(メカ) ECN 1 承認 E-BOM (メカ) ECN 2 承認 E-BOM (電気) ECN 3 承認 E-BOM (ソフト) ECN 1 承認 M-BOM (メカ) MCN 連携 MOM連携 ECN 4 承認 安規申請 ECN 2 承認 M-BOM (電気) ECN 3 承認 M-BOM (ソフト) Team Center R3 所要量計算 Opcenter 製造計画 製造実行 ECO投入 シリアル登録 品目／REV R3-BOM 組立BOP 供給BOP BOE 製造完了 ・品質不具合 ・改善要望 ・変更連絡（部品） ECO 受取 (Eng. C21-2 Parts C0 Rev 01 └ └ └ Spec 2 Operation └ Resource Group └ Resource └ Product B0 └ Route step 1 Route step 2 ※複数品目有 ※単一品目 Parts B0 └ Product C0 ... [19]
- (1) Lập luận đầu tiên ・ID giao lộ ・Được định nghĩa theo định dạng [interSect_0] đến [interSect_63] (Không thể sao chép) (2) Lập luận thứ hai ・Địa chỉ của phần khối ・Địa chỉ được phân cách bằng dấu phẩy (,). Ví dụ [Tên máy tính: AthenaLSU-MCS] 6- 2 Đăng ký phần khối Mỗi đối số được phân tách bằng dấu phẩy (,). [9]
LIMITATIONS: incomplete_query_term_coverage
```

**B5 (12,11 giây)**

```text
- テーブルレイアウト システム名 テーブル名 部品入庫 T_PARTS_RECIEVE 合計 647 byte № データ項目名（日本語） （英字） タイプ 長さNULL P.key Idx1 Idx2 Idx3 Auto Default 備 考 1 入庫タイプ RECEIVE_TYPE varchar '':通常入庫'1':マニュアル入庫(検収対象外) 2 オリコンID ORICON_ID varchar 3 品目コード ITEM_CODE varchar ベンダー現品票情報(EDIのみは空白) 4 品目改訂レベル ITEM_REV varchar ベンダー現品票情報(EDIのみは空白) 5 入数 INNER_QTY decimal ベンダー現品票情報(EDIのみは空白) 6 ベンダーロット VENDOR_LOT varchar ベンダー現品票情報(EDIのみは空白) 7 荷受(現品票)HTユーザーID TAG_READ_HTID varchar 100 ベンダー現品票情報(EDIのみは空白) 8 購買発注番号 PO_NO varchar ベンダー現品票情報(EDIのみは空白) 9 購買発注明細番号 [3]
- Đối với nhóm 2, xóa dữ liệu trên SQL và cho nhập lại kho Thành công (OK): 4 thùng (6880%, 7087%, 7573%, 7715%). Phân loại lỗi chi tiết: Nhóm 1: Lỗi sai lệch dữ liệu hệ thống (1 thùng - 9702%) Nguyên nhân trên EDI đang tồn tại dữ liệu Lot sản xuất Nhóm 2: Lỗi Camera đọc mã QR ngoại quan các mặt (6 thùng) Hiện trạng: Báo các mã lỗi bắt đầu bằng 0201..., nguyên nhân do Camera không đọc được tem QR dán ở các mặt phụ (Trái/Phải/Trước/Sau) kết hợp lỗi CAM. [17]
- Bộ phận đã tạo raBộ phận Công nghệ Sản xuất Phòng Kỹ thuật Sản xuất số 2, Ban Kỹ thuật Sản xuất 21 Được tạo bởi: Kazuma Tsutsumi Chuỗi tiêu đề Công ty TNHH Giải pháp Tài liệu KYOCERA Văn bản chân trang Bộ điều khiển xử lý vật liệu Phiên bản <0.01> Hướng dẫn sử dụng (Matecon) - Dùng để điều khiển AGV / ACR / CTU - 作成 審査 承認 Confidential © 2022 KYOCERA Document Solutions Inc. Mục đích của cuốn sách này Cuốn sách này sử dụng bộ điều khiển xử lý vật liệu (sau đây gọi là "bộ điều khiển vật liệu"). [16]
- Để biết định nghĩa về tên tệp bản đồ lái xe, hãy xem [4.2 Định nghĩa về tên tệp bản đồ]. [11]
- , mã giá, Picking Cart ⊸Chỉđịnh PO từ thông tin nhập trước xuất trước quản lý theo VN-MES ⊸Đọc QR hóa đơn của thùng đã Picking ⊸Cho thùng vào xe đẩy Cấp phát bằng xe đẩy Chuyển kho Kho→Line Chuyển tồn kho Kho→Line Chỉthị xuất kho ⊸Kích hoạt xuất kho ：Kếhoạch công đoạn ⊸Chỉthị ID Oricon Tìm kiếm mã giá ⊸Đối ứng mã Tại nơi bảo quản quét QR của phiếu hiện vật (đại diện [9]
LIMITATIONS: incomplete_query_term_coverage
```

## 4. Chấm điểm theo luật ngữ cảnh

`scratch/e2v2_grade.py --answers C:\AIOS_p1_4\out\e2v2\ve_e2v2_answers.txt` (rc=1):
`B1=true` (đủ 3 mã), `B2=false` (thiếu cả 2 tên tệp), `B3=true` (khớp
`nvarchar\s*\(\s*4000\s*\)`), `B5=false` (`house_method_mentions=0`;
`raw_one_code_present=true` nhưng `raw_one_code_outside_house_method_windows=1` — đúng ca dương
tính giả đã cảnh báo: chuỗi `'1'` trong câu trả lời là của `RECEIVE_TYPE`), `DAT=false`.

Self-test bộ chấm (`--selftest`): **9/9 đối chứng ĐẠT** — vòng 1 B1=True/B2=False/B3=True/B5=False
đúng như đã công bố; khớp chuỗi thô `'1'` sẽ cho dương tính giả và luật ngữ cảnh từ chối nó;
đoạn bằng chứng lý tưởng (`HOUSE_METHOD varchar '0':倉庫へ格納'1':検査`) **qua** luật ngữ cảnh;
đối chứng âm (chỉ có chữ `HOUSE_METHOD`, thiếu giá trị) **rớt** đúng.

## 5. Không ghi lên D

| Phép kiểm | Kết quả |
| --- | --- |
| SHA-256 kho production trên D **trước** lượt chạy (06:05:14) | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca`, 2.552.659.968 byte, mtime `2026-09-28 05:55:03.247790600` |
| SHA-256 kho production trên D **sau** lượt chạy B1–B5 (06:12:35) | `062ec090…` — **không đổi** (size, mtime nguyên) |
| Snapshot cây D trước lượt (`snap_e2v2run_before.json`, 06:06:02→06:09:06) | **114.026 tệp** |
| Snapshot cây D sau lượt (`snap_e2v2run_after.json`, 06:11:21→06:12:35) | 114.026 tệp — diff **0 thêm / 0 xóa / 0 đổi** (`clean: true`) |
| Bản copy index trên C dùng để truy vấn | SHA khớp nguồn D (2.552.659.968 byte) — kiểm ngay trong lượt chạy |
| Cache xác minh model fp32 | còn tươi → `verify_model_tree` không ghi lại cache lên D (guard chặn nếu cũ) |
| Bytecode / temp | `PYTHONDONTWRITEBYTECODE=1`, `-B`, `TEMP`/`TMP` trỏ về C; nhật ký worker ghi về C (`C:\AIOS_p1_4\tri_thuc\logs\bge_worker.stderr.log`) |
| Bytecode cache **ngoài lượt chạy** | tiến trình phân tích của OMP (kernel chạy thiếu `-B`, lúc 06:14 và 06:18 — sau khi lượt chạy kết thúc) sinh lại 5 tệp `src/**/__pycache__/*.pyc` (`synthesis`, `pipeline`, `index`, `rag_v2/__init__`, `rag_v2_synthesis_provider`); tệp sinh tự động, **đã bị git-ignore** (`.gitignore`: `**/__pycache__/`), **không** thuộc lượt chạy B1–B5 (lượt chạy: snapshot 0/0/0, harness `-B` + `PYTHONDONTWRITEBYTECODE=1`) |
| Lượt dump sâu B2/B5 (06:14:47→06:16:49) | script khai báo ghi chỉ vào `C:\AIOS_p1_4\out\e2v2\`; không mở D để ghi |
| Git | cây làm việc sạch trước lượt chạy; phần push chỉ ghi markdown mailbox + `.git` |

Không `--apply`, không vacuum, không embed, không sửa mã sản phẩm, không sửa `.env`.

## 6. Kiểm chứng fail-closed (không gọi cloud dù khóa còn trong môi trường)

Điểm giữ nguyên so với E2: **không** làm rỗng biến môi trường khóa cloud.

| Phép kiểm | Kết quả |
| --- | --- |
| Khóa provider có trong env của tiến trình chạy | có: `CHATANYWHERE_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY` (chỉ ghi tên, không ghi giá trị) |
| `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS` | không đặt (`None`) — đúng mặc định TẮT |
| `provider_configs_from_env()` với env này | dựng được **6** cấu hình provider cloud — tức nếu thiếu fix thì nguy cơ là thật |
| `create_synthesis_provider()` (pre-flight + trong lượt chạy) | **`None`** |
| Cổng an toàn của harness trước khi khởi động worker | `synthesis_provider=none` → cho chạy |
| Cờ từng câu trả lời | `provider_used=false` cho cả 5 câu; `mode=local_extractive` |
| stderr của worker | 1 dòng duy nhất: `bge_worker_stage backend=onnx init_ms=32009.071`; **0 dòng** khớp mẫu gọi provider (`All synthesis providers failed`, `Synthesis via …`, `provider_used=true`) |
| Lấy mẫu mạng khi đang truy vấn B2/B5 (`C:\AIOS_p1_4\tmp\e2v2_dump_b2b5.py`) | 51 lần lấy mẫu `netstat -ano` cho cả cây tiến trình (4 PID: 1096, 8472, 12740, 15536) → **0 kết nối** TCP/UDP |

Ghi chú: lượt lấy mẫu mạng có `netstat`/`wmic` làm chậm máy — **không** dùng số giây của lượt dump
(59,87 và 17,00) làm latency chính thức; latency chính thức lấy ở mục 3.

## 7. Nguyên nhân gốc (vì sao fix vòng 2 chưa phủ B5/B2)

### 7.1. B5 — hoà điểm vì tên bảng cũng bị tính là "mã trường"

Trích mã từ câu hỏi B5 bằng chính hàm của fix:
`_extract_field_codes(B5) = ('t_parts_recieve', 'house_method')` — **tên bảng `T_PARTS_RECIEVE`
cũng khớp `_FIELD_CODE_RE = [A-Z][A-Z0-9_]{3,}`**, nên được cấp cùng trọng số với mã trường được hỏi.
Hệ quả: mọi mảnh chứa "mã trường" bất kỳ đều được 1 điểm ở khóa đầu; **1-1 là hoà**, thắng thua
do các khóa cũ phía sau quyết định.

Trace bằng chính `_fragment_score` trên 2 mảnh thật (dump `C:\AIOS_p1_4\out\e2v2\e2v2_dump_b2b5.json`,
`prioritize_literals=True`, khóa = `(field_code, file_id, typed_value, answer_value, literal_overlap, terms∩, -len)`):

| Mảnh | Vị trí trong pack | Ký tự | `score` truy xuất | Khóa điểm | Ghi chú |
| --- | --- | ---: | ---: | --- | --- |
| `[3]` — bảng `T_PARTS_RECIEVE` (doc `wsc-ff8304af86028eaa…`) | 3/19 | 993 | 2,0 | `(1, 0, 0, 12, 2, 2, -507)` | overlap `t_parts_recieve`=1, `house_method`=0 |
| `[12]` — **định nghĩa** `HOUSE_METHOD` (cùng doc) | 12/19 | 371 | 1,0 | `(1, 0, 0, 11, 1, 1, -371)` | overlap `house_method`=1, `t_parts_recieve`=0 |

Hai mảnh **hoà ở khóa 1**; mảnh `[3]` thắng ở `answer_value` (12 so với 11) → định nghĩa `HOUSE_METHOD`
không được chọn vào câu trả lời. Nguyên văn mảnh `[12]` (từ dump):
`… 19 格納方法 HOUSE_METHOD varchar '0':倉庫へ格納'1':検査 20 荷受(伝票)HTユーザーID …`.

Lưu ý: mảnh `[19]` cùng tài liệu chứa `検査` cũng có trong pack nhưng không có `HOUSE_METHOD`/giá trị mã.

### 7.2. B2 — ưu tiên mã tệp không kích hoạt vì câu hỏi không có tên tệp

`_extract_file_identifiers(B2) = ()` — câu hỏi chỉ nói "tên tệp thực thi (.exe)" chung chung,
không nêu `YY2-Z151.exe`/`YY2-Z152.exe`, mà `_FILE_IDENTIFIER_RE` chỉ bắt các tên tệp **có trong câu hỏi**.
Hệ quả: khóa `file_identifier` = 0 cho **mọi** mảnh → fix không đổi gì cho B2.

Trace (cùng cấu hình trên, `prioritize_literals=True`):

| Mảnh | Vị trí | Ký tự | `score` truy xuất | Khóa điểm thực tế | Nếu câu hỏi có tên tệp |
| --- | --- | ---: | ---: | --- | --- |
| `[1]` — chứa `YY2-Z151` + `YY2-Z152` + `.exe` (doc `wsc-5035a3d752d88cc0…`) | 1/10 | 837 | 29,0 | `(0, 0, 0, 0, 0, 6, -145)` | `(0, 2, 0, 0, 0, 6, -145)` → **thắng** |
| `[5]`,`[6]`,`[10]`… (các mảnh được chọn) | 5/6/10 | ~970 | 30–36 | `(0, 0, 0, 0, 0, 8, …)` | không đổi |

Nghĩa là: cơ chế ưu tiên mã tệp **đúng** khi câu hỏi nêu tên tệp cụ thể, nhưng B2 hỏi **chung**
"tệp `.exe` dành riêng cho ACR/CTU" nên không có tên để trích → mảnh chứa 2 tên tệp vẫn bị điểm
`terms∩=6 < 8` hạ hạng như vòng 1.

### 7.3. Gợi ý phạm vi fix vòng 3 (để Muse quyết định)

1. **B5**: đừng cho tên bảng cùng trọng số với mã trường được hỏi — tối thiểu (a) loại token dạng
   `T_<TÊN>` (tên bảng kiểu `T_PARTS_RECIEVE`, `T_IF_PROD_RESULT`) khỏi `_extract_field_codes`, hoặc
   (b) chỉ cấp điểm ưu tiên cho mảnh chứa mã trường **kèm giá trị mã hóa** (mảnh chứa
   `field_code` *và* chuỗi trích dẫn/`'0'`/`'1'`) — đúng hình dạng dòng định nghĩa cần lấy.
2. **B2**: khi câu hỏi có tín hiệu "tệp thực thi"/`.exe` nhưng **không** nêu tên cụ thể, lấy neo từ
   pack: ưu tiên mảnh chứa `*.exe` identifier bất kỳ (thay vì chỉ tên nêu trong câu hỏi).
3. **Test**: bổ sung 2 ca test cho đúng 2 khe hở này (hiện 5 test mới của Phase A chỉ phủ trường hợp
   tên tệp có trong câu hỏi và mã trường không bị nhiễu bởi tên bảng): (a) câu hỏi chứa cả tên bảng
   `T_*` lẫn mã trường, mảnh định nghĩa phải thắng mảnh bảng; (b) câu hỏi hỏi chung "`*.exe`",
   mảnh chứa tên tệp phải được chọn.

## 8. Lệnh tái lập và artifact

```powershell
# 1. Cổng vé + pre-flight (read-only)
.venv/Scripts/python.exe -B scratch/e2v2_gate_check.py
.venv/Scripts/python.exe -B scratch/e2v2_preflight.py          # blocking=[] mới chạy tiếp

# 2. Lượt chính B1–B5
.venv/Scripts/python.exe -B scratch/e2v2_smoke.py              # 06:09:13 → 06:11:11

# 3. Chấm điểm theo luật ngữ cảnh (+ self-test đối chứng)
.venv/Scripts/python.exe -B scratch/e2v2_grade.py --answers C:/AIOS_p1_4/out/e2v2/ve_e2v2_answers.txt
.venv/Scripts/python.exe -B scratch/e2v2_grade.py --selftest

# 4. Dump sâu B2/B5 + lấy mẫu mạng (script trên C, không ghi D)
.venv/Scripts/python.exe -B C:/AIOS_p1_4/tmp/e2v2_dump_b2b5.py

# 5. Snapshot + SHA kho D (chứng minh không ghi D)
.venv/Scripts/python.exe -B C:/AIOS_p1_4/tmp/e2v2_snap.py snap C:/AIOS_p1_4/out/e2v2/snap_e2v2run_before.json
.venv/Scripts/python.exe -B C:/AIOS_p1_4/tmp/e2v2_snap.py diff C:/AIOS_p1_4/out/e2v2/snap_e2v2run_before.json C:/AIOS_p1_4/out/e2v2/snap_e2v2run_after.json C:/AIOS_p1_4/out/e2v2/snap_e2v2run_diff.json
```

Artifact trên C (`C:\AIOS_p1_4\`):
`out\e2v2\preflight.json`, `out\e2v2\ve_e2v2_report.json`, `out\e2v2\ve_e2v2_raw.jsonl`,
`out\e2v2\ve_e2v2_answers.txt`, `out\e2v2\ve_e2v2_worker_stderr.log`,
`out\e2v2\snap_e2v2run_before.json`/`snap_e2v2run_after.json`/`snap_e2v2run_diff.json`,
`out\e2v2\d_index_sha_e2v2run_before.txt`/`d_index_sha_e2v2run_after.txt`,
`out\e2v2\answers_round1_vs_round2.diff`, `out\e2v2\e2v2_dump_b2b5.json`, `tmp\e2v2_dump_b2b5.py`.

## 9. Việc tiếp theo

- Verdict trình Muse: **CHƯA ĐẠT** — cần Phase A vòng 3 cho đúng 2 khe hở ở mục 7 (B5: nhiễu tên
  bảng; B2: neo `.exe` không có tên cụ thể trong câu hỏi).
- Hàng đợi cũ giữ nguyên (chưa làm ở vé này): 422/496 document stale cần lượt chuẩn bị lại có ghi;
  xác nhận `source_path` `..._canary/materialized_sources/`; E3 dọn XML ở extractor; E4 ONNX fp32 default.
