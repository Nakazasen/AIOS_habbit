# Báo cáo vé FEEDBACK-REVIEW-HOME — vòng xem lại định kỳ + cảnh báo xu hướng SMA(20)

- Ngày: 2026-10-06 05:19 +07 (giờ máy khi chốt).
- Vé: `FEEDBACK-REVIEW-HOME` — điểm 3 của vòng lặp cải thiện liên tục (điểm 1+2 đã ĐẠT ở vé LOOP-HOME: nút like/dislike + store mã máy + metric + học thói quen).
- Prompt: `docs/phieu-viec/mailbox/prompt.md` (copy `prompt-queue-feedback-review-home.md`).
- Nhánh: `phieu-viec/rag-fix1`. Không merge `main`.
- Trạng thái: đã code + verify xong, chờ duyệt.
- Cổng gate: MỞ suốt vé (HEAD=origin khi nhận=c64cbbb, prompt đúng vé REVIEW-HOME, trạng thái `moi` mới ~06:05 06/10 theo giờ Muse, không có file watcher tự mở trong `mailbox/`).

## 1. Khảo sát code sẵn có (tái dùng, không viết lại)

- `src/aios_habit/answer_feedback.py`: store JSONL `local_cases/answer_feedback.jsonl` (ghi kèm `device_id`/`topic` từ vé trước). Vé này chỉ ĐỌC qua `iter_recent`, không sửa store.
- `src/aios_habit/feedback_loop_home.py` (~459 dòng): `question_key` (chuẩn hóa khóa câu), `compute_loop_metrics` (bảng xếp hạng chê theo câu/chủ đề), `flag_answers_for_fix` (chê từ 2 máy trở lên), cờ `AIOS_FEATURE_FEEDBACK_LOOP_HOME` TẮT mặc định. Vé này tái dùng cả 4 (không viết lại store/metric/cờ).
- Không có CLI xem lại nào trước đó → vé này thêm entry `python -m aios_habit.feedback_review_home` (chỉ chạy khi được gọi, không tự chạy ngầm).

## 2. Phương án đã làm (1 module mới + 1 test mới, không sửa luồng cũ)

- Mới `src/aios_habit/feedback_review_home.py` (~490 dòng):
  - `sma`/`sigma`/`sma_sigma` trên đuôi chuỗi (cửa sổ 20, chỉnh được; chuỗi <20 điểm dùng SMA(n) hiện có + cờ `so_bo` = "chưa đủ 20 điểm, sơ bộ").
  - `is_anomaly`: |tỉ lệ chê − SMA| > k·σ (k mặc định 2, chỉnh qua `--k`).
  - `detect_anomalies`: mỗi điểm so với cửa sổ TRƯỚC nó (không gồm chính nó) — để 3 điểm xấu liên tiếp không tự làm mờ nhau.
  - `has_trend_alert`: cảnh báo khi ≥3 điểm bất thường LIÊN TIẾP hoặc ≥3 trong 5 ngày gần nhất; 1 điểm xấu đơn lẻ KHÔNG cảnh báo.
  - `build_daily_rates`: gom tỉ lệ chê theo ngày cho từng `question_key` và từng chủ đề (ngày lấy từ `created_at`, chủ đề thiếu thì dùng lại `detect_topic`).
  - `run_periodic_review()`: chạy 1 lần khi được gọi; khi cờ TẮT trả `tat_co` và không ghi gì; khi bật: đọc feedback → metric cũ → SMA/trend từng chuỗi → báo cáo Markdown ghi vào `local_cases/feedback_review_*.md` + đề xuất sửa gốc theo thứ tự (ưu tiên 1 = vừa trend xấu vừa bị chê từ 2 máy; ưu tiên 2 = trend xấu cần theo dõi; ưu tiên 3 = bị chê nhiều máy nhưng chưa trend; kèm xem lại chủ đề chê >30%).
  - `main()`: CLI `--cua-so/--k/--dau-ra`, in tiếng Việt ("Đã ghi báo cáo…", "Cờ … đang tắt nên không chạy.").
- Mới `tests/test_feedback_review_home.py` (10 test): SMA(20) của 0..19 = 9.5; sigma phẳng = 0; chuỗi ngắn gắn sơ bộ; 1 điểm lệch KHÔNG cảnh báo; 3 điểm liên tiếp CÓ cảnh báo; 3-trong-5 cảnh báo (kể cả không liên tiếp); gom tỉ lệ theo ngày đúng; cờ tắt thì không làm gì; end-to-end có báo cáo đủ 3 mục + đề xuất ưu tiên; CLI ghi file thật.
- Không sửa file cũ nào (diff `c64cbbb..HEAD -- src tests` chỉ có 2 file mới).

## 3. Đối chiếu tiêu chí nghiệm thu trong prompt

