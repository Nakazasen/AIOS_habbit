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


def _nhan_chi_so(chi_so: str) -> str:
    """Nhãn chỉ số cho biểu đồ, tránh lặp lại mã chỉ số hai lần.

    Tên chỉ số của log Iris (``BOW:BLACK:0``, ``DEPTH:BEAM:H:LD1:…``) đã đủ rõ và
    không có tên Việt tương ứng, nên giữ nguyên. Chỉ ghép ``tên (mã)`` cho các mã
    chỉ số ngắn có bảng tên Việt (``BOW_VALUE``).
    """
    if ":" in (chi_so or ""):
        return chi_so
    ten_viet = ten_tieng_viet(chi_so)
    if ten_viet and ten_viet != chi_so:
        return f"{ten_viet} ({chi_so})"
    return chi_so


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


_BANG_DON_VI_THEO_CHI_SO = {
    "BOW": "um",
    "SKEW": "um",
    "LIGHT_PATH": "mm",
    "BEAM_DIAMETER:H": "um",
    "BEAM_DIAMETER:V": "um",
    "BEAM_POS:X": "um",
    "BEAM_POS:Y": "um",
    "APC:CURRENT": "mA",
    "APC:VOLTAGE": "V",
}


def ma_chi_so_chuan(ten_chi_so: str) -> str:
    """Quy tên chỉ số của log Iris về mã chỉ số dùng để tra ngưỡng.

    ``BOW:BLACK:0`` → ``BOW``; ``BEAM_DIAMETER:H:BLACK:-140:0:LD1`` →
    ``BEAM_DIAMETER:H``; ``BEAM_POS:X:BLACK:-140:LD1`` → ``BEAM_POS:X``;
    ``APC:CURRENT`` → ``APC:CURRENT``.

    Cột ``Current[mA]``/``Voltage[V]`` của log 2ND-1004 là cùng đại lượng mà tệp
    Spec gọi là ``Spec:Current``/``Spec:Voltage``, nên phải quy về cùng khoá; nếu
    không, ngưỡng thật sẽ không bao giờ gặp giá trị đo tương ứng.
    """
    ten = (ten_chi_so or "").strip().upper()
    if not ten:
        return ""
    ten = re.sub(r"\[[^\]]*\]", "", ten).strip()  # bỏ phần đơn vị
    if ten.startswith("SPEC:"):
        ten = ten.split(":", 1)[1]
    phan = [p for p in ten.split(":") if p]
    phan = [p for p in phan if p not in ("LOWER", "UPPER")]
    if not phan:
        return ""
    goc = phan[0]
    if goc == "LIGHTPATH":
        goc = "LIGHT_PATH"
    if goc == "BEAMDIAMETER":
        goc = "BEAM_DIAMETER"
    if goc == "BEAMPOS":
        goc = "BEAM_POS"
    # Dạng camelCase không có dấu hai chấm: ``BeamPosX`` → ``BEAM_POS:X``.
    hop_pos = re.match(r"^BEAM_?POS([XY])$", goc)
    if hop_pos:
        return f"BEAM_POS:{hop_pos.group(1)}"
    hop_dia = re.match(r"^BEAM_?DIAMETER([HV])$", goc)
    if hop_dia:
        return f"BEAM_DIAMETER:{hop_dia.group(1)}"
    if goc in ("CURRENT", "VOLTAGE"):
        return f"APC:{goc}"
    # Chỉ số có hai thành phần phân biệt: hướng/trục của chùm tia, hoặc loại APC.
    if goc in ("BEAM_DIAMETER", "BEAM_POS", "APC") and len(phan) > 1:
        return f"{goc}:{phan[1]}"
    return goc


