import html
from typing import Any

def esc(val: Any) -> str:
    return html.escape(str(val))

def graph_to_html_map(graph: dict, max_nodes: int = 50, max_edges: int = 100) -> str:
    if not graph:
        return "<html><body style='background-color:#0e1117;color:#c9d1d9;font-family:sans-serif;padding:20px;'><h3>Đồ thị trống</h3></body></html>"
    
    raw_nodes = graph.get("nodes", [])
    raw_edges = graph.get("edges", [])
    
    nodes_truncated = len(raw_nodes) > max_nodes
    edges_truncated = len(raw_edges) > max_edges
    
    nodes = raw_nodes[:max_nodes]
    node_ids = {n.get("id") for n in nodes}
    
    # Filter edges to only include valid edges connecting two existing nodes
    edges = []
    for e in raw_edges:
        if e.get("from") in node_ids and e.get("to") in node_ids:
            edges.append(e)
            if len(edges) >= max_edges:
                break
    
    # Group nodes by type
    lanes_keys = ["system", "process", "setting", "error", "cause", "action", "learning", "document", "case", "component", "other"]
    lanes = {lk: [] for lk in lanes_keys}
    for n in nodes:
        ntype = n.get("type", "other").lower()
        if ntype not in lanes:
            ntype = "other"
        lanes[ntype].append(n)
        
    # Build node lookup map for edge labels
    node_map = {n.get("id"): n for n in nodes}
    
    # HTML generation
    html_lines = []
    html_lines.append("<!DOCTYPE html>")
    html_lines.append("<html>")
    html_lines.append("<head>")
    html_lines.append("<meta charset=\"utf-8\">")
    html_lines.append("<style>")
    html_lines.append("""
      body {
        background-color: #0e1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        margin: 0;
        padding: 16px;
      }
      .warning-banner {
        background-color: #7e5600;
        color: #ffffff;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 16px;
        font-size: 0.9em;
        border: 1px solid #d29922;
      }
      .board {
        display: flex;
        gap: 16px;
        overflow-x: auto;
        padding-bottom: 16px;
        align-items: flex-start;
      }
      .column {
        flex: 0 0 280px;
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
      }
      .column-title {
        font-size: 0.85em;
        font-weight: bold;
        color: #58a6ff;
        text-transform: uppercase;
        border-bottom: 2px solid #30363d;
        padding-bottom: 6px;
        margin-bottom: 12px;
        letter-spacing: 0.5px;
      }
      .card {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 10px;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
      }
      .card-title {
        font-weight: bold;
        font-size: 0.95em;
        margin-bottom: 6px;
        color: #ffffff;
      }
      .badge {
        display: inline-block;
        padding: 2px 6px;
        font-size: 0.7em;
        border-radius: 4px;
        font-weight: bold;
        margin-right: 4px;
        margin-bottom: 4px;
      }
      .badge-type {
        background-color: #1f6feb;
        color: #ffffff;
      }
      .badge-conf-high {
        background-color: #238636;
        color: #ffffff;
      }
      .badge-conf-medium {
        background-color: #9e6a00;
        color: #ffffff;
      }
      .badge-conf-low {
        background-color: #da3633;
        color: #ffffff;
      }
      .card-desc {
        font-size: 0.8em;
        color: #8b949e;
        margin-top: 6px;
        margin-bottom: 6px;
        line-height: 1.3;
      }
      .card-ref {
        font-size: 0.75em;
        color: #58a6ff;
        font-style: italic;
      }
      .relations-section {
        margin-top: 24px;
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
      }
      .relations-title {
        font-size: 1.0em;
        font-weight: bold;
        color: #58a6ff;
        margin-bottom: 12px;
        border-bottom: 1px solid #30363d;
        padding-bottom: 6px;
      }
      .relation-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .relation-chip {
        background-color: #21262d;
        border: 1px solid #30363d;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 0.85em;
      }
      .relation-arrow {
        color: #58a6ff;
        font-weight: bold;
        margin: 0 6px;
      }
      .relation-type {
        font-weight: bold;
        color: #f0883e;
      }
      .relation-desc {
        font-size: 0.8em;
        color: #8b949e;
        margin-top: 4px;
      }
    """)
    html_lines.append("</style>")
    html_lines.append("</head>")
    html_lines.append("<body>")
    
    # Render warning banner if truncated
    if nodes_truncated or edges_truncated:
        warn_msg = []
        if nodes_truncated:
            warn_msg.append(f"số nút vượt quá {max_nodes} (đã ẩn {len(raw_nodes) - max_nodes} nút)")
        if edges_truncated:
            warn_msg.append(f"số liên kết vượt quá {max_edges}")
        html_lines.append(f"<div class=\"warning-banner\">⚠️ <strong>Cảnh báo:</strong> Bản đồ tri thức này đã được cắt bớt do {', '.join(warn_msg)}.</div>")
        
    # Render columns board
    html_lines.append("<div class=\"board\">")
    for lane_key in lanes_keys:
        lane_nodes = lanes[lane_key]
        if not lane_nodes:
            continue
        
        lane_title = lane_key.upper()
        html_lines.append("  <div class=\"column\">")
        html_lines.append(f"    <div class=\"column-title\">{esc(lane_title)} ({len(lane_nodes)})</div>")
        for n in lane_nodes:
            html_lines.append("    <div class=\"card\">")
            html_lines.append(f"      <div class=\"card-title\">{esc(n.get('label', n.get('id')))}</div>")
            
            # Badges
            html_lines.append(f"      <span class=\"badge badge-type\">{esc(n.get('type', lane_key))}</span>")
            conf = n.get("confidence", "").lower()
            if conf in ("high", "medium", "low"):
                html_lines.append(f"      <span class=\"badge badge-conf-{conf}\">CONF: {esc(conf.upper())}</span>")
                
            # Description
            desc = n.get("description", "")
            if desc:
                html_lines.append(f"      <div class=\"card-desc\">{esc(desc)}</div>")
                
            # Reference
            ref = n.get("source_ref", "")
            if ref:
                html_lines.append(f"      <div class=\"card-ref\">{esc(ref)}</div>")
                
            html_lines.append("    </div>")
        html_lines.append("  </div>")
    html_lines.append("</div>")
    
    # Render relations/edges section
    if edges:
        html_lines.append("<div class=\"relations-section\">")
        html_lines.append("  <div class=\"relations-title\">Quan hệ liên kết giữa các thực thể (Relations)</div>")
        html_lines.append("  <div class=\"relation-list\">")
        for e in edges:
            from_node = node_map.get(e.get("from"))
            to_node = node_map.get(e.get("to"))
            
            # Skip if missing nodes
            if not from_node or not to_node:
                continue
                
            from_label = from_node.get("label", from_node.get("id"))
            to_label = to_node.get("label", to_node.get("id"))
            relation = e.get("relation", "")
            
            html_lines.append("    <div class=\"relation-chip\">")
            html_lines.append(f"      <strong>{esc(from_label)}</strong>")
            if relation:
                html_lines.append(f"      <span class=\"relation-arrow\">➔</span>")
                html_lines.append(f"      <span class=\"relation-type\">[{esc(relation)}]</span>")
                html_lines.append(f"      <span class=\"relation-arrow\">➔</span>")
            else:
                html_lines.append(f"      <span class=\"relation-arrow\">➔</span>")
                
            html_lines.append(f"      <strong>{esc(to_label)}</strong>")
            
            # Edge badges (confidence)
            edge_conf = e.get("confidence", "").lower()
            if edge_conf in ("high", "medium", "low"):
                html_lines.append(f"      <span class=\"badge badge-conf-{edge_conf}\" style=\"margin-left:8px;\">CONF: {esc(edge_conf.upper())}</span>")
                
            # Edge source reference
            edge_ref = e.get("source_ref", "")
            if edge_ref:
                html_lines.append(f"      <span class=\"card-ref\" style=\"margin-left:8px;\">({esc(edge_ref)})</span>")
                
            # Edge description
            edge_desc = e.get("description", "")
            if edge_desc:
                html_lines.append(f"      <div class=\"relation-desc\">{esc(edge_desc)}</div>")
                
            html_lines.append("    </div>")
        html_lines.append("  </div>")
        html_lines.append("</div>")
        
    html_lines.append("</body>")
    html_lines.append("</html>")
    return "\n".join(html_lines)
