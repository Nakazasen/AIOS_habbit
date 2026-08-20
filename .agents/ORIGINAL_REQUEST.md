# Original User Request

## 2026-08-19T23:43:03Z

Triển khai gói sửa đổi và nâng cấp toàn diện cho hệ thống MOM trong dự án AIOS_habbit: loại bỏ hoàn toàn các điểm hardcode/heuristic cũ trong tìm kiếm, nâng cấp bộ trích xuất Excel sang streaming chunking cho file lớn, chuẩn hóa cơ chế tự động từ chối trả lời (dynamic abstention), và bảo đảm hệ thống vận hành thực tế vững chắc với 100% test suite vượt qua.

Working directory: d:\Sandbox\AIOS_habbit
Integrity mode: development

## Requirements

### R1. Loại Bỏ Hoàn Toàn Hardcode & Heuristics trong MOM Search
- Xóa bỏ triệt để các danh sách từ khóa cố định (`q1_terms`, `q2_terms`, `q3_terms`), các lệnh cộng điểm nhân tạo và lệnh trừ điểm `-50.0` nhắm vào tệp `erd_kho_van_new.html` trong `src/aios_habit/mom_local_index.py`.
- Chuẩn hóa thuật toán xếp hạng sang BM25 / TF-IDF khách quan hoặc liên kết với RAG v2 Hybrid Retrieval để bảo đảm chấm điểm công bằng cho mọi câu hỏi thực tế.

### R2. Nâng Cấp Bộ Trích Xuất Excel Sang Streaming Chunking
- Trong `src/aios_habit/excel_extractors.py`: Loại bỏ giới hạn cứng 1,000 dòng/sheet và 20,000 ô.
- Triển khai cơ chế phân đoạn theo dòng dạng luồng (streaming row-chunking, chia khối dòng kèm header lặp lại ở mỗi chunk) giúp trích xuất trọn vẹn các file bảng tính sản xuất lớn (BOM, vật tư, kế hoạch) mà không bị cắt cụt hay quá tải bộ nhớ.

### R3. Chuẩn Hóa Cơ Chế Tự Động Từ Chối Trả Lời & Xóa Bỏ Canned Answers
- Trong `scripts/generate_ai_grounded_report.py` và `scripts/run_workspace_chat_12_questions.py`: Xóa bỏ từ điển `POLISHED_ANSWERS` và các chuỗi từ chối gán cứng.
- Tích hợp trực tiếp logic của `ClaimGuard` và engine trích xuất để hệ thống tự động sinh câu trả lời hoặc từ chối dựa trên bằng chứng thực tế tìm được.

### R4. Kiểm Thử Toàn Diện & Đảm Bảo Không Hồi Quy (Zero Regression)
- Bổ sung và cập nhật test suites trong `tests/` để kiểm chứng:
  1. Thuật toán tìm kiếm MOM không chứa hardcode và tìm kiếm chính xác trên các câu hỏi mới.
  2. Bộ trích xuất Excel xử lý trọn vẹn bảng tính lớn vượt ngưỡng 1,000 dòng.
  3. Toàn bộ test suite `pytest` chạy pass 100%.

## Acceptance Criteria

### Xác minh Mã Nguồn (Code Verification)
- [ ] Không còn bất kỳ từ khóa `q1_terms`, `q2_terms`, `q3_terms`, hay lệnh trừ điểm `-50.0` nào trong `src/aios_habit/mom_local_index.py`.
- [ ] `excel_extractors.py` có hàm streaming chunking và loại bỏ giới hạn cắt cụt 1,000 dòng.
- [ ] `scripts/generate_ai_grounded_report.py` không còn biến `POLISHED_ANSWERS` hardcode.

### Xác minh Kiểm thử (Automated Tests)
- [ ] Viết test tự động xác nhận bảng tính Excel > 1,500 dòng được trích xuất đầy đủ các chunk.
- [ ] Chạy `pytest tests/` đạt 100% PASS (Zero Failures / Zero Errors).

## 2026-08-20T13:27:39Z

Tiếp tục thực hiện nhiệm vụ theo Checkpoint đã lưu (mem_mt0r1m76_ab623e4a6f0f):
Triển khai gói sửa đổi và nâng cấp toàn diện cho hệ thống MOM trong dự án AIOS_habbit:
1. R1: Loại bỏ hoàn toàn các điểm hardcode/heuristic cũ trong tìm kiếm (`mom_local_index.py`), loại bỏ q1_terms, q2_terms, q3_terms, điểm bonus nhân tạo và trừ điểm -50.
2. R2: Nâng cấp bộ trích xuất Excel sang streaming chunking cho file lớn (>1000 dòng) trong `excel_extractors.py`.
3. R3: Chuẩn hóa cơ chế tự động từ chối trả lời (dynamic abstention) và xóa canned answers (`POLISHED_ANSWERS`) trong `scripts/generate_ai_grounded_report.py` và `scripts/run_workspace_chat_12_questions.py`.
4. R4: Kiểm thử toàn diện và bảo đảm 100% test suite `pytest tests/` vượt qua mà không hồi quy.

Working directory: d:\Sandbox\AIOS_habbit
Integrity mode: development
Requested team: Full Engineering Swarm

Thực hiện và nghiệm thu qua quy trình Victory Audit độc lập.

