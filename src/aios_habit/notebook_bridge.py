import json
from typing import Optional

def build_notebooklm_bridge_prompt(
    notebook_id: str,
    task_type: str,
    user_question: str = "",
) -> str:
    try:
        from aios_habit.workspace_models import load_notebooks
        nbs = {n.notebook_id: n.name for n in load_notebooks()}
        nb_name = nbs.get(notebook_id, notebook_id)
    except Exception:
        nb_name = notebook_id
        
    intro = (
        f"Tôi đang làm việc với Sổ tri thức (Notebook): '{nb_name}'.\n"
        "Lưu ý: Bạn đã được upload toàn bộ tài liệu nguồn liên quan cho Sổ tri thức này trước đó. "
        "Hãy chỉ trả lời dựa trên những nguồn đã được upload này. Tuyệt đối không tự bịa đặt câu trả lời nếu không tìm thấy bằng chứng.\n\n"
    )
    
    if task_type == "knowledge_graph_json":
        prompt = intro + (
            "Yêu cầu: Hãy trích xuất đồ thị tri thức (Knowledge Graph) từ tài liệu nguồn dưới dạng JSON hợp lệ theo đúng cấu trúc sau:\n"
            "{\n"
            '  "nodes": [\n'
            "    {\n"
            '      "id": "stable_id",\n'
            '      "label": "Tên khái niệm",\n'
            '      "type": "system|process|setting|table|screen|role|error|cause|action|document|case",\n'
            '      "description": "Mô tả ngắn",\n'
            '      "source_ref": "Tên nguồn hoặc citation từ NotebookLM",\n'
            '      "confidence": "low|medium|high"\n'
            "    }\n"
            "  ],\n"
            '  "edges": [\n'
            "    {\n"
            '      "from": "node_id",\n'
            '      "to": "node_id",\n'
            '      "relation": "depends_on|initializes|checks|causes|mitigates|belongs_to|references|updates",\n'
            '      "description": "Mô tả quan hệ",\n'
            '      "source_ref": "Tên nguồn hoặc citation từ NotebookLM",\n'
            '      "confidence": "low|medium|high"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Yêu cầu nghiêm ngặt:\n"
            "- Trả về JSON hợp lệ.\n"
            "- Mỗi node và edge bắt buộc phải đi kèm trường 'source_ref' trích dẫn từ nguồn tài liệu.\n"
            "- Không thêm bất kỳ văn bản giải thích hoặc định dạng markdown nào ở ngoài khối JSON."
        )
    elif task_type == "study_pack_json":
        prompt = intro + (
            "Yêu cầu: Hãy tạo một Study Pack ôn tập chi tiết dưới dạng JSON hợp lệ theo cấu trúc sau:\n"
            "{\n"
            '  "summary": "Tóm tắt ngắn gọn nội dung cốt lõi",\n'
            '  "glossary": [\n'
            "    {\n"
            '      "term": "Thuật ngữ",\n'
            '      "meaning": "Ý nghĩa định nghĩa",\n'
            '      "source_ref": "Nguồn"\n'
            "    }\n"
            "  ],\n"
            '  "flashcards": [\n'
            "    {\n"
            '      "front": "Câu hỏi ôn tập mặt trước",\n'
            '      "back": "Câu trả lời ngắn mặt sau",\n'
            '      "source_ref": "Nguồn"\n'
            "    }\n"
            "  ],\n"
            '  "review_questions": [\n'
            "    {\n"
            '      "question": "Câu hỏi kiểm tra rộng",\n'
            '      "expected_answer": "Đáp án chuẩn mong đợi",\n'
            '      "source_ref": "Nguồn"\n'
            "    }\n"
            "  ],\n"
            '  "unknowns": [\n'
            '    "Điểm chưa đủ dữ liệu hoặc cần làm rõ thêm"\n'
            "  ]\n"
            "}\n\n"
            "Yêu cầu nghiêm ngặt:\n"
            "- Trả về JSON hợp lệ.\n"
            "- Mỗi mục phải đi kèm trường 'source_ref'.\n"
            "- Không thêm bất kỳ văn bản giải thích hoặc định dạng markdown nào ở ngoài khối JSON."
        )
    elif task_type == "case_investigation_json":
        prompt = intro + (
            f"Câu hỏi/Tình huống cần điều tra: {user_question if user_question else 'Phân tích tổng hợp sự việc.'}\n\n"
            "Yêu cầu: Hãy phân tích bối cảnh và trích xuất thông tin điều tra dưới dạng JSON hợp lệ theo cấu trúc sau:\n"
            "{\n"
            '  "symptoms": ["Triệu chứng lỗi phát hiện"],\n'
            '  "hypotheses": ["Các giả thuyết nguyên nhân"],\n'
            '  "evidence_to_check": ["Các bằng chứng/tham số cần kiểm tra thêm"],\n'
            '  "do_not_conclude_yet": ["Các điểm chưa thể kết luận vội"],\n'
            '  "first_checks_next_time": ["Các điểm cần ưu tiên check trước trong lần tới"],\n'
            '  "draft_reply_vi": "Bản thảo giải đáp tiếng Việt",\n'
            '  "draft_reply_ja": "Bản thảo giải đáp tiếng Nhật"\n'
            "}\n\n"
            "Yêu cầu nghiêm ngặt:\n"
            "- Trả về JSON hợp lệ.\n"
            "- Không thêm bất kỳ văn bản giải thích hoặc định dạng markdown nào ở ngoài khối JSON."
        )
    elif task_type == "mermaid_graph":
        prompt = intro + (
            "Yêu cầu: Hãy tạo sơ đồ quan hệ Mermaid (Mermaid Graph) dạng 'graph TD' biểu diễn cấu trúc tri thức của tài liệu này.\n"
            "Yêu cầu nghiêm ngặt:\n"
            "- Trả về mã nguồn Mermaid hợp lệ (bắt đầu bằng graph TD).\n"
            "- Tránh các ký tự đặc biệt có thể làm lỗi cú pháp Mermaid như ngoặc vuông [], ngoặc nhọn {} trong nội dung nhãn nút. Trích dẫn nhãn bằng dấu nháy kép.\n"
            "- Chỉ trả về mã nguồn Mermaid, không kèm văn bản giải thích ngoài."
        )
    else:
        prompt = intro + f"Câu hỏi: {user_question}\n"
        
    return prompt

