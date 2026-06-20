from typing import List
from .case_models import Case, EvidenceItem

def generate_next_actions(case: Case, evidence_items: List[EvidenceItem]) -> List[str]:
    actions = []
    case_ev = [e for e in evidence_items if e.case_id == case.case_id]
    
    if not case_ev:
        actions.append("Thêm ít nhất một nguồn bằng chứng.")
        
    has_screenshot = any(e.source_type in ["screenshot", "image"] for e in case_ev)
    if has_screenshot:
        # Check if any screenshot lacks description
        if any(e.source_type in ["screenshot", "image"] and not e.extracted_text and not e.structured_summary for e in case_ev):
            actions.append("Mô tả nội dung ảnh chụp màn hình.")
            
    has_excel = any(e.source_type in ["excel", "csv"] for e in case_ev)
    if has_excel:
        actions.append("Xem xét các hàng/cột bất thường trong bảng dữ liệu.")
        
    has_log = any(e.source_type in ["chat_paste", "log_paste"] for e in case_ev)
    if has_log:
        actions.append("Trích xuất các quyết định/hành động từ tin nhắn hoặc nhật ký (chat/log).")
        
    if not case.hypotheses:
        actions.append("Tạo giả thuyết đầu tiên.")
        
    if case.status not in ["resolved", "archived"]:
        actions.append("Chuẩn bị gói câu lệnh (prompt) cho AI để điều tra sự việc.")
        
    return actions
