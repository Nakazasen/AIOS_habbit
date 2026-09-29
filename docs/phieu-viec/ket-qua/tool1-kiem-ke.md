# Vé `TOOL-1` — Kiểm kê tool chưa nối vào chat: báo cáo nghiệm thu

- Trạng thái: **xong — chờ Muse duyệt** (vé chỉ đọc + báo cáo; không sửa code).
- Máy: `h410asrock` — Windows (`win32`, 10.0.18363); Python `3.11.14` (venv repo, `uv 0.10.6`).
- Nhánh: `phieu-viec/rag-fix1`. Mốc commit: `7f25517` (nhận vé lúc 03:08) → `6a56206` (mốc 1: quét xong + kiểm chứng động). Không đụng `main`, không force-push.
- Phạm vi ghi: chỉ file báo cáo này + `docs/phieu-viec/mailbox/trang-thai.md` (đúng quy ước commit của vé). Không ghi index, không embed, không sửa mã nguồn/test, không đụng dữ liệu/index production trên ổ D. Script phân tích tạm nằm trong `scratch/` (đã gitignore).

## 1. Cách làm (bằng chứng thật, không đoán)

1. Quét AST toàn bộ **218 tệp `.py`** dưới `src/aios_habit/` (155 tệp gói gốc + 63 tệp trong 3 gói con `error_cases`, `production_prediction`, `rag_v2`).
2. Dựng đồ thị import nội bộ: `import aios_habit.X`, `from aios_habit.X import y` (tính cả `X.y` là module nếu có tệp thật), import tương đối quy về tuyệt đối.
3. Tính bao đóng (closure) từ đúng 2 entry chat theo vé: `workspace_chat_ui.py`, `workspace_chat_app.py`.
4. **Kiểm chứng động**: import thật 2 entry trong venv Python 3.11.14 → **100 module `aios_habit.*` được nạp thật**, cả 100 đều nằm trong bao đóng tĩnh (nhất quán). Phần còn lại của bao đóng là import khi gọi hàm / theo điều kiện.
5. Quét bổ sung: tham chiếu chuỗi tên module, tiến trình con (`-m aios_habit.rag_v2.bge_subprocess_worker` trong `bge_subprocess_client`), và đối chiếu thủ công vài chuỗi tiêu biểu bằng `grep` (ví dụ `expert_interview_service` ← `workspace_case_ui`; `excaliflow_adapter` ← `evidence_graph_viewer`; `jig_chat_wire.handle_jig_chat_text` ← `workspace_chat_app` dòng 3878).

Lệnh chính đã chạy: `uv run --no-sync --group dev python scratch/tool1_scan.py`, `... tool1_closure.py`, `... tool1_runtime.py`, `... tool1_final.py`, `... tool1_table2.py` (script tạm, không commit).

## 2. Kết quả tổng hợp

- **217 module** (không kể gói gốc `aios_habit`): **136 đã nối chat** (62,7%) — 100 nạp thật khi mở chat, phần còn lại import khi gọi hàm/điều kiện; **81 chưa nối** (37,3%).
- 4 ca đặc biệt được tính là "có nối" kèm ghi chú: `rag_v2.bge_subprocess_worker` (chạy tiến trình con qua client đã nối), `rag_v2` + `rag_v2.eval_harness` + `production_prediction` (nạp kèm gói cha khi chat import gói con).

| Nhóm | Tổng | Đã nối | Chưa nối |
|---|---:|---:|---:|
| RAG | 53 | 40 | 13 |
| benchmark | 11 | 0 | 11 |
| interview | 12 | 11 | 1 |
| prediction | 24 | 23 | 1 |
| visual | 12 | 2 | 10 |
| extract | 11 | 10 | 1 |
| memory | 6 | 3 | 3 |
| khác | 88 | 47 | 41 |
| **Cộng** | **217** | **136** | **81** |

## 3. Bảng chi tiết (module | nhóm | đã nối | ghi chú)

### RAG — 53 module (nối 40, chưa nối 13)

