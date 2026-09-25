# FIX 3 — Báo cáo định tuyến summary-first

## 1. Tóm tắt thay đổi

Thêm đường định tuyến cho câu hỏi chung chung. Đường cũ không bị xoá và vẫn là đường mặc định.

- `src/aios_habit/rag_v2/query_planning.py`: `detect_retrieval_mode` tách `overview` / `focused` / `full`. `apply_summary_first_to_plan` chỉ được gọi khi flag bật, và khi đó cắt số biến thể theo mode.
- `src/aios_habit/rag_v2/index.py`: `search_summaries_with_summary` chỉ xếp hạng chunk `file_type=document_summary`. Không nhúng, không quét chunk thân.
- `src/aios_habit/rag_v2/pipeline.py`: flag bật thì `overview` dừng ở summary (tối đa 15 tài liệu) và được phép trả lời kèm ghi chú tổng quan. `focused` chọn tài liệu từ summary rồi mới search đầy đủ trong các tài liệu đó. `full` giữ pipeline cũ. Intent không phải overview không được nới abstain.

## 2. Bảng benchmark trước/sau

Người dùng không đưa câu hỏi. Bảng dưới là **câu mẫu**, đo trên index canary `local_runs/workspace_chat_rag_v2_canary/bge_m3_hybrid/workspace_chat.sqlite`: 2132 chunk, 28 summary. Một lần mỗi câu. Đường lexical, không nạp BGE. Đơn vị giây.

| Câu | Mode | Quét đầy đủ | Summary-only + synthesis | Abstain sau khi bật |
| --- | --- | ---: | ---: | --- |
| Tóm tắt các tài liệu đã nạp | overview | 0.476817 | 0.041162 | không |
| Tổng quan hệ thống | overview | 0.066598 | 0.031446 | không |
| What is this corpus about? | overview | 0.048187 | 0.026858 | không |
| Giới thiệu các tài liệu | overview | 0.076284 | 0.037921 | không |
| Overview of the collected manuals | overview | 0.044840 | 0.027502 | không |

Năm câu chi tiết, vẫn đi đường đầy đủ hoặc focused, không nới abstain. Thời gian quét lexical đầy đủ:

| Câu | Mode | Giây | Hit | Hit summary trong top lexical |
| --- | --- | ---: | ---: | ---: |
| What is the exact cell range for SKU-123? | full | 0.110686 | 15 | 0 |
| Kiểm tra lỗi C001 trên máy A | full | 0.087049 | 15 | 3 |
| Làm thế nào để reset máy X200? | full | 0.091851 | 15 | 1 |
| Compare version 1 and version 2 of SOP-ABC | full | 0.123194 | 15 | 2 |
| How does data flow between the tank system and the pump controller? | focused | 0.057395 | 2 | 0 |

Không có số đo hybrid BGE trước/sau. Index canary không phải tập 50k chunk trong phiếu.

## 3. So sánh chất lượng

Câu mẫu, không phải câu người dùng giao.

Overview, flag bật, có câu trả lời trích từ summary và có dòng `Ghi chú: trả lời ở mức tổng quan.`:

- `Tóm tắt các tài liệu đã nạp`: không abstain. Trích mở đầu nói về xử lý EDI/Lot ngày 17.06.2026 và một đoạn XML slide. Summary trong index này lẫn nội dung thô.
- `Tổng quan hệ thống`: không abstain. Trích phân loại lỗi nhóm 1 / nhóm 2.
- `What is this corpus about?`: không abstain. Trích mục lục EBOM-MBOM và chương 4.
- `Giới thiệu các tài liệu`: không abstain. Trích XML slide và dòng thiết lập dữ liệu.
- `Overview of the collected manuals`: không abstain. Cùng kiểu trích mục lục với câu tiếng Anh phía trên.

