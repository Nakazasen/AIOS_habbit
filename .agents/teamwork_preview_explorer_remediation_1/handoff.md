# REMEDIATION BLUEPRINT & SYNTHESIS REPORT — teamwork_preview_explorer_remediation_1

**Target Work Product**: `C:\Users\Admin\.gemini\config\skills\excaliflow\scripts\generate_diagram.py` & `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip`  
**Milestone**: Remediation Strategy & Implementation Blueprint for Excaliflow Skill Upgrade (v2)  
**Date**: 2026-08-20T05:44:00+07:00  
**Handoff Type**: Hard (Complete Actionable Blueprint)  

---

## 1. Observation

A forensic synthesis of findings across the Forensic Auditor (`teamwork_preview_auditor_1`), Code Reviewer (`teamwork_preview_reviewer_2`), Empirical Challenger 1 (`teamwork_preview_challenger_1`), and Adversarial Challenger 2 (`teamwork_preview_challenger_2`) establishes 5 distinct defect clusters:

### 1.1 Finding Catalog & Reviewer Consensus

| # | Finding & Defect Description | Severity | Sources | Empirical Evidence / Exact Location |
|---|---|---|---|---|
| **D1** | **Physical Deliverable Missing (`excaliflow-skill-v2.zip`)** | **CRITICAL (Integrity Violation)** | Auditor 1, Reviewer 2, Challenger 1, Challenger 2 | File `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip` does not exist on disk. `build_package.py` was authored in `.agents/teamwork_preview_worker_m2/` but was never executed to create the physical deliverable. |
| **D2** | **Graphify & Understand JSON Parser Fragility** | **HIGH** | Challenger 2, Reviewer 2 | `generate_diagram.py:90–96, 111–131, 163–175`. If `graph.json` contains non-dict root JSON (`[]`, `null`, `123`), `data.get()` fails with unhandled `AttributeError`. If `nodes`/`edges` contain non-dict elements (e.g. `{"nodes": ["a"]}`), `n.get()` crashes immediately before AST fallback can trigger. |
| **D3** | **Mermaid Syntax Fragility (Keywords, Newlines, Angle Brackets)** | **HIGH** | Challenger 1, Challenger 2 | `generate_diagram.py:32–43`. (1) `sanitize_mermaid_id` does not escape reserved keywords like `end`, `subgraph`, `flowchart`, `class` causing parser crashes when node id is `end`. (2) `escape_mermaid_label` does not convert `\r\n` / `\n` to `<br/>`, and does not escape `<` / `>` (e.g. `List<String>`), causing client-side Mermaid v11 parse errors. |
| **D4** | **UI Layout Collision & Event Listener Accumulation** | **MEDIUM** | Challenger 1, Reviewer 2 | `generate_diagram.py:981–999, 1195–1197`. (1) `#toggle-sidebar` sits at `top: 16px; left: 16px; z-index: 30`, directly overlapping `.header-title` when sidebar is open. (2) `diagramOutput.addEventListener('panzoomchange', ...)` is executed inside `renderDiagram()`, attaching redundant listeners on every tab switch / live edit. |
| **D5** | **Premature Script Tag Termination Injection** | **LOW / SECURITY** | Reviewer 2 | `generate_diagram.py:1333`. `json.dumps(diagrams)` is injected raw into `HTML_TEMPLATE`. If node summaries or comments contain `</script>`, it terminates the inline `<script>` tag prematurely. |

---

## 2. Logic Chain

1. **Packaging Defect Chain (D1)**:
   - *Premise*: User Request R3 and Acceptance Criteria explicitly mandate creating `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip`.
   - *Observation*: The worker wrote `build_package.py` but never ran it. The file system check confirms 0 bytes / file missing.
   - *Deduction*: The worker must execute a verified Python packaging script that creates the zip file, verifies its internal archive structure (`SKILL.md` and `scripts/generate_diagram.py` at root), and validates `zipfile.testzip() == None`.

