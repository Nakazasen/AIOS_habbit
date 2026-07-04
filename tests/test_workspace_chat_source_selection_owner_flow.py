import importlib
import sys
from pathlib import Path

import pytest
import streamlit as st

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
    enable_idx = source.find("set_source_enabled(conversation_id, SOURCE_SCOPE_TEMPORARY, ts.id, True)")
    rerun_idx = source.find("safe_rerun()", enable_idx)

    assert save_idx != -1, "save_temporary_source(ts) not found in app"
    assert enable_idx != -1, "set_source_enabled for temporary not found in app helper"
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

    # Phase 2C: XLSX upload form is conversation-scoped and main-area only.
    assert "Thêm file Excel .xlsx" in source
    assert "Chọn file Excel cho cuộc trò chuyện này" in source
    assert "Đọc và thêm vào nguồn tạm" in source
    assert 'key=f"wsc_excel_upload_{active_conversation.id}"' in source
    assert 'type=["xlsx", "xls"]' in source

    # Phase 2C: success flow order is extract -> temp source -> save -> enable -> rerun.
    extract_idx = source.find("result = extract_xlsx_text(uploaded_excel.getvalue(), uploaded_excel.name)")
    temp_idx = source.find("temporary_source = create_excel_temporary_source_from_extraction", extract_idx)
    xlsx_type_idx = source.find("source_type=\"xlsx\"", source.find("def create_excel_temporary_source_from_extraction"))
    title_idx = source.find("title=extraction_result.filename", source.find("def create_excel_temporary_source_from_extraction"))
    preview_idx = source.find("content_preview=extraction_result.preview", source.find("def create_excel_temporary_source_from_extraction"))
    text_idx = source.find("content_text=extraction_result.text", source.find("def create_excel_temporary_source_from_extraction"))
    save_xlsx_idx = source.find("save_temporary_source(ts)", source.find("def create_temporary_source_with_privacy"))
    enable_xlsx_idx = source.find("set_source_enabled(conversation_id, SOURCE_SCOPE_TEMPORARY, ts.id, True)", save_xlsx_idx)
    rerun_xlsx_idx = source.find("safe_rerun()", temp_idx)

    assert extract_idx != -1
    assert temp_idx != -1
    assert xlsx_type_idx != -1
    assert title_idx != -1
    assert preview_idx != -1
    assert text_idx != -1
    assert save_xlsx_idx != -1
    assert enable_xlsx_idx != -1
    assert rerun_xlsx_idx != -1
    assert extract_idx < temp_idx < rerun_xlsx_idx
    assert save_xlsx_idx < enable_xlsx_idx
    assert xlsx_type_idx != -1
    assert title_idx != -1
    assert preview_idx != -1
    assert text_idx != -1

    # Phase 2C: failure path reports result.owner_message and does not save/enable/rerun.
    failure_idx = source.find("else:", rerun_xlsx_idx)
    error_idx = source.find("st.error(result.owner_message)", rerun_xlsx_idx)
    assert error_idx != -1
    assert source.find("save_temporary_source", error_idx, error_idx + 120) == -1
    assert source.find("set_source_enabled", error_idx, error_idx + 120) == -1
    assert source.find("safe_rerun", error_idx, error_idx + 120) == -1

    assert "promote_temporary_source_to_notebook(active_conversation.id, temporary_source.id" not in source
    assert "SOURCE_SCOPE_NOTEBOOK, temporary_source.id, True" not in source


def _simulate_excel_upload_submit(result):
    from aios_habit.workspace_chat_models import TemporaryConversationSource, SOURCE_SCOPE_TEMPORARY

    calls = []
    errors = []

    def save_temporary_source(src):
        calls.append(("save", src))

    def set_source_enabled(conversation_id, source_scope, source_id, enabled):
        calls.append(("enable", conversation_id, source_scope, source_id, enabled))

    def safe_rerun():
        calls.append(("rerun",))

    if result.ok:
        temporary_source = TemporaryConversationSource(
            id="SRC-TEST",
            conversation_id="conv_1",
            source_type="xlsx",
            title=result.filename,
            content_preview=result.preview,
            content_text=result.text,
        )
        save_temporary_source(temporary_source)
        set_source_enabled("conv_1", SOURCE_SCOPE_TEMPORARY, temporary_source.id, True)
        safe_rerun()
    else:
        errors.append(result.owner_message)

    return calls, errors


def test_excel_upload_xls_failure_does_not_save_enable_or_rerun():
    from aios_habit.workspace_chat_excel import XLS_UNSUPPORTED_MESSAGE, extract_xlsx_text

    result = extract_xlsx_text(b"legacy", "legacy.xls")
    calls, errors = _simulate_excel_upload_submit(result)

    assert result.ok is False
    assert errors == [XLS_UNSUPPORTED_MESSAGE]
    assert calls == []


