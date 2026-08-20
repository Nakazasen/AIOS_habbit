# Project: Excaliflow Skill Upgrade (v2)

## Architecture
- **Skill Root**: `C:\Users\Admin\.gemini\config\skills\excaliflow`
  - `SKILL.md`: Skill definition, prompts, documentation, usage workflows.
  - `scripts\generate_diagram.py`: Python CLI tool analyzing target project and generating self-contained interactive HTML diagram with Mermaid hand-drawn look.
- **Package Target**: `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip`
- **Output HTML Architecture**:
  - `#sidebar`: 460px default width, collapsible via CSS `margin-left: -460px; opacity: 0; pointer-events: none;` with smooth `0.3s cubic-bezier(0.4, 0, 0.2, 1)`.
  - `#toggle-sidebar`: Clean toggle button in header/floating bar that expands/collapses the sidebar.
  - `#viewport`: `flex: 1` area that smoothly expands to full screen when sidebar is collapsed.
  - `#panzoom-container`: Container wrapping `#diagram-output`, managed by Panzoom v4.5.1 with unconstrained pan, zoom scale tracking, and reset/fit.
  - Floating Toolbar: `#zoom-in`, `#zoom-out`, `#zoom-reset`, `#zoom-fit`, `#zoom-badge`, `#export-svg`, `#export-png`.
  - Knowledge Graph Ingestion: Scans for `graphify-out/graph.json` (or `/understand` artifacts); if present, parses nodes, edges, communities, and call hierarchies to build high-fidelity Mermaid diagrams; fallbacks to AST/directory scanner if absent.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| F1 | Zoom & Pan (R1) | Panzoom integration with wheel zoom, drag pan, zoom toolbar buttons, badge, fit-to-screen | M1 | User Request R1 |
| F2 | Collapsible Sidebar (R2) | Smooth sidebar collapsing/expanding with layout recalculation and toggle button | M1 | User Request R2 |
| F3 | Knowledge Graph Ingestion (R4) | Auto-detect and parse `graphify-out/graph.json` / `/understand` graph data for enhanced Mermaid diagrams with AST fallback | M1 | User Request R4 |
| F4 | Playwright E2E UI Test | Automated headless browser verification of sidebar toggle, pan/zoom scale transformations, and controls | M2 | Acceptance Criteria |
| F5 | Zip Packaging (R3) | Zero-defect packaging of upgraded skill into `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip` | M2 | User Request R3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Core Implementation | Update `generate_diagram.py` (and `SKILL.md`) with R1 (Zoom/Pan), R2 (Collapsible Sidebar), and R4 (Graphify ingestion with AST fallback) | none | DONE |
| M2 | Verification & Packaging | Execute Playwright E2E headless tests on generated sample diagram and package into `excaliflow-skill-v2.zip` | M1 | DONE |

## Interface Contracts
### `generate_diagram.py` CLI & Outputs
- CLI: `python scripts/generate_diagram.py <target_path> [-o <output_file>]`
- Detection priority:
  1. `<target_path>/graphify-out/graph.json` -> Parse JSON graph (nodes, edges, communities) -> Generate high-fidelity architecture Mermaid diagram.
  2. Fallback -> AST parser (Python `ast`, JS regex/scan) & directory walker -> Standard architecture Mermaid diagram.
- HTML Output:
  - Generates standalone HTML containing Panzoom v4.5.1, Mermaid v11 (hand-drawn theme), collapsible sidebar with `#sidebar.collapsed` class, and zoom controls.

### Packaging Target
- Path: `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip`
- Contents: `SKILL.md`, `scripts/generate_diagram.py` (and any necessary assets).
