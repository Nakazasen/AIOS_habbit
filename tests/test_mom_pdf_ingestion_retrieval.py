# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path
import pytest

from aios_habit.document_extractors import _extract_pdf
from aios_habit.mom_local_index import (
    MomChunk,
    build_mom_local_index,
    search_mom_index,
)

def test_pdf_extraction_success(monkeypatch, tmp_path):
    # Success path: mock pymupdf4llm.to_markdown to return some text
    class DummyPyMuPDF4LLM:
        @staticmethod
        def to_markdown(path):
            return "# Document Title\nThis is a mock PDF text-layer content."

    monkeypatch.setitem(sys.modules, "pymupdf4llm", DummyPyMuPDF4LLM)

    file_path = tmp_path / "mock.pdf"
    with open(file_path, "wb") as f:
        f.write(b"%PDF-1.4\n")

    results = _extract_pdf(file_path)
    assert len(results) == 1
    assert "mock PDF text-layer content" in results[0].text
    assert results[0].extraction_status == "extracted"
    assert results[0].extractor_name == "pymupdf4llm"

def test_pdf_extraction_fail_soft(monkeypatch, tmp_path):
    # Fail-soft path: no dependencies installed
    monkeypatch.setitem(sys.modules, "pymupdf4llm", None)
    monkeypatch.setitem(sys.modules, "fitz", None)

    file_path = tmp_path / "mock.pdf"
    with open(file_path, "wb") as f:
        f.write(b"%PDF-1.4\n")

    results = _extract_pdf(file_path)
    assert len(results) == 1
    assert results[0].extraction_status == "dependency_missing"
    assert results[0].text == ""

def test_mom_index_includes_pdf_chunks(monkeypatch, tmp_path):
    # Success path integration in build_mom_local_index
    class DummyPyMuPDF4LLM:
        @staticmethod
        def to_markdown(path):
            return "This is content from test_spec.pdf."

    monkeypatch.setitem(sys.modules, "pymupdf4llm", DummyPyMuPDF4LLM)

    # Mock the index path so we don't overwrite production index
    test_index = tmp_path / "test_mom_local_index.jsonl"
    from aios_habit import mom_local_index
    monkeypatch.setattr(mom_local_index, "INDEX_FILE", test_index)

    root = tmp_path / "docs"
    root.mkdir()
    (root / "test_spec.pdf").write_bytes(b"%PDF-1.4\n")

    res = build_mom_local_index(root, write_runtime=True)
    assert res.root_exists is True
    assert res.chunks_generated >= 1

    # Verify index contains PDF chunk
    lines = [json.loads(line) for line in test_index.read_text(encoding="utf-8").splitlines()]
    assert len(lines) >= 1
    assert any(l["file_type"] == ".pdf" and "test_spec.pdf" in l["relative_path"] for l in lines)

def test_retrieval_q1_mes_mom_boosting(monkeypatch, tmp_path):
    # Q1 MES/MOM query priority test
    test_index = tmp_path / "test_mom_local_index.jsonl"

    chunks = [
        # Target Q1 chunk in PDF
        MomChunk(
            chunk_id="MOM-1-CH001",
            source_file="MES_MOM_Linkage.pdf",
            relative_path="spec/MES_MOM_Linkage.pdf",
            file_type=".pdf",
            text="This spec describes the interface between MES and MOM systems for scheduling.",
            preview="descriptions of MES and MOM...",
            privacy_level="local_only",
            source_hash="1",
        ),
        # Unrelated Excel chunk
        MomChunk(
            chunk_id="MOM-2-CH001",
            source_file="ItemMaster.xlsx",
            relative_path="ItemMaster.xlsx",
            file_type=".xlsx",
            text="Item Code A123 has description widget.",
            preview="Item Code A123 description...",
            privacy_level="local_only",
            source_hash="2",
        )
    ]

    with open(test_index, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.__dict__, ensure_ascii=False) + "\n")

    from aios_habit import mom_local_index
    monkeypatch.setattr(mom_local_index, "INDEX_FILE", test_index)

    hits = search_mom_index("What is the difference between MES and MOM?", index_path=test_index)
    assert len(hits) >= 1
    assert hits[0].chunk.source_file == "MES_MOM_Linkage.pdf"