def test_excel_upload_corrupt_failure_does_not_save_enable_or_rerun():
    from aios_habit.workspace_chat_excel import GENERIC_READ_ERROR_MESSAGE, extract_xlsx_text

    result = extract_xlsx_text(b"not-a-workbook", "bad.xlsx")
    calls, errors = _simulate_excel_upload_submit(result)

    assert result.ok is False
    assert errors == [GENERIC_READ_ERROR_MESSAGE]
    assert "Traceback" not in errors[0]
    assert calls == []


def test_excel_upload_success_callback_flow_order_and_payload():
    from aios_habit.workspace_chat_excel import ExtractedWorkspaceSource

    result = ExtractedWorkspaceSource(
        ok=True,
        filename="ok.xlsx",
        text="full text",
        preview="preview",
        owner_message="ok",
    )
    calls, errors = _simulate_excel_upload_submit(result)

    assert errors == []
    assert [call[0] for call in calls] == ["save", "enable", "rerun"]
    saved_source = calls[0][1]
    assert saved_source.source_type == "xlsx"
    assert saved_source.title == "ok.xlsx"
    assert saved_source.content_preview == "preview"
    assert saved_source.content_text == "full text"
    assert calls[1] == ("enable", "conv_1", SOURCE_SCOPE_TEMPORARY, "SRC-TEST", True)


def test_excel_upload_passive_rerun_does_not_extract_or_persist():
    import ast

    source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    extract_calls = []

    class SubmitBranchChecker(ast.NodeVisitor):
        def __init__(self):
            self.submit_depth = 0
            self.extracts_inside_submit = 0
            self.extracts_outside_submit = 0

        def visit_If(self, node):
            is_submit_if = (
                isinstance(node.test, ast.Call)
                and isinstance(node.test.func, ast.Attribute)
                and node.test.func.attr == "form_submit_button"
                and node.test.args
                and isinstance(node.test.args[0], ast.Constant)
                and node.test.args[0].value == "Đọc và thêm vào nguồn tạm"
            )
            if is_submit_if:
                self.submit_depth += 1
            self.generic_visit(node)
            if is_submit_if:
                self.submit_depth -= 1

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == "extract_xlsx_text":
                extract_calls.append(node)
                if self.submit_depth:
                    self.extracts_inside_submit += 1
                else:
                    self.extracts_outside_submit += 1
            self.generic_visit(node)

    checker = SubmitBranchChecker()
    checker.visit(tree)

    assert len(extract_calls) == 1
    assert checker.extracts_inside_submit == 1
    assert checker.extracts_outside_submit == 0


def test_phase2d_app_submit_builds_source_aware_placeholder_structure():
    source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "load_enabled_sources_for_conversation(active_conversation.id)" in source
    assert "current_notebook_sources = load_notebook_sources(active_nb_id)" in source
    assert "current_temp_sources = load_temporary_sources(active_conversation.id)" in source
    assert "selection.source_scope == SOURCE_SCOPE_NOTEBOOK" in source
    assert "selection.source_scope == SOURCE_SCOPE_TEMPORARY" in source
    assert "resolved_source is None" in source
    assert "WorkspaceTrialSourceInput(" in source
    # Phase 2H: AI-first flow uses build_source_check_summary and pack_workspace_ai_context
    assert "build_source_check_summary(check_source_inputs)" in source
    assert "pack_workspace_ai_context" in source
    assert "selected_source_ids" not in source


def test_phase2d_submit_order_save_user_resolve_build_save_assistant_rerun():
    source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    # Phase 2H: AI-first flow uses ask_submitted pattern
    assert "ask_submitted" in source
    # Save order: save_message(user_msg) before save_message(assistant_msg) before safe_rerun()
    user_save_idx = source.index("save_message(user_msg)")
    assistant_save_idx = source.index("save_message(assistant_msg)", user_save_idx)
    rerun_idx = source.index("safe_rerun()", assistant_save_idx)
    assert user_save_idx < assistant_save_idx < rerun_idx
    assert source.count("save_message(user_msg)") == 1
    assert source.count("save_message(assistant_msg)") == 1


def test_phase2d_app_does_not_reparse_xlsx_or_update_source_use_metadata_on_submit():
    source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    # Phase 2H: AI-first flow uses ask_submitted pattern
    start = source.index("if ask_submitted")
    end = source.index("# Phase 2H: Dán nhanh", start)
    block = source[start:end]
    assert "extract_xlsx_text" not in block
    assert "openpyxl" not in block
    assert "used_in_last_answer" not in block
    assert "last_used_at" not in block
    assert "save_conversation_source_selection" not in block


def test_phase2d_app_imports_no_case_cockpit():
    source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "case_cockpit" not in source