Chi tiết: mode `full` hoặc `focused`, không gắn ghi chú tổng quan, không hạ ngưỡng abstain. Test `test_pipeline_overview_answers_from_summaries_only_when_enabled` khoá: flag tắt thì câu tổng quan vẫn `lexical` và `retrieval_mode=full`; flag bật thì overview chỉ trả summary; câu SKU-123 vẫn `full`/`lexical`; câu data-flow focused chỉ còn document mà summary có chữ pump. Chưa so tay câu trả lời BGE cũ và mới trên cùng 5 câu chi tiết.

## 4. Kết quả `pytest tests/`

`pytest -q tests` trong 453.35 giây: **3124 passed, 3 skipped, 4 failed**. Không có test mới nào đỏ. `tests/test_rag_v2_summary_first.py` nằm trong số passed.

Bốn lỗi không nằm trong diff của FIX 3, cùng lớp đã ghi ở FIX 2:

- `tests/test_commit_d_wheel_and_packaging.py::TestDependencyManifestLockIntegrity::test_uv_lock_check_succeeds`: `uv lock --check` báo lockfile cần cập nhật. `pyproject.toml` và `uv.lock` không đổi.
- `tests/test_commit_d_wheel_and_packaging.py::TestBgeM3ModelPackPackaging::test_bge_m3_model_pack_verification_and_discovery`: cây model cục bộ hash ra `sha256:697a97c…`, test cứng pin cũ `sha256:b1d887e…`.
- `tests/test_commit_d_wheel_and_packaging.py::TestCleanMachineSmokeScript::test_clean_machine_full_isolated_venv_installation`: pip không tìm thấy `streamlit>=1.60.0`.
- `tests/test_mom_local_pilot.py::test_document_extractor_png_ocr_local_or_safe_unsupported`: lỗi phụ thuộc thứ tự đã ghi từ trước. FIX 2 chạy riêng thì đạt.

`scripts/check_docs.py` in `DOCUMENTATION_CONTRACT=PASS`.

## 5. Flag rollback

- `AIOS_RAG_V2_SUMMARY_FIRST`: mặc định không đặt, tức tắt. `1` / `true` / `yes` / `on` bật. `0` / `false` / `no` / `off` tắt.
- `RagV2DevConfig.summary_first_routing`: mặc định `False`. Biến môi trường thắng nếu được đặt.
- `overview_max_variants` / `focused_max_variants`: mặc định 3. `full_max_variants`: mặc định 8.
- `overview_summary_limit`: mặc định 15. `focused_summary_doc_limit`: mặc định 10.
- Tắt flag là về đủ biến thể và abstain cũ. Không đụng `BGE_BACKEND`.

## 6. Điểm khác với phiếu việc

- Phiếu nêu intent `summarize_document` và `open_ended_research`. Planner hiện tại không phát hai nhãn đó; nó phát `general`, `procedure`, `cross_source_synthesis`. Mode overview được nhận từ các nhãn đó nếu có, cộng câu chữ tổng quan, cộng câu ngắn không có mã/số hiệu.
- Không hỏi lại người dùng vì phiếu yêu cầu tự dùng câu mẫu nếu không được cung cấp, và ghi rõ đó là câu mẫu.
- Two-stage không nhúng ở stage 1. Stage 1 là lexical trên summary. Stage 2 mới vào pipeline đầy đủ, nên vẫn có thể nhúng nếu hồ sơ retrieval cần embed.
- Câu mơ hồ dài, không có mã, đi `focused` (3 biến thể + giới hạn tài liệu), không phải lúc nào cũng 8 biến thể. Câu có mã hoặc procedure giữ `full`.

## 7. Đánh giá

Không đạt đủ tiêu chí nghiệm thu. Năm câu mẫu đều có câu trả lời dưới 10 giây và không abstain trên index canary, nhưng đó không phải câu thật của người dùng, và chất lượng trích xuất bị kéo bởi summary đang lẫn XML. Năm câu chi tiết chưa được so tay với câu trả lời cũ. Flag giữ tắt.
