# Kế Hoạch Triển Khai: Nâng Cấp Tổng Hợp Đa Tài Liệu Xuyên Nguồn (Implementation Plan: Cross-Source Multi-Document Synthesis Upgrade)

## Các Trụ Cột Kiến Trúc (Architectural Pillars)

1. **Ngân Sách Chunk Động:** Mở rộng các giới hạn chunk động dựa trên ý định truy vấn trong `query_planning.py`, `index.py`, và `evidence.py`.
2. **Phân Rã Đa Truy Vấn:** Tạo 2-3 biến thể truy vấn cho các câu hỏi đa hệ thống và hợp nhất kết quả tìm kiếm sử dụng RRF.
3. **Độ Bền Vững Của Tổng Hợp Bằng Chứng:** Ngăn chặn các kích hoạt từ chối trả lời sai trên các câu hỏi có độ bao phủ rộng.

