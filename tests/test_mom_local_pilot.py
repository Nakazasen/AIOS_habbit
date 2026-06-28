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
    assert any(item.file_type == ".pdf" and item.supported for item in inv.files)


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


def test_document_extractor_html_removes_tags_local_only(tmp_path):
    from aios_habit.document_extractors import extract_text_chunks_from_file

    html_file = tmp_path / "procedure.html"
    html_file.write_text(
        "<html><head><style>.x{}</style><script>hidden()</script></head>"
        "<body><h1>Production History</h1><p>Register result interface.</p></body></html>",
        encoding="utf-8",
    )

    chunks = extract_text_chunks_from_file(html_file, root=tmp_path)

    assert chunks[0]["extraction_status"] == "extracted_success"
    assert chunks[0]["privacy_level"] == "local_only"
    assert "Production History" in chunks[0]["text"]
    assert "<h1>" not in chunks[0]["text"]
    assert "hidden" not in chunks[0]["text"]


def test_document_extractor_pptx_zip_xml_synthetic(tmp_path):
    import zipfile
    from aios_habit.document_extractors import extract_text_chunks_from_file

    pptx_file = tmp_path / "slides.pptx"
    with zipfile.ZipFile(pptx_file, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", "<p:sld><a:t>MOM confirmation slide</a:t></p:sld>")
        archive.writestr("ppt/notesSlides/notesSlide1.xml", "<p:notes><a:t>review before approval</a:t></p:notes>")

    chunks = extract_text_chunks_from_file(pptx_file, root=tmp_path)

    assert chunks[0]["extraction_status"] == "extracted_success"
    assert chunks[0]["file_type"] == ".pptx"
    assert "MOM confirmation slide" in chunks[0]["text"]
    assert chunks[0]["privacy_level"] == "local_only"


def test_document_extractor_xlsm_uses_openpyxl_when_available(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from aios_habit.document_extractors import extract_text_chunks_from_file

    xlsm_file = tmp_path / "book.xlsm"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Interface"
    sheet["A1"] = "field"
    sheet["B1"] = "production_history_id"
    workbook.save(xlsm_file)

    chunks = extract_text_chunks_from_file(xlsm_file, root=tmp_path)

    assert chunks[0]["extraction_status"] == "extracted_success"
    assert chunks[0]["file_type"] == ".xlsm"
    assert chunks[0]["sheet"] == "Interface"
    assert "production_history_id" in chunks[0]["text"]


def test_document_extractor_pdf_and_png_fail_gracefully(tmp_path):
    from aios_habit.document_extractors import extract_text_chunks_from_file

    pdf_file = tmp_path / "fake.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake")
    png_file = tmp_path / "image.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    pdf_chunks = extract_text_chunks_from_file(pdf_file, root=tmp_path)
    png_chunks = extract_text_chunks_from_file(png_file, root=tmp_path)

    assert pdf_chunks[0]["extraction_status"] in {"unsupported_no_local_ocr", "failed_with_reason", "parse_failed"}
    assert pdf_chunks[0]["privacy_level"] == "local_only"
    assert png_chunks[0]["extraction_status"] in {"unsupported_no_local_ocr", "failed_with_reason", "ocr_partial", "ocr_success"}
    assert png_chunks[0]["privacy_level"] == "local_only"


def test_mom_local_index_uses_document_extractors_for_html_pptx_xlsm(tmp_path, monkeypatch):
    import zipfile
    import openpyxl

    monkeypatch.chdir(tmp_path)
    from aios_habit.mom_local_index import build_mom_local_index, search_mom_index, build_mom_qa_prompt

    root = tmp_path / "docs"
    root.mkdir()
    (root / "procedure.html").write_text("<body>HTML production result registration</body>", encoding="utf-8")
    with zipfile.ZipFile(root / "deck.pptx", "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", "<a:t>PPTX interface mapping token</a:t>")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Fields"
    sheet["A1"] = "xlsm production result field"
    workbook.save(root / "fields.xlsm")

    result = build_mom_local_index(root)
    hits = search_mom_index("interface mapping token", limit=3)
    html_hits = search_mom_index("HTML production result", limit=3)
    pack = build_mom_qa_prompt("interface mapping?", hits)

    assert result.chunks_generated >= 3
    assert hits
    assert html_hits
    assert hits[0].chunk.extractor_name in {"pptx_zip_xml", "document_extractors"}
    assert pack["source_refs"][0]["file_type"] == ".pptx"
    assert pack["source_refs"][0]["extraction_status"] == "extracted_success"
    assert pack["source_refs"][0]["privacy_level"] == "local_only"


def test_document_extractor_docx_zip_xml_synthetic(tmp_path):
    import zipfile
    from aios_habit.document_extractors import extract_text_chunks_from_file

    docx_file = tmp_path / "procedure.docx"
    with zipfile.ZipFile(docx_file, "w") as archive:
        archive.writestr("word/document.xml", "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>DOCX production registration rule</w:t></w:r></w:p></w:body></w:document>")
        archive.writestr("word/header1.xml", "<w:hdr xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:p><w:r><w:t>Header context</w:t></w:r></w:p></w:hdr>")

    chunks = extract_text_chunks_from_file(docx_file, root=tmp_path)

    assert chunks[0]["extraction_status"] == "extracted_success"
    assert chunks[0]["file_type"] == ".docx"
    assert chunks[0]["privacy_level"] == "local_only"
    assert "DOCX production registration rule" in chunks[0]["text"]


def test_document_extractor_png_ocr_local_or_safe_unsupported(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image, ImageDraw
    from aios_habit.document_extractors import extract_text_chunks_from_file, local_capabilities

    image_file = tmp_path / "ocr.png"
    image = Image.new("RGB", (320, 80), color="white")
    draw = ImageDraw.Draw(image)
    draw.text((10, 25), "MOM OCR TEST", fill="black")
    image.save(image_file)

    chunks = extract_text_chunks_from_file(image_file, root=tmp_path)
    caps = local_capabilities()

    assert chunks[0]["privacy_level"] == "local_only"
    if caps["ocr_available"]:
        assert chunks[0]["extraction_status"] in {"ocr_success", "ocr_partial", "failed_with_reason"}
    else:
        assert chunks[0]["extraction_status"] == "unsupported_no_local_ocr"
        assert "local OCR unavailable" in chunks[0]["warning"]


def test_mom_coverage_summary_no_unknown_unsupported(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aios_habit.mom_coverage import summarize_mom_coverage

    root = tmp_path / "docs"
    root.mkdir()
    (root / "note.md").write_text("Production registration evidence", encoding="utf-8")
    (root / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    summary = summarize_mom_coverage(root)

    assert summary.total_files == 2
    assert summary.unknown_unsupported == 0
    assert summary.status_counts["extracted_success"] >= 1
    assert summary.privacy_level == "local_only"


def test_benchmark_gate_blocks_50_when_score_below_90():
    from aios_habit.mom_benchmark import MomBenchmarkRecord
    from aios_habit.mom_benchmark_gate import evaluate_benchmark_gate

    records = [MomBenchmarkRecord(
        question_id=f"Q{i:02d}",
        question="Q",
        aios_answer_summary="Có nguồn nhưng chưa đủ bằng chứng.",
        aios_source_refs=[{"chunk_id": "c1"}],
        notebooklm_query_status="success",
        comparison_scores={"source_traceability": 3, "answer_completeness": 3, "hallucination_risk": 5, "actionability": 3, "vietnamese_clarity": 4, "evidence_alignment": 4},
        winner="Tie",
    ) for i in range(20)]

    gate = evaluate_benchmark_gate(records, target_questions=20, expansion_threshold=18)

    assert gate.target_90_met is False
    assert gate.attempted_50 is False
    assert gate.reason == "average maturity score below 90"


def test_benchmark_gate_allows_50_when_20q_passes():
    from aios_habit.mom_benchmark import MomBenchmarkRecord
    from aios_habit.mom_benchmark_gate import evaluate_benchmark_gate

    records = [MomBenchmarkRecord(
        question_id=f"Q{i:02d}",
        question="Q",
        aios_answer_summary="Trả lời dựa trên nguồn; next checks rõ.",
        aios_source_refs=[{"chunk_id": "c1"}, {"chunk_id": "c2"}],
        notebooklm_query_status="success",
        comparison_scores={"source_traceability": 5, "answer_completeness": 5, "hallucination_risk": 5, "actionability": 5, "vietnamese_clarity": 5, "evidence_alignment": 5},
        winner="AIOS",
    ) for i in range(20)]

    gate = evaluate_benchmark_gate(records, target_questions=20, expansion_threshold=18)

    assert gate.target_90_met is True
    assert gate.attempted_50 is True
    assert gate.aios_answers_with_source_refs == 20


def test_tesseract_env_path_discovery_mock(tmp_path, monkeypatch):
    from aios_habit import document_extractors

    fake = tmp_path / "tesseract.exe"
    fake.write_text("fake", encoding="utf-8")
    monkeypatch.setenv("AIOS_TESSERACT_CMD", str(fake))
    monkeypatch.setattr(document_extractors.shutil, "which", lambda name: None)

    assert document_extractors._discover_tesseract_cmd() == str(fake)


def test_benchmark_scores_prompt_pack_above_90_with_diverse_refs():
    from aios_habit.mom_benchmark_gate import score_aios_prompt_pack, weighted_maturity_score

    pack = {
        "prompt": "Câu hỏi nghiệp vụ MOM\nNext checks",
        "answer_text": "Confirmed by source: có nguồn. Not found / insufficient evidence: chưa thấy phần ngoài nguồn. Next checks: kiểm tra nguồn liên quan. Source coverage: 3 nguồn local_only.",
        "insufficient_evidence": False,
        "source_refs": [
            {"relative_path": "a.xlsx"},
            {"relative_path": "b.pdf"},
            {"relative_path": "c.png"},
        ],
        "source_coverage": {"source_count": 3},
        "answer_discipline": {
            "confirmed_by_source_required": True,
            "insufficient_evidence_required": True,
            "next_checks_required": True,
            "notebooklm_comparator_not_ground_truth": True,
        },
    }

    assert weighted_maturity_score(score_aios_prompt_pack(pack)) >= 90


def test_benchmark_scores_weak_ref_only_answer_below_90():
    from aios_habit.mom_benchmark_gate import score_aios_prompt_pack, weighted_maturity_score

    pack = {
        "prompt": "Câu hỏi nghiệp vụ MOM\nNext checks",
        "insufficient_evidence": False,
        "source_refs": [
            {"relative_path": "a.xlsx"},
            {"relative_path": "b.pdf"},
            {"relative_path": "c.png"},
        ],
        "answer_discipline": {
            "confirmed_by_source_required": True,
            "insufficient_evidence_required": True,
            "next_checks_required": True,
            "notebooklm_comparator_not_ground_truth": True,
        },
    }

    assert weighted_maturity_score(score_aios_prompt_pack(pack)) < 90


def test_generate_mom_grounded_answer_returns_actual_sections(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aios_habit.mom_benchmark import generate_mom_grounded_answer, score_mom_real_answer, weighted_real_answer_score
    from aios_habit.mom_local_index import build_mom_local_index, search_mom_index

    root = tmp_path / "docs"
    root.mkdir()
    (root / "interface.md").write_text(
        "Production registration interface confirms source records, required conditions, and next validation checks.",
        encoding="utf-8",
    )
    build_mom_local_index(root)
    hits = search_mom_index("Production registration", limit=3)
    answer = generate_mom_grounded_answer("Production registration", hits)

    assert answer["privacy_level"] == "local_only"
    assert answer["answer_text"]
    assert answer["confirmed_by_source"]
    assert answer["next_checks"]
    assert answer["source_refs"]
    assert "Confirmed by source" in answer["answer_text"]
    assert "Not found / insufficient evidence" in answer["answer_text"]
    assert "Next checks" in answer["answer_text"]
    assert weighted_real_answer_score(score_mom_real_answer(answer)) >= 90


def test_generate_mom_grounded_answer_insufficient_when_no_hits():
    from aios_habit.mom_benchmark import generate_mom_grounded_answer, score_mom_real_answer, weighted_real_answer_score

    answer = generate_mom_grounded_answer("unknown unsupported", [])

    assert answer["confidence_level"] == "insufficient"
    assert "Không đủ bằng chứng" in answer["answer_text"]
    assert answer["source_refs"] == []
    assert weighted_real_answer_score(score_mom_real_answer(answer)) < 70


def test_generate_mom_grounded_answer_filters_unsupported_specific_terms(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aios_habit.mom_benchmark import generate_mom_grounded_answer, score_mom_real_answer, weighted_real_answer_score
    from aios_habit.mom_local_index import build_mom_local_index, search_mom_index

    root = tmp_path / "docs"
    root.mkdir()
    (root / "process.md").write_text("MOM production history registration process evidence.", encoding="utf-8")
    build_mom_local_index(root)

    hits = search_mom_index("unsupported blockchain topic not in MOM docs", limit=5)
    answer = generate_mom_grounded_answer("unsupported blockchain topic not in MOM docs", hits)

    assert answer["confidence_level"] == "insufficient"
    assert answer["source_refs"] == []
    assert weighted_real_answer_score(score_mom_real_answer(answer)) < 70

    for unsupported in [
        "unsupported payroll approval workflow in MOM docs",
        "unsupported machine learning prediction model accuracy",
        "unsupported customer CRM sales opportunity pipeline",
        "unsupported finance invoice tax compliance policy",
    ]:
        hits = search_mom_index(unsupported, limit=5)
        answer = generate_mom_grounded_answer(unsupported, hits)
        assert answer["confidence_level"] == "insufficient"
        assert answer["source_refs"] == []
        assert weighted_real_answer_score(score_mom_real_answer(answer)) < 70


def test_generate_mom_grounded_answer_broadened_fallback_not_high_confidence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from aios_habit.mom_benchmark import generate_mom_grounded_answer
    from aios_habit.mom_local_index import build_mom_local_index, search_mom_index

    root = tmp_path / "docs"
    root.mkdir()
    (root / "interface.md").write_text("MOM production interface includes order data and registration flow.", encoding="utf-8")
    build_mom_local_index(root)

    hits = search_mom_index("unicorn interface", limit=5)
    answer = generate_mom_grounded_answer("unicorn interface", hits)

    assert answer["source_refs"]
    assert answer["broadened_fallback"] is True
    assert answer["confidence_level"] in {"low", "medium"}
    assert "Tóm tắt trả lời" in answer["answer_text"]
    assert "Điều có bằng chứng" in answer["answer_text"]


def test_real_answer_scoring_penalizes_prompt_only_and_weak_refs():
    from aios_habit.mom_benchmark import score_mom_real_answer, weighted_real_answer_score

    prompt_only = {"answer_text": "", "source_refs": [{"chunk_id": "c1", "relative_path": "a.xlsx"}], "confidence_level": "high"}
    weak = {"answer_text": "Có nguồn nhưng không trả lời thật.", "source_refs": [{"chunk_id": "c1", "relative_path": "a.xlsx"}], "confidence_level": "medium"}

    assert weighted_real_answer_score(score_mom_real_answer(prompt_only)) < 70
    assert weighted_real_answer_score(score_mom_real_answer(weak)) < 80


def test_real_answer_scoring_penalizes_fake_refs_and_bad_high_confidence():
    from aios_habit.mom_benchmark import score_mom_real_answer, weighted_real_answer_score

    answer = {
        "answer_text": "Confirmed by source: x\nNot found / insufficient evidence: không đủ bằng chứng\nNext checks: kiểm tra lại\nSource coverage: none",
        "confirmed_by_source": ["x"],
        "next_checks": ["kiểm tra lại", "đối chiếu"],
        "source_refs": [],
        "confidence_level": "high",
    }

    assert score_mom_real_answer(answer)["hallucination_control"] == 0
    assert weighted_real_answer_score(score_mom_real_answer(answer, valid_source_refs=False)) < 80
