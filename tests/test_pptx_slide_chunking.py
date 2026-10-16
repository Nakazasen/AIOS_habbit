"""Unit tests for Whole-slide PowerPoint chunking.

Ticket requirement:
(ii) Đảm bảo toàn văn của một slide PowerPoint nằm trọn trong một đoạn, không cắt giữa slide.
Q0706: slide 8 (chứa số liệu 0.7mm và 3/517) không bị cắt ngang giữa chừng.
"""
from pathlib import Path
import pptx
from pptx.util import Inches
import pytest

from aios_habit.rag_v2.adapters import ConversionContext
from aios_habit.rag_v2.converters import PowerPointDocumentConverterAdapter
from aios_habit.rag_v2.chunking import StructureAwareChunker


def test_pptx_whole_slide_chunking(tmp_path: Path):
    """Create a PPTX with multiple slides, including a long slide, and verify whole-slide chunks."""
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Short slide
    slide1 = prs.slides.add_slide(blank_layout)
    txBox1 = slide1.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(2))
    tf1 = txBox1.text_frame
    tf1.text = "Slide 1: Overview and Introduction"

    # Slide 2: Long slide (> 600 characters) with multiple items
    slide2 = prs.slides.add_slide(blank_layout)
    txBox2 = slide2.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(5))
    tf2 = txBox2.text_frame
    tf2.text = "Slide 2: Detailed Defect Analysis & Verification Results"
    
    p1 = tf2.add_paragraph()
    p1.text = "① 隙間不良（レンズと鏡筒のクリアランス）: 測定数 100点、NG数 0点。すべてのサンプルで規格内であることを確認した。"
    
    p2 = tf2.add_paragraph()
    p2.text = "② 傾き不良（チルト角の偏差）: 設計許容値 0.05度に対し、最大値 0.03度、平均値 0.015度で安定して推移している。"
    
    p3 = tf2.add_paragraph()
    p3.text = "③ 倒れ量不良（ブラケット倒れ基準）: 規格 0.7mm 以下に対し、実力 3/517 - 0.58% NG が発生しており、調整工程の改善が必須である。"

    # Slide 3: Conclusion slide
    slide3 = prs.slides.add_slide(blank_layout)
    txBox3 = slide3.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(2))
    tf3 = txBox3.text_frame
    tf3.text = "Slide 3: Next Actions and Summary"

    pptx_path = tmp_path / "test_presentation.pptx"
    prs.save(pptx_path)

    # 1. Convert using PowerPointDocumentConverterAdapter
    adapter = PowerPointDocumentConverterAdapter()
    context = ConversionContext(document_id="doc-test-pptx")
    elements = adapter.convert(pptx_path, context)

    # Must produce exactly 3 DocumentElements (1 per slide)
    assert len(elements) == 3, f"Expected 3 elements (1 per slide), got {len(elements)}"
    assert elements[0].slide == 1
    assert elements[1].slide == 2
    assert elements[2].slide == 3

    # Check Slide 2 content
    slide2_elem = elements[1]
    assert "0.7mm" in slide2_elem.text
    assert "3/517" in slide2_elem.text

    # 2. Chunk using StructureAwareChunker
    chunker = StructureAwareChunker()
    chunks = chunker.chunk_elements(elements)

    # Verify each slide produces exactly one retrievable chunk without mid-slide splitting
    # (plus 1 automatic document architecture summary chunk)
    retrievable_chunks = [c for c in chunks if c.retrievable]
    slide_chunks = [c for c in retrievable_chunks if not c.metadata.get("is_document_summary")]
    assert len(slide_chunks) == 3, (
        f"Expected exactly 3 whole-slide chunks (1 per slide), got {len(slide_chunks)}"
    )

    slide2_chunk = slide_chunks[1]
    assert slide2_chunk.slide_range == (2, 2)
    # Entire slide text must be whole in this single chunk
    assert "Detailed Defect Analysis" in slide2_chunk.text
    assert "0.7mm" in slide2_chunk.text
    assert "3/517" in slide2_chunk.text
    assert "0.58% NG" in slide2_chunk.text
    assert len(slide2_chunk.text) > 200, "Slide 2 text must be whole without cutoff"
