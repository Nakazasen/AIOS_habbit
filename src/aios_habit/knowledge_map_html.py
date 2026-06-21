import html
from typing import Any


def esc(val: Any) -> str:
    return html.escape(str(val), quote=True)


RELATION_LABELS = {
    "HAS_EVIDENCE": "có bằng chứng",
    "SUPPORTS": "có bằng chứng",
    "CONTAINS": "tham chiếu tài liệu",
    "LEARNED_FROM": "rút ra bài học",
    "SUGGESTS_NEXT_CHECK": "đề xuất đối ứng",
    "DESCRIBES_ROOT_CAUSE": "dẫn đến",
    "DESCRIBES_COUNTERMEASURE": "đề xuất đối ứng",
    "liên_kết": "liên quan đến",
    "khảo_sát": "liên quan đến",
    "cần_làm": "đề xuất đối ứng",
    "dẫn_đến": "dẫn đến",
    "EXPLAINS": "dẫn đến",
    "SUGGESTS_CHECK": "đề xuất đối ứng",
}

VALID_NODE_TYPES = {
    "system", "process", "setting", "error", "cause", "action", "learning",
    "document", "evidence", "case", "component", "other", "workspace",
    "notebook", "source"
}

ZONE_DEFS = [
    ("evidence", "Bằng chứng", ("evidence",)),
    ("systems", "Hệ thống / Quy trình", ("system", "process", "component")),
    ("case", "Case trung tâm", ("case",)),
    ("analysis", "Thiết lập / Lỗi / Nguyên nhân", ("setting", "error", "cause")),
    ("actions", "Đối ứng / Bài học", ("action", "learning")),
    ("documents", "Tài liệu tham chiếu", ("document",)),
    ("other", "Khác", ("other", "workspace", "notebook", "source")),
]


def _relation_label(raw: Any) -> str:
    relation = str(raw or "").strip()
    if not relation:
        return "liên quan đến"
    return RELATION_LABELS.get(relation, relation.replace("_", " "))


def _node_type(node: dict) -> str:
    ntype = str(node.get("type") or "other").lower()
    return ntype if ntype in VALID_NODE_TYPES else "other"


def _zone_for(node: dict) -> str:
    ntype = _node_type(node)
    for key, _title, types in ZONE_DEFS:
        if ntype in types:
            return key
    return "other"


def _graph_meta(graph: dict) -> dict:
    meta = graph.get("meta") or {}
    return meta if isinstance(meta, dict) else {}


def _has_real_case_flow(graph: dict) -> bool:
    meta = _graph_meta(graph)
    if meta.get("graph_kind") != "semantic":
        return False
    nodes = graph.get("nodes", [])
    node_types = {_node_type(n) for n in nodes}
    return "case" in node_types and bool(node_types & {"evidence", "learning", "cause", "action", "document"})


def _banner(meta: dict, nodes_truncated: bool, edges_truncated: bool, raw_nodes_len: int, max_nodes: int, max_edges: int) -> str:
    graph_kind = meta.get("graph_kind", "unknown")
    uses_sample_data = bool(meta.get("uses_sample_data"))
    warnings = list(meta.get("warnings") or [])

    if graph_kind == "empty":
        text = "Chưa đủ dữ liệu nghiệp vụ để dựng bản đồ tri thức. Hãy tạo Case/Evidence hoặc chọn đồ thị nhập để xem trước."
        cls = "banner warning"
    elif uses_sample_data:
        text = "Dữ liệu mẫu/import - chưa phải hồ sơ thật."
        cls = "banner sample"
    elif graph_kind == "imported":
        text = "Đồ thị nhập từ NotebookLM - kiểm tra lại trước khi kết luận."
        cls = "banner import"
    elif graph_kind == "structural":
        text = "Sơ đồ cấu trúc ứng dụng - không phải bản đồ nghiệp vụ đã xác minh."
        cls = "banner structure"
    elif graph_kind == "semantic":
        text = "Bản đồ nghiệp vụ từ hồ sơ, bằng chứng và bài học hiện có."
        cls = "banner semantic"
    else:
        text = f"Loại đồ thị: {graph_kind}"
        cls = "banner structure"

    if nodes_truncated:
        warnings.append(f"Số nút vượt quá {max_nodes}; đã ẩn {max(0, raw_nodes_len - max_nodes)} nút.")
    if edges_truncated:
        warnings.append(f"Số liên kết vượt quá {max_edges}; đã giới hạn để giữ giao diện nhẹ.")

    warning_html = ""
    if warnings:
        warning_html = "<ul>" + "".join(f"<li>{esc(w)}</li>" for w in warnings) + "</ul>"
    return f"<div class=\"{cls}\"><strong>{esc(text)}</strong>{warning_html}</div>"


