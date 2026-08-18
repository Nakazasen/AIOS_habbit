# Understand Dashboard Compatibility & Render Audit Report

**Target File**: `d:\Sandbox\AIOS_habbit\.understand-anything\knowledge-graph.json`  
**Auditor**: `teamwork_preview_challenger_2` (Dashboard Compatibility & Render Challenger)  
**Date**: 2026-08-19  
**Status**: ⚠️ **REQUEST_CHANGES** (Actionable schema fixes required)

---

## Executive Summary

An exhaustive compatibility analysis of `knowledge-graph.json` against `@understand-anything/core/schema.ts`, `NodeInfo.tsx`, `LayerLegend.tsx`, `LearnPanel.tsx`, and `store.ts` (SearchEngine) was conducted.

| Category | Status | Details |
|---|---|---|
| **Core Schema Validation (`schema.ts`)** | ⚠️ **Issues Found** | 6 invalid edge types dropped by `validateGraph()`; missing `weight` attribute across all edges |
| **Node Summary Markdown & Text (`NodeInfo.tsx`)** | ✅ **100% COMPATIBLE** | No broken markdown tags, clean UTF-8 strings, valid JSX paragraph rendering |
| **Layer Structure (`LayerLegend.tsx`)** | ✅ **100% COMPATIBLE** | All 8 architectural layers strictly follow `LayerSchema`, valid node references, modulo palette support |
| **Guided Tour (`LearnPanel.tsx`)** | ✅ **100% COMPATIBLE** | All 9 tour steps strictly follow `TourStepSchema`, orders 1–9, valid component pills, ReactMarkdown rendering |
| **Vietnamese Search Indexing (`store.ts`)** | ✅ **100% COMPATIBLE** | SearchEngine / Fuse.js indexes UTF-8 Vietnamese summaries without encoding errors |

---

## Detailed Findings & Attack Surface Analysis

### 1. Schema Validation against `@understand-anything/core/schema.ts`

#### Issue 1.1: 6 Edge Types Are Non-Canonical & Unaliased (Severity: HIGH)
`@understand-anything/core/schema.ts` defines 35 canonical edge types (`EdgeTypeSchema`) and a dictionary of aliases (`EDGE_TYPE_ALIASES`).
When `validateGraph()` runs on `knowledge-graph.json`, 6 edges fail `GraphEdgeSchema.safeParse()` because their `type` is neither in `EdgeTypeSchema` nor in `EDGE_TYPE_ALIASES`. As a result, `validateGraph()` marks them as `invalid-edge` and silently **drops** them.

| Line | Edge Source | Edge Target | Raw Edge Type | Status in `schema.ts` | Recommended Canonical Type |
|---|---|---|---|---|---|
| **1772** | `file:.agents/teamwork_preview_reviewer_2/plan.md` | `file:.agents/teamwork_preview_reviewer_2/progress.md` | `"updates"` | ❌ Unrecognized (Dropped) | `"documents"` or `"transforms"` |
| **1862** | `file:docs/rag_v2/AUTOMATED_INGESTION_OPERATIONS.md` | `file:docs/rag_v2/RAG_V2_DESIGN.md` | `"refers_to"` | ❌ Unrecognized (Dropped) | `"references"` (aliased to `"cites"`) or `"documents"` |
| **1868** | `file:docs/rag_v2/SAME_PROTOCOL_ANSWER_QUALITY_PROTOCOL.md` | `file:docs/rag_v2/RAG_V2_DESIGN.md` | `"refers_to"` | ❌ Unrecognized (Dropped) | `"references"` (aliased to `"cites"`) or `"documents"` |
| **1874** | `file:docs/rag_v2/BLIND_RERUN_QUESTIONS_DRAFT.json` | `file:docs/rag_v2/benchmark_gold_identity.schema.json` | `"follows_schema"` | ❌ Unrecognized (Dropped) | `"defines_schema"` or `"implements"` |
| **1940** | `file:specs/excel-structured-query-remediation/tasks.md` | `file:specs/excel-structured-query-remediation/plan.md` | `"tracks"` | ❌ Unrecognized (Dropped) | `"documents"` or `"depends_on"` |
| **2078** | `file:tests/test_rag_v2_ingestion_service.py` | `file:src/aios_habit/rag_v2/ingestion_service.py` | `"tests"` | ❌ Unrecognized (Dropped) | `"tested_by"` (or inverted to `prod -> test`) |

#### Issue 1.2: Missing `weight` Field Across All Edges (Severity: MEDIUM)
- `GraphEdgeSchema` requires `weight: z.number().min(0).max(1)`.
- All 58 edges in `knowledge-graph.json` omit `"weight"`.
- *Impact*: While runtime `autoFixGraph()` injects `weight: 0.5` with an `"auto-corrected"` warning, strict schema verification directly against `GraphEdgeSchema.safeParse()` fails.
- *Recommendation*: Populate `"weight": 0.5` explicitly on all edges or ensure downstream tools rely on `validateGraph()` auto-fix.

---

### 2. Node Summary Markdown Rendering (`NodeInfo.tsx`)

