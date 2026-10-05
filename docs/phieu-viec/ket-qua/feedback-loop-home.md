# Báo cáo vé FEEDBACK-LOOP-HOME — nút like/dislike + máy tự học thói quen

- Ngày: 2026-10-06 (giờ máy khi ghi trạng thái).
- Vé: `FEEDBACK-LOOP-HOME` — vòng lặp phản hồi đầy đủ + máy tự học thói quen, không tài khoản.
- Prompt: `docs/phieu-viec/mailbox/prompt.md`.
- Nhánh: `phieu-viec/rag-fix1`. Không merge `main`.
- Trạng thái: đã code + verify xong, chờ duyệt.

## 1. Khảo sát code sẵn có (tái dùng, không viết lại)

- `src/aios_habit/answer_feedback.py`: phản hồi tại chỗ (thích / chưa thích + lý do bắt buộc khi chê), lưu `local_cases/answer_feedback.jsonl`, không ghi kho tri thức. Vé này giữ nguyên API cũ, chỉ thêm 2 trường mới `device_id` + `topic` (bản ghi cũ không có 2 trường này vẫn đọc được, test cũ vẫn xanh).
- `src/aios_habit/workspace_chat_ui.py` (`render_answer_feedback_row`, khoảng dòng 360): hàng phản hồi nhỏ dưới mỗi câu trả lời (thumbs + ô lý do + nút gửi). Vé này thêm nhánh mới sau cờ riêng: chê thì chọn lý do có sẵn (radio) + ô tự ghi thêm, vẫn trong bong bóng chat, không thêm đống nút toolbar.
- `src/aios_habit/index_domain.py` (`detect_domain_from_question`): phân loại chủ đề câu hỏi (lsu / dieu_tra_loi / mom) có sẵn từ vé tách kho. Vé này tái dùng để gắn chủ đề cho mỗi feedback, kèm ngưỡng tin cậy dưới 0,4 thì ghi `chua_phan_loai` (câu chào / cảm ơn không bị gán nhầm vào Điều tra lỗi).
- `src/aios_habit/workspace_chat_store.py` (`load_all_messages`): lịch sử chat đã có trên đĩa là một phần trí nhớ, tái dùng làm đầu vào hồ sơ thói quen.
- An toàn dữ liệu: `local_cases/` đã nằm trong `.gitignore` (đã kiểm); mã máy + feedback chỉ ở local, không commit, không đưa lên mây.

## 2. Phương án đã làm (mở rộng module cũ, không thay luồng cũ)

- Mới `src/aios_habit/feedback_loop_home.py` (~450 dòng): mã máy ngẫu nhiên (`local_cases/device_id`, dạng `may-` + hex, tạo 1 lần mỗi máy) + gắn chủ đề + ghi feedback kèm mã máy/chủ đề + metric tỉ lệ chê theo câu / theo chủ đề + đánh dấu câu bị chê từ 2 máy trở lên để sửa gốc + hồ sơ thói quen từng máy (chủ đề hay hỏi, độ dài ưa thích, giờ hay dùng) + gợi ý điều chỉnh (hay hỏi LSU buổi sáng → ưu tiên đống LSU; hay chê dài → trả lời súc tích cho máy đó). Cờ riêng `AIOS_FEATURE_FEEDBACK_LOOP_HOME`, mặc định TẮT.
- Sửa `src/aios_habit/answer_feedback.py` (+6 dòng: 2 tham số `device_id`/`topic` + 2 trường trong bản ghi). Không đổi hành vi cũ.
- Sửa `src/aios_habit/workspace_chat_ui.py` (+~60 dòng trong `render_answer_feedback_row`): khi cờ bật, like ghi kèm mã máy/chủ đề; dislike hiện radio 5 lý do có sẵn + ô tự ghi thêm (chọn "Lý do khác" thì bắt buộc ghi thêm, các mục khác thì ghi thêm là tùy chọn). Khi cờ tắt, luồng cũ nguyên vẹn.
- Sửa `src/aios_habit/i18n.py` (+21 dòng: 7 khóa mới × 3 miền `vi`/`ja`/`zh-CN`, kiểm parity đạt).
- Mới `tests/test_feedback_loop_home.py` (12 test: cờ TẮT mặc định, bật/tắt override, mã máy ổn định, ghi kèm mã máy/chủ đề, chê thiếu lý do bị từ chối, phân loại chủ đề + câu chào về `chua_phan_loai`, chuẩn hóa khóa câu hỏi, metric + đánh dấu sửa gốc trên dữ liệu giả lập nhiều máy, gợi ý xem lại, hồ sơ thói quen LSU buổi sáng + súc tích, thiếu mã máy báo lỗi, API cũ vẫn chạy).

