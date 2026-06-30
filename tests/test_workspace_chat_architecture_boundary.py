import sys
from pathlib import Path
import pytest

def test_no_imports_from_case_cockpit():
    app_path = Path("src/aios_habit/workspace_chat_app.py")
    ui_path = Path("src/aios_habit/workspace_chat_ui.py")
    
    app_source = app_path.read_text(encoding="utf-8")
    ui_source = ui_path.read_text(encoding="utf-8")
    
    # Assert neither file imports case_cockpit
    assert "case_cockpit" not in app_source
    assert "case_cockpit" not in ui_source

def test_store_directory_boundary():
    # Verify store uses its own separate directory
    from aios_habit.workspace_chat_store import LOCAL_CHAT_DIR
    
    # Assert directory name ends with workspace_chat and is under local_cases
    assert LOCAL_CHAT_DIR.name == "workspace_chat"
    assert LOCAL_CHAT_DIR.parent.name == "local_cases"

def test_import_smoke_case_cockpit():
    # Verify case_cockpit can be imported without syntax/module errors
    try:
        import aios_habit.case_cockpit as cockpit
        assert cockpit is not None
    except Exception as e:
        pytest.fail(f"Failed to import case_cockpit: {e}")

def test_import_smoke_workspace_chat_app():
    # Verify workspace_chat_app components can be imported
    try:
        import aios_habit.workspace_chat_app as app
        assert app is not None
    except Exception as e:
        pytest.fail(f"Failed to import workspace_chat_app: {e}")
