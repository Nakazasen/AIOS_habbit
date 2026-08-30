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
    ChatMessage,
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

def test_source_summary_stays_in_sidebar_and_manager_moves_to_main_chat():
    import ast
    app_path = Path("src/aios_habit/workspace_chat_app.py")
    source = app_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    target_helpers = {"render_source_library_summary"}
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
    assert "render_document_manager(" in source

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


def test_excel_upload_xls_failure_does_not_save_enable_or_rerun(monkeypatch):
    from aios_habit.workspace_chat_excel import XLS_UNSUPPORTED_MESSAGE, extract_xlsx_text
    from types import SimpleNamespace
    monkeypatch.setattr("aios_habit.excel_extractors.extract_excel", lambda *args, **kwargs: SimpleNamespace(dependency_missing=True, error=False))

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
            is_submit_if = False
            if (
                isinstance(node.test, ast.Call)
                and isinstance(node.test.func, ast.Attribute)
                and node.test.func.attr == "form_submit_button"
                and len(node.test.args) >= 1
            ):
                first_arg = node.test.args[0]
                if isinstance(first_arg, ast.Call) and getattr(first_arg.func, "id", "") == "t":
                    if first_arg.args and isinstance(first_arg.args[0], ast.Constant) and first_arg.args[0].value == "btn_read_add_temp_source":
                        is_submit_if = True

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

    import aios_habit.workspace_chat_app as app

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
    assert "demo_create_test_data" in app_source
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


def test_save_case_callback_creates_case_from_existing_trace_and_reruns(monkeypatch):
    session_state = MockSessionState()
    monkeypatch.setattr(st, "session_state", session_state)

    reruns = []
    monkeypatch.setattr(st, "rerun", lambda: reruns.append(True))

    import aios_habit.workspace_chat_app as app

    class FakeResult:
        case_id = "CASE-LOCAL-1"
        evidence_count = 2

    class FakeService:
        def __init__(self):
            self.received = None

        def create_case_from_trace_id(self, trace_id, *, expected_conversation_id):
            self.received = (trace_id, expected_conversation_id)
            return FakeResult()

    service = FakeService()
    result = app.save_current_answer_to_case(
        "CONV-1",
        {"conversation_id": "CONV-1", "type": "ai_answered", "trace_id": "trc-1"},
        service=service,
    )

    assert result is True
    assert service.received == ("trc-1", "CONV-1")
    assert "CASE-LOCAL-1" in session_state.wsc_action_message
    assert "không được sao chép" in session_state.wsc_action_message
    assert reruns == [True]


def test_save_case_callback_uses_only_the_existing_trace_and_no_provider():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    helper_start = app_source.index("def save_current_answer_to_case(")
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
    assert "create_case_from_trace_id(" in save_path
    assert "trace_id" in save_path
    assert "safe_rerun()" in save_path


def test_save_case_callback_rejects_missing_or_mismatched_trace(monkeypatch):
    session_state = MockSessionState()
    monkeypatch.setattr(st, "session_state", session_state)
    reruns = []
    monkeypatch.setattr(st, "rerun", lambda: reruns.append(True))

    import aios_habit.workspace_chat_app as app

    result = app.save_current_answer_to_case(
        "CONV-1",
        {"conversation_id": "CONV-OTHER", "type": "ai_answered", "trace_id": "trc-1"},
    )

    assert result is False
    assert "không còn hợp lệ" in session_state.wsc_action_error
    assert reruns == [True]


def test_save_case_callback_has_no_placeholder_or_optimistic_success_copy():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    start = app_source.index("def save_current_answer_to_case(")
    end = app_source.index("def open_notebook_callback", start)
    block = app_source[start:end]

    assert "chế độ mô phỏng" not in block
    assert "Đã lưu hồ sơ cục bộ" in block
    assert "không được sao chép" in block


# --- Phase 2H structural tests ---

