#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
Excali-Flow v2: Universal Architecture & Diagram Generator (Mermaid -> Excalidraw)
Tự động quét cấu trúc bất kỳ dự án nào (Python, Node.js, Go, Rust, v.v.),
tích hợp phân tích Đồ thị tri thức (Graphify / Knowledge Graph),
tạo sơ đồ kiến trúc Mermaid phong cách vẽ tay Excalidraw và xuất ra giao diện
Web tương tác độc lập (Standalone Single-File HTML) với Pan/Zoom (Panzoom v4.5.1),
Collapsible Sidebar (Ctrl+B), Live Editor, Export PNG 2x / SVG Vector.
=============================================================================
"""

import os
import sys
import re
import time
import ast
import json
import webbrowser
import argparse
from pathlib import Path

# Đảm bảo in UTF-8 trên Windows console
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


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
    # 1. Thoát dấu ngoặc và dấu nháy có thể phá vỡ cú pháp định nghĩa node
    lbl = lbl.replace('"', "'").replace('[', '(').replace(']', ')')
    lbl = lbl.replace('{', '(').replace('}', ')')
    # 2. Thoát dấu so sánh / thẻ góc TRƯỚC KHI chuyển đổi ngắt dòng sang <br/>
    lbl = lbl.replace('<', '&lt;').replace('>', '&gt;')
    # 3. Chuyển đổi ngắt dòng thành <br/> để Mermaid hiển thị nhiều dòng hợp lệ
    lbl = lbl.replace('\r\n', '<br/>').replace('\n', '<br/>').replace('\r', '<br/>')
    # 4. Thoát dấu pipe (|) tránh làm hỏng edge text trong cú pháp -->|label|
    lbl = lbl.replace('|', '/')
    return lbl.strip()



def find_knowledge_graph(project_root: Path):
    """
    Tự động tìm kiếm file đồ thị tri thức (Graphify hoặc Understand-Anything).
    Ưu tiên:
    1. graphify-out/graph.json (hoặc trong thư mục con của graphify-out)
    2. .understand-anything/knowledge-graph.json
    3. .understand/knowledge-graph.json
    4. graph.json / knowledge-graph.json ở root
    """
    project_root = project_root.resolve()
    
    # 1. Check graphify-out
    g_out = project_root / "graphify-out" / "graph.json"
    if g_out.is_file():
        return ("graphify", g_out)
    
    if (project_root / "graphify-out").is_dir():
        for p in (project_root / "graphify-out").glob("**/graph.json"):
            if p.is_file():
                return ("graphify", p)

    # 2. Check .understand-anything
    u_out = project_root / ".understand-anything" / "knowledge-graph.json"
    if u_out.is_file():
        return ("understand", u_out)
        
    u_out2 = project_root / ".understand" / "knowledge-graph.json"
    if u_out2.is_file():
        return ("understand", u_out2)

    # 3. Check root
    if (project_root / "graph.json").is_file():
        return ("graphify", project_root / "graph.json")
    if (project_root / "knowledge-graph.json").is_file():
        return ("understand", project_root / "knowledge-graph.json")

    return (None, None)


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
        raw_edges = [e for e in raw_edges if isinstance(e, dict)]

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
        raw_edges = [e for e in raw_edges if isinstance(e, dict)]

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


def generate_mermaid_from_graphify(graph_data: dict, root_name: str) -> dict:
    """Tạo sơ đồ Mermaid độ nét cao từ dữ liệu đồ thị Graphify."""
    diagrams = {}
    node_map = graph_data["node_map"]
    raw_edges = graph_data["raw_edges"]
    communities = graph_data["communities"]
    degree_map = graph_data["degree_map"]

    # 1. SƠ ĐỒ CỘNG ĐỒNG KIẾN TRÚC (Graphify Communities Architecture)
    comm_lines = [
        "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2fe', 'primaryBorderColor': '#0284c7', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef3c7', 'secondaryBorderColor': '#d97706', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#f3e8ff', 'tertiaryBorderColor': '#9333ea', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%",
        "flowchart TD"
    ]

    used_node_ids = set()
    node_to_comm = {}

    if communities:
        for idx, comm in enumerate(communities[:8]):
            comm_id = f"COMM_{idx}"
            comm_label = escape_mermaid_label(comm['label'])
            comm_lines.append(f'    subgraph {comm_id}["📦 {comm_label}"]')
            
            for nid in comm["nodes"][:6]:
                clean_id = sanitize_mermaid_id(nid)
                used_node_ids.add(nid)
                node_to_comm[nid] = comm_id
                
                ninfo = node_map.get(nid, {})
                label = escape_mermaid_label(ninfo.get("label", nid))
                icon = "📄" if ninfo.get("file_type") == "code" else "📑"
                comm_lines.append(f'        {clean_id}["{icon} {label}"]')
            comm_lines.append('    end')
    else:
        # Fallback grouping by source_file directory
        dir_groups = {}
        for nid, ninfo in node_map.items():
            sfile = ninfo.get("source_file", "")
            dname = sfile.split("/")[0] if "/" in sfile else "Core"
            dir_groups.setdefault(dname, []).append(nid)
            
        for idx, (dname, nids) in enumerate(list(dir_groups.items())[:6]):
            comm_id = f"DIR_{idx}"
            comm_lines.append(f'    subgraph {comm_id}["📁 {dname}"]')
            for nid in nids[:5]:
                clean_id = sanitize_mermaid_id(nid)
                used_node_ids.add(nid)
                label = escape_mermaid_label(node_map[nid].get("label", nid))
                comm_lines.append(f'        {clean_id}["📄 {label}"]')
            comm_lines.append('    end')

    # Draw inter-community edges
    added_edges = set()
    for e in raw_edges:
        src = e.get("source")
        tgt = e.get("target")
        if src in used_node_ids and tgt in used_node_ids and src != tgt:
            rel = escape_mermaid_label(e.get("relation", "relates_to"))
            pair = (src, tgt, rel)
            if pair not in added_edges and len(added_edges) < 25:
                added_edges.add(pair)
                s_id = sanitize_mermaid_id(src)
                t_id = sanitize_mermaid_id(tgt)
                comm_lines.append(f'    {s_id} -->|{rel}| {t_id}')

    diagrams["graphify_arch"] = {
        "title": "🧠 Kiến Trúc Tri Thức & Cộng Đồng (Graphify Knowledge Architecture)",
        "desc": f"Đồ thị cộng đồng kiến trúc và các mô-đun chức năng được trích xuất từ Graphify cho {root_name}",
        "code": "\n".join(comm_lines)
    }

    # 2. SƠ ĐỒ MẠNG LƯỚI PHỤ THUỘC & GỌI HÀM (Dependency & Call Graph)
    dep_lines = [
        "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ede9fe', 'primaryBorderColor': '#7c3aed', 'primaryTextColor': '#0f172a', 'secondaryColor': '#dcfce7', 'secondaryBorderColor': '#16a34a', 'secondaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%",
        "flowchart LR"
    ]

    sorted_nodes = sorted(degree_map.items(), key=lambda x: x[1], reverse=True)
    top_nids = {nid for nid, deg in sorted_nodes[:25] if nid in node_map}
    
    for nid in top_nids:
        clean_id = sanitize_mermaid_id(nid)
        label = escape_mermaid_label(node_map[nid]["label"])
        dep_lines.append(f'    {clean_id}["⚙️ <b>{label}</b>"]')

    added_dep_edges = set()
    for e in raw_edges:
        src = e.get("source")
        tgt = e.get("target")
        if src in top_nids and tgt in top_nids and src != tgt:
            rel = escape_mermaid_label(e.get("relation", "calls"))
            pair = (src, tgt)
            if pair not in added_dep_edges and len(added_dep_edges) < 30:
                added_dep_edges.add(pair)
                dep_lines.append(f'    {sanitize_mermaid_id(src)} -->|{rel}| {sanitize_mermaid_id(tgt)}')

    diagrams["graphify_deps"] = {
        "title": "🔗 Mạng Lưới Phụ Thuộc & Quan Hệ Mô-Đun (Dependency Graph)",
        "desc": "Các nút trung tâm (God nodes) và liên kết phụ thuộc, luồng gọi hàm giữa các thành phần cốt lõi",
        "code": "\n".join(dep_lines)
    }

    # 3. SƠ ĐỒ LUỒNG DỮ LIỆU & VẬN HÀNH (Data Flow & Pipeline)
    diagrams["pipeline"] = {
        "title": "🔄 Luồng Dữ Liệu & Xử Lý (Data Pipeline)",
        "desc": "Mô tả chu trình tiếp nhận dữ liệu đầu vào, xử lý qua các tầng và xuất kết quả",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#dcfce7', 'primaryBorderColor': '#16a34a', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef9c3', 'secondaryBorderColor': '#ca8a04', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#fee2e2', 'tertiaryBorderColor': '#dc2626', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '15px' }, 'look': 'handDrawn'}}%%
flowchart LR
    INPUT["📥 Dữ liệu đầu vào<br/>(Sources / Evidence)"] --> AUTH{"🔐 Kiểm tra & Xác thực"}
    
    AUTH -->|Hợp lệ| PROCESS["⚙️ Xử lý Logic & Trích xuất<br/>(Extraction Engine)"]
    AUTH -->|Không hợp lệ| ERR["❌ Báo lỗi & Ghi log"]

    PROCESS --> VAULT[("💾 Lưu trữ Bằng chứng & Bộ nhớ<br/>(Evidence Vault / Knowledge Graph)")]
    VAULT --> SYNTH["✨ Tổng hợp & Điều phối Agent"]
    SYNTH --> OUTPUT["📤 Xuất kết quả & Phản hồi<br/>(Workspace Output / Insights)"]
"""
    }

    # 4. SƠ ĐỒ TUẦN TỰ (Sequence / Call Flow)
    diagrams["sequence"] = {
        "title": "⏱️ Sơ Đồ Tuần Tự (Sequence Diagram)",
        "desc": "Luồng tương tác tuần tự giữa Người dùng, Giao diện, Bộ định tuyến và Tầng lưu trữ",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#fee2e2', 'primaryBorderColor': '#dc2626', 'primaryTextColor': '#0f172a', 'secondaryColor': '#e0f2fe', 'secondaryBorderColor': '#0284c7', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%
sequenceDiagram
    autonumber
    actor User as 👤 Người Dùng (User)
    participant UI as 🖥️ Giao Diện (Workspace UI)
    participant Router as 🧭 Bộ Định Tuyến (Router / Gateway)
    participant Agent as 🤖 Tác Vụ Agent (Orchestrator)
    participant Vault as 💾 Lưu Trữ (Memory Vault / DB)

    User->>UI: 1. Gửi yêu cầu / Thao tác tương tác
    UI->>Router: 2. Chuyển tiếp Request và Context
    Router->>Vault: 3. Truy vấn Bằng chứng & Tri thức
    Vault-->>Router: 4. Trả về đồ thị ngữ cảnh liên quan
    Router->>Agent: 5. Kích hoạt Agent xử lý chuyên sâu
    Agent->>Agent: 6. Thực thi thuật toán & biến đổi
    Agent->>Vault: 7. Ghi nhận Checkpoint & Bằng chứng mới
    Agent-->>UI: 8. Cập nhật kết quả hoàn thành
    UI-->>User: 9. Hiển thị thông báo và đồ họa trực quan
"""
    }

    return diagrams


def generate_mermaid_from_understand(understand_data: dict, root_name: str) -> dict:
    """Tạo sơ đồ Mermaid từ dữ liệu Understand-Anything knowledge-graph.json."""
    diagrams = {}
    node_map = understand_data["node_map"]
    raw_edges = understand_data["raw_edges"]
    project = understand_data.get("project", {})

    proj_name = project.get("name", root_name)
    proj_desc = project.get("description", "Dự án phần mềm")

    dir_groups = {}
    for nid, ninfo in node_map.items():
        fpath = ninfo.get("filePath", "")
        if "/" in fpath:
            top_dir = fpath.split("/")[0]
            if top_dir.startswith(".") and "/" in fpath:
                parts = fpath.split("/")
                top_dir = f"{parts[0]}/{parts[1]}" if len(parts) > 1 else parts[0]
        else:
            top_dir = "Root"
        dir_groups.setdefault(top_dir, []).append(nid)

    arch_lines = [
        "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2fe', 'primaryBorderColor': '#0284c7', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef3c7', 'secondaryBorderColor': '#d97706', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#f3e8ff', 'tertiaryBorderColor': '#9333ea', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%",
        "flowchart TD"
    ]

    used_nodes = set()
    for idx, (group_name, nids) in enumerate(list(dir_groups.items())[:8]):
        gid = f"GRP_{idx}"
        clean_gname = escape_mermaid_label(group_name)
        arch_lines.append(f'    subgraph {gid}["📁 {clean_gname}"]')
        for nid in nids[:5]:
            clean_id = sanitize_mermaid_id(nid)
            used_nodes.add(nid)
            name = escape_mermaid_label(node_map[nid].get("name", nid))
            arch_lines.append(f'        {clean_id}["📄 {name}"]')
        arch_lines.append('    end')

    added_edges = set()
    for e in raw_edges:
        src = e.get("source")
        tgt = e.get("target")
        if src in used_nodes and tgt in used_nodes and src != tgt:
            etype = escape_mermaid_label(e.get("type", "uses"))
            pair = (src, tgt)
            if pair not in added_edges and len(added_edges) < 25:
                added_edges.add(pair)
                arch_lines.append(f'    {sanitize_mermaid_id(src)} -->|{etype}| {sanitize_mermaid_id(tgt)}')

    diagrams["understand_arch"] = {
        "title": "🏛️ Kiến Trúc Hệ Thống (Knowledge Graph Architecture)",
        "desc": f"Sơ đồ phân cấp cấu trúc thành phần từ đồ thị tri thức của {proj_name}: {proj_desc}",
        "code": "\n".join(arch_lines)
    }

    # Dependency Flow
    dep_lines = [
        "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ede9fe', 'primaryBorderColor': '#7c3aed', 'primaryTextColor': '#0f172a', 'secondaryColor': '#dcfce7', 'secondaryBorderColor': '#16a34a', 'secondaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%",
        "flowchart LR"
    ]
    
    code_nodes = [nid for nid, n in node_map.items() if "src" in n.get("filePath", "") or n.get("type") == "file"][:20]
    for nid in code_nodes:
        clean_id = sanitize_mermaid_id(nid)
        name = escape_mermaid_label(node_map[nid]["name"])
        dep_lines.append(f'    {clean_id}["⚙️ {name}"]')

    dep_set = set()
    for e in raw_edges:
        src = e.get("source")
        tgt = e.get("target")
        if src in code_nodes and tgt in code_nodes and src != tgt:
            pair = (src, tgt)
            if pair not in dep_set and len(dep_set) < 25:
                dep_set.add(pair)
                rel = escape_mermaid_label(e.get("type", "imports"))
                dep_lines.append(f'    {sanitize_mermaid_id(src)} -->|{rel}| {sanitize_mermaid_id(tgt)}')

    diagrams["understand_deps"] = {
        "title": "🔗 Liên Kết Phụ Thuộc Mô-Đun (Module Dependency)",
        "desc": "Mối quan hệ import và sử dụng giữa các module mã nguồn trong dự án",
        "code": "\n".join(dep_lines)
    }

    # Pipeline
    diagrams["pipeline"] = {
        "title": "🔄 Luồng Dữ Liệu & Vận Hành (Data Pipeline)",
        "desc": "Quy trình xử lý dữ liệu từ đầu vào đến lưu trữ và hiển thị kết quả",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#dcfce7', 'primaryBorderColor': '#16a34a', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef9c3', 'secondaryBorderColor': '#ca8a04', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#fee2e2', 'tertiaryBorderColor': '#dc2626', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '15px' }, 'look': 'handDrawn'}}%%
flowchart LR
    INPUT["📥 Dữ liệu & Sự kiện"] --> ROUTER{"🧭 Điều phối & Xác thực"}
    ROUTER -->|Hợp lệ| EXEC["⚙️ Bộ Xử Lý Cốt Lõi"]
    ROUTER -->|Không hợp lệ| ERR["❌ Xử lý lỗi"]
    EXEC --> DB[("💾 Cơ sở dữ liệu & Bộ nhớ")]
    DB --> UI["🖥️ Giao diện người dùng"]
"""
    }

    # Sequence
    diagrams["sequence"] = {
        "title": "⏱️ Sơ Đồ Tuần Tự (Sequence Diagram)",
        "desc": "Luồng trao đổi thông điệp tuần tự giữa Client, Controller và Database",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#fee2e2', 'primaryBorderColor': '#dc2626', 'primaryTextColor': '#0f172a', 'secondaryColor': '#e0f2fe', 'secondaryBorderColor': '#0284c7', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%
sequenceDiagram
    autonumber
    actor User as 👤 Người Dùng
    participant UI as 🖥️ Giao Diện
    participant Core as ⚙️ Bộ Xử Lý
    participant Storage as 💾 Lưu Trữ

    User->>UI: 1. Thao tác / Gửi yêu cầu
    UI->>Core: 2. Kích hoạt xử lý với tham số
    Core->>Storage: 3. Đọc / Ghi dữ liệu
    Storage-->>Core: 4. Trả về kết quả
    Core-->>UI: 5. Cập nhật trạng thái
    UI-->>User: 6. Hiển thị hoàn tất
"""
    }

    return diagrams


def scan_project_structure(project_root: Path) -> dict:
    """Tự động phân tích ngôn ngữ và cấu trúc dự án bất kỳ (Fallback khi không có Knowledge Graph)."""
    project_root = project_root.resolve()
    
    is_python = any(project_root.glob("*.py")) or (project_root / "src").exists() or (project_root / "requirements.txt").exists() or (project_root / "pyproject.toml").exists()
    is_node = (project_root / "package.json").exists() or (project_root / "node_modules").exists()
    is_go = (project_root / "go.mod").exists() or any(project_root.glob("*.go"))
    is_rust = (project_root / "Cargo.toml").exists()

    file_tree = {}
    total_files = 0

    ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build', '.next', '.cache', 'graphify-out'}

    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        rel_root = Path(root).relative_to(project_root).as_posix()
        
        valid_files = [f for f in files if not f.startswith('.') and not f.endswith(('.pyc', '.exe', '.dll', '.so', '.dylib'))]
        if valid_files:
            file_tree[rel_root] = valid_files[:15]
            total_files += len(valid_files)

    return {
        "root_name": project_root.name,
        "is_python": is_python,
        "is_node": is_node,
        "is_go": is_go,
        "is_rust": is_rust,
        "file_tree": file_tree,
        "total_files": total_files
    }


def scan_python_ast(project_root: Path) -> dict:
    """Quét AST mã nguồn Python nếu là dự án Python."""
    classes = {}
    functions = {}
    calls = []

    files_to_scan = list(project_root.glob("src/**/*.py")) + list(project_root.glob("*.py"))
    
    for file_path in files_to_scan[:40]:
        if "__pycache__" in str(file_path):
            continue
        rel_path = file_path.relative_to(project_root).as_posix()
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8", errors="ignore"), filename=str(file_path))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes[node.name] = {
                    "file": rel_path,
                    "methods": methods[:6],
                    "bases": [b.id for b in node.bases if isinstance(b, ast.Name)]
                }
            elif isinstance(node, ast.FunctionDef) and not isinstance(getattr(node, 'parent', None), ast.ClassDef):
                functions[node.name] = {
                    "file": rel_path,
                    "args": [a.arg for a in node.args.args][:4]
                }
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append({"caller_file": rel_path, "target": node.func.id})
                elif isinstance(node.func, ast.Attribute):
                    calls.append({"caller_file": rel_path, "target": node.func.attr})

    return {"classes": classes, "functions": functions, "calls": calls}


def generate_mermaid_from_project(project_info: dict, ast_data: dict = None) -> dict:
    """Tự động sinh các mẫu sơ đồ Mermaid phong cách Excalidraw cho dự án thông thường."""
    root_name = project_info["root_name"]
    diagrams = {}

    # --- SƠ ĐỒ 1: KIẾN TRÚC MÔ-ĐUN TỔNG THỂ ---
    flow_lines = [
        "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2fe', 'primaryBorderColor': '#0284c7', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef3c7', 'secondaryBorderColor': '#d97706', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#f3e8ff', 'tertiaryBorderColor': '#9333ea', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '15px' }, 'look': 'handDrawn'}}%%",
        "flowchart TD"
    ]

    sub_idx = 0
    dir_nodes = {}
    for rel_dir, files in list(project_info["file_tree"].items())[:8]:
        sub_id = f"DIR_{sub_idx}"
        sub_idx += 1
        disp_name = rel_dir if rel_dir != "." else f"📦 {root_name} (Root)"
        flow_lines.append(f'    subgraph {sub_id}["📁 {disp_name}"]')
        
        for f in files[:5]:
            file_node_id = f"F_{sub_idx}_{abs(hash(f)) % 10000}"
            dir_nodes[f] = file_node_id
            flow_lines.append(f'        {file_node_id}["📄 {f}"]')
        flow_lines.append('    end')

    root_files = project_info["file_tree"].get(".", [])
    for rf in root_files[:3]:
        rf_id = dir_nodes.get(rf)
        if rf_id:
            for other_f, of_id in dir_nodes.items():
                if of_id != rf_id and not any(other_f == r for r in root_files):
                    flow_lines.append(f'    {rf_id} -->|Imports / Coordinates| {of_id}')
                    break

    diagrams["overview"] = {
        "title": "🏛️ Kiến Trúc Thư Mục & Mô-Đun (Module Overview)",
        "desc": f"Sơ đồ phân cấp cấu trúc mô-đun chính của dự án {root_name}",
        "code": "\n".join(flow_lines)
    }

    # --- SƠ ĐỒ 2: NẾU LÀ PYTHON VÀ CÓ AST ---
    if ast_data and (ast_data["classes"] or ast_data["functions"]):
        ast_lines = [
            "%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ede9fe', 'primaryBorderColor': '#7c3aed', 'primaryTextColor': '#0f172a', 'secondaryColor': '#dcfce7', 'secondaryBorderColor': '#16a34a', 'secondaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%",
            "flowchart TD"
        ]

        class_node_map = {}
        for cname, cinfo in list(ast_data["classes"].items())[:15]:
            cid = f"CLS_{abs(hash(cname)) % 10000}"
            class_node_map[cname] = cid
            methods_txt = "<br/>• ".join(cinfo["methods"][:4])
            if methods_txt:
                methods_txt = "<br/>• " + methods_txt
            ast_lines.append(f'    {cid}["🏛️ class <b>{cname}</b><br/><i>({cinfo["file"]})</i>{methods_txt}"]')

        for fname, finfo in list(ast_data["functions"].items())[:10]:
            fid = f"FN_{abs(hash(fname)) % 10000}"
            class_node_map[fname] = fid
            ast_lines.append(f'    {fid}["⚙️ def <b>{fname}()</b><br/><i>({finfo["file"]})</i>"]')

        added = set()
        for call in ast_data["calls"]:
            tgt = call["target"]
            if tgt in class_node_map:
                for src_name, src_info in ast_data["classes"].items():
                    if src_info["file"] == call["caller_file"] and src_name != tgt:
                        pair = (src_name, tgt)
                        if pair not in added:
                            added.add(pair)
                            ast_lines.append(f'    {class_node_map[src_name]} -->|Calls/Uses| {class_node_map[tgt]}')

        diagrams["ast_live"] = {
            "title": "🔍 Sơ Đồ Code & Quan Hệ Hàm (Live AST)",
            "desc": "Trích xuất tự động các Class, Function và mối quan hệ thực tế trong mã nguồn",
            "code": "\n".join(ast_lines)
        }

    # --- SƠ ĐỒ 3: LUỒNG DỮ LIỆU MẪU (DATA PIPELINE) ---
    diagrams["pipeline"] = {
        "title": "🔄 Luồng Dữ Liệu & Xử Lý (Data Flow / Pipeline)",
        "desc": "Mô tả chu trình tiếp nhận dữ liệu đầu vào, xử lý qua các tầng và xuất kết quả",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#dcfce7', 'primaryBorderColor': '#16a34a', 'primaryTextColor': '#0f172a', 'secondaryColor': '#fef9c3', 'secondaryBorderColor': '#ca8a04', 'secondaryTextColor': '#0f172a', 'tertiaryColor': '#fee2e2', 'tertiaryBorderColor': '#dc2626', 'tertiaryTextColor': '#0f172a', 'lineColor': '#334155', 'fontSize': '15px' }, 'look': 'handDrawn'}}%%
flowchart LR
    INPUT["📥 Dữ liệu đầu vào<br/>(Input Data / Request)"] --> AUTH{"🔐 Kiểm tra & Xác thực"}
    
    AUTH -->|Hợp lệ| PROCESS["⚙️ Xử lý Logic cốt lõi<br/>(Core Processing Engine)"]
    AUTH -->|Không hợp lệ| ERR["❌ Báo lỗi & Ghi log"]

    PROCESS --> ENHANCE["✨ Tối ưu & Tinh chỉnh dữ liệu"]
    ENHANCE --> STORE[("💾 Lưu trữ kết quả<br/>(Database / File Storage)")]
    STORE --> OUTPUT["📤 Xuất kết quả<br/>(Response / Export File)"]
"""
    }

    # --- SƠ ĐỒ 4: SƠ ĐỒ TUẦN TỰ (SEQUENCE / CALL FLOW) ---
    diagrams["sequence"] = {
        "title": "⏱️ Sơ Đồ Tuần Tự (Sequence Diagram)",
        "desc": "Luồng trao đổi thông điệp tuần tự giữa Client, Presenter/Controller và Service/Database",
        "code": """%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#fee2e2', 'primaryBorderColor': '#dc2626', 'primaryTextColor': '#0f172a', 'secondaryColor': '#e0f2fe', 'secondaryBorderColor': '#0284c7', 'lineColor': '#334155', 'fontSize': '14px' }, 'look': 'handDrawn'}}%%
sequenceDiagram
    autonumber
    actor User as 👤 Người Dùng
    participant UI as 🖥️ Giao Diện (UI / View)
    participant Core as ⚙️ Bộ Xử Lý (Core Engine)
    participant Storage as 💾 Lưu Trữ (Disk / DB)

    User->>UI: 1. Thao tác / Gửi yêu cầu
    UI->>Core: 2. Kích hoạt xử lý với tham số
    Core->>Storage: 3. Đọc dữ liệu gốc
    Storage-->>Core: 4. Trả về luồng dữ liệu
    Core->>Core: 5. Thực hiện tính toán & biến đổi
    Core->>Storage: 6. Ghi dữ liệu đã xử lý
    Core-->>UI: 7. Cập nhật tiến độ & hoàn tất
    UI-->>User: 8. Hiển thị thông báo thành công
"""
    }

    return diagrams


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Excali-Flow Architecture Visualizer</title>
  
  <!-- Google Fonts: Hand-drawn & Modern UI -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Caveat:wght@600;700&family=Inter:wght@400;500;600;700&family=Shantell+Sans:ital,wght@0,400..700;1,400..700&family=Virgil&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
  
  <!-- Mermaid.js v11 with Rough.js Hand-drawn Engine -->
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  <!-- Panzoom for smooth canvas zooming and panning (v4.5.1) -->
  <script src="https://cdn.jsdelivr.net/npm/@panzoom/panzoom@4.5.1/dist/panzoom.min.js"></script>

  <style>
    :root {
      --bg-canvas: #f8f9fa;
      --bg-panel: #ffffff;
      --border-color: #e2e8f0;
      --text-main: #1e293b;
      --text-muted: #64748b;
      --primary: #4f46e5;
      --primary-hover: #4338ca;
      --accent: #f59e0b;
      --font-hand: 'Shantell Sans', 'Caveat', 'Virgil', cursive, sans-serif;
      --font-ui: 'Inter', system-ui, -apple-system, sans-serif;
      --font-code: 'Fira Code', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: var(--font-ui);
      background-color: var(--bg-canvas);
      color: var(--text-main);
      display: flex;
      height: 100vh;
      width: 100vw;
      overflow: hidden;
    }

    #sidebar {
      width: 460px;
      min-width: 460px;
      max-width: 460px;
      background: var(--bg-panel);
      border-right: 2px solid var(--border-color);
      display: flex;
      flex-direction: column;
      box-shadow: 4px 0 15px rgba(0,0,0,0.03);
      z-index: 10;
      margin-left: 0;
      opacity: 1;
      pointer-events: auto;
      transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease;
    }

    #sidebar.collapsed {
      margin-left: -460px;
      opacity: 0;
      pointer-events: none;
    }

    .header-bar {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #fafafa;
    }

    .header-title {
      font-family: var(--font-hand);
      font-size: 1.4rem;
      font-weight: 700;
      color: #0f172a;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .badge {
      font-family: var(--font-ui);
      font-size: 0.7rem;
      font-weight: 600;
      background: #e0e7ff;
      color: #3730a3;
      padding: 2px 8px;
      border-radius: 12px;
      text-transform: uppercase;
    }

    .icon-btn {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.9rem;
      color: var(--text-muted);
      transition: all 0.15s ease;
    }

    .icon-btn:hover {
      background: #e2e8f0;
      color: var(--text-main);
    }

    .tabs-nav {
      display: flex;
      padding: 8px 12px 0 12px;
      gap: 6px;
      border-bottom: 1px solid var(--border-color);
      background: #f8fafc;
      overflow-x: auto;
    }

    .tab-btn {
      padding: 8px 14px;
      font-size: 0.85rem;
      font-weight: 600;
      background: transparent;
      border: 1px solid transparent;
      border-bottom: none;
      border-radius: 8px 8px 0 0;
      color: var(--text-muted);
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }

    .tab-btn:hover {
      color: var(--text-main);
      background: #e2e8f0;
    }

    .tab-btn.active {
      background: var(--bg-panel);
      color: var(--primary);
      border-color: var(--border-color);
      border-bottom: 1px solid var(--bg-panel);
      margin-bottom: -1px;
    }

    .editor-section {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 16px;
      gap: 10px;
      min-height: 0;
    }

    .editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .editor-desc {
      font-size: 0.82rem;
      color: var(--text-muted);
      line-height: 1.4;
    }

    #mermaid-code {
      flex: 1;
      width: 100%;
      font-family: var(--font-code);
      font-size: 0.82rem;
      line-height: 1.45;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid var(--border-color);
      background: #0f172a;
      color: #f8fafc;
      resize: none;
      outline: none;
    }

    #mermaid-code:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
    }

    .btn-row {
      display: flex;
      gap: 8px;
    }

    .btn {
      padding: 9px 14px;
      font-size: 0.85rem;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      border: 1px solid var(--border-color);
      background: #ffffff;
      color: var(--text-main);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.15s ease;
    }

    .btn:hover {
      background: #f1f5f9;
      border-color: #cbd5e1;
    }

    .btn-primary {
      background: var(--primary);
      color: #ffffff;
      border-color: var(--primary);
    }

    .btn-primary:hover {
      background: var(--primary-hover);
    }

    #viewport {
      flex: 1;
      position: relative;
      background: 
        radial-gradient(circle, #cbd5e1 1px, transparent 1px);
      background-size: 24px 24px;
      background-color: #fdfbf7; /* Warm Excalidraw paper */
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s ease;
      min-width: 0;
    }

    #panzoom-container {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: grab;
      overflow: hidden;
    }

    #panzoom-container:active {
      cursor: grabbing;
    }

    #diagram-output {
      padding: 40px;
      display: inline-block;
      user-select: none;
      transform-origin: center center;
    }

    .floating-toolbar {
      position: absolute;
      bottom: 24px;
      right: 24px;
      display: flex;
      align-items: center;
      gap: 6px;
      background: #ffffff;
      padding: 6px 12px;
      border-radius: 12px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
      border: 1px solid var(--border-color);
      z-index: 20;
    }

    .tool-btn {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: transparent;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 1.05rem;
      color: var(--text-main);
      transition: background 0.15s;
    }

    .tool-btn:hover {
      background: #f1f5f9;
    }

    .zoom-badge {
      font-family: var(--font-ui);
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--text-muted);
      background: #f1f5f9;
      padding: 4px 8px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      min-width: 48px;
      user-select: none;
    }

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

    .toggle-sidebar-btn:hover {
      background: #f8fafc;
      box-shadow: 0 6px 12px -2px rgba(0,0,0,0.12);
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

    .mermaid text {
      font-family: var(--font-hand) !important;
      font-size: 15px !important;
      letter-spacing: 0.2px;
    }

    .error-box {
      background: #fee2e2;
      border: 1px solid #ef4444;
      color: #991b1b;
      padding: 12px;
      border-radius: 8px;
      font-size: 0.85rem;
      display: none;
    }
  </style>
</head>
<body>

  <aside id="sidebar">
    <div class="header-bar">
      <div class="header-title">
        <span>🎨 Excali-Flow</span>
        <span class="badge">Hand-Drawn</span>
      </div>
      <button id="btn-collapse-sidebar" class="icon-btn" title="Thu gọn Sidebar (Ctrl+B)">◀</button>
    </div>

    <nav class="tabs-nav" id="tabs-container"></nav>

    <div class="editor-section">
      <div class="editor-header">
        <div class="editor-desc" id="tab-desc">Mô tả sơ đồ</div>
      </div>

      <textarea id="mermaid-code" spellcheck="false" placeholder="Nhập mã Mermaid tại đây..."></textarea>
      
      <div id="error-msg" class="error-box"></div>

      <div class="btn-row">
        <button id="btn-render" class="btn btn-primary" style="flex: 2;">
          <span>⚡ Cập Nhật Sơ Đồ</span>
        </button>
        <button id="btn-copy" class="btn" style="flex: 1;">
          <span>📋 Sao Chép</span>
        </button>
      </div>
    </div>
  </aside>

  <button id="toggle-sidebar" class="toggle-sidebar-btn" title="Mở bảng điều khiển (Ctrl+B)">
    <span>✏️</span> <span>Mở Bảng Điều Khiển</span>
  </button>

  <main id="viewport">
    <div id="panzoom-container">
      <div id="diagram-output" class="mermaid"></div>
    </div>

    <div class="floating-toolbar">
      <button id="zoom-in" class="tool-btn" title="Phóng to (Zoom In)">➕</button>
      <button id="zoom-out" class="tool-btn" title="Thu nhỏ (Zoom Out)">➖</button>
      <button id="zoom-reset" class="tool-btn" title="Về mặc định (Reset)">🎯</button>
      <button id="zoom-fit" class="tool-btn" title="Vừa khung hình (Fit to Screen)">📐</button>
      <span id="zoom-badge" class="zoom-badge">100%</span>
      <div style="width: 1px; height: 24px; background: var(--border-color); margin: 0 4px;"></div>
      <button id="export-svg" class="tool-btn" title="Tải file Vector SVG">🖼️ SVG</button>
      <button id="export-png" class="tool-btn" title="Tải ảnh PNG độ nét cao">📷 PNG</button>
    </div>
  </main>

  <script>
    const diagrams = __DIAGRAMS_DATA__;

    let currentTab = Object.keys(diagrams)[0];
    let panzoomInstance = null;

    mermaid.initialize({
      startOnLoad: false,
      look: 'handDrawn',
      theme: 'base',
      fontFamily: '"Shantell Sans", "Caveat", "Virgil", cursive, sans-serif',
      themeVariables: {
        fontFamily: '"Shantell Sans", "Caveat", "Virgil", cursive, sans-serif',
        fontSize: '15px',
        primaryColor: '#e0f2fe',
        primaryBorderColor: '#0284c7',
        primaryTextColor: '#0f172a',
        secondaryColor: '#fef3c7',
        secondaryBorderColor: '#d97706',
        secondaryTextColor: '#0f172a',
        tertiaryColor: '#f3e8ff',
        tertiaryBorderColor: '#9333ea',
        tertiaryTextColor: '#0f172a',
        lineColor: '#334155',
        edgeLabelBackground: '#ffffff'
      }
    });

    const codeArea = document.getElementById('mermaid-code');
    const descArea = document.getElementById('tab-desc');
    const tabsContainer = document.getElementById('tabs-container');
    const diagramOutput = document.getElementById('diagram-output');
    const panzoomContainer = document.getElementById('panzoom-container');
    const zoomBadge = document.getElementById('zoom-badge');
    const errorBox = document.getElementById('error-msg');

    function setupTabs() {
      tabsContainer.innerHTML = '';
      Object.keys(diagrams).forEach(key => {
        const btn = document.createElement('button');
        btn.className = `tab-btn ${key === currentTab ? 'active' : ''}`;
        btn.textContent = diagrams[key].title.split('(')[0].trim();
        btn.onclick = () => selectTab(key);
        tabsContainer.appendChild(btn);
      });
    }

    function selectTab(key) {
      currentTab = key;
      setupTabs();
      descArea.textContent = diagrams[key].desc;
      codeArea.value = diagrams[key].code.trim();
      renderDiagram();
    }

    function updateZoomBadge(scale) {
      if (zoomBadge) {
        zoomBadge.textContent = `${Math.round((scale || 1) * 100)}%`;
      }
    }

    function fitToScreen() {
      if (!panzoomInstance) return;
      const svg = diagramOutput.querySelector('svg');
      if (!svg) {
        panzoomInstance.reset();
        updateZoomBadge(panzoomInstance.getScale());
        return;
      }

      const containerRect = panzoomContainer.getBoundingClientRect();
      const svgRect = svg.getBoundingClientRect();

      const svgWidth = svg.viewBox?.baseVal?.width || svgRect.width || 800;
      const svgHeight = svg.viewBox?.baseVal?.height || svgRect.height || 600;

      const padding = 80;
      const availableWidth = Math.max(containerRect.width - padding * 2, 200);
      const availableHeight = Math.max(containerRect.height - padding * 2, 200);

      const scaleX = availableWidth / svgWidth;
      const scaleY = availableHeight / svgHeight;
      let targetScale = Math.min(scaleX, scaleY, 1.2);
      if (targetScale < 0.2) targetScale = 0.2;

      panzoomInstance.zoom(targetScale, { animate: true });
      panzoomInstance.pan(0, 0, { animate: true });
      updateZoomBadge(targetScale);
    }

    // Attach wheel event on container once to avoid memory leaks
    panzoomContainer.addEventListener('wheel', (event) => {
      if (!panzoomInstance) return;
      panzoomInstance.zoomWithWheel(event);
    }, { passive: false });

    // Gắn panzoomchange trên diagramOutput một lần duy nhất tránh tích lũy listener
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

    function toggleSidebar() {
      const sidebar = document.getElementById('sidebar');
      sidebar.classList.toggle('collapsed');
    }

    document.getElementById('btn-render').onclick = renderDiagram;
    
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

    document.getElementById('toggle-sidebar').onclick = toggleSidebar;
    
    const btnCollapse = document.getElementById('btn-collapse-sidebar');
    if (btnCollapse) {
      btnCollapse.onclick = toggleSidebar;
    }

    window.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        toggleSidebar();
      }
    });

    document.getElementById('zoom-in').onclick = () => panzoomInstance && panzoomInstance.zoomIn();
    document.getElementById('zoom-out').onclick = () => panzoomInstance && panzoomInstance.zoomOut();
    document.getElementById('zoom-reset').onclick = () => {
      if (panzoomInstance) {
        panzoomInstance.reset();
        updateZoomBadge(panzoomInstance.getScale());
      }
    };
    document.getElementById('zoom-fit').onclick = fitToScreen;

    document.getElementById('export-svg').onclick = () => {
      const svgElement = diagramOutput.querySelector('svg');
      if (!svgElement) return alert('Chưa có sơ đồ để xuất!');
      
      const svgData = new XMLSerializer().serializeToString(svgElement);
      const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `architecture-${currentTab}.svg`;
      a.click();
      URL.revokeObjectURL(url);
    };

    document.getElementById('export-png').onclick = () => {
      const svgElement = diagramOutput.querySelector('svg');
      if (!svgElement) return alert('Chưa có sơ đồ để xuất!');

      const svgData = new XMLSerializer().serializeToString(svgElement);
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();

      const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(svgBlob);

      img.onload = () => {
        const scale = 2;
        const box = svgElement.viewBox?.baseVal;
        const w = (box && box.width) ? box.width : (svgElement.clientWidth || 1200);
        const h = (box && box.height) ? box.height : (svgElement.clientHeight || 800);
        
        canvas.width = w * scale;
        canvas.height = h * scale;
        
        ctx.fillStyle = '#fdfbf7';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        const pngUrl = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.href = pngUrl;
        a.download = `architecture-${currentTab}.png`;
        a.click();
        URL.revokeObjectURL(url);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        alert('Không thể xuất ảnh PNG từ SVG!');
      };
      img.src = url;
    };

    window.addEventListener('DOMContentLoaded', () => {
      selectTab(currentTab);
    });
  </script>
