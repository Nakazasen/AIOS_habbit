"""Shared chart-selection builder for 015-csv-chart-selector.

Pure logic (no Streamlit import) so contract tests run fast.
Both the Thẻ 1 select-box UI and the Omnibar natural-language command
call into this module, guaranteeing the preview image and the email
image are built from the same data.
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from aios_habit.production_prediction.spc_chart import SpcChartInput

LOAI_BIEU_DO = ("xu_huong", "phan_bo", "so_sanh_mau")

TEN_LOAI_BIEU_DO = {
    "xu_huong": "Xu hướng theo thời gian",
    "phan_bo": "Phân bố giá trị",
    "so_sanh_mau": "So sánh theo màu",
}

TEN_CHI_SO_TIENG_VIET = {
    "BOW_VALUE": "Độ lệch chùm tia",
    "SKEW_VALUE": "Độ nghiêng chùm tia",
    "BOW": "Độ lệch chùm tia",
    "SKEW": "Độ nghiêng chùm tia",
    "BEAMDIAMETER": "Đường kính chùm tia",
    "BEAM_POS": "Vị trí chùm tia",
    "LIGHTPATH": "Đường đi ánh sáng",
}

_COT_KHONG_PHAI_CHI_SO = (
    "DATE", "TIME", "S/N", "SERIAL", "RESULT", "MODE",
    "TAKT", "TOTALTACT", "SPEC:", "LOT", "LENS", "TOTALJUDGE",
)

_GIOI_HAN_DIEM_VE = 500


def ten_tieng_viet(ma_chi_so: str) -> str:
    """Return a friendly Vietnamese name next to the raw metric code."""
    ma = (ma_chi_so or "").strip()
    if not ma:
        return "Chưa rõ chỉ số"
    upper = ma.upper()
    if ma in TEN_CHI_SO_TIENG_VIET:
        return TEN_CHI_SO_TIENG_VIET[ma]
    for khoa, ten in TEN_CHI_SO_TIENG_VIET.items():
        if khoa in upper:
            return ten
    return ma


def la_chi_so_do_duoc(ten_cot: str) -> bool:
    """Check whether a raw column holds a plottable measurement."""
    ten = (ten_cot or "").strip()
    if not ten:
        return False
    upper = ten.upper()
    for cam in _COT_KHONG_PHAI_CHI_SO:
        if upper == cam or upper.startswith(cam):
            return False
    return True


def sap_xep_chi_so_uu_tien(danh_sach_chi_so: Sequence[str]) -> List[str]:
    """Sort metrics with BOW/SKEW first, the rest alphabetically."""
    def _khoa(ten: str) -> tuple:
        upper = (ten or "").upper()
        uu_tien = 0 if ("BOW" in upper or "SKEW" in upper) else 1
        return (uu_tien, (ten or "").lower())
    return sorted(list(danh_sach_chi_so), key=_khoa)


def la_tep_depth_khong_tieu_de(duong_dan: str | Path) -> bool:
    """Detect headerless depth files (date in the first cell, no header words)."""
    try:
        with open(duong_dan, encoding="utf-8-sig", errors="replace") as f:
            dong_dau = (f.readline() or "").strip()
    except OSError:
        raise ValueError("Không mở được tệp. Vui lòng kiểm tra lại đường dẫn và quyền đọc tệp.")
    if not dong_dau:
        return False
    upper = dong_dau.upper()
    if any(tu in upper for tu in ("DATE", "TIME", "SERIAL", "JIG", "METRIC", "VALUE")):
        return False
    return bool(re.match(r"\s*\d{4}[./-]\d{2}[./-]\d{2}", dong_dau))


def doc_depth_khong_tieu_de(duong_dan: str | Path) -> List[Dict[str, Any]]:
    """Read a headerless 3-column depth file by common column positions.

    Expected positions: ngày giờ, mã sản phẩm, rồi chuỗi giá trị đo.
    Raises a Vietnamese ValueError when the file is empty or unreadable.
    """
    try:
        with open(duong_dan, encoding="utf-8-sig", errors="replace", newline="") as f:
            cac_dong = [d for d in csv.reader(f) if any((o or "").strip() for o in d)]
    except OSError:
        raise ValueError("Không mở được tệp. Vui lòng kiểm tra lại đường dẫn và quyền đọc tệp.")
    if not cac_dong:
        raise ValueError("Tệp đang trống. Vui lòng kiểm tra lại xuất log từ JIG.")
    ket_qua: List[Dict[str, Any]] = []
    for dong in cac_dong:
        if len(dong) < 3:
            continue
        gia_tri: List[float] = []
        for o in dong[2:]:
            try:
                gia_tri.append(float(str(o).strip().replace(",", ".")))
            except ValueError:
                continue
        if not gia_tri:
            continue
        ket_qua.append({
            "ngay_gio": f"{dong[0].strip()} {dong[1].strip()}".strip(),
            "ma_san_pham": dong[1].strip() if len(dong) > 2 else "",
            "gia_tri": gia_tri,
        })
    if not ket_qua:
        raise ValueError("Không nhận diện được cột giá trị đo. Vui lòng bổ sung tên cột hoặc xuất lại tệp đúng mẫu.")
    return ket_qua


def _lay_gia_tri_hang(hang: Any) -> Optional[float]:
    if isinstance(hang, dict):
        for khoa in ("value", "gia_tri", "VALUE"):
            if khoa in hang and hang[khoa] not in (None, ""):
                try:
                    return float(hang[khoa])
                except (TypeError, ValueError):
                    return None
        return None
    try:
        return float(hang)
    except (TypeError, ValueError):
        return None


def _lay_chuoi(hang: Any, *cac_khoa: str) -> str:
    if isinstance(hang, dict):
        for khoa in cac_khoa:
            if hang.get(khoa):
                return str(hang[khoa])
        return ""
    return "" if hang is None else str(hang)


def dung_du_lieu_bieu_do(
    ma_jig: str,
    ten_chi_so: str,
    cac_hang: Sequence[Any],
    loai_bieu_do: str = "xu_huong",
    nguoi_phu_trach: str = "",
) -> SpcChartInput:
    """Build a shared SpcChartInput for one JIG and one metric.

    Used by both the select-box UI and the chat command so the preview
    image and the email image never diverge.
    """
    if loai_bieu_do not in LOAI_BIEU_DO:
        raise ValueError("Loại biểu đồ chưa hợp lệ. Vui lòng chọn xu hướng, phân bố hoặc so sánh theo màu.")
    if not (ma_jig or "").strip():
        raise ValueError("Chưa chọn mã JIG. Vui lòng chọn mã JIG từ danh sách gợi ý.")
    if not (ten_chi_so or "").strip():
        raise ValueError("Chưa chọn chỉ số. Vui lòng chọn chỉ số từ danh sách gợi ý.")
    if not cac_hang:
        raise ValueError("Chưa có dữ liệu để vẽ. Vui lòng tải tệp và chờ báo dữ liệu hợp lệ.")

    ma_jig_chuan = ma_jig.strip()
    chi_so_chuan = ten_chi_so.strip()
    da_loc: List[tuple] = []
    for hang in cac_hang:
        jig_hang = _lay_chuoi(hang, "jig_id", "ma_jig", "JigNumber")
        metric_hang = _lay_chuoi(hang, "metric_name", "ten_chi_so", "metric")
        if jig_hang and jig_hang.strip() != ma_jig_chuan:
            continue
        if metric_hang and metric_hang.strip() != chi_so_chuan:
            continue
        gia_tri = _lay_gia_tri_hang(hang)
        if gia_tri is None or not math.isfinite(gia_tri):
            continue
        moc_thoi_gian = _lay_chuoi(hang, "event_time", "ngay_gio", "TIME", "DATE")
        da_loc.append((moc_thoi_gian, gia_tri))
    if not da_loc:
        raise ValueError(
            f"Không tìm thấy dữ liệu của {ten_tieng_viet(chi_so_chuan)} trên {ma_jig_chuan}. "
            "Vui lòng chọn lại JIG hoặc chỉ số từ danh sách gợi ý."
        )
    da_loc.sort(key=lambda cap: cap[0])
    cac_gia_tri = [v for _, v in da_loc[-_GIOI_HAN_DIEM_VE:]]
    nhan = [t or f"Điểm {i + 1}" for i, (t, _) in enumerate(da_loc[-_GIOI_HAN_DIEM_VE:])]
    don_vi = ""
    for hang in cac_hang:
        u = _lay_chuoi(hang, "unit", "don_vi")
        if u:
            don_vi = u
            break
    trung_binh = sum(cac_gia_tri) / len(cac_gia_tri)
    if len(cac_gia_tri) > 1:
        phuong_sai = sum((v - trung_binh) ** 2 for v in cac_gia_tri) / len(cac_gia_tri)
        do_lech = math.sqrt(phuong_sai)
    else:
        do_lech = 0.0
    return SpcChartInput(
        jig_id=ma_jig_chuan,
        cong_doan="LSU Iris",
        metric=f"{ten_tieng_viet(chi_so_chuan)} ({chi_so_chuan})",
        unit=don_vi,
        values=cac_gia_tri,
        nhan_thoi_gian=nhan,
        ucl=(trung_binh + 3 * do_lech) if do_lech > 0 else None,
        cl=trung_binh,
        lcl=(trung_binh - 3 * do_lech) if do_lech > 0 else None,
        sigma=(do_lech if do_lech > 0 else None),
        nguoi_phu_trach=nguoi_phu_trach,
    )


@dataclass
class KetQuaLenhVe:
    ma_jig: str = ""
    ten_chi_so: str = ""
    loai_bieu_do: str = "xu_huong"
    con_thieu: List[str] = field(default_factory=list)


_LOAI_TU_KHOA = (
    (("phan bo", "phân bố", "histogram", "mat do", "mật độ"), "phan_bo"),
    (("so sanh", "so sánh", "4 mau", "4 màu", "theo mau", "theo màu"), "so_sanh_mau"),
)

_CHI_SO_TU_KHOA = (
    (("do lech", "độ lệch", "bow"), "BOW_VALUE"),
    (("do nghieng", "độ nghiêng", "skew"), "SKEW_VALUE"),
    (("duong kinh", "đường kính", "beamdiameter", "beam diameter"), "BEAMDIAMETER"),
)


def _chuan_hoa_khong_dau(text: str) -> str:
    return (text or "").strip().lower()


def hieu_lenh_ve_bieu_do(
    cau_chat: str,
    danh_sach_jig: Sequence[str] = (),
    danh_sach_chi_so: Sequence[str] = (),
) -> KetQuaLenhVe:
    """Understand a Vietnamese chat request for a chart.

    Never guesses: any missing piece is reported in con_thieu so the
    caller asks back in Vietnamese instead of plotting the wrong data.
    """
    text = _chuan_hoa_khong_dau(cau_chat)
    loai = "xu_huong"
    for cum_tu, ma_loai in _LOAI_TU_KHOA:
        if any(cum in text for cum in cum_tu):
            loai = ma_loai
            break
    ma_jig_tim = ""
    for jig in danh_sach_jig:
        if jig and str(jig).strip().lower() in text:
            ma_jig_tim = str(jig).strip()
            break
    if not ma_jig_tim:
        hop = re.search(r"(2nd-\d+|jig[-\s]?\w+|bowskew[_\s]?\d*\s?beam)", text)
        if hop:
            ma_jig_tim = hop.group(1).strip().upper().replace(" ", "")
    chi_so_tim = ""
    for chi_so in danh_sach_chi_so:
        if chi_so and str(chi_so).strip().lower() in text:
            chi_so_tim = str(chi_so).strip()
            break
    if not chi_so_tim:
        for cum_tu, ma_chi_so in _CHI_SO_TU_KHOA:
            if any(cum in text for cum in cum_tu):
                chi_so_tim = ma_chi_so
                break
    con_thieu: List[str] = []
    if not ma_jig_tim:
        con_thieu.append("mã JIG")
    if not chi_so_tim:
        con_thieu.append("tên chỉ số")
    return KetQuaLenhVe(ma_jig=ma_jig_tim, ten_chi_so=chi_so_tim, loai_bieu_do=loai, con_thieu=con_thieu)
