"""One-shot maintenance for document-summary provenance.

Copy ``source_fingerprint`` and ``privacy_labels_json`` onto summary chunks that
lack them, using only values already present on body chunks of the same
``document_id``. This never invents a value, never overwrites a non-empty
field, and never touches chunk text or any other column.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Mapping, Sequence, Tuple

SUMMARY_FILE_TYPE = "document_summary"

SUMMARY_PROVENANCE_FLAG = "AIOS_RAG_V2_SUMMARY_PROVENANCE"
_SUMMARY_PROVENANCE_TRUE = frozenset({"1", "true", "yes", "on"})


def summary_provenance_enabled() -> bool:
    """Return whether summary provenance is opt-in for this process."""
    raw = str(os.environ.get(SUMMARY_PROVENANCE_FLAG, "") or "").strip().casefold()
    return raw in _SUMMARY_PROVENANCE_TRUE



def with_body_provenance(summary: Any, body_chunks: Sequence[Any]) -> Any:
    """Copy one agreed body fingerprint and privacy set onto a summary chunk.

    Never invents a value, never overwrites a non-empty field, and returns the
    input unchanged when the body offers no single answer. Used by the chunker
    at ingest time, so a freshly built summary already carries provenance.
    """
    from dataclasses import replace

    fingerprints = {
        chunk.source_fingerprint
        for chunk in body_chunks
        if chunk.file_type != SUMMARY_FILE_TYPE and chunk.source_fingerprint
    }
    privacies = {
        tuple(chunk.privacy_labels)
        for chunk in body_chunks
        if chunk.file_type != SUMMARY_FILE_TYPE and chunk.privacy_labels
    }
    fingerprint = summary.source_fingerprint
    privacy = tuple(summary.privacy_labels)
    if not fingerprint and len(fingerprints) == 1:
        fingerprint = next(iter(fingerprints))
    if not privacy and len(privacies) == 1:
        privacy = next(iter(privacies))
    return replace(summary, source_fingerprint=fingerprint, privacy_labels=privacy)


@dataclass(frozen=True)
class SummaryProvenancePlan:
    """A deterministic, inspectable proposal for one index file."""

    summary_count: int
    updates: Tuple[Tuple[str, str, str], ...] = ()
    skipped_ambiguous: Tuple[Tuple[str, str, str], ...] = ()
    skipped_no_body_value: Tuple[str, ...] = ()

    @property
    def update_count(self) -> int:
        return len(self.updates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_count": self.summary_count,
            "update_count": self.update_count,
            "skipped_ambiguous_count": len(self.skipped_ambiguous),
            "skipped_no_body_value_count": len(self.skipped_no_body_value),
            "updates": [
                {"chunk_id": chunk_id, "field": name, "value": value}
                for chunk_id, name, value in self.updates
            ],
            "skipped_ambiguous": [
                {"chunk_id": chunk_id, "field": name, "reason": reason}
                for chunk_id, name, reason in self.skipped_ambiguous
            ],
            "skipped_no_body_value": list(self.skipped_no_body_value),
        }


def _body_provenance(
    conn: sqlite3.Connection,
    document_id: str,
) -> Tuple[set[str], set[str]]:
    """Return distinct non-empty body fingerprints and privacy label sets."""
    fingerprints: set[str] = set()
    privacies: set[str] = set()
    rows = conn.execute(
        """
        SELECT source_fingerprint, privacy_labels_json
        FROM chunks
        WHERE document_id = ? AND file_type != ?
        """,
        (document_id, SUMMARY_FILE_TYPE),
    ).fetchall()
    for fingerprint, privacy_json in rows:
        text = str(fingerprint or "").strip()
        if text:
            fingerprints.add(text)
        for label in _labels(privacy_json):
            privacies.add(label)
    return fingerprints, privacies


def _labels(raw: Any) -> Tuple[str, ...]:
    if raw is None:
        return ()
    try:
        values = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return ()
    if not isinstance(values, (list, tuple)):
        return ()
    return tuple(str(item) for item in values if str(item))


def plan_summary_provenance(index_path: Path | str) -> SummaryProvenancePlan:
    """Build the dry-run plan. Reads only; writes nothing."""
    path = Path(index_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            """
            SELECT chunk_id, document_id, source_fingerprint, privacy_labels_json
            FROM chunks
            WHERE file_type = ?
            """,
            (SUMMARY_FILE_TYPE,),
        ).fetchall()
        updates: List[Tuple[str, str, str]] = []
        ambiguous: List[Tuple[str, str, str]] = []
        no_body: List[str] = []
        for chunk_id, document_id, fingerprint, privacy_json in rows:
            chunk_key = str(chunk_id)
            fingerprints, privacies = _body_provenance(conn, str(document_id))
            if not str(fingerprint or "").strip():
                if len(fingerprints) == 1:
                    updates.append((chunk_key, "source_fingerprint", next(iter(fingerprints))))
                elif len(fingerprints) > 1:
                    ambiguous.append((chunk_key, "source_fingerprint", "multiple_body_fingerprints"))
                else:
                    no_body.append(chunk_key)
            if not _labels(privacy_json):
                if len(privacies) == 1:
                    updates.append((chunk_key, "privacy_labels_json", json.dumps([next(iter(privacies))], ensure_ascii=False)))
                elif len(privacies) > 1:
                    ambiguous.append((chunk_key, "privacy_labels_json", "multiple_body_privacy_sets"))
                else:
                    no_body.append(chunk_key)
        return SummaryProvenancePlan(
            summary_count=len(rows),
            updates=tuple(updates),
            skipped_ambiguous=tuple(ambiguous),
            skipped_no_body_value=tuple(dict.fromkeys(no_body)),
        )
    finally:
        conn.close()


def apply_summary_provenance(index_path: Path | str, plan: SummaryProvenancePlan) -> int:
    """Apply a plan. Only empty fields are written. Returns rows changed.

    Refuses to write unless the opt-in flag is set, so the default behaviour of
    an unconfigured install is unchanged.
    """
    if not summary_provenance_enabled():
        raise RuntimeError("summary_provenance_disabled")
    if not plan.updates:
        return 0
    path = Path(index_path)
    conn = sqlite3.connect(str(path), timeout=30.0)
    try:
        with conn:
            changed = 0
            for chunk_id, name, value in plan.updates:
                cursor = conn.execute(
                    f"""
                    UPDATE chunks
                    SET {name} = ?
                    WHERE chunk_id = ?
                      AND file_type = ?
                      AND ({name} IS NULL OR {name} = '' OR {name} = '[]')
                    """,
                    (value, chunk_id, SUMMARY_FILE_TYPE),
                )
                changed += cursor.rowcount
            return changed
    finally:
        conn.close()
