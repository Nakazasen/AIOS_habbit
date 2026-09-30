# Vé GPU-DC — Báo cáo tiến độ (nhúng GPU 344 tài liệu "Điều chỉnh" + đóng gói delta cho PC0575)

- Trạng thái: `xong-cho-duyet`; đã nhúng, xác minh và đóng gói **329 tài liệu / 12.720 mảnh** (10.238 mảnh retrievable có vector). Gói delta chưa nhập vào production.
- Máy thực hiện: máy nhà `h410asrock` (Windows), 2026-10-01 ~02:10–03:3x +07.
- Nguồn vé: `docs/phieu-viec/mailbox/prompt.md` (GPU-DC).

## 0. Nhận vé + cổng gate

- Điều kiện mở đã thoả trước khi nhận: GPU-262b `xong-cho-duyet` + verdict ĐẠT; don-canary xong (ổ C trống để bung ZIP).
- ZIP nguồn đúng chỗ trên ổ D: `D:\Sandbox\AIOS_habbit\Tài liệu của tất cả dòng máy\Điều chỉnh-20260905T053942Z-1-001.zip` — **858.190.286 byte, SHA-256 `f18bbae2c0c472fe063cd80543802e8677512012a8aa4606d8c3d09ca8ca18b7` — khớp ghim**.
- Vì điều kiện mở đã đạt, nhánh dự phòng "4 lần watcher → `cho-muse`" không dùng đến.

## 1. Bước 1–2 — lọc danh sách file + bung giải nén (chỉ đọc ổ D)

- ZIP có **2.147 member / 936.853.642 byte** (khớp cây `aios-v14-data` cũ).
- Quy tắc lọc đúng vé: extension (không phân biệt hoa/thường) ∈ {`.xlsx`, `.xls`, `.pdf`, `.msg`, `.png`, `.bmp`, `.html`, `.csv`} VÀ tên khác `Loi KDTPS.xlsx`.
- Kết quả: **344 file / 650.894.980 byte (~621 MiB) — khớp kỳ vọng của Muse**: 231 `.xlsx`, 88 `.pdf`, 8 `.msg`, 6 `.csv`, 5 `.xls`, 3 `.png`, 2 `.bmp`, 1 `.html`. `Loi KDTPS.xlsx` bị loại đúng 1 chỗ (`Điều chỉnh/Lịch sử lỗi/Loi KDTPS.xlsx`).
- Bung **chỉ 344 member cần thiết** ra `C:\tmp\gpu-dc\extract` (tiết kiệm chỗ): **344/344 file, 0 lỗi, đủ 650.894.980 byte**. Chỉ đọc ổ D; không ghi ổ D.

## 2. Bước 3 — pipeline trích text + chunk "đúng của app" (như `export_262`)

### 2.1 Chuỗi xử lý (đúng code app, không trích tay)

1. **Text (content_text)**: dùng đúng chuỗi trích xuất mà app dùng khi nạp file — `workspace_chat_source_ingest` → `workspace_chat_excel.extract_xlsx_text` (cho `.xlsx/.xls`, qua `excel_extractors` với `xlrd`), `workspace_chat_legacy_extractors.extract_outlook_msg` (`.msg`), `document_extractors.extract_text_chunks_from_file` (`.pdf/.html/.png/.bmp`), `.csv` đọc text UTF-8 (nhánh `.txt` của app).
2. **`document_id`**: đúng công thức adapter `workspace_chat_rag_v2_adapter._document_id` — `wsc-` + `sha256(text.strip())[:24]`; fingerprint đúng `_source_fingerprint`; nhãn `local_only`.
3. **Chunk**: ghi `content_text` ra `.txt` (như `_materialize_sources`) → `ConverterRegistry.convert_document` → `StructureAwareChunker` (cấu hình runtime `max_chunk_chars=1200` → child ≤ 1.000 ký tự, parent 6.000 ký tự) — đúng chuỗi mà worker nhúng thật.

### 2.2 Quyết định về giới hạn (ghi rõ để audit)

