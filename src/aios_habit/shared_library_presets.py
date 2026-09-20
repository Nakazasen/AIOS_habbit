"""Shared library preset registry for nontech one-touch join (E5 follow-up).

English code comments by repo rule. User-facing strings stay in the UI layer.
A preset is a named published snapshot: name, description, folder path,
version, and compatibility hash. The registry scans a manifest directory so
5 or 10 stores need no code change. Join still goes through the existing
snapshot + quick_check path in workspace_chat_store.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class SharedPreset:
    name: str
    description: str
    folder: str
    version: str = "v1"
    compatibility_hash: str = ""
    doc_count: int = 0
    updated_at: str = ""


def _clean(value: Any) -> str:
    return str(value or "").strip()


def load_presets(manifest_dir: Path) -> List[SharedPreset]:
    """Scan manifest_dir for *.json presets sorted by name."""
    if not manifest_dir.exists():
        return []
    presets: List[SharedPreset] = []
    for path in sorted(manifest_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        name = _clean(data.get("name")) or path.stem
        folder = _clean(data.get("folder"))
        if not folder:
            continue
        presets.append(SharedPreset(
            name=name,
            description=_clean(data.get("description")),
            folder=folder,
            version=_clean(data.get("version")) or "v1",
            compatibility_hash=_clean(data.get("compatibility_hash")),
            doc_count=int(data.get("doc_count", 0) or 0),
            updated_at=_clean(data.get("updated_at")),
        ))
    return presets


def preset_to_dict(preset: SharedPreset) -> Dict[str, Any]:
    return {
        "name": preset.name,
        "description": preset.description,
        "folder": preset.folder,
        "version": preset.version,
        "compatibility_hash": preset.compatibility_hash,
        "doc_count": preset.doc_count,
        "updated_at": preset.updated_at,
    }


def find_preset(presets: List[SharedPreset], name: str) -> SharedPreset | None:
    wanted = _clean(name).casefold()
    return next((item for item in presets if item.name.casefold() == wanted), None)
