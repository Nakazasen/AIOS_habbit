# Research: 012-ready-hybrid-recall

## Decision: Lệch hệ chữ, không dịch thuật ngữ nghiệp vụ

- **Decision**: Phân `latin` / `cjk` / `mixed` bằng đếm ký tự Unicode. Nếu câu và đa số nguồn khác họ, truy xuất mọi nguồn ready và tăng trọng số dense/sparse.
- **Rationale**: BGE-M3 đã đa ngữ. Cắt lexical 3 nguồn theo token Latin làm mất tài liệu CJK. Dịch “completion→完工” là hardcode ngữ liệu.
- **Alternatives**: LLM dịch câu hỏi (đụng privacy); từ điển MOM/WMS (cấm); GraphRAG (đắt, lệch cổng).

## Decision: Giữ cắt 3 lúc chuẩn bị

- **Decision**: `select_workspace_chat_preparation_scope` không đổi.
- **Rationale**: Nhúng cả sổ vì một câu mơ hồ quá đắt. Truy xuất trên nguồn đã ready rẻ hơn.
- **Alternatives**: Bỏ cắt cả prep — từ chối.

## Decision: Retry một lần khi ≤1 tài liệu

- **Decision**: Nếu fuse xong ≤1 `document_id` và index còn ≥5 tài liệu được phép, tìm lại với hạn mức cao hơn và ranking lệch chữ.
- **Rationale**: Câu quy trình từng chỉ ra 1 đoạn lạc đề.
- **Alternatives**: Luôn lấy 25 chunk — chậm câu hẹp không cần.
