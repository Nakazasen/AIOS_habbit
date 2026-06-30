# Visual Map UI Reference Study

## Scope

This is a design/reference study only. It does not implement UI, add dependencies, add a graph database, run benchmarks, compare against NotebookLM as a benchmark, claim NotebookLM replacement, claim global parity, or open P1.0.

## Current AIOS Visual Map State

### Existing node types

From `visual_map_models.py`, AIOS already has typed nodes for: `case`, `source`, `evidence`, `extracted_fact`, `claim`, `answer`, `decision`, `action`, `risk`, `missing_evidence`, `learning_card`, `checklist_item`, `person_or_role`, `system_or_tool`, `tag_topic`, and `domain_playbook`.

### Existing edge types

Existing typed edge types are: `cites`, `supports`, `contradicts`, `derived_from`, `requires`, `blocks`, `follows_up`, `similar_to`, `caused_by`, `mitigates`, `assigned_to`, `belongs_to`, `extracted_from`, `answered_by`, `has_limitation`, `has_missing_evidence`, `updates_learning`, and `uses_domain_playbook`.

### Existing export modes

Existing export modes are `local_full`, `local_redacted`, `cloud_safe_summary`, and `notebooklm_safe`. Safe exports redact paths/names, remove `local_only` objects in cloud-safe modes, include export/privacy summaries, and keep NotebookLM/P1.0 claim discipline explicit.

### Existing preview UI

Case Cockpit currently exposes `Bản đồ tri thức công việc`, builds a current-case graph from local case/evidence/learning state, and offers local JSON plus safe Mermaid preview. After owner retrial, Visual Map preview appears after save-back with node/edge counts, missing evidence count, risk/claim count, local JSON, and safe Mermaid.

### Current owner pain points

The owner retrial shows the bridge flow improved: request_id tracking, manual JSON, pending response discovery, JSON escaping risk, and map preview are fixed or reduced. Remaining pain points for Visual Map UI are interaction-specific: the owner needs clearer ways to select a node/edge, inspect evidence, filter clutter, see missing evidence, and turn the map into next actions without understanding graph jargon.

### Current privacy constraints

AIOS is local-first. Real company evidence remains `local_only`. UI and exports must visibly show privacy mode, avoid absolute paths and personal identifiers in safe output, never upload graph data, and keep cloud-safe warnings explicit. Raw company docs, screenshots, answers, API keys, and local runtime data must not be committed.

## Reference Tool Comparison

| Tool | Useful pattern | Borrow for AIOS | Avoid | Does not fit now | Future version |
| --- | --- | --- | --- | --- | --- |
| Obsidian Graph View | Global/local graph, current-note focus, filters, tags, arrows, groups, hiding orphans. | Default to local/current case map; visible filters; color/group by type/privacy/status; arrow direction for typed relations. | Graph as decorative backlink soup; random physics layout as source of meaning; requiring owner to tune forces. | Full-vault global graph as default is too noisy and not evidence-first. | Work Stream Map with multi-case/topic view after current-case UI is stable. |
| React Flow | Selectable/draggable nodes and edges, node detail panel, controls, fit view, minimap, custom nodes. | Click node/edge -> right detail panel; simple controls; future minimap for larger cases; stable interaction vocabulary. | Diagram editor behavior that lets owner accidentally edit truth graph; heavy React component too early. | Embedded custom React adds architecture and audit cost for next sprint. | Later interactive graph if table-first owner trial proves value. |
| Cytoscape.js | Layout choices, data-driven styling, clustering/compound nodes, graph analysis, large graph handling. | Type/privacy/confidence styling; clustering low-value nodes; later analytics for degree/centrality/missing evidence. | Starting with large graph library before owner UI questions are clear. | JS safety review and dependency governance needed; overkill for small case-first UI. | Later local HTML/JS view for dense maps with audited bundle. |
| D3-force | Force simulation, collision avoidance, focus+context, hierarchy/network patterns. | Learn anti-hairball discipline: filtering, collision, focus, neighborhood expansion, stable initial views. | Force-directed graph as default; random-looking layout; high-complexity custom force tuning. | Custom D3 has highest implementation and maintenance complexity. | Use only if custom visualization need is proven and layout can be deterministic enough. |
| Logseq | Page/block graph, local context around active page. | Current-case-first with expandable context. | Generic page backlinks without typed evidence. | Block graph is not AIOS evidence schema. | Multi-case topic exploration. |
| Foam / VS Code graph | Lightweight local markdown graph inside IDE. | Local-first, no-cloud mental model; simple search/filter. | Markdown-only relationship model. | AIOS nodes are structured work objects, not notes. | Developer-facing diagnostic graph. |
| Neo4j Bloom | Guided exploration, style rules, natural-language-like graph exploration. | Guided presets and business-friendly labels. | Graph database requirement; broad exploratory graph without privacy controls. | Adds DB/infra and violates no graph database rule. | Optional conceptual inspiration only. |
| NotebookLM source/citation UX | Source-grounded answer UX and citation inspection. | Every claim/action links back to evidence or missing evidence. | Benchmark/parity framing or replacement claim. | Do not compare as benchmark in this study. | Source/citation UX audit reference only. |
| Mermaid / Markmap | Simple local text preview and shareable diagrams. | Safe preview/export for lightweight display. | Treating static Mermaid as enough interaction; diagrams become unreadable at scale. | Limited selection/detail/filter interaction. | Keep as export/preview path, not primary interaction if maps grow. |

## Borrowed Patterns

### From Obsidian

- Current-context graph first, global graph later.
- Search/filter controls always visible.
- Tags/groups/colors to reduce cognitive load.
- Link direction arrows, but grounded by typed AIOS edge reasons.
- Hide low-value/orphan nodes by default.

