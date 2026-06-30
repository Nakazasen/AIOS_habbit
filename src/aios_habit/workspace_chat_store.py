import json
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    TemporaryConversationSource,
    NotebookSource,
    ConversationSourceSelection
)

LOCAL_CHAT_DIR = Path.cwd() / "local_cases" / "workspace_chat"
NOTEBOOKS_FILE = LOCAL_CHAT_DIR / "notebooks.jsonl"
CONVERSATIONS_FILE = LOCAL_CHAT_DIR / "conversations.jsonl"
MESSAGES_FILE = LOCAL_CHAT_DIR / "messages.jsonl"
TEMPORARY_SOURCES_FILE = LOCAL_CHAT_DIR / "temporary_sources.jsonl"
NOTEBOOK_SOURCES_FILE = LOCAL_CHAT_DIR / "notebook_sources.jsonl"
SOURCE_SELECTIONS_FILE = LOCAL_CHAT_DIR / "conversation_source_selections.jsonl"

def init_chat_store():
    LOCAL_CHAT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Touch files
    for filepath in [
        NOTEBOOKS_FILE, CONVERSATIONS_FILE, MESSAGES_FILE, TEMPORARY_SOURCES_FILE,
        NOTEBOOK_SOURCES_FILE, SOURCE_SELECTIONS_FILE
    ]:
        if not filepath.exists():
            filepath.touch()
            
    # Auto-initialize default notebooks if empty
    nbs = load_notebooks()
    if not nbs:
        defaults = [
            DocumentNotebook(id="mom_opcenter", title="MOM / Opcenter", description="Sổ biên bản cuộc họp và thông tin vận hành Opcenter"),
            DocumentNotebook(id="interstock_wms", title="InterStock / WMS", description="Sổ thông tin hệ thống kho InterStock và phần mềm WMS"),
            DocumentNotebook(id="email_jp_vn", title="Email Nhật - Việt", description="Sổ lưu trữ trao đổi thư từ Nhật Bản và Việt Nam"),
            DocumentNotebook(id="aios_project", title="AIOS Project", description="Sổ thông tin dự án AIOS và tài liệu hướng dẫn vận hành")
        ]
        for nb in defaults:
            save_notebook(nb)

def load_notebooks() -> List[DocumentNotebook]:
    if not NOTEBOOKS_FILE.exists():
        return []
    notebooks = []
    with open(NOTEBOOKS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    notebooks.append(DocumentNotebook(**data))
                except Exception:
                    pass
    return notebooks

def load_notebook(notebook_id: str) -> Optional[DocumentNotebook]:
    for nb in load_notebooks():
        if nb.id == notebook_id:
            return nb
    return None

def save_notebook(nb: DocumentNotebook):
    notebooks = load_notebooks()
    found = False
    for i, item in enumerate(notebooks):
        if item.id == nb.id:
            notebooks[i] = nb
            found = True
            break
    if not found:
        notebooks.append(nb)
        
    with open(NOTEBOOKS_FILE, 'w', encoding='utf-8') as f:
        for item in notebooks:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + '\n')

def load_all_conversations() -> List[WorkspaceConversation]:
    if not CONVERSATIONS_FILE.exists():
        return []
    conversations = []
    with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    conversations.append(WorkspaceConversation(**data))
                except Exception:
                    pass
    return conversations

def load_conversations(notebook_id: str) -> List[WorkspaceConversation]:
    return [c for c in load_all_conversations() if c.notebook_id == notebook_id]

def load_conversation(conv_id: str) -> Optional[WorkspaceConversation]:
    for c in load_all_conversations():
        if c.id == conv_id:
            return c
    return None

def save_conversation(conv: WorkspaceConversation):
    conversations = load_all_conversations()
    found = False
    for i, item in enumerate(conversations):
        if item.id == conv.id:
            conversations[i] = conv
            found = True
            break
    if not found:
        conversations.append(conv)
        
    with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
        for item in conversations:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + '\n')

def rename_conversation(conv_id: str, new_title: str):
    conv = load_conversation(conv_id)
    if conv:
        conv.title = new_title
        save_conversation(conv)

def load_all_messages() -> List[ChatMessage]:
    if not MESSAGES_FILE.exists():
        return []
    messages = []
    with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    messages.append(ChatMessage(**data))
                except Exception:
                    pass
    return messages

def load_messages(conv_id: str) -> List[ChatMessage]:
    return [m for m in load_all_messages() if m.conversation_id == conv_id]

def save_message(msg: ChatMessage):
    messages = load_all_messages()
    messages.append(msg)
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        for item in messages:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + '\n')

def load_all_temporary_sources() -> List[TemporaryConversationSource]:
    if not TEMPORARY_SOURCES_FILE.exists():
        return []
    sources = []
    with open(TEMPORARY_SOURCES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    sources.append(TemporaryConversationSource(**data))
                except Exception:
                    pass
    return sources

def load_temporary_sources(conv_id: str) -> List[TemporaryConversationSource]:
    return [s for s in load_all_temporary_sources() if s.conversation_id == conv_id]

def save_temporary_source(src: TemporaryConversationSource):
    sources = load_all_temporary_sources()
    found = False
    for i, item in enumerate(sources):
        if item.id == src.id:
            sources[i] = src
            found = True
            break
    if not found:
        sources.append(src)
        
    with open(TEMPORARY_SOURCES_FILE, 'w', encoding='utf-8') as f:
        for item in sources:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + '\n')

