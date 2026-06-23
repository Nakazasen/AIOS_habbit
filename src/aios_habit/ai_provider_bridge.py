import ipaddress
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping, Optional


DEFAULT_ENDPOINT = "http://127.0.0.1:11434/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_CONTEXT_CHARS = 6000
MAX_SOURCE_REFS = 5


@dataclass
class ProviderConfig:
    provider_type: str = "deterministic"
    endpoint_url: str = ""
    model_name: str = ""
    api_key: str = ""
    locality: str = "local"
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    enabled: bool = False
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS


@dataclass
class ProviderResult:
    ok: bool
    answer_text: str
    provider_name: str
    model_name: str
    error_message: str = ""
    used_fallback: bool = False
    safety_status: str = "safe"


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def load_provider_config_from_env_or_session(
    session_values: Optional[Mapping[str, Any]] = None,
) -> ProviderConfig:
    """Load config from transient UI state first, then environment variables."""
    session = session_values or {}
    endpoint = str(
        session.get("local_ai_endpoint")
        or os.getenv("AIOS_LOCAL_AI_ENDPOINT", "")
    ).strip()
    model = str(
        session.get("local_ai_model")
        or os.getenv("AIOS_LOCAL_AI_MODEL", "")
    ).strip()
    api_key = str(
        session.get("local_ai_api_key")
        or os.getenv("AIOS_LOCAL_AI_API_KEY", "")
    )
    provider_type = str(
        session.get("local_ai_provider_type")
        or os.getenv("AIOS_LOCAL_AI_PROVIDER_TYPE", "openai_compatible_local" if endpoint else "deterministic")
    )
    locality = str(
        session.get("local_ai_locality")
        or os.getenv("AIOS_LOCAL_AI_LOCALITY", "local")
    ).lower()
    enabled_default = bool(endpoint and model)
    enabled = _as_bool(
        session.get("local_ai_enabled", os.getenv("AIOS_LOCAL_AI_ENABLED")),
        enabled_default,
    )
    timeout = _as_int(
        session.get("local_ai_timeout", os.getenv("AIOS_LOCAL_AI_TIMEOUT_SECONDS")),
        DEFAULT_TIMEOUT_SECONDS,
        1,
        120,
    )
    max_context = _as_int(
        session.get("local_ai_max_context_chars", os.getenv("AIOS_LOCAL_AI_MAX_CONTEXT_CHARS")),
        DEFAULT_MAX_CONTEXT_CHARS,
        1000,
        12000,
    )
    return ProviderConfig(
        provider_type=provider_type,
        endpoint_url=endpoint,
        model_name=model,
        api_key=api_key,
        locality=locality,
        timeout_seconds=timeout,
        enabled=enabled,
        max_context_chars=max_context,
    )


