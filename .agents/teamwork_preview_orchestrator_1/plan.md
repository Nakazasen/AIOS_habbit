# Master Plan: Vietnamese Translation & Verification of knowledge-graph.json

## Objective
Translate the entire knowledge graph file at `.understand-anything/knowledge-graph.json` from English to Vietnamese:
1. `layers` and `tour` arrays translated naturally with preserved IT terms.
2. All 727 node `summary` fields translated accurately with preserved IT terms.
3. Validate JSON integrity, parseability, structure, and dashboard compatibility.

## Execution Phases & Milestones

### Phase 0: Survey & Schema Analysis
- Explorer 1: Inspect `layers`, `tour`, global metadata, and overall schema in `.understand-anything/knowledge-graph.json`.
- Explorer 2: Inspect `nodes` array (node schema, summary distribution, total count, id formats, key categories).
- Explorer 3: Inspect dashboard loading mechanism, visualizer dependencies, and validation scripts to establish exact verification criteria.

### Phase 1: Planning & Tooling Setup (PROJECT.md)
- Synthesize explorer findings into `PROJECT.md`.
- Establish translation glossary & guidelines for standard IT terms (Agent, Local Storage, Orchestration, Framework, Dashboard, State, Dispatcher, Hook, etc.).
- Partition ~727 nodes into parallel worker chunks (e.g. 4 chunks of ~180 nodes each, plus 1 chunk for layers/tour).

### Phase 2: Translation Execution (Parallel Workers)
- Worker 1 (Layers & Tour): Translate `layers` and `tour` entries.
- Worker 2 (Nodes Chunk 1: Nodes 0-180): Translate `summary` of chunk 1.
- Worker 3 (Nodes Chunk 2: Nodes 181-360): Translate `summary` of chunk 2.
- Worker 4 (Nodes Chunk 3: Nodes 361-540): Translate `summary` of chunk 3.
- Worker 5 (Nodes Chunk 4: Nodes 541-727): Translate `summary` of chunk 4.

### Phase 3: Assembly, Merge & Format Verification
- Worker (Merge & Synthesize): Assemble all translated parts into `.understand-anything/knowledge-graph.json`.
- Worker (Validation Harness): Execute automated JSON syntax checks, node count preservation checks, non-empty summary checks, and test loading with Node.js/Python validator.

### Phase 4: Review, Challenger & Forensic Audit Gate
- Reviewer 1: Linguistic quality, natural Vietnamese phrasing, and consistency check across all sections.
- Reviewer 2: IT terminology compliance check (ensuring technical terms remain intact and not awkwardly translated).
- Challenger 1: Adversarial structural and diff verification (zero data loss, no lost node IDs, exact 727 node count).
- Auditor: Forensic integrity verification ensuring authentic translations without mock data or corrupted fields.

### Phase 5: Final Acceptance & Sentinel Reporting
- Consolidate gate results into `GATE_STATUS.md`.
- Final checkpoint in AgentMemory.
- Handoff report to parent.
