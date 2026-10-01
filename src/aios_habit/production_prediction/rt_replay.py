"""Phat lai log JIG that theo dung dong thoi gian (J1-RT, prototype mo phong).

Doc tep CSV log Iris that bang ``iris_log_adapter.doc_log_iris`` (tai dung
nguyen bo loc gia tri canh loi 999/9999 cua may), sap xep theo ``event_time``,
chuyen thanh ban tin stream va gui len server theo lo. Moi ban tin duoc gan
nhan ``nguon="SIMULATED_REALTIME"`` de phan biet ro voi du lieu that truc tiep.

Khong bia du lieu: moi gia tri deu trich tu tep that; che do mo phong chi thay
doi *thoi diem gui*, khong thay doi noi dung do.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

from .iris_log_adapter import BanGhiIris, doc_log_iris
from .stream_api import NGUON_PHAT_LAI_MO_PHONG, STREAM_PATH

#: Nhan mo phong bat buoc cho moi ban tin phat lai.
NHAN_MO_PHONG = NGUON_PHAT_LAI_MO_PHONG


def ban_tin_tu_ban_ghi_iris(ban_ghi: BanGhiIris, jig_id: str = "") -> Optional[Dict[str, Any]]:
    """Chuyen mot BanGhiIris thanh ban tin stream. Tra ve None neu khong dung duoc."""
    if ban_ghi.value is None:
        return None
    thoi_gian = ban_ghi.event_time
    return {
        "timestamp": thoi_gian.isoformat() if thoi_gian else None,
        "unit_serial": ban_ghi.unit_serial,
        "jig_id": jig_id or ban_ghi.jig_id or "unknown",
        "metric": ban_ghi.metric_name,
        "value": ban_ghi.value,
        "unit": ban_ghi.unit,
        "nguon": NHAN_MO_PHONG,
    }


def phat_lai_csv_iris(
    duong_dan: str | Path,
    jig_id: str = "",
    chi_so: Optional[Sequence[str]] = None,
    gioi_han_dong: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    """Phat lai tep CSV Iris that theo dung thu tu thoi gian do.

    - ``chi_so``: chi lay cac chi so nay (so sanh khong phan biet hoa/thuong);
      None = lay tat ca chi so do duoc.
    - ``gioi_han_dong``: gioi han so ban tin (de demo/test nhanh).
    """
    cac_ban_ghi = doc_log_iris(duong_dan)
    muon = {c.strip().upper() for c in chi_so} if chi_so else None
    da_loc: List[BanGhiIris] = []
    for ban_ghi in cac_ban_ghi:
        if ban_ghi.value is None or ban_ghi.event_time is None:
            continue
        if muon and ban_ghi.metric_name.strip().upper() not in muon:
            continue
        da_loc.append(ban_ghi)
    da_loc.sort(key=lambda b: (b.event_time, b.unit_serial, b.metric_name))
    dem = 0
    for ban_ghi in da_loc:
        if gioi_han_dong is not None and dem >= gioi_han_dong:
            break
        ban_tin = ban_tin_tu_ban_ghi_iris(ban_ghi, jig_id)
        if ban_tin is not None:
            dem += 1
            yield ban_tin


def gui_lo_len_server(
    cac_ban_tin: Iterable[Dict[str, Any]],
    base_url: str,
    auth_token: Optional[str] = None,
    kich_co_lo: int = 50,
    nghi_giua_lo_giay: float = 0.0,
    timeout_giay: float = 15.0,
    so_lan_thu_toi_da: int = 3,
) -> Dict[str, Any]:
    """Gui cac ban tin len server theo lo (JSON). Tra ve tong ket tieng Viet.

    Moi lo duoc thu lai khi gap loi mang/timeout (backoff mu 0,5s -> 1s ->
    2s, toi da ``so_lan_thu_toi_da`` lan) theo dac ta J1-RT muc 1. Loi HTTP
    (400/401/...) khong thu lai vi gui lai du lieu sai khong co tac dung.
    Nho ingestion idempotent phia server, gui lai 1 lo sau loi mang khong
    gay trung du lieu.
    """
    base_url = base_url.rstrip("/")
    tieu_de = {"Content-Type": "application/json"}
    if auth_token:
        tieu_de["Authorization"] = "Bearer " + auth_token
    tong_gui = 0
    tong_lo = 0
    lo: List[Dict[str, Any]] = []
    for ban_tin in cac_ban_tin:
        lo.append(ban_tin)
        if len(lo) >= kich_co_lo:
            tong_gui += _gui_mot_lo(base_url, tieu_de, lo, timeout_giay, so_lan_thu_toi_da)
            tong_lo += 1
            lo = []
            if nghi_giua_lo_giay > 0:
                time.sleep(nghi_giua_lo_giay)
    if lo:
        tong_gui += _gui_mot_lo(base_url, tieu_de, lo, timeout_giay, so_lan_thu_toi_da)
        tong_lo += 1
    return {"trang_thai": "Đã gửi xong", "tong_ban_tin": tong_gui, "tong_lo": tong_lo}


def _gui_mot_lo(
    base_url: str,
    tieu_de: Dict[str, str],
    lo: List[Dict[str, Any]],
    timeout_giay: float,
    so_lan_thu_toi_da: int = 3,
) -> int:
    than = json.dumps(lo, ensure_ascii=False).encode("utf-8")
    yeu_cau = urllib.request.Request(
        base_url + STREAM_PATH, data=than, headers=tieu_de, method="POST"
    )
    loi_cuoi: Optional[Exception] = None
    so_lan = max(1, int(so_lan_thu_toi_da))
    for lan in range(so_lan):
        try:
            with urllib.request.urlopen(yeu_cau, timeout=timeout_giay) as tra_loi:
                ket_qua = json.loads(tra_loi.read().decode("utf-8"))
            return int(ket_qua.get("so_dong", len(lo)))
        except urllib.error.HTTPError as exc:
            raise ValueError("Máy chủ từ chối lô dữ liệu (HTTP %d)." % exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            loi_cuoi = exc
            if lan < so_lan - 1:
                time.sleep(0.5 * (2 ** lan))  # 0,5s -> 1s -> 2s
    raise ValueError(
        "Không gửi được lô dữ liệu tới máy chủ sau %d lần thử." % so_lan
    ) from loi_cuoi