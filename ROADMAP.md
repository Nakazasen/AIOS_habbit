# AIOS WorkLens Roadmap

| Chuẩn bị nguồn tăng dần cho Workspace Chat (005) | `IMPLEMENTED_PENDING_BROWSER_SMOKE` — chuẩn bị tối đa một nguồn khớp nhất cho câu hỏi mới; readiness và retrieval dùng cùng phạm vi; câu hỏi chờ có số lượng/hủy được; 103 test liên quan PASS. Browser smoke trên câu hỏi tài liệu thật còn cần xác nhận. |

`ROADMAP.md` là **nguồn trạng thái canonical duy nhất** cho công việc hiện tại.
Historical design/audit evidence nằm trong `docs/archive/`; không đọc nó như
hướng dẫn vận hành hoặc status runtime.

## Hướng phát triển sản phẩm

AIOS WorkLens là hệ thống trí tuệ công việc ưu tiên cục bộ (local-first). Luồng sử dụng của chủ sở hữu:

```text
Mở Workspace Chat → thêm/chọn nguồn → hỏi tự nhiên → kiểm tra nguồn/citation
```

Workspace Chat là giao diện chính (primary UI). Case Cockpit/Habit Studio không còn là tuyến người dùng được hỗ trợ; xem [RETIREMENT_MANIFEST.md](docs/legacy/RETIREMENT_MANIFEST.md).

Tài liệu tham khảo tầm nhìn dài hạn tương lai: [Production Intelligence Vision](docs/design/PRODUCTION_INTELLIGENCE_VISION.md) (`PLANNED`; chỉ dùng làm tài liệu tham khảo thiết kế, không mở gate bàn giao mới).

## Vị trí hiện tại

| Hạng mục | Trạng thái |
|---|---|
| Giai đoạn hiện tại | Giai đoạn 4 — Nền tảng Workspace Chat & Chuẩn bị AI Gateway |
| Giao diện chính | Workspace Chat |
| Dọn dẹp tài liệu | `DONE` — triển khai `9123caa`, kiểm chứng hiện tại đã đạt |
| Cho dừng route legacy Studio/public | `DONE` — triển khai `9123caa`, kiểm chứng hiện tại đã đạt |
| Nakazasen AI Router | `v0.8.0`; đã xác minh tích hợp Workspace Chat cả offline lẫn trực tiếp với khả năng phục hồi mô hình quá hạn trong ngưỡng |
| Chuẩn hóa chuyên nghiệp (Professionalization) | `DONE` — bằng chứng tài liệu/CI/khôi phục đã kiểm chứng; hoàn tất hợp nhất chính sách route thực tế P0 |
| Dừng khối Case Cockpit monolith | `IMPLEMENTED_PENDING_CURRENT_FULL_SUITE` — các file monolith đã được gỡ bỏ; các service dùng chung vẫn trong phạm vi xử lý |
| Gate triển khai P0 hiện tại | `DONE`: `AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION` |
| Truy xuất kết hợp RAG v2 | `DONE`: `RAG-V2-HYBRID-RETRIEVAL-MIN` — 18 test trọng điểm, 907 test toàn bộ |
| Tổng hợp bằng chứng RAG v2 | `DONE`: `RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN` — 15 test trọng điểm, 921 test toàn bộ |
| Bộ đo lường đánh giá RAG v2 | `DONE`: `RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE` — 11 test trọng điểm, 931 test toàn bộ |
| Benchmark năng lực RAG v2 | `DONE`: `NOTEBOOKLM-BATTLE-RERUN-RAG-V2` — 11 dòng dữ liệu đánh giá mù; RAG v2 đạt 2.898/5 so với NotebookLM 3.807/5 |
| Hội tụ chất lượng Dev RAG v2 | `DONE`: `RAG-V2-DEV-QUALITY-CONVERGENCE` — `DEV_READY_WITH_LIMITATIONS` |
| Gate H hybrid canary | `DONE`: `RAG-V2-GATE-H-HYBRID-CANARY` — `ADVANCE_TO_CANARY_WITH_LIMITATIONS`; 87 test trọng điểm, 1094 test toàn bộ |
| OCR tập dữ liệu & phục hồi nguồn RAG v2 | `DONE`: 70/70 nguồn sử dụng tốt, kiểm tra cục bộ nghiêm ngặt ĐẠT, 49 test trọng điểm và 1108 test toàn bộ |
| Adaptive Reranking UX (003) | `IMPLEMENTED_PENDING_REAL_BENCHMARK` — 154 test trọng điểm ĐẠT, 1.175 test toàn bộ ĐẠT, schema v3, circuit breaker, fail-closed benchmark CLI; canary/production activation `BLOCKED` cho đến khi chạy benchmark trên model/corpus thật |

