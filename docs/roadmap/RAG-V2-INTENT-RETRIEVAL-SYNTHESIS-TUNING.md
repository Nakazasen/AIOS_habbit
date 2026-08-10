# RAG v2 Intent-Aware Retrieval and Synthesis Tuning

Status: `DONE` — `ADVANCE_TO_CANARY_WITH_LIMITATIONS`

## Baseline & Context

- **Baseline Score**: Dev RAG v2 scored **3.15/5** vs NotebookLM **4.27/5** in live blind run `BATTLE-RAGv2-1785003571-e33e5670`.
- **Primary Failure Mode**: BQ04 (diagnosis) scored **1.0/5** (System A) due to returning raw BOP lexical dumps instead of structured troubleshooting procedures.
- **Root Cause**: BM25/FTS5 lexical search heavily favors long documents with high term frequency over structured procedural guides. Additive signal scoring without obligation matching allowed raw dumps to outrank action items.

## Invariant Gate Boundaries

1. **Local-First & Privacy**: Local SQLite retrieval only. Fail-closed privacy filters run prior to any scoring or variant fusion.
2. **Primary-UI Freeze**: Workspace Chat retrieval path remains unchanged until owner approval and live blind rerun criteria are met.
3. **No Domain/Benchmark Hardcoding**: No BQ IDs, specific document filenames, or corpus-specific keywords may be hardcoded into query planning or index ranking. Tuning and blind evaluation sets are strictly separated.
4. **Independent Audit Gate**: Code changes must be audited independently before any live rerun request.

## Goal Criteria

- Intent-aware query planning detects generic intent categories (`diagnosis`, `procedure`, `comparison`, `lookup`, `table`) and obligation markers (`problem`, `check`, `action`).
- `LocalChunkIndex` candidate scoring penalizes raw repetitive process dumps when procedural or diagnostic intent is active, and applies obligation-matching boosts.
- Evidence selection prioritizes obligation coverage (e.g. error + action pairing for diagnosis).
- Synthesis contract for `diagnosis` mandates structured output markers (`SYMPTOMS:`, `CHECKS:`, `ACTIONS:`).
- Validation and fallbacks preserve structured answer shape without falling back to raw dumps.

## Gate H closure — 2026-07-28

- Gate H retrieval laboratory and the Workspace Chat production adapter are integrated in the
  primary workspace.
- `bge_m3_hybrid` was selected with Recall@10 `1.000`, MRR@10 `0.620`, and measured warm CPU
  retrieval p95 `1.792s`.
- H4 recorded `ADVANCE_TO_CANARY`; this is not a NotebookLM answer-parity claim.
- Focused affected tests: **87/87 passed**. Full regression: **1094/1094 passed**.
- Browser E2E passed for default behavior, lexical canary, rollback, model-unavailable recovery,
  and repeated Streamlit reruns after the SQLite cross-thread repair.
- Canonical evaluation retains asymmetric identities: 70 local business files and 48 READY
  NotebookLM sources; no source upload or false parity was introduced.
- Seventeen PNG and two empty-PDF gaps remain explicit and are transferred to a corpus-recovery
  gate.
- The normal-user experience remains a single ask-and-answer flow; technical canary/fallback modes
  are internal operational controls.

## Closure and transferred work

Gate H is closed in
[RAG-V2-GATE-H-HYBRID-CANARY.md](completed/RAG-V2-GATE-H-HYBRID-CANARY.md).
The transferred implementation gates are also closed:

1. [RAG-V2-HYBRID-PRODUCTION-ACTIVATION](completed/RAG-V2-HYBRID-PRODUCTION-ACTIVATION.md)
   activated the validated `bge_m3_hybrid` retriever on the approved 16 GB CPU target while
   preserving fail-closed rollback semantics.
2. [RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY](completed/RAG-V2-CORPUS-OCR-AND-SOURCE-RECOVERY.md)
   completed local-only OCR and source recovery with a strict `70/70` usable corpus audit.

Answer parity was not claimed by either implementation gate. The sole active follow-up is
[RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY](active/RAG-V2-SAME-PROTOCOL-BLINDED-ANSWER-QUALITY.md),
which freezes the activated production identity and immutable reference before independent scoring.
It cannot relabel the current `local_only` corpus or expose a normal-user technical mode selector.

## Measurement integrity follow-up — 2026-07-29

Any answer-quality result used to prioritize future retrieval tuning must prove
that the evaluated Workspace arm invoked the activated adapter and expose its
redacted effective backend/profile/fallback telemetry. The first `BQ01/BQ02`
diagnostic called legacy lexical retrieval despite being labeled production; it
is therefore retained only as legacy-arm evidence. A corrected adapter-backed
two-question remediation gate must finish before ranking, evidence, OCR, or
synthesis tuning is considered.