def cac_khoa_nguong(ten_chi_so: str) -> List[str]:
    """Trả các khoá ngưỡng nên thử, từ **cụ thể nhất tới tổng quát nhất**.

    Chỉ số đo sâu mang cả vị trí trục (``DEPTH:BEAM:H:LD1:IMGHEIGHT:-140:CAM-2``).
    Người dùng thường đặt ngưỡng cho **cả dòng** (``…:IMGHEIGHT:-140``) chứ không
    cho từng cột, nên phải thử lần lượt: mã chuẩn → tên đầy đủ → tên bỏ hậu tố
    trục ``:CAM…`` → tên bỏ cả vị trí cuối. Nhờ vậy một ngưỡng đặt cho dòng vẫn
    áp được cho mọi cột của dòng đó, mà ngưỡng đặt riêng cho một cột vẫn thắng.
    """
    ten = re.sub(r"\[[^\]]*\]", "", (ten_chi_so or "").strip().upper()).strip()
    if not ten:
        return []
    ung_vien: List[str] = []

    def _them(gia_tri: str) -> None:
        if gia_tri and gia_tri not in ung_vien:
            ung_vien.append(gia_tri)

    _them(ten)
    khong_cam = re.sub(r":CAM[+-]?\d+$", "", ten)
    _them(khong_cam)
    phan = [p for p in khong_cam.split(":") if p]
    if len(phan) > 1:
        _them(":".join(phan[:-1]))
    _them(ma_chi_so_chuan(ten))
    return ung_vien


def tra_nguong_theo_chi_so(
    kho_nguong: Any,
    ma_jig: str,
    ten_chi_so: str,
    unit_serial: str = "",
    luc_do: Any = None,
) -> Any:
    """Tra ngưỡng theo thứ tự khoá từ cụ thể tới tổng quát (xem ``cac_khoa_nguong``)."""
    if kho_nguong is None:
        return None
    for khoa in cac_khoa_nguong(ten_chi_so):
        ket_qua = kho_nguong.lay(ma_jig, khoa, unit_serial, luc_do)
        if ket_qua is not None:
            return ket_qua
    return None


def nguong_cho_chi_so(
    kho_nguong: Any,
    ma_jig: str,
    ten_chi_so: str,
    unit_serial: str = "",
    luc_do: Any = None,
) -> Any:
    """Tra ngưỡng thật cho một tên chỉ số của log Iris (016 T016-08).

    Ưu tiên ngưỡng riêng của đúng ``unit_serial``; chỉ rơi về ngưỡng dùng chung
    khi Unit chưa được khai báo riêng, vì mỗi S/N có thể có dải dung sai khác.
    """
    if kho_nguong is None:
        return None
    ma = ma_chi_so_chuan(ten_chi_so)
    if not ma:
        return None
    return tra_nguong_theo_chi_so(kho_nguong, ma_jig, ten_chi_so, unit_serial, luc_do)


