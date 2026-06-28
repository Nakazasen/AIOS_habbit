import json
from dataclasses import dataclass
from typing import Any, Dict, List, Set
from aios_habit.case_models import Case, EvidenceItem

@dataclass
class MapNode:
    id: str
    label: str
    type: str  # case, evidence, system, symptom, cause, action, lesson, answer
    details: Dict[str, Any]

@dataclass
class MapEdge:
    source: str
    target: str
    relation: str

class VisualKnowledgeGraph:
    def __init__(self, case: Case):
        self.case = case
        self.nodes: Dict[str, MapNode] = {}
        self.edges: List[MapEdge] = []
        
        self.add_node(case.case_id, case.title, "case", {"status": case.status})

    def add_node(self, node_id: str, label: str, node_type: str, details: Dict[str, Any] = None):
        if node_id not in self.nodes:
            self.nodes[node_id] = MapNode(node_id, label, node_type, details or {})

    def add_edge(self, source: str, target: str, relation: str):
        if source in self.nodes and target in self.nodes:
            self.edges.append(MapEdge(source, target, relation))

def build_visual_knowledge_graph(case: Case, evidence_items: List[EvidenceItem], learning_cards: List[Any], answers: List[EvidenceItem]) -> VisualKnowledgeGraph:
    graph = VisualKnowledgeGraph(case)
    
    # 1. Add Evidence Nodes
    for ev in evidence_items:
        if ev.source_type == "ide_handoff_strong_answer":
            continue
        graph.add_node(ev.evidence_id, ev.title, "evidence", {
            "source_type": ev.source_type,
            "privacy": ev.privacy_level
        })
        graph.add_edge(case.case_id, ev.evidence_id, "case_has_evidence")
        
    # 2. Add AI Answer Nodes
    for ans in answers:
        if ans.source_type == "ide_handoff_strong_answer":
            graph.add_node(ans.evidence_id, ans.title, "answer", {"privacy": ans.privacy_level})
            graph.add_edge(case.case_id, ans.evidence_id, "case_has_answer")
            try:
                meta = json.loads(ans.structured_summary or "{}")
                cites = meta.get("citation_ids", []) or meta.get("evidence_ids", [])
                for ref in cites:
                    if ref in graph.nodes:
                        graph.add_edge(ans.evidence_id, ref, "answer_cites_evidence")
            except:
                pass

    # 3. Add Lessons/Actions (using dummy structure or real logic if stored in case)
    # If learning cards are passed
    for idx, lc in enumerate(learning_cards):
        lid = f"LESSON-{idx}"
        graph.add_node(lid, lc.get("title", f"Lesson {idx}"), "lesson", lc)
        graph.add_edge(case.case_id, lid, "action_creates_lesson")

    return graph

def _escape_mermaid(text: str) -> str:
    return text.replace('"', '').replace('\n', ' ').replace('[', '(').replace(']', ')')[:60]

def export_mermaid_graph(graph: VisualKnowledgeGraph) -> str:
    lines = ["graph TD"]
    for nid, n in graph.nodes.items():
        shape_open, shape_close = ("[", "]")
        if n.type == "evidence": shape_open, shape_close = ("(", ")")
        elif n.type == "answer": shape_open, shape_close = ("{{", "}}")
        elif n.type == "lesson": shape_open, shape_close = ("([", "])")
        label = _escape_mermaid(n.label)
        lines.append(f"    {nid}{shape_open}\"{label}\"{shape_close}")
        lines.append(f"    class {nid} {n.type}")
        
    for e in graph.edges:
        lines.append(f"    {e.source} -- \"{e.relation}\" --> {e.target}")
        
    lines.append("\n    classDef case fill:#f9f,stroke:#333,stroke-width:2px")
    lines.append("    classDef evidence fill:#bbf,stroke:#333,stroke-width:1px")
    lines.append("    classDef answer fill:#bfb,stroke:#333,stroke-width:2px")
    lines.append("    classDef lesson fill:#fbb,stroke:#333,stroke-width:1px")
    
    return "\n".join(lines)

def export_markmap_markdown(graph: VisualKnowledgeGraph) -> str:
    lines = [f"# {graph.case.title}"]
    for n in graph.nodes.values():
        if n.id != graph.case.case_id:
            lines.append(f"## {n.type.title()}: {n.label}")
            for e in graph.edges:
                if e.target == n.id:
                    lines.append(f"- Liên kết từ: {graph.nodes[e.source].label} ({e.relation})")
    return "\n".join(lines)

def export_interactive_html(graph: VisualKnowledgeGraph) -> str:
    # A safe fallback static HTML generator
    html = ["<html><body><h1>Bản đồ tri thức</h1><ul>"]
    for n in graph.nodes.values():
        html.append(f"<li><b>{n.label}</b> ({n.type})")
        html.append("<ul>")
        for e in graph.edges:
            if e.source == n.id:
                html.append(f"<li>-> {e.relation} -> {graph.nodes[e.target].label}</li>")
        html.append("</ul></li>")
    html.append("</ul></body></html>")
    return "\n".join(html)

def summarize_map_metrics(graph: VisualKnowledgeGraph) -> Dict[str, Any]:
    nodes_by_type = {}
    for n in graph.nodes.values():
        nodes_by_type[n.type] = nodes_by_type.get(n.type, 0) + 1
        
    ev_count = nodes_by_type.get("evidence", 0)
    ans_count = nodes_by_type.get("answer", 0)
    
    cites = len([e for e in graph.edges if e.relation == "answer_cites_evidence"])
    cov = f"{(cites / ev_count * 100):.1f}%" if ev_count > 0 and ans_count > 0 else "0%"
    
    return {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "evidence_count": ev_count,
        "answer_count": ans_count,
        "lesson_count": nodes_by_type.get("lesson", 0),
        "citation_coverage": cov
    }
