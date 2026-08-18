# Project Environment & Dashboard Integration Survey for `knowledge-graph.json`

**Agent**: `teamwork_preview_explorer_3`  
**Working Directory**: `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_explorer_3`  
**Target File**: `d:\Sandbox\AIOS_habbit\.understand-anything\knowledge-graph.json`  
**Timestamp**: 2026-08-19T06:15:00+07:00  

---

## 1. System Architecture & `knowledge-graph.json` Consumers

The file `.understand-anything/knowledge-graph.json` is the central knowledge artifact produced by the `/understand` engine and consumed across multiple subsystems in the development environment:

```
                                 ┌────────────────────────────────────────┐
                                 │ .understand-anything/                  │
                                 │   knowledge-graph.json                 │
                                 └──────────────────┬─────────────────────┘
                                                    │
        ┌───────────────────────────┬───────────────┴──────────────┬───────────────────────────┐
        ▼                           ▼                              ▼                           ▼
┌───────────────┐           ┌───────────────┐              ┌───────────────┐           ┌───────────────┐
│ Vite Server   │           │ React Client  │              │ Understand    │           │ Core Schema & │
│ (vite.config) │           │ (Dashboard)   │              │ Agent Skills  │           │ Search Engine │
└───────┬───────┘           └───────┬───────┘              └───────┬───────┘           └───────┬───────┘
        │                           │                              │                           │
        ▼                           ▼                              ▼                           ▼
• Token Auth                • validateGraph()              • /understand-chat          • types.ts
• Path Sanitization         • XYFlow / Elk Layouts         • /understand-explain       • schema.ts
• HTTP 200 JSON feed        • SearchEngine index           • /understand-onboard       • search.ts
```

### Detailed Component Inventory:

1. **Dashboard Server Layer (`packages/dashboard/vite.config.ts`)**:
   - **Location**: `C:\Users\Admin\.understand-anything\repo\understand-anything-plugin\packages\dashboard\vite.config.ts`
   - **File Access**: Lines 15–28 (`graphFileCandidates`), 55–70 (`graphFilePathSet`), and 308–348 (file serving middleware).
   - **Mechanism**: Reads `.understand-anything/knowledge-graph.json` from the active repository using `fs.readFileSync(..., "utf-8")` and parses it with `JSON.parse`.
   - **Path Sanitization**: Translates absolute host file paths into project-relative paths (`src/...`) before serving to the browser.
   - **Failure Mode**: If `JSON.parse` fails, the server responds with HTTP 500 (`Failed to read graph file`).

