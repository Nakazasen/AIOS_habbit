# Data Model: Chunking Evaluation

## EvaluationCase

One locally stored question and its expected evidence.

| Field | Meaning | Validation |
|---|---|---|
| `case_id` | Stable case identifier | Unique and non-empty |
| `question` | User question retained locally | Non-empty UTF-8 |
| `language` | `vi`, `ja`, or `zh-CN` | Required |
| `source_ids` | Expected supporting source identities | At least one |
| `expected_chunk_hints` | Optional page/section/row expectations | Local provenance only |
| `challenge_labels` | Boundary, table, summary, short-text, or cross-source labels | Controlled values |

## ChunkingStrategy

A named, immutable evaluated behavior.

| Field | Meaning | Validation |
|---|---|---|
| `strategy_id` | Stable strategy/version identity | Unique |
| `baseline_of` | Baseline identity when this is a candidate | Optional |
| `boundary_policy` | Human-readable boundary policy | Required |
| `context_policy` | Parent/neighbor/overlap policy | Required |
| `summary_policy` | Navigation versus evidence policy | Required |
| `provenance_policy` | Required metadata preservation | Required |

## EvaluationRun

One reproducible comparison execution.

| Field | Meaning | Validation |
|---|---|---|
| `run_id` | Stable run identity | Unique |
| `corpus_fingerprint` | Frozen corpus identity | Required |
| `question_set_fingerprint` | Frozen case-set identity | Required |
| `strategy_id` | Evaluated strategy | Required |
| `model_identity` | Local embedding/index identity | Required |
| `started_at` / `completed_at` | Timing provenance | UTC timestamps |
| `decision` | `baseline`, `improved`, `neutral`, `rejected`, or `blocked` | Required |

## CaseOutcome

The result for one EvaluationCase in one EvaluationRun.

| Field | Meaning | Validation |
|---|---|---|
| `case_id` | Linked evaluation case | Must exist |
| `retrieved_source_ids` | Ordered source identities returned | Required |
| `expected_evidence_found` | Whether expected evidence is returned | Boolean |
| `detailed_evidence_present` | Detailed source survived final evidence selection | Boolean |
| `summary_used` | Summary involvement and role | Controlled value |
| `latency_ms` | Warm-query time | Non-negative |
| `fallback_boundary_used` | Character fallback occurred during ingest | Boolean |

## StrategyMetrics

Aggregate comparison metrics retained for an EvaluationRun.

| Field | Meaning |
|---|---|
| `expected_evidence_recall_at_k` | Share of cases finding expected evidence |
| `citation_support_rate` | Share of cases with supporting detailed evidence |
| `warm_query_p95_ms` | 95th percentile warm-query latency |
| `preparation_duration_ms` | Ingestion/index preparation duration |
| `index_size_bytes` | Resulting dedicated index size |
| `retrievable_chunk_count` | Number of retrievable chunks |
| `length_distribution` | Counts in agreed length bands |
| `language_breakdown` | Metrics partitioned by vi/ja/zh-CN |
