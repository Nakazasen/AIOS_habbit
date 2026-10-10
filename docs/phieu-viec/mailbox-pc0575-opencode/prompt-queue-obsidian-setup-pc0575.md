# VÉ: OBSIDIAN-SETUP-PC0575 (cài Obsidian và mở vault sổ cái tại máy công ty) — BẢN ĐÍNH CHÍNH ĐÍCH VAULT 2026-10-10 ~09:15

- Mã vé: `OBSIDIAN-SETUP-PC0575`
- Role gợi ý: TINY/SMOL (opencode — thợ phụ tạm thời, máy công ty KDTVN-PC0575). Việc nhẹ, không gọi mô hình nặng.
- Điều kiện mở vé: máy công ty đang dừng (mốc hoạt động cuối 23:18 ngày 09/10) — vé nằm trong hàng chờ và chỉ thực hiện khi máy hoạt động trở lại, sau vé đo lại giao diện đang chờ điều kiện.
- Báo cáo: `docs/phieu-viec/ket-qua/obsidian-setup-pc0575.md`
- **ĐÍNH CHÍNH (điều phối, 09:15 ngày 10/10):** user đã tạo kho điều phối riêng `aios-dieu-phoi` và sổ cái chính thức đã chuyển về đó. Vault cần mở nằm ở thư mục `so-cai` trong bản clone của kho `aios-dieu-phoi` tại máy công ty — KHÔNG mở bản sao trong `docs/so-cai-vault` của kho dự án (bản đó đã thành lưu trữ). Các bước dưới đây đã viết lại theo đích mới. Chỉ thao tác trong `D:\Sandbox` theo quy ước của máy này.

## Bối cảnh

Theo lệnh của user ngày 2026-10-10, sổ cái dự án chuyển từ Notion sang Obsidian và đặt tại kho điều phối riêng tư `Nakazasen/aios-dieu-phoi`, thư mục `so-cai` (tệp chính `So-cai-AIOS_habbit.md`). Vé này thiết lập phía máy công ty để dùng chung một vault với máy nhà, đồng bộ hai chiều qua kho điều phối.

## Việc phải làm

1. Cập nhật bản sao kho dự án tại máy về đầu nhánh `phieu-viec/rag-fix1` mới nhất. Clone kho điều phối `https://github.com/Nakazasen/aios-dieu-phoi.git` về `D:\Sandbox\aios-dieu-phoi` (nếu đã clone thì kéo nhánh `main` mới nhất). Nếu clone bị từ chối quyền truy cập: ghi nguyên văn thông báo lỗi vào báo cáo, báo điểm gãy và dừng — không tự xử lý thông tin đăng nhập.
2. Tải bộ cài Obsidian cho Windows từ trang chủ chính thức (obsidian.md) hoặc từ kho phát hành chính thức trên GitHub (bản mới nhất tại thời điểm viết vé: 1.14.4) và cài đặt cho người dùng hiện tại của máy. Không tải từ nguồn lạ.
3. Mở Obsidian, chọn mở thư mục làm vault trỏ vào `D:\Sandbox\aios-dieu-phoi\so-cai`. Kiểm chứng nhìn thấy tệp `So-cai-AIOS_habbit.md`, mở ra thấy nội dung sổ, và thấy được dòng kiểm chứng mà phía máy nhà đã thêm vào `so-cai/README.md` (bằng chứng đồng bộ hai chiều đã thông: thay đổi từ máy nhà hiện diện tại máy công ty).
4. Tạo tệp lệnh đồng bộ một chạm `dong-bo-so-cai.ps1` tại `D:\Sandbox\aios-dieu-phoi` (UTF-8 có BOM) với đúng hành vi, chỉ thao tác trong thư mục clone đó: kéo nhánh `main` mới nhất về; chỉ ghi lại các thay đổi nằm trong `so-cai` bằng một commit riêng có thông điệp rõ ràng; kéo lại (rebase) rồi đẩy lên. Tệp lệnh không được đụng vào các thay đổi ngoài thư mục `so-cai`.
5. Kiểm chứng chiều ngược lại: qua chính Obsidian tại máy công ty, thêm một dòng kiểm chứng có ghi thời gian vào cuối tệp `so-cai/README.md`, chạy tệp lệnh đồng bộ, xác nhận commit đã lên kho `aios-dieu-phoi` từ xa. Điều phối kiểm tra từ xa và phía máy nhà sẽ thấy dòng này ở lần đồng bộ kế tiếp của họ.
6. Chụp ảnh màn hình Obsidian đang mở tệp sổ cái (thấy rõ cây tệp của vault và nội dung sổ) nộp kèm báo cáo.

## Rào cứng

- Không sửa nội dung các mục cũ trong tệp sổ cái — chỉ thêm đúng một dòng kiểm chứng vào `so-cai/README.md` ở bước 5.
- Không cài thêm plugin nào ngoài mặc định trong vé này (cơ chế đồng bộ là git qua tệp lệnh).
- Không merge `main` ở kho dự án. Không đụng chỉ mục production. Không chạy việc này đồng thời với phiên ứng dụng của user trên máy.
- Kích thước tệp trong báo cáo đo trên bản đã nộp vào kho sau khi commit.