def is_local_endpoint(endpoint_url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(endpoint_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        hostname = parsed.hostname.lower()
        if hostname == "localhost" or hostname.endswith(".local"):
            return True
        address = ipaddress.ip_address(hostname)
        return address.is_loopback or address.is_private
    except (ValueError, TypeError):
        return False


def _bounded(value: str, limit: int) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n[ĐÃ GIỚI HẠN NGỮ CẢNH CỤC BỘ]"


def build_grounded_prompt(
    question: str,
    source_refs: list[dict[str, Any]],
    deterministic_answer: str,
    source_context: str = "",
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> str:
    refs = []
    for index, ref in enumerate((source_refs or [])[:MAX_SOURCE_REFS], 1):
        path = str(ref.get("relative_path") or ref.get("source_file") or "Nguồn chưa đặt tên")
        chunk = str(ref.get("chunk_id") or ref.get("source_id") or "Không có mã")
        refs.append(f"{index}. {path} · đoạn {chunk}")
    refs_text = "\n".join(refs) if refs else "Không có nguồn đủ mạnh."
    bounded_context = _bounded(source_context, max_context_chars)
    bounded_draft = _bounded(deterministic_answer, min(4000, max_context_chars))
    return (
        "Câu hỏi người dùng:\n"
        f"{question.strip()}\n\n"
        "Nguồn tham chiếu cục bộ (tối đa 5):\n"
        f"{refs_text}\n\n"
        "Ngữ cảnh nguồn đã giới hạn:\n"
        f"{bounded_context or 'Không có trích đoạn bổ sung.'}\n\n"
        "Bản nháp deterministic của AIOS:\n"
        f"{bounded_draft}\n\n"
        "Yêu cầu trả lời:\n"
        "- Trả lời bằng tiếng Việt, rõ ràng và hữu ích cho người vận hành.\n"
        "- Chỉ kết luận từ nguồn đã cung cấp; không suy đoán ngoài nguồn.\n"
        "- Nếu thiếu bằng chứng, phải nói rõ 'chưa đủ bằng chứng'.\n"
        "- Giữ mục 'Nguồn đã dùng' và dẫn lại số nguồn tương ứng.\n"
        "- Gồm: Tóm tắt, Điều đã xác nhận, Điểm chưa đủ bằng chứng, Việc cần kiểm tra tiếp."
    )


def _fallback(
    deterministic_answer: str,
    config: Optional[ProviderConfig],
    error_message: str,
    safety_status: str,
) -> ProviderResult:
    return ProviderResult(
        ok=False,
        answer_text=deterministic_answer,
        provider_name=(config.provider_type if config else "deterministic"),
        model_name=(config.model_name if config else ""),
        error_message=error_message,
        used_fallback=True,
        safety_status=safety_status,
    )


def _post_chat(config: ProviderConfig, user_prompt: str, max_tokens: int = 700) -> str:
    system_prompt = (
        "Bạn là trợ lý AI cục bộ của AIOS. Chỉ trả lời từ nguồn được cung cấp, "
        "không bịa dữ kiện, nói rõ khi chưa đủ bằng chứng và giữ dẫn nguồn."
    )
    payload = {
        "model": config.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    request = urllib.request.Request(
        config.endpoint_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
        data = json.loads(response.read().decode("utf-8"))
    choices = data.get("choices") or []
    content = choices[0].get("message", {}).get("content", "") if choices else ""
    if not str(content).strip():
        raise RuntimeError("Endpoint không trả về nội dung trả lời.")
    return str(content).strip()


def answer_with_provider(
    question: str,
    source_context: str,
    config: Optional[ProviderConfig],
    deterministic_answer: str,
    source_refs: Optional[list[dict[str, Any]]] = None,
    source_privacy: str = "local_only",
) -> ProviderResult:
    if config is None or not config.enabled or config.provider_type == "deterministic":
        return _fallback(
            deterministic_answer,
            config,
            "Chưa cấu hình AI cục bộ.",
            "fallback_missing_config",
        )
    if source_privacy == "local_only" and config.locality != "local":
        return _fallback(
            deterministic_answer,
            config,
            "Đã chặn gửi dữ liệu chỉ đọc cục bộ tới endpoint không cục bộ.",
            "blocked_local_only_cloud",
        )
    if config.provider_type == "antigravity_if_available" and not config.endpoint_url:
        return _fallback(
            deterministic_answer,
            config,
            "Chưa phát hiện API/MCP runtime của Antigravity.",
            "antigravity_runtime_unavailable",
        )
    if not config.endpoint_url or not config.model_name:
        return _fallback(
            deterministic_answer,
            config,
            "Thiếu endpoint cục bộ hoặc tên mô hình.",
            "fallback_missing_config",
        )
    if config.locality == "local" and not is_local_endpoint(config.endpoint_url):
        return _fallback(
            deterministic_answer,
            config,
            "Endpoint không thuộc địa chỉ cục bộ/private được phép.",
            "blocked_non_local_endpoint",
        )
    prompt = build_grounded_prompt(
        question=question,
        source_refs=source_refs or [],
        deterministic_answer=deterministic_answer,
        source_context=source_context,
        max_context_chars=config.max_context_chars,
    )
    try:
        answer_text = _post_chat(config, prompt)
        return ProviderResult(
            ok=True,
            answer_text=answer_text,
            provider_name=config.provider_type,
            model_name=config.model_name,
            used_fallback=False,
            safety_status="local_provider_ok",
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, socket.timeout, OSError, ValueError, RuntimeError) as exc:
        return _fallback(
            deterministic_answer,
            config,
            f"AI cục bộ không phản hồi: {type(exc).__name__}.",
            "fallback_provider_error",
        )


def test_provider_connection(config: ProviderConfig) -> ProviderResult:
    if not config.enabled or not config.endpoint_url or not config.model_name:
        return _fallback("", config, "Thiếu endpoint cục bộ hoặc tên mô hình.", "fallback_missing_config")
    if config.locality != "local" or not is_local_endpoint(config.endpoint_url):
        return _fallback("", config, "Chỉ cho phép kiểm tra endpoint cục bộ/private.", "blocked_non_local_endpoint")
    try:
        answer = _post_chat(
            config,
            "Kiểm tra kết nối. Chỉ trả lời đúng một từ: OK",
            max_tokens=8,
        )
        return ProviderResult(
            ok=True,
            answer_text=answer,
            provider_name=config.provider_type,
            model_name=config.model_name,
            safety_status="local_provider_ok",
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, socket.timeout, OSError, ValueError, RuntimeError) as exc:
        return _fallback(
            "",
            config,
            f"Không kết nối được AI cục bộ: {type(exc).__name__}.",
            "fallback_provider_error",
        )
