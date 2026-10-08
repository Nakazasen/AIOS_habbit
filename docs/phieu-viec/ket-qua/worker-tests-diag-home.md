# Báo cáo vé `WORKER-TESTS-DIAG-HOME` — điều tra 3 ca test hạ tầng bộ đọc BGE đỏ ở cả hai môi trường

- Máy: h410asrock (Windows, Python 3.11.14), ngày 2026-10-09.
- Người làm: OMP (thợ phụ máy nhà), theo lệnh user.
- HEAD khi nhận vé: `8bcc77d` (sau verdict ĐẠT `AUDIT-ENV-FAILOVER-HOME`).
- Commit sửa test: `ef840aa`.
- Phạm vi: chẩn đoán + sửa test lạc hậu. **Không đổi mã chạy thật** (`src/` không bị đụng trong vé này).

## 1. Kết luận nhanh

| Ca | Test | Phân loại | Gốc rễ | Xử lý |
|---|---|---|---|---|
| 1 | `test_adapter_self_healing_reconciles_timeout_errors` | **Lỗi ở TEST** (lạc hậu) | `ce6212c` thêm short-circuit: nguồn `notebook` được đánh dấu ready tức thì, không đi vào sổ cái chuẩn bị → `enqueued` trả 0 đúng thiết kế mới | Đổi fixture sang scope `temporary` (đúng tầng sổ cái còn chuẩn bị) — ĐÃ SỬA |
| 2 | `test_client_enforces_bounded_deep_timeout` | **Lỗi ở TEST** (ngân sách phi thực tế) | Truy vấn lexical thật trên máy nhà mất 2,7–13,6s, budget 5s của test thấp hơn độ trễ thật | Budget hợp lệ 60s + thêm phép thử budget bất khả thi phải fail-closed — ĐÃ SỬA |
| 3 | `test_bge_subprocess_worker_crash_handling` | **Lỗi môi trường / dọn dẹp test** | Xóa `runtime\rag_v2_dev.sqlite` ngay sau khi kill worker → Windows còn giữ handle ~0,2s → `WinError 5` | Dọn thư mục tạm có retry — ĐÃ SỬA |

**Kết luận chung:** cả 3 ca là lỗi phía test/môi trường, **không có hồi quy chức năng** trong mã chạy thật của bộ đọc.

## 2. Ca 1 — `test_adapter_self_healing_reconciles_timeout_errors`

### Trước khi sửa
Rớt tại dòng 124: `E  assert 0 == 1` (file `tests/test_bge_worker_self_healing.py`: 1 failed / 4 passed).

### Đối chiếu mã nguồn
- Test được thêm trong `c338a87` (07/10, BGE-WORKER-FIX-HOME): đặt một dòng sổ cái `FAILED` với mã lỗi `preparation_init_bge_worker_persist_timeout` (mã "được phép thử lại"), rồi kỳ vọng `reconcile_and_enqueue_workspace_chat_sources(...) == 1` và dòng chuyển về `PENDING`, `last_error` rỗng.
- Commit làm lệch: `ce6212c` (08/10, APP-SOURCE-MODEL-PC0575 chặng 2b) thêm short-circuit trong hàm reconcile (`src/aios_habit/workspace_chat_rag_v2_adapter.py` khoảng dòng 2117–2124): mọi nguồn `source_scope == "notebook"` được ghi thẳng `READY` vào sổ đăng ký bộ nhớ và `continue`, không tính vào `enqueued`.
- Fixture của test dùng `source_scope="notebook"` → chạm short-circuit → `enqueued == 0`. Với thiết kế mới, **chỉ nguồn `temporary`** mới đi qua sổ cái chuẩn bị; nguồn notebook là tài liệu production đã lập chỉ mục sẵn.

### Kết luận & sửa
- Lệch nằm ở **test** (giả định cũ), không phải ở code: hành vi "notebook không vào hàng đợi chuẩn bị" là chủ đích của vé cấu hình kho nguồn và đã có test khác phủ gián tiếp (`tests/test_workspace_chat_rag_v2_adapter.py`).
- Sửa: đổi fixture sang `source_scope="temporary"` kèm chú thích — giữ nguyên ý nghĩa gốc của test (lỗi thuộc nhóm "được phép thử lại" thì KHÔNG được ghim `FAILED`; phải được xếp lại `PENDING` với `last_error` rỗng).
- Sau sửa: **PASS** (0,30s).

## 3. Ca 2 — `test_client_enforces_bounded_deep_timeout`

### Trước khi sửa
Rớt với chuỗi lỗi:
- `_send_request` … `raise SemanticBackendError(f"bge_worker_{phase}_timeout")` (`src/aios_habit/rag_v2/bge_subprocess_client.py:783`) → bị bọc lại tại nhánh `except Exception` (dòng 663–667) thành `SemanticBackendError: bge_subprocess_worker_crashed`, worker bị đóng (fail-closed).

### Số đo thật trên máy nhà (máy rảnh)
- `initialize_worker` 0,32s; `prepare_sources` 0,01s.
- 4 truy vấn lexical liên tiếp với budget 60s: **13,59s / 10,13s / 2,66s / 11,60s**.
- Lúc máy có tải nền: 10,34s / 15,10s / 3,35s.
- → Budget 5s của test nằm dưới độ trễ thật; việc test rớt là **đúng theo thực tế**, không phải lỗi chức năng.

