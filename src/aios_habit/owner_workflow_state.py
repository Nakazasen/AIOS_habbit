from enum import Enum

class WorkflowState(Enum):
    START = "START"
    ISSUE_ENTERED = "ISSUE_ENTERED"
    EVIDENCE_ADDED = "EVIDENCE_ADDED"
    READY_TO_ANALYZE = "READY_TO_ANALYZE"
    ANALYZED = "ANALYZED"
    ANSWER_READY = "ANSWER_READY"
    CASE_SAVED = "CASE_SAVED"
    BLOCKED_MISSING_ISSUE = "BLOCKED_MISSING_ISSUE"
    BLOCKED_MISSING_EVIDENCE = "BLOCKED_MISSING_EVIDENCE"
    BLOCKED_UNSAFE_PRIVACY = "BLOCKED_UNSAFE_PRIVACY"

def evaluate_owner_workflow_state(
    issue_text: str, 
    evidence_count: int, 
    has_analysis: bool = False, 
    has_answer: bool = False, 
    is_saved: bool = False,
    is_local_only: bool = True,
    requested_cloud_action: bool = False
) -> WorkflowState:
    
    if requested_cloud_action and is_local_only:
        return WorkflowState.BLOCKED_UNSAFE_PRIVACY
        
    has_issue = bool(issue_text and issue_text.strip())
    
    if not has_issue and evidence_count == 0:
        return WorkflowState.START
        
    if not has_issue and evidence_count > 0:
        return WorkflowState.BLOCKED_MISSING_ISSUE
        
    if has_issue and evidence_count == 0:
        return WorkflowState.ISSUE_ENTERED
        
    # has_issue and evidence_count > 0
    if is_saved:
        return WorkflowState.CASE_SAVED
    
    if has_answer:
        return WorkflowState.ANSWER_READY
        
    if has_analysis:
        return WorkflowState.ANALYZED
        
    return WorkflowState.READY_TO_ANALYZE

def get_next_required_action(state: WorkflowState) -> str:
    if state == WorkflowState.START:
        return "Nhập vấn đề đang gặp và tải lên bằng chứng."
    if state == WorkflowState.ISSUE_ENTERED or state == WorkflowState.BLOCKED_MISSING_EVIDENCE:
        return "Tải lên tài liệu, ảnh, log hoặc dán nội dung để làm bằng chứng."
    if state == WorkflowState.BLOCKED_MISSING_ISSUE:
        return "Mô tả vấn đề đang gặp."
    if state == WorkflowState.READY_TO_ANALYZE:
        return "Phân tích và tạo hồ sơ."
    if state == WorkflowState.ANALYZED:
        return "Xem kết quả phân tích hoặc hỏi AI."
    if state == WorkflowState.ANSWER_READY:
        return "Lưu kết quả."
    return "Không có hành động bắt buộc."

def can_analyze(state: WorkflowState) -> bool:
    return state in [WorkflowState.READY_TO_ANALYZE, WorkflowState.ANALYZED, WorkflowState.ANSWER_READY, WorkflowState.CASE_SAVED]

def can_generate_ai_answer(state: WorkflowState) -> bool:
    return state in [WorkflowState.ANALYZED, WorkflowState.ANSWER_READY, WorkflowState.CASE_SAVED]

def can_create_full_bundle(state: WorkflowState) -> bool:
    return state in [WorkflowState.ANALYZED, WorkflowState.ANSWER_READY, WorkflowState.CASE_SAVED]

def build_owner_friendly_blocking_message(state: WorkflowState, context: str = "") -> str:
    if state == WorkflowState.START and context == "analyze":
        return "Cần mô tả vấn đề trước. Chỉ cần 1-2 câu."

    if state == WorkflowState.BLOCKED_MISSING_ISSUE:
        return "Cần mô tả vấn đề trước. Chỉ cần 1–2 câu."
    
    if state == WorkflowState.BLOCKED_MISSING_EVIDENCE or (state == WorkflowState.ISSUE_ENTERED and context == "analyze"):
        return "Cần thêm ít nhất một tài liệu, ảnh, log, hoặc nội dung chat/email để AIOS có bằng chứng."
        
    if state in [WorkflowState.START, WorkflowState.ISSUE_ENTERED] and context == "answer":
        return "Chưa có bằng chứng nên AIOS không trả lời như kết luận. Hãy thêm tài liệu/ảnh/log trước."
        
    if state in [WorkflowState.START, WorkflowState.ISSUE_ENTERED] and context == "bundle":
        return "Chưa có bằng chứng để đóng gói."
        
    if state == WorkflowState.BLOCKED_UNSAFE_PRIVACY:
        return "Dữ liệu đang ở chế độ chỉ xử lý cục bộ. AIOS không tự gửi cloud."
        
    return ""
