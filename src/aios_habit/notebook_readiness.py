"""Persistent one-line notebook status (UX-CHAT-CORE).

Replaces the confusing repeated "preparing documents" flow and the
percentage texts users could not understand. Each notebook gets exactly
one clear status line, persisted so reopening the app never asks the
user to "prepare" again:

    "Sổ X — sẵn sàng, N tài liệu"

The readiness snapshot is stored in local_cases/notebook_readiness.json
and refreshed whenever sources change; the UI only reads the snapshot.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

SNAPSHOT_FILENAME = "notebook_readiness.json"


def _snapshot_path(base_dir: Optional[Path] = None) -> Path:
    root = Path(base_dir) if base_dir is not None else Path("local_cases")
    return root / SNAPSHOT_FILENAME


@dataclass
class NotebookReadiness:
    """Persisted readiness snapshot of one notebook."""

    notebook_id: str
    san_sang: bool = False
    so_tai_lieu: int = 0
    ten_thu_vien: str = ""
    cap_nhat_luc: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotebookReadiness":
        return cls(
            notebook_id=str(data.get("notebook_id", "")),
            san_sang=bool(data.get("san_sang", False)),
            so_tai_lieu=int(data.get("so_tai_lieu", 0) or 0),
            ten_thu_vien=str(data.get("ten_thu_vien", "") or ""),
            cap_nhat_luc=float(data.get("cap_nhat_luc", 0.0) or 0.0),
        )


def dong_trang_thai_so(
    tieu_de: str,
    so_tai_lieu: int,
    san_sang: bool = True,
    ten_thu_vien: str = "",
) -> str:
    """Render the single status line shown in the sidebar and chat.

    Examples:
      "Sổ Lỗi JIG — sẵn sàng, 12 tài liệu"
      "Sổ Lỗi JIG — chưa sẵn sàng (đang nạp tài liệu)"
    """
    ten = (tieu_de or "Sổ").strip()
    if not san_sang:
        return "Sổ {} — chưa sẵn sàng (đang nạp tài liệu)".format(ten)
    dong = "Sổ {} — sẵn sàng, {} tài liệu".format(ten, max(0, int(so_tai_lieu)))
    if ten_thu_vien:
        dong += " (thư viện: {})".format(ten_thu_vien.strip())
    return dong


class NotebookReadinessStore:
    """JSON-backed store for readiness snapshots (one file, no DB needed)."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._path = _snapshot_path(base_dir)

    @property
    def path(self) -> Path:
        return self._path

    def _doc(self) -> Dict[str, Any]:
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            pass
        return {}

    def _ghi(self, data: Dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def cap_nhat(
        self,
        notebook_id: str,
        *,
        san_sang: bool,
        so_tai_lieu: int,
        ten_thu_vien: str = "",
    ) -> NotebookReadiness:
        """Save/refresh the snapshot for one notebook."""
        data = self._doc()
        snap = NotebookReadiness(
            notebook_id=notebook_id,
            san_sang=bool(san_sang),
            so_tai_lieu=max(0, int(so_tai_lieu)),
            ten_thu_vien=ten_thu_vien or "",
            cap_nhat_luc=time.time(),
        )
        data[notebook_id] = snap.to_dict()
        self._ghi(data)
        return snap

    def lay(self, notebook_id: str) -> Optional[NotebookReadiness]:
        data = self._doc()
        raw = data.get(notebook_id)
        if not isinstance(raw, dict):
            return None
        return NotebookReadiness.from_dict(raw)

    def xoa(self, notebook_id: str) -> bool:
        data = self._doc()
        if notebook_id not in data:
            return False
        del data[notebook_id]
        self._ghi(data)
        return True

    def tat_ca(self) -> List[NotebookReadiness]:
        data = self._doc()
        out = []
        for raw in data.values():
            if isinstance(raw, dict):
                out.append(NotebookReadiness.from_dict(raw))
        return out


def dong_trang_thai_tu_snapshot(
    snap: Optional[NotebookReadiness],
    tieu_de: str,
) -> str:
    """Status line from a stored snapshot (no recompute, no re-prepare)."""
    if snap is None:
        return "Sổ {} — chưa có thông tin trạng thái".format((tieu_de or "Sổ").strip())
    return dong_trang_thai_so(
        tieu_de,
        snap.so_tai_lieu,
        san_sang=snap.san_sang,
        ten_thu_vien=snap.ten_thu_vien,
    )
