# Báo cáo vé `DON-O-C` — lần phát hành lại 2026-10-03

## Tóm tắt

- Vé phát hành lại sau verdict `SCAN-O-D` ĐẠT (20:33 +07). Prompt là bản copy `prompt-queue-don-o-c.md`.
- **Không xóa file nào.** Thu hồi do xóa: **0 byte**.
- Ổ C lúc 20:39:30 trống **6.104.203.264 byte** (5.821,4 MiB). Lúc 20:46:30 trống **4.399.620.096 byte** (4.195,8 MiB). Chênh lệch là chỗ trống bị tiến trình khác chiếm trong lúc chỉ đọc, không phải do vé này xóa.
- Mục tiêu ~8 GB của vé **không lấy lại thêm** trong lần này: các mục an toàn đã dọn ngày 2026-09-29 (phụ lục). Phần lớn còn lại là kho đang chạy, bản backup rollback duy nhất, hoặc nằm ngoài 4 đường vé cho phép.
- Không đụng ổ D. Không đụng index production. Không đụng cây model ONNX. Không sửa code. Không merge `main`.
- Cổng gate: watcher `LAUNCH 1/4` lúc 2026-10-03 20:35:12. Điều kiện mở đã có (user cho phép dọn 2026-09-29 ~20:10 +07, lane [NHÀ]). Không chuyển `cho-muse`, không quay no-op.

## Máy và phạm vi

- Máy `h410asrock`, nhánh `phieu-viec/rag-fix1`, 20:36–20:46 +07 ngày 2026-10-03.
- Mỗi bước: liệt kê → xác minh → chỉ xóa khi chắc → đo dung lượng. Không chắc thì dừng, không xóa.

## Bước 1 — Rác tmp: thu hồi 0

Ngưỡng “quá 7 ngày”: `LastWriteTime` trước 2026-09-26 20:39:30.

