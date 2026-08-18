# Implementation Log: Feature 003 Adaptive Reranking UX

## 1. Initial State Record (T001)

- **Date**: 2026-08-16
- **Branch**: `main`
- **Platform**: `Windows-10-10.0.18363-SP0`
- **Python**: `3.13.14 [MSC v.1944 64 bit (AMD64)]`
- **Dependency Environment**:
  - `torch`: True
  - `transformers`: True
  - `onnxruntime`: True
  - `numpy`: True
  - `pytest`: True
  - `streamlit`: True
- **Graphify Query**:
  - Query: `Where does Workspace Chat choose and execute RAG retrieval, persist conversation preferences, and report reranker fallback?`
  - Graph: `graphify-out/graph.json`
  - Key nodes identified: `RagV2DevPipeline`, `retrieve_workspace_chat_evidence`, `WorkspaceChatStore`, `WorkspaceConversation`, `bge_subprocess_worker`, `bge_subprocess_client`, `SearchSummary`, `CrossEncoderRerankBackend`.
- **Pre-existing Dirty Files Status**:
  - Pre-existing uncommitted changes are present in the worktree from prior documentation localization and testing.
  - Policy: All pre-existing diffs outside feature `003-adaptive-reranking-ux` are strictly preserved untouched; no `git reset`, `checkout`, `clean`, or staging.

---

## 2. Phase Execution Log

### Phase 1: Setup and Frozen Baseline (T001 - T004)
- **T001**: Baseline state recorded in implementation-log.md.
- **T002**: Created `tests/fixtures/adaptive_routing_cases.json` with 60 balanced synthetic test cases across 6 slices (simple, hard, ambiguous, weak_evidence, multi_source, explicit_deep). SHA256: `e2698883157c1d3d108df372174a573a95cb1620fd689871a6f6223830641da6`.
- **T003**: Created JSON Schema draft-07 in `tests/fixtures/adaptive_reranking_report_schema.json`.
- **T004**: Measured Hybrid baseline latency (p50: 13.19ms, p95: 14.28ms) and memory (5.87 GB available), documented in `specs/003-adaptive-reranking-ux/baseline-summary.md`.

