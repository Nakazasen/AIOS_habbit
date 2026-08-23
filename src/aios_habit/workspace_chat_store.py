import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Optional
from aios_habit.local_jsonl import atomic_write_jsonl, atomic_write_jsonl_batch, load_jsonl_records
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
LOGGER = logging.getLogger(__name__)

def init_chat_store():
    LOCAL_CHAT_DIR.mkdir(parents=True, exist_ok=True)
    init_flag = LOCAL_CHAT_DIR / ".initialized"

    # Touch files
    for filepath in [
        NOTEBOOKS_FILE, CONVERSATIONS_FILE, MESSAGES_FILE, TEMPORARY_SOURCES_FILE,
        NOTEBOOK_SOURCES_FILE, SOURCE_SELECTIONS_FILE
    ]:
        if not filepath.exists():
            filepath.touch()

    # Auto-initialize default notebooks only on very first setup
    if not init_flag.exists():
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
        try:
            init_flag.touch()
        except OSError:
            LOGGER.exception("Could not mark Workspace Chat storage as initialized")

def _deserialize_notebook(record: dict) -> DocumentNotebook:
    return DocumentNotebook(**record)


def _deserialize_conversation(record: dict) -> WorkspaceConversation:
    return WorkspaceConversation(**record)


def _deserialize_message(record: dict) -> ChatMessage:
    return ChatMessage(**record)


def _deserialize_temporary_source(record: dict) -> TemporaryConversationSource:
    return TemporaryConversationSource(**record)


def load_notebooks() -> List[DocumentNotebook]:
    if not NOTEBOOKS_FILE.exists():
        return []
    return load_jsonl_records(NOTEBOOKS_FILE, _deserialize_notebook)


def notebook_is_archived(notebook: DocumentNotebook) -> bool:
    return notebook.is_archived()


def load_active_notebooks() -> List[DocumentNotebook]:
    return [nb for nb in load_notebooks() if not notebook_is_archived(nb)]


def load_archived_notebooks() -> List[DocumentNotebook]:
    return [nb for nb in load_notebooks() if notebook_is_archived(nb)]


def archive_notebook(notebook_id: str) -> bool:
    notebook = load_notebook(notebook_id)
    if notebook is None:
        return False
    if not notebook_is_archived(notebook):
        now_iso = datetime.now().isoformat()
        notebook.archived_at = now_iso
        notebook.updated_at = now_iso
        save_notebook(notebook)
    return True


def restore_notebook(notebook_id: str) -> bool:
    notebook = load_notebook(notebook_id)
    if notebook is None:
        return False
    if notebook_is_archived(notebook):
        notebook.archived_at = None
        notebook.updated_at = datetime.now().isoformat()
        save_notebook(notebook)
    return True

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

    atomic_write_jsonl(NOTEBOOKS_FILE, notebooks)

def load_all_conversations() -> List[WorkspaceConversation]:
    if not CONVERSATIONS_FILE.exists():
        return []
    return load_jsonl_records(CONVERSATIONS_FILE, _deserialize_conversation)

def load_conversations(notebook_id: str) -> List[WorkspaceConversation]:
    return [c for c in load_all_conversations() if c.notebook_id == notebook_id]

def load_conversation(conv_id: str) -> Optional[WorkspaceConversation]:
    for c in load_all_conversations():
        if c.id == conv_id:
            return c
    return None


def resolve_conversation_id(notebook_id: str, requested_conversation_id: Optional[str]) -> Optional[str]:
    """Return a valid conversation ID for a notebook, or None when it is empty."""
    conversations = load_conversations(notebook_id)
    if requested_conversation_id and any(c.id == requested_conversation_id for c in conversations):
        return requested_conversation_id
    return conversations[0].id if conversations else None

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

    atomic_write_jsonl(CONVERSATIONS_FILE, conversations)

def rename_conversation(conv_id: str, new_title: str):
    conv = load_conversation(conv_id)
    if conv:
        conv.title = new_title
        conv.updated_at = datetime.now().isoformat()
        save_conversation(conv)

def update_conversation_search_preference(conv_id: str, search_preference: str) -> bool:
    conv = load_conversation(conv_id)
    if conv:
        conv.search_preference = search_preference
        conv.updated_at = datetime.now().isoformat()
        save_conversation(conv)
        return True
    return False


