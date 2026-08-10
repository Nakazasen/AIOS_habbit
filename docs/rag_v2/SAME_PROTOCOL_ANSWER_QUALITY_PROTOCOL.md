# Same-Protocol Answer Quality Evaluation Protocol

Status: `ACTIVE`  
Owner role: `Project owner`  
Last reviewed: `2026-07-29`  
Review cadence: `Per evaluation gate`  

## Purpose & Scope

This document specifies the exact execution protocol for evaluating the activated `bge_m3_hybrid` production candidate against the frozen NotebookLM benchmark baseline. It ensures reproducibility, privacy compliance, and strict evaluation discipline without ad-hoc tuning or unauthorized data egress.

## Frozen Evaluation Baseline

- **Question Set**: Canonical `BQ01`–`BQ12` manifest. The SHA-256 fingerprint of the question set must match the immutable reference.
- **Corpus Target**: Canonical `tailieugoc/` 70-file document collection audited at 70/70 coverage.
- **Historical Benchmarks**:
  - NotebookLM reference score: `3.807/5` (initial) / `4.27/5` (fail-closed rerun).
  - RAG v2 prior score: `2.898/5` (initial) / `3.15/5` (fail-closed rerun).
- **Candidate Profile**: Activated `bge_m3_hybrid` with approved local model revision and checksum.

## Staging Model: Stage A vs Stage B

To prevent accidental cloud egress and maintain strict privacy boundaries, evaluations follow a two-stage protocol:

### Stage A: Provider-Free / Local-Only Evaluation

- Runs completely offline without loading API credentials or opening network sockets.
- Exercises document ingestion, structure-aware chunking, hybrid retrieval, workspace staging, and local synthesis fallback checks.
- Validates production identity binding (`rag_v2_subprocess`, `bge_m3_hybrid`, `fail_closed=True`, `lexical_fallback_enabled=True`).
- If the corpus is classified `local_only` and no approved live route exists, Stage A completes with verdict `BLOCKED_PRIVACY_ROUTE`.

### Stage B: Live Provider Synthesis Evaluation

- Requires an explicitly approved `cloud_safe` or `public` corpus classification and owner authorization.
- Passes retrieved evidence through the `BrainGateway` provider router using configured credentials.
- Retries transient transport failures up to pre-declared limits without changing candidate configuration.
- Requires independent blind human scoring across 3 randomized system arms before claiming parity.

## Production Identity & Binding Verification

Before any query is evaluated, the benchmark harness enforces strict candidate identity matching:

1. **Deployment Manifest**: Must be an activated `workspace_chat_rag_v2.local.json` manifest specifying `requested_profile: bge_m3_hybrid`.
2. **Model Integrity**: Pinned BGE-M3 model path, revision, and tree checksum must match declared production constants.
3. **Workspace Stage**: Battles bound to production must reuse or create a content-addressed `workspace_stage_manifest.json` sealing source fingerprints and preparation state.
4. **Fallback Telemetry**: Every evaluated answer row must prove `rag_v2_subprocess` execution without fallback degradation.

## Evaluation Discipline

1. **Freeze Requirements**: Question set, corpus manifest, candidate identity, and reference data must be frozen before generation.
2. **No Tuning After Unblinding**: No retrieval parameters, prompt wording, chunk sizes, or scoring logic may be modified after viewing unblinded results for an active gate.
3. **Fail-Closed Privacy**: `local_only` sources must never be transmitted externally. Missing keys, network errors, or identity mismatches result in technical failures (`FAIL` / `BLOCKED`), not scorable quality rows.
4. **Single Primary Run**: One primary evaluation run is permitted per gate checkpoint. Predeclared transport retries do not alter run identity.

## Acceptance Criteria & Verdict Definitions

A gate run must satisfy all hard conditions:

- Zero privacy or gateway policy regressions.
- Exact activated production candidate identity.
- Complete 70/70 corpus audit and matching hash.
- Zero fabricated citations and accurate abstention on insufficient questions (`BQ11`, `BQ12`).
- Reproducible, non-hardcoded evaluation execution.

### Standard Closure Verdicts

- `QUALITY_GATE_PASSED`: Frozen rubric reaches or exceeds the pre-registered parity threshold.
- `QUALITY_IMPROVED_NOT_PARITY`: Score improved over prior baseline but remains below parity.
- `QUALITY_GATE_FAILED`: Unblinded score degraded or hard quality gates failed.
- `BLOCKED_PRIVACY_ROUTE`: Stage A verified candidate identity, but Stage B is blocked due to `local_only` classification or missing approved egress route.
- `INSUFFICIENT_EVIDENCE`: Run completed with incomplete rows or missing reviewer score files.

## Command Patterns

### Provider-Free Stage A Preflight

```powershell
py -3 scripts/battle_notebooklm_rag_v2.py --source-root tailieugoc --preflight --privacy-label local_only --rag-profile bge_m3_hybrid --production-deployment-manifest config/workspace_chat_rag_v2.local.json
```

### Workspace Index Staging

```powershell
py -3 scripts/battle_notebooklm_rag_v2.py --source-root tailieugoc --workspace-stage --privacy-label local_only --production-deployment-manifest config/workspace_chat_rag_v2.local.json
```

### Provider-Free Stage A Dry Run

```powershell
py -3 scripts/battle_notebooklm_rag_v2.py --source-root tailieugoc --dry-run --privacy-label local_only --rag-profile bge_m3_hybrid --production-deployment-manifest config/workspace_chat_rag_v2.local.json --workspace-staging-manifest <path-to-stage-manifest>
```
