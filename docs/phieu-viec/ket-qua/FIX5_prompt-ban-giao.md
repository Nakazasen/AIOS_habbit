# Prompt bàn giao — FIX 5 (dán vào model mới)

Dán nguyên khối dưới đây cho model tiếp theo.

---

Trong repo `D:\Sandbox\AIOS_habbit`, trên branch `phieu-viec/rag-fix1`.

Việc FIX 5 **đã code xong nhưng CHƯA commit, CHƯA push**. Toàn bộ thay đổi đang nằm trong working tree. Nhiệm vụ của bạn là kiểm tra lại, rồi commit riêng và push. **Không viết lại code, không đổi thiết kế, không đụng `main`.**

## Đọc trước

1. `docs/phieu-viec/ket-qua/FIX5_ban-giao.md` — bàn giao đầy đủ: đã làm gì, số liệu, việc còn lại, lệnh chính xác, bẫy đã gặp.
2. `docs/phieu-viec/ket-qua/FIX5_bao-cao.md` — báo cáo FIX 5.
3. `docs/phieu-viec/ket-qua/FIX3_dieu-tra-summary.md` — nguyên nhân gốc.

## Bối cảnh một dòng

Summary chunk thiếu `source_fingerprint` và `privacy_labels`, nên query production lọc sạch chúng và overview abstain với `no_document_summaries`. FIX 5 vá việc đó sau một flag **mặc định tắt**.

## Thay đổi trong working tree

- `src/aios_habit/rag_v2/summary_provenance.py` (mới): cờ `AIOS_RAG_V2_SUMMARY_PROVENANCE`, `with_body_provenance`, `plan_summary_provenance` (dry-run), `apply_summary_provenance` (raise `summary_provenance_disabled` khi cờ tắt).
- `src/aios_habit/rag_v2/chunking.py`: `_summary_gate_open` thay `len(usable_elements) >= 3`; khi bật cờ thì chép provenance từ chunk thân.
- `scripts/backfill_summary_provenance.py` (mới): CLI `INDEX [--apply] [--json]`, mặc định dry-run.
- `tests/test_rag_v2_chunking.py`, `tests/test_rag_v2_summary_provenance.py` (mới), `tests/test_rag_v2_summary_first.py`: test cho cờ, cổng mới, backfill, và một test tích hợp ingest.
- `CHANGELOG.md`: mục “Optional document-summary provenance”.
- `docs/phieu-viec/ket-qua/FIX5_bao-cao.md`, `FIX5_ban-giao.md`.

## Ràng buộc cứng

- Flag `AIOS_RAG_V2_SUMMARY_PROVENANCE` **mặc định tắt**; tắt flag phải giữ hành vi cũ y hệt.
- Không đổi schema (không thêm cột). Không đụng `detect_retrieval_mode`, `BGE_BACKEND`, `AIOS_RAG_V2_SUMMARY_FIRST`, đường hybrid full.
- Không viết tay summary cho bất kỳ file nào.
- Backfill: không bịa giá trị, không ghi đè trường đã có, không đụng `text`; ca mơ hồ (nhiều fingerprint hoặc nhiều bộ nhãn trong chunk thân) thì bỏ qua và log.
- Đề xuất (4) trong `FIX3_dieu-tra-summary.md` (hybrid lexical+embedding cho tìm summary) **để phase 2**, không làm trong FIX 5.
- **KHÔNG** chạy `--apply` trên index thật. Việc đó chờ người dùng duyệt riêng.

## Việc phải làm

1. `git status --short` và `git diff` — xác nhận đúng các file trên, không có file lạ.
2. Chạy lại test hẹp:
   `"D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe" -m pytest -q tests/test_rag_v2_chunking.py tests/test_rag_v2_summary_provenance.py tests/test_rag_v2_summary_first.py`
3. Chạy `"D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe" scripts/check_docs.py` → phải in `DOCUMENTATION_CONTRACT=PASS`.
4. Chạy dry-run trên index thật (chỉ đọc):
   `"D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe" scripts/backfill_summary_provenance.py local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite --json`
   Kỳ vọng: `summary_count 10`, `update_count 20`, `skipped_ambiguous 0`, `skipped_no_body_value 0`.
5. Commit **riêng**, đúng các path này (đừng `git add -A`):
   ```
   git add CHANGELOG.md src/aios_habit/rag_v2/chunking.py src/aios_habit/rag_v2/summary_provenance.py scripts/backfill_summary_provenance.py tests/test_rag_v2_chunking.py tests/test_rag_v2_summary_provenance.py tests/test_rag_v2_summary_first.py docs/phieu-viec/ket-qua/FIX5_bao-cao.md docs/phieu-viec/ket-qua/FIX5_ban-giao.md
   git commit -m "fix(rag-v2): give new document summaries real provenance"
   git push origin HEAD
   ```
6. Báo lại link commit và dừng.

## Cấm

- Không đụng `main`, không push `main`.
- Không commit `docs/phieu-viec/ket-qua/MOM_INGEST_KHAO_SAT.md` (file cũ, không thuộc FIX 5).
- Không `--apply` backfill trên index thật.
- Không sửa code cho tới khi bạn thực sự tìm ra lỗi; nếu có, báo trước thay vì tự ý đổi thiết kế.

## Bẫy

- Shell Windows: luôn dùng đường dẫn tuyệt đối tới venv: `"D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe"`.
- `apply_summary_provenance` cố tình raise khi cờ tắt; test phải `setenv` cờ.
- 4 lỗi pytest cũ (uv lock, pin checksum model, streamlit, OCR thứ tự) không liên quan FIX 5 — đừng cố sửa.