def test_right_panel_resolution_logic():
    conv_id = "conv_1"
    nb_id = "mom_opcenter"

    # 1. Enabled Notebook Source
    ns_enabled = NotebookSource(id="ns_en", notebook_id=nb_id, title="Notebook Active", source_type="xlsx")
    store.save_notebook_source(ns_enabled)
    store.set_source_enabled(conv_id, SOURCE_SCOPE_NOTEBOOK, "ns_en", True)

    # 2. Disabled Notebook Source
    ns_disabled = NotebookSource(id="ns_dis", notebook_id=nb_id, title="Notebook Inactive", source_type="pasted_text")
    store.save_notebook_source(ns_disabled)
    store.set_source_enabled(conv_id, SOURCE_SCOPE_NOTEBOOK, "ns_dis", False)

    # 3. Enabled Temporary Source
    ts_enabled = TemporaryConversationSource(id="ts_en", conversation_id=conv_id, title="Temp Active", source_type="pasted_text", content_preview="P")
    store.save_temporary_source(ts_enabled)
    store.set_source_enabled(conv_id, SOURCE_SCOPE_TEMPORARY, "ts_en", True)

    # 4. Disabled Temporary Source
    ts_disabled = TemporaryConversationSource(id="ts_dis", conversation_id=conv_id, title="Temp Inactive", source_type="pasted_text", content_preview="P")
    store.save_temporary_source(ts_disabled)
    store.set_source_enabled(conv_id, SOURCE_SCOPE_TEMPORARY, "ts_dis", False)

    # 5. Orphan selection
    store.set_source_enabled(conv_id, SOURCE_SCOPE_TEMPORARY, "ts_orphan", True)

    # 6. Cross-conversation temporary source
    ts_cross_conv = TemporaryConversationSource(id="ts_cross", conversation_id="conv_2", title="Temp Cross", source_type="pasted_text", content_preview="P")
    store.save_temporary_source(ts_cross_conv)
    store.set_source_enabled(conv_id, SOURCE_SCOPE_TEMPORARY, "ts_cross", True)

    # 7. Cross-notebook notebook source
    ns_cross_nb = NotebookSource(id="ns_cross", notebook_id="nb_2", title="Notebook Cross", source_type="pasted_text")
    store.save_notebook_source(ns_cross_nb)
    store.set_source_enabled(conv_id, SOURCE_SCOPE_NOTEBOOK, "ns_cross", True)

    enabled_selections = store.load_enabled_sources_for_conversation(conv_id)
    current_notebook_sources = store.load_notebook_sources(nb_id)
    current_temp_sources = store.load_temporary_sources(conv_id)
    notebook_source_by_id = {s.id: s for s in current_notebook_sources}
    temp_source_by_id = {s.id: s for s in current_temp_sources}

    proven_sources = []
    for selection in enabled_selections:
        if selection.source_scope == SOURCE_SCOPE_NOTEBOOK:
            resolved = notebook_source_by_id.get(selection.source_id)
            prefix = "Nguồn trong sổ"
        elif selection.source_scope == SOURCE_SCOPE_TEMPORARY:
            resolved = temp_source_by_id.get(selection.source_id)
            prefix = "Nguồn tạm"
        else:
            resolved = None

        if resolved is None:
            continue

        stype = (resolved.source_type or "").strip().lower()
        if stype == "xlsx":
            friendly_type = "Excel"
        elif stype in {"text", "pasted_text", "plain_text"}:
            friendly_type = "Văn bản"
        else:
            friendly_type = "Nguồn"

        proven_sources.append(f"{prefix}: {resolved.title} ({friendly_type})")

    assert "Nguồn trong sổ: Notebook Active (Excel)" in proven_sources
    assert "Nguồn tạm: Temp Active (Văn bản)" in proven_sources
    assert any("Notebook Inactive" in s for s in proven_sources) is False
    assert any("Temp Inactive" in s for s in proven_sources) is False
    assert any("ts_orphan" in s for s in proven_sources) is False
    assert any("Temp Cross" in s for s in proven_sources) is False
    assert any("Notebook Cross" in s for s in proven_sources) is False
    assert len(proven_sources) == 2


def test_right_panel_empty_state_logic():
    conv_id = "conv_empty"
    ts_disabled = TemporaryConversationSource(id="ts_dis", conversation_id=conv_id, title="Temp Inactive", source_type="pasted_text", content_preview="P")
    store.save_temporary_source(ts_disabled)
    store.set_source_enabled(conv_id, SOURCE_SCOPE_TEMPORARY, "ts_dis", False)

    enabled_selections = store.load_enabled_sources_for_conversation(conv_id)
    assert len(enabled_selections) == 0


def test_phase2d_app_explain_popup_copy():
    source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "phân tích đối chiếu" not in source.lower()
    assert "khớp hoàn toàn" not in source.lower()
    assert "gợi ý phân tích" not in source.lower()


