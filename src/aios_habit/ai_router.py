from __future__ import annotations

import time
import urllib.error
from dataclasses import dataclass, field
from typing import Callable, Any

from aios_habit.ai_provider_bridge import ProviderConfig, answer_with_provider
from aios_habit.provider_catalog import get_provider_profile, is_provider_allowed_for_safety_mode
from aios_habit.safety_modes import SAFETY_MODE_AUTO, SAFETY_MODE_COMPANY, SAFETY_MODE_NORMAL

@dataclass
class RouterRequest:
    question: str
    source_context: str
    deterministic_answer: str
    source_refs: list[dict[str, Any]] = field(default_factory=list)
    safety_mode_label: str = SAFETY_MODE_AUTO
    notebook_name: str = ""
    max_attempts: int = 3
    allow_parallel: bool = False

@dataclass
class RouterProviderConfig:
    provider_id: str
    display_name_vi: str
    endpoint_url: str = ""
    model_name: str = ""
    api_key: str = ""
    enabled: bool = False
    trusted_internal: bool = False
    priority: int = 100
    timeout_seconds: int = 30

@dataclass
class RouterAttempt:
    provider_id: str
    provider_name: str
    model_name: str = ""
    status: str = "skipped"
    reason_vi: str = ""
    latency_ms: int = 0
    error_type: str = ""

@dataclass
class RouterHealthState:
    provider_id: str
    status: str = "unknown"
    failure_count: int = 0
    cooldown_until: float = 0.0
    last_error_type: str = ""

@dataclass
class RouterResult:
    answer_text: str
    used_provider: str = "Dữ liệu cục bộ"
    used_model: str = ""
    used_fallback: bool = True
    safety_status: str = "fallback_local"
    attempts: list[RouterAttempt] = field(default_factory=list)
    route_summary_vi: str = ""
    source_refs: list[dict[str, Any]] = field(default_factory=list)

ProviderClient = Callable[[RouterProviderConfig, RouterRequest], str]

AUTH_HINTS = ("401", "403", "invalid api key", "unauthorized", "forbidden")
RATE_HINTS = ("429", "quota", "rate limit", "rate_limit")
TIMEOUT_HINTS = ("timeout", "timed out")
SERVER_HINTS = ("500", "502", "503", "504", "server error", "bad gateway")


def classify_provider_error(error: Exception | str) -> str:
    text = str(error).lower()
    if any(h in text for h in AUTH_HINTS): return "auth_error"
    if any(h in text for h in RATE_HINTS): return "rate_limited"
    if any(h in text for h in TIMEOUT_HINTS): return "timeout"
    if any(h in text for h in SERVER_HINTS): return "server_error"
    if "empty answer" in text or "không trả về" in text: return "bad_response"
    return "unknown_error"


def should_cooldown(error_type: str) -> int:
    return {"rate_limited": 600, "timeout": 120, "server_error": 120, "bad_response": 60}.get(error_type, 0)


def fallback_to_deterministic(request: RouterRequest, reason_vi: str, attempts: list[RouterAttempt] | None = None) -> RouterResult:
    result = RouterResult(request.deterministic_answer, used_fallback=True, safety_status=reason_vi, attempts=attempts or [], source_refs=request.source_refs)
    result.route_summary_vi = build_route_summary_vi(result, external_sent=False, reason_vi=reason_vi)
    return result


def _is_cloud(profile_id: str) -> bool:
    profile = get_provider_profile(profile_id)
    return bool(profile and profile.safety_scope == "normal_docs_only")


def select_candidate_providers(request: RouterRequest, provider_configs: list[RouterProviderConfig], health_state: dict[str, RouterHealthState] | None = None) -> tuple[list[RouterProviderConfig], list[RouterAttempt]]:
    health_state = health_state or {}
    attempts: list[RouterAttempt] = []
    if request.safety_mode_label == SAFETY_MODE_AUTO:
        attempts.append(RouterAttempt("auto", "Tự động", status="blocked", reason_vi="Chưa chắc loại tài liệu, AIOS chọn an toàn và không gửi ra ngoài."))
        return [], attempts
    candidates = []
    for cfg in provider_configs:
        profile = get_provider_profile(cfg.provider_id)
        if not cfg.enabled:
            attempts.append(RouterAttempt(cfg.provider_id, cfg.display_name_vi, cfg.model_name, "skipped", "Nguồn AI chưa bật hoặc chưa cấu hình.")); continue
        if not profile:
            attempts.append(RouterAttempt(cfg.provider_id, cfg.display_name_vi, cfg.model_name, "skipped", "Nguồn AI chưa có trong danh mục.")); continue
        if not is_provider_allowed_for_safety_mode(profile, request.safety_mode_label, custom_endpoint_trusted=cfg.trusted_internal):
            attempts.append(RouterAttempt(cfg.provider_id, cfg.display_name_vi, cfg.model_name, "blocked", "Không gửi ra ngoài vì đây là tài liệu công ty/mật.")); continue
        state = health_state.get(cfg.provider_id)
        if state and state.cooldown_until > time.time():
            attempts.append(RouterAttempt(cfg.provider_id, cfg.display_name_vi, cfg.model_name, "cooldown", "Nguồn AI đang tạm nghỉ do lỗi trước đó.", error_type=state.last_error_type)); continue
        candidates.append(cfg)
    candidates.sort(key=lambda c: (c.priority, 1 if _is_cloud(c.provider_id) else 0, c.display_name_vi))
    return candidates, attempts


