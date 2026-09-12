# Nhiệm Vụ: Nâng Cấp Tổng Hợp Đa Tài Liệu Xuyên Nguồn (Tasks: Cross-Source Multi-Document Synthesis Upgrade)

- [x] T001: Triển khai phát hiện ý định truy vấn & phân rã truy vấn con trong `src/aios_habit/rag_v2/query_planning.py`.
- [x] T002: Tăng cường `search_hybrid` và kết hợp RRF trong `src/aios_habit/rag_v2/index.py` cho ngân sách đa truy vấn động.
- [x] T003: Cập nhật `EvidencePackConfig` và xử lý ngưỡng bao phủ trong `src/aios_habit/rag_v2/evidence.py`.
- [x] T004: Thêm các bài kiểm thử đơn vị tập trung trong `tests/test_rag_v2_cross_source_upgrade.py`.
- [ ] T005: Chạy bộ kiểm thử đầy đủ cuối cùng và xác minh tổng hợp đa tài liệu đầu cuối trên các câu hỏi đo chuẩn; ghi nhận bằng chứng chính xác trước khi đóng.
  - 2026-09-12: `uv run --no-sync --group dev pytest -q --durations=20` → **2778 passed, 2 failed** in 711.31s. Hai fail: `test_desktop_build_prerequisites_function` (`verified_wheels` 3 < 80) và `test_app_preparation_gate_is_scoped_to_query_relevant_sources` (chuỗi Non-blocking RAG). Không đánh dấu xong. Không chạy lại battle BQ02/BQ07/BQ10 (cấm `--run` chưa niêm phong).
  - 2026-09-12 lát chất lượng (phương án A): planner cục bộ + cửa sổ truy xuất đa ý + tổng hợp theo facet. Test tập trung `test_rag_v2_query_planning.py`, `test_rag_v2_cross_source_upgrade.py`, `test_rag_v2_synthesis.py`, `test_workspace_chat_rag_v2_adapter.py`, `test_rag_v2_index.py` đạt. Không tuyên bố TECHNICAL_PASS.

