# Vé `TOOL-1` — Kiểm kê tool chưa nối vào chat: báo cáo nghiệm thu

- Trạng thái: **xong — chờ Muse duyệt** (vé chỉ đọc + báo cáo; không sửa code).
- Thợ thực hiện: `agy` (Gemini 3.8 Flash High) trên máy `h410asrock` (Windows 10, Python 3.11).
- Nhánh làm việc: `phieu-viec/rag-fix1`.
- Phạm vi: Chỉ cập nhật file báo cáo này và `docs/phieu-viec/mailbox-agy/trang-thai.md`. Tuyệt đối không sửa code sản phẩm, không đụng dữ liệu ngoài repo/ổ D.
- Sửa mục 4 ngày 2026-10-04: đồng bộ với bảng, kiểm tra bằng script.

## 1. Phương pháp kiểm kê (Bằng chứng thực thi, không suy đoán)

1. **Quét toàn diện mã nguồn**: Phân tích AST của toàn bộ **267 module tính năng** (tổng số 268 tệp `.py` bao gồm cả `aios_habit.__init__`) trong `src/aios_habit/` (bao gồm gói gốc và 3 gói con `error_cases`, `production_prediction`, `rag_v2`).
2. **Xây dựng đồ thị phụ thuộc import (Import Graph)**: Truy vết toàn bộ câu lệnh `import` và `from ... import` ở cả cấp độ module (top-level) và cấp độ hàm (function/lazy import), chuẩn hóa import tương đối sang tuyệt đối.
3. **Xác định đường dẫn kết nối tới Chat**: Xuất phát từ 2 điểm vào chính của chat là `workspace_chat_ui.py` và `workspace_chat_app.py`, cùng router hành động tích hợp `chat_action.py` (`BUILTIN_ACTION_MODULES`).
4. **Kiểm chứng động trong runtime Python 3.11**: Import trực tiếp `workspace_chat_app`, `workspace_chat_ui` và kích hoạt `chat_action.load_builtin_actions()` để ghi nhận danh sách module thực sự được nạp trong bộ nhớ `sys.modules`.
5. **So sánh với báo cáo ngày 30/9/2026**: Cơ sở mã nguồn đã phát triển thêm **51 module mới** (tập trung vào hệ thống `chat_action_*`, báo cáo điều tra, bộ câu hỏi chuẩn vàng `golden_question_*`, và giám sát luồng log). Báo cáo này cập nhật số liệu chuẩn xác nhất theo HEAD của nhánh `phieu-viec/rag-fix1`.

## 2. Kết quả tổng hợp

- **Tổng số module tính năng**: **267 module** (không tính gói gốc `aios_habit`).
- **Đã nối vào Chat**: **207 module** (77.5%) — bao gồm các module nạp trực tiếp khi mở app, nạp qua router hành động `chat_action`, nạp lazy theo điều kiện hoặc tiến trình con worker.
- **Chưa nối vào Chat**: **60 module** (22.5%) — các module độc lập chỉ dùng qua CLI, script kiểm thử, notebook cũ hoặc chưa có giao diện tích hợp trong chat.

| Nhóm | Tổng số | Đã nối chat | Chưa nối | Tỷ lệ đã nối |
|---|---:|---:|---:|---:|
| **RAG** | 58 | 43 | 15 | 74.1% |
| **benchmark** | 16 | 8 | 8 | 50.0% |
| **interview** | 16 | 15 | 1 | 93.8% |
| **prediction** | 32 | 29 | 3 | 90.6% |
| **visual** | 14 | 8 | 6 | 57.1% |
| **extract** | 11 | 10 | 1 | 90.9% |
| **memory** | 6 | 4 | 2 | 66.7% |
| **khác** | 114 | 90 | 24 | 78.9% |
| **Tổng cộng** | **267** | **207** | **60** | **77.5%** |

## 3. Bảng kiểm kê chi tiết theo 8 nhóm tính năng

### RAG — 58 module (Đã nối: 43, Chưa nối: 15)

