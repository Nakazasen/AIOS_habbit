# Bàn giao FIX 5 — provenance cho document_summary

Trạng thái: **code + test + báo cáo đã xong, CHƯA commit, CHƯA push.**
Nhánh: `phieu-viec/rag-fix1`, HEAD đang là `e40a3ee` (đã push, không phải FIX 5).
Không đụng `main`. Không đụng `BGE_BACKEND`, `AIOS_RAG_V2_SUMMARY_FIRST`, `detect_retrieval_mode`.

## 1. Việc đã làm

Flag `AIOS_RAG_V2_SUMMARY_PROVENANCE`, **mặc định tắt**. Tắt flag = hành vi cũ y hệt.

| File | Thay đổi |
| --- | --- |
| `src/aios_habit/rag_v2/summary_provenance.py` (mới) | `SUMMARY_PROVENANCE_FLAG`, `summary_provenance_enabled()`, `with_body_provenance()`, `plan_summary_provenance()` (dry-run), `apply_summary_provenance()` (từ chối ghi nếu cờ tắt) |
| `src/aios_habit/rag_v2/chunking.py` | `chunk_elements` gọi `self._summary_gate_open(...)` thay `len(usable_elements) >= 3`; khi bật cờ thì `with_body_provenance(summary_chunk, chunks)` chép fingerprint + privacy từ chunk thân |
| `scripts/backfill_summary_provenance.py` (mới) | CLI `INDEX [--apply] [--json]`, mặc định dry-run |
| `tests/test_rag_v2_chunking.py` | +4 test (cờ tắt giữ null; cờ bật chép provenance; cổng 1/2 phần tử; text không đổi) |
| `tests/test_rag_v2_summary_provenance.py` (mới) | 7 test backfill: mặc định tắt, dry-run không ghi, apply từ chối khi cờ tắt, chỉ điền trường thiếu, mơ hồ bị bỏ qua, không có body thì giữ rỗng |
| `tests/test_rag_v2_summary_first.py` | +1 test tích hợp: ingest 1 file một đoạn + 1 file nhiều đoạn, query overview với `allowed_privacy_labels` + fingerprint kỳ vọng phải trả summary |
| `CHANGELOG.md` | mục “Optional document-summary provenance” |
| `docs/phieu-viec/ket-qua/FIX5_bao-cao.md` (mới) | báo cáo đầy đủ, đã gồm số pytest |

Quy tắc ca mơ hồ: chunk thân cùng `document_id` có **hơn một** fingerprint, hoặc **hơn một** bộ nhãn privacy → bỏ qua, ghi `multiple_body_fingerprints` / `multiple_body_privacy_sets`. Không bịa, không ghi đè trường đã có, không đụng `text`.

## 2. Số liệu đã đo

**Dry-run trên index thật** (chỉ đọc, chưa `--apply`):
`local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite`
→ `summary_count 10`, `update_count 20`, `skipped_ambiguous 0`, `skipped_no_body_value 0`.

**End-to-end trên bản copy** (temp dir, không đụng index thật):
→ `applied_rows_changed 20`, `production_untouched True` (so `st_mtime_ns`).
→ A1–A5: `summary_only`, **không còn abstain**, có dòng `Ghi chú: trả lời ở mức tổng quan.`, không có XML `xmlns`.
→ Held-out H1, H2: `summary_only`, có ghi chú. H3 (“Khi có lỗi xảy ra thì xử lý theo trình tự nào?”): `focused` + `hybrid`, vẫn trả lời.
→ A3 và A5 chỉ có khung `PRECHECKS/STEPS/POSTCHECKS` trống + ghi chú: giới hạn của summary tiền tố 1500 ký tự, không phải lỗi provenance.

**`pytest -q tests`**: 3137 passed, 3 skipped, 4 failed trong 548.92s. 4 lỗi cũ, không liên quan:
`uv lock --check`, pin checksum model cục bộ, pip thiếu `streamlit>=1.60.0`, test OCR phụ thuộc thứ tự.
`scripts/check_docs.py` → `DOCUMENTATION_CONTRACT=PASS`.

## 3. Việc CÒN LẠI (đúng thứ tự)

1. Chạy lại test hẹp cho chắc, rồi **commit riêng** và **push** `phieu-viec/rag-fix1`.
2. **Chưa** `--apply` backfill trên index thật. Việc này chờ người dùng duyệt riêng.
3. Không commit `docs/phieu-viec/ket-qua/MOM_INGEST_KHAO_SAT.md` (file cũ, không thuộc FIX 5).
4. `scratch/fix5_e2e.py` và `scratch/fix5_e2e.json` nằm ngoài git (scratch/ bị ignore); xoá sau khi dùng nếu muốn.

## 4. Lệnh chính xác

Shell Windows. **Luôn dùng đường dẫn tuyệt đối tới venv python**, `.venv/Scripts/python.exe` tương đối sẽ lỗi command not found.

```
"D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe" -m pytest -q tests/test_rag_v2_chunking.py tests/test_rag_v2_summary_provenance.py tests/test_rag_v2_summary_first.py
"D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe" scripts/check_docs.py
"D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe" scripts/backfill_summary_provenance.py local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/collections/tri_thuc/library.sqlite --json
"D:/Sandbox/AIOS_habbit/.venv/Scripts/python.exe" scratch/fix5_e2e.py
```

Commit (đúng các path này, đừng `git add -A`):

```
git add CHANGELOG.md src/aios_habit/rag_v2/chunking.py src/aios_habit/rag_v2/summary_provenance.py scripts/backfill_summary_provenance.py tests/test_rag_v2_chunking.py tests/test_rag_v2_summary_provenance.py tests/test_rag_v2_summary_first.py docs/phieu-viec/ket-qua/FIX5_bao-cao.md
git commit -m "fix(rag-v2): give new document summaries real provenance"
git push origin HEAD
```

## 5. Bẫy đã gặp (đừng lặp lại)

- Công cụ `read` với selector dòng trên đường dẫn Windows hay báo ENOENT. Dùng shell đọc file bằng python nếu cần.
- Chèn hàm vào giữa class rất dễ làm hỏng indent; kiểm tra `ast.parse` sau mỗi lần sửa `chunking.py`.
- `apply_summary_provenance` **cố tình** raise `RuntimeError("summary_provenance_disabled")` khi cờ tắt. Test nào gọi nó phải `setenv` cờ.
- Câu hỏi H3 không vào overview vì classifier thấy chữ “trình tự”. Đó là hành vi mong đợi của FIX 3, không phải lỗi FIX 5.
- Đề xuất (4) trong `FIX3_dieu-tra-summary.md` (hybrid lexical+embedding cho tìm summary) để **phase 2**, không làm trong FIX 5.
