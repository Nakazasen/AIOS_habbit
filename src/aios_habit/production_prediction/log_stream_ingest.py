"""Nap log dang stream: KHONG cat bo o 50k dong nhu truoc.

Van de user hoi 2026-10-03: dan log lon bi `ghi_ban_ghi` cat o 50.000 dong,
phan duoi (`bi_cat`) bi LOAI BO chu khong luu. Module nay nap HET theo tung
dot (chunk), bao tien trinh, ho tro doc file lon theo dong + resume.

- `nap_stream(records, *, ghi_chunk, ...)`: nhan iterable ban ghi, ghi theo
  chunk qua ham `ghi_chunk` duoc chi dinh (ghi_ban_ghi / ghi_dong_log_jig).
- `nap_file_log(path, ...)`: generator doc file theo chunk dong, tu nhan dien
  dinh dang (jig_line / iris / depth), checkpoint de resume khi nap do.

Tuong thich Python 3.11.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional

CHUNK_DONG_MAC_DINH = 10_000


def checkpoint_file() -> Path:
    base = Path(os.environ.get("AIOS_LOCAL_CASES_DIR", "") or Path.cwd() / "local_cases")
    return base / "log_stream_checkpoint.json"


def nap_stream(
    records: Iterable[Any],
    *,
    ghi_chunk: Callable[[List[Any]], Dict[str, Any]],
    chunk: int = CHUNK_DONG_MAC_DINH,
    tien_trinh: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Nap het records theo tung dot. Khong bao gio cat bo nhu gioi han 50k."""
    chunk = max(1, int(chunk or CHUNK_DONG_MAC_DINH))
    tong = {"da_ghi": 0, "bo_qua_rong": 0, "bi_cat": 0, "dot": 0}
    dem = []
    for ban_ghi in records:
        dem.append(ban_ghi)
        if len(dem) >= chunk:
            ket_qua = ghi_chunk(dem)
            _cong_don(tong, ket_qua)
            tong["dot"] += 1
            if tien_trinh:
                tien_trinh(dict(tong))
            dem = []
    if dem:
        ket_qua = ghi_chunk(dem)
        _cong_don(tong, ket_qua)
        tong["dot"] += 1
        if tien_trinh:
            tien_trinh(dict(tong))
    return tong


def _cong_don(tong: Dict[str, Any], ket_qua: Dict[str, Any]) -> None:
    for khoa in ("da_ghi", "bo_qua_rong", "bi_cat"):
        try:
            tong[khoa] += int(ket_qua.get(khoa, 0) or 0)
        except (TypeError, ValueError):
            pass


def _nhan_dien_dinh_dang(dong_dau: List[str]) -> str:
    """Tra ve 'jig_line' | 'iris' | 'depth' | 'la'. """
    from aios_habit.production_prediction.iris_log_adapter import (
        nhan_dien_khoi_log_dan,
    )
    from aios_habit.production_prediction.jig_log_ingest import (
        is_jig_log_line,
        la_dong_log_iris_that,
    )

    mau = "\n".join(dong_dau[:20])
    for dong in dong_dau:
        if dong.strip():
            if is_jig_log_line(dong):
                return "jig_line"
            if la_dong_log_iris_that(dong):
                return "iris"
            break
    if nhan_dien_khoi_log_dan(mau) == "depth":
        return "depth"
    return "la"


def _doc_checkpoint() -> Dict[str, Any]:
    path = checkpoint_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def _ghi_checkpoint(path: Path, dong_da_doc: int) -> None:
    record = {
        "path": str(path),
        "size": path.stat().st_size,
        "dong_da_doc": dong_da_doc,
        "cap_nhat": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    cp = checkpoint_file()
    cp.parent.mkdir(parents=True, exist_ok=True)
    try:
        du_lieu = _doc_checkpoint()
    except OSError:
        du_lieu = {}
    du_lieu[str(path.resolve())] = record
    cp.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=1), encoding="utf-8")