| Module | Nhóm | Đã nối chat | Ghi chú / Điểm kết nối |
|---|---|---|---|
| `citation_answer` | RAG | có — gián tiếp | nối gián tiếp qua `rag_answer_composer` |
| `digest_qa` | RAG | không | test×1 |
| `final_answer_composer` | RAG | có — gián tiếp | nối gián tiếp qua `rag_answer_composer` |
| `index_domain` | RAG | có — trực tiếp (import khi gọi) |  |
| `knowledge_digest` | RAG | không | test×1 |
| `model_pack` | RAG | không | nội bộ: cli; test×1; script: 1 |
| `query_intent` | RAG | có — gián tiếp | nối gián tiếp qua `rag_search` |
| `query_planner` | RAG | có — trực tiếp (import khi gọi) |  |
| `question_suggestions` | RAG | có — trực tiếp (import khi gọi) |  |
| `rag_answer_composer` | RAG | có — gián tiếp | nối gián tiếp qua `ide_handoff_bridge` |
| `rag_core_profiles` | RAG | có — gián tiếp | nối gián tiếp qua `final_answer_composer` |
| `rag_evidence` | RAG | có — gián tiếp | nối gián tiếp qua `rag_answer_composer` |
| `rag_ingest` | RAG | có — gián tiếp | nối gián tiếp qua `chat_action_answer_quality` |
| `rag_rerank` | RAG | có — gián tiếp | nối gián tiếp qua `rag_benchmark` |
| `rag_search` | RAG | có — gián tiếp | nối gián tiếp qua `knowledge_publication` |
| `rag_v2` | RAG | có — một phần (nạp kèm gói cha) | nạp kèm gói cha khi chat import gói con |
| `rag_v2.adapters` | RAG | có — gián tiếp | nối gián tiếp qua `rag_v2` |
| `rag_v2.adaptive_retrieval` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_rag_v2_adapter` |
| `rag_v2.bge_onnx_backend` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_rag_v2_adapter` |
| `rag_v2.bge_subprocess_client` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_rag_v2_adapter` |
| `rag_v2.bge_subprocess_worker` | RAG | có — qua tiến trình con | chạy tiến trình con qua `bge_subprocess_client` (đã nối chat) |
| `rag_v2.bge_worker_protocol` | RAG | có — gián tiếp | nối gián tiếp qua `rag_v2.bge_subprocess_client` |
| `rag_v2.chunk_evaluation` | RAG | không | test×1; script: 1 |
| `rag_v2.chunk_revisions` | RAG | không | test×1 |
| `rag_v2.chunk_upload_config` | RAG | không | test×1 |
| `rag_v2.chunking` | RAG | có — gián tiếp | nối gián tiếp qua `rag_v2` |
| `rag_v2.converters` | RAG | có — gián tiếp | nối gián tiếp qua `rag_v2` |
| `rag_v2.eval_harness` | RAG | có — một phần (nạp kèm gói cha) | nạp kèm gói cha khi chat import gói con |
| `rag_v2.evidence` | RAG | có — gián tiếp | nối gián tiếp qua `rag_v2` |
| `rag_v2.index` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_rag_v2_adapter` |
| `rag_v2.index_bundle` | RAG | không | nội bộ: rag_v2.index_registry; test×1 |
| `rag_v2.index_registry` | RAG | không | test×1 |
| `rag_v2.ingest_manifest` | RAG | có — gián tiếp | nối gián tiếp qua `rag_v2` |
| `rag_v2.ingestion_jobs` | RAG | không | nội bộ: rag_v2.ingestion_service; test×2 |
| `rag_v2.ingestion_service` | RAG | không | test×1 |
| `rag_v2.ingestion_workers` | RAG | không | test×1 |
| `rag_v2.multilingual_query_expand` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_rag_v2_adapter` |
| `rag_v2.pipeline` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_rag_v2_adapter` |
| `rag_v2.query_planning` | RAG | có — trực tiếp (import khi gọi) |  |
| `rag_v2.registry` | RAG | có — gián tiếp | nối gián tiếp qua `rag_v2` |
| `rag_v2.remote_ingestion_client` | RAG | không | test×1 |
| `rag_v2.retrieval_backends` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_rag_v2_adapter` |
| `rag_v2.schema` | RAG | có — gián tiếp | nối gián tiếp qua `rag_v2` |
| `rag_v2.script_family` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_rag_v2_adapter` |
| `rag_v2.semantic` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_rag_v2_adapter` |
| `rag_v2.structured_query` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_rag_v2_adapter` |
| `rag_v2.summary_provenance` | RAG | có — gián tiếp | nối gián tiếp qua `rag_v2.chunking` |
| `rag_v2.synthesis` | RAG | có — gián tiếp | nối gián tiếp qua `rag_v2` |
| `rag_v2_synthesis_provider` | RAG | không | nội bộ: rag_v2.bge_subprocess_worker; test×1 |
| `shared_library_presets` | RAG | có — trực tiếp (import khi gọi) |  |
| `source_ingest` | RAG | có — gián tiếp | nối gián tiếp qua `chat_action_visual_maps` |
| `source_router` | RAG | có — gián tiếp | nối gián tiếp qua `final_answer_composer` |
| `split_index_by_domain` | RAG | không | test×1 |
| `strong_answer_ui` | RAG | không | test×1 |
| `workspace_chat_rag_v2_adapter` | RAG | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_rag_v2_deployment` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_rag_v2_adapter` |
| `workspace_chat_router_adapter` | RAG | có — gián tiếp | nối gián tiếp qua `workspace_chat_ai_answer` |
| `workspace_chat_source_ingest` | RAG | có — trực tiếp (nạp ngay) |  |

