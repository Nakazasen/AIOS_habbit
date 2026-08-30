"""Fail-closed conversion of dynamic UI errors to safe Vietnamese text."""
from __future__ import annotations

import re
from typing import Any


_VIETNAMESE_MARKERS = set("ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")
_ENGLISH_DIAGNOSTIC = re.compile(
    r"\b(?:connection|denied|error|exception|failed|failure|file|invalid|line|"
    r"not\s+(?:available|found)|out\s+of\s+memory|permission|refused|stack|"
    r"timed?\s*out|traceback|unavailable|unknown)\b",
    re.IGNORECASE,
)


def safe_vietnamese_ui_message(value: Any, fallback: str) -> str:
    """Return dynamic text only when it is safe and recognizably Vietnamese."""
    text = str(value or "").strip()
    lowered = text.lower()
    if not text:
        return fallback
    if (
        _ENGLISH_DIAGNOSTIC.search(text)
        or re.search(r"[A-Za-z]:[\\/]", text)
        or re.search(r"(?:^|\s)/(?:[^\s/]+/)+[^\s]+", text)
        or "\\\\" in text
        or re.search(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b", text)
    ):
        return fallback
    if re.fullmatch(r"[A-Z][A-Z0-9_]+", text):
        return fallback
    if any(marker in lowered for marker in _VIETNAMESE_MARKERS):
        return text
    # Câu không có dấu hoặc chỉ có token kỹ thuật có thể là lỗi tiếng Anh;
    # không đoán, dùng câu tiếng Việt an toàn do caller cung cấp.
    return fallback