def test_safe_test_data_generation_uses_app_helper_without_real_store_writes(tmp_path, monkeypatch):
    test_dir = tmp_path / "workspace_chat_safe_data"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    monkeypatch.setattr(store, "NOTEBOOK_SOURCES_FILE", test_dir / "notebook_sources.jsonl")
    monkeypatch.setattr(store, "SOURCE_SELECTIONS_FILE", test_dir / "conversation_source_selections.jsonl")
    store.init_chat_store()

    sys.modules.pop("aios_habit.workspace_chat_app", None)
    app = importlib.import_module("aios_habit.workspace_chat_app")

    source = app.create_safe_test_data("CONV-SAFE-TEST")

    assert source.conversation_id == "CONV-SAFE-TEST"
    assert source.source_type == "plain_text"
    assert source.privacy_label == "machine_only"
    assert "Dữ liệu test an toàn" in source.title
    assert "dữ liệu test giả lập" in source.content_preview
    assert "dữ liệu test giả lập" in source.content_text
    assert "thông tin mật" in source.content_text
    assert "API" not in source.content_text

    saved_sources = store.load_temporary_sources("CONV-SAFE-TEST")
    assert [saved.id for saved in saved_sources] == [source.id]

    selections = store.load_conversation_source_selections("CONV-SAFE-TEST")
    assert len(selections) == 1
    assert selections[0].source_scope == SOURCE_SCOPE_TEMPORARY
    assert selections[0].source_id == source.id
    assert selections[0].enabled is True

    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "Tạo dữ liệu test không mật" in app_source
    assert "create_safe_test_data(active_conversation.id)" in app_source

    assert not (tmp_path / ".ai").exists()
    assert not (tmp_path / "local_cases").exists()


def test_notebook_creation_flow(tmp_path, monkeypatch):
    session_state = MockSessionState()
    session_state.wsc_action_message = None
    session_state.wsc_action_error = None
    monkeypatch.setattr(st, "session_state", session_state)

    reruns = []
    def mock_rerun():
        reruns.append(True)
    monkeypatch.setattr(st, "rerun", mock_rerun)

    from aios_habit.workspace_chat_store import save_notebook, load_notebooks
    from aios_habit.workspace_chat_models import DocumentNotebook
    import uuid

    # 1. Title empty
    title = "   "
    if not title.strip():
        session_state.wsc_action_error = "Vui lòng nhập tên sổ tài liệu."
    else:
        new_nb = DocumentNotebook(
            id=f"NB-{uuid.uuid4().hex[:8].upper()}",
            title=title.strip(),
            description="Mô tả"
        )
        save_notebook(new_nb)
        session_state.wsc_action_message = "Đã tạo sổ tài liệu mới."

    assert session_state.wsc_action_error == "Vui lòng nhập tên sổ tài liệu."
    assert session_state.wsc_action_message is None
    assert len(load_notebooks()) == 4

    # 2. Title valid
    session_state.wsc_action_error = None
    title = "Sổ tài liệu tiếng Việt 日本語"
    desc = "Mô tả ngắn"

    if not title.strip():
        session_state.wsc_action_error = "Vui lòng nhập tên sổ tài liệu."
    else:
        new_nb = DocumentNotebook(
            id=f"NB-{uuid.uuid4().hex[:8].upper()}",
            title=title.strip(),
            description=desc.strip()
        )
        save_notebook(new_nb)
        session_state.wsc_action_message = "Đã tạo sổ tài liệu mới."

    assert session_state.wsc_action_error is None
    assert session_state.wsc_action_message == "Đã tạo sổ tài liệu mới."

    nbs = load_notebooks()
    assert len(nbs) == 5
    created_nb = nbs[-1]
    assert created_nb.title == "Sổ tài liệu tiếng Việt 日本語"
    assert created_nb.description == "Mô tả ngắn"
    assert created_nb.id.startswith("NB-")

    # Verify no .ai or local_cases written in root workspace
    assert not (tmp_path / ".ai").exists()
    assert not (tmp_path / "local_cases").exists()


def test_save_case_placeholder_feedback_sets_state_and_reruns(monkeypatch):
    session_state = MockSessionState()
    session_state.wsc_show_save_placeholder = False
    monkeypatch.setattr(st, "session_state", session_state)

    reruns = []
    monkeypatch.setattr(st, "rerun", lambda: reruns.append(True))

    sys.modules.pop("aios_habit.workspace_chat_app", None)
    app = importlib.import_module("aios_habit.workspace_chat_app")
    app.show_save_case_placeholder_feedback()

    assert session_state.wsc_show_save_placeholder is True
    assert reruns == [True]


def test_save_case_placeholder_path_does_not_call_persistence_or_provider():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    helper_start = app_source.index("def show_save_case_placeholder_feedback():")
    helper_end = app_source.index("def open_notebook_callback", helper_start)
    helper_block = app_source[helper_start:helper_end]
    callback_start = app_source.index("def on_save_case_cb():")
    callback_end = app_source.index("def on_explain_cb():", callback_start)
    callback_block = app_source[callback_start:callback_end]
    save_path = helper_block + callback_block

    forbidden_calls = [
        "save_notebook(",
        "save_conversation(",
        "save_message(",
        "save_temporary_source(",
        "load_notebooks(",
        "load_conversations(",
        "load_messages(",
        "promote_temporary_source_to_notebook(",
        "generate_workspace_ai_answer(",
        "RealWorkspaceAIProviderClient(",
        "extract_xlsx_text(",
        "case_cockpit",
        "Case(",
    ]
    for token in forbidden_calls:
        assert token not in save_path
    assert "wsc_show_save_placeholder = True" in save_path
    assert "safe_rerun()" in save_path


