"""Append-only chunk revision store for Lite-CPU pilot (E5).

Keeps edit history with diff-friendly snapshots and one-touch rollback.
Local-only; never sends raw text to cloud. Reindex flag tells the caller
to rebuild the affected local index entries.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ChunkRevision:
    chunk_id: str
    version: int
    text: str
    checksum: str
    created_at: float
    note: str = ""
    needs_reindex: bool = True


@dataclass
class ChunkRevisionStore:
    path: Path
    revisions: Dict[str, List[ChunkRevision]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "ChunkRevisionStore":
        store = cls(path=path)
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                rev = ChunkRevision(**item)
                store.revisions.setdefault(rev.chunk_id, []).append(rev)
        return store

    def _append_line(self, rev: ChunkRevision) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(rev.__dict__, ensure_ascii=False) + "\n")

    def current(self, chunk_id: str) -> Optional[ChunkRevision]:
        items = self.revisions.get(chunk_id, [])
        return items[-1] if items else None

    def edit(self, chunk_id: str, new_text: str, note: str = "") -> ChunkRevision:
        cleaned = (new_text or "").strip()
        if not cleaned:
            raise ValueError("empty chunk text")
        version = len(self.revisions.get(chunk_id, [])) + 1
        rev = ChunkRevision(
            chunk_id=chunk_id,
            version=version,
            text=cleaned,
            checksum=hashlib.sha256(cleaned.encode("utf-8")).hexdigest(),
            created_at=time.time(),
            note=note,
            needs_reindex=True,
        )
        self.revisions.setdefault(chunk_id, []).append(rev)
        self._append_line(rev)
        return rev

    def rollback(self, chunk_id: str, version: int) -> ChunkRevision:
        items = self.revisions.get(chunk_id, [])
        target = next((item for item in items if item.version == version), None)
        if target is None:
            raise ValueError("unknown revision version")
        return self.edit(chunk_id, target.text, note=f"rollback-to-v{version}")

    def diff(self, chunk_id: str, from_version: int, to_version: int) -> str:
        items = {item.version: item for item in self.revisions.get(chunk_id, [])}
        if from_version not in items or to_version not in items:
            raise ValueError("unknown revision version")
        old_lines = items[from_version].text.splitlines()
        new_lines = items[to_version].text.splitlines()
        return "\n".join(difflib.unified_diff(old_lines, new_lines, lineterm=""))

    def history(self, chunk_id: str) -> List[Dict[str, Any]]:
        return [rev.__dict__ for rev in self.revisions.get(chunk_id, [])]
