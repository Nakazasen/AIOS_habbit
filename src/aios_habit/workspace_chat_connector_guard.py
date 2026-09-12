"""Fail-closed rules for Workspace Chat AI connectors."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

CONNECTORS_BLOCKING_IMAGE_FILES = frozenset({"gemini_web", "nakazasen_router"})
IMAGE_FILE_TYPES = frozenset({
    "png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "image",
})
IMAGE_FILE_SUFFIXES = frozenset(f".{name}" for name in IMAGE_FILE_TYPES if name != "image")


def connector_blocks_image_files(backend: str) -> bool:
    return str(backend or "").strip() in CONNECTORS_BLOCKING_IMAGE_FILES


def source_looks_like_image_file(source: Any) -> bool:
    source_type = str(getattr(source, "source_type", "") or "").strip().lower().lstrip(".")
    if source_type in IMAGE_FILE_TYPES:
        return True
    title = str(getattr(source, "title", "") or "").strip()
    return Path(title).suffix.lower() in IMAGE_FILE_SUFFIXES


def source_carries_image_payload(source: Any) -> bool:
    """True only when this source would put image file bytes on the wire.

    Extracted text from an image (OCR / caption) is not an image payload.
    A library that merely contains PNG/JPG files must not block a text question.
    """
    for attr in ("image_bytes", "file_bytes", "media_bytes"):
        if getattr(source, attr, None):
            return True
    text = str(getattr(source, "text", "") or "").lstrip()
    return text.startswith("data:image")


def image_files_blocked_message(backend: str, sources: Iterable[Any]) -> str | None:
    """Return a Vietnamese error if this connector would receive image files."""
    if not connector_blocks_image_files(backend):
        return None
    if any(source_carries_image_payload(source) for source in sources):
        return (
            "Gemini Web và Nakazasen Router không được gửi ảnh hay bản vẽ. "
            "Hãy dùng C-AGENT để gửi gói điều tra có hình, hoặc gỡ ảnh khỏi câu hỏi."
        )
    return None