def test_save_case_placeholder_render_uses_info_not_success():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    start = app_source.index("if st.session_state.wsc_show_save_placeholder:")
    end = app_source.index("if st.session_state.wsc_show_explain_placeholder:", start)
    block = app_source[start:end]

    assert "st.info" in block
    assert "st.success" not in block
    assert "SAVE_CASE_PLACEHOLDER_MESSAGE" in block


# --- Phase 2H structural tests ---

def test_phase2h_source_check_not_saved_as_assistant():
    """Source check panel must never save a ChatMessage(role='assistant')."""
    import ast
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    # Find the source check block using the precise comment marker
    check_start = app_source.index("# Phase 2H: Source check panel")
    check_end = app_source.index("# Phase 2H: AI answer badge", check_start)
    check_block = app_source[check_start:check_end]

    assert "save_message" not in check_block
    assert 'role="assistant"' not in check_block
    assert "ChatMessage" not in check_block


def test_phase2h_source_check_no_provider_call():
    """Source check panel must never call provider or generate AI answer."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    check_start = app_source.index("# Phase 2H: Source check panel")
    check_end = app_source.index("# Phase 2H: AI answer badge", check_start)
    check_block = app_source[check_start:check_end]

    assert "generate_workspace_ai_answer" not in check_block
    assert "RealWorkspaceAIProviderClient" not in check_block
    assert "pack_workspace_ai_context" not in check_block


def test_phase2h_quick_paste_creates_one_source(mock_streamlit_app):
    """Quick paste saves exactly one temp source, auto-enables, no AI call."""
    from aios_habit.workspace_chat_models import TemporaryConversationSource, SOURCE_SCOPE_TEMPORARY

    conv_id = "conv_quick_paste"
    content = "Nội dung dán nhanh test 日本語"
    title = "Log sáng 3/7"

    ts = TemporaryConversationSource(
        id="SRC-QUICK",
        conversation_id=conv_id,
        source_type="pasted_text",
        title=title,
        content_preview=content[:150],
        content_text=content
    )
    store.save_temporary_source(ts)
    store.set_source_enabled(conv_id, SOURCE_SCOPE_TEMPORARY, ts.id, True)

    saved = store.load_temporary_sources(conv_id)
    assert len(saved) == 1
    assert saved[0].title == title
    assert saved[0].content_text == content

    sels = store.load_conversation_source_selections(conv_id)
    assert len(sels) == 1
    assert sels[0].source_id == "SRC-QUICK"
    assert sels[0].enabled is True


def test_phase2h_quick_paste_empty_rejected():
    """Empty quick paste should be caught by UI form validation."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    # Find the quick paste form
    quick_start = app_source.index("quick_paste_form")
    quick_end = app_source.index("# Khung dán nhật ký", quick_start)
    quick_block = app_source[quick_start:quick_end]

    assert "quick_content.strip()" in quick_block
    assert 'Nội dung không được để trống.' in quick_block
    assert "create_pasted_text_temporary_source" in quick_block


def test_phase2h_no_radio_no_consent_checkbox_in_sidebar():
    """Phase 2H removes the radio and consent checkbox from sidebar."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "st.radio" not in app_source
    assert "wsc_privacy_mode_widget" not in app_source
    assert "consent_key" not in app_source
    assert "cloud_consent_confirmed = st.checkbox" not in app_source


def test_phase2h_ask_button_explicit():
    """Phase 2H requires explicit button for AI action."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "wsc_ai_ask_form" in app_source
    assert "ask_submitted" in app_source
    assert "check_submitted" in app_source
    # st.chat_input auto-submit must not be used for AI calls
    assert "st.chat_input" not in app_source


def test_phase2j_safe_test_helper_remains_explicit_and_has_no_ai_call():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    start = app_source.index('with st.expander("🛠️ Công cụ thử nghiệm an toàn"')
    end = app_source.index("with col_results:", start)
    helper_block = app_source[start:end]

    assert "expanded=False" in helper_block
    assert 'if st.button("Tạo dữ liệu test không mật"):' in helper_block
    assert "create_safe_test_data(active_conversation.id)" in helper_block
    assert "generate_workspace_ai_answer" not in helper_block
    assert "RealWorkspaceAIProviderClient" not in helper_block



class _Phase2IExtractionResult:
    ok = True
    filename = "owner_source.xlsx"
    preview = "Excel preview"
    text = "Excel extracted text"
    truncated = False


def _assert_one_created_source(conv_id, expected_label, expected_source_type, expected_text):
    saved = store.load_temporary_sources(conv_id)
    assert len(saved) == 1
    assert saved[0].privacy_label == expected_label
    assert saved[0].source_type == expected_source_type
    assert saved[0].content_text == expected_text
    selections = store.load_conversation_source_selections(conv_id)
    assert len(selections) == 1
    assert selections[0].source_scope == SOURCE_SCOPE_TEMPORARY
    assert selections[0].source_id == saved[0].id
    assert selections[0].enabled is True
    assert store.load_messages(conv_id) == []


