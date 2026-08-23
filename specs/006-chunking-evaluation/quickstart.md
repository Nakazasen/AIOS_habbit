# Validation Quickstart: Chunking Evaluation

## Prerequisites

- The local BGE-M3 model and the selected source corpus are available.
- The active Workspace Chat index is not used as the evaluation runtime.
- The local question-evidence case set is frozen and has a recorded fingerprint.

## E1: Establish baseline

1. Run the planned local evaluation command against the current
   `StructureAwareChunker` behavior.
2. Confirm the report has corpus, question-set, strategy, and model identities.
3. Confirm every case has a result and that raw `local_only` text is absent from
   the report.
4. Save this result as the baseline; do not change default retrieval behavior.

Expected outcome: a `baseline` decision with quality, latency, index-size,
language, summary, and chunk-distribution measurements.

## E2/E3: Evaluate candidates

1. Run each candidate using the exact same corpus and question-set identities.
2. Compare its metrics with the baseline.
3. Review every Japanese/Chinese boundary case and every precise/procedure case
   that returned a summary.
4. Label the candidate `improved`, `neutral`, or `rejected` according to the
   feature gates.

Expected outcome: no candidate is promoted merely because it creates more
chunks or appears more sophisticated.

## E4: Promotion check

1. Build a fresh dedicated index with the accepted strategy.
2. Run affected unit/integration tests plus selected real-document checks.
3. Verify rollback restores the prior baseline index/strategy identity.
4. Update handover/roadmap records only after the evidence is retained.
