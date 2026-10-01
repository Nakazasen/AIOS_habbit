# Báo cáo vé MOVE-INDEX-C — chuyển kho production app sang ổ C (vé tiền đề cho merge-home)

Ngày: 2026-10-01 (giờ `+07`), máy nhà `h410asrock`, nhánh `phieu-viec/rag-fix1`.
Vé: `docs/phieu-viec/mailbox/prompt.md` (Muse phát hành ~07:24 sau khi xử lý cờ `cho-muse` của vé merge-home).
Không đụng `main`, không force-push, không merge delta, không xóa bản D.

## 1. Kết luận

**ĐẠT 5 tiêu chí của vé**, với hai điểm phải nói rõ để Muse biết khi review:

1. **Kho C đã tăng thêm dữ liệu sau khi chuyển** (không phải lỗi vé): app sau khi restart tự chạy cơ chế
   "chuẩn bị nguồn" sẵn có (người dùng mở sổ/hội thoại) và **tự nhúng thêm tài liệu vào kho C** — đúng
   fingerprint `016c5255…`. Vì vậy SHA kho C **không còn bằng ghim** tại thời điểm đọc báo cáo này; SHA
   khớp ghim là số đo **lúc chuyển kho** (băm lại ngay sau khi move, trước khi app chạy). Bản D giữ
   nguyên ghim làm mốc đối chiếu/rollback.
2. **Automation UI không gửi được câu hỏi** (Chrome headless qua bridge: widget Streamlit không nhận
   thao tác chuột/phím — đã thử click JS, click chuột thật theo toạ độ, dán clipboard, Ctrl+Enter).
   Theo đúng cho phép của vé, kiểm chứng đọc dùng **mức smoke tương đương P1**: chạy chính đường truy
   vấn của app (adapter + worker BGE + pipeline `index_read_only=True`) trên kho C — **ĐẠT**: trả lời
   `grounded=true` với 5 trích dẫn và 10 dòng bằng chứng từ tài liệu Matecon trong kho C (mục 5.1).

## 2. Pha 0 — xác minh chỉ đọc (không ghi gì)

| Phép kiểm | Kết quả |
| --- | --- |
| SHA-256 bản C `C:\AIOS_p1_4\tri_thuc\library.sqlite` | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` |
| SHA-256 bản D `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | trùng bản C (byte-đối-byte), 2.552.659.968 byte |
| `PRAGMA integrity_check` / `quick_check` bản C (`mode=ro`) | `ok` / `ok` (623.208 trang × 4.096 B) |
| Dung lượng trống ổ C | 9.504.657.408 B (~8,85 GiB) — đủ backup merge-home (~2,6 GB) + tăng trưởng (~0,3 GB) |
| Key trỏ D | `config/workspace_chat_rag_v2.local.json` → `runtime.root` = `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production` |

Chuỗi resolve (đọc từ mã, không đoán): `runtime.root / requested_profile` → `collection_runtime_layout("tri_thuc", …)`
→ `<profile>/collections/tri_thuc/library.sqlite`. Collection `tri_thuc` trong `local_cases/workspace_chat/collections.jsonl`
có `storage_root=""` nên đi theo layout profile; đường D cũ ghi lại để rollback:
`D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production`.

## 3. Pha 1 — chuyển kho sang C (không ghi/xóa gì trên D)

1. Dừng app cũ theo đúng cây tiến trình (`cmd` PID 14908 → `streamlit` 15284 → `python` 15420 → app 3440)
   trước khi đổi cấu hình để không có ghi nào lên D giữa chừng.