### benchmark — 16 module (Đã nối: 8, Chưa nối: 8)

| Module | Nhóm | Đã nối chat | Ghi chú / Điểm kết nối |
|---|---|---|---|
| `benchmark_reference_acquisition` | benchmark | không | test×1; script: 1 |
| `benchmark_reference_registry` | benchmark | không | nội bộ: benchmark_reference_acquisition, rag_v2.index_bundle, rag_v2.index_registry; test×2; script: 2 |
| `golden_answer_importer` | benchmark | có — gián tiếp | nối gián tiếp qua `expert_interview_session` |
| `golden_question_export` | benchmark | không | test×5 |
| `golden_question_generator` | benchmark | có — gián tiếp | nối gián tiếp qua `expert_interview_session` |
| `golden_question_quality` | benchmark | không | test×1 |
| `golden_question_schema` | benchmark | có — gián tiếp | nối gián tiếp qua `chat_interview_ui` |
| `golden_question_scorer` | benchmark | có — gián tiếp | nối gián tiếp qua `expert_interview_session` |
| `mom_benchmark` | benchmark | có — gián tiếp | nối gián tiếp qua `chat_action_answer_quality` |
| `mom_benchmark_gate` | benchmark | không | test×1 |
| `mom_coverage` | benchmark | không | test×1; script: 1 |
| `mom_local_index` | benchmark | không | nội bộ: mom_coverage; test×5 |
| `notebooklm_compare` | benchmark | không | nội bộ: cli; test×2 |
| `rag_benchmark` | benchmark | có — gián tiếp | nối gián tiếp qua `chat_action_answer_quality` |
| `rag_evaluator` | benchmark | có — gián tiếp | nối gián tiếp qua `chat_action_answer_quality` |
| `real_doc_inventory` | benchmark | có — gián tiếp | nối gián tiếp qua `mom_benchmark` |

### interview — 16 module (Đã nối: 15, Chưa nối: 1)

| Module | Nhóm | Đã nối chat | Ghi chú / Điểm kết nối |
|---|---|---|---|
| `adaptive_interview_engine` | interview | có — gián tiếp | nối gián tiếp qua `chat_action_expert_interview` |
| `chat_action_expert_interview` | interview | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_action_interview_chat` | interview | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_interview_ui` | interview | có — trực tiếp (import khi gọi) |  |
| `controlled_knowledge_artifact` | interview | có — gián tiếp | nối gián tiếp qua `workspace_case_ui` |
| `expert_identity` | interview | có — gián tiếp | nối gián tiếp qua `workspace_case_repository` |
| `expert_identity_windows` | interview | có — gián tiếp | nối gián tiếp qua `workspace_case_ui` |
| `expert_interview_models` | interview | có — gián tiếp | nối gián tiếp qua `workspace_case_ui` |
| `expert_interview_repository` | interview | có — gián tiếp | nối gián tiếp qua `workspace_case_ui` |
| `expert_interview_service` | interview | có — gián tiếp | nối gián tiếp qua `workspace_case_ui` |
| `expert_interview_session` | interview | có — gián tiếp | nối gián tiếp qua `chat_interview_ui` |
| `fine_tune_eligibility` | interview | không | test×2 |
| `knowledge_claim_extractor` | interview | có — gián tiếp | nối gián tiếp qua `controlled_knowledge_artifact` |
| `knowledge_coverage` | interview | có — gián tiếp | nối gián tiếp qua `workspace_case_repository` |
| `knowledge_publication` | interview | có — gián tiếp | nối gián tiếp qua `workspace_memory_service` |
| `local_transcription` | interview | có — gián tiếp | nối gián tiếp qua `workspace_case_ui` |

