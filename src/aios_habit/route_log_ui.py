from __future__ import annotations

import re
from typing import Any

RAW_REPLACEMENTS = {
    "local_only": "trong máy",
    "cloud_allowed": "tài liệu thường",
    "provider policy": "quy tắc chọn nguồn",
    "route policy": "quy tắc xử lý",
}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{6,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{10,}"),
    re.compile(r"nvapi-[A-Za-z0-9_\-]{6,}"),
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.I),
    re.compile(r"BEGIN " + r"PRIVATE KEY.*?END " + r"PRIVATE KEY", re.I | re.S),
]

STATUS_VI = {
    "success": "Thành công",
    "skipped": "Đã bỏ qua",
    "blocked": "Bị chặn an toàn",
    "failed": "Lỗi",
    "cooldown": "Đang tạm nghỉ",
    "fallback": "Đã tự đổi về dữ liệu cục bộ",
}


def sanitize_route_log_text(text: Any) -> str:
    value = str(text or "")
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[đã ẩn]", value)
    for raw, friendly in RAW_REPLACEMENTS.items():
        value = re.sub(re.escape(raw), friendly, value, flags=re.I)
    return value.strip()


def route_attempt_status_to_vi(status: str) -> str:
    return STATUS_VI.get(str(status or "").strip().lower(), "Chưa rõ")


def external_status_to_vi(external_sent: bool, safety_status: str = "") -> str:
    if external_sent:
        return "Có dùng nguồn AI ngoài vì đây là tài liệu thường"
    if "công ty/mật" in str(safety_status).lower():
        return "Không gửi ra ngoài"
    return "Không gửi ra ngoài"


def _meta_value(meta: Any, key: str, default: Any = "") -> Any:
    if isinstance(meta, dict):
        return meta.get(key, default)
    return getattr(meta, key, default)


def _attempts_from_meta(meta: Any) -> list[dict[str, Any]]:
    attempts = _meta_value(meta, "attempts", []) or []
    normalized = []
    for item in attempts:
        if isinstance(item, dict):
            normalized.append(item)
        else:
            normalized.append({
                "provider_id": getattr(item, "provider_id", ""),
                "provider_name": getattr(item, "provider_name", ""),
                "model_name": getattr(item, "model_name", ""),
                "status": getattr(item, "status", ""),
                "reason_vi": getattr(item, "reason_vi", ""),
                "latency_ms": getattr(item, "latency_ms", 0),
            })
    return normalized


def format_route_log_for_ui(router_result_or_provider_meta: Any) -> dict[str, Any]:
    meta = router_result_or_provider_meta or {}
    used_fallback = bool(_meta_value(meta, "used_fallback", True))
    safety_status = sanitize_route_log_text(_meta_value(meta, "safety_status", ""))
    provider = sanitize_route_log_text(_meta_value(meta, "used_provider", "") or _meta_value(meta, "provider_name", "") or "Dữ liệu cục bộ")
    model = sanitize_route_log_text(_meta_value(meta, "used_model", "") or _meta_value(meta, "model_name", ""))
    route_summary = sanitize_route_log_text(_meta_value(meta, "route_summary_vi", ""))
    external_sent = "Có, vì đây là tài liệu thường" in route_summary or safety_status == "external_allowed_normal_docs"
    attempts = []
    any_failed = False
    for attempt in _attempts_from_meta(meta):
        status = sanitize_route_log_text(attempt.get("status", ""))
        any_failed = any_failed or status.lower() in {"failed", "cooldown", "blocked"}
        attempts.append({
            "source": sanitize_route_log_text(attempt.get("provider_name") or attempt.get("provider_id") or "Nguồn AI"),
            "status_vi": route_attempt_status_to_vi(status),
            "reason_vi": sanitize_route_log_text(attempt.get("reason_vi", "")),
            "latency_ms": int(attempt.get("latency_ms") or 0),
            "is_technical": False,
        })
    if used_fallback:
        summary_badge = "Tự đổi về dữ liệu cục bộ" if attempts else "Xử lý trong máy"
        fallback_status = "Đã tự đổi nguồn"
        reason = "Chưa có nguồn AI phù hợp hoặc nguồn AI lỗi. AIOS đã tự trả lời bằng dữ liệu cục bộ."
    elif external_sent:
        summary_badge = "Đã dùng nguồn AI ngoài"
        fallback_status = "Không cần tự đổi nguồn" if not any_failed else "Đã tự đổi nguồn"
        reason = "Tài liệu thường: AIOS được phép dùng nguồn AI đã cấu hình."
    else:
        summary_badge = "Xử lý trong máy"
        fallback_status = "Không cần tự đổi nguồn" if not any_failed else "Đã tự đổi nguồn"
        reason = "Tài liệu này được xử lý theo chế độ công ty/mật nên không gửi ra ngoài."
    if safety_status and not external_sent and "công ty/mật" in safety_status.lower():
        reason = "Tài liệu này được xử lý theo chế độ công ty/mật nên không gửi ra ngoài."
    return {
        "title": "Nhật ký AI đã dùng",
        "summary_badge": summary_badge,
        "external_status": external_status_to_vi(external_sent, safety_status),
        "main_provider": provider,
        "model": model,
        "fallback_status": fallback_status,
        "reason": sanitize_route_log_text(reason),
        "attempts": attempts,
        "safe_for_main_ui": True,
    }
