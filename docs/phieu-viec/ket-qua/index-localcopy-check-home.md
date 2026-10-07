# Báo cáo vé `INDEX-LOCALCOPY-CHECK-HOME` — kiểm tra bản sao chỉ mục thiếu mảnh trong `local_runs` ở máy nhà

- Vé: `INDEX-LOCALCOPY-CHECK-HOME` (máy nhà `h410asrock`).
- Nhánh: `phieu-viec/rag-fix1`, không merge `main`.
- Mức hoàn thành: **ĐẠT chờ duyệt** — kiểm tra chỉ-đọc + khuyến nghị, không tự sửa hay làm tươi ở vé này.
- Rào giữ: chỉ đọc bản sao local bằng `mode=ro&immutable=1`; không mở tệp production ở `C:\AIOS_workspace_chat_rag_v2_production\...`; không ghi hay xóa chỉ mục nào; không commit dữ liệu thật.

## 1. Số đếm bản sao local (đo trực tiếp, chỉ đọc)

- Tệp: `local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite`.
- Cỡ: 2.552.659.968 byte; sửa lần cuối 2026-09-28 05:55; tạo 2026-09-27 10:02 (giờ máy).
- Mở bằng `sqlite3` với `mode=ro&immutable=1` + `PRAGMA query_only=ON` (tránh khóa ghi; mở thường `mode=ro` treo vì khóa trên máy này).
- Kết quả:
  - Tổng mảnh `chunks`: **133.144**.
  - Tài liệu riêng biệt: **496**.
  - Mảnh truy xuất được `retrievable=1`: **107.331**.
  - `PRAGMA quick_check`: **ok**.
  - Phân loại theo `file_type`: xlsm 62.967, xlsx 60.580, pdf 6.862, txt 1.234, png 552, msg 366, `document_summary` 361, html 115, pptx 105, bmp 2.
- Đối chiếu production đã kiểm chứng (lấy từ báo cáo `index-prod-home.md`, không mở lại tệp production ở vé này): 889 tài liệu / 149.800 mảnh.
- Lệch: thiếu **16.656 mảnh** (149.800 − 133.144) và **393 tài liệu** (889 − 496). Nhóm thiếu hẳn: xls, csv; pdf chỉ còn 6.862 so với 15.586; tóm tắt chỉ 361 so với 385.

## 2. Nguồn gốc bản sao (dấu vết trong thư mục)

- Cỡ và mốc 2.552.659.968 byte + 28/09 trùng bản ghi trong `index-nguon-kiem-ke.md`, `scan-o-d.md` (mã ghim `062ec090…`), `move-index-c.md`: đây là **bản ghim cũ ngày 28/09**, không phải kho app đang chạy.
- Dấu vết cùng thư mục `local_runs/workspace_chat_rag_v2_production/`:
  - `.aios-library-writer.lock` ngày 12/09, `library.sqlite.bak-20260927-023546` (28.753.920 byte) ngày 13/09.
  - Nhật ký `bge_worker.stderr.log` các ngày 27/09 (3 nơi: gốc, `bge_m3_hybrid/`, `collections/tri_thuc/logs/`).
  - `materialized_sources/` có 79 tệp `wsc-*.txt`, phần lớn ngày 30/08–04/09, vài tệp 12–13/09.
- Kết luận nguồn gốc: bản sao được tạo khoảng 27–28/09 làm bản dev trong repo, rồi đóng băng từ đó; app thật đã chuyển sang đọc production ở `C:\AIOS_workspace_chat_rag_v2_production\...` (vé `INDEX-PROD-HOME` đã chứng minh 889/149.800, SHA từng byte).

## 3. Rà đường đọc: chỗ nào còn trỏ vào bản sao thiếu (quan trọng nhất)

- Kết luận chung: **app chạy thật an toàn** (đọc production ở ổ C), nhưng **bài kiểm tra và kịch bản mặc định còn trỏ vào bản thiếu** — ai đo hay chạy trên đó sẽ ra số sai.

