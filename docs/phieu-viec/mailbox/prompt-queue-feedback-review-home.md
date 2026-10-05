# VÉ: FEEDBACK-REVIEW-HOME (vòng xem lại định kỳ + cảnh báo xu hướng SMA(20))

- Mã vé: `FEEDBACK-REVIEW-HOME`
- Role OMP gợi ý: DEFAULT (code + test nhẹ, không nặng)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/feedback-review-home.md`

## Bối cảnh

User chốt 2026-10-03: mọi tính năng phải có vòng lặp cải thiện liên tục
(feedback tại chỗ → metric đo được → vòng xem lại). Vé FEEDBACK-LOOP-HOME
vừa ĐẠT (verdict Muse 2026-10-06 ~06:00 +07) đã làm xong điểm 1+2: nút
like/dislike + lý do chọn sẵn ngay dưới câu trả lời trong khung chat, store
`local_cases/answer_feedback.jsonl` theo mã máy (không tài khoản), metric tỉ
lệ chê theo câu/chủ đề, đánh dấu câu cần sửa gốc, hồ sơ thói quen từng máy.

Vé này làm nốt điểm 3 — vòng xem lại ĐỊNH KỲ chạy thật được, kèm yêu cầu
"đừng quên" của user: **cảnh báo theo XU HƯỚNG + SMA(20)**:
không cảnh báo từ một điểm xấu; điểm bất thường = lệch xa SMA(20) quá k*σ;
cảnh báo khi có xu hướng (nhiều điểm bất thường liên tiếp).

## Việc cần làm

1. **SMA(20) + σ trên chuỗi tỉ lệ chê theo ngày** của từng câu hỏi
   (`question_key`) và theo chủ đề, đọc từ `local_cases/answer_feedback.jsonl`
   (tái dùng module `feedback_loop_home`, không viết lại store).
   - Điểm bất thường: |tỉ lệ chê ngày đó − SMA(20)| > k·σ (k mặc định 2,
     chỉnh được qua tham số).
   - Cảnh báo XU HƯỚNG: chỉ cảnh báo khi có ≥3 điểm bất thường LIÊN TIẾP
     (hoặc ≥3 trong 5 ngày gần nhất) — MỘT điểm xấu đơn lẻ KHÔNG cảnh báo.
   - Chuỗi <20 điểm: dùng SMA(n) hiện có, ghi rõ "chưa đủ 20 điểm, sơ bộ".
2. **Báo cáo xem lại** (Markdown, ghi ra `local_cases/` — tuyệt đối không ghi
   kho tri thức): bảng xếp hạng câu bị chê nhiều nhất, danh sách trend alert
   (câu có xu hướng xấu đi), chủ đề chê tăng, đề xuất sửa gốc theo thứ tự ưu tiên.
3. **Chế độ chạy**: hàm `run_periodic_review()` + entry CLI đơn giản
   (`python -m ...` hoặc hàm gọi từ app sau cờ). Mặc định KHÔNG tự chạy ngầm —
   chỉ chạy khi được gọi.
4. **Cờ tính năng**: tái dùng cờ `AIOS_FEATURE_FEEDBACK_LOOP_HOME` (mặc định
   TẮT). Khi cờ tắt, module mới không làm gì.
5. Code tương thích Python 3.11 (máy nhà), tránh syntax 3.12+.

## Tiêu chí nghiệm thu

- SMA(20)/σ tính đúng trên chuỗi giả lập biết trước (vd SMA(20) của 20 số
  0..19 = 9.5).
- Anomaly: 1 điểm lệch xa đơn lẻ → KHÔNG cảnh báo; 3 điểm liên tiếp lệch xa →
  CÓ cảnh báo (test cả hai trường hợp).
- Báo cáo review mẫu chạy thật trên dữ liệu giả lập nhiều máy: có bảng xếp
  hạng câu chê, trend alert, đề xuất sửa gốc có thứ tự ưu tiên.
- `compileall` sạch, test vé mới ≥8 test xanh, hồi quy 12 test
  FEEDBACK-LOOP-HOME vẫn xanh, `cli audit` PASS, import app OK.
  (Bộ toàn kho nặng: không bắt buộc — báo trung thực như vé trước.)
- Không ghi index/kho tri thức (chỉ đọc/ghi `local_cases/`), không merge
  `main`, không secret.
- Báo cáo `feedback-review-home.md` có số đo demo vòng xem lại chạy thật.

## Rào an toàn (bắt buộc)

- Chỉ đọc/ghi trong `local_cases/` (đã gitignore). Cấm chạm index, kho tri
  thức, ổ D.
- Không merge `main`. Commit riêng trên nhánh `phieu-viec/rag-fix1`.
- Không secret/khóa nào trong code hay báo cáo.
- Heartbeat: nếu vé chạy quá 30 phút, ghi mốc tiến độ vào `trang-thai.md`
  tối thiểu 15 phút/lần.
