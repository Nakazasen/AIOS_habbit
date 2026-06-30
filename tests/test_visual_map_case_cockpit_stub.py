import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_streamlit():
    with patch('aios_habit.case_cockpit.st') as mock_st:
        yield mock_st

def test_case_cockpit_stub_exposes_vietnamese_label():
    from aios_habit.case_cockpit import page_knowledge_map
    with patch('aios_habit.case_cockpit.st') as mock_st, \
         patch('aios_habit.case_cockpit.get_active_case') as mock_get_case:
        mock_get_case.return_value = None
        page_knowledge_map()
        mock_st.title.assert_called_with("🧠 Bản đồ tri thức công việc")



def test_ui_helper_exposes_vietnamese_pending_and_markdown_labels():
    from aios_habit.case_cockpit import antigravity_bridge_owner_labels
    labels = antigravity_bridge_owner_labels()
    assert labels["pending"] == "Gói đang chờ phản hồi"
    assert labels["paste_markdown"] == "Dán câu trả lời Markdown từ Antigravity"
    assert labels["import_validate"] == "Nhập phản hồi và kiểm tra bằng chứng"
    assert labels["map_preview"] == "Xem nhanh bản đồ tri thức"


def test_visual_map_preview_helper_returns_counts():
    from aios_habit.case_cockpit import build_visual_map_preview_for_owner
    from aios_habit.case_models import Case, EvidenceItem
    case = Case("CASE-1", "Sample", privacy_level="local_only")
    ev = EvidenceItem("EVD-1", "CASE-1", "note", "manual", "Evidence", "Safe text", privacy_level="local_only")
    preview = build_visual_map_preview_for_owner(case, [ev], final_answer={"cited_evidence_ids": ["EVD-1"], "confidence": "high"})
    assert preview["node_count"] >= 2
    assert preview["edge_count"] >= 1
    assert "local_json" in preview
    assert "safe_mermaid" in preview