| A18 | `DONE` — Đã xác minh Chính sách Router thông minh & Sàn so sánh (Comparison Arena) |

| Cầu nối Antigravity IDE AI Brain | `IMPLEMENTED_PENDING_CURRENT_FULL_SUITE` — đã ghi nhận bằng chứng cầu nối/bàn giao trọng điểm |
| P1.0 | `DONE` — Gate Production 1.0 đã được phê duyệt và mở khóa |

### Lưu ý kiểm chứng cây thư mục làm việc hiện tại — 2026-08-16

Các dòng vòng đời ở trên phản ánh metadata của Gate Card hiện có trong cây làm việc này. Cây làm việc chưa được commit và bằng chứng toàn bộ repository hiện tại là `1,143` test được thu thập cùng các bộ test trọng điểm; một lượt chạy full pytest đạt hoàn chỉnh hiện chưa được ghi nhận lại. Không chuyển đổi báo cáo lịch sử hoặc cục bộ thành tuyên bố phát hành (release claim) cho đến khi diff cuối cùng vượt qua tất cả các quality gate và roadmap, bàn giao cùng changelog được đối soát đồng thời.

## Nền tảng đã hoàn thành

- `RAG-V2-ELEMENT-SCHEMA-AND-ADAPTER-INTERFACE` — `DONE`
  ([commit `7db254a`](CHANGELOG.md)).
- `RAG-V2-DOC-CONVERTER-ADAPTERS-MIN` — `DONE`
  ([commit `e2e3942`](CHANGELOG.md)).
- `RAG-V2-STRUCTURE-AWARE-CHUNKING-AND-LOCAL-INDEX-MIN` — `DONE`
  ([commit `c75c319`](CHANGELOG.md)).
- `RM-SYNC-RAG-V2-STRUCTURE-AWARE-CHUNKING-AND-LOCAL-INDEX-MIN` — `DONE`
  ([commit `30e722e`](CHANGELOG.md)).
- `COMPANY-68-RAG-V2-LOCAL-SMOKE-READONLY` — `RECORDED`, chỉ cục bộ,
  không thay đổi mã nguồn. Tài liệu đã được commit trong `9123caa`.

## Giới hạn đã biết và khóa cứng (Hard Locks)

- Gate H đã chọn `bge_m3_hybrid` cho việc kích hoạt có kiểm soát, nhưng mức độ tương đương chất lượng câu trả lời do NotebookLM tạo ra vẫn chưa được chứng minh hoàn toàn.
- Tập tài liệu production 70 nguồn hiện đạt 100% độ bao phủ sử dụng/xử lý thông qua trích xuất gốc hoặc OCR cục bộ có giới hạn; việc tiếp tục giám sát chất lượng OCR vẫn là bắt buộc.
- Người dùng thông thường tuyệt đối không thấy bộ chọn chế độ hybrid/lexical/legacy. Workspace Chat phải tự động sử dụng bộ truy xuất sẵn sàng tốt nhất và không được âm thầm hạ cấp chất lượng mà không cảnh báo.
- Lõi RAG v2 phải luôn giữ tính chất: generic / ưu tiên cục bộ (local-first) / ưu tiên phần tử (element-first) / ưu tiên quyền riêng tư (privacy-first). Không nhúng cứng mã miền/khách hàng/MOM/WMS vào lõi.
- `local_cases/`, `local_runs/`, các nguồn dữ liệu riêng tư và thông tin xác thực luôn được Git bỏ qua (ignored) và nằm ngoài phạm vi dọn dẹp xóa file nguồn.

