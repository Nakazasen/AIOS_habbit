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
| --- | --- |
| Giai đoạn hiện tại | Đưa Workspace Chat vào vận hành cá nhân: khóa phần nền rồi hoàn thành một pilot điều tra line thật |
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
| Vòng hồ sơ bằng chứng & LSU Loop (008), Mốc 0–4 | `TECHNICAL_PASS`: Mốc 0–4 đạt 100% kỹ thuật (Mốc 0 đạt đầy đủ; Mốc 1–4 đạt `OPERATIONAL_PARTIAL` chờ dữ liệu/nghiệm thu thực địa tại xưởng). Mốc 5 đang kiểm toán. |
| Tổng hợp đa nguồn (002) | `IMPLEMENTED_PENDING_CURRENT_FULL_SUITE` — còn lượt xác minh cuối trên cây code hiện tại |
| Quản lý cuộc trò chuyện (004) | `IMPLEMENTED_PENDING_CURRENT_FULL_SUITE` — chức năng đã có, chưa ghi bằng chứng đầy đủ hiện tại |
| Đánh giá chunk dựa trên bằng chứng (006) | `IMPLEMENTED_PENDING_REAL_CORPUS_VALIDATION` — đóng băng thay đổi E3/E4 cho đến khi corpus thật chứng minh lợi ích |
| Thanh nhập chat hiện đại (007) | `IMPLEMENTED_PENDING_VERIFICATION` — còn lượt kiểm chứng trình duyệt và test hiện tại |

| A18 | `DONE` — Đã xác minh Chính sách Router thông minh & Sàn so sánh (Comparison Arena) |

| Cầu nối Antigravity IDE AI Brain | `DONE` — 89 test trọng điểm ĐẠT, smoke test an toàn thành công, FSM direct_ready, khởi chạy 1-click qua start_antigravity_bridge.bat |
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

1. [ANTIGRAVITY-IDE-AI-BRAIN-BRIDGE](docs/roadmap/completed/ANTIGRAVITY-IDE-AI-BRAIN-BRIDGE.md) — `DONE`.
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

## Kế hoạch Gate Card & Trạng thái Vận hành theo Mốc

**Cổng ngôn ngữ áp dụng cho mọi mốc**: tiếng Việt là ngôn ngữ giao diện duy nhất. Mốc chưa được đóng nếu nút, hướng dẫn, tiến độ, cảnh báo, lỗi, nhật ký vận hành hoặc báo cáo còn câu tiếng Anh hay hiện nguyên lỗi từ thư viện bên ngoài. Tài liệu nguồn ngoại ngữ vẫn được giữ nguyên làm bằng chứng.

1. **Mốc 0 — Khóa phần nền (T001–T005)**: `TECHNICAL_PASS` (100%). Khóa interpreter Python 3.11.14, atomicity kho Case SQLite, quét UI tiếng Việt 100%, headless smoke Streamlit port 8537 đạt.
2. **Mốc 1 — Trợ lý LSU có căn cứ (T006–T010, US2)**: `TECHNICAL_PASS` & `OPERATIONAL_PARTIAL`. Hợp đồng thẩm định chuyên gia `ExpertRequest`/`ExpertReview` append-only, phân quyền theo scope, màn hình chi tiết case tiếng Việt, restart/readback case LSU có citation đạt `RESTART_READBACK_PASS`.
3. **Mốc 2 — Nối dữ liệu BOWSKEW 4 BEAM (T011–T017, US7)**: `TECHNICAL_PASS` & `OPERATIONAL_PARTIAL`. Bộ 7 fixture giả lập LSU Iris, mô hình dữ liệu và Data Gate rubric, kho SQLite có migration và chốt chặn `BLOCKED_DATA`, màn hình kiểm tra dữ liệu và tra cứu chuỗi Unit. Rehearsal đạt `REHEARSAL_RESTART_READBACK_PASS`.
4. **Mốc 3 — Phát lại lịch sử (T018–T022, US8)**: `TECHNICAL_PASS` & `OPERATIONAL_PARTIAL` (kết luận `LEARNING_SHADOW`). Giao thức phát lại lịch sử khóa `as_of_time`, chống rò rỉ tương lai 100%, so sánh phương án nền `no_alert` với `EWMA` (3.0 std), nhánh mô hình học máy khóa an toàn (`not_applicable`). Báo cáo so sánh tiếng Việt tất định theo digest.
5. **Mốc 4 — Shadow thủ công (T023–T027, US9)**: `TECHNICAL_PASS` & `OPERATIONAL_PARTIAL`. Runner thủ công theo lô nhỏ (`ManualShadowRunner`) an toàn CPU laptop, tiến độ thời gian thực, nút dừng an toàn, đánh giá nguy cơ gắn `idempotency_key` bất biến, liên kết case Workspace Case chống trùng, ghi nhận outcome thực tế (kể cả Unit NG bị bỏ sót). Rehearsal đạt `REHEARSAL_MILESTONE_4_PASS`.
6. **Mốc 5 — Đóng đợt & Kích hoạt đợt kế tiếp (T028–T029)**: T028 hoàn tất đồng bộ tài liệu, lộ trình và bản đồ kích hoạt; T029 thực hiện kiểm toán độc lập toàn diện.

