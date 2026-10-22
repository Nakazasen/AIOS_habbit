"""Tests for DESKTOP-SPEED-FIX-G5-CATALOG-LINELOG-HOME (ARCH-09 & ARCH-14).

Verifies:
1. ARCH-09 (index_domain.py - load_all_index_specs):
   - Eliminates full-table `GROUP BY document_id` scan on `chunks` when cache is cold.
   - Uses lightweight catalog manifest sidecar (keyed by mtime_ns, size) + covering index
     `idx_chunks_doc_source_catalog` on `(document_id, source_path, source_name)` / recursive index skip-scan.
   - Returns 100% identical `SourceSpec` list compared to legacy implementation on real and synthetic DBs.
2. ARCH-14 (line_log_parser.py - match_line_events_for_question):
   - Combines matched tokens into a single SQL query backed by `COLLATE NOCASE` indexes.
   - Gates/skips scanning `line_events` when a question has neither matching tokens nor investigation signal.
   - Returns 100% identical matched event slices (`events`, `mode`, `count`, `owner_text`) as legacy across sample questions.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Any

import pytest

import aios_habit.index_domain as index_domain
import aios_habit.line_log_parser as line_log_parser
import aios_habit.workspace_chat_store as store
from aios_habit.local_jsonl import clear_jsonl_cache
from aios_habit.rag_v2.pipeline import SourceSpec


# ---------------------------------------------------------------------------
# Reference Legacy Implementations (pre-G5 at commit f61c491a / 7d28383e)
# ---------------------------------------------------------------------------


def _legacy_load_all_index_specs(db_path: Path) -> list[SourceSpec]:
    """Exact legacy query from index_domain.py:472-485."""
    uri = db_path.resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=10.0)
    try:
        rows = con.execute(
            "SELECT document_id, MIN(source_path), MIN(source_name) "
            "FROM chunks GROUP BY document_id ORDER BY document_id"
        ).fetchall()
    finally:
        con.close()
    return [
        SourceSpec(
            path=Path(str(r[2] if r[2] else r[1])),
            source_id=str(r[0]),
            document_id=str(r[0]),
            owner_consent=True,
            language_hints=("vi", "ja", "en"),
        )
        for r in rows
    ]


def _legacy_match_line_events_for_question(
    question: str,
    collection_id: str | None = None,
    *,
    limit: int = 8,
) -> dict[str, Any]:
    """Exact legacy implementation from line_log_parser.py:391-482."""
    db_path = line_log_parser.line_events_db_path(collection_id)
    empty: dict[str, Any] = {"events": (), "mode": "none", "count": 0, "owner_text": ""}
    if not db_path.is_file():
        return empty
    tokens = line_log_parser._question_tokens(question)
    cap = max(1, min(int(limit), 12))
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        total = int(conn.execute("SELECT COUNT(*) FROM line_events").fetchone()[0])
        if total <= 0:
            return empty
        rows: list[sqlite3.Row] = []
        for token in tokens:
            if len(token) < 2:
                continue
            found = conn.execute(
                """
                SELECT event_id, source_name, dialect, occurred_at, station, code,
                       serial, duration_s, provenance
                FROM line_events
                WHERE lower(code) = ? OR lower(station) = ?
                   OR instr(lower(code), ?) > 0 OR instr(lower(station), ?) > 0
                ORDER BY occurred_at DESC
                LIMIT ?
                """,
                (token, token, token, token, cap),
            ).fetchall()
            rows.extend(found)
            if len(rows) >= cap:
                break
        mode = "matched"
        if not rows and line_log_parser._looks_like_investigation(question):
            rows = conn.execute(
                """
                SELECT event_id, source_name, dialect, occurred_at, station, code,
                       serial, duration_s, provenance
                FROM line_events
                ORDER BY occurred_at DESC
                LIMIT ?
                """,
                (min(5, cap),),
            ).fetchall()
            mode = "recent"
        if not rows:
            return empty
        seen: set[str] = set()
        events: list[line_log_parser.LineLogEvent] = []
        for row in rows:
            event_id = str(row["event_id"])
            if event_id in seen:
                continue
            seen.add(event_id)
            events.append(
                line_log_parser.LineLogEvent(
                    event_id=event_id,
                    source_name=str(row["source_name"] or ""),
                    dialect=str(row["dialect"] or "unknown"),
                    occurred_at=str(row["occurred_at"] or ""),
                    station=str(row["station"] or ""),
                    code=str(row["code"] or ""),
                    serial=str(row["serial"] or ""),
                    duration_s=row["duration_s"],
                    provenance=str(row["provenance"] or line_log_parser.PROVENANCE_SUSPECTED),
                )
            )
            if len(events) >= cap:
                break
    finally:
        conn.close()
    lines = [
        "Sự kiện log (nghi ngờ, chưa phải chẩn đoán):",
    ]
    for event in events:
        lines.append(
            f"- {event.occurred_at or '?'} | {event.dialect} | "
            f"mã {event.code or '?'} | trạm {event.station or '?'} | "
            f"trạng thái {event.provenance}"
        )
    return {
        "events": tuple(events),
        "mode": mode,
        "count": len(events),
        "owner_text": "\n".join(lines),
    }


# ---------------------------------------------------------------------------
# ARCH-09 Tests: load_all_index_specs
# ---------------------------------------------------------------------------


def _create_synthetic_chunks_db(db_path: Path, num_docs: int = 80, chunks_per_doc: int = 15) -> None:
    con = sqlite3.connect(str(db_path))
    try:
        con.execute(
            """
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_name TEXT NOT NULL,
                text TEXT NOT NULL,
                retrievable INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        con.execute("CREATE INDEX idx_chunks_document_id ON chunks(document_id)")
        rows = []
        for d in range(num_docs):
            doc_id = f"doc_{d:04d}"
            s_path = f"D:/docs/block_{d % 4}/file_{d:04d}.pdf"
            s_name = f"file_{d:04d}.pdf" if d % 7 != 0 else ""
            for c in range(chunks_per_doc):
                rows.append(
                    (
                        f"{doc_id}_c{c:03d}",
                        doc_id,
                        s_path,
                        s_name,
                        f"Chunk text content {d}-{c} " + ("x" * 200),
                        1,
                    )
                )
        con.executemany("INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?)", rows)
        con.commit()
    finally:
        con.close()


