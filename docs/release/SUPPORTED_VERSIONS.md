# Các Phiên Bản và Môi Trường Được Hỗ Trợ (Supported Versions and Environments)

Status: `PROPOSED`
Owner role: Release owner / project owner
Last reviewed: 2026-07-25
Review cadence: Each release candidate or Python/dependency update

## Mức Cơ Sở Đề Xuất (Proposed Baseline)

| Khu vực | Trạng thái đề xuất | Bằng chứng cần thiết trước khi phê duyệt |
|---|---|---|
| Windows 10/11 | Ứng viên môi trường cục bộ được hỗ trợ | Cài đặt sạch + toàn bộ các cổng chất lượng |
| Python 3.11 | Môi trường cơ sở CI | Quy trình làm việc GitHub Actions hiện tại |
| Python 3.12 | Ứng viên | Cài đặt sạch + toàn bộ các cổng chất lượng |
| Python 3.13 | Ứng viên | Bằng chứng môi trường đã kiểm chứng cục bộ |
| macOS/Linux | Chưa cam kết | Quyết định của chủ sở hữu và ma trận kiểm chứng |
| Package registry / Trình cài đặt | Chưa cam kết | ADR về phân phối / quy trình phát hành |

## Chính Sách Hỗ Trợ (Support Policy)

Chỉ những môi trường được thăng cấp rõ ràng lên `APPROVED` sau khi kiểm chứng mới là các cam kết hỗ trợ chính thức. Mã nguồn hiện tại khai báo `requires-python >=3.11`; đó là mức sàn tương thích tối thiểu, không phải bằng chứng cho thấy mọi tổ hợp Python / nền tảng sau này đều được hỗ trợ.

## Cửa Sổ Hỗ Trợ Bảo Mật (Security Support Window)

Khung thời gian bảo trì / cập nhật bảo mật cho các phiên bản phát hành ở trạng thái `OWNER_DECISION_REQUIRED` (Yêu cầu quyết định từ chủ sở hữu). Cho đến khi có quyết định, nhánh `main` / bản ứng viên phát hành hiện tại là dòng phiên bản duy nhất được dự kiến tiếp nhận các bản sửa lỗi.

