# Tổng Hợp Bằng Chứng Tổng Quát Tối Thiểu Cho RAG v2 (RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN)

Status: `DONE`

## Mục Tiêu (Goal)

Bổ sung khả năng xây dựng câu trả lời dựa trên bằng chứng tổng quát có trích dẫn và xử lý trường hợp thiếu dữ liệu bên trong RAG v2, mà không tạo ra giao diện kỹ thuật phức tạp cho người dùng thông thường hay luồng mặc định qua cloud.

## Điều Kiện Tiên Quyết (Prerequisite)

- `RAG-V2-HYBRID-RETRIEVAL-MIN` phải được kiểm chứng — `DONE`.

## Phạm Vi Đã Triển Khai (Implemented Scope)

- Module mới `rag_v2/evidence.py`, hoàn toàn độc lập khỏi các module cũ `rag_evidence.py`, `rag_search.py`, và `query_intent.py`.
- Các kiểu dữ liệu tổng quát: `EvidencePackConfig`, `EvidenceConfidence` (enum), `EvidenceItem`, `PrivacySummary`, `EvidencePack`.
- `build_evidence_pack(query, response, config)`: chuyển đổi `SearchResponse` thành `EvidencePack` với các trích dẫn được đánh số `[1]`, `[2]`..., cắt tỉa đoạn trích, đánh giá độ tin cậy có thể cấu hình, giới hạn theo từng tài liệu và tóm tắt bảo mật theo quy tắc nghiêm ngặt nhất (strictest-wins).
- `format_evidence_for_prompt(pack)`: khối văn bản thuần với trích dẫn, tên/vị trí nguồn, điểm số, đoạn trích, cảnh báo thiếu bằng chứng và thông báo bảo mật. Sử dụng ngôn ngữ trung lập (tiếng Anh) cho phần lõi tổng quát.
- `evidence_pack_to_dict(pack)`: tuần tự hóa tương thích JSON với chuyển đổi đệ quy từ tuple sang list.
- Độ tin cậy được tính toán từ các lý do thiếu dữ liệu của `SearchSummary` truy xuất cộng với các ngưỡng điểm số / độ bao phủ có thể cấu hình (mặc định: cao ≥ 8.0, trung bình ≥ 3.0).
- Các lý do thiếu bằng chứng được truyền từ tóm tắt truy xuất và bổ sung các kiểm tra cấp bằng chứng: `no_evidence_items`, `top_score_below_threshold`, `too_few_evidence_items`, `weak_term_coverage`.
- Bảo mật: quy tắc nghiêm ngặt nhất áp dụng trên toàn bộ các mục; chỉ cần một mục là `local_only`/`confidential` sẽ biến toàn bộ gói bằng chứng thành `local_only`.

## Bằng Chứng Nghiệm Thu (Acceptance Evidence)

- Kiểm thử bằng chứng tập trung + chốt chặn mã cứng: **15 passed** in 0.19s.
- Hợp đồng tài liệu: PASS.
- Biên dịch: PASS.
- Toàn bộ bộ kiểm thử: **921 passed** in 45.98s.
- Kiểm toán CLI audit: PASS, không có lỗi hay cảnh báo.
- Import Workspace Chat: PASS (chỉ có cảnh báo bare-mode của Streamlit như kỳ vọng).
- `git diff --check`: PASS.
- Chốt chặn mã cứng (`test_rag_v2_hardcode_guard.py`): PASS; không có thuật ngữ được bảo vệ nào trong mã nguồn hoặc chú thích của RAG v2.

## Các Loại Trừ Rõ Ràng (Explicitly Excluded)

- Không thay đổi UI Workspace Chat hay di chuyển runtime.
- Không có lệnh gọi mạng/cloud/provider, credential, hay dependency mới.
- Không import từ các module cũ `rag_evidence.py`, `rag_search.py`, hay `query_intent.py`.
- Không có thuật ngữ đặc thù ngành trong mã nguồn hay chú thích.
- Không có bộ tạo câu trả lời (answer composer / response generator) — cổng này chỉ tạo các gói bằng chứng (evidence pack).

## Tài Liệu Tham Khảo (References)

- Kiến trúc: `docs/rag_v2/RAG_V2_DESIGN.md` phần 11–12.
- Mẫu thiết kế: Haystack `DocumentJoiner`, LlamaIndex `QueryFusionRetriever`, module kế thừa `rag_evidence.py` (tham khảo, không import).

