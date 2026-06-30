# Visual Map UI Interaction Table-First Report

## What was implemented
We implemented a table-first Visual Knowledge Map UI in `case_cockpit.py`, avoiding any heavy JavaScript or graph database dependencies. We introduced a new helper module `visual_map_ui.py` that processes the graph state and serves as the bridge between the logic layer and the Streamlit UI presentation.

## Reference study followed
The implementation adheres strictly to the `.ai/VISUAL_MAP_UI_REFERENCE_STUDY.md` and `.ai/VISUAL_MAP_UI_INTERACTION_DECISION.md`. We selected Option A (Streamlit table-first UI) augmented with Option B (safe Mermaid preview). 

## Why table-first
Table-first UI avoids the "graph hairball" problem common in complex, force-directed network visualizations (e.g., D3, Cytoscape). It allows the owner to read the map like a structured report with familiar filtering controls, focusing on what matters: missing evidence, unsupported claims, and next actions. It is also the safest and fastest way to ensure data stays local without requiring extensive security audits of third-party JS libraries.

## UI helper module
`visual_map_ui.py` contains deterministic functions that compute map metrics (node count, edge count, missing evidence, risk), extract specific nodes (actions, missing evidence, learning cards), retrieve detail payloads with optional safe redaction, and build owner summaries. It has no Streamlit dependency, keeping it clean and testable.

## Case Cockpit UI changes
The section "Bản đồ tri thức công việc" has been rebuilt with the following sections:
- **Tóm tắt bản đồ**: Top-level metrics.
- **Tóm tắt cho owner**: A generated textual report summarizing what the graph says, what's missing, risks, next actions, and learning.
- **Chọn góc nhìn / Bộ lọc**: Selectboxes to filter nodes and edges by type, privacy, confidence, and search strings.
- **Dataframes**: Tabular views for nodes and edges.
- **Chi tiết**: Node and edge detail inspection by selecting specific IDs.
- **Missing evidence / Risk / Action / Learning panels**: Dedicated panels highlighting critical nodes.
- **Export**: Local JSON and safe Mermaid export capabilities with a visible preview.

## Exports and Privacy
The system displays a clear warning: "Dữ liệu local_only chỉ dùng trong máy này". The safe Mermaid export and cloud-safe JSON exports correctly filter out `local_only` nodes and redact sensitive paths/names to prevent data leakage. No raw paths are displayed in safe mode exports.

## Anti-hairball behavior
By default, the table only shows the current case map items and requires the user to select specific nodes/edges for deep inspection. The Mermaid preview is collapsed inside an expander so it doesn't dominate the screen or become a confusing "hairball" when the graph is large.

## Tests
- Added `test_visual_map_ui.py` to verify the UI helper module functionality, counts, filtering, payloads, and owner summary.
- Added `test_visual_map_case_cockpit_interaction.py` to ensure all required Vietnamese labels are present and no forbidden dependencies (React Flow, D3, etc.) are introduced.
- Tests pass cleanly without modifying the core behavior.

## Stash status
The dirty working tree from a previous UI attempt was stashed and ignored during this implementation. The stash remains on the stack and was not blindly applied.

## Remaining gaps
- There is no interactive drag-and-drop graph rendering.
- No multi-case/Work Stream Map view yet.
- The Mermaid preview may become difficult to read for extremely large graphs (but the table UI compensates for this).

## Readiness
- Ready for Codex audit: YES
- Ready for owner UI trial: YES
