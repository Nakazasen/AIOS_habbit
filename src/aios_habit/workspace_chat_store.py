import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional
from aios_habit.workspace_chat_models import (
    DocumentNotebook,
    WorkspaceConversation,
    ChatMessage,
    TemporaryConversationSource
)

LOCAL_CHAT_DIR = Path.cwd() / "local_cases" / "workspace_chat"
NOTEBOOKS_FILE = LOCAL_CHAT_DIR / "notebooks.jsonl"
CONVERSATIONS_FILE = LOCAL_CHAT_DIR / "conversations.jsonl"
MESSAGES_FILE = LOCAL_CHAT_DIR / "messages.jsonl"
TEMPORARY_SOURCES_FILE = LOCAL_CHAT_DIR / "temporary_sources.jsonl"

def init_chat_store():
    LOCAL_CHAT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Touch files
    for filepath in [NOTEBOOKS_FILE, CONVERSATIONS_FILE, MESSAGES_FILE, TEMPORARY_SOURCES_FILE]:
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
