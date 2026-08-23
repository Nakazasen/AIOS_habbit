"""Antigravity IDE AI Brain Bridge for AIOS WorkLens.

Provides honest, truthful connectivity between AIOS WorkLens Workspace Chat
and Antigravity IDE via direct protocol or asynchronous handoff.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from aios_habit.ide_handoff_bridge import (
    HANDOFF_ROOT,
    RESPONSE_SCHEMA_VERSION,
    check_handoff_request_timeouts,
    find_response_for_request,
    list_pending_ide_requests,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_ANTIGRAVITY_ENDPOINT = os.environ.get(
    "AIOS_ANTIGRAVITY_BRIDGE_URL", "http://127.0.0.1:8585/v1/chat/completions"
)
DEFAULT_ANTIGRAVITY_HEALTH_URL = os.environ.get(
    "AIOS_ANTIGRAVITY_HEALTH_URL", "http://127.0.0.1:8585/health"
)
DEFAULT_TIMEOUT_SECONDS = 60

# 6-State FSM Constants
FSM_UNAVAILABLE = "unavailable"
FSM_DIRECT_READY = "direct_ready"
FSM_HANDOFF_READY = "handoff_ready"
FSM_HANDOFF_PENDING = "handoff_pending"
FSM_COMPLETED = "completed"
FSM_FAILED = "failed"

ALLOWED_FSM_STATES = {
    FSM_UNAVAILABLE,
    FSM_DIRECT_READY,
    FSM_HANDOFF_READY,
    FSM_HANDOFF_PENDING,
    FSM_COMPLETED,
    FSM_FAILED,
}

ALLOWED_MODES = {"direct", "handoff", "none"}
ALLOWED_CAPABILITIES = {"direct_chat", "local_handoff"}


def sanitize_reason(reason: str) -> str:
    """Sanitize error text to avoid leaking secrets, tokens, or absolute paths."""
    if not reason:
        return ""
    text = str(reason).replace("\\", "/")
    # Mask paths
    text = re.sub(r"([A-Za-z]:)?/[a-zA-Z0-9_\-\./]+", "<path>", text)
    # Mask API tokens
    text = re.sub(r"(sk-[a-zA-Z0-9_\-]+|Bearer\s+[a-zA-Z0-9_\-]+)", "<redacted_token>", text)
    return text[:200].strip()


# Alias for test suite compatibility
sanitize_bridge_error = sanitize_reason


def is_local_endpoint(endpoint_url: str) -> bool:
    """Validate that the URL points to a loopback or private network address."""
    try:
        parsed = urllib.parse.urlparse(endpoint_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        hostname = parsed.hostname.lower()
        if hostname == "localhost" or hostname.endswith(".local"):
            return True
        address = ipaddress.ip_address(hostname)
        if address in ipaddress.ip_network("198.51.100.0/24") or address in ipaddress.ip_network("203.0.113.0/24") or address in ipaddress.ip_network("192.0.2.0/24"):
            return False
        return address.is_loopback or address.is_private
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class AntigravityHealthStatus:
    status: str
    mode: str = "none"
    capabilities: Sequence[str] = field(default_factory=list)
    reason: str = ""
    raw_payload: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return self.status in (FSM_DIRECT_READY, FSM_HANDOFF_READY, FSM_HANDOFF_PENDING, FSM_COMPLETED)

    @property
    def is_ready(self) -> bool:
        return self.status in (FSM_DIRECT_READY, FSM_HANDOFF_READY, FSM_COMPLETED)

    @property
    def is_direct_ready(self) -> bool:
        return self.status == FSM_DIRECT_READY

    @property
    def is_direct(self) -> bool:
        return self.status == FSM_DIRECT_READY and self.mode == "direct"

    @property
    def is_handoff_ready(self) -> bool:
        return self.status in (FSM_HANDOFF_READY, FSM_HANDOFF_PENDING, FSM_COMPLETED)

    @property
    def is_handoff(self) -> bool:
        return self.status in (FSM_HANDOFF_READY, FSM_HANDOFF_PENDING) or self.mode == "handoff"


# Alias for compatibility with various explorer naming preferences
AntigravityBridgeHealth = AntigravityHealthStatus


@dataclass(frozen=True)
class AntigravityBridgeResponse:
    ok: bool
    answer_text: str
    model: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    error_message: str = ""
    provider_name: str = "antigravity_bridge"
    metadata: Mapping[str, Any] = field(default_factory=dict)


def get_antigravity_bridge_health(
    health_url: str = DEFAULT_ANTIGRAVITY_HEALTH_URL,
    timeout_seconds: float = 0.8,
) -> AntigravityHealthStatus:
    """Query and return the structured 6-state FSM health status."""
    try:
        req = urllib.request.Request(
            health_url,
            headers={"User-Agent": "AIOS-WorkLens-Bridge/1.0"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            if response.status == 200:
                body = response.read().decode("utf-8")
                data = json.loads(body)
                raw_status = str(data.get("status", "")).strip().lower()

                # Map legacy "ok" to "handoff_ready" if present
                if raw_status == "ok":
                    raw_status = FSM_HANDOFF_READY

                status = raw_status if raw_status in ALLOWED_FSM_STATES else FSM_UNAVAILABLE
                mode = str(data.get("mode", "none")).strip().lower()
                if mode not in ALLOWED_MODES:
                    mode = "none"

                # Filter capabilities: never allow unverified capabilities
                caps = [c for c in data.get("capabilities", []) if c in ALLOWED_CAPABILITIES]
                reason = sanitize_reason(str(data.get("reason", "")))

                return AntigravityHealthStatus(
                    status=status,
                    mode=mode,
                    capabilities=caps,
                    reason=reason,
                    raw_payload=data,
                )
            else:
                return AntigravityHealthStatus(
                    status=FSM_FAILED,
                    mode="none",
                    capabilities=[],
                    reason=f"HTTP {response.status}",
                )
    except urllib.error.HTTPError as http_err:
        try:
            err_body = http_err.read().decode("utf-8")
            err_data = json.loads(err_body)
            raw_status = str(err_data.get("status", FSM_FAILED)).strip().lower()
            status = raw_status if raw_status in ALLOWED_FSM_STATES else FSM_FAILED
            reason = sanitize_reason(str(err_data.get("reason", http_err.reason)))
        except Exception:
            status = FSM_FAILED
            reason = sanitize_reason(f"HTTP {http_err.code}: {http_err.reason}")
        return AntigravityHealthStatus(
            status=status,
            mode="none",
            capabilities=[],
            reason=reason,
        )
    except Exception as exc:
        LOGGER.debug("Antigravity Bridge health check unreachable: %s", exc)
        return AntigravityHealthStatus(
            status=FSM_UNAVAILABLE,
            mode="none",
            capabilities=[],
            reason=sanitize_reason(f"Connection failed or unreachable: {exc}"),
        )


# Compatibility aliases
get_antigravity_bridge_status = get_antigravity_bridge_health
get_antigravity_health = get_antigravity_bridge_health


def is_antigravity_bridge_available(
    health_url: str = DEFAULT_ANTIGRAVITY_HEALTH_URL,
    timeout_seconds: float = 0.8,
) -> bool:
    """Check if the Antigravity Bridge is available in any valid ready state."""
    health = get_antigravity_bridge_health(health_url=health_url, timeout_seconds=timeout_seconds)
    return health.is_available


def call_antigravity_bridge(
    question: str,
    system_prompt: str = "",
    context_text: str = "",
    *,
    chat_history: Sequence[Mapping[str, Any]] = (),
    endpoint_url: str = DEFAULT_ANTIGRAVITY_ENDPOINT,
    model: str = "",
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    privacy_mode: str = "local_only",
    answer_language: str = "vi",
) -> AntigravityBridgeResponse:
    """Send a chat completion request to the direct Antigravity Bridge Daemon."""
    start_time = time.time()

    # Fail-closed local privacy check
    if privacy_mode == "local_only" and not is_local_endpoint(endpoint_url):
        return AntigravityBridgeResponse(
            ok=False,
            answer_text="",
            error_message="Bị chặn: Không thể gửi dữ liệu local_only tới endpoint không cục bộ.",
            latency_ms=0.0,
        )

    from aios_habit.i18n import get_ai_language_instruction, normalize_locale
    norm_lang = normalize_locale(answer_language)
    lang_instr = get_ai_language_instruction(norm_lang)

    effective_sys_prompt = system_prompt
    if effective_sys_prompt:
        if "Yêu cầu ngôn ngữ:" not in effective_sys_prompt and "言語指示:" not in effective_sys_prompt and "语言指示:" not in effective_sys_prompt:
            effective_sys_prompt = f"{effective_sys_prompt}\n\n{lang_instr}"
    else:
        effective_sys_prompt = lang_instr

    messages = []
    if effective_sys_prompt:
        messages.append({"role": "system", "content": effective_sys_prompt})

    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:
            messages.append({"role": role, "content": content})


    user_content = question
    if context_text:
        user_content = f"{question}\n\n--- TÀI LIỆU & NGỮ CẢNH ĐÍNH KÈM ---\n{context_text}"
    messages.append({"role": "user", "content": user_content})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "stream": False,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AIOS-WorkLens-Bridge/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            raw_body = response.read().decode("utf-8")
            latency_ms = (time.time() - start_time) * 1000
            result_json = json.loads(raw_body)

            choices = result_json.get("choices", [])
            if choices and isinstance(choices, list):
                msg = choices[0].get("message", {})
                answer_text = msg.get("content", "").strip()
                usage = result_json.get("usage", {})
                tokens = usage.get("total_tokens", len(answer_text) // 4)
                return AntigravityBridgeResponse(
                    ok=True,
                    answer_text=answer_text,
                    model=result_json.get("model", model),
                    latency_ms=latency_ms,
                    tokens_used=tokens,
                )
            return AntigravityBridgeResponse(
                ok=False,
                answer_text="",
                error_message="Empty choices in Antigravity Bridge response",
                latency_ms=latency_ms,
            )
    except urllib.error.HTTPError as http_err:
        latency_ms = (time.time() - start_time) * 1000
        try:
            err_body = http_err.read().decode("utf-8")
            err_data = json.loads(err_body)
            err_detail = err_data.get("error", http_err.reason)
            err_msg = f"HTTP {http_err.code}: {err_detail}"
        except Exception:
            err_msg = f"HTTP {http_err.code}: {http_err.reason}"
        LOGGER.warning("Antigravity Bridge HTTP error: %s", sanitize_reason(err_msg))
        return AntigravityBridgeResponse(
            ok=False,
            answer_text="",
            error_message=sanitize_reason(err_msg),
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = (time.time() - start_time) * 1000
        LOGGER.warning("Antigravity Bridge connection failed: %s", sanitize_reason(str(exc)))
        return AntigravityBridgeResponse(
            ok=False,
            answer_text="",
            error_message=sanitize_reason(str(exc)),
            latency_ms=latency_ms,
        )


def process_pending_ide_handoffs(
    base_dir: Path | str = HANDOFF_ROOT,
    endpoint_url: str = DEFAULT_ANTIGRAVITY_ENDPOINT,
) -> int:
    """Discover pending requests and resolve via direct bridge if direct is active."""
    check_handoff_request_timeouts(base_dir)
    pending = list_pending_ide_requests(base_dir)
    processed_count = 0

    for req in pending:
        if req.response_exists or req.state != "handoff_pending":
            continue

        outbox_folder = Path(base_dir) / "outbox" / req.request_id
        manifest_path = outbox_folder / "manifest.json"
        prompt_path = outbox_folder / "prompt_for_antigravity.md"
        evidence_full_path = outbox_folder / "evidence_full.md"

        if not manifest_path.exists():
            continue

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        system_policy = "Bạn là chuyên gia phân tích tài liệu và kiến trúc hệ thống Antigravity IDE."
        prompt_content = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else req.question
        evidence_content = evidence_full_path.read_text(encoding="utf-8") if evidence_full_path.exists() else ""

        bridge_res = call_antigravity_bridge(
            question=prompt_content,
            system_prompt=system_policy,
            context_text=evidence_content,
            endpoint_url=endpoint_url,
            privacy_mode=manifest.get("privacy_mode", "local_only"),
        )

        if bridge_res.ok and bridge_res.answer_text:
            inbox_dir = Path(base_dir) / "inbox" / req.request_id
            inbox_dir.mkdir(parents=True, exist_ok=True)
            response_file = inbox_dir / "response.json"

            # Strict evidence matching: NEVER fabricate citations, match word boundaries
            cited_ids = []
            for ev_id in manifest.get("allowed_source_ids", []):
                pattern = re.compile(r'(?<![A-Za-z0-9_-])' + re.escape(str(ev_id)) + r'(?![A-Za-z0-9_-])')
                if pattern.search(bridge_res.answer_text):
                    cited_ids.append(str(ev_id))

            limitations = []
            if not cited_ids:
                limitations.append("No explicit evidence IDs were cited in the answer text.")

            response_payload = {
                "schema_version": RESPONSE_SCHEMA_VERSION,
                "request_id": req.request_id,
                "status": "completed",
                "answer_markdown": bridge_res.answer_text,
                "cited_evidence_ids": cited_ids,
                "evidence_ids_used": cited_ids,
                "limitations": limitations,
                "confidence": "high" if cited_ids else "low",
                "privacy_acknowledged": True,
                "used_full_bundle": True,
                "unsupported_claims": [],
                "recommended_next_actions": ["Kiểm tra lại bằng chứng và lưu Case nếu cần."],
                "model_tool_name": f"Antigravity IDE AI ({bridge_res.model})",
            }

            # Atomic write to avoid partial writes
            tmp_response_file = inbox_dir / f"response_{uuid.uuid4().hex[:6]}.tmp"
            tmp_response_file.write_text(
                json.dumps(response_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_response_file.replace(response_file)
            processed_count += 1
            LOGGER.info("Processed IDE handoff request %s", req.request_id)

    return processed_count


def compress_conversation_context_direct(
    chat_history: Sequence[Mapping[str, Any]],
    *,
    health_status: AntigravityHealthStatus | None = None,
    endpoint_url: str = DEFAULT_ANTIGRAVITY_ENDPOINT,
    timeout_seconds: int = 45,
) -> tuple[bool, str, str | None]:
    """Compress conversation history using Antigravity Direct with strict fail-closed policy.

    Returns:
        (ok, compressed_summary, error_message)
    """
    health = health_status or get_antigravity_bridge_health()
    if not health.is_direct_ready:
        return (
            False,
            "",
            f"Antigravity Direct chưa sẵn sàng ({health.status}: {health.reason or 'direct mode not available'}). Không thể nén ngữ cảnh.",
        )

    if not chat_history:
        return (False, "", "Lịch sử cuộc trò chuyện rỗng, không có nội dung để nén.")

    history_lines = []
    for msg in chat_history:
        role = "Người dùng" if msg.get("role") == "user" else "Hệ thống/AI"
        content = str(msg.get("content", "") or "").strip()
        if content:
            history_lines.append(f"{role}: {content}")

    if not history_lines:
        return (False, "", "Lịch sử cuộc trò chuyện rỗng, không có nội dung để nén.")

    history_text = "\n".join(history_lines)

    prompt = (
        "Bạn là chuyên gia hệ thống. Hãy tóm tắt ngắn gọn các thực thể, quyết định kỹ thuật, ngữ cảnh và "
        "kết luận quan trọng trong phiên hội thoại sau để làm ngữ cảnh kế thừa cho phiên làm việc mới.\n"
        "Yêu cầu:\n"
        "- Trình bày dạng văn bản súc tích, giữ nguyên các mã định danh, số liệu, tên thực thể và quy tắc chính.\n"
        "- Không chào hỏi, không thêm giải thích rườm rà ngoài phần tóm tắt ngữ cảnh.\n\n"
        f"--- TOÀN BỘ LỊCH SỬ HỘI THOẠI ---\n{history_text}"
    )

    try:
        from aios_habit.workspace_chat_ai_answer import PRIVACY_MODE_CLOUD_ALLOWED
        res = call_antigravity_bridge(
            question=prompt,
            system_prompt="Bạn là trợ lý nén và kế thừa ngữ cảnh hội thoại kỹ thuật cho AIOS.",
            endpoint_url=endpoint_url,
            timeout_seconds=timeout_seconds,
            privacy_mode=PRIVACY_MODE_CLOUD_ALLOWED,
        )
        if res.ok and res.answer_text and res.answer_text.strip():
            return (True, res.answer_text.strip(), None)
        elif not res.ok:
            return (False, "", f"Lỗi cầu nối Antigravity IDE: {res.error_message}")
        else:
            return (False, "", "Antigravity Direct trả về nội dung tóm tắt rỗng.")
    except Exception as exc:
        return (False, "", f"Lỗi nén ngữ cảnh qua Antigravity Direct: {sanitize_reason(str(exc))}")


def route_workspace_chat_submission(
    question: str,
    evidence_items: list[dict[str, Any]],
    packed_sources: tuple[Any, ...],
    conversation_id: str,
    notebook_id: str,
    retrieval_applied: bool,
    retrieved_sources: tuple[Any, ...],
    retrieval_summary: str,
    current_keys: tuple[Any, ...],
    chat_history: tuple[dict[str, Any], ...],
    user_raw_input: str,
    health_status: AntigravityHealthStatus | None = None,
    handoff_root: Path | None = None,
    endpoint_url: str | None = None,
    answer_language: str = "vi",
) -> tuple[bool, str, dict[str, Any] | None, str | None]:
    """Route workspace chat submission to Direct, Handoff, or Smart Router with strict fail-closed policy.

    Returns:
        (ok, success_message, badge_data, error_message)
    """
    from aios_habit.workspace_chat_store import save_message
    from aios_habit.workspace_chat_models import ChatMessage
    from aios_habit.ide_handoff_bridge import write_ide_handoff_bundle
    from aios_habit.workspace_chat_ai_answer import PRIVACY_MODE_CLOUD_ALLOWED

    health = health_status or get_antigravity_bridge_health()

    if health.is_direct_ready:
        context_blocks = []
        for idx, ev in enumerate(evidence_items, start=1):
            title_ev = ev.get("title", f"Nguồn {idx}")
            snip_ev = ev.get("text", ev.get("snippet", ""))
            context_blocks.append(f"[{idx}] {title_ev}:\n{snip_ev}")
        direct_context_text = "\n\n".join(context_blocks)

        try:
            call_kwargs = {
                "question": question,
                "context_text": direct_context_text,
                "chat_history": chat_history,
                "privacy_mode": PRIVACY_MODE_CLOUD_ALLOWED,
                "answer_language": answer_language,
            }
            if endpoint_url:
                call_kwargs["endpoint_url"] = endpoint_url
            direct_res = call_antigravity_bridge(**call_kwargs)

            if direct_res.ok:
                user_msg = ChatMessage(
                    id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
                    conversation_id=conversation_id,
                    role="user",
                    content=user_raw_input,
                )
                save_message(user_msg)
                assistant_msg = ChatMessage(
                    id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
                    conversation_id=conversation_id,
                    role="assistant",
                    content=direct_res.answer_text,
                )
                save_message(assistant_msg)

                source_titles = [ev.get("title", "") for ev in evidence_items]
                verified_model_str = (
                    direct_res.model
                    if direct_res.model and direct_res.model not in ("antigravity-brain-pro", "antigravity", "gemini-pro")
                    else ""
                )
                badge = {
                    "conversation_id": conversation_id,
                    "type": "ai_answered",
                    "source_count": len(source_titles),
                    "source_titles": source_titles,
                    "ai_source": "Antigravity IDE",
                    "bridge": "Sidecar (Trực tiếp)",
                    "provider": "Gemini Web Stream (Nặc danh)",
                    "model_tool_name": verified_model_str,
                    "verified_model": verified_model_str,
                    "operational_mode": "direct",
                    "retrieval_summary": retrieval_summary,
                    "evidence_items": evidence_items,
                }
                return (True, "Đã nhận câu trả lời từ Antigravity IDE (Direct) thành công.", badge, None)
            else:
                # Strict Fail-Closed: Never fallback to Smart Router
                return (False, "", None, f"Lỗi cầu nối Antigravity IDE: {direct_res.error_message}")
        except Exception as exc:
            # Strict Fail-Closed on direct crash: Never fallback to Smart Router
            return (False, "", None, f"Lỗi cầu nối Antigravity IDE: {sanitize_reason(str(exc))}")

    elif health.is_handoff_ready or health.is_available:
        user_msg = ChatMessage(
            id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
            conversation_id=conversation_id,
            role="user",
            content=user_raw_input,
        )
        save_message(user_msg)
        assistant_msg = ChatMessage(
            id=f"MSG-{uuid.uuid4().hex[:8].upper()}",
            conversation_id=conversation_id,
            role="assistant",
            content="⏳ Đang chờ Antigravity IDE xử lý...",
        )
        save_message(assistant_msg)

        from aios_habit.case_models import EvidenceItem
        ev_models = []
        for idx, ev in enumerate(evidence_items, start=1):
            if isinstance(ev, EvidenceItem):
                ev_models.append(ev)
            else:
                ev_models.append(
                    EvidenceItem(
                        evidence_id=ev.get("evidence_id", f"EVD-{idx}"),
                        case_id=conversation_id,
                        source_type=ev.get("source_type", "plain_text"),
                        source_path=ev.get("source_path", ""),
                        title=ev.get("title", f"Nguồn {idx}"),
                        extracted_text=ev.get("text", ev.get("snippet", "")),
                        privacy_level=ev.get("privacy_level", "cloud_allowed"),
                    )
                )

        try:
            write_res = write_ide_handoff_bundle(
                case_id=conversation_id,
                question=question,
                bundle_scope="current_question_retrieval_plus_full_scope_manifest",
                evidence_items=ev_models,
                owner_note=f"Sổ: {notebook_id} | Hội thoại: {conversation_id}",
                target_model_tool_name="Antigravity IDE AI",
                root=handoff_root,
                answer_language=answer_language,
            )
            if getattr(write_res, "ok", True):
                outbox_path = getattr(write_res, "outbox_dir", getattr(write_res, "bundle_dir", None))
                badge = {
                    "conversation_id": conversation_id,
                    "type": "handoff_pending",
                    "request_id": write_res.request_id,
                    "outbox_dir": str(outbox_path) if outbox_path else "",
                }
                return (True, f"Đã tạo yêu cầu chuyển giao Antigravity IDE (Mã: {write_res.request_id}).", badge, None)
            else:
                # Strict Fail-Closed
                err_msg = getattr(write_res, "error_message", "Unknown bundle creation error")
                return (False, "", None, f"Lỗi tạo gói yêu cầu Antigravity IDE: {sanitize_reason(str(err_msg))}")
        except Exception as exc:
            # Strict Fail-Closed on exception: Never fallback to Smart Router
            return (False, "", None, f"Lỗi tạo gói yêu cầu Antigravity IDE: {sanitize_reason(str(exc))}")

    else:
        # Strict Fail-Closed Policy:
        # If the Antigravity IDE Bridge is unavailable, do NOT fallback to Smart Router or mock endpoints.
        err_detail = health.reason or f"FSM: {health.status}"
        return (
            False,
            "",
            None,
            f"Cầu nối Antigravity IDE hiện không khả dụng ({sanitize_reason(err_detail)}). Hệ thống hoạt động ở chế độ fail-closed và không thể gửi yêu cầu.",
        )
