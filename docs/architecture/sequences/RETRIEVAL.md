# Trình tự: Truy xuất Cục bộ (Local Retrieval)

Status: `ACTIVE`
Owner role: Project owner / RAG architecture reviewer
Last reviewed: 2026-07-25
Review cadence: Before changing chunking, index storage or ranking behavior

```mermaid
sequenceDiagram
    participant UI as Workspace Chat
    participant AD as Adaptive Gate (Pre/Post)
    participant R as Điều phối truy xuất (Retrieval orchestration)
    participant C as Bộ chuyển đổi / cắt đoạn (Converter/chunker)
    participant I as Chỉ mục LocalChunkIndex (BM25 + Dense)
    participant RK as BGE Reranker (Subprocess Worker)

    UI->>AD: Đặt câu hỏi + Tùy chọn tìm kiếm (Tự động / Tìm kỹ hơn)
    AD->>R: Phân loại Pre-Gate (Fast / Deep / Uncertain)
    R->>C: Chuyển đổi / cắt đoạn khi cần
    C->>I: Cập nhật chunk cục bộ
    R->>I: Truy xuất Hybrid (BM25 + BGE-M3 Dense)
    I-->>R: Top 30 ứng viên sơ tuyển
    alt User chọn Tìm kỹ hơn HOẶC Pre-Gate Deep HOẶC Post-Gate Thiếu bằng chứng
        R->>RK: Xếp hạng lại (Cross-Encoder BGE-Reranker-v2)
        RK-->>R: Top kết quả tinh lọc chính xác cao
    else Fast Path (Tự động + Bằng chứng đầy đủ)
        R->>R: Bỏ qua Reranker (Tiết kiệm CPU/RAM)
    end
    R-->>UI: Bằng chứng ngữ cảnh an toàn + Thông điệp minh bạch
```

Nền tảng RAG v2 hỗ trợ truy xuất thích ứng 2 tầng (2-Stage Adaptive Reranking) kết hợp BM25 + Dense BGE-M3 và Cross-Encoder BGE-Reranker-v2-M3. Hệ thống có Circuit Breaker tự ngắt sau 3 lỗi liên tiếp và hạ cấp trong suốt về Hybrid khi backend reranker bận/quá tải.

## Các Bản ghi Liên quan (Related Records)

- [Thiết kế RAG v2 (RAG v2 design)](../../rag_v2/RAG_V2_DESIGN.md)
- [ADR-0003](../../adr/0003-local-sqlite-lexical-index.md)
- [Hướng dẫn Vận hành Adaptive Reranking](../../../specs/003-adaptive-reranking-ux/operations-guide.md)
- [Mức hiệu năng cơ sở (Performance baseline)](../../operations/PERFORMANCE_CAPACITY_BASELINE.md)


