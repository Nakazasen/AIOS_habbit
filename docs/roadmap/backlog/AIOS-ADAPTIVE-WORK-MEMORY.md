# Thẻ cổng: Vòng trí nhớ công việc thích nghi

Status: `IMPLEMENTED_PENDING_INDEPENDENT_AUDIT`  
Mã tính năng: `011-adaptive-work-memory`  
Chủ sở hữu: Project owner / Privacy reviewer  
Cập nhật: 2026-09-12

## Mục tiêu

Khép vòng học tối thiểu trên Workspace Chat: gọi lại tri thức đã xác nhận trước câu trả lời; “Hãy nhớ:” / “Hãy quên:” có preview và xác nhận; biến correction rõ ràng thành bài học sau khi người dùng duyệt.

## T001 — Nguồn Goal 010 là tùy chọn, không phải cổng

Người dùng 2026-09-12 xác nhận: Goal 010 **không** phải cổng của Goal 011. Không kiểm tra, không sửa, không yêu cầu đóng T106/T108/T109. Không đổi Gate Card hay trạng thái canonical của Goal 010 trong lượt này.

Adapter `list_eligible_published_memory_candidates()` chỉ đọc artifact published còn hiệu lực. Thiếu thư viện, thiếu bảng, revoked hoặc lỗi đọc → trả candidate rỗng, Goal 011 tiếp tục với ba nguồn còn lại.

Bằng chứng: `tests/test_workspace_memory_recall.py::test_goal010_published_adapter_empty_when_source_unavailable` và `test_goal010_optional_source_does_not_block_other_recall`.

Non-blocking RAG trên `workspace_chat_app.py` / `pipeline.py` được giữ nguyên theo lệnh người dùng.

## T002 — Baseline workspace

- Nhánh: `gate1-local-case-sqlite`
- Python: 3.11.14
- Cờ Goal 011: `adaptive_work_memory` mặc định `False` (rollback = tắt cờ)

### Phân loại dirty tree (không đưa vào phạm vi Goal 011)

| File | Phân loại |
| --- | --- |
| `src/aios_habit/workspace_chat_app.py` (phần RAG) | Non-blocking RAG — người dùng giữ nguyên |
| `src/aios_habit/rag_v2/pipeline.py` | Non-blocking RAG — người dùng giữ nguyên |
| `src/aios_habit/rag_v2/adaptive_retrieval.py` | Non-blocking RAG sẵn có |
| `src/aios_habit/workspace_chat_rag_v2_adapter.py` | Non-blocking RAG sẵn có |
| `src/aios_habit/i18n.py` | Chuỗi Non-blocking RAG — giữ nguyên |
| `tests/test_non_blocking_rag_and_graceful_degradation.py` | Test RAG sẵn có, untracked |
| `.specify/feature.json` | Sẵn có, ngoài Goal 011 |
| `docs/roadmap/backlog/AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md` | Evidence Goal 010 — không sửa trong lượt này |
| `Lam_viec_thong_minh_nhu_Grokbot.md` | File người dùng — **không sửa/stage/commit** |
| `specs/011-adaptive-work-memory/` | Gói đặc tả Goal 011 |

Không đưa `local_cases/`, `local_runs/`, `.env` vào phạm vi.

### Baseline prompt

Oracle T003: khi `adaptive_work_memory` tắt, `build_workspace_ai_prompt()` giữ nguyên byte so với output hiện tại cho cùng input; không có block “Sổ việc đã xác nhận”.

### Rollback

Tắt `adaptive_work_memory`. Không xóa JSONL quyết định (US2, ngoài Git). Không checkout các file Non-blocking RAG.

## Checkpoint T003–T007

- T003: `test_baseline_prompt_byte_stable_when_flag_off`, `test_baseline_prompt_has_no_memory_block_when_flag_off`
- T004/T005: cờ mặc định tắt, override cô lập, reset sạch trong `feature_flags.py`
- T006: fixture 30 tình huống (20 related / 10 no-match) tại `tests/fixtures/workspace_memory/fixture_manifest.json`
- T007: dataclass request/item/result/trace trong `workspace_memory_models.py`

## Checkpoint US1 (T008–T015)

- Bốn bộ đọc read-only: MemoryUnit, SeniorLearningCard, CaseLesson, published artifact. Lỗi một nguồn không chặn nguồn khác.
- Eligibility trước scoring; draft/revoked/missing-evidence không vào prompt.
- Block “Sổ việc đã xác nhận” tối đa 5 mục / 4.000 ký tự; memory-as-data.
- Direct provider, C-AGENT và Nakazasen dùng cùng `recall_memory_for_answer`.
- Panel “Vì sao AIOS nhớ điều này?”; copy tiếng Việt, không lộ path/traceback.
- Focused tests: `uv run --no-sync --group dev pytest -q tests/test_workspace_memory_recall.py tests/test_workspace_chat_ai_answer.py` — nằm trong 119 passed (2026-09-12).
- SC-002: `test_recall_eligibility_unicode_scope_conflict_and_sc002` yêu cầu ≥18/20 related và 10/10 no-match.
- Benchmark: `scripts/benchmark_workspace_memory_recall.py --items 10000 --runs 100` → p50 251.6 ms, p95 364.7 ms, max 591.5 ms, working_set_delta_mb 34.11, `model_loaded=false`, `gpu_loaded=false`, exit 0. Artifact `local_runs/workspace_memory_benchmark.json` (không stage).

## Checkpoint US2 (T016–T021)

