# -*- coding: utf-8 -*-
"""Luu tru phien lam viec bieu do va quan ly tep log dinh kem theo hoi thoai.

Nhiem vu:
- Luu tep log da nap tai `local_cases/log_chart_files/<file_hash>_<file_name>`.
- Luu trang thai ChartSpec & ParsedLogTable tai `local_cases/log_chart_sessions/<conversation_id>.json`.
- Cho phep hoi thoai tiep theo cap nhat cung bieu do do ("them duong SMA(20)", "chi xem line 2").
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from aios_habit.log_chart.parser import ParsedLogTable, parse_log_file
from aios_habit.log_chart.spec import ChartSpec


def _base_dir() -> Path:
    env_p = os.environ.get("AIOS_LOCAL_CASES_DIR", "")
    if env_p:
        p = Path(env_p)
    else:
        p = Path.cwd() / "local_cases"
    return p


def files_dir() -> Path:
    d = _base_dir() / "log_chart_files"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sessions_dir() -> Path:
    d = _base_dir() / "log_chart_sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_log_file_bytes(file_name: str, raw_bytes: bytes) -> Tuple[str, Path]:
    """Luu tep log len may de dung lai trong phien lam viec."""
    h = hashlib.sha256(raw_bytes).hexdigest()[:12]
    clean_name = Path(file_name).name.replace(" ", "_")
    target_path = files_dir() / f"{h}_{clean_name}"
    target_path.write_bytes(raw_bytes)
    return h, target_path


def save_chart_session(conversation_id: str, spec: ChartSpec, file_path: Path) -> None:
    """Luu ChartSpec va duong dan tep log cho cuoc hoi thoai."""
    session_file = sessions_dir() / f"{conversation_id}.json"
    data = {
        "conversation_id": conversation_id,
        "file_path": str(file_path),
        "spec": spec.to_dict(),
    }
    session_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_chart_session(conversation_id: str) -> Optional[Tuple[ChartSpec, ParsedLogTable, Path]]:
    """Tai ChartSpec va ParsedLogTable cua cuoc hoi thoai."""
    session_file = sessions_dir() / f"{conversation_id}.json"
    if not session_file.exists():
        return None

    try:
        data = json.loads(session_file.read_text(encoding="utf-8"))
        fpath = Path(data.get("file_path", ""))
        if not fpath.exists():
            return None
        spec = ChartSpec.from_dict(data.get("spec", {}))
        table = parse_log_file(fpath)
        return spec, table, fpath
    except Exception:
        return None
