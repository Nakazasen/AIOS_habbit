# Privacy Model

Status: `ACTIVE`
Owner role: Project owner / privacy decision maker
Last reviewed: 2026-07-25
Review cadence: Before a new data class, external recipient or cloud route

AIOS WorkLens is local-first. Public repository content is limited to code, docs,
schemas, templates and synthetic samples. Private runtime data remains local and
Git-ignored, including Workspace Chat state, evidence/memory JSONL, candidate
output, generated export packs and final local audit/handover reports.

Discovery is metadata-first. Extraction creates candidates, not verified truth.
Verified memory requires evidence; export packs require audit before use.

The canonical engineering privacy controls are:

- [Data policy](../00_governance/DATA_POLICY.md)
- [Privacy impact assessment](security/PRIVACY_IMPACT_ASSESSMENT.md)
- [Threat model](security/THREAT_MODEL.md)
- [Incident response](operations/INCIDENT_RESPONSE.md)

No automatic retention/deletion schedule, legal compliance claim or provider
subprocessor approval is implied until owner decisions are recorded.
