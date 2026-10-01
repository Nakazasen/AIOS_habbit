# Vé `BK-ERRCODE` — Backfill mã thật cho ca thiếu mã: kết quả chạy trên máy nhà

- Trạng thái: **Chạy xong trên bản copy, chờ Muse duyệt.** Kết luận sơ bộ: **ĐẠT tiêu chí vé** — số ca thiếu mã thật giảm đo được (12.651 → 11.674; nhóm `ERROR` 3.537 → 3.196), test vé 18/18 đạt (17 bài gốc + 1 bài hồi quy của bản vá dry-run), cổng nền đạt, full suite không thoái lui so với nền (mục 6).
- Máy: `h410asrock` — Windows 10 Pro `10.0.18363` x64; Python `3.11.14` (`.venv` repo qua `uv 0.10.6`).
- Nhánh: `phieu-viec/rag-fix1`. Mốc: `6d7bf56` (nhận vé, `dang-lam`) → `8645e2a` (Mốc 2: backfill xong — kèm báo lỗi dry-run) → `8b813db` + `fe0376b` (Muse vá dry-run + ghi chú, ~5 phút sau Mốc 2) → `4acf66f` (Mốc 3: test/cổng nền) → `105bd62` (báo cáo này) → (cập nhật nghiệm thu bản vá + mốc `xong-cho-duyet` theo sau).
- Phạm vi ghi: DB copy `C:/tmp/b0-dict/error_cases_dict.db` + file phụ trong `C:/tmp/bk-errcode/`; repo chỉ nhận báo cáo này + `trang-thai.md`. **Không ghi DB gốc, không đụng dữ liệu ổ D, không merge `main`, không force-push, dữ liệu thật không vào Git.**

## 0. Cổng gate (vòng khép kín)

- Watcher máy nhà (`D:/Sandbox/Vong_lap_giao_viec/`, state `launchStallCount=2`) tự mở OMP lần 2/4 lúc **11:42:43**; phiên kiểm cổng 11:51 xác nhận **chưa có mã** (đã ghi `d09c2a1`).
- **11:54–11:55 Muse đẩy code xong** (`5dc0d08` + `0570cbc`, ghi chú `c9d26c7`) → **điều kiện mở ĐÃ TỚI**; OMP nhận vé, chuyển `trang-thai.md` sang `dang-lam` lúc 12:00 (`6d7bf56`) — dừng đúng cơ chế stall, không dùng nhánh "4 lần watcher"/`cho-muse`, không no-op.
- Lưu ý còn treo: dòng `Ticket hiện tại:` trong `trang-thai.md` vẫn ghi `B1-FEAT` (Muse chưa cập nhật khi phát hành `BK-ERRCODE`) — log watcher hiện ticket theo chuỗi cũ; OMP giữ nguyên để không reset bộ đếm (đã báo trong ghi_chu 11:51), đề nghị Muse cập nhật ở verdict tới.

## 1. Nguồn & phạm vi

| Nguồn | Đường dẫn | Byte | SHA-256 |
|---|---|---:|---|
| DB copy đích (đã apply) | `C:/tmp/b0-dict/error_cases_dict.db` | 54.480.896 | sau apply `6bd41a8cdad66a06789df3ebcfed6e9fc90e77093a0052bef38624a7dd012369` |
| Backup trước apply | `C:/tmp/bk-errcode/error_cases_dict.db.bak-20261001-bk-errcode` | 54.050.816 | `3dad67fe5fa94b3c723cf3e4a4b45ea933ed59dc2d8deeb869d734c6f29e3d97` (khớp SHA ghim trong báo cáo `B1-FEAT`) |
| Bản scratch (lấy số liệu trước, rồi đối chứng) | `C:/tmp/bk-errcode/scratch-migrate-test.db` | 54.480.896 | cùng kết quả apply như bản chính |
| KTD (đối chiếu theo TÊN file, không mở file) | `C:/tmp/aios-v14-data/dieu_tra_loi/Điều chỉnh/Lịch sử lỗi/C Call/` | 215 file `KTD-*.xlsx` | — |

