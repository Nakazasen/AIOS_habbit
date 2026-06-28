# Visual Knowledge Map >90 & Commercial UI Design

## Current UI Pain Points
- Feels too technical (developer/debug oriented).
- Uses raw terms like "Prompt pack", "Local Evidence Draft", "RAG", "Chunk".
- Visual knowledge map/mindmap is weak (~45-50% readiness).
- Too many confusing buttons exposed by default.
- Lacks a guided owner-friendly daily workflow.

## Commercial UX Target
- **Clear & Visual**: Streamlined views, hiding JSONs and debug details.
- **Guided**: 5-step progress bar (Sự việc -> Bằng chứng -> Hỏi AI -> Lưu câu trả lời -> Rút bài học).
- **Less Technical**: Hide backend terminology under an expandable "Chi tiết kỹ thuật" accordion.
- **Workflow-first**: Action-oriented buttons ("Tạo mindmap", "Hỏi AI từ bằng chứng").
- **Vietnamese-first**: Owner-facing labels in Vietnamese.

## Visual Knowledge Map Target
Achieve >90% readiness for P1 owner pilot by rendering clear, associative graphs from evidence to lessons.
- **Data Model**: Case, Evidence, System, Symptom, Cause, Action, Lesson, AI Answer, Source.
- **Edges**: `case_has_evidence`, `answer_cites_evidence`, `cause_requires_action`, `action_creates_lesson`, etc.
- **Privacy**: Track `local_only` vs `cloud_safe` metadata in nodes.

## UI Layout
1. **Home / Today** ("Hôm nay cần xử lý gì?"): Summary cards, recent tasks.
2. **Quick Case** ("Nhập nhanh sự việc"): One-screen intake.
3. **Ask from Evidence** ("Hỏi từ bằng chứng"): Simplification of Strong Answer and IDE Handoff. 3 big buttons.
4. **Knowledge Map** ("Bản đồ tri thức"): Visual map with Mermaid/HTML render, interactive filters, node detail panel.
5. **Learning Memory** ("Rút bài học"): Extract reusable insights.
6. **Handover** ("Tạo bàn giao"): Safe summary for handover.

## Interaction Model
- Select node -> view details in side panel / under the graph.
- Expand "Chi tiết kỹ thuật" only if debugging.
- Click to export to Mermaid, Markdown, HTML.

## Privacy & Policies
- No cloud call policy strictly enforced.
- Do not call NotebookLM APIs.
- Do not upload `local_only` data.

## Test Plan
- Unit tests for visual knowledge map graph generation and exports (Mermaid, Markdown, HTML).
- UI copy tests to ensure technical words are hidden.
- Validation that local_only data is preserved and protected.

## Acceptance Criteria
- [ ] Visual map correctly models relationships (case, evidence, answer, lesson).
- [ ] UI is successfully refactored to match the Commercial UX Target.
- [ ] Guided workflow renders correctly based on case state.
- [ ] Tests pass (pytest, CLI audit).
- [ ] No local_runs or raw data committed.
- [ ] NotebookLM parity claimed: NO.
- [ ] P1.0 opened: NO.
