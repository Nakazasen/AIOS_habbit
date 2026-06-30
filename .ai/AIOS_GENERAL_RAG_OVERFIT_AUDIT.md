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