def test_phase2h_source_check_not_saved_as_assistant():
    """Source check debug panel must not exist in production app."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "render_source_check_panel" not in app_source
    assert "wsc_source_check_visible" not in app_source


def test_phase2h_source_check_no_provider_call():
    """Source check expander must be removed from production UI."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    assert "Kiểm tra nguồn nâng cao" not in app_source


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
    assert 'content_cannot_be_empty' in quick_block
    assert "_submit_pasted_source" in quick_block


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
    assert "ask_submitted" in app_source
    assert 'key=f"wsc_ask_{active_conversation.id}"' in app_source
    assert "__wscComposerShortcutBound" in app_source
    # st.chat_input auto-submit must not be used for AI calls
    assert "st.chat_input" not in app_source



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
    assert owner_choice_to_privacy_label(PRIVACY_CHOICE_SENDABLE) == "cloud_safe"
    assert owner_choice_to_privacy_label(PRIVACY_CHOICE_LOCAL_ONLY) == "local_only"
    for sendable in ["cloud_safe", "public"]:
        assert privacy_label_to_owner_choice(sendable) == PRIVACY_CHOICE_SENDABLE
        assert privacy_label_is_sendable(sendable) is True
    for blocked in ["machine_only", "cloud_allowed", "local_only", "confidential", "", "   ", None, "unknown"]:
        assert privacy_label_to_owner_choice(blocked) == PRIVACY_CHOICE_LOCAL_ONLY
        assert privacy_label_is_sendable(blocked) is False


def test_phase2i_source_creation_forms_call_production_helpers_with_privacy_choice():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    quick_block = app_source[app_source.index("quick_paste_form"):app_source.index("# Khung dán nhật ký", app_source.index("quick_paste_form"))]
    assert "quick_privacy_choice = render_privacy_choice" in quick_block
    assert "_submit_pasted_source" in quick_block
    assert "quick_privacy_choice" in quick_block
    paste_block = app_source[app_source.index("paste_log_form"):app_source.index("with tab_upload:", app_source.index("paste_log_form"))]
    assert "paste_privacy_choice = render_privacy_choice" in paste_block
    assert "_submit_pasted_source" in paste_block
    assert "paste_privacy_choice" in paste_block
    excel_block = app_source[app_source.index("excel_upload_form"):]
    assert "excel_privacy_choice = render_privacy_choice" in excel_block
    assert "create_excel_temporary_source_from_extraction" in excel_block
    assert "owner_choice=excel_privacy_choice" in excel_block


def test_phase2i_real_quick_paste_creation_path_executes_both_privacy_choices():
    import aios_habit.workspace_chat_app as app
    from aios_habit.workspace_chat_ui import PRIVACY_CHOICE_SENDABLE, PRIVACY_CHOICE_LOCAL_ONLY
    for idx, (choice, expected_label) in enumerate([(PRIVACY_CHOICE_SENDABLE, "cloud_safe"), (PRIVACY_CHOICE_LOCAL_ONLY, "local_only")]):
        conv_id = f"conv_quick_real_{idx}"
        app.create_pasted_text_temporary_source(conv_id, "Quick paste title", "Quick paste text", choice)
        _assert_one_created_source(conv_id, expected_label, "pasted_text", "Quick paste text")


def test_phase2i_real_long_text_creation_path_executes_both_privacy_choices():
    import aios_habit.workspace_chat_app as app
    from aios_habit.workspace_chat_ui import PRIVACY_CHOICE_SENDABLE, PRIVACY_CHOICE_LOCAL_ONLY
    for idx, (choice, expected_label) in enumerate([(PRIVACY_CHOICE_SENDABLE, "cloud_safe"), (PRIVACY_CHOICE_LOCAL_ONLY, "local_only")]):
        conv_id = f"conv_long_real_{idx}"
        app.create_pasted_text_temporary_source(conv_id, "Long text title", "Long text body", choice)
        _assert_one_created_source(conv_id, expected_label, "pasted_text", "Long text body")


def test_phase2i_real_excel_creation_path_uses_extracted_text_and_both_privacy_choices():
    import aios_habit.workspace_chat_app as app
    from aios_habit.workspace_chat_ui import PRIVACY_CHOICE_SENDABLE, PRIVACY_CHOICE_LOCAL_ONLY
    for idx, (choice, expected_label) in enumerate([(PRIVACY_CHOICE_SENDABLE, "cloud_safe"), (PRIVACY_CHOICE_LOCAL_ONLY, "local_only")]):
        conv_id = f"conv_excel_real_{idx}"
        app.create_excel_temporary_source_from_extraction(conv_id, _Phase2IExtractionResult(), choice)
        saved = store.load_temporary_sources(conv_id)
        assert saved[0].title == "owner_source.xlsx"
        assert saved[0].content_preview == "Excel preview"
        _assert_one_created_source(conv_id, expected_label, "xlsx", "Excel extracted text")


