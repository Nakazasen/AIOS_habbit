# AIOS General RAG Overfit Audit

## Verdict

Overfit risk confirmed: YES.

AIOS had a useful local RAG foundation, but the recent router/synthesizer layer
was drifting toward a MOM/WMS manufacturing benchmark answer machine. The risk
was not only code style; it could create misleading NotebookLM replacement
confidence from a narrow benchmark.

## Generic RAG Code Paths

- Document extraction: `document_extractors.py`.
- Chunking and metadata: `rag_ingest.py`.
- Local retrieval: `rag_search.py` SQLite FTS/fallback search.
- Reranking: `rag_rerank.py`.
- Evidence pack and citation metadata: `rag_evidence.py`.
- Citation-first local draft: `rag_answer_composer.py` and
  `citation_answer.py`.
- Privacy/local-only route: evidence pack privacy fields and answer composers.

These are domain-neutral in concept, though retrieval previously loaded
manufacturing-specific intent boosts from `query_intent.py`.

## Domain-Specific Code Paths

- `query_intent.py` contained MOM/WMS/AGV/Oricon source boosts.
- `source_router.py` used domain-shaped profiles such as `excel_mapping`,
  `process_boundary`, `design_change`, and `owner_handover`.
- `final_answer_composer.py` injected owner workflow and manufacturing-style
  action text into default answers.
- 12Q reports and side-by-side reviews were centered on MOM/WMS evidence.

## Hard-Coded Owner Workflow Templates

The previous deterministic composer pushed answers toward:

- owner action language,
- handover framing,
- operational log checks,
- manufacturing-style mapping/troubleshooting,
- score-friendly section templates.

Those may be useful in a domain playbook, but they are not generic RAG.

## Query Profiles

Generic after reset:

- `factual_lookup`
- `compare_contrast`
- `summarize_document`
- `extract_fields`
- `table_question`
- `image_visible_facts`
- `image_limitations`
- `schema_question`
- `procedure_steps`
- `troubleshooting_general`
- `missing_evidence_general`
- `handover_general`
- `translation_or_rewrite`
- `decision_support`
- `open_ended_research`

Legacy MOM-shaped profiles now map into generic profiles instead of defining the
core vocabulary.

## Evaluator False Confidence Risks

- PARTIAL source routing could still look high quality if the answer had a
  polished template.
- `HUMAN_REVIEW` side-by-side status could be read as a win/pass signal.
- Deterministic AIOS answers were compared against NotebookLM model synthesis
  without a fair model-assisted AIOS bridge.
- MOM-only results could be mistaken for general NotebookLM replacement
  evidence.

## Invalid General Claims From Current Benchmark

The MOM/WMS 12Q benchmark is invalid for:

- general NotebookLM replacement,
- global NotebookLM parity,
- daily replacement across the owner's whole work,
- P1.0 readiness.

It can only support a partial manufacturing-assistant claim with caveats.

## Multi-Domain Breakage Risk

- HR policy: old templates could ask for operational logs or owner workflow
  actions instead of policy clauses.
- Accounting documents: field extraction could be confused with manufacturing
  mapping language.
- Japanese learning material: troubleshooting/handover sections would be
  irrelevant.
- Legal/contract documents: decision support could be overconfident without
  legal-specific caveats.
- IT troubleshooting logs: generic log investigation is useful, but
  manufacturing handoff terms would be wrong.
- General PDF manuals: procedure steps should stay document-centric, not
  factory-process-centric.

## Claim Discipline

- Can AIOS claim general NotebookLM replacement: NO.
- Can AIOS claim MOM-specific assistant: PARTIAL only, with caveats.
- Can AIOS claim global NotebookLM parity: NO.
- P1.0 opened: NO.

## 2026-08-09 BGE-M3 RAG v2 Clean-Core Re-audit

The active package at `src/aios_habit/rag_v2/` is now separated from the old
benchmark-aware code:

- Removed built-in named-subject translations and target-equivalent aliases.
- Removed multilingual intent, facet, incident, and obligation cue dictionaries.
- Removed the final `named_procedure_*` synthesis branch.
- Kept only corpus-neutral signals: literal query segments, validated external
  query-only expansions, semantic/sparse retrieval, source-derived metadata,
  provenance, citation checks, and generic sanitation.
- Restored only a small English function-word list to prevent overlap on words
  such as `the` and `for` from counting as evidence. This is linguistic
  normalization, not benchmark knowledge.

The old `query_intent.py`, `domain_playbooks.py`, `mom_local_index.py`,
`rag_search.py`, and Workspace Chat modules still contain domain-specific
behavior. They are classified as **quarantined legacy**, not BGE-M3 RAG v2.
The hardcode regression guard now scans every Python file in `rag_v2`, detects
known benchmark literals and suspicious module-level semantic vocabularies, and
fails if active modules import a quarantined legacy prefix.

Verification after cleanup:

- compile check: PASS;
- structural hardcode/import-boundary guard: PASS;
- clean planner and targeted retrieval/synthesis regressions: 12 PASS;
- broader legacy-shaped core test run: 54 PASS / 35 FAIL because those tests
  still require removed intent dictionaries, named aliases, and fixed answer
  shapes. These failures are recorded as stale-contract debt, not hidden.

All BQ01 answer-quality results produced before this cleanup are invalid for the
clean-core competition. BQ01 must be rerun before unlocking BQ02-BQ12, and no
handcrafted vocabulary may be restored to recover the old score.
