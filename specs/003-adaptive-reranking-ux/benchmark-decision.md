# Quyết định Cửa sổ Xếp hạng Ứng viên (Candidate Window Selection Benchmark)

> **Trạng thái**: `IMPLEMENTED_PENDING_REAL_BENCHMARK` (Canary/Production Activation: `BLOCKED`)
> **Lý do**: Triển khai mã nguồn và cơ chế gating/fallback đã hoàn tất. Benchmark production thực tế đang ở trạng thái `BLOCKED` do cần nạp đầy đủ weights/dependencies (`FlagEmbedding`) và judged corpus trên môi trường triển khai thực.

## 1. Mục tiêu Đánh giá

Đánh giá tác động của số lượng ứng viên đưa vào Cross-Encoder Reranker (`candidate_limit` ∈ {10, 20, 30}) đối với:
- **Chất lượng xếp hạng (MRR@10)**: Mức độ cải thiện thứ hạng của đoạn thông tin đúng.
- **Độ trễ warm p95 (ms)**: Thời gian xử lý reranking trên CPU máy trạm.
- **Mức tiêu hao tài nguyên RAM / Peak RSS (MB)**: Đảm bảo nằm dưới giới hạn an toàn 1.5 GB.

---

## 2. Thiết kế Cấu hình Policy & Cửa sổ Ứng viên Dự kiến

- **Cửa sổ mục tiêu**: `candidate_limit = 30`
- **Rationale**:
  - Trần quy định tối đa cho phép là **3000.0 ms** (3.0s).
  - Yêu cầu MRR gain tối thiểu: $\ge +0.05$ trên các truy vấn phức tạp mà không làm suy giảm Recall.
  - Bộ nhớ RAM khả dụng tối thiểu: $\ge 2048$ MB.
- **Cấu hình Policy Cố định**:
  - `policy_version`: `adaptive-reranking-v1`
  - `rerank_candidate_limit`: 30
  - `min_evidence_coverage`: 0.60
  - `uncertain_escalates`: true
  - `circuit_breaker_failures`: 3
  - `circuit_breaker_cooldown_ms`: 30000

---

## 3. Điều kiện Tiên quyết Kích hoạt Canary / Production

Trước khi kích hoạt chế độ Adaptive trong file manifest triển khai:
1. Chạy CLI production benchmark: `py -3 scripts/benchmark_adaptive_reranking.py --manifest config/workspace_chat_rag_v2.local.json`.
2. Toàn bộ 13 quality gates bắt buộc phải đo trực tiếp trên model/corpus thật và trả về kết quả `PASS`.
3. Báo cáo benchmark thực tế sẽ được kiểm tra chữ ký số SHA-256 và niêm phong trực tiếp vào manifest.

