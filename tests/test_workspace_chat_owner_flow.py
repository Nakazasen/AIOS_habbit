import pytest
from pathlib import Path
import aios_habit.workspace_chat_store as store
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    TemporaryConversationSource
)


class MockSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

@pytest.fixture(autouse=True)
def setup_test_store(tmp_path, monkeypatch):
    test_dir = tmp_path / "workspace_chat"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", test_dir)
    monkeypatch.setattr(store, "NOTEBOOKS_FILE", test_dir / "notebooks.jsonl")
    monkeypatch.setattr(store, "CONVERSATIONS_FILE", test_dir / "conversations.jsonl")
    monkeypatch.setattr(store, "MESSAGES_FILE", test_dir / "messages.jsonl")
    monkeypatch.setattr(store, "TEMPORARY_SOURCES_FILE", test_dir / "temporary_sources.jsonl")
    store.init_chat_store()

def test_owner_multiple_conversations_in_notebook():
    # 1. Open default notebook MOM / Opcenter
    nb = store.load_notebook("mom_opcenter")
    assert nb is not None
    assert nb.title == "MOM / Opcenter"

    # 2. Create multiple conversations in it
    conv1 = WorkspaceConversation(id="conv_a", notebook_id="mom_opcenter", title="Lỗi Manual Supply")
    conv2 = WorkspaceConversation(id="conv_b", notebook_id="mom_opcenter", title="Họp thiết kế")
    store.save_conversation(conv1)
    store.save_conversation(conv2)

    # 3. Retrieve all conversations for MOM / Opcenter
    convs = store.load_conversations("mom_opcenter")
    assert len(convs) == 2
    titles = [c.title for c in convs]
    assert "Lỗi Manual Supply" in titles
    assert "Họp thiết kế" in titles

def test_owner_conversation_scoped_temporary_source():
    # 1. Create two conversations
    conv1 = WorkspaceConversation(id="conv_a", notebook_id="mom_opcenter", title="Conv A")
    conv2 = WorkspaceConversation(id="conv_b", notebook_id="mom_opcenter", title="Conv B")
    store.save_conversation(conv1)
    store.save_conversation(conv2)

    # 2. Add temporary source to Conv A (e.g. pasted log)
    src_a = TemporaryConversationSource(
        id="src_log_a",
        conversation_id="conv_a",
        source_type="pasted_text",
        title="Opcenter log error",
        content_preview="Log contents..."
    )
    store.save_temporary_source(src_a)

    # 3. Retrieve temporary sources for Conv A and Conv B
    sources_a = store.load_temporary_sources("conv_a")
    sources_b = store.load_temporary_sources("conv_b")

    # Verify temporary source is in Conv A, not Conv B
    assert len(sources_a) == 1
    assert sources_a[0].title == "Opcenter log error"
    assert sources_a[0].status == "conversation_only"  # equivalent to 'Chưa lưu lâu dài'
    assert len(sources_b) == 0

    # 4. Simulate reload (reopening conversation) and verify source is still there
    reloaded_sources_a = store.load_temporary_sources("conv_a")
    assert len(reloaded_sources_a) == 1
    assert reloaded_sources_a[0].title == "Opcenter log error"

def test_owner_open_notebook_state_transition(monkeypatch):
    import streamlit as st

    session_state = MockSessionState()
    monkeypatch.setattr(st, "session_state", session_state)

    # Mock st.rerun
    rerun_called = []
    def mock_rerun():
        rerun_called.append(True)
    monkeypatch.setattr(st, "rerun", mock_rerun)

    # Import callback from app
    from aios_habit.workspace_chat_app import open_notebook_callback

    # Execute callback
    open_notebook_callback("mom_opcenter")

    # Verify state transition
    assert session_state.wsc_active_notebook_id == "mom_opcenter"
    assert session_state.wsc_active_conversation_id is None
    assert session_state.wsc_show_save_placeholder is False
    assert session_state.wsc_show_explain_placeholder is False
    assert len(rerun_called) == 1


def test_owner_navigation_recovers_missing_or_cross_notebook_conversation_reference():
    first = WorkspaceConversation(id="conv_first", notebook_id="mom_opcenter", title="First")
    other = WorkspaceConversation(id="conv_other", notebook_id="interstock_wms", title="Other")
    store.save_conversation(first)
    store.save_conversation(other)

    assert store.resolve_conversation_id("mom_opcenter", "conv_missing") == first.id
    assert store.resolve_conversation_id("mom_opcenter", other.id) == first.id
    assert store.resolve_conversation_id("email_jp_vn", "conv_missing") is None