### Phase 2: Foundational Reranker Capability (T005 - T012)
- **T005 & T006**: Extended `WorkspaceChatRagV2Deployment` with support for schema v2 and v3 in `src/aios_habit/workspace_chat_rag_v2_deployment.py` and validated in `tests/test_workspace_chat_rag_v2_deployment.py`.
- **T007 & T008**: Implemented IPC routing contract in `bge_subprocess_client.py` and `bge_subprocess_worker.py` with allowlisted reason codes, bounded lengths, and routing metadata serialization. Validated in `tests/test_bge_subprocess_client.py` and `tests/test_bge_subprocess_worker.py`.
- **T009 & T010**: Added optional pinned reranker support to `RagV2DevConfig` & `RagV2DevPipeline.query()` preserving `bge_m3_hybrid` base identity and index compatibility fingerprint. Validated in `tests/test_rag_v2_pipeline.py`.
- **T011**: Connected deployment manifest reranker artifacts to `WorkspaceChatRagV2CanaryConfig` in `src/aios_habit/workspace_chat_rag_v2_adapter.py`. Validated in `tests/test_workspace_chat_rag_v2_adapter.py`.
- **T012**: Executed Phase 2 foundation test suite:
### Phase 3: User Story 1 - Tự chọn mức tìm kiếm phù hợp (T013 - T021)
- **T013**: Implemented decision-table tests in `tests/test_adaptive_retrieval.py` for pre-gate, post-gate, uncertain escalation, and balanced routing distribution.
- **T014**: Added spy reranker tests in `tests/test_rag_v2_pipeline.py` verifying that reranker backend is never invoked when `rerank_requested=False`.
- **T015 & T016**: Implemented adapter tests in `tests/test_workspace_chat_rag_v2_adapter.py` verifying pre-deep routing, fast Hybrid routing, post-insufficient escalation, and structured Excel strict priority over text retrieval.
- **T017**: Created `src/aios_habit/rag_v2/adaptive_retrieval.py` containing pure pre/post gates, enum classifications, versioned `AdaptiveRetrievalPolicy`, and allowlisted reason codes.
- **T018**: Updated `RagV2DevPipeline.query()` in `src/aios_habit/rag_v2/pipeline.py` to support query-time reranking and routing telemetry.
- **T019 & T020**: Implemented priority order `structured Excel -> pre-gate/user policy -> Hybrid -> post-gate -> optional rerank` in `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- **T021**: Preliminary confusion matrix over 60 benchmark test cases:
  - Pre-gate:
    - simple (10): 10 Fast, 0 Deep
    - hard (10): 0 Fast, 10 Deep
    - ambiguous (10): 0 Fast, 10 Deep (escalated from uncertain)
    - explicit_deep (10): 0 Fast, 10 Deep
    - weak_evidence (10): 10 Fast (initial), escalated to Deep via post-gate
    - multi_source (10): 10 Fast (initial), escalated to Deep via post-gate
  - End-to-End:
    - Expected Fast (10): 10 Fast, 0 Deep
    - Expected Deep (50): 0 Fast, 50 Deep
    - Accuracy: 100% (TP=50, TN=10, FP=0, FN=0).
### Phase 4: User Story 2 - Người dùng chủ động Tìm kỹ hơn (T022 - T029)
- **T022**: Implemented backward-compatible model & store tests in `tests/test_workspace_chat_store.py` (legacy JSONL records without `search_preference` default to `auto`, round-trip persistence for `deep`, invalid preference fail-safe fallback to `auto`).
- **T023**: Implemented UI flow tests in `tests/test_workspace_chat_source_selection_owner_flow.py` for selector state persistence and per-conversation independence.
- **T024**: Implemented copy tests in `tests/test_workspace_chat_ui_copy.py` verifying that Vietnamese user-facing labels `Tự động` and `Tìm kỹ hơn` are used without technical model leakage.
- **T025**: Implemented adapter tests in `tests/test_workspace_chat_rag_v2_adapter.py` verifying `search_preference=deep` strictly overrides Auto for simple queries (`reranker_requested=True`, `user_requested_deep`).
- **T026**: Extended `WorkspaceConversation` with validated `search_preference` in `src/aios_habit/workspace_chat_models.py` and added `update_conversation_search_preference` to `src/aios_habit/workspace_chat_store.py`.
- **T027 & T028**: Added search preference selector in `src/aios_habit/workspace_chat_app.py` composer, persisting user preference per conversation and passing `search_preference` into `retrieve_workspace_chat_evidence()`.
- **T029**: Executed Phase 4 test suite:
  - Command: `py -3 -m pytest tests/test_workspace_chat_store.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_ui_copy.py tests/test_workspace_chat_rag_v2_adapter.py -q`
  - Result: 104 passed in 4.67s.
  - Command: `py -3 -m compileall src tests`
### Phase 5: User Story 3 - Hạ cấp minh bạch và bảo vệ máy (T030 - T037)
- **T030**: Implemented failure tests in `tests/test_rag_v2_pipeline.py` verifying that reranker timeouts, inference crashes (OOM/load shed), and missing reranker models degrade gracefully to Hybrid search without failing the query (`degraded=True`, `reranker_applied=False`, `effective_path="hybrid"`).
- **T031**: Implemented adapter invariants in `tests/test_workspace_chat_rag_v2_adapter.py` verifying that false `Đã tìm kỹ` is strictly prohibited upon reranker failure, returning `Đã dùng X đoạn...` while maintaining full telemetry (`reranker_requested=True`, `reranker_applied=False`, `degraded=True`, `degraded_reason="reranker_backend_timeout"`).
- **T032**: Implemented worker IPC degradation handling tests in `tests/test_bge_subprocess_worker.py` ensuring worker returns `status="ok"` with degraded routing rather than terminating the subprocess.
- **T033**: Implemented safe fallback and exception trapping in `RagV2DevPipeline.query()` in `src/aios_habit/rag_v2/pipeline.py`.
- **T034**: Verified bounded timeouts and failure cooldowns via `AdaptiveRetrievalPolicy` and worker client.
- **T035**: Implemented reranker-to-Hybrid fallback retaining evidence in `src/aios_habit/rag_v2/pipeline.py` and `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- **T036**: Created `CircuitBreaker` in `src/aios_habit/rag_v2/adaptive_retrieval.py` and wired into `RagV2DevPipeline` with failure threshold = 3, cooling down after consecutive errors to protect host RAM.
- **T037**: Executed Phase 5 degradation test suite and verified simulated error mappings:
  - Simulated Timeout -> degraded to `hybrid` (`reranker_backend_timeout`) -> PASS
### Phase 6: User Story 4 - Audit được và kích hoạt có gate (T038 - T045)
- **T038**: Implemented draft-07 JSON Schema validation tests in `tests/test_adaptive_retrieval_evidence.py` ensuring `audit_report.json` structure strictly complies with `tests/fixtures/adaptive_reranking_report_schema.json`.
- **T039**: Implemented CLI deployment audit tests in `tests/test_workspace_chat_rag_v2_deployment.py` testing `--check-adaptive`, `--manifest`, `--json`, and human-readable summary table output.
- **T040**: Implemented `audit_deployment()` and CLI entrypoint `main()` in `src/aios_habit/workspace_chat_rag_v2_deployment.py`.
- **T041**: Implemented `generate_adaptive_audit_report()` in `src/aios_habit/rag_v2/eval_harness.py`.
- **T042**: Verified that `adaptive_enabled` defaults strictly to `False` in `WorkspaceChatRagV2CanaryConfig` and `WorkspaceChatRagV2Deployment`.
- **T043**: Created `specs/003-adaptive-reranking-ux/operations-guide.md` with step-by-step guides for Pre-flight audit, 1-step activation via manifest v3, 1-step instant rollback, and self-healing circuit breaker telemetry.
- **T044**: Executed 60-query benchmark evaluation and produced `specs/003-adaptive-reranking-ux/audit_report.json` with overall_status PASS:
  - Route Accuracy: 100% (60/60)
  - Explicit Deep Rate: 100% (10/10)
  - Uncertain to Deep Rate: 100% (10/10)
  - Zero Privacy Leakage: 0 leaks detected
  - Selected Window: 30 candidates (MRR: 0.94, p95: 28.5ms)
- **T045**: Executed Phase 6 test suite: 152 passed in 9.32s, compileall 0 errors.





