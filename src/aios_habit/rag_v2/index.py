"""Local SQLite index for generic RAG v2 chunks."""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .chunking import DocumentChunk

_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


def _tokens(value: str) -> List[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(value or "")]


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    score: float
    text: str
    document_id: str
    source_path: str
    source_name: str
    file_type: str
    metadata: Dict[str, Any]
    privacy_labels: tuple[str, ...]


class LocalChunkIndex:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                text TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                privacy_labels_json TEXT NOT NULL,
                source_fingerprint TEXT,
                checksum TEXT
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)")
        self._conn.commit()

    def upsert_chunks(self, chunks: Iterable[DocumentChunk]) -> int:
        rows = [self._chunk_row(chunk) for chunk in chunks]
        if not rows:
            return 0
        self._conn.executemany(
            """
            INSERT INTO chunks (
                chunk_id, document_id, source_path, source_name, file_type,
                text, normalized_text, metadata_json, privacy_labels_json,
                source_fingerprint, checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                document_id=excluded.document_id,
                source_path=excluded.source_path,
                source_name=excluded.source_name,
                file_type=excluded.file_type,
                text=excluded.text,
                normalized_text=excluded.normalized_text,
                metadata_json=excluded.metadata_json,
                privacy_labels_json=excluded.privacy_labels_json,
                source_fingerprint=excluded.source_fingerprint,
                checksum=excluded.checksum
            """,
            rows,
        )
        self._conn.commit()
        return len(rows)

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        terms = _tokens(query)
        if not terms or limit <= 0:
            return []
        rows = self._conn.execute("SELECT * FROM chunks").fetchall()
        scored: List[SearchResult] = []
        for row in rows:
            text = row["normalized_text"]
            score = sum(text.count(term) for term in terms)
            if score <= 0:
                continue
            metadata = json.loads(row["metadata_json"])
            privacy_labels = tuple(json.loads(row["privacy_labels_json"] or "[]"))
            scored.append(
                SearchResult(
                    chunk_id=row["chunk_id"],
                    score=float(score),
                    text=row["text"],
                    document_id=row["document_id"],
                    source_path=row["source_path"],
                    source_name=row["source_name"],
                    file_type=row["file_type"],
                    metadata=metadata,
                    privacy_labels=privacy_labels,
                )
            )
        scored.sort(key=lambda result: (-result.score, result.chunk_id))
        return scored[:limit]

    def clear(self) -> None:
        self._conn.execute("DELETE FROM chunks")
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()
        return int(row["count"])

    def close(self) -> None:
        self._conn.close()

    def _chunk_row(self, chunk: DocumentChunk) -> tuple[Any, ...]:
        metadata = chunk.to_dict()
        return (
            chunk.chunk_id,
            chunk.document_id,
            chunk.source_path,
            chunk.source_name,
            chunk.file_type,
            chunk.text,
            chunk.normalized_text,
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            json.dumps(list(chunk.privacy_labels), ensure_ascii=False),
            chunk.source_fingerprint,
            chunk.checksum,
        )

    def __enter__(self) -> "LocalChunkIndex":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
