from typing import List
from .case_models import Case, EvidenceItem

def safe_mermaid_label(value: str, max_len: int = 80) -> str:
    if not value:
        return ""
    val_str = str(value)
    # Replace newlines, carriage returns, and tabs with spaces
    val_str = val_str.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    
    # Normalize double quotes, square brackets, curly braces, and pipes to avoid breaking Mermaid syntax
    val_str = val_str.replace('"', "'")
    val_str = val_str.replace('[', '(').replace(']', ')')
    val_str = val_str.replace('{', '(').replace('}', ')')
    val_str = val_str.replace('|', '-')
    
    # Collapse multiple spaces
    val_str = " ".join(val_str.split())
    
    # Truncate if overly long
    if len(val_str) > max_len:
        val_str = val_str[:max_len - 3] + "..."
        
    return val_str

def generate_case_mermaid(case: Case, evidence_items: List[EvidenceItem]) -> str:
    lines = ["graph TD"]
    case_node = f'C["{safe_mermaid_label(case.title)}"]'
    lines.append(case_node)
    
    for ev in evidence_items:
        if ev.case_id == case.case_id:
            label = f"{safe_mermaid_label(ev.source_type)}: {safe_mermaid_label(ev.title)}"
            ev_node = f'{ev.evidence_id}["{label}"]'
            lines.append(f'C -->|contains| {ev_node}')
            
    for i, hypo in enumerate(case.hypotheses):
        h_node = f'H{i}["Hypothesis: {safe_mermaid_label(hypo)}"]'
        lines.append(f'C -->|explores| {h_node}')
        
    for i, action in enumerate(case.next_actions):
        a_node = f'A{i}["Action: {safe_mermaid_label(action)}"]'
        lines.append(f'C -->|needs| {a_node}')
        
    for i, decision in enumerate(case.decisions):
        d_node = f'D{i}["Decision: {safe_mermaid_label(decision)}"]'
        lines.append(f'C -->|resulted_in| {d_node}')
        
    return "\n".join(lines)