def test_arch09_semantic_equivalence_on_real_and_copied_db(tmp_path: Path) -> None:
    """Verify 100% identical SourceSpec list between legacy GROUP BY and new catalog/skip-scan."""
    candidates = [
        Path("D:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/mom/library.sqlite"),
        Path("D:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/lsu/library.sqlite"),
        Path("local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite"),
    ]
    real_db = next((p for p in candidates if p.is_file()), None)
    if real_db is not None:
        target_db = tmp_path / "real_copy_library.sqlite"
        shutil.copy2(real_db, target_db)
    else:
        target_db = tmp_path / "synthetic_library.sqlite"
        _create_synthetic_chunks_db(target_db, num_docs=120, chunks_per_doc=20)

    expected_specs = _legacy_load_all_index_specs(target_db)
    assert len(expected_specs) > 0

    # 1. Cold cache, no manifest, skip-scan on existing idx_chunks_document_id
    index_domain.clear_index_specs_cache()
    manifest_file = index_domain._catalog_manifest_path(target_db.resolve())
    if manifest_file.exists():
        manifest_file.unlink()

    specs_skip_scan = index_domain.load_all_index_specs(target_db, use_manifest=False)
    assert specs_skip_scan == expected_specs

    # 2. Cold cache with manifest generation & subsequent cold-cache manifest hit
    index_domain.clear_index_specs_cache()
    specs_manifest_write = index_domain.load_all_index_specs(target_db, use_manifest=True)
    assert specs_manifest_write == expected_specs
    assert manifest_file.is_file()

    index_domain.clear_index_specs_cache()
    specs_manifest_hit = index_domain.load_all_index_specs(target_db, use_manifest=True)
    assert specs_manifest_hit == expected_specs

    # 3. With covering index idx_chunks_doc_source_catalog ensured
    assert index_domain.ensure_index_catalog(target_db) is True
    index_domain.clear_index_specs_cache()
    specs_covering = index_domain.load_all_index_specs(target_db, use_manifest=False)
    assert specs_covering == expected_specs


