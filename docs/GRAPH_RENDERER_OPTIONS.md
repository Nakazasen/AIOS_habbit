# Graph Renderer Options in AIOS Case Cockpit

AIOS Case Cockpit provides multiple visualization modes for the Knowledge Map (Bản đồ tri thức) under Tab 5 (Bản đồ). These options can be toggled using the **Kiểu hiển thị** (Display Mode) dropdown.

## 1. HTML Card Map (Bản đồ thẻ HTML)
- **Goal**: Provide a clean, readable, column-based lane board of nodes grouped by entity types (`system`, `process`, `setting`, etc.) with relationship chips.
- **Constraints**: 
  - Pure HTML and inline CSS.
  - Zero heavy external libraries (no React Flow, Cytoscape, or d3).
  - No CDNs or remote dependencies.
  - Strictly no external Javascript (`<script>`) or remote connections (`http://`, `https://`) for data safety.
  - Fully HTML-escaped node and relation properties to prevent any XSS.
- **Truncation**: Warnings are displayed if nodes exceed 50 or relations exceed 100 to ensure performance.

## 2. Table + Mermaid (Bảng + Mermaid)
- **Goal**: Offer a standard text-based diagram (Mermaid) and tabular views of nodes and edges for copying or structural review.
- **Fallback**: Works completely local via Streamlit's built-in table viewer and raw code markdown.
