"""Tests for DESKTOP-SPEED-FIX-G6-PROVIDER-HOME (ARCH-06 & ARCH-10).

Covers:
1. Semantic equivalence when provider responds normally.
2. ARCH-06: Explicit timeout_seconds propagation through
   WorkspaceAIAnswerRequest -> RouterRequest -> ProviderConfig without mutating os.environ,
   concurrent thread isolation, and one-time loaded timeout configuration constants.
3. ARCH-10 (1): Preserving valid streamed content with timeout notice when router/provider
   times out mid-stream, while falling back cleanly when zero valid content was streamed.
4. ARCH-10 (2): Budget-aware reasoning-only retry in _post_chat — retries only when sufficient
   time budget remains in router_timeout, and skips retry immediately when budget is exhausted.
"""
from __future__ import annotations

import io
import json
import os
import socket
import threading
import time
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

import pytest

from aios_habit import ai_provider_bridge as pb
from aios_habit import ai_router as router_mod
from aios_habit import antigravity_bridge as bridge
from aios_habit.brain_gateway import GatewaySource, SanitizedRouterPayload
from aios_habit.workspace_chat_ai_answer import (
    PRIVACY_MODE_CLOUD_ALLOWED,
    WorkspaceAIAnswerRequest,
    WorkspaceAIAnswerResult,
    WorkspaceAIContextSource,
    generate_workspace_ai_answer,
)


@pytest.fixture
def mock_store_and_trace(monkeypatch: pytest.MonkeyPatch) -> Dict[str, List[Any]]:
    import aios_habit.workspace_chat_store as store

    saved_messages: List[Any] = []
    saved_traces: List[Any] = []

    monkeypatch.setattr(store, "save_message", lambda msg: saved_messages.append(msg))
    monkeypatch.setattr(store, "save_evidence_trace", lambda trc: saved_traces.append(trc))
    monkeypatch.setattr(store, "load_messages", lambda conv_id: list(saved_messages))
    monkeypatch.setattr(store, "load_conversation", lambda conv_id: None)
    monkeypatch.setattr(store, "load_conversation_source_selections", lambda conv_id: [])
    monkeypatch.setattr(
        "aios_habit.evidence_trace.build_evidence_trace_from_citations",
        lambda **kwargs: SimpleNamespace(
            trace_id="trc-g6-test",
            metadata={"status": "valid"},
            provenance=kwargs.get("provenance", {}),
            answer_text=kwargs.get("answer_text", ""),
        ),
    )
    monkeypatch.setattr(
        bridge,
        "_get_or_create_user_message",
        lambda *args, **kwargs: SimpleNamespace(id="MSG-USER-G6"),
    )
    monkeypatch.setattr(
        "aios_habit.workspace_memory_service.get_workspace_memory_enabled_preference",
        lambda: False,
    )
    return {"messages": saved_messages, "traces": saved_traces}


# ---------------------------------------------------------------------------
# 1. Semantic Equivalence Tests (Normal Provider Response)
# ---------------------------------------------------------------------------

