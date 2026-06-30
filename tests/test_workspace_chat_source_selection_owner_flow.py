import pytest
import streamlit as st
from pathlib import Path
import aios_habit.workspace_chat_store as store
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    TemporaryConversationSource,
    NotebookSource,
    SOURCE_SCOPE_NOTEBOOK,
    SOURCE_SCOPE_TEMPORARY
)

@pytest.fixture(autouse=True)
def setup_test_store(tmp_path, monkeypatch):
    test_dir = tmp_path / "workspace_chat"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(store, "NOTEBOOK_SOURCES_FILE", test_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    store.init_chat_store()

class MockSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)
    def __setattr__(self, name, value):
        self[name] = value

@pytest.fixture
def mock_streamlit_app(monkeypatch):
    session_state = MockSessionState()
    session_state.wsc_active_notebook_id = "mom_opcenter"
    session_state.wsc_active_conversation_id = "conv_1"
    session_state.wsc_show_save_placeholder = False
    session_state.wsc_show_explain_placeholder = False
    session_state.wsc_action_message = None
    session_state.wsc_action_error = None
    
    monkeypatch.setattr(st, "session_state", session_state)
    
    reruns = []
    def mock_rerun():
        reruns.append(True)
    monkeypatch.setattr(st, "rerun", mock_rerun)
    
    return session_state, reruns

def test_owner_toggle_notebook_source(mock_streamlit_app):
    # Setup notebook source
    src = NotebookSource(id="src_nb_1", notebook_id="mom_opcenter", title="Opcenter Checklist", source_type="pasted_text")
    store.save_notebook_source(src)
    
    # Toggle enable notebook source
    store.set_source_enabled("conv_1", SOURCE_SCOPE_NOTEBOOK, "src_nb_1", True)
    selections = store.load_conversation_source_selections("conv_1")
    assert len(selections) == 1
    assert selections[0].source_id == "src_nb_1"
    assert selections[0].source_scope == SOURCE_SCOPE_NOTEBOOK
    assert selections[0].enabled is True
    
    # Toggle disable notebook source
    store.set_source_enabled("conv_1", SOURCE_SCOPE_NOTEBOOK, "src_nb_1", False)
    selections = store.load_conversation_source_selections("conv_1")
    assert selections[0].enabled is False

def test_owner_toggle_temporary_source(mock_streamlit_app):
    # Setup temporary source
    ts = TemporaryConversationSource(id="ts_1", conversation_id="conv_1", title="Temp log", source_type="pasted_text", content_preview="Preview")
    store.save_temporary_source(ts)
    
    # Toggle enable temporary source
    store.set_source_enabled("conv_1", SOURCE_SCOPE_TEMPORARY, "ts_1", True)
    selections = store.load_conversation_source_selections("conv_1")
    assert len(selections) == 1
    assert selections[0].source_id == "ts_1"
    assert selections[0].source_scope == SOURCE_SCOPE_TEMPORARY
    assert selections[0].enabled is True
    
    # Toggle disable temporary source
    store.set_source_enabled("conv_1", SOURCE_SCOPE_TEMPORARY, "ts_1", False)
    selections = store.load_conversation_source_selections("conv_1")
    assert selections[0].enabled is False

def test_paste_temporary_source_auto_enables(mock_streamlit_app, monkeypatch):
    # Mock active conversation and notebook
    conv = WorkspaceConversation(id="conv_1", notebook_id="mom_opcenter", title="Cuộc trò chuyện 1")
    store.save_conversation(conv)
    
    # We will simulate the submit handler in workspace_chat_app.py:
    # 1. create temporary source
    ts = TemporaryConversationSource(
        id="ts_pasted",
        conversation_id="conv_1",
        source_type="pasted_text",
        title="Email dán tay",
        content_preview="Noi dung email...",
        content_text="Noi dung email day du..."
    )
    # 2. save
    store.save_temporary_source(ts)
    # 3. enable
    store.set_source_enabled("conv_1", SOURCE_SCOPE_TEMPORARY, ts.id, True)
    
    # Verify both temporary source is saved and selection is enabled
    saved_sources = store.load_temporary_sources("conv_1")
    assert len(saved_sources) == 1
    assert saved_sources[0].id == "ts_pasted"
    
    selections = store.load_conversation_source_selections("conv_1")
    assert len(selections) == 1
    assert selections[0].source_id == "ts_pasted"
    assert selections[0].source_scope == SOURCE_SCOPE_TEMPORARY
    assert selections[0].enabled is True

def test_promote_temporary_source_keeps_temp_and_creates_notebook_source_not_enabled(mock_streamlit_app):
    # Setup temporary source
    ts = TemporaryConversationSource(
        id="ts_promote",
        conversation_id="conv_1",
        source_type="pasted_text",
        title="Promoted Title",
        content_preview="Preview text",
        content_text="Full text"
    )
    store.save_temporary_source(ts)
    
    # Enable temporary source selection prior to promote
    store.set_source_enabled("conv_1", SOURCE_SCOPE_TEMPORARY, "ts_promote", True)
    
    # Promote it
    nb_src = store.promote_temporary_source_to_notebook("conv_1", "ts_promote", "mom_opcenter")
    
    # Verify temporary source still exists and status updated
    temp_sources = store.load_temporary_sources("conv_1")
    assert len(temp_sources) == 1
    assert temp_sources[0].id == "ts_promote"
    assert temp_sources[0].long_term_saved is True
    assert temp_sources[0].status == "added_to_notebook"
    
    # Verify notebook source is created
    nb_sources = store.load_notebook_sources("mom_opcenter")
    assert len(nb_sources) == 1
    assert nb_sources[0].origin_temporary_source_id == "ts_promote"
    
    # Verify new notebook source is NOT auto-enabled
    selections = store.load_conversation_source_selections("conv_1")
    # Only the original temporary source selection should exist
    assert len(selections) == 1
    assert selections[0].source_id == "ts_promote"
    assert selections[0].source_scope == SOURCE_SCOPE_TEMPORARY
    
    # Query selections for the new notebook source and ensure it's not enabled
    nb_selections = [sel for sel in selections if sel.source_scope == SOURCE_SCOPE_NOTEBOOK and sel.source_id == nb_src.id]
    assert len(nb_selections) == 0

