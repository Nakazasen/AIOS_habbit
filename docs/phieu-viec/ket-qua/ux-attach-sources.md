# Báo cáo UX-ATTACH-SOURCES — máy nhà

- Trạng thái: **chưa đạt**, chuyển `cho-muse`. Không merge `main`. Không sửa code.
- Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`. Mã UI kiểm: `0d68d383`.
- Ngày: 2026-10-04, khoảng 07:01–07:21 +07.
- Cổng gate: watcher `LAUNCH 1/4` lúc 07:00:28 (`launchStallCount=1`). Điều kiện mở đã tới (mã `0d68d383` có trên nhánh). Không dùng nhánh 4 lần watcher.

## Kết luận

Nhãn, help, thumbnail và panel nguồn đúng hướng. **Không hỏi được câu có ảnh** vì lane tự động là Gemini và app chặn gửi ảnh. Vì vậy chưa đủ 5 điểm verify.

## Điểm đã thấy trên app thật

App mở lại cổng `8501`, cùng biến `RUN_AIOS_WORKSPACE_CHAT.bat` (cờ định tuyến bật). Sổ thử mới `UX-ATTACH-SOURCES` (`NB-19FB596C`), cuộc `CONV-D7ACE777`. Không đụng sổ công ty.

1. Nút composer hiện `🖼️ Ảnh cho câu hỏi này`. Bấm vào đọc được help: ảnh chỉ dùng cho đúng câu hỏi này, gửi xong là hết, không lưu; muốn lưu lâu thì thêm vào Nguồn tham khảo ở thanh bên. Ảnh `01-help-anh-mot-lan.png`.
2. Đính kèm `anh-mot-lan.png` (ảnh giả, chữ `MA-UX-7741`) thì có thumbnail rộng 78px, chú thích tên file và nút `Bỏ ảnh`. Ảnh `02-thumbnail-bi-chan.png`.
3. Dưới khung chat **không còn** expander `Thêm tài liệu/ảnh để AI tham khảo`.
4. Thanh bên có `📚 Nguồn tham khảo` và expander thêm nguồn. Mở ra đủ 4 tab: Dán nhanh, Dán văn bản dài, Thêm tài liệu / ảnh, Nhập từ thư mục. Dán đoạn giả `NGUON-UX-7741` thì thêm được (nguồn tạm, không lưu vào sổ). Ảnh `03-nguon-tham-khao.png`.
5. Tắt nguồn đó rồi gửi câu hỏi: app báo `Thiếu ngữ cảnh` / `Chưa có nguồn nào`, không trả lời từ đoạn vừa dán. Bật lại rồi hỏi cùng ý: câu trả lời `Có`, trích `NGUON-UX-7741`. Ảnh `04-nguon-bat.png`.

## Điểm chưa đạt

- Hỏi kèm ảnh **không chạy**. App đang `Đang dùng: Gemini qua cầu nối (tự động)` và hiện cảnh báo: Gemini Web và Nakazasen Router không được gửi ảnh; hãy dùng C-AGENT hoặc gỡ ảnh. Không có chỗ đổi lane trên giao diện. Vì câu 1 không gửi được, không kiểm được câu 2 không dùng lại ảnh.
- Nhãn expander bị thừa một dấu cộng: hiện `＋ ＋ Thêm nguồn` (code ghép `＋` với chuỗi đã có `＋`). Không gây nhầm với ảnh một lần, nhưng không đúng chữ vé.

## Kho tri thức

| Mục | Trước | Sau |
| --- | --- | --- |
| File | `collections\tri_thuc\library.sqlite` | cùng file |
| Byte | 2.942.201.856 | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA |

Thêm nguồn tạm có ghi 1 chunk vào `bge_m3_hybrid\workspace_chat.sqlite` (không phải `tri_thuc`). Sổ thử và nguồn `NGUON-UX-7741` còn trên máy để Muse đối chiếu. Không embed lại kho `tri_thuc`. Không merge `main`.

## Ảnh

- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/01-help-anh-mot-lan.png`
- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/02-thumbnail-bi-chan.png`
- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/03-nguon-tham-khao.png`
- `docs/phieu-viec/ket-qua/ux-attach-sources-anh/04-nguon-bat.png`