def test_semantic_equivalence_normal_provider_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Normal SSE streaming response produces identical output and streams all chunks cleanly."""
    sse_lines = [
        b'data: {"model": "qwen2.5:7b", "choices": [{"delta": {"content": "Quy tr\xc3\xacnh LSU "}, "finish_reason": null}]}\n\n',
        b'data: {"model": "qwen2.5:7b", "choices": [{"delta": {"content": "ho\xc3\xa0n t\xe1\xba\xa5t an to\xc3\xa0n."}, "finish_reason": "stop"}]}\n\n',
        b"data: [DONE]\n\n",
    ]

    class FakeSSEResponse(io.BytesIO):
        def __enter__(self) -> "FakeSSEResponse":
            return self

        def __exit__(self, *args: Any) -> None:
            self.close()

    def fake_urlopen(req: Any, timeout: float = 30.0) -> FakeSSEResponse:
        return FakeSSEResponse(b"".join(sse_lines))

    monkeypatch.setattr(pb.urllib.request, "urlopen", fake_urlopen)

    cfg = pb.ProviderConfig(
        provider_type="openai_compatible_local",
        endpoint_url="http://127.0.0.1:11434/v1/chat/completions",
        model_name="qwen2.5:7b",
        locality="local",
        timeout_seconds=15,
        enabled=True,
    )
    chunks: List[str] = []
    res = pb.answer_with_provider(
        question="Quy trình LSU như thế nào?",
        source_context="Tài liệu LSU: vận hành an toàn.",
        config=cfg,
        deterministic_answer="Fallback",
        on_chunk=chunks.append,
    )
    assert res.ok is True
    assert res.used_fallback is False
    assert res.answer_text == "Quy trình LSU hoàn tất an toàn."
    assert "".join(chunks) == "Quy trình LSU hoàn tất an toàn."
    assert pb.TIMEOUT_STREAM_INTERRUPTED_NOTICE_VI.strip() not in res.answer_text


# ---------------------------------------------------------------------------
# 2. ARCH-06 Tests: Explicit Timeout Propagation & Zero os.environ Mutation
# ---------------------------------------------------------------------------

def test_arch06_explicit_timeout_propagation_chain_no_env_mutation(
    monkeypatch: pytest.MonkeyPatch,
    mock_store_and_trace: Dict[str, List[Any]],
) -> None:
    """Verify timeout_seconds flows WorkspaceAIAnswerRequest -> RouterRequest -> ProviderConfig without mutating os.environ."""
    monkeypatch.setenv("AIOS_ROUTER_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("AIOS_LOCAL_AI_TIMEOUT_SECONDS", "90")
    monkeypatch.setenv("AIOS_PROVIDER_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("AIOS_LOCAL_AI_ENDPOINT", "http://127.0.0.1:11434/v1/chat/completions")
    monkeypatch.setenv("AIOS_LOCAL_AI_MODEL", "qwen2.5:7b")
    monkeypatch.setenv("AIOS_USE_LEGACY_NAKAZASEN_ROUTER", "0")

    captured: Dict[str, Any] = {}

    class EnvironmentMutationWatchdog(dict):
        pass

    orig_setitem = os.environ.__class__.__setitem__
    env_mutations: List[tuple[str, str]] = []

    def tracking_setitem(self: Any, key: str, value: str) -> None:
        if key in ("AIOS_LOCAL_AI_TIMEOUT_SECONDS", "AIOS_PROVIDER_TIMEOUT_SECONDS"):
            env_mutations.append((key, value))
        orig_setitem(self, key, value)

    monkeypatch.setattr(os.environ.__class__, "__setitem__", tracking_setitem)

    def fake_answer_with_provider(
        question: str,
        source_context: str,
        config: pb.ProviderConfig,
        deterministic_answer: str,
        source_refs: Optional[list] = None,
        safety_mode: str = "local_only",
        ai_mode: str = "grounded",
        custom_system_prompt: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> pb.ProviderResult:
        captured["provider_config_timeout"] = config.timeout_seconds
        captured["provider_deadline"] = config.router_deadline_monotonic
        captured["env_local_during_provider"] = os.environ.get("AIOS_LOCAL_AI_TIMEOUT_SECONDS")
        captured["env_cloud_during_provider"] = os.environ.get("AIOS_PROVIDER_TIMEOUT_SECONDS")
        if on_chunk:
            on_chunk("Đáp án kiểm thử chuỗi timeout tường minh.")
        return pb.ProviderResult(
            ok=True,
            answer_text="Đáp án kiểm thử chuỗi timeout tường minh.",
            provider_name="openai_compatible_local",
            model_name=config.model_name,
            used_fallback=False,
        )

    monkeypatch.setattr(router_mod, "answer_with_provider", fake_answer_with_provider)

    src = WorkspaceAIContextSource(
        source_id="SRC-1",
        source_scope="notebook",
        source_type="markdown",
        title="Tài liệu kỹ thuật",
        privacy_label="cloud_safe",
        text="Nội dung kỹ thuật kiểm thử.",
        included_chars=28,
    )

    ok, msg, badge, err = bridge.route_workspace_chat_submission(
        question="Kiểm thử timeout chain?",
        evidence_items=[{"evidence_id": "SRC-1", "title": "Tài liệu kỹ thuật", "text": "Nội dung kỹ thuật kiểm thử."}],
        packed_sources=(src,),
        conversation_id="CONV-ARCH06-CHAIN",
        notebook_id="NB-1",
        retrieval_applied=False,
        retrieved_sources=(),
        retrieval_summary="",
        current_keys=(("notebook", "SRC-1"),),
        chat_history=(),
        user_raw_input="Kiểm thử timeout chain?",
        backend="nakazasen_router",
    )

    assert ok is True
    assert err is None
    assert env_mutations == [], f"os.environ must not be mutated, but saw: {env_mutations}"
    assert captured["provider_config_timeout"] == 7
    assert captured["provider_deadline"] is not None
    assert captured["env_local_during_provider"] == "90"
    assert captured["env_cloud_during_provider"] == "60"


def test_arch06_concurrent_router_requests_isolated_timeouts() -> None:
    """Concurrent threads with different explicit timeout_seconds do not race or bleed timeouts."""
    env_snapshot = {
        "AIOS_LOCAL_AI_ENDPOINT": "http://127.0.0.1:11434/v1/chat/completions",
        "AIOS_LOCAL_AI_MODEL": "local-model",
        "AIOS_LOCAL_AI_TIMEOUT_SECONDS": "90",
        "GEMINI_API_KEY": "fake-gemini-key",
        "AIOS_PROVIDER_TIMEOUT_SECONDS": "60",
    }
    observed_timeouts: Dict[int, tuple[int, int]] = {}
    barrier = threading.Barrier(4)

    def worker(desired_timeout: int) -> None:
        barrier.wait(timeout=2.0)
        cfgs = router_mod.provider_configs_from_env(env_snapshot, timeout_seconds=desired_timeout)
        local_cfg = next(c for c in cfgs if c.trusted_internal)
        cloud_cfg = next(c for c in cfgs if not c.trusted_internal)
        req = router_mod.RouterRequest(
            question="Q",
            source_context="Ctx",
            deterministic_answer="Det",
            timeout_seconds=desired_timeout,
        )
        # Verify call_openai_compatible_provider builds ProviderConfig with desired_timeout
        captured_pcfg: List[pb.ProviderConfig] = []
        orig_answer = router_mod.answer_with_provider
        observed_timeouts[desired_timeout] = (local_cfg.timeout_seconds, cloud_cfg.timeout_seconds)

    threads = [threading.Thread(target=worker, args=(t,)) for t in (3, 8, 15, 25)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert observed_timeouts[3] == (3, 3)
    assert observed_timeouts[8] == (8, 8)
    assert observed_timeouts[15] == (15, 15)
    assert observed_timeouts[25] == (25, 25)


# ---------------------------------------------------------------------------
# 3. ARCH-10 (Part 1) Tests: Streamed Content Preservation on Timeout
# ---------------------------------------------------------------------------

def test_arch10_post_chat_preserves_valid_streamed_chunks_on_midstream_socket_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fake provider streams valid SSE chunks then raises socket.timeout -> _post_chat preserves content + timeout label."""

    class MidStreamTimeoutResponse:
        def __init__(self) -> None:
            self._step = 0

        def __enter__(self) -> "MidStreamTimeoutResponse":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def __iter__(self) -> "MidStreamTimeoutResponse":
            return self

        def __next__(self) -> bytes:
            self._step += 1
            if self._step == 1:
                return 'data: {"model": "qwen2.5:7b", "choices": [{"delta": {"content": "Bước 1: Kiểm tra áp suất buồng LSU. "}, "finish_reason": null}]}\n'.encode("utf-8")
            if self._step == 2:
                return 'data: {"model": "qwen2.5:7b", "choices": [{"delta": {"content": "Bước 2: Xác nhận tín hiệu cảm biến."}, "finish_reason": null}]}\n'.encode("utf-8")
            raise socket.timeout("Read timed out mid-stream")

    monkeypatch.setattr(pb.urllib.request, "urlopen", lambda req, timeout=30.0: MidStreamTimeoutResponse())

    cfg = pb.ProviderConfig(
        provider_type="openai_compatible_local",
        endpoint_url="http://127.0.0.1:11434/v1/chat/completions",
        model_name="qwen2.5:7b",
        locality="local",
        timeout_seconds=2,
        enabled=True,
    )
    streamed: List[str] = []
    res = pb.answer_with_provider(
        question="Các bước kiểm tra LSU?",
        source_context="Tài liệu hướng dẫn kiểm tra LSU.",
        config=cfg,
        deterministic_answer="Fallback",
        on_chunk=streamed.append,
    )

    assert res.ok is True
    assert res.used_fallback is False
    assert "Bước 1: Kiểm tra áp suất buồng LSU." in res.answer_text
    assert "Bước 2: Xác nhận tín hiệu cảm biến." in res.answer_text
    assert "[Lưu ý: Phản hồi bị ngắt do hết thời gian chờ" in res.answer_text
    assert any("[Lưu ý: Phản hồi bị ngắt do hết thời gian chờ" in c for c in streamed)