- **Giữ nguyên cap bên trong extractor của app** (Excel: 12 sheet/1.000 hàng/20.000 ô/200 KiB text + thông điệp "một phần nội dung"; PDF: 12.000 ký tự/trang, OCR tối đa 3 trang PDF).
- **Bỏ qua 3 guard của tầng upload chat** (10 MB/file, cap tổng 200 KiB, luật "CSV không thuộc kho chữ") vì: (a) vé liệt kê cả file >10 MB và CSV là đáng nhúng; (b) production PC0575 thật đang chứa tài liệu tới 65 MB text và 25 tài liệu ≥204.800 byte, 0 dấu vết marker cắt "bị cắt bớt" — chứng tỏ thư viện không áp cap tầng chat. Bằng chứng đo trực tiếp trên `C:\AIOS_p1_4\tri_thuc\library.sqlite` (chỉ đọc).
- **Workbook 40 MB** `Màn hình trắng Iris.xlsx` vượt guard 10 MB của chính extractor Excel → dùng nhánh dự phòng bằng engine registry (`ExcelDocumentConverterAdapter` + `excel_extractors`, đều là code app): 259 ô/3 vùng, text 16.083 byte → 22 mảnh.
- **OCR không có sẵn trên máy** (rapidocr/paddleocr/tesseract đều không) → 5 file ảnh và trang PDF scan không có text-layer sẽ bị loại (đúng hành vi app: "Chưa đọc được nội dung ảnh").

### 2.3 Kết quả export

| Chỉ số | Giá trị |
|---|---|
| `document_id` nhúng được | **329** (9 file loại + 6 đường dẫn trùng nội dung) |
| Tổng chunk | **12.720** — child 10.077 / parent (context) 2.482 / summary 161 |
| Chunk rỗng | **0** |
| Tổng text | 7.237.017 byte |
| `export_dc.jsonl` | **16.048.605 byte**, SHA-256 `1d300c3a68430b3488df40ba47165d3aedfe47992571869cea672c08b8020526` |
| Sidecar roles | `export_dc_roles.json`, SHA-256 `c9aa8d7fabd75bd6fa15c7ee75175b8031017ffa84e3cc0794c38d0f97e6a6b3` |
| Tài liệu lớn nhất | `2xd_smkdj_jpnサービスアニュアル.pdf` (158 MB): 999 trang, ~1,52 M ký tự, 3.942 mảnh |

- **Loại 9 file** (ghi rõ trong stats): 3× `panelss.png` + `TEK00001.BMP` + `TEK00002.BMP` (thiếu OCR); `N00137687_実行.pdf` (PDF scan 10,5 MB, 28 trang không có text, OCR thiếu); 2× file khoá `~$【Iris2020】...xlsx` (165 B, Excel báo hỏng/mật khẩu); `信号　7303.xlsx` (workbook không có ô dữ liệu đọc được).
- **6 đường dẫn trùng nội dung** (giữ 1 `document_id`): `dvu_prt_engpage_info_log.csv` ×2, `dvu_prt_vdbg_docpg.csv` ×2, `APC_302XD47250-01.pdf`, `【Iris2020】全体配線図_上位_DMT.xlsx`.
- **Verify độc lập** (script riêng, chạy lại chuỗi trích→chunk trên 6 tài liệu mẫu đại diện 6 loại): khớp **từng mảnh một** với JSONL; phân bố độ dài khớp tuyệt đối cờ roles (10.077 mảnh ≤1.000 ký tự = toàn bộ child; 2.482 parent + 161 summary nằm trong khoảng lớn hơn; 0 mảnh >6.000).
- File JSONL chỉ nằm cục bộ + trên Drive (không commit vào git).

## 3. Bước 4 — upload JSONL lên Drive (để Muse audit độc lập)

- Đích: thư mục **AIOS_Data** (đúng thư mục vé trước).
- Link: `https://drive.google.com/file/d/1cBqrWn0E8VlnlOZ9rzItLgoS62GbwwTa/view?usp=sharing`
- Quyền: **Bất kỳ ai có đường liên kết = Người xem** (như tiền lệ vé `onnx-upload-drive`).
- **Xác minh đầu-cuối ẩn danh** (không cookie): tải qua `https://drive.usercontent.google.com/download?id=1cBqrWn0E8VlnlOZ9rzItLgoS62GbwwTa&export=download&confirm=t` → nhận đủ **16.048.605 byte**, SHA-256 **trùng khớp** `1d300c3a…0526`; bản tải kiểm chứng đã xoá sau khi băm.
- Cách làm: điều khiển Chrome đang đăng nhập sẵn bằng UI automation (relay extension của omp không kết nối được nên dùng chuột/bàn phím + UIA; chi tiết giới hạn/tác động phụ ở mục 10).

## 4. Bước 5 — staging mới `C:\AIOS_staging_dc\library.sqlite`