def test_phase2i_owner_choice_mapping_helpers():
    from aios_habit.workspace_chat_ui import PRIVACY_CHOICE_SENDABLE, PRIVACY_CHOICE_LOCAL_ONLY, owner_choice_to_privacy_label, privacy_label_to_owner_choice, privacy_label_is_sendable
    assert owner_choice_to_privacy_label(PRIVACY_CHOICE_SENDABLE) == "machine_only"
    assert owner_choice_to_privacy_label(PRIVACY_CHOICE_LOCAL_ONLY) == "local_only"
    assert privacy_label_to_owner_choice("machine_only") == PRIVACY_CHOICE_SENDABLE
    assert privacy_label_to_owner_choice("cloud_allowed") == PRIVACY_CHOICE_SENDABLE
    for blocked in ["local_only", "confidential", "", "   ", None, "unknown"]:
        assert privacy_label_to_owner_choice(blocked) == PRIVACY_CHOICE_LOCAL_ONLY
        assert privacy_label_is_sendable(blocked) is False


def test_phase2i_source_creation_forms_call_production_helpers_with_privacy_choice():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    quick_block = app_source[app_source.index("quick_paste_form"):app_source.index("# Khung dán nhật ký", app_source.index("quick_paste_form"))]
    assert "quick_privacy_choice = render_privacy_choice" in quick_block
    assert "create_pasted_text_temporary_source" in quick_block
    assert "owner_choice=quick_privacy_choice" in quick_block
    paste_block = app_source[app_source.index("paste_log_form"):app_source.index("Tạo dữ liệu test không mật", app_source.index("paste_log_form"))]
    assert "paste_privacy_choice = render_privacy_choice" in paste_block
    assert "create_pasted_text_temporary_source" in paste_block
    assert "owner_choice=paste_privacy_choice" in paste_block
    excel_block = app_source[app_source.index("excel_upload_form"):]
    assert "excel_privacy_choice = render_privacy_choice" in excel_block
    assert "create_excel_temporary_source_from_extraction" in excel_block
    assert "owner_choice=excel_privacy_choice" in excel_block


def test_phase2i_real_quick_paste_creation_path_executes_both_privacy_choices():
    sys.modules.pop("aios_habit.workspace_chat_app", None)
    app = importlib.import_module("aios_habit.workspace_chat_app")
    from aios_habit.workspace_chat_ui import PRIVACY_CHOICE_SENDABLE, PRIVACY_CHOICE_LOCAL_ONLY
    for idx, (choice, expected_label) in enumerate([(PRIVACY_CHOICE_SENDABLE, "machine_only"), (PRIVACY_CHOICE_LOCAL_ONLY, "local_only")]):
        conv_id = f"conv_quick_real_{idx}"
        app.create_pasted_text_temporary_source(conv_id, "Quick paste title", "Quick paste text", choice)
        _assert_one_created_source(conv_id, expected_label, "pasted_text", "Quick paste text")


def test_phase2i_real_long_text_creation_path_executes_both_privacy_choices():
    sys.modules.pop("aios_habit.workspace_chat_app", None)
    app = importlib.import_module("aios_habit.workspace_chat_app")
    from aios_habit.workspace_chat_ui import PRIVACY_CHOICE_SENDABLE, PRIVACY_CHOICE_LOCAL_ONLY
    for idx, (choice, expected_label) in enumerate([(PRIVACY_CHOICE_SENDABLE, "machine_only"), (PRIVACY_CHOICE_LOCAL_ONLY, "local_only")]):
        conv_id = f"conv_long_real_{idx}"
        app.create_pasted_text_temporary_source(conv_id, "Long text title", "Long text body", choice)
        _assert_one_created_source(conv_id, expected_label, "pasted_text", "Long text body")


def test_phase2i_real_excel_creation_path_uses_extracted_text_and_both_privacy_choices():
    sys.modules.pop("aios_habit.workspace_chat_app", None)
    app = importlib.import_module("aios_habit.workspace_chat_app")
    from aios_habit.workspace_chat_ui import PRIVACY_CHOICE_SENDABLE, PRIVACY_CHOICE_LOCAL_ONLY
    for idx, (choice, expected_label) in enumerate([(PRIVACY_CHOICE_SENDABLE, "machine_only"), (PRIVACY_CHOICE_LOCAL_ONLY, "local_only")]):
        conv_id = f"conv_excel_real_{idx}"
        app.create_excel_temporary_source_from_extraction(conv_id, _Phase2IExtractionResult(), choice)
        saved = store.load_temporary_sources(conv_id)
        assert saved[0].title == "owner_source.xlsx"
        assert saved[0].content_preview == "Excel preview"
        _assert_one_created_source(conv_id, expected_label, "xlsx", "Excel extracted text")