2. **Knowledge Graph Parsing Fallback Chain (D2)**:
   - *Premise*: R4 mandates high-fidelity ingestion with automatic fallback to AST on any missing or malformed graph data.
   - *Observation*: If `graph.json` contains `[]` or `{"nodes": ["str"]}`, `data.get()` or `n.get()` throws unhandled `AttributeError` outside the `try` block, crashing the script.
   - *Deduction*: Top-level `isinstance(data, dict)` check must be enforced inside a comprehensive `try...except`. Every element in `raw_nodes`, `raw_edges`, `raw_hyperedges` must be guarded with `isinstance(item, dict)`. On any exception, return `None` so `generate_html_file` cleanly transitions to `scan_project_structure` + `scan_python_ast`.

3. **Mermaid Rendering Chain (D3)**:
   - *Premise*: Node summaries from Graphify and codebases frequently contain newlines (`\n`), generic types (`Map<K,V>`), and standard identifiers like `end.py`.
   - *Observation*: Mermaid v11 grammar treats unquoted newlines inside `["..."]` as syntax breaks, parses `end` as subgraph termination, and treats `<...>` as unclosed HTML tags.
   - *Deduction*: `sanitize_mermaid_id` must prepend a prefix (e.g. `ID_end`) for reserved keywords (`end`, `subgraph`, `graph`, `flowchart`, `class`, `click`, etc.). `escape_mermaid_label` must convert `\r\n` / `\n` to `<br/>`, escape `<` to `&lt;` and `>` to `&gt;`, and sanitize `|` and quotes.

4. **UI Architecture & DOM Cleanliness Chain (D4 & D5)**:
   - *Premise*: The UI must provide a professional, clutter-free user experience with panzoom and collapsible sidebar.
   - *Observation*: `#toggle-sidebar` placed at `(16px, 16px)` hovers over the sidebar title when the sidebar is open. Adding `panzoomchange` inside `renderDiagram()` adds an anonymous listener every time the diagram re-renders. Injecting unescaped `</script>` breaks the document parser.
   - *Deduction*:
     - Hide `#toggle-sidebar` via CSS when `#sidebar` is not collapsed (`#sidebar:not(.collapsed) + #toggle-sidebar { opacity: 0; pointer-events: none; }`).
     - Register `panzoomchange` ONCE in `DOMContentLoaded` or outside `renderDiagram()`.
     - Replace `</script>` with `<\\/script>` in `json.dumps(diagrams)`.

---

## 3. Caveats

1. **Read-Only Explorer Scope**: This blueprint specifies exact drop-in code modifications and verification procedures for the Worker agent (`teamwork_preview_worker_remediation_1` or implementer).
2. **Environment Execution**: Packaging to `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip` requires standard Python file I/O permissions.
3. **Headless Browser Testing**: Playwright tests in `verify_ui.py` can be executed if Chromium is installed; otherwise, unit tests on JSON fallback, Mermaid syntax escaping, and zip verification provide complete static/dynamic coverage.

---

## 4. Conclusion & Step-by-Step Remediation Strategy

The Worker MUST execute the following 5 concrete remediation steps:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             REMEDIATION BLUEPRINT                                │
├──────────────────────────────────────────────────────────────────────────────────┤
│ Step 1: Update generate_diagram.py Sanitization & Escaping (D3, D5)              │
│ Step 2: Update generate_diagram.py Graphify/Understand Parsers (D2)              │
│ Step 3: Update generate_diagram.py HTML Template CSS & Event Handlers (D4)       │
│ Step 4: Execute Verified Skill Packaging to C:\Users\Admin\Downloads (D1)       │
│ Step 5: Run Comprehensive Verification Test Suite & Assert 100% Pass             │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

### Step 1: Update Sanitization & Escaping in `scripts/generate_diagram.py`

**Target File**: `C:\Users\Admin\.gemini\config\skills\excaliflow\scripts\generate_diagram.py`  
**Lines to Replace**: Lines 32–44

