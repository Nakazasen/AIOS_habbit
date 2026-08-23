# Validation Guide

## Prerequisites

- BGE-M3 Local Pilot or a valid activated deployment is available.
- Start Workspace Chat normally; no Gemini call is needed for preparation tests.

## Scenarios

1. Upload three new searchable documents. The UI returns immediately and shows `0/3 sẵn sàng`, then progresses until `3/3` without another question.
2. Restart during the second document. Reopen the notebook and confirm ready content is reused, the interrupted item is requeued, and progress continues.
3. With one ready and one pending document, ask a precise ready-document question. It proceeds immediately.
4. Ask about the pending document once. Confirm the retained question is answered exactly once after it becomes ready; cancel stops only the retained question.
5. Replace, disable, and delete a source during preparation. Confirm no stale answer or orphan index remains.
6. Inspect an AI response. It shows the bridge, Gemini Web provider, “Chưa xác minh tên model” when applicable, and grouped evidence such as `3 đoạn từ 1 tài liệu`.

## Automated verification

Run focused queue, pending-question, provenance, and UI tests first, then the full pytest suite and the project audit required by the constitution.
