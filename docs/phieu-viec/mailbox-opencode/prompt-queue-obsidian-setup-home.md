# VÉ: OBSIDIAN-SETUP-HOME (cài Obsidian và mở vault sổ cái tại máy nhà)

- Mã vé: `OBSIDIAN-SETUP-HOME`
- Role gợi ý: TINY/SMOL (opencode — thợ phụ tạm thời, máy nhà h410asrock). Việc nhẹ, không gọi mô hình nặng.
- Báo cáo: `docs/phieu-viec/ket-qua/obsidian-setup-home.md`
- Bối cảnh: theo lệnh của user ngày 2026-10-10, sổ cái dự án chuyển từ Notion (gói Free chạm trần số khối) sang Obsidian. Toàn bộ nội dung sổ đã được điều phối chuyển vào vault tại thư mục `docs/so-cai-vault` trong chính kho này (tệp chính `So-cai-AIOS_habbit.md` và `README.md` hướng dẫn). Vé này thiết lập phía máy nhà để user và thợ dùng chung vault đó, đồng bộ hai chiều qua git của dự án.

## Việc phải làm

1. Cập nhật bản sao kho tại máy về đầu nhánh `phieu-viec/rag-fix1` mới nhất (đợt cập nhật có thư mục `docs/so-cai-vault`).
2. Tải bộ cài Obsidian cho Windows từ trang chủ chính thức (obsidian.md) hoặc từ kho phát hành chính thức trên GitHub (bản mới nhất tại thời điểm viết vé: 1.14.4) và cài đặt cho người dùng hiện tại của máy. Không tải từ nguồn lạ.
3. Mở Obsidian, chọn mở thư mục làm vault trỏ vào `docs/so-cai-vault` trong thư mục dự án. Kiểm chứng nhìn thấy tệp `So-cai-AIOS_habbit.md` và mở ra thấy nội dung sổ (mục mới nhất ở phần Nhật ký nhắc tới trạng thái máy công ty và chênh lệch hai máy).
4. Tạo tệp lệnh đồng bộ một chạm tại thư mục dự án: `dong-bo-so-cai.ps1` (giữ mã hoá UTF-8 có BOM như quy ước các tệp lệnh khác) với đúng hành vi: kéo bản mới nhất của nhánh về; chỉ ghi lại các thay đổi nằm trong `docs/so-cai-vault` bằng một commit riêng có thông điệp rõ ràng; kéo lại một lần nữa (rebase) rồi đẩy lên. Tệp lệnh không được đụng vào các thay đổi ngoài thư mục vault.
5. Kiểm chứng đồng bộ thật: qua chính Obsidian, thêm một dòng kiểm chứng có ghi thời gian vào cuối tệp `README.md` của vault, chạy tệp lệnh đồng bộ, xác nhận commit đã lên kho từ xa. Điều phối sẽ kiểm tra dòng đó từ xa.
6. Chụp ảnh màn hình Obsidian đang mở tệp sổ cái (thấy rõ cây tệp của vault và nội dung sổ) nộp kèm báo cáo.

## Rào cứng

- Không sửa nội dung các mục cũ trong tệp sổ cái — chỉ thêm đúng một dòng kiểm chứng vào `README.md` của vault ở bước 5.
- Không cài thêm plugin nào ngoài mặc định trong vé này (cơ chế đồng bộ là git qua tệp lệnh, không dùng plugin tự commit toàn kho).
- Không merge `main`. Không đụng chỉ mục production.
- Kích thước tệp trong báo cáo đo trên bản đã nộp vào kho sau khi commit.
