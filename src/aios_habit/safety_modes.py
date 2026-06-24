from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

SAFETY_MODE_AUTO = "Tự động"
SAFETY_MODE_COMPANY = "Tài liệu công ty / tài liệu mật"
SAFETY_MODE_NORMAL = "Tài liệu thường"

_INTERNAL_AUTO = "auto"
_INTERNAL_COMPANY = "company_safe"
_INTERNAL_NORMAL = "normal_max_ai"

SAFETY_MODE_OPTIONS = [
    SAFETY_MODE_AUTO,
    SAFETY_MODE_COMPANY,
    SAFETY_MODE_NORMAL,
]

COMPANY_SAFE_KEYWORDS = {
    "mom", "wms", "erp", "production", "factory", "company", "internal", "confidential",
    "công ty", "noi bo", "nội bộ", "san xuat", "sản xuất", "khach hang", "khách hàng",
    "tai chinh", "tài chính", "nhan su", "nhân sự", "he thong mom", "hệ thống mom",
}

NORMAL_KEYWORDS = {
    "test", "sample", "synthetic", "demo", "public", "personal", "mẫu",
    "cong khai", "công khai", "ca nhan", "cá nhân",
}

PRIVACY_TO_LABEL = {
    "local_only": SAFETY_MODE_COMPANY,
    "redacted_export": SAFETY_MODE_COMPANY,
    "cloud_allowed": SAFETY_MODE_NORMAL,
}

LABEL_TO_INTERNAL = {
    SAFETY_MODE_AUTO: _INTERNAL_AUTO,
    SAFETY_MODE_COMPANY: _INTERNAL_COMPANY,
    SAFETY_MODE_NORMAL: _INTERNAL_NORMAL,
}


def get_safety_mode_options() -> list[str]:
    return list(SAFETY_MODE_OPTIONS)


def _normalize_text_parts(parts: Iterable[Any]) -> str:
    return " ".join(str(part or "").lower() for part in parts)


def suggest_safety_mode(
    name: str = "",
    path: str | Path = "",
    notebook_name: str = "",
    source_type: str = "",
) -> str:
    haystack = _normalize_text_parts([name, path, notebook_name, source_type])
    if any(keyword in haystack for keyword in COMPANY_SAFE_KEYWORDS):
        return SAFETY_MODE_COMPANY
    if any(keyword in haystack for keyword in NORMAL_KEYWORDS):
        return SAFETY_MODE_NORMAL
    return SAFETY_MODE_AUTO


def safety_mode_to_privacy_level(mode: str, context: Mapping[str, Any] | None = None) -> str:
    if mode == SAFETY_MODE_COMPANY:
        return "local_only"
    if mode == SAFETY_MODE_NORMAL:
        return "cloud_allowed"
    if mode == SAFETY_MODE_AUTO:
        context = context or {}
        suggested = suggest_safety_mode(
            name=str(context.get("name", "")),
            path=str(context.get("path", "")),
            notebook_name=str(context.get("notebook_name", "")),
            source_type=str(context.get("source_type", "")),
        )
        if suggested == SAFETY_MODE_NORMAL:
            return "cloud_allowed"
        return "local_only"
    return "local_only"


def privacy_level_to_safety_mode_label(privacy_level: str) -> str:
    return PRIVACY_TO_LABEL.get(str(privacy_level or ""), SAFETY_MODE_AUTO)


def safety_mode_to_internal_id(mode: str) -> str:
    return LABEL_TO_INTERNAL.get(mode, _INTERNAL_AUTO)


def explain_safety_mode(mode: str) -> str:
    if mode == SAFETY_MODE_COMPANY:
        return "Tài liệu công ty/mật sẽ không gửi ra ngoài; AIOS chỉ dùng dữ liệu trong máy, AI nội bộ hoặc điểm kết nối đã tin cậy."
    if mode == SAFETY_MODE_NORMAL:
        return "AIOS có thể dùng các nguồn AI đã cấu hình để trả lời nhanh và hay hơn, trong giới hạn lượt dùng và chi phí thật."
    return "AIOS sẽ tự chọn cách xử lý an toàn nhất. Tài liệu công ty sẽ không gửi ra ngoài; tài liệu thường dùng nguồn AI tốt nhất đã cấu hình."
