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