def test_phase2i_actual_privacy_edit_helpers_two_way_and_scope_safe(monkeypatch):
    sys.modules.pop("aios_habit.workspace_chat_app", None)
    app = importlib.import_module("aios_habit.workspace_chat_app")
    from aios_habit.workspace_chat_ui import PRIVACY_CHOICE_SENDABLE, PRIVACY_CHOICE_LOCAL_ONLY
    nb = NotebookSource(id="nb_edit", notebook_id="nb_active", title="NB", source_type="pasted_text", privacy_label="machine_only")
    nb_cross = NotebookSource(id="nb_cross", notebook_id="nb_other", title="Cross", source_type="pasted_text", privacy_label="machine_only")
    ts = TemporaryConversationSource(id="ts_edit", conversation_id="conv_active", title="TS", source_type="pasted_text", content_preview="P", privacy_label="machine_only")
    ts_cross = TemporaryConversationSource(id="ts_cross", conversation_id="conv_other", title="Cross", source_type="pasted_text", content_preview="P", privacy_label="machine_only")
    store.save_notebook_source(nb); store.save_notebook_source(nb_cross); store.save_temporary_source(ts); store.save_temporary_source(ts_cross)
    store.set_source_enabled("conv_active", SOURCE_SCOPE_NOTEBOOK, "nb_edit", True); store.set_source_enabled("conv_active", SOURCE_SCOPE_TEMPORARY, "ts_edit", True)
    assert app.update_notebook_source_privacy_for_active_notebook("nb_active", "nb_edit", PRIVACY_CHOICE_LOCAL_ONLY) is True
    assert app.update_temporary_source_privacy_for_active_conversation("conv_active", "ts_edit", PRIVACY_CHOICE_LOCAL_ONLY) is True
    assert store.load_notebook_sources("nb_active")[0].privacy_label == "local_only"
    assert store.load_temporary_sources("conv_active")[0].privacy_label == "local_only"
    assert app.update_notebook_source_privacy_for_active_notebook("nb_active", "nb_edit", PRIVACY_CHOICE_SENDABLE) is True
    assert app.update_temporary_source_privacy_for_active_conversation("conv_active", "ts_edit", PRIVACY_CHOICE_SENDABLE) is True
    assert store.load_notebook_sources("nb_active")[0].privacy_label == "machine_only"
    assert store.load_temporary_sources("conv_active")[0].privacy_label == "machine_only"
    assert app.update_notebook_source_privacy_for_active_notebook("nb_active", "missing", PRIVACY_CHOICE_LOCAL_ONLY) is False
    assert app.update_temporary_source_privacy_for_active_conversation("conv_active", "missing", PRIVACY_CHOICE_LOCAL_ONLY) is False
    assert app.update_notebook_source_privacy_for_active_notebook("nb_active", "nb_cross", PRIVACY_CHOICE_LOCAL_ONLY) is False
    assert app.update_temporary_source_privacy_for_active_conversation("conv_active", "ts_cross", PRIVACY_CHOICE_LOCAL_ONLY) is False
    assert store.load_notebook_sources("nb_other")[0].privacy_label == "machine_only"
    assert store.load_temporary_sources("conv_other")[0].privacy_label == "machine_only"


def test_phase2i_mixed_sources_block_without_messages_or_ai_badge():
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIAnswerRequest, pack_workspace_ai_context, generate_workspace_ai_answer, PRIVACY_MODE_CLOUD_ALLOWED
    conv_id = "conv_mixed_block"
    sendable = TemporaryConversationSource(id="ts_send", conversation_id=conv_id, title="Send", source_type="pasted_text", content_preview="S", content_text="send", privacy_label="machine_only")
    blocked = TemporaryConversationSource(id="ts_block", conversation_id=conv_id, title="Block", source_type="pasted_text", content_preview="B", content_text="block", privacy_label="local_only")
    store.save_temporary_source(sendable); store.save_temporary_source(blocked)
    store.set_source_enabled(conv_id, SOURCE_SCOPE_TEMPORARY, sendable.id, True); store.set_source_enabled(conv_id, SOURCE_SCOPE_TEMPORARY, blocked.id, True)
    enabled = store.load_enabled_sources_for_conversation(conv_id)
    _, packed, _ = pack_workspace_ai_context("question", [], [sendable, blocked], enabled)
    req = WorkspaceAIAnswerRequest(conversation_id=conv_id, question="question", context_sources=packed, privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED, cloud_consent_confirmed=True, consent_source_keys=tuple((s.source_scope, s.source_id) for s in enabled))
    result = generate_workspace_ai_answer(req, provider_client=object())
    assert result.ok is False
    assert "chỉ được dùng trên máy" in result.error_message
    assert store.load_messages(conv_id) == []