def test_rerun_restores_from_store_source_of_truth(mock_streamlit_app):
    # Enable a source directly in store
    store.set_source_enabled("conv_1", SOURCE_SCOPE_NOTEBOOK, "src_direct", True)
    
    # Simulating UI reload - read selections
    selections = store.load_conversation_source_selections("conv_1")
    selections_map = {(sel.source_scope, sel.source_id): sel.enabled for sel in selections}
    
    # Check that reload gets current selection state
    assert selections_map.get((SOURCE_SCOPE_NOTEBOOK, "src_direct")) is True

def test_source_selection_helpers_called_inside_sidebar_context():
    import ast
    app_path = Path("src/aios_habit/workspace_chat_app.py")
    source = app_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    
    target_helpers = {"render_source_summary", "render_notebook_source_list", "render_temporary_source_list"}
    found_calls = {helper: False for helper in target_helpers}
    
    class SidebarCallChecker(ast.NodeVisitor):
        def __init__(self):
            self.in_sidebar = False
            
        def visit_With(self, node):
            is_sidebar_context = False
            for item in node.items:
                expr = item.context_expr
                if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name) and expr.value.id == "st" and expr.attr == "sidebar":
                    is_sidebar_context = True
            
            old_in_sidebar = self.in_sidebar
            if is_sidebar_context:
                self.in_sidebar = True
                
            self.generic_visit(node)
            self.in_sidebar = old_in_sidebar
            
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id in target_helpers:
                if not self.in_sidebar:
                    pytest.fail(f"Function {node.func.id} called outside of 'with st.sidebar:' context!")
                found_calls[node.func.id] = True
            self.generic_visit(node)
            
    checker = SidebarCallChecker()
    checker.visit(tree)
    
    for helper, found in found_calls.items():
        assert found, f"Expected call to {helper} not found in workspace_chat_app.py"

def test_conversation_isolation_selection_keys():
    conv_id = "conv_abc"
    source_id = "src_123"
    
    key_nb = f"wsc_source_notebook_{conv_id}_{source_id}"
    key_temp = f"wsc_source_temporary_{conv_id}_{source_id}"
    key_promote = f"wsc_promote_temporary_{conv_id}_{source_id}"
    
    assert key_nb == "wsc_source_notebook_conv_abc_src_123"
    assert key_temp == "wsc_source_temporary_conv_abc_src_123"
    assert key_promote == "wsc_promote_temporary_conv_abc_src_123"

def test_conversation_isolation_store(mock_streamlit_app):
    store.set_source_enabled("conv_1", SOURCE_SCOPE_NOTEBOOK, "src_nb", True)
    store.set_source_enabled("conv_2", SOURCE_SCOPE_NOTEBOOK, "src_nb", False)
    
    selections_1 = store.load_conversation_source_selections("conv_1")
    selections_2 = store.load_conversation_source_selections("conv_2")
    
    assert len(selections_1) == 1
    assert selections_1[0].enabled is True
    
    assert len(selections_2) == 1
    assert selections_2[0].enabled is False

def test_app_wiring_structure():
    import ast
    app_path = Path("src/aios_habit/workspace_chat_app.py")
    source = app_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    
    # 3.1 & 3.2: Notebook/Temporary toggle scope checks
    class ToggleChecker(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if node.name == "on_toggle_notebook":
                calls = [c for c in ast.walk(node) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "set_source_enabled"]
                assert len(calls) == 1
                args = calls[0].args
                assert len(args) >= 4
                assert isinstance(args[1], ast.Name) and args[1].id == "SOURCE_SCOPE_NOTEBOOK"
                
            elif node.name == "on_toggle_temporary":
                calls = [c for c in ast.walk(node) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "set_source_enabled"]
                assert len(calls) == 1
                args = calls[0].args
                assert len(args) >= 4
                assert isinstance(args[1], ast.Name) and args[1].id == "SOURCE_SCOPE_TEMPORARY"
            self.generic_visit(node)
            
    ToggleChecker().visit(tree)

    # 3.3: Temporary source submit order check: save -> enable -> rerun
    save_idx = source.find("save_temporary_source(ts)")
    enable_idx = source.find("set_source_enabled(active_conversation.id, SOURCE_SCOPE_TEMPORARY, ts.id, True)")
    rerun_idx = source.find("safe_rerun()", enable_idx)
    
    assert save_idx != -1, "save_temporary_source(ts) not found in app"
    assert enable_idx != -1, "set_source_enabled for temporary not found in app"
    assert rerun_idx != -1, "safe_rerun() after enable not found in app"
    assert save_idx < enable_idx < rerun_idx, "Incorrect submit order: save, enable, then rerun required!"

    # 3.4: Promotion wiring check: promote -> rerun, without calling set_source_enabled in promote block
    class PromoteChecker(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if node.name == "on_promote_temporary":
                calls = [c for c in ast.walk(node) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)]
                call_names = {c.func.id for c in calls}
                assert "promote_temporary_source_to_notebook" in call_names
                assert "safe_rerun" in call_names
                assert "set_source_enabled" not in call_names
            self.generic_visit(node)
            
    PromoteChecker().visit(tree)


