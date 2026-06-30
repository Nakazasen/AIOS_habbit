# Visual Map UI Interaction Decision

## Decision

Choose **Option A — Streamlit table-first UI** for the next Visual Map UI implementation sprint, with **Option B — safe Mermaid/HTML preview** as a secondary orientation aid.

This document is design-only. It does not implement UI, add a dependency, add a graph database, run a benchmark, compare against NotebookLM as a benchmark, claim NotebookLM replacement, claim global parity, or open P1.0.

## Why this path

1. **Safest for local-first privacy**: Streamlit tables/selectboxes/details can render existing local graph data without introducing new browser graph dependencies or cloud rendering.
2. **Fastest owner validation**: The owner needs to inspect evidence, missing evidence, risk, and next actions; a table-first UI can test this immediately.
3. **Anti-hairball by design**: Tables and grouped cards force current-case focus and prevent unreadable graph soup.
4. **Evidence-grounded**: Existing graph schema already has typed nodes, typed edges, evidence IDs, privacy metadata, confidence, and edge reasons. Table-first UI can expose those fields directly.
5. **No new dependency governance**: React Flow, Cytoscape.js, or D3-force would require dependency, JavaScript safety, and local export audits before use.

## What to implement next

For `VISUAL_MAP_UI_INTERACTION_IMPLEMENTATION_TABLE_FIRST`, implement only the smallest owner-facing interaction layer:

1. `Bản đồ tri thức công việc` section in Case Cockpit.
2. Top summary cards:
   - `Số nút`.
   - `Số quan hệ`.
   - `Bằng chứng còn thiếu`.
   - `Rủi ro / claim cần kiểm`.
   - `Việc tiếp theo`.
3. View selector:
   - Current Case Map.
   - Evidence Map.
   - Action Map.
   - Learning Map.
4. Visible filters:
   - node type.
   - edge type.
   - privacy.
   - confidence.
   - search.
5. Center panel:
   - table/card hybrid showing nodes and edges relevant to the selected view.
   - optional safe Mermaid preview behind an expander.
6. Right detail panel:
   - selected node detail.
   - selected edge detail.
   - evidence refs.
   - limitations.
   - next action.
7. Bottom panels:
   - missing evidence.
   - risk/claim.
   - learning card.
   - export.
8. Owner-facing Vietnamese labels and short explanations for graph terms.

## What not to implement yet

- No React Flow embedded component.
- No Cytoscape.js embedded local HTML.
- No D3-force custom canvas/SVG.
- No graph database.
- No editable graph truth surface.
- No cloud graph upload/rendering.
- No multi-case Work Stream Map as default.
- No manufacturing-only UI vocabulary.
- No NotebookLM replacement/global parity/P1.0 claim.

## When to consider React Flow

Consider React Flow after table-first UI passes owner trial and the owner specifically needs:

- drag/zoom/pan spatial interaction;
- minimap navigation;
- richer node cards;
- edge click detail in a visual canvas;
- stable local-only frontend component audit.

React Flow should remain read-only at first. Editing graph truth should require a separate governance design.

## When to consider Cytoscape.js

Consider Cytoscape.js if AIOS needs:

- clustering/compound nodes;
- graph analysis in the UI;
- larger case or topic maps;
- stable preset layouts;
- data-driven visual styling by type/privacy/confidence.

Before adoption, require dependency review, local bundled asset review, export/redaction audit, and performance smoke tests.

## When to consider D3-force

Consider D3-force only if custom visualization is required and other options cannot express the needed interaction. D3-force should not be the default because force layout can create random-looking graph hairballs and high maintenance cost.

## Audit requirements for next implementation

1. Tests must prove no new dependency is added unless explicitly approved.
2. Tests must prove `local_only` badges and export mode warnings are visible in UI text/helper output.
3. Tests must prove missing evidence and risk/claim panels are available.
4. Tests must prove every selected claim/action/answer can show evidence refs or missing-evidence reason.
5. Tests must prove no raw local path, API key, raw screenshot, raw answer, or real case content is committed.
6. Tests must preserve NotebookLM/P1.0 claim discipline.
7. Full pytest and CLI audit must pass before commit.

## Chosen verdict

PASS_REFERENCE_STUDY_READY_TABLE_FIRST_RECOMMENDED
