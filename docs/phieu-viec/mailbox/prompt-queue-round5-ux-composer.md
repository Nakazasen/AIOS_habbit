# Vé ROUND5-UX-COMPOSER [NHÀ] — Sửa xô lệch composer + công tắc chọn khối tri thức

> Vé CODE (thợ OMP máy nhà implement + verify app thật). Làm SAU khi vòng 4
> UX-ATTACH-SOURCES xong. Phát hành bằng cách copy file này vào `prompt.md`,
> reset `trang-thai.md` về `moi`.
> Role OMP gợi ý: DEFAULT (code + verify). Không cần PLAN (thiết kế đã chốt
> sẵn dưới đây). Vé verify nhanh sau này dùng SMOL/TINY cho rẻ.

## Bối cảnh
- Vòng 4 (one-shot-inline, commit c317d84) tách ảnh 1 lần / nguồn lâu dài.
- User gửi ảnh chụp: hàng điều khiển dưới ô nhập bị xô lệch — chữ nút
  "🖼️ Ảnh cho câu hỏi này" đè lên dòng "Đang dùng: Gemini qua cầu nối
  (tự động)" vì 6 phần tử ([+], nút ảnh, trạng thái lane, dropdown Tìm nhanh,
  gợi ý phím Ctrl+↵, nút Hỏi) bị nhồi trong một hàng.

## Việc 1 — Sửa xô lệch (bắt buộc)
- Ô nhập full-width một hàng riêng.
- Hàng dưới chỉ còn: nút [+] đính kèm bên trái, nút Hỏi bên phải.
- Dòng trạng thái lane ("Đang dùng: ...") dời xuống một dòng mờ riêng,
  không chen ngang.
- Thanh tiến trình "Đã chuẩn bị xong..." giữ khoảng cách rõ với cụm nút.
- Bằng chứng: chụp ảnh composer sau sửa, không còn chữ đè chữ ở các độ rộng
  cửa sổ thông thường.

## Việc 2 — Công tắc chọn khối tri thức (bắt buộc)
- Một dòng chữ mờ dưới ô nhập, mặc định "Tự động" (giữ nguyên hành vi
  router hiện tại). Bấm vào bung ra 4 lựa chọn: Tự động / LSU / Điều tra lỗi
  / MOM. Không thêm toolbar, không thêm tab.
- Khi ép khối: câu trả lời hiện badge "Đang tra cứu khối X" đúng khối đã
  chọn; chỉ tìm trong khối đó (không vào tong_hop).
- Khi để Tự động: hành vi y như hiện tại.

## Việc 3 — Dòng thư viện chung ở sidebar (bắt buộc)
- Thêm đúng một dòng gập sẵn: "Thư viện chung · 3 khối · luôn bật".
- Bấm mới mở ra xem 3 khối + trạng thái; mặc định gập.

## Ràng buộc cứng (cấm regression)
- GIỮ NGUYÊN thiết kế one-shot-inline vòng 4: ảnh OCR gộp vào câu hỏi,
  không tạo nguồn tạm, câu sau không dùng lại.
- Code tương thích Python 3.11.
- Test hiện có phải pass: test_workspace_chat_composer_ui.py,
  test_workspace_chat_connector_guard.py, test_workspace_chat_ui_i18n.py
  (trừ 2 anti-hardcode đã biết fail từ trước).
- Bổ sung test cho công tắc khối (ép khối → badge đúng; Tự động → router như cũ).

## Nghiệm thu
1. Ảnh chụp composer: không xô lệch, tối giản.
2. Ép từng khối → badge đúng + kết quả chỉ từ khối đó.
3. Tự động → hành vi cũ.
4. Sidebar có dòng thư viện chung, mặc định gập.
5. SHA kho tri_thuc không đổi (vé chỉ đụng UI).
