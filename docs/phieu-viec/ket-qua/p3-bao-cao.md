# P3 — Báo cáo chẩn đoán app Streamlit báo "0/171 tài liệu sẵn sàng"

- Ngày: 2026-09-29 (giờ máy công ty, +07)
- Máy: `KDTVN-PC0575` (CPU-only)
- Repo: `D:\Sandbox\AIOS_habbit`, nhánh `phieu-viec/rag-fix1`, commit gốc `7a7163f`
- Ràng buộc vé: chỉ đọc — **không ghi byte nào lên index production, không chạy embed, không merge `main`**. Đã tuân thủ.
- Kết quả: **tìm ra nguyên nhân gốc; không sửa gì trong vé này** (đúng ràng buộc). Đề xuất vé tiếp theo ở mục 7.

## 0. Kết luận ngắn

App đọc **đúng** file index production đã verify ở P2; index còn nguyên (SHA-256 khớp 100%).
Nhưng tiến trình con chuẩn bị tài liệu (BGE worker) **không khởi động được** vì thiếu biến môi trường
ONNX (`AIOS_BGE_ONNX_MODEL_PATH` / `AIOS_BGE_ONNX_MODEL_CHECKSUM`) và thư mục mặc định
`models\bge-m3-onnx-fp32` không tồn tại. Vì cổng "fail-closed", app coi **tất cả** tài liệu là chưa sẵn sàng
→ hiện "0/171" và đếm nhóm lỗi thành "tài liệu cần xử lý" (68 lúc chụp màn hình, 171 khi lượt chạy kết thúc).

Đây là **lỗi cấu hình môi trường**, không phải lỗi dữ liệu index và không phải app đọc sai DB.

## 1. App đang chạy là app nào, đọc DB nào (câu hỏi 1)

- Tiến trình: `python.exe` PID 23196 (cổng 8501), dòng lệnh:
  `"...\.venv\Scripts\streamlit.exe" run src\aios_habit\workspace_chat_app.py --browser.gatherUsageStats false --server.fileWatcherType none --server.runOnSave false`
  → đúng app Workspace Chat của repo, khởi chạy 2026-09-29 16:40:46 bằng `scripts/run_workspace_chat.ps1`.
- Cấu hình app: `config/workspace_chat_rag_v2.local.json` → `runtime.root = D:/Sandbox/AIOS_habbit/local_runs/workspace_chat_rag_v2_production`,
  `requested_profile = bge_m3_hybrid`, `runtime.index_filename = library.sqlite`.
- Đường dẫn index app dùng (theo `collection_runtime_layout`, xem `workspace_chat_rag_v2_adapter.py:923`):
  `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`.
- Ledger trạng thái chuẩn bị tài liệu của app: `local_runs/workspace_chat_rag_v2_production/workspace_chat.sqlite`,
  bảng `source_preparation_ledger` (xem `_get_ledger_db_path`, `workspace_chat_rag_v2_adapter.py:1435`).

⇒ **App không đọc sai DB.** Cả index lẫn ledger đều nằm trong thư mục production đã verify.

## 2. So với index production đã verify ở P2 (câu hỏi 2)

