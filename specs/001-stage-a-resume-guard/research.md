# Research: Resumable Stage A Preparation

## Decision: Checkpoint in the benchmark staging cache, not in the UI registry

**Rationale**: The in-memory adapter registry is temporary and the benchmark runner owns the content-addressed stage identity and stage manifest. A checkpoint beside that manifest survives a stopped process without changing UI-session semantics.

**Alternatives considered**:

- Persist every UI preparation entry globally: rejected because it risks cross-workspace state and lacks the frozen benchmark identity.
- Rebuild the whole corpus after failure: rejected because it repeats work and hides the slow source.

## Decision: Record opaque committed document IDs only

**Rationale**: The adapter produces stable opaque `wsc-` document IDs. Combined with the stage identity they identify completion without retaining titles, paths, or source text.

**Alternatives considered**:

- Store names and paths for diagnosis: rejected by local-only privacy constraints.
- Store source content hashes alone: rejected because the adapter needs a direct safe skip key.

## Decision: Deadline applies to each worker RPC within a source, while the CLI supplies one per-source budget

**Rationale**: The worker protocol already accepts RPC timeouts. Passing the remaining source budget for each stage/embed/commit operation bounds the whole source rather than merely an individual group.

**Alternatives considered**:

- Global full-corpus timeout: rejected because it cannot isolate a bad source or preserve a useful restart point.
- Unbounded timeout: rejected because it recreates the prior stuck run.

## Decision: Resume only an exact frozen identity

**Rationale**: The existing stage key binds corpus fingerprint, activated production identity and source fingerprints. Reuse of a different identity could mix evidence from different candidates or corpora.

**Alternatives considered**:

- Best-effort merge by matching some sources: rejected because the gate requires a frozen experiment identity.

## Decision: Allow an explicit unsealed local diagnostic

**Rationale**: The operator has authorized removal of the historical-artifact blocker. The override remains limited to BQ01/BQ02, local-only inputs, and provider-free execution, so it diagnoses the deployed retrieval path without claiming historical comparability.

**Alternatives considered**:

- Recreate historical evidence: rejected because it would misrepresent a new artifact as old evidence.
- Permit arbitrary questions or live synthesis: rejected because it would exceed the authorized diagnostic scope.
