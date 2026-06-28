from aios_habit.case_cockpit import nav_to_page
import pytest

def test_ui_labels_are_commercial(monkeypatch):
    from unittest.mock import MagicMock
    mock_st = MagicMock()
    monkeypatch.setattr("aios_habit.case_cockpit.st", mock_st)
    
    # Check nav maps "Bản đồ tri thức" properly
    class SessionState(dict):
        def __getattr__(self, name):
            return self.get(name)
        def __setattr__(self, name, value):
            self[name] = value

    mock_st.session_state = SessionState()
    
    nav_to_page("Bản đồ tri thức")
    assert mock_st.session_state.active_main_category == "📁 Hồ sơ sự việc"
    assert mock_st.session_state.page == "Bản đồ tri thức"
    
    nav_to_page("Hỏi AI từ bằng chứng")
    assert mock_st.session_state.active_main_category == "🧪 Xuất kết quả"
    assert mock_st.session_state.page == "Hỏi AI từ bằng chứng"

def test_page_knowledge_map_empty_state(monkeypatch):
    from unittest.mock import MagicMock
    mock_st = MagicMock()
    monkeypatch.setattr("aios_habit.case_cockpit.st", mock_st)
    monkeypatch.setattr("aios_habit.case_cockpit.get_active_case", lambda: None)
    
    from aios_habit.case_cockpit import page_knowledge_map
    page_knowledge_map()
    mock_st.info.assert_called_with("Vui lòng chọn một sự việc.")
