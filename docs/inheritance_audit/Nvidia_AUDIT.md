# Nvidia Inheritance Audit

## Status
KEEP_AS_REFERENCE / PAUSE for heavy runtime. No code copied.

## Read Materials
- `README.md`
- `package.json`
- top-level structure

## Folder Structure
- `tools`, `tests`, `skills`, `flowkit`, `docs`, `proof`, `node_modules`, `.nvidia-agent`

## Entrypoints
- `npm start` / `tools/nvidia-server.mjs`
- CLI and agent scripts under `tools`
- Electron desktop via `electron-main.js`

## Tests / Scripts
`package.json` lists many tests: provider routing, bridge preflight, browser smoke, pending edits, file operations, reliability, port collisions.

## Features Observed
- Provider abstraction and tool calling.
- MCP server/tool patterns.
- Command jobs and pending edits.
- Browser smoke and UI proof harness.
- Electron desktop shell.

## Reusable Modules / Concepts
- Provider abstraction may inform future Agent Bridge.
- Browser smoke tests may help validate WorkLens UI later.
- Command job safety may inform future action execution.

## Dead / Unclear Modules
None declared dead. Electron/IDE/runtime shell is out of scope for v0.1 and likely PAUSED.

## Risks
- Contains `.env`, `node_modules`, logs, and runtime state; never copy data.
- High complexity and provider concerns could derail Case Cockpit.
- Product identity differs from WorkLens.

## Harvest Candidates
| Candidate | Status | Loop Fit | Tests | Portability | Complexity |
|---|---|---|---|---|---|
| Provider abstraction | NEEDS_AUDIT | Agent Bridge | Yes | Low-Medium | High |
| Browser smoke harness | NEEDS_AUDIT | Validation | Yes | Medium | Medium |
| Command job model | NEEDS_AUDIT | Action | Yes | Medium | High |
| Electron shell | PAUSE | Delivery only | Unknown | Low | High |

## Recommendation
Do not port runtime. Keep prompt packs as bridge v0.1. Revisit after pilot.
