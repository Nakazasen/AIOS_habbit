import json
from pathlib import Path

import pytest


def test_inventory_scan_synthetic_folder_local_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aios_habit.real_doc_inventory import scan_mom_inventory

    root = tmp_path / "docs"
    root.mkdir()
    (root / "process.md").write_text("Production history registration process", encoding="utf-8")
    (root / "binary.pdf").write_bytes(b"%PDF fake")

    inv = scan_mom_inventory(root)

    assert inv.root_exists is True
    assert inv.total_files == 2
    assert inv.file_types[".md"] == 1
    assert inv.file_types[".pdf"] == 1
    assert inv.privacy_level == "local_only"
    assert all(item.privacy_level == "local_only" for item in inv.files)
    assert inv.unsupported_files[0]["privacy_level"] == "local_only"


def test_mom_local_index_chunks_and_search_synthetic_text(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aios_habit.mom_local_index import build_mom_local_index, search_mom_index

    root = tmp_path / "docs"
    root.mkdir()
    (root / "interface.md").write_text(
        "Production history registration interface input fields include order_no and item_code.",
        encoding="utf-8",
    )

    result = build_mom_local_index(root)
    hits = search_mom_index("production history input fields", limit=3)

    assert result.root_exists is True
    assert result.chunks_generated >= 1
    assert result.privacy_level == "local_only"
    assert hits
    assert hits[0].chunk.privacy_level == "local_only"
    assert "interface.md" in hits[0].chunk.relative_path


def test_mom_prompt_pack_includes_refs_and_privacy_warning(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aios_habit.mom_local_index import build_mom_local_index, search_mom_index, build_mom_qa_prompt

    root = tmp_path / "docs"
    root.mkdir()
    (root / "flow.md").write_text("MOM WMS interaction sends production result after confirmation.", encoding="utf-8")
    build_mom_local_index(root)

    hits = search_mom_index("MOM WMS interaction", limit=2)
    pack = build_mom_qa_prompt("MOM WMS interaction là gì?", hits)

    assert pack["privacy_level"] == "local_only"
    assert pack["source_refs"]
    assert "local_only" in pack["cloud_warning"]
    assert "relative_path" in pack["source_refs"][0]
    assert "chưa đủ bằng chứng" in pack["prompt"]


def test_mom_prompt_pack_marks_insufficient_when_no_hits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aios_habit.mom_local_index import build_mom_qa_prompt

    pack = build_mom_qa_prompt("unknown question", [])

    assert pack["insufficient_evidence"] is True
    assert pack["source_refs"] == []
    assert "Không tìm thấy nguồn MOM local đủ khớp" in pack["prompt"]


def test_create_mom_case_from_hit_has_draft_local_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aios_habit import case_store
    from aios_habit.mom_local_index import build_mom_local_index, search_mom_index, create_mom_case_from_hit

    monkeypatch.setattr(case_store, "LOCAL_CASES_DIR", tmp_path / "local_cases")
    monkeypatch.setattr(case_store, "CASES_FILE", tmp_path / "local_cases" / "cases.jsonl")
    monkeypatch.setattr(case_store, "EVIDENCE_FILE", tmp_path / "local_cases" / "evidence.jsonl")
    monkeypatch.setattr(case_store, "ASSETS_DIR", tmp_path / "local_cases" / "assets")

    root = tmp_path / "docs"
    root.mkdir()
    (root / "case.md").write_text("Production history evidence source", encoding="utf-8")
    build_mom_local_index(root)
    hit = search_mom_index("production history", limit=1)[0]

    res = create_mom_case_from_hit("production history?", hit, workspace_id="ws-test")
    cases = case_store.load_cases()
    evidence = case_store.load_evidence()

    assert res["source_origin"] == "mom_official_local"
    assert res["verification_status"] == "draft"
    assert cases[0].source_origin == "mom_official_local"
    assert cases[0].verification_status == "draft"
    assert cases[0].privacy_level == "local_only"
    assert evidence[0].source_origin == "mom_official_local"
    assert evidence[0].verification_status == "draft"
    assert evidence[0].privacy_level == "local_only"


def test_benchmark_record_manual_required_not_fake_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aios_habit.mom_benchmark import notebooklm_manual_required_record, save_benchmark_record, load_benchmark_records

    record = notebooklm_manual_required_record(
        question_id="Q1",
        question="Quy trình là gì?",
        aios_source_refs=[{"chunk_id": "c1", "relative_path": "doc.md", "privacy_level": "local_only"}],
        aios_answer_summary="Có source refs; cần hỏi NotebookLM thủ công.",
    )
    path = save_benchmark_record(record)
    records = load_benchmark_records(path)

    assert record.notebooklm_query_status == "manual_required"
    assert record.winner == "Inconclusive"
    assert record.privacy_level == "local_only"
    assert records[0].notebooklm_query_status == "manual_required"


def test_compare_rubric_deterministic_with_notebook_answer():
    from aios_habit.mom_benchmark import compare_aios_notebooklm

    scores, winner, notes = compare_aios_notebooklm(
        question="Q",
        aios_source_refs=[{"chunk_id": "c1"}, {"chunk_id": "c2"}],
        aios_answer_summary="Trả lời có next checks và nguồn.",
        notebooklm_answer_summary="NotebookLM answer with source citation.",
        notebooklm_query_status="success",
    )

    assert scores["source_traceability"] == 5
    assert winner in {"AIOS", "NotebookLM", "Tie"}
    assert "comparator" in notes


def test_safe_benchmark_questions_generated_local_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aios_habit.mom_local_index import generate_safe_benchmark_questions

    qs = generate_safe_benchmark_questions(limit=5)

    assert len(qs) == 5
    assert all(q["privacy_level"] == "local_only" for q in qs)
    assert all(q["question_id"].startswith("MOM-Q") for q in qs)
