# COMMERCIAL OWNER UI REDESIGN REPORT

## What Changed
- Refactored `case_cockpit.py` to add `Bản đồ tri thức`.
- Replaced internal terminology with business-facing language (e.g. "Prompt Pack" -> "Hỏi AI từ bằng chứng").
- Added a 5-step guided workflow ("Quy trình đề xuất").
- Export maps to Mermaid, Markmap, HTML.

## Before/After UX Summary
- **Before:** JSON heavy, exposing RAG chunks and debug logs explicitly.
- **After:** Owner-focused summary stats. Visual node relationships. Internal debug info hidden under technical detail expanders.
