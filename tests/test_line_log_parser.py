from pathlib import Path

from aios_habit.line_log_parser import (
    detect_line_log_dialect,
    ingest_line_log_bytes,
    parse_line_log_bytes,
    summarize_line_events,
)
from aios_habit.workspace_chat_source_ingest import ingest_and_extract_bytes


def test_jam_csv_is_not_ingested_into_knowledge_library():
    payload = b"timestamp,station,jam_code,serial\n2026-08-30 08:01,C1,JAM-01,SN1\n"
    knowledge = ingest_and_extract_bytes(payload, "jam.csv")
    assert knowledge["ok"] is False
    assert knowledge["error_code"] == "csv_not_in_knowledge_library"


def test_detect_jam_and_c_call_dialects():
    assert detect_line_log_dialect(["Time", "Station", "jam_code"]) == "jam"
    assert detect_line_log_dialect(["datetime", "c_call", "line"]) == "c_call"
    assert detect_line_log_dialect(["DATE", "TIME", "CAM_ID", "ERR_NUM"]) == "lsu_cam"
    assert detect_line_log_dialect(["foo", "bar"]) == "unknown"


def test_parse_lsu_cam_log_csv():
    payload = (
        b"DATE,TIME,CAM_ID,ERR_NUM,BARCODE,TACT_TIME\n"
        b"2026-08-30,08:15:22,CAM_01,E102,SN_LSU_001,12.5\n"
    )
    lsu = parse_line_log_bytes(
        payload,
        "LSU_CamError.csv",
    )
    assert lsu.ok is True
    assert lsu.dialect == "lsu_cam"
    assert len(lsu.events) == 1
    assert lsu.events[0].station == "CAM_01"
    assert lsu.events[0].code == "E102"
    assert lsu.events[0].serial == "SN_LSU_001"
    assert lsu.events[0].duration_s == 12.5
    assert lsu.events[0].provenance == "suspected"

    knowledge = ingest_and_extract_bytes(payload, "LSU_CamError.csv")
    assert knowledge["ok"] is False
    assert knowledge["error_code"] == "csv_not_in_knowledge_library"


def test_parse_jam_and_c_call_csv():
    jam = parse_line_log_bytes(
        b"timestamp,station,jam_code,serial,duration_s\n"
        b"2026-08-30 08:01,C1,JAM-01,SN1,1.5\n"
        b"2026-08-30 08:02,C1,JAM-01,SN2,2\n",
        "jam.csv",
    )
    assert jam.ok is True
    assert jam.dialect == "jam"
    assert len(jam.events) == 2
    assert jam.events[0].code == "JAM-01"
    assert jam.events[0].provenance == "suspected"

    ccall = parse_line_log_bytes(
        b"datetime,line,c_call\n2026-08-30 09:00,A2,CC-9\n",
        "ccall.csv",
    )
    assert ccall.ok is True
    assert ccall.dialect == "c_call"
    assert ccall.events[0].station == "A2"
    assert ccall.events[0].code == "CC-9"


def test_ingest_line_log_writes_sqlite_not_library(tmp_path, monkeypatch):
    import aios_habit.line_log_parser as parser
    import aios_habit.workspace_chat_store as store
    from aios_habit.local_jsonl import clear_jsonl_cache

    chat_dir = tmp_path / "chat"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", chat_dir)
    monkeypatch.setattr(store, "COLLECTIONS_FILE", chat_dir / "collections.jsonl")
    monkeypatch.setattr(parser, "LOCAL_CHAT_DIR", chat_dir)
    clear_jsonl_cache()
    store.init_chat_store()

    payload = (
        b"timestamp,station,jam_code\n"
        b"2026-08-30 08:01,C1,JAM-01\n"
        b"2026-08-30 08:03,C1,JAM-02\n"
    )
    summary = ingest_line_log_bytes(payload, "jam.csv", collection_id="tri_thuc")
    assert summary.ok is True
    assert summary.inserted == 2
    db_path = Path(summary.db_path)
    assert db_path.name == "line_events.sqlite"
    assert db_path.name != "library.sqlite"
    rolled = summarize_line_events("tri_thuc")
    assert rolled["count"] == 2
    assert rolled["top_codes"][0][0] in {"JAM-01", "JAM-02"}


def test_match_line_events_for_question_attaches_suspected_jam(tmp_path, monkeypatch):
    import aios_habit.line_log_parser as parser
    import aios_habit.workspace_chat_store as store
    from aios_habit.local_jsonl import clear_jsonl_cache
    from aios_habit.workspace_chat_rag_v2_adapter import _attach_line_log_evidence

    chat_dir = tmp_path / "chat"
    monkeypatch.setattr(store, "LOCAL_CHAT_DIR", chat_dir)
    monkeypatch.setattr(parser, "LOCAL_CHAT_DIR", chat_dir)
    clear_jsonl_cache()
    store.init_chat_store()
    ingest_line_log_bytes(
        b"timestamp,station,jam_code\n2026-08-30 08:01,C1,JAM-01\n",
        "jam.csv",
        collection_id="tri_thuc",
    )
    matched = parser.match_line_events_for_question("Máy C1 bị JAM-01", "tri_thuc")
    assert matched["count"] == 1
    assert matched["events"][0].code == "JAM-01"
    assert "chẩn đoán" in matched["owner_text"]
    attached = _attach_line_log_evidence(
        "Máy C1 bị JAM-01",
        {
            "evidence_items": [],
            "citations": [],
            "retrieved_context_sources": (),
            "summary_count": 0,
            "safe_owner_message": "Đã dùng 0 đoạn.",
        },
        "tri_thuc",
    )
    assert attached["line_log_attached"] is True
    assert attached["evidence_items"][0]["source_type"] == "line_log"
    assert "JAM-01" in attached["evidence_items"][0]["text"]
