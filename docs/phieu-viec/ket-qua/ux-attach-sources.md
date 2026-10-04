# Báo cáo UX-ATTACH-SOURCES — vòng 4, máy nhà

- Trạng thái: **CHƯA ĐẠT** → chuyển `cho-muse`. Bốn điểm Phần B đều đạt, nhưng phát hiện lỗi UI mới trong đúng luồng của vé: một câu hỏi kèm ảnh làm chat hiện **hai bubble** (bubble 2 trùng câu thô, do tầng cầu nối tự tạo tin nhắn). Cần Muse xử lý trước khi công nhận.
- Máy: `h410asrock`. Nhánh: `phieu-viec/rag-fix1`. Mã kiểm: `c317d84` (vòng 4). Không merge `main`; không ghi index production.
- Ngày: 2026-10-04, 08:47–10:25 +07 — phiên 1 (08:47–09:49) thu bằng chứng; phiên 2 (watcher tự mở lại 09:50) tái xác nhận và dựng lại lỗi.
- Cổng gate: watcher `LAUNCH 1/4` lúc 08:47:48; `RELAUNCH 1/4` lúc 09:50:32 (điều kiện mở: đang verify dở). Không dùng nhánh 4 lần watcher.

## Kết luận

Bốn điểm Phần B của vé đều đạt trên app thật (bằng chứng + ảnh bên dưới). Tuy nhiên một lần gửi câu hỏi kèm ảnh đang tạo **hai bubble**: bubble 1 là câu hỏi kèm khối chữ OCR (đúng thiết kế vòng 4), bubble 2 là câu thô trùng lặp do tầng cầu nối (`antigravity_bridge`) tự tạo thêm. Lỗi tái hiện 2/2 lần, có dấu vết trong `messages.jsonl` và evidence trace. Đây là lỗi UI thấy được trong luồng chính của vé → chuyển Muse xử lý (hướng sửa gợi ý ở cuối).

## Phần A (bổ sung) — môi trường

- `AIOS_OCR_LANG=vie+eng` đã đặt ở biến User; app mở lại cùng bộ biến của `RUN_AIOS_WORKSPACE_CHAT.bat`, cổng 8501. Cầu nối Antigravity `127.0.0.1:8585` xanh.
- Tesseract v5.5.3.20260724 có gói `vie` (cài từ vòng 3). OCR lần này giữ được dấu tiếng Việt ở nhiều cụm: `Thiếu ngữ cảnh`, `Chưa có nguồn nào` (xem ảnh 23).

## Phần B — 4 điểm (đều ĐẠT)

1. **ĐẠT — câu hỏi kèm ảnh chạy trên lane Gemini, đọc được chữ trong ảnh.**
   - Phiên 1: đính ảnh lỗi thật `07-cau1-ocr-fail.png` + hỏi `lỗi này là gì?` → câu chạy trên `Đang dùng: Gemini qua cầu nối (tự động)`; câu trả lời đọc đúng nội dung ảnh (`Thiếu ngữ cảnh. Chưa có nguồn nào.`). Ảnh 16 (composer + thumbnail), 18 (câu trả lời), 22 (khối chữ OCR nằm trong câu hỏi).
   - Phiên 2 (tái xác nhận, đúng 1 lần gửi): câu trả lời `Dựa trên hình ảnh bạn cung cấp, đây không phải là lỗi kỹ thuật hệ thống…`. Ảnh 23. Store: `MSG-0DC46178` (10:17:27, 342 ký tự — câu hỏi đã gộp khối OCR) → `MSG-2873C125` (10:17:33, câu trả lời).
2. **ĐẠT — câu sau không dùng lại ảnh; không sinh nguồn tạm từ ảnh; huy hiệu không tính ảnh.**
   - Phiên 1: câu tiếp theo không đính kèm (`Trong san xuat, log jig cua LSU…`) trả lời chỉ theo nguồn chữ, không nhắc nội dung ảnh (store `MSG-E5D765F9` → `MSG-0B44A5A2`; ảnh 20). Thumbnail đã biến khỏi composer sau câu 1 (ảnh 12).
   - Thanh bên không có nguồn nào sinh từ ảnh: chỉ có 2 nguồn `Dán nhanh` (nguồn test) — ảnh 21 (phiên 1), ảnh 24 (phiên 2, `Nguồn đang bật: 0`, cả hai nguồn `Đã tắt`).
   - Huy hiệu `Nguồn gửi cùng câu hỏi` = 0 cho câu trả lời mới dù câu hỏi kèm ảnh (phiên 2; phiên 1 câu 1 cũng = 0) — ảnh không được tính là nguồn.
   - (Khi chưa có nguồn nào và không kèm ảnh, câu hỏi vẫn bị chặn `Thiếu ngữ cảnh` như hành vi nền từ trước — ảnh 19; không phải lỗi của vé.)
3. **ĐẠT — expander thanh bên đúng `＋ Thêm nguồn` (một dấu cộng).** Ảnh 17 (phiên 1), ảnh 24 (phiên 2).
4. **ĐẠT — SHA kho `tri_thuc` không đổi.**

## Lỗi mới — hai bubble khi hỏi kèm ảnh (lý do chưa đạt)

