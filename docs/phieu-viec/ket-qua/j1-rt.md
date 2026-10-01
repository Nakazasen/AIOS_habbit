# Vé `J1-RT` — JIG realtime: kết quả kiểm chứng trên máy nhà

- Trạng thái: **ĐẠT** — hai blocker của lượt kiểm trước đã được Muse vá (`5bb837e`) và OMP kiểm lại độc lập trên máy nhà: test vé **26/26**, probe độc lập **39/39**, E2E dữ liệu thật đạt, cổng nền + full suite ghi ở mục 4. Chờ Muse review.
- Nhánh: `phieu-viec/rag-fix1`. Mã được kiểm: `5bb837e` (bản vá 2 blocker). Mốc báo cáo: `543c4c5` (Mốc 2) + commit báo cáo này.
- Máy: Windows 10 x64, Python 3.11.14. Đúng lane `[VM]`: OMP chỉ kiểm chứng, không sửa mã. CSV nguồn đọc qua bản mirror cục bộ chỉ-đọc; mọi tệp phát sinh ở `C:/tmp/j1-rt-verify/r3/`, không đưa dữ liệu hoặc SQLite vào repo, không đụng DB gốc, ổ D hay `main`.

## 1. Bản vá của Muse và phạm vi kiểm lại

Commit `5bb837e` (22:23:07) trả lời trực tiếp báo cáo blocker `2c19869`:

- **Fail-closed theo từng JIG:** `_token_cho_jig` giờ trả `None` cho JIG không có trong `jig_tokens`; `_kiem_tra_auth_post` từ chối khi token yêu cầu là `None` hoặc không khớp (`yeu_cau is None or token != yeu_cau`) — JIG chưa cấu hình bị **401**, không rơi về token chung.
- **Từ chối phần tử không phải object:** `_tach_cac_ban_tin` ném `json.JSONDecodeError` cho mọi phần tử không phải object ở **cả** nhánh mảng JSON lẫn NDJSON, trước bước kiểm định/ghi → **400**, lô giữ nguyên tử (không ghi một phần).
- Test hồi quy mới: `test_fix4_auth_tu_choi_jig_chua_cau_hinh`, `test_fix2_lo_co_phan_tu_khong_phai_object_bi_tu_choi` (bộ vé 24 → **26 bài**).

Muse đã review độc lập trên clone mới (tip `5bb837e`): 26/26 đỗ, và ghi verdict trong `trang-thai.md` yêu cầu OMP chạy lại 2 probe + test vé. Đúng điều kiện mở gate (không dùng nhánh "4 lần watcher"/`cho-muse`; phiên này là `RELAUNCH 2/4`).

## 2. Mốc 1 — test vé và nhóm hồi quy

| Lệnh / phạm vi | Kết quả |
|---|---|
| `tests/test_j1_rt.py` chạy từ `C:/tmp` với mirror CSV thật (`C:/home/hatch/...`, 24.375.633 B, SHA-256 `6ebf2930…441c` khớp ghim LSU-1) | **26/26 đạt** (11,88 s), không bài nào skip |
| Chạy lại xác nhận lúc 23:19 (cùng máy, cùng mirror) | **26/26 đạt** (11,85 s), log `C:/tmp/j1-rt-verify/r3/pytest_j1rt_r3_final.log` |
| Nhóm hồi quy từ gốc repo: `test_stream_api`, `test_iris_any_log_and_archive`, `test_iris_log_intake`, `test_j1_csv` | **99 đạt / 4 bỏ qua** (4 skip là cổng dữ liệu thật hardcode path Linux — đúng thiết kế) |

## 3. Mốc 2 — probe độc lập (39/39 đạt, 0 FAIL)

Script `C:/tmp/j1-rt-verify/r3/probes_j1rt_r3.py` chạy trên Python 3.11.14, mỗi nhóm dùng listener + SQLite riêng. Tổng kết: **39 PASS / 0 FAIL** (`probe_r3_summary.json`).

| Nhóm | Nội dung | Kết quả |
|---|---|---|
| P1 | Lô **105 dòng** | HTTP 200, ACK `so_dong=100` + `bi_cat_bot=5`; DB đúng **100 dòng** — không mất dữ liệu, ACK trung thực |
| P2 | JSON object pretty-print nhiều dòng + NDJSON | Nhận đúng cả hai (200; `so_dong=1` và `2`) |
| P3 | Lô có dòng sai, dòng hợp lệ đứng **trước** | **400**, DB **0 dòng** — batch nguyên tử, không ghi một phần |
| P4 | Gửi lại y nguyên lô (retry) | `trung_lap=2`, DB vẫn 2 dòng; lặp cả với `event_id` gửi kèm — không ghi trùng |
| P5 | Token riêng từng JIG | Đúng token → 200; dùng nhầm token jig khác → 401; thiếu token → 401; **JIG chưa cấu hình + token hợp lệ → 401 và 0 dòng ghi** (blocker 1 đã hết); GET: token bất kỳ đã cấu hình → 200, thiếu/sai → 401 |
| P6 | Phần tử không phải object (blocker 2) | Mảng `[{...}, "not-an-object"]` → **400**, DB 0 dòng; NDJSON có dòng chuỗi → **400**, DB 0 dòng; lô toàn object → 200 và ghi đủ — blocker 2 đã hết |
| P7 | E2E dữ liệu thật | 60 dòng `SKEW:BLACK` thật từ CSV mirror + 12 điểm drift mô phỏng (tb+4σ tính từ chính 60 giá trị thật, gắn `SIMULATED_REALTIME`) → gửi 2 lô qua HTTP: **72/72 dòng lưu**; consumer nhận **2 cảnh báo `canh_bao_drift`**; thẻ cảnh báo hiện "[Dữ liệu phát lại mô phỏng]"; sự kiện giữ nguồn `SIMULATED_REALTIME`; GET thiếu token → 401; cursor lưu đĩa, consumer mới nạp lại → **0 sự kiện mới**; sự kiện bền qua restart listener |
| P8 | Sender retry | Lỗi mạng → thử lại 3 lần có backoff rồi báo lỗi tiếng Việt; lỗi HTTP 400 → báo ngay, không thử lại |