### From React Flow

- Click/select node and edge to open detail panel.
- Fit-to-view and reset controls.
- Minimap only after graph exceeds a threshold.
- Custom node cards for evidence, answer, risk, action, and learning.
- Keep editing disabled until graph editing has separate governance.

### From Cytoscape.js

- Data-driven styling by node type, privacy, confidence, and status.
- Grouping/clustering for low-value or repeated evidence/source nodes.
- Use analysis later to detect central blockers, unsupported claims, and dense clusters.
- Prefer preset/stable layouts for large static maps.

### From D3-force

- Hairball avoidance is a product requirement, not a visual polish task.
- Collision and repulsion help only after filtering/grouping.
- Focus+context is safer than showing everything at once.
- Avoid random force layout as the default truth surface.

## Rejected Patterns

- Graph database or Neo4j dependency for MVP UI.
- Full force-directed canvas as default view.
- Unfiltered global graph first.
- Untyped backlinks or generic `related` edges.
- Editable diagram nodes before evidence governance exists.
- Cloud rendering or cloud graph upload.
- Manufacturing-only node/edge vocabulary.
- Mermaid-only UI as final interaction model.

## AIOS UI Principles

1. Evidence-first: every visible claim links to evidence or explicit missing evidence.
2. Local-first: `local_only` data stays local and export mode is always visible.
3. Owner-first: use non-technical Vietnamese labels and explain graph terms.
4. Anti-hairball: default to small current-case view; group/hide low-value nodes; show filters.
5. Action-oriented: answer what happened, what supports it, what is missing, what risk exists, what to do next, and what to reuse.
6. Explainable edges: selecting an edge shows edge type, plain-language reason, evidence IDs, confidence, and privacy.
7. Privacy visible: show `local_only` badge, export mode badge, and cloud-safe warning.

## Proposed Views

### 1. Current Case Map

Default view. Shows case, evidence, final/strong answer, next actions, risks, missing evidence, and learning cards. It should answer: `Hồ sơ này đang nói gì và tôi nên làm gì tiếp?`

### 2. Evidence Map

Shows evidence -> extracted fact/claim -> answer. Unsupported or missing evidence must appear as first-class rows/cards, not hidden warnings.

### 3. Action Map

Shows answer -> recommended next actions -> owner/checklist/blockers. Prioritize action status, required evidence, and owner-friendly wording.

### 4. Learning Map

Shows case -> learning card -> reusable checklist -> next-time-first-check. This makes senior memory reusable beyond one case.

### Future: Work Stream Map

Multi-case/topic map. Not in the next implementation sprint unless current-case map is stable and audited.

## Concrete Case Cockpit Layout

Section title: `Bản đồ tri thức công việc`.

### Top summary cards

- `Số nút`.
- `Số quan hệ`.
- `Bằng chứng còn thiếu`.
- `Rủi ro / claim cần kiểm`.
- `Việc tiếp theo`.

### Left panel

- View selector: `Bản đồ hồ sơ`, `Bằng chứng`, `Hành động`, `Bài học`.
- Node type filter with Vietnamese labels.
- Edge type filter with Vietnamese labels.
- Privacy filter: `local_only`, `safe`, `all local`.
- Confidence filter.
- Search box.

### Center panel

- Table-first graph hybrid for next sprint.
- Rows/cards grouped by selected view.
- Optional safe Mermaid preview behind an expander.
- No force-directed UI by default.

### Right panel

- Selected node detail.
- Selected edge detail.
- Evidence references.
- Limitations/missing evidence.
- Next action.

### Bottom panels

- Missing evidence.
- Risk/claim checks.
- Learning card.
- Export controls with visible privacy/export badges.

## Implementation Strategy

### Option A — Streamlit table-first UI

Recommended for the next sprint. It is safest, fastest, does not add JS dependencies, matches local-first constraints, and is enough to run another owner UI trial. It can still support node/edge selection through tables/selectboxes and show detail panels.

### Option B — Streamlit + Mermaid/HTML preview

Good as a supplement. Use safe Mermaid preview for visual orientation, but keep tables as the source of interaction.

### Option C — React Flow embedded component

Best interaction later, but it requires custom frontend architecture, dependency review, and a stronger UI audit. Consider when owner needs drag/zoom/minimap after table-first UI proves map value.

### Option D — Cytoscape.js embedded local HTML

Strong for graph visualization and clustering later. Requires JS safety review and careful local-only export handling.

### Option E — D3-force custom

Highest complexity. Not recommended until a custom visualization problem cannot be solved by table-first, Mermaid, React Flow, or Cytoscape.

## Risk Matrix

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Hairball graph overwhelms owner | High | Current-case default, filters, grouping, table-first. |
| Privacy leak in visual/export path | High | Always show privacy/export badges, reuse safe export modes, no cloud rendering. |
| Unsupported claim looks trustworthy | High | Evidence-first display; missing evidence first-class; right-panel citations. |
| New JS dependency increases audit burden | Medium | Defer React Flow/Cytoscape/D3 until table-first proves need. |
| Owner does not understand graph jargon | Medium | Vietnamese labels and task-oriented wording. |
| Static Mermaid becomes unreadable | Medium | Use only as optional preview/export. |
| UI becomes manufacturing-specific | Medium | Keep generic node/edge labels and domain playbook metadata only. |

## Recommendation

Use Option A for the next implementation sprint: Streamlit table-first Visual Map UI, with optional safe Mermaid preview. The UI should prioritize evidence inspection, missing evidence, risk/claim visibility, next actions, and learning reuse. React Flow/Cytoscape/D3 should remain later options after a table-first owner trial identifies interaction needs.
