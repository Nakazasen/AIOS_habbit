# Báo cáo vé `don-canary` — dọn kho canary 2,4 GB + rác tmp trên ổ C

- Máy thực hiện: máy nhà `h410asrock` (Windows), 2026-10-01 01:45–02:00 +07.
- Vé: `docs/phieu-viec/mailbox/prompt.md` (xếp hàng #1 theo `trang-thai.md`; chạy trước GPU-DC để có chỗ bung ZIP 858 MB + staging).
- Kết quả: **ĐẠT** — verify production trước, xóa canary sau, dọn rác an toàn; tổng thu hồi **13.985.363.736 byte (~13,0 GiB)**.

## 1. Bước 0 — dọn rác (`C:\tmp`, `C:\temp`, `C:\c`, `C:\nonexistent`)

Hiện trạng đo lúc nhận vé: ổ C chỉ còn **414.445.568 byte** trống (vé ghi ~2,4 GB — nay còn thấp hơn).

### Đã xóa (mục / byte / bằng chứng an toàn)

| Mục | Byte | Bằng chứng trước khi xóa |
|---|---|---|
| `C:\tmp\omp-ve-v1` | 2.709.061.554 | Clone worker nhánh `phieu-viec/rag-fix1`: `git status` sạch, 0 commit chưa push, 0 stash, 0 file ignored/untracked; wheel LFS `torch-2.5.1-cp311-…manylinux1_x86_64.whl` (906.474.467 B) còn bản thật tại `D:\Sandbox\AIOS_habbit\vendor\wheels_linux\`; `AI c\u1ea3nh b\u00e1o l\u1ed7i LSU.pptx` (5.841.550 B) có bản trong Git + trên D: |
| `C:\tmp\omp-ve-v1-clean` | 2.709.198.403 | Như trên |
| `C:\tmp\gpu-262` | 2.800.419.290 | Clone worker GPU-262 + `text_export.jsonl` (81.531.448 B, SHA `95aecf07…` — nguồn gốc trên Drive, bản lọc 19 tài liệu và delta vẫn nguyên ở `C:\tmp\gpu-262b` + `C:\AIOS_staging_262b` — KHÔNG đụng) + script tạm; dữ liệu cục bộ `local_cases`/`local_runs` (~2 MB) đã archive trước khi xóa |
| `C:\tmp\aios-data-v14` | 936.853.642 | Bản giải nén trùng: đối chiếu với `aios-v14-data` — 2.147 tệp / tổng byte bằng nhau / diff danh sách tệp = rỗng |
| `C:\tmp\aios-data-v14.zip` | 858.190.286 | SHA-256 `f18bbae2c0c472fe063cd80543802e8677512012a8aa4606d8c3d09ca8ca18b7` trùng khít ZIP nguồn trên D: (nguồn của vé GPU-DC) |
| `C:\tmp\pytest-of-Vinh` | 91.882.794 | Thư mục tạm pytest (2 phiên pytest-12/22), toàn fixture test |
| `C:\tmp\e3-ab` | 9.461 | 2 file `lastfailed-*.json` scratch |
| 29 × `C:\tmp\aios_ckpt_*` + 18 × `C:\tmp\aios_worktree_*` | 57.564 | Scratch harness (tệp 22–276 B); quét `*library*/*backup*/*production*/*.sqlite*` = 0 hit thật |
| `C:\temp\bge-m3-onnx-fp32.zip` | 1.326.939.447 | Gói model: cây gốc `D:\Sandbox\AIOS_habbit\models\bge-m3-onnx-fp32` (9 tệp, 2.289.625.694 B, ghim `9f81075f…`) còn nguyên; zip đã upload Drive + verify ẩn danh (báo cáo `onnx-upload-drive.md`); tạo lại được bằng `tar` từ ổ D |

**Tổng bước 0: 11.432.612.441 byte.**

### Giữ lại (kèm lý do)

- `C:\tmp\aios-v14-data` (936.853.642 B) — bản duy nhất còn của gói Điều chỉnh đã giải nén; vé `LSU-1` bước 1 tham chiếu trực tiếp (`kiểm tra C:/tmp/aios-v14-data`) và là `AIOS_DATA_DIR` của môi trường full-suite chuẩn (các vé tool2–5). Bản trùng `aios-data-v14` đã xóa.
- `C:\tmp\buoc0-deploy` (~49 MB DB + script/log) — vé `B0-MEASURE` cần "DB thật (vé buoc0-deploy)".
- `C:\tmp\gpu-262b` (9 MB) — script + `model-verify-cache` của flow vừa xong; vé GPU-DC dùng lại khuôn.
- `C:\tmp\e3-py311` — `xlrd 2.0.2` dùng trong lệnh test chuẩn (`PYTHONPATH=src;C:/tmp/e3-py311`).
- `C:\tmp\uv-cache` (11 MB) — cache uv, nhỏ.
- `C:\tmp\sessions` (23 thư mục rỗng), `C:\tmp\presenton` (rỗng), `C:\tmp\tmpo358_h5i` (rỗng) — 0 byte, giữ.
- `C:\tmp\iii-0.11.2-windows-amd64` + zip (39 MB) — chưa rõ công cụ → theo luật "không chắc thì bỏ qua".
- `C:\tmp\deep-dev-*` (6 thư mục) — chứa `*.backup` cấu hình `.gemini` (probe cài đặt 27/08) → bỏ qua theo luật.
- `C:\temp\ui` + script/ảnh nhỏ (~5 MB) — bằng chứng vé onnx-upload (báo cáo trỏ tới).
- `C:\c\AIOS_ve03_worktree_local_cases_archive_20260929.zip` (21.141 B) — archive dữ liệu cục bộ vé 0.3 (báo cáo don-o-c ghi "có thể xóa khi không cần đối chiếu nữa" — giữ để đối chiếu).
- `C:\nonexistent\path.db` (81.920 B), file lẻ cũ trong `C:\tmp` (~2 MB) — giữ, không đáng kể / chưa rõ.

### An toàn dữ liệu

- Quét `*library*` / `*backup*` / `*production*` / `*.sqlite*` trên toàn bộ mục bị xóa: các hit đều là tên tài liệu markdown, test fixture / tên module (`production.py` 22 B, `production_prediction.sqlite` 36 KB…), **không có `library.sqlite` hay dữ liệu production thật**.
- Archive mới tạo trước khi xóa nhóm clone GPU-262: `C:\c\gpu-262-worker-local-data-archive-20261001.zip` (22.838 B, 23 mục `local_cases` + `local_runs`).
- Mọi mục bị xóa đều nằm trong 4 thư mục vé cho phép; không đụng `C:\AIOS_p1_4`, `C:\AIOS_backup_production_2026-09-28\`, `C:\AIOS_staging_262`, `C:\AIOS_staging_262b`, ổ D.

## 2. Bước 1 — verify production (điều kiện bắt buộc trước khi xóa canary)

- `C:\AIOS_p1_4\tri_thuc\library.sqlite` — 2.552.659.968 byte, mtime 2026-09-28 22:47.
- SHA-256: `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` — **KHỚP** chuỗi ghim.
- `PRAGMA integrity_check` = `ok`; `PRAGMA quick_check` = `ok` (mở `mode=ro`, chỉ đọc).

## 3. Bước 2 — xóa canary `C:\AIOS_habit_index_ve03\`

Hiện trạng ghi lại trước khi xóa — tổng **2.552.751.295 byte**:

| Tệp | Byte | Ghi chú |
|---|---|---|
| `library.sqlite` | 2.552.659.968 | SHA-256 `062ec090…` — **trùng ghim production** (bản copy của production) |
| `_run_ve03_resume.py` | 6.794 | script migration vé 0.3 |
| `_run_ve03_sample.py` | 4.066 | script vé 0.3 |
| `model-verify-cache.json` | 826 | cache kiểm tra model |
| `resume.log` | 79.102 | log |
| `sample.log` | 539 | log |

Đã xóa toàn bộ thư mục (kiểm tra `exists_after = False`, rc=0). Sau xóa đã liệt kê xác nhận còn nguyên: `C:\AIOS_p1_4`, `C:\AIOS_backup_production_2026-09-28`, `C:\AIOS_staging_262`, `C:\AIOS_staging_262b`.

## 4. Tổng kết thu hồi

- Bước 0: **11.432.612.441 byte**; Bước 2: **2.552.751.295 byte**; tổng **13.985.363.736 byte (~13,0 GiB)**.
- Ổ C trống: **414.445.568 → 14.435.442.688 byte** (Δ 14.020.997.120 B; chênh với tổng `du` do khối cấp phát/FS).
- Rác còn lại giữ theo luật "không chắc thì bỏ qua" (~1,05 GB gồm `aios-v14-data`, `iii-*`, `uv-cache`, `buoc0-deploy`, tool-smoke…); đề xuất Muse quyết ở vé sau nếu cần thêm chỗ.

## 5. Ràng buộc đã giữ

- Không ghi ổ D (chỉ đọc ZIP/SHA để đối chiếu); không đụng production/backup/staging; không ghi index/embed; không sửa code/test.
- Không merge `main`, không force-push; chỉ commit tài liệu lên `phieu-viec/rag-fix1`.
- Báo cáo này + `trang-thai.md` → `xong-cho-duyet` chờ Muse review độc lập.