def _node_card(node: dict, role_class: str = "") -> str:
    ntype = _node_type(node)
    label = node.get("label") or node.get("id") or "(không tên)"
    desc = node.get("description") or ""
    ref = node.get("source_ref") or ""
    conf = str(node.get("confidence") or "").lower()

    bits = [
        f"<article class=\"node-card {esc(ntype)} {esc(role_class)}\">",
        f"<div class=\"node-type\">{esc(ntype)}</div>",
        f"<h3>{esc(label)}</h3>",
    ]
    if desc:
        bits.append(f"<p>{esc(desc)}</p>")
    meta = []
    if conf:
        meta.append(f"<span class=\"meta-pill\">tin cậy: {esc(conf)}</span>")
    if ref:
        meta.append(f"<span class=\"meta-pill\">nguồn: {esc(ref)}</span>")
    if meta:
        bits.append(f"<div class=\"node-meta\">{''.join(meta)}</div>")
    bits.append("</article>")
    return "\n".join(bits)


def _relation_strip(edge: dict, node_map: dict) -> str:
    from_node = node_map.get(edge.get("from"), {})
    to_node = node_map.get(edge.get("to"), {})
    from_label = from_node.get("label") or edge.get("from") or "?"
    to_label = to_node.get("label") or edge.get("to") or "?"
    relation = _relation_label(edge.get("relation"))
    desc = edge.get("description") or ""
    ref = edge.get("source_ref") or ""

    details = []
    if desc:
        details.append(esc(desc))
    if ref:
        details.append(f"nguồn: {esc(ref)}")
    detail_html = f"<small>{' | '.join(details)}</small>" if details else ""
    return (
        "<div class=\"relation-strip\">"
        f"<span>{esc(from_label)}</span>"
        f"<b>{esc(relation)}</b>"
        f"<span>{esc(to_label)}</span>"
        f"{detail_html}"
        "</div>"
    )


