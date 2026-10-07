"""Unit and regression tests for Entity Matching Boost and Diversity Capping in RAG v2."""
from __future__ import annotations

import logging
from pathlib import Path
import sqlite3
import tempfile
import pytest

from aios_habit.rag_v2.index import (
    LocalChunkIndex,
    SearchOptions,
    SearchResult,
    _compute_entity_boost,
    _extract_query_entities,
    _select_hybrid_results,
    MAX_ENTITY_BOOST,
)
from aios_habit.rag_v2.query_planning import RetrievalQueryPlan, coerce_query_plan


def test_extract_query_entities_group_a_patterns() -> None:
    """Kiểm tra nhận diện đúng các thực thể nhóm A theo đặc tả vé."""
    # Mã lỗi chuyên biệt
    ents_c7620 = _extract_query_entities("Lỗi C7620 tại line Magenta")
    assert any("C7620" in e for e in ents_c7620)

    # Tên chuyên đề / đồ gá
    ents_sirius = _extract_query_entities("Báo cáo Sirius 2 về hiện tượng lệch màu")
    assert any("Sirius" in e for e in ents_sirius)

    ents_jig = _extract_query_entities("Kiểm tra tương quan trên Jig Bow_Skew 1035")
    assert any("1035" in e for e in ents_jig) or any("Bow_Skew" in e for e in ents_jig)

    ents_part = _extract_query_entities("Bản vẽ MOUNT LD BLOCK số 3V2ND19040")
    assert any("3V2ND19040" in e for e in ents_part)
    assert any("MOUNT" in e for e in ents_part)

    ents_okng = _extract_query_entities("Dữ liệu OKNGUNIT của CO BRACKET")
    assert any("OKNGUNIT" in e for e in ents_okng)

    ents_camera = _extract_query_entities("Hiện tượng tại Camera 140")
    assert any("Camera" in e for e in ents_camera)

    # Vị trí đo / Dung sai / Vật tư
    ents_sim = _extract_query_entities("Dán SIM tape dày 40um tại điểm 119.h2")
    assert any("SIM" in e for e in ents_sim)

    ents_g1 = _extract_query_entities("Thông số nominal g1 và g2")
    assert "g1" in [e.lower() for e in ents_g1]
    assert "g2" in [e.lower() for e in ents_g1]

    ents_ohp = _extract_query_entities("Kiểm tra tỷ lệ NG bằng tấm OHP")
    assert any("OHP" in e for e in ents_ohp)


def test_entity_boost_capped_and_proportional() -> None:
    """Kiểm tra boost thực thể có trần và không áp đảo hoàn toàn điểm gốc."""
    entities = ("C7620", "Sirius 2")
    
    # Tài liệu khớp tiêu đề
    boost_title = _compute_entity_boost(
        entities,
        source_name="Sirius 2 _ C7620_報告版 4.pptx",
        source_path="lsu/Sirius 2 _ C7620_報告版 4.pptx",
        text="Báo cáo phân tích hiện tượng C7620 tại line",
    )
    assert 0.0 < boost_title <= MAX_ENTITY_BOOST

    # Câu hỏi không có thực thể -> boost = 0.0
    boost_none = _compute_entity_boost(
        (),
        source_name="Sirius 2 _ C7620_報告版 4.pptx",
        source_path="lsu/Sirius 2 _ C7620_報告版 4.pptx",
        text="Nội dung thông thường",
    )
    assert boost_none == 0.0

    # Trần boost không bao giờ vượt MAX_ENTITY_BOOST
    many_entities = ("C7620", "Sirius 2", "1035", "MOUNT LD BLOCK", "OKNGUNIT")
    boost_many = _compute_entity_boost(
        many_entities,
        source_name="Sirius 2 C7620 1035 MOUNT LD BLOCK OKNGUNIT.pptx",
        source_path="path",
        text="prefix text with all entities",
    )
    assert boost_many <= MAX_ENTITY_BOOST


def test_diversity_capping_max_3_chunks(caplog: pytest.LogCaptureFixture) -> None:
    """Tái lập ca lấn át: tệp lớn chiếm hết top-k -> sau vá <= 3 mảnh và ghi log."""
    plan = coerce_query_plan("Tra cứu lỗi bảo hành LSU Magenta")
    
    # Giả lập 10 mảnh từ Loi KDTPS.xlsx và 2 mảnh từ Sirius 2
    candidates = []
    for i in range(10):
        candidates.append(
            SearchResult(
                chunk_id=f"kdtps_{i}",
                score=10.0 - i * 0.1,
                text=f"Lỗi nhật ký {i} từ bảng tổng hợp bảo hành",
                document_id="doc_kdtps_huge",
                source_path="lsu/Loi KDTPS.xlsx",
                source_name="Loi KDTPS.xlsx",
                file_type="xlsx",
                metadata={},
                privacy_labels=(),
                ranking_signals={},
                matched_query_variants=(),
                matched_query_variant_ids=(),
                matched_query_facets=(),
                matched_obligations=(),
            )
        )
    for i in range(3):
        candidates.append(
            SearchResult(
                chunk_id=f"sirius_{i}",
                score=8.5 - i * 0.1,
                text=f"Phân tích chuyên sâu từ slide Sirius 2 {i}",
                document_id="doc_sirius_spec",
                source_path="lsu/Sirius 2.pptx",
                source_name="Sirius 2.pptx",
                file_type="pptx",
                metadata={},
                privacy_labels=(),
                ranking_signals={},
                matched_query_variants=(),
                matched_query_variant_ids=(),
                matched_query_facets=(),
                matched_obligations=(),
            )
        )

    with caplog.at_level(logging.INFO):
        selected, rejected = _select_hybrid_results(
            candidates,
            plan,
            limit=10,
            per_document_limit=3,
            near_duplicate_threshold=0.9,
        )

    # Đảm bảo tệp Loi KDTPS.xlsx bị cap tối đa 3 mảnh
    kdtps_count = sum(1 for c in selected if c.source_name == "Loi KDTPS.xlsx")
    assert kdtps_count == 3
    assert len(rejected) > 0

    # Đảm bảo tệp Sirius 2 được vào top context nhờ giải phóng chỗ
    sirius_count = sum(1 for c in selected if c.source_name == "Sirius 2.pptx")
    assert sirius_count == 3

    # Kiểm tra log cảnh báo khi diversity cap kích hoạt
    assert any("rag_v2.diversity_cap_triggered" in record.message for record in caplog.records)


def test_no_entity_query_behavior_unchanged() -> None:
    """Khi câu hỏi không có thực thể, không thêm boost và giữ nguyên thứ tự gốc."""
    query = "Quy trình bảo dưỡng thiết bị định kỳ chung"
    entities = _extract_query_entities(query)
    # Không nhận nhầm các từ thông thường thành thực thể chuyên biệt
    assert len(entities) == 0

    boost1 = _compute_entity_boost(entities, "Tài liệu A", "path A", "text A")
    boost2 = _compute_entity_boost(entities, "Tài liệu B", "path B", "text B")
    assert boost1 == 0.0
    assert boost2 == 0.0
