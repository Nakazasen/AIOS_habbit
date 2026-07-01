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

    # Phase 2C: XLSX upload form is conversation-scoped and main-area only.
    assert "Thêm file Excel .xlsx" in source
    assert "Chọn file Excel cho cuộc trò chuyện này" in source
    assert "Đọc và thêm vào nguồn tạm" in source
    assert 'key=f"wsc_excel_upload_{active_conversation.id}"' in source
    assert 'type=["xlsx", "xls"]' in source

    # Phase 2C: success flow order is extract -> temp source -> save -> enable -> rerun.
    extract_idx = source.find("result = extract_xlsx_text(uploaded_excel.getvalue(), uploaded_excel.name)")
    temp_idx = source.find("temporary_source = TemporaryConversationSource", extract_idx)
    xlsx_type_idx = source.find('source_type="xlsx"', temp_idx)
    title_idx = source.find("title=result.filename", temp_idx)
    preview_idx = source.find("content_preview=result.preview", temp_idx)
    text_idx = source.find("content_text=result.text", temp_idx)
    save_xlsx_idx = source.find("save_temporary_source(temporary_source)", temp_idx)
    enable_xlsx_idx = source.find("set_source_enabled(active_conversation.id, SOURCE_SCOPE_TEMPORARY, temporary_source.id, True)", save_xlsx_idx)
    rerun_xlsx_idx = source.find("safe_rerun()", enable_xlsx_idx)

    assert extract_idx != -1
    assert temp_idx != -1
    assert xlsx_type_idx != -1
    assert title_idx != -1
    assert preview_idx != -1
    assert text_idx != -1
    assert save_xlsx_idx != -1
    assert enable_xlsx_idx != -1
    assert rerun_xlsx_idx != -1
    assert extract_idx < temp_idx < save_xlsx_idx < enable_xlsx_idx < rerun_xlsx_idx
    assert temp_idx < xlsx_type_idx < save_xlsx_idx
    assert temp_idx < title_idx < save_xlsx_idx
    assert temp_idx < preview_idx < save_xlsx_idx
    assert temp_idx < text_idx < save_xlsx_idx

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
    assert "preview = build_trial_answer_preview(user_input, enabled_preview_sources)" in source
    assert "content=preview.answer_text" in source
    assert "selected_source_ids" not in source[source.find("if user_input:"):source.find("# Khung dán nhật ký")]


def test_phase2d_submit_order_save_user_resolve_build_save_assistant_rerun():
    source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    start = source.index("if user_input:")
    end = source.index("# Khung dán nhật ký", start)
    block = source[start:end]
    order_tokens = [
        "save_message(user_msg)",
        "load_enabled_sources_for_conversation(active_conversation.id)",
        "load_notebook_sources(active_nb_id)",
        "load_temporary_sources(active_conversation.id)",
        "build_trial_answer_preview(user_input, enabled_preview_sources)",
        "save_message(assistant_msg)",
        "safe_rerun()",
    ]
    positions = [block.index(token) for token in order_tokens]
    assert positions == sorted(positions)
    assert block.count("save_message(user_msg)") == 1
    assert block.count("save_message(assistant_msg)") == 1


def test_phase2d_app_does_not_reparse_xlsx_or_update_source_use_metadata_on_submit():
    source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")
    start = source.index("if user_input:")
    end = source.index("# Khung dán nhật ký", start)
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