### prediction — 32 module (Đã nối: 29, Chưa nối: 3)

| Module | Nhóm | Đã nối chat | Ghi chú / Điểm kết nối |
|---|---|---|---|
| `cagent_api` | prediction | có — gián tiếp | nối gián tiếp qua `antigravity_bridge` |
| `chat_action_prediction` | prediction | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `in_app_risk_alert` | prediction | có — trực tiếp (nạp ngay) |  |
| `prediction_shadow_ui` | prediction | có — trực tiếp (nạp ngay) |  |
| `production_prediction` | prediction | có — một phần (nạp kèm gói cha) | nạp kèm gói cha khi chat import gói con |
| `production_prediction.alert_config_chat` | prediction | có — gián tiếp | nối gián tiếp qua `production_prediction.jig_chat_wire` |
| `production_prediction.alert_mailer` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.chart_selection` | prediction | có — gián tiếp | nối gián tiếp qua `production_prediction.jig_chat_wire` |
| `production_prediction.evaluation` | prediction | có — gián tiếp | nối gián tiếp qua `prediction_shadow_ui` |
| `production_prediction.iris_log_adapter` | prediction | có — gián tiếp | nối gián tiếp qua `production_prediction.jig_chat_wire` |
| `production_prediction.jig_alert_cards` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.jig_chat_wire` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.jig_csv_import` | prediction | có — gián tiếp | nối gián tiếp qua `production_prediction.jig_chat_wire` |
| `production_prediction.jig_log_ingest` | prediction | có — gián tiếp | nối gián tiếp qua `production_prediction.jig_chat_wire` |
| `production_prediction.log_archive` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.log_stream_ingest` | prediction | có — gián tiếp | nối gián tiếp qua `production_prediction.jig_chat_wire` |
| `production_prediction.lsu_iris` | prediction | có — gián tiếp | nối gián tiếp qua `prediction_shadow_ui` |
| `production_prediction.metric_limits` | prediction | có — gián tiếp | nối gián tiếp qua `production_prediction.jig_chat_wire` |
| `production_prediction.migrations` | prediction | có — gián tiếp | nối gián tiếp qua `production_prediction.repository` |
| `production_prediction.models` | prediction | có — gián tiếp | nối gián tiếp qua `prediction_shadow_ui` |
| `production_prediction.reporting` | prediction | không | test×2 |
| `production_prediction.repository` | prediction | có — trực tiếp (nạp ngay) |  |
| `production_prediction.rt_consumer` | prediction | không | test×1 |
| `production_prediction.rt_replay` | prediction | không | test×1 |
| `production_prediction.session_isolation` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.shadow` | prediction | có — gián tiếp | nối gián tiếp qua `prediction_shadow_ui` |
| `production_prediction.smtp_config` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.spc_chart` | prediction | có — gián tiếp | nối gián tiếp qua `production_prediction.jig_chat_wire` |
| `production_prediction.stream_api` | prediction | có — trực tiếp (import khi gọi) |  |
| `production_prediction.trend_alerts` | prediction | có — gián tiếp | nối gián tiếp qua `production_prediction.jig_chat_wire` |
| `production_prediction.trend_response` | prediction | có — gián tiếp | nối gián tiếp qua `production_prediction.jig_chat_wire` |
| `threshold_alert_chat` | prediction | có — trực tiếp (import khi gọi) |  |

### visual — 14 module (Đã nối: 8, Chưa nối: 6)

