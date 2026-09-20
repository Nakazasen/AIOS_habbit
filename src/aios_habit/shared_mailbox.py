"""Shared per-store mailbox for warehouse requests (004 extension).

English code comments by repo rule. User-facing strings stay in the UI layer.
Each store owns its mailbox inside its own folder so requests travel with the
store and new stores need no code change. Writes take LibraryWriterLease on
the mailbox directory; readers never lock.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from aios_habit.workspace_chat_store import LibraryWriterLease

MAILBOX_DIRNAME = "_YeuCau"
MAILBOX_FILENAME = "yeu_cau.jsonl"

STATUS_OPEN = "open"
STATUS_DONE = "done"


@dataclass
class MailboxRequest:
    request_id: str
    store_name: str
    text: str
    requested_by: str
    created_at: str
    status: str = STATUS_OPEN
    handled_by: str = ""
    handled_at: str = ""


def mailbox_dir(store_folder: str | Path) -> Path:
    return Path(store_folder) / MAILBOX_DIRNAME


def mailbox_file(store_folder: str | Path) -> Path:
    return mailbox_dir(store_folder) / MAILBOX_FILENAME


def is_local_store_folder(store_folder: str | Path) -> bool:
    """Check whether a store folder lives inside this machine's local cases."""
    try:
        resolved = Path(store_folder).resolve()
        local_root = (Path.cwd() / "local_cases").resolve()
        return resolved.is_relative_to(local_root)
    except (OSError, ValueError):
        return False


def append_request(
    store_folder: str | Path,
    store_name: str,
    text: str,
    requested_by: str,
) -> MailboxRequest:
    """Append one request to the store mailbox under an exclusive lease."""
    clean_text = str(text or "").strip()
    if not clean_text:
        raise ValueError("mailbox_text_required")
    clean_name = str(requested_by or "").strip()
    if not clean_name:
        raise ValueError("mailbox_requester_required")
    folder = Path(store_folder)
    box_dir = mailbox_dir(folder)
    lease = LibraryWriterLease(box_dir)
    if not lease.acquire():
        raise ValueError("library_writer_busy")
    try:
        request = MailboxRequest(
            request_id=uuid.uuid4().hex[:8],
            store_name=str(store_name or "").strip(),
            text=clean_text,
            requested_by=clean_name,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        box_dir.mkdir(parents=True, exist_ok=True)
        with mailbox_file(folder).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(request), ensure_ascii=False) + "\n")
        return request
    finally:
        lease.release()


def list_requests(store_folder: str | Path) -> List[MailboxRequest]:
    """Read all requests newest first without taking any lock."""
    path = mailbox_file(store_folder)
    if not path.exists():
        return []
    items: List[MailboxRequest] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            items.append(MailboxRequest(**{k: data.get(k, "") for k in (
                "request_id", "store_name", "text", "requested_by",
                "created_at", "status", "handled_by", "handled_at",
            )}))
        except (ValueError, TypeError):
            continue
    items.reverse()
    return items


def mark_done(
    store_folder: str | Path,
    request_id: str,
    handled_by: str,
) -> MailboxRequest:
    """Mark one request done, recording who did it and when."""
    clean_handler = str(handled_by or "").strip()
    if not clean_handler:
        raise ValueError("mailbox_requester_required")
    folder = Path(store_folder)
    box_dir = mailbox_dir(folder)
    lease = LibraryWriterLease(box_dir)
    if not lease.acquire():
        raise ValueError("library_writer_busy")
    try:
        current = list_requests(folder)
        target: Optional[MailboxRequest] = next(
            (item for item in current if item.request_id == request_id), None
        )
        if target is None:
            raise ValueError("mailbox_request_missing")
        target.status = STATUS_DONE
        target.handled_by = clean_handler
        target.handled_at = datetime.now().isoformat(timespec="seconds")
        box_dir.mkdir(parents=True, exist_ok=True)
        with mailbox_file(folder).open("w", encoding="utf-8") as handle:
            for item in reversed(current):
                handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
        return target
    finally:
        lease.release()


def request_to_dict(request: MailboxRequest) -> Dict[str, Any]:
    return asdict(request)