## 3. Đối chiếu tiêu chí nghiệm thu trong prompt

- Nút like/dislike + lý do dưới câu trả lời, chữ tiếng Việt, không vỡ layout chat: đạt — tái dùng hàng feedback cũ trong bong bóng chat, thêm radio lý do + ô tự ghi sau cờ riêng, toàn bộ chữ qua `t()`.
- Feedback ghi đúng `local_cases/`, có mã máy, không lọt kho tri thức: đạt — `device_id` + `topic` nằm trong `answer_feedback.jsonl` ở `local_cases/` (đã ignore), không chạm index/kho chính; audit PASS; grep không thấy ghi index trong diff vé.
- Test đủ 3 nhóm (ghi feedback, metric, học thói quen, dữ liệu giả lập nhiều máy): đạt — 12/12 test vé xanh (xem mục 2).
- `compileall` sạch, `pytest` đạt, `cli audit` PASS, import app OK: đạt một phần trung thực — `compileall src tests` sạch; test vé 12/12; hồi quy liên quan 61 đạt/2 lỗi i18n cũ có sẵn (đã đối chiếu cây sạch bằng stash: cùng 2 lỗi ở dòng cũ `File nhị phân…` và `module_root`, diff vé không chạm các dòng đó); `cli audit` PASS (`status: PASS`); `import workspace_chat_app` OK. Bộ toàn kho `pytest -q` chưa chạy (nặng, quá 10 phút trên máy này — không báo đạt cho bộ toàn kho).
- Không nút thừa, không ghi index, không merge `main`, không secret: đạt — diff vé 6 file (lõi mới + 2 sửa nhỏ + chữ + test + báo cáo + trạng thái); không nút toolbar mới; không ghi index; không merge `main`; secret duy nhất là `secrets.token_hex` tạo mã máy local (không phải khóa).
- Báo cáo có số đo demo vòng lặp chạy thật: đạt — xem mục 4.

## 4. Số đo demo vòng lặp chạy thật (dữ liệu giả lập, môi trường cách ly)

- Gieo 5 feedback (3 máy giả lập `may-aaa`/`may-bbb`/`may-ccc`, 2 câu Điều tra lỗi + 3 câu LSU, 1 câu LSU buổi sáng chê dài): metric tổng 5 lượt, 1 khen / 4 chê, tỉ lệ chê 0,8.
- Câu bị chê nhiều nhất: `loi jam4709 ket giay la gi?` — 2 lượt chê từ 2 máy, tỉ lệ chê 1,0 → lọt danh sách `flag_answers_for_fix` (sửa gốc).
- Theo chủ đề: Điều tra lỗi 2/2 chê (1,0), LSU 2/3 chê (0,667).
- Gợi ý xem lại: "Tỉ lệ chê trên 30%..." + "Có 1 câu bị chê từ 2 máy trở lên...".
- Hồ sơ máy `may-aaa` (4 feedback + 1 câu lịch sử buổi sáng): chủ đề hay hỏi LSU (4/5), độ dài ưa thích `suc_tich`, giờ hay dùng `buoi_sang`, gợi ý: "Máy này hay hỏi LSU buổi sáng → ưu tiên tìm đống LSU khi máy hỏi buổi sáng." + "Máy này hay chê dài → trả lời súc tích hơn cho máy này."; `device_adjustment` cho `uu_tien_kho=lsu`, `do_dai=suc_tich`.

## 5. Cách dùng và hoàn tác

- Bật thử: đặt `AIOS_FEATURE_FEEDBACK_LOOP_HOME=1`, mở khung chat, chấm thích/chê dưới câu trả lời (chê thì chọn lý do + ghi thêm nếu cần).
- Xem số liệu: đọc `local_cases/answer_feedback.jsonl` rồi chạy `compute_loop_metrics`, đọc `review_recommendations`; câu cần sửa gốc: `flag_answers_for_fix`; hồ sơ từng máy: `build_device_profile(mã_máy)`.
- Hoàn tác: tắt cờ là về luồng feedback cũ (ô lý do tự do, không mã máy/chủ đề mới), dữ liệu cũ còn nguyên vì chỉ thêm trường.

## 6. Đề nghị duyệt vé

- Vé đạt ở mức chờ duyệt: đủ nút + lý do chọn sẵn trong chat + store mã máy local + metric theo câu/chủ đề + đánh dấu sửa gốc + học thói quen từng máy + hồ sơ dùng lịch sử chat có sẵn, đúng rào (cờ TẮT, chỉ ghi `local_cases/`, không nhập kho chính, không merge `main`).
- Nhờ Muse review độc lập rồi phát hành vé tiếp theo.
