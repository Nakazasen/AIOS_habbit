# skill-Anti-brain-wiki_note Inheritance Audit

## Status
KEEP_AS_REFERENCE / WRAP_LATER / PORT_LATER after audit. No code copied.

## Read Materials
- `README.md`
- `pyproject.toml`
- top-level structure

## Folder Structure
- `.brain`, `raw`, `processed`, `wiki`, `workflows`, `skills`, `templates`, `schemas`, `scripts`, `src`, `tests`, `ui`, `notebooks`, `examples`

## Entrypoints
- `abw.bat`
- Python package from `pyproject.toml`
- install scripts

## Tests / Scripts
Tests and CI-like assets exist. Not executed in this phase.

## Features Observed
- Knowledge ingestion pipeline.
- Raw/processed/wiki separation.
- Workflow and skill registry.
- Audit/eval/continuation style discipline.
- Packaging and export-oriented docs.

## Reusable Modules / Concepts
- Grounded knowledge workflow can inform WorkLens case learning.
- No-fake-success and continuation gates align with evidence-first case handling.
- Wiki packaging can inform later case memory export.

## Dead / Unclear Modules
None declared dead. Large ABW surface is likely too broad for WorkLens v0.1.

## Risks
- Full ABW workflow surface could turn WorkLens into a framework instead of a daily case tool.
- Raw/processed directories may contain private data; never copy blindly.
- Many workflows require pruning before user-facing product integration.

## Harvest Candidates
| Candidate | Status | Loop Fit | Tests | Portability | Complexity |
|---|---|---|---|---|---|
| `.brain` durable learning pattern | NEEDS_AUDIT | Learning | Unknown | Medium | Medium |
| Raw/processed/wiki separation | NEEDS_AUDIT | Evidence/Learning | Unknown | High | Medium |
| Audit/eval gates | NEEDS_AUDIT | Governance | Unknown | High | Low-Medium |
| Query workflow | NEEDS_AUDIT | Evidence review | Unknown | Medium | High |

## Recommendation
Wrap concepts first. Port only small governance and learning patterns after Case Cockpit pilot.