- SMA(20)/σ đúng trên chuỗi biết trước: đạt — SMA(20) của 0..19 = 9.5 (test + chạy thật).
- 1 điểm lệch KHÔNG cảnh báo / 3 điểm liên tiếp CÓ cảnh báo (test cả hai): đạt — 10/10 test vé xanh, trong đó có 3 test đúng 2 trường hợp này + 1 test 3-trong-5-ngày.
- Báo cáo mẫu chạy thật trên dữ liệu giả lập nhiều máy (bảng xếp hạng + trend alert + đề xuất ưu tiên): đạt — xem mục 4.
- `compileall` sạch + test vé ≥8 + hồi quy 12 test LOOP-HOME + `cli audit` PASS + import app OK: đạt — `compileall src tests` sạch (không error/fail); test vé 10/10; hồi quy LOOP-HOME 12/12; bộ feedback rộng 50/50 (`answer_feedback` + `feedback_loop` + `loop_home` + `review_home`); `cli audit` PASS (`errors: []` — chạy bằng `PYTHONPATH=src` vì `.venv` thiếu cài đặt gói, xem mục 5); `import workspace_chat_app` OK. Bộ toàn kho nặng: không bắt buộc theo prompt — báo trung thực là chưa chạy.
- Không ghi index/kho tri thức, không merge `main`, không secret: đạt — grep `index|knowledge|memory_vault|write_json|append_jsonl` trong module mới chỉ trúng 1 dòng comment "never the index"; báo cáo ghi `local_cases/` (đã gitignore dòng 77); không import `studio`/`case_cockpit`; không `api_key/secret/token/password`; 2 commit vé đều single-parent (không merge `main`).
- Báo cáo có số đo demo vòng xem lại chạy thật: đạt — mục 4.

## 4. Số đo demo vòng xem lại chạy thật (dữ liệu giả lập, môi trường cách ly `D:/tmp/rv-demo`)

- Gieo 161 lượt (125 khen / 36 chê, tỉ lệ chê 0,224), 3 câu × 23 ngày:
  - Câu xấu `Lỗi JAM4709 kẹt giấy là gì?`: 20 ngày ổn định (mỗi ngày 4 khen + 1 chê, tỉ lệ 0,2) + 3 ngày spike (mỗi ngày 5 chê, tỉ lệ 1,0) → tổng 115 lượt, 35 chê, tỉ lệ 0,304.
  - Câu tốt MOM: 23 ngày toàn khen (23 lượt, 0 chê).
  - Câu ổn định: 22 ngày khen + đúng 1 ngày chê đơn lẻ (23 lượt, 1 chê, tỉ lệ 0,043).
- Kết quả `run_periodic_review`: đúng 1 cảnh báo câu (JAM4709, 23 ngày, SMA=0,320 σ=0,286, ngày bất thường 2026-09-21/22/23) + 1 cảnh báo chủ đề (`dieu_tra_loi` cùng 3 ngày); câu 1-điểm-xấu KHÔNG cảnh báo.
- Bảng xếp hạng: JAM4709 đầu bảng (115 lượt, 35 chê, 4 máy) → lọt `flag_answers_for_fix` (chê từ ≥2 máy).
- Đề xuất theo thứ tự: ưu tiên 1 sửa gốc JAM4709 (vừa trend xấu vừa bị chê từ 2 máy trở lên) + xem lại chủ đề `dieu_tra_loi` (35/115 chê).
- CLI kiểm chứng: cờ bật → `Đã ghi báo cáo… Tổng 0 lượt…` (thư mục demo trống ghi đúng 0, trung thực); cờ tắt → `Cờ … đang tắt nên không chạy.` + exit 0, không ghi file.

## 5. Ghi chú trung thực (không báo PASS khống)

- `.venv` máy này thiếu cài đặt gói `aios-habit` nên `python -m aios_habit.cli` báo `No module named 'aios_habit'` nếu thiếu `PYTHONPATH`; đã chạy đúng bằng `PYTHONPATH=src uv run …` (Python 3.11.14, đúng `pyproject` >=3.11,<3.12) cho cả audit + import app + CLI module.
- Module mới không dùng `os`/`sys` (đã gỡ import thừa sau khi linter nhắc); epsilon float `1e-18` trong `_dev_of` để chuỗi phẳng trả σ đúng 0,0 (test `test_sigma_flat_series_is_zero` từng đỏ vì nhiễu `2.7e-17`).
- Báo cáo review mẫu (`D:/tmp/rv-demo/review.md`, `cli-check.md`) nằm NGOÀI repo theo rào vé (chỉ đọc/ghi `local_cases/`), không commit.

## 6. Cách dùng và hoàn tác

- Bật thử: đặt `AIOS_FEATURE_FEEDBACK_LOOP_HOME=1`, rồi chạy `PYTHONPATH=src python -m aios_habit.feedback_review_home --dau-ra local_cases/feedback_review_x.md` (thêm `--cua-so 20 --k 2.0` nếu muốn chỉnh).
- Đọc báo cáo trong `local_cases/feedback_review_*.md`: bảng xếp hạng → trend alert → đề xuất ưu tiên.
- Hoàn tác: tắt cờ là module không làm gì; xóa file mới là về đúng cây vé LOOP-HOME (không sửa file cũ nào).

## 7. Đề nghị duyệt vé

- Vé đạt ở mức chờ duyệt: SMA(20)+σ đúng, 1-điểm-xấu im lặng / 3-điểm-xấu báo động (test cả hai + demo thật), báo cáo đủ 3 mục + đề xuất ưu tiên, đúng rào (cờ TẮT, chỉ `local_cases/`, không index, không merge `main`).
- Nhờ Muse review độc lập rồi phát hành vé tiếp theo.