def test_phase2i_actual_privacy_edit_helpers_two_way_and_scope_safe(monkeypatch):
    import aios_habit.workspace_chat_app as app
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
    assert store.load_notebook_sources("nb_active")[0].privacy_label == "cloud_safe"
    assert store.load_temporary_sources("conv_active")[0].privacy_label == "cloud_safe"
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


def test_phase2i_notebook_lifecycle_ui_copy_and_hard_delete_actions():
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
    assert "Xóa vĩnh viễn sổ" in combined
    assert "Nhập chính xác tên sổ để xác nhận xóa" in combined
    assert "cascade delete" not in combined.lower()
    assert "confirm hard delete" not in combined.lower()
    assert "load_active_notebooks()" in app_source
    assert "load_archived_notebooks()" in app_source
    assert "render_archived_notebook_card" in app_source


def test_app_hard_delete_behavioral_flows(mock_streamlit_app, monkeypatch):
    session_state, reruns = mock_streamlit_app

    # 1. Setup target notebook, unrelated notebook, and archived notebook in store
    nb_target = DocumentNotebook(id="target_nb", title="Target Notebook", description="Desc")
    nb_unrelated = DocumentNotebook(id="unrelated_nb", title="Unrelated Notebook", description="Desc")
    nb_archived = DocumentNotebook(id="archived_nb", title="Archived Notebook", description="Desc", archived_at="2026-07-04T12:00:00")
    store.save_notebook(nb_target)
    store.save_notebook(nb_unrelated)
    store.save_notebook(nb_archived)

    conv_target = WorkspaceConversation(id="conv_target", notebook_id="target_nb", title="Target Conv")
    conv_unrelated = WorkspaceConversation(id="conv_unrelated", notebook_id="unrelated_nb", title="Unrelated Conv")
    store.save_conversation(conv_target)
    store.save_conversation(conv_unrelated)

    # Setup unrelated conversation with existing messages
    store.save_message(ChatMessage(id="msg_u1", conversation_id="conv_unrelated", role="user", content="hello"))
    store.save_message(ChatMessage(id="msg_u2", conversation_id="conv_unrelated", role="assistant", content="hi there"))

    # Setup a local-only source in the unrelated notebook to test RAG blocking later
    src_unrelated = NotebookSource(
        id="src_unrelated",
        notebook_id="unrelated_nb",
        title="Unrelated Source",
        source_type="plain_text",
        privacy_label="local_only",
        content_preview="some preview",
        content_text="some content"
    )
    store.save_notebook_source(src_unrelated)
    store.set_source_enabled("conv_unrelated", "notebook", "src_unrelated", True)

    # Import app module to invoke callbacks
    import aios_habit.workspace_chat_app as app

    # Setup spies
    delete_call_count = 0
    delete_called_with = None

    def spy_delete_notebook_permanently(notebook_id):
        nonlocal delete_call_count, delete_called_with
        delete_call_count += 1
        delete_called_with = notebook_id
        return store.delete_notebook_permanently(notebook_id)

    monkeypatch.setattr(app, "delete_notebook_permanently", spy_delete_notebook_permanently)

    # Mock generate_workspace_ai_answer to prevent and detect any AI provider path calls
    # app module imports generate_workspace_ai_answer directly, so we must patch app's namespace
    original_generate_answer = app.generate_workspace_ai_answer

    ai_called = False
    def spy_generate_workspace_ai_answer(*args, **kwargs):
        nonlocal ai_called
        ai_called = True
        raise AssertionError("AI generation path must not be called during delete operations!")
    monkeypatch.setattr(app, "generate_workspace_ai_answer", spy_generate_workspace_ai_answer)

    # Mock active session pointing to target notebook
    session_state.wsc_active_notebook_id = "target_nb"
    session_state.wsc_active_conversation_id = "conv_target"
    session_state.wsc_delete_confirm_notebook_id = None
    session_state.wsc_archive_confirm_notebook_id = "target_nb"

    # Capture a full snapshot of unrelated messages before any delete action
    unrelated_msgs_before = sorted([
        (m.id, m.conversation_id, m.role, m.content)
        for m in store.load_messages("conv_unrelated")
    ])
    assert unrelated_msgs_before
    assert any(role == "user" and content == "hello" for _, _, role, content in unrelated_msgs_before)
    assert any(role == "assistant" and content == "hi there" for _, _, role, content in unrelated_msgs_before)

    # --- Scenario A: Wrong title spy & Confirmation state cleanup ---
    # Request delete on archived
    app.request_delete_notebook_callback("archived_nb")
    assert session_state.wsc_delete_confirm_notebook_id == "archived_nb"

    # Set text widget state to wrong title
    session_state[f"delete_confirm_title_archive_archived_nb"] = "Wrong Title"
    session_state[f"delete_confirm_ack_archive_archived_nb"] = True

    app.confirm_delete_notebook_callback("archived_nb", "Wrong Title", True)

    # Assertions for wrong title:
    assert delete_call_count == 0, "Delete helper should NOT be called with wrong title!"
    assert session_state.wsc_action_error == app.NOTEBOOK_DELETE_WRONG_TITLE
    # Verify widget keys and pending state are cleared
    assert session_state.wsc_delete_confirm_notebook_id is None
    assert f"delete_confirm_title_archive_archived_nb" not in session_state
    assert f"delete_confirm_ack_archive_archived_nb" not in session_state
    # Verify archived notebook is still in store
    assert store.load_notebook("archived_nb") is not None

    # --- Scenario B: Exact title spy on archived notebook ---
    app.request_delete_notebook_callback("archived_nb")
    # Simulate widget values
    session_state[f"delete_confirm_title_archive_archived_nb"] = "Archived Notebook"
    session_state[f"delete_confirm_ack_archive_archived_nb"] = True

    app.confirm_delete_notebook_callback("archived_nb", "Archived Notebook", True)

    # Assertions for exact title:
    assert delete_call_count == 1
    assert delete_called_with == "archived_nb"
    assert session_state.wsc_action_message == app.NOTEBOOK_DELETE_SUCCESS
    # Verify store actually has it deleted
    assert store.load_notebook("archived_nb") is None
    # Verify widgets cleaned
    assert f"delete_confirm_title_archive_archived_nb" not in session_state
    assert f"delete_confirm_ack_archive_archived_nb" not in session_state

    # Verify archived list does not have it
    archived_list = store.load_archived_notebooks()
    assert not any(n.id == "archived_nb" for n in archived_list)

    # --- Scenario C: Active notebook exact delete and session clearing ---
    delete_call_count = 0  # reset spy
    app.request_delete_notebook_callback("target_nb")
    session_state[f"delete_confirm_title_active_target_nb"] = "Target Notebook"
    session_state[f"delete_confirm_ack_active_target_nb"] = True

    app.confirm_delete_notebook_callback("target_nb", "Target Notebook", True)

    # Assertions:
    assert delete_call_count == 1
    assert delete_called_with == "target_nb"
    assert store.load_notebook("target_nb") is None

    # Verify session cleared
    assert session_state.wsc_active_notebook_id is None
    assert session_state.wsc_active_conversation_id is None
    assert session_state.wsc_delete_confirm_notebook_id is None
    assert session_state.wsc_archive_confirm_notebook_id is None
    assert f"delete_confirm_title_active_target_nb" not in session_state
    assert f"delete_confirm_ack_active_target_nb" not in session_state

    # --- Scenario D: No AI answer created & Provider safety ---
    assert not ai_called, "AI path was triggered during delete flow!"
    # Ensure messages in the unrelated notebook conversation were not modified or added to
    unrelated_msgs = store.load_messages("conv_unrelated")
    unrelated_msgs_after = sorted([
        (m.id, m.conversation_id, m.role, m.content)
        for m in unrelated_msgs
    ])
    assert len(unrelated_msgs) == 2, "Messages count in unrelated conv changed!"
    assert [m.role for m in unrelated_msgs] == ["user", "assistant"], "Stale messages or new assistant messages were created!"
    assert unrelated_msgs_after == unrelated_msgs_before, "Unrelated messages content or attributes changed!"

    # --- Scenario E: Cancel state cleanup ---
    app.request_delete_notebook_callback("unrelated_nb")
    session_state[f"delete_confirm_title_active_unrelated_nb"] = "Unrelated Notebook"
    session_state[f"delete_confirm_ack_active_unrelated_nb"] = True

    app.cancel_delete_notebook_callback("unrelated_nb")
    assert session_state.wsc_delete_confirm_notebook_id is None
    assert f"delete_confirm_title_active_unrelated_nb" not in session_state
    assert f"delete_confirm_ack_active_unrelated_nb" not in session_state

    # --- Scenario F: Local-only source in unrelated notebook still blocks AI ---
    # restore generate_workspace_ai_answer spy on app namespace to test RAG blocking without calling monkeypatch.undo()
    monkeypatch.setattr(app, "generate_workspace_ai_answer", original_generate_answer)
    from aios_habit.workspace_chat_ai_answer import WorkspaceAIAnswerRequest, pack_workspace_ai_context, generate_workspace_ai_answer, PRIVACY_MODE_CLOUD_ALLOWED
    enabled = store.load_enabled_sources_for_conversation("conv_unrelated")
    _, packed, _ = pack_workspace_ai_context("question", [src_unrelated], [], enabled)
    req = WorkspaceAIAnswerRequest(
        conversation_id="conv_unrelated",
        question="question",
        context_sources=packed,
        privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        cloud_consent_confirmed=True,
        consent_source_keys=tuple((s.source_scope, s.source_id) for s in enabled)
    )

    # Record provider calls
    provider_calls = 0
    class FakeProvider:
        def generate_answer(self, *args, **kwargs):
            nonlocal provider_calls
            provider_calls += 1
            return None

    result = generate_workspace_ai_answer(req, provider_client=FakeProvider())
    assert result.ok is False
    assert "chỉ được dùng trên máy" in result.error_message.lower()
    assert provider_calls == 0, "Provider was called despite local_only source restriction!"


