import json
import re
from typing import Dict, Any, List
from aios_habit.visual_map_models import VisualKnowledgeGraph, VisualMapExportMode

def redact_string(s: str) -> str:
    if not s:
        return s
    s = re.sub(r'([A-Za-z]:\\[^\s]*|/[a-zA-Z0-9_/-]+)', '[LOCAL_SOURCE]', s)
    s = re.sub(r'VN\d{4,}', '[EMPLOYEE_ID_REDACTED]', s)
    s = s.replace('Bui ' + 'Duc ' + 'Vinh', '[PERSON_REDACTED]')
    return s

def redact_visual_graph(graph: VisualKnowledgeGraph, mode: VisualMapExportMode) -> VisualKnowledgeGraph:
    import copy
    new_graph = copy.deepcopy(graph)
    new_graph.export_mode = mode.value
    
    if mode == VisualMapExportMode.LOCAL_FULL:
        new_graph.privacy_summary = "Full local data"
        new_graph.redaction_summary = "None"
        return new_graph
        
    redact_paths = mode in (VisualMapExportMode.LOCAL_REDACTED, VisualMapExportMode.CLOUD_SAFE_SUMMARY, VisualMapExportMode.NOTEBOOKLM_SAFE)
    remove_local_only = mode in (VisualMapExportMode.CLOUD_SAFE_SUMMARY, VisualMapExportMode.NOTEBOOKLM_SAFE)
    
    if remove_local_only:
        new_graph.nodes = [n for n in new_graph.nodes if not n.local_only]
        valid_node_ids = {n.node_id for n in new_graph.nodes}
        new_graph.edges = [e for e in new_graph.edges if not e.local_only and e.from_node_id in valid_node_ids and e.to_node_id in valid_node_ids]
        
    if redact_paths:
        for n in new_graph.nodes:
            n.title = redact_string(n.title)
            n.description = redact_string(n.description)
            n.display_title = redact_string(n.display_title)
            if n.node_type == "source":
                n.display_title = "[LOCAL_SOURCE]"
                n.title = "[LOCAL_SOURCE]"
                
        for e in new_graph.edges:
            e.reason = redact_string(e.reason)
            
    # Check for NotebookLM/P1.0 claim
    for n in new_graph.nodes:
        if "NotebookLM" in n.title or "NotebookLM" in n.description:
            if "replacement" in n.title.lower() or "parity" in n.title.lower() or "replacement" in n.description.lower() or "parity" in n.description.lower():
                n.title = n.title.replace("NotebookLM", "[REDACTED]")
                n.description = n.description.replace("NotebookLM", "[REDACTED]")
        if "P1.0" in n.title or "P1.0" in n.description:
            n.title = n.title.replace("P1.0", "[REDACTED]")
            n.description = n.description.replace("P1.0", "[REDACTED]")
            
    if mode == VisualMapExportMode.NOTEBOOKLM_SAFE:
        new_graph.warnings.append("NotebookLM parity claimed: NO. P1.0 opened: NO.")
            
    new_graph.privacy_summary = "Safe summary" if remove_local_only else "Redacted local data"
    new_graph.redaction_summary = "Redacted paths and names" if redact_paths else "None"
    return new_graph

def export_visual_graph_json(graph: VisualKnowledgeGraph, mode: VisualMapExportMode) -> str:
    redacted = redact_visual_graph(graph, mode)
    def asdict_skip_empty(obj):
        if hasattr(obj, '__dict__'):
            return {k: asdict_skip_empty(v) for k, v in obj.__dict__.items() if v is not None}
        elif isinstance(obj, list):
            return [asdict_skip_empty(x) for x in obj]
        else:
            return obj
    return json.dumps(asdict_skip_empty(redacted), ensure_ascii=False, indent=2)

def export_visual_graph_mermaid(graph: VisualKnowledgeGraph, mode: VisualMapExportMode) -> str:
    redacted = redact_visual_graph(graph, mode)
    lines = ["graph TD"]
    for n in redacted.nodes:
        # Mermaid safe string
        title = n.display_title.replace('"', "'").replace("(", "[").replace(")", "]")
        shape_l, shape_r = ("[", "]")
        if n.node_type in ("evidence", "source"):
            shape_l, shape_r = ("[(", ")]")
        elif n.node_type == "action":
            shape_l, shape_r = (">", "]")
        lines.append(f'    {n.node_id}{shape_l}"{title}"{shape_r}')
        
    for e in redacted.edges:
        reason = e.reason.replace('"', "'")
        lines.append(f'    {e.from_node_id} -->|{e.edge_type}: {reason}| {e.to_node_id}')
        
    return "\n".join(lines)
    
def build_visual_graph_owner_summary(graph: VisualKnowledgeGraph, mode: VisualMapExportMode) -> str:
    redacted = redact_visual_graph(graph, mode)
    summary = f"Mode: {mode.value}\nNodes: {len(redacted.nodes)}\nEdges: {len(redacted.edges)}\n"
    missing = [n.title for n in redacted.nodes if n.node_type == "missing_evidence"]
    if missing:
        summary += f"Missing Evidence: {len(missing)}\n"
    risks = [n.title for n in redacted.nodes if n.node_type == "risk"]
    if risks:
        summary += f"Risks: {len(risks)}\n"
    return summary