| module | nhóm | đã nối | ghi chú |
|---|---|---|---|
| `citation_answer` | RAG | có — gián tiếp |  |
| `final_answer_composer` | RAG | có — gián tiếp |  |
| `model_pack` | RAG | không | CLI (`cli.py`); test×1; script: desktop_smoke_test.py |
| `query_intent` | RAG | có — gián tiếp |  |
| `query_planner` | RAG | có — trực tiếp (import khi gọi) |  |
| `question_suggestions` | RAG | có — trực tiếp (import khi gọi) |  |
| `rag_answer_composer` | RAG | có — gián tiếp |  |
| `rag_core_profiles` | RAG | có — gián tiếp |  |
| `rag_evidence` | RAG | có — gián tiếp |  |
| `rag_ingest` | RAG | có — gián tiếp |  |
| `rag_rerank` | RAG | không | nội bộ: notebooklm_compare.py, rag_benchmark.py; test×1 |
| `rag_search` | RAG | có — gián tiếp |  |
| `rag_v2` | RAG | có — một phần (nạp kèm gói cha) | nạp kèm gói cha khi chat import gói con |
| `rag_v2.adapters` | RAG | có — gián tiếp |  |
| `rag_v2.adaptive_retrieval` | RAG | có — gián tiếp |  |
| `rag_v2.bge_onnx_backend` | RAG | có — gián tiếp |  |
| `rag_v2.bge_subprocess_client` | RAG | có — gián tiếp |  |
| `rag_v2.bge_subprocess_worker` | RAG | có — qua tiến trình con | chạy tiến trình con qua `bge_subprocess_client` (đã nối chat) |
| `rag_v2.chunk_evaluation` | RAG | không | test×1; script: evaluate_chunking.py |
| `rag_v2.chunk_revisions` | RAG | không | test×1 |
| `rag_v2.chunk_upload_config` | RAG | không | test×1 |
| `rag_v2.chunking` | RAG | có — gián tiếp |  |
| `rag_v2.converters` | RAG | có — gián tiếp |  |
| `rag_v2.eval_harness` | RAG | có — một phần (nạp kèm gói cha) | nạp kèm gói cha khi chat import gói con |
| `rag_v2.evidence` | RAG | có — gián tiếp |  |
| `rag_v2.index` | RAG | có — gián tiếp |  |
| `rag_v2.index_bundle` | RAG | không | nội bộ: rag_v2/index_registry.py; test×1 |
| `rag_v2.index_registry` | RAG | không | test×1 |
| `rag_v2.ingest_manifest` | RAG | có — gián tiếp |  |
| `rag_v2.ingestion_jobs` | RAG | không | nội bộ: rag_v2/ingestion_service.py; test×2 |
| `rag_v2.ingestion_service` | RAG | không | test×1 |
| `rag_v2.ingestion_workers` | RAG | không | test×1 |
| `rag_v2.multilingual_query_expand` | RAG | có — gián tiếp |  |
| `rag_v2.pipeline` | RAG | có — gián tiếp |  |
| `rag_v2.query_planning` | RAG | có — trực tiếp (import khi gọi) |  |
| `rag_v2.registry` | RAG | có — gián tiếp |  |
| `rag_v2.remote_ingestion_client` | RAG | không | test×1 |
| `rag_v2.retrieval_backends` | RAG | có — gián tiếp |  |
| `rag_v2.schema` | RAG | có — gián tiếp |  |
| `rag_v2.script_family` | RAG | có — gián tiếp |  |
| `rag_v2.semantic` | RAG | có — gián tiếp |  |
| `rag_v2.structured_query` | RAG | có — gián tiếp |  |
| `rag_v2.summary_provenance` | RAG | có — gián tiếp |  |
| `rag_v2.synthesis` | RAG | có — gián tiếp |  |
| `rag_v2_synthesis_provider` | RAG | không | nội bộ: rag_v2/bge_subprocess_worker.py; test×1 |
| `shared_library_presets` | RAG | có — trực tiếp (nạp ngay) |  |
| `source_ingest` | RAG | có — gián tiếp |  |
| `source_router` | RAG | có — gián tiếp |  |
| `strong_answer_ui` | RAG | không | test×1 |
| `workspace_chat_rag_v2_adapter` | RAG | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_rag_v2_deployment` | RAG | có — gián tiếp |  |
| `workspace_chat_router_adapter` | RAG | có — gián tiếp |  |
| `workspace_chat_source_ingest` | RAG | có — trực tiếp (nạp ngay) |  |

### benchmark — 11 module (nối 0, chưa nối 11)

| module | nhóm | đã nối | ghi chú |
|---|---|---|---|
| `agent_learning` | benchmark | không | không tham chiếu ở đâu |
| `benchmark_reference_acquisition` | benchmark | không | test×1; script: battle_notebooklm_rag_v2.py |
| `benchmark_reference_registry` | benchmark | không | nội bộ: benchmark_reference_acquisition.py, rag_v2/index_bundle.py, rag_v2/index_registry.py (+1); test×2; script: battle_notebooklm_rag_v2.py, reference_registry.py |
| `mom_benchmark` | benchmark | không | nội bộ: mom_benchmark_gate.py; test×1 |
| `mom_benchmark_gate` | benchmark | không | test×1 |
| `mom_coverage` | benchmark | không | test×1; script: audit_mom_corpus.py |
| `mom_local_index` | benchmark | không | nội bộ: mom_coverage.py; test×4; tham chiếu chuỗi: tests/test_rag_v2_hardcode_guard.py |
| `notebooklm_compare` | benchmark | không | CLI (`cli.py`); test×2 |
| `rag_benchmark` | benchmark | không | test×2 |
| `rag_evaluator` | benchmark | không | test×1 |
| `real_doc_inventory` | benchmark | không | nội bộ: mom_benchmark.py, mom_local_index.py; test×1 |

### interview — 12 module (nối 11, chưa nối 1)

| module | nhóm | đã nối | ghi chú |
|---|---|---|---|
| `adaptive_interview_engine` | interview | có — gián tiếp |  |
| `controlled_knowledge_artifact` | interview | có — gián tiếp |  |
| `expert_identity` | interview | có — gián tiếp |  |
| `expert_identity_windows` | interview | có — gián tiếp |  |
| `expert_interview_models` | interview | có — gián tiếp |  |
| `expert_interview_repository` | interview | có — gián tiếp |  |
| `expert_interview_service` | interview | có — gián tiếp |  |
| `fine_tune_eligibility` | interview | không | test×2 |
| `knowledge_claim_extractor` | interview | có — gián tiếp |  |
| `knowledge_coverage` | interview | có — gián tiếp |  |
| `knowledge_publication` | interview | có — gián tiếp |  |
| `local_transcription` | interview | có — gián tiếp |  |

### prediction — 24 module (nối 23, chưa nối 1)

| module | nhóm | đã nối | ghi chú |
|---|---|---|---|
| `cagent_api` | prediction | có — gián tiếp |  |
| `in_app_risk_alert` | prediction | có — trực tiếp (nạp ngay) |  |
| `prediction_shadow_ui` | prediction | có — trực tiếp (nạp ngay) |  |
| `production_prediction` | prediction | có — một phần (nạp kèm gói cha) | nạp kèm gói cha khi chat import gói con |
| `production_prediction.alert_config_chat` | prediction | có — gián tiếp |  |
| `production_prediction.alert_mailer` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.chart_selection` | prediction | có — gián tiếp |  |
| `production_prediction.evaluation` | prediction | có — gián tiếp |  |
| `production_prediction.iris_log_adapter` | prediction | có — gián tiếp |  |
| `production_prediction.jig_alert_cards` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.jig_chat_wire` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.jig_log_ingest` | prediction | có — gián tiếp |  |
| `production_prediction.log_archive` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.lsu_iris` | prediction | có — gián tiếp |  |
| `production_prediction.metric_limits` | prediction | có — gián tiếp |  |
| `production_prediction.migrations` | prediction | có — gián tiếp |  |
| `production_prediction.models` | prediction | có — gián tiếp |  |
| `production_prediction.reporting` | prediction | không | chỉ dùng trong test (2 tệp) |
| `production_prediction.repository` | prediction | có — trực tiếp (nạp ngay) |  |
| `production_prediction.session_isolation` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.shadow` | prediction | có — gián tiếp |  |
| `production_prediction.smtp_config` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.spc_chart` | prediction | có — gián tiếp |  |
| `production_prediction.stream_api` | prediction | có — trực tiếp (import khi gọi) |  |

### visual — 12 module (nối 2, chưa nối 10)

| module | nhóm | đã nối | ghi chú |
|---|---|---|---|
| `evidence_graph_viewer` | visual | có — trực tiếp (nạp ngay) |  |
| `excaliflow_adapter` | visual | có — gián tiếp |  |
| `graphify_adapter` | visual | không | test×4; script: desktop_smoke_test.py |
| `knowledge_map_html` | visual | không | test×2 |
| `knowledge_map_view` | visual | không | nội bộ: worklens_semantic_map.py; test×1 |
| `notebook_graph` | visual | không | test×1 |
| `visual_knowledge_map` | visual | không | test×1 |
| `visual_map_builder` | visual | không | test×3 |
| `visual_map_export` | visual | không | nội bộ: visual_map_ui.py; test×2 |
| `visual_map_models` | visual | không | nội bộ: visual_map_builder.py, visual_map_export.py, visual_map_ui.py; test×4 |
| `visual_map_ui` | visual | không | test×1 |
| `worklens_semantic_map` | visual | không | test×1 |

### extract — 11 module (nối 10, chưa nối 1)

| module | nhóm | đã nối | ghi chú |
|---|---|---|---|
| `agent_result_import` | extract | có — gián tiếp |  |
| `deep_document_parsers` | extract | có — gián tiếp |  |
| `document_extractors` | extract | có — gián tiếp |  |
| `excel_extractors` | extract | có — gián tiếp |  |
| `extraction` | extract | không | CLI (`cli.py`) |
| `extractor_registry` | extract | có — gián tiếp |  |
| `line_log_parser` | extract | có — trực tiếp (import khi gọi) |  |
| `ocr_engines` | extract | có — gián tiếp |  |
| `workspace_chat_excel` | extract | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_folder_import` | extract | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_legacy_extractors` | extract | có — gián tiếp |  |

### memory — 6 module (nối 3, chưa nối 3)

| module | nhóm | đã nối | ghi chú |
|---|---|---|---|
| `learning_models` | memory | không | nội bộ: case_audit.py, case_prompt.py, visual_map_builder.py (+1); test×2 |
| `memory` | memory | không | test×1 |
| `study_store` | memory | không | test×1 |
| `workspace_memory_models` | memory | có — gián tiếp |  |
| `workspace_memory_service` | memory | có — trực tiếp (nạp ngay) |  |
| `workspace_memory_ui` | memory | có — trực tiếp (nạp ngay) |  |

### khác — 88 module (nối 47, chưa nối 41)

| module | nhóm | đã nối | ghi chú |
|---|---|---|---|
| `agent_draft_sop` | khác | có — trực tiếp (nạp ngay) |  |
| `agent_task_pack` | khác | có — gián tiếp |  |
| `agent_work_artifact` | khác | có — trực tiếp (nạp ngay) |  |
| `ai_provider_bridge` | khác | không | nội bộ: ai_router.py, provider_safety.py, strong_answer_ui.py; test×4 |
| `ai_router` | khác | không | CLI (`cli.py`); nội bộ: rag_v2_synthesis_provider.py; test×6 |
| `antigravity_bridge` | khác | có — trực tiếp (nạp ngay) |  |
| `audit` | khác | không | CLI (`cli.py`); nội bộ: phase_gate.py; test×1 |
| `brain_gateway` | khác | có — gián tiếp |  |
| `case_audit` | khác | không | test×2 |
| `case_models` | khác | có — gián tiếp |  |
| `case_prompt` | khác | không | test×3 |
| `case_store` | khác | có — gián tiếp |  |
| `claim_guard` | khác | không | test×2 |
| `cli` | khác | không | entry CLI (`python -m aios_habit.cli`), không phải chat; test tham chiếu |
| `coding_assistant` | khác | có — gián tiếp |  |
| `core` | khác | có — gián tiếp |  |
| `daily_next_actions` | khác | không | test×1 |
| `discovery` | khác | không | CLI (`cli.py`); test×1 |
| `domain_playbooks` | khác | có — gián tiếp |  |
| `error_cases` | khác | không | nội bộ: error_cases/import_history.py, error_cases/store.py; test×5 |
| `error_cases.auto_classifier` | khác | không | nội bộ: error_cases/__init__.py; test×1 |
| `error_cases.column_map` | khác | không | nội bộ: error_cases/__init__.py, error_cases/import_history.py, error_cases/store.py; test×1 |
| `error_cases.completeness` | khác | không | nội bộ: error_cases/__init__.py |
| `error_cases.feedback_loop` | khác | không | nội bộ: error_cases/__init__.py; test×1 |
| `error_cases.glossary` | khác | không | nội bộ: error_cases/__init__.py, error_cases/auto_classifier.py, error_cases/investigation_tree.py; test×2 |
| `error_cases.import_history` | khác | không | nội bộ: error_cases/__init__.py; test×1 |
| `error_cases.investigation_tree` | khác | không | nội bộ: error_cases/__init__.py; test×1 |
| `error_cases.store` | khác | không | nội bộ: error_cases/__init__.py, error_cases/import_history.py; test×1 |
| `error_cases.trend_analysis` | khác | không | nội bộ: error_cases/__init__.py |
| `evidence` | khác | không | không tham chiếu ở đâu |
| `evidence_trace` | khác | có — trực tiếp (nạp ngay) |  |
| `evidence_trace_schema` | khác | có — trực tiếp (nạp ngay) |  |
| `export_pack` | khác | không | CLI (`cli.py`) |
| `feature_flags` | khác | có — gián tiếp |  |
| `gemini_web_engine` | khác | không | test×1; script: antigravity_sidecar_daemon.py |
| `handover` | khác | không | CLI (`cli.py`) |
| `i18n` | khác | có — trực tiếp (nạp ngay) |  |
| `ide_bridge` | khác | không | test×2 |
| `ide_handoff_bridge` | khác | có — trực tiếp (nạp ngay) |  |
| `library_backup` | khác | có — trực tiếp (nạp ngay) |  |
| `line_investigation` | khác | có — gián tiếp |  |
| `llm_client` | khác | có — gián tiếp |  |
| `local_folder_picker` | khác | có — trực tiếp (nạp ngay) |  |
| `local_jsonl` | khác | có — gián tiếp |  |
| `models` | khác | không | CLI (`cli.py`); nội bộ: audit.py, discovery.py, evidence.py (+5); test×1 |
| `notebook_bridge` | khác | không | test×2 |
| `notebook_case_actions` | khác | không | test×2 |
| `notebook_import_store` | khác | không | nội bộ: daily_next_actions.py, worklens_semantic_map.py; test×4 |
| `notebook_index` | khác | không | nội bộ: daily_next_actions.py, notebook_qa.py, study_store.py; test×8 |
| `notebook_qa` | khác | không | test×3 |
| `opencode_runtime_adapter` | khác | có — trực tiếp (nạp ngay) |  |
| `owner_workflow_state` | khác | không | test×1 |
| `paths` | khác | không | không tham chiếu ở đâu |
| `phase_gate` | khác | không | CLI (`cli.py`); test×1 |
| `profiles` | khác | không | CLI (`cli.py`) |
| `provider_catalog` | khác | có — gián tiếp |  |
| `provider_health` | khác | có — gián tiếp |  |
| `provider_model_discovery` | khác | không | CLI (`cli.py`); nội bộ: ai_router.py; test×1 |
| `provider_safety` | khác | không | test×1 |
| `resilient_routing` | khác | có — gián tiếp |  |
| `route_log_ui` | khác | không | test×1 |
| `router_adapter` | khác | có — gián tiếp |  |
| `router_synth_redaction` | khác | không | test×1 |
| `safety_modes` | khác | có — gián tiếp |  |
| `shared_ai_provider_fabric` | khác | có — gián tiếp |  |
| `shared_mailbox` | khác | có — trực tiếp (nạp ngay) |  |
| `storage` | khác | không | CLI (`cli.py`); nội bộ: audit.py, evidence.py, memory.py; test×1 |
| `ui_safety` | khác | có — trực tiếp (nạp ngay) |  |
| `workflow` | khác | không | không tham chiếu ở đâu |
| `workspace_agent_bridge_client` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_agent_models` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_agent_orchestrator` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_agent_policy` | khác | có — trực tiếp (import khi gọi) |  |
| `workspace_case_authorization` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_case_migrations` | khác | có — gián tiếp |  |
| `workspace_case_models` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_case_repository` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_case_service` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_case_ui` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_ai_answer` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_answer_preview` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_app` | khác | — (chính là entry chat) | entry Streamlit của chat (`streamlit run src/aios_habit/workspace_chat_app.py`) |
| `workspace_chat_connector_guard` | khác | có — trực tiếp (import khi gọi) |  |
| `workspace_chat_models` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_store` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_ui` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_models` | khác | không | nội bộ: case_audit.py, case_prompt.py, notebook_bridge.py (+2); test×4 |
| `workspace_paths` | khác | có — trực tiếp (nạp ngay) |  |