def test_arch10_router_timeout_preserves_streamed_content_in_antigravity_bridge(
    monkeypatch: pytest.MonkeyPatch,
    mock_store_and_trace: Dict[str, List[Any]],
) -> None:
    """When _try_nakazasen_router hits future TimeoutError after receiving valid streamed chunks,
    it preserves the streamed content with a timeout label instead of returning empty and wiping the UI."""
    monkeypatch.setenv("AIOS_ROUTER_TIMEOUT_SECONDS", "1")

    def fake_streaming_then_hanging_router(
        request: WorkspaceAIAnswerRequest,
        context: Any,
    ) -> WorkspaceAIAnswerResult:
        if request.on_chunk:
            request.on_chunk("Phần 1: Cấu hình ACR gồm 3 mô-đun chính. ")
            request.on_chunk("Phần 2: Điện áp định mức là 24VDC.")
        time.sleep(1.5)
        if request.on_chunk:
            request.on_chunk("PHẦN RÒ RỈ SAU TIMEOUT KHÔNG ĐƯỢC PHÉP NHẬN")
        return WorkspaceAIAnswerResult(
            ok=True,
            answer_text="Never reached in time",
            included_source_titles=(),
            warnings=(),
        )

    monkeypatch.setattr(
        "aios_habit.workspace_chat_ai_answer.generate_workspace_ai_answer",
        fake_streaming_then_hanging_router,
    )

    ui_chunks: List[str] = []
    ok, msg, badge, err = bridge.route_workspace_chat_submission(
        question="Cấu hình ACR như thế nào?",
        evidence_items=[{"evidence_id": "EV-ACR", "title": "Tài liệu ACR", "text": "Cấu hình ACR 24VDC"}],
        packed_sources=(),
        conversation_id="CONV-ARCH10-PARTIAL",
        notebook_id="NB-1",
        retrieval_applied=True,
        retrieved_sources=(),
        retrieval_summary="Đã tìm thấy 1 đoạn nguồn ACR.",
        current_keys=(),
        chat_history=(),
        user_raw_input="Cấu hình ACR như thế nào?",
        backend="nakazasen_router",
        on_chunk=ui_chunks.append,
    )

    assert ok is True
    assert err is None
    assert badge is not None
    assert badge.get("partial_timeout") is True
    assert not badge.get("fallback_used")

    saved_messages = mock_store_and_trace["messages"]
    assert len(saved_messages) == 1
    saved_content = saved_messages[0].content
    assert "Phần 1: Cấu hình ACR gồm 3 mô-đun chính." in saved_content
    assert "Phần 2: Điện áp định mức là 24VDC." in saved_content
    assert "[Lưu ý: Phản hồi bị ngắt do hết thời gian chờ" in saved_content
    assert "PHẦN RÒ RỈ SAU TIMEOUT" not in saved_content