| Module | Nhóm | Đã nối chat | Ghi chú / Điểm kết nối |
|---|---|---|---|
| `chat_action_visual_maps` | visual | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `evidence_graph_viewer` | visual | có — trực tiếp (nạp ngay) |  |
| `excaliflow_adapter` | visual | có — gián tiếp | nối gián tiếp qua `evidence_graph_viewer` |
| `graphify_adapter` | visual | không | test×5; script: 1 |
| `knowledge_map_html` | visual | có — gián tiếp | nối gián tiếp qua `chat_action_visual_maps` |
| `knowledge_map_view` | visual | có — gián tiếp | nối gián tiếp qua `worklens_semantic_map` |
| `notebook_graph` | visual | không | test×1 |
| `visual_knowledge_map` | visual | có — gián tiếp | nối gián tiếp qua `chat_action_visual_maps` |
| `visual_map_builder` | visual | không | test×3 |
| `visual_map_export` | visual | không | nội bộ: visual_map_ui; test×2 |
| `visual_map_image` | visual | có — gián tiếp | nối gián tiếp qua `chat_action_visual_maps` |
| `visual_map_models` | visual | không | nội bộ: visual_map_builder, visual_map_export, visual_map_ui; test×4 |
| `visual_map_ui` | visual | không | test×1 |
| `worklens_semantic_map` | visual | có — gián tiếp | nối gián tiếp qua `chat_action_visual_maps` |

### extract — 11 module (Đã nối: 10, Chưa nối: 1)

| Module | Nhóm | Đã nối chat | Ghi chú / Điểm kết nối |
|---|---|---|---|
| `agent_result_import` | extract | có — gián tiếp | nối gián tiếp qua `workspace_agent_orchestrator` |
| `deep_document_parsers` | extract | có — gián tiếp | nối gián tiếp qua `document_extractors` |
| `document_extractors` | extract | có — gián tiếp | nối gián tiếp qua `workspace_chat_source_ingest` |
| `excel_extractors` | extract | có — gián tiếp | nối gián tiếp qua `agent_work_artifact` |
| `extraction` | extract | không | nội bộ: cli; test×30; script: 3 |
| `extractor_registry` | extract | có — gián tiếp | nối gián tiếp qua `document_extractors` |
| `line_log_parser` | extract | có — trực tiếp (import khi gọi) |  |
| `ocr_engines` | extract | có — gián tiếp | nối gián tiếp qua `document_extractors` |
| `workspace_chat_excel` | extract | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_folder_import` | extract | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_legacy_extractors` | extract | có — gián tiếp | nối gián tiếp qua `workspace_chat_source_ingest` |

### memory — 6 module (Đã nối: 4, Chưa nối: 2)

| Module | Nhóm | Đã nối chat | Ghi chú / Điểm kết nối |
|---|---|---|---|
| `learning_models` | memory | có — gián tiếp | nối gián tiếp qua `chat_action_visual_maps` |
| `memory` | memory | không | test×41; script: 10 |
| `study_store` | memory | không | test×1 |
| `workspace_memory_models` | memory | có — gián tiếp | nối gián tiếp qua `workspace_memory_service` |
| `workspace_memory_service` | memory | có — trực tiếp (import khi gọi) |  |
| `workspace_memory_ui` | memory | có — trực tiếp (import khi gọi) |  |

### khác — 114 module (Đã nối: 90, Chưa nối: 24)