def test_retrieval_q2_production_history_anti_erd(monkeypatch, tmp_path):
    # Q2 Production History system query priority and ERD penalty test
    test_index = tmp_path / "test_mom_local_index.jsonl"

    seisan_rireki = "".join(chr(c) for c in [0x751f, 0x7523, 0x5c65, 0x6b74]) # 生産履歴
    touroku = "".join(chr(c) for c in [0x767b, 0x9332]) # 登録
    shisutemu = "".join(chr(c) for c in [0x30b7, 0x30b9, 0x30c6, 0x30e0]) # システム
    shiyousho = "".join(chr(c) for c in [0x4ed5, 0x69d8, 0x66f8]) # 仕様書
    q2_system = seisan_rireki + touroku + shisutemu # 生産履歴登録システム

    chunks = [
        # Target Q2 chunk in PDF
        MomChunk(
            chunk_id="MOM-1-CH001",
            source_file=q2_system + shiyousho + ".pdf",
            relative_path="spec/" + q2_system + shiyousho + ".pdf",
            file_type=".pdf",
            text=q2_system + ": lineout, restart, repair.",
            preview="Chức năng chính của " + seisan_rireki + "...",
            privacy_level="local_only",
            source_hash="1",
        ),
        # ERD HTML chunk (should be penalized)
        MomChunk(
            chunk_id="MOM-2-CH001",
            source_file="ERD_Kho_Van_NEW.html",
            relative_path="ERD_Kho_Van_NEW.html",
            file_type=".html",
            text="ERD diagram showing tables for Warehouse and Inventory tracking details.",
            preview="ERD showing tables...",
            privacy_level="local_only",
            source_hash="2",
        )
    ]

    with open(test_index, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.__dict__, ensure_ascii=False) + "\n")

    from aios_habit import mom_local_index
    monkeypatch.setattr(mom_local_index, "INDEX_FILE", test_index)

    hits = search_mom_index("Các chức năng của " + q2_system + " là gì?", index_path=test_index)
    assert len(hits) >= 1
    assert hits[0].chunk.source_file == q2_system + shiyousho + ".pdf"

    # If we search for ERD details specifically, the penalty should not trigger
    hits_erd = search_mom_index("ERD diagram showing tables Warehouse", index_path=test_index)
    assert len(hits_erd) >= 1
    assert hits_erd[0].chunk.source_file == "ERD_Kho_Van_NEW.html"

def test_retrieval_q3_manual_shipping_no_regression(monkeypatch, tmp_path):
    # Q3 Excel manual shipping query priority test
    test_index = tmp_path / "test_mom_local_index.jsonl"

    chunks = [
        # Unrelated PDF chunk
        MomChunk(
            chunk_id="MOM-1-CH001",
            source_file="MOM_Overview.pdf",
            relative_path="MOM_Overview.pdf",
            file_type=".pdf",
            text="General overview of MOM system features.",
            preview="General overview...",
            privacy_level="local_only",
            source_hash="1",
        ),
        # Target Q3 Excel chunk
        MomChunk(
            chunk_id="MOM-2-CH001",
            source_file="ManualShippingSpec.xlsx",
            relative_path="ManualShippingSpec.xlsx",
            file_type=".xlsx",
            sheet="ManualSupplyLine",
            text="ManualShipping_ExistingLineAuto_InboundDownload Item_Code Item_Rev Sup_Line Process_Id Oricon_Id ContainerName kdcRenameShipChangeQty",
            preview="Staging table fields for manual supply...",
            privacy_level="local_only",
            source_hash="2",
        )
    ]

    with open(test_index, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.__dict__, ensure_ascii=False) + "\n")

    from aios_habit import mom_local_index
    monkeypatch.setattr(mom_local_index, "INDEX_FILE", test_index)

    query = "ManualShipping_ExistingLineAuto_InboundDownload Item_Code Item_Rev Sup_Line Process_Id Oricon_Id ContainerName kdcRenameShipChangeQty"
    hits = search_mom_index(query, index_path=test_index)
    assert len(hits) >= 1
    assert hits[0].chunk.source_file == "ManualShippingSpec.xlsx"
    assert hits[0].chunk.sheet == "ManualSupplyLine"
