from aios_habit.case_models import Case, EvidenceItem
from aios_habit.visual_knowledge_map import (
    build_visual_knowledge_graph,
    export_mermaid_graph,
    export_markmap_markdown,
    export_interactive_html,
    summarize_map_metrics
)
import json

def test_visual_knowledge_map_generation():
    case = Case(case_id="CASE-1", title="Test Case", status="open", created_at="2026", updated_at="2026")
    ev1 = EvidenceItem("EVD-1", "CASE-1", "xlsx", "fake.xlsx", "text", privacy_level="local_only")
    ans_meta = json.dumps({"citation_ids": ["EVD-1"]})
    ans1 = EvidenceItem("ANS-1", "CASE-1", "ide_handoff_strong_answer", "ans", "text", structured_summary=ans_meta)
    lessons = [{"title": "Check table"}]
    
    graph = build_visual_knowledge_graph(case, [ev1, ans1], lessons, [ans1])
    
    # Verify nodes
    assert "CASE-1" in graph.nodes
    assert "EVD-1" in graph.nodes
    assert "ANS-1" in graph.nodes
    assert "LESSON-0" in graph.nodes
    
    # Verify edges
    relations = [e.relation for e in graph.edges]
    assert "case_has_evidence" in relations
    assert "case_has_answer" in relations
    assert "answer_cites_evidence" in relations
    assert "action_creates_lesson" in relations
    
    # Verify export
    mermaid = export_mermaid_graph(graph)
    assert "graph TD" in mermaid
    assert "CASE-1" in mermaid
    assert "EVD-1" in mermaid
    assert "ANS-1" in mermaid
    assert "LESSON-0" in mermaid
    
    markdown = export_markmap_markdown(graph)
    assert "# Test Case" in markdown
    assert "Evidence: fake.xlsx" in markdown or "Evidence:" in markdown
    
    html = export_interactive_html(graph)
    assert "<html>" in html
    assert "Test Case" in html
    
    metrics = summarize_map_metrics(graph)
    assert metrics["node_count"] == 4
    assert metrics["edge_count"] == 4
    assert metrics["evidence_count"] == 1
    assert metrics["answer_count"] == 1
    assert metrics["lesson_count"] == 1
    assert metrics["citation_coverage"] == "100.0%"