</body>
</html>
"""

def generate_html_file(project_dir: str = ".", output_path: str = "architecture_viewer.html"):
    """Sinh file HTML Excalidraw Viewer chứa dữ liệu Mermaid từ dự án chỉ định"""
    proj_path = Path(project_dir).resolve()
    
    # 1. Kiểm tra xem có Đồ thị tri thức (Graphify hoặc Understand-Anything) hay không
    kg_type, kg_path = find_knowledge_graph(proj_path)
    
    diagrams = {}
    if kg_type == "graphify":
        print(f"[*] Phat hien Knowledge Graph tu Graphify: {kg_path}")
        gdata = parse_graphify_graph(kg_path)
        if gdata:
            diagrams = generate_mermaid_from_graphify(gdata, proj_path.name)
            
    elif kg_type == "understand":
        print(f"[*] Phat hien Knowledge Graph tu Understand-Anything: {kg_path}")
        udata = parse_understand_graph(kg_path)
        if udata:
            diagrams = generate_mermaid_from_understand(udata, proj_path.name)

    # 2. Nếu không tìm thấy hoặc trích xuất không thành công, fallback về quét AST & Folder Tree
    if not diagrams:
        print("[*] Quet cau truc thu muc va AST ma nguon...")
        project_info = scan_project_structure(proj_path)
        ast_data = None
        if project_info["is_python"]:
            try:
                ast_data = scan_python_ast(proj_path)
            except Exception as e:
                print(f"[!] AST Notice: {e}")
        diagrams = generate_mermaid_from_project(project_info, ast_data)

    diagrams_json = json.dumps(diagrams, ensure_ascii=False, indent=2)
    # Tránh làm vỡ thẻ script khi trong label hoặc code Mermaid chứa chuỗi </script>
    diagrams_json = diagrams_json.replace("</script>", "<\\/script>").replace("</SCRIPT>", "<\\/SCRIPT>")
    html_content = HTML_TEMPLATE.replace("__DIAGRAMS_DATA__", diagrams_json)
    
    out_file = Path(output_path)
    if not out_file.is_absolute():
        out_file = proj_path / out_file
        
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html_content, encoding="utf-8")
    print(f"[*] Da tao thanh cong file giao dien: {out_file.resolve()}")
    return out_file.resolve()


def install_git_hooks(project_dir: str = "."):
    """Cài đặt Git Pre-commit và Post-commit Hooks cho dự án"""
    proj_path = Path(project_dir).resolve()
    hooks_dir = proj_path / ".git" / "hooks"
    if not hooks_dir.exists():
        print(f"[!] Khong tim thay thu muc {hooks_dir}. Hay dam bao ban dang o trong git repository.")
        return

    post_commit = hooks_dir / "post-commit"
    post_commit.write_text("#!/bin/sh\npython generate_architecture_diagram.py\n", encoding="utf-8")
    
    pre_commit = hooks_dir / "pre-commit"
    pre_commit.write_text("#!/bin/sh\npython generate_architecture_diagram.py\ngit add architecture_viewer.html\n", encoding="utf-8")

    print(f"[*] Da cai dat thanh cong Git Hooks tai {hooks_dir}")


def watch_mode(project_dir: str = ".", interval: float = 1.5):
    """Lắng nghe thay đổi file và tự động build lại"""
    proj_path = Path(project_dir).resolve()
    print(f"[*] Che do Watch Mode dang hoat dong tai {proj_path}... Nhan Ctrl+C de dung.")
    last_mtimes = {}

    def get_file_mtimes():
        mtimes = {}
        for p in proj_path.rglob("*"):
            if any(part.startswith('.') or part in {'__pycache__', 'node_modules', 'dist', 'build'} for part in p.parts):
                continue
            if p.is_file():
                try:
                    mtimes[str(p)] = p.stat().st_mtime
                except Exception:
                    pass
        return mtimes

    last_mtimes = get_file_mtimes()
    generate_html_file(str(proj_path))

    while True:
        try:
            time.sleep(interval)
            current_mtimes = get_file_mtimes()
            if current_mtimes != last_mtimes:
                print(f"[*] Phat hien thay doi file lúc {time.strftime('%H:%M:%S')}. Dang cap nhat so do...")
                generate_html_file(str(proj_path))
                last_mtimes = current_mtimes
        except KeyboardInterrupt:
            print("\n[*] Da dung Watch Mode.")
            break


def main():
    parser = argparse.ArgumentParser(description="Excali-Flow: Universal Architecture & Diagram Generator.")
    parser.add_argument("target", nargs="?", default=None, help="Thu muc du an can quet (mac dinh: .)")
    parser.add_argument("-d", "--dir", default=None, help="Thu muc du an can quet (mac dinh: .)")
    parser.add_argument("-o", "--out", default="architecture_viewer.html", help="Duong dan file HTML dau ra")
    parser.add_argument("--open", action="store_true", help="Tu dong mo trinh duyet sau khi tao")
    parser.add_argument("--install-hook", action="store_true", help="Cai dat Git Hooks cho du an")
    parser.add_argument("--watch", action="store_true", help="Tu dong lang nghe thay doi file va render lai")
    args = parser.parse_args()

    target_dir = args.dir or args.target or "."
    out_path = args.out

    if args.install_hook:
        install_git_hooks(target_dir)
        return

    if args.watch:
        watch_mode(target_dir)
        return

    full_path = generate_html_file(target_dir, out_path)

    if args.open:
        print("[*] Dang mo tren trinh duyet...")
        webbrowser.open(f"file:///{full_path}")


if __name__ == "__main__":
    main()
