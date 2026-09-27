"""Durable per-file ingest manifest.

The manifest records, for every source file the pipeline has ingested, the
content fingerprint (sha256) together with the file's mtime and size at ingest
time. On the next ingest run the pipeline first compares only mtime and size
(a cheap stat call): when they match, the file is skipped without being read,
converted, chunked or hashed again.

The manifest is stored as JSON next to the index sqlite file and is written
atomically (temporary file + os.replace). It is a fast-path cache only: the
index's own source fingerprints remain the source of truth, so a manifest hit
is always cross-checked against the index before skipping.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional, Union


@dataclass(frozen=True)
class IngestManifestEntry:
    """One recorded ingest of a source file."""

    sha256: str
    mtime_ns: int
    size: int
    document_id: str

    def matches_stat(self, stat_result: os.stat_result) -> bool:
        """True when the file metadata is byte-identical to ingest time."""
        return (
            self.mtime_ns == stat_result.st_mtime_ns
            and self.size == stat_result.st_size
        )


class IngestManifest:
    """JSON manifest of ingested source files, stored beside the index."""

    VERSION = 1

    def __init__(self, path: Union[Path, str]) -> None:
        self.path = Path(path)
        self._entries: Dict[str, IngestManifestEntry] = {}
        self._dirty = False
        self._load()

    @staticmethod
    def key_for(source_path: Union[Path, str]) -> str:
        """Stable manifest key for a source file.

        SourceSpec already resolves paths to absolute form; the key is the
        path string as given.
        """
        return str(Path(source_path))

    @classmethod
    def default_path_for_index(cls, index_path: Union[Path, str]) -> Path:
        return Path(f"{index_path}.ingest_manifest.json")

    def lookup(self, key: str) -> Optional[IngestManifestEntry]:
        return self._entries.get(key)

    def record(
        self,
        key: str,
        *,
        sha256: str,
        mtime_ns: int,
        size: int,
        document_id: str,
    ) -> None:
        self._entries[key] = IngestManifestEntry(
            sha256=sha256,
            mtime_ns=mtime_ns,
            size=size,
            document_id=document_id,
        )
        self._dirty = True

    def save(self) -> None:
        """Persist pending records atomically. No-op when nothing changed."""
        if not self._dirty:
            return
        payload = {
            "version": self.VERSION,
            "files": {
                key: asdict(entry) for key, entry in sorted(self._entries.items())
            },
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp_path, self.path)
        self._dirty = False

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # Missing or corrupt manifest: start empty. The index fingerprint
            # gate stays the source of truth, so the worst case is a re-ingest.
            return
        files = raw.get("files")
        if not isinstance(files, dict):
            return
        for key, item in files.items():
            if not isinstance(item, dict):
                continue
            try:
                self._entries[str(key)] = IngestManifestEntry(
                    sha256=str(item["sha256"]),
                    mtime_ns=int(item["mtime_ns"]),
                    size=int(item["size"]),
                    document_id=str(item["document_id"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
