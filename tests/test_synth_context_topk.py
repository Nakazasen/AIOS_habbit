"""Unit tests for configurable synthesis context top-k (ticket SYNTH-CONTEXT-TOPK-PC0575)."""

import os
import unittest
from unittest.mock import MagicMock, patch

from aios_habit.antigravity_bridge import (
    DEFAULT_SYNTH_CONTEXT_TOPK,
    SYNTH_CONTEXT_TOPK_ENV,
    get_synth_context_topk,
)


class TestSynthContextTopkConfig(unittest.TestCase):
    def setUp(self):
        self._orig_env = os.environ.get(SYNTH_CONTEXT_TOPK_ENV)
        if SYNTH_CONTEXT_TOPK_ENV in os.environ:
            del os.environ[SYNTH_CONTEXT_TOPK_ENV]

    def tearDown(self):
        if self._orig_env is not None:
            os.environ[SYNTH_CONTEXT_TOPK_ENV] = self._orig_env
        elif SYNTH_CONTEXT_TOPK_ENV in os.environ:
            del os.environ[SYNTH_CONTEXT_TOPK_ENV]

    def test_default_is_eight(self):
        self.assertEqual(get_synth_context_topk(), 8)
        self.assertEqual(DEFAULT_SYNTH_CONTEXT_TOPK, 8)

    def test_configured_via_env(self):
        os.environ[SYNTH_CONTEXT_TOPK_ENV] = "12"
        self.assertEqual(get_synth_context_topk(), 12)

    def test_invalid_env_falls_back_to_default(self):
        os.environ[SYNTH_CONTEXT_TOPK_ENV] = "not_a_number"
        self.assertEqual(get_synth_context_topk(), 8)

        os.environ[SYNTH_CONTEXT_TOPK_ENV] = ""
        self.assertEqual(get_synth_context_topk(), 8)

    def test_bounds_protection(self):
        os.environ[SYNTH_CONTEXT_TOPK_ENV] = "0"
        self.assertEqual(get_synth_context_topk(), 1)

        os.environ[SYNTH_CONTEXT_TOPK_ENV] = "-5"
        self.assertEqual(get_synth_context_topk(), 1)

        os.environ[SYNTH_CONTEXT_TOPK_ENV] = "100"
        self.assertEqual(get_synth_context_topk(), 50)


class TestBridgeContextCapping(unittest.TestCase):
    @patch.dict(os.environ, {SYNTH_CONTEXT_TOPK_ENV: "12"})
    def test_route_workspace_chat_submission_caps_context_to_topk(self):
        from aios_habit.antigravity_bridge import route_workspace_chat_submission, AntigravityHealthStatus, FSM_DIRECT_READY

        fake_health = AntigravityHealthStatus(
            status=FSM_DIRECT_READY,
            mode="direct",
        )

        evidence_items = [
            {"title": f"Source {i}", "text": f"Chunk text {i}", "source_id": f"src_{i}"}
            for i in range(1, 20)  # 19 items
        ]

        with patch("aios_habit.antigravity_bridge.call_antigravity_bridge") as mock_call, \
             patch("aios_habit.antigravity_bridge._get_or_create_user_message") as mock_user_msg, \
             patch("aios_habit.workspace_chat_store.load_conversation", return_value=None), \
             patch("aios_habit.workspace_chat_store.load_conversation_source_selections", return_value=[]), \
             patch("aios_habit.workspace_chat_store.save_message"), \
             patch("aios_habit.workspace_chat_store.save_evidence_trace"):
            
            mock_call.return_value = MagicMock(ok=True, answer_text="Câu trả lời mẫu [1]")
            mock_user_msg.return_value = MagicMock(id="MSG-1")

            ok, msg, badge, err = route_workspace_chat_submission(
                question="Câu hỏi thử nghiệm",
                evidence_items=evidence_items,
                packed_sources=(),
                conversation_id="conv-1",
                notebook_id="nb-1",
                retrieval_applied=True,
                retrieved_sources=(),
                retrieval_summary="summary",
                current_keys=(),
                chat_history=(),
                user_raw_input="Câu hỏi thử nghiệm",
                health_status=fake_health,
            )

            self.assertTrue(ok)
            mock_call.assert_called_once()
            called_context = mock_call.call_args[1].get("context_text", "")
            # With topk=12, only sources 1..12 should be included
            self.assertIn("[1] Source 1:", called_context)
            self.assertIn("[12] Source 12:", called_context)
            self.assertNotIn("[13] Source 13:", called_context)


if __name__ == "__main__":
    unittest.main()
