"""Tests for DESKTOP-CJK-EXPAND-BRIDGE-FUSE-FIX-HOME.

Verifies:
1. Timeout reduction for CJK query expansion preprocessing step (target 5-8s, default 6s).
2. Bridge fuse (_BRIDGE_UNAVAILABLE_UNTIL) coverage across all 3 failure branches:
   - Branch 1: Health check not ready (is_direct_ready = False)
   - Branch 2: Expand call raises an exception
   - Branch 3: Expand call returns failure/None without raising exception (fixed!)
3. Healthy path: expansion succeeds and leaves the fuse open.
4. Subsequent turn behavior: immediately bypassed when the fuse is tripped (<1ms).
"""
import time
from typing import Tuple
from unittest.mock import MagicMock, patch

import pytest

from aios_habit.rag_v2.multilingual_query_expand import (
    DEFAULT_CJK_EXPAND_TIMEOUT_SECONDS,
    expand_question_for_corpus_script,
    get_cjk_expand_timeout_seconds,
)
from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
import aios_habit.workspace_chat_rag_v2_adapter as adapter


def _make_cjk_sources(count: int = 10) -> Tuple[WorkspaceAIContextSource, ...]:
    return tuple(
        WorkspaceAIContextSource(
            source_id=f"cjk-{index}",
            source_scope="notebook",
            source_type="xlsx",
            title=f"生産管理システム完工マニュアル_{index}.xlsx",
            privacy_label="local_only",
            text="完工登録の手順、生産計画と実績の照合、ロット番号の入力と確定処理。",
            included_chars=60,
            truncated=False,
        )
        for index in range(count)
    )


@pytest.fixture(autouse=True)
def _reset_fuse():
    """Ensure bridge fuse is reset before and after each test."""
    adapter._reset_cjk_bridge_fuse()
    yield
    adapter._reset_cjk_bridge_fuse()


def test_cjk_expand_default_timeout_is_within_target_window(monkeypatch):
    """(b) Timeout of preprocessing expansion must be reduced to 5-8s (default 6s)."""
    assert 5 <= DEFAULT_CJK_EXPAND_TIMEOUT_SECONDS <= 8
    assert DEFAULT_CJK_EXPAND_TIMEOUT_SECONDS == 6
    assert get_cjk_expand_timeout_seconds() == 6

    # Test override via environment variable
    monkeypatch.setenv("AIOS_CJK_EXPAND_TIMEOUT_SECONDS", "7")
    assert get_cjk_expand_timeout_seconds() == 7

    monkeypatch.setenv("AIOS_CJK_EXPAND_TIMEOUT_SECONDS", "invalid")
    assert get_cjk_expand_timeout_seconds() == 6


def test_expand_question_for_corpus_script_passes_reduced_timeout():
    """Verify expand_question_for_corpus_script forwards the 6s timeout to bridge."""
    with patch("aios_habit.antigravity_bridge.call_antigravity_bridge") as mock_bridge:
        mock_bridge.return_value = MagicMock(ok=False)

        expand_question_for_corpus_script(
            "How to register production completion?",
            corpus_script="cjk",
            gemini_ready=True,
        )

        assert mock_bridge.called
        kwargs = mock_bridge.call_args.kwargs
        assert kwargs.get("timeout_seconds") == 6


def test_cjk_expand_bridge_fuse_branch1_health_not_ready():
    """Branch 1: When health check reports bridge not ready, set fuse and skip next turn."""
    sources = _make_cjk_sources(10)
    question = "How to register production completion?"

    mock_health = MagicMock()
    mock_health.is_direct_ready = False

    with patch(
        "aios_habit.antigravity_bridge.get_antigravity_bridge_health",
        return_value=mock_health,
    ) as mock_get_health, patch(
        "aios_habit.workspace_chat_rag_v2_adapter.expand_question_for_corpus_script"
    ) as mock_expand:
        # Turn 1: Health check fails
        t_start = time.monotonic()
        res1 = adapter._maybe_expand_latin_query_for_cjk_corpus(question, sources)
        assert res1 is None
        assert mock_get_health.call_count == 1
        assert mock_expand.call_count == 0

        # Verify fuse is set for ~10 seconds
        assert adapter._BRIDGE_UNAVAILABLE_UNTIL > t_start
        assert adapter._BRIDGE_UNAVAILABLE_UNTIL <= t_start + 11.0

        # Turn 2: Subsequent call within cooldown skips immediately without checking health
        res2 = adapter._maybe_expand_latin_query_for_cjk_corpus(question, sources)
        assert res2 is None
        assert mock_get_health.call_count == 1  # Still 1, NOT called again
        assert mock_expand.call_count == 0


