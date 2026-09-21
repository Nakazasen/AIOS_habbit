# Workspace Chat Composer UI Contract

## Default state

- Shows one compact composer with a collapsed-label multiline input, an accessible attachment action, and an explicit send action.
- Does not render the image picker until attachment is requested.
- Keeps the current Vietnamese-first placeholder and send label.

## Attachment state

- Shows the existing image picker and retains PNG, JPG, JPEG, WEBP and BMP restrictions.
- Keeps the existing help text and upload-version reset behavior.
- Does not send or persist data until the explicit send action is used.

## Submit state

- Text-only, image-only, and text-plus-image submissions follow the existing processing route.
- Empty text with no image produces the existing guidance.
- Ctrl+Enter is exposed as a submit shortcut; native focus order remains available.

## Responsive state

- At 360 px and above, text input, attachment and send controls remain visible and non-overlapping.
- Secondary search controls may wrap or disclose below the primary composer row.

## Trạng thái thân thiện cho người không chuyên (làm giàu 2026-09-21)

- Composer luôn có nhãn tiếng Việt nhìn thấy được cho ô nhập, thao tác đính kèm và thao tác gửi; không dùng gợi ý mờ thay cho nhãn.
- Nút gửi và nút dừng nằm trong composer, tối thiểu 44 px, cách nhau tối thiểu 8 px; lỗi và hướng dẫn hiện ngay cạnh trường vừa thao tác.
- Khi chờ tài liệu, nút gửi đổi thành nút dừng ngay trong composer; bấm là hủy được, không tạo lượt gửi trùng.

## Trạng thái thẻ JIG, biểu đồ và mail (làm giàu 2026-09-21)

- Thẻ JIG mở đầu bằng một câu kết luận tiếng Việt: Bình thường, Cần kiểm tra, hoặc Nguy cơ, kèm tên JIG, thông số vi phạm và việc cần làm tiếp.
- Biểu đồ đánh dấu điểm bất thường bằng hình và chữ kèm theo, kèm bảng số gọn; không phân biệt trạng thái chỉ bằng màu sắc.
- Luồng trực tiếp có nút Tạm dừng/Tiếp tục; khi tạm dừng, dòng chat ngừng cập nhật nhưng dữ liệu vẫn ghi ngầm.
- Mail cảnh báo luôn hiện màn hình duyệt nội dung và biểu đồ trước khi gửi; chỉ gửi khi người dùng đồng ý.
