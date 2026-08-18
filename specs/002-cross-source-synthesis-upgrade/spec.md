# Đặc Tả Tính Năng: Nâng Cấp Tổng Hợp Đa Tài Liệu Xuyên Nguồn (>5 Tài Liệu) (Feature Specification: Cross-Source Multi-Document Synthesis Upgrade)

**Trạng thái**: `IMPLEMENTED_PENDING_CURRENT_FULL_SUITE — 2026-08-16`

## Tuyên Bố Vấn Đề (Problem Statement)

Các hệ thống RAG truyền thống đối mặt với sự suy giảm recall và hiện tượng từ chối trả lời sai (false insufficiency) trên các câu hỏi yêu cầu tổng hợp xuyên suốt >5 tài liệu do giới hạn chunk thấp cố định (mặc định 10 chunk) và thiên kiến từ vựng / dense của truy vấn đơn lẻ.

## Yêu Cầu (Requirements)

- **FR-001 (Phát hiện ý định & Ngân sách động):** Bộ lập kế hoạch truy vấn phải phát hiện các truy vấn tổng hợp xuyên nguồn và tự động mở rộng ngân sách chunk truy xuất lên tới 25 chunk và giới hạn trên mỗi tài liệu lên 5.
- **FR-002 (Phân rã đa truy vấn):** Phân rã các câu hỏi đa khía cạnh thành tối đa 3 truy vấn con chuyên biệt kết hợp khử trùng lặp theo xếp hạng tương hỗ (RRF - Reciprocal Rank Fusion).
- **FR-003 (Nhận biết tóm tắt cấp tài liệu):** Ưu tiên các phần tử kiến trúc và tổng quan tài liệu trong quá trình chọn ứng viên cho các câu hỏi tổng quan rộng.
- **FR-004 (Tương thích ngược & Hiệu năng):** Các câu hỏi tra cứu đơn lẻ phải duy trì độ trễ dưới 1 giây và ngân sách chunk hẹp.

## Tiêu Chí Nghiệm Thu (Acceptance Criteria)

- Các bài kiểm thử đơn vị xác minh việc phân rã truy vấn, mở rộng ngân sách động và hợp nhất RRF.
- Toàn bộ bộ kiểm thử cuối cùng phải đạt mà không có hồi quy; ghi nhận số lượng hiện tại và kết quả lệnh lúc đóng cổng thay vì nhúng một số lượng kiểm thử dự đoán.
- Đánh giá trên BQ02, BQ07, và BQ10 chứng minh độ bao phủ đa tài liệu được mở rộng mà không có hiện tượng ảo giác (hallucination).