- Preview/cancel không ghi; confirm append-only JSONL dưới `local_cases/workspace_memory/memory_decisions.jsonl`.
- Tái sử dụng `LibraryWriterLease`; contention fail-closed, không tạo dòng dở dang.
- Forget/revoke ghi quyết định mới, ngừng recall ngay, giữ lịch sử.
- UI “Hãy nhớ:” / “Hãy quên:” có xem trước và xác nhận/hủy.
- Test: `tests/test_workspace_memory_commands.py` nằm trong 119 passed.

## Checkpoint US3 (T022–T026)

- `CorrectionLessonCandidate` session-only; chưa xác nhận không recall; không persist raw answer.
- Duplicate/conflict bắt buộc chọn merge / replace / keep_both / cancel.
- UI “Sửa để AIOS học” trên câu trả lời gần nhất.
- Test: `tests/test_workspace_memory_corrections.py` nằm trong 119 passed.

## T027 — Tiếng Việt

- `scripts/check_user_facing_vietnamese.py` gồm `workspace_memory_ui.py`.
- Kết quả: `VIETNAMESE_UI_POLICY_CHECK=PASS`.
- `tests/test_workspace_memory_ui.py` và `TestWorkspaceMemoryUiCopy` trong `tests/test_workspace_chat_ui_i18n.py`.

## T028 — Cổng đầy đủ

| Lệnh | Kết quả |
| --- | --- |
| Python 3.11.14 | exit 0 |
| `python -m compileall src tests` | exit 0 |
| Focused Goal 011 + i18n/ai_answer | 119 passed / 3.08s / exit 0 |
| `python -m aios_habit.cli audit` | `"status": "PASS"` |
| `python -c "import aios_habit.workspace_chat_app"` | exit 0 |
| `python scripts/check_user_facing_vietnamese.py` | PASS |
| `git diff --check` trên file Goal 011 | exit 0 |
| `git diff --check` toàn cây | FAIL sẵn có trên `AIOS-EXPERT-KNOWLEDGE-ACQUISITION.md` (trailing whitespace Goal 010; không sửa trong lượt này) |
| Full `pytest -q` | 2 failed, 2763 passed, 961.61s, exit 1. Hai fail ngoài Goal 011: `test_desktop_build_prerequisites_function` (đóng gói Goal 010) và `test_app_preparation_gate_is_scoped_to_query_relevant_sources` (hợp đồng chuỗi cũ vs Non-blocking RAG đã giữ nguyên). Không sửa hai fail này trong lượt Goal 011. |

Smoke thủ công Streamlit (mục 7 quickstart) chưa chạy trên UI thật — chuyển Codex.

## T029 — Graphify

`graphify update .` exit 0. AST 141 file; graph 15057 nodes, 29950 edges, 1019 communities; `graph.json` / `graph.html` / `GRAPH_REPORT.md` cập nhật trong `graphify-out`. Backup curated graph vào `graphify-out/2026-09-12/`.

## T030 — Trạng thái canonical

Grok ghi `IMPLEMENTED_PENDING_INDEPENDENT_AUDIT` trên thẻ này, `ROADMAP.md`, `ARCHITECTURE.md`, `PROJECT_HANDOVER.md`. Không tự tuyên bố PASS cuối. T031–T032 dành cho Codex.

## Rollback

Tắt `adaptive_work_memory`. Prompt Workspace Chat trở về baseline. JSONL quyết định còn trên đĩa, ngoài Git; code cũ bỏ qua an toàn.

## Rủi ro chuyển Codex

- Smoke thủ công UI chưa làm.
- Các đường provider ngoài đều fail-closed khi tập memory có fingerprint rỗng hoặc không khớp; C-AGENT cũng dùng lọc cloud nên không nhận `local_only`. UI chưa gắn fingerprint vào lượt xác nhận nên trường hợp có memory sẽ bị chặn an toàn cho đến khi luồng này được kiểm tra thủ công.
- `git diff --check` toàn cây còn FAIL vì file Goal 010 sẵn có.
- Full pytest 2 failed / 2763 passed; cả hai fail ngoài phạm vi Goal 011 (đóng gói Goal 010 và hợp đồng chuỗi Non-blocking RAG). Không giả PASS toàn suite.
- `git diff --check` toàn cây FAIL vì trailing whitespace sẵn có trên Gate Card Goal 010.

## Khắc phục sau kiểm toán độc lập

Ba finding còn lại đã được sửa theo phạm vi tối thiểu: khóa consent trên mọi bridge ngoài, từ chối lệnh quên mơ hồ/khác workspace và giới hạn toàn block memory tối đa 4.000 ký tự. Regression Goal 011 đạt 162 bài; test bridge bổ sung đạt 31 bài. Trạng thái vẫn chờ kiểm toán độc lập lại và smoke UI thật; không tự tuyên bố `PASS`.

## T030A — Lựa chọn ghi nhớ dễ hiểu trên giao diện

Theo phản hồi người dùng, Workspace Chat hiện trực tiếp lựa chọn “Cho AIOS ghi nhớ để hỗ trợ tôi tốt hơn”, cùng trạng thái “Đang bật ghi nhớ” hoặc “Đang tắt ghi nhớ”. Lựa chọn được giữ tại `local_cases/workspace_memory/settings.json`, không cần nhớ lệnh PowerShell và không thêm database. Test trí nhớ/cầu nối đạt 157 bài; test giao diện tiếng Việt đạt 35 bài; `compileall`, kiểm tra tiếng Việt, CLI audit và import Workspace Chat trong thư mục thử nghiệm đều đạt. Full suite: 2.778 bài đạt, 2 bài lỗi đã biết ngoài T030A (đóng gói Goal 010 và assertion chuỗi cũ của Non-blocking RAG). Trạng thái vẫn chờ smoke UI thật và kiểm toán độc lập lại.