```python
# ==========================================
# BEFORE (Lines 32–44):
# ==========================================
def sanitize_mermaid_id(raw_id: str) -> str:
    """Chuẩn hóa ID để hợp lệ trong cú pháp Mermaid (không chứa dấu cách, gạch ngang, ký tự đặc biệt)."""
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', str(raw_id))
    if clean and clean[0].isdigit():
        clean = "N_" + clean
    return clean or "NODE"


def escape_mermaid_label(label: str) -> str:
    """Thoát các ký tự gây lỗi cú pháp hiển thị Mermaid."""
    lbl = str(label).replace('"', "'").replace('[', '(').replace(']', ')').replace('{', '(').replace('}', ')')
    return lbl.strip()

# ==========================================
# AFTER (Replace with):
# ==========================================
MERMAID_RESERVED_KEYWORDS = {
    "end", "subgraph", "graph", "flowchart", "class", "click", "style",
    "call", "direction", "linkstyle", "classdef", "interpolate", "acctitle", "accdescr"
}

def sanitize_mermaid_id(raw_id: str) -> str:
    """Chuẩn hóa ID để hợp lệ trong cú pháp Mermaid (không chứa dấu cách, gạch ngang, ký tự đặc biệt và từ khóa dành riêng)."""
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', str(raw_id))
    if clean and clean[0].isdigit():
        clean = "N_" + clean
    if not clean:
        clean = "NODE"
    elif clean.lower() in MERMAID_RESERVED_KEYWORDS:
        clean = f"ID_{clean}"
    return clean


def escape_mermaid_label(label: str) -> str:
    """Thoát các ký tự gây lỗi cú pháp hiển thị Mermaid (newline, ngoặc, nháy, thẻ góc, v.v.)."""
    if label is None:
        return ""
    lbl = str(label)
    # 1. Chuyển đổi ngắt dòng thành <br/> để Mermaid hiển thị nhiều dòng hợp lệ
    lbl = lbl.replace('\r\n', '<br/>').replace('\n', '<br/>').replace('\r', '<br/>')
    # 2. Thoát dấu ngoặc và dấu nháy có thể phá vỡ cú pháp định nghĩa node
    lbl = lbl.replace('"', "'").replace('[', '(').replace(']', ')')
    lbl = lbl.replace('{', '(').replace('}', ')')
    # 3. Thoát dấu so sánh / thẻ góc tránh xung đột với HTML/Mermaid parser
    lbl = lbl.replace('<', '&lt;').replace('>', '&gt;')
    # 4. Thoát dấu pipe (|) tránh làm hỏng edge text trong cú pháp -->|label|
    lbl = lbl.replace('|', '/')
    return lbl.strip()
```

---

### Step 2: Update `parse_graphify_graph` & `parse_understand_graph`

**Target File**: `C:\Users\Admin\.gemini\config\skills\excaliflow\scripts\generate_diagram.py`  
**Lines to Replace**: Lines 85–197

