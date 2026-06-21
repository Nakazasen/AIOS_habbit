from typing import List
from aios_habit.source_ingest import load_sources
from aios_habit.notebook_index import load_chunks
from aios_habit.notebook_import_store import load_bridge_imports
from aios_habit.case_store import load_cases

def suggest_next_actions(workspace_id: str, notebook_id: str) -> List[str]:
    actions = []
    
    if not notebook_id:
        return ["Chọn một Sổ tri thức để bắt đầu."]
        
    # 1. Check sources
    sources = [s for s in load_sources() if s.notebook_id == notebook_id]
    if not sources:
        actions.append("Nạp tài liệu nguồn vào Sổ tri thức.")
        return actions
        
    # 2. Check chunks
    chunks = load_chunks(notebook_id)
    if not chunks:
        actions.append("Bấm Cập nhật chỉ mục.")
        return actions
        
    # 3. Check saved imports
    imports = load_bridge_imports(notebook_id)
    if not imports:
        actions.append("Dùng NotebookLM Bridge để tạo graph/study/case investigation.")
        return actions
        
    # 4. Check case_investigation import exists but no Case draft
    has_case_investigation = any(imp.import_type == "case_investigation_json" for imp in imports)
    cases = [c for c in load_cases() if c.workspace_id == workspace_id]
    has_linked_case = any(notebook_id in getattr(c, "linked_notebook_ids", []) for c in cases)
    if has_case_investigation and not has_linked_case:
        actions.append("Tạo Case nháp từ kết quả điều tra đã lưu.")
        
    # 5. Check graph import exists
    has_graph_import = any(imp.import_type in ("knowledge_graph_json", "mermaid_graph") for imp in imports)
    if has_graph_import:
        actions.append("Xem lại graph trong tab Bản đồ và đánh dấu reviewed/confirmed nếu đúng.")
        
    if not actions:
        actions.append("Tiếp tục nghiên cứu tài liệu nguồn hoặc thảo luận với chuyên gia.")
        
    return actions
