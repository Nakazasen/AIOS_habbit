"""Small, failure-visible helpers for local JSONL persistence."""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from collections.abc import Callable, Iterable
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, TypeVar


LOGGER = logging.getLogger(__name__)
T = TypeVar("T")

_JSONL_CACHE: dict[tuple[Path, int, int, Any], list[Any]] = {}


def clear_jsonl_cache() -> None:
    _JSONL_CACHE.clear()


def load_jsonl_records(path: Path, deserialize: Callable[[dict[str, Any]], T]) -> list[T]:
    """Load valid records while making corrupt local rows visible in logs.

    A malformed row does not make a local workspace unusable, but it must never
    disappear silently: the warning includes only the filename and line number,
    never the potentially private record contents.
    """
    if not path.exists():
        return []

    cache_key = None
    try:
        stat = path.stat()
        cache_key = (path.resolve(), stat.st_mtime_ns, stat.st_size, deserialize)
        if cache_key in _JSONL_CACHE:
            return list(_JSONL_CACHE[cache_key])
    except OSError:
        pass

    records: list[T] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(deserialize(json.loads(line)))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                LOGGER.warning(
                    "Skipping invalid local record in %s at line %d: %s",
                    path.name,
                    line_number,
                    exc,
                )

    if cache_key is not None:
        _JSONL_CACHE[cache_key] = list(records)
    return records



def serialize_record(record: Any) -> dict[str, Any]:
    if hasattr(record, "to_dict"):
        return record.to_dict()
    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, dict):
        return record
    raise TypeError(f"Cannot serialize {type(record).__name__} as a JSONL record")


def atomic_write_jsonl(path: Path, records: Iterable[Any]) -> None:
    """Durably replace one JSONL file, leaving its prior version intact on failure."""
    atomic_write_jsonl_batch(((path, records),))


def atomic_write_jsonl_batch(targets: Iterable[tuple[Path, Iterable[Any]]]) -> None:
    """Replace related JSONL files with rollback if any replacement fails.

    Filesystems cannot atomically replace several files at once. This helper
    writes and fsyncs every temporary file first, then rolls back already
    replaced targets if a later replacement fails.
    """
    prepared = [(path, list(records)) for path, records in targets]
    token = uuid.uuid4().hex
    temporary_files: list[tuple[Path, Path]] = []
    backups: list[tuple[Path, Path]] = []
    replaced: list[tuple[Path, Path | None]] = []

    try:
        for path, records in prepared:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.{token}.tmp")
            temporary_files.append((path, temporary))
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                for record in records:
                    handle.write(json.dumps(serialize_record(record), ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())

        for path, temporary in temporary_files:
            backup: Path | None = None
            if path.exists():
                backup = path.with_name(f".{path.name}.{token}.bak")
                shutil.copy2(path, backup)
                backups.append((path, backup))
            os.replace(temporary, path)
            replaced.append((path, backup))
    except Exception:
        LOGGER.exception("Local JSONL persistence failed; attempting rollback")
        for path, backup in reversed(replaced):
            try:
                if backup is not None and backup.exists():
                    os.replace(backup, path)
                elif path.exists():
                    path.unlink()
            except OSError:
                LOGGER.exception("Could not roll back local JSONL file %s", path.name)
        raise
    finally:
        for _, temporary in temporary_files:
            temporary.unlink(missing_ok=True)
        for _, backup in backups:
            backup.unlink(missing_ok=True)
        for path, _ in prepared:
            try:
                resolved_p = path.resolve()
                stale_keys = [k for k in _JSONL_CACHE if k[0] == resolved_p]
                for k in stale_keys:
                    _JSONL_CACHE.pop(k, None)
            except Exception:
                pass