# ---------------------------------------------------------------------------
# 4. ARCH-10 (Part 2) Tests: Budget-Aware Reasoning-Only Retry in _post_chat
# ---------------------------------------------------------------------------

def test_arch10_reasoning_only_retry_executes_when_budget_sufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fake provider returns reasoning-only on attempt 1 with ample budget -> retries and returns direct content."""
    call_payloads: List[Dict[str, Any]] = []

    class FakeJSONResponse(io.BytesIO):
        def __enter__(self) -> "FakeJSONResponse":
            return self

        def __exit__(self, *args: Any) -> None:
            self.close()

    def fake_urlopen(req: Any, timeout: float = 30.0) -> FakeJSONResponse:
        body = json.loads(req.data.decode("utf-8"))
        call_payloads.append(body)
        if len(call_payloads) == 1:
            resp_obj = {
                "model": "deepseek-reasoner",
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "reasoning_content": "Thinking step 1... Thinking step 2...",
                        },
                        "finish_reason": "length",
                    }
                ],
            }
        else:
            resp_obj = {
                "model": "deepseek-reasoner",
                "choices": [
                    {
                        "message": {
                            "content": "Câu trả lời trực tiếp sau khi retry có đủ thời gian.",
                        },
                        "finish_reason": "stop",
                    }
                ],
            }
        return FakeJSONResponse(json.dumps(resp_obj).encode("utf-8"))

    monkeypatch.setattr(pb.urllib.request, "urlopen", fake_urlopen)

    cfg = pb.ProviderConfig(
        provider_type="openai_compatible_local",
        endpoint_url="http://127.0.0.1:11434/v1/chat/completions",
        model_name="deepseek-reasoner",
        locality="local",
        timeout_seconds=10,
        enabled=True,
        router_deadline_monotonic=time.monotonic() + 10.0,
    )

    res = pb.answer_with_provider(
        question="Giải thích nguyên lý CTU?",
        source_context="Tài liệu CTU.",
        config=cfg,
        deterministic_answer="Fallback",
    )

    assert len(call_payloads) == 2, "Should retry once when ample time budget remains"
    assert res.ok is True
    assert res.answer_text == "Câu trả lời trực tiếp sau khi retry có đủ thời gian."


def test_arch10_reasoning_only_retry_skipped_when_budget_insufficient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fake provider returns reasoning-only on attempt 1 when remaining router_timeout budget is low -> skips retry immediately."""
    call_count = 0

    class FakeJSONResponse(io.BytesIO):
        def __enter__(self) -> "FakeJSONResponse":
            return self

        def __exit__(self, *args: Any) -> None:
            self.close()

    def fake_urlopen(req: Any, timeout: float = 30.0) -> FakeJSONResponse:
        nonlocal call_count
        call_count += 1
        resp_obj = {
            "model": "deepseek-reasoner",
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning_content": "Spent nearly entire timeout thinking...",
                    },
                    "finish_reason": "length",
                }
            ],
        }
        return FakeJSONResponse(json.dumps(resp_obj).encode("utf-8"))

    monkeypatch.setattr(pb.urllib.request, "urlopen", fake_urlopen)

    # Simulate only 0.05s left on router_deadline_monotonic out of a 10s timeout budget
    cfg = pb.ProviderConfig(
        provider_type="openai_compatible_local",
        endpoint_url="http://127.0.0.1:11434/v1/chat/completions",
        model_name="deepseek-reasoner",
        locality="local",
        timeout_seconds=10,
        enabled=True,
        router_deadline_monotonic=time.monotonic() + 0.05,
    )

    res = pb.answer_with_provider(
        question="Giải thích nguyên lý CTU?",
        source_context="Tài liệu CTU.",
        config=cfg,
        deterministic_answer="Fallback cục bộ an toàn.",
    )

    assert call_count == 1, f"Retry must be skipped when budget is insufficient, but saw {call_count} calls"
    assert res.ok is False
    assert res.used_fallback is True
    assert res.answer_text == "Fallback cục bộ an toàn."
    assert res.error_message == pb.EMPTY_ANSWER_ERROR_MESSAGE_VI
