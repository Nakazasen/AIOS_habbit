# Báo cáo TEST-SUITE-CONFIRM-HOME — chạy lại toàn bộ bộ kiểm thử tại đầu nhánh

- Mã vé: `TEST-SUITE-CONFIRM-HOME`
- Ngày chạy: 2026-10-09 (bắt đầu 10:54 +07, kết thúc ~12:14 +07)
- Người chạy: opencode (thợ phụ tạm thời, máy nhà `h410asrock`)

## 1. Đầu nhánh tại thời điểm chạy

- Commit khởi động lượt pytest: `683554f` (đã gồm mọi thay đổi `src/`/`tests/` tính tới lúc chạy — mới nhất là `9805b6d` stage2 source-model).
- Các commit về sau trong lúc chạy chỉ là tài liệu (`docs/`, `mailbox*`, verdict — đã kiểm `show --stat` với 2 commit đầu, còn lại theo message đều `docs:`/`VERDICT`), `git status` tracked sạch sau chạy: **không sửa `src/`/`tests/` trong vé này**.
- Python 3.11.14 qua `uv run --no-sync --group dev`. Thư mục tạm `D:\pytest-tmp` (ổ C còn ~4,2 GB).
- Lệnh đúng cổng repo, một lượt duy nhất: `uv run --no-sync --group dev pytest -q --tb=short` (log ngoài Git: `local_runs/test-suite-confirm-home/pytest-full.log` + `.err.log`, `done.marker exit=1`).

## 2. Kết quả tổng (một lượt duy nhất)

- **1 failed, 4218 passed, 66 skipped, 0 errors trong 4776,22 giây (1 giờ 19 phút 36 giây).**
- Tổng số ca: 4285 (mốc vé dọn dẹp: 4283 — tăng ròng +2, khớp các thay đổi thật đã vào nhánh sau đó: mở rộng phân loại intent diagnosis/lookup + sửa synthesis + stale-guards).
- Chạy chậm hơn các mốc cũ (30,9–57,5 phút) vì máy chạy song song app thật + worker BGE của thợ khác (OMP) trong cùng thời gian.

## 3. Ca đỏ duy nhất — phân loại sơ bộ: flaky môi trường đã biết, KHÔNG phải hồi quy code

- Tên ca: `tests/test_commit_d_wheel_and_packaging.py::TestDesktopPackagingConfiguration::test_packaged_desktop_e2e_rag_to_atlas`
- Thông báo gốc (ngắn gọn): ca này mở một lượt pytest lồng trong interpreter mới để cách ly BGE-M3, với trần cứng `timeout=300` (`test_commit_d_wheel_and_packaging.py:394-401`); lượt con không xong kịp 300 giây dưới tải máy nặng nên tiến trình cha nhận `subprocess.TimeoutExpired` và FAIL. Không có assert sai hành vi nào — chỉ là hết giờ.
- Bằng chứng phân loại môi trường (không phải code mới hỏng):
  1. Báo cáo `b0-form.md` đã ghi đúng ca này là **"bài nền flaky cần môi trường BGE cách ly"** (lần đó tự xanh).
  2. Chạy RIÊNG đúng 1 ca này trên cùng mã nguồn sau lượt full: **1 passed trong 139,50 giây** — tức bản thân lượt con đã ngốn ~140 giây ngay cả khi chạy lẻ lúc máy còn tải; trong lượt full (cả bộ + app thật + BGE của thợ khác) vượt 300 giây là hợp lý theo tải, không phải logic sai.
  3. Phần còn lại của bộ xanh gần tuyệt đối (4218 passed, 0 errors) so với ROUND2 (19 failed + 19 errors) và HEALTH (26 failed + 19 errors) — đúng hướng "tín hiệu sạch còn đứng vững", chỉ lọt 1 ca giờ-giấc môi trường.
- Không sửa mã, không sửa kiểm thử theo rào vé. Đề xuất cho điều phối: giữ ca này ở nhóm flaky môi trường (cân nhắc nới trần lồng hoặc skip có điều kiện khi máy tải nặng), không mở vé sửa code vì nó.

## 4. Đối chiếu số bỏ qua với mốc vé dọn dẹp

- Mốc dọn dẹp (`test-suite-hygiene-home.md`): **0 failed / 4217 passed / 66 skipped / 0 errors** (skip 46 → 66 = +20 ca có điều kiện: 19 thiếu tệp máy khác + 1 slow packaging).
- Lượt này: **66 skipped — khớp tuyệt đối**, không tăng/giảm, không cần giải thích thêm theo điều kiện máy.
- Passed 4217 → 4218 (+1) và failed 0 → 1 là cùng một câu chuyện ca flaky giờ-giấc ở §3 (tổng +2 ca mới từ thay đổi thật đã vào nhánh).

## 5. Cổng repo (phụ trợ, không thay nghiệm thu)

- `compileall src tests`: sạch.
- `python -m aios_habit.cli audit`: `{"status": "PASS"}`.
- `import aios_habit.workspace_chat_app`: OK.
- Không ghi chỉ mục, không merge `main`.

## 6. Kết luận cho điều phối

- Tín hiệu sạch sau vé dọn dẹp **cơ bản còn đứng vững**: 0 errors, skip giữ nguyên 66, 4218/4219 ca có kết luận đạt.
- 1 ca đỏ duy nhất là flaky môi trường đã biết (hết giờ lượt con BGE dưới tải), đã chứng minh chạy riêng xanh — đề nghị verdict ghi nhận, không tính là hồi quy thật.
