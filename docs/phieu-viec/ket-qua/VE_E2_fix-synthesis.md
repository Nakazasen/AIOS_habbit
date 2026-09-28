# Báo cáo Vé E2 — Phase B: chạy lại B1–B5 sau fix synthesis

Ngày: 2026-09-29 (giờ `+07`), máy `h410asrock`. Nhánh: `phieu-viec/rag-fix1`.
Vé: `docs/phieu-viec/mailbox/prompt.md` (Muse phát 00:05, cổng Phase B mở 00:36 với
`e2_fix_commit` = `58ec138`). Không đụng `main`, không force-push.

## Kết luận

**CHƯA ĐẠT** theo tiêu chí của vé: B3 đã nêu được `nvarchar(4000)` (điểm rớt của P1.4 nay
đã qua), nhưng **B5 vẫn rớt** phần định nghĩa `HOUSE_METHOD` — bằng chứng vẫn nằm trong
tập truy xuất nhưng bộ soạn không chọn dòng đó.

Ngoài ra lượt này phát hiện **một điểm thoái lui so với P1.4**: B2 mất hai tên tệp
`YY2-Z151.exe` / `YY2-Z152.exe` (P1.4 đã có). Đây là điểm mới, chưa nằm trong tiêu chí
của vé, nên báo cáo nêu riêng ở mục 6 để Muse quyết định.

Các tiêu chí còn lại của vé đều ĐẠT: B1/B2/B3/B5 chạy xong không lỗi/không timeout, câu
trả lời grounded từ bằng chứng truy xuất, **không byte nào ghi lên D**, và **không dữ liệu
nào rời máy dù khóa cloud vẫn còn trong môi trường** (kiểm chứng fail-closed).

## 1. Phạm vi và cách chạy

### 1.1. Mã đã pull

- `dd1e7a7` — E1 đợt 2 vào repo (`docs/phieu-viec/ket-qua/E1_synthesis-dieu-tra-dot2.md`).
- `725c40f` — fix synthesis theo E1 (chọn claim theo giá trị, quota summary, facet nhiều
  claim, `prioritize_body_evidence` mặc định cho lookup/diagnosis/câu hỏi có mã-số, repair
  nén thay vì xóa, validation loại dòng lỗi giữ dòng đúng).
- `58ec138` — fail-closed `create_synthesis_provider()` (chỉ dựng provider cloud khi
  `allow_cloud=True` hoặc `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS` truthy; mặc định TẮT).
- `49a7045` — mailbox: Phase A xong, mở cổng Phase B.

### 1.2. Đường chạy (giống P1.4)

