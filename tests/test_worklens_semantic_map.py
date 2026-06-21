import pytest
from aios_habit.worklens_semantic_map import build_worklens_semantic_graph
from aios_habit.knowledge_map_html import graph_to_html_map

class MockWorkspace:
    def __init__(self, workspace_id, name, description=""):
        self.workspace_id = workspace_id
        self.name = name
        self.description = description

class MockNotebook:
    def __init__(self, notebook_id, workspace_id, name, description=""):
        self.notebook_id = notebook_id
        self.workspace_id = workspace_id
        self.name = name
        self.description = description

class MockSource:
    def __init__(self, source_id, notebook_id, title, description=""):
        self.source_id = source_id
        self.notebook_id = notebook_id
        self.title = title
        self.description = description

class MockCase:
    def __init__(self, case_id, title, workspace_id="default", priority="normal", current_situation="", hypotheses=None, next_actions=None, decisions=None, linked_notebook_ids=None):
        self.case_id = case_id
        self.title = title
        self.workspace_id = workspace_id
        self.priority = priority
        self.current_situation = current_situation
        self.hypotheses = hypotheses or []
        self.next_actions = next_actions or []
        self.decisions = decisions or []
        self.linked_notebook_ids = linked_notebook_ids or []

class MockEvidence:
    def __init__(self, evidence_id, case_id, title, source_type="note", source_path="manual", extracted_text="", structured_summary="", confidence="low"):
        self.evidence_id = evidence_id
        self.case_id = case_id
        self.title = title
        self.source_type = source_type
        self.source_path = source_path
        self.extracted_text = extracted_text
        self.structured_summary = structured_summary
        self.confidence = confidence

class MockLearningCard:
    def __init__(self, learning_id, case_id, reusable_lesson, true_cause="", actions_taken="", check_first_next_time="", confidence="draft"):
        self.learning_id = learning_id
        self.case_id = case_id
        self.reusable_lesson = reusable_lesson
        self.true_cause = true_cause
        self.actions_taken = actions_taken
        self.check_first_next_time = check_first_next_time
        self.confidence = confidence

class MockBridgeImport:
    def __init__(self, import_id, notebook_id, workspace_id, import_type, title, parsed_json=None):
        self.import_id = import_id
        self.notebook_id = notebook_id
        self.workspace_id = workspace_id
        self.import_type = import_type
        self.title = title
        self.parsed_json = parsed_json or {}

# 1. Test building graph from case + evidence
def test_build_semantic_graph_case_and_evidence():
    case = MockCase(case_id="case-1", title="My Case", workspace_id="ws-1", priority="high", current_situation="This is the situation")
    ev = MockEvidence(evidence_id="ev-1", case_id="case-1", title="Key Evidence", source_path="path/to/doc.pdf", confidence="medium")
    
    graph = build_worklens_semantic_graph(
        workspace="ws-1",
        notebooks=[],
        sources=[],
        cases=[case],
        evidence=[ev],
        learning_cards=[],
        bridge_imports=[]
    )
    
    # Assert nodes
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert "case_case_1" in nodes
    assert nodes["case_case_1"]["label"] == "My Case"
    assert nodes["case_case_1"]["type"] == "case"
    assert nodes["case_case_1"]["confidence"] == "high"
    
    assert "evidence_ev_1" in nodes
    assert nodes["evidence_ev_1"]["label"] == "Key Evidence"
    assert nodes["evidence_ev_1"]["type"] == "evidence"
    assert nodes["evidence_ev_1"]["source_ref"] == "path/to/doc.pdf"
    assert nodes["evidence_ev_1"]["confidence"] == "medium"
    
    # Assert edges
    edges = graph["edges"]
    assert len(edges) >= 2
    relations = {(e["from"], e["to"]): e["relation"] for e in edges}
    assert relations[("case_case_1", "evidence_ev_1")] == "HAS_EVIDENCE"
    assert relations[("evidence_ev_1", "case_case_1")] == "SUPPORTS"
    
    # Test HTML Map compatibility
    html_str = graph_to_html_map(graph)
    assert "My Case" in html_str
    assert "Key Evidence" in html_str
    
    # Assert graph meta
    assert graph["meta"]["graph_kind"] == "semantic"
    assert graph["meta"]["uses_sample_data"] is False

# 2. Test empty input does not crash
def test_build_semantic_graph_empty():
    graph = build_worklens_semantic_graph(
        workspace="ws-empty",
        notebooks=[],
        sources=[],
        cases=[],
        evidence=[],
        learning_cards=[],
        bridge_imports=[]
    )
    assert graph["nodes"] == []
    assert graph["edges"] == []
    assert graph["meta"]["graph_kind"] == "empty"

# 3. Test max_nodes and max_edges truncation
def test_build_semantic_graph_limits():
    cases = [MockCase(case_id=f"case-{i}", title=f"Case {i}", workspace_id="ws-limit") for i in range(10)]
    graph = build_worklens_semantic_graph(
        workspace="ws-limit",
        notebooks=[],
        sources=[],
        cases=cases,
        evidence=[],
        learning_cards=[],
        bridge_imports=[],
        max_nodes=3
    )
    assert len(graph["nodes"]) == 3
    assert "Nút vượt quá giới hạn đã bị cắt bớt" in graph["meta"]["warnings"]

