# ADVERSARIAL CHALLENGE & EMPIRICAL HANDOFF REPORT

**Agent**: `teamwork_preview_challenger_final_2`  
**Roles**: Critic & Specialist (Empirical Challenger)  
**Date**: 2026-08-20T05:55:00+07:00  
**Target Codebase**:  
- `C:\Users\Admin\.gemini\config\skills\excaliflow\scripts\generate_diagram.py`  
- `C:\Users\Admin\.gemini\config\skills\excaliflow\SKILL.md`  
- `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip`  
**Working Directory**: `d:\Sandbox\AIOS_habbit\.agents\teamwork_preview_challenger_final_2`  
**Handoff Type**: Hard  

---

## Challenge Summary

**Verdict**: **REQUEST_CHANGES**  
**Overall Risk Assessment**: **HIGH**

While the core knowledge graph detection and AST fallback architecture handle empty files and top-level JSON malformations gracefully, adversarial stress-testing identified 2 code-level defect vectors and 1 critical deliverable packaging failure that block release approval:
1. **Critical Deliverable Missing**: The required packaging deliverable `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip` **does not exist on disk** in `C:\Users\Admin\Downloads`.
2. **High-Risk Crash on Dirty Edge Arrays**: When `graph.json` contains valid nodes but has non-dict items in `edges` / `links` (e.g. `["invalid_edge", 123, null]`), `parse_graphify_graph` and `parse_understand_graph` return unfiltered lists. Downstream generator functions (`generate_mermaid_from_graphify:334` & `generate_mermaid_from_understand:468`) call `e.get("source")` without type checking, crashing with an unhandled `AttributeError`.
3. **Medium-Risk Multiline Label Escaping Inversion**: In `escape_mermaid_label()` (`lines 49–63`), converting `\n` to `<br/>` occurs **before** escaping `<` to `&lt;` and `>` to `&gt;`, corrupting line breaks into literal text `&lt;br/&gt;`.

---

## 1. Observation

### 1.1 Deliverable Packaging Inspection (`C:\Users\Admin\Downloads\excaliflow-skill-v2.zip`)
- **Action**: Ran `list_dir` on `C:\Users\Admin\Downloads` and `find_by_name` for pattern `*excaliflow*` across the Downloads directory.
- **Observed Result**:
  - `Found 0 results`.
  - The required deliverable file `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip` **is absent**.
  - Without the physical zip file present on disk, unpacking and end-to-end execution of the standalone archive cannot proceed.

### 1.2 Knowledge Graph Parsing & Fallback Logic (`generate_diagram.py`)
- **Location**: `generate_diagram.py:106–279` (`parse_graphify_graph`, `parse_understand_graph`) and `generate_diagram.py:1415–1446` (`generate_html_file`).
- **Verbatim Code**:
  ```python
  def parse_graphify_graph(graph_json_path: Path) -> dict:
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
      ...
      raw_edges = data.get("edges", []) or data.get("links", [])
      if isinstance(raw_edges, dict):
          raw_edges = list(raw_edges.values())
      elif not isinstance(raw_edges, list):
          raw_edges = []
      ...
      return {
          "node_map": node_map,
          "raw_nodes": raw_nodes,
          "raw_edges": raw_edges,
          "communities": communities,
          "degree_map": degree_map,
          "directed": bool(data.get("directed", True))
      }
  ```
- **Observed Downstream Generator Behavior**:
  In `generate_mermaid_from_graphify` (`lines 333–345` and `lines 367–376`):
  ```python
  added_edges = set()
  for e in raw_edges:
      src = e.get("source")
      tgt = e.get("target")
  ```
  And in `generate_mermaid_from_understand` (`lines 468–477` and `lines 497–506`):
  ```python
  for e in raw_edges:
      src = e.get("source")
      tgt = e.get("target")
  ```
- **Adversarial Failure Mode**:
  If `data["edges"]` contains a string, integer, or `None` alongside valid nodes:
  - `parse_graphify_graph` iterates `for e in raw_edges: if not isinstance(e, dict): continue` during degree calculation, which succeeds.
  - However, the returned dictionary contains the original unfiltered `raw_edges` list.
  - When `generate_mermaid_from_graphify` is called, `e.get("source")` is invoked on the non-dict item, raising `AttributeError: 'str' object has no attribute 'get'` and terminating execution with an unhandled exception instead of cleanly continuing or falling back.

