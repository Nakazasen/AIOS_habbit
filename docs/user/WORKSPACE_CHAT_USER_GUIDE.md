# Hướng Dẫn Sử Dụng Workspace Chat (Workspace Chat User Guide)

Status: `ACTIVE`
Owner role: Project owner / UI reviewer
Last reviewed: 2026-07-25
Review cadence: Before supported user-flow or privacy-copy changes

## Chức năng của Workspace Chat (What Workspace Chat does)

Workspace Chat là giao diện người dùng được hỗ trợ chính thức của AIOS WorkLens. Nó giúp bạn tổ chức các nguồn dữ liệu cục bộ, đặt câu hỏi bằng ngôn ngữ tự nhiên và kiểm tra trực tiếp ngữ cảnh nguồn trước khi tin tưởng vào câu trả lời.

## Luồng Sử Dụng Cơ Bản (Basic Flow)

1. Khởi động qua `RUN_AIOS_WORKSPACE_CHAT.bat` hoặc `scripts/run_workspace_chat.ps1`.
2. Tạo mới hoặc chọn một sổ ghi chép (notebook).
3. Thêm/dán/chọn một nguồn dữ liệu và cẩn thận chọn nhãn bảo mật phù hợp cho nó.
4. Chỉ bật (enable) các nguồn dữ liệu thực sự liên quan đến cuộc trò chuyện hiện tại.
5. Đặt câu hỏi bằng ngôn ngữ tự nhiên và kiểm tra ngữ cảnh nguồn / trích dẫn (citations).
6. Nếu câu trả lời cho biết chưa đủ bằng chứng (insufficient evidence), hãy thêm/chọn các nguồn dữ liệu tốt hơn thay vì mặc định xem câu trả lời là tuyệt đối chắc chắn.

## Các Nhãn Bảo Mật (Privacy Labels)

| Nhãn | Ý nghĩa |
|---|---|
| Chỉ dùng cục bộ (`local_only`) | Tuyệt đối không bao giờ gửi nguồn này tới provider AI bên ngoài. |
| Bảo mật (`confidential`) | Tuyệt đối không bao giờ gửi nguồn này tới provider AI bên ngoài. |
| Cần xác nhận chủ sở hữu (`machine_only`) | Tuyến gửi ra ngoài cần sự xác nhận đồng ý hợp lệ từ chủ sở hữu. |
| Chưa phân loại (`unknown`) | Tuyến gửi ra ngoài bị chặn cho đến khi được phân loại / xác nhận hợp lệ. |
| Cho phép gửi AI cloud (`cloud_safe`) | Có thể đủ điều kiện gửi qua tuyến bên ngoài tùy chọn sau khi qua các bước kiểm tra chính sách. |
| Công khai (`public`) | Có thể đủ điều kiện gửi qua tuyến bên ngoài tùy chọn sau khi qua các bước kiểm tra chính sách. |

## Khi Gặp Sự Cố (If Something Goes Wrong)

- Nguồn bị thiếu / không được sử dụng: trước tiên hãy kiểm tra lại sổ ghi chép, cuộc trò chuyện và các nguồn đang được bật chọn.
- Trích xuất tệp thất bại: giữ tệp hoàn toàn ở cục bộ và đọc thông báo Tiếng Việt; không dán tệp vào dịch vụ khác như một giải pháp tạm bợ.
- Dịch vụ AI tùy chọn thất bại: luồng làm việc với nguồn cục bộ vẫn hoạt động bình thường; chỉ thử lại sau khi kiểm tra mạng/cấu hình mà không làm lộ API key.
- Tuyệt đối không đưa tài liệu riêng tư, ảnh chụp màn hình, dữ liệu chat hay thông tin xác thực vào Git.

Về quy trình khôi phục vận hành, xem [cẩm nang vận hành (Operator runbook)](../OPERATOR_RUNBOOK.md).