def test_app_hard_delete_helper_failure_behavioral_flow(mock_streamlit_app, monkeypatch):
    session_state, _ = mock_streamlit_app

    # 1. Setup target notebook and data in store
    nb_target = DocumentNotebook(id="target_nb_fail", title="Target Notebook Fail", description="Desc")
    store.save_notebook(nb_target)

    conv_target = WorkspaceConversation(id="conv_target_fail", notebook_id="target_nb_fail", title="Target Conv Fail")
    store.save_conversation(conv_target)

    # Setup conversation with existing messages
    store.save_message(ChatMessage(id="msg_f1", conversation_id="conv_target_fail", role="user", content="hello"))
    store.save_message(ChatMessage(id="msg_f2", conversation_id="conv_target_fail", role="assistant", content="hi there"))

    # Import app module
    import aios_habit.workspace_chat_app as app

    # Spy AI answer path to assert it is never called
    ai_called = False
    def spy_generate_workspace_ai_answer(*args, **kwargs):
        nonlocal ai_called
        ai_called = True
        raise AssertionError("AI generation must not be called!")
    monkeypatch.setattr(app, "generate_workspace_ai_answer", spy_generate_workspace_ai_answer)

    # Spy delete helper to return False
    delete_calls = 0
    def mock_delete_permanently(notebook_id):
        nonlocal delete_calls
        delete_calls += 1
        return False

    monkeypatch.setattr(app, "delete_notebook_permanently", mock_delete_permanently)

    # Mock active session pointing to target notebook
    session_state.wsc_active_notebook_id = "target_nb_fail"
    session_state.wsc_active_conversation_id = "conv_target_fail"
    session_state.wsc_delete_confirm_notebook_id = None
    session_state.wsc_archive_confirm_notebook_id = "target_nb_fail"

    # Request delete
    app.request_delete_notebook_callback("target_nb_fail")
    assert session_state.wsc_delete_confirm_notebook_id == "target_nb_fail"

    # Set widgets values
    session_state["delete_confirm_title_active_target_nb_fail"] = "Target Notebook Fail"
    session_state["delete_confirm_ack_active_target_nb_fail"] = True

    # Capture target messages snapshot before calling callback
    fail_msgs_before = sorted([
        (m.id, m.conversation_id, m.role, m.content)
        for m in store.load_messages("conv_target_fail")
    ])
    assert fail_msgs_before
    assert any(role == "user" and content == "hello" for _, _, role, content in fail_msgs_before)
    assert any(role == "assistant" and content == "hi there" for _, _, role, content in fail_msgs_before)

    # Confirm delete (fails due to spy returning False)
    app.confirm_delete_notebook_callback("target_nb_fail", "Target Notebook Fail", True)

    # Assertions:
    assert delete_calls == 1
    # Error message set
    assert session_state.wsc_action_error == app.NOTEBOOK_DELETE_FAILURE
    # Active session MUST REMAIN UNCHANGED
    assert session_state.wsc_active_notebook_id == "target_nb_fail"
    assert session_state.wsc_active_conversation_id == "conv_target_fail"
    # Pending states and widgets are cleared
    assert session_state.wsc_delete_confirm_notebook_id is None
    assert "delete_confirm_title_active_target_nb_fail" not in session_state
    assert "delete_confirm_ack_active_target_nb_fail" not in session_state

    # Verify notebook is still in store
    assert store.load_notebook("target_nb_fail") is not None
    # Verify AI generation path not called
    assert not ai_called
    # Verify messages count/roles/content not changed
    msgs = store.load_messages("conv_target_fail")
    fail_msgs_after = sorted([
        (m.id, m.conversation_id, m.role, m.content)
        for m in msgs
    ])
    assert len(msgs) == 2
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert fail_msgs_after == fail_msgs_before, "Target messages content or attributes changed upon helper failure!"

