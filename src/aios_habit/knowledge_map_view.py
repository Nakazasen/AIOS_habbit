import re
from typing import Dict, List, Any

def build_saved_graph_view(import_record) -> dict:
    if not import_record or not import_record.parsed_json:
        return {"nodes": [], "edges": []}
    return import_record.parsed_json

def graph_to_node_table(graph: dict) -> List[dict]:
    if not graph:
        return []
    nodes = graph.get("nodes", [])
    return [
        {
            "label": n.get("label", ""),
            "type": n.get("type", ""),
            "description": n.get("description", ""),
            "source_ref": n.get("source_ref", ""),
            "confidence": n.get("confidence", ""),
            "id": n.get("id", "")
        }
        for n in nodes
    ]

def graph_to_edge_table(graph: dict) -> List[dict]:
    if not graph:
        return []
    nodes = graph.get("nodes", [])
    node_labels = {n.get("id"): n.get("label", n.get("id")) for n in nodes}
    edges = graph.get("edges", [])
    return [
        {
            "from_label": node_labels.get(e.get("from", ""), e.get("from", "")),
            "relation": e.get("relation", ""),
            "to_label": node_labels.get(e.get("to", ""), e.get("to", "")),
            "description": e.get("description", ""),
            "source_ref": e.get("source_ref", ""),
            "confidence": e.get("confidence", "")
        }
        for e in edges
    ]

def sanitize_id(nid: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', str(nid))

def escape_label(label: str) -> str:
    cleaned = label.replace('"', "'").replace('[', '(').replace(']', ')').replace('{', '(').replace('}', ')')
    cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').strip()
    if len(cleaned) > 45:
        cleaned = cleaned[:42] + "..."
    return cleaned

def graph_to_pretty_mermaid(graph: dict, max_nodes: int = 50) -> str:
    if not graph:
        return "graph LR\n    %% Empty graph"
        
    raw_nodes = graph.get("nodes", [])
    truncated = len(raw_nodes) > max_nodes
    nodes = raw_nodes[:max_nodes]
    node_ids = {n.get("id") for n in nodes}
    
    lines = ["flowchart LR"]
    
    # Class definitions for node types
    lines.append("    classDef system fill:#4F46E5,stroke:#312E81,stroke-width:2px,color:#FFFFFF;")
    lines.append("    classDef process fill:#06B6D4,stroke:#0891B2,stroke-width:2px,color:#FFFFFF;")
    lines.append("    classDef setting fill:#10B981,stroke:#047857,stroke-width:2px,color:#FFFFFF;")
    lines.append("    classDef error fill:#EF4444,stroke:#B91C1C,stroke-width:2px,color:#FFFFFF;")
    lines.append("    classDef cause fill:#F59E0B,stroke:#D97706,stroke-width:2px,color:#FFFFFF;")
    lines.append("    classDef action fill:#8B5CF6,stroke:#5B21B6,stroke-width:2px,color:#FFFFFF;")
    lines.append("    classDef document fill:#6B7280,stroke:#374151,stroke-width:2px,color:#FFFFFF;")
    lines.append("    classDef component fill:#EC4899,stroke:#BE185D,stroke-width:2px,color:#FFFFFF;")
    lines.append("    classDef case fill:#F59E0B,stroke:#D97706,stroke-width:2px,color:#FFFFFF;")
    lines.append("    classDef other fill:#6B7280,stroke:#374151,stroke-width:2px,color:#FFFFFF;")
    
    # Render nodes
    for n in nodes:
        nid = n.get("id", "")
        if not nid:
            continue
        san_id = sanitize_id(nid)
        label = n.get("label", nid)
        escaped = escape_label(label)
        ntype = n.get("type", "other")
        
        lines.append(f'    {san_id}["{escaped}"]')
        
        # Apply style classes if matching
        if ntype in ("system", "process", "setting", "error", "cause", "action", "document", "component", "case", "other"):
            lines.append(f"    class {san_id} {ntype};")
            
    # Render edges
    edges = graph.get("edges", [])
    for e in edges:
        from_id = e.get("from", "")
        to_id = e.get("to", "")
        
        # Skip if source or target node is missing in graph/nodes list
        if not from_id or not to_id or from_id not in node_ids or to_id not in node_ids:
            continue
            
        san_from = sanitize_id(from_id)
        san_to = sanitize_id(to_id)
        relation = e.get("relation", "")
        
        if relation:
            escaped_rel = escape_label(relation)
            lines.append(f"    {san_from} -->|{escaped_rel}| {san_to}")
        else:
            lines.append(f"    {san_from} --> {san_to}")
            
    if truncated:
        lines.append("    %% Đã giới hạn số node vẽ Mermaid để tránh quá tải.")
        
    return "\n".join(lines)
