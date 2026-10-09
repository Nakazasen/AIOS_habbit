"""Unit tests for conditional entity-based context expansion (ticket SYNTH-CONTEXT-ENTITY-HOME).

Verifies:
- Concrete entity extraction from technical queries.
- Lookaround word boundary matching with CJK text.
- Ranks 9-12 included when matching an entity; rejected when not matching.
- Disabling flag AIOS_RAG_SYNTH_CONTEXT_ENTITY_EXPAND=0 works.
- Preserves original order and citation numbering of base 8 chunks.
- General questions with no entities keep strictly base 8 chunks.
- Integration with route_workspace_chat_submission and build_evidence_pack.
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from aios_habit.rag_v2.entity_context import (
    DEFAULT_SYNTH_CONTEXT_EXPAND_MAX,
    DEFAULT_SYNTH_CONTEXT_TOPK,
    SYNTH_CONTEXT_ENTITY_EXPAND_ENV,
    extract_concrete_query_entities,
    is_synth_context_entity_expand_enabled,
    item_matches_any_entity,
    select_entity_conditional_context,
)


class TestEntityExtraction(unittest.TestCase):
    def test_extract_machine_and_error_codes(self):
        q = "Hiện tượng tại LSU Line được mô tả như thế nào trong tài liệu C7620?"
        ents = extract_concrete_query_entities(q)
        self.assertIn("C7620", ents)
        self.assertIn("LSU", ents)

    def test_extract_units_and_numbers(self):
        q = "Đường kính chùm tia beam là bao nhiêu mm và độ lệch 0.05 mm có đạt không?"
        ents = extract_concrete_query_entities(q)
        self.assertTrue(any("mm" in e for e in ents))
        self.assertIn("beam", ents)

    def test_extract_dates_and_acronyms(self):
        q = "Sau ngày bảo dưỡng khuôn 14/2, Housing màu Magenta và DMT-PMT có biểu hiện gì?"
        ents = extract_concrete_query_entities(q)
        self.assertIn("DMT-PMT", ents)
        self.assertTrue(any("14/2" in e for e in ents))
        self.assertIn("Magenta", ents)
        self.assertIn("Housing", ents)

    def test_cjk_color_and_axis_markers(self):
        q = "M軸方向の調整 và K色距離 có sai lệch không?"
        ents = extract_concrete_query_entities(q)
        self.assertIn("M", ents)
        self.assertIn("K", ents)

    def test_stopwords_filtered(self):
        q = "Data sau khi kiểm tra NG hay OK trong file này?"
        ents = extract_concrete_query_entities(q)
        self.assertNotIn("NG", ents)
        self.assertNotIn("OK", ents)
        self.assertNotIn("DATA", ents)
        self.assertNotIn("FILE", ents)

    def test_general_query_produces_empty_or_no_concrete_entities(self):
        q = "このDataから原因候補を評価する時に何を注意しますか。"
        ents = extract_concrete_query_entities(q)
        self.assertEqual(ents, ())


class TestItemMatching(unittest.TestCase):
    def test_matches_entity_with_cjk_boundary(self):
        item = {"title": "Báo cáo lỗi", "text": "Phát hiện sự cố trên dòng máy C7620中心部 trong quá trình thử nghiệm."}
        matched, ent = item_matches_any_entity(item, ("C7620",))
        self.assertTrue(matched)
        self.assertEqual(ent, "C7620")

    def test_matches_attribute_access(self):
        class FakeDoc:
            title = "Sirius 2 _ C7620_報告版 4.pptx"
            text = "Bowskew 調整治具で調整開始時に光路高さがプラス側にずれた"

        matched, ent = item_matches_any_entity(FakeDoc(), ("Bowskew", "C7620"))
        self.assertTrue(matched)
        self.assertIn(ent, {"Bowskew", "C7620"})

    def test_rejects_unrelated_item(self):
        item = {"title": "Tài liệu chung", "text": "Quy trình kiểm tra an toàn lao động đầu ca."}
        matched, ent = item_matches_any_entity(item, ("C7620", "DMT-PMT"))
        self.assertFalse(matched)
        self.assertEqual(ent, "")


class TestSelectEntityConditionalContext(unittest.TestCase):
    def setUp(self):
        self._orig_env = os.environ.get(SYNTH_CONTEXT_ENTITY_EXPAND_ENV)
        if SYNTH_CONTEXT_ENTITY_EXPAND_ENV in os.environ:
            del os.environ[SYNTH_CONTEXT_ENTITY_EXPAND_ENV]

    def tearDown(self):
        if self._orig_env is not None:
            os.environ[SYNTH_CONTEXT_ENTITY_EXPAND_ENV] = self._orig_env
        elif SYNTH_CONTEXT_ENTITY_EXPAND_ENV in os.environ:
            del os.environ[SYNTH_CONTEXT_ENTITY_EXPAND_ENV]

    def _make_dummy_items(self, count: int = 15) -> list[dict]:
        return [
            {
                "title": f"Doc {i}",
                "text": f"Nội dung chung của mảnh số {i}.",
                "source_id": f"src_{i}",
            }
            for i in range(1, count + 1)
        ]

    def test_includes_matching_ranks_9_to_12(self):
        items = self._make_dummy_items(15)
        # Rank 11 (index 10) matches target entity C7620 (like Q0701)
        items[10]["text"] = "Sirius 2 _ C7620_報告版: Bowskew 調整治具で調整開始時に光路高さがプラス側へずれた"

        selected, telem = select_entity_conditional_context(
            question="Hiện tượng tại LSU Line được mô tả như thế nào trong C7620?",
            evidence_items=items,
            base_topk=8,
            max_expand_topk=12,
        )

        # 8 base chunks + 1 expanded chunk (rank 11) = 9 chunks total
        self.assertEqual(len(selected), 9)
        self.assertTrue(telem["expanded"])
        self.assertEqual(telem["base_count"], 8)
        self.assertEqual(telem["total_selected"], 9)
        self.assertEqual(telem["expanded_indices"], [10])
        self.assertIn("C7620", telem["matched_entities"])

        # Base 8 order is strictly preserved
        for i in range(8):
            self.assertEqual(selected[i]["title"], f"Doc {i+1}")
        # Expanded chunk is appended at position 8 (9th item)
        self.assertEqual(selected[8]["title"], "Doc 11")

    def test_rejects_non_matching_ranks_9_to_12(self):
        items = self._make_dummy_items(15)
        # None of items 9..12 have entities for C7620
        selected, telem = select_entity_conditional_context(
            question="Hiện tượng tại LSU Line được mô tả như thế nào trong C7620?",
            evidence_items=items,
            base_topk=8,
            max_expand_topk=12,
        )

        self.assertEqual(len(selected), 8)
        self.assertFalse(telem["expanded"])
        self.assertEqual(telem["total_selected"], 8)
        self.assertEqual(telem["expanded_indices"], [])

    def test_disabled_by_environment_flag(self):
        os.environ[SYNTH_CONTEXT_ENTITY_EXPAND_ENV] = "0"
        items = self._make_dummy_items(15)
        items[10]["text"] = "C7620 Bowskew error"

        selected, telem = select_entity_conditional_context(
            question="Hiện tượng C7620?",
            evidence_items=items,
            base_topk=8,
            max_expand_topk=12,
        )

        self.assertEqual(len(selected), 8)
        self.assertFalse(telem["enabled"])
        self.assertFalse(telem["expanded"])

    def test_general_query_with_no_entities_keeps_base_eight(self):
        items = self._make_dummy_items(15)
        items[9]["text"] = "Một số lưu ý quan trọng"

        selected, telem = select_entity_conditional_context(
            question="このDataから原因候補を評価する時に何を注意しますか。",
            evidence_items=items,
            base_topk=8,
            max_expand_topk=12,
        )

        self.assertEqual(len(selected), 8)
        self.assertFalse(telem["expanded"])
        self.assertEqual(telem["entities_found"], [])


class TestBridgeAndEvidencePackIntegration(unittest.TestCase):
    def test_bridge_route_includes_entity_telemetry_in_badge(self):
        from aios_habit.antigravity_bridge import (
            AntigravityHealthStatus,
            FSM_DIRECT_READY,
            route_workspace_chat_submission,
        )

        fake_health = AntigravityHealthStatus(
            status=FSM_DIRECT_READY,
            mode="direct",
        )

        items = [
            {"title": f"Source {i}", "text": f"Nội dung mảnh {i}", "source_id": f"src_{i}"}
            for i in range(1, 15)
        ]
        # Make rank 10 have entity C7620
        items[9]["text"] = "Dòng máy C7620 gặp lỗi điều chỉnh quang học."

        with patch("aios_habit.antigravity_bridge.call_antigravity_bridge") as mock_call, \
             patch("aios_habit.antigravity_bridge._get_or_create_user_message") as mock_user_msg, \
             patch("aios_habit.workspace_chat_store.load_conversation", return_value=None), \
             patch("aios_habit.workspace_chat_store.load_conversation_source_selections", return_value=[]), \
             patch("aios_habit.workspace_chat_store.save_message"), \
             patch("aios_habit.workspace_chat_store.save_evidence_trace"):

            mock_call.return_value = MagicMock(ok=True, answer_text="Đã tìm thấy [1] [9]")
            mock_user_msg.return_value = MagicMock(id="MSG-1")

            ok, msg, badge, err = route_workspace_chat_submission(
                question="Lỗi của máy C7620 là gì?",
                evidence_items=items,
                packed_sources=(),
                conversation_id="conv-test",
                notebook_id="nb-test",
                retrieval_applied=True,
                retrieved_sources=(),
                retrieval_summary="summary",
                current_keys=(),
                chat_history=(),
                user_raw_input="Lỗi của máy C7620 là gì?",
                health_status=fake_health,
            )

            self.assertTrue(ok)
            self.assertIsNotNone(badge)
            self.assertIn("entity_conditional_expand", badge)
            telem = badge["entity_conditional_expand"]
            self.assertTrue(telem["expanded"])
            self.assertEqual(telem["total_selected"], 9)
            self.assertIn(9, telem["expanded_indices"])

            # Verify prompt context had 9 sources (original 8 + expanded rank 10)
            context_arg = mock_call.call_args[1].get("context_text", "")
            self.assertIn("[1] Source 1:", context_arg)
            self.assertIn("[8] Source 8:", context_arg)
            self.assertIn("[9] Source 10:", context_arg)
            self.assertNotIn("[10] Source 11:", context_arg)


class TestEvidencePackEntityExpand(unittest.TestCase):
    def test_build_evidence_pack_conditional_expansion(self):
        from aios_habit.rag_v2.evidence import EvidencePackConfig, build_evidence_pack
        from aios_habit.rag_v2.index import SearchResponse, SearchResult, SearchSummary

        def make_res(i: int, text: str = "") -> SearchResult:
            return SearchResult(
                chunk_id=f"chk_{i}",
                document_id=f"doc_{i}",
                source_name=f"file_{i}.txt",
                source_path=f"/path/{i}.txt",
                file_type="txt",
                metadata={},
                text=text or f"Nội dung của chunk {i}",
                score=10.0 - (i * 0.5),
                matched_terms=("test",),
                term_coverage=0.8,
                privacy_labels=(),
            )

        results = [make_res(i) for i in range(1, 16)]
        # Put entity into candidate rank 11
        results[10] = make_res(11, text="Tài liệu Sirius 2 _ C7620_報告版 4 lỗi quang học")

        summary = SearchSummary(
            query="Chi tiết lỗi C7620",
            indexed_chunk_count=15,
            eligible_chunk_count=15,
            candidate_count=15,
            returned_count=15,
            evidence_set_term_coverage=0.9,
            planned_facet_ids=(),
            planned_obligation_ids=(),
        )
        resp = SearchResponse(results=tuple(results), summary=summary)

        # Case 1: default with max_items=8, expand enabled -> 9 items (rank 11 added)
        cfg = EvidencePackConfig(max_items=8, max_expand_items=12)
        pack = build_evidence_pack("Chi tiết lỗi C7620", resp, config=cfg)
        self.assertEqual(len(pack.items), 9)
        self.assertIsNotNone(pack.entity_expand_telemetry)
        self.assertTrue(pack.entity_expand_telemetry["expanded"])
        self.assertIn("C7620", pack.entity_expand_telemetry["matched_entities"])
        self.assertEqual(pack.items[8].chunk_id, "chk_11")

        # Case 2: explicit conditional_entity_expand=False -> exactly 8 items
        cfg_off = EvidencePackConfig(max_items=8, conditional_entity_expand=False)
        pack_off = build_evidence_pack("Chi tiết lỗi C7620", resp, config=cfg_off)
        self.assertEqual(len(pack_off.items), 8)
        self.assertFalse(pack_off.entity_expand_telemetry["expanded"])


if __name__ == "__main__":
    unittest.main()