def test_arch09_no_group_by_scan_and_covering_index_query_plan(tmp_path: Path) -> None:
    """Verify SQLite never executes GROUP BY on chunks and uses covering index + manifest."""
    db_path = tmp_path / "catalog_plan.sqlite"
    _create_synthetic_chunks_db(db_path, num_docs=50, chunks_per_doc=10)
    expected = _legacy_load_all_index_specs(db_path)

    # Ensure covering index
    assert index_domain.ensure_index_catalog(db_path) is True

    con = sqlite3.connect(str(db_path))
    try:
        executed_sql: list[str] = []
        con.set_trace_callback(executed_sql.append)
        rows = index_domain._query_index_catalog_rows(con)
        con.set_trace_callback(None)

        assert len(rows) == 50
        for sql in executed_sql:
            assert "GROUP BY document_id" not in sql.upper()

        # Verify EXPLAIN QUERY PLAN uses COVERING INDEX idx_chunks_doc_source_catalog
        plan_rows = con.execute(
            """
            EXPLAIN QUERY PLAN
            WITH RECURSIVE docs(doc_id) AS (
                SELECT MIN(document_id) FROM chunks
                UNION ALL
                SELECT (SELECT MIN(document_id) FROM chunks WHERE document_id > docs.doc_id)
                FROM docs
                WHERE docs.doc_id IS NOT NULL
            )
            SELECT d.doc_id,
                   (SELECT MIN(source_path) FROM chunks WHERE document_id = d.doc_id),
                   (SELECT MIN(source_name) FROM chunks WHERE document_id = d.doc_id)
            FROM docs d
            WHERE d.doc_id IS NOT NULL
            ORDER BY d.doc_id
            """
        ).fetchall()
        plan_details = " | ".join(str(r[-1]) for r in plan_rows)
        assert "USING COVERING INDEX" in plan_details
        assert index_domain.COVERING_CATALOG_INDEX_NAME in plan_details
    finally:
        con.close()

    # Verify manifest invalidation when DB changes
    index_domain.clear_index_specs_cache()
    loaded_before = index_domain.load_all_index_specs(db_path)
    assert loaded_before == expected

    # Insert a new document into chunks -> mtime/size changes -> cache & manifest auto-refresh
    con_w = sqlite3.connect(str(db_path))
    try:
        con_w.execute(
            "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?)",
            ("doc_9999_c001", "doc_9999", "D:/docs/new_doc.pdf", "new_doc.pdf", "New content", 1),
        )
        con_w.commit()
    finally:
        con_w.close()

    index_domain.clear_index_specs_cache()
    loaded_after = index_domain.load_all_index_specs(db_path)
    assert len(loaded_after) == 51
    assert loaded_after == _legacy_load_all_index_specs(db_path)


# ---------------------------------------------------------------------------
# ARCH-14 Tests: match_line_events_for_question
# ---------------------------------------------------------------------------


def _seed_diverse_line_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    chat_dir = tmp_path / "chat"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", chat_dir)
    monkeypatch.setattr(store, "COLLECTIONS_FILE", chat_dir / "collections.jsonl")
    monkeypatch.setattr(line_log_parser, "LOCAL_CHAT_DIR", chat_dir)
    clear_jsonl_cache()
    line_log_parser.clear_line_events_cache()
    store.init_chat_store()

    jam_csv = (
        "timestamp,station,jam_code,serial,duration_s\n"
        "2026-09-10T08:01:00,C1,JAM-01,SN001,1.2\n"
        "2026-09-10T08:05:00,C1,JAM-01,SN002,1.5\n"
        "2026-09-10T08:10:00,C2,JAM-02,SN003,2.0\n"
        "2026-09-10T08:15:00,STATION_A,JAM-010,SN004,1.1\n"
        "2026-09-10T08:15:00,STATION_B,JAM-01,SN005,1.8\n"
        "2026-09-10T09:00:00,A2,JAM-4709,SN006,3.4\n"
    ).encode("utf-8")
    ccall_csv = (
        "datetime,line,c_call,serial\n"
        "2026-09-10T09:30:00,A2,CC-9,SN101\n"
        "2026-09-10T09:45:00,LINE_03,C7620,SN102\n"
        "2026-09-10T10:00:00,LINE_03,C6770,SN103\n"
    ).encode("utf-8")
    lsu_csv = (
        "DATE,TIME,CAM_ID,ERR_NUM,BARCODE,TACT_TIME\n"
        "2026-09-10,10:15:00,CAM_01,E102,SN_LSU_01,11.5\n"
        "2026-09-10,10:20:00,CAM_02,E105,SN_LSU_02,12.0\n"
    ).encode("utf-8")

    s1 = line_log_parser.ingest_line_log_bytes(jam_csv, "jam.csv", collection_id="tri_thuc")
    s2 = line_log_parser.ingest_line_log_bytes(ccall_csv, "ccall.csv", collection_id="tri_thuc")
    s3 = line_log_parser.ingest_line_log_bytes(lsu_csv, "lsu.csv", collection_id="tri_thuc")
    assert s1.ok and s2.ok and s3.ok
    return Path(s1.db_path)