## Các Gate Card hoàn thành gần đây

1. [ANTIGRAVITY-IDE-AI-BRAIN-BRIDGE](docs/roadmap/completed/ANTIGRAVITY-IDE-AI-BRAIN-BRIDGE.md) — `IMPLEMENTED_PENDING_CURRENT_FULL_SUITE`.
2. [CASE-COCKPIT-DEPENDENCY-MIGRATION-AND-RETIREMENT](docs/roadmap/completed/CASE-COCKPIT-DEPENDENCY-MIGRATION-AND-RETIREMENT.md) — `IMPLEMENTED_PENDING_CURRENT_FULL_SUITE`.
3. [RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY](docs/roadmap/completed/RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY.md) — `DOCUMENTED_RESULT_PENDING_CURRENT_VALIDATION`.
4. [RAG-V2-HYBRID-PRODUCTION-ACTIVATION](docs/roadmap/completed/RAG-V2-HYBRID-PRODUCTION-ACTIVATION.md)
5. [RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY](docs/roadmap/completed/RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY.md)
6. [RAG-V2-GATE-H-HYBRID-CANARY](docs/roadmap/completed/RAG-V2-GATE-H-HYBRID-CANARY.md)
7. [RAG-V2-DEV-QUALITY-CONVERGENCE](docs/roadmap/completed/RAG-V2-DEV-QUALITY-CONVERGENCE.md)
8. [NOTEBOOKLM-BATTLE-RERUN-RAG-V2](docs/roadmap/completed/NOTEBOOKLM-BATTLE-RERUN-RAG-V2.md)
9. [RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE](docs/roadmap/completed/RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE.md)
10. [RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN](docs/roadmap/completed/RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN.md)
11. [RAG-V2-HYBRID-RETRIEVAL-MIN](docs/roadmap/completed/RAG-V2-HYBRID-RETRIEVAL-MIN.md)
12. [AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION](docs/roadmap/completed/AI-GW-REAL-ROUTE-POLICY-CONSOLIDATION.md)
13. [PROFESSIONALIZATION-BASELINE](docs/roadmap/completed/PROFESSIONALIZATION-BASELINE.md)
14. [DOCS-LEGACY-CLEANUP-RESET](docs/roadmap/completed/DOCS-LEGACY-CLEANUP-RESET.md)
15. [STUDIO-AND-PUBLIC-LEGACY-ROUTE-RETIREMENT](docs/roadmap/completed/STUDIO-AND-PUBLIC-LEGACY-ROUTE-RETIREMENT.md)

## Kế hoạch Gate Card ngắn hạn

- Các Gate Card mới trong cây làm việc đang chờ kiểm chứng đầy đủ/commit theo ghi chú kiểm chứng ở trên; không mở một gate mới chỉ từ báo cáo cục bộ hoặc kết quả thu thập test.
- Hướng phát triển tiếp theo theo [Production Intelligence Vision](docs/design/PRODUCTION_INTELLIGENCE_VISION.md) sẽ là mở rộng năng lực trợ lý tự chủ đa nguồn (Multi-Source Autonomous Assistant) và tích hợp các kênh phân tích nâng cao.

## Chính sách xác minh & kiểm chứng

Một Gate Card chỉ có thể chuyển sang trạng thái `DONE` sau khi các thay đổi trong danh sách cho phép và bằng chứng kiểm chứng hiện tại được ghi lại đầy đủ. Tối thiểu cần chạy:

```powershell
uv run --no-sync --group dev python scripts/check_docs.py
uv run --no-sync --group dev python -m compileall src tests
uv run --no-sync --group dev pytest -q
uv run --no-sync --group dev python -m aios_habit.cli audit
uv run --no-sync --group dev python -c "import aios_habit.workspace_chat_app"
git diff --check
git diff --cached --check
```

Xem [docs/roadmap/README.md](docs/roadmap/README.md) để biết quy ước định dạng Gate Card.
