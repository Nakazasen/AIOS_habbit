"""Tests cho knowledge_digest + digest_qa (ve KNOWLEDGE-DIGEST-HOME).

Khong can LLM that, khong cham vao DB that: dung sqlite tam + llm_call gia.
"""

import hashlib
import json
import sqlite3

import pytest

from aios_habit import digest_qa, knowledge_digest
from aios_habit.digest_qa import QABenchmarkReport, ask_handbook, run_benchmark
from aios_habit.knowledge_digest import (
    DigestEntry,
    count_documents,
    group_by_topic,
    list_documents,
    open_index_readonly,
    read_document_text,
    render_handbook,
    run_digest,
    summarize_document,
    write_manifest,
)


def _make_index(path):
    conn = sqlite3.connect(str(path))
    conn.execute(
        """CREATE TABLE chunk_metadata (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT,
            source_title TEXT,
            relative_path TEXT,
            citation_label TEXT,
            file_type TEXT,
            privacy_mode TEXT,
            page_numbers_json TEXT,
            sheet_names_json TEXT,
            slide_numbers_json TEXT,
            element_types_json TEXT,
            text TEXT,
            raw_json TEXT
        )"""
    )
    rows = [
        ("c1", "doc-a", "Tai lieu A", "a/a.md", "noi dung A phan 1"),
        ("c2", "doc-a", "Tai lieu A", "a/a.md", "noi dung A phan 2"),
        ("c3", "doc-b", "Tai lieu B", "b/b.md", "noi dung B"),
        ("c4", "doc-c", "Tai lieu C", "c/c.md", "x" * 20000),
    ]
    conn.executemany(
        "INSERT INTO chunk_metadata (chunk_id, document_id, source_title,"
        " relative_path, text) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()
    return path


def _fake_llm_json(prompt: str) -> str:
    return json.dumps(
        {
            "chu_de": "Chu de test",
            "y_chinh": ["y 1", "y 2"],
            "so_lieu": ["10 mm"],
            "dieu_kien_nguong_ngoai_le": ["nhiet do < 40 do"],
            "lien_quan": [],
        },
        ensure_ascii=False,
    )


def test_open_readonly_and_count_and_list(tmp_path):
    index = _make_index(tmp_path / "library.sqlite")
    conn = open_index_readonly(index)
    try:
        assert count_documents(conn) == 3
        docs = list_documents(conn)
        assert [d["document_id"] for d in docs] == ["doc-a", "doc-b", "doc-c"]
        assert docs[0]["chunks"] == 2
    finally:
        conn.close()


def test_read_document_text_joins_chunks_and_flags_truncation(tmp_path):
    index = _make_index(tmp_path / "library.sqlite")
    conn = open_index_readonly(index)
    try:
        text, truncated = read_document_text(conn, "doc-a")
        assert "phan 1" in text and "phan 2" in text
        assert truncated is False
        text_c, truncated_c = read_document_text(conn, "doc-c", max_chars=100)
        assert len(text_c) == 100
        assert truncated_c is True
    finally:
        conn.close()


def test_summarize_document_parses_structured_json():
    doc = {"document_id": "doc-a", "source_title": "Tai lieu A", "relative_path": "a/a.md"}
    entry = summarize_document(doc, "noi dung", False, _fake_llm_json)
    assert entry.chu_de == "Chu de test"
    assert entry.y_chinh == ["y 1", "y 2"]
    assert entry.so_lieu == ["10 mm"]
    assert entry.raw == ""


def test_summarize_document_keeps_raw_when_llm_returns_garbage():
    doc = {"document_id": "doc-a", "source_title": "A", "relative_path": ""}
    entry = summarize_document(doc, "noi dung", False, lambda prompt: "khong phai json {{{")
    assert entry.y_chinh == []
    assert "khong phai json" in entry.raw


def test_run_digest_end_to_end_with_resume(tmp_path):
    index = _make_index(tmp_path / "library.sqlite")
    out = tmp_path / "digest_out"
    calls = []

    def llm(prompt: str) -> str:
        calls.append(prompt)
        return _fake_llm_json(prompt)

    stats = run_digest(index, out, llm)
    assert stats["doc_total"] == 3
    assert stats["entry_count"] == 3
    handbook = (out / "so_tay_tri_thuc.md").read_text(encoding="utf-8")
    assert handbook.startswith("# Sổ tay tri thức")
    assert knowledge_digest.DRAFT_BANNER in handbook
    assert "Tai lieu A" in handbook

    manifest = json.loads((out / "so_tay_tri_thuc.md.manifest.json").read_text(encoding="utf-8"))
    assert manifest["doc_total"] == 3
    assert manifest["entry_count"] == 3
    expected_sha = hashlib.sha256((out / "so_tay_tri_thuc.md").read_bytes()).hexdigest()
    assert manifest["sha256"] == expected_sha

    # Chay lai: resume tu checkpoint, khong goi LLM them.
    before = len(calls)
    stats2 = run_digest(index, out, llm)
    assert stats2["entry_count"] == 3
    assert len(calls) == before


def test_run_digest_checkpoint_every_n(tmp_path):
    index = _make_index(tmp_path / "library.sqlite")
    out = tmp_path / "digest_out"
    run_digest(index, out, _fake_llm_json, progress_every=1)
    ckpt = json.loads((out / "digest_checkpoint.json").read_text(encoding="utf-8"))
    assert len(ckpt["done"]) == 3


def test_group_by_topic_handles_empty_topic():
    entries = [
        DigestEntry(document_id="a", source_title="A", relative_path="", chu_de="X"),
        DigestEntry(document_id="b", source_title="B", relative_path="", chu_de=""),
    ]
    groups = group_by_topic(entries)
    assert set(groups.keys()) == {"X", "Chưa phân loại"}


def test_render_handbook_sorts_topics_and_counts(tmp_path):
    entries = [
        DigestEntry(document_id="a", source_title="A", relative_path="", chu_de="X", y_chinh=["y"]),
    ]
    text = render_handbook(entries, doc_total=5)
    assert "Số document trong kho: 5" in text
    assert "Số mục trong sổ tay: 1" in text
    assert "# Chủ đề: X" in text


def test_ask_handbook_records_timing_and_sizes():
    result = ask_handbook("SO TAY NGAN", "cau hoi?", lambda prompt: "tra loi")
    assert result.answer == "tra loi"
    assert result.elapsed_s >= 0
    assert result.handbook_chars == len("SO TAY NGAN")
    assert result.prompt_chars > result.handbook_chars


def test_run_benchmark_report_aggregates(tmp_path):
    handbook = tmp_path / "so_tay.md"
    handbook.write_text("noi dung so tay", encoding="utf-8")
    report = run_benchmark(handbook, lambda prompt: "ok", questions=["q1", "q2"])
    assert isinstance(report, QABenchmarkReport)
    data = report.to_dict()
    assert data["questions"] == 2
    assert data["avg_s"] >= 0
    assert all(r["answer"] == "ok" for r in data["results"])


def test_default_benchmark_questions_are_broad_vietnamese():
    assert len(digest_qa.DEFAULT_BENCHMARK_QUESTIONS) >= 10
    assert all("?" in q for q in digest_qa.DEFAULT_BENCHMARK_QUESTIONS)


def test_coverage_rubric_exists():
    assert "2 điểm" in digest_qa.COVERAGE_RUBRIC