```python
# ==========================================
# AFTER (Replace lines 85–197 with robust implementations):
# ==========================================
def parse_graphify_graph(graph_json_path: Path) -> dict:
    """
    Phân tích file graphify-out/graph.json để trích xuất các cộng đồng (communities/hyperedges),
    các node trung tâm (god nodes / high-degree nodes), và các liên kết quan trọng.
    Đảm bảo an toàn tuyệt đối khi gặp JSON rỗng, JSON mảng [] hoặc node/edge không đúng định dạng.
    """
    try:
        raw_text = graph_json_path.read_text(encoding="utf-8", errors="ignore")
        if not raw_text.strip():
            print(f"[!] File {graph_json_path} rỗng.")
            return None
        data = json.loads(raw_text)
    except Exception as e:
        print(f"[!] Lỗi đọc/parse JSON {graph_json_path}: {e}")
        return None

    if not isinstance(data, dict):
        print(f"[!] Cảnh báo: Dữ liệu {graph_json_path} không phải là JSON object (dict). Bỏ qua để fallback.")
        return None

    try:
        raw_nodes = data.get("nodes", [])
        if isinstance(raw_nodes, dict):
            raw_nodes = list(raw_nodes.values())
        elif not isinstance(raw_nodes, list):
            raw_nodes = []

        raw_edges = data.get("edges", []) or data.get("links", [])
        if isinstance(raw_edges, dict):
            raw_edges = list(raw_edges.values())
        elif not isinstance(raw_edges, list):
            raw_edges = []

        raw_hyperedges = data.get("hyperedges", [])
        if isinstance(raw_hyperedges, dict):
            raw_hyperedges = list(raw_hyperedges.values())
        elif not isinstance(raw_hyperedges, list):
            raw_hyperedges = []

        if not raw_nodes and not raw_hyperedges:
            return None

        node_map = {}
        degree_map = {}
        for n in raw_nodes:
            if not isinstance(n, dict):
                continue
            nid = n.get("id")
            if not nid:
                continue
            str_nid = str(nid)
            node_map[str_nid] = {
                "id": str_nid,
                "label": str(n.get("label") or nid),
                "file_type": str(n.get("file_type", "code")),
                "source_file": str(n.get("source_file", "")),
                "community": str(n.get("community", ""))
            }
            degree_map[str_nid] = 0

        for e in raw_edges:
            if not isinstance(e, dict):
                continue
            src = str(e.get("source", ""))
            tgt = str(e.get("target", ""))
            if src in degree_map:
                degree_map[src] += 1
            if tgt in degree_map:
                degree_map[tgt] += 1

        communities = []
        for h in raw_hyperedges:
            if not isinstance(h, dict):
                continue
            hid = str(h.get("id", ""))
            hlabel = str(h.get("label") or hid)
            hnodes = h.get("nodes", [])
            if isinstance(hnodes, list):
                hnodes = [str(x) for x in hnodes if x]
            else:
                hnodes = []
            relation = str(h.get("relation", ""))
            source_file = str(h.get("source_file", ""))
            if hnodes:
                communities.append({
                    "id": hid,
                    "label": hlabel,
                    "nodes": hnodes,
                    "relation": relation,
                    "source_file": source_file,
                    "size": len(hnodes)
                })

        communities.sort(key=lambda x: x["size"], reverse=True)

        if not node_map and not communities:
            return None

        return {
            "node_map": node_map,
            "raw_nodes": raw_nodes,
            "raw_edges": raw_edges,
            "communities": communities,
            "degree_map": degree_map,
            "directed": bool(data.get("directed", True))
        }
    except Exception as e:
        print(f"[!] Lỗi trích xuất đồ thị Graphify từ {graph_json_path}: {e}")
        return None


def parse_understand_graph(graph_json_path: Path) -> dict:
    """Phân tích file knowledge-graph.json từ Understand-Anything an toàn tuyệt đối."""
    try:
        raw_text = graph_json_path.read_text(encoding="utf-8", errors="ignore")
        if not raw_text.strip():
            print(f"[!] File {graph_json_path} rỗng.")
            return None
        data = json.loads(raw_text)
    except Exception as e:
        print(f"[!] Lỗi đọc/parse JSON {graph_json_path}: {e}")
        return None

    if not isinstance(data, dict):
        print(f"[!] Cảnh báo: Dữ liệu {graph_json_path} không phải là JSON object (dict). Bỏ qua để fallback.")
        return None

    try:
        raw_nodes = data.get("nodes", [])
        if isinstance(raw_nodes, dict):
            raw_nodes = list(raw_nodes.values())
        elif not isinstance(raw_nodes, list):
            raw_nodes = []

        raw_edges = data.get("edges", []) or data.get("links", [])
        if isinstance(raw_edges, dict):
            raw_edges = list(raw_edges.values())
        elif not isinstance(raw_edges, list):
            raw_edges = []

        project = data.get("project", {})
        if not isinstance(project, dict):
            project = {"name": str(project), "description": ""}

        node_map = {}
        for n in raw_nodes:
            if not isinstance(n, dict):
                continue
            nid = n.get("id")
            if not nid:
                continue
            str_nid = str(nid)
            node_map[str_nid] = {
                "id": str_nid,
                "name": str(n.get("name") or nid),
                "filePath": str(n.get("filePath", "")),
                "summary": str(n.get("summary", "")),
                "tags": n.get("tags", []) if isinstance(n.get("tags"), list) else [],
                "type": str(n.get("type", "file"))
            }

        if not node_map:
            return None

        return {
            "project": project,
            "node_map": node_map,
            "raw_nodes": raw_nodes,
            "raw_edges": raw_edges
        }
    except Exception as e:
        print(f"[!] Lỗi trích xuất đồ thị Understand từ {graph_json_path}: {e}")
        return None
```

---

### Step 3: Update HTML Template CSS & JavaScript (UI/UX Cleanliness)