def _dong_da_doc_truoc(path: Path) -> int:
    du_lieu = _doc_checkpoint()
    ban_ghi = du_lieu.get(str(path.resolve()))
    if not ban_ghi:
        return 0
    try:
        if int(ban_ghi.get("size", -1)) != path.stat().st_size:
            return 0  # File doi thi nap lai tu dau cho an toan.
        return max(0, int(ban_ghi.get("dong_da_doc", 0)))
    except (TypeError, ValueError, OSError):
        return 0


def nap_file_log(
    path: str | Path,
    *,
    kho: str | Path | None = None,
    chunk_dong: int = CHUNK_DONG_MAC_DINH,
    nguon: str = "tep",
    resume: bool = True,
) -> Iterator[Dict[str, Any]]:
    """Generator nap file log theo stream. Yield tien trinh moi dot, cuoi la tong ket.

    Moi yield: {"tien_trinh"/"xong": True, "dot": n, "da_doc": lines,
    "da_ghi": n, "bo_qua_rong": n, "dinh_dang": ...}.
    """
    from aios_habit.production_prediction.iris_log_adapter import (
        parse_khoi_depth_dan,
    )
    from aios_habit.production_prediction.jig_log_ingest import (
        parse_dong_log_iris_dan,
        parse_jig_log_line,
    )
    from aios_habit.production_prediction.log_archive import (
        MAC_DINH_KHO_PATH,
        ghi_ban_ghi,
        ghi_dong_log_jig,
    )

    tep = Path(path)
    if not tep.is_file():
        yield {"xong": True, "ok": False, "error_vi": f"Không tìm thấy file: {path}."}
        return
    kho_dung = kho if kho is not None else MAC_DINH_KHO_PATH

    dong_bo_qua = _dong_da_doc_truoc(tep) if resume else 0
    dinh_dang: Optional[str] = None
    da_doc = 0
    tong = {"da_ghi": 0, "bo_qua_rong": 0, "bi_cat": 0, "dot": 0}
    dem_dong: List[str] = []

    def _xa_chunk() -> Dict[str, Any]:
        nonlocal dinh_dang
        if dinh_dang is None:
            dinh_dang = _nhan_dien_dinh_dang(dem_dong)
        if dinh_dang == "jig_line":
            ban_ghi = [r for dong in dem_dong if (r := parse_jig_log_line(dong)) is not None]
            ket_qua = ghi_dong_log_jig(ban_ghi, kho=kho_dung, nguon=nguon)
        elif dinh_dang == "iris":
            ket_qua = ghi_ban_ghi(
                parse_dong_log_iris_dan("\n".join(dem_dong)).ban_ghi_hop_le(),
                nguon=nguon, tep=tep.name, kho=kho_dung,
            )
        elif dinh_dang == "depth":
            ket_qua = ghi_ban_ghi(
                parse_khoi_depth_dan("\n".join(dem_dong)).ban_ghi_hop_le(),
                nguon=nguon, tep=tep.name, kho=kho_dung,
            )
        else:
            ket_qua = {"da_ghi": 0, "bo_qua_rong": len(dem_dong), "bi_cat": 0}
        _cong_don(tong, ket_qua)
        tong["dot"] += 1
        return {"tien_trinh": True, **tong, "da_doc": da_doc, "dinh_dang": dinh_dang}

    try:
        with tep.open("r", encoding="utf-8", errors="replace") as handle:
            for dong in handle:
                da_doc += 1
                if da_doc <= dong_bo_qua:
                    continue
                dem_dong.append(dong.rstrip("\n"))
                if len(dem_dong) >= chunk_dong:
                    tien = _xa_chunk()
                    _ghi_checkpoint(tep, da_doc)
                    yield tien
                    dem_dong = []
            if dem_dong:
                tien = _xa_chunk()
                _ghi_checkpoint(tep, da_doc)
                yield tien
    except OSError as exc:
        yield {"xong": True, "ok": False, "error_vi": f"Không đọc được file: {exc}."}
        return
    yield {
        "xong": True, "ok": True, **tong, "da_doc": da_doc,
        "dinh_dang": dinh_dang or "la",
        "tiep_tuc_tu_dong": dong_bo_qua,
    }
