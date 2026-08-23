# E2E Test Infra: Antigravity Truthful Bridge

## Test Philosophy
- Opaque-box, requirement-driven testing covering all aspects of ORIGINAL_REQUEST.md.
- Strict fail-closed verification: verifying that under failure conditions, zero calls to cloud LLMs or Smart Router occur.
- Non-facade verification: verifying AST and runtime to ensure `RealWorkspaceAIProviderClient` is never invoked by the bridge or sidecar.

## Feature Inventory & Test Mapping
| # | Feature | Source | Tier 1 (Feature) | Tier 2 (Boundary) | Tier 3 (Cross) | Tier 4 (Scenario) |
|---|---|---|:---:|:---:|:---:|:---:|
| 1 | Health FSM States | R1 | 6 | 4 | 2 | 2 |
| 2 | Sidecar Loopback Purge | R1 | 2 | 2 | 2 | 1 |
| 3 | Citation Integrity | R1, R2 | 2 | 3 | 2 | 2 |
| 4 | Outbox/Inbox Lifecycle | R2 | 4 | 4 | 3 | 3 |
| 5 | Schema Validation | R2 | 3 | 4 | 2 | 2 |
| 6 | Workspace Chat Routing | R3 | 3 | 3 | 3 | 3 |
| 7 | Strict Fail-Closed Policy | R3 | 3 | 3 | 2 | 2 |
| 8 | Honest UI Attribution | R3 | 3 | 2 | 2 | 2 |
| 9 | Privacy & Sanitization | R4 | 3 | 3 | 2 | 2 |
| 10 | Governance & Spec Kit | R5 | 2 | 1 | 1 | 1 |

## Test Architecture
- Test Runner: `.venv\Scripts\python.exe -m pytest`
- Test Files:
  - `tests/test_antigravity_bridge.py`: Health FSM, direct mode adapter, sidecar loopback check, privacy sanitization.
  - `tests/test_antigravity_handoff_ui_flow.py`: Handoff bundle creation, schema v1 validation, timeout handling, UI state transitions, fail-closed assertions.
  - `tests/test_ai_provider_bridge.py` & `tests/test_ide_handoff_bridge.py`: Outbox/Inbox IO, citations, and provider routing.

## Test Tier Definitions
- **Tier 1 (Feature Coverage)**: Basic happy-path tests for each FSM state, handoff bundle creation, schema check, UI attribution, log redaction.
- **Tier 2 (Boundary & Corner Cases)**: Malformed JSON, corrupted bundle, invalid citations, zero allowed sources, timeout expiration, invalid schema versions.
- **Tier 3 (Cross-Feature Combinations)**: Direct unavailable transitioning to Outbox handoff; pending handoff transition to completed on response import; fail-closed under sidecar crash.
- **Tier 4 (Real-World Application Scenarios)**: End-to-end user chat query in Workspace Chat with `local_only` notebook documents routed through Antigravity handoff, completed response rendered with "Nguồn AI: Antigravity IDE", and 0 leakage of private data.
- **Tier 5 (Adversarial Coverage Hardening)**: White-box challenger stress tests to probe all unexercised branch conditions.

## Coverage Thresholds
- Tier 1: ≥30 tests
- Tier 2: ≥25 tests
- Tier 3: ≥15 tests
- Tier 4: ≥5 scenarios
- Total: ≥75 assertions across test suites
- Target: 100% pytest pass rate