## 4. Mốc 3 — cổng nền và full suite

- `uv run --no-sync --group dev python -m compileall -q src tests` → **EXIT=0**.
- `uv run --no-sync --group dev python scripts/check_docs.py` → **DOCUMENTATION_CONTRACT=PASS**.
- CLI audit (`PYTHONPATH=src`) → **`"status": "PASS"`**, `errors`/`warnings` rỗng; import `aios_habit.workspace_chat_app` → **OK**.
- Log cổng: `C:/tmp/j1-rt-verify/r3/gates_r3.log`.
- Full suite: `uv run --no-sync --group dev pytest -q` → **3.574 đạt / 36 bỏ qua / 37 lỗi / 19 error**, exit 1, 620,32 giây; log `C:/tmp/j1-rt-verify/r3/pytest_full_r3.log` (kết thúc 23:14:16). Cây chạy: `543c4c5` = mã `5bb837e` + docs (không gồm commit LEXICAL `4a796ac` — vé khác, vào nhánh sau khi lượt suite bắt đầu). 19 error do thiếu fixture XLS/XLSX cục bộ; các lỗi còn lại gồm BGE worker/Graphify không sẵn có, kiểm thử cần mạng/provider, `uv.lock`/import và assertion RAG/privacy. **Không có bài `test_j1_rt.py`/`test_stream_api.py` trong danh sách lỗi**; đối chiếu lượt full suite liền trước cùng máy (mã tiền-vá `edf6f23`, 3.572/36/37/19): **+2 đạt đúng bằng 2 test hồi quy mới**, số lỗi/error/bỏ qua không đổi.

## 5. Đối chiếu tiêu chí vé

- [x] **Spec API hoàn chỉnh** — `docs/phieu-viec/ket-qua/j1-rt-api-spec.md`: endpoint nhận log (`POST /api/v1/jig/stream-log`), endpoint server→AI (`GET /api/v1/jig/events`), định dạng bản tin (object/mảng/NDJSON), trần 100 bản tin/lô, auth Bearer theo từng JIG, retry/backoff, cursor bền, drift 40+10/3σ và nhãn mô phỏng.
- [x] **Prototype chạy được với dữ liệu phát lại** — phát lại CSV JIG thật theo đúng dòng thời gian, gắn `SIMULATED_REALTIME`, đi qua HTTP thật tới consumer AI (mục 3, P7); không bịa dữ liệu.
- [x] **Danh sách yêu cầu hạ tầng** — `docs/phieu-viec/ket-qua/j1-rt-yeu-cau-ha-tang.md`: máy chủ, mạng LAN, agent thu log trên JIG, token, vận hành và thứ tự triển khai. Triển khai hạ tầng thật thuộc việc khác, ngoài phạm vi vé (đúng ghi chú của vé).
- [x] **Hợp đồng đặc tả ↔ mã** — toàn bộ điểm từng bị lệch ở lượt 1–2 (ACK cắt lô, JSON nhiều dòng, ghi một phần, token dùng chung, thiếu retry, cursor chỉ RAM, JIG chưa cấu hình qua mặt auth, phần tử non-object bị bỏ âm thầm) đã được vá và kiểm lại độc lập đạt.

## 6. Lịch sử các lượt kiểm (rút gọn)

| Lượt | Mã | Kết luận |
|---|---|---|
| 1 | `3fd332c` | CHƯA ĐẠT — 6 lỗi chặn: ACK lệch 105/100, JSON nhiều dòng 400, ghi một phần lô lỗi, token dùng chung, sender thiếu retry, cursor chỉ ở RAM |
| 2 (sau `f02a9e9` + `edf6f23`) | `edf6f23` | Test vé 24/24 nhưng còn **2 blocker** phát hiện bằng probe độc lập: JIG chưa cấu hình vượt auth; phần tử non-object bị bỏ âm thầm (ghi một phần, HTTP 200) |
| 3 (sau `5bb837e`) | `5bb837e` | **ĐẠT** — test vé 26/26, probe 39/39, E2E dữ liệu thật đạt; cổng nền + full suite ghi ở mục 4 |

## 7. Bằng chứng cục bộ

- `C:/tmp/j1-rt-verify/r3/probes_j1rt_r3.py` — script probe độc lập.
- `C:/tmp/j1-rt-verify/r3/probe_r3_summary.json` — 39 mục PASS/FAIL kèm chi tiết.
- `C:/tmp/j1-rt-verify/r3/*.sqlite`, `p7-cursor.json` — DB tạm từng nhóm probe.
- `C:/tmp/j1-rt-verify/r3/gates_r3.log`, `C:/tmp/j1-rt-verify/r3/pytest_full_r3.log`, `C:/tmp/j1-rt-verify/r3/pytest_j1rt_r3_final.log` — log cổng nền + full suite + lượt chạy lại test vé.

Commit OMP chỉ cập nhật báo cáo và mailbox; không sửa mã vé.
