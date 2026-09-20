"""Per-upload chunking config for Lite-CPU pilot (E5).

English code comments by repo rule; user-facing strings stay Vietnamese
in the UI layer, not here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class UploadChunkConfig:
    """Small, CPU-safe per-batch override."""

    parser: str = "default"
    max_chars: int = 900
    style_override: str = ""
    graph_manual: bool = False
    graph_workers: int = 1


_ALLOWED_PARSERS = frozenset({"default", "office", "ocr-text"})
_ALLOWED_STYLES = frozenset({"", "heading", "heuristic", "recursive"})


def validate_upload_config(config: UploadChunkConfig) -> Dict[str, Any]:
    """Validate config and return a sanitized summary dict."""
    if config.parser not in _ALLOWED_PARSERS:
        raise ValueError(f"unknown parser: {config.parser!r}")
    if config.style_override not in _ALLOWED_STYLES:
        raise ValueError(f"unknown style: {config.style_override!r}")
    if not 80 <= config.max_chars <= 1000:
        raise ValueError("max_chars must stay within 80..1000 for CPU safety")
    if config.graph_workers < 1 or config.graph_workers > 1:
        raise ValueError("graph_workers must be 1 on i5 pilot")
    return {
        "parser": config.parser,
        "max_chars": config.max_chars,
        "style_override": config.style_override or "auto",
        "graph_manual": config.graph_manual,
        "graph_workers": 1,
    }