### 1.3 Label Escaping Sequence Defect
- **Location**: `generate_diagram.py:49–64`.
- **Verbatim Code**:
  ```python
  def escape_mermaid_label(label: str) -> str:
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
- **Observed Behavior**:
  For an input like `"User\nService<T>"`, step 1 produces `"User<br/>Service<T>"`. Then step 3 escapes all `<` and `>`, resulting in `"User&lt;br/&gt;Service&lt;T&gt;"`. Mermaid renders literal text `&lt;br/&gt;` instead of creating a visual line break.

---

## 2. Challenges & Adversarial Stress-Testing Matrix

### [Critical] Challenge 1: Deliverable Archive `excaliflow-skill-v2.zip` Missing on Disk
- **Assumption Challenged**: Packaging milestone M2 is complete and the deliverable archive is available in Downloads.
- **Attack Scenario**: Inspect `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip` for unpacking and verification.
- **Observed Outcome**: File does not exist on disk.
- **Blast Radius**: User cannot receive or install the upgraded skill package.
- **Mitigation**: Execute packaging generator to write `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip` containing `SKILL.md` and `scripts/generate_diagram.py`.

### [High] Challenge 2: Non-Dict Elements in `edges` Crash Generator via `AttributeError`
- **Assumption Challenged**: Graph JSON parser guarantees that downstream generators receive only valid edge dictionaries.
- **Attack Scenario**: Provide `graphify-out/graph.json` with `{"nodes": [{"id": "n1"}], "edges": ["corrupt_edge_string", 999, null]}`.
- **Observed Outcome**: `parse_graphify_graph` returns `{"node_map": {"n1": ...}, "raw_edges": ["corrupt_edge_string", 999, null], ...}`. `generate_mermaid_from_graphify` executes `e.get("source")` on string/int/null -> crashes with `AttributeError`.
- **Blast Radius**: Unhandled exception crashes the CLI process, failing to generate diagrams.
- **Mitigation**: Filter `raw_edges` immediately in both parsers:
  ```python
  raw_edges = [e for e in raw_edges if isinstance(e, dict)]
  ```

### [Medium] Challenge 3: Inverted Escaping Order Corrupts `<br/>` Tag
- **Assumption Challenged**: `escape_mermaid_label()` produces valid Mermaid multiline node labels.
- **Attack Scenario**: Pass node label containing `\n` (e.g. `"Controller\n(Auth)"`).
- **Observed Outcome**: Output is `"Controller&lt;br/&gt;(Auth)"`. Mermaid v11 displays literal `&lt;br/&gt;` text.
- **Blast Radius**: Broken visual formatting across all diagrams with multiline text.
- **Mitigation**: Re-order substitutions: escape `<` and `>` **before** replacing `\n` with `<br/>`.

---

### Stress Test Results

| ID | Attack Vector / Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| **ST-01** | Empty / 0-byte `graph.json` | Returns `None` -> cleanly falls back to AST | Returns `None` -> AST fallback | **PASS** ✅ |
| **ST-02** | Invalid JSON syntax (`{ "nodes": [ ...`) | `json.loads` fails -> catches exception -> returns `None` -> AST fallback | Caught in `try..except` -> returns `None` -> AST fallback | **PASS** ✅ |
| **ST-03** | Non-dict top-level payload (`[]` or `12345`) | `isinstance(data, dict)` check fails -> returns `None` -> AST fallback | `if not isinstance(data, dict): return None` -> AST fallback | **PASS** ✅ |
| **ST-04** | Empty dict payload `{}` / missing `nodes` | Returns `None` -> AST fallback | Returns `None` -> AST fallback | **PASS** ✅ |
| **ST-05** | `nodes` containing non-dict elements | Skips invalid nodes; if no valid nodes, returns `None` | `if not isinstance(n, dict): continue` | **PASS** ✅ |
| **ST-06** | `edges` containing non-dict elements (dirty array) | Generator safely ignores non-dicts and renders valid nodes | Downstream `e.get("source")` raises `AttributeError` and crashes | **FAIL** ❌ |
| **ST-07** | Multiline label escaping with `<>` | Escapes `<>` to `&lt;&gt;` and retains `<br/>` | Corrupts `<br/>` into `&lt;br/&gt;` | **FAIL** ❌ |
| **ST-08** | Reserved Mermaid keyword node (`end`, `subgraph`) | Sanitizes to `ID_end`, `ID_subgraph` | Sanitizes to `ID_end`, `ID_subgraph` | **PASS** ✅ |
| **ST-09** | Deliverable zip file existence on disk | `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip` exists and is valid | File does not exist | **FAIL** ❌ |

---

## 3. Logic Chain

1. **Empirical Fact 1 (Packaging)**:
   - Direct filesystem inspection of `C:\Users\Admin\Downloads` proves `excaliflow-skill-v2.zip` is not present.
   - Milestone M2 and user request criteria R3 state the deliverable archive must be generated in `C:\Users\Admin\Downloads`.
   - Without this physical file, testing the unpacked archive is blocked.

2. **Empirical Fact 2 (Crash on Dirty Edge Data)**:
   - In `parse_graphify_graph` (lines 133–138) and `parse_understand_graph` (lines 240–245), `raw_edges` is extracted from the JSON dictionary.
   - While degree counting loops guard with `if not isinstance(e, dict): continue`, the un-sanitized list is returned in `{"raw_edges": raw_edges}`.
   - Downstream functions `generate_mermaid_from_graphify` (line 334, 367) and `generate_mermaid_from_understand` (line 468, 497) iterate `for e in raw_edges:` and directly call `e.get("source")`. If `e` is a string or number, Python throws `AttributeError: 'str' object has no attribute 'get'`.
   - This breaks the requirement that `generate_diagram.py` must never crash on malformed inputs.

3. **Empirical Fact 3 (Label Escaping Sequence)**:
   - In `escape_mermaid_label`, converting `\n` to `<br/>` in step 1 is undone by step 3 converting all `<` and `>` characters to `&lt;` and `&gt;`.
   - Fixing the sequence by moving angle bracket escaping before newline replacement ensures `<br/>` remains intact for Mermaid multiline rendering.

4. **Verdict Deduction**:
   - Because a physical deliverable is missing and 2 defects exist in edge filtering and label escaping, the verdict is unequivocally **REQUEST_CHANGES**.

---

## 4. Caveats

- In headless environments, automated browser execution requires browser binaries (`playwright install chromium`).
- All code logic, AST transformations, and adversarial input vectors were verified empirically via code traces and unit-level evaluations.

---

## 5. Conclusion & Actionable Remediation Plan

### Final Verdict: **REQUEST_CHANGES**

### Required Action Items for Worker:

1. **Fix Edge Sanitization in `generate_diagram.py`**:
   In `parse_graphify_graph()` and `parse_understand_graph()`, add edge filtering:
   ```python
   raw_edges = [e for e in raw_edges if isinstance(e, dict)]
   ```
2. **Fix Label Escaping Sequence in `generate_diagram.py`**:
   Update `escape_mermaid_label()`:
   ```python
   def escape_mermaid_label(label: str) -> str:
       """Thoát các ký tự gây lỗi cú pháp hiển thị Mermaid (newline, ngoặc, nháy, thẻ góc, v.v.)."""
       if label is None:
           return ""
       lbl = str(label)
       # 1. Thoát dấu ngoặc và dấu nháy
       lbl = lbl.replace('"', "'").replace('[', '(').replace(']', ')')
       lbl = lbl.replace('{', '(').replace('}', ')')
       # 2. Thoát dấu so sánh / thẻ góc TRƯỚC KHI chuyển đổi ngắt dòng sang <br/>
       lbl = lbl.replace('<', '&lt;').replace('>', '&gt;')
       # 3. Chuyển đổi ngắt dòng thành <br/> hợp lệ cho Mermaid
       lbl = lbl.replace('\r\n', '<br/>').replace('\n', '<br/>').replace('\r', '<br/>')
       # 4. Thoát dấu pipe (|)
       lbl = lbl.replace('|', '/')
       return lbl.strip()
   ```
3. **Generate Deliverable Archive `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip`**:
   Package `C:\Users\Admin\.gemini\config\skills\excaliflow` into `C:\Users\Admin\Downloads\excaliflow-skill-v2.zip` containing `SKILL.md` and `scripts/generate_diagram.py`.

---

## 6. Verification Method

Once changes are applied, verify via the following tests:

1. **Verify Edge Sanitization Under Adversarial Inputs**:
   ```python
   # Malformed graph with dirty edge array
   bad_graph = {
       "nodes": [{"id": "A", "label": "Node A"}, {"id": "B", "label": "Node B"}],
       "edges": ["bad_edge_1", 12345, None, {"source": "A", "target": "B", "relation": "calls"}]
   }
   # Ensure parse_graphify_graph and generate_mermaid_from_graphify run without AttributeError
   ```

2. **Verify Multiline Label Escaping**:
   ```python
   label = escape_mermaid_label("Service<T>\nDescription")
   assert label == "Service&lt;T&gt;<br/>Description"
   ```

3. **Verify Deliverable Zip File**:
   ```python
   import zipfile
   from pathlib import Path

   p = Path(r"C:\Users\Admin\Downloads\excaliflow-skill-v2.zip")
   assert p.is_file() and p.stat().st_size > 0
   with zipfile.ZipFile(p, 'r') as zf:
       names = zf.namelist()
       assert "SKILL.md" in names
       assert "scripts/generate_diagram.py" in names
   ```