**Hiện tượng:** một lần gửi câu hỏi kèm ảnh → chat hiện: bubble 1 = `lỗi này là gì?` + khối chữ OCR (đúng thiết kế), bubble 2 = `lỗi này là gì?` trơn (trùng lặp), rồi mới tới câu trả lời. Xem ảnh 23.

**Tái hiện:** 2/2 lần độc lập (mỗi lần chỉ MỘT lần bấm gửi, không phải double-submit). Câu hỏi không kèm ảnh thì không dính (đã đối chiếu: câu 2 phiên 1 chỉ có 1 bubble).

**Bằng chứng store `local_cases/workspace_chat/messages.jsonl`:**
- Phiên 2: `MSG-0DC46178` (user, 10:17:27, 342 ký tự = câu hỏi + khối OCR) → `MSG-2D0A6E06` (user, 10:17:32, 14 ký tự = `lỗi này là gì?` trơn) → `MSG-2873C125` (assistant, 10:17:33).
- Phiên 1: `MSG-46ECD3E6` (user, 09:07:15, 342) → `MSG-43FD366B` (user, 09:07:19, 14) → `MSG-51306F38` (assistant, 09:07:37).

**Bằng chứng trace `local_cases/workspace_chat/traces.jsonl`:** trace `trc_9d835d909435` (phiên 2) gán câu trả lời cho `user_message_id = MSG-2D0A6E06` (bubble trơn) dù câu hỏi thực là bản đã gộp OCR; phiên 1 tương tự (`trc_295ee64ccbc0` → `MSG-43FD366B`).

**Nguyên nhân gốc (OMP đọc mã, mã kiểm `c317d84`):**
- `c317d84` đổi đường hỏi để gộp khối OCR thẳng vào câu hỏi (`src/aios_habit/workspace_chat_app.py`, ~dòng 4725) và lưu chính câu đã gộp làm tin nhắn user (~dòng 4950).
- Tầng cầu nối `route_workspace_chat_submission` gọi `_get_or_create_user_message(conversation_id, user_raw_input)` (`src/aios_habit/antigravity_bridge.py` dòng 600; gọi từ dòng 1113/1199/1333/1419). Hàm này chỉ tái dùng tin nhắn cuối khi nội dung khớp **đúng** câu thô; bản đã lưu = thô + khối OCR (khác chuỗi) → hàm **tạo thêm** một tin nhắn user mới bằng câu thô → thành bubble thứ hai và bị trace gán nhầm.

**Hướng sửa gợi ý (Muse quyết định):**
- Cầu nối coi là khớp khi câu thô là *tiền tố* của nội dung tin nhắn cuối (thô + `---` + khối OCR), hoặc
- Đường hỏi truyền thẳng id tin nhắn đã lưu xuống cầu nối để cầu nối liên kết thay vì tự tạo tin nhắn mới.

## Ảnh bằng chứng vòng này

- `16-composer-thumbnail.png` — composer có thumbnail ảnh + nhãn `🖼️ Ảnh cho câu hỏi này`
- `17-sidebar-mot-dau.png` — expander `＋ Thêm nguồn` một dấu cộng
- `18-cau1-doc-duoc-chu.png` — câu 1 đọc được chữ trong ảnh
- `19-cau2-khong-co-nguon.png` — câu 2 khi chưa có nguồn: chặn `Thiếu ngữ cảnh` (hành vi nền)
- `20-cau2-khong-dung-anh.png` — câu 2 với nguồn chữ: không nhắc lại ảnh
- `21-sidebar-nguon-sau-verify.png` — danh sách nguồn sau verify (không có nguồn từ ảnh)
- `22-cau1-chu-ocr-nam-trong-cau-hoi.png` — khối chữ OCR nằm trong câu hỏi (thiết kế one-shot-inline)
- `23-bubble-trung-sau-mot-lan-gui.png` — **lỗi mới**: một lần gửi, hai bubble
- `24-sidebar-sau-lan-2.png` — thanh bên phiên 2: `＋ Thêm nguồn` một dấu, `Nguồn đang bật: 0`, không nguồn từ ảnh

(Ảnh các vòng `01`–`15` giữ để đối chiếu.)

## Kho tri thức

| Mục | Trước | Sau |
| --- | --- | --- |
| File | `C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite` | cùng file |
| Byte | 2.942.201.856 | 2.942.201.856 |
| mtime | 2026-10-01 08:27:27 | 2026-10-01 08:27:27 |
| SHA-256 | `45eb0e072893f802d71ab201cfbb2b29c36e2b0a31313fa79fc55a025b65b7c0` | cùng SHA |

## Ghi chú thêm (không phải lỗi của vé)

- Lần chạy đầu ở phiên 2 (10:08, có 1 nguồn test đang bật) gặp bộ đọc BGE còn nguội sau khi mở lại app → app hiện thông báo tự làm nóng/thử lại (`...bấm Hỏi lại, không cần khởi động lại AIOS`). Chạy lại sau đó bình thường. Hiện tượng môi trường đã biết ở máy CPU-only, ngoài phạm vi vé này.
- Không ghi index production bằng tay; không merge `main`; không force-push.
