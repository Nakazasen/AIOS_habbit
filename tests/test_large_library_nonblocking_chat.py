# -*- coding: utf-8 -*-
"""Unit tests for large library non-blocking chat improvements (014-large-library-nonblocking-chat).

Verifies:
1. Graceful degradation in _pending_source_submission_state:
   - Doesn't fail if some sources failed but at least one source succeeded.
   - Resumes with ready if other available sources in the conversation are ready.
   - Falls back to raw text / bridge when sources have text.
2. Removal of eager enqueue for whole library on page load (L2181 & L3466).
3. Compliance with FR-006 & FR-011 for broad query processing.
4. Optimization of UI polling interval and tracking scope.
"""
from __future__ import annotations

from pathlib import Path
import time
from typing import Any
import pytest

from aios_habit.workspace_chat_ai_answer import WorkspaceAIContextSource
from aios_habit.workspace_chat_app import (
    _new_pending_source_submission,
    _pending_source_submission_state,
)


def _dummy_source(
    source_id: str,
    scope: str = "notebook",
    text: str = "Nội dung tài liệu",
) -> WorkspaceAIContextSource:
    return WorkspaceAIContextSource(
        source_id=source_id,
        source_scope=scope,
        source_type="pasted_text",
        title=f"Doc {source_id}",
        privacy_label="local_only",
        text=text,
        included_chars=len(text),
        truncated=False,
    )


def test_pending_state_graceful_degradation_with_mixed_statuses(monkeypatch):
    """When some required sources are ready and some failed, the question proceeds on ready sources."""
    src_ready = _dummy_source("src_1")
    src_failed = _dummy_source("src_2")

    pending = _new_pending_source_submission(
        conversation_id="conv_1",
        question="Lỗi LSU xảy ra ở đâu?",
        selection_keys=(("notebook", "src_1"), ("notebook", "src_2")),
        required_sources=(src_ready, src_failed),
        now=1000.0,
    )

    def mock_get_status(sources, **kwargs):
        res = {}
        for s in sources:
            if s.source_id == "src_1":
                res[f"{s.source_scope}:{s.source_id}"] = "ready"
            elif s.source_id == "src_2":
                res[f"{s.source_scope}:{s.source_id}"] = "failed"
            else:
                res[f"{s.source_scope}:{s.source_id}"] = "ready"
        return res

    monkeypatch.setattr(
        "aios_habit.workspace_chat_app.get_workspace_chat_source_preparation_status",
        mock_get_status,
    )

    state, detail = _pending_source_submission_state(
        pending,
        conversation_id="conv_1",
        selection_keys=(("notebook", "src_1"), ("notebook", "src_2")),
        available_sources=(src_ready, src_failed),
        now=1005.0,
    )

    assert state == "ready", "Graceful degradation must return 'ready' when at least one required source is ready"
    assert detail == ""


def test_pending_state_graceful_degradation_with_available_ready_sources(monkeypatch):
    """When required source failed, but another available enabled source is ready, proceed."""
    src_failed = _dummy_source("src_failed")
    src_avail_ready = _dummy_source("src_avail")

    pending = _new_pending_source_submission(
        conversation_id="conv_1",
        question="Giải thích sự cố",
        selection_keys=(("notebook", "src_failed"), ("notebook", "src_avail")),
        required_sources=(src_failed,),
        now=1000.0,
    )

    def mock_get_status(sources, **kwargs):
        res = {}
        for s in sources:
            if s.source_id == "src_failed":
                res[f"{s.source_scope}:{s.source_id}"] = "failed"
            else:
                res[f"{s.source_scope}:{s.source_id}"] = "ready"
        return res

    monkeypatch.setattr(
        "aios_habit.workspace_chat_app.get_workspace_chat_source_preparation_status",
        mock_get_status,
    )

    state, detail = _pending_source_submission_state(
        pending,
        conversation_id="conv_1",
        selection_keys=(("notebook", "src_failed"), ("notebook", "src_avail")),
        available_sources=(src_failed, src_avail_ready),
        now=1005.0,
    )

    assert state == "ready", "Must return 'ready' when available sources contain ready documents"