## 4. Nhận xét chính

- **benchmark: toàn bộ 11 module đứng riêng** — `mom_benchmark`, `mom_benchmark_gate`, `mom_coverage`, `mom_local_index`, `rag_benchmark`, `rag_evaluator`, `benchmark_reference_acquisition`, `benchmark_reference_registry`, `notebooklm_compare`, `real_doc_inventory`, `agent_learning`. Đúng như vé TOOL-3 dự kiến nối `mom_benchmark` + `rag_benchmark` + `rag_evaluator`.
- **visual: 10/12 chưa nối** — còn `visual_map_builder/export/models/ui`, `visual_knowledge_map`, `knowledge_map_html`, `knowledge_map_view`, `worklens_semantic_map`, `graphify_adapter`, `notebook_graph`. Lưu ý cho TOOL-5: `evidence_graph_viewer` **đã nối** (import trực tiếp trong `workspace_chat_ui`), khác với giả định trong prompt xếp hàng.
- **Bộ điều tra lỗi LSU (`error_cases`, 11 module) chưa nối chat** — hiện chỉ dùng qua CLI/test (Bước 0–5), ví dụ `error_cases.investigation_tree`, `error_cases.trend_analysis`, `error_cases.auto_classifier`.
- **interview (11/12) và prediction (23/24) đã nối nhưng "một phần"**: interview đi gián tiếp qua màn hồ sơ `workspace_case_ui`; prediction đi qua wiring S12 (`jig_chat_wire`, `prediction_shadow_ui` import khi gọi trong app). Chưa có khung `chat_action` chung — đúng khoảng trống mà TOOL-2 sẽ lấp.
- **Bộ notebook/study chưa nối**: `notebook_bridge`, `notebook_index`, `notebook_qa`, `notebook_import_store`, `notebook_case_actions`, `notebook_graph`, `study_store`, `daily_next_actions`.
- Một số module **không tham chiếu ở đâu** (chết/đứng riêng): `agent_learning`, `evidence`, `paths`, `workflow` — cân nhắc khi dọn dẹp sau này.
- **RAG 13 module chưa tới chat** chủ yếu là hạ tầng index/ingest (`index_bundle`, `index_registry`, `ingestion_jobs`, `ingestion_service`, `ingestion_workers`, `remote_ingestion_client`, `chunk_evaluation`, `chunk_revisions`, `chunk_upload_config`, `model_pack`, `rag_rerank`, `rag_v2_synthesis_provider`, `strong_answer_ui`).
- Gợi ý cho TOOL-2 (chọn tool mẫu đơn giản nhất): các tool nhỏ, ít phụ thuộc, chưa nối như `rag_evaluator` (57 dòng), `claim_guard` (81), `daily_next_actions` (47) hoặc `mom_benchmark` (339).

## 5. Xác nhận ràng buộc vé

- Chỉ đọc + báo cáo: **0 dòng mã nguồn/test thay đổi** (commit báo cáo chỉ thêm file này; commit mốc chỉ sửa `trang-thai.md`).
- Không đụng index production RAG, không embed, không ghi dữ liệu trên ổ D (repo chỉ nhận 2 file tài liệu theo quy ước vé).
- Không merge `main`, không force-push.

