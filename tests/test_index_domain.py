import os
import sqlite3

import pytest

from aios_habit.index_domain import (
    CONFIDENCE_LOW_THRESHOLD,
    DOMAIN_DIEU_TRA_LOI,
    DOMAIN_LSU,
    DOMAIN_MOM,
    DOMAINS,
    Classification,
    DomainRoute,
    detect_domain_from_question,
    classify_document,
    domain_routing_enabled,
    lookup_ledger_hint,
    select_domain_collection,
)


def test_taxonomy_has_exactly_three_domains():
    assert DOMAINS == (DOMAIN_LSU, DOMAIN_DIEU_TRA_LOI, DOMAIN_MOM)


def test_classify_lsu_document():
    result = classify_document(
        "LSU_log_jig.xlsx",
        "D:/Drive/LSU/LSU_log_jig.xlsx",
        "SelNo 1234 bowskew NG tai tram fin test, log jig ghi nhan loi laser scan unit",
    )
    assert isinstance(result, Classification)
    assert result.domain == DOMAIN_LSU
    assert result.confidence >= 0.5
    assert 0.0 <= result.confidence <= 1.0


def test_classify_dieu_tra_loi_document():
    result = classify_document(
        "Bang ma loi KDTPS.xlsx",
        "D:/Drive/Dieu-tra-loi/Bang ma loi KDTPS.xlsx",
        "F123 hien tuong: ket giay. Nguyen nhan: sensor ban. Doi sach: ve sinh sensor.",
    )
    assert result.domain == DOMAIN_DIEU_TRA_LOI
    assert result.confidence >= 0.5


def test_classify_mom_document():
    result = classify_document(
        "MOM_AGV_spec.pdf",
        "D:/Drive/MOM/MOM_AGV_spec.pdf",
        "AGV通信仕様 staging table oricon xuat kho, lien ket WMS va MOM Opcenter",
    )
    assert result.domain == DOMAIN_MOM
    assert result.confidence >= 0.5


def test_classify_ambiguous_falls_back_with_zero_confidence():
    result = classify_document("notes.txt", "/tmp/notes.txt", "ghi chu linh tinh khong ro linh vuc")
    assert result.domain == DOMAIN_DIEU_TRA_LOI  # documented fallback
    assert result.confidence == 0.0
    assert "minh bạch" in result.reason or "minh bach" in result.reason


def test_classify_every_document_lands_in_exactly_one_domain():
    samples = [
        ("a.xlsx", "/x/a.xlsx", ""),
        ("", "", ""),
        ("jig report.docx", "/d/jig report.docx", "lỗi ở trạm jig cần điều tra nguyên nhân"),
    ]
    for name, path, text in samples:
        result = classify_document(name, path, text)
        assert result.domain in DOMAINS
        assert 0.0 <= result.confidence <= 1.0


def test_classify_margin_reflects_contest():
    # Mixed signals: both LSU and investigation keywords; winner should not be overconfident.
    clear = classify_document("LSU.xlsx", "/LSU/LSU.xlsx", "jig selno bowskew fin test lsu log")
    mixed = classify_document(
        "jig_loi.docx", "/d/jig_loi.docx", "lỗi jig: hiện tượng kẹt, nguyên nhân sensor, đối sách vệ sinh"
    )
    assert clear.domain == DOMAIN_LSU
    assert mixed.confidence < clear.confidence


def test_detect_domain_from_question_each_domain():
    assert detect_domain_from_question("mã lỗi F123 nghĩa là gì, đối sách ra sao?").domain == DOMAIN_DIEU_TRA_LOI
    assert detect_domain_from_question("log jig báo bowskew ở trạm SelNo là sao?").domain == DOMAIN_LSU
    assert detect_domain_from_question("quy trình xuất kho trên MOM Opcenter thế nào?").domain == DOMAIN_MOM


def test_detect_domain_ambiguous_question_names_most_plausible_block():
    result = detect_domain_from_question("hôm nay ăn gì ngon?")
    assert result.domain in DOMAINS
    assert result.confidence < CONFIDENCE_LOW_THRESHOLD
    assert "không rõ lĩnh vực" in result.reason


def test_domain_routing_enabled_flag(monkeypatch):
    monkeypatch.delenv("AIOS_DOMAIN_ROUTING_ENABLED", raising=False)
    assert domain_routing_enabled() is False
    monkeypatch.setenv("AIOS_DOMAIN_ROUTING_ENABLED", "1")
    assert domain_routing_enabled() is True
    monkeypatch.setenv("AIOS_DOMAIN_ROUTING_ENABLED", "0")
    assert domain_routing_enabled() is False


def _route(monkeypatch, enabled, base, exists_map):
    monkeypatch.setenv("AIOS_DOMAIN_ROUTING_ENABLED", "1" if enabled else "0")
    detected = detect_domain_from_question("mã lỗi F123 đối sách?")
    return select_domain_collection(
        detected, base, collection_exists=lambda cid: exists_map.get(cid, False)
    )


def test_select_domain_applies_when_everything_ready(monkeypatch):
    route = _route(monkeypatch, True, "tri_thuc", {"dieu_tra_loi": True})
    assert isinstance(route, DomainRoute)
    assert route.applied is True
    assert route.collection_id == "dieu_tra_loi"


