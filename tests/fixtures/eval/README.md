# Bộ đề & Thước đo kiểm thử chất lượng (Eval Fixtures)

Thư mục này chứa bộ câu hỏi chuẩn hóa và rubric chấm điểm dùng để đo lường, kiểm thử hồi quy và đối sánh chất lượng giữa các lane (RAG, C-Agent) trong hệ thống AIOS.

## 1. Nguồn gốc và xuất xứ dữ liệu

- **Bộ 50 câu hỏi (`lsu_quality_50_questions.json`):**
  - **Xuất xứ ban đầu:** Trích xuất từ 1.790 cặp Q&A thực tế trong `wire-qa-mapping.jsonl` tại vé `PREP-LSU-QUALITY-PC0575` (2026-10-06).
  - **Cơ cấu nghiệp vụ:** Phủ đều 4 nhóm nghiệp vụ chính của cụm LSU (13 câu Mã lỗi, 12 câu Nguyên nhân, 12 câu Đối sách, 13 câu Thông số kỹ thuật).
  - **Chuẩn hoá từ khóa:** Đã được rà soát và đính chính 4 từ khóa lỗi tại vé `RUBRIC-NORMALIZE-PC0575` (2026-10-07):
    - `Q0630`: Đổi `['DRUM.', 'DRUM.', 'LSU_2019.01.18_K.']` thành `['quét ngang', 'quay drum']`.
    - `Q0635`: Đổi `['LSU_2019.01.18_K.']` thành `['quang lượng tâm', 'vùng biên', 'nhạt màu']`.
    - `Q0674`: Đổi `['OK']` thành `['không bất thường', 'không thay đổi']`.
    - `Q0708`: Đổi `['1.15 mm以上', '1.24以上']` thành `['1.15', '1.24']`.
  - Toàn bộ 46 câu còn lại giữ nguyên 100% từ khóa gốc.

- **Rubric đánh giá (`lsu_quality_rubric.json`):**
  - Gồm 2 tiêu chí theo chuẩn chất lượng:
    1. `chinh_xac` (tối đa 2.0 điểm): Độ chính xác nội dung kỹ thuật dựa trên tỷ lệ khớp từ khóa sau khi qua hàm chuẩn hóa `normalize_text_for_eval`.
    2. `trich_dan` (tối đa 1.0 điểm): Kiểm chứng xem câu trả lời có trích dẫn nguồn tài liệu hợp lệ (`.xlsx`, `.pptx`, `.pdf`, v.v.).
  - Tổng điểm tối đa mỗi câu: **3.0 điểm** (thang điểm 0–3 chuẩn hóa, GPA = tổng điểm / 50).

## 2. Mục đích lưu trữ trong repo

- Đóng dấu thước đo vào kiểm soát phiên bản Git tại vé `RETRIEVAL-ENTITY-PC0575` (Bước 0) theo yêu cầu kiến trúc.
- Đảm bảo các kết quả đo lường và đánh giá chất lượng có thể **tái lập 100%** từ mã nguồn repo mà không phụ thuộc vào các tệp nằm ngoài repo (`local_cases/`).