- `C:\Windows\Temp`: 0 file.
- `%TEMP%` = `C:\Users\Admin\AppData\Local\Temp`: 2.999 file / 246.404.551 byte, **0 file** quá 7 ngày. Không xóa.
- `local_runs\**\tmp` dưới `D:\Sandbox\AIOS_habbit\local_runs`: 0 thư mục tên `tmp`.
- `scratch\` trên D: 963 file / 123.890.447 byte. Có 6 file `.py` cũ (11.361 byte, tên `fix2_onnx_probe.py`, `reproduce_oricon_query.py`, `test_*.py`). Đây là script, không phải tmp/log/cache, và nằm trên ổ D. **Không xóa.**

Danh sách đã xóa: không có.

## Bước 2 — Venv trùng: thu hồi 0

`sys.prefix` của Python dự án: `D:\Sandbox\AIOS_habbit\.venv`. OMP là binary native, không phải tiến trình Python; venv đang dùng lấy theo `sys.prefix` này.

| Venv | Byte | Quyết định |
| --- | ---: | --- |
| `D:\Sandbox\AIOS_habbit\.venv` | 2.263.914.512 | **GIỮ** — đang dùng |
| `D:\Sandbox\AIOS_habbit\.venv-rag` | 1.326.346.716 | **GIỮ** — ổ D, cấm đụng; không phải bản trùng của `.venv` |
| `D:\Sandbox\AIOS_habbit\.venv-rag-compat` | 1.674.487.483 | **GIỮ** — cùng lý do |
| 3 thư mục `C:\tmp\pytest-of-Vinh\...\ .venv` | 0 (chỉ có `Scripts\python.exe` 0 byte) | **GIỮ** — không phải venv thật, không so được `pip freeze`; mtime 2026-10-01, chưa quá 7 ngày |

Ba venv tạm trên C đã xóa ngày 2026-09-29 (`omp-ve-v1-py311`, `omp-ve-v1-venv`, `omp-ve-v14-gdown`) không còn. Không có venv trùng trên ổ C để xóa.

Danh sách đã xóa: không có.

## Bước 3 — Worktree vé 0.3: thu hồi 0

- `C:\c\AIOS_ve03_worktree` và `C:\AIOS_ve03_worktree`: không còn (đã xóa ngày 2026-09-29).
- `git worktree list` không có worktree vé 0.3. Có 2 mục khác, **không thuộc vé này**, không gỡ:
  - `C:\Users\Admin\AppData\Local\deep-dev\worktrees\aios_habbit_895eea08\...` nhánh `deep-dev/...`, đánh dấu `prunable`
  - `D:\Sandbox\AIOS_habbit_gate_f_live_baseline` — ổ D, cấm đụng

Danh sách đã xóa: không có.

## Bước 4 — Backup cũ: thu hồi 0

`C:\AIOS_habit_index_ve03` không còn. Bốn file `.bak-*` của vé 0.3 đã xóa ngày 2026-09-29.

Bản **đang chạy**, cấm xóa, đo lại chỉ đọc (`mode=ro`):

| Mục | Giá trị |
| --- | --- |
| Đường dẫn | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` |
| Byte | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` — khớp ghim |
| `PRAGMA integrity_check` | `ok` |

Không có backup cũ nào đủ điều kiện xóa:

| Tệp | Byte | Quyết định |
| --- | ---: | --- |
| `C:\AIOS_backup_library_c_2026-10-01_merge-home\library.sqlite.bak-20261001-merge-home` | 2.576.191.488 | **GIỮ** — bản rollback duy nhất của kho trước merge (SHA ghim `aa7eac3b…6f0c` trong báo cáo `merge-home`). Xóa là vi phạm “không xóa nếu chỉ còn 1 bản backup”. Không băm lại vì không xóa; size khớp ghim. |
| `C:\AIOS_backup_production_2026-09-28\library.sqlite.backup` | 32.452.608 | **GIỮ** — lần trước đã giữ vì là backup production cũ; không chắc đây là “2 backup cũ” của lần phát hành lại. |
| `C:\AIOS_staging_262\library.sqlite.bak-20260930-gpu262-preembed` và các `.bak` staging `262b` / `dc` | 834.904.064 và nhỏ hơn | **GIỮ** — staging GPU, không phải backup index production kiểu `C:\AIOS_habit_index_*`. Không chắc nên dừng. |
| `C:\AIOS_staging_262`, `262b`, `dc` (file `library.sqlite` đang dùng của staging) | 1.005.621.248 / 57.020.416 / 228.937.728 | **GIỮ** — không phải backup cũ. |

Danh sách đã xóa: không có.

## Bước 5 — `tri_thuc`: bỏ qua

Đúng vé: chưa làm, chờ E2v3 đóng hẳn. `C:\AIOS_p1_4\tri_thuc\library.sqlite` không còn (đã chuyển vào kho production ngày 2026-10-01). Không đụng `collections\tri_thuc` của kho đang chạy.

## Bảng dung lượng

| Bước | Trống trước (byte) | Trống sau (byte) | Thu hồi do xóa |
| --- | ---: | ---: | ---: |
| 1 — rác tmp | 6.104.203.264 | 6.104.203.264 | 0 |
| 2 — venv trùng | cùng mức liệt kê | cùng mức | 0 |
| 3 — worktree vé 0.3 | cùng mức | cùng mức | 0 |
| 4 — backup cũ | cùng mức | 4.399.620.096 lúc 20:46:30 | 0 |
| **Tổng xóa** | 6.104.203.264 | 4.399.620.096 | **0** |

Chỗ trống giảm ~1,59 GiB trong lúc chạy `integrity_check` chỉ đọc và các tiến trình khác ghi tạm. Không có file vé này xóa.

## Cấm — đã giữ

- Kho production `workspace_chat_rag_v2_production`: băm một lần trong phiên, khớp ghim `45eb0e07…b7c0`; mtime vẫn 2026-10-01 08:27:27.
- Cây model ONNX `models\bge-m3-onnx-fp32`: không mở, không xóa.
- Ổ D: chỉ đọc tên/size/mtime của `scratch` và tên venv. Không xóa, không sửa.

## Ngoài phạm vi — đề xuất vé riêng, không làm trong vé này

`C:\tmp` còn nhiều thư mục không nằm trong 4 đường bước 1 (checkpoint/worktree tạm ngày 2026-10-01, `uv-cache`, `deep-dev-*` tháng 8, dữ liệu vé cũ). Muốn lấy lại ~8 GB cần vé mới nêu rõ đường được xóa. Không tự nới luật.

---

# Phụ lục — lần dọn 2026-09-29 (đã xong trước vé phát hành lại)

## Tóm tắt

- **Ổ C trước khi dọn:** trống 3.532,5 MiB (~3,45 GiB) — đo lúc 23:44 +07 bằng `(Get-PSDrive C).Free`.
- **Ổ C sau khi dọn:** trống **12.884,6 MiB (~12,6 GiB)**.
- **Tổng thu hồi: 9.352,1 MiB (~9,1 GiB)** — vượt mục tiêu ~8 GB của vé.
- Không xóa gì trên ổ D (theo mục Cấm). Không đụng index production (cả bản D lẫn bản copy C). Không ghi index, không embed, không sửa code.
- Cổng gate: watcher mới tự mở OMP **1/4 lần** cho vé này → chưa kẹt; "điều kiện mở" (máy nhà đang bật + user đã cho phép ~20:10) đã có → vé chạy bình thường, không no-op, không chuyển `cho-muse`.

## Máy và phạm vi

- Máy `h410asrock`, nhánh `phieu-viec/rag-fix1`, khoảng 23:26–23:58 +07 ngày 2026-09-29.
- Chỉ xóa trên ổ C. Chỉ đọc/liệt kê trên ổ D, không xóa.
- Mỗi bước theo đúng trình tự vé: liệt kê → xác minh → xóa → đo dung lượng.

## Bước 1 — Rác tmp: thu hồi 0

- `C:\Windows\Temp`: rỗng (0 file đọc được).
- `%TEMP%` = `C:\Users\Admin\AppData\Local\Temp`: 954 file / 430 MiB, **nhưng file cũ nhất là 2026-09-27 20:29** → không có file nào "quá 7 ngày không đụng tới" theo đúng luật vé ⇒ không xóa file nào.
- `local_runs\**\tmp`: quét đệ quy `D:\Sandbox\AIOS_habbit\local_runs` — không tồn tại thư mục `tmp` nào.
- `scratch\`: bản trong repo trên D (117,7 MiB, script các lượt chạy) — để nguyên (Cấm "không đụng ổ D").

## Bước 2 — Venv trùng lặp: thu hồi 56,2 MiB

**Giữ lại (venv đang dùng):** `D:\Sandbox\AIOS_habbit\.venv`
- Mọi lượt chạy gần nhất (P1.4, E2 vòng 2–4, stale-check) đều dùng `D:\Sandbox\AIOS_habbit\.venv\Scripts\python.exe`; khớp `uv.lock`.
- Ghi chú: vé ghi "kiểm tra `sys.prefix` của OMP" — OMP là binary native (`C:\Users\Admin\AppData\Local\omp\omp.exe`), không phải tiến trình Python, nên căn cứ theo venv dự án đang được dùng.

**Đã xóa (trên ổ C)** — đều là venv tạm của các lượt vé V1/V1.4 (ngày 28/09), không tiến trình nào đang dùng, xóa thành công (`exists_after=False`):

| Venv | Kích thước | Gói chỉ có ở venv này (so `.venv`) | Ghi chú |
| --- | ---: | --- | --- |
| `C:\tmp\omp-ve-v1-py311` | 11,7 MiB | xlrd 2.0.2, packaging 26.3, Pygments 2.21.0 | `xlrd 2.0.2` nằm trong `uv.lock` extra `rag-ingestion-xls` (cài lại được) |
| `C:\tmp\omp-ve-v1-venv` | 27,2 MiB | packaging 26.3, Pygments 2.21.0 | venv pytest tối thiểu |
| `C:\tmp\omp-ve-v14-gdown` | 17,3 MiB | gdown 6.4.0, PySocks, beautifulsoup4… | công cụ tải Drive cài tay, không có trong lock — pip cài lại được |

⇒ Không có gói nào "đặc biệt" không tái tạo được.

**Để lại trên ổ D (theo Cấm):** `.venv-rag` (1.264,9 MiB), `.venv-rag-compat` (1.596,9 MiB) — hai môi trường khác nhau có mục đích (bảng so sánh trong `FIX2_dieu-kien-may-nha.md`: torch 2.5.1 vs 2.13.0, transformers 4.44.2 vs 4.57.6, onnxruntime), không phải bản trùng; `local_runs\_g1_gpu_test_venv` (2.541,4 MiB).

## Bước 3 — Worktree vé 0.3: thu hồi 2.611,3 MiB

- Hiện trạng: `C:\c\AIOS_ve03_worktree` (2.605,4 MiB) — thực chất là **bản clone độc lập** (`.git` riêng 1.286,9 MiB), KHÔNG có trong `git worktree list` của repo chính ⇒ không đăng ký là worktree, không thể/không cần `git worktree remove`; đã xác minh rồi xóa cả thư mục.
- Xác minh trước khi xóa:
  - Nhánh `phieu-viec/rag-fix1`, HEAD `c6aa083` (28/09 03:16 +07), cây làm việc sạch (`git status --short` rỗng).
  - `git log --all --not --remotes` rỗng → không có commit nào chưa push; không có stash.
  - `c6aa083` là tổ tiên của `origin/phieu-viec/rag-fix1` (`merge-base --is-ancestor` trả 0).
  - Dữ liệu cục bộ còn lại (đều bị `.gitignore`): `local_cases/` (~0,5 MiB) + `08_audit/final_audit_report.md` → đã đóng gói giữ lại: `C:\c\AIOS_ve03_worktree_local_cases_archive_20260929.zip` (27 mục, kiểm bằng `ZipFile.OpenRead`).
- Đã xóa `C:\c\AIOS_ve03_worktree` (`exists_after=False`).

## Bước 4 — Backup cũ trên ổ C: thu hồi 6.709,3 MiB

Đã kiểm toàn vẹn **bản giữ lại trước khi xóa** (điều kiện vé):
- `PRAGMA integrity_check` (mở `mode=ro`) trên `C:\AIOS_habit_index_ve03\library.sqlite` → **`ok`**
- `PRAGMA integrity_check` trên `C:\AIOS_backup_production_2026-09-28\library.sqlite.backup` → **`ok`**

| Tệp | Bytes | SHA-256 (đo trước khi xóa) | Quyết định |
| --- | ---: | --- | --- |
| `C:\AIOS_habit_index_ve03\library.sqlite.bak-20260927-1936-ve03` | 1.750.740.992 | `31E80A9497B3C64F8BFD7EDE0233F6EAF0526F55C78D5D694BFCCDAF69452FDA` | xóa |
| `…\library.sqlite.bak-20260927-211022-ve03` | 1.751.441.408 | `58580889F40BC7CA16E4ED1E6E19DCD487E23D33B5684B6A58307D4B55FF5F84` | xóa |
| `…\library.sqlite.bak-20260927-211949-ve03` | 1.752.297.472 | `0882786FBC416603A186BB449C205D9A397C5B573691ACFAB1F93F0BB3D2779C` | xóa |
| `…\library.sqlite.bak-20260927-223834-ve03-retry` | 1.780.740.096 | `F7F393E15778A1A4073F5BB8504CFF92390AB6F71FC32F9A4B770A721D1465FF` | xóa |
| `C:\AIOS_habit_index_ve03\library.sqlite` (canary đã thành production) | 2.552.659.968 | `062ec090644fb4ec09d2fb6388f3175e988e48d63061b04e6c27bbed334ef8ca` (băm lại trong vé này, khớp ghim P1.3) | **GIỮ** |
| `C:\AIOS_backup_production_2026-09-28\library.sqlite.backup` (production cũ trước P1.3) | 32.452.608 | `eedf4bf28dcaf5a871a1f632ab28286dff3296c6d1a57ff11e11cda781ed9c32` | **GIỮ** |
| `C:\AIOS_p1_4\tri_thuc\library.sqlite` (bản copy để truy vấn read-only) | 2.552.659.968 | `062ec090…` (đã kiểm ở vé stale-check) | **GIỮ** (ngoài phạm vi xóa của vé) |

- 4 tệp `.bak-*` đã xóa (`exists_after=False` cho cả 4). Còn lại trong thư mục: `library.sqlite`, `resume.log`, `sample.log`, `model-verify-cache.json`, 2 script vé 0.3.
- Sau khi xóa vẫn còn ≥1 bản backup của index production (bản GIỮ ở trên + bản copy truy vấn + bản production trên D) ⇒ không vi phạm điều kiện "không xóa nếu chỉ còn 1 bản backup duy nhất".

## Bảng dung lượng theo bước

| Bước | Trống trước (MiB) | Trống sau (MiB) | Thu hồi (MiB) |
| --- | ---: | ---: | ---: |
| 1 — rác tmp | 3.532,5 | 3.532,5 | 0 |
| 2 — venv trùng | 3.532,5 | 3.580,3 | 47,8 (đã xóa 56,2; chênh do file tạm sinh trong lúc chạy) |
| 3 — worktree vé 0.3 | 3.576,3 | 6.187,6 | 2.611,3 |
| 4 — backup cũ | 6.175,3 | 12.884,6 | 6.709,3 |
| **Tổng** | 3.532,5 | **12.884,6** | **9.352,1 (~9,1 GiB)** |

Ghi chú: ổ C có tiến trình khác (watcher/log/session) sinh file tạm trong lúc chạy nên "trống trước" của bước sau lệch nhẹ so với "trống sau" của bước liền trước — số thu hồi ở bảng là hiệu đo trực tiếp trong từng bước.

## Cổng gate (theo yêu cầu kiểm tra trước khi làm)

- Watcher v5 (`D:\Sandbox\Vong_lap_giao_viec\Watch-Mailbox.ps1`) tự mở OMP khi vé `moi` + hết cooldown 10 phút; đếm `launchStallCount`, đủ **4 lần không tiến triển** thì tự chuyển `cho-muse` (escalate).
- Lúc nhận vé: `launchStallCount = 1` cho vé `don-o-c` (lần tự mở 1/4, 23:25:47). Bốn lần tự mở tối nay (E2v3 20:04, E2v4 21:32, stale-check 22:44, don-o-c 23:26) đều là vé khác nhau và đều có tiến triển thật → không phải chuỗi no-op.
- Kết luận: chưa chạm ngưỡng 4 lần → **không chuyển `cho-muse`**; vé được nhận, làm trọn và báo cáo.

## Không đụng / để lại (ngoài phạm vi)

- **Ổ D (theo Cấm):** `local_runs` (~19,7 GB: canary 8.865,7 MiB, `retrieval_models` 4.376,1 MiB, `.venv-rag*`, `_g1_gpu_test_venv`…); `scratch` 117,7 MiB; index production `local_runs\workspace_chat_rag_v2_production\…\library.sqlite` nguyên vẹn.
- **Ổ C ngoài phạm vi Bước 1–4:** `C:\AIOS_p1_4` (GIỮ — bản copy truy vấn read-only); `C:\tmp` ~7,9 GB còn lại (ứng viên dọn tiếp: `omp-ve-v1` 2.583,6 MiB, `omp-ve-v1-clean` 2.583,7 MiB, `aios-data-v14` + `aios-v14-data` 893,5 MiB ×2, `aios-data-v14.zip` 818,4 MiB, `uv-cache`…) — không thuộc các bước của vé này, đề xuất vé riêng; `%TEMP%` 430 MiB (toàn file mới dưới 7 ngày).

## Giới hạn và đề xuất

- Bước 1 thu hồi 0 theo đúng luật "quá 7 ngày"; nếu muốn dọn sâu hơn phần `%TEMP%` (430 MiB) cần vé nới luật.
- Không xóa gì trên ổ D theo Cấm, kể cả các mục nhìn giống bản trùng (`.venv-rag`, `.venv-rag-compat`, `_g1_gpu_test_venv`, các thư mục `local_runs` cũ) — cần vé riêng nếu user muốn.
- Zip lưu dữ liệu cục bộ của clone vé 0.3 nằm ở `C:\c\AIOS_ve03_worktree_local_cases_archive_20260929.zip` (21.141 byte) — có thể xóa khi không cần đối chiếu nữa.