- DB gốc không đụng: `C:/tmp/date-map/error_cases_date.db` SHA `a362e571…` (khớp ghim `B0-DICT`), mtime nguyên; `C:/tmp/buoc0-deploy/error_cases_deploy.db` (`fa9efeba…`) + `C:/tmp/lsu1-deploy/error_cases_lsu.db` (`e24c356a…`) mtime/SHA nguyên (2 DB này còn nằm trong deny-list của script).
- Lệnh chạy (đúng env máy nhà): `AIOS_DATA_DIR='C:/tmp/aios-v14-data' PYTHONPATH='src;C:/tmp/e3-py311' TMP=TEMP='C:/tmp' uv run --no-sync --group dev python scripts/backfill_errcode.py --db C:/tmp/b0-dict/error_cases_dict.db --ktd-dir "C:/tmp/aios-v14-data/dieu_tra_loi/Điều chỉnh/Lịch sử lỗi/C Call" --csv-out C:/tmp/bk-errcode/manual.csv --apply` — log đầy đủ `C:/tmp/bk-errcode/apply_target.log`.
- Ghi chú môi trường: venv thiếu `xlrd` (group tùy chọn) → cần `PYTHONPATH` kèm `C:/tmp/e3-py311` như các vé trước.

## 2. Tiêu chí vé — số trước/sau (ĐẠT)

| Chỉ số | Trước | Sau | Chênh |
|---|---:|---:|---:|
| Ca thiếu mã thật (`error_code_i` rỗng) | 12.651 | 11.674 | **−977** |
| Trong đó nhóm `ERROR` | 3.537 | 3.196 | **−341** |
| Ca có mã thật | 3.056 | 4.033 | +977 |

- Nguồn từng mã (nhãn ghim trong `error_code_i_src`): **345 `extracted_them`** (trích tự động cột N/O/L/M/R, quét chặt có guard) + **632 `ktd_matched`** (khớp tên file KTD) = 977 ca ghi; **3.056 ca cũ** (từ `B0-DICT`, cột I) được đóng dấu nguồn `extracted_them` / ghi chú `cột I (B0-DICT)`. Nhãn `manual` chưa dùng (không có mã nào do người bổ sung trong lượt này — danh sách rà tay nằm ở CSV).
- Mẫu trích tự động (từ log apply): `2023/15` → `JAM9000` (cột O); `2023/38` → `F000` (cột N); `2023/174` → `JAM4211` (cột N); `2023/231` → `C3210` (cột N).
- Mẫu KTD: `2024/3428` (+`3429`, `3653`) → `C3200` từ `KTD-2024-11-1610-Iris2020-C35-A1-C3200.xlsx` (khớp line C35 + tháng 2024-11 + máy Iris2020); `2024/2644` (+`2672`) → `C0980` từ `KTD-2024-10-1272-Iris2020-C34-A1-C0980.xlsx`.
- Ca còn lại: **11.674** → CSV rà tay `C:/tmp/bk-errcode/manual.csv` (10.000 dòng — danh sách bị cắt trần 10k trong bộ nhớ script; có cột `candidates`/`conflicts` cho người rà, không bịa mã).
- Idempotent: chạy lại `--apply` lần 2 → `trích tự động 0 | KTD khớp 0 | đã ghi 0 | cần rà tay 11.674`, integrity ok.
- `integrity_check` trước/sau apply đều `ok`; **không sinh `-wal/-shm`**; backup nguyên vẹn. Migrate **thuần cộng thêm**: `error_cases` +2 cột `error_code_i_src`, `error_code_i_note` (thứ tự cột cũ giữ nguyên); không thêm/xóa/đổi object nào khác trong `sqlite_master`.

## 3. Đối chiếu KTD (bước 4 của vé)

