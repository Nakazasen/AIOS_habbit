# Handover: Matecon Manual Retrieval Repair

## Incident

Workspace Chat answered the Matecon manual-mode question as though the guide
contained only a table-of-contents entry. The staged corpus and SQLite index
were inspected: the source contains the complete chapter 11 and its chunks are
present in the index.

## Root causes fixed

- When semantic RAG was unavailable, the UI sent all enabled sources to the
  cloud-answer path. Provider source capping then favored the leading portion
  of the guide and produced the false conclusion.
- The UI could label a request as Deep while silently falling back to ordinary
  Hybrid when no reranker was configured.
- The BGE hybrid result path emitted `multi_variant_rrf`, while the reranker
  sort expected only `fused_rrf`. Successful cross-encoder scores therefore
  failed with `KeyError` and were discarded.
- The previous 30-second IPC deadline could not accommodate CPU reranking.

## Delivered safeguards and verification

- Unavailable RAG stops before any provider call; it cannot pass the complete
  source set as a fallback.
- Explicit Deep fails closed unless the adaptive configuration and pinned
  reranker are available.
- Reranking accepts both valid RRF signal names, uses a bounded ten-candidate
  window, and has a separate five-minute Deep deadline. Auto remains bounded
  by its normal 30-second deadline.
- A one-document manual may use the normal retrieval window rather than the
  multi-document cap of three chunks.
- The locally verified reranker revision and checksum replace the old
  placeholder pins.
- The compatibility environment uses Python 3.11 with `FlagEmbedding 1.3.5`,
  `transformers 4.44.2`, `sentence-transformers 3.1.1`, and `torch 2.5.1`;
  `import FlagEmbedding` succeeds there.
- The one-manual local BGE-M3 diagnostic was run again after the query-shape
  and evidence-window fix. `Auto` returned ten evidence items with no
  degradation; they include chapter 11, `ctrlMode=1`, ACR/CTU startup, and
  manual-drive preparation. `Deep` returned ten items with
  `reranker_requested=true`, `reranker_applied=true`, and no degradation.
- The Windows `py -3` interpreter is Python 3.13 and does not have
  `FlagEmbedding`; invoke diagnostics and the app from `.venv\\Scripts\\python.exe`
  (the pinned Python 3.11 environment), not from the system interpreter.
- The Gate H progress record now fails honestly: a partial multi-arm run is
  `INCOMPLETE`, never `COMPLETED`. The previous batch-4 candidate contains
  only the 12-question lexical arm (12/24 total), so it is not activation
  evidence.

## Remaining production gate

The active deployment manifest references an absent sealed selected-profile
report, identity, and runtime; its loader fails closed. Candidate activation
must remain blocked. Start the app from the verified project `.venv`, recreate
the sealed selected-profile evidence through a resumable Gate H run, run the
real adaptive benchmark, and activate only after its authentic PASS result. See
`docs/runbooks/MATECON_MANUAL_RETRIEVAL_OPERATIONS.md` for operator checks.
