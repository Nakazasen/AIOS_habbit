# Product Requirements Baseline

Status: `ACTIVE`
Owner role: Project owner / product reviewer
Last reviewed: 2026-07-25
Review cadence: Before a product-scope or supported-flow change

## Scope

This baseline records currently supported product behavior. It does not open
planned RAG, A18 or P1.0 work.

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| PR-01 | Owner can launch one supported Workspace Chat UI locally. | `IMPLEMENTED` | README, Workspace Chat import gate |
| PR-02 | Owner can create/select local notebook and source context. | `IMPLEMENTED` | Workspace Chat store/app tests |
| PR-03 | Owner can label local source privacy before optional AI routing. | `IMPLEMENTED` | UI/gateway behavior and privacy tests |
| PR-04 | Local-only/confidential content is not eligible for external provider routing. | `IMPLEMENTED` | `brain_gateway` tests |
| PR-05 | Answers expose source context/evidence or insufficiency rather than invented certainty. | `PARTIAL` | Current preview/RAG design; generic synthesis remains planned |
| PR-06 | Optional provider error is safe and Vietnamese-facing. | `IMPLEMENTED` | Workspace router adapter tests |
| PR-07 | User can operate without cloud service by default. | `IMPLEMENTED` | Constitution, install and architecture docs |
| PR-08 | Legacy Studio/Case Cockpit is not a supported normal-user route. | `IMPLEMENTED` | Roadmap and retirement evidence |

## Out of scope

Semantic/vector retrieval, PNG OCR, multi-user synchronization, automatic cloud
backup and guaranteed external-provider availability are not product
requirements today.

## Related records

- [NFR baseline](NON_FUNCTIONAL_REQUIREMENTS.md)
- [Traceability matrix](TRACEABILITY_MATRIX.md)
- [User guide](../user/WORKSPACE_CHAT_USER_GUIDE.md)
