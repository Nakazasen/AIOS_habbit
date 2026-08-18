# Chính Sách Phụ Thuộc và Chuỗi Cung Ứng (Dependency and Supply-Chain Policy)

Status: `PROPOSED`
Owner role: Release owner with security reviewer
Last reviewed: 2026-08-02
Review cadence: Each dependency update and release candidate

## Chính Sách (Policy)

1. Chỉ thêm một phụ thuộc mới khi nó phục vụ một Gate Card đã được phê duyệt và giấy phép (license), trạng thái hỗ trợ, tác động quyền riêng tư cùng phương án hoàn tác (rollback) đã được ghi nhận.
2. Ghim chặt (Pin) các phụ thuộc Git vào một tag phát hành bất biến hoặc commit cụ thể. Phụ thuộc router hiện tại được ghim vào `nakazasen-ai-router@v0.8.0` (`f95c6609a34446be9ebca578f2ad187f40c9c985`); mục tiêu hoàn tác đã biết là `nakazasen-ai-router@v0.5.2`.
3. Chỉ sử dụng dải phiên bản có giới hạn khi có quy trình kiểm chứng cài đặt sạch và đường dẫn hoàn tác. Chỉ riêng `pyproject.toml` không phải là tệp lockfile.
4. Tuyệt đối không đưa thông tin xác thực, chỉ mục package riêng tư hoặc dữ liệu của chủ sở hữu vào metadata phụ thuộc, log CI hay đầu ra SBOM.
5. Xem xét kỹ các phụ thuộc trực tiếp khi nâng cấp: tính tương thích API, các lưu ý bảo mật, giấy phép và tác động changelog. Chạy các bài test trọng điểm kèm theo toàn bộ bộ test.

## Bằng Chứng Nâng Cấp Bắt Buộc (Required Upgrade Evidence)

- Nguồn / phiên bản / tham chiếu đã thay đổi.
- Lý do và đánh giá rủi ro.
- Các bài kiểm thử tương thích trọng điểm và toàn bộ cổng chất lượng.
- Kiểm tra cài đặt sạch / đóng gói khi bản phát hành phân phối nằm trong phạm vi.
- Mục tiêu hoàn tác (phiên bản / commit tốt đã biết trước đó).
- Mục ghi trong Changelog và ghi chú phát hành.

## Hiện Trạng SBOM và Cảnh Báo Lỗ Hổng (SBOM and Advisory Posture)

`SBOM_POLICY.md` xác định các quy tắc đề xuất về việc tạo và công bố SBOM. Việc tự động quét lỗ hổng bảo mật mang tính khuyến cáo cho đến khi chủ sở hữu thiết lập công cụ, ngưỡng mức độ nghiêm trọng, quy trình xử lý ngoại lệ và chính sách chặn merge. Các phát hiện cảnh báo phải được ghi nhận vào sổ đăng ký rủi ro; tuyệt đối không âm thầm bỏ qua.

## Giấy Phép và Nguồn Gốc Xuất Xứ (License and Provenance)

Trước khi phân phối ra bên ngoài, hãy tạo một bản kiểm kê giấy phép bên thứ ba từ môi trường đã giải quyết hoặc từ SBOM đã sinh ra, đồng thời đánh giá tính tương thích giấy phép với tệp `LICENSE` của repository. Repository này hiện chưa tuyên bố có cơ chế kiểm soát nguồn gốc xuất xứ có chữ ký số (signed-provenance) hay lockfile tái tạo hoàn toàn.

## Hoàn Tác (Rollback)

Khôi phục (Revert) khai báo phụ thuộc về phiên bản đã được kiểm chứng gần nhất, cài đặt lại trong môi trường sạch, chạy lại toàn bộ các cổng chất lượng và ghi nhận nguyên nhân vào changelog / sổ đăng ký rủi ro. Tuyệt đối không bao giờ sử dụng thông tin xác thực provider để chẩn đoán sự cố cài đặt package.

