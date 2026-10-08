# Báo cáo vé `BGE-ERROR-CODE-HOME` — giữ mã lỗi hết-giờ riêng + test trực tiếp đường tắt sổ

- Máy: h410asrock (Windows, Python 3.11.14 qua `uv`), ngày 2026-10-09.
- Người làm: OMP (thợ phụ máy nhà), theo lệnh user, tiếp nối vé `WORKER-TESTS-DIAG-HOME` (đã verdict ĐẠT).
- HEAD khi tiếp tục phiên này: `9d801c6` (= origin lúc 02:07).
- Commit sửa code + test (có sẵn từ trước phiên này): `b0a5fc5`.
- Phạm vi: chỉ sửa NHÃN lỗi tại nhánh bọc lỗi `query_ready` + test. Không đổi ngưỡng thời gian, không đổi hành vi đóng/mở worker, không nới cổng, không ghi index, không merge `main`.

## 1. Kết luận nhanh

- Mục chính ĐẠT: lỗi hết-giờ truy vấn (`bge_worker_*_timeout`) giữ nguyên mã khi ném lại; lỗi khác vẫn mã sập `bge_subprocess_worker_crashed`. Cả hai đường đều đóng worker (fail-closed) như cũ.
- Tương thích ĐẠT: không nơi nào trong `src/` rẽ nhánh theo mã sập; mã timeout mới còn giúp lớp adapter tự phục hồi đúng hơn (chi tiết §3).
- Test: 3 tệp hạ tầng 23/23 PASS, test liên quan timeout/persist 13/13 PASS, filtering 4/4 (trừ 1 ca dữ liệu kho máy ngoài vé).
- Cổng repo: `compileall` sạch, `cli audit` PASS, `import workspace_chat_app` OK.

## 2. Diff tóm tắt (commit `b0a5fc5`, `86c1481..b0a5fc5`)

- `src/aios_habit/rag_v2/bge_subprocess_client.py` (+11/-3, nhánh `query_ready` khoảng dòng 663–674): nếu `str(exc)` là `SemanticBackendError` dạng `bge_worker_*_timeout` thì giữ nguyên mã vào `_last_failure_reason` và ném lại mã đó; còn lại giữ nguyên hành vi cũ (mã sập + `LOGGER.warning` + `_close_internal(preserve_failure=True)` + ném lại). Dòng đóng worker nằm ngoài cả hai nhánh nên fail-closed giữ nguyên.
- `tests/test_bge_subprocess_client.py` (+3/-2): thắt chặt `test_client_enforces_bounded_deep_timeout` — phép thử budget bất khả thi giờ chỉ chấp nhận đúng `bge_worker_query_timeout` (trước đây chấp nhận `crash|timeout` vì mã bị đè).
- `tests/test_bge_subprocess_worker.py` (+69): 2 test mới giả lập `_send_request`: (a) `test_query_ready_preserves_timeout_code_and_stays_fail_closed` — timeout giữ mã + worker đóng; (b) `test_query_ready_still_maps_non_timeout_to_crash_code` — lỗi thường (`OSError`) vẫn mã sập + worker đóng.
- `tests/test_workspace_chat_production_index_filtering.py` (+50): 1 test chung `test_notebook_short_circuits_while_temporary_enqueues_together` — một lần reconcile với 2 nguồn: notebook → `READY` tức thì, temporary → `PENDING`, `enqueued == 1`.

## 3. Tương thích mã lỗi (rào cứng vé yêu cầu khai TRƯỚC khi sửa)

- Quét `src/` theo chuỗi `bge_subprocess_worker_crashed`: chỉ 2 điểm ném ra (nhánh `query_ready` vừa sửa + đường `ingest_and_query` cũ), KHÔNG có điểm nào đọc/rẽ nhánh theo mã sập (`if`/`in`/`==` với mã sập = 0 hit). File đọc mã lỗi duy nhất ở tầng trên là `workspace_chat_rag_v2_adapter.py` qua `_safe_reason()` + kiểm tra chuỗi con, không so mã sập trực tiếp.
- Hành vi `_safe_reason()` đo thật trong phiên này (`python -c`):
  - `SemanticBackendError("bge_worker_query_timeout")` → `"bge_worker_query_timeout"` (giữ nguyên vì có tiền tố `bge_worker_`).
  - `SemanticBackendError("bge_subprocess_worker_crashed")` → `"semanticbackenderror"` (rơi về tên lớp vì không thuộc tiền tố/mã cho phép).