| Module | Nhóm | Đã nối chat | Ghi chú / Điểm kết nối |
|---|---|---|---|
| `agent_doc_edit` | khác | có — gián tiếp | nối gián tiếp qua `agent_report_artifact` |
| `agent_draft_sop` | khác | có — trực tiếp (nạp ngay) |  |
| `agent_report_artifact` | khác | có — trực tiếp (import khi gọi) |  |
| `agent_report_feedback` | khác | có — gián tiếp | nối gián tiếp qua `chat_action_agent_report` |
| `agent_task_pack` | khác | có — gián tiếp | nối gián tiếp qua `agent_result_import` |
| `agent_work_artifact` | khác | có — trực tiếp (nạp ngay) |  |
| `ai_lane` | khác | có — trực tiếp (import khi gọi) |  |
| `ai_provider_bridge` | khác | có — gián tiếp | nối gián tiếp qua `ai_router` |
| `ai_router` | khác | có — trực tiếp (import khi gọi) |  |
| `answer_feedback` | khác | có — trực tiếp (import khi gọi) |  |
| `antigravity_bridge` | khác | có — trực tiếp (nạp ngay) |  |
| `audit` | khác | không | nội bộ: cli, phase_gate; test×19; script: 7 |
| `brain_gateway` | khác | có — gián tiếp | nối gián tiếp qua `workspace_chat_ai_answer` |
| `case_audit` | khác | không | test×5 |
| `case_models` | khác | có — gián tiếp | nối gián tiếp qua `antigravity_bridge` |
| `case_prompt` | khác | không | test×3 |
| `case_store` | khác | có — gián tiếp | nối gián tiếp qua `workspace_memory_service` |
| `chat_action` | khác | có — trực tiếp (import khi gọi) |  |
| `chat_action_agent_report` | khác | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_action_answer_quality` | khác | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_action_bao_cao_dieu_tra` | khác | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_action_case_form` | khác | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_action_data_paste` | khác | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_action_dieu_tra` | khác | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_action_error_lookup` | khác | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_action_log_stream` | khác | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_action_next_actions` | khác | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_action_phan_hoi` | khác | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_action_suggestion_review` | khác | có — trực tiếp qua action router | nạp qua builtin action router (`chat_action.py`) |
| `chat_intent_router` | khác | có — trực tiếp (import khi gọi) |  |
| `claim_guard` | khác | không | test×3 |
| `cli` | khác | không | test×42; script: 4 |
| `coding_assistant` | khác | có — gián tiếp | nối gián tiếp qua `workspace_case_ui` |
| `core` | khác | có — gián tiếp | nối gián tiếp qua `workspace_memory_service` |
| `daily_next_actions` | khác | có — gián tiếp | nối gián tiếp qua `chat_action_next_actions` |
| `discovery` | khác | không | nội bộ: cli; test×6 |
| `domain_playbooks` | khác | có — gián tiếp | nối gián tiếp qua `final_answer_composer` |
| `error_cases` | khác | có — một phần (nạp kèm gói cha) | nạp kèm gói cha khi chat import gói con |
| `error_cases.auto_classifier` | khác | có — gián tiếp | nối gián tiếp qua `error_cases.investigation_report` |
| `error_cases.backfill_fix` | khác | có — gián tiếp | nối gián tiếp qua `error_cases` |
| `error_cases.case_form` | khác | có — gián tiếp | nối gián tiếp qua `chat_action_case_form` |
| `error_cases.column_map` | khác | có — gián tiếp | nối gián tiếp qua `chat_action_dieu_tra` |
| `error_cases.completeness` | khác | có — gián tiếp | nối gián tiếp qua `error_cases` |
| `error_cases.feedback_loop` | khác | có — gián tiếp | nối gián tiếp qua `chat_action_error_lookup` |
| `error_cases.glossary` | khác | có — gián tiếp | nối gián tiếp qua `chat_action_error_lookup` |
| `error_cases.import_history` | khác | có — gián tiếp | nối gián tiếp qua `error_cases` |
| `error_cases.import_lsu_logs` | khác | có — gián tiếp | nối gián tiếp qua `error_cases` |
| `error_cases.investigation_report` | khác | có — gián tiếp | nối gián tiếp qua `chat_action_bao_cao_dieu_tra` |
| `error_cases.investigation_tree` | khác | có — gián tiếp | nối gián tiếp qua `chat_action_dieu_tra` |
| `error_cases.store` | khác | có — gián tiếp | nối gián tiếp qua `chat_action_error_lookup` |
| `error_cases.trend_analysis` | khác | có — gián tiếp | nối gián tiếp qua `error_cases.investigation_report` |
| `error_cases.trend_notify` | khác | có — gián tiếp | nối gián tiếp qua `error_cases` |
| `evidence` | khác | không | test×130; script: 17 |
| `evidence_trace` | khác | có — trực tiếp (nạp ngay) |  |
| `evidence_trace_schema` | khác | có — trực tiếp (nạp ngay) |  |
| `export_pack` | khác | không | nội bộ: cli; test×1 |
| `feature_flags` | khác | có — gián tiếp | nối gián tiếp qua `chat_action` |
| `gemini_web_engine` | khác | không | test×1; script: 1 |
| `handover` | khác | không | nội bộ: cli; test×4 |
| `i18n` | khác | có — trực tiếp (nạp ngay) |  |
| `ide_bridge` | khác | không | test×2 |
| `ide_handoff_bridge` | khác | có — trực tiếp (nạp ngay) |  |
| `library_backup` | khác | có — trực tiếp (import khi gọi) |  |
| `line_investigation` | khác | có — gián tiếp | nối gián tiếp qua `workspace_case_ui` |
| `llm_client` | khác | có — gián tiếp | nối gián tiếp qua `workspace_chat_ai_answer` |
| `local_folder_picker` | khác | có — trực tiếp (nạp ngay) |  |
| `local_jsonl` | khác | có — gián tiếp | nối gián tiếp qua `workspace_chat_store` |
| `models` | khác | không | nội bộ: audit, cli, discovery; test×85; script: 14 |
| `notebook_bridge` | khác | không | test×4 |
| `notebook_case_actions` | khác | không | test×2 |
| `notebook_import_store` | khác | có — gián tiếp | nối gián tiếp qua `daily_next_actions` |
| `notebook_index` | khác | có — gián tiếp | nối gián tiếp qua `daily_next_actions` |
| `notebook_qa` | khác | không | test×5 |
| `notebook_readiness` | khác | có — trực tiếp (import khi gọi) |  |
| `opencode_runtime_adapter` | khác | có — trực tiếp (nạp ngay) |  |
| `owner_workflow_state` | khác | không | test×1 |
| `paths` | khác | không | test×55; script: 11 |
| `phase_gate` | khác | không | nội bộ: cli; test×1 |
| `profiles` | khác | không | nội bộ: cli; test×4; script: 1 |
| `provider_catalog` | khác | có — gián tiếp | nối gián tiếp qua `ai_router` |
| `provider_health` | khác | có — gián tiếp | nối gián tiếp qua `ai_router` |
| `provider_model_discovery` | khác | có — gián tiếp | nối gián tiếp qua `ai_router` |
| `provider_safety` | khác | không | test×1 |
| `resilient_routing` | khác | có — gián tiếp | nối gián tiếp qua `ai_router` |
| `route_log_ui` | khác | không | test×1 |
| `router_adapter` | khác | có — gián tiếp | nối gián tiếp qua `workspace_chat_ai_answer` |
| `router_synth_redaction` | khác | không | test×1 |
| `safety_modes` | khác | có — gián tiếp | nối gián tiếp qua `ai_router` |
| `self_improvement` | khác | có — gián tiếp | nối gián tiếp qua `chat_interview_ui` |
| `shared_ai_provider_fabric` | khác | có — gián tiếp | nối gián tiếp qua `provider_catalog` |
| `shared_mailbox` | khác | có — trực tiếp (import khi gọi) |  |
| `storage` | khác | không | nội bộ: audit, cli, evidence; test×18; script: 1 |
| `suggestion_feedback` | khác | có — gián tiếp | nối gián tiếp qua `chat_interview_ui` |
| `ui_safety` | khác | có — trực tiếp (nạp ngay) |  |
| `workflow` | khác | không | test×12; script: 2 |
| `workspace_agent_bridge_client` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_agent_models` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_agent_orchestrator` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_agent_policy` | khác | có — gián tiếp | nối gián tiếp qua `workspace_agent_orchestrator` |
| `workspace_case_authorization` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_case_migrations` | khác | có — gián tiếp | nối gián tiếp qua `workspace_case_repository` |
| `workspace_case_models` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_case_repository` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_case_service` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_case_ui` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_ai_answer` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_answer_preview` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_app` | khác | có — gián tiếp |  |
| `workspace_chat_connector_guard` | khác | có — gián tiếp | nối gián tiếp qua `antigravity_bridge` |
| `workspace_chat_models` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_store` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_chat_ui` | khác | có — trực tiếp (nạp ngay) |  |
| `workspace_models` | khác | có — gián tiếp | nối gián tiếp qua `chat_action_visual_maps` |
| `workspace_paths` | khác | có — trực tiếp (nạp ngay) |  |

