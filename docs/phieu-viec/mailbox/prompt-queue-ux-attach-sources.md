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
