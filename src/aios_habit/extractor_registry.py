from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class ExtractorElement:
    source_path: str
    relative_path: str
    element_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    extraction_status: str = "metadata_only"
    extractor_name: str = "metadata_fallback"
    confidence: str = "low"
    page: str = ""
    sheet: str = ""
    slide: str = ""
    image_index: str = ""


@dataclass
class AdapterStatus:
    extension: str
    extractor_name: str
    status: str
    reason: str = ""


ExtractorFunc = Callable[[Path, Path | None], list[ExtractorElement]]
_REGISTRY: dict[str, tuple[str, ExtractorFunc]] = {}


def dependency_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def metadata_only_fallback(path: str | Path, root: str | Path | None = None, *, status: str = "metadata_only", warning: str = "adapter unavailable") -> list[ExtractorElement]:
    p = Path(path)
    root_path = Path(root).resolve() if root else None
    rel = p.relative_to(root_path).as_posix() if root_path else p.name
    return [ExtractorElement(
        source_path=str(p),
        relative_path=rel,
        element_type="metadata_only",
        text="",
        metadata={"source_file": p.name, "file_type": p.suffix.lower(), "warning": warning, "_is_metadata_only": "True"},
        extraction_status=status,
        extractor_name="metadata_fallback",
        confidence="none",
    )]


def register_adapter(extension: str, extractor_name: str, func: ExtractorFunc) -> None:
    _REGISTRY[extension.lower()] = (extractor_name, func)


def adapter_status(extension: str) -> AdapterStatus:
    ext = extension.lower()
    if ext in _REGISTRY:
        return AdapterStatus(ext, _REGISTRY[ext][0], "available")
    return AdapterStatus(ext, "metadata_fallback", "dependency_missing", "no registered local adapter")


def registered_extensions() -> list[str]:
    return sorted(_REGISTRY)


def extract_with_registry(path: str | Path, root: str | Path | None = None) -> list[ExtractorElement]:
    p = Path(path)
    entry = _REGISTRY.get(p.suffix.lower())
    if not entry:
        return metadata_only_fallback(p, root, status="dependency_missing", warning="no registered adapter")
    name, func = entry
    try:
        elements = func(p, Path(root).resolve() if root else None)
    except Exception as exc:  # noqa: BLE001
        return metadata_only_fallback(p, root, status="parse_failed", warning=f"{name} failed: {type(exc).__name__}")
    if not elements:
        return metadata_only_fallback(p, root, status="empty_text", warning=f"{name} returned no elements")
    return elements


def element_to_dict(element: ExtractorElement) -> dict[str, Any]:
    return asdict(element)
