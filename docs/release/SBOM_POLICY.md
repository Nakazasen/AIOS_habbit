# Chính Sách SBOM (Software Bill of Materials Policy)

Status: `PROPOSED`
Owner role: Release owner / security reviewer
Last reviewed: 2026-07-25
Review cadence: Each distributable release and dependency update

## Mục đích (Purpose)

Bản kê thành phần phần mềm (SBOM - Software Bill of Materials) ghi lại tên và phiên bản của các package đã được giải quyết (resolved) cho một môi trường hoặc bản ứng viên phát hành (release candidate). Nó giúp cải thiện việc kiểm toán chuỗi cung ứng; nó không chứng minh sự vắng mặt của các lỗ hổng bảo mật hay cung cấp nguồn gốc xuất xứ có chữ ký số.

## Quy trình Hiện tại (Current Procedure)

Sử dụng công cụ thư viện chuẩn (stdlib) có sẵn trong repository:

```powershell
py -3 scripts/generate_sbom.py --output local_runs/sbom/aios-habit-sbom.json
```

Đầu ra mặc định là dữ liệu runtime (được gitignore). Hãy kiểm tra kỹ trước khi chia sẻ; tuyệt đối không đưa vào chỉ mục package riêng tư, thông tin xác thực, đường dẫn cục bộ hoặc các biến môi trường.

## Xuất bản và Thực thi (Publication and Enforcement)

Việc xuất bản SBOM, yêu cầu định dạng, công cụ quét lỗ hổng bảo mật, ngưỡng mức độ nghiêm trọng, quy trình xử lý ngoại lệ và hành vi chặn merge trong CI ở trạng thái `OWNER_DECISION_REQUIRED` (Yêu cầu quyết định từ chủ sở hữu). Cho đến khi được phê duyệt, việc kiểm tra SBOM/cảnh báo chỉ là bằng chứng phục vụ xem xét thay vì là artifact từ xa bắt buộc.

## Thời gian Lưu trữ (Retention)

Lưu giữ SBOM của các bản phát hành theo chính sách phát hành của chủ sở hữu. Mặc định không đưa chúng vào Git trừ khi chủ sở hữu phê duyệt rõ ràng một quy trình artifact phát hành đã được làm sạch và có thể tái tạo.

