from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock

import aios_habit.workspace_chat_store as store
from aios_habit.workspace_chat_models import TemporaryConversationSource, SOURCE_SCOPE_TEMPORARY
from aios_habit.workspace_chat_store import init_chat_store, load_temporary_sources, load_enabled_sources_for_conversation
from aios_habit.workspace_chat_app import process_workspace_upload_batch
from aios_habit.workspace_chat_source_ingest import ingest_and_extract_bytes

class MockUploadedFile:
    def __init__(self, name: str, content: bytes):
        self.name = name
        self.content = content

    def getvalue(self) -> bytes:
        return self.content

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

def test_process_workspace_upload_batch_success_and_fail(monkeypatch):
    conversation_id = "test_conv_batch_1"

    # Mock ingest_and_extract_bytes to succeed for file1 & file2, but fail for file3
    def mock_ingest(file_bytes, filename, privacy_label):
        if "fail" in filename:
            return {
                "ok": False,
                "filename": filename,
                "owner_message": "Không thể đọc tập tin này. Lỗi giả lập.",
                "text": "",
                "preview": "",
                "metadata": {"file_size_bytes": len(file_bytes), "extension": ".txt"}
            }
        return {
            "ok": True,
            "filename": filename,
            "text": f"Nội dung của {filename}",
            "preview": f"Preview {filename}",
            "metadata": {"file_size_bytes": len(file_bytes), "extension": ".txt"}
        }

    monkeypatch.setattr("aios_habit.workspace_chat_app.ingest_and_extract_bytes", mock_ingest)

    files = [
        MockUploadedFile("success1.txt", b"content 1"),
        MockUploadedFile("failed_file.txt", b"content 2"),
        MockUploadedFile("success2.txt", b"content 3"),
    ]

    # Test with enable_now = False
    res = process_workspace_upload_batch(
        files,
        conversation_id,
        doc_privacy_choice="Chỉ dùng trên máy / không gửi AI",
        enable_now=False
    )

    assert res["success_count"] == 2
    assert res["fail_count"] == 1
    assert "success1.txt" in res["success_files"]
    assert "success2.txt" in res["success_files"]
    assert "failed_file.txt" in res["failed_files"]
    assert res["errors_by_file"]["failed_file.txt"] == "Không thể đọc tập tin này. Lỗi giả lập."

    # Verify sources saved
    saved = load_temporary_sources(conversation_id)
    assert len(saved) == 2
    titles = [s.title for s in saved]
    assert "success1.txt" in titles
    assert "success2.txt" in titles

    # Since enable_now = False, sources should not be enabled
    enabled = load_enabled_sources_for_conversation(conversation_id)
    assert len(enabled) == 0

def test_process_workspace_upload_batch_unique_ids(monkeypatch):
    conversation_id = "test_conv_batch_unique"

    # Mock ingest to succeed
    def mock_ingest(file_bytes, filename, privacy_label):
        return {
            "ok": True,
            "filename": filename,
            "text": "Nội dung",
            "preview": "Preview",
            "metadata": {"file_size_bytes": len(file_bytes), "extension": ".txt"}
        }

    monkeypatch.setattr("aios_habit.workspace_chat_app.ingest_and_extract_bytes", mock_ingest)

    # Upload two files with the exact same name
    files = [
        MockUploadedFile("same_name.txt", b"content 1"),
        MockUploadedFile("same_name.txt", b"content 2"),
    ]

    res = process_workspace_upload_batch(
        files,
        conversation_id,
        doc_privacy_choice="Chỉ dùng trên máy / không gửi AI",
        enable_now=True
    )

    assert res["success_count"] == 2
    saved = load_temporary_sources(conversation_id)
    assert len(saved) == 2
    assert saved[0].id != saved[1].id
    assert saved[0].title == "same_name.txt"
    assert saved[1].title == "same_name.txt"

    # Since enable_now = True, both should be enabled
    enabled = load_enabled_sources_for_conversation(conversation_id)
    assert len(enabled) == 2
    enabled_ids = {sel.source_id for sel in enabled}
    assert saved[0].id in enabled_ids
    assert saved[1].id in enabled_ids

def test_image_ocr_missing_graceful_handling(monkeypatch):
    # Simulates OCR tool missing when parsing an image
    # We want it to gracefully fail with custom Vietnamese message
    def mock_extract(temp_path):
        return [{
            "text": "",
            "source_file": Path(temp_path).name,
            "relative_path": Path(temp_path).name,
            "file_type": Path(temp_path).suffix,
            "extraction_status": "unsupported_no_local_ocr",
            "warning": "local OCR unavailable",
            "ocr_engine": "none",
            "ocr_lang": "eng",
        }]

    monkeypatch.setattr("aios_habit.workspace_chat_source_ingest.extract_text_chunks_from_file", mock_extract)

    res = ingest_and_extract_bytes(b"dummy image bytes", "test_photo.png", "machine_only")
    assert res["ok"] is False
    assert res["owner_message"] == "Chưa đọc được nội dung ảnh. Có thể máy chưa có OCR hoặc ảnh không có chữ rõ."
    assert "dependency_missing" in res["error_code"]
