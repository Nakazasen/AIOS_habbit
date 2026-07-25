# Performance and Capacity Baseline

Status: `PLANNED`
Owner role: Project owner / performance reviewer
Last reviewed: 2026-07-25
Review cadence: Before external release or when ingest/retrieval architecture changes

## Current truth

No production latency, throughput, document-size, index-size, concurrent-user,
RTO or capacity target has been measured or approved. The application is local
and owner-operated; it must not claim an SLA.

## Benchmark protocol

Use only synthetic/public fixtures in tracked tests. Private local benchmarks may
run in ignored `local_runs/` and must record only sanitized aggregate metrics.
For each run capture:

- Python/package/version/commit;
- fixture profile and count (not private filenames/text);
- ingest/conversion elapsed time and failure count;
- chunk/index count and database size where safe;
- retrieval latency and hit/citation metric where applicable;
- machine class at coarse level, without user path/identifier;
- known limitations and comparison to prior baseline.

## Release use

A performance result becomes a release claim only after owner-approved target,
repeatable methodology and regression threshold are defined. Until then, results
are diagnostic evidence, not a support commitment.

## Known constraints

Current RAG v2 retrieval is deterministic lexical, bilingual ranking is a known
limitation, and PNG OCR is unsupported. See [RAG v2 design](../rag_v2/RAG_V2_DESIGN.md).