def test_select_domain_disabled_flag_keeps_base(monkeypatch):
    route = _route(monkeypatch, False, "tri_thuc", {"dieu_tra_loi": True})
    assert route.applied is False
    assert route.collection_id == "tri_thuc"


def test_select_domain_non_legacy_base_keeps_base(monkeypatch):
    route = _route(monkeypatch, True, "notebook_abc", {"dieu_tra_loi": True})
    assert route.applied is False
    assert route.collection_id == "notebook_abc"


def test_select_domain_missing_collection_falls_back(monkeypatch):
    route = _route(monkeypatch, True, "tri_thuc", {})
    assert route.applied is False
    assert route.collection_id == "tri_thuc"
    assert route.note


def _make_ledger_db(path, rows):
    conn = sqlite3.connect(str(path))
    conn.execute(
        """CREATE TABLE source_preparation_ledger (
            source_scope TEXT NOT NULL, source_id TEXT NOT NULL,
            source_fingerprint TEXT NOT NULL, model_id TEXT NOT NULL,
            model_revision TEXT NOT NULL, state TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT '', attempt_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT NOT NULL DEFAULT '', document_id TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL, updated_at REAL NOT NULL,
            PRIMARY KEY (source_scope, source_id))"""
    )
    for scope, sid, fp, doc in rows:
        conn.execute(
            "INSERT INTO source_preparation_ledger VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (scope, sid, fp, "m", "r", "ready", "", 0, "", doc, 0.0, 0.0),
        )
    conn.commit()
    conn.close()


def test_lookup_ledger_hint_found(tmp_path):
    db = tmp_path / "ledger.sqlite"
    _make_ledger_db(db, [("notebook", "LSU_jig_logs", "fp1", "doc-1")])
    hint = lookup_ledger_hint(db, "doc-1")
    assert hint == {"source_scope": "notebook", "source_id": "LSU_jig_logs", "source_fingerprint": "fp1"}


def test_lookup_ledger_hint_missing_row_returns_none(tmp_path):
    db = tmp_path / "ledger.sqlite"
    _make_ledger_db(db, [("notebook", "x", "fp", "doc-9")])
    assert lookup_ledger_hint(db, "doc-1") is None


def test_lookup_ledger_hint_missing_table_returns_none(tmp_path):
    db = tmp_path / "plain.sqlite"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE other (id TEXT)")
    conn.commit()
    conn.close()
    assert lookup_ledger_hint(db, "doc-1") is None


def test_lookup_ledger_hint_missing_db_returns_none(tmp_path):
    assert lookup_ledger_hint(tmp_path / "nope.sqlite", "doc-1") is None


def test_ledger_hint_enriches_reason(tmp_path):
    db = tmp_path / "ledger.sqlite"
    _make_ledger_db(db, [("notebook", "LSU_jig_logs", "fp1", "doc-1")])
    hint = lookup_ledger_hint(db, "doc-1")
    result = classify_document("a.bin", "/x/a.bin", "selno bowskew", ledger_hint=hint)
    assert result.domain == DOMAIN_LSU
    assert "LSU_jig_logs" in result.reason


def _make_chunk(source_name, source_path, text):
    from aios_habit.rag_v2 import DocumentElement, ElementType, ExtractionStatus
    from aios_habit.rag_v2.chunking import StructureAwareChunker

    element = DocumentElement(
        element_id="e1",
        document_id="doc-1",
        source_path=source_path,
        source_name=source_name,
        file_type="xlsx",
        extractor="unit",
        extraction_status=ExtractionStatus.SUCCESS,
        element_type=ElementType.TEXT,
        text=text,
        privacy_labels=("private",),
        source_fingerprint="fp1",
        page=1,
    )
    return StructureAwareChunker(max_chars=500).chunk_elements([element])[0]


def test_ingest_labels_chunk_domain(tmp_path):
    from aios_habit.rag_v2.index import LocalChunkIndex

    chunk = _make_chunk(
        "LSU_log_jig.xlsx",
        "/data/LSU_log_jig.xlsx",
        "SelNo bowskew NG tai tram fin test, log jig laser scan unit",
    )
    db_path = tmp_path / "idx.sqlite"
    with LocalChunkIndex(str(db_path)) as index:
        assert index.upsert_chunks([chunk]) == 1
    conn = sqlite3.connect(str(db_path))
    try:
        assert conn.execute("SELECT domain FROM chunks").fetchone()[0] == DOMAIN_LSU
    finally:
        conn.close()


def test_ingest_labels_reupsert_updates_domain(tmp_path):
    from dataclasses import replace as dc_replace

    from aios_habit.rag_v2.index import LocalChunkIndex

    db_path = tmp_path / "idx.sqlite"
    with LocalChunkIndex(str(db_path)) as index:
        chunk = _make_chunk("notes.txt", "/x/notes.txt", "ghi chu chung chung")
        index.upsert_chunks([chunk])
        # Same chunk_id, new MOM-flavoured source: label must follow the content.
        chunk2 = dc_replace(
            _make_chunk("MOM_spec.pdf", "/x/MOM_spec.pdf", "AGV通信仕様 WMS MOM Opcenter"),
            chunk_id=chunk.chunk_id,
        )
        index.upsert_chunks([chunk2])
    conn = sqlite3.connect(str(db_path))
    try:
        assert conn.execute("SELECT domain FROM chunks").fetchone()[0] == DOMAIN_MOM
    finally:
        conn.close()