## 4. Phân tích các module chưa nối & Kiến nghị lộ trình

*(Sửa mục 4 ngày 2026-10-04: đồng bộ với bảng, kiểm tra bằng script)*

Qua đối chiếu thực tế với bảng kiểm kê, có đúng 60 module chưa nối vào giao diện chat, phân bổ theo các nhóm chức năng như sau:

1. **Nhóm Benchmark (8 module chưa nối)**: `benchmark_reference_acquisition`, `benchmark_reference_registry`, `golden_question_export`, `golden_question_quality`, `mom_benchmark_gate`, `mom_coverage`, `mom_local_index`, `notebooklm_compare`. Các module này hiện chỉ phục vụ đo lường benchmark offline qua dòng lệnh hoặc kịch bản kiểm thử. Kiến nghị đưa lệnh kích hoạt benchmark nhanh (hoặc xem kết quả benchmark gần nhất) thành hành động trả lời trực tiếp trong chat.
2. **Nhóm RAG v2 chuyên sâu (15 module chưa nối)**: `digest_qa`, `knowledge_digest`, `model_pack`, `rag_v2.chunk_evaluation`, `rag_v2.chunk_revisions`, `rag_v2.chunk_upload_config`, `rag_v2.index_bundle`, `rag_v2.index_registry`, `rag_v2.ingestion_jobs`, `rag_v2.ingestion_service`, `rag_v2.ingestion_workers`, `rag_v2.remote_ingestion_client`, `rag_v2_synthesis_provider`, `split_index_by_domain`, `strong_answer_ui`. Phần lớn là hạ tầng nạp dữ liệu (ingestion) ngầm, đánh giá chất lượng chunk hoặc service nền. Kiến nghị nối trạng thái tiến độ ingestion nền vào thông báo chat.
3. **Nhóm Visual (6 module chưa nối)**: `graphify_adapter`, `notebook_graph`, `visual_map_builder`, `visual_map_export`, `visual_map_models`, `visual_map_ui`. Các module xây dựng và kết xuất sơ đồ trực quan. Kiến nghị cho phép hiển thị sơ đồ tri thức hoặc đồ thị phụ thuộc dạng xem trước trực tiếp trong khung hội thoại chat.
4. **Nhóm Khác & các nhóm chức năng chuyên biệt (31 module chưa nối)**:
   - **Phân nhóm Khác (24 module)**: `audit`, `case_audit`, `case_prompt`, `claim_guard`, `cli`, `discovery`, `evidence`, `export_pack`, `gemini_web_engine`, `handover`, `ide_bridge`, `models`, `notebook_bridge`, `notebook_case_actions`, `notebook_qa`, `owner_workflow_state`, `paths`, `phase_gate`, `profiles`, `provider_safety`, `route_log_ui`, `router_synth_redaction`, `storage`, `workflow`. Chủ yếu là các module dòng lệnh CLI cũ, kiểm toán nội bộ, quản lý pha cổng kiểm tra chất lượng, bộ cung cấp web engine hoặc các mô hình/kho lưu trữ độc lập. Có thể giữ nguyên độc lập hoặc đưa lệnh kiểm toán nhanh vào hành động của bot.
   - **Phân nhóm Prediction (3 module)**: `production_prediction.reporting`, `production_prediction.rt_consumer`, `production_prediction.rt_replay`. Các module tạo báo cáo dự đoán sự cố, tiêu thụ log và phát lại luồng sự kiện sản xuất thời gian thực. Kiến nghị tích hợp xem báo cáo dự đoán theo yêu cầu vào giao diện chat.
   - **Phân nhóm Memory (2 module)**: `memory`, `study_store`. Module quản lý bộ nhớ tiến trình và lưu trữ ca học sâu độc lập. Có thể giữ nguyên độc lập hoặc đồng bộ vào dịch vụ bộ nhớ workspace chat.
   - **Phân nhóm Extract (1 module)**: `extraction`. Module trích xuất đa định dạng mức thấp qua dòng lệnh CLI. Hệ thống chat hiện đã có bộ trích xuất riêng; có thể nối thêm các parser còn thiếu nếu cần mở rộng định dạng tệp.
   - **Phân nhóm Interview (1 module)**: `fine_tune_eligibility`. Module kiểm tra điều kiện dữ liệu phục vụ huấn luyện tinh chỉnh mô hình ngoại tuyến. Kiến nghị tích hợp thành bước kiểm tra tự động trước khi xuất gói dữ liệu phỏng vấn chuyên gia.
