# Vé ROUND4B-DOUBLE-BUBBLE [NHÀ] — Sửa lỗi 2 bubble khi hỏi kèm ảnh

> Vé CODE (thợ OMP máy nhà implement + verify app thật). Phát hành bằng cách
> copy file này vào `prompt.md`, reset `trang-thai.md` về `moi`.
> Role OMP gợi ý: DEFAULT (code + verify). Không cần PLAN (thiết kế đã chốt).

## Bối cảnh
- Vòng 4 UX-ATTACH-SOURCES (one-shot-inline, commit c317d84) CHƯA ĐẠT:
  4 điểm Phần B đều đạt, nhưng một lần gửi câu hỏi kèm ảnh tạo **hai bubble**
  (bubble 1 = câu hỏi + khối OCR đúng thiết kế; bubble 2 = câu thô trùng lặp).
  Tái hiện 2/2, bằng chứng: ảnh 23, `messages.jsonl`, `traces.jsonl` trong
  `docs/phieu-viec/ket-qua/ux-attach-sources.md` (mục "Lỗi mới").

## Chẩn đoán đã xác nhận (Muse audit độc lập)
- Composer (`workspace_chat_app.py` ~dòng 4952) lưu bubble user với nội dung
  **đã gộp OCR** (`q_text` = câu thô + khối OCR).
- Tầng cầu nối (`antigravity_bridge.py` dòng 600)
  `_get_or_create_user_message(conversation_id, user_raw_input)` chỉ tái dùng
  tin nhắn cuối khi nội dung khớp **chính xác** câu thô → không khớp bản đã
  gộp → tự tạo thêm một tin nhắn mới bằng câu thô → bubble thứ hai. Trace còn
  gán nhầm `user_message_id` vào bubble trơn này.

## Hướng sửa CHỐT (Muse quyết — cấm làm khác)
- **Truyền thẳng id tin nhắn đã lưu xuống tầng cầu nối.** Không dùng so khớp
  tiền tố (đề xuất (a) của OMP bị loại: hai câu hỏi liên tiếp giống nhau, câu
  sau không kèm ảnh, sẽ bị nhận nhầm vào bubble đã gộp OCR của câu trước).
- Cụ thể:
  1. Composer khi submit: truyền thêm `user_message_id=user_msg.id` vào
     `_run_chat_turn_async` (param mới, optional).
  2. `_run_chat_turn_async` (dòng 1063) nhận param và chuyển tiếp vào
     `route_workspace_chat_submission` (dòng 987, param mới optional).
  3. `_get_or_create_user_message` thêm param optional `reuse_message_id`:
     nếu có và tìm thấy tin nhắn đó trong cuộc trò chuyện → trả về luôn,
     không tạo mới; các đường gọi cũ không truyền id giữ nguyên hành vi
     (4 điểm gọi dòng 1113/1199/1333/1419 chỉ đổi khi có id).
- Không đổi thiết kế one-shot-inline: bubble 1 vẫn hiện câu hỏi + khối OCR
  như đã verify ở vòng 4.

## Ràng buộc cứng
- Python 3.11. Không đụng index (SHA các khối giữ nguyên).
- Test cũ pass; bổ sung test: đã có id → không tạo tin nhắn mới;
  không id → hành vi cũ.

## Nghiệm thu (app thật)
1. Gửi 1 câu hỏi kèm ảnh → đúng **1 bubble** (câu hỏi + khối OCR). Làm 2 lần độc lập.
2. Câu hỏi không kèm ảnh → 1 bubble như cũ.
3. Hai câu hỏi liên tiếp giống nhau (câu 2 không kèm ảnh) → 2 bubble riêng, không gộp nhầm.
4. Trace `user_message_id` trỏ đúng bubble đã gộp OCR.
5. Bằng chứng: ảnh chụp + đoạn `messages.jsonl`/`traces.jsonl` liên quan.
