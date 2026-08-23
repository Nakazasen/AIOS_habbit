# Research: Evidence-Based Chunking Evaluation

## Decision 1: Measure before adding overlap

**Decision**: Treat current zero-overlap chunking as the baseline and compare
bounded alternatives only on identical local corpus/question inputs.

**Rationale**: The current system already has table-aware chunks, local parents,
and an optional neighbor/parent expansion path. Fixed character overlap might
recover boundary context, but can also inflate vectors, duplicate evidence, and
slow CPU retrieval. No source inspection proves its net value.

**Alternatives considered**:

- Add a fixed 100-character overlap immediately — rejected because it assumes a
  benefit and makes no language distinction.
- Keep zero overlap forever — rejected because CJK sentence boundaries and
  cross-boundary questions have confirmed risk.

## Decision 2: Treat CJK boundaries as a first measured candidate

**Decision**: Test recognised Vietnamese, Japanese, and Chinese sentence
punctuation before character-limit fallback, while retaining a bounded fallback
when no such boundary exists.

**Rationale**: Existing splitting prioritises English full stop, newline, and
space. The current index snapshot contains chunks with `。` and `、`, so this is
not theoretical for the corpus.

**Alternatives considered**:

- Use only whitespace boundaries — rejected because Japanese/Chinese may not
  contain whitespace between words.
- Tokenise every language with a new external service — rejected for this phase
  because it would add scope and external dependency before the basic boundary
  comparison is measured.

## Decision 3: Separate navigation summaries from answer evidence

**Decision**: Measure document-summary outcomes independently and require a
detailed source chunk for precise/procedure answers when one exists.

**Rationale**: Summary chunks can help locate a document, but cannot replace an
original step, value, row, or safety constraint as evidence.

**Alternatives considered**:

- Remove summaries now — rejected because they may improve broad document
  discovery.
- Treat summaries as ordinary proof — rejected because it can make generic
  architecture text crowd out detailed evidence.

## Decision 4: Do not repair legacy chunkers without a runtime path finding

**Decision**: Capture a supported Workspace Chat ingestion/query trace before
changing `document_extractors` or `rag_ingest` behavior.

**Rationale**: Their fixed-width/truncating behavior exists in code, but the
RAG v2 path uses `StructureAwareChunker`. A code reference is insufficient to
justify a user-facing change.

**Alternatives considered**:

- Repair every old chunker in parallel — rejected as out of scope and high
  regression risk.

## Decision 5: Use a dedicated local runtime for comparison

**Decision**: Each evaluation strategy gets a fresh local index/runtime and
never writes to the active Workspace Chat index.

**Rationale**: Index identity and vector coverage must stay attributable to one
strategy, and a rejected candidate must not change what users see.

**Alternatives considered**:

- Reuse the active index — rejected because results become irreproducible and
  rollback is unsafe.
