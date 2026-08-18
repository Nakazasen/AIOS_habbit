# Baseline Summary: BGE-M3 Hybrid (T004)

**Date**: 2026-08-16  
**Profile**: `bge_m3_hybrid`  
**Platform**: Windows-10 64-bit (16 GB Total RAM)  
**Raw Artifact**: `local_runs/adaptive_reranking/baseline_raw.json`  
**Dataset Reference**: `tests/fixtures/adaptive_routing_cases.json` (`SHA256: e2698883157c1d3d108df372174a573a95cb1620fd689871a6f6223830641da6`)

## 1. Metric Baseline

| Metric | Measured Baseline | Target Constraint / Threshold |
|---|---|---|
| Sample Count | 50 queries | >= 50 queries |
| p50 Latency | 13.19 ms | Fast interactive baseline |
| p95 Latency | 14.28 ms | Baseline reference for Auto-fast regression (<= 10%) |
| Min Latency | 12.25 ms | - |
| Max Latency | 14.71 ms | - |
| Process RSS | 15.82 MB (pre-heavy) | Model worker bound |
| Available System RAM | 5,867.39 MB (~5.87 GB) | Minimum required: >= 2,048 MB (2 GB) |
| Total System RAM | 16,293.29 MB (16 GB) | Target Reference Machine |

## 2. Observations & Constraints

- Hệ thống có ~5.87 GB RAM khả dụng, thỏa mãn ngưỡng tối thiểu 2 GB cho việc chạy BGE-M3 Hybrid kết hợp reranker cục bộ.
- P95 baseline cho Hybrid là ~14.28 ms; khi chạy Auto fast path, p95 không được vượt quá 10% ngưỡng này cộng chi phí pre-gate evaluation (tổng budget < 200 ms).
- Dataset 60 cases phân bổ đều 6 nhóm (10 simple, 10 hard, 10 ambiguous, 10 weak_evidence, 10 multi_source, 10 explicit_deep) đã được khóa checksum SHA256 trước khi triển khai policy.