| Mục | Giá trị |
|---|---|
| Đường dẫn | `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite` |
| Kích thước | `2552659968` byte (khớp P2) |
| mtime | `2026-09-29 11:20:54` — **không đổi** so với lúc deploy |
| SHA-256 (tính lại trong vé này, 38,6 giây) | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` |
| SHA-256 P2 đã verify | `062EC090644FB4EC09D2FB6388F3175E988E48D63061B04E6C27BBED334EF8CA` |

⇒ **Khớp tuyệt đối.** Index production nguyên vẹn; app và worker **không ghi byte nào** lên index.

## 3. Vì sao readiness = 0/171 (câu hỏi 3)

### 3.1 Chuỗi nhân quả

1. App xếp lịch chuẩn bị cho từng nguồn trong phiên làm việc. Mỗi nguồn cần **BGE worker** (tiến trình con ONNX).
2. Worker khởi động thất bại. Log nguyên văn `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/logs/bge_worker.stderr.log`:

```
Traceback (most recent call last):
  File "D:\Sandbox\AIOS_habbit\src\aios_habit\rag_v2\bge_subprocess_worker.py", line 252, in main
    model_path = require_onnx_model_dir(backend_name=backend_name)
  File "D:\Sandbox\AIOS_habbit\src\aios_habit\rag_v2\bge_onnx_backend.py", line 161, in require_onnx_model_dir
    raise SemanticBackendUnavailable(
aios_habit.rag_v2.semantic.SemanticBackendUnavailable: default ONNX fp32 model is unavailable:
model directory is missing: D:\Sandbox\AIOS_habbit\models\bge-m3-onnx-fp32.
Set BGE_BACKEND=pytorch to use the PyTorch path explicitly.
```

3. Nguyên nhân của dòng lỗi: `resolve_onnx_model_path()` (`bge_onnx_backend.py:74-82`) lấy
   `AIOS_BGE_ONNX_MODEL_PATH`; biến này **không được đặt** (kiểm tra cả scope `User` và `Machine`: đều trống),
   nên rơi về mặc định `<repo>/models/bge-m3-onnx-fp32` — thư mục **không tồn tại**.
   Model ONNX thật nằm ở `local_runs\retrieval_models\bge-m3-5617a9f\onnx\`
   (`model.onnx` + `model.onnx_data` + `sparse_linear.npy`… do P2-B7b đặt vào lúc 15:40 hôm nay).
   `scripts/run_workspace_chat.ps1` cũng không đặt các biến ONNX này.
4. Mọi lượt chuẩn bị đều hỏng ở bước khởi tạo worker ⇒ ledger ghi `failed` với mã lỗi rút gọn
   `preparation_init_bge_worker_model_verify_failed`.
5. Cổng backend-aware (`_expected_backend_fingerprint`, `workspace_chat_rag_v2_adapter.py:97`) **fail-closed**:
   không xác định được định danh backend ⇒ trả `""` ⇒ **mọi nguồn đều không thể ở trạng thái `ready`**,
   kể cả nguồn đã có vector trong index.

### 3.2 Bằng chứng đo trực tiếp (chỉ đọc)

Ledger `workspace_chat.sqlite` (truy vấn read-only):

| Chỉ tiêu | Giá trị |
|---|---|
| Số dòng | `171` |
| Trạng thái | `failed` = **171/171** |
| `attempt_count` | 1 mỗi dòng (tổng 171) |
| `last_error` | `preparation_init_bge_worker_model_verify_failed` (171/171) |
| `source_scope` | `temporary` (171) |
| `priority` | `normal` (171) |
| `model_fingerprint` | `''` (rỗng — cổng không tính được) |
| `model_revision` | `5617a9f61b028005a4858fdac845db406aefb181` |
| Thời gian tạo → cập nhật cuối | `16:45:25` → `16:48:07` (hôm nay) |

Thí nghiệm cô lập (không ghi gì, chỉ gọi hàm tính định danh):

| Kịch bản | `_expected_backend_fingerprint` |
|---|---|
| A. Môi trường như app đang chạy (không có biến ONNX) | `''` (rỗng → fail-closed) |
| B. Có `AIOS_BGE_ONNX_MODEL_PATH` trỏ đúng thư mục onnx | `''` — vì còn thiếu checksum (`AIOS_BGE_ONNX_MODEL_CHECKSUM` hoặc tệp phụ trợ `onnx.sha256`, cả hai đều chưa có) |
| C. Có cả path + checksum (`sha256:728c9eb7…`, checksum cây model hiện tại) | `8274fbb05ec3ad6895bfc7a4a8cdd835d28317acf66b34e49f816ba5cab9bc3f` |

⇒ Đủ cả path **và** checksum thì cổng mới hoạt động. Hiện thiếu cả hai ⇒ 0/171 là hệ quả tất yếu, không phải
"status tracking sai" đơn thuần.

## 4. "68 tài liệu cần xử lý" — thật hay ảo? (câu hỏi 4)

- "68" là **ảnh chụp giữa lượt chạy**: lượt chuẩn bị bắt đầu `16:45:25`, chạy tuần tự từng tài liệu (batch = 1).
  Lúc chụp màn hình (~16:46) đã hỏng 68 tài liệu; đến `16:48:07` thì hỏng hết **171**. Cùng một đợt lỗi, không phải hai nhóm khác nhau.
- Con số này **không liên quan** 25.813 chunk `retrievable=0` đã biết ở P2 (những chunk đó không retrieve được nên không tính là "cần xử lý").
- 171 nguồn `temporary` **thật sự chưa có vector** trong index production. `_document_id` sinh khóa theo **nội dung văn bản**
  (`wsc-<sha256(text)[:24]>`, `workspace_chat_rag_v2_adapter.py:737`) nên khóa không phụ thuộc máy/đường dẫn.
  Truy vấn read-only trên index: **0/171** mã tài liệu có chunk nào (`retrievable=1` = 0).
- Thống kê index (đối chiếu): 496 tài liệu, 133.144 chunk, 107.331 chunk `retrievable=1`;
  định danh dense ONNX `016c5255…` = 107.331, dense PyTorch cũ `ce7fb53f…` = 340 (dead weight như P2 đã kết luận).

## 5. Đã sửa gì

**Không sửa gì** — đúng ràng buộc "chỉ đọc, cấm ghi index, cấm embed" của vé:

- Không đặt biến môi trường máy (không đổi cấu hình bền vững ngoài phạm vi vé).
- **Không restart app**: sửa env rồi restart sẽ khiến app chuẩn bị lại tài liệu ⇒ ghi vector vào index production,
  vi phạm ràng buộc vé. Việc này thuộc vé tiếp theo, phải có dry-run/backup/theo dõi như quy ước.
- Không chụp màn hình "sau" vì không có thay đổi nào được áp dụng.
- Không mở UI trong vé này để tránh kích hoạt thêm một lượt chuẩn bị (dù fail-closed); bằng chứng lấy trực tiếp từ log worker + ledger.

Screenshot của user **là chụp trên chính máy KDTVN-PC0575** (localhost:8501, và ledger trong thư mục production của máy này
có đúng 171 dòng tạo lúc 16:45–16:48 cùng ngày). Không rơi vào trường hợp "screenshot máy nhà" nên vé không phải dừng.

## 6. Phát hiện phụ — rủi ro lớn cần Muse quyết trước khi sửa env

Đây chính là câu hỏi còn treo trong báo cáo P2-B7b (`p2_b7b_smoke_2026-09-29.md`, mục "Điểm cần Muse quyết"):

- Vector ONNX trong index production mang định danh `016c5255…`.
- Trên máy này, nếu đặt env ONNX "cho chạy được", định danh kỳ vọng là `8274fbb0…` — **khác** `016c5255…`.
- Vì cổng so khớp định danh theo từng vector, chỉnh env kiểu "có là được" sẽ khiến app coi **toàn bộ 107.331 vector cũ là cũ/hết hạn**
  ⇒ đánh dấu lại là `pending` ⇒ **embed lại hàng loạt và ghi vào index production** — đúng thứ vé này cấm và cũng là rủi ro vận hành lớn.
- Định danh được băm từ: `artifact_checksum` (checksum cây ONNX), `runtime_version` (phiên bản `onnxruntime` đang cài — máy này `1.28.0`),
  cùng model_id/revision/dimension/device. Sau P2-B7b, cây ONNX có thêm `sparse_linear.npy` nên checksum cây đổi thành `728c9eb7…`,
  trong khi hằng số trong mã/manifest vẫn là `b1d887e0…` (`src/aios_habit/bge_m3_manifest.json`, `packaging/models/bge_m3_manifest.json`).
- Thử dò tổ hợp {checksum manifest `b1d887e0…`, checksum cây hiện tại `728c9eb7…`, rỗng} × {onnxruntime `1.28.0`, `1.29.0`}:
  **không tổ hợp nào tái tạo được `016c5255…`** ⇒ môi trường đã sinh vector gốc (máy nhà, thời FIX2/FIX3) chưa được xác định đầy đủ.
  Cần chốt "bộ hằng số deploy" trước khi bật env, nếu không sẽ kích hoạt embed lại toàn bộ.

## 7. Đề xuất cho vé tiếp theo (chờ Muse duyệt, chưa làm)

1. **Chốt bộ định danh deploy** (ưu tiên): xác định cặp (checksum ONNX, phiên bản onnxruntime) khớp `016c5255…`,
   hoặc quyết định chấp nhận embed lại có kiểm soát (dry-run + backup + báo cáo số chunk sẽ đổi).
2. **Cấp env cho app** (sau khi chốt mục 1) — chọn 1 trong 2 cách:
   - `[Environment]::SetEnvironmentVariable("AIOS_BGE_ONNX_MODEL_PATH", "<...>\bge-m3-5617a9f\onnx", "User")`
     và đặt checksum qua `AIOS_BGE_ONNX_MODEL_CHECKSUM`; hoặc
   - tạo tệp phụ trợ `local_runs\retrieval_models\bge-m3-5617a9f\onnx.sha256` (nội dung `sha256:<checksum>`) — cách này khớp sẵn cơ chế sidecar của mã.
   - (tuỳ chọn) junction `models\bge-m3-onnx-fp32` → thư mục onnx để đường dẫn mặc định cũng đúng.
3. **Xác minh lại readiness** bằng UI sau khi restart, kèm ảnh chụp "trước/sau" và SHA-256 index trước/sau để chứng minh không ghi ngoài ý muốn.
4. Việc **embed 171 tài liệu `temporary`** (nếu Muse muốn chúng sẵn sàng) là ticket riêng, có dry-run/backup theo quy ước.

## 8. Phụ lục — lệnh/số liệu đã dùng

- `sha256sum local_runs/.../collections/tri_thuc/library.sqlite` → `062ec090…ef8ca` (38,6 giây).
- Ledger: `sqlite3` chế độ `mode=ro` trên `workspace_chat.sqlite` → bảng `source_preparation_ledger` (mục 3.2).
- Index (read-only): đếm theo `document_id`, `model_fingerprint`, `retrievable` (mục 4).
- Fingerprint: gọi `SemanticModelDescriptor.fingerprint` với các tổ hợp đầu vào (mục 3.2 bảng B/C, mục 6).
- Env: `[Environment]::GetEnvironmentVariable(..., 'User'/'Machine')` → `AIOS_BGE_ONNX_MODEL_PATH`, `AIOS_BGE_ONNX_MODEL_CHECKSUM`, `BGE_BACKEND` đều trống.