2. **Dashboard Frontend Application (`packages/dashboard/src/`)**:
   - **Location**: `C:\Users\Admin\.understand-anything\repo\understand-anything-plugin\packages\dashboard\src\`
   - **Data Fetch**: `App.tsx` (lines 133–163) executes `fetch("/knowledge-graph.json?token=...")` and immediately executes `validateGraph(data)` from `@understand-anything/core/schema`.
   - **State Store (`store.ts`)**: 
     - Rebuilds indexes `nodesById` (Map<id, GraphNode>), `nodeIdToLayerId` (Map<id, layerId>), `nodeIdToLayerIds` (Map<id, Set<layerId>>).
     - Instantiates `SearchEngine(graph.nodes)` for fuzzy/keyword search over node names, summaries, and tags.
   - **Visual Renderers**:
     - `GraphView.tsx`: XYFlow graph canvas with Elk / Dagre auto-layout.
     - `NodeInfo.tsx`: Displays `node.name`, `node.summary` (rendered as Markdown), `node.tags`, `node.complexity`.
     - `LayerLegend.tsx`: Renders architectural layer list, names, and descriptions.
     - `LearnPanel.tsx`: Interactive tour guide rendering `tour[*].title`, `tour[*].description`, and step highlights.
     - `ProjectOverview.tsx`: Displays `project.name`, `project.description`, `project.languages`, and `project.frameworks`.

3. **Core Schema & Validation Rules (`packages/core/src/schema.ts`)**:
   - **Location**: `C:\Users\Admin\.understand-anything\repo\understand-anything-plugin\packages\core\src\schema.ts`
   - **Schema Constraints**:
     - `KnowledgeGraphSchema`: Top-level collections `project`, `nodes`, `edges`, `layers`, `tour`.
     - `GraphNodeSchema`: 21 allowed `NodeType` values (`file`, `function`, `class`, `config`, `document`, `service`, `table`, etc.), `summary` (string), `tags` (string[]), `complexity` (`simple` | `moderate` | `complex`).
     - `GraphEdgeSchema`: 35 allowed `EdgeType` values, `direction` (`forward` | `backward` | `bidirectional`), `source` and `target` referential integrity.
     - `LayerSchema`: `id`, `name`, `description`, `nodeIds` (all referenced IDs must exist in `nodes`).
     - `TourStepSchema`: `order` (number), `title` (string), `description` (string), `nodeIds` (all referenced IDs must exist in `nodes`).

4. **Understand Agent Skills**:
   - `/understand-chat`: Greps `nodes[*].summary`, `nodes[*].name`, and `layers` to answer developer queries.
   - `/understand-explain`: Reads node neighborhood and summaries for code explanations.
   - `/understand-onboard`: Walks through the guided tour steps to generate onboarding documentation.

---

## 2. Runtime Environment & Toolchain Availability

| Runtime / Tool | Available in Workspace / System | Capabilities for Validation |
|---|---|---|
| **Python** | Python 3.11/3.12 in `.venv` (`pyproject.toml: >=3.11, <3.13`) | Standard modules (`json`, `pathlib`, `re`, `unicodedata`, `hashlib`) allow fast, deterministic, cross-platform verification of JSON syntax, UTF-8 validity, schema invariants, and Vietnamese translation metrics. |
| **Node.js** | Node.js runtime present (`pnpm`, `vite`, `packages/core/dist/`) | Native `JSON.parse`, direct import of `@understand-anything/core/schema`, and execution of `.mjs`/`.cjs` verification scripts. |
| **PowerShell** | Windows PowerShell 5.1 / 7+ | Automation scripting, file diffs, test automation triggering. |

---

## 3. Dashboard Visualizer Verification Methodology (Zero-Risk Protocol)

To ensure that translating `knowledge-graph.json` will not degrade or break the interactive dashboard:

1. **Pre-translation Baseline Snapshot**:
   - Create a clean backup copy: `.understand-anything/knowledge-graph.json.bak` before any write operation.
2. **Deterministic Automated Verification**:
   - Run `verify_knowledge_graph.py` (or `verify_knowledge_graph.mjs`) against the candidate file.
   - Assert all 7 core integrity gates:
     - **Gate 1 (Syntax)**: `JSON.parse` parses with 0 errors.
     - **Gate 2 (Encoding)**: 100% valid UTF-8, no replacement chars (`\uFFFD`), no null bytes (`\x00`).
     - **Gate 3 (Cardinality)**: Node count, edge count, layer count, and tour step count match baseline.
     - **Gate 4 (ID Set Parity)**: Exact 1:1 match of all node IDs and layer IDs. No IDs dropped or renamed.
     - **Gate 5 (Referential Integrity)**: 100% of edge sources/targets, layer nodeIds, and tour nodeIds exist in `nodes`.
     - **Gate 6 (Field Preservation)**: Non-translated fields (`id`, `type`, `filePath`, `tags`, `complexity`, `direction`) remain strictly intact.
     - **Gate 7 (Translation Quality)**: `nodes[*].summary`, `layers[*].description`, `tour[*].title`, and `tour[*].description` contain valid Vietnamese text while preserving core IT keywords.
3. **Live Server Smoke Testing (Optional/Manual)**:
   - When interactive server testing is desired, launch `/understand-dashboard` and verify HTTP 200 response on `http://127.0.0.1:5173/knowledge-graph.json?token=...`.

---

## 4. Verification Harness Scripts Delivered

Two production-ready verification harnesses have been written to the agent directory:

### A. Python Verification Harness (`verify_knowledge_graph.py`)
- **Path**: `.agents/teamwork_preview_explorer_3/verify_knowledge_graph.py`
- **Features**:
  - Full structural validation matching `@understand-anything/core/schema.ts`
  - Byte-level UTF-8 corruption detection
  - Exact baseline comparison mode
  - Vietnamese diacritics and IT terminology preservation checks
  - Detailed metrics, warnings, and exit codes (0 for PASS, 1 for FAIL)
- **Execution Command**:
  ```bash
  python .agents/teamwork_preview_explorer_3/verify_knowledge_graph.py .understand-anything/knowledge-graph.json .understand-anything/knowledge-graph.json.bak
  ```

### B. Node.js Verification Harness (`verify_knowledge_graph.mjs`)
- **Path**: `.agents/teamwork_preview_explorer_3/verify_knowledge_graph.mjs`
- **Features**:
  - Validates using Node.js `JSON.parse` and native buffer processing
  - Fast referential integrity and translation metric auditing
- **Execution Command**:
  ```bash
  node .agents/teamwork_preview_explorer_3/verify_knowledge_graph.mjs .understand-anything/knowledge-graph.json
  ```