def dung_du_lieu_bieu_do(
    ma_jig: str,
    ten_chi_so: str,
    cac_hang: Sequence[Any],
    loai_bieu_do: str = "xu_huong",
    nguoi_phu_trach: str = "",
    kho_nguong: Any = None,
) -> SpcChartInput:
    """Build a shared SpcChartInput for one JIG and one metric.

    Used by both the select-box UI and the chat command so the preview
    image and the email image never diverge.

    When ``kho_nguong`` (a ``metric_limits.KhoNguong``) carries a real,
    effective threshold for this metric, it is passed as ``usl``/``lsl`` so the
    chart draws the actual specification lines instead of only the
    mean ± 3σ control band.
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
    # Mỗi S/N có thể có dải dung sai riêng. Chỉ được lấy Unit của chính các dòng
    # đã lọc để vẽ (cùng JIG, cùng chỉ số); lấy Unit của dòng đầu danh sách chưa
    # lọc sẽ vẽ sai dải của Unit khác lên biểu đồ.
    unit_cua_hang = ""
    moc_cua_hang = None
    nhieu_serial = False
    for hang in cac_hang:
        if not isinstance(hang, dict):
            continue
        jig_hang = _lay_chuoi(hang, "jig_id", "ma_jig", "JigNumber")
        metric_hang = _lay_chuoi(hang, "metric_name", "ten_chi_so", "metric")
        if jig_hang and jig_hang.strip() != ma_jig_chuan:
            continue
        if metric_hang and metric_hang.strip() != chi_so_chuan:
            continue
        sn = _lay_chuoi(hang, "unit_serial", "ma_unit", "serial")
        if not sn:
            continue
        if not unit_cua_hang:
            unit_cua_hang = sn
        if sn != unit_cua_hang:
            # Nhiều S/N trên cùng biểu đồ: không có một dải duy nhất đúng cho
            # mọi điểm, nên không vẽ đường giới hạn để tránh vẽ sai.
            unit_cua_hang = ""
            nhieu_serial = True
            break
        moc = _lay_chuoi(hang, "event_time", "ngay_gio", "TIME", "DATE") or None
        # Dải đang áp dụng là dải có hiệu lực tại lần đo mới nhất.
        if moc and (moc_cua_hang is None or moc > moc_cua_hang):
            moc_cua_hang = moc
    if nhieu_serial:
        # Không tra ngưỡng nào cả, kể cả ngưỡng dùng chung: một dải chung vẫn
        # không đúng cho từng S/N riêng trên cùng biểu đồ.
        nguong = None
    else:
        nguong = nguong_cho_chi_so(
            kho_nguong, ma_jig_chuan, chi_so_chuan, unit_cua_hang, moc_cua_hang
        )
    usl = nguong.gioi_han_tren if (nguong is not None and nguong.hieu_luc()) else None
    lsl = nguong.gioi_han_duoi if (nguong is not None and nguong.hieu_luc()) else None
    # Chưa có giới hạn thật → biểu đồ là MÔ PHỎNG và phải ghi rõ trên ảnh.
    mo_phong = usl is None and lsl is None
    if not don_vi and nguong is not None:
        don_vi = _BANG_DON_VI_THEO_CHI_SO.get(ma_chi_so_chuan(chi_so_chuan), "")
    return SpcChartInput(
        jig_id=ma_jig_chuan,
        cong_doan="LSU Iris",
        metric=_nhan_chi_so(chi_so_chuan),
        unit=don_vi,
        values=cac_gia_tri,
        nhan_thoi_gian=nhan,
        usl=usl,
        lsl=lsl,
        ucl=(trung_binh + 3 * do_lech) if do_lech > 0 else None,
        cl=trung_binh,
        lcl=(trung_binh - 3 * do_lech) if do_lech > 0 else None,
        sigma=(do_lech if do_lech > 0 else None),
        nguoi_phu_trach=nguoi_phu_trach,
        mo_phong=mo_phong,
    )


def huong_dan_thieu_nguong(ten_chi_so: str) -> str:
    """Câu tiếng Việt nói **rõ thiếu gì** và **nhập gì** để có giới hạn thật.

    Dùng khi biểu đồ chỉ vẽ được dải tham khảo: người dùng cần biết chính xác
    phải gõ gì trong chat, hoặc phải bổ sung tệp nào.
    """
    chi_so = (ten_chi_so or "").strip()
    # Gợi ý khoá **cấp dòng** (bỏ hậu tố cột ``:CAM…``): đủ cụ thể để không áp
    # nhầm sang dòng khác, mà vẫn ngắn hơn tên đầy đủ của từng cột. Không dùng
    # khoá ngắn nhất (ví dụ ``DEPTH``) vì như vậy sẽ áp cho mọi dòng đo sâu.
    goi_y_khoa = chi_so
    ma_chuan = ma_chi_so_chuan(chi_so)
    for khoa in cac_khoa_nguong(chi_so):
        # Chỉ nhận khoá **cấp dòng** (bỏ hậu tố cột ``:CAM…``) hoặc chính mã
        # chuẩn của chỉ số; không nhận khoá tổng quát hơn mã chuẩn.
        if re.search(r":CAM[+-]?\d+$", khoa):
            goi_y_khoa = khoa
            continue
        if khoa == ma_chuan or len(khoa) < len(goi_y_khoa):
            goi_y_khoa = khoa
        break
    dong = [
        "Chưa vẽ được đường giới hạn thật vì **thiếu ngưỡng trên/dưới** cho chỉ số này.",
        f"Chỉ số: {chi_so or 'chưa rõ'}",
        "",
        "Biểu đồ dưới đây là **MÔ PHỎNG**: đường giới hạn chỉ là dải tham khảo "
        "(trung bình ± 3 độ lệch chuẩn), không phải tiêu chuẩn kỹ thuật.",
        "",
        "Để có giới hạn thật, chọn một trong hai cách:",
        "1) Nhập ngay trong chat, ví dụ:",
        f"   - đặt ngưỡng trên 100 cho {goi_y_khoa}",
        f"   - đặt ngưỡng dưới 10 cho {goi_y_khoa}",
        "   (đặt được cả hai phía; ngưỡng đặt cho một dòng sẽ áp cho mọi cột của dòng đó)",
        "2) Bổ sung tệp giới hạn của JIG (Spec/CamPos) vào ô “Tệp giới hạn kèm theo” ở Thẻ 1, "
        "hệ thống sẽ tự đọc giới hạn theo đúng số sê-ri và thời điểm đo.",
    ]
    return "\n".join(dong)


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