- Hệ quả tương thích (giữ đúng thiết kế tự phục hồi BGE-WORKER-FIX-HOME): với mã timeout mới, điều kiện `if "timeout" in reason or ... "bge_worker" in reason` tại `retrieve_workspace_chat_evidence` (~dòng 3660) và đường chuẩn bị (~dòng 1600) sẽ ĐÚNG → adapter xóa cờ lỗi client để lượt hỏi sau thử lại được. Với mã sập cũ, reason gập thành `semanticbackenderror` → KHÔNG xóa cờ. Đây là hướng đúng (hết-giờ là lỗi tạm thời, được phép thử lại), không phá điểm đọc nào vì không ai rẽ nhánh theo mã sập.
- Đường persistent (`_query_ready_persistent`, dòng 938–983) KHÔNG bị đè mã từ trước (ném lại `SemanticBackendError` gốc / mã `bge_worker_persist_*`) nên vé này không cần đụng — đúng phạm vi "chỉ sửa đúng điểm bọc lỗi nêu trên".
- Đường `ingest_and_query` (dòng 734–739) vẫn giữ mã sập cho mọi lỗi — là đường cũ, test duy nhất gọi nó (`test_bge_subprocess_worker.py:60`) không assert mã lỗi, nên không ảnh hưởng.

## 4. Kết quả test

### 4.1 Trước sửa (kế thừa từ vé trước, không chạy lại vì code đã sửa từ `b0a5fc5`)

- Báo cáo `WORKER-TESTS-DIAG-HOME` §3-ca2 ghi nhận: budget bất khả thi ném `SemanticBackendError: bge_subprocess_worker_crashed` (mã timeout gốc `bge_worker_query_timeout` bị đè tại dòng 663–667). Test lúc đó phải `match="crash|timeout"` mới xanh.

### 4.2 Sau sửa (chạy thật phiên này 02:07–02:28)

- 2 test nhãn mới: `pytest tests/test_bge_subprocess_worker.py -q -k "preserves_timeout_code or non_timeout_to_crash"` → **2 passed** (2,31s).
- 3 tệp hạ tầng bộ đọc: `pytest tests/test_bge_subprocess_client.py tests/test_bge_subprocess_worker.py tests/test_bge_worker_self_healing.py -q` → **23 passed** (118,56s).
- Test client liên quan: `pytest tests/test_hodap_worker_timeout_fix.py tests/test_bge_worker_persist.py -q` → **13 passed** (17,20s).
- Filtering (vé mục phụ): `pytest tests/test_workspace_chat_production_index_filtering.py -q -k "not test_production_index_specs_retrieval"` → **4 passed** (1,49s). Chạy cả tệp: **1 failed / 4 passed** (85,61s) — ca rớt duy nhất `test_production_index_specs_retrieval` assert `496 == 889` do kho production trên máy chỉ còn 496 spec (dữ liệu máy, ngoài phạm vi vé; test này đọc DB thật `local_runs/.../library.sqlite`, không liên quan mã lỗi hay đường tắt sổ).

### 4.3 Nghiệm thu sử dụng thật (ghi rõ giới hạn)

- Vé này là vé nhãn lỗi + test đơn vị cho client hạ tầng; không có luồng giao diện người dùng mới để "mở sổ, hỏi đáp đầu-cuối" như vé UI. Phần dùng thật tương đương đã có trong `test_client_enforces_bounded_deep_timeout`: truy vấn lexical thật trên worker thật với budget 60s (PASS) + budget bất khả thi 0,001s fail-closed đúng mã timeout mới. Không ghi index thật (test dùng `tmp_path`), đúng rào cứng.

## 5. Cổng repo (chạy thật phiên này)

- `uv run --no-sync --group dev python -m compileall -q src tests` → exit 0.
- `uv run --no-sync --group dev python -m aios_habit.cli audit` → `{"status": "PASS", "errors": [], "warnings": []}`.
- `uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"` → `import-ok`.
- Rào cứng giữ: `git diff 86c1481..b0a5fc5 --stat` chỉ đụng 1 file `src/` đúng điểm vé + 3 file test; không đổi ngưỡng timeout, không merge `main`. File bẩn ngoài vé trong cây (`src/aios_habit/workspace_chat_ai_answer.py` + 8 JSON `ui-localonly-synth-open-home-*` untracked) là của thợ/lane khác — để nguyên, không commit cùng vé này.

## 6. Còn lại / rủi ro

- Không chạy full `pytest -q` trong vé này (tốn ~30+ phút, vé trước vừa chạy full 8 failed/4195 passed tại `3160a3d` làm baseline; vé này chỉ đụng 1 nhánh nhãn lỗi đã phủ kín bởi 23+13 test trên). Muse đối chiếu có thể chạy full nếu cần.
- Đề xuất ghi hồ sơ: cân nhắc mở rộng cùng cách giữ nhãn cho đường `ingest_and_query` cũ nếu đường đó còn được dùng trong tương lai — hiện để nguyên để giữ phạm vi vé.
