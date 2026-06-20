from typing import List
from .case_models import Case, EvidenceItem

def generate_case_mermaid(case: Case, evidence_items: List[EvidenceItem]) -> str:
    lines = ["graph TD"]
    case_node = f'C[{case.title}]'
    lines.append(case_node)
    
    for ev in evidence_items:
        if ev.case_id == case.case_id:
            ev_node = f'{ev.evidence_id}["{ev.source_type}: {ev.title}"]'
            lines.append(f'C -->|contains| {ev_node}')
            
    for i, hypo in enumerate(case.hypotheses):
        h_node = f'H{i}["Hypothesis: {hypo}"]'
        lines.append(f'C -->|explores| {h_node}')
        
    for i, action in enumerate(case.next_actions):
        a_node = f'A{i}["Action: {action}"]'
        lines.append(f'C -->|needs| {a_node}')
        
    for i, decision in enumerate(case.decisions):
        d_node = f'D{i}["Decision: {decision}"]'
        lines.append(f'C -->|resulted_in| {d_node}')
        
    return "\n".join(lines)
