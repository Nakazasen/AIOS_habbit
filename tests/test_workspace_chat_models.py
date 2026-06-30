from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    TemporaryConversationSource
)

def test_document_notebook_instantiation():
    nb = DocumentNotebook(id="test_nb", title="Test Notebook", description="Testing description")
    assert nb.id == "test_nb"
    assert nb.title == "Test Notebook"
    assert nb.description == "Testing description"
    assert nb.created_at is not None

def test_workspace_conversation_instantiation():
    conv = WorkspaceConversation(
        id="conv_1",
        notebook_id="test_nb",
        title="My Conversation",
        selected_source_ids=["src1"],
        temporary_source_ids=["temp1"],
        saved_case_id="case_1"
    )
    assert conv.id == "conv_1"
    assert conv.notebook_id == "test_nb"
    assert conv.title == "My Conversation"
    assert "src1" in conv.selected_source_ids
    assert "temp1" in conv.temporary_source_ids
    assert conv.saved_case_id == "case_1"

def test_chat_message_instantiation():
    msg = ChatMessage(
        id="msg_1",
        conversation_id="conv_1",
        role="user",
        content="Hello world"
    )
    assert msg.id == "msg_1"
    assert msg.conversation_id == "conv_1"
    assert msg.role == "user"
    assert msg.content == "Hello world"

def test_temporary_source_instantiation():
    src = TemporaryConversationSource(
        id="src_1",
        conversation_id="conv_1",
        source_type="pasted_text",
        title="Error Log",
        content_preview="Line 1: error occurred"
    )
    assert src.id == "src_1"
    assert src.conversation_id == "conv_1"
    assert src.source_type == "pasted_text"
    assert src.title == "Error Log"
    assert src.content_preview == "Line 1: error occurred"
    assert src.status == "conversation_only"
    assert src.privacy_label == "machine_only"
    assert not src.long_term_saved