2. Dựng layout app trên C: `C:\AIOS_workspace_chat_rag_v2_production\{bge_m3_hybrid\collections\tri_thuc, materialized_sources}`.
3. **Chuyển (move, không copy lại)** bản index C đã xác minh vào đúng chỗ resolve:
   `C:\AIOS_p1_4\tri_thuc\library.sqlite` → `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
   (rename trong cùng ổ C, mtime giữ nguyên `28/09 22:47`; băm lại tại chỗ mới = `062ec090…4ef8ca`, 2.552.659.968 B).
   Đường P1.4 cũ không còn file — bản D vẫn là bản gốc/fallback.
4. Copy kèm từ D sang C (chỉ đọc D, không sửa D): `materialized_sources/` (75 file, 1.051.381 B),
   ledger `workspace_chat.sqlite` (81.920 B), `bge_m3_hybrid\workspace_chat.sqlite` (7.176.192 B),
   `rag_v2_dev.sqlite` (86.016 B) — giữ nguyên trạng thái app như trước khi chuyển.
5. Sửa manifest (file máy, không nằm trong Git):
   - File: `config/workspace_chat_rag_v2.local.json`
   - Key: `runtime.root`
   - Cũ: `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production`
   - Mới: `C:\AIOS_workspace_chat_rag_v2_production`
   - Không đổi key nào khác (khối `benchmark`/`evidence` là bản ghi lịch sử của lần định chuẩn trên D;
     file báo cáo benchmark trên D vốn đã không còn nên nhánh kiểm chi tiết của loader đã bỏ qua từ trước).
   - Backup manifest trước khi sửa: `config/workspace_chat_rag_v2.local.json.bak-20261001-move-index-c`.
6. Validate bằng chính code app (`load_workspace_chat_rag_v2_deployment(require_activated=True)`):
   `activation_state=activated`, `benchmark_status=PASS`, `runtime_root=C:\AIOS_workspace_chat_rag_v2_production`,
   model path D tồn tại, `collection_runtime_layout("tri_thuc", …)` → đường C (file tồn tại 2.552.659.968 B).
7. Restart app bằng đúng trình khởi chạy của máy (`RUN_AIOS_WORKSPACE_CHAT.bat`), `http://localhost:8501/_stcore/health` = `ok`.

## 4. Kiểm chứng app đang dùng kho C

Bằng chứng sống từ app đang chạy (không phải suy luận từ config):

- App ghi file khoá/định danh người ghi **trong layout C**: `.aios-library-writer.lock`, `.aios-library-writer.info`,
  `…\collections\tri_thuc\logs\bge_worker.stderr.log` (log worker: `bge_worker_stage backend=onnx init_ms=96044.313`).
- App cập nhật ledger **C** (`C:\AIOS_workspace_chat_rag_v2_production\workspace_chat.sqlite`) và
  **tự nhúng thêm tài liệu vào kho C**: index 2.552.659.968 B → 2.569.261.056 B (07:56), +3 tài liệu / +116 chunk
  (dense+sparse), fingerprint `016c5255…` đúng backend ONNX fp32 — đây là cơ chế chuẩn bị nguồn sẵn có
  (UI báo "Đã chuẩn bị xong 68/109 tài liệu"), chạy nền sau khi app khởi động lại.
- Bản D vẫn nguyên: băm lại `062ec090…4ef8ca`; không có thao tác ghi nào của vé lên D (xem mục 6).
- Trạng thái kho C sau khi app chạy lại lần hai (08:06, app PID 15920, health `ok`): `PRAGMA quick_check` = `ok`,
  134.027 chunk / 108.429 vector dense, kích thước 2.571.603.968 B — app vẫn đang tự chuẩn bị nguồn ở chế độ nền
  (đúng cơ chế sẵn có; kho là nguồn thay đổi).

## 5. Smoke đọc kho C (mức tương đương P1)

Đường chạy: `WorkspaceChatRagV2CanaryConfig.from_env()` → `runtime_root = C:\AIOS_workspace_chat_rag_v2_production`;
nguồn: 109 tài liệu notebook của hội thoại `CONV-47535415` (đúng nguồn app dùng); lọc nguồn READY theo ledger;
pipeline `bge_m3_hybrid`, `index_read_only=True`, `ensure_embeddings_on_open=False`; worker BGE subprocess
(đúng cơ chế app dùng); câu hỏi Matecon ACR/CTU (câu từng được app trả lời đúng trong sổ này).

Kết quả: **xem mục 5.1** (điền bằng số đo thật của lượt chạy cuối).

### 5.1 Kết quả lượt chạy

Lệnh: `PYTHONPATH=<repo>/src AIOS_BGE_QUERY_TIMEOUT=300 uv run --no-sync python -B scratch/move_index_c_smoke.py`
(script chạy trong `scratch/`, git-ignore, không commit). Thời gian lượt: 88,7 giây.