- Dựng từ JSONL + sidecar roles bằng `LocalChunkIndex` + `StructureAwareChunker(1200)`, mỗi dòng = 1 mảnh (đúng cơ chế vé 262b).
- Kết quả: **12.720 mảnh / 329 tài liệu / 10.238 retrievable** (parent giữ `retrievable=0` — đúng ngữ nghĩa app và production thật: production có 25.813 mảnh `retrievable=0`); FTS 10.238 (FTS chỉ index mảnh retrievable, giống production).
- `integrity_check=ok`, foreign key 0 lỗi, **schema khớp tuyệt đối** với production copy `C:\AIOS_p1_4\tri_thuc\library.sqlite` (so signature `sqlite_master`).
- Kích thước: **143.638.528 byte trước nhúng** (228.937.728 byte sau khi nhúng — bằng đúng bản delta). Backup trước nhúng: `library.sqlite.bak-20261001-gpu-dc-preembed`, SHA-256 `1a2a9aace7dd9969fb4b442003223dbcdf07795b0ec5486cb5d69991a74af4d1`.
- Không ghi production, không ghi staging GPU-262/262b, không ghi ổ D.

## 5. Bước 6 — nhúng GPU

- Kiểm tra khô: ONNX Runtime + metadata gói đều `1.28.0`; cây mô hình khớp ghim `sha256:9f81075f…b11093`; revision `5617a9f61b028005a4858fdac845db406aefb181`; fingerprint `016c5255d0cec1fcb75b99f71f3c6a47a6e67b6087c3eb943b039cf8ac6274fb`; `pending=10238`, `already_onnx=0`; phiên `CUDAExecutionProvider` đứng đầu, CPU dự phòng. Cache kiểm tra cây mô hình đặt trên C (`C:\tmp\gpu-dc\model-verify-cache-20261001.json`).
- Nhúng: **10.238/10.238 mảnh** qua 2 lượt liên tiếp (lượt 1 bị công cụ chạy nền cắt ở 300 s nhưng đã ghi từng mẻ; lượt 2 tự tính lại phần còn thiếu và chạy tiếp — 7.538 mảnh trong 903,1 s = **8,35 mảnh/giây**). Tổng thời gian GPU ~20 phút.
  - Chỉ 10.238 mảnh `retrievable=1` được nhúng vector — đúng ngữ nghĩa app/production: 2.482 mảnh parent là "context view" giữ kèm trong delta để bảo toàn ngữ cảnh nhưng production thật cũng không có vector cho mảnh `retrievable=0` (kiểm chứng: bản production copy có 25.813 mảnh `retrievable=0` không vector).

## 6. Bước 7 — xác minh (chỉ đọc)

- Map đủ **12.720/12.720 dòng JSONL ↔ mảnh staging** (đối chiếu `chunk_id`, đường dẫn logic, `source_name`, text, checksum, cờ retrievable — khớp từng dòng).
- Dense + sparse: **10.238/10.238** đủ cả hai bảng, đúng fingerprint `016c5255…` và revision `5617a9f…`; `dense_invalid=0`, `sparse_invalid=0`, orphan=0; FTS 10.238; `integrity_check=ok`.
- **Spot-check cosine GPU/CPU: 240 mẫu** (3 mảnh retrievable/tài liệu, phủ đều 329 tài liệu) — **min = max = 1.000000** (ngưỡng 0,999).

## 7. Bước 8 — đóng gói delta cho PC0575

| Tệp (trên ổ C) | Dung lượng | SHA-256 |
|---|---|---|
| `C:\AIOS_staging_dc\gpu-dc-delta-20261001.sqlite` | 228.937.728 | `a0ca1345b62a5d95867bb62f5790a40b3bd5f46704002323731c68822ad1cec3` |
| `C:\AIOS_staging_dc\gpu-dc-manifest-20261001.json` | — | (kèm trong zip) |
| `C:\AIOS_staging_dc\gpu-dc-delta-20261001.zip` | **74.065.213** | **`31afe1e3bf7767379cce30588670db61f21a919ec5484b173c94961d97b063e3`** |