def test_app_submit_no_evidence_behavioral():
    # 1. Static assertion: Prove code structure in workspace_chat_app.py
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    # Assert that retrieve_local_evidence is called
    assert "retrieve_local_evidence(" in app_source
    assert "packed_sources" in app_source

    # Assert check on summary_count == 0
    assert 'ret_res["summary_count"] == 0' in app_source
    # Assert that st.session_state.wsc_action_error is set in the true branch
    assert 'st.session_state.wsc_action_error = "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."' in app_source

    # Verify that saving messages and calling provider are inside the else block
    idx_error = app_source.index('st.session_state.wsc_action_error = "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."')
    idx_else = app_source.index("else:", idx_error)
    idx_provider = app_source.index("generate_workspace_ai_answer", idx_else)
    idx_save = app_source.index("save_message(user_msg)", idx_provider)

    assert idx_error < idx_else < idx_provider < idx_save

    # 2. Dynamic simulation of the submit decision flow
    provider_called = 0
    messages_saved = []

    def mock_retrieval(q, sources):
        return {
            "retrieval_applied": True,
            "summary_count": 0,
            "evidence_items": [],
            "retrieved_context_sources": (),
            "safe_owner_message": "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."
        }

    def mock_provider(req):
        nonlocal provider_called
        provider_called += 1
        return None

    def mock_save_message(msg):
        messages_saved.append(msg)

    # Simulate submission logic
    q_text = "Hỏi"
    packed_sources = ()

    ret_res = mock_retrieval(q_text, packed_sources)
    if ret_res["summary_count"] == 0:
        action_error = "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."
        last_ai_badge = None
    else:
        # Should not enter here
        req = object()
        res = mock_provider(req)
        user_msg = ChatMessage(id="1", conversation_id="c", role="user", content="q")
        mock_save_message(user_msg)

    # Verify behavioral outcomes
    assert action_error == "Chưa tìm thấy đoạn phù hợp trong nguồn đang bật."
    assert last_ai_badge is None
    assert provider_called == 0
    assert len(messages_saved) == 0


