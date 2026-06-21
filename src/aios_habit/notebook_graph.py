from typing import Optional
from aios_habit.workspace_models import load_workspaces, load_notebooks
from aios_habit.source_ingest import load_sources
from aios_habit.case_store import load_cases, load_evidence

def escape_label(label: str) -> str:
    cleaned = label.replace('"', "'").replace('[', '(').replace(']', ')').replace('{', '(').replace('}', ')')
    cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').strip()
    if len(cleaned) > 45:
        cleaned = cleaned[:42] + "..."
    return cleaned

def build_notebook_mermaid_graph(
    workspace_id: Optional[str] = None,
    notebook_id: Optional[str] = None,
    max_nodes: int = 50
) -> str:
    workspaces = load_workspaces()
    notebooks = load_notebooks()
    sources = load_sources()
    cases = load_cases()
    evidence = load_evidence()
    
    # 1. Determine active notebooks and workspaces
    if notebook_id:
        active_notebooks = [n for n in notebooks if n.notebook_id == notebook_id]
        active_ws_ids = {n.workspace_id for n in active_notebooks}
        active_workspaces = [w for w in workspaces if w.workspace_id in active_ws_ids]
    elif workspace_id:
        active_workspaces = [w for w in workspaces if w.workspace_id == workspace_id]
        active_ws_ids = {workspace_id}
        active_notebooks = [n for n in notebooks if n.workspace_id == workspace_id]
    else:
        active_workspaces = workspaces
        active_notebooks = notebooks
        
    active_nb_ids = {n.notebook_id for n in active_notebooks}
    active_ws_ids = {w.workspace_id for w in active_workspaces}
    
    # 2. Determine active sources
    active_sources = [s for s in sources if s.notebook_id in active_nb_ids]
    
    # 3. Determine active cases
    if notebook_id:
        active_cases = [c for c in cases if notebook_id in getattr(c, "linked_notebook_ids", [])]
    elif workspace_id:
        active_cases = [c for c in cases if c.workspace_id == workspace_id]
    else:
        active_cases = cases
        
    active_case_ids = {c.case_id for c in active_cases}
    
    # 4. Determine active evidence
    active_evidence = [e for e in evidence if e.case_id in active_case_ids]
    
    # Graph building
    nodes = []
    edges = []
    added_nodes = set()
    
    def add_node(nid: str, label: str, ntype: str) -> bool:
        if nid in added_nodes:
            return True
        if len(added_nodes) >= max_nodes:
            return False
        added_nodes.add(nid)
        nodes.append((nid, label, ntype))
        return True
        
    truncated = False
    
    # Add workspaces
    for ws in active_workspaces:
        nid = f"WS_{ws.workspace_id}"
        if not add_node(nid, f"WS: {ws.name}", "workspace"):
            truncated = True
            break
            
    # Add notebooks
    if not truncated:
        for nb in active_notebooks:
            nid = f"NB_{nb.notebook_id}"
            if not add_node(nid, f"Notebook: {nb.name}", "notebook"):
                truncated = True
                break
            ws_nid = f"WS_{nb.workspace_id}"
            if ws_nid in added_nodes:
                edges.append((ws_nid, nid))
                
    # Add sources
    if not truncated:
        for src in active_sources:
            nid = f"SRC_{src.source_id}"
            if not add_node(nid, f"Source: {src.title}", "source"):
                truncated = True
                break
            nb_nid = f"NB_{src.notebook_id}"
            if nb_nid in added_nodes:
                edges.append((nb_nid, nid))
                
    # Add cases
    if not truncated:
        for case in active_cases:
            nid = f"CASE_{case.case_id}"
            if not add_node(nid, f"Case: {case.title}", "case"):
                truncated = True
                break
            for nb_id in getattr(case, "linked_notebook_ids", []):
                nb_nid = f"NB_{nb_id}"
                if nb_nid in added_nodes:
                    edges.append((nid, nb_nid))
                    
    # Add evidence
    if not truncated:
        for ev in active_evidence:
            nid = f"EVD_{ev.evidence_id}"
            if not add_node(nid, f"Evidence: {ev.title}", "evidence"):
                truncated = True
                break
            case_nid = f"CASE_{ev.case_id}"
            if case_nid in added_nodes:
                edges.append((case_nid, nid))
                
    # Format Mermaid TD
    lines = ["graph TD"]
    
    # Color coding styles
    lines.append("classDef ws fill:#4F46E5,stroke:#312E81,stroke-width:2px,color:#FFFFFF;")
    lines.append("classDef nb fill:#06B6D4,stroke:#0891B2,stroke-width:2px,color:#FFFFFF;")
    lines.append("classDef src fill:#10B981,stroke:#047857,stroke-width:2px,color:#FFFFFF;")
    lines.append("classDef case fill:#F59E0B,stroke:#D97706,stroke-width:2px,color:#FFFFFF;")
    lines.append("classDef evd fill:#EF4444,stroke:#B91C1C,stroke-width:2px,color:#FFFFFF;")
    
    # Nodes definitions
    for nid, label, ntype in nodes:
        escaped = escape_label(label)
        lines.append(f'    {nid}["{escaped}"]')
        if ntype == "workspace":
            lines.append(f"    class {nid} ws;")
        elif ntype == "notebook":
            lines.append(f"    class {nid} nb;")
        elif ntype == "source":
            lines.append(f"    class {nid} src;")
        elif ntype == "case":
            lines.append(f"    class {nid} case;")
        elif ntype == "evidence":
            lines.append(f"    class {nid} evd;")
            
    # Edges definitions
    for from_id, to_id in edges:
        if from_id in added_nodes and to_id in added_nodes:
            lines.append(f"    {from_id} --> {to_id}")
            
    if truncated:
        lines.append("    %% Đã giới hạn số node để tránh lag.")
        
    return "\n".join(lines)