- Kiểm kê thật: **215 file `KTD-*.xlsx`** trong `Lịch sử lỗi/C Call/` (cả 2 bản copy dữ liệu đều 215; con số "217" trong vé chênh 2 file không ảnh hưởng luật khớp — script khớp theo tên, không theo số lượng). Ngoài ra có **7 file `KTD-*.pdf`** cùng mã trong `C Call/` + `Log/<mã>/` (không phải xlsx, không quét).
- Trong 215 tên: **90 tên dùng được** (đuôi tên kết thúc bằng mã), **125 bị bỏ qua** vì đuôi tên là mô tả / định dạng underscore (ví dụ `KTD-2024-12-1696-Iris2020-C34-C6950 RL1.xlsx` — mã không nằm trọn đuôi) → script **không bịa mã**.
- Kết quả khớp: **24 file → 632 ca** (luật: đúng-1 dossier theo line + `YYYY-MM` + máy). Top khớp: `C0363` (47 ca), `C6950` (42 + 42), `JAM4709` (40), `JAM4012` (37), `C0980` (35).
- File ví dụ trong vé `KTD-2024-11-1537-Iris2020-C34-A1-C7901.xlsx`: **khớp 0 ca** (không ca thiếu mã nào đủ điều kiện đúng-1) — ghi nhận khách quan, không cưỡng khớp.

## 4. Lỗi dry-run [VM] — phát hiện, Muse vá, OMP nghiệm thu

- **Phát hiện (OMP, Mốc 2)**: đường dry-run của `scripts/backfill_errcode.py` gọi `backfill_error_code_i_extended(conn, apply=False, migrate=False)`, nhưng hàm **luôn** SELECT kèm `error_code_i_src` — trên DB chưa có cột (đúng ca "dry-run trước rồi mới `--apply`") thì SQLite ném `sqlite3.OperationalError: no such column: error_code_i_src`. Đã tái hiện trên bản copy sạch.
- **Muse vá `8b813db`** (12:19 — ~5 phút sau ghi chú Mốc 2; ghi chú `fe0376b` "OMP pull rồi chạy lại"): SELECT tự nhận diện cột — thiếu cột thì chọn NULL thay vì crash; kèm test hồi quy fail-trên-code-cũ / pass-trên-code-mới. Đường `--apply` (có migrate) không đổi.
- **OMP nghiệm thu bản vá (chỉ đọc)**: chạy lại đúng lệnh dry-run trên bản **chưa migrate** (`C:/tmp/bk-errcode/error_cases_dict.db.bak-20261001-bk-errcode`) — `rc=0`, số liệu khớp apply (345 / 632 / 11.674; đóng dấu nguồn 0; đã ghi 0), in `DRY-RUN: chưa ghi gì vào DB`; SHA bản copy **không đổi** sau lượt (`3dad67fe…` → `3dad67fe…`). Quy trình chuẩn của vé ("dry-run trước + backup trước") nay chạy đủ.
- Xử lý tạm của OMP lúc chưa có bản vá (để không chặn vé): lấy số liệu "trước khi ghi bản chính" bằng apply trên bản scratch byte-identical (`scratch-migrate-test.db`) rồi mới apply bản chính — số 2 lần trùng khít (345/632/3.056/977/11.674). Bản copy chính luôn có backup trước khi ghi.

## 5. Ràng buộc đã giữ

- **Không ghi DB gốc**: chỉ ghi bản copy; 3 DB đối chứng (date-map, deploy, LSU) SHA/mtime nguyên; script còn có deny-list tên DB production + tham số `--production-db`.
- **Không đụng dữ liệu ổ D**: mọi file sinh trong `C:/tmp/bk-errcode/`; repo chỉ nhận báo cáo + `trang-thai.md`.
- **Không merge `main`**, không force-push; dữ liệu thật không vào Git (báo cáo chỉ mã nghiệp vụ ngắn + số liệu + đường dẫn).

## 6. Test & cổng nền