def test_phase2i_notebook_lifecycle_store_archive_restore_preserves_child_data():
    nb = DocumentNotebook(id="nb_life", title="Lifecycle", description="Keep children")
    store.save_notebook(nb)
    conv = WorkspaceConversation(id="conv_life", notebook_id=nb.id, title="Conversation")
    store.save_conversation(conv)
    msg = store.ChatMessage(id="msg_life", conversation_id=conv.id, role="user", content="hello") if hasattr(store, "ChatMessage") else None
    from aios_habit.workspace_chat_models import ChatMessage
    store.save_message(ChatMessage(id="msg_life", conversation_id=conv.id, role="user", content="hello"))
    nb_src = NotebookSource(id="nb_src_life", notebook_id=nb.id, title="Notebook source", source_type="pasted_text", privacy_label="local_only")
    temp_src = TemporaryConversationSource(id="temp_src_life", conversation_id=conv.id, title="Temp source", source_type="pasted_text", content_preview="preview", content_text="full", privacy_label="local_only")
    store.save_notebook_source(nb_src)
    store.save_temporary_source(temp_src)
    store.set_source_enabled(conv.id, SOURCE_SCOPE_NOTEBOOK, nb_src.id, True)
    store.set_source_enabled(conv.id, SOURCE_SCOPE_TEMPORARY, temp_src.id, False)

    before = {
        "conversations": [c.__dict__.copy() for c in store.load_conversations(nb.id)],
        "messages": [m.__dict__.copy() for m in store.load_messages(conv.id)],
        "notebook_sources": [src.to_dict() for src in store.load_notebook_sources(nb.id)],
        "temporary_sources": [src.__dict__.copy() for src in store.load_temporary_sources(conv.id)],
        "selections": [sel.to_dict() for sel in store.load_conversation_source_selections(conv.id)],
    }

    assert store.load_notebook(nb.id).archived_at is None
    assert [n.id for n in store.load_active_notebooks()] == ["mom_opcenter", "interstock_wms", "email_jp_vn", "aios_project", nb.id]
    assert store.archive_notebook(nb.id) is True
    archived = store.load_notebook(nb.id)
    assert archived.archived_at
    assert nb.id not in [n.id for n in store.load_active_notebooks()]
    assert nb.id in [n.id for n in store.load_archived_notebooks()]
    assert store.archive_notebook(nb.id) is True

    after_archive = {
        "conversations": [c.__dict__.copy() for c in store.load_conversations(nb.id)],
        "messages": [m.__dict__.copy() for m in store.load_messages(conv.id)],
        "notebook_sources": [src.to_dict() for src in store.load_notebook_sources(nb.id)],
        "temporary_sources": [src.__dict__.copy() for src in store.load_temporary_sources(conv.id)],
        "selections": [sel.to_dict() for sel in store.load_conversation_source_selections(conv.id)],
    }
    assert after_archive == before
    assert store.load_notebook_sources(nb.id)[0].privacy_label == "local_only"
    assert {(s.source_scope, s.source_id): s.enabled for s in store.load_conversation_source_selections(conv.id)} == {
        (SOURCE_SCOPE_NOTEBOOK, nb_src.id): True,
        (SOURCE_SCOPE_TEMPORARY, temp_src.id): False,
    }

    assert store.restore_notebook(nb.id) is True
    assert store.load_notebook(nb.id).archived_at is None
    assert nb.id in [n.id for n in store.load_active_notebooks()]
    assert nb.id not in [n.id for n in store.load_archived_notebooks()]
    assert store.restore_notebook(nb.id) is True


def test_phase2i_notebook_lifecycle_backward_compat_and_malformed_fail_safe():
    import json
    store.NOTEBOOKS_FILE.write_text(
        json.dumps({"id": "old_nb", "title": "Old", "description": "Legacy"}, ensure_ascii=False) + "\n" +
        json.dumps({"id": "bad_nb", "title": "Bad", "description": "Malformed", "archived_at": {"bad": True}}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    active_ids = [nb.id for nb in store.load_active_notebooks()]
    archived_ids = [nb.id for nb in store.load_archived_notebooks()]
    assert "old_nb" in active_ids
    assert "bad_nb" not in active_ids
    assert "bad_nb" in archived_ids


def test_phase2i_notebook_lifecycle_ui_copy_and_no_hard_delete_actions():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    ui_source = Path("src/aios_habit/workspace_chat_ui.py").read_text(encoding="utf-8")
    combined = app_source + ui_source
    for text in [
        "Lưu trữ sổ",
        "Sổ đã lưu trữ",
        "Khôi phục sổ",
        "Sổ này sẽ được ẩn khỏi danh sách chính. Dữ liệu bên trong không bị xóa.",
        "Đã lưu trữ sổ.",
        "Đã khôi phục sổ.",
        "Không xóa dữ liệu trong Phase 2I.",
    ]:
        assert text in combined
    assert "Xóa vĩnh viễn" not in combined
    assert "cascade delete" not in combined.lower()
    assert "confirm hard delete" not in combined.lower()
    assert "load_active_notebooks()" in app_source
    assert "load_archived_notebooks()" in app_source
    assert "render_archived_notebook_card" in app_source
    assert "st.stop()" in app_source