def call_openai_compatible_provider(config: RouterProviderConfig, request: RouterRequest) -> str:
    pcfg = ProviderConfig(provider_type=config.provider_id, endpoint_url=config.endpoint_url, model_name=config.model_name, api_key=config.api_key, locality="local" if config.trusted_internal else "cloud", timeout_seconds=config.timeout_seconds, enabled=config.enabled)
    res = answer_with_provider(request.question, request.source_context, pcfg, request.deterministic_answer, request.source_refs, "cloud_allowed" if request.safety_mode_label == SAFETY_MODE_NORMAL else "local_only")
    if not res.ok:
        raise RuntimeError(res.error_message or "empty answer")
    return res.answer_text


def route_answer(request: RouterRequest, provider_configs: list[RouterProviderConfig], health_state: dict[str, RouterHealthState] | None = None, provider_client: ProviderClient | None = None) -> RouterResult:
    health_state = health_state if health_state is not None else {}
    candidates, attempts = select_candidate_providers(request, provider_configs, health_state)
    if not candidates:
        reason = "Không gửi ra ngoài vì đây là tài liệu công ty/mật." if request.safety_mode_label == SAFETY_MODE_COMPANY else "Chưa có nguồn AI nào được cấu hình. AIOS đang trả lời bằng dữ liệu cục bộ."
        return fallback_to_deterministic(request, reason, attempts)
    client = provider_client or call_openai_compatible_provider
    for cfg in candidates[:max(1, request.max_attempts)]:
        started = time.time()
        try:
            answer = client(cfg, request)
            if not str(answer).strip():
                raise RuntimeError("empty answer")
            attempts.append(RouterAttempt(cfg.provider_id, cfg.display_name_vi, cfg.model_name, "success", "Đã dùng nguồn AI phù hợp cho tài liệu thường.", round((time.time()-started)*1000)))
            result = RouterResult(answer, cfg.display_name_vi, cfg.model_name, False, "external_allowed_normal_docs", attempts, source_refs=request.source_refs)
            result.route_summary_vi = build_route_summary_vi(result, external_sent=_is_cloud(cfg.provider_id), reason_vi="Có, vì đây là tài liệu thường" if _is_cloud(cfg.provider_id) else "Không")
            return result
        except Exception as exc:
            et = classify_provider_error(exc)
            attempts.append(RouterAttempt(cfg.provider_id, cfg.display_name_vi, cfg.model_name, "failed", "Nguồn AI lỗi, AIOS thử nguồn tiếp theo.", round((time.time()-started)*1000), et))
            state = health_state.setdefault(cfg.provider_id, RouterHealthState(cfg.provider_id))
            state.failure_count += 1; state.last_error_type = et
            if et == "auth_error": state.status = "disabled"
            cd = should_cooldown(et)
            if cd: state.status = "cooldown"; state.cooldown_until = time.time() + cd
    return fallback_to_deterministic(request, "Tất cả nguồn AI đều lỗi. AIOS đang trả lời bằng dữ liệu cục bộ.", attempts)


def build_route_summary_vi(result: RouterResult, external_sent: bool | None = None, reason_vi: str = "") -> str:
    if external_sent is None:
        external_sent = result.safety_status == "external_allowed_normal_docs"
    changed = "Có" if result.used_fallback or any(a.status == "failed" for a in result.attempts) else "Không"
    lines = [
        "Nhật ký AI đã dùng",
        f"Cách xử lý: {'Trả lời bằng dữ liệu cục bộ' if result.used_fallback else 'Tự động chọn AI tốt nhất'}",
        f"Nguồn đã dùng: {result.used_provider}",
        f"Có gửi ra ngoài không: {'Có, vì đây là tài liệu thường' if external_sent else 'Không'}",
        f"Tự đổi nguồn: {changed}",
        f"Lý do: {reason_vi or result.safety_status}",
        "Các lần thử:",
    ]
    for a in result.attempts:
        lines.append(f"- {a.provider_name}: {a.status} — {a.reason_vi}")
    return "\n".join(lines)


def providers_from_env_or_session(catalog=None, session_state: dict[str, Any] | None = None) -> list[RouterProviderConfig]:
    session_state = session_state or {}
    endpoint = str(session_state.get("local_ai_endpoint", "")).strip()
    model = str(session_state.get("local_ai_model", "")).strip()
    configs = []
    if endpoint and model:
        configs.append(RouterProviderConfig("openai_compatible_local", "AI trong máy tương thích OpenAI", endpoint, model, str(session_state.get("local_ai_api_key", "")), True, True, 10, int(session_state.get("local_ai_timeout", 30))))
    return configs