- **Analysis**:
  - `NodeInfo.tsx` renders `node.summary` as plain text inside `<p className="text-sm text-text-secondary mb-4 leading-relaxed">{node.summary}</p>`.
  - All 154 nodes in `knowledge-graph.json` have valid, non-empty Vietnamese summaries.
  - Summaries contain clean punctuation, valid technical terms, and no unclosed formatting delimiters (such as unclosed backticks, dangling asterisks, or unescaped HTML tags).
- **Verdict**: ✅ **PASS**

---

### 3. Layer Architecture Compatibility (`LayerLegend.tsx`)

- **Analysis**:
  - `LayerLegend.tsx` expects `layers: LayerSchema[]` where each layer has `{ id, name, description, nodeIds }`.
  - All 8 layers in `knowledge-graph.json` are fully specified with Vietnamese names and comprehensive architectural descriptions:
    1. `layer:presentation-ui` (7 nodes)
    2. `layer:orchestration-agents` (12 nodes)
    3. `layer:intelligence-routing` (10 nodes)
    4. `layer:knowledge-retrieval` (15 nodes)
    5. `layer:data-storage` (47 nodes)
    6. `layer:testing-quality` (70 nodes)
    7. `layer:specifications-tooling` (44 nodes)
    8. `layer:governance-documentation` (148 nodes)
  - All referenced `nodeIds` (353 total assignments) exist in `nodes`.
  - `LayerLegend.tsx` palette (`LAYER_PALETTE` with 7 colors) handles 8 layers gracefully using `i % LAYER_PALETTE.length`.
- **Verdict**: ✅ **PASS**

---

### 4. Guided Tour Compatibility (`LearnPanel.tsx`)

- **Analysis**:
  - `LearnPanel.tsx` expects `tour: TourStepSchema[]` where each step has `{ order, title, description, nodeIds }`.
  - All 9 tour steps are ordered 1 to 9, providing a logical walkthrough from Governance/Architecture down to QA and Benchmarking:
    1. Tổng quan Hệ thống, Quản trị & Kiến trúc (5 nodes)
    2. Mô hình Dữ liệu Cốt lõi & Local Storage (7 nodes)
    3. Thu nạp Tài liệu & Trích xuất Đa Định dạng (5 nodes)
    4. Lập Chỉ mục Cục bộ, Tìm kiếm & Truy xuất Đồ thị (RAG v2) (4 nodes)
    5. Định tuyến Trí tuệ AI & Brain Gateway (5 nodes)
    6. Đối chiếu Trích dẫn & Claim Guard (5 nodes)
    7. Điều phối Agent & Cầu nối IDE (6 nodes)
    8. Giao diện Trình diễn UI & Bản đồ Tri thức Tương tác (5 nodes)
    9. Đặc tả Kỹ thuật, Benchmarking & Đảm bảo Chất lượng (5 nodes)
  - `step.description` is rendered using `<ReactMarkdown>`. Descriptions are clean Markdown paragraphs with no broken tags.
  - All referenced `nodeIds` exist in `nodes` and resolve correctly to interactive component pills.
- **Verdict**: ✅ **PASS**

---

### 5. Vietnamese Search Indexing (`store.ts` / `SearchEngine`)

- **Analysis**:
  - `store.ts` initializes `SearchEngine(graph.nodes)`.
  - `SearchEngine` uses Fuse.js indexing `name` (0.4), `tags` (0.3), `summary` (0.2), `languageNotes` (0.1).
  - All Vietnamese diacritics in `summary` (e.g. "Bản ghi Bằng chứng", "định tuyến", "bảo vệ quyền riêng tư", "chỉ mục từ vựng") are valid UTF-8 strings.
  - Tokenization via `split(/\s+/).join(" | ")` correctly parses multi-word queries in both English and Vietnamese without encoding exceptions or buffer truncations.
- **Verdict**: ✅ **PASS**

---

## Remediation Plan (Required Changes)

To achieve 100% strict compatibility with zero dropped edges and zero schema warnings, apply the following 6 edge type replacements in `knowledge-graph.json`:

1. **Line 1772**: Change `"type": "updates"` to `"type": "documents"` (or `"transforms"`)
2. **Line 1862**: Change `"type": "refers_to"` to `"type": "references"` (or `"documents"`)
3. **Line 1868**: Change `"type": "refers_to"` to `"type": "references"` (or `"documents"`)
4. **Line 1874**: Change `"type": "follows_schema"` to `"type": "defines_schema"` (or `"implements"`)
5. **Line 1940**: Change `"type": "tracks"` to `"type": "documents"` (or `"depends_on"`)
6. **Line 2078**: Change `"type": "tests"` to `"type": "tested_by"` (or flip source/target for canonical `production -> test` direction)

---

## Conclusion

The knowledge graph is structurally rich, high quality, and well localized in Vietnamese. Once the 6 non-canonical edge types are mapped to valid schema types, the file will achieve **100% strict compliance** with `@understand-anything/core` and render flawlessly across all dashboard views.
