"""Migrate stored dense+sparse vectors to the pinned ONNX fp32 fingerprint.

Dry-run by default. Writes only with ``--apply`` and an ONNX fp32 selection
(``BGE_BACKEND`` unset, ``auto`` or ``onnx``). The ``onnx_int8`` and PyTorch
overrides refuse writes. This script never changes its ONNX fp32 target.

Each ``--apply`` batch commits independently, so an interrupted run resumes by
skipping chunks that already carry the ONNX fingerprint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aios_habit.rag_v2.bge_onnx_backend import (  # noqa: E402
    BGE_BACKEND_FLAG,
    OnnxInt8BgeM3Backend,
    require_onnx_model_dir,
    resolve_bge_backend_name,
    resolve_onnx_checksum,
)
from aios_habit.rag_v2.semantic import normalize_sparse_vector, normalize_vector  # noqa: E402

BATCH_SIZE = 10
COLD_SECONDS_PER_CHUNK = 22.8
WARM_SECONDS_PER_CHUNK = 1.8
BGE_M3_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pack_vector(vector: object, dimension: int) -> bytes:
    normalized = normalize_vector(vector, dimension=dimension)
    return struct.pack(f"<{dimension}f", *normalized)


@dataclass(frozen=True)
class MigrationPlan:
    index: Path
    onnx_fingerprint: str
    pytorch_fingerprint: str
    pending: tuple[tuple[str, str], ...]
    retrievable_chunks: int
    already_onnx: int

    def to_dict(self) -> dict[str, object]:
        return {
            "index": str(self.index),
            "onnx_fingerprint": self.onnx_fingerprint,
            "pytorch_fingerprint": self.pytorch_fingerprint,
            "retrievable_chunks": self.retrievable_chunks,
            "already_onnx": self.already_onnx,
            "pending_chunks": len(self.pending),
        }


def _other_fingerprint(conn: sqlite3.Connection, fingerprint: str) -> str:
    rows = conn.execute(
        "SELECT DISTINCT model_fingerprint FROM chunk_embeddings "
        "WHERE model_fingerprint != ?",
        (fingerprint,),
    ).fetchall()
    if len(rows) != 1:
        return ""
    return str(rows[0][0])


def _backup_candidates(index_path: Path) -> list[Path]:
    parent = index_path.resolve().parent
    return sorted(
        parent.glob(f"{index_path.name}.bak-*"),
        key=lambda candidate: candidate.stat().st_mtime_ns,
    )


def _require_fresh_backup(index_path: Path) -> Path:
    """Refuse writes unless a sibling backup of this index exists and reads ok."""
    path = index_path.resolve()
    backups = [item for item in _backup_candidates(path) if item.is_file()]
    if not backups:
        raise SystemExit(
            f"refusing to migrate: no backup {path.name}.bak-* next to the index; "
            "copy the index and verify PRAGMA integrity_check first"
        )
    backup = backups[-1]
    conn = sqlite3.connect(f"file:{backup.as_posix()}?mode=ro", uri=True)
    try:
        status = conn.execute("PRAGMA integrity_check").fetchone()
    finally:
        conn.close()
    if not status or str(status[0]).casefold() != "ok":
        raise SystemExit(
            f"refusing to migrate: backup {backup.name} failed integrity_check"
        )
    return backup


def _require_onnx_backend_selected() -> None:
    if resolve_bge_backend_name() != "onnx":
        raise SystemExit(
            f"refusing to migrate: {BGE_BACKEND_FLAG} must select the ONNX fp32 "
            "runtime (unset, auto or onnx); onnx_int8 and pytorch are separate backends"
        )


def _open_backend() -> OnnxInt8BgeM3Backend:
    onnx_path = require_onnx_model_dir(backend_name="onnx")
    return OnnxInt8BgeM3Backend(
        model_path=onnx_path,
        backend_name="onnx",
        revision=BGE_M3_REVISION,
        artifact_checksum=resolve_onnx_checksum(onnx_path),
        batch_size=8,
    )


def plan_migration(index_path: Path | str) -> MigrationPlan:
    """List retrievable chunks missing ONNX dense vectors. Reads only."""
    path = Path(index_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    backend = _open_backend()
    fingerprint = backend.descriptor.fingerprint
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            """
            SELECT c.chunk_id, c.text, e.content_hash
            FROM chunks AS c
            LEFT JOIN chunk_embeddings AS e
              ON e.chunk_id = c.chunk_id AND e.model_fingerprint = ?
            WHERE c.retrievable = 1
            ORDER BY c.chunk_id
            """,
            (fingerprint,),
        ).fetchall()
        pending = tuple(
            (str(chunk_id), str(text))
            for chunk_id, text, content_hash in rows
            if content_hash != _content_hash(str(text))
        )
        retrievable = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE retrievable = 1"
        ).fetchone()[0]
        already = conn.execute(
            "SELECT COUNT(DISTINCT chunk_id) FROM chunk_embeddings "
            "WHERE model_fingerprint = ?",
            (fingerprint,),
        ).fetchone()[0]
        return MigrationPlan(
            index=path.resolve(),
            onnx_fingerprint=fingerprint,
            pytorch_fingerprint=_other_fingerprint(conn, fingerprint),
            pending=pending,
            retrievable_chunks=int(retrievable),
            already_onnx=int(already),
        )
    finally:
        conn.close()


def _row_needs_migration(
    conn: sqlite3.Connection, chunk_id: str, text: str, fingerprint: str
) -> bool:
    row = conn.execute(
        "SELECT content_hash FROM chunk_embeddings "
        "WHERE chunk_id = ? AND model_fingerprint = ?",
        (chunk_id, fingerprint),
    ).fetchone()
    if row is None:
        return True
    return row[0] != _content_hash(text)


def apply_migration(
    index_path: Path | str,
    plan: MigrationPlan,
    *,
    batch_size: int = BATCH_SIZE,
) -> int:
    """Embed pending chunks with ONNX and upsert dense+sparse rows per batch."""
    _require_onnx_backend_selected()
    path = Path(index_path)
    backup = _require_fresh_backup(path)
    print(f"backup: {backup.name} (integrity ok)")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    backend = _open_backend()
    if backend.descriptor.fingerprint != plan.onnx_fingerprint:
        raise ValueError("plan fingerprint does not match the pinned ONNX model")
    backend.sparse_capability.require()
    total = 0
    remaining = list(plan.pending)
    batch_no = 0
    while remaining:
        batch_no += 1
        batch, remaining = remaining[:batch_size], remaining[batch_size:]
        # Resume: skip chunks another run already migrated.
        conn = sqlite3.connect(str(path), timeout=30.0)
        try:
            todo = [
                (chunk_id, text)
                for chunk_id, text in batch
                if _row_needs_migration(
                    conn, chunk_id, text, plan.onnx_fingerprint
                )
            ]
        finally:
            conn.close()
        if not todo:
            print(f"batch {batch_no}: 0 pending (already migrated), skipping")
            continue
        started = time.perf_counter()
        dense = backend.embed_documents(tuple(text for _, text in todo))
        sparse = backend.sparse_documents(tuple(text for _, text in todo))
        if len(dense) != len(todo) or len(sparse) != len(todo):
            raise RuntimeError(
                f"embedding count mismatch: expected {len(todo)}, "
                f"received {len(dense)}/{len(sparse)}"
            )
        _upsert_batch(path, plan.onnx_fingerprint, backend, todo, dense, sparse)
        total += len(todo)
        elapsed = time.perf_counter() - started
        done = total + (len(plan.pending) - len(remaining) - len(todo))
        print(
            f"batch {batch_no}: migrated {len(todo)} chunks in {elapsed:.1f}s "
            f"(total {total}/{len(plan.pending)}, skipped {done - total} resumed)"
        )
    return total


def _upsert_batch(
    path: Path,
    fingerprint: str,
    backend: OnnxInt8BgeM3Backend,
    todo: list[tuple[str, str]],
    dense: object,
    sparse: object,
) -> None:
    from datetime import datetime, timezone

    descriptor = backend.descriptor
    created_at = datetime.now(timezone.utc).isoformat()
    dense_rows = []
    sparse_rows = []
    for (chunk_id, text), vector, sparse_vector in zip(todo, dense, sparse):
        dense_rows.append((
            chunk_id,
            fingerprint,
            _content_hash(text),
            descriptor.model_id,
            descriptor.revision,
            descriptor.runtime,
            descriptor.runtime_version,
            descriptor.dimension,
            "float32-le",
            int(descriptor.normalized),
            _pack_vector(vector, descriptor.dimension),
            created_at,
        ))
        sparse_rows.append((
            chunk_id,
            fingerprint,
            _content_hash(text),
            json.dumps(
                normalize_sparse_vector(sparse_vector),
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ),
            created_at,
        ))
    conn = sqlite3.connect(str(path), timeout=30.0)
    try:
        with conn:
            conn.executemany(
                """
                INSERT INTO chunk_embeddings (
                    chunk_id, model_fingerprint, content_hash, model_id,
                    model_revision, runtime, runtime_version, dimension, dtype,
                    normalized, vector_blob, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                    content_hash=excluded.content_hash,
                    model_id=excluded.model_id,
                    model_revision=excluded.model_revision,
                    runtime=excluded.runtime,
                    runtime_version=excluded.runtime_version,
                    dimension=excluded.dimension,
                    dtype=excluded.dtype,
                    normalized=excluded.normalized,
                    vector_blob=excluded.vector_blob,
                    created_at=excluded.created_at
                """,
                dense_rows,
            )
            conn.executemany(
                """
                INSERT INTO chunk_sparse_embeddings (
                    chunk_id, model_fingerprint, content_hash, sparse_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, model_fingerprint) DO UPDATE SET
                    content_hash=excluded.content_hash,
                    sparse_json=excluded.sparse_json,
                    created_at=excluded.created_at
                """,
                sparse_rows,
            )
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path, help="Path to a RAG v2 chunks sqlite file")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Migrate pending vectors. Without this flag nothing is written.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE, help="Chunks per commit"
    )
    parser.add_argument("--json", action="store_true", help="Print the plan as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.apply:
        _require_onnx_backend_selected()
        _require_fresh_backup(Path(args.index))
    plan = plan_migration(args.index)
    payload = plan.to_dict()
    cold_s = len(plan.pending) * COLD_SECONDS_PER_CHUNK
    warm_s = len(plan.pending) * WARM_SECONDS_PER_CHUNK
    payload["estimate_cold_s"] = round(cold_s, 1)
    payload["estimate_warm_s"] = round(warm_s, 1)
    if args.json:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    else:
        print(f"index: {plan.index}")
        print(f"index_bytes: {plan.index.stat().st_size}")
        print(f"onnx_fingerprint: {plan.onnx_fingerprint}")
        print(f"pytorch_fingerprint: {plan.pytorch_fingerprint or '(none/ambiguous)'}")
        print(f"retrievable_chunks: {plan.retrievable_chunks}")
        print(f"already_onnx: {plan.already_onnx}")
        print(f"pending_chunks: {len(plan.pending)}")
        print(
            f"estimate: cold ~{cold_s / 3600:.2f}h "
            f"({COLD_SECONDS_PER_CHUNK}s/chunk x {len(plan.pending)}), "
            f"warm ~{warm_s / 60:.1f}min "
            f"({WARM_SECONDS_PER_CHUNK}s/chunk x {len(plan.pending)})"
        )
    if not args.apply:
        print("dry_run: no changes written")
        return 0
    migrated = apply_migration(args.index, plan, batch_size=args.batch_size)
    print(f"applied_chunks_migrated: {migrated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