- Test vé: `tests/test_bk_errcode.py` — **18/18 đạt** trên máy nhà sau bản vá dry-run (17 bài gốc + 1 bài hồi quy của `8b813db`; trước vá đo 17/17).
- Bộ liên quan (bk_errcode + b0_dict + error_cases F1–F4 + backfill_fix + lsu_logs): **121/121 đạt** sau vá (6,31 s; trước vá 120/120, 8,36 s).
- Full suite cuối trên cây sau vá (đúng lệnh nền `AIOS_DATA_DIR='C:/tmp/aios-v14-data' PYTHONPATH='src;C:/tmp/e3-py311' TMP=TEMP='C:/tmp'`; junit: `C:/tmp/bk-errcode/junit_bk2.xml`): **3.494 đạt / 2 bỏ qua / 35 lỗi / 9 error** (511,09 s). Nền `B1-FEAT` tại `7d06e51` (log `C:/tmp/b1-feat/pytest_full3.log`): 3.475 / 2 / 35 / 9 (522,80 s). Lượt giữa (cây trước bản vá nhỏ): 3.493 / 2 / 35 / 9 (`junit_bk.xml`).
  - **Không thoái lui**: 44 mục lỗi/error hiện tại **trùng khít từng node** với nền (đối chiếu junit ↔ log nền; 9 error đều là fixture hardcode đường VM `/home/hatch/...` của test vé `B1-FEAT` — ngoài phạm vi vé này); số bỏ qua giữ nguyên 2.
  - Node thu thập 3.521 → **3.540 (+19)**: 17 test của vé + 1 test hồi quy bản vá dry-run (`8b813db`) + 1 test lane `pc0575` (`0a5f8d2`, có trước phiên này); **không node nào biến mất** (đối chiếu danh sách node bằng worktree tạm — `collect_baseline.txt` ↔ `collect_current.txt`, đã dọn).
- Cổng nhanh: `scripts/check_docs.py` **DOCUMENTATION_CONTRACT=PASS** · `compileall -q src tests` **PASS** · `aios_habit.cli audit` **`"status": "PASS"`** (errors/warnings rỗng) · import `workspace_chat_app` **OK** · `git diff --check` + `--cached --check` sạch.

## 7. Kết luận & đề xuất

1. **ĐẠT tiêu chí vé**: thiếu mã giảm đo được (977 ca; riêng nhóm `ERROR` −341), test mới đạt, full suite không thoái lui so với nền, báo cáo + commit riêng trên `phieu-viec/rag-fix1`.
2. Đề nghị Muse: (a) sửa lỗi dry-run (mục 4) + test hồi quy; (b) cập nhật dòng `Ticket hiện tại` ở verdict tới; (c) xem 125 file KTD bỏ qua — muốn khớp thêm cần chuẩn hóa tên (mã ở cuối) hoặc luật trích mã giữa tên; (d) 11.674 ca rà tay (CSV) là đầu vào cho vé `BK-82`/đợt sau.

## 8. Phụ lục — bằng chứng thô

- Log apply + phiên: `C:/tmp/bk-errcode/apply_target.log`; CSV: `manual.csv`, `manual_rerun.csv` (idempotent), `manual_scratch.csv`; backup `error_cases_dict.db.bak-20261001-bk-errcode`; scratch DB `scratch-migrate-test.db`.
- SHA bản copy trước apply `3dad67fe…9e3d97` → sau apply `6bd41a8c…2369`; `integrity_check` = `ok` cả 2 mốc.
- Full suite: junit `C:/tmp/bk-errcode/junit_bk.xml` (cây trước bản vá nhỏ) + `junit_bk2.xml` (cây cuối); danh sách node đối chiếu `collect_baseline.txt` (nền `7d06e51`, worktree tạm đã dọn) ↔ `collect_current.txt`.
- Nghiệm thu bản vá dry-run (chỉ đọc): chạy trên `…bak-20261001-bk-errcode` (chưa migrate), CSV `manual_dryrun_fixed.csv`, SHA bản copy không đổi trước/sau (`3dad67fe…`).
- Code Muse được verify: `5dc0d08` (extractor N/O/L/M/R + KTD matching + CLI) + `0570cbc` (17 test) + `8b813db` (vá dry-run + test hồi quy); ghi chú phát hành `c9d26c7`, `fe0376b`.
