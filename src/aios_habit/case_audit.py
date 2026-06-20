from pathlib import Path
from typing import List, Dict, Optional, Any
from .case_models import Case, EvidenceItem

def audit_case_cockpit_state(
    case: Optional[Case],
    evidence_items: List[EvidenceItem],
    prompt_outputs: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    errors = []
    warnings = []
    
    # 1. selected/active case exists
    if not case:
        errors.append("Hồ sơ sự việc đang hoạt động không tồn tại hoặc chưa được chọn.")
        return {
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings
        }
        
    # 2. active case has non-empty title
    if not case.title or not case.title.strip():
        errors.append("Hồ sơ sự việc đang hoạt động có tiêu đề bị trống.")
        
    # 3. active case has non-empty current_situation
    if not case.current_situation or not case.current_situation.strip():
        errors.append("Hồ sơ sự việc đang hoạt động có phần tóm tắt tình huống bị trống.")
        
    # Let's resolve the expected local cases assets folder path
    cwd = Path.cwd().resolve()
    assets_dir = (cwd / "local_cases" / "assets").resolve()
    
    # Check evidence items
    for ev in evidence_items:
        # 4. every evidence item has case_id
        if not ev.case_id or not ev.case_id.strip():
            errors.append(f"Bằng chứng {ev.evidence_id} không có case_id.")
            
        # 5. every evidence item has source_type
        if not ev.source_type or not ev.source_type.strip():
            errors.append(f"Bằng chứng {ev.evidence_id} không có source_type.")
            
        # 6. every evidence item has privacy_level
        if not ev.privacy_level or not ev.privacy_level.strip():
            errors.append(f"Bằng chứng {ev.evidence_id} không có privacy_level.")
            
        # 9. no evidence item has empty title and empty extracted_text at the same time
        has_title = bool(ev.title and ev.title.strip())
        has_text = bool(ev.extracted_text and ev.extracted_text.strip())
        if not has_title and not has_text:
            errors.append(f"Bằng chứng {ev.evidence_id} có cả tiêu đề và văn bản trích xuất thô bị trống.")
            
        # 8. uploaded asset path, if present, stays under local_cases/assets
        if ev.source_path and ev.source_path not in ("clipboard", "manual"):
            try:
                p = Path(ev.source_path).resolve()
                if not str(p).startswith(str(assets_dir)):
                    errors.append(f"Bằng chứng {ev.evidence_id} có đường dẫn tệp '{ev.source_path}' nằm ngoài thư mục tài nguyên cục bộ '{assets_dir}'.")
            except Exception as e:
                errors.append(f"Bằng chứng {ev.evidence_id} có đường dẫn tệp không hợp lệ: {e}")
                
        # 7. local_only evidence is excluded from notebooklm_safe/gemini/gpt/copilot prompt outputs by default
        if ev.privacy_level == "local_only" and prompt_outputs:
            for target, prompt_text in prompt_outputs.items():
                if target.lower() in ("notebooklm_safe", "gemini", "gpt", "copilot"):
                    if has_text and ev.extracted_text in prompt_text:
                        errors.append(f"Bằng chứng local_only '{ev.evidence_id}' bị rò rỉ văn bản trích xuất thô trong prompt đích '{target}'.")

    status = "FAIL" if errors else "PASS"
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings
    }