| Số đo | Kết quả |
| --- | --- |
| `config.runtime_root` (từ manifest activated) | `C:\AIOS_workspace_chat_rag_v2_production` |
| Đường index resolve + tồn tại | `…\bge_m3_hybrid\collections\tri_thuc\library.sqlite` — có, `read_only=True` |
| Nguồn (nguồn thật của hội thoại) | 109 tài liệu, 109 có nội dung; **71 READY**, 71 đưa vào truy vấn |
| Truy vấn | `candidate_count=149`, `returned_count=15`, `filtered_as_stale_count=0`, `indexed_chunk_count=108.089`, `degraded=false`, `fallback_applied=false` |
| Câu trả lời | `grounded=true`, `mode=answer_with_limits`, 5 mã trích dẫn `[1] [5] [6] [10] [2]` |
| Bằng chứng | 10 dòng trỏ về `マテコン操作手順書_v001_生産技術_TV.pdf` / `.xlsx` (đúng tài liệu Matecon trong sổ) |
| Nội dung khớp kỳ vọng | Có cặp `YY2-Z151.exe` / `YY2-Z152.exe` (ACR/CTU) — đúng dữ kiện đối chiếu P1.4 |
| Thời gian trả lời | 88,2 s (CPU) — vượt ngân sách mặc định 30 s của worker, vì vậy lượt smoke đặt `AIOS_BGE_QUERY_TIMEOUT=300`; app thật gặp cùng ngân sách này sẽ báo "làm nóng rồi thử lại" (đúng thông báo người dùng đã thấy trong hội thoại) |

Ghi chú: lượt đầu (không tăng ngân sách) worker khởi tạo xong nhưng truy vấn vượt 30 s nên client báo
`bge_subprocess_worker_crashed` — đây là ngân sách thời gian, không phải lỗi kho; xác nhận bằng log worker
`bge_worker_stage backend=onnx init_ms=27671.438` và lần chạy lại thành công với cùng kho.

## 6. Bất biến của vé

| Điều kiện | Kết quả |
| --- | --- |
| Không ghi/xóa trên ổ D | Vùng kho/runtime `D:\…\local_runs\workspace_chat_rag_v2_production` **không đổi một mtime nào** (index `28/09 05:55`, ledger `30/09 04:19`, collection `27/09 11:20`, …); bản D băm lại sau vé: `062ec090…4ef8ca`. Ngoại lệ đã định trước của vé (nằm trong repo trên D): sửa `config/workspace_chat_rag_v2.local.json` + bản `.bak-20261001-move-index-c` (đúng bước 1.2 của vé) và các commit Git của vé. |
| Không xóa bản D | Bản D còn nguyên (2.552.659.968 B, mtime `28/09 05:55`). |
| Không merge delta | Không chạy merge, không đụng 2 gói delta. |
| Không đụng `main`, không force-push | Chỉ commit trên `phieu-viec/rag-fix1` (linear). |

## 7. Đường rollback

1. Sửa `config/workspace_chat_rag_v2.local.json` → `runtime.root` về
   `D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_production` (hoặc khôi phục
   `config/workspace_chat_rag_v2.local.json.bak-20261001-move-index-c`).
2. Restart app bằng `RUN_AIOS_WORKSPACE_CHAT.bat`.
3. Bản D nguyên vẹn (`062ec090…4ef8ca`) nên chỉ cần trỏ lại là chạy như cũ. Đổi ngược lại về C cũng chỉ cần
   sửa 1 key.

## 8. Ghi chú cho vé sau (merge-home)

- Kho app hiện tại: `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite`
  (đã tăng nhẹ so với ghim do app tự nhúng thêm tài liệu; đo lại trước khi backup/merge — kho là nguồn thay đổi,
  không dùng ghim `062ec090…` để so).
- App đang chạy nền cơ chế chuẩn bị nguồn (có thể còn ghi kho trong lúc merge). Nên **dừng app trước khi
  backup/merge** rồi restart sau, đúng như Pha 2 của vé merge-home.
- Bản D (`…\local_runs\workspace_chat_rag_v2_production\…\library.sqlite`) vẫn là bản ghim cũ, không dùng làm
  đích merge.

## 9. Phạm vi và commit

- Commit nhận vé: `9863cc2`; mốc Pha 0: `87747b0`; mốc Pha 1: `0f9eb5d`; mốc kiểm chứng app: `0c748aa`;
  báo cáo này là commit riêng sau đó.
- Script smoke (git-ignore, không commit): `scratch/move_index_c_smoke.py`.
- Ghi chú nhỏ: log worker dùng chung đường dẫn `…\collections\tri_thuc\logs\bge_worker.stderr.log` — lượt smoke
  có spawn worker riêng nên log bị ghi đè; dòng log gốc của app (`init_ms=96044.313`) đã ghi lại trong mục 4.
