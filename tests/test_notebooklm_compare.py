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



def _score_for_text(
    text,
    question="What is the answer?",
    answer_kind="final_owner_answer",
    citations=None,
    metadata=None,
):
    from aios_habit.notebooklm_compare import _score_pair
    row = {
        "question": {"question_id": "QX", "question": question},
        "answer": {
            "answer_text": text,
            "answer_kind": answer_kind,
            "citation_ids": ["[E1]"] if citations is None else citations,
            "insufficient_evidence": False,
            "warnings": [],
            "metadata": metadata or {},
        },
    }
    return _score_pair(row, None)


def test_generic_local_draft_score_is_capped_at_6():
    score = _score_for_text("Local draft for: Q\nThis is a local evidence draft, not a final model answer.", answer_kind="local_evidence_draft")
    assert score["max_total_score"] <= 6
    assert score["total_score_12"] <= 6


def test_evidence_only_snippet_list_score_is_capped_at_7():
    text = "- [E1] route code missing\n- [E2] export mapping blank\n- [E3] dispatch failed"
    score = _score_for_text(text, citations=["[E1]", "[E2]", "[E3]"])
    assert score["max_total_score"] <= 7
    assert score["total_score_12"] <= 7


def test_final_synthesized_answer_can_score_higher_only_if_concrete():
    text = """## Kết luận ngắn
- Mapping thiếu route code nên owner cần kiểm tra master data [E1].
## Cách hiểu từ bằng chứng
Nguồn [E1] hỗ trợ claim vì nêu lỗi export mapping.
## Hướng xử lý / kiểm tra
1. Kiểm tra route code.
2. Đối chiếu log export.
3. Bàn giao owner dữ liệu.
"""
    score = _score_for_text(text, question="Give troubleshooting path")
    assert score["max_total_score"] == 12
    assert score["total_score_12"] > 6


def test_citations_without_claim_support_traceability_max_1():
    score = _score_for_text("## Kết luận ngắn\n- Route code missing.\n## Bảng nguồn\n| [E1] | file |", citations=["[E1]"])
    assert score["source_traceability"] <= 1


def test_process_question_answered_as_excel_mapping_is_capped_at_6():
    text = """## Kết luận ngắn
- Mapping route code cần kiểm tra trong bảng dữ liệu [E1].
## Hướng xử lý / kiểm tra
1. Kiểm tra route code.
2. Đối chiếu mapping export.
3. Bàn giao owner dữ liệu.
"""
    score = _score_for_text(
        text,
        question="Explain automatic/manual boundary in the process",
        metadata={"answer_profile": "excel_mapping"},
    )
    assert score["max_total_score"] <= 6
    assert score["total_score_12"] <= 6


def test_screenshot_answer_using_html_primary_is_capped_at_5():
    text = """## Kết luận ngắn
- schema/html shows route error markup [E1].
## Hướng xử lý / kiểm tra
1. Kiểm tra HTML.
2. Đối chiếu schema.
3. Bàn giao owner.
"""
    score = _score_for_text(
        text,
        question="What does the screenshot show?",
        metadata={"answer_profile": "screenshot_visible_facts"},
    )
    assert score["max_total_score"] <= 5
    assert score["total_score_12"] <= 5


def test_excel_mapping_without_fields_or_keys_is_capped_at_7():
    text = """## Kết luận ngắn
- Export looks wrong [E1].
## Hướng xử lý / kiểm tra
1. Check export.
2. Review data.
3. Ask owner.
"""
    score = _score_for_text(text, metadata={"answer_profile": "excel_mapping"})
    assert score["max_total_score"] <= 7
    assert score["total_score_12"] <= 7


def test_generic_check_logs_for_troubleshooting_is_capped_at_6():
    score = _score_for_text(
        "Check logs [E1].",
        question="Give full troubleshooting path and missing evidence",
    )
    assert score["max_total_score"] <= 6
    assert score["total_score_12"] <= 6


def test_missing_target_source_without_admission_is_capped_at_6():
    text = """## Kết luận ngắn
- Route export failed [E1].
## Hướng xử lý / kiểm tra
1. Kiểm tra route.
2. Đối chiếu log.
3. Bàn giao owner.
"""
    score = _score_for_text(text, metadata={"source_type_pass": "FAIL"})
    assert score["max_total_score"] <= 6
    assert score["total_score_12"] <= 6


def test_source_type_partial_score_cap_at_8_without_override():
    text = """## Ket luan ngan
- Application timeout is visible in log [E1].
## Huong xu ly / kiem tra
1. Check the cited log.
2. Compare configuration.
3. Collect missing record.
"""
    score = _score_for_text(text, metadata={"source_type_pass": "PARTIAL"})
    assert score["max_total_score"] <= 8
    assert score["total_score_12"] <= 8


def test_source_type_fail_score_cap_at_6():
    score = _score_for_text(
        "## Ket luan ngan\n- Direct answer [E1].\n## Huong xu ly / kiem tra\n1. Check source.\n2. Check record.\n3. Check log.",
        metadata={"source_type_pass": "FAIL"},
    )
    assert score["max_total_score"] <= 6
    assert score["total_score_12"] <= 6


def test_wrong_domain_playbook_cap_at_6():
    score = _score_for_text(
        "## Ket luan ngan\n- Direct answer [E1].\n## Huong xu ly / kiem tra\n1. Check source.\n2. Check record.\n3. Check log.",
        metadata={"domain_playbook": "manufacturing_mom_wms", "expected_domain_playbook": "general"},
    )
    assert score["max_total_score"] <= 6
    assert score["total_score_12"] <= 6


def test_manufacturing_template_in_general_domain_cap_at_6():
    text = """## Ket luan ngan
- Check WMS/MOM/AGV handoff [E1].
## Huong xu ly / kiem tra
1. Check WMS log.
2. Check MOM record.
3. Check AGV signal.
"""
    score = _score_for_text(text, metadata={"domain_playbook": "general"})
    assert score["max_total_score"] <= 6
    assert score["total_score_12"] <= 6


def test_human_review_side_by_side_does_not_imply_pass_or_win():
    score = _score_for_text(
        "## Ket luan ngan\n- Direct answer [E1].\n## Huong xu ly / kiem tra\n1. Check source.\n2. Check record.\n3. Check log.",
        metadata={"side_by_side_status": "HUMAN_REVIEW"},
    )
    assert score["max_total_score"] <= 8
    assert score["winner"] == "aios_only_no_notebooklm_answer"


def test_score_10_requires_correct_primary_evidence_and_citations():
    weak = _score_for_text(
        "## Ket luan ngan\n- Direct answer.\n## Huong xu ly / kiem tra\n1. Check source.\n2. Check record.\n3. Check log.",
        citations=[],
        metadata={"source_type_pass": "PARTIAL"},
    )
    strong = _score_for_text(
        "## Ket luan ngan\n- Direct answer supported by citation [E1].\n## Huong xu ly / kiem tra\n1. Check source.\n2. Check record.\n3. Check log.",
        metadata={"source_type_pass": "PASS"},
    )
    assert weak["total_score_12"] < 10
    assert strong["max_total_score"] == 12
