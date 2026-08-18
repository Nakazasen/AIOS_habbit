# Tinh Chỉnh Truy Xuất và Tổng Hợp Nhận Biết Ý Định Cho RAG v2 (RAG v2 Intent-Aware Retrieval and Synthesis Tuning)

Status: `DONE` — `ADVANCE_TO_CANARY_WITH_LIMITATIONS`

## Đường Cơ Sở & Ngữ Cảnh (Baseline & Context)

- **Điểm số đường cơ sở (Baseline Score)**: Bản Dev RAG v2 đạt **3.15/5** so với NotebookLM **4.27/5** trong lượt chạy mù trực tiếp `BATTLE-RAGv2-1785003571-e33e5670`.
- **Dạng lỗi chính (Primary Failure Mode)**: BQ04 (chẩn đoán lỗi) bị chấm điểm **1.0/5** (System A) do trả về các đoạn trích từ vựng BOP thô thay vì các quy trình xử lý sự cố có cấu trúc.
- **Nguyên nhân gốc rễ (Root Cause)**: Tìm kiếm từ vựng BM25/FTS5 ưu tiên quá mức các tài liệu dài có tần suất xuất hiện từ cao hơn là các hướng dẫn quy trình có cấu trúc. Việc tính điểm tín hiệu cộng dồn mà không khớp nghĩa vụ (obligation matching) đã khiến các đoạn văn bản thô vượt mặt các mục hành động cụ thể.

## Ranh Giới Bất Biến Của Cổng (Invariant Gate Boundaries)

1. **Ưu Tiên Cục Bộ & Bảo Mật**: Chỉ truy xuất SQLite cục bộ. Các bộ lọc bảo mật fail-closed chạy trước bất kỳ bước tính điểm hay kết hợp biến thể nào.
2. **Đóng Băng UI Chính**: Luồng truy xuất của Workspace Chat giữ nguyên cho đến khi có sự phê duyệt của chủ sở hữu và đáp ứng tiêu chí chạy lại mù trực tiếp.
3. **Không Gắn Cứng Nghiệp Vụ / Đo Chuẩn**: Tuyệt đối không gắn cứng các ID BQ, tên tệp tài liệu cụ thể hoặc từ khóa đặc thù ngữ liệu vào việc lập kế hoạch truy vấn hay xếp hạng chỉ mục. Tập dữ liệu tinh chỉnh và đánh giá mù được tách biệt nghiêm ngặt.
4. **Cổng Kiểm Toán Độc Lập**: Các thay đổi mã nguồn phải được kiểm toán độc lập trước bất kỳ yêu cầu chạy lại trực tiếp nào.

## Tiêu Chí Mục Tiêu (Goal Criteria)

- Lập kế hoạch truy vấn nhận biết ý định phát hiện các danh mục ý định tổng quát (`diagnosis`, `procedure`, `comparison`, `lookup`, `table`) và các đánh dấu nghĩa vụ (`problem`, `check`, `action`).
- Chấm điểm ứng viên trong `LocalChunkIndex` giảm điểm các đoạn trích quy trình lặp lại thô khi ý định chẩn đoán hoặc quy trình đang hoạt động, đồng thời áp dụng tăng điểm khớp nghĩa vụ.
- Lựa chọn bằng chứng ưu tiên độ bao phủ nghĩa vụ (ví dụ: ghép cặp lỗi + hành động đối với chẩn đoán).
- Hợp đồng tổng hợp cho `diagnosis` bắt buộc phải có các đánh dấu đầu ra có cấu trúc (`SYMPTOMS:`, `CHECKS:`, `ACTIONS:`).
- Kiểm tra tính hợp lệ và dự phòng bảo toàn hình thái câu trả lời có cấu trúc mà không bị suy giảm về các đoạn trích thô.

## Đóng Cổng Gate H — 2026-07-28

- Phòng thí nghiệm truy xuất Gate H và adapter sản xuất của Workspace Chat đã được tích hợp trong workspace chính.
- `bge_m3_hybrid` đã được chọn với Recall@10 đạt `1.000`, MRR@10 đạt `0.620`, và thời gian truy xuất p95 đo được trên CPU ấm là `1.792s`.
- H4 ghi nhận `ADVANCE_TO_CANARY`; đây không phải là tuyên bố tương đương câu trả lời với NotebookLM.
- Các bài kiểm thử tập trung bị ảnh hưởng: **87/87 passed**. Toàn bộ hồi quy: **1094/1094 passed**.
- Kiểm thử E2E trên trình duyệt đạt các kịch bản: hành vi mặc định, canary từ vựng, hoàn tác, phục hồi khi model không khả dụng và chạy lại Streamlit nhiều lần sau khi sửa lỗi đa luồng SQLite.
- Đánh giá chuẩn tắc duy trì các định danh bất đối xứng: 70 tệp kinh doanh cục bộ và 48 nguồn NotebookLM ở trạng thái READY; không tải nguồn lên và không đưa ra tuyên bố tương đương giả mạo.
- Khoảng trống 17 tệp PNG và 2 PDF trống vẫn được nêu rõ và chuyển giao sang cổng phục hồi tập ngữ liệu.
- Trải nghiệm của người dùng thông thường vẫn là luồng hỏi - đáp duy nhất; các chế độ kỹ thuật canary / fallback là các kiểm soát vận hành nội bộ.

## Đóng Cổng và Công Việc Chuyển Giao

Gate H đã được đóng tại [RAG-V2-GATE-H-HYBRID-CANARY.md](completed/RAG-V2-GATE-H-HYBRID-CANARY.md).
Các cổng triển khai được chuyển giao cũng đã được đóng:

1. [RAG-V2-HYBRID-PRODUCTION-ACTIVATION](completed/RAG-V2-HYBRID-PRODUCTION-ACTIVATION.md) đã kích hoạt bộ truy xuất `bge_m3_hybrid` đã được kiểm chứng trên mục tiêu CPU 16 GB được phê duyệt trong khi vẫn bảo toàn ngữ nghĩa hoàn tác fail-closed.
2. [RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY](completed/RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY.md) đã hoàn thành OCR chỉ dùng cục bộ và phục hồi nguồn với kiểm toán nghiêm ngặt `70/70` tệp ngữ liệu có thể sử dụng.

Không có cổng triển khai nào đưa ra tuyên bố tương đương câu trả lời. Theo dõi hoạt động duy nhất là [RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY](completed/RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY.md), nơi đóng băng định danh sản xuất đã kích hoạt và tham chiếu bất biến trước khi chấm điểm độc lập. Nó không thể gắn nhãn lại tập ngữ liệu `local_only` hiện tại hoặc làm lộ bộ chọn chế độ kỹ thuật cho người dùng thông thường.

## Theo Dõi Tính Toàn Vẹn Của Đo Lường — 2026-07-29

Mọi kết quả chất lượng câu trả lời được sử dụng để ưu tiên tinh chỉnh truy xuất trong tương lai bắt buộc phải chứng minh rằng nhánh Workspace được đánh giá đã gọi adapter đã kích hoạt và công khai viễn trắc telemetry backend / profile / fallback hiệu quả đã làm sạch. Chẩn đoán `BQ01/BQ02` đầu tiên đã gọi truy xuất từ vựng cũ mặc dù được gắn nhãn sản xuất; do đó nó chỉ được giữ lại như bằng chứng của nhánh kế thừa. Một cổng khắc phục hai câu hỏi có hỗ trợ adapter chuẩn xác phải hoàn thành trước khi việc tinh chỉnh xếp hạng, bằng chứng, OCR hoặc tổng hợp được xem xét.

