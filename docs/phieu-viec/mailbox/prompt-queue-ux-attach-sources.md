# Vé: UX-ATTACH-SOURCES — phân định rõ "ảnh đính kèm một lần" và "nguồn tham khảo lâu dài"

Lane: [VM] Muse code+test xong (commit `0d68d383`) → [NHÀ] OMP verify bằng mắt trên app thật. Không merge `main`; code tương thích Python 3.11; không force-push.

## Bối cảnh (user phản hồi 2026-10-04 ~06:20 +07, kèm ảnh chụp màn hình)

User bối rối vì có 2 chỗ "đính kèm" trông giống nhau nhưng khác nhau:
1. Trong khung chat: nút "Đính kèm" — thực chất là **ảnh dùng một lần cho đúng câu hỏi đó** (chụp màn hình lỗi rồi hỏi, xong là hết, không lưu).
2. Dưới khung chat: expander "Thêm tài liệu/ảnh để AI tham khảo" — thực chất là **nạp nguồn tri thức lâu dài** (dán biên bản, upload spec, import thư mục; lưu vào sổ, dùng cho mọi câu hỏi sau, bật/tắt từng nguồn được).

User duyệt phương án: khung chat gọn kiểu Antigravity/Cursor (1 ô nhập + 1 nút [+] + nút gửi, ảnh hiện thumbnail trong khung), mục thêm nguồn dời ra panel riêng bên cạnh kiểu NotebookLM.

## Việc Muse làm trên VM (xong, commit `0d68d383`)

1. Nút đính kèm trong composer đổi nhãn thành "🖼️ Ảnh cho câu hỏi này"; help text nói rõ: ảnh chỉ dùng cho ĐÚNG câu hỏi này, gửi xong là hết, không lưu lại; muốn lưu lâu dài thì thêm vào "Nguồn tham khảo" ở thanh bên.
2. Xóa expander "➕ Thêm tài liệu/ảnh để AI tham khảo" khỏi dưới khung chat.
3. Thanh bên: mục "📚 Nguồn tham khảo" gồm expander "＋ Thêm nguồn" (đủ 4 tab: dán nhanh, văn bản dài, tải file, nhập thư mục — dời nguyên từ dưới khung chat lên) + danh sách nguồn đầy đủ kèm công tắc bật/tắt từng nguồn (dùng lại `render_source_library`, trước đây chỉ hiện tóm tắt số lượng).
4. i18n: `source_library` → "Nguồn tham khảo" (vi/ja/zh đồng bộ key mới `add_source_button`).
5. Test: 4 test contract mới trong `tests/test_workspace_chat_composer_ui.py`; 2 test cũ cập nhật theo thiết kế mới; toàn bộ suite workspace_chat không có lỗi mới (lỗi còn lại đều có sẵn từ trước).

## Việc OMP verify [NHÀ] — kiểm bằng mắt, chụp màn hình

1. Pull `0d68d383`, restart app (Streamlit cổng 8501 như mọi khi).
2. **Composer:** nút đính kèm hiện "🖼️ Ảnh cho câu hỏi này"; bấm vào đọc help — phải hiểu ngay là ảnh một lần, không lưu. Đính kèm 1 ảnh → thumbnail hiện trong khung chat kèm nút gỡ; hỏi 1 câu → ảnh được dùng; hỏi tiếp câu thứ 2 KHÔNG đính kèm → ảnh không bị dùng lại.
3. **Dưới khung chat:** không còn expander "Thêm tài liệu/ảnh để AI tham khảo".
4. **Thanh bên:** thấy "📚 Nguồn tham khảo" với expander "＋ Thêm nguồn" (mở ra đủ 4 tab, thử dán 1 đoạn văn bản → thêm thành công) và danh sách nguồn có công tắc bật/tắt từng nguồn. Tắt 1 nguồn → hỏi câu liên quan, câu trả lời không dùng nguồn đó; bật lại → dùng.
5. Chụp màn hình: (a) composer đang có thumbnail ảnh đính kèm, (b) panel "Nguồn tham khảo" ở thanh bên.
6. Không ghi index production; SHA kho tri thức không đổi (vé này chỉ đụng UI).

## Tiêu chí ĐẠT

- Cả 5 điểm verify trên đều đúng trên app thật, có ảnh chụp màn hình đính kèm báo cáo.
- Không còn chỗ nào khiến user nhầm giữa "ảnh một lần" và "nguồn lâu dài".
- Báo cáo `docs/phieu-viec/ket-qua/ux-attach-sources.md` + `xong-cho-duyet`.
- CHƯA ĐẠT → ghi rõ điểm nào sai + ảnh chụp, đặt `cho-muse`.

## Ràng buộc

- Đây là vé UI-verify, không phải vé code: OMP không sửa code trong vé này. Lỗi UI → báo `cho-muse`, Muse sửa trên VM.
- Phân biệt với vé UX-CHAT-CORE trước đây (xong 03/10): vé này chỉ về phân định đính kèm/nguồn, không đụng logic hỏi đáp.

## Sửa sau `cho-muse` (Muse fix trên VM, commit `26a71c2`, đã push)

Nguyên nhân gốc OMP bắt được: app chặn câu hỏi ngay khi thấy ảnh đính kèm, TRƯỚC cả khi ảnh được đọc thành chữ — trong khi thiết kế đúng là ảnh luôn được OCR thành nguồn chữ trước khi tới lane AI (mọi lane đều đọc được chữ). Ba chỗ sửa:

1. **Hỏi kèm ảnh không còn bị chặn:** bỏ block cứng ở ask flow; ảnh đính kèm được OCR thành nguồn tạm rồi câu hỏi chạy bình thường trên mọi lane (kể cả Gemini qua cầu nối). Guard chặn byte ảnh thô ở tầng cầu nối vẫn giữ nguyên (fail-closed). Nếu OCR không đọc được ảnh: báo nhẹ một dòng, câu hỏi vẫn gửi theo chữ đã nhập.
2. **Vòng đời một lần đúng nghĩa:** sau khi gửi, ảnh dán từ clipboard cũng bị xóa khỏi composer (trước đây chỉ reset đường tải file); nguồn tạm sinh ra từ ảnh được ghi nhớ và TỰ TẮT khi câu hỏi tiếp theo được gửi — câu sau không đính kèm thì không dùng lại nội dung ảnh.
3. **Nhãn expander:** hết `＋ ＋ Thêm nguồn` (dấu ＋ chỉ còn một, nằm trong i18n).

## Verify lại [NHÀ] (chỉ 3 điểm còn lại)

1. Pull `26a71c2`, restart app. Đính kèm ảnh `MA-UX-7741` + hỏi "lỗi này là gì?" trên lane Gemini tự động → câu hỏi CHẠY (không còn bị chặn), câu trả lời đọc được chữ trong ảnh.
2. Hỏi tiếp câu thứ 2 KHÔNG đính kèm → câu trả lời không dùng nội dung ảnh cũ; thumbnail ảnh đã biến khỏi composer sau câu 1.
3. Thanh bên: expander hiện đúng `＋ Thêm nguồn` (một dấu cộng).
4. SHA kho `tri_thuc` không đổi (vé này chỉ đụng UI + luồng hỏi).
