import json
from pathlib import Path

from aios_habit.notebooklm_compare import (
    CompareConfig,
    build_chunks_from_folder,
    evaluate_answers,
    generate_questions,
    run_aios_answers,
    write_questions,
)


def _config(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "mom.txt").write_text("Quy trinh WMS gom buoc nhap kho, kiem tra, va xuat kho.", encoding="utf-8")
    (src / "error.log").write_text("ERROR route code missing after export mapping validation", encoding="utf-8")
    return CompareConfig(source_root=str(src), output_dir=str(tmp_path / "runs"), question_count=6)


def test_generate_questions_has_required_categories(tmp_path):
    config = _config(tmp_path)
    questions = generate_questions(config)
    assert len(questions) == 6
    assert {q.category for q in questions} == {
        "direct_lookup", "procedure_step", "cause_effect", "evidence_sufficiency", "cross_document_relation", "unanswerable"
    }
    assert any(q.language == "ja" for q in questions)


def test_aios_runner_writes_ignored_runtime_jsonl_with_citations(tmp_path):
    config = _config(tmp_path)
    questions_path = write_questions(config)
    out = run_aios_answers(config, questions_path)
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 6
    assert rows[0]["answer"]["provider_call"] is False
    assert rows[0]["answer"]["notebooklm_call"] is False
    assert "citation_ids" in rows[0]["answer"]


def test_evaluator_marks_human_review_without_notebooklm_answers(tmp_path):
    config = _config(tmp_path)
    run_aios_answers(config, write_questions(config))
    paths = evaluate_answers(config)
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert payload["status"] == "PASS_CANDIDATE"
    assert payload["notebooklm_answers"] == 0
    assert "human review" in payload["note"]


def test_build_chunks_from_folder_uses_safe_relative_paths(tmp_path):
    config = _config(tmp_path)
    chunks = build_chunks_from_folder(config)
    assert chunks
    assert all(not chunk.relative_path.startswith("D:") for chunk in chunks)
    assert all(chunk.privacy_mode == "local_only" for chunk in chunks)

def test_build_chunks_from_folder_extracts_excel(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    
    # Create valid base workbook
    import openpyxl
    file_path = src / "mock.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = "Real Excel Text Here"
    wb.save(file_path)
    wb.close()
    
    config = CompareConfig(source_root=str(src), output_dir=str(tmp_path / "runs"), question_count=1)
    chunks = build_chunks_from_folder(config)
    
    assert len(chunks) > 0
    # Should contain the real text from the Excel file
    assert any("Real Excel Text Here" in chunk.text for chunk in chunks)
    # Should not be just a metadata string
    assert all("Raw binary content was not extracted" not in chunk.text for chunk in chunks if chunk.file_type == "xlsx")
