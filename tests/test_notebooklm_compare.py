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
    assert payload["comparison_mode"] == "local_draft_vs_notebooklm_answer"
    assert "retrieval/extraction coverage" in payload["warning"]


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
    # Should not be just a metadata string
    assert all("Raw binary content was not extracted" not in chunk.text for chunk in chunks if chunk.file_type == "xlsx")


def test_print_local_review(tmp_path):
    from aios_habit.notebooklm_compare import print_local_review
    
    config = CompareConfig(source_root=str(tmp_path / "src"), output_dir=str(tmp_path / "runs"), question_count=1)
    out_dir = tmp_path / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    q_path = out_dir / "questions.jsonl"
    a_path = out_dir / "aios_answers.jsonl"
    
    q_path.write_text(json.dumps({"question_id": "Q001", "question": "What is the procedure?"}), encoding="utf-8")
    a_path.write_text(json.dumps({
        "question": {"question_id": "Q001"},
        "answer": {"answer_text": "Local draft text", "insufficient_evidence": False},
        "evidence_pack": {"evidence_quality": "content_supported"}
    }), encoding="utf-8")
    
    output_md = out_dir / "human_review.md"
    print_local_review(config, str(output_md))
    
    assert output_md.exists()
    content = output_md.read_text(encoding="utf-8")
    assert "Q Q001" in content
    assert "What is the procedure?" in content
    assert "Local draft text" in content
    assert "NotebookLM answer" in content
    assert "Không có kết quả" in content
    assert "Evidence quality: content_supported" in content
