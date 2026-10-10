# Vault sổ cái AIOS_habbit

Đây là vault Obsidian chứa sổ cái chính thức của dự án AIOS_habbit (tệp chính: `So-cai-AIOS_habbit.md`), chuyển từ Notion ngày 2026-10-10 vì Notion gói Free chạm trần số khối. Dữ liệu là các tệp Markdown thuần trên đĩa — không giới hạn số mục, không phụ thuộc dịch vụ trả phí.

## Cách dùng trên mỗi máy

1. Cài Obsidian từ trang chủ obsidian.md (miễn phí).
2. Vault nằm ngay trong bản sao sẵn có của kho dự án trên máy: thư mục `docs/so-cai-vault` bên trong thư mục dự án (máy công ty: `D:\Sandbox\AIOS_habbit\docs\so-cai-vault`; máy nhà: cùng cấu trúc trong thư mục dự án đã clone). Không cần clone thêm kho nào khác.
3. Mở Obsidian, chọn "Open folder as vault" trỏ vào thư mục `docs/so-cai-vault` đó.
4. Đồng bộ hai chiều đi qua chính kho git của dự án (nhánh `phieu-viec/rag-fix1`) — cùng kênh mà các hộp thư của thợ đang dùng mỗi ngày. Mỗi máy có một tệp lệnh đồng bộ một chạm do thợ thiết lập khi cài đặt (kéo bản mới nhất về, ghi lại thay đổi riêng trong thư mục vault, đẩy lên). Sửa ở máy này rồi chạy đồng bộ, máy kia chạy đồng bộ là thấy. Không bật plugin Obsidian Git ở chế độ tự commit toàn kho trong vault này, vì kho chứa cả mã nguồn của dự án và commit phải đi theo kỷ luật của hộp thư.

## Quy ước ghi

- Mục mới chèn ngay dưới tiêu đề "Nhật ký" trong tệp chính (mới nhất ở trên cùng), tiêu đề cấp 2 gồm thời gian và tóm tắt, nội dung gạch đầu dòng, viết ở biến thể tiếng Việt vi-VN.
- Trước khi sửa thủ công một mục cũ, hãy để Obsidian Git kéo bản mới nhất về (hoặc bấm kéo thủ công) để tránh xung đột. Nếu xảy ra xung đột, giữ cả hai phiên bản của đoạn xung đột rồi báo điều phối viên xử lý — không tự xóa đoạn của phía bên kia.
- Không đổi tên tệp chính và không di chuyển vault ra khỏi thư mục đã clone.

## Đồng bộ và an toàn

- Kênh đồng bộ là kho git của dự án trên GitHub, thư mục `docs/so-cai-vault`, nhánh `phieu-viec/rag-fix1` — kho riêng cho vault không tạo được vì mã truy cập hiện tại không có quyền tạo kho mới; phương án này dùng hạ tầng sẵn có và đã được cả ba phía dùng hằng ngày. Khi nhánh làm việc được hợp nhất vào nhánh chính trong tương lai, vault đi theo cùng đợt hợp nhất và README này sẽ được cập nhật.
- Toàn bộ lịch sử thay đổi nằm trong lịch sử commit của kho — khôi phục được mọi phiên bản cũ của sổ.
- Bản Notion cũ được giữ nguyên làm bản lưu trữ lịch sử tới thời điểm chuyển đổi, không ghi thêm.
