# Local Contract: `chunk-evaluation/v1`

This is a local-only UTF-8 contract. It MUST contain source identifiers and
provenance but MUST NOT export raw `local_only` text.

## Input

```json
{
  "schema_version": "chunk-evaluation/v1",
  "corpus_fingerprint": "sha256:<digest>",
  "question_set_fingerprint": "sha256:<digest>",
  "strategy": {
    "strategy_id": "baseline-structure-aware-v1",
    "boundary_policy": "existing",
    "context_policy": "existing",
    "summary_policy": "existing"
  },
  "runtime_root": "local_runs/chunk_evaluation/<run-id>"
}
```

## Result

```json
{
  "schema_version": "chunk-evaluation/v1",
  "run_id": "chunk-eval-<timestamp>-<suffix>",
  "decision": "baseline|improved|neutral|rejected|blocked",
  "metrics": {
    "expected_evidence_recall_at_k": 0.0,
    "citation_support_rate": 0.0,
    "warm_query_p95_ms": 0.0,
    "preparation_duration_ms": 0.0,
    "index_size_bytes": 0,
    "retrievable_chunk_count": 0
  },
  "case_outcomes": [
    {
      "case_id": "case-id",
      "expected_evidence_found": true,
      "detailed_evidence_present": true,
      "retrieved_source_ids": ["opaque-source-id"],
      "fallback_boundary_used": false
    }
  ],
  "privacy": {
    "raw_local_only_text_exported": false
  }
}
```

## Decision Rule

A non-baseline candidate may be labelled `improved` only when it meets the
quality/resource gates in the feature specification. Missing corpus identity,
question identity, model identity, or case outcomes produces `blocked`, never
`improved`.