def test_delete_active_conversation_selects_remaining_and_replaces_url(monkeypatch):
    import streamlit as st
    import aios_habit.workspace_chat_app as app

    target = WorkspaceConversation(id="conv_target", notebook_id="mom_opcenter", title="Delete me")
    survivor = WorkspaceConversation(id="conv_survivor", notebook_id="mom_opcenter", title="Keep me")
    conversations = [target, survivor]
    session_state = MockSessionState(
        wsc_active_notebook_id="mom_opcenter",
        wsc_active_conversation_id=target.id,
        wsc_manage_conversation_id=target.id,
        wsc_pending_conversation_delete_id=target.id,
        wsc_action_message=None,
        wsc_action_error=None,
    )
    navigation = []

    monkeypatch.setattr(st, "session_state", session_state)
    monkeypatch.setattr(app, "safe_rerun", lambda: None)
    monkeypatch.setattr(app, "set_query_params", lambda **kwargs: navigation.append(kwargs))
    monkeypatch.setattr(app, "load_conversation", lambda conversation_id: next((c for c in conversations if c.id == conversation_id), None))
    monkeypatch.setattr(app, "resolve_conversation_id", lambda _notebook_id, requested_id: requested_id if any(c.id == requested_id for c in conversations) else (conversations[0].id if conversations else None))

    def delete_target(conversation_id):
        nonlocal conversations
        conversations = [conversation for conversation in conversations if conversation.id != conversation_id]
        return True

    monkeypatch.setattr(app, "delete_conversation", delete_target)

    app.confirm_delete_conversation_callback("mom_opcenter", target.id)

    assert session_state.wsc_active_conversation_id == survivor.id
    assert session_state.wsc_manage_conversation_id == survivor.id
    assert session_state.wsc_pending_conversation_delete_id is None
    assert navigation[-1] == {"nb": "mom_opcenter", "conv": survivor.id}
    assert "Delete me" in session_state.wsc_action_message


def test_delete_last_active_conversation_clears_stale_navigation_to_empty_state(monkeypatch):
    import streamlit as st
    import aios_habit.workspace_chat_app as app

    target = WorkspaceConversation(id="conv_last", notebook_id="mom_opcenter", title="Last conversation")
    conversations = [target]
    session_state = MockSessionState(
        wsc_active_notebook_id="mom_opcenter",
        wsc_active_conversation_id=target.id,
        wsc_manage_conversation_id=target.id,
        wsc_pending_conversation_delete_id=target.id,
        wsc_action_message=None,
        wsc_action_error=None,
    )
    navigation = []

    monkeypatch.setattr(st, "session_state", session_state)
    monkeypatch.setattr(app, "safe_rerun", lambda: None)
    monkeypatch.setattr(app, "set_query_params", lambda **kwargs: navigation.append(kwargs))
    monkeypatch.setattr(app, "load_conversation", lambda conversation_id: next((c for c in conversations if c.id == conversation_id), None))
    monkeypatch.setattr(app, "resolve_conversation_id", lambda _notebook_id, _requested_id: None)

    def delete_target(conversation_id):
        nonlocal conversations
        conversations = [conversation for conversation in conversations if conversation.id != conversation_id]
        return True

    monkeypatch.setattr(app, "delete_conversation", delete_target)

    app.confirm_delete_conversation_callback("mom_opcenter", target.id)

    assert session_state.wsc_active_conversation_id is None
    assert session_state.wsc_manage_conversation_id is None
    assert session_state.wsc_pending_conversation_delete_id is None
    assert navigation[-1] == {"nb": "mom_opcenter", "conv": None}


def test_select_conversation_keeps_selected_state_and_url_on_the_same_target(monkeypatch):
    import streamlit as st
    import aios_habit.workspace_chat_app as app

    session_state = MockSessionState(wsc_active_conversation_id="conv_old")
    navigation = []
    monkeypatch.setattr(st, "session_state", session_state)
    monkeypatch.setattr(app, "set_query_params", lambda **kwargs: navigation.append(kwargs))
    monkeypatch.setattr(
        app,
        "resolve_conversation_id",
        lambda notebook_id, conversation_id: conversation_id if notebook_id == "mom_opcenter" else None,
    )

    selected = app.set_active_conversation_callback("mom_opcenter", "conv_target")

    assert selected == "conv_target"
    assert session_state.wsc_active_conversation_id == "conv_target"
    assert navigation == [{"nb": "mom_opcenter", "conv": "conv_target"}]


def test_conversation_delete_target_is_explicit_and_cancel_is_non_destructive(monkeypatch):
    import streamlit as st
    import aios_habit.workspace_chat_app as app

    target = WorkspaceConversation(id="conv_target", notebook_id="mom_opcenter", title="Target")
    session_state = MockSessionState(
        wsc_active_notebook_id="mom_opcenter",
        wsc_active_conversation_id="conv_other",
        wsc_manage_conversation_id="conv_other",
        wsc_pending_conversation_delete_id=None,
        wsc_action_error=None,
    )

    monkeypatch.setattr(st, "session_state", session_state)
    monkeypatch.setattr(app, "safe_rerun", lambda: None)
    monkeypatch.setattr(app, "load_conversation", lambda conversation_id: target if conversation_id == target.id else None)

    app.request_delete_conversation_callback("mom_opcenter", target.id)
    assert session_state.wsc_pending_conversation_delete_id == target.id
    assert session_state.wsc_active_conversation_id == "conv_other"

    app.cancel_delete_conversation_callback(target.id)
    assert session_state.wsc_pending_conversation_delete_id is None
    assert session_state.wsc_active_conversation_id == "conv_other"


