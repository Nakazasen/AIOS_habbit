# Visual Knowledge Map Pattern Study

## Reference Patterns

1. **Obsidian Graph View**: 
   - Uses a node graph to visually represent backlinks.
   - Document-centered exploration.
   - Good for finding "orphaned" knowledge or central hubs.

2. **Logseq Graph / Block References**: 
   - Concept of "linked thinking".
   - Links blocks and pages.
   - Good for progressive disclosure and granular connection.

3. **TheBrain-style associative map**: 
   - A central "active" thought with parents above, children below, and jumps to the side.
   - Very focused, hierarchical associative navigation.

4. **Markmap (Markdown to Mindmap)**: 
   - Extracts heading structures and bullet points to render a tree-based mindmap.
   - Excellent for static, easily readable hierarchical maps.

5. **Mermaid Flowchart/State/Sequence**: 
   - Diagram-as-code approach.
   - Good for causal chains, workflows, system architectures, and static embedding.

6. **Cytoscape.js / D3 Graph**: 
   - Rich interactive web graphs.
   - Nodes, edges, interactive filtering, clustering.
   - High complexity but powerful.

7. **React Flow / tldraw / Excalidraw**: 
   - Canvas-based freeform spatial thinking.
   - Good for whiteboarding, manual curation.

8. **NotebookLM-style Grounding**: 
   - Focuses on the "Answer Panel" with direct source citations (Source 1, Source 2).
   - Click a citation to view the highlighted source document.

## Selected Product Patterns for AIOS Case Cockpit

Because AIOS is Streamlit/local-first and the owner needs a clear, commercial, and less technical UI:
- **Visual first**: The map must render immediately without requiring technical setup.
- **Click node to inspect evidence**: Nodes should have associated details (citations, text) accessible via a click or selection panel.
- **Filter by type**: Show/hide Evidence, AI Answers, Lessons, Systems.
- **Progressive disclosure**: Hide complex RAG/chunk/backend terms inside a "Chi tiết kỹ thuật" (Technical Details) section.
- **Source grounding**: Answers must visibly link to evidence (similar to NotebookLM).
- **Exportable formats**: Provide Markdown, Mermaid, and static HTML for easy sharing and documentation.
- **Daily owner workflow**: The graph should reflect the flow from Case -> Evidence -> Answer -> Lesson.