# 4. Test senior learning card semantic extraction
def test_build_semantic_graph_learning_cards():
    case = MockCase(case_id="case-1", title="My Case", workspace_id="ws-learn")
    lc = MockLearningCard(
        learning_id="lc-1",
        case_id="case-1",
        reusable_lesson="Never delete config without backup",
        true_cause="Lack of backup policy",
        actions_taken="Created backup cron",
        check_first_next_time="Check backup files size",
        confidence="reviewed"
    )
    
    graph = build_worklens_semantic_graph(
        workspace="ws-learn",
        notebooks=[],
        sources=[],
        cases=[case],
        evidence=[],
        learning_cards=[lc],
        bridge_imports=[]
    )
    
    nodes = {n["id"]: n for n in graph["nodes"]}
    assert "learning_lc_1" in nodes
    assert nodes["learning_lc_1"]["type"] == "learning"
    assert nodes["learning_lc_1"]["description"].startswith("Bài học kinh nghiệm:")
    html_str = graph_to_html_map(graph)
    assert "learning" in html_str
    assert "Bài học kinh nghiệm:" in html_str
    assert "cause_lc_1_cause" in nodes
    assert "action_lc_1_countermeasure" in nodes
    assert "action_lc_1_nextcheck" in nodes
    
    relations = {(e["from"], e["to"]): e["relation"] for e in graph["edges"]}
    assert relations[("learning_lc_1", "case_case_1")] == "LEARNED_FROM"
    assert relations[("learning_lc_1", "action_lc_1_nextcheck")] == "SUGGESTS_NEXT_CHECK"
    assert relations[("learning_lc_1", "cause_lc_1_cause")] == "DESCRIBES_ROOT_CAUSE"
    assert relations[("learning_lc_1", "action_lc_1_countermeasure")] == "DESCRIBES_COUNTERMEASURE"

# 5. Test no hardcoding of LSU
def test_build_semantic_graph_no_lsu_hardcode():
    case = MockCase(case_id="case-normal", title="Normal Issue", workspace_id="ws-normal")
    graph = build_worklens_semantic_graph(
        workspace="ws-normal",
        notebooks=[],
        sources=[],
        cases=[case],
        evidence=[],
        learning_cards=[],
        bridge_imports=[]
    )
    # Ensure standard words aren't in the clean nodes unless we put them
    for n in graph["nodes"]:
        assert "LSU" not in n["label"]
        assert "Drum" not in n["label"]


def test_notebooklm_import_nodes_are_marked_unconfirmed():
    notebook = MockNotebook("nb-1", "ws-import", "Notebook")
    imported = MockBridgeImport(
        import_id="IMP-REAL",
        notebook_id="nb-1",
        workspace_id="ws-import",
        import_type="knowledge_graph_json",
        title="NotebookLM import",
        parsed_json={
            "nodes": [
                {"id": "n1", "label": "Imported concept", "type": "cause", "description": "Imported claim"}
            ],
            "edges": []
        }
    )

    graph = build_worklens_semantic_graph(
        workspace="ws-import",
        notebooks=[notebook],
        sources=[],
        cases=[],
        evidence=[],
        learning_cards=[],
        bridge_imports=[imported],
        include_bridge_imports=True
    )

    imported_nodes = [n for n in graph["nodes"] if n["id"].startswith("imp_IMP_REAL")]
    assert len(imported_nodes) == 1
    assert imported_nodes[0]["description"].startswith("NotebookLM import — chưa xác nhận:")
    html_str = graph_to_html_map(graph)
    assert "NotebookLM import — chưa xác nhận:" in html_str


def test_business_semantic_graph_excludes_notebooklm_imports_even_when_available():
    case = MockCase(case_id="case-1", title="Verified Case", workspace_id="ws-mixed")
    ev = MockEvidence(evidence_id="ev-1", case_id="case-1", title="Verified Evidence")
    imported = MockBridgeImport(
        import_id="IMP-MIXED",
        notebook_id="nb-1",
        workspace_id="ws-mixed",
        import_type="knowledge_graph_json",
        title="NotebookLM import",
        parsed_json={
            "nodes": [
                {"id": "n1", "label": "Imported claim", "type": "cause", "description": "AI claim"}
            ],
            "edges": []
        }
    )

    graph = build_worklens_semantic_graph(
        workspace="ws-mixed",
        notebooks=[],
        sources=[],
        cases=[case],
        evidence=[ev],
        learning_cards=[],
        bridge_imports=[imported]
    )

    labels = {n["label"] for n in graph["nodes"]}
    descriptions = " ".join(n.get("description", "") for n in graph["nodes"])
    html_str = graph_to_html_map(graph)

    assert graph["meta"]["graph_kind"] == "semantic"
    assert "Verified Case" in labels
    assert "Verified Evidence" in labels
    assert "Imported claim" not in labels
    assert "NotebookLM import" not in descriptions
    assert "NotebookLM import" not in html_str


def test_business_semantic_graph_does_not_fallback_to_import_only_data():
    imported = MockBridgeImport(
        import_id="IMP-ONLY",
        notebook_id="nb-1",
        workspace_id="ws-import-only",
        import_type="knowledge_graph_json",
        title="NotebookLM import",
        parsed_json={
            "nodes": [
                {"id": "n1", "label": "Imported-only claim", "type": "cause"}
            ],
            "edges": []
        }
    )

    graph = build_worklens_semantic_graph(
        workspace="ws-import-only",
        notebooks=[],
        sources=[],
        cases=[],
        evidence=[],
        learning_cards=[],
        bridge_imports=[imported]
    )
    html_str = graph_to_html_map(graph)

    assert graph["nodes"] == []
    assert graph["edges"] == []
    assert graph["meta"]["graph_kind"] == "empty"
    assert "Imported-only claim" not in html_str
    assert "Chưa đủ dữ liệu nghiệp vụ để dựng bản đồ tri thức" in html_str
