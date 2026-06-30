import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class DocumentNotebook:
    id: str
    title: str
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

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
