import json
import sqlite3
import struct
from pathlib import Path

import pytest

from aios_habit.split_index_by_domain import main as split_main

DOCS = [
    # (document_id, source_name, source_path, text, expected_domain)
    (
        "d-lsu",
        "LSU_log_jig.xlsx",
        "C:/Drive/LSU/LSU_log_jig.xlsx",
        "SelNo bowskew NG tai tram fin test, log jig laser scan unit",
        "lsu",
    ),
    (
        "d-dtl",
        "Bang ma loi KDTPS.xlsx",
        "C:/Drive/Dieu-tra-loi/Bang ma loi.xlsx",
        "F123 hien tuong ket giay, nguyen nhan sensor ban, doi sach ve sinh",
        "dieu_tra_loi",
    ),
    (
        "d-mom",
        "MOM_AGV_spec.pdf",
        "C:/Drive/MOM/MOM_AGV_spec.pdf",
        "AGV通信仕様 staging oricon xuat kho WMS MOM Opcenter",
        "mom",
    ),
    (
        "d-amb",
        "notes.txt",
        "C:/misc/notes.txt",
        "ghi chu linh tinh khong ro linh vuc nao",
        "dieu_tra_loi",  # documented transparent fallback
    ),
]


def _build_fixture_db(path: Path, *, with_fts: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
            source_path TEXT NOT NULL, source_name TEXT NOT NULL,
            file_type TEXT NOT NULL, text TEXT NOT NULL,
            normalized_text TEXT NOT NULL, metadata_json TEXT NOT NULL,
            privacy_labels_json TEXT NOT NULL, source_fingerprint TEXT,
            checksum TEXT,
            retrievable INTEGER NOT NULL DEFAULT 1 CHECK (retrievable IN (0, 1))
        );
        CREATE TABLE chunk_embeddings (
            chunk_id TEXT NOT NULL, model_fingerprint TEXT NOT NULL,
            content_hash TEXT NOT NULL, model_id TEXT NOT NULL,
            model_revision TEXT NOT NULL, runtime TEXT NOT NULL,
            runtime_version TEXT NOT NULL, dimension INTEGER NOT NULL,
            dtype TEXT NOT NULL, normalized INTEGER NOT NULL,
            vector_blob BLOB NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY (chunk_id, model_fingerprint));
        CREATE TABLE chunk_sparse_embeddings (
            chunk_id TEXT NOT NULL, model_fingerprint TEXT NOT NULL,
            content_hash TEXT NOT NULL, sparse_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (chunk_id, model_fingerprint));
        """
    )
    if with_fts:
        conn.executescript(
            """
            CREATE VIRTUAL TABLE chunks_fts USING fts5(
                chunk_id UNINDEXED, normalized_text, source_name,
                source_path, metadata_json, tokenize='unicode61');
            CREATE TRIGGER chunks_fts_insert AFTER INSERT ON chunks
            WHEN new.retrievable = 1 BEGIN
                INSERT INTO chunks_fts(chunk_id, normalized_text, source_name,
                    source_path, metadata_json)
                VALUES (new.chunk_id, new.normalized_text, new.source_name,
                    new.source_path, new.metadata_json);
            END;
            """
        )
    blob = struct.pack("4f", 0.1, 0.2, 0.3, 0.4)
    for doc_id, name, spath, text, _domain in DOCS:
        for i in range(3):
            cid = "%s-c%d" % (doc_id, i)
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
                (cid, doc_id, spath, name, "txt", text, text.lower(), "{}", "[]", "fp", "ck"),
            )
            conn.execute(
                "INSERT INTO chunk_embeddings VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, "016c5255", "h", "bge-m3", "rev", "cpu", "1.28", 4, "float32-le", 1, blob, "t"),
            )
            conn.execute(
                "INSERT INTO chunk_sparse_embeddings VALUES (?,?,?,?,?)",
                (cid, "016c5255", "h", '{"tok": 1}', "t"),
            )
    conn.commit()
    conn.close()


def _split_args(source: Path, out: Path, extra=()):
    return ["--source", str(source), "--out", str(out), *extra]


def test_dry_run_writes_nothing(tmp_path):
    source = tmp_path / "lib" / "library.sqlite"
    out = tmp_path / "out"
    _build_fixture_db(source)
    assert split_main(_split_args(source, out, ("--dry-run",))) == 0
    assert not out.exists()


def test_split_counts_disjointness_vectors_and_manifest(tmp_path):
    source = tmp_path / "lib" / "library.sqlite"
    out = tmp_path / "out"
    _build_fixture_db(source)
    assert split_main(_split_args(source, out)) == 0

    manifest_path = out / "domain_manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["overall"] == "DAT"

    # Every document classified into exactly one expected domain.
    for doc_id, _name, _path, _text, expected in DOCS:
        assert manifest["documents"][doc_id]["domain"] == expected

    # Chunk totals preserved, documents disjoint across the three blocks.
    total = sum(manifest["domains"][d]["chunks"] for d in ("lsu", "dieu_tra_loi", "mom"))
    assert total == 12
    seen: set[str] = set()
    for domain in ("lsu", "dieu_tra_loi", "mom"):
        conn = sqlite3.connect(str(out / domain / "library.sqlite"))
        try:
            doc_ids = {r[0] for r in conn.execute("SELECT DISTINCT document_id FROM chunks")}
            assert not (seen & doc_ids), "document appears in two blocks"
            seen |= doc_ids
            # Every chunk kept its dense + sparse vector rows.
            for (cid,) in conn.execute("SELECT chunk_id FROM chunks"):
                dense = conn.execute(
                    "SELECT COUNT(*) FROM chunk_embeddings WHERE chunk_id = ?", (cid,)
                ).fetchone()[0]
                sparse = conn.execute(
                    "SELECT COUNT(*) FROM chunk_sparse_embeddings WHERE chunk_id = ?", (cid,)
                ).fetchone()[0]
                assert dense >= 1 and sparse >= 1
            # FTS index rebuilt by triggers.
            fts = conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            assert fts == chunks
        finally:
            conn.close()
    assert manifest["verification"]["cross_domain"]["ok"] is True


def test_split_refuses_production_without_flag(tmp_path):
    source = tmp_path / "workspace_chat_rag_v2_production" / "library.sqlite"
    _build_fixture_db(source)
    out = tmp_path / "out"
    assert split_main(_split_args(source, out)) == 2
    assert not out.exists()


def test_split_refuses_existing_target_without_overwrite(tmp_path):
    source = tmp_path / "lib" / "library.sqlite"
    out = tmp_path / "out"
    _build_fixture_db(source)
    assert split_main(_split_args(source, out)) == 0
    # Second run without --overwrite must refuse, not silently merge.
    assert split_main(_split_args(source, out)) == 2


def test_low_confidence_documents_listed_in_manifest(tmp_path):
    source = tmp_path / "lib" / "library.sqlite"
    out = tmp_path / "out"
    _build_fixture_db(source)
    assert split_main(_split_args(source, out)) == 0
    manifest = json.loads((out / "domain_manifest.json").read_text(encoding="utf-8"))
    assert manifest["documents"]["d-amb"]["confidence"] == 0.0


# --- Phase A2: centroid fallback + dry-run guard ---


def _build_centroid_fixture_db(path: Path) -> None:
    """Docs with known vector clusters: one trusted doc per domain plus one
    opaque-named doc whose vectors sit near the LSU cluster."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE chunks (
            chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
            source_path TEXT NOT NULL, source_name TEXT NOT NULL,
            file_type TEXT NOT NULL, text TEXT NOT NULL,
            normalized_text TEXT NOT NULL, metadata_json TEXT NOT NULL,
            privacy_labels_json TEXT NOT NULL, source_fingerprint TEXT,
            checksum TEXT,
            retrievable INTEGER NOT NULL DEFAULT 1 CHECK (retrievable IN (0, 1))
        );
        CREATE TABLE chunk_embeddings (
            chunk_id TEXT NOT NULL, model_fingerprint TEXT NOT NULL,
            content_hash TEXT NOT NULL, model_id TEXT NOT NULL,
            model_revision TEXT NOT NULL, runtime TEXT NOT NULL,
            runtime_version TEXT NOT NULL, dimension INTEGER NOT NULL,
            dtype TEXT NOT NULL, normalized INTEGER NOT NULL,
            vector_blob BLOB NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY (chunk_id, model_fingerprint));
        """
    )
    docs = [
        ("d-lsu", "LSU_log_jig.xlsx", "SelNo bowskew log jig", (1.0, 0.0, 0.0, 0.0)),
        (
            "d-dtl",
            "Bang ma loi KDTPS.xlsx",
            "F123 hien tuong nguyen nhan doi sach",
            (0.0, 1.0, 0.0, 0.0),
        ),
        ("d-mom", "MOM_AGV_spec.pdf", "AGV WMS MOM Opcenter", (0.0, 0.0, 1.0, 0.0)),
        ("d-opaque", "wsc-zzz000.txt", "ghi chu linh tinh khong ro", (0.9, 0.1, 0.0, 0.05)),
    ]
    for doc_id, name, text, vec in docs:
        for i in range(2):
            cid = "%s-c%d" % (doc_id, i)
            conn.execute(
                "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,1)",
                (cid, doc_id, "/x/" + name, name, "txt", text, text.lower(), "{}", "[]", "fp", "ck"),
            )
            conn.execute(
                "INSERT INTO chunk_embeddings VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    cid, "016c5255", "h", "bge-m3", "rev", "cpu", "1.28",
                    4, "float32-le", 1, struct.pack("4f", *vec), "t",
                ),
            )
    conn.commit()
    conn.close()


def test_centroid_fallback_reassigns_opaque_document(tmp_path):
    from aios_habit.split_index_by_domain import (
        _open_read_only,
        apply_centroid_fallback,
        classify_all,
    )

    source = tmp_path / "lib" / "library.sqlite"
    _build_centroid_fixture_db(source)
    conn = _open_read_only(source)
    try:
        manifest = classify_all(conn, ledger_db=None, sample_chunks=3, sample_chars=6000)
    finally:
        conn.close()
    assert manifest["d-opaque"]["confidence"] == 0.0

    conn = _open_read_only(source)
    try:
        manifest = apply_centroid_fallback(conn, manifest)
    finally:
        conn.close()

    entry = manifest["d-opaque"]
    assert entry["domain"] == "lsu"
    assert entry["confidence"] >= 0.4
    assert "centroid" in entry["reason"]
    # Trusted keyword classifications are untouched.
    assert manifest["d-lsu"]["domain"] == "lsu"
    assert manifest["d-dtl"]["domain"] == "dieu_tra_loi"
    assert manifest["d-mom"]["domain"] == "mom"


def test_centroid_fallback_skips_without_embedding_table(tmp_path):
    from aios_habit.split_index_by_domain import (
        _open_read_only,
        apply_centroid_fallback,
        classify_all,
    )

    source = tmp_path / "lib" / "library.sqlite"
    source.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(source))
    conn.execute(
        "CREATE TABLE chunks (chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL,"
        " source_path TEXT NOT NULL, source_name TEXT NOT NULL, text TEXT NOT NULL)"
    )
    conn.execute(
        "INSERT INTO chunks VALUES ('c1', 'd1', '/x/notes.txt', 'notes.txt', 'ghi chu')"
    )
    conn.commit()
    conn.close()

    conn = _open_read_only(source)
    try:
        manifest = classify_all(conn, ledger_db=None, sample_chunks=3, sample_chars=6000)
        manifest = apply_centroid_fallback(conn, manifest)
    finally:
        conn.close()
    assert manifest["d1"]["confidence"] == 0.0  # unchanged, no vector store


def test_dry_run_on_production_path_needs_no_flag(tmp_path):
    source = tmp_path / "workspace_chat_rag_v2_production" / "library.sqlite"
    _build_fixture_db(source)
    out = tmp_path / "out"
    assert split_main(_split_args(source, out, ("--dry-run",))) == 0
    assert not out.exists()