def delete_conversation(conv_id: str) -> bool:
    conversations = load_all_conversations()
    new_convs = [c for c in conversations if c.id != conv_id]
    if len(new_convs) == len(conversations):
        return False

    messages = [m for m in load_all_messages() if m.conversation_id != conv_id]
    temp_sources = [s for s in load_all_temporary_sources() if s.conversation_id != conv_id]
    selections = [sel for sel in load_all_conversation_source_selections() if sel.conversation_id != conv_id]
    atomic_write_jsonl_batch((
        (CONVERSATIONS_FILE, new_convs),
        (MESSAGES_FILE, messages),
        (TEMPORARY_SOURCES_FILE, temp_sources),
        (SOURCE_SELECTIONS_FILE, selections),
    ))

    return True

def load_all_messages() -> List[ChatMessage]:
    if not MESSAGES_FILE.exists():
        return []
    return load_jsonl_records(MESSAGES_FILE, _deserialize_message)

def load_messages(conv_id: str) -> List[ChatMessage]:
    return [m for m in load_all_messages() if m.conversation_id == conv_id]

def save_message(msg: ChatMessage):
    messages = load_all_messages()
    messages.append(msg)
    atomic_write_jsonl(MESSAGES_FILE, messages)

def load_all_temporary_sources() -> List[TemporaryConversationSource]:
    if not TEMPORARY_SOURCES_FILE.exists():
        return []
    return load_jsonl_records(TEMPORARY_SOURCES_FILE, _deserialize_temporary_source)

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

    atomic_write_jsonl(TEMPORARY_SOURCES_FILE, sources)

def load_all_notebook_sources() -> List[NotebookSource]:
    if not NOTEBOOK_SOURCES_FILE.exists():
        return []
    return load_jsonl_records(NOTEBOOK_SOURCES_FILE, NotebookSource.from_dict)

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

    atomic_write_jsonl(NOTEBOOK_SOURCES_FILE, sources)
    return source

def get_notebook_source(source_id: str) -> Optional[NotebookSource]:
    for s in load_all_notebook_sources():
        if s.id == source_id:
            return s
    return None

def delete_notebook_source(source_id: str) -> bool:
    return bool(delete_sources("notebook", [source_id]).get("sources"))

def delete_temporary_source(source_id: str) -> bool:
    return bool(delete_sources("temporary", [source_id]).get("sources"))


def _source_records_for_scope(scope: str) -> list[Any]:
    if scope == "notebook":
        return load_all_notebook_sources()
    if scope == "temporary":
        return load_all_temporary_sources()
    raise ValueError(f"Unsupported source scope: {scope}")


def find_source_ids_by_title(scope: str, owner_id: str, title: str) -> list[str]:
    """Find sources with the same visible title within one chat or notebook."""
    normalized_title = str(title or "").strip().casefold()
    if not normalized_title:
        return []
    if scope == "notebook":
        return [
            source.id for source in load_notebook_sources(owner_id)
            if source.title.strip().casefold() == normalized_title
        ]
    if scope == "temporary":
        return [
            source.id for source in load_temporary_sources(owner_id)
            if source.title.strip().casefold() == normalized_title
        ]
    raise ValueError(f"Unsupported source scope: {scope}")


def snapshot_sources(scope: str, source_ids: Iterable[str]) -> dict[str, Any]:
    """Capture sources and their selections so a UI action can be undone safely."""
    requested_ids = {str(source_id) for source_id in source_ids}
    sources = [source for source in _source_records_for_scope(scope) if source.id in requested_ids]
    source_id_set = {source.id for source in sources}
    selections = [
        selection for selection in load_all_conversation_source_selections()
        if selection.source_scope == scope and selection.source_id in source_id_set
    ]
    return {
        "scope": scope,
        "sources": [asdict(source) for source in sources],
        "selections": [asdict(selection) for selection in selections],
    }


def delete_sources(scope: str, source_ids: Iterable[str]) -> dict[str, Any]:
    """Delete one or more sources in one scope and return an undo snapshot."""
    snapshot = snapshot_sources(scope, source_ids)
    source_id_set = {record["id"] for record in snapshot["sources"]}
    if not source_id_set:
        return snapshot

    remaining_sources = [
        source for source in _source_records_for_scope(scope)
        if source.id not in source_id_set
    ]
    remaining_selections = [
        selection for selection in load_all_conversation_source_selections()
        if not (selection.source_scope == scope and selection.source_id in source_id_set)
    ]
    source_file = NOTEBOOK_SOURCES_FILE if scope == "notebook" else TEMPORARY_SOURCES_FILE
    atomic_write_jsonl_batch(((source_file, remaining_sources), (SOURCE_SELECTIONS_FILE, remaining_selections)))
    return snapshot