def graph_json_to_mermaid(graph: dict, max_nodes: int = 50) -> str:
    if not graph or not isinstance(graph, dict):
        return "graph TD\n    ERROR[\"Dữ liệu đồ thị không hợp lệ hoặc rỗng\"]"
        
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    
    if not isinstance(nodes, list):
        nodes = []
    if not isinstance(edges, list):
        edges = []
        
    lines = ["graph TD"]
    lines.append("classDef default fill:#4F46E5,stroke:#312E81,stroke-width:2px,color:#FFFFFF;")
    
    node_ids = set()
    added_count = 0
    
    def escape_label(label: str) -> str:
        cleaned = str(label).replace('"', "'").replace('[', '(').replace(']', ')').replace('{', '(').replace('}', ')')
        cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').strip()
        if len(cleaned) > 45:
            cleaned = cleaned[:42] + "..."
        return cleaned

    for node in nodes:
        if not isinstance(node, dict):
            continue
        nid = node.get("id")
        label = node.get("label", nid)
        if not nid:
            continue
            
        nid_clean = "".join(c for c in str(nid) if c.isalnum() or c == "_")
        if not nid_clean:
            continue
            
        if added_count >= max_nodes:
            break
            
        node_ids.add(nid_clean)
        escaped = escape_label(label)
        lines.append(f'    {nid_clean}["{escaped}"]')
        added_count += 1
        
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        from_id = edge.get("from")
        to_id = edge.get("to")
        relation = edge.get("relation", "")
        
        if not from_id or not to_id:
            continue
            
        from_clean = "".join(c for c in str(from_id) if c.isalnum() or c == "_")
        to_clean = "".join(c for c in str(to_id) if c.isalnum() or c == "_")
        
        if from_clean in node_ids and to_clean in node_ids:
            if relation:
                escaped_rel = escape_label(relation)
                lines.append(f'    {from_clean} -->|"{escaped_rel}"| {to_clean}')
            else:
                lines.append(f'    {from_clean} --> {to_clean}')
                
    if len(nodes) > max_nodes:
        lines.append("    %% Đã giới hạn số node để tránh lag.")
        
    return "\n".join(lines)

def clean_code_fences(t: str) -> str:
    t_clean = t.strip()
    if t_clean.startswith("```"):
        lines = t_clean.splitlines()
        if lines:
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            t_clean = "\n".join(lines).strip()
    return t_clean

def detect_bridge_import_type(text: str) -> str:
    clean_text = clean_code_fences(text)
    if clean_text.startswith("graph") or "graph TD" in clean_text or "graph LR" in clean_text:
        return "mermaid_graph"
        
    try:
        data = json.loads(clean_text)
        if not isinstance(data, dict):
            return "unknown"
        if "nodes" in data or "edges" in data:
            return "knowledge_graph_json"
        if "summary" in data or "glossary" in data or "flashcards" in data:
            return "study_pack_json"
        if "symptoms" in data or "hypotheses" in data or "evidence_to_check" in data:
            return "case_investigation_json"
    except Exception:
        pass
        
    return "unknown"

def parse_bridge_import(text: str) -> dict:
    clean_text = clean_code_fences(text)
    t = detect_bridge_import_type(text)
    if t == "mermaid_graph" or t == "unknown":
        return {}
    try:
        data = json.loads(clean_text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}

def summarize_bridge_import(parsed_json: dict, import_type: str) -> dict:
    if not parsed_json:
        return {}
    if import_type == "knowledge_graph_json":
        return {
            "node_count": len(parsed_json.get("nodes", [])),
            "edge_count": len(parsed_json.get("edges", []))
        }
    elif import_type == "study_pack_json":
        return {
            "glossary_count": len(parsed_json.get("glossary", [])),
            "flashcard_count": len(parsed_json.get("flashcards", [])),
            "review_question_count": len(parsed_json.get("review_questions", [])),
            "unknown_count": len(parsed_json.get("unknowns", []))
        }
    elif import_type == "case_investigation_json":
        return {
            "symptom_count": len(parsed_json.get("symptoms", [])),
            "hypothesis_count": len(parsed_json.get("hypotheses", [])),
            "evidence_to_check_count": len(parsed_json.get("evidence_to_check", []))
        }
    return {}

