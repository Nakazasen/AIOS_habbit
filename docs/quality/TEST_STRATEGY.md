# Test Strategy

Status: `ACTIVE`
Owner role: Maintainer / quality reviewer
Last reviewed: 2026-07-25
Review cadence: Each new runtime boundary, provider route or release candidate

## Objectives

Prove the local-first, evidence-grounded contract without requiring private data
or live provider credentials in normal development/CI.

## Test layers

| Layer | Purpose | Network/data rule |
|---|---|---|
| Unit | Pure parsing, schemas, privacy decisions, ranking and error mapping | Synthetic data; network prohibited |
| Integration | Store, converter, index, gateway and adapter contracts | Temp paths/synthetic fixtures; network prohibited |
| System/import | Workspace Chat and CLI boot boundaries | No credentials; network prohibited |
| Manual live smoke | Verify explicitly approved provider wiring | Generic prompt only; temporary in-memory key; no source context/logged key |
| Private local evaluation | Assess owner datasets/RAG quality | Local-only, ignored output, never CI artifact |

## Fixture policy

- Fixtures are synthetic, minimal and safe for Git.
- Do not commit raw owner documents, screenshots, local logs, tokens or real
  provider responses.
- Secret-pattern tests construct fake values at runtime where source scanning
  would otherwise mistake a complete fake literal for a tracked secret.

## AI and RAG behavior

- Treat provider text as nondeterministic; assert contract/status/citation and
  failure behavior rather than exact prose unless a deterministic fake is used.
- Retrieval evaluation measures hit@k, citation correctness, faithfulness and
  insufficient-evidence behavior as defined by RAG v2 design.
- Bilingual rank quality and PNG/OCR support remain known limitations, not hidden
  success criteria.

## Exit criteria

Every behavior change supplies focused regression evidence, passes all quality
gates, preserves privacy boundary tests and documents manual live evidence only
when a live route changed. Flaky tests are owned by the maintainer who introduces
or observes them and must not be silently retried as proof of success.
