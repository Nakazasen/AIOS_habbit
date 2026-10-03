"""Threshold alerts configured from chat (UX-CHAT-CORE).

The user types e.g. "cảnh báo khi nhiệt độ vượt 80" directly in the chat box:
this module parses the command, persists the rule, and immediately checks
it against recent data using the SMA(20) trend logic from
production_prediction.trend_alerts (alert only on trend, never on a single
bad point — user decision 2026-10-03).

Rules live in local_cases/threshold_rules.json (JSON, atomic write).
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

RULES_FILENAME = "threshold_rules.json"


def _snapshot_path(base_dir: Optional[Path] = None) -> Path:
    root = Path(base_dir) if base_dir is not None else Path("local_cases")
    return root / RULES_FILENAME


def _khong_dau(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").strip()


@dataclass
class QuyTacCanhBao:
    """One persisted threshold rule."""

    id: str
    thong_so: str
    phep_so_sanh: str  # ">" or "<"
    nguong: float
    tao_luc: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuyTacCanhBao":
        return cls(
            id=str(data.get("id", "")),
            thong_so=str(data.get("thong_so", "")),
            phep_so_sanh=str(data.get("phep_so_sanh", ">")),
            nguong=float(data.get("nguong", 0.0)),
            tao_luc=float(data.get("tao_luc", 0.0) or 0.0),
        )

    def mo_ta(self) -> str:
        dau = "vượt" if self.phep_so_sanh == ">" else "dưới"
        nguong_txt = ("%g" % self.nguong)
        return "cảnh báo khi {} {} {}".format(self.thong_so, dau, nguong_txt)


# "cảnh báo khi nhiệt độ vượt 80" / "cảnh báo khi áp suất < 5 bar" ...
_MAU_CANH_BAO = re.compile(
    r"cảnh báo khi\s+(.+?)\s+"
    r"(vượt|vuot|lớn hơn|lon hon|cao hơn|cao hon|>|>=|dưới|duoi|nhỏ hơn|nho hon|thấp hơn|thap hon|<|<=)\s*"
    r"([0-9]+(?:[.,][0-9]+)?)",
    re.IGNORECASE,
)
# "đặt ngưỡng nhiệt độ 80" / "thiết lập ngưỡng áp suất dưới 5"
_MAU_DAT_NGUONG = re.compile(
    r"(?:đặt|dat|thiết lập|thiet lap)\s+ngưỡng\s+(.+?)\s+"
    r"(?:(vượt|vuot|dưới|duoi)\s+)?([0-9]+(?:[.,][0-9]+)?)",
    re.IGNORECASE,
)
_MAU_LIET_KE = re.compile(r"liệt kê cảnh báo|liet ke canh bao|danh sách cảnh báo", re.IGNORECASE)
_MAU_XOA = re.compile(r"(?:xóa|hủy|tắt)\s+cảnh báo\s+(\S+)", re.IGNORECASE)

_PHEP_TREN = {"vượt", "vuot", "lớn hơn", "lon hon", "cao hơn", "cao hon", ">", ">="}
_PHEP_DUOI = {"dưới", "duoi", "nhỏ hơn", "nho hon", "thấp hơn", "thap hon", "<", "<="}


def _chuan_hoa_phep(tu: str) -> Optional[str]:
    n = _khong_dau(tu)
    if n in _PHEP_TREN:
        return ">"
    if n in _PHEP_DUOI:
        return "<"
    return None


def parse_lenh_canh_bao(text: str) -> Optional[Dict[str, Any]]:
    """Parse "cảnh báo khi X vượt Y" style commands.

    Returns {"thong_so", "phep_so_sanh", "nguong"} or None.
    """
    clean = (text or "").strip()
    m = _MAU_CANH_BAO.search(clean)
    if m:
        phep = _chuan_hoa_phep(m.group(2))
        if phep is None:
            return None
        return {
            "thong_so": m.group(1).strip(),
            "phep_so_sanh": phep,
            "nguong": float(m.group(3).replace(",", ".")),
        }
    m = _MAU_DAT_NGUONG.search(clean)
    if m:
        tu_phep = (m.group(2) or "").strip()
        phep = _chuan_hoa_phep(tu_phep) if tu_phep else ">"
        if phep is None:
            return None
        return {
            "thong_so": m.group(1).strip(),
            "phep_so_sanh": phep,
            "nguong": float(m.group(3).replace(",", ".")),
        }
    return None


def la_lenh_liet_ke(text: str) -> bool:
    return bool(_MAU_LIET_KE.search(text or ""))


def parse_lenh_xoa(text: str) -> Optional[str]:
    m = _MAU_XOA.search(text or "")
    return m.group(1).strip() if m else None


class KhoQuyTacCanhBao:
    """JSON-backed rule store (atomic replace on write)."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._path = _snapshot_path(base_dir)

    @property
    def path(self) -> Path:
        return self._path

    def _doc(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [d for d in data if isinstance(d, dict)]
        except (OSError, ValueError):
            pass
        return []

    def _ghi(self, rules: List[Dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def them(self, thong_so: str, phep_so_sanh: str, nguong: float) -> QuyTacCanhBao:
        rules = self._doc()
        rule = QuyTacCanhBao(
            id="CB-" + uuid.uuid4().hex[:6].upper(),
            thong_so=thong_so.strip(),
            phep_so_sanh=phep_so_sanh,
            nguong=float(nguong),
            tao_luc=time.time(),
        )
        rules.append(rule.to_dict())
        self._ghi(rules)
        return rule

    def liet_ke(self) -> List[QuyTacCanhBao]:
        return [QuyTacCanhBao.from_dict(d) for d in self._doc()]

    def xoa(self, rule_id: str) -> bool:
        rules = self._doc()
        giu = [d for d in rules if str(d.get("id", "")).upper() != rule_id.upper()]
        if len(giu) == len(rules):
            return False
        self._ghi(giu)
        return True


def kiem_tra_quy_tac(
    rule: QuyTacCanhBao,
    chuoi: Sequence[float],
    window: int = 20,
) -> Dict[str, Any]:
    """Evaluate one rule against a value series.

    Combines the hard threshold with the SMA(20) trend gate: a rule fires
    only when the latest value crosses the threshold AND the SMA trend
    analysis sees an abnormal trend (no alert on a single bad point).
    """
    from aios_habit.production_prediction.trend_alerts import (
        danh_gia_xu_huong_sma,
    )

    gia_tri = [float(v) for v in chuoi if isinstance(v, (int, float))]
    if not gia_tri:
        return {
            "kich_hoat": False,
            "ly_do": "Chưa có dữ liệu cho thông số '{}'.".format(rule.thong_so),
        }
    moi_nhat = gia_tri[-1]
    vuot_cung = (moi_nhat > rule.nguong) if rule.phep_so_sanh == ">" else (moi_nhat < rule.nguong)
    xu_huong = danh_gia_xu_huong_sma(gia_tri, window=window)
    if vuot_cung and xu_huong.get("canh_bao"):
        return {
            "kich_hoat": True,
            "ly_do": (
                "Giá trị mới nhất {} đã {} ngưỡng {} và có xu hướng bất thường "
                "theo SMA({}): {}"
            ).format(
                moi_nhat,
                "vượt" if rule.phep_so_sanh == ">" else "xuống dưới",
                rule.nguong,
                window,
                xu_huong.get("chi_tiet", ""),
            ),
        }
    if vuot_cung:
        return {
            "kich_hoat": False,
            "ly_do": (
                "Giá trị mới nhất {} đã {} ngưỡng {} nhưng chưa thành xu hướng "
                "theo SMA({}) — theo dõi thêm, chưa cảnh báo."
            ).format(
                moi_nhat,
                "vượt" if rule.phep_so_sanh == ">" else "xuống dưới",
                rule.nguong,
                window,
            ),
        }
    return {
        "kich_hoat": False,
        "ly_do": "Giá trị mới nhất {} còn trong ngưỡng {}.".format(moi_nhat, rule.nguong),
    }


def xu_ly_cau_lenh(
    text: str,
    history_provider: Optional[Callable[[str], List[float]]] = None,
    base_dir: Optional[Path] = None,
) -> Optional[str]:
    """Full chat pipeline for threshold commands.

    Returns the Vietnamese reply text, or None if the text is not a
    threshold command at all.
    """
    clean = (text or "").strip()
    kho = KhoQuyTacCanhBao(base_dir)

    if la_lenh_liet_ke(clean):
        rules = kho.liet_ke()
        if not rules:
            return "Hiện chưa có quy tắc cảnh báo ngưỡng nào. Bạn gõ ví dụ: cảnh báo khi nhiệt độ vượt 80"
        dong = ["Các quy tắc cảnh báo ngưỡng đang theo dõi:"]
        for r in rules:
            dong.append("- {}: {}".format(r.id, r.mo_ta()))
        return "\n".join(dong)

    rule_id = parse_lenh_xoa(clean)
    if rule_id:
        if kho.xoa(rule_id):
            return "Đã xóa quy tắc {}.".format(rule_id.upper())
        return "Không tìm thấy quy tắc {}. Bạn gõ 'liệt kê cảnh báo' để xem danh sách.".format(rule_id.upper())

    parsed = parse_lenh_canh_bao(clean)
    if parsed is None:
        return None

    rule = kho.them(parsed["thong_so"], parsed["phep_so_sanh"], parsed["nguong"])
    tra_loi = ["Đã lưu quy tắc {}: {}.".format(rule.id, rule.mo_ta())]

    chuoi: List[float] = []
    if history_provider is not None:
        try:
            chuoi = [float(v) for v in (history_provider(rule.thong_so) or [])]
        except Exception:
            chuoi = []
    ket_qua = kiem_tra_quy_tac(rule, chuoi)
    tra_loi.append(ket_qua["ly_do"])
    if ket_qua["kich_hoat"]:
        tra_loi.append("⚠️ CẢNH BÁO: quy tắc này đang kích hoạt.")
    return "\n".join(tra_loi)


VI_DU_CANH_BAO = "Ví dụ: cảnh báo khi nhiệt độ vượt 80"
