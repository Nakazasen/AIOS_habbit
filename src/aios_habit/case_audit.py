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
        errors.append("Active case does not exist or is not selected.")
        return {
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings
        }
        
    # 2. active case has non-empty title
    if not case.title or not case.title.strip():
        errors.append("Active case has an empty title.")
        
    # 3. active case has non-empty current_situation
    if not case.current_situation or not case.current_situation.strip():
        errors.append("Active case has an empty current situation.")
        
    # Let's resolve the expected local cases assets folder path
    cwd = Path.cwd().resolve()
    assets_dir = (cwd / "local_cases" / "assets").resolve()
    
    # Check evidence items
    for ev in evidence_items:
        # 4. every evidence item has case_id
        if not ev.case_id or not ev.case_id.strip():
            errors.append(f"Evidence item {ev.evidence_id} has no case_id.")
            
        # 5. every evidence item has source_type
        if not ev.source_type or not ev.source_type.strip():
            errors.append(f"Evidence item {ev.evidence_id} has no source_type.")
            
        # 6. every evidence item has privacy_level
        if not ev.privacy_level or not ev.privacy_level.strip():
            errors.append(f"Evidence item {ev.evidence_id} has no privacy_level.")
            
        # 9. no evidence item has empty title and empty extracted_text at the same time
        has_title = bool(ev.title and ev.title.strip())
        has_text = bool(ev.extracted_text and ev.extracted_text.strip())
        if not has_title and not has_text:
            errors.append(f"Evidence item {ev.evidence_id} has both empty title and empty extracted_text.")
            
        # 8. uploaded asset path, if present, stays under local_cases/assets
        if ev.source_path and ev.source_path not in ("clipboard", "manual"):
            try:
                p = Path(ev.source_path).resolve()
                if not str(p).startswith(str(assets_dir)):
                    errors.append(f"Evidence item {ev.evidence_id} asset path '{ev.source_path}' is outside assets directory '{assets_dir}'.")
            except Exception as e:
                errors.append(f"Evidence item {ev.evidence_id} has invalid asset path: {e}")
                
        # 7. local_only evidence is excluded from notebooklm_safe/gemini/gpt/copilot prompt outputs by default
        if ev.privacy_level == "local_only" and prompt_outputs:
            for target, prompt_text in prompt_outputs.items():
                if target.lower() in ("notebooklm_safe", "gemini", "gpt", "copilot"):
                    if has_text and ev.extracted_text in prompt_text:
                        errors.append(f"local_only evidence '{ev.evidence_id}' raw extracted_text was leaked in target '{target}'.")

    status = "FAIL" if errors else "PASS"
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings
    }