def test_cjk_expand_bridge_fuse_branch2_expand_raises_exception():
    """Branch 2: When expand call raises an exception, catch, set fuse and skip next turn."""
    sources = _make_cjk_sources(10)
    question = "How to register production completion?"

    mock_health = MagicMock()
    mock_health.is_direct_ready = True

    with patch(
        "aios_habit.antigravity_bridge.get_antigravity_bridge_health",
        return_value=mock_health,
    ) as mock_get_health, patch(
        "aios_habit.workspace_chat_rag_v2_adapter.expand_question_for_corpus_script",
        side_effect=RuntimeError("Simulated bridge socket failure"),
    ) as mock_expand:
        # Turn 1: Expand raises exception
        t_start = time.monotonic()
        res1 = adapter._maybe_expand_latin_query_for_cjk_corpus(question, sources)
        assert res1 is None
        assert mock_get_health.call_count == 1
        assert mock_expand.call_count == 1

        # Verify fuse is set for ~10 seconds
        assert adapter._BRIDGE_UNAVAILABLE_UNTIL > t_start
        assert adapter._BRIDGE_UNAVAILABLE_UNTIL <= t_start + 11.0

        # Turn 2: Subsequent call within cooldown skips immediately
        res2 = adapter._maybe_expand_latin_query_for_cjk_corpus(question, sources)
        assert res2 is None
        assert mock_get_health.call_count == 1  # Skipped
        assert mock_expand.call_count == 1  # Skipped


def test_cjk_expand_bridge_fuse_branch3_expand_returns_failure_no_exception():
    """Branch 3: When expand call returns None/failure without raising exception (THE BUG FIX).

    Previously, if the bridge was blocked or timed out, call_antigravity_bridge
    returned ok=False (no exception raised). expand_question_for_corpus_script
    returned None, and _maybe_expand_latin_query_for_cjk_corpus returned None
    WITHOUT setting the fuse, causing repeat timeouts on subsequent calls.
    With the fix, the fuse MUST be set!
    """
    sources = _make_cjk_sources(10)
    question = "How to register production completion?"

    mock_health = MagicMock()
    mock_health.is_direct_ready = True

    with patch(
        "aios_habit.antigravity_bridge.get_antigravity_bridge_health",
        return_value=mock_health,
    ) as mock_get_health, patch(
        "aios_habit.workspace_chat_rag_v2_adapter.expand_question_for_corpus_script",
        return_value=None,  # Returns None on failure without exception
    ) as mock_expand:
        # Turn 1: Expand returns failure (None)
        t_start = time.monotonic()
        res1 = adapter._maybe_expand_latin_query_for_cjk_corpus(question, sources)
        assert res1 is None
        assert mock_get_health.call_count == 1
        assert mock_expand.call_count == 1

        # CRITICAL ASSERTION: The fuse MUST be set!
        assert adapter._BRIDGE_UNAVAILABLE_UNTIL > t_start
        assert adapter._BRIDGE_UNAVAILABLE_UNTIL <= t_start + 11.0

        # Turn 2: Subsequent call within cooldown skips immediately (< 1ms)
        t2_start = time.monotonic()
        res2 = adapter._maybe_expand_latin_query_for_cjk_corpus(question, sources)
        t2_elapsed = time.monotonic() - t2_start

        assert res2 is None
        assert mock_get_health.call_count == 1  # Did NOT call health again
        assert mock_expand.call_count == 1  # Did NOT call expand again
        assert t2_elapsed < 0.05  # Instant return


def test_cjk_expand_bridge_fuse_branch3_empty_variants_payload():
    """Branch 3 variant: Expand returns empty variants mapping."""
    sources = _make_cjk_sources(10)
    question = "How to register production completion?"

    mock_health = MagicMock()
    mock_health.is_direct_ready = True

    with patch(
        "aios_habit.antigravity_bridge.get_antigravity_bridge_health",
        return_value=mock_health,
    ), patch(
        "aios_habit.workspace_chat_rag_v2_adapter.expand_question_for_corpus_script",
        return_value={"variants": []},
    ):
        t_start = time.monotonic()
        res = adapter._maybe_expand_latin_query_for_cjk_corpus(question, sources)
        assert res is None
        assert adapter._BRIDGE_UNAVAILABLE_UNTIL > t_start


def test_cjk_expand_healthy_path_preserves_expansion_and_leaves_fuse_open():
    """When bridge is healthy and returns valid variants, return payload and leave fuse open."""
    sources = _make_cjk_sources(10)
    question = "How to register production completion?"

    expected_payload = {
        "variants": [
            {"text": "生産完了 登録 手順", "language_hint": "ja", "origin": "expansion"}
        ]
    }

    mock_health = MagicMock()
    mock_health.is_direct_ready = True

    with patch(
        "aios_habit.antigravity_bridge.get_antigravity_bridge_health",
        return_value=mock_health,
    ), patch(
        "aios_habit.workspace_chat_rag_v2_adapter.expand_question_for_corpus_script",
        return_value=expected_payload,
    ):
        res = adapter._maybe_expand_latin_query_for_cjk_corpus(question, sources)
        assert res == expected_payload
        # Fuse must NOT be set
        assert adapter._BRIDGE_UNAVAILABLE_UNTIL == 0.0