def build_notebook_structural_dict_graph(
    workspace_id: Optional[str] = None,
    notebook_id: Optional[str] = None,
    max_nodes: int = 50
) -> dict:
    workspaces = load_workspaces()
    notebooks = load_notebooks()
    sources = load_sources()
    cases = load_cases()
    evidence = load_evidence()
    
    if notebook_id:
        active_notebooks = [n for n in notebooks if n.notebook_id == notebook_id]
        active_ws_ids = {n.workspace_id for n in active_notebooks}
        active_workspaces = [w for w in workspaces if w.workspace_id in active_ws_ids]
    elif workspace_id:
        active_workspaces = [w for w in workspaces if w.workspace_id == workspace_id]
        active_notebooks = [n for n in notebooks if n.workspace_id == workspace_id]
    else:
        active_workspaces = workspaces
        active_notebooks = notebooks
        
    active_nb_ids = {n.notebook_id for n in active_notebooks}
    active_sources = [s for s in sources if s.notebook_id in active_nb_ids]
    
    if notebook_id:
        active_cases = [c for c in cases if notebook_id in getattr(c, "linked_notebook_ids", [])]
    elif workspace_id:
        active_cases = [c for c in cases if c.workspace_id == workspace_id]
    else:
        active_cases = cases
        
    active_case_ids = {c.case_id for c in active_cases}
    active_evidence = [e for e in evidence if e.case_id in active_case_ids]
    
    nodes = []
    edges = []
    added_nodes = set()
    
    def add_node(nid: str, label: str, ntype: str):
        if nid in added_nodes:
            return True
        if len(nodes) >= max_nodes:
            return False
        added_nodes.add(nid)
        nodes.append({
            "id": nid,
            "label": label,
            "type": ntype,
            "description": "",
            "source_ref": "",
            "confidence": ""
        })
        return True
        
    for ws in active_workspaces:
        if not add_node(f"WS_{ws.workspace_id}", f"WS: {ws.name}", "workspace"):
            break
            
    for nb in active_notebooks:
        nid = f"NB_{nb.notebook_id}"
        if not add_node(nid, f"Notebook: {nb.name}", "notebook"):
            break
        ws_nid = f"WS_{nb.workspace_id}"
        if ws_nid in added_nodes:
            edges.append({"from": ws_nid, "to": nid, "relation": ""})
            
    for src in active_sources:
        nid = f"SRC_{src.source_id}"
        if not add_node(nid, f"Source: {src.title}", "source"):
            break
        nb_nid = f"NB_{src.notebook_id}"
        if nb_nid in added_nodes:
            edges.append({"from": nb_nid, "to": nid, "relation": ""})
            
    for case in active_cases:
        nid = f"CASE_{case.case_id}"
        if not add_node(nid, f"Case: {case.title}", "case"):
            break
        for nb_id in getattr(case, "linked_notebook_ids", []):
            nb_nid = f"NB_{nb_id}"
            if nb_nid in added_nodes:
                edges.append({"from": nid, "to": nb_nid, "relation": ""})
                
    for ev in active_evidence:
        nid = f"EVD_{ev.evidence_id}"
        if not add_node(nid, f"Evidence: {ev.title}", "evidence"):
            break
        case_nid = f"CASE_{ev.case_id}"
        if case_nid in added_nodes:
            edges.append({"from": case_nid, "to": nid, "relation": ""})
            
    return {"nodes": nodes, "edges": edges}