def graph_to_case_board_html(graph: dict, max_nodes: int = 80, max_edges: int = 160) -> str:
    raw_nodes = list((graph or {}).get("nodes", []))
    raw_edges = list((graph or {}).get("edges", []))
    meta = dict(_graph_meta(graph or {}))

    if not graph or not raw_nodes:
        meta.setdefault("graph_kind", "empty")

    nodes_truncated = len(raw_nodes) > max_nodes
    nodes = raw_nodes[:max_nodes]
    node_ids = {n.get("id") for n in nodes}

    edges = []
    for edge in raw_edges:
        if edge.get("from") in node_ids and edge.get("to") in node_ids:
            edges.append(edge)
            if len(edges) >= max_edges:
                break
    edges_truncated = len(raw_edges) > len(edges)

    node_map = {n.get("id"): n for n in nodes}
    zones = {key: [] for key, _title, _types in ZONE_DEFS}
    for node in nodes:
        zones[_zone_for(node)].append(node)

    case_nodes = zones["case"]
    if not case_nodes and nodes:
        case_nodes = nodes[:1]
    center_case = case_nodes[0] if case_nodes else None

    relation_html = "\n".join(_relation_strip(edge, node_map) for edge in edges)

    def zone_cards(zone_key: str) -> str:
        return "\n".join(_node_card(node) for node in zones.get(zone_key, []))

    empty_state = ""
    if meta.get("graph_kind") == "empty" or not nodes:
        empty_state = (
            "<section class=\"empty-state\">"
            "<h2>Chưa đủ dữ liệu nghiệp vụ để dựng bản đồ tri thức.</h2>"
            "<p>Hãy tạo Case/Evidence hoặc chọn đồ thị nhập để xem trước.</p>"
            "</section>"
        )

    html_lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset=\"utf-8\">",
        "<style>",
        """
        :root {
          color-scheme: dark;
          --bg: #0f141b;
          --panel: #151b23;
          --panel-2: #1d2630;
          --line: #334155;
          --text: #e5edf5;
          --muted: #9aa8b7;
          --case: #f8d36b;
          --evidence: #67d6b0;
          --analysis: #f08a7a;
          --action: #8fb8ff;
          --doc: #c5b3ff;
        }
        body {
          margin: 0;
          padding: 18px;
          background: var(--bg);
          color: var(--text);
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
        }
        .banner {
          border: 1px solid var(--line);
          border-radius: 8px;
          margin-bottom: 14px;
          padding: 12px 14px;
          background: #182230;
          line-height: 1.45;
        }
        .banner ul { margin: 8px 0 0 18px; padding: 0; color: var(--muted); }
        .semantic { border-color: #2ea66f; }
        .import, .sample { border-color: #d48a31; background: #2a2117; }
        .structure { border-color: #4a78b8; }
        .warning { border-color: #b98b2f; background: #241f16; }
        .board {
          min-width: 980px;
          display: grid;
          grid-template-columns: 1.1fr 1.1fr 1.35fr 1.1fr 1.1fr;
          gap: 12px;
          align-items: stretch;
        }
        .zone {
          border: 1px solid var(--line);
          border-radius: 8px;
          background: var(--panel);
          padding: 12px;
          min-height: 420px;
        }
        .zone h2 {
          margin: 0 0 10px;
          font-size: 13px;
          font-weight: 700;
          text-transform: uppercase;
          color: var(--muted);
          letter-spacing: 0;
        }
        .case-column {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .case-zone { min-height: auto; }
        .case-focus {
          border: 2px solid var(--case);
          background: #292514;
          box-shadow: 0 0 0 3px rgba(248, 211, 107, 0.08);
        }
        .node-card {
          border: 1px solid #334155;
          border-radius: 8px;
          background: var(--panel-2);
          padding: 10px;
          margin-bottom: 10px;
        }
        .node-card h3 {
          margin: 4px 0 6px;
          font-size: 14px;
          line-height: 1.3;
          letter-spacing: 0;
        }
        .node-card p {
          margin: 0;
          color: var(--muted);
          font-size: 12px;
          line-height: 1.45;
        }
        .node-type {
          display: inline-block;
          color: #071018;
          background: var(--muted);
          border-radius: 4px;
          padding: 2px 6px;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
        }
        .case .node-type { background: var(--case); }
        .evidence .node-type { background: var(--evidence); }
        .cause .node-type, .error .node-type, .setting .node-type { background: var(--analysis); }
        .action .node-type, .learning .node-type { background: var(--action); }
        .document .node-type { background: var(--doc); }
        .node-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 8px;
        }
        .meta-pill {
          border: 1px solid #3b4654;
          border-radius: 4px;
          color: var(--muted);
          font-size: 11px;
          padding: 2px 5px;
        }
        .relations {
          border: 1px solid #3b4654;
          border-radius: 8px;
          background: #111820;
          padding: 10px;
        }
        .relations h2 { margin-bottom: 8px; }
        .relation-strip {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
          gap: 8px;
          align-items: center;
          border-top: 1px solid #2f3b49;
          padding: 8px 0;
          font-size: 12px;
        }
        .relation-strip:first-of-type { border-top: 0; }
        .relation-strip span { overflow-wrap: anywhere; color: var(--text); }
        .relation-strip b {
          color: var(--case);
          white-space: nowrap;
          font-size: 11px;
          border: 1px solid #5b4c23;
          border-radius: 999px;
          padding: 2px 7px;
          background: #211d12;
        }
        .relation-strip small {
          grid-column: 1 / 4;
          color: var(--muted);
          line-height: 1.35;
        }
        .empty-state {
          border: 1px dashed #526173;
          border-radius: 8px;
          padding: 28px;
          background: #131a22;
        }
        .empty-state h2 {
          margin: 0 0 8px;
          font-size: 18px;
        }
        .empty-state p { margin: 0; color: var(--muted); }
        """,
        "</style>",
        "</head>",
        "<body>",
        _banner(meta, nodes_truncated, edges_truncated, len(raw_nodes), max_nodes, max_edges),
    ]

    if empty_state:
        html_lines.append(empty_state)
    else:
        html_lines.extend(
            [
                "<main class=\"board\">",
                "<section class=\"zone\"><h2>Bằng chứng</h2>",
                zone_cards("evidence") or "<p class=\"muted\">Chưa có bằng chứng hiển thị.</p>",
                "</section>",
                "<section class=\"zone\"><h2>Hệ thống / Quy trình</h2>",
                zone_cards("systems") or "<p class=\"muted\">Chưa có hệ thống/quy trình liên quan.</p>",
                "</section>",
                "<section class=\"case-column\">",
                "<section class=\"zone case-zone\"><h2>Case trung tâm</h2>",
                _node_card(center_case, "case-focus") if center_case else "",
                "</section>",
                "<section class=\"relations\"><h2>Quan hệ đã ghi nhận</h2>",
                relation_html or "<p class=\"muted\">Chưa có quan hệ đủ dữ liệu để hiển thị.</p>",
                "</section>",
                "</section>",
                "<section class=\"zone\"><h2>Thiết lập / Lỗi / Nguyên nhân</h2>",
                zone_cards("analysis") or "<p class=\"muted\">Chưa có nguyên nhân đã xác minh.</p>",
                "</section>",
                "<section class=\"zone\"><h2>Đối ứng / Bài học / Tài liệu</h2>",
                zone_cards("actions") + zone_cards("documents") + zone_cards("other")
                or "<p class=\"muted\">Chưa có đối ứng hoặc bài học.</p>",
                "</section>",
                "</main>",
            ]
        )

    html_lines.extend(["</body>", "</html>"])
    return "\n".join(html_lines)


def graph_to_html_map(graph: dict, max_nodes: int = 50, max_edges: int = 100) -> str:
    if _has_real_case_flow(graph or {}) or (graph or {}).get("meta"):
        return graph_to_case_board_html(graph, max_nodes=max_nodes, max_edges=max_edges)

    graph = graph or {"nodes": [], "edges": [], "meta": {"graph_kind": "empty"}}
    graph.setdefault("meta", {"graph_kind": "structural"})
    return graph_to_case_board_html(graph, max_nodes=max_nodes, max_edges=max_edges)