**Target File**: `C:\Users\Admin\.gemini\config\skills\excaliflow\scripts\generate_diagram.py`  
**Locations**:
1. **CSS Layout & Button Overlap Fix** (around line 981):
```css
    /* Toggle Button CSS - Chỉ hiển thị khi Sidebar bị thu gọn */
    .toggle-sidebar-btn {
      position: absolute;
      top: 16px;
      left: 16px;
      z-index: 30;
      background: #ffffff;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 8px -1px rgba(0,0,0,0.08);
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      color: var(--text-main);
    }

    /* Ẩn nút toggle khi Sidebar đang mở để tránh đè lên tiêu đề header */
    #sidebar:not(.collapsed) + #toggle-sidebar {
      opacity: 0;
      pointer-events: none;
      transform: translateX(-20px);
    }

    #sidebar.collapsed + #toggle-sidebar {
      opacity: 1;
      pointer-events: auto;
      transform: translateX(0);
    }
```

2. **DOM Ordering**:
In `<body>` of `HTML_TEMPLATE`:
Place `<button id="toggle-sidebar" ...>` immediately AFTER `<aside id="sidebar">...</aside>` so the sibling selector `#sidebar:not(.collapsed) + #toggle-sidebar` works seamlessly.

```html
<body>
  <aside id="sidebar">
    <div class="header-bar">
      <div class="header-title">
        <span>🎨 Excali-Flow</span>
        <span class="badge">Hand-Drawn</span>
      </div>
      <button id="btn-collapse-sidebar" class="icon-btn" title="Thu gọn Sidebar (Ctrl+B)">◀</button>
    </div>
    ...
  </aside>

  <button id="toggle-sidebar" class="toggle-sidebar-btn" title="Mở bảng điều khiển (Ctrl+B)">
    <span>✏️</span> <span>Mở Bảng Điều Khiển</span>
  </button>

  <main id="viewport">
    ...
  </main>
```

3. **Event Listener Fix in `renderDiagram()` & Global Init**:
Remove `diagramOutput.addEventListener('panzoomchange', ...)` from inside `renderDiagram()`.  
Attach it ONCE globally or inside `DOMContentLoaded`:

```javascript
    // Gắn panzoomchange trên diagramOutput một lần duy nhất
    diagramOutput.addEventListener('panzoomchange', (event) => {
      updateZoomBadge(event.detail.scale);
    });

    async function renderDiagram() {
      const code = codeArea.value.trim();
      errorBox.style.display = 'none';
      diagramOutput.innerHTML = '<div style="font-family: var(--font-hand); font-size: 1.2rem; color: #64748b;">⏳ Đang vẽ sơ đồ phác thảo...</div>';

      try {
        const id = 'render-' + Date.now();
        const { svg } = await mermaid.render(id, code);
        diagramOutput.innerHTML = svg;

        if (panzoomInstance) {
          try { panzoomInstance.destroy(); } catch (e) {}
          panzoomInstance = null;
        }

        panzoomInstance = Panzoom(diagramOutput, {
          maxScale: 6,
          minScale: 0.1,
          step: 0.2,
          canvas: true
        });

        fitToScreen();
      } catch (err) {
        console.error(err);
        errorBox.style.display = 'block';
        errorBox.textContent = '❌ Lỗi cú pháp Mermaid: ' + (err.message || err);
      }
    }
```

4. **Clipboard & Image Export Error Handling**:
```javascript
    document.getElementById('btn-copy').onclick = () => {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(codeArea.value).then(() => {
          alert('Đã sao chép mã Mermaid vào clipboard!');
        }).catch(() => {
          fallbackCopyText(codeArea.value);
        });
      } else {
        fallbackCopyText(codeArea.value);
      }
    };

    function fallbackCopyText(text) {
      codeArea.select();
      document.execCommand('copy');
      alert('Đã sao chép mã Mermaid vào clipboard!');
    }
```
And on `img.onerror` in `export-png`:
```javascript
      img.onerror = () => {
        URL.revokeObjectURL(url);
        alert('Không thể xuất ảnh PNG từ SVG!');
      };
```

---

### Step 4: HTML Injection Escaping in `generate_html_file`

