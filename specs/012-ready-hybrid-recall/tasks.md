# Tasks: 012-ready-hybrid-recall

## Phase 1 — Nền

- [X] T001 Tạo `src/aios_habit/rag_v2/script_family.py` (latin/cjk/mixed, majority, mismatch)
- [X] T002 [P] Test `tests/test_rag_v2_script_family.py`

## Phase 2 — US1 cửa sổ ready

- [X] T003 [US1] Test lệch chữ không cắt 3; kho nhỏ Matecon vẫn hẹp trong `tests/test_workspace_chat_rag_v2_adapter.py`
- [X] T004 [US1] Sửa `_retrieval_source_window` trong `src/aios_habit/workspace_chat_rag_v2_adapter.py`

## Phase 3 — US2 ranking

- [X] T005 [US2] `hybrid_ranking_for_texts` + gắn vào `search_hybrid` trong `src/aios_habit/rag_v2/index.py`
- [X] T006 [P] [US2] Test trọng số lệch chữ

## Phase 4 — US3 retry mỏng

- [X] T007 [US3] Một lần retry khi ≤1 document và index còn nhiều tài liệu trong `search_hybrid`
- [X] T008 [US3] Test đánh dấu/hành vi retry

## Phase 5 — Polish

- [X] T009 compileall, pytest tập trung, CLI audit; cấm BQ-id trong mã mới (144 passed, audit PASS)