def restore_source_snapshot(snapshot: dict[str, Any]) -> int:
    """Restore a snapshot made by ``delete_sources`` without overwriting newer data."""
    scope = str(snapshot.get("scope") or "")
    records = list(snapshot.get("sources") or [])
    if scope not in {"notebook", "temporary"} or not records:
        return 0

    source_type = NotebookSource if scope == "notebook" else TemporaryConversationSource
    current_sources = _source_records_for_scope(scope)
    known_ids = {source.id for source in current_sources}
    restored_sources = [source_type(**record) for record in records if record.get("id") not in known_ids]
    if not restored_sources:
        return 0

    current_selections = load_all_conversation_source_selections()
    known_selection_ids = {selection.id for selection in current_selections}
    restored_selections = [
        ConversationSourceSelection(**record)
        for record in snapshot.get("selections") or []
        if record.get("id") not in known_selection_ids
    ]
    source_file = NOTEBOOK_SOURCES_FILE if scope == "notebook" else TEMPORARY_SOURCES_FILE
    atomic_write_jsonl_batch(((source_file, [*current_sources, *restored_sources]), (SOURCE_SELECTIONS_FILE, [*current_selections, *restored_selections])))
    return len(restored_sources)


def purge_unreferenced_managed_files(snapshot: dict[str, Any]) -> int:
    """Remove only app-owned workbook copies after an undo window has elapsed."""
    try:
        from aios_habit.workspace_chat_source_ingest import MANAGED_WORKBOOK_ROOT
    except ImportError:
        return 0

    managed_root = MANAGED_WORKBOOK_ROOT.resolve()
    live_paths = {
        str(Path(source.managed_path).resolve())
        for source in [*load_all_notebook_sources(), *load_all_temporary_sources()]
        if getattr(source, "managed_path", "")
    }
    removed = 0
    for record in snapshot.get("sources") or []:
        managed_path = str(record.get("managed_path") or "")
        if not managed_path:
            continue
        try:
            candidate = Path(managed_path).resolve()
            if managed_root not in candidate.parents or str(candidate) in live_paths:
                continue
            if candidate.is_file():
                candidate.unlink()
                removed += 1
        except OSError:
            LOGGER.warning("Could not remove managed source file", exc_info=True)
    return removed

def load_all_conversation_source_selections() -> List[ConversationSourceSelection]:
    if not SOURCE_SELECTIONS_FILE.exists():
        return []
    return load_jsonl_records(SOURCE_SELECTIONS_FILE, ConversationSourceSelection.from_dict)

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

    atomic_write_jsonl(SOURCE_SELECTIONS_FILE, selections)
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
        origin_temporary_source_id=temp_src.id,
        managed_path=temp_src.managed_path,
    )
    save_notebook_source(nb_src)

    return nb_src


def delete_notebook_permanently(notebook_id: str) -> bool:
    notebook = load_notebook(notebook_id)
    if notebook is None:
        return False

    conversations = load_conversations(notebook_id)
    conv_ids = {c.id for c in conversations}

    notebooks = load_notebooks()
    notebooks = [nb for nb in notebooks if nb.id != notebook_id]

    all_convs = load_all_conversations()
    all_convs = [c for c in all_convs if c.notebook_id != notebook_id]

    all_msgs = load_all_messages()
    all_msgs = [m for m in all_msgs if m.conversation_id not in conv_ids]

    all_nb_sources = load_all_notebook_sources()
    all_nb_sources = [s for s in all_nb_sources if s.notebook_id != notebook_id]

    all_temp_sources = load_all_temporary_sources()
    all_temp_sources = [s for s in all_temp_sources if s.conversation_id not in conv_ids]

    all_selections = load_all_conversation_source_selections()
    all_selections = [sel for sel in all_selections if sel.conversation_id not in conv_ids]

    targets = [
        (NOTEBOOKS_FILE, notebooks),
        (CONVERSATIONS_FILE, all_convs),
        (MESSAGES_FILE, all_msgs),
        (NOTEBOOK_SOURCES_FILE, all_nb_sources),
        (TEMPORARY_SOURCES_FILE, all_temp_sources),
        (SOURCE_SELECTIONS_FILE, all_selections),
    ]

    try:
        atomic_write_jsonl_batch(targets)
    except OSError:
        LOGGER.exception("Could not delete notebook %s without losing related records", notebook_id)
        return False
    return True