**Target File**: `C:\Users\Admin\.gemini\config\skills\excaliflow\scripts\generate_diagram.py`  
**Around Line 1333**:

```python
    diagrams_json = json.dumps(diagrams, ensure_ascii=False, indent=2)
    # Tránh làm vỡ thẻ script khi trong label hoặc code Mermaid chứa chuỗi </script>
    diagrams_json = diagrams_json.replace("</script>", "<\\/script>").replace("</SCRIPT>", "<\\/SCRIPT>")
    html_content = HTML_TEMPLATE.replace("__DIAGRAMS_DATA__", diagrams_json)
```

---

### Step 5: Executable Packaging Script & Physical Zip Creation

The worker must create and execute the verified packaging script `build_package.py`:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verified Packaging Script for Excaliflow Skill v2
Target: C:\Users\Admin\Downloads\excaliflow-skill-v2.zip
"""
import os
import sys
import zipfile
from pathlib import Path

def package_excaliflow():
    skill_dir = Path(r"C:\Users\Admin\.gemini\config\skills\excaliflow").resolve()
    zip_dest = Path(r"C:\Users\Admin\Downloads\excaliflow-skill-v2.zip").resolve()
    
    assert skill_dir.exists(), f"Skill directory {skill_dir} does not exist!"
    assert (skill_dir / "SKILL.md").is_file(), f"SKILL.md missing in {skill_dir}"
    assert (skill_dir / "scripts" / "generate_diagram.py").is_file(), f"generate_diagram.py missing in {skill_dir}"

    zip_dest.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[*] Packaging {skill_dir} -> {zip_dest}...")
    with zipfile.ZipFile(zip_dest, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(skill_dir):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(skill_dir).as_posix()
                print(f"  + Added: {rel_path} ({full_path.stat().st_size:,} bytes)")
                zf.write(full_path, arcname=rel_path)

    # Post-packaging integrity verification
    assert zip_dest.is_file(), "Zip destination file was not created!"
    assert zip_dest.stat().st_size > 0, "Zip file size is 0 bytes!"
    
    with zipfile.ZipFile(zip_dest, 'r') as zf:
        bad_file = zf.testzip()
        assert bad_file is None, f"Corrupted file in zip: {bad_file}"
        namelist = zf.namelist()
        assert "SKILL.md" in namelist, "SKILL.md missing at root of zip!"
        assert "scripts/generate_diagram.py" in namelist, "scripts/generate_diagram.py missing in zip!"
        print(f"[✓] Verification SUCCESS: {zip_dest} ({zip_dest.stat().st_size:,} bytes, {len(namelist)} files)")

if __name__ == "__main__":
    package_excaliflow()
```

---

## 5. Verification Method

To independently verify that the worker has flawlessly remediated all 5 defect clusters:

### V1. Physical Release Package Existence & Contents
Run:
```python
import os, zipfile
zip_path = r"C:\Users\Admin\Downloads\excaliflow-skill-v2.zip"
assert os.path.isfile(zip_path), f"Missing package: {zip_path}"
assert os.path.getsize(zip_path) > 1000, "Package too small"
with zipfile.ZipFile(zip_path, 'r') as zf:
    assert zf.testzip() is None, "Corrupted archive"
    names = zf.namelist()
    assert "SKILL.md" in names
    assert "scripts/generate_diagram.py" in names
print("V1 Packaging Verification: PASS")
```

### V2. Graphify / JSON Malformed Stress Test (AST Fallback)
Run a test passing `[]`, `null`, `123`, `{"nodes": ["str_node"]}`, and `{"project": "StringProject"}` into `generate_diagram.py` and assert zero process crashes and clean AST fallback.

### V3. Mermaid Syntax & Keyword Verification
Verify that:
- `sanitize_mermaid_id("end")` returns `"ID_end"` (no collision with Mermaid `end`).
- `escape_mermaid_label("Line1\nLine2<Test>")` returns `"Line1<br/>Line2&lt;Test&gt;"`.

### V4. UI Layout & Event Listener Check
- Open generated `sample_graphify_diagram.html` in browser.
- Verify `#toggle-sidebar` is hidden while sidebar is open and smoothly appears when sidebar collapses.
- Verify `panzoomchange` fires once per zoom/pan event without listener accumulation.