### Bản đồ kích hoạt các nhánh độc lập kế tiếp (US3, US4, US5, US6, US10, US11)

Đăng ký 2 bí danh nguồn cục bộ:

- `KHO_LSU_CUC_BO`: Thư mục dữ liệu sản xuất thật LSU tại nhà máy (nhãn `local_only`, không commit Git).
- `GOI_KYOCERA_CUC_BO`: Gói tài liệu và log mẫu dòng máy Kyocera cục bộ để kiểm kê cấu trúc.

Bản đồ kích hoạt (mỗi nhánh độc lập 4 tiêu chí bắt buộc theo chuẩn `spec.md`):

- **US3 (Học từ bài học đã xác nhận)**: Đầu vào: Ít nhất 1 case `confirmed` đã kết luận; Người duyệt: Quản lý kỹ thuật / QC; Đầu ra: Bảng tra cứu bài học trong kho case-memory dẫn về bằng chứng gốc; Test đầu tiên: `pytest tests/test_case_knowledge_lessons.py -k test_lesson_extraction_contract`.
- **US4 (Trợ lý điều tra line chủ động)**: Đầu vào: Hồ sơ điều tra kèm log và biên bản được phép; Người duyệt: Chuyên gia công đoạn phụ trách line; Đầu ra: Dòng thời gian sự kiện, phân nhóm hiện tượng và danh sách câu hỏi cần làm rõ; Test đầu tiên: `pytest tests/test_line_investigation_assistant.py -k test_investigation_timeline_contract`.
- **US5 (Agent tạo đầu ra công việc có kiểm soát: Báo cáo & SOP)**: Đầu vào: Hồ sơ case có đủ bằng chứng đã xác nhận; Người duyệt: Kỹ sư trưởng / Người phê duyệt tài liệu công đoạn; Đầu ra: Bản nháp báo cáo điều tra và SOP có đối chiếu khác biệt phiên bản; Test đầu tiên: `pytest tests/test_controlled_work_artifacts.py -k test_sop_report_generation`.
- **US6 (Agent hỗ trợ lập trình trong workspace tách biệt)**: Đầu vào: Nhiệm vụ lập trình có phạm vi file và lệnh test rõ ràng; Người duyệt: Kỹ sư phần mềm phụ trách kho mã; Đầu ra: Bản vá đề xuất trong sandbox có bằng chứng test thực tế trước khi áp dụng; Test đầu tiên: `pytest tests/test_isolated_coding_agent.py -k test_proposal_sandbox_execution`.
- **US10 (Cảnh báo nguy cơ an toàn trong app)**: Đầu vào: Ít nhất 1 lô sản xuất thật hoàn tất outcome và người dùng cấp quyền; Người duyệt: Trưởng ca vận hành; Đầu ra: Khối cảnh báo nguy cơ an toàn trên Workspace Chat; Test đầu tiên: `pytest tests/test_in_app_risk_notification.py -k test_notification_banner_render`.
- **US11 (Thư viện dùng chung mạng NAS/SMB)**: Đầu vào: Đường dẫn thư mục mạng cục bộ có cấu hình sao lưu; Người duyệt: Quản trị viên IT; Đầu ra: Khóa tệp SQLite fail-closed chống xung đột ghi đa máy; Test đầu tiên: `pytest tests/test_nas_sqlite_concurrency.py -k test_safe_file_locking`.

*Ghi chú*: Các miền dữ liệu mở rộng như dòng máy Kyocera (cụm Drum / DLP) và phân tích sự kiện C-call/Jam là các task pack độc lập phát triển tiếp theo sau chuỗi LSU Iris (US7–US10), không làm thay đổi định nghĩa chuẩn của US4–US6 trong `spec.md`.

Chi tiết và điều kiện vào/ra nằm tại [kế hoạch 008](specs/008-evidence-case-loop/plan.md). Không mở gate mới chỉ từ báo cáo cục bộ hoặc kết quả thu thập test.

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
