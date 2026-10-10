# VÉ: OBSIDIAN-SETUP-HOME (cài Obsidian và mở vault sổ cái tại máy nhà) — BẢN ĐÍNH CHÍNH ĐÍCH VAULT 2026-10-10 ~09:15

- Mã vé: `OBSIDIAN-SETUP-HOME`
- Role gợi ý: TINY/SMOL (opencode — thợ phụ tạm thời, máy nhà h410asrock). Việc nhẹ, không gọi mô hình nặng.
- Báo cáo: `docs/phieu-viec/ket-qua/obsidian-setup-home.md`
- **ĐÍNH CHÍNH (điều phối, 09:15 ngày 10/10 — đọc kỹ, bản này thay toàn bộ chỉ dẫn đích vault của bản phát hành 08:20):** user đã tạo kho điều phối riêng `aios-dieu-phoi` và sổ cái chính thức đã chuyển về đó. Vault cần mở nằm ở thư mục `so-cai` trong bản clone của kho `aios-dieu-phoi` — KHÔNG mở bản sao trong `docs/so-cai-vault` của kho dự án (bản đó đã thành lưu trữ). Các bước dưới đây đã viết lại theo đích mới.

## Bối cảnh

Theo lệnh của user ngày 2026-10-10, sổ cái dự án chuyển từ Notion sang Obsidian và đặt tại kho điều phối riêng tư `Nakazasen/aios-dieu-phoi`, thư mục `so-cai` (tệp chính `So-cai-AIOS_habbit.md`). Vé này thiết lập phía máy nhà để user và thợ dùng chung vault đó, đồng bộ hai chiều qua chính kho điều phối.

## Việc phải làm

1. Cập nhật bản sao kho dự án tại máy về đầu nhánh `phieu-viec/rag-fix1` mới nhất. Clone kho điều phối `https://github.com/Nakazasen/aios-dieu-phoi.git` về `D:\Sandbox\aios-dieu-phoi` (nếu đã clone thì kéo nhánh `main` mới nhất). Nếu clone bị từ chối quyền truy cập: ghi nguyên văn thông báo lỗi vào báo cáo, đặt trạng thái chờ duyệt kèm điểm gãy và dừng — không tự xử lý thông tin đăng nhập.
2. Tải bộ cài Obsidian cho Windows từ trang chủ chính thức (obsidian.md) hoặc từ kho phát hành chính thức trên GitHub (bản mới nhất tại thời điểm viết vé: 1.14.4) và cài đặt cho người dùng hiện tại của máy. Không tải từ nguồn lạ.
3. Mở Obsidian, chọn mở thư mục làm vault trỏ vào `D:\Sandbox\aios-dieu-phoi\so-cai`. Kiểm chứng nhìn thấy tệp `So-cai-AIOS_habbit.md` và mở ra thấy nội dung sổ (mục mới nhất ở phần Nhật ký ghi mốc kho điều phối `aios-dieu-phoi` đã mở).
4. Tạo tệp lệnh đồng bộ một chạm tại thư mục clone của kho điều phối: `D:\Sandbox\aios-dieu-phoi\dong-bo-so-cai.ps1` (giữ mã hoá UTF-8 có BOM như quy ước các tệp lệnh khác) với đúng hành vi, chỉ thao tác trong thư mục clone đó: kéo nhánh `main` mới nhất về; chỉ ghi lại các thay đổi nằm trong `so-cai` bằng một commit riêng có thông điệp rõ ràng; kéo lại một lần nữa (rebase) rồi đẩy lên. Tệp lệnh không được đụng vào các thay đổi ngoài thư mục `so-cai`.
5. Kiểm chứng đồng bộ thật: qua chính Obsidian, thêm một dòng kiểm chứng có ghi thời gian vào cuối tệp `README.md` trong thư mục `so-cai` của bản clone, chạy tệp lệnh đồng bộ, xác nhận commit đã lên kho `aios-dieu-phoi` từ xa. Điều phối sẽ kiểm tra dòng đó từ xa.
6. Chụp ảnh màn hình Obsidian đang mở tệp sổ cái (thấy rõ cây tệp của vault và nội dung sổ) nộp kèm báo cáo.

## Rào cứng

- Không sửa nội dung các mục cũ trong tệp sổ cái — chỉ thêm đúng một dòng kiểm chứng vào `so-cai/README.md` ở bước 5.
- Không cài thêm plugin nào ngoài mặc định trong vé này (cơ chế đồng bộ là git qua tệp lệnh).
- Không merge `main` ở kho dự án. Không đụng chỉ mục production.
- Kích thước tệp trong báo cáo đo trên bản đã nộp vào kho sau khi commit.
