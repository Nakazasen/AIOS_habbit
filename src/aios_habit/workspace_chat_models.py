import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional

SOURCE_SCOPE_NOTEBOOK = "notebook"
SOURCE_SCOPE_TEMPORARY = "temporary"

NOTEBOOK_SOURCE_STATUS_READY = "ready"
NOTEBOOK_SOURCE_STATUS_PREVIEW_ONLY = "preview_only"
NOTEBOOK_SOURCE_STATUS_FAILED = "failed"

WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT = 2000
WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES = 200 * 1024

@dataclass
class DocumentNotebook:
    id: str
    title: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    archived_at: Optional[str] = None

    def is_archived(self) -> bool:
        if self.archived_at is None:
            return False
        if isinstance(self.archived_at, str):
            return bool(self.archived_at.strip())
        return True

@dataclass
class WorkspaceConversation:
    id: str
    notebook_id: str
    title: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    selected_source_ids: List[str] = field(default_factory=list)
    temporary_source_ids: List[str] = field(default_factory=list)
    saved_case_id: Optional[str] = None

@dataclass
class ChatMessage:
    id: str
    conversation_id: str
    role: str  # user/assistant/system
    content: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class TemporaryConversationSource:
    id: str
    conversation_id: str
    source_type: str  # pasted_text/file_placeholder/image_placeholder/excel_placeholder
    title: str
    content_preview: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "conversation_only"  # conversation_only / saved_to_case / added_to_notebook
    privacy_label: str = "machine_only"
    long_term_saved: bool = False
    content_text: str = ""

@dataclass
class NotebookSource:
    id: str
    notebook_id: str
    title: str
    source_type: str
    filename: Optional[str] = None
    file_type: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    privacy_label: str = "machine_only"
    content_preview: str = ""
    content_text: str = ""
    extraction_status: str = NOTEBOOK_SOURCE_STATUS_READY
    source_note: str = ""
    origin_temporary_source_id: Optional[str] = None

    def __post_init__(self):
        if self.content_preview and len(self.content_preview) > WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT:
            self.content_preview = self.content_preview[:WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT]
        
        if self.content_text:
            text_bytes = self.content_text.encode("utf-8")
            if len(text_bytes) > WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES:
                self.content_text = text_bytes[:WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES].decode("utf-8", errors="ignore")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'NotebookSource':
        valid_keys = {
            "id", "notebook_id", "title", "source_type", "filename", "file_type",
            "created_at", "updated_at", "privacy_label", "content_preview",
            "content_text", "extraction_status", "source_note", "origin_temporary_source_id"
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

@dataclass
class ConversationSourceSelection:
    id: str
    conversation_id: str
    source_id: str
    source_scope: str
    enabled: bool
    enabled_at: Optional[str] = None
    disabled_at: Optional[str] = None
    used_in_last_answer: bool = False
    last_used_at: Optional[str] = None
    owner_note: str = ""

    def __post_init__(self):
        if self.source_scope not in (SOURCE_SCOPE_NOTEBOOK, SOURCE_SCOPE_TEMPORARY):
            raise ValueError(f"Invalid source_scope: {self.source_scope}")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationSourceSelection':
        valid_keys = {
            "id", "conversation_id", "source_id", "source_scope", "enabled",
            "enabled_at", "disabled_at", "used_in_last_answer", "last_used_at", "owner_note"
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

