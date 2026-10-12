"""Regression tests for knowledge block selector and adapter tong_hop inclusion.

Ticket: DESKTOP-BLOCK-SELECTOR-TONGHOP-FIX-HOME
Requirements:
1. Selector block choices in workspace_chat_app.py matches domain_document_map.json (4/4 blocks + auto).
2. Document counts are dynamic and match actual domain map counts (auto 894, lsu 99, dieu_tra_loi 679, mom 44, tong_hop 72).
3. Legacy blocks order and labels are preserved across locales (vi, ja, zh-CN).
4. RAG V2 adapter accepts forced_domain for every block in domain_document_map.
5. Invalid/unwhitelisted blocks are safely rejected.
6. Sidebar shared block status covers all 4 blocks.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from aios_habit.index_domain import (
    DOMAIN_DIEU_TRA_LOI,
    DOMAIN_LSU,
    DOMAIN_MOM,
    DOMAIN_TONG_HOP,
    KNOWLEDGE_BLOCKS,
    get_domain_counts,
    get_domain_document_ids,
    load_domain_document_map,
)
from aios_habit.workspace_chat_app import get_workspace_chat_block_choices
from aios_habit.workspace_chat_rag_v2_adapter import (
    WorkspaceChatRagV2CanaryConfig,
    _select_domain_route,
    workspace_chat_domain_block_status,
)


def test_block_choices_covers_all_domain_document_map_blocks():
    """Selector choices set (excluding 'auto') must strictly equal domain map block set."""
    doc_map = load_domain_document_map()
    expected_blocks = set(doc_map.values())
    assert expected_blocks == {"lsu", "dieu_tra_loi", "mom", "tong_hop"}

    choices = get_workspace_chat_block_choices("vi")
    selector_blocks = set(choices.keys()) - {"auto"}

    assert selector_blocks == expected_blocks, (
        f"Block selector choices mismatch: {selector_blocks} != {expected_blocks}"
    )


def test_block_counts_dynamic_and_accurate():
    """Document counts must reflect actual numbers from domain_document_map."""
    counts = get_domain_counts()
    assert counts["auto"] == 894
    assert counts[DOMAIN_LSU] == 99
    assert counts[DOMAIN_DIEU_TRA_LOI] == 679
    assert counts[DOMAIN_MOM] == 44
    assert counts[DOMAIN_TONG_HOP] == 72


def test_block_order_and_multilingual_labels_preserved():
    """Block ordering must keep auto, lsu, dieu_tra_loi, mom, tong_hop with proper labels."""
    expected_order = ["auto", DOMAIN_LSU, DOMAIN_DIEU_TRA_LOI, DOMAIN_MOM, DOMAIN_TONG_HOP]

    # Vietnamese
    vi_choices = get_workspace_chat_block_choices("vi")
    assert list(vi_choices.keys()) == expected_order
    assert vi_choices["auto"] == "Tự động (894 tài liệu)"
    assert vi_choices[DOMAIN_LSU] == "LSU (99 tài liệu)"
    assert vi_choices[DOMAIN_DIEU_TRA_LOI] == "Điều tra lỗi (679 tài liệu)"
    assert vi_choices[DOMAIN_MOM] == "MOM (44 tài liệu)"
    assert vi_choices[DOMAIN_TONG_HOP] == "Tổng hợp (72 tài liệu)"

    # Japanese
    ja_choices = get_workspace_chat_block_choices("ja")
    assert list(ja_choices.keys()) == expected_order
    assert ja_choices["auto"] == "自動 (894 件)"
    assert ja_choices[DOMAIN_LSU] == "LSU (99 件)"
    assert ja_choices[DOMAIN_DIEU_TRA_LOI] == "エラー調査 (679 件)"
    assert ja_choices[DOMAIN_MOM] == "MOM (44 件)"
    assert ja_choices[DOMAIN_TONG_HOP] == "総合 (72 件)"

    # Chinese
    zh_choices = get_workspace_chat_block_choices("zh-CN")
    assert list(zh_choices.keys()) == expected_order
    assert zh_choices["auto"] == "自动 (894 份)"
    assert zh_choices[DOMAIN_LSU] == "LSU (99 份)"
    assert zh_choices[DOMAIN_DIEU_TRA_LOI] == "故障调查 (679 份)"
    assert zh_choices[DOMAIN_MOM] == "MOM (44 份)"
    assert zh_choices[DOMAIN_TONG_HOP] == "综合 (72 份)"


def test_adapter_accepts_all_blocks_in_domain_document_map(monkeypatch):
    """Adapter must accept queries for each block in the domain document map."""
    from aios_habit import workspace_chat_rag_v2_adapter as adapter

    monkeypatch.setattr(adapter, "_collection_id_for_sources", lambda sources: "tri_thuc")
    # Simulate on-disk collection readiness
    monkeypatch.setattr(
        adapter,
        "_domain_index_ready",
        lambda config, cid: cid in {"lsu", "dieu_tra_loi", "mom", "tong_hop", "tri_thuc"},
    )

    doc_map = load_domain_document_map()
    all_blocks = set(doc_map.values())

    for block in all_blocks:
        route = _select_domain_route(
            question="truy vấn kiểm tra khối",
            sources=(),
            config=None,
            forced_domain=block,
        )
        assert route is not None, f"Adapter rejected forced domain: {block}"
        assert route.applied is True
        assert route.domain == block
        assert route.detected is not None
        assert route.detected.domain == block
        assert route.detected.confidence == 1.0


def test_adapter_unified_index_fallback_routes_all_blocks(monkeypatch):
    """When standalone block index is missing but unified tri_thuc index exists, adapter filters via index."""
    from aios_habit import workspace_chat_rag_v2_adapter as adapter

    monkeypatch.setattr(adapter, "_collection_id_for_sources", lambda sources: "tri_thuc")
    # Standalone block dbs not ready, but base tri_thuc is ready
    monkeypatch.setattr(
        adapter,
        "_domain_index_ready",
        lambda config, cid: cid == "tri_thuc",
    )

    for block in KNOWLEDGE_BLOCKS:
        route = _select_domain_route(
            question="truy vấn kiểm tra chỉ mục hợp nhất",
            sources=(),
            config=None,
            forced_domain=block,
        )
        assert route is not None
        assert route.applied is True
        assert route.collection_id == "tri_thuc"
        assert route.domain == block
        assert "lọc qua chỉ mục" in route.note


def test_adapter_rejects_unwhitelisted_blocks(monkeypatch):
    """Adapter must reject arbitrary unwhitelisted forced_domain strings."""
    from aios_habit import workspace_chat_rag_v2_adapter as adapter

    monkeypatch.setattr(adapter, "_collection_id_for_sources", lambda sources: "tri_thuc")
    monkeypatch.setattr(adapter, "_domain_index_ready", lambda config, cid: True)

    assert _select_domain_route("q", (), None, forced_domain="invalid_block") is None
    assert _select_domain_route("q", (), None, forced_domain="hack_domain") is None
    assert _select_domain_route("q", (), None, forced_domain="12345") is None


def test_tong_hop_document_ids_strictly_match_map():
    """get_domain_document_ids('tong_hop') must return exactly the 72 documents in the map."""
    doc_map = load_domain_document_map()
    expected_tong_hop_ids = tuple(sorted(doc_id for doc_id, dom in doc_map.items() if dom == "tong_hop"))
    assert len(expected_tong_hop_ids) == 72

    retrieved_ids = get_domain_document_ids("tong_hop")
    assert retrieved_ids == expected_tong_hop_ids


def test_sidebar_shared_blocks_status_includes_all_four_blocks():
    """Sidebar shared blocks status helper must report all 4 knowledge blocks."""
    blocks = workspace_chat_domain_block_status()
    domains_reported = [b["domain"] for b in blocks]
    assert domains_reported == [DOMAIN_LSU, DOMAIN_DIEU_TRA_LOI, DOMAIN_MOM, DOMAIN_TONG_HOP]

    tong_hop_entry = next(b for b in blocks if b["domain"] == "tong_hop")
    assert tong_hop_entry["display"] == "Tổng hợp"
    assert "ready" in tong_hop_entry
    assert "size_bytes" in tong_hop_entry


def test_legacy_three_blocks_behavior_unchanged(monkeypatch):
    """Behavior of lsu, dieu_tra_loi, and mom must remain completely unchanged."""
    from aios_habit import workspace_chat_rag_v2_adapter as adapter

    monkeypatch.setattr(adapter, "_collection_id_for_sources", lambda sources: "tri_thuc")
    monkeypatch.setattr(
        adapter,
        "_domain_index_ready",
        lambda config, cid: cid in {"lsu", "dieu_tra_loi", "mom"},
    )

    for block in (DOMAIN_LSU, DOMAIN_DIEU_TRA_LOI, DOMAIN_MOM):
        route = _select_domain_route("hỏi LSU/lỗi/MOM", (), None, forced_domain=block)
        assert route is not None
        assert route.applied is True
        assert route.domain == block
        assert route.collection_id == block
