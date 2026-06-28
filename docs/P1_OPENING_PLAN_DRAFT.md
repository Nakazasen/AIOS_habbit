# P1 Opening Plan Draft

This is a draft plan only. It does not open P1.0.

## Current status

- P1.0: CLOSED
- NotebookLM parity: NOT_CLAIMED
- Real owner acceptance: BLOCKED_NEEDS_OWNER_ACCEPTANCE
- Push gate: PENDING_PUSH_GATE

## Required before P1.0 can open

1. Human owner completes `docs/P1_OWNER_ACCEPTANCE_RUNBOOK.md`.
2. Owner reports PASS with acceptable manual-step burden.
3. Full pytest passes.
4. CLI audit passes.
5. Secret/runtime/generated artifact scans pass.
6. Privacy rules are rechecked for `local_only` and `cloud_safe` paths.
7. RAG benchmark passes using agreed criteria.
8. Documentation avoids NotebookLM parity or replacement claims.

## Optional improvements before P1.0

- Use the deterministic local answer composer for local cited drafts.
- Use the deterministic local reranker only as an opt-in benchmark/search quality improvement.
- Add owner-facing screenshots only with fake data.

## Explicit non-goals for P1 opening

- No Vector DB unless benchmark evidence proves it is required.
- No Graph DB unless cross-case graph queries become P1-critical.
- No provider/cloud automation for company or sensitive content.
- No NotebookLM parity claim.

## Opening decision

P1.0 may be opened only after the owner acceptance run is complete and all validation gates pass.