- ZIP gồm đúng 2 member (`gpu-dc-delta-20261001.sqlite` + `gpu-dc-manifest-20261001.json`), CRC đạt, manifest trong ZIP khớp bản ngoài.
- Manifest ghi: 329 tài liệu / 12.720 mảnh / 10.238 retrievable; từng tài liệu bao nhiêu mảnh, bao nhiêu retrievable; **`skip_existing_document_ids = []`** (đối chiếu với bản production copy `C:\AIOS_p1_4\tri_thuc\library.sqlite`: **không id nào trùng**) → **merge_id = toàn bộ 329**; chính sách merge "bỏ qua id đã tồn tại, không ghi đè, mảnh parent chèn kèm giữ ngữ cảnh".
- Manifest cũng lưu link Drive của JSONL, hash sidecar roles, hash bản backup pre-embed, danh sách 9 file loại + 6 đường dẫn trùng để Muse audit.
- Delta/zip nằm trên ổ C, chờ chuyển sang PC0575 (LAN/USB) ở vé merge — như tiền lệ 262b.

## 8. Cổng kiểm tra kho mã

- Python `3.11.14`; `compileall src tests` đạt; `scripts/check_docs.py` trả `DOCUMENTATION_CONTRACT=PASS`; CLI audit trả `status=PASS` (via `PYTHONPATH=src`); import `aios_habit.workspace_chat_app` đạt.
- `pytest -q` (kèm `xlrd` cho nhóm test legacy, `-p no:cacheprovider`, ~5 phút): **3.376 đạt, 3 bỏ qua, 27 thất bại, 14 lỗi** (tổng 3.420 bài) — không có bài nào liên quan thay đổi của vé (vé không sửa code).
  - 14 lỗi: 10 lỗi `test_error_cases_f4.py` + 4 lỗi `test_chat_action_error_lookup.py` đều do thiếu 2 tệp Excel cục bộ theo đường dẫn `/home/hatch/workspace/aios_data/dieu_tra_loi/...` (fixture của máy VM, không có trên máy nhà) — **đúng nhóm 14 lỗi đã ghi trong báo cáo 262b**.
  - 27 thất bại thuộc các nhóm có sẵn: 8 bài worker BGE subprocess không init được trong môi trường test (`bge_worker_init_stdout_eof`), nhóm cần mạng (cloud/LLM provider bị chặn: `getaddrinfo failed`/connection refused), nhóm cần gói tùy chọn `torch`/`FlagEmbedding`, 1 bài checksum manifest `src-quality-process`, và vài assertion quyền riêng tư/ánh xạ lựa chọn chủ sở hữu — không bài nào thuộc phần code/đường ống mà vé này đụng tới (vé chỉ đọc dữ liệu, không đổi mã nguồn).

## 9. Đã KHÔNG làm (đúng lệnh cấm)

- Không ghi/đụng production hay bản copy `C:\AIOS_p1_4` (chỉ mở `mode=ro` để đối chiếu id/schema).
- Không đụng staging GPU-262 (`C:\AIOS_staging_262`) và 262b (`C:\AIOS_staging_262b`).
- Không ghi ổ D (dữ liệu/công việc đều trên C; repo D chỉ đọc + commit/push git như quy ước mailbox).
- Không nhúng lại `Loi KDTPS.xlsx` (đã có trong `error_cases`).
- Không merge `main`.

## 10. Tác động phụ khi điều khiển Chrome để upload (đã/đang khôi phục)

- Relay extension của omp chưa kết nối được trên Chrome 154 (bị chặn cài); buộc dùng UI automation chuột/bàn phím + UIA:
  - Đã tạm ẩn một cửa sổ tiến trình phụ và **đẩy cửa sổ "omp" ra ngoài màn hình** trong lúc thao tác — **đã khôi phục** về đúng vị trí `(25,25)`.
  - Windows **Narrator** được bật/tắt trong một thí nghiệm accessibility — **đã tắt hẳn** (không còn process, dialog đã đóng).
  - Tab Chrome cuối cùng: `[Chat — Muse, Điều chỉnh-…zip, AIOS_Data, Điều chỉnh-…zip, AIOS_Data]`. Tab AIOS_Data gốc bị đổi qua `/drive/projects` trong lúc dò tọa độ **đã được đưa lại đúng folder AIOS_Data**; một tab từng mở folder khác (nay hiển thị danh sách AIOS_Data) chưa khôi phục được URL gốc vì địa chỉ đó chưa từng được ghi lại trước thao tác. Tab "Chat — Muse" giữ nguyên nội dung; không mở/đóng thêm tab nào.
  - File kiểm chứng tải ẩn danh đã xoá; không để lại file rác mới trên Desktop.
- Giới hạn đã gặp: cửa sổ hộp thoại "Open" là DirectUI custom nên UIA không thấy ô tên file/nút Open — xử lý bằng bàn phím (Alt+N, clipboard, Enter), tránh IME tiếng Việt làm hỏng chuỗi gõ tay.