def load_all_notebook_sources() -> List[NotebookSource]:
    if not NOTEBOOK_SOURCES_FILE.exists():
        return []
    sources = []
    with open(NOTEBOOK_SOURCES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    sources.append(NotebookSource.from_dict(data))
                except Exception:
                    pass
    return sources

def load_notebook_sources(notebook_id: str) -> List[NotebookSource]:
    return [s for s in load_all_notebook_sources() if s.notebook_id == notebook_id]

def save_notebook_source(source: NotebookSource) -> NotebookSource:
    sources = load_all_notebook_sources()
    found = False
    for i, item in enumerate(sources):
        if item.id == source.id:
            sources[i] = source
            found = True
            break
    if not found:
        sources.append(source)
        
    with open(NOTEBOOK_SOURCES_FILE, 'w', encoding='utf-8') as f:
        for item in sources:
            f.write(json.dumps(item.to_dict(), ensure_ascii=False) + '\n')
    return source

def get_notebook_source(source_id: str) -> Optional[NotebookSource]:
    for s in load_all_notebook_sources():
        if s.id == source_id:
            return s
    return None

def delete_notebook_source(source_id: str) -> bool:
    sources = load_all_notebook_sources()
    initial_len = len(sources)
    sources = [s for s in sources if s.id != source_id]
    if len(sources) == initial_len:
        return False
    with open(NOTEBOOK_SOURCES_FILE, 'w', encoding='utf-8') as f:
        for item in sources:
            f.write(json.dumps(item.to_dict(), ensure_ascii=False) + '\n')
    return True

def load_all_conversation_source_selections() -> List[ConversationSourceSelection]:
    if not SOURCE_SELECTIONS_FILE.exists():
        return []
    selections = []
    with open(SOURCE_SELECTIONS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    selections.append(ConversationSourceSelection.from_dict(data))
                except Exception:
                    pass
    return selections

def load_conversation_source_selections(conversation_id: str) -> List[ConversationSourceSelection]:
    return [s for s in load_all_conversation_source_selections() if s.conversation_id == conversation_id]

def save_conversation_source_selection(selection: ConversationSourceSelection) -> ConversationSourceSelection:
    selections = load_all_conversation_source_selections()
    found = False
    for i, item in enumerate(selections):
        if item.id == selection.id:
            selections[i] = selection
            found = True
            break
    if not found:
        selections.append(selection)
        
    with open(SOURCE_SELECTIONS_FILE, 'w', encoding='utf-8') as f:
        for item in selections:
            f.write(json.dumps(item.to_dict(), ensure_ascii=False) + '\n')
    return selection

def set_source_enabled(
    conversation_id: str,
    source_scope: str,
    source_id: str,
    enabled: bool,
) -> ConversationSourceSelection:
    selections = load_conversation_source_selections(conversation_id)
    existing = None
    for s in selections:
        if s.source_id == source_id and s.source_scope == source_scope:
            existing = s
            break
            
    now_iso = datetime.now().isoformat()
    if existing:
        existing.enabled = enabled
        if enabled:
            existing.enabled_at = now_iso
        else:
            existing.disabled_at = now_iso
        save_conversation_source_selection(existing)
        return existing
    else:
        new_sel = ConversationSourceSelection(
            id=f"SEL-{uuid.uuid4().hex[:8].upper()}",
            conversation_id=conversation_id,
            source_id=source_id,
            source_scope=source_scope,
            enabled=enabled,
            enabled_at=now_iso if enabled else None,
            disabled_at=None if enabled else now_iso
        )
        save_conversation_source_selection(new_sel)
        return new_sel

def load_enabled_sources_for_conversation(conversation_id: str) -> List[ConversationSourceSelection]:
    return [s for s in load_conversation_source_selections(conversation_id) if s.enabled]

def promote_temporary_source_to_notebook(
    conversation_id: str,
    temporary_source_id: str,
    notebook_id: str,
    title: str | None = None,
) -> NotebookSource:
    temp_sources = load_temporary_sources(conversation_id)
    temp_src = None
    for s in temp_sources:
        if s.id == temporary_source_id:
            temp_src = s
            break
            
    if not temp_src:
        raise ValueError(f"Temporary source not found: {temporary_source_id} in conversation {conversation_id}")
        
    temp_src.long_term_saved = True
    temp_src.status = "added_to_notebook"
    save_temporary_source(temp_src)
    
    nb_src = NotebookSource(
        id=f"SRC-{uuid.uuid4().hex[:8].upper()}",
        notebook_id=notebook_id,
        title=title if title is not None else temp_src.title,
        source_type=temp_src.source_type,
        privacy_label=temp_src.privacy_label,
        content_preview=temp_src.content_preview,
        content_text=temp_src.content_text,
        origin_temporary_source_id=temp_src.id
    )
    save_notebook_source(nb_src)
    
    return nb_src