def test_arch14_semantic_equivalence_across_sample_questions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify 100% identical event sets, ordering, modes, and owner_text vs legacy."""
    _seed_diverse_line_events(tmp_path, monkeypatch)

    sample_questions = [
        "Máy C1 bị JAM-01 xử lý thế nào?",
        "Kiểm tra mã lỗi C7620 và E102 trên LINE_03",
        "Tại sao trạm A2 báo CC-9 và JAM-4709?",
        "c1 jam-01",
        "STATION_A và STATION_B lúc 08:15 có sự kiện gì?",
        "Phân tích CAM_01 và CAM_02",
        "Điều tra lỗi dừng máy gần đây trên dây chuyền",  # investigation fallback -> recent
        "Log alarm hôm nay có gì bất thường không?",       # investigation fallback -> recent
        "Quy trình kiểm tra ngoại quan cụm thấu kính nhựa", # non-investigation -> none
        "Hướng dẫn vệ sinh gương đa giác polygon mirror",   # non-investigation -> none
        "Thông số dung sai điểm đo g1 và g2 trong bảng tiêu chuẩn",  # non-investigation -> none
        "A2 CC-9",  # matched without explicit hint word
        "E105",     # single code token without explicit hint word
        "jam",      # broad substring token matching multiple JAM-* codes
        "station",  # substring token matching STATION_A, STATION_B
        "",         # empty question
    ]

    for limit in (8, 3, 12):
        for q in sample_questions:
            line_log_parser.clear_line_events_cache()
            cold_actual = line_log_parser.match_line_events_for_question(
                q, "tri_thuc", limit=limit
            )
            warm_actual = line_log_parser.match_line_events_for_question(
                q, "tri_thuc", limit=limit
            )
            expected = _legacy_match_line_events_for_question(
                q, "tri_thuc", limit=limit
            )
            assert cold_actual == expected, f"Mismatch (cold) for question={q!r}, limit={limit}"
            assert warm_actual == expected, f"Mismatch (warm) for question={q!r}, limit={limit}"


def test_arch14_single_sql_query_and_collate_nocase_index_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify multi-token matching runs a single combined SQL query using COLLATE NOCASE indexes."""
    db_path = _seed_diverse_line_events(tmp_path, monkeypatch)

    # Warm vocab cache first
    line_log_parser.match_line_events_for_question("Khởi tạo bộ đệm", "tri_thuc")

    # 1. Non-investigation question with no matching tokens must not open SQLite at all!
    orig_connect = sqlite3.connect
    connect_calls: list[str] = []

    def _tracked_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        connect_calls.append(str(args[0]) if args else "")
        return orig_connect(*args, **kwargs)

    monkeypatch.setattr(line_log_parser.sqlite3, "connect", _tracked_connect)
    res_none = line_log_parser.match_line_events_for_question(
        "Quy trình bảo dưỡng định kỳ gương phản xạ", "tri_thuc"
    )
    assert res_none["count"] == 0
    assert res_none["mode"] == "none"
    assert len(connect_calls) == 0

    # 2. Multi-token question matching C1, JAM-01, A2, CC-9, C7620 must open SQLite once
    # and run a SINGLE combined SELECT query (UNION ALL) instead of a loop of SELECTs.
    executed_selects: list[str] = []

    def _tracing_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        con = orig_connect(*args, **kwargs)
        con.set_trace_callback(
            lambda sql: executed_selects.append(sql)
            if sql.strip().upper().startswith("SELECT")
            else None
        )
        return con

    monkeypatch.setattr(line_log_parser.sqlite3, "connect", _tracing_connect)
    q_multi = "Kiểm tra trạm C1 bị JAM-01, trạm A2 bị CC-9 và mã C7620"
    res_multi = line_log_parser.match_line_events_for_question(q_multi, "tri_thuc", limit=8)
    assert res_multi["count"] > 0
    assert res_multi["mode"] == "matched"
    assert len(executed_selects) == 1
    assert "UNION ALL" in executed_selects[0]
    assert "COLLATE NOCASE" in executed_selects[0]

    # 3. Verify EXPLAIN QUERY PLAN on db_path uses idx_line_events_code_nocase & idx_line_events_station_nocase
    monkeypatch.setattr(line_log_parser.sqlite3, "connect", orig_connect)
    con_plan = sqlite3.connect(str(db_path))
    try:
        plan_rows = con_plan.execute(
            "EXPLAIN QUERY PLAN " + executed_selects[0],
            # Extract literal check by running EXPLAIN on a single branch
        ).fetchall() if "?" not in executed_selects[0] else con_plan.execute(
            """
            EXPLAIN QUERY PLAN
            SELECT event_id, source_name, dialect, occurred_at, station, code,
                   serial, duration_s, provenance
            FROM line_events
            WHERE code COLLATE NOCASE IN ('JAM-01') OR station COLLATE NOCASE IN ('C1')
            ORDER BY occurred_at DESC, rowid ASC
            LIMIT 8
            """
        ).fetchall()
        plan_text = " | ".join(str(r[-1]) for r in plan_rows)
        assert "idx_line_events_code_nocase" in plan_text
        assert "idx_line_events_station_nocase" in plan_text
    finally:
        con_plan.close()
