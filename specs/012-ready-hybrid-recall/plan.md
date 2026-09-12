# Kế hoạch: 012-ready-hybrid-recall

**Branch**: `gate1-local-case-sqlite` | **Date**: 2026-09-12 | **Spec**: [spec.md](spec.md)

## Summary

Nâng tỉ lệ tìm đúng trên nguồn đã ready khi câu hỏi và kho khác hệ chữ, không hardcode ngữ liệu. Giữ BGE-M3 Hybrid. Giữ cắt 3 lúc **chuẩn bị**. Truy xuất: bỏ cắt khi lệch script; hybrid ưu tiên dense; một lần retry nếu kết quả mỏng.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: Workspace Chat RAG v2 adapter, `LocalChunkIndex.search_hybrid`, BGE-M3 subprocess worker

**Storage**: Index SQLite hiện có (read-only lúc query)

**Testing**: pytest tập trung adapter + index + query planning

**Target Platform**: Windows local Workspace Chat

**Project Type**: library + Streamlit Workspace Chat

**Performance Goals**: Query hybrid trên sổ ~100 nguồn ready vẫn hoàn tất trong timeout deep hiện có

**Constraints**: Không GraphRAG, không rebuild index, không BQ-id, không dịch câu hỏi bằng cloud trên `local_only`

**Scale/Scope**: Lát retrieval; không đổi composer/UI

## Constitution Check

- Privacy: không gửi chữ tài liệu để dịch query.
- Không fake PASS; không hardcode ngữ liệu (AGENT_RULES).
- Không import studio/case_cockpit.
- Xác minh: compileall, pytest tập trung, audit.

## Project Structure

```text
specs/012-ready-hybrid-recall/
src/aios_habit/rag_v2/script_family.py
src/aios_habit/workspace_chat_rag_v2_adapter.py
src/aios_habit/rag_v2/index.py
tests/test_rag_v2_script_family.py
tests/test_workspace_chat_rag_v2_adapter.py
tests/test_rag_v2_index.py
```