| Tham số | Giá trị |
| --- | --- |
| Index | bản copy trên C `C:\AIOS_p1_4\tri_thuc\library.sqlite`, mở `mode=ro` |
| SHA bản copy (kiểm trong lượt chạy) | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` — khớp nguồn D |
| Nguồn đưa vào truy vấn | 74/496 document (422 document stale `file_changed_since_ingest`); 1.064/107.331 đoạn truy vấn được |
| Đường truy vấn | worker BGE subprocess (`BgeSubprocessWorkerClient`), như app |
| Backend | ONNX fp32 (`BGE_BACKEND=onnx`), `onnxruntime 1.28.0`, Python 3.11.14, CPU |
| Fingerprint model | `016c5255…` — khớp vector trong index (guard chặn nếu khác) |
| Khởi tạo worker | 43,626 giây |
| `enable_network` / `enable_provider_synthesis` | `False` / `False` |
| Ngân sách mỗi câu | 180 giây |
| B4 | chạy đủ nhưng **loại khỏi chấm điểm** (theo vé) |

Harness: `scratch/e2_smoke.py` (bản E2 của `p1_4_smoke.py`, git-ignore). Khác P1.4 đúng ba
điểm: (a) **không làm rỗng khóa provider** trong môi trường, (b) cổng an toàn chạy trước
mọi bước nặng — bắt buộc `create_synthesis_provider()` trả `None`, (c) kiểm SHA bản copy
index và quét `bge_worker.stderr.log` sau lượt chạy.

Lệnh chạy: `.venv/Scripts/python.exe -B scratch/e2_smoke.py` (00:22:35 → 00:27:25).

## 2. Diff hành vi trước / sau fix

Cùng câu hỏi, cùng tập nguồn, cùng tuyến nội bộ. "Trước" = lượt P1.4
(`docs/phieu-viec/ket-qua/VE_P1_4_smoke-test-noi-bo.md`), "sau" = lượt này.

| Câu | Dữ kiện tham chiếu trong **câu trả lời** (P1.4 → E2) | Độ dài câu trả lời | Kết luận |
| --- | --- | ---: | --- |
| B1 | `11922`, `12860`, `12626` → **giữ đủ cả 3** | 1.131 → 1.593 ký tự | Giữ, phủ rộng hơn |
| B2 | `YY2-Z151.exe`, `YY2-Z152.exe` → **mất cả hai** | 833 → 827 | **Thoái lui** |
| B3 | chỉ `4000` → **nay có nguyên văn `nvarchar(4000)`** | 1.113 → 1.482 | **Đã sửa** |
| B4 | không có (đúng loại trừ) → không có | 2.016 → 2.271 | Loại khỏi chấm |
| B5 | không có định nghĩa `HOUSE_METHOD` → **vẫn không có** | 1.532 → 1.994 | **Chưa sửa được** |

Latency (giây, không tính khởi tạo worker và warmup): B1 `50,78 → 52,75`; B2 `18,19 → 21,55`;
B3 `19,61 → 17,51`; B4 `39,58 → 46,39` (loại); B5 `21,95 → 24,92`. Warmup lượt này 48,75 giây.

## 3. Kết quả B1–B5

### 3.1. Bảng tổng hợp

| Câu | Giây | Lỗi | Abstain | Đường | Chế độ | Grounded | Trích dẫn | Đoạn bằng chứng | Ứng viên / trả về | Phủ thuật ngữ | Đối chiếu tham chiếu |
| --- | ---: | --- | --- | --- | --- | --- | ---: | ---: | --- | ---: | --- |
| B1 | 52,75 | không | không | hybrid | `local_extractive` | có | 5 | 16 | 192 / 15 | 0,925 | **Đúng**: đủ `11922`, `12860`, `12626` kèm ngữ cảnh Oricon |
| B2 | 21,55 | không | không | hybrid | `local_extractive` | có | 5 | 10 | 145 / 15 | 0,897 | **Chưa**: thiếu `YY2-Z151.exe` / `YY2-Z152.exe` (bằng chứng có) |
| B3 | 17,51 | không | không | hybrid | `local_extractive` | có | 5 | 12 | 190 / 15 | 0,935 | **Đúng**: nêu nguyên văn `nvarchar(4000)` và giới hạn 4000 ký tự |
| B4 | 46,39 | không | không | hybrid | `local_extractive` | có | 5 | 20 | 221 / 15 | 0,806 | Loại khỏi chấm theo vé |
| B5 | 24,92 | không | không | hybrid | `local_extractive` | có | 5 | 19 | 200 / 15 | 0,774 | **Chưa**: bằng chứng có định nghĩa ở đoạn `[12]` nhưng câu trả lời không chọn |

- `filtered_as_stale_count` = 0 cho cả 5 câu; không câu nào `degraded`; cả 5 câu có cảnh báo
  mềm `incomplete_query_term_coverage`.
- Mọi câu: `provider_used=false`, `mode=local_extractive`, `abstained=false`, 5 trích dẫn.

### 3.2. Toàn văn câu trả lời

**B1 (52,75 giây)**

```text
- Ngày 16,17/6/2026 Ban đầu: Thùng Oricon ....11922 và ...12860 đang nằm trên giá kệ, hệ thống quản lý kho WMS (Inter-Stock) ghi nhận tọa độ này đang "Có hàng". Lệnh nhập kho mới: Khi có một thùng hàng mới ( ...12626) cần cất vào kho, WMS quét thấy tọa độ đang "trống" (trên phần mềm, tại vị trí của 1/2 thùng trên) nên đã chỉ định ACR cất thùng mới vào chính tọa độ này. [2]
- LỖI BOP-MOM / WORKCENTER / SUP_PROCESS ẢNH HƯỞNG CTU VÀ XUẤT KHO ------------------------------------------------------------ Ngày phát sinh/ghi nhận: 25/06/2026-26/06/2026; được nhắc lại khi đối ứng các lỗi SUP_PROCESS sau đó. [12]
- (1) Thông tin lỗi ①Số ・Số đơn vị AGV ②Trạng thái ・trạng thái thực thi nhiệm vụ AGV C1J: 0: Không hoạt động, 1: Bận, 2: Lỗi Atlas: 99 đã sửa [ErrorInfo]タブ (1) [11]
- phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu và hoàn thành ⊸Tạo thông tin bắt đầu sản xuất Opcenter ⊸Thực hiện xử lý bắt đầu sản xuất Opcenter ⊸Nhận thông tin kế hoạch Excel ⊸Lập bảng trình tự sản xuất Đăng ký thời gian bắt đầu Lập kế hoạch ～Bắt tay vào sản xuất Đọc Barcode S/No. [15]
- Phân loại lỗi chi tiết: Nhóm 1: Lỗi sai lệch dữ liệu hệ thống (1 thùng - 9702%) Nguyên nhân trên EDI đang tồn tại dữ liệu Lot sản xuất Nhóm 2: Lỗi Camera đọc mã QR ngoại quan các mặt (6 thùng) Hiện trạng: Báo các mã lỗi bắt đầu bằng 0201..., nguyên nhân do Camera không đọc được tem QR dán ở các mặt phụ (Trái/Phải/Trước/Sau) kết hợp lỗi CAM. 7 thùng: Phát sinh cảnh báo từ hệ thống, ORICON_STATUS khác '0000000000000001' và bị đẩy ra cổng NG. [3]
LIMITATIONS: incomplete_query_term_coverage
```

**B2 (21,55 giây)**

```text
- Dữ liệu được lưu ở định dạng CSV, và phần mềm Matecon sẽ đọc bản đồ lái xe khi khởi động. [5]
- Một hệ thống điều khiển đưa ra các chỉ dẫn lái xe cho AGV/ACR/CTU, giám sát trạng thái hoạt động của chúng và điều khiển các giao lộ và đoạn đường. [6]
- Nắm vững các phương pháp vận hành và quy trình cấu hình để điều khiển và giám sát AGV/ACR/CTU. [10]
- Sau khi thực hiện bất kỳ thay đổi nào, hãy nhớ khởi động lại phần mềm Matecon. [2]
- 8- 1 Cấu hình màn hình hiển thị phần mềm Matecon (CTU) 8- 1 [Trạng thái] tab Màn hình chính của phần mềm Matecon (1) Trạng thái ・Trạng thái thực thi phần mềm Matecon (2) Trạng thái AGV ①Idx ・Trình tự thiết lập liên lạc với người kiểm soát vật tư ②Số ・Số đơn vị AGV ③Kết nối ・Cho biết liệu việc giám sát AGV có đang được thực hiện hay không. [3]
LIMITATIONS: incomplete_query_term_coverage
```

**B3 (17,51 giây)**

```text
- Trong một số trường hợp VN có khoảng 150 item tiêu hao, XML vượt quá giới hạn nvarchar(4000), dẫn đến lỗi xử lý và không insert được vào bảng. LỖI LIÊN QUAN ĐẾN T_IF_PROD_RESULT VÀ XML TIÊU HAO LINH KIỆN ------------------------------------------------------------ Ngày phát sinh/ghi nhận: Chưa xác định ngày cụ thể trong dữ liệu hiện có; ghi nhận khi VN liên kết khoảng 150 item tiêu hao và XML vượt 4000 ký tự. [1]
- MOM Control PLC Hệ thống xung quanh MOM Hệ thống hiện tại R3 Vị trí Line sản xuất System Phát hành lệnh sản xuất APS ⊸Lập kế hoạh công đoạn Bảng liên kết lệnh Bắt đầu lắp ráp Lắp ráp Điều chỉnh／Kiểm tra Đóng gói Dừng Line Quản lý tiến độ ⊸Phân số Serial Công cụ IF ⊸Chia lệnh theo đơn vị Serial Opcenter ⊸Lập kế hoạch cung cấp Opcenter ⊸Liên kết thiết bị kế hoạch công đoạn Opcenter ⊸Liên kết thiết bị kế hoạch cung cấp Đến lưu trình cấp phát In Barcode số Serial In bảng thành tích Đọc Barcode Hệthống đăng ký bắt đầu [10]
- à máy" varchar(3) BUILDING "Tòa nhà" varchar(2) FLOOR "Tầng" varchar(5) LINE "Chuyền" varchar(9) WORKER_ID "ID Công nhân" varchar(26) TRACEABILITY_ID "Mã truy vết" varchar(16) PROCESS_ID "Mã công đoạn" varchar(3) PROCESS_NUMBER "Số thứ tự CĐ" varch... [12]
- Dữ liệu LINE cần tải lên bảng mã liên kết ⑥ [9]
- Thông tin về bảng T_IF_PROD_RESULT Ngày phát sinh/ghi nhận: Chưa xác định ngày cụ thể trong file hiện tại; lỗi được ghi nhận khi VN liên kết lượng lớn dữ liệu tiêu hao linh kiện. [3]
LIMITATIONS: incomplete_query_term_coverage
```

**B4 (46,39 giây — loại khỏi chấm điểm)**

```text
- Quản lý sản xuất PLM Opcenter MOM VPS MFG Chuẩn bị digital CN4T (Liên kết ECN Thông báo thay đổi <p:cNvPr id="183" name="図 182" descr="文字が書かれている 中程度の精度で自動的に生成された説明"> <a:bodyPr rot="0" spcFirstLastPara="0" vert="horz" wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" numCol="1" spcCol="0" rtlCol="0" fromWordArt="0" anchor="ctr" anchorCtr="1" forceAA="0" compatLnSpc="1"> M aster Thực hiện chế tạo / lập kế hoạch công đoạn Định nghĩa master công đoạn chế tạo Quản lý phẩm ・ Thiết kế thiết bị NX CAD Địa điểm X 100%BOP [3]
- làm việc APS - QLSX công đoạn kết APS→MOM (qua web Opcenter ) - QLSX Hoàn thành nhập Oricon - Kho, KTCT báo (= phần mềm <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"> Đăng ký quản lý tiến độ (MES) lên MES nhưng lệnh SX thông thường biểu thứ tự sản xuất Mở file excel “ 生産順位表 ( 本番サーバ )Ver_06.xlsm” ở trong link: \\fstvn01\Data\10_Production [8]
- Ngày 16,17/6/2026 Ban đầu: Thùng Oricon ....11922 và ...12860 đang nằm trên giá kệ, hệ thống quản lý kho WMS (Inter-Stock) ghi nhận tọa độ này đang "Có hàng". Lệnh nhập kho mới: Khi có một thùng hàng mới ( ...12626) cần cất vào kho, WMS quét thấy tọa độ đang "trống" (trên phần mềm, tại vị trí của 1/2 thùng trên) nên đã chỉ định ACR cất thùng mới vào chính tọa độ này. [11]
- 変更管理 指図登録 ／発行 PR (Problem Report) 部品調達 生産日程 計画 ECR PL→(メカ) ECN 1 承認 E-BOM (メカ) ECN 2 承認 E-BOM (電気) ECN 3 承認 E-BOM (ソフト) ECN 1 承認 M-BOM (メカ) MCN 連携 MOM連携 ECN 4 承認 安規申請 ECN 2 承認 M-BOM (電気) ECN 3 承認 M-BOM (ソフト) Team Center R3 所要量計算 Opcenter 製造計画 製造実行 ECO投入 シリアル登録 品目／REV R3-BOM 組立BOP 供給BOP BOE 製造完了 ・品質不具合 ・改善要望 ・変更連絡（部品） ECO 受取 (Eng. C21-2 Parts C0 Rev 01 └ └ └ Spec 2 Operation └ Resource Group └ Resource └ Product B0 └ Route step 1 Route step 2 ※複数品目有 ※単一品目 Parts B0 └ Product C0 ... [19]
- (1) Lập luận đầu tiên ・ID giao lộ ・Được định nghĩa theo định dạng [interSect_0] đến [interSect_63] (Không thể sao chép) (2) Lập luận thứ hai ・Địa chỉ của phần khối ・Địa chỉ được phân cách bằng dấu phẩy (,). Ví dụ [Tên máy tính: AthenaLSU-MCS] 6- 2 Đăng ký phần khối Mỗi đối số được phân tách bằng dấu phẩy (,). [9]
LIMITATIONS: incomplete_query_term_coverage
```

**B5 (24,92 giây)**

```text
- テーブルレイアウト システム名 テーブル名 部品入庫 T_PARTS_RECIEVE 合計 647 byte № データ項目名（日本語） （英字） タイプ 長さNULL P.key Idx1 Idx2 Idx3 Auto Default 備 考 1 入庫タイプ RECEIVE_TYPE varchar '':通常入庫'1':マニュアル入庫(検収対象外) 2 オリコンID ORICON_ID varchar 3 品目コード ITEM_CODE varchar ベンダー現品票情報(EDIのみは空白) 4 品目改訂レベル ITEM_REV varchar ベンダー現品票情報(EDIのみは空白) 5 入数 INNER_QTY decimal ベンダー現品票情報(EDIのみは空白) 6 ベンダーロット VENDOR_LOT varchar ベンダー現品票情報(EDIのみは空白) 7 荷受(現品票)HTユーザーID TAG_READ_HTID varchar 100 ベンダー現品票情報(EDIのみは空白) 8 購買発注番号 PO_NO varchar ベンダー現品票情報(EDIのみは空白) 9 購買発注明細番号 [3]
- Đối với nhóm 2, xóa dữ liệu trên SQL và cho nhập lại kho Thành công (OK): 4 thùng (6880%, 7087%, 7573%, 7715%). Phân loại lỗi chi tiết: Nhóm 1: Lỗi sai lệch dữ liệu hệ thống (1 thùng - 9702%) Nguyên nhân trên EDI đang tồn tại dữ liệu Lot sản xuất Nhóm 2: Lỗi Camera đọc mã QR ngoại quan các mặt (6 thùng) Hiện trạng: Báo các mã lỗi bắt đầu bằng 0201..., nguyên nhân do Camera không đọc được tem QR dán ở các mặt phụ (Trái/Phải/Trước/Sau) kết hợp lỗi CAM. [17]
- Bộ phận đã tạo raBộ phận Công nghệ Sản xuất Phòng Kỹ thuật Sản xuất số 2, Ban Kỹ thuật Sản xuất 21 Được tạo bởi: Kazuma Tsutsumi Chuỗi tiêu đề Công ty TNHH Giải pháp Tài liệu KYOCERA Văn bản chân trang Bộ điều khiển xử lý vật liệu Phiên bản <0.01> Hướng dẫn sử dụng (Matecon) - Dùng để điều khiển AGV / ACR / CTU - 作成 審査 承認 Confidential © 2022 KYOCERA Document Solutions Inc. Mục đích của cuốn sách này Cuốn sách này sử dụng bộ điều khiển xử lý vật liệu (sau đây gọi là "bộ điều khiển vật liệu"). [16]
- Để biết định nghĩa về tên tệp bản đồ lái xe, hãy xem [4.2 Định nghĩa về tên tệp bản đồ]. [11]
- , mã giá, Picking Cart ⊸Chỉđịnh PO từ thông tin nhập trước xuất trước quản lý theo VN-MES ⊸Đọc QR hóa đơn của thùng đã Picking ⊸Cho thùng vào xe đẩy Cấp phát bằng xe đẩy Chuyển kho Kho→Line Chuyển tồn kho Kho→Line Chỉthị xuất kho ⊸Kích hoạt xuất kho ：Kếhoạch công đoạn ⊸Chỉthị ID Oricon Tìm kiếm mã giá ⊸Đối ứng mã Tại nơi bảo quản quét QR của phiếu hiện vật (đại diện [9]
LIMITATIONS: incomplete_query_term_coverage
```

## 4. Kiểm chứng fail-closed (không gọi cloud dù khóa còn trong môi trường)

Điểm mới của vé so với P1.4: **không** làm rỗng biến môi trường khóa cloud.

| Phép kiểm | Kết quả |
| --- | --- |
| Khóa provider có trong env của tiến trình chạy | có: `CHATANYWHERE_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY` (chỉ ghi tên, không ghi giá trị) |
| `AIOS_SYNTHESIS_ALLOW_CLOUD_PROVIDERS` | không đặt (`None`) — đúng mặc định TẮT |
| `provider_configs_from_env()` với env này | dựng được **6** cấu hình provider cloud (gemini, openrouter, groq, deepseek, mistral, chatanywhere) — tức nếu thiếu fix thì nguy cơ là thật |
| **Trước fix** (probe trên mã cũ, env nguyên) | `create_synthesis_provider()` → `RouterSynthesisProvider` (**không** None) |
| **Sau fix** (probe trên mã đã pull, cùng env) | `create_synthesis_provider()` → **`None`** |
| Cổng an toàn của harness trước khi khởi động worker | `synthesis_provider=none` → cho chạy |
| Cờ từng câu trả lời | `provider_used=false` cho cả 5 câu; `mode=local_extractive` |
| stderr của worker | 1 dòng duy nhất: `bge_worker_stage backend=onnx init_ms=43316.402`; **0 dòng** khớp mẫu gọi provider (`All synthesis providers failed`, `Synthesis via …`) |
| Lấy mẫu mạng khi đang truy vấn B5 (`scratch/e2_b5_netcheck.py`) | 44 lần lấy mẫu `netstat -ano` cho cả cây tiến trình (4 PID: 1452, 6024, 12604, 12980) → **0 kết nối** TCP/UDP |

Ghi chú: lượt lấy mẫu mạng chạy 66,128 giây cho B5 — **không** dùng số này làm latency, vì
`netstat`/`wmic` làm chậm máy (latency chính thức lấy ở mục 3).

## 5. Không ghi lên D

| Phép kiểm | Kết quả |
| --- | --- |
| SHA-256 kho production trên D **trước** lượt chạy (00:1x) | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` |
| SHA-256 kho production trên D **sau** toàn bộ lượt chạy B1–B5 | `062ec090…` — **không đổi** |
| Snapshot gốc dữ liệu D trước/sau lượt B1–B5 | 2.190 → 2.190 file, **0 file thêm/xóa/đổi** (`clean: true`) |
| Snapshot gốc dữ liệu D trước/sau lượt lấy mẫu mạng | 2.191 → 2.191 file, **0 file thêm/xóa/đổi** (`clean: true`) |
| Bản copy index trên C dùng để truy vấn | SHA khớp nguồn D (2.552.659.968 byte) — kiểm ngay trong lượt chạy |
| Cache xác minh model fp32 | còn tươi → `verify_model_tree` không ghi lại cache lên D |
| Bytecode / temp | `PYTHONDONTWRITEBYTECODE=1`, `-B`, `TEMP`/`TMP` trỏ về C; nhật ký worker ghi về C |

Không `--apply`, không vacuum, không embed, không sửa mã sản phẩm, không sửa `.env`.
Cây làm việc git sạch trước và sau lượt chạy.

## 6. Điểm rớt còn lại (chi tiết để Muse fix vòng sau)

### 6.1. B5 — định nghĩa `HOUSE_METHOD` vẫn không vào câu trả lời

Từ lượt dump chi tiết (`C:\AIOS_p1_4\out\e2\ve_e2_b5_netcheck.json`), tập bằng chứng có
**19 đoạn**, trong đó **đúng 1 đoạn** chứa định nghĩa:

- Trích dẫn `[12]`, document `wsc-ff8304af86028eaa474a1706`, **371 ký tự**, vị trí **11/19**
  trong pack, `score=1.0`.
- Nguyên văn trong đoạn: `… 18 オリコン状態 ORICON_STATUS varchar オリコンのチェック結果状態を示すコード
  19 格納方法 HOUSE_METHOD varchar '0':倉庫へ格納'1':検査 20 荷受(伝票)HTユーザーID SLIP_READ_HTID varchar …`
- Câu trả lời chỉ trích dẫn `[3]`, `[17]`, `[16]`, `[11]`, `[9]` — **không có `[12]`**.

⇒ Rớt ở **khâu chọn dòng để soạn câu trả lời**, không phải ở truy xuất hay đóng gói bằng
chứng (đoạn đáp án đã nằm trong pack). Đây đúng loại lỗi đã ghi ở E1 (nhóm A/B) nhưng fix
vòng này chưa phủ được trường hợp: đoạn đáp án là **bảng tiếng Nhật** nằm ở giữa danh sách,
không có trùng khớp từ vựng với câu hỏi tiếng Việt ngoài chính mã trường `HOUSE_METHOD`.

Cảnh báo khi chấm tự động: câu trả lời B5 **có** chuỗi `'1'` — nhưng đó là `'1':マニュアル入庫`
của trường `RECEIVE_TYPE` (đoạn `[3]`), **không phải** giá trị của `HOUSE_METHOD`. Chấm bằng
khớp chuỗi thô sẽ ra dương tính giả; phải chấm theo ngữ cảnh `HOUSE_METHOD` + `倉庫`/`検査`.

### 6.2. B2 — thoái lui so với P1.4

- P1.4: câu trả lời có dòng `[Trong trường hợp của Matecon CTU] YY2-Z151.exe YY2-Z152.exe … [1]`.
- Lượt này: câu trả lời trích `[5]`, `[6]`, `[10]`, `[2]`, `[3]`; không còn tên tệp `.exe`.
- Bằng chứng vẫn còn trong pack: đoạn `[1]`, document `wsc-5035a3d752d88cc0e20eb4c3`,
  `score=29.0`, có `YY2-Z151`/`YY2-Z152`.

⇒ Nghi vấn: thay đổi chấm điểm claim theo giá trị (fix số 1 của Phase A) đã hạ hạng dòng
chứa mã tệp trong câu hỏi này. Đề xuất Muse xem lại trọng số cho **mã định danh dạng tệp**
(`*.exe`) trong `_compose_grounded_claims`.

## 7. Tiêu chí ĐẠT của vé

| Tiêu chí | Kết quả | Bằng chứng |
| --- | --- | --- |
| B1/B2/B3/B5 chạy xong, không lỗi, không timeout | ĐẠT | Mục 3.1: 52,75 / 21,55 / 17,51 / 24,92 giây; B4 chạy đủ 46,39 giây; không câu nào lỗi/abstain/timeout |
| B3 nêu được `nvarchar(4000)` | **ĐẠT** | Câu trả lời B3 dòng đầu: “… XML vượt quá giới hạn nvarchar(4000) …” |
| B5 nêu được định nghĩa `HOUSE_METHOD` (`'0'` cất vào kho / `'1'` kiểm tra) | **RỚT** | Mục 6.1: đoạn `[12]` có định nghĩa trong pack nhưng không được chọn vào câu trả lời |
| Câu trả lời grounded từ bằng chứng truy xuất (không bịa) | ĐẠT | `grounded=true`, `provider_used=false`, `mode=local_extractive`, 5 trích dẫn/câu; mọi dữ kiện nêu ra đều có trong đoạn bằng chứng tương ứng |
| Không byte nào ghi lên D (kiểm chứng được) | ĐẠT | Mục 5: SHA kho D sau chạy `062ec090…` không đổi; 2 lượt snapshot 0 thay đổi |
| Không dữ liệu nào rời máy, kể cả khi khóa cloud có trong env | ĐẠT | Mục 4: guard `None` với 6 khóa còn nguyên; `provider_used=false`; stderr 0 dòng provider; 44 mẫu mạng = 0 kết nối |

**Rớt 1 trong 2 dòng kiểm then chốt (B5) ⇒ vé CHƯA ĐẠT.**

## 8. Kiểm chứng phụ trên máy này

- `pytest tests/test_rag_v2_synthesis.py tests/test_rag_v2_synthesis_provider.py -q` →
  **61 passed** (42 + 19), Python 3.11.14, Windows — khớp con số Muse đã chạy trên Linux.
  Chạy với `-p no:cacheprovider` + `PYTHONDONTWRITEBYTECODE=1` + `PYTHONPYCACHEPREFIX` trỏ
  về C nên không ghi gì lên D; `git status` sạch sau đó.
- Probe độc lập `scratch/e2_precheck.py` chạy trước và sau khi pull để chốt diff hành vi của
  `create_synthesis_provider()` (mục 4).

## 9. Phạm vi, file phụ trợ, commit

- Commit nhận vé: `0c993eb`; các mốc tiến độ: `5dad312`, `e394401`, `b00bd95`; báo cáo này là
  commit riêng sau đó. Đã pull Phase A `dd1e7a7` / `725c40f` / `58ec138` / `49a7045`.
- Script chạy (git-ignore, không commit): `scratch/e2_precheck.py`, `scratch/e2_smoke.py`,
  `scratch/e2_b5_netcheck.py`, `scratch/p1_4_snapshot.py`, `scratch/p1_4_snapshot_diff.py`.
- Kết quả trung gian trên C: `C:\AIOS_p1_4\out\e2\` — `ve_e2_report.json`, `ve_e2_raw.jsonl`,
  `ve_e2_answers.txt`, `ve_e2_worker_stderr.log`, `ve_e2_b5_netcheck.json`,
  `snap_before.json`, `snap_after.json`, `snap_diff.json`, `snap_before_netcheck.json`,
  `snap_after_netcheck.json`, `snap_diff_netcheck.json`.
- Bản copy index trên C giữ nguyên: `C:\AIOS_p1_4\tri_thuc\library.sqlite`.
- Đính chính: ba dòng `ghi_chu` mốc 2–4 trước đó ghi giờ tay bị lệch so với giờ máy; giờ thật
  theo commit là 00:14:38 (`5dad312`), 00:16:11 (`e394401`), 00:22:01 (`b00bd95`).

## 10. Đề xuất bước kế (không tự mở scope)

1. **B5**: mở rộng chấm điểm claim để ưu tiên đoạn chứa **mã trường khớp câu hỏi**
   (`HOUSE_METHOD`) kể cả khi phần còn lại là tiếng Nhật; hoặc khi câu hỏi nêu tên trường, chèn
   trực tiếp dòng định nghĩa của trường đó nếu pack có.
2. **B2**: xem lại trọng số cho mã định danh dạng tệp (`YY2-Z151.exe`) để không thoái lui.
3. Sau khi Muse vá, lượt kiểm tiếp chỉ cần chạy lại `scratch/e2_smoke.py` trên cùng bản copy C.
