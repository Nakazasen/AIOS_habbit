from typing import List
from .case_models import Case, EvidenceItem

def summarize_evidence_for_prompt(evidence_items: List[EvidenceItem], target: str, include_local_only: bool = False) -> str:
    # Target normalization to lower case to handle user inputs robustly
    target_lower = target.lower()
    
    if target_lower == "notebooklm_safe":
        should_include_local_only = False
    elif target_lower in ("gemini", "gpt", "copilot"):
        should_include_local_only = include_local_only
    elif target_lower == "local_ai":
        should_include_local_only = include_local_only
    else:
        should_include_local_only = False

    lines = []
    excluded_any = False
    for e in evidence_items:
        if e.privacy_level == "local_only":
            if not should_include_local_only:
                excluded_any = True
                lines.append(f"- [{e.source_type}] {e.title}: [ĐÃ LOẠI BỎ VÌ RIÊNG TƯ - local_only]")
                continue
        
        snippet = e.extracted_text[:200] if e.extracted_text else ""
        lines.append(f"- [{e.source_type}] {e.title}: {snippet}...")
    
    summary_text = "\n".join(lines)
    if excluded_any:
        if summary_text:
            summary_text += "\n"
        summary_text += "Một số bằng chứng local_only (chỉ lưu cục bộ) đã bị loại bỏ vì lý do riêng tư."
    return summary_text

def build_prompt_pack(case: Case, evidence_items: List[EvidenceItem], target: str, include_local_only: bool = False) -> str:
    prompt = f"Tiêu đề Hồ sơ: {case.title}\n"
    prompt += f"Tình huống Hiện tại: {case.current_situation}\n\n"
    prompt += "Tóm tắt Bằng chứng:\n"
    prompt += summarize_evidence_for_prompt(evidence_items, target, include_local_only)
    
    prompt += "\n\nGiả thuyết:\n"
    for h in case.hypotheses:
        prompt += f"- {h}\n"
        
    prompt += "\nKết quả yêu cầu: Vui lòng phân tích tình huống hiện tại và bằng chứng. Không tự bịa đặt sự thật. Hãy đề xuất các bước chẩn đoán tiếp theo."
    return prompt
