# Báo cáo UX-ATTACH-SOURCES — vòng 3, máy nhà

- Trạng thái: **chưa đạt**, chuyển `cho-muse`. Không merge `main`. Không sửa code.
- Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`. Mã kiểm: `8e5e59b`.
- Ngày: 2026-10-04, khoảng 08:03–08:25 +07.
- Cổng gate: watcher `LAUNCH 1/4` lúc 08:02:06 (`launchStallCount=1`). Điều kiện mở đã tới (mã `8e5e59b` có trên nhánh). Không dùng nhánh 4 lần watcher.
- Sổ thử: `UX-ATTACH-SOURCES` (`NB-19FB596C`). Câu hỏi kèm ảnh chạy trên cuộc `CONV-868EBB6B`. Không đụng sổ công ty.

## Kết luận

Phần A đạt: Tesseract đã cài đúng chỗ, có tiếng Việt. Điểm 1 và điểm 3 của Phần B đạt. Điểm 2 chưa đạt: sau câu 1, thumbnail đã biến, nhưng câu 2 không đính kèm vẫn dùng lại nội dung ảnh cũ.

## Phần A — cài Tesseract

- File cài: `tesseract-ocr-w64-setup-5.5.3.20260724.exe` (đúng bản trên wiki UB Mannheim).
- Cài im lặng vào `C:\Program Files\Tesseract-OCR\` (cần quyền quản trị, đã chạy được).
- `tesseract --version` ra `tesseract v5.5.3.20260724`.
- Gói tiếng Việt: bộ cài im lặng không có ô tick ngôn ngữ, nên tải `vie.traineddata` (kho tessdata chuẩn) vào `tessdata`, đúng cách B trên wiki. `tesseract --list-langs` có `vie`.
- Đã thêm thư mục cài vào PATH của user để lệnh `tesseract` chạy được trong cmd mới.

## Phần B — 3 điểm trên app thật

App mở lại bằng cùng bộ biến của `RUN_AIOS_WORKSPACE_CHAT.bat`, cổng 8501. Lane đúng `Đang dùng: Gemini qua cầu nối (tự động)`, cầu nối xanh.

1. **Đạt.** Đính ảnh lỗi thật `07-cau1-ocr-fail.png` (ảnh chụp màn hình app vòng trước, có chữ, không phải ảnh giả) rồi hỏi `lỗi này là gì?`. Câu hỏi chạy, không bị chặn. Câu trả lời trên Gemini đọc được chữ trong ảnh: trích `Thiếu ngữ cảnh` và `Chưa có nguồn nào`, có tên file ảnh. Ảnh `11-cau1-doc-duoc-chu.png`.
2. **Chưa đạt.** Thumbnail và nút `Bỏ ảnh` đã biến khỏi composer sau câu 1 (ảnh `12-composer-sau-cau1.png`). Hỏi tiếp câu không đính kèm: `Trong anh vua roi co cum Thieu ngu canh khong? Chi tra loi co hoac khong.` Câu trả lời vẫn là `Có`, huy hiệu vẫn `Nguồn gửi cùng câu hỏi: 2`, gợi ý vẫn gọi tên `07-cau1-ocr-fail.png`, thanh bên vẫn còn nguồn tạm đó đang bật. Nguồn một lần không tự tắt. Ảnh `14-cau2-van-dung-anh.png`, `15-cau2-goi-y-van-anh.png`.
3. **Đạt.** Expander thanh bên đúng một dấu `＋ Thêm nguồn`, bên dưới là `📚 Nguồn tham khảo`. Không còn `＋ ＋`. Ảnh `13-sidebar-mot-dau.png`.

## Ghi chú thêm, không phải lỗi cài đặt

App vẫn OCR bằng ngôn ngữ mặc định `eng` (không tự chọn `vie` dù gói đã cài). Bản chữ lưu trong nguồn tạm bị mất dấu. Gemini vẫn đọc lại được cụm `Thiếu ngữ cảnh`. Muốn ảnh tiếng Việt sạch hơn, Muse cần cho app gọi `vie+eng` (biến `AIOS_OCR_LANG` đã có sẵn, launcher thường không đặt).

Câu trả lời câu 1 còn kéo thêm một sự kiện log điều tra khác ngoài ảnh. Không chép nội dung log đó vào báo cáo này.

## Kho tri thức

| Mục | Trước | Sau |
| --- | --- | --- |
| File | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng file |
| Byte | 2.942.201.856 | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA |

Không ghi index production bằng tay. Không merge `main`.

## Ảnh vòng này

- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/09-thumbnail-anh-loi-that.png` — ảnh lỗi đã vào khung đính kèm
- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/10-truoc-khi-hoi.png` — câu hỏi trên lane Gemini tự động
- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/11-cau1-doc-duoc-chu.png` — câu trả lời đọc được `Thiếu ngữ cảnh`
- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/12-composer-sau-cau1.png` — composer sau câu 1, không còn thumbnail
- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/13-sidebar-mot-dau.png` — một dấu `＋`
- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/14-cau2-van-dung-anh.png` — câu 2 vẫn trả lời `Có`
- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/15-cau2-goi-y-van-anh.png` — nguồn ảnh vẫn còn trong sổ

Ảnh vòng trước (`01`–`07`) giữ để đối chiếu.
