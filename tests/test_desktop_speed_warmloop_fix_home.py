"""Tests for DESKTOP-SPEED-WARMLOOP-FIX-HOME.

Verifies:
1. Hard error fail-fast: consecutive hard errors (max 2) with no progress exit immediately (<1s).
2. Progress tracking: genuine worker startup progress allows continued waiting until success.
3. No-progress budget: worker without progress exits when no_progress_timeout is reached.
4. Absolute ceiling: waiting exits when absolute_timeout is reached even if worker showed progress.
5. Milestone logging: each iteration logs loop, warming_s, reason, elapsed_wait_s.
6. Preserved behaviors: cancellation interrupts wait; domain_block_missing and deep_search_unavailable
   exit immediately; draft fallback delivers promptly without 300s stall.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any
import pytest

from aios_habit.workspace_chat_app import (
    wait_for_workspace_chat_worker,
    _run_chat_turn_async,
    _is_hard_worker_error,
    _check_worker_progress,
    _is_worker_startup_reason,
)
from aios_habit.answer_draft_fallback import (
    DraftEntry,
    DRAFT_LABEL,
    clear_draft_fallback_override,
    set_draft_fallback_override,
    clear_cached_draft_entries,
)
from aios_habit.workspace_chat_models import WorkspaceConversation
from aios_habit.workspace_chat_store import (
    save_conversation,
    load_messages,
)


@pytest.fixture(autouse=True)
def _clean_state():
    clear_draft_fallback_override()
    clear_cached_draft_entries()
    yield
    clear_draft_fallback_override()
    clear_cached_draft_entries()


def test_is_hard_worker_error_detection():
    assert _is_hard_worker_error("bge_worker_init_stdout_eof") is True
    assert _is_hard_worker_error("bge_worker_init_exception") is True
    assert _is_hard_worker_error("runtimeerror") is True
    assert _is_hard_worker_error("hết giờ ống dẫn") is True
    assert _is_hard_worker_error("broken pipe") is True
    assert _is_hard_worker_error("bge_worker_init_spawn_failed") is True
    assert _is_hard_worker_error("bge_worker_model_verify_failed") is True
    assert _is_hard_worker_error("", exc=BrokenPipeError("pipe broken")) is True
    assert _is_hard_worker_error("", exc=EOFError("unexpected EOF")) is True

    # Benign or pending states are not hard errors
    assert _is_hard_worker_error("bge_worker_init_pending") is False
    assert _is_hard_worker_error("warming_pending") is False
    assert _is_hard_worker_error("") is False


def test_check_worker_progress_detection():
    prev = {"alive": False, "pid": None, "stderr_size": -1, "stderr_mtime": 0.0, "reason": "not_initialized"}
    curr_spawned = {"alive": True, "pid": 1234, "stderr_size": 0, "stderr_mtime": 0.0, "reason": "bge_worker_init_pending"}
    assert _check_worker_progress(prev, curr_spawned) is True

    # Progress on stderr write
    curr_logged = {"alive": True, "pid": 1234, "stderr_size": 256, "stderr_mtime": 10.0, "reason": "bge_worker_init_pending"}
    assert _check_worker_progress(curr_spawned, curr_logged) is True

    # No progress if stderr size and mtime unchanged
    curr_stalled = {"alive": True, "pid": 1234, "stderr_size": 256, "stderr_mtime": 10.0, "reason": "bge_worker_init_pending"}
    assert _check_worker_progress(curr_logged, curr_stalled) is False

    # Process dead -> no progress
    curr_dead = {"alive": False, "pid": None, "stderr_size": 256, "stderr_mtime": 10.0, "reason": "bge_worker_init_stdout_eof"}
    assert _check_worker_progress(curr_logged, curr_dead) is False

    # Ready -> progress
    curr_ready = {"alive": True, "pid": 1234, "ready": True, "stderr_size": 500, "stderr_mtime": 12.0, "reason": ""}
    assert _check_worker_progress(curr_logged, curr_ready) is True


def test_hard_error_fails_fast_within_two_loops():
    """Consecutive hard failures (max 2) exit immediately (<0.5s) without waiting full budget."""
    call_counts = {"warming": 0, "retrieval": 0}

    def mock_warming(blocking: bool = True, timeout_s: float = 5.0) -> bool:
        call_counts["warming"] += 1
        return False

    def mock_retrieval() -> dict[str, Any]:
        call_counts["retrieval"] += 1
        return {
            "status": "quality_search_unavailable",
            "rag_v2_canary": {"fallback_reason": "bge_worker_init_stdout_eof"},
        }

    def mock_progress() -> dict[str, Any]:
        return {
            "alive": False,
            "pid": None,
            "exit_code": 1,
            "pending": False,
            "ready": False,
            "reason": "bge_worker_init_stdout_eof",
            "stderr_size": -1,
            "stderr_mtime": 0.0,
        }

    t0 = time.monotonic()
    res, early_exit = wait_for_workspace_chat_worker(
        attempt_retrieval_fn=mock_retrieval,
        initial_ret_res={
            "status": "quality_search_unavailable",
            "rag_v2_canary": {"fallback_reason": "bge_worker_init_stdout_eof"},
        },
        warming_fn=mock_warming,
        progress_fn=mock_progress,
        no_progress_timeout=20.0,
        absolute_timeout=120.0,
        max_consecutive_hard_errors=2,
        step_timeout=1.0,
        poll_interval=0.01,
    )
    elapsed = time.monotonic() - t0

    assert early_exit is None
    assert res.get("status") == "quality_search_unavailable"
    assert call_counts["warming"] == 2
    assert elapsed < 1.0


def test_hard_error_exception_fails_fast():
    """Warming raising unhandled exception fails fast in 2 loops."""
    call_counts = {"warming": 0}

    def mock_warming(blocking: bool = True, timeout_s: float = 5.0) -> bool:
        call_counts["warming"] += 1
        raise RuntimeError("bge_worker_init_spawn_failed")

    def mock_retrieval() -> dict[str, Any]:
        return {
            "status": "quality_search_unavailable",
            "rag_v2_canary": {"fallback_reason": "runtimeerror"},
        }

    def mock_progress() -> dict[str, Any]:
        return {"alive": False, "reason": "spawn_failed"}

    t0 = time.monotonic()
    res, early_exit = wait_for_workspace_chat_worker(
        attempt_retrieval_fn=mock_retrieval,
        initial_ret_res={"status": "quality_search_unavailable"},
        warming_fn=mock_warming,
        progress_fn=mock_progress,
        no_progress_timeout=20.0,
        absolute_timeout=120.0,
        max_consecutive_hard_errors=2,
        step_timeout=1.0,
        poll_interval=0.01,
    )
    elapsed = time.monotonic() - t0

    assert early_exit is None
    assert res.get("status") == "quality_search_unavailable"
    assert call_counts["warming"] == 2
    assert elapsed < 1.0


def test_worker_progress_allows_waiting_until_success():
    """When worker shows genuine progress, wait continues until retrieval succeeds."""
    step = 0

    def mock_progress() -> dict[str, Any]:
        nonlocal step
        # Progressively larger stderr_size
        return {
            "alive": True,
            "pid": 5678,
            "pending": True,
            "ready": (step >= 3),
            "reason": "" if step >= 3 else "bge_worker_init_pending",
            "stderr_size": step * 200,
            "stderr_mtime": 1.0 + step,
        }

    def mock_warming(blocking: bool = True, timeout_s: float = 5.0) -> bool:
        nonlocal step
        step += 1
        return step >= 3

    def mock_retrieval() -> dict[str, Any]:
        if step >= 3:
            return {
                "status": "ready",
                "summary_count": 2,
                "evidence_items": [{"title": "Doc1", "text": "Content"}],
            }
        return {
            "status": "quality_search_unavailable",
            "rag_v2_canary": {"fallback_reason": "bge_worker_init_pending"},
        }

    res, early_exit = wait_for_workspace_chat_worker(
        attempt_retrieval_fn=mock_retrieval,
        initial_ret_res={"status": "quality_search_unavailable"},
        warming_fn=mock_warming,
        progress_fn=mock_progress,
        no_progress_timeout=10.0,
        absolute_timeout=30.0,
        step_timeout=0.1,
        poll_interval=0.01,
    )

    assert early_exit is None
    assert res.get("status") == "ready"
    assert res.get("summary_count") == 2


def test_worker_no_progress_timeout_exhausted():
    """Worker alive but frozen without progress exits when no_progress_timeout expires."""
    def mock_progress() -> dict[str, Any]:
        return {
            "alive": True,
            "pid": 9999,
            "pending": True,
            "ready": False,
            "reason": "bge_worker_init_pending",
            "stderr_size": 100,  # Constant size -> no progress
            "stderr_mtime": 1.0,
        }

    def mock_warming(blocking: bool = True, timeout_s: float = 5.0) -> bool:
        time.sleep(0.05)
        return False

    def mock_retrieval() -> dict[str, Any]:
        return {
            "status": "quality_search_unavailable",
            "rag_v2_canary": {"fallback_reason": "bge_worker_init_pending"},
        }

    t0 = time.monotonic()
    res, early_exit = wait_for_workspace_chat_worker(
        attempt_retrieval_fn=mock_retrieval,
        initial_ret_res={"status": "quality_search_unavailable"},
        warming_fn=mock_warming,
        progress_fn=mock_progress,
        no_progress_timeout=0.3,
        absolute_timeout=10.0,
        step_timeout=0.05,
        poll_interval=0.01,
    )
    elapsed = time.monotonic() - t0

    assert early_exit is None
    assert res.get("status") == "quality_search_unavailable"
    assert 0.25 <= elapsed <= 1.0


def test_worker_absolute_ceiling_exhausted():
    """Waiting halts when absolute ceiling is reached even if worker keeps making small progress."""
    counter = 0

    def mock_progress() -> dict[str, Any]:
        nonlocal counter
        counter += 1
        return {
            "alive": True,
            "pid": 8888,
            "pending": True,
            "ready": False,
            "reason": "bge_worker_init_pending",
            "stderr_size": counter * 10,  # Small continuous progress
            "stderr_mtime": float(counter),
        }

    def mock_warming(blocking: bool = True, timeout_s: float = 5.0) -> bool:
        time.sleep(0.05)
        return False

    def mock_retrieval() -> dict[str, Any]:
        return {
            "status": "quality_search_unavailable",
            "rag_v2_canary": {"fallback_reason": "bge_worker_init_pending"},
        }

    t0 = time.monotonic()
    res, early_exit = wait_for_workspace_chat_worker(
        attempt_retrieval_fn=mock_retrieval,
        initial_ret_res={"status": "quality_search_unavailable"},
        warming_fn=mock_warming,
        progress_fn=mock_progress,
        no_progress_timeout=2.0,
        absolute_timeout=0.3,  # Ceiling is lower
        step_timeout=0.05,
        poll_interval=0.01,
    )
    elapsed = time.monotonic() - t0

    assert early_exit is None
    assert res.get("status") == "quality_search_unavailable"
    assert 0.25 <= elapsed <= 1.0


def test_cancellation_event_stops_wait_immediately():
    """Cancellation event immediately interrupts the loop."""
    cancel_evt = threading.Event()
    cancel_evt.set()

    res, early_exit = wait_for_workspace_chat_worker(
        attempt_retrieval_fn=lambda: {"status": "quality_search_unavailable"},
        initial_ret_res={"status": "quality_search_unavailable"},
        cancellation_event=cancel_evt,
        no_progress_timeout=20.0,
        absolute_timeout=120.0,
    )

    assert early_exit is not None
    ok, succ, badge, err = early_exit
    assert ok is False
    assert err == "Đã dừng yêu cầu AI."


def test_domain_block_missing_exits_immediately():
    """When retry returns domain_block_missing, exits immediately with localized notice."""
    def mock_retrieval() -> dict[str, Any]:
        return {
            "status": "quality_search_unavailable",
            "rag_v2_canary": {"fallback_reason": "domain_block_missing"},
            "domain_routing": {"domain_display": "Khối MOM"},
        }

    res, early_exit = wait_for_workspace_chat_worker(
        attempt_retrieval_fn=mock_retrieval,
        initial_ret_res={"status": "quality_search_unavailable"},
        warming_fn=lambda **kwargs: False,
        progress_fn=lambda: {"alive": True},
        no_progress_timeout=20.0,
        absolute_timeout=120.0,
        step_timeout=0.01,
        poll_interval=0.01,
    )

    assert early_exit is not None
    ok, succ, badge, err = early_exit
    assert ok is False
    assert "Khối MOM" in err or "chưa sẵn sàng" in err


def test_deep_search_unavailable_exits_immediately():
    """When retry returns deep_search_unavailable, exits immediately."""
    def mock_retrieval() -> dict[str, Any]:
        return {
            "status": "quality_search_unavailable",
            "rag_v2_canary": {"fallback_reason": "deep_search_unavailable"},
        }

    res, early_exit = wait_for_workspace_chat_worker(
        attempt_retrieval_fn=mock_retrieval,
        initial_ret_res={"status": "quality_search_unavailable"},
        warming_fn=lambda **kwargs: False,
        progress_fn=lambda: {"alive": True},
        no_progress_timeout=20.0,
        absolute_timeout=120.0,
        step_timeout=0.01,
        poll_interval=0.01,
    )

    assert early_exit is not None
    ok, succ, badge, err = early_exit
    assert ok is False
    assert "tìm kỹ hơn" in err.lower() or "chuyên sâu" in err.lower() or "deep_search" in err.lower()


def test_milestone_logging_format(caplog):
    """Each loop iteration logs required fields: loop, warming_s, reason, elapsed_wait_s."""
    caplog.set_level(logging.INFO, logger="aios_habit.workspace_chat_app")

    def mock_warming(**kwargs):
        time.sleep(0.01)
        return False

    def mock_retrieval():
        return {
            "status": "quality_search_unavailable",
            "rag_v2_canary": {"fallback_reason": "bge_worker_init_stdout_eof"},
        }

    wait_for_workspace_chat_worker(
        attempt_retrieval_fn=mock_retrieval,
        initial_ret_res={"status": "quality_search_unavailable"},
        warming_fn=mock_warming,
        progress_fn=lambda: {"alive": False},
        no_progress_timeout=5.0,
        absolute_timeout=10.0,
        max_consecutive_hard_errors=2,
        step_timeout=0.05,
        poll_interval=0.01,
    )

    step_logs = [r.message for r in caplog.records if "[WORKER_WARM_LOOP_STEP]" in r.message]
    assert len(step_logs) >= 2
    for entry in step_logs:
        assert "loop=" in entry
        assert "warming_s=" in entry
        assert "reason=" in entry
        assert "elapsed_wait_s=" in entry


def test_full_chat_turn_hard_error_falls_to_draft_within_ceiling(monkeypatch):
    """In _run_chat_turn_async, worker hard error fails fast and delivers draft answer cleanly."""
    conv_id = "conv_test_speed_warmloop"
    save_conversation(
        WorkspaceConversation(
            id=conv_id,
            notebook_id="mom_opcenter",
            title="Speed Warmloop Test",
        )
    )

    q = "File chỉ ra thiếu chức năng gì để phát hiện sớm tình trạng jig suy giảm?"

    # Mock retrieval to return EOF hard error
    def _mock_retrieval(*args, **kwargs):
        return {
            "status": "quality_search_unavailable",
            "rag_v2_canary": {"fallback_reason": "bge_worker_init_stdout_eof"},
        }

    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.retrieve_workspace_chat_evidence",
        _mock_retrieval,
    )
    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.ensure_workspace_chat_worker_warming",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(
        "aios_habit.workspace_chat_rag_v2_adapter.get_workspace_chat_worker_progress",
        lambda **kwargs: {"alive": False, "reason": "bge_worker_init_stdout_eof"},
    )

    set_draft_fallback_override(True)

    t0 = time.monotonic()
    res = _run_chat_turn_async(
        q_text=q,
        conversation_id=conv_id,
        notebook_id="mom_opcenter",
        query_relevant_sources=(),
        forced_domain="lsu",
    )
    turn_duration = time.monotonic() - t0

    # Must complete fast (fail-fast, definitely < 3.0s, not 246-300s!)
    assert turn_duration < 3.0
    assert res[0] is True
    badge = res[2]
    assert badge is not None
    assert badge.get("is_draft_fallback") is True

    msgs = load_messages(conv_id)
    asst_msg = [m for m in msgs if m.role == "assistant"][-1]
    assert DRAFT_LABEL in asst_msg.content
    assert "Hiệu suất jig giảm sút" in asst_msg.content
