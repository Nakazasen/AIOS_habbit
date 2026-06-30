from typing import Dict, Any, List, Optional
from aios_habit.visual_map_models import VisualKnowledgeGraph, VisualMapNode, VisualMapEdge, VisualMapExportMode
from aios_habit.visual_map_export import export_visual_graph_json, export_visual_graph_mermaid, redact_string

def build_visual_map_ui_state(graph: VisualKnowledgeGraph) -> Dict[str, Any]:
    missing_nodes = list_missing_evidence_nodes(graph)
    risk_nodes = list_risk_claim_nodes(graph)
    return {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "missing_evidence_count": len(missing_nodes),
        "risk_claim_count": len(risk_nodes)
    }

def summarize_visual_map_for_owner(graph: VisualKnowledgeGraph) -> Dict[str, Any]:
    high_conf_ev = [n.display_title or n.title for n in graph.nodes if n.node_type == "evidence" and n.confidence == "high"]
    missing = [n.display_title or n.title for n in list_missing_evidence_nodes(graph)]
    risks = [n.display_title or n.title for n in list_risk_claim_nodes(graph)]
    actions = [n.display_title or n.title for n in list_next_action_nodes(graph)]
    learning = [n.display_title or n.title for n in list_learning_nodes(graph)]
    
    return {
        "Bản đồ này nói gì?": f"Bản đồ có {len(graph.nodes)} nút và {len(graph.edges)} quan hệ.",
        "Bằng chứng mạnh nhất là gì?": high_conf_ev,
        "Còn thiếu gì trước khi kết luận?": missing,
        "Rủi ro nếu kết luận vội là gì?": risks,
        "Việc tiếp theo nên làm là gì?": actions,
        "Bài học nào có thể dùng lại?": learning,
    }

def filter_visual_map_nodes(graph: VisualKnowledgeGraph, node_type: Optional[str] = None, privacy_level: Optional[str] = None, min_confidence: Optional[str] = None, status: Optional[str] = None, search_text: Optional[str] = None) -> List[VisualMapNode]:
    results = []
    for n in graph.nodes:
        if node_type and node_type != "All" and n.node_type != node_type:
            continue
        if privacy_level and privacy_level != "All" and n.privacy_level != privacy_level:
            continue
        if min_confidence and min_confidence != "All" and n.confidence != min_confidence:
            continue
        if status and status != "All" and n.status != status:
            continue
        if search_text:
            text_to_search = f"{n.title} {n.description} {n.display_title}".lower()
            if search_text.lower() not in text_to_search:
                continue
        results.append(n)
    return results

def filter_visual_map_edges(graph: VisualKnowledgeGraph, edge_type: Optional[str] = None, privacy_level: Optional[str] = None, min_confidence: Optional[str] = None, search_text: Optional[str] = None) -> List[VisualMapEdge]:
    results = []
    for e in graph.edges:
        if edge_type and edge_type != "All" and e.edge_type != edge_type:
            continue
        if privacy_level and privacy_level != "All" and e.privacy_level != privacy_level:
            continue
        if min_confidence and min_confidence != "All" and e.confidence != min_confidence:
            continue
        if search_text:
            text_to_search = f"{e.reason}".lower()
            if search_text.lower() not in text_to_search:
                continue
        results.append(e)
    return results

def get_node_detail_payload(graph: VisualKnowledgeGraph, node_id: str) -> Optional[Dict[str, Any]]:
    for n in graph.nodes:
        if n.node_id == node_id:
            title = n.title
            desc = n.description
            if n.privacy_level != "local_only":
                title = redact_string(title)
                desc = redact_string(desc)
                
            return {
                "node_id": n.node_id,
                "node_type": n.node_type,
                "title": title,
                "description": desc,
                "evidence_ids": n.evidence_ids,
                "confidence": n.confidence,
                "privacy_level": n.privacy_level,
                "local_only": n.local_only,
                "limitations": n.limitations,
                "status": n.status
            }
    return None

def get_edge_detail_payload(graph: VisualKnowledgeGraph, edge_id: str) -> Optional[Dict[str, Any]]:
    for e in graph.edges:
        if e.edge_id == edge_id:
            reason = e.reason
            if e.privacy_level != "local_only":
                reason = redact_string(reason)
            return {
                "edge_id": e.edge_id,
                "edge_type": e.edge_type,
                "reason": reason,
                "evidence_ids": e.evidence_ids,
                "confidence": e.confidence,
                "privacy_level": e.privacy_level,
                "local_only": e.local_only
            }
    return None

def list_missing_evidence_nodes(graph: VisualKnowledgeGraph) -> List[VisualMapNode]:
    return [n for n in graph.nodes if n.node_type == "missing_evidence"]

def list_risk_claim_nodes(graph: VisualKnowledgeGraph) -> List[VisualMapNode]:
    return [n for n in graph.nodes if n.node_type in ("risk", "claim")]

def list_next_action_nodes(graph: VisualKnowledgeGraph) -> List[VisualMapNode]:
    return [n for n in graph.nodes if n.node_type == "action"]

def list_learning_nodes(graph: VisualKnowledgeGraph) -> List[VisualMapNode]:
    return [n for n in graph.nodes if n.node_type in ("learning_card", "checklist_item")]

def build_visual_map_export_payload(graph: VisualKnowledgeGraph, mode: VisualMapExportMode) -> Dict[str, str]:
    return {
        "json": export_visual_graph_json(graph, mode),
        "mermaid": export_visual_graph_mermaid(graph, mode)
    }