### Kiểm hành vi "giới hạn kín" hiện tại (giữ nguyên, không sửa)
- Budget bất khả thi 0,001s: raise sau **1,50s**, lý do bọc `bge_subprocess_worker_crashed`, worker đóng (`is_alive() == False`) — đúng ngữ nghĩa fail-closed có chặn trần.

### Kết luận & sửa
- Lệch nằm ở **test** (kỳ vọng chạy được trong 5s). Sửa:
  1. Truy vấn hợp lệ với budget 60s (biên ~4,4x so với max đo được) + assert thời gian < 60s.
  2. Thêm phép thử thứ hai: budget bất khả thi (0,001s) phải raise trong < 30s và worker phải đóng — khóa chặt ngữ nghĩa "enforces bounded" của tên test.
- Sau sửa: **PASS** (12,22s).

## 4. Ca 3 — `test_bge_subprocess_worker_crash_handling`

### Trước khi sửa
`PermissionError: [WinError 5] Access is denied` khi `TemporaryDirectory` dọn `runtime\rag_v2_dev.sqlite` (lúc thoát context), sau khi test đã kill worker bằng `_process.kill()`.

### Điều tra
- Quét tiến trình (psutil) sau khi test xong: **không tiến trình nào còn giữ file** kể cả tiến trình test.
- Thử xóa lại sau đó: thành công ngay; vòng lặp đo 6/6 lần dọn được, khóa tối đa **~0,2s** (5/6 lần cần lần thử thứ hai).
- → Đây là **khóa tạm thời lúc hệ điều hành nhả handle** (nhánh kill đột ngột), không phải lỗi quyền thư mục tạm và không phải tiến trình còn sót.

### Kết luận & sửa
- Lỗi thuộc **dọn dẹp của test** (environment). Sửa: thay `tempfile.TemporaryDirectory` bằng `mkdtemp` + hàm `_remove_tree_with_retry` (tối đa 50 lần × 0,2s) chỉ trong đúng ca này.
- Tái lập sạch: chạy lại ca 3 nhiều lần đều xanh; mỗi lần thư mục được dọn xong (≤ 0,2s khóa đầu), không để lại rác.
- Sau sửa: **PASS** (0,84s).

## 5. Cổng xác minh

- `uv run --no-sync --group dev python -m compileall src tests`: sạch (exit 0, kiểm lại trong phiên chốt).
- `uv run --no-sync --group dev python -m aios_habit.cli audit`: `"status": "PASS"`, không lỗi, không cảnh báo.
- Import `aios_habit.workspace_chat_app`: OK.
- 3 tệp liên quan chạy lại liên tiếp **2 vòng**: vòng 1 **21/21 PASS** (106,05s), vòng 2 **21/21 PASS** (114,65s); phiên chốt chạy lại: 3 ca vé **3 passed** (15,58s) + 3 tệp **21 passed** (117,36s) — không còn ca đỏ, không chập chờn.
- Full `pytest -q` toàn repo (phiên chốt, 1305,71s ≈ 21,8 phút): **8 failed / 4195 passed / 46 skipped / 19 errors**.
  - Đối chiếu baseline tại `4068e02` (báo cáo TEST-PORTABLE: 11 failed / 4192 passed / 46 skipped / 19 errors): chênh lệch đúng **−3 failed / +3 passed = chính 3 ca vé đã sửa**; skipped và errors giữ nguyên.
  - 8 failed còn lại chạy riêng xác minh **8 failed y hệt** (30,45s), toàn ngoài phạm vi vé, trùng nhóm baseline: 2 ca cần mạng; 3 ca khẳng định chuỗi mã nguồn app (chuỗi đã bị gỡ bởi commit khác); 2 ca `rag_v2_opt_pyloops` (kỳ vọng ngược với bản sửa đã duyệt / phụ thuộc môi trường); 1 ca index production (`496 != 889` — index cục bộ trên máy này).
  - 19 errors giữ nguyên: thiếu dữ liệu theo đường dẫn máy khác `\home\hatch\...` (lỗi môi trường dữ liệu, không phải logic).

## 6. Phát hiện phụ & đề xuất (không tự sửa)

1. **Nhãn lỗi bị đè:** timeout truy vấn (`bge_worker_query_timeout`) bị đổi mã thành `bge_subprocess_worker_crashed` tại nhánh bọc chung (dòng 663–667). Hành vi fail-closed là chủ đích, nhưng mã lỗi làm mất thông tin chẩn đoán (timeout khác hẳn crash). Đề xuất vé riêng: giữ mã timeout riêng khi nguyên nhân gốc là timeout.
2. **Độ trễ truy vấn biến thiên rộng:** 2,7–13,6s (lexical, máy nhà). Mặc định ứng dụng `AIOS_BGE_QUERY_TIMEOUT` = 30s còn biên ~2,2x — tạm đủ; nếu biến động tăng, vận hành có thể nâng biến môi trường.
3. **Phủ test cho short-circuit notebook** (`ce6212c`): chưa có test khẳng định trực tiếp "nguồn notebook không vào hàng đợi chuẩn bị"; hiện chỉ được phủ gián tiếp. Đề xuất bổ sung khi mở vé chạm vùng này.

## 7. Rào cứng đã giữ

- Chỉ sửa 3 tệp test: `tests/test_bge_worker_self_healing.py`, `tests/test_bge_subprocess_client.py`, `tests/test_bge_subprocess_worker.py`. Không đổi mã chạy thật, không ghi chỉ mục, không chạy lại lượt đo 50 câu, không merge `main`.
- Không thêm/bớt mã lỗi sản phẩm; không đổi hành vi worker ở đường giao diện.
