# VÉ: FEEDBACK-DOGFOOD-HOME (chạy thử vòng lặp feedback trên dữ liệu thật máy nhà)

- Mã vé: `FEEDBACK-DOGFOOD-HOME`
- Role OMP gợi ý: DEFAULT (nhẹ: chạy app thật + tạo feedback + chạy review, không nặng)
- Máy: nhà h410asrock
- Báo cáo: `docs/phieu-viec/ket-qua/feedback-dogfood-home.md`

## Bối cảnh

2 vé vòng lặp cải thiện liên tục đều đã ĐẠT (verdict Muse 06/10):
điểm 1+2 `FEEDBACK-LOOP-HOME` (nút like/dislike + lý do chê + store mã máy
+ metric + học thói quen) và điểm 3 `FEEDBACK-REVIEW-HOME` (SMA(20) + σ +
cảnh báo xu hướng ≥3 điểm bất thường, 1 điểm xấu đơn lẻ im lặng).
Cả hai mới chỉ chạy trên dữ liệu giả lập; cờ
`AIOS_FEATURE_FEEDBACK_LOOP_HOME` đang TẮT mặc định (fail-closed).
Vé này "ăn thử món mình nấu": bật cờ THEO PHIÊN, tạo feedback THẬT trên app
thật, chạy vòng xem lại trên `local_cases/` THẬT.

## Việc cần làm

1. Bật cờ theo phiên: chạy app với `AIOS_FEATURE_FEEDBACK_LOOP_HOME=1`
   (set env var khi chạy — KHÔNG sửa default trong code).
2. Tạo ≥30 lượt feedback thật qua đường UI thật (bấm tay trên app Streamlit,
   hoặc gọi đúng handler mà nút like/dislike gọi): ít nhất 2 câu hỏi khác
   nhau; trong đó 1 câu chê thật nhiều lần (≥10 lượt chê kèm lý do, có ít
   nhất 1 lý do tự ghi tay). Xác nhận `local_cases/answer_feedback.jsonl`
   có `device_id` là mã máy thật này.
3. Chạy metric `compute_loop_metrics` trên dữ liệu thật → bảng xếp hạng
   câu/chủ đề bị chê THẬT (số đo thật).
4. Chạy `python -m aios_habit.feedback_review_home --dau-ra local_cases/feedback_review_dogfood.md`
   trên dữ liệu thật → báo cáo review THẬT. Ghi rõ chuỗi dữ liệu có bao
   nhiêu ngày; nếu <20 điểm thì báo cáo phải ghi "chưa đủ 20 điểm, sơ bộ"
   và KHÔNG được có cảnh báo giả từ dữ liệu ít.
5. Tắt cờ sau khi xong (trở về TẮT mặc định). Dữ liệu feedback thật giữ lại
   trong `local_cases/` (đã gitignore, không commit).

## Tiêu chí nghiệm thu

- ≥30 lượt feedback thật, store JSONL có device_id máy thật, ≥1 lý do chê tự ghi.
- Bảng xếp hạng metric thật (câu/chủ đề) có số đo thật trong báo cáo.
- Báo cáo review thật sinh ra từ `local_cases/` thật; không cảnh báo giả
  khi chuỗi ngắn; ghi "sơ bộ" đúng quy ước.
- Kiểm lại: cờ tắt → module không làm gì (exit 0, không ghi file).
- `compileall` sạch, `cli audit` PASS, import app OK.
- Không ghi index/kho tri thức (chỉ đọc/ghi `local_cases/`), không merge
  `main`, không secret, không đổi default cờ trong code.

## Rào an toàn (bắt buộc)

- Chỉ đọc/ghi trong `local_cases/` (đã gitignore). Cấm chạm index, kho tri
  thức, ổ D.
- Không merge `main`. Commit riêng trên nhánh `phieu-viec/rag-fix1`.
- Không secret/khóa nào trong code hay báo cáo.
- Code tương thích Python 3.11 (máy nhà), tránh syntax 3.12+.
- Heartbeat: nếu vé chạy quá 30 phút, ghi mốc tiến độ vào `trang-thai.md`
  tối thiểu 15 phút/lần.
