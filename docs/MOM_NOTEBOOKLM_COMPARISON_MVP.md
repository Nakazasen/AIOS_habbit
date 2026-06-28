# AIOS vs NotebookLM MVP Benchmark

This benchmark compares AIOS local RAG with NotebookLM on a user-approved local MOM/WMS source folder. It evaluates quality only. It does not prove NotebookLM parity.

## Real data path

User-local source folder example: `D:/Sandbox/MOM_WMS_QLLSSX/tailieugoc`.

Generated outputs must stay under ignored `local_runs/notebooklm_compare/`.

## AIOS flow

1. Load the local benchmark config.
2. Discover supported text-like documents recursively.
3. Build local `RAGChunk` objects with `local_only` privacy.
4. Search locally with SQLite FTS/BM25.
5. Optionally apply the deterministic local reranker.
6. Build evidence packs.
7. Compose deterministic local cited drafts with the local answer composer.

## NotebookLM flow

Use `nlm` only after CLI capability discovery. If the local CLI cannot automate source import/query safely, use the manual runbook in `docs/NOTEBOOKLM_MANUAL_COLLECTION_RUNBOOK.md`.

## Question generation

The generator samples document names and safe metadata from local documents. It creates Vietnamese/English/Japanese-style prompts across:

1. direct lookup
2. procedure/step extraction
3. cause/effect investigation
4. evidence sufficiency
5. cross-document relation
6. unanswerable/insufficient evidence

## Answer collection

AIOS answers are written to ignored JSONL. NotebookLM answers, if collected, are also written to ignored JSONL and must not be committed because they may contain company content.

## Scoring

The deterministic evaluator scores 0-3 for relevance, citation usefulness, source grounding, completeness, insufficient-evidence honesty, privacy/local control, owner actionability, and hallucination risk.

## Claim policy

Allowed: "AIOS vs NotebookLM MVP benchmark", "self-evaluation candidate result", "NotebookLM comparison run", "local RAG quality report".

Forbidden unless later proven by human-reviewed evidence: "NotebookLM parity", "AIOS is better than NotebookLM", or "NotebookLM replacement".

PASS_CANDIDATE only means the self-eval passed. Human review is still required before any parity claim.
