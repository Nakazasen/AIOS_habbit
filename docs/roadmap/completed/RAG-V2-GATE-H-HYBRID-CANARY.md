# Kiểm Thử Canary Kết Hợp Cho Gate H RAG v2 (RAG-V2-GATE-H-HYBRID-CANARY)

Status: `DONE`

## Mục Tiêu (Goal)

Lựa chọn cấu hình truy xuất cục bộ mạnh nhất, tích hợp an toàn vào Workspace Chat và chứng minh bản canary sản xuất mà không làm phức tạp hóa trải nghiệm của người dùng thông thường.

## Phạm Vi Đã Hoàn Thành (Completed Scope)

- Đánh giá các cấu hình từ vựng (lexical), dense BGE-M3, hybrid BGE-M3, rerank và mở rộng cha (parent-expansion) trên tập ngữ liệu cục bộ đóng băng.
- Đã lựa chọn `bge_m3_hybrid`: Recall@10 đạt `1.000`, MRR@10 đạt `0.620`, độ trễ truy xuất p95 đo được trên CPU sau khi sẵn sàng là `1.792s`.
- Hoàn thành H4 với kết luận `ADVANCE_TO_CANARY`.
- Bổ sung adapter cho Workspace Chat, xác thực ghim phiên bản mô hình (model-pin), vòng đời nguồn/chỉ mục, viễn trắc telemetry, dự phòng bảo toàn quyền riêng tư và hoàn tác.
- Sửa lỗi tái sử dụng đường ống SQLite có cache xuyên suốt các luồng chạy lại của Streamlit.

## Hành Vi Sản Phẩm (Product Behavior)

Luồng người dùng thông thường vẫn là một đường dẫn đơn giản duy nhất:

```text
Mở Workspace Chat → chọn nguồn dữ liệu → đặt câu hỏi → nhận câu trả lời tốt nhất có bằng chứng xác thực
```

Các cờ canary và các giai đoạn dự phòng là kiểm soát vận hành nội bộ, không phải là lựa chọn dành cho người dùng thông thường. Một phương án dự phòng bị suy giảm tính năng tuyệt đối không được âm thầm giả mạo là bộ truy xuất chất lượng cao đã chọn.

## Bằng Chứng Đóng Cổng (Closure Evidence)

- Bộ kiểm thử hồi quy tập trung bị ảnh hưởng: **87/87 passed**.
- Toàn bộ bộ kiểm thử repository: **1094/1094 passed**.
- Kiểm thử E2E trên trình duyệt đạt các kịch bản: mặc định, canary từ vựng, hoàn tác, dự phòng khi thiếu mô hình và 3 lần chạy lại Streamlit liên tiếp.
- Log sau khi sửa lỗi không chứa lỗi đa luồng SQLite và không có lỗi dự phòng từ vựng.
- Các ranh giới bảo mật, sự đồng ý, làm sạch và provider của Brain Gateway giữ nguyên vẹn.

## Quyết Định Đóng Cổng (Closure Decision)

Gate H hoàn thành với kết luận **`ADVANCE_TO_CANARY_WITH_LIMITATIONS`**.

Điều này cho phép một cổng kích hoạt sản xuất có kiểm soát. Nó **không** xác lập tính tương đương câu trả lời tự sinh với NotebookLM và không cho phép chuyển đổi mặc định âm thầm.

## Các Giới Hạn Còn Lại Được Chuyển Tiếp

- 17 nguồn PNG vẫn chưa được hỗ trợ nếu không có OCR.
- Hai nguồn PDF bị trống và yêu cầu phục hồi nguồn hoặc loại trừ rõ ràng.
- Ghim mô hình triển khai cuối cùng, thời gian khởi động lạnh (cold-start), mức sử dụng bộ nhớ, độ ổn định câu trả lời và nghiệm thu triển khai phải được kiểm chứng trên dòng laptop CPU 16 GB mục tiêu.
- Tính tương đương câu trả lời cùng giao thức với NotebookLM vẫn chưa được chứng minh.

## Hoàn Tác (Rollback)

Vô hiệu hóa cấu hình canary RAG v2 nội bộ của Workspace Chat để duy trì luồng truy xuất cũ. Chỉ mục runtime và các artifact mô hình có thể tái tạo, nằm cục bộ và ngoài hệ thống quản lý phiên bản.

## Liên Kết Bằng Chứng (Evidence Links)

- `docs/roadmap/RAG-V2-INTENT-RETRIEVAL-SYNTHESIS-TUNING.md`
- `src/aios_habit/workspace_chat_rag_v2_adapter.py`
- Bằng chứng runtime riêng tư nằm dưới thư mục `local_runs/` bị gitignore.

