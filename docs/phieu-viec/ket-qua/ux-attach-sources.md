# Báo cáo UX-ATTACH-SOURCES — máy nhà, vòng verify lại

- Trạng thái: **chưa đạt**, chuyển `cho-muse`. Không merge `main`. Không sửa code.
- Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`. Mã kiểm: `26a71c2` (HEAD khi nhận vé `e6aeac8`).
- Ngày: 2026-10-04, khoảng 07:36–07:52 +07.
- Cổng gate: watcher `LAUNCH 1/4` lúc 07:34:30 (`launchStallCount=1`). Điều kiện mở đã tới (mã `26a71c2` có trên nhánh). Không dùng nhánh 4 lần watcher.
- Sổ thử: `UX-ATTACH-SOURCES` (`NB-19FB596C`), cuộc mới `CONV-77E1085A`. Không đụng sổ công ty.

## Kết luận

Nhãn expander đã đúng một dấu `＋`. Câu hỏi kèm ảnh **vẫn không chạy** trên lane Gemini. App không còn chặn bằng câu “không được gửi ảnh”, nhưng OCR không đọc được ảnh, không tạo nguồn tạm, rồi dừng ở `Thiếu ngữ cảnh` / `Chưa có nguồn nào`. Không có câu trả lời, không có chữ `MA-UX-7741`.

## 3 điểm verify lại

1. **Chưa đạt.** Lane đúng `Đang dùng: Gemini qua cầu nối (tự động)`, cầu nối xanh. Đính `anh-mot-lan.png` (chữ rõ `MA-UX-7741`) rồi bấm Hỏi với câu `lỗi này là gì?`. App hiện một dòng: `Chưa đọc được nội dung ảnh (có thể thiếu bộ đọc OCR hoặc ảnh mờ). Câu hỏi vẫn được gửi dựa trên chữ bạn nhập.` Ngay sau đó khung chat vẫn là `Hãy bắt đầu cuộc trò chuyện...` và banner đỏ `Thiếu ngữ cảnh` / `Chưa có nguồn nào`. Không có tin nhắn user, không có câu trả lời, không có `MA-UX-7741`. Ảnh `06-thumbnail.png`, `07-cau1-ocr-fail.png`.
2. **Chưa kiểm được.** Thumbnail `anh-mot-lan.png` và nút `Bỏ ảnh` còn trong composer sau lần bấm Hỏi. Câu 1 không được gửi nên không có câu 2 để xem ảnh cũ có bị dùng lại không.
3. **Đạt.** Thanh bên hiện đúng `＋ Thêm nguồn` (một dấu cộng, đúng chữ trong i18n). Bên dưới là `📚 Nguồn tham khảo`. Không còn `＋ ＋ Thêm nguồn`. Ảnh `05b-sidebar-nhan.png`.

## Vì sao OCR fail

Chạy cùng hàm đọc ảnh của app trên đúng file thử, không qua giao diện:

- trạng thái: `unsupported_no_local_ocr`
- cảnh báo: `rapidocr_unavailable; paddleocr_unavailable; local OCR unavailable: tesseract executable not found; set AIOS_TESSERACT_CMD or add Tesseract to PATH`
- chữ đọc được: rỗng

`AIOS_TESSERACT_CMD` trống. `tesseract` không có trên PATH, không thấy ở `C:\Program Files\Tesseract-OCR`. Máy nhà không có bộ đọc chữ cho ảnh.

Hệ quả trên app: lượt OCR thất bại không tăng `wsc_upload_version`, không tạo nguồn tạm, rồi nhánh `not enabled_selections` gọi rerun. Câu hỏi không tới lane Gemini, dù dòng cảnh báo nói câu hỏi vẫn được gửi.

## Kho tri thức

| Mục | Trước | Sau |
| --- | --- | --- |
| File | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng file |
| Byte | 2.942.201.856 | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA |

Không ghi index production. Không merge `main`.

## Ảnh

- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/05b-sidebar-nhan.png` — nhãn một dấu `＋`
- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/06-thumbnail.png` — ảnh đã vào composer, lane Gemini tự động
- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/07-cau1-ocr-fail.png` — sau khi hỏi: chưa có hội thoại, `Thiếu ngữ cảnh`

Ảnh vòng trước (`01`–`04`) giữ nguyên để đối chiếu.
