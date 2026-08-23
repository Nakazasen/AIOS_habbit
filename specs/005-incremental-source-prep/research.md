# Research: Incremental Source Preparation

## Durable queue location

**Decision:** Store source-preparation state in the existing BGE SQLite runtime, not only Streamlit session state or JSONL.

**Rationale:** The vector index already owns source document ids and fingerprints. SQLite makes `ready` reusable after restart and can turn interrupted `processing` records back into `pending` atomically.

**Alternatives considered:** A Python-only in-memory registry loses work on restart. A separate JSONL queue risks concurrent write conflicts and duplicates fingerprint/index truth.

## Background scheduling

**Decision:** Use one CPU worker, a persistent priority queue, and one source per committed unit of work.

**Rationale:** BGE-M3 is CPU-bound on this machine. One worker avoids resource contention, gives meaningful progress, and lets a question-related source jump ahead without cancelling the rest.

**Alternatives considered:** Embedding all 75 simultaneously causes severe latency and memory pressure. Preparing only question candidates leaves most uploads permanently unprepared.

## Query behavior

**Decision:** Uploads and notebook opening enqueue all unready sources; an interactive request only promotes its exact bounded source set and automatically resumes once.

**Rationale:** This completes the library in the background without allowing vague questions to create a second expensive library job.

## Provenance and evidence UI

**Decision:** Separate bridge, generation provider, and verified model identity; group evidence by source id.

**Rationale:** Antigravity is a local bridge while the current generator is Gemini Web. The bridge only echoes a requested alias and has no verified upstream model id. Repeated filenames are chunks, not independent documents.
