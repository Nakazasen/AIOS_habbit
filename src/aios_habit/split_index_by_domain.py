"""Split one RAG ``library.sqlite`` into one collection per knowledge domain.

Reads the source database strictly read-only, classifies every document with
``aios_habit.index_domain.classify_document`` (each document lands in exactly
one domain, none are dropped), then copies the filtered tables into three new
collections::

    <out>/lsu/library.sqlite
    <out>/dieu_tra_loi/library.sqlite
    <out>/mom/library.sqlite

Chunk vectors are copied as-is (dense + sparse + multivector); nothing is
re-embedded. A ``domain_manifest.json`` records every document's domain,
confidence and reason, plus a self-verification report.

``--dry-run`` only prints the distribution and the low-confidence documents
without writing anything.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import sqlite3
import struct
import sys
from pathlib import Path

from aios_habit.index_domain import (
    CONFIDENCE_LOW_THRESHOLD,
    DOMAIN_DISPLAY,
    DOMAINS,
    classify_document,
    lookup_ledger_hint,
)

EMBEDDING_TABLES = (
    "chunk_embeddings",
    "chunk_sparse_embeddings",
    "chunk_multivector_embeddings",
)
LEDGER_TABLE = "source_preparation_ledger"
MANIFEST_NAME = "domain_manifest.json"
PRODUCTION_PATH_MARKER = "workspace_chat_rag_v2_production"


def _quote_identifier(name: str) -> str:
    return '"%s"' % name.replace('"', '""')


def _open_read_only(path: Path) -> sqlite3.Connection:
    uri = "file:%s?mode=ro" % path.as_posix()
    conn = sqlite3.connect(uri, uri=True, timeout=30.0)
    conn.execute("PRAGMA query_only=ON")
    return conn


def _load_documents(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT document_id, MIN(source_path) AS source_path,
               MIN(source_name) AS source_name, COUNT(*) AS chunk_count
        FROM chunks
        GROUP BY document_id
        ORDER BY document_id
        """
    ).fetchall()
    return [
        {
            "document_id": str(row[0]),
            "source_path": str(row[1] or ""),
            "source_name": str(row[2] or ""),
            "chunk_count": int(row[3] or 0),
        }
        for row in rows
    ]


def _text_sample(conn: sqlite3.Connection, document_id: str, max_chunks: int, max_chars: int) -> str:
    rows = conn.execute(
        "SELECT text FROM chunks WHERE document_id = ? ORDER BY rowid LIMIT ?",
        (document_id, max_chunks),
    ).fetchall()
    sample = "\n".join(str(row[0] or "") for row in rows)
    return sample[:max_chars]


def classify_all(
    conn: sqlite3.Connection,
    *,
    ledger_db: Path | None,
    sample_chunks: int,
    sample_chars: int,
) -> dict[str, dict]:
    """Return ``{document_id: manifest_entry}`` covering every document."""
    manifest: dict[str, dict] = {}
    for doc in _load_documents(conn):
        doc_id = doc["document_id"]
        hint = lookup_ledger_hint(ledger_db, doc_id) if ledger_db is not None else None
        sample = _text_sample(conn, doc_id, sample_chunks, sample_chars)
        result = classify_document(doc["source_name"], doc["source_path"], sample, ledger_hint=hint)
        manifest[doc_id] = {
            "domain": result.domain,
            "confidence": result.confidence,
            "reason": result.reason,
            "source_name": doc["source_name"],
            "source_path": doc["source_path"],
            "chunk_count": doc["chunk_count"],
        }
    return manifest


CENTROID_HIGH_THRESHOLD = 0.7
CENTROID_MAX_CHUNKS_PER_DOC = 50
CENTROID_MAX_CONFIDENCE = 0.85


def _decode_float32_le(blob: bytes, dimension: int) -> list[float] | None:
    """Decode one ``float32-le`` vector blob. Returns None on any mismatch."""
    if not isinstance(blob, (bytes, bytearray, memoryview)):
        return None
    raw = bytes(blob)
    if len(raw) != dimension * 4:
        return None
    try:
        return list(struct.unpack("<%df" % dimension, raw))
    except struct.error:
        return None


def _mean_vector(vecs: list[list[float]]) -> list[float] | None:
    if not vecs:
        return None
    dim = len(vecs[0])
    mean = [0.0] * dim
    for vec in vecs:
        if len(vec) != dim:
            continue
        for i, value in enumerate(vec):
            mean[i] += value
    count = len(vecs)
    mean = [value / count for value in mean]
    norm = math.sqrt(sum(value * value for value in mean))
    if norm <= 0:
        return None
    return [value / norm for value in mean]


