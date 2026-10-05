"""Bo chuyen doi log JIG BEAM rong sang ban tin stream chuan (RT-JIGBEAM-ADAPTER-HOME).

Log JIG BEAM (vi du ``2026_08_Master.csv`` — 677 cot, 132 dong) co cau truc
mot dong = mot lan do mot Unit, giong log Iris dang ma tran rong, nhung
ten cot thuoc ho BEAM (``TaktTime``, ``XyPosX_B``, ``Ld1H_...``) nen
``iris_log_adapter`` khong nhan ra (0/677 cot thuoc ho Iris) va
``rt_replay`` tu choi.

Module nay chi dung thu vien chuan, khong import Streamlit, khong goi mang.
Tai dung bo loc canh loi 999/9999 va cach ghep thoi gian cua
``iris_log_adapter`` de giu nhat quan voi duong Iris cu.

Che do mac dinh: ``phat_lai_csv_jigbeam`` khong loc (chi_so=None) chi lay
``TaktTime`` — moi dong 1 ban tin, dam bao 132/132 dong qua duoc, khong mat
dong, khong doi hanh vi ham Iris cu. Muon nhieu chi so thi truyen ``chi_so``
tuong minh.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

from .iris_log_adapter import chuan_hoa_ten_cot, ghep_thoi_gian, la_canh_loi
from .stream_api import NGUON_PHAT_LAI_MO_PHONG

#: Co tinh nang mo duong tu dong JIG BEAM (mac dinh TAT, fail-closed).
FLAG_ENV_KEY = "AIOS_FEATURE_JIGBEAM_ADAPTER"

#: Chi so mac dinh khi phat lai khong loc: 1 ban tin / dong, dam bao khong mat dong.
CHI_SO_MAC_DINH = ("TAKTTIME",)

_COT_NGAY = ("date",)
_COT_GIO = ("time",)
_COT_SERIAL = ("serial number", "s/n", "serial", "sn")
_COT_JIG = ("jig number", "jignumber", "jig")
_COT_KET_QUA = ("totaljudge", "result")


def co_flag_bat() -> bool:
    """True khi co ``AIOS_FEATURE_JIGBEAM_ADAPTER=1`` (mac dinh tat)."""
    return os.environ.get(FLAG_ENV_KEY, "").strip().lower() in ("1", "true", "yes", "on")


@dataclass
class BanGhiJigBeam:
    """Mot gia tri do tach ra tu mot dong log JIG BEAM."""

    unit_serial: str
    ngay: str
    gio: str
    jig_id: str
    metric_name: str
    value: Optional[float]
    unit: str = ""
    target_label: str = "UNKNOWN"
    ly_do_bo_qua: str = ""

    @property
    def event_time(self) -> Optional[datetime]:
        return ghep_thoi_gian(self.ngay, self.gio)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_serial": self.unit_serial,
            "jig_id": self.jig_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "target_label": self.target_label,
            "event_time": self.event_time.isoformat() if self.event_time else "",
            "ly_do_bo_qua": self.ly_do_bo_qua,
        }


@dataclass
class KetQuaDocJigBeam:
    """Ket qua doc mot tep log JIG BEAM."""

    loai: str = "jigbeam"
    so_dong: int = 0
    so_cot: int = 0
    ban_ghi: List[BanGhiJigBeam] = field(default_factory=list)
    bo_qua_canh_loi: int = 0
    thieu_cot: List[str] = field(default_factory=list)

    def ban_ghi_hop_le(self) -> List[BanGhiJigBeam]:
        return [b for b in self.ban_ghi if b.value is not None]


def _tim_cot(tieu_de: Sequence[str], ten_ung_vien: Sequence[str]) -> Optional[int]:
    chuan = [chuan_hoa_ten_cot(t).lower() for t in tieu_de]
    for ung_vien in ten_ung_vien:
        if ung_vien.lower() in chuan:
            return chuan.index(ung_vien.lower())
    return None


def la_log_jigbeam(tieu_de: Sequence[str]) -> bool:
    """True khi tieu de la log JIG BEAM dang rong.

    Dieu kien: >= 20 cot, co DATE + TIME + S/N, va co it nhat mot cot
    dac trung BEAM (``TaktTime`` hoac ``XyPos``). Khong doi hanh vi Iris:
    tep Iris that khong co TaktTime/XyPos nen khong bi nhan nham.
    """
    sach = [chuan_hoa_ten_cot(t) for t in tieu_de]
    if len(sach) < 20:
        return False
    if _tim_cot(sach, _COT_NGAY) is None:
        return False
    if _tim_cot(sach, _COT_GIO) is None:
        return False
    if _tim_cot(sach, _COT_SERIAL) is None:
        return False
    upper = [t.upper() for t in sach]
    return any(t == "TAKTTIME" or t.startswith("XYPOS") for t in upper)


def _doi_so(token: Any) -> Optional[float]:
    if token is None:
        return None
    chuoi = str(token).strip().replace(",", ".")
    if not chuoi or chuoi in {"-", "--", "---"}:
        return None
    try:
        return float(chuoi)
    except ValueError:
        return None


def _cot_do_jigbeam(tieu_de: Sequence[str]) -> List[int]:
    """Chi so cac cot do so (bo qua cot meta DATE/TIME/SN/Jig/ket qua/Mode)."""
    bo_qua = set()
    for nhom in (_COT_NGAY, _COT_GIO, _COT_SERIAL, _COT_JIG, _COT_KET_QUA):
        idx = _tim_cot(tieu_de, nhom)
        if idx is not None:
            bo_qua.add(idx)
    # Them cac cot meta van ban da biet (khong phai so do).
    for idx, ten in enumerate(tieu_de):
        up = chuan_hoa_ten_cot(ten).upper()
        if up in ("LD LOT NO", "LENSACAVITYNUMBER", "MODE", "BLACK_JUDGE",
                   "MAGENTA_JUDGE", "CYAN_JUDGE", "YELLOW_JUDGE"):
            bo_qua.add(idx)
    return [i for i in range(len(tieu_de)) if i not in bo_qua]


def doc_log_jigbeam(duong_dan: str | Path) -> KetQuaDocJigBeam:
    """Doc tep log JIG BEAM thanh danh sach ban ghi chuan (da bo canh loi)."""
    path = Path(duong_dan)
    ket_qua = KetQuaDocJigBeam()
    if not path.exists():
        ket_qua.thieu_cot.append("tep log (khong tim thay tep)")
        return ket_qua
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            cac_dong = [d for d in csv.reader(f) if any((o or "").strip() for o in d)]
    except (OSError, UnicodeDecodeError):
        ket_qua.thieu_cot.append("tep log (khong mo duoc tep)")
        return ket_qua
    if not cac_dong:
        ket_qua.thieu_cot.append("tep log (tep dang trong)")
        return ket_qua
    tieu_de = [chuan_hoa_ten_cot(t) for t in cac_dong[0]]
    ket_qua.so_cot = len(tieu_de)
    if not la_log_jigbeam(tieu_de):
        ket_qua.thieu_cot.append("dinh dang JIG BEAM (thieu DATE/TIME/S/N hoac TaktTime/XyPos)")
        return ket_qua
    i_serial = _tim_cot(tieu_de, _COT_SERIAL)
    i_ngay = _tim_cot(tieu_de, _COT_NGAY)
    i_gio = _tim_cot(tieu_de, _COT_GIO)
    i_jig = _tim_cot(tieu_de, _COT_JIG)
    i_ket_qua = _tim_cot(tieu_de, _COT_KET_QUA)
    if i_serial is None or i_ngay is None or i_gio is None:
        ket_qua.thieu_cot.append("DATE/TIME/SERIAL NUMBER")
        return ket_qua
    cot_do = _cot_do_jigbeam(tieu_de)
    jig_ma_dinh = path.stem
    for dong in cac_dong[1:]:
        unit_serial = (dong[i_serial] or "").strip() if i_serial < len(dong) else ""
        if not unit_serial:
            continue
        ngay = (dong[i_ngay] or "").strip() if i_ngay < len(dong) else ""
        gio = (dong[i_gio] or "").strip() if i_gio < len(dong) else ""
        jig_id = (dong[i_jig] or "").strip() if i_jig is not None and i_jig < len(dong) else ""
        if not jig_id:
            jig_id = jig_ma_dinh
        nhan = (dong[i_ket_qua] or "").strip().upper() if i_ket_qua is not None and i_ket_qua < len(dong) else ""
        if nhan not in ("OK", "NG"):
            nhan = "UNKNOWN" if not nhan else nhan
        ket_qua.so_dong += 1
        for idx in cot_do:
            if idx >= len(dong):
                continue
            token = (dong[idx] or "").strip()
            if not token:
                continue
            gia_tri = _doi_so(token)
            ten_chi_so = chuan_hoa_ten_cot(tieu_de[idx]).upper()
            if gia_tri is None:
                continue
            if la_canh_loi(gia_tri):
                ket_qua.bo_qua_canh_loi += 1
                continue
            ket_qua.ban_ghi.append(
                BanGhiJigBeam(
                    unit_serial=unit_serial, ngay=ngay, gio=gio, jig_id=jig_id,
                    metric_name=ten_chi_so, value=gia_tri,
                    target_label=nhan,
                )
            )
    return ket_qua


def ban_tin_tu_ban_ghi_jigbeam(
    ban_ghi: BanGhiJigBeam, jig_id: str = ""
) -> Optional[Dict[str, Any]]:
    """Chuyen mot BanGhiJigBeam thanh ban tin stream (None neu khong dung duoc)."""
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
        "nguon": NGUON_PHAT_LAI_MO_PHONG,
    }


def phat_lai_csv_jigbeam(
    duong_dan: str | Path,
    jig_id: str = "",
    chi_so: Optional[Sequence[str]] = None,
    gioi_han_dong: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    """Phat lai tep CSV JIG BEAM theo dung thu tu thoi gian do.

    - ``chi_so=None``: chi lay ``TaktTime`` (1 ban tin / dong, dam bao
      132/132 dong qua duoc, khong mat dong).
    - ``chi_so`` tuong minh: loc theo ten cot (khong phan biet hoa/thuong).
    """
    ket_qua = doc_log_jigbeam(duong_dan)
    if ket_qua.thieu_cot:
        raise ValueError(
            "Tep khong phai log JIG BEAM dang rong (%s). "
            "Vui long kiem tra lai tep xuat tu JIG." % ", ".join(ket_qua.thieu_cot)
        )
    muon = {c.strip().upper() for c in chi_so} if chi_so is not None else set(CHI_SO_MAC_DINH)
    da_loc: List[BanGhiJigBeam] = []
    for ban_ghi in ket_qua.ban_ghi:
        if ban_ghi.value is None or ban_ghi.event_time is None:
            continue
        if ban_ghi.metric_name.strip().upper() not in muon:
            continue
        da_loc.append(ban_ghi)
    da_loc.sort(key=lambda b: (b.event_time, b.unit_serial, b.metric_name))
    dem = 0
    for ban_ghi in da_loc:
        if gioi_han_dong is not None and dem >= gioi_han_dong:
            break
        ban_tin = ban_tin_tu_ban_ghi_jigbeam(ban_ghi, jig_id)
        if ban_tin is not None:
            dem += 1
            yield ban_tin
