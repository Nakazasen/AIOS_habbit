# AIOS Generic RAG Core Architecture

## Purpose

AIOS must be a general RAG core with optional domain playbooks, not a hidden
MOM/WMS benchmark answer machine.

## Layer A: Generic RAG Core

Domain-neutral responsibilities:

- document ingestion
- chunking
- metadata extraction
- source type normalization
- retrieval
- reranking when available
- evidence pack creation
- citations
- answer mode selection
- missing evidence detection
- privacy gate
- `local_only` safety
- export to AI model bridge
- evaluation

Generic query intents:

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

## Layer B: Domain Playbooks

Playbooks are optional and explicitly named. Default is `general`.

Initial playbooks:

- `manufacturing_mom_wms`
- `accounting`
- `hr_policy`
- `japanese_learning`
- `it_ops`
- `legal_contract`
- `general_office`

Playbooks may provide:

- vocabulary
- example checklists
- preferred output format
- common evidence types
- risk reminders

Playbooks must not:

- override generic retrieval truth
- force unrelated source types
- inject manufacturing text into unrelated domains
- improve scores by keyword matching only
- claim generality

## Layer C: Model-Assisted Answer Bridge

NotebookLM uses model synthesis. A fair comparison requires AIOS to separate
deterministic evidence handling from model-assisted answer synthesis.

Required bridge concepts:

- `evidence_pack_to_model_prompt`
- model answer import
- citation validation
- hallucination check
- privacy gate
- owner review

The deterministic composer is useful for bounded local answers, but it is not a
NotebookLM-equivalent model synthesis engine.

## Claim Guard Boundary

The claim guard blocks:

- general replacement claims from MOM/WMS-only tests
- NotebookLM parity when deterministic synthesis is compared against NotebookLM
  model synthesis
- P1.0 opened claims without explicit owner approval
- replacement claims when human review says AIOS is weaker

## Exit Criteria For Generic Reset

- Generic profiles are the core router vocabulary.
- Manufacturing assistance is isolated in `manufacturing_mom_wms`.
- General-mode answers contain no hidden manufacturing workflow text.
- Evaluator caps prevent PARTIAL/FAIL/wrong-domain answers from appearing as
  confident wins.
- Multi-domain smoke tests pass.
