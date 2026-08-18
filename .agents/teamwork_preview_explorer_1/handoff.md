# Handoff Report: Survey of `layers`, `tour`, Root Structure & IT Terminology

**From Agent**: `teamwork_preview_explorer_1`  
**To Agent**: `teamwork_preview_orchestrator_1` (Parent)  
**Date**: 2026-08-19  
**Handoff Type**: Hard (Task complete)  

---

## 1. Observation

1. **File Location & Metrics**:
   - Target File: `.understand-anything/knowledge-graph.json` (Line count: 2,663 lines; Size: 92,229 bytes; Encoding: UTF-8).
   - Root Keys (Line 2, 3, 18, 1744, 2094, 2551): `"version"`, `"project"`, `"nodes"`, `"edges"`, `"layers"`, `"tour"`.

2. **Layers Structure (Lines 2094 to 2550)**:
   - Exactly **8 layer objects** in `layers` array.
   - Each element schema: `{"id": string, "name": string, "description": string, "nodeIds": string[]}`.
   - Layer IDs:
     1. `layer:presentation-ui` (7 nodes)
     2. `layer:orchestration-agents` (12 nodes)
     3. `layer:intelligence-routing` (10 nodes)
     4. `layer:knowledge-retrieval` (15 nodes)
     5. `layer:data-storage` (47 nodes)
     6. `layer:testing-quality` (71 nodes)
     7. `layer:specifications-tooling` (45 nodes)
     8. `layer:governance-documentation` (196 nodes)

3. **Tour Structure (Lines 2551 to 2662)**:
   - Exactly **9 tour step objects** in `tour` array.
   - Each element schema: `{"order": integer, "title": string, "description": string, "nodeIds": string[]}`.
   - Step orders 1 to 9 covering all key architectural flows from System Overview, Data Models, Document Ingestion, Retrieval, Intelligence Routing, Citation Grounding, Agent Orchestration, UI, to Specs/QA.

4. **Project Glossary & Governance Standards**:
   - `docs/governance/LOCALIZATION_GLOSSARY.md` (Lines 1-30) mandates:
     - Keep technical terms in English when explained or clear in context.
     - Standardized Vietnamese translations: `evidence` -> `bằng chứng`, `source` -> `nguồn` / `nguồn dữ liệu`, `privacy label` -> `nhãn bảo mật`, `insufficient evidence` -> `chưa đủ bằng chứng`, `fallback` -> `phương án dự phòng`.
   - `01_design/TERMINOLOGY.md` (Lines 1-31) defines: `bản ghi bằng chứng` (Evidence Record), `bộ nhớ ứng viên` (Candidate Memory), `bộ nhớ đã xác thực` (Validated Memory), `hồ sơ tổng thể` (Master Profile), `gói xuất` (Export Pack), `cổng kiểm soát giai đoạn` (Phase Gate).

---

## 2. Logic Chain

1. **Step 1: Structural Integrity (from Obs 1 & 2)**:
   - The knowledge graph relies on `id` matching between `nodes[].id` and `nodeIds` in `layers` and `tour`.
   - Therefore, `id`, `nodeIds`, `version`, `edges`, `type`, `order`, and file paths MUST NOT be modified or translated.
2. **Step 2: Translation Boundary for Layers & Tour (from Obs 2 & 3)**:
   - For `layers`: Only `name` and `description` are translatable.
   - For `tour`: Only `title` and `description` are translatable.
   - `project.description` can be translated as auxiliary project summary.
3. **Step 3: IT Terminology Strategy (from Obs 4 & User Request)**:
   - Core IT terms (`Agent`, `Multi-agent`, `Orchestration`, `Framework`, `Dashboard`, `Local Storage`, `Streamlit`, `Pydantic`, `JSONL`, `SQLite`, `CLI`, `OCR`, `RAG`, `BM25`, `Brain Gateway`, `Claim Guard`, `Spec-Kit`) are preserved in English to prevent ambiguity and preserve developer clarity.
   - System domain concepts are translated using established project glossary terms (`bản ghi bằng chứng`, `kho bộ nhớ`, `bộ nhớ ứng viên`, `cổng kiểm soát giai đoạn`).

---

## 3. Caveats

- **Nodes array**: The detailed survey and translation of 727 node summaries in `nodes` array is scoped to `teamwork_preview_explorer_2` and translation workers.
- **Project description**: `project.description` ("Local-first evidence-based personal memory platform") was surveyed and provided with a Vietnamese equivalent, but workers can decide whether to translate it or keep the metadata object untouched.
- No other unexamined areas within `layers`, `tour`, and root metadata.

---

## 4. Conclusion

- The survey of root structure, `layers`, `tour`, and IT terminology for `.understand-anything/knowledge-graph.json` is complete and documented in detail in `analysis.md`.
- All 8 layers and 9 tour steps have been fully analyzed, mapped, and provided with proposed Vietnamese translations ready for immediate merging by implementers.
- All core IT terms to preserve vs project-specific terms to standardize in Vietnamese have been categorized.

---

## 5. Verification Method

To independently verify the survey findings:
1. **Root keys check**:
   Inspect line 2, 3, 18, 1744, 2094, 2551 of `.understand-anything/knowledge-graph.json` using `view_file`.
2. **Layer count check**:
   Search for `"id": "layer:` in `.understand-anything/knowledge-graph.json` (returns 8 matches).
3. **Tour count check**:
   Search for `"order":` in `.understand-anything/knowledge-graph.json` (returns 9 matches).
4. **File Output**:
   Check `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_1\analysis.md`.
