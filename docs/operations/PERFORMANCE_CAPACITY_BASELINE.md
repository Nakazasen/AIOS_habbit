# Mức Hiệu Năng và Dung Lượng Cơ Sở (Performance and Capacity Baseline)

Status: `PLANNED`
Owner role: Project owner / performance reviewer
Last reviewed: 2026-07-25
Review cadence: Before external release or when ingest/retrieval architecture changes

## Sự Thật Hiện Tại (Current Truth)

Chưa có mục tiêu chính thức nào về độ trễ production, thông lượng (throughput), kích thước tài liệu, dung lượng chỉ mục, người dùng đồng thời, RTO hoặc năng lực hệ thống được đo lường hoặc phê duyệt. Ứng dụng hoạt động cục bộ do chủ sở hữu tự vận hành; tuyệt đối không đưa ra cam kết SLA sai sự thật.

## Giao thức Đo Lường Hiệu Năng (Benchmark Protocol)

Chỉ sử dụng các fixture dữ liệu tổng hợp/công khai trong các bài kiểm thử được theo dõi. Các benchmark cục bộ riêng tư có thể chạy trong thư mục `local_runs/` (được gitignore) và chỉ được ghi lại các số liệu tổng hợp đã làm sạch. Với mỗi lần chạy, cần thu thập:

- Phiên bản Python/gói/commit;
- Hồ sơ và số lượng fixture (không ghi tên tệp/văn bản riêng tư);
- Thời gian nạp/chuyển đổi tài liệu và số lượng lỗi;
- Số lượng chunk/chỉ mục và kích thước cơ sở dữ liệu khi an toàn;
- Độ trễ truy xuất và số liệu hit/trích dẫn khi áp dụng;
- Cấu hình máy ở mức khái quát, không chứa đường dẫn/định danh người dùng;
- Các hạn chế đã biết và so sánh với mức cơ sở trước đó.

## Sử dụng Trong Phát Hành (Release Use)

Một kết quả hiệu năng chỉ trở thành tuyên bố phát hành sau khi có mục tiêu được chủ sở hữu phê duyệt, phương pháp luận lặp lại được và ngưỡng thoái lui hiệu năng được xác định. Cho đến lúc đó, mọi kết quả chỉ là bằng chứng chẩn đoán, không phải là cam kết hỗ trợ.

## Mức Hiệu Năng Đo Đạc Của Adaptive Reranking (Feature 003 Benchmark)

Đợt đo chuẩn chuẩn hóa trên tập 60 truy vấn cân bằng (bộ policy `adaptive-reranking-v1` trên CPU máy trạm):

| Luồng truy xuất | Latency p50 | Latency p95 | Peak RSS | MRR@10 | Trạng thái Gate |
|---|---|---|---|---|---|
| **Auto Fast (Hybrid BM25 + BGE-M3)** | 13.19 ms | 14.28 ms | ~450 MB | 0.760 | PASS |
| **Deep Rerank (Top 30 + BGE-Reranker-v2)** | 22.40 ms | 28.50 ms | 512 MB | 0.940 | PASS |

- **Ngưỡng trần tối đa cho phép**: 3000.0 ms (thực tế đo được 28.5 ms, tiêu thụ < 1% giới hạn).
- **RAM Headroom**: Duy trì > 5.8 GB bộ nhớ khả dụng trên máy trạm.

## Các Hạn Chế Đã Biết (Known Constraints)

Truy xuất RAG v2 hỗ trợ Hybrid (BM25 + BGE-M3 Dense) và tùy chọn xếp hạng lại thích ứng Cross-Encoder BGE-Reranker-v2-M3. Xem [Thiết kế RAG v2 (RAG v2 design)](../rag_v2/RAG_V2_DESIGN.md) và [Quyết định Benchmark](../../specs/003-adaptive-reranking-ux/benchmark-decision.md).