def _cosine(a: list[float], b: list[float]) -> float:
    # Inputs are L2-normalized, so cosine == dot product.
    return sum(x * y for x, y in zip(a, b))


def _doc_centroid(
    conn: sqlite3.Connection,
    document_id: str,
    model_fingerprint: str,
    *,
    max_chunks: int,
) -> list[float] | None:
    """Mean of a document's dense chunk vectors (sampled, L2-normalized)."""
    rows = conn.execute(
        """
        SELECT vector_blob, dimension FROM chunk_embeddings
        WHERE model_fingerprint = ?
          AND dtype = 'float32-le'
          AND chunk_id IN (
              SELECT chunk_id FROM chunks WHERE document_id = ?
              ORDER BY rowid LIMIT ?
          )
        """,
        (model_fingerprint, document_id, max_chunks),
    ).fetchall()
    vecs: list[list[float]] = []
    for blob, dimension in rows:
        vec = _decode_float32_le(blob, int(dimension))
        if vec is None:
            continue
        norm = math.sqrt(sum(value * value for value in vec))
        if norm > 0:
            vecs.append([value / norm for value in vec])
    return _mean_vector(vecs)


def apply_centroid_fallback(
    conn: sqlite3.Connection,
    manifest: dict[str, dict],
    *,
    low_threshold: float = CONFIDENCE_LOW_THRESHOLD,
    high_threshold: float = CENTROID_HIGH_THRESHOLD,
    max_chunks_per_doc: int = CENTROID_MAX_CHUNKS_PER_DOC,
) -> dict[str, dict]:
    """Reassign low-confidence documents by nearest domain centroid.

    Uses the dense vectors already stored in ``chunk_embeddings`` -- nothing
    is re-embedded. Domain centroids are built from documents the keyword
    classifier already trusts (confidence >= ``high_threshold``). Each
    document below ``low_threshold`` is assigned the nearest centroid; its
    confidence is margin-based (best minus second-best cosine) and capped at
    :data:`CENTROID_MAX_CONFIDENCE` so vector assignments never outrank
    strong keyword evidence.

    Never raises for missing tables/columns or unusable vectors: without a
    usable vector store the manifest is returned unchanged.
    """
    try:
        tables = {
            str(row[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "chunk_embeddings" not in tables or "chunks" not in tables:
            return manifest
        columns = {
            str(row[1]) for row in conn.execute("PRAGMA table_info(chunk_embeddings)").fetchall()
        }
        if not {"chunk_id", "vector_blob", "dimension", "dtype", "model_fingerprint"} <= columns:
            return manifest
        fp_row = conn.execute(
            "SELECT model_fingerprint FROM chunk_embeddings "
            "GROUP BY model_fingerprint ORDER BY COUNT(*) DESC LIMIT 1"
        ).fetchone()
        if fp_row is None:
            return manifest
        fingerprint = str(fp_row[0])

        trusted: dict[str, list[str]] = {domain: [] for domain in DOMAINS}
        for doc_id, entry in manifest.items():
            if entry["confidence"] >= high_threshold:
                trusted[entry["domain"]].append(doc_id)
        if not all(trusted[domain] for domain in DOMAINS):
            return manifest

        centroids: dict[str, list[float]] = {}
        for domain in DOMAINS:
            vecs = [
                vec
                for doc_id in trusted[domain]
                if (vec := _doc_centroid(conn, doc_id, fingerprint, max_chunks=max_chunks_per_doc))
                is not None
            ]
            centroid = _mean_vector(vecs)
            if centroid is None:
                return manifest
            centroids[domain] = centroid

        for doc_id, entry in manifest.items():
            if entry["confidence"] >= low_threshold:
                continue
            vec = _doc_centroid(conn, doc_id, fingerprint, max_chunks=max_chunks_per_doc)
            if vec is None:
                continue
            sims = {domain: _cosine(vec, centroids[domain]) for domain in DOMAINS}
            ranked = sorted(DOMAINS, key=lambda d: sims[d], reverse=True)
            best, second = ranked[0], ranked[1]
            margin = sims[best] - sims[second]
            if margin <= 0:
                # No discriminative vector signal: keep the keyword result.
                continue
            confidence = round(min(CENTROID_MAX_CONFIDENCE, max(0.0, margin * 4.0)), 3)
            entry["domain"] = best
            entry["confidence"] = confidence
            entry["reason"] = (
                "%s | centroid vector: gần nhất %s (cos %.3f, chênh %.3f)"
                % (entry["reason"], DOMAIN_DISPLAY[best], sims[best], margin)
            )
    except sqlite3.Error:
        pass
    return manifest


def _table_columns(conn: sqlite3.Connection, table: str) -> dict[str, str]:
    return {
        str(row[1]): str(row[2] or "")
        for row in conn.execute("PRAGMA table_info(%s)" % _quote_identifier(table)).fetchall()
    }


def _copy_schema(source: sqlite3.Connection, target: sqlite3.Connection) -> list[str]:
    """Copy table/index/trigger definitions. Returns the created object names."""
    entries = source.execute(
        """
        SELECT type, name, tbl_name, sql FROM sqlite_master
        WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%%'
        ORDER BY CASE type WHEN 'table' THEN 0 WHEN 'index' THEN 1 ELSE 2 END, name
        """
    ).fetchall()
    created: list[str] = []
    virtual_tables: list[str] = []
    for obj_type, name, _tbl, sql in entries:
        name_s = str(name)
        # FTS5 shadow tables (chunks_fts_data, ...) are created implicitly with
        # the virtual table; creating them again only produces noise.
        if obj_type == "table" and any(
            name_s.startswith(vt + "_") for vt in virtual_tables
        ):
            continue
        try:
            target.execute(str(sql))
            created.append(name_s)
            if obj_type == "table" and "using fts5" in str(sql).lower():
                virtual_tables.append(name_s)
        except sqlite3.Error as exc:  # keep going; verify step will catch real damage
            print("  cảnh báo: không tạo được %s %s: %s" % (obj_type, name, exc), file=sys.stderr)
    return created


def _copy_domain_tables(
    target: sqlite3.Connection,
    source: sqlite3.Connection,
    domain_doc_ids: list[str],
) -> dict[str, int]:
    tables = {
        row[0]
        for row in source.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    }
    placeholders = ",".join("?" for _ in domain_doc_ids)
    copied: dict[str, int] = {}

    def _count(table: str) -> int:
        return int(target.execute("SELECT COUNT(*) FROM %s" % _quote_identifier(table)).fetchone()[0])

    # chunks first: AFTER INSERT triggers refill chunks_fts automatically.
    with target:
        target.execute(
            "INSERT INTO chunks SELECT * FROM srcdb.chunks WHERE document_id IN (%s)" % placeholders,
            domain_doc_ids,
        )
    copied["chunks"] = _count("chunks")

    for table in EMBEDDING_TABLES:
        if table not in tables:
            continue
        with target:
            target.execute(
                "INSERT INTO %s SELECT * FROM srcdb.%s "
                "WHERE chunk_id IN (SELECT chunk_id FROM chunks)"
                % (_quote_identifier(table), _quote_identifier(table))
            )
        copied[table] = _count(table)

    if LEDGER_TABLE in tables and "document_id" in _table_columns(source, LEDGER_TABLE):
        with target:
            target.execute(
                "INSERT INTO %s SELECT * FROM srcdb.%s WHERE document_id IN (%s)"
                % (_quote_identifier(LEDGER_TABLE), _quote_identifier(LEDGER_TABLE), placeholders),
                domain_doc_ids,
            )
        copied[LEDGER_TABLE] = _count(LEDGER_TABLE)
    return copied


def _verify_domain(
    target: sqlite3.Connection,
    source: sqlite3.Connection,
    domain: str,
    domain_doc_ids: set[str],
) -> dict:
    report: dict = {"domain": domain, "ok": True, "checks": {}}
    target_chunks = int(target.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
    target_docs = {
        str(row[0]) for row in target.execute("SELECT DISTINCT document_id FROM chunks").fetchall()
    }
    report["checks"]["documents_match"] = target_docs == domain_doc_ids
    report["chunks"] = target_chunks
    report["documents"] = len(target_docs)

    # No vector row may be lost: every chunk keeps at least as many dense /
    # sparse / multivector rows as it had in the source.
    chunk_ids = [str(row[0]) for row in target.execute("SELECT chunk_id FROM chunks").fetchall()]
    placeholders = ",".join("?" for _ in chunk_ids)
    lost: list[str] = []
    for table in EMBEDDING_TABLES:
        in_source = source.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        in_target = target.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not in_source or not in_target or not chunk_ids:
            continue
        quoted = _quote_identifier(table)
        src_counts = {
            str(row[0]): int(row[1])
            for row in source.execute(
                "SELECT chunk_id, COUNT(*) FROM %s WHERE chunk_id IN (%s) GROUP BY chunk_id"
                % (quoted, placeholders),
                chunk_ids,
            ).fetchall()
        }
        dst_counts = {
            str(row[0]): int(row[1])
            for row in target.execute(
                "SELECT chunk_id, COUNT(*) FROM %s WHERE chunk_id IN (%s) GROUP BY chunk_id"
                % (quoted, placeholders),
                chunk_ids,
            ).fetchall()
        }
        bad = [cid for cid in chunk_ids if dst_counts.get(cid, 0) < src_counts.get(cid, 0)]
        if bad:
            lost.append("%s: %d chunk mất vector (vd %s)" % (table, len(bad), bad[0]))
    report["checks"]["vectors_intact"] = not lost
    report["vector_loss"] = lost
    report["ok"] = bool(report["checks"]["documents_match"]) and not lost
    return report


def _print_distribution(manifest: dict[str, dict], low_threshold: float) -> None:
    by_domain: dict[str, list[dict]] = {d: [] for d in DOMAINS}
    for doc_id, entry in manifest.items():
        by_domain[entry["domain"]].append(entry)
    print("Phân bố tài liệu theo lĩnh vực:")
    print("  %-14s %8s %10s %12s" % ("lĩnh vực", "tài liệu", "chunk", "độ tin cậy TB"))
    for domain in DOMAINS:
        entries = by_domain[domain]
        chunks = sum(e["chunk_count"] for e in entries)
        avg_conf = sum(e["confidence"] for e in entries) / len(entries) if entries else 0.0
        print("  %-14s %8d %10d %12.3f" % (DOMAIN_DISPLAY[domain], len(entries), chunks, avg_conf))
    low = sorted(
        ((doc_id, e) for doc_id, e in manifest.items() if e["confidence"] < low_threshold),
        key=lambda item: item[1]["confidence"],
    )
    print("\nTài liệu độ tin cậy thấp (< %.2f): %d" % (low_threshold, len(low)))
    for doc_id, entry in low[:50]:
        print("  - %s | %s | %.3f | %s" % (doc_id, DOMAIN_DISPLAY[entry["domain"]], entry["confidence"], entry["source_name"]))
    if len(low) > 50:
        print("  ... và %d tài liệu nữa (xem manifest)" % (len(low) - 50))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tách library.sqlite thành 3 kho theo lĩnh vực (LSU / Điều tra lỗi / MOM).",
    )
    parser.add_argument("--source", required=True, help="Đường dẫn library.sqlite nguồn (chỉ đọc).")
    parser.add_argument("--out", required=True, help="Thư mục gốc chứa 3 kho mới.")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in phân bố, không ghi file.")
    parser.add_argument("--ledger-db", default=None, help="DB có bảng source_preparation_ledger (tùy chọn).")
    parser.add_argument("--sample-chunks", type=int, default=3, help="Số chunk đầu mỗi tài liệu dùng phân loại.")
    parser.add_argument("--sample-chars", type=int, default=6000, help="Số ký tự tối đa của mẫu văn bản.")
    parser.add_argument("--low-threshold", type=float, default=CONFIDENCE_LOW_THRESHOLD)
    parser.add_argument("--overwrite", action="store_true", help="Ghi đè kho đích đã tồn tại.")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Cho phép chạy khi --source trỏ vào kho production đang chạy.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = Path(args.source).expanduser()
    out_root = Path(args.out).expanduser()
    if not source.is_file():
        print("Lỗi: không tìm thấy file nguồn: %s" % source, file=sys.stderr)
        return 2

    source_conn = _open_read_only(source)
    try:
        integrity = source_conn.execute("PRAGMA integrity_check").fetchone()[0]
        if str(integrity).lower() != "ok":
            print("Lỗi: integrity_check nguồn không đạt: %s" % integrity, file=sys.stderr)
            return 1
        total_chunks = int(source_conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
        ledger_db = Path(args.ledger_db).expanduser() if args.ledger_db else None
        manifest_docs = classify_all(
            source_conn,
            ledger_db=ledger_db,
            sample_chunks=args.sample_chunks,
            sample_chars=args.sample_chars,
        )
        # Vector fallback: reassign keyword-missed documents by nearest
        # domain centroid (dense vectors already in the DB, no re-embedding).
        manifest_docs = apply_centroid_fallback(source_conn, manifest_docs)
    finally:
        source_conn.close()

    if args.dry_run:
        _print_distribution(manifest_docs, args.low_threshold)
        print("\nChế độ dry-run: không ghi file nào.")
        return 0

    # The production guard only gates real splits. A dry-run only reads, so it
    # must not require --allow-production.
    if PRODUCTION_PATH_MARKER in source.as_posix() and not args.allow_production:
        print(
            "Lỗi: --source trỏ vào kho production đang chạy. "
            "Thêm --allow-production nếu thật sự muốn tách trên kho này.",
            file=sys.stderr,
        )
        return 2

    by_domain: dict[str, list[str]] = {d: [] for d in DOMAINS}
    for doc_id, entry in manifest_docs.items():
        by_domain[entry["domain"]].append(doc_id)

    out_root.mkdir(parents=True, exist_ok=True)
    verification: dict[str, dict] = {}
    domain_stats: dict[str, dict] = {}
    skipped_tables: list[str] = []
    overall_ok = True

    src_probe = _open_read_only(source)
    try:
        source_tables = [
            str(row[0])
            for row in src_probe.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
    finally:
        src_probe.close()

    for domain in DOMAINS:
        doc_ids = sorted(by_domain[domain])
        target_dir = out_root / domain
        target_db = target_dir / "library.sqlite"
        if target_db.exists() and not args.overwrite:
            print("Lỗi: %s đã tồn tại. Dùng --overwrite để ghi đè." % target_db, file=sys.stderr)
            return 2
        target_dir.mkdir(parents=True, exist_ok=True)
        if target_db.exists():
            target_db.unlink()
        print("Đang tách kho %s: %d tài liệu..." % (DOMAIN_DISPLAY[domain], len(doc_ids)))

        target = sqlite3.connect(str(target_db), timeout=60.0)
        try:
            src = _open_read_only(source)
            try:
                _copy_schema(src, target)
                target.execute("ATTACH DATABASE 'file:%s?mode=ro' AS srcdb" % source.as_posix())
                copied = _copy_domain_tables(target, src, doc_ids)
                target.execute("DETACH DATABASE srcdb")
            finally:
                src.close()
            target.commit()
            verify_src = _open_read_only(source)
            try:
                report = _verify_domain(target, verify_src, domain, set(doc_ids))
            finally:
                verify_src.close()
        finally:
            target.close()

        verification[domain] = report
        copied_tables = set(copied) | {"chunks_fts"}
        if domain == DOMAINS[0]:
            fts_shadow = {t for t in source_tables if t.startswith("chunks_fts_")}
            skipped_tables = sorted(
                t
                for t in source_tables
                if t not in copied_tables and t not in fts_shadow
            )
        domain_stats[domain] = {
            "collection_dir": domain,
            "documents": report["documents"],
            "chunks": report["chunks"],
            "copied_tables": copied,
        }
        status = "ĐẠT" if report["ok"] else "CHƯA ĐẠT"
        print("  %s: %d tài liệu, %d chunk — tự kiểm: %s" % (DOMAIN_DISPLAY[domain], report["documents"], report["chunks"], status))
        overall_ok = overall_ok and report["ok"]

    # Cross-domain checks: chunk totals and document disjointness.
    chunk_sum = sum(domain_stats[d]["chunks"] for d in DOMAINS)
    doc_sets = [set(by_domain[d]) for d in DOMAINS]
    overlap = (doc_sets[0] & doc_sets[1]) | (doc_sets[0] & doc_sets[2]) | (doc_sets[1] & doc_sets[2])
    cross_ok = chunk_sum == total_chunks and not overlap and sum(len(s) for s in doc_sets) == len(manifest_docs)
    verification["cross_domain"] = {
        "ok": bool(cross_ok),
        "source_chunks": total_chunks,
        "split_chunks_sum": chunk_sum,
        "source_documents": len(manifest_docs),
        "overlapping_documents": sorted(overlap),
    }
    overall_ok = overall_ok and cross_ok

    manifest = {
        "generated_at": _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=7))).isoformat(),
        "tool": "aios_habit.split_index_by_domain (Phase A)",
        "source": {"path": str(source), "size_bytes": source.stat().st_size},
        "domains": domain_stats,
        "documents": manifest_docs,
        "verification": verification,
        "skipped_tables": skipped_tables,
        "overall": "DAT" if overall_ok else "CHUA_DAT",
    }
    manifest_path = out_root / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nĐã ghi manifest: %s" % manifest_path)
    print("Kết quả tổng: %s" % ("ĐẠT" if overall_ok else "CHƯA ĐẠT — xem verification trong manifest"))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
