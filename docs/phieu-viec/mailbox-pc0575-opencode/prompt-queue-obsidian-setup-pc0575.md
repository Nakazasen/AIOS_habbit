# VÉ: OBSIDIAN-SETUP-PC0575 (cài Obsidian và mở vault sổ cái tại máy công ty)

- Mã vé: `OBSIDIAN-SETUP-PC0575`
- Role gợi ý: TINY/SMOL (opencode — thợ phụ tạm thời, máy công ty KDTVN-PC0575). Việc nhẹ, không gọi mô hình nặng.
- Điều kiện mở vé: máy công ty đang dừng (mốc hoạt động cuối 23:18 ngày 09/10) — vé nằm trong hàng chờ và chỉ thực hiện khi máy hoạt động trở lại, sau vé đo lại giao diện đang chờ điều kiện.
- Báo cáo: `docs/phieu-viec/ket-qua/obsidian-setup-pc0575.md`
- Bối cảnh: theo lệnh của user ngày 2026-10-10, sổ cái dự án chuyển từ Notion (gói Free chạm trần số khối) sang Obsidian. Toàn bộ nội dung sổ đã được điều phối chuyển vào vault tại thư mục `docs/so-cai-vault` trong chính kho này (tệp chính `So-cai-AIOS_habbit.md` và `README.md` hướng dẫn). Vé này thiết lập phía máy công ty để dùng chung một vault với máy nhà, đồng bộ hai chiều qua git của dự án. Chỉ thao tác trong `D:\Sandbox\AIOS_habbit` theo quy ước của máy này.

## Việc phải làm

1. Cập nhật bản sao kho tại máy về đầu nhánh `phieu-viec/rag-fix1` mới nhất (đợt cập nhật có thư mục `docs/so-cai-vault`).
2. Tải bộ cài Obsidian cho Windows từ trang chủ chính thức (obsidian.md) hoặc từ kho phát hành chính thức trên GitHub (bản mới nhất tại thời điểm viết vé: 1.14.4) và cài đặt cho người dùng hiện tại của máy. Không tải từ nguồn lạ.
3. Mở Obsidian, chọn mở thư mục làm vault trỏ vào `D:\Sandbox\AIOS_habbit\docs\so-cai-vault`. Kiểm chứng nhìn thấy tệp `So-cai-AIOS_habbit.md`, mở ra thấy nội dung sổ, và thấy được dòng kiểm chứng mà phía máy nhà đã thêm vào `README.md` của vault (bằng chứng đồng bộ hai chiều đã thông: thay đổi từ máy nhà hiện diện tại máy công ty).
4. Tạo tệp lệnh đồng bộ một chạm `dong-bo-so-cai.ps1` tại thư mục dự án (UTF-8 có BOM) với đúng hành vi: kéo bản mới nhất của nhánh về; chỉ ghi lại các thay đổi nằm trong `docs/so-cai-vault` bằng một commit riêng có thông điệp rõ ràng; kéo lại (rebase) rồi đẩy lên. Tệp lệnh không được đụng vào các thay đổi ngoài thư mục vault.
5. Kiểm chứng chiều ngược lại: qua chính Obsidian tại máy công ty, thêm một dòng kiểm chứng có ghi thời gian vào cuối tệp `README.md` của vault, chạy tệp lệnh đồng bộ, xác nhận commit đã lên kho từ xa. Điều phối kiểm tra từ xa và phía máy nhà sẽ thấy dòng này ở lần đồng bộ kế tiếp của họ.
6. Chụp ảnh màn hình Obsidian đang mở tệp sổ cái (thấy rõ cây tệp của vault và nội dung sổ) nộp kèm báo cáo.

## Rào cứng

- Không sửa nội dung các mục cũ trong tệp sổ cái — chỉ thêm đúng một dòng kiểm chứng vào `README.md` của vault ở bước 5.
- Không cài thêm plugin nào ngoài mặc định trong vé này (cơ chế đồng bộ là git qua tệp lệnh, không dùng plugin tự commit toàn kho).
- Không merge `main`. Không đụng chỉ mục production. Không chạy việc này đồng thời với phiên ứng dụng của user trên máy.
- Kích thước tệp trong báo cáo đo trên bản đã nộp vào kho sau khi commit.
