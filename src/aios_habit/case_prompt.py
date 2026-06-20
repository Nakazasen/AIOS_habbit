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
                lines.append(f"- [{e.source_type}] {e.title}: [EXCLUDED FOR PRIVACY - local_only]")
                continue
        
        snippet = e.extracted_text[:200] if e.extracted_text else ""
        lines.append(f"- [{e.source_type}] {e.title}: {snippet}...")
    
    summary_text = "\n".join(lines)
    if excluded_any:
        if summary_text:
            summary_text += "\n"
        summary_text += "Some local_only evidence was excluded for privacy."
    return summary_text

def build_prompt_pack(case: Case, evidence_items: List[EvidenceItem], target: str, include_local_only: bool = False) -> str:
    prompt = f"Case Title: {case.title}\n"
    prompt += f"Current Situation: {case.current_situation}\n\n"
    prompt += "Evidence Summary:\n"
    prompt += summarize_evidence_for_prompt(evidence_items, target, include_local_only)
    
    prompt += "\n\nHypotheses:\n"
    for h in case.hypotheses:
        prompt += f"- {h}\n"
        
    prompt += "\nRequested Output: Please analyze the current situation and evidence. Do not invent facts. Ask for next diagnostic steps."
    return prompt