| Nơi | Dòng | Điều kiện kích hoạt | Mức nguy hiểm |
|---|---|---|---|
| `tests/test_index_status.py:143` + khẳng định `:160-161` | `real_db = Path("local_runs/workspace_chat_rag_v2_production/.../library.sqlite")`, rồi `assert chunk_count == 149800`, `doc_count == 889` | Chạy bài `test_index_status_matches_real_db_if_present` trên máy nhà (tệp tồn tại nên không bỏ qua) | **Cao**: bài này đỏ chắc chắn vì tệp thật chỉ có 133.144/496; ai nhìn đỏ tưởng production hỏng |
| `scripts/workspace_chat_rag_v2_activation.py:54` | `DEFAULT_RUNTIME_ROOT = PROJECT_ROOT / "local_runs/workspace_chat_rag_v2_production"` | Chạy kịch bản kích hoạt mà không truyền `--runtime-root` | **Cao**: mặc định trỏ vào bản thiếu |
| `scripts/benchmark_adaptive_reranking.py:593` | `effective_runtime = str(runtime_root or (deployment.runtime_root if deployment else PROJECT_ROOT / "local_runs/workspace_chat_rag_v2_production"))` | Bỏ trống `runtime_root` và không có `deployment` | **Trung bình**: đo chuẩn rơi vào bản thiếu |
| `src/aios_habit/workspace_chat_rag_v2_adapter.py:247` + `:470` | `_DEFAULT_RUNTIME_ROOT = Path("local_runs/workspace_chat_rag_v2_canary")`, cho phép đổi qua biến môi trường `RUNTIME_ROOT_ENV` | Dùng cấu hình mặc định không qua triển khai | **Thấp**: mặc định là canary, không phải bản production thiếu; chỉ nguy hiểm nếu ai cố tình đặt biến môi trường trỏ sang bản thiếu |
| `src/aios_habit/rag_v2/pipeline.py:174` | `runtime_root: Path \| str = Path("local_runs/rag_v2_dev")` | Dùng đường ống mặc định khi thử nghiệm | **Thấp**: bản dev, không phải bản thiếu đang xét |
| `config/workspace_chat_rag_v2.local.json:15-16` + `:36` | `runtime.root = "C:\\AIOS_workspace_chat_rag_v2_production"` (đường hỏi đáp thật), `benchmark.runtime_root = ".../local_runs/workspace_chat_rag_v2_production"` (ghi rõ `evidence_only_not_workspace_chat_query_index`) | App mở trang hội thoại | **An toàn**: đường hỏi đáp thật đã trỏ production ở ổ C; bản `local_runs` chỉ là bằng chứng cũ, không dùng để hỏi đáp |
| `src/aios_habit/workspace_chat_app.py:2101,2124,2212,2428,2476,2518,2534` | `fallback_root = rag_config.runtime_root / rag_config.requested_profile` và đọc `storage_root` của bộ sưu tập | `storage_root` trống thì về `runtime_root` trong cấu hình | **An toàn khi cấu hình đúng**: vì `runtime_root` thật là ổ C nên đường dự phòng cũng về ổ C, không về `local_runs` |

## 4. Khuyến nghị chốt: chọn hướng (b), chưa làm ở vé này

- Đề xuất chọn **hướng (b): đánh dấu và loại bản sao thiếu khỏi mọi đường đọc mặc định**, chưa làm tươi vội. Lý do:
  - App thật không cần bản này (đang đọc production ở ổ C đầy đủ 889/149.800).
  - Làm tươi (hướng a) tốn sao chép ~2,9 GB, phải dừng app/worker, rủi ro ghi nhầm production; lợi ích chưa rõ vì chưa có ai cần đọc bản `local_runs` này.
  - Sửa hướng (b) nhẹ và an toàn: đổi mặc định trong 2 kịch bản trên sang bắt buộc truyền đường dẫn hoặc trỏ production ở ổ C; sửa bài `test_index_status.py` để bỏ qua bản 133.144/496 (hoặc đổi kỳ vọng đúng + ghi rõ đây là bản cũ); thêm cảnh báo khi mở tệp có đúng 133.144 mảnh/496 tài liệu rằng đây là bản cũ 28/09.
- Nếu sau này cần hướng (a) làm tươi: sao lưu bản cũ, sao chép ngoại tuyến từ `C:\AIOS_workspace_chat_rag_v2_production\...\library.sqlite` khi không có app/worker nào chạy, rồi kiểm `quick_check=ok` + đếm 889/149.800 + so SHA trước khi thay. Vé này **không tự thực hiện** theo rào, chờ điều phối duyệt.

## 5. Cổng kho (vé không sửa `src/`/`tests/`)

- `compileall src tests`: sạch.
- `cli audit`: `PASS`.
- `import aios_habit.workspace_chat_app`: thành công.
- Không chạy toàn bộ `pytest` vì vé chỉ đọc (tiền lệ vé đo `INDEX-PROD-HOME`); riêng bài `test_index_status_matches_real_db_if_present` được kết luận đỏ bằng đối chiếu số (133.144/496 so với kỳ vọng 149.800/889), không cần chạy để tránh treo khóa như mục 1.
- Rào giữ: chỉ đọc bản sao local, không đụng production, không ghi chỉ mục, không merge `main`, không bí mật.