def test_pending_state_fallback_text_when_all_sources_failed_but_text_present(monkeypatch):
    """When vector prep failed for all sources, fallback to raw text mode instead of discarding question."""
    src1 = _dummy_source("src_1", text="Nội dung văn bản còn nguyên")

    pending = _new_pending_source_submission(
        conversation_id="conv_1",
        question="Câu hỏi trên tài liệu lỗi",
        selection_keys=(("notebook", "src_1"),),
        required_sources=(src1,),
        now=1000.0,
    )

    monkeypatch.setattr(
        "aios_habit.workspace_chat_app.get_workspace_chat_source_preparation_status",
        lambda sources, **kw: {f"{s.source_scope}:{s.source_id}": "failed" for s in sources},
    )

    state, detail = _pending_source_submission_state(
        pending,
        conversation_id="conv_1",
        selection_keys=(("notebook", "src_1"),),
        available_sources=(src1,),
        now=1005.0,
    )

    assert state == "ready", "Must return 'ready' to allow fallback text answer when source text is present"


def test_app_source_code_guards_for_large_library():
    """Verify AST/source-level architectural constraints for large libraries."""
    app_source = Path("src/aios_habit/workspace_chat_app.py").read_text(encoding="utf-8")

    # 1. Verify eager enqueue in sidebar is removed
    assert "reconcile_and_enqueue_workspace_chat_sources(prep_context_sources)" not in app_source
    assert "prep_status_map = get_workspace_chat_source_preparation_status(prep_context_sources)" not in app_source

    # 2. Verify only enabled sources are scheduled on page load
    assert "enabled_ctx_sources = tuple(" in app_source
    assert "if enabled_ctx_sources:\n                    schedule_workspace_chat_source_preparation(enabled_ctx_sources)" in app_source
    assert "schedule_workspace_chat_source_preparation(ctx_all_sources)" not in app_source

    # 3. Verify polling interval optimized to 4.0s
    assert "run_every=4.0 if is_preparing else None" in app_source
    assert "run_every=2.5 if is_preparing else None" not in app_source

    # 4. Verify broad query adheres to FR-006 & FR-011
    # Does not enqueue non_empty_sources indiscriminately
    assert "required_sources=tuple(non_empty_sources)" not in app_source
    assert "required_sources=(single_src,)" in app_source
    assert "Câu hỏi quá rộng trong khi các tài liệu đang được chuẩn bị" in app_source

    # 5. Verify graceful degradation fallback in retrieval
    assert "query_relevant_sources = ready_sources or ready_in_scope" in app_source
    assert "query_relevant_sources = ready_sources" in app_source
    assert "if query_relevant_sources:" in app_source
    assert "Đang trả lời trực tiếp qua nội dung văn bản nguồn." in app_source
    assert "vector" not in "Đang trả lời trực tiếp qua nội dung văn bản nguồn."


def test_pending_state_fails_when_all_sources_failed_and_no_text(monkeypatch):
    """When vector prep failed for all sources and no source text is available, return failed."""
    src1 = _dummy_source("src_empty", text="")

    pending = _new_pending_source_submission(
        conversation_id="conv_1",
        question="Câu hỏi trên tài liệu rỗng",
        selection_keys=(("notebook", "src_empty"),),
        required_sources=(src1,),
        now=1000.0,
    )

    monkeypatch.setattr(
        "aios_habit.workspace_chat_app.get_workspace_chat_source_preparation_status",
        lambda sources, **kw: {f"{s.source_scope}:{s.source_id}": "failed" for s in sources},
    )

    state, detail = _pending_source_submission_state(
        pending,
        conversation_id="conv_1",
        selection_keys=(("notebook", "src_empty"),),
        available_sources=(src1,),
        now=1005.0,
    )

    assert state == "failed", "Must return 'failed' when all sources failed and no text fallback exists"
    assert "src_empty" in detail


def test_pending_state_waits_while_any_required_source_is_still_preparing(monkeypatch):
    """When any required source is still pending or processing, state must be waiting."""
    src1 = _dummy_source("src_prep")

    pending = _new_pending_source_submission(
        conversation_id="conv_1",
        question="Câu hỏi đang chờ chuẩn bị",
        selection_keys=(("notebook", "src_prep"),),
        required_sources=(src1,),
        now=1000.0,
    )

    monkeypatch.setattr(
        "aios_habit.workspace_chat_app.get_workspace_chat_source_preparation_status",
        lambda sources, **kw: {f"{s.source_scope}:{s.source_id}": "processing" for s in sources},
    )

    state, detail = _pending_source_submission_state(
        pending,
        conversation_id="conv_1",
        selection_keys=(("notebook", "src_prep"),),
        available_sources=(src1,),
        now=1005.0,
    )

    assert state == "waiting"
    assert "src_prep" in detail
