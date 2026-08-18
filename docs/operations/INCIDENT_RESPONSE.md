# Phản Ứng Sự Cố (Incident Response)

Status: `PROPOSED`
Owner role: Project owner / designated incident coordinator
Last reviewed: 2026-07-25
Review cadence: After incident, release candidate or security boundary change

## Mục đích (Purpose)

Cách ly, điều tra và phục hồi sau sự cố nghi ngờ liên quan đến quyền riêng tư, thông tin xác thực, tính toàn vẹn hoặc tính khả dụng mà không làm lan truyền thêm dữ liệu riêng tư.

## Mô hình Mức độ Nghiêm trọng (Severity Model)

| Mức độ | Ví dụ | Mục tiêu ngay lập tức |
|---|---|---|
| SEV-1 | Nghi ngờ lộ thông tin xác thực / dữ liệu riêng tư ra vị trí công cộng | Chặn rò rỉ, thu hồi/cách ly, bảo toàn bằng chứng tối thiểu |
| SEV-2 | Mất mát/hỏng dữ liệu cục bộ hoặc tuyến provider có thể vi phạm chính sách | Dừng luồng bị ảnh hưởng, khôi phục / đánh giá phạm vi |
| SEV-3 | Provider ngừng hoạt động, phát hành thất bại hoặc thoái lui tính năng không nhạy cảm | Khôi phục hành vi cục bộ được hỗ trợ |
| SEV-4 | Lỗ hổng tài liệu / quy trình không có tác động trực tiếp | Theo dõi trong sổ đăng ký rủi ro và lên kế hoạch khắc phục |

## Phản ứng Đầu tiên (First Response)

1. Tuyệt đối không dán secret, tài liệu thô, toàn bộ prompt, đường dẫn cục bộ hoặc ảnh chụp màn hình vào issue/chat công khai.
2. Dừng tuyến/tiến trình bị ảnh hưởng khi an toàn. Đối với sự cố provider, hãy vô hiệu hóa tuyến router và chuyển sang quy trình chỉ dùng cục bộ (local-only).
3. Lưu giữ các dữ kiện an toàn tối thiểu: thời gian, phiên bản/commit, tính năng bị ảnh hưởng, trạng thái quan sát được và liệu có nghi ngờ lộ dữ liệu/thông tin xác thực hay không.
4. Nếu một thông tin xác thực (credential) có nguy cơ bị lộ, hãy thu hồi/đổi mới (rotate) ngay thông qua quy trình bí mật của provider hoặc chủ sở hữu. Không thử lại key cũ nhiều lần.
5. Nếu một tệp riêng tư vô tình bị đưa vào git stage, hãy gỡ nó khỏi chỉ mục (git reset) mà không xóa dữ liệu của chủ sở hữu; leo thang lên SEV-1 ngay nếu dữ liệu đã bị push/lộ ra môi trường từ xa.

## Điều tra và Cách ly (Investigation and Containment)

- Chỉ tái hiện lỗi bằng dữ liệu tổng hợp (synthetic) khi có thể.
- Kiểm tra `git status`, kết quả audit và log đã được làm sạch; tuyệt đối không tạo artifact chẩn đoán chứa dữ liệu thô trong repository.
- Xác định xem cơ chế default-deny / sự đồng ý / làm sạch dữ liệu của Gateway có bị ảnh hưởng hay không đối với các sự cố liên quan đến tuyến bên ngoài.
- Ưu tiên hoàn tác (rollback) về phiên bản/phụ thuộc đã được kiểm chứng gần nhất thay vì thực hiện các chỉnh sửa nóng (hot edit) chưa qua đánh giá.

## Phục hồi và Truyền thông (Recovery and Communication)

- Làm theo tài liệu [sao lưu và phục hồi](BACKUP_RESTORE.md) để khôi phục dữ liệu cục bộ.
- Làm theo tài liệu [khắc phục sự cố](TROUBLESHOOTING.md) để cô lập lỗi an toàn.
- Kênh báo cáo bảo mật, tên chủ sở hữu, người nhận thông báo và khung thời gian công bố ở trạng thái `OWNER_DECISION_REQUIRED` (Yêu cầu quyết định từ chủ sở hữu); xem [SECURITY.md](../../SECURITY.md) ở thư mục gốc.
- Ghi lại bản tóm tắt sau sự cố (post-incident note) đã được làm sạch: dòng thời gian, phân loại tác động, nguyên nhân gốc rễ, hành động khắc phục, xác minh và rủi ro tồn dư. Liên kết nó từ sổ đăng ký rủi ro mà không kèm bằng chứng riêng tư.

## Tiêu chí Đóng Sự Cố (Closure Criteria)

Một sự cố chỉ được đóng lại sau khi có đầy đủ bằng chứng cách ly, phục hồi/hoàn tác, kiểm chứng thoái lui tính năng, quyết định truyền thông của chủ sở hữu và cập nhật rủi ro/ADR/runbook. Tuyệt đối không đóng sự cố chỉ vì lỗi không còn xuất hiện.
