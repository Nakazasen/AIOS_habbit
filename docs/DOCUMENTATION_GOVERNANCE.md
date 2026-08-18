# Quản Trị Tài Liệu (Documentation Governance)

Status: `ACTIVE`
Owner role: Project owner
Last reviewed: 2026-07-25
Review cadence: Each release candidate and every material architecture change

## Mục Đích (Purpose)

Giữ cho tài liệu luôn hữu ích, có thể truy xuất nguồn gốc và không mâu thuẫn. Tài liệu là một artifact của sản phẩm: một chốt chặn kiểm soát không được coi là đã được ghi nhận chỉ vì tệp đó tồn tại.

## Các Nguồn Chân Lý Canonical (Canonical Sources)

| Chủ đề | Nguồn chân lý Canonical |
|---|---|
| Trạng thái chuyển giao hiện tại | `ROADMAP.md` |
| Bàn giao hiện tại và rủi ro tồn dư | `PROJECT_HANDOVER.md` |
| Bằng chứng thay đổi lịch sử | `CHANGELOG.md` |
| Nguyên tắc sản phẩm | `CONSTITUTION.md` |
| Kiến trúc dữ liệu / bộ nhớ logic | `ARCHITECTURE.md` |
| Khung nhìn runtime và ranh giới tin cậy | `docs/architecture/` |
| Hiện trạng bảo mật và quyền riêng tư | `SECURITY.md`, `docs/security/` |
| Chất lượng và kiểm chứng | `docs/quality/` |
| Quy trình vận hành | `docs/operations/` |
| Kiểm soát phát hành và phụ thuộc | `docs/release/` |

Các bằng chứng lịch sử trong `docs/archive/` không phải là nguồn chân lý vận hành.

## Metadata Bắt Buộc (Required Metadata)

Các tài liệu quản trị kiểm soát chuyên nghiệp bắt buộc phải hiển thị: `Status`, `Owner role`, `Last reviewed`, và `Review cadence` ngay bên dưới tiêu đề H1. Một tài liệu có thể nêu trạng thái `OWNER_DECISION_REQUIRED`; trạng thái đó là trung thực và không đồng nghĩa với việc đã được phê duyệt.

## Bộ Từ Vựng Trạng Thái (Status Vocabulary)

- `ACTIVE`: chính sách hoặc tài liệu tham chiếu hiện hành đang được duy trì.
- `PROPOSED`: chốt chặn được dự thảo cần sự phê duyệt của chủ sở hữu.
- `PARTIAL`: đã triển khai một phần; các hạn chế được nêu rõ.
- `PLANNED`: công việc đã biết nhưng chưa được triển khai.
- `RETIRED`: chỉ dùng cho mục đích lịch sử; liên kết thay thế được cung cấp.

## Quy Tắc Thay Đổi và Đánh Giá (Change and Review Rules)

1. Cập nhật tài liệu canonical trong cùng lượt thay đổi đối với một thay đổi hành vi trọng yếu.
2. Dẫn link các tuyên bố tới mã nguồn, kiểm thử, Gate Card hoặc bằng chứng runbook khi khả thi.
3. Tuyệt đối không đưa secret, nội dung tài liệu riêng tư, ảnh chụp màn hình, đường dẫn cục bộ hoặc bản ghi runtime vào tài liệu được theo dõi.
4. Sử dụng đường dẫn tương đối (relative links) bên trong repository để đảm bảo hoạt động khi clone/chuyển nhánh.
5. Sử dụng `docs/PROFESSIONALIZATION_INDEX.md` làm bản đồ điều hướng; không tạo các chỉ mục cạnh tranh.
6. Chạy `py -3 scripts/check_docs.py` trước khi đánh dấu gate tài liệu hoàn thành.

## Xử Lý Tài Liệu Lỗi Thời (Stale-document Handling)

Khi một tuyên bố trở nên lỗi thời: cập nhật nguồn canonical, giữ nguyên các bản ghi lịch sử, thêm liên kết thay thế và lưu trữ (archive) các tài liệu lịch sử dài thay vì viết lại lịch sử. Một chốt chặn bị hỏng hoặc mơ hồ phải được ghi nhận vào sổ rủi ro cho đến khi được sửa chữa.

