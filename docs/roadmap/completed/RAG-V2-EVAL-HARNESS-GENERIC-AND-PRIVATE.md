# Khung Đánh Giá RAG v2 Tổng Quát và Riêng Tư (RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE)

Status: `DONE`

## Mục Tiêu (Goal)

Xây dựng một khung đánh giá tổng quát, chỉ chạy cục bộ bên trong RAG v2 nhằm đo lường chất lượng truy xuất và bằng chứng với các chỉ số cụ thể.

## Điều Kiện Tiên Quyết (Prerequisite)

- `RAG-V2-HYBRID-RETRIEVAL-MIN` phải được kiểm chứng — `DONE`.
- `RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN` phải được kiểm chứng — `DONE`.

## Phạm Vi Đã Triển Khai (Implemented Scope)

- Module mới `rag_v2/eval_harness.py`, độc lập hoàn toàn khỏi các module cũ `rag_benchmark.py`, `rag_evaluator.py`, `rag_search.py`, và `query_intent.py`.
- Các kiểu dữ liệu tổng quát: `BenchmarkConfig`, `BenchmarkQuestion`, `BenchmarkResult`, `BenchmarkSummary`.
- `run_benchmark(index, questions, config)`: runner toàn bộ đường ống thực thi `LocalChunkIndex.search_with_summary()` → `build_evidence_pack()` → chấm điểm.
- Các chỉ số: tỷ lệ trúng truy xuất, tỷ lệ trúng tài liệu, tỷ lệ trúng nguồn trích dẫn, tỷ lệ phát hiện thiếu dữ liệu, tỷ lệ đạt bảo mật, độ trễ trung bình.
- Kiểm tra các thuật ngữ bị cấm trong các đoạn trích bằng chứng.
- ID benchmark ổn định, có tính tái lập từ mã băm của bộ câu hỏi + cấu hình.
- `format_benchmark_summary(summary)`: báo cáo văn bản thân thiện với con người.
- `benchmark_summary_to_dict(summary)`: tuần tự hóa tương thích JSON.
- Kết luận PASS / FAIL / PASS_WITH_WARNINGS từ các ngưỡng có thể cấu hình.

## Bằng Chứng Nghiệm Thu (Acceptance Evidence)

- Kiểm thử đánh giá tập trung + chốt chặn mã cứng: **11 passed** in 0.37s.
- Hợp đồng tài liệu: PASS.
- Biên dịch: PASS.
- Toàn bộ bộ kiểm thử: **931 passed** in 25.45s.
- Kiểm toán CLI audit: PASS, không có lỗi hay cảnh báo.
- Import Workspace Chat: PASS (chỉ có cảnh báo bare-mode của Streamlit như kỳ vọng).
- Chốt chặn mã cứng (`test_rag_v2_hardcode_guard.py`): PASS; không có thuật ngữ được bảo vệ nào bị vi phạm.

## Các Loại Trừ Rõ Ràng (Explicitly Excluded)

- Không thay đổi UI Workspace Chat hay di chuyển runtime.
- Không có lệnh gọi cloud/provider/LLM, credential, hay dependency mới.
- Không import từ các module benchmark/evaluator/search/intent cũ.
- Không có thuật ngữ đặc thù ngành trong mã nguồn hay chú thích.
- Không commit tập dữ liệu riêng tư vào Git.
- Chỉ số độ trung thực câu trả lời được tạm hoãn (yêu cầu giám khảo LLM — cổng tương lai).

## Tài Liệu Tham Khảo (References)

- Kiến trúc: `docs/rag_v2/RAG_V2_DESIGN.md` phần 13.
- Mẫu kế thừa: `rag_benchmark.py` (tham khảo, không import trực tiếp).