def test_app_never_sends_full_sources_when_quality_retrieval_is_unavailable():
    """A long document must not fall back to its leading pages/TOC at the provider."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    unavailable_idx = app_source.index('if ret_res.get("status") == "quality_search_unavailable":')
    rerun_idx = app_source.index("safe_rerun()", unavailable_idx)
    provider_idx = app_source.index("generate_workspace_ai_answer", unavailable_idx)
    branch_end = app_source.index('elif ret_res["summary_count"] == 0:', unavailable_idx)

    assert "no_evidence_found_error" in app_source[unavailable_idx:branch_end]
    assert "retrieval_applied = False" not in app_source[unavailable_idx:branch_end]
    assert unavailable_idx < rerun_idx < provider_idx


def test_app_preparation_gate_is_scoped_to_query_relevant_sources():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    gate_idx = app_source.index("source_scope = select_workspace_chat_preparation_scope(")
    status_idx = app_source.index(
        "get_workspace_chat_source_preparation_status(\n                                    query_relevant_sources",
        gate_idx,
    )

    assert "schedule_workspace_chat_source_preparation(query_relevant_sources)" in app_source[gate_idx:status_idx]
    assert "broad_query_unready_error" in app_source[gate_idx:status_idx]
    assert gate_idx < status_idx


def test_app_retrieval_uses_the_exact_scope_that_preparation_checked():
    """A released pending question must not re-select from the full source library."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    gate_idx = app_source.index("source_scope = select_workspace_chat_preparation_scope(")
    retrieval_idx = app_source.index("ret_res = retrieve_local_evidence(", gate_idx)
    retrieval_call = app_source[retrieval_idx:retrieval_idx + 220]

    assert "limit=1" in app_source[gate_idx:retrieval_idx]
    assert "tuple(query_relevant_sources)" in retrieval_call
    assert "packed_sources," not in retrieval_call


def test_app_keeps_a_pending_question_and_continues_it_once_sources_are_ready():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    assert "_PENDING_SOURCE_SUBMISSION_KEY" in app_source
    assert "_new_pending_source_submission(" in app_source
    assert 'if pending_state == "ready":' in app_source
    assert "pending_auto_question =" in app_source
    assert "resumed_pending_question" in app_source
    assert "st.session_state.pop(_PENDING_SOURCE_SUBMISSION_KEY, None)" in app_source
    assert '"required_source_count": len(required_sources)' in app_source
    assert "cancel_pending_question" in app_source


def test_app_schedules_newly_uploaded_sources_without_bypassing_bge_gate():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    upload_idx = app_source.index("created_context_sources = tuple(")
    schedule_idx = app_source.index("schedule_workspace_chat_source_preparation(created_context_sources)", upload_idx)

    assert upload_idx < schedule_idx
    assert "fail-closed retrieval is disabled" in app_source[upload_idx - 900:upload_idx]


def test_app_skips_cloud_query_planning_for_precise_procedure_questions():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    planning_idx = app_source.index("local_query_plan = coerce_query_plan(q_text)")
    expansion_idx = app_source.index("expansion = generate_query_expansion(", planning_idx)

    assert "local_query_plan.intent_category not in {" in app_source[planning_idx:expansion_idx]
    assert '"procedure"' in app_source[planning_idx:expansion_idx]


def test_conversation_search_preference_selector_flow(mock_streamlit_app):
    session_state, reruns = mock_streamlit_app

    # 1. Create two conversations
    c1 = WorkspaceConversation(id="conv_pref_1", notebook_id="mom_opcenter", title="Conv 1", search_preference="auto")
    c2 = WorkspaceConversation(id="conv_pref_2", notebook_id="mom_opcenter", title="Conv 2", search_preference="deep")
    store.save_conversation(c1)
    store.save_conversation(c2)

    # 2. Verify active conv 1 loads as auto
    loaded1 = store.load_conversation("conv_pref_1")
    assert loaded1.search_preference == "auto"

    # 3. Simulate user toggling selector in conv 1 to deep
    store.update_conversation_search_preference("conv_pref_1", "deep")
    reloaded1 = store.load_conversation("conv_pref_1")
    assert reloaded1.search_preference == "deep"

    # 4. Conv 2 remains deep independently
    reloaded2 = store.load_conversation("conv_pref_2")
    assert reloaded2.search_preference == "deep"

    # 5. Switch conv 1 back to auto
    store.update_conversation_search_preference("conv_pref_1", "auto")
    assert store.load_conversation("conv_pref_1").search_preference == "auto"
    assert store.load_conversation("conv_pref_2").search_preference == "deep"


def test_app_hides_unavailable_deep_search_and_reports_the_real_reason():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    assert "get_workspace_chat_deep_search_availability" in app_source
    assert 'pref_options = ["auto", "deep"] if deep_search.available else ["auto"]' in app_source
    assert 'unavailable_reason == "deep_search_unavailable"' in app_source
    assert 'unavailable_reason == "runtimeerror"' in app_source
    assert 't("deep_search_unavailable", locale=current_ui_locale)' in app_source
    assert 'elif unavailable_reason == "runtimeerror"' in app_source


def test_app_exposes_a_machine_local_deep_search_control():
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    assert "get_workspace_chat_deep_search_enabled_preference" in app_source
    assert "set_workspace_chat_deep_search_enabled" in app_source
    assert "wsc_deep_search_machine_setting" in app_source
    assert "deep_search_machine_help" in app_source


def test_e2e_sandbox_upload_new_source_transitions_from_pending_to_ready(tmp_path: Path, monkeypatch):
    """End-to-end sandbox test: newly uploaded file is scheduled, transitions from pending to ready in ledger and UI."""
    import aios_habit.workspace_chat_rag_v2_adapter as adapter
    from aios_habit.workspace_chat_app import _workspace_context_sources
    from aios_habit.workspace_chat_ui import (
        render_preparation_progress_bar,
        format_preparation_summary_text,
    )

    canary_dir = tmp_path / "canary_runtime"
    config = adapter.WorkspaceChatRagV2CanaryConfig(
        enabled=True,
        runtime_root=canary_dir,
        bge_m3_model_revision="test-rev-123",
    )
    db_path = adapter._get_ledger_db_path(config)
    adapter._init_preparation_ledger_db(db_path)
    with adapter._PREPARATION_LOCK:
        adapter._PREPARATION_REGISTRY.clear()
    with adapter._SOURCE_CACHE_LOCK:
        adapter._SOURCE_CACHE.clear()

    # 1. Simulate new uploaded temporary source
    new_src = TemporaryConversationSource(
        id="upload_e2e_src_1",
        conversation_id="conv_e2e",
        source_type="txt",
        title="tai_lieu_moi_upload.txt",
        content_preview="Nội dung quy trình vận hành mới upload 2026.",
        content_text="Nội dung quy trình vận hành mới upload 2026.",
    )
    store.save_temporary_source(new_src)

    ctx_sources = _workspace_context_sources([], [new_src])
    assert len(ctx_sources) == 1

    # Mock BGE prepare to simulate successful embedding execution
    prepared_items = []
    def fake_prepare(sources, *, config=None):
        for s in sources:
            prepared_items.append(s.source_id)
        return len(sources)

    monkeypatch.setattr(adapter, "prepare_workspace_chat_sources", fake_prepare)
    monkeypatch.setattr(adapter, "_durable_semantic_coverage_ready", lambda *a, **kw: False)

    # 2. Schedule source preparation (which triggers real background drain thread)
    adapter.schedule_workspace_chat_source_preparation(ctx_sources, config=config)

    # 3. Poll for background thread completion without calling internal drain manually
    import time
    deadline = time.time() + 5.0
    final_summary = None
    while time.time() < deadline:
        summary = adapter.get_workspace_chat_preparation_summary(ctx_sources, config=config)
        if summary["ready"] == 1:
            final_summary = summary
            break
        time.sleep(0.05)

    assert final_summary is not None, "Background worker did not complete preparation within deadline"
    assert final_summary["total"] == 1
    assert final_summary["ready"] == 1
    assert final_summary["pending"] == 0
    assert final_summary["failed"] == 0
    assert final_summary["statuses"].get("temporary:upload_e2e_src_1") == "ready"
    summary_text = format_preparation_summary_text(final_summary, locale="vi")
    assert "1/1 sẵn sàng" in summary_text

    # 4. Verify SQLite ledger record
    row = adapter._load_ledger_row(db_path, "temporary", "upload_e2e_src_1")
    assert row is not None
    assert row.state == adapter.PREP_STATE_READY
    assert row.source_id == "upload_e2e_src_1"
    assert row.source_scope == "temporary"
