# Visual Knowledge Map MVP Decision

## Decision

Build the Visual Knowledge Map MVP after the bridge pilot, starting with a design-first schema and pipeline. Do not implement the UI or add a visualization library in this sprint.

## Why Now

AIOS already has the ingredients for an evidence-grounded work graph:

- local cases
- evidence items
- source metadata
- final owner answers
- Antigravity strong-answer save-back
- senior learning cards
- claim guard logic
- early semantic map prototypes

The bridge pilot makes stronger answers traceable back into AIOS. The next useful step is to make those case/evidence/answer/action/learning relationships visible and inspectable, while preserving privacy and claim discipline.

## What Not To Build Yet

- No new graph UI.
- No new visualization library.
- No graph database.
- No automatic all-files graph.
- No LLM-only graph generation as source of truth.
- No NotebookLM replacement claim.
- No P1.0 opening.
- No manufacturing-only graph logic.

## Next Implementation Sprint Proposal

Sprint name: `VISUAL_KNOWLEDGE_MAP_MVP_IMPLEMENTATION`

Scope:

1. Add graph node/edge schema models.
2. Add deterministic active-case graph builder.
3. Add typed edge validator.
4. Add privacy export modes.
5. Add local JSON and safe Mermaid export.
6. Add tests for HR, accounting, Japanese learning, IT manual, manufacturing, and general office samples.
7. Add Case Cockpit design stub only after schema/export tests pass.

Exit criteria:

- every edge has a typed relationship
- every important edge has a reason
- every claim has evidence or missing evidence
- local-only content is blocked from cloud-safe export
- source paths and personal identifiers are redacted in safe export modes
- no NotebookLM/P1.0 overclaim appears

## Expected Owner Value

- The owner can see what the case knows, what it does not know, and what should happen next.
- Evidence and answers become inspectable instead of buried in text.
- Decisions can show their support, risks, and limitations.
- Learning cards become reusable checklists and check-first-next-time prompts.
- The map becomes a work brain: not just notes, but evidence, action, and memory.

## Verdict

PASS_DESIGN_READY_IMPLEMENTATION_NEEDS_REVIEW
