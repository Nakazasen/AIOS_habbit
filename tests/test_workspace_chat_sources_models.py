import pytest
from datetime import datetime
from aios_habit.workspace_chat_models import (
    NotebookSource,
    ConversationSourceSelection,
    SOURCE_SCOPE_NOTEBOOK,
    SOURCE_SCOPE_TEMPORARY,
    NOTEBOOK_SOURCE_STATUS_READY,
    NOTEBOOK_SOURCE_STATUS_PREVIEW_ONLY,
    WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT,
    WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES
)

def test_notebook_source_instantiation():
    src = NotebookSource(
        id="src1",
        notebook_id="nb1",
        title="Test Source",
        source_type="pasted_text",
        content_preview="Hello world",
        content_text="Hello world full text"
    )
    assert src.id == "src1"
    assert src.notebook_id == "nb1"
    assert src.title == "Test Source"
    assert src.source_type == "pasted_text"
    assert src.content_preview == "Hello world"
    assert src.content_text == "Hello world full text"
    assert src.extraction_status == NOTEBOOK_SOURCE_STATUS_READY
    assert src.privacy_label == "machine_only"

def test_notebook_source_preview_capping():
    long_preview = "A" * (WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT + 100)
    src = NotebookSource(
        id="src1",
        notebook_id="nb1",
        title="Test Source",
        source_type="pasted_text",
        content_preview=long_preview
    )
    assert len(src.content_preview) == WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT
    assert src.content_preview == "A" * WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT

def test_notebook_source_text_capping():
    # Enforce UTF-8 byte limit capping
    long_text = "A" * (WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES + 100)
    src = NotebookSource(
        id="src1",
        notebook_id="nb1",
        title="Test Source",
        source_type="pasted_text",
        content_text=long_text
    )
    assert len(src.content_text.encode('utf-8')) == WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES
    assert src.content_text == "A" * WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES

def test_notebook_source_serialization_roundtrip():
    src = NotebookSource(
        id="src_round",
        notebook_id="nb1",
        title="Test Source Round",
        source_type="pasted_text",
        filename="test.txt",
        file_type="txt",
        content_preview="Preview",
        content_text="Text content",
        origin_temporary_source_id="temp_123"
    )
    d = src.to_dict()
    assert d["id"] == "src_round"
    assert d["filename"] == "test.txt"
    assert d["origin_temporary_source_id"] == "temp_123"

    loaded = NotebookSource.from_dict(d)
    assert loaded.id == src.id
    assert loaded.title == src.title
    assert loaded.filename == src.filename
    assert loaded.origin_temporary_source_id == src.origin_temporary_source_id

def test_notebook_source_from_dict_tolerance():
    # Missing optional fields
    data = {
        "id": "src_tol",
        "notebook_id": "nb1",
        "title": "Tolerant Source",
        "source_type": "pasted_text"
    }
    src = NotebookSource.from_dict(data)
    assert src.id == "src_tol"
    assert src.filename is None
    assert src.origin_temporary_source_id is None
    assert src.extraction_status == NOTEBOOK_SOURCE_STATUS_READY

def test_conversation_source_selection_instantiation():
    sel = ConversationSourceSelection(
        id="sel1",
        conversation_id="conv1",
        source_id="src1",
        source_scope=SOURCE_SCOPE_NOTEBOOK,
        enabled=True
    )
    assert sel.id == "sel1"
    assert sel.source_scope == SOURCE_SCOPE_NOTEBOOK
    assert sel.enabled is True

def test_conversation_source_selection_invalid_scope():
    with pytest.raises(ValueError, match="Invalid source_scope"):
        ConversationSourceSelection(
            id="sel1",
            conversation_id="conv1",
            source_id="src1",
            source_scope="invalid_scope",
            enabled=True
        )

def test_conversation_source_selection_serialization_roundtrip():
    sel = ConversationSourceSelection(
        id="sel_round",
        conversation_id="conv1",
        source_id="src1",
        source_scope=SOURCE_SCOPE_TEMPORARY,
        enabled=False,
        owner_note="Some note"
    )
    d = sel.to_dict()
    assert d["id"] == "sel_round"
    assert d["source_scope"] == SOURCE_SCOPE_TEMPORARY
    assert d["owner_note"] == "Some note"

    loaded = ConversationSourceSelection.from_dict(d)
    assert loaded.id == sel.id
    assert loaded.source_scope == sel.source_scope
    assert loaded.enabled == sel.enabled
    assert loaded.owner_note == sel.owner_note

def test_notebook_source_unicode_byte_capping():
    # Vietnamese, Japanese, and emojis
    sample = "Xin chào các bạn! こんにちは! 🚀✨"
    # Create a long text that will definitely exceed the limit
    long_sample = sample * 10000
    
    src = NotebookSource(
        id="src1",
        notebook_id="nb1",
        title="Unicode Test",
        source_type="pasted_text",
        content_text=long_sample
    )
    
    encoded_bytes = src.content_text.encode("utf-8")
    assert len(encoded_bytes) <= WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES
    # Ensure it decodes cleanly and has no replacement character
    decoded = encoded_bytes.decode("utf-8")
    assert "\ufffd" not in decoded

def test_conversation_source_selection_from_dict_invalid_scope():
    data = {
        "id": "sel1",
        "conversation_id": "conv1",
        "source_id": "src1",
        "source_scope": "bad_scope",
        "enabled": True
    }
    with pytest.raises(ValueError, match="Invalid source_scope"):
        ConversationSourceSelection.from_dict(data)

def test_notebook_source_truncation_behavior():
    long_text = "A" * (WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES + 500)
    src = NotebookSource(
        id="src1",
        notebook_id="nb1",
        title="Test Source",
        source_type="pasted_text",
        content_text=long_text
    )
    # Verify current truncation behavior: content is capped, no crash, status ready by default
    assert len(src.content_text) == WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES
    assert src.extraction_status == NOTEBOOK_SOURCE_STATUS_READY