def test_delete_non_active_conversation_preserves_active_conversation_and_url(monkeypatch):
    import streamlit as st
    import aios_habit.workspace_chat_app as app

    target = WorkspaceConversation(id="conv_target", notebook_id="mom_opcenter", title="Delete me")
    active = WorkspaceConversation(id="conv_active", notebook_id="mom_opcenter", title="Keep me active")
    conversations = [active, target]
    session_state = MockSessionState(
        wsc_active_notebook_id="mom_opcenter",
        wsc_active_conversation_id=active.id,
        wsc_manage_conversation_id=target.id,
        wsc_pending_conversation_delete_id=target.id,
        wsc_action_message=None,
        wsc_action_error=None,
    )
    navigation = []

    monkeypatch.setattr(st, "session_state", session_state)
    monkeypatch.setattr(app, "safe_rerun", lambda: None)
    monkeypatch.setattr(app, "set_query_params", lambda **kwargs: navigation.append(kwargs))
    monkeypatch.setattr(app, "load_conversation", lambda conversation_id: next((c for c in conversations if c.id == conversation_id), None))
    monkeypatch.setattr(app, "resolve_conversation_id", lambda _notebook_id, requested_id: requested_id if any(c.id == requested_id for c in conversations) else (conversations[0].id if conversations else None))

    def delete_target(conversation_id):
        nonlocal conversations
        conversations = [conversation for conversation in conversations if conversation.id != conversation_id]
        return True

    monkeypatch.setattr(app, "delete_conversation", delete_target)

    app.confirm_delete_conversation_callback("mom_opcenter", target.id)

    assert session_state.wsc_active_conversation_id == active.id
    assert session_state.wsc_manage_conversation_id == active.id
    assert session_state.wsc_pending_conversation_delete_id is None
    assert navigation[-1] == {"nb": "mom_opcenter", "conv": active.id}
    assert "Delete me" in session_state.wsc_action_message


def test_ui_sidebar_manage_and_delete_flow(monkeypatch):
    import streamlit as st
    import aios_habit.workspace_chat_app as app

    conv_a = WorkspaceConversation(id="conv_a", notebook_id="mom_opcenter", title="Conv A")
    conv_b = WorkspaceConversation(id="conv_b", notebook_id="mom_opcenter", title="Conv B")
    store.save_conversation(conv_a)
    store.save_conversation(conv_b)

    session_state = MockSessionState(
        wsc_active_notebook_id="mom_opcenter",
        wsc_active_conversation_id=conv_b.id,
        wsc_manage_conversation_id=conv_b.id,
        wsc_pending_conversation_delete_id=None,
    )
    navigation = []
    rerun_count = 0

    def mock_safe_rerun():
        nonlocal rerun_count
        rerun_count += 1

    monkeypatch.setattr(st, "session_state", session_state)
    monkeypatch.setattr(app, "safe_rerun", mock_safe_rerun)
    monkeypatch.setattr(app, "set_query_params", lambda **kwargs: navigation.append(kwargs))

    # 1. Request delete on conv_b
    app.request_delete_conversation_callback("mom_opcenter", conv_b.id)
    assert session_state.wsc_pending_conversation_delete_id == conv_b.id

    # 2. Cancel delete on conv_b
    app.cancel_delete_conversation_callback(conv_b.id)
    assert session_state.wsc_pending_conversation_delete_id is None
    assert store.load_conversation(conv_b.id) is not None

    # 3. Request delete again and confirm (deleting active conversation B -> moves to A)
    app.request_delete_conversation_callback("mom_opcenter", conv_b.id)
    app.confirm_delete_conversation_callback("mom_opcenter", conv_b.id)

    assert store.load_conversation(conv_b.id) is None
    assert store.load_conversation(conv_a.id) is not None
    assert session_state.wsc_active_conversation_id == conv_a.id
    assert navigation[-1] == {"nb": "mom_opcenter", "conv": conv_a.id}

    # 4. Now delete conv_a (last remaining conversation -> empty state conv=None)
    app.confirm_delete_conversation_callback("mom_opcenter", conv_a.id)
    assert store.load_conversation(conv_a.id) is None
    assert session_state.wsc_active_conversation_id is None
    assert navigation[-1] == {"nb": "mom_opcenter", "conv": None}
