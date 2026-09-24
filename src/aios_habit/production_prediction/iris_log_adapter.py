"""Bộ chuyển đổi log JIG Iris thật sang bản ghi chuẩn LSU (016-iris-log-intake).

Log Iris tại xưởng là **ma trận rộng**: một dòng = một lần đo một Unit, với
572–1.059 cột. Tên cột tuân theo quy ước ``<HỌ>:<MÀU>[:<VỊ TRÍ>…][<đơn vị>]``,
ví dụ ``SKEW:BLACK[um]``, ``BOW:BLACK:-70[um]``, ``BEAM_DIAMETER:H:BLACK:-140:0:LD1:[um]``.

Module này chỉ dùng thư viện chuẩn, không import Streamlit, không gọi mạng.
Nó tách ma trận rộng thành từng cặp (Unit, chỉ số, giá trị) để phần còn lại
của hệ thống dùng lại nguyên vẹn đường nối chuỗi và cổng dữ liệu hiện có.

Ba nhóm tệp được nhận diện:

- **Nhóm A — UnitTest**: một dòng = một lần đo, có ``SERIAL NUMBER``/``S/N`` và
  các cột ``RESULT``/``RESULT:<MÀU>``/``Judge:<Màu>``.
- **Nhóm B — Spec/CamPos**: tệp giới hạn, tên cột bắt đầu bằng ``Spec:`` hoặc
  có hậu tố ``:Lower``/``:Upper``.
- **Nhóm C — Depth/Profile**: nhiều khối, mỗi khối mở đầu bằng dòng
  ``ngày,giờ,mã_sản_phẩm`` rồi tới các dòng ``,,,,CamPos,…`` / ``,,,,imgHeight:…``.

Giá trị canh lỗi ``999`` là giá trị "không đo được" của máy; chúng bị bỏ và
**ghi lại lý do**, không nuốt âm thầm. Đo thật trên hai tệp xuất của JIG cho thấy
máy dùng ba biến thể: ``999``, ``999.9`` và ``9999.9``. Vùng canh lỗi vì vậy là
``999 <= |v| < 1000`` **hoặc** ``9999 <= |v| < 10000``.

Không được dùng ngưỡng ``>= 999``: giá trị đo hợp lệ có thể lớn hơn 1000 (vị trí
chùm tia ``BeamPosX`` ≈ 2890–3190 µm là giá trị thật, không phải canh lỗi).
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Các vùng canh lỗi của máy Iris: ô không đo được. Đo thật thấy 999, 999.9, 9999.9.
CAC_VUNG_CANH_LOI: Tuple[Tuple[float, float], ...] = (
    (999.0, 1000.0),
    (9999.0, 10000.0),
)


def la_canh_loi(gia_tri: Optional[float]) -> bool:
    """True khi giá trị thuộc vùng canh lỗi "máy không đo được"."""
    if gia_tri is None:
        return False
    tri_tuyet_doi = abs(gia_tri)
    return any(duoi <= tri_tuyet_doi < tren for duoi, tren in CAC_VUNG_CANH_LOI)


# Số cột tối thiểu để coi là ma trận rộng (log thật luôn rộng hơn nhiều).
NGUONG_COT_MA_TRAN_RONG = 20

# Tên cột nhận dạng, đã chuẩn hoá chữ thường.
_COT_NGAY = ("date",)
_COT_GIO = ("time",)
_COT_SERIAL = ("serial number", "s/n", "serial", "sn")
_COT_JIG = ("jig number", "jignumber", "jig")
_COT_MAY = ("mode",)
_COT_RESULT_TONG = ("result", "totaljudge")

# Họ chỉ số đo được trong ma trận rộng (đã chuẩn hoá, bỏ dấu phân cách).
_HO_CHI_SO = (
    "BOW",
    "BOWINIT",
    "SKEW",
    "SKEWINIT",
    "LIGHT_PATH",
    "LIGHTPATH",
    "BEAM_DIAMETER",
    "BEAMDIAMETER",
    "BEAMPITCH",
    "BEAMPOS",
    "APC",
    "CURRENT",
    "VOLTAGE",
)

# Màu trong tên cột → nhãn màu chuẩn của hệ thống.
_MAU = {
    "BLACK": "BLACK",
    "MAGENTA": "MAGENTA",
    "CYAN": "CYAN",
    "YELLOW": "YELLOW",
    "B": "BLACK",
    "M": "MAGENTA",
    "C": "CYAN",
    "Y": "YELLOW",
}

_RE_DON_VI_MOI = re.compile(r"\[([^\]]*)\]")
_RE_SO = re.compile(r"^-?\d+(?:[.,]\d+)?$")


@dataclass
class CotLogIris:
    """Một cột đo được đã tách khỏi tiêu đề ma trận rộng."""

    ten_cot: str
    ho: str
    mau: str
    vi_tri: str
    don_vi: str

    def ten_chuan(self) -> str:
        """Tên chỉ số chuẩn để hiển thị và đối chiếu ngưỡng.

        Giữ nguyên thứ tự các thành phần như trong tệp gốc (bỏ phần đơn vị),
        ví dụ ``APC:CURRENT`` và ``BEAM_DIAMETER:H:BLACK:-140:0:LD1``. Không
        ghép lại theo thứ tự khác vì tên chỉ số phải tra khớp được với tệp
        giới hạn của JIG.
        """
        ten = _RE_DON_VI_MOI.sub("", self.ten_cot).strip()
        ten = re.sub(r":{2,}", ":", ten)
        return ten.strip().rstrip(":").upper()


@dataclass
class BanGhiIris:
    """Một giá trị đo tách ra từ một dòng log Iris."""

    unit_serial: str
    ngay: str
    gio: str
    jig_id: str
    metric_name: str
    value: Optional[float]
    unit: str = ""
    mau: str = ""
    target_label: str = "UNKNOWN"
    ly_do_bo_qua: str = ""

    @property
    def event_time(self) -> Optional[datetime]:
        """Thời điểm đo theo định dạng ``YYYY.MM.DD`` hoặc ``YYYY/MM/DD``."""
        return ghep_thoi_gian(self.ngay, self.gio)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_serial": self.unit_serial,
            "jig_id": self.jig_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "mau": self.mau,
            "target_label": self.target_label,
            "event_time": self.event_time.isoformat() if self.event_time else "",
            "ly_do_bo_qua": self.ly_do_bo_qua,
        }


@dataclass
class KetQuaDocIris:
    """Kết quả đọc một tệp log Iris."""

    loai: str
    so_dong: int = 0
    so_cot: int = 0
    ban_ghi: List[BanGhiIris] = field(default_factory=list)
    nhan_theo_mau: Dict[str, str] = field(default_factory=dict)
    bo_qua_canh_loi: int = 0
    thieu_cot: List[str] = field(default_factory=list)
    dong_loi: List[str] = field(default_factory=list)

    def ban_ghi_hop_le(self) -> List[BanGhiIris]:
        return [b for b in self.ban_ghi if b.value is not None]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loai": self.loai,
            "so_dong": self.so_dong,
            "so_cot": self.so_cot,
            "so_ban_ghi": len(self.ban_ghi),
            "so_hop_le": len(self.ban_ghi_hop_le()),
            "bo_qua_canh_loi": self.bo_qua_canh_loi,
            "nhan_theo_mau": dict(self.nhan_theo_mau),
            "thieu_cot": list(self.thieu_cot),
            "dong_loi": list(self.dong_loi),
        }


def chuan_hoa_ten_cot(ten: str) -> str:
    """Chuẩn hoá tên cột: bỏ khoảng trắng thừa và khoảng trắng hai đầu."""
    return " ".join((ten or "").strip().split())


def ghep_thoi_gian(ngay: str, gio: str) -> Optional[datetime]:
    """Ghép ngày và giờ kiểu Iris (``2026.07.01`` + ``16:33:07``)."""
    ngay_sach = (ngay or "").strip().replace(".", "-").replace("/", "-")
    gio_sach = (gio or "").strip()
    if not ngay_sach:
        return None
    for dinh_dang in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        thu = f"{ngay_sach} {gio_sach}".strip()
        try:
            return datetime.strptime(thu, dinh_dang)
        except ValueError:
            continue
    return None


def la_so_do_duoc(token: str) -> bool:
    """True khi ô là số đo được (bỏ qua canh lỗi ``999`` và ô trống)."""
    gia_tri = _doi_so(token)
    return gia_tri is not None and not la_canh_loi(gia_tri)


def _doi_so(token: Any) -> Optional[float]:
    if token is None:
        return None
    chuoi = str(token).strip().replace(",", ".")
    if not chuoi or chuoi in {"-", "--", "---"}:
        return None
    if not _RE_SO.match(chuoi.replace(",", ".")):
        return None
    try:
        return float(chuoi.replace(",", "."))
    except ValueError:
        return None


def la_ma_tran_rong(tieu_de: Sequence[str]) -> bool:
    """True khi tiêu đề là ma trận rộng kiểu UnitTest (nhiều cột đo)."""
    cot_do = [t for t in tieu_de if tach_cot_do(t) is not None]
    return len(tieu_de) >= NGUONG_COT_MA_TRAN_RONG and len(cot_do) >= 10


def tach_cot_do(ten_cot: str) -> Optional[CotLogIris]:
    """Tách một tên cột ma trận rộng thành họ / màu / vị trí / đơn vị.

    Trả về ``None`` khi cột không phải chỉ số đo (ví dụ ``DATE``, ``RESULT``).
    Đơn vị có thể nằm giữa tên cột chứ không chỉ ở cuối
    (``BeamPosX:Black:-140:LD1_1[um]:6face``), nên phần ``[…]`` được bỏ ở mọi vị
    trí trước khi tách.
    """
    ten = chuan_hoa_ten_cot(ten_cot)
    if not ten:
        return None
    don_vi = ""
    phan_don_vi = _RE_DON_VI_MOI.findall(ten)
    if phan_don_vi:
        don_vi = phan_don_vi[0].strip()
        ten = _RE_DON_VI_MOI.sub("", ten)
    ten = ten.strip().strip(":").strip()
    ten = re.sub(r":{2,}", ":", ten)
    if not ten:
        return None
    phan = [p.strip() for p in ten.split(":")]
    ho_raw = next((p for p in phan if p), "")
    if not ho_raw:
        return None
    ho_norm = ho_raw.upper().replace(" ", "_").replace("-", "_")
    ho_chuan = ""
    for ung_vien in _HO_CHI_SO:
        if ho_norm == ung_vien:
            ho_chuan = ung_vien
            break
    if not ho_chuan:
        # Họ viết liền có hậu tố trục: ``BeamPosX``/``BeamDiameterH``.
        for goc, hau_to in (("BEAMPOS", "BEAM_POS"), ("BEAMDIAMETER", "BEAM_DIAMETER")):
            if ho_norm.startswith(goc) and len(ho_norm) == len(goc) + 1:
                ho_chuan = f"{hau_to}:{ho_norm[-1]}"
                break
    if not ho_chuan:
        return None
    mau = ""
    vi_tri = ""
    for phan_tu in phan[1:]:
        if not phan_tu:
            continue
        if phan_tu.upper() in _MAU:
            mau = _MAU[phan_tu.upper()]
            continue
        if phan_tu.isdigit() or re.match(r"^LD\d", phan_tu.upper()):
            # Chỉ số lặp/vị trí diode: giữ để tên cột không trùng nhau.
            vi_tri = f"{vi_tri}:{phan_tu}" if vi_tri else phan_tu
            continue
        vi_tri = f"{vi_tri}:{phan_tu}" if vi_tri else phan_tu
    return CotLogIris(ten_cot=ten, ho=ho_chuan, mau=mau, vi_tri=vi_tri, don_vi=don_vi)


def _nhan_mau_bang_chu(mau: str) -> str:
    """Đổi mã màu một ký tự (B/M/C/Y) thành tên màu đầy đủ."""
    return _MAU.get((mau or "").strip().upper(), (mau or "").strip().upper())


def _tim_cot(tieu_de: Sequence[str], ten_ung_vien: Iterable[str]) -> Optional[int]:
    """Tìm chỉ số cột theo danh sách tên ứng viên (không phân biệt hoa thường)."""
    chuan = [chuan_hoa_ten_cot(t).lower() for t in tieu_de]
    for ung_vien in ten_ung_vien:
        if ung_vien.lower() in chuan:
            return chuan.index(ung_vien.lower())
    return None


def _doc_ban_ghi_nhom_a(
    tieu_de: Sequence[str],
    cac_dong: Sequence[Sequence[str]],
    ten_tep: str,
) -> KetQuaDocIris:
    """Đọc nhóm A — tệp UnitTest ma trận rộng."""
    ket_qua = KetQuaDocIris(loai="unit_test", so_cot=len(tieu_de))
    i_serial = _tim_cot(tieu_de, _COT_SERIAL)
    i_ngay = _tim_cot(tieu_de, _COT_NGAY)
    i_gio = _tim_cot(tieu_de, _COT_GIO)
    i_jig = _tim_cot(tieu_de, _COT_JIG)
    if i_serial is None:
        ket_qua.thieu_cot.append("SERIAL NUMBER (hoặc S/N)")
    if i_ngay is None:
        ket_qua.thieu_cot.append("DATE")
    if i_gio is None:
        ket_qua.thieu_cot.append("TIME")

    # Cột nhãn theo màu: RESULT:<MÀU>, Judge:<Màu>, <Màu>_Judge, RESULT.
    cot_nhan: List[Tuple[int, str]] = []
    for idx, ten in enumerate(tieu_de):
        chuan = chuan_hoa_ten_cot(ten)
        upper = chuan.upper()
        if upper.startswith("RESULT:"):
            cot_nhan.append((idx, _nhan_mau_bang_chu(chuan.split(":", 1)[1])))
        elif upper.startswith("JUDGE:"):
            cot_nhan.append((idx, _nhan_mau_bang_chu(chuan.split(":", 1)[1])))
        elif upper.endswith("_JUDGE") and len(upper) > len("_JUDGE"):
            cot_nhan.append((idx, _nhan_mau_bang_chu(upper[: -len("_JUDGE")])))
    i_result_tong = _tim_cot(tieu_de, _COT_RESULT_TONG)
    i_total_judge = _tim_cot(tieu_de, ("totaljudge",))
    if i_total_judge is not None and i_result_tong == i_total_judge:
        i_result_tong = i_total_judge

    # Cột đo được.
    cot_do: List[Tuple[int, CotLogIris]] = []
    for idx, ten in enumerate(tieu_de):
        cot = tach_cot_do(ten)
        if cot is not None:
            cot_do.append((idx, cot))
    if not cot_do:
        ket_qua.thieu_cot.append("cột chỉ số đo (BOW/SKEW/LIGHT_PATH/BEAM_DIAMETER/…)")

    if ket_qua.thieu_cot:
        return ket_qua

    jig_ma_dinh = Path(ten_tep).stem if ten_tep else "unknown"
    for so_dong, dong in enumerate(cac_dong, start=2):
        if i_serial is not None and i_serial >= len(dong):
            continue
        unit_serial = (dong[i_serial] or "").strip() if i_serial < len(dong) else ""
        if not unit_serial:
            ket_qua.dong_loi.append(f"Dòng {so_dong}: thiếu mã Unit (SERIAL NUMBER).")
            continue
        ngay = (dong[i_ngay] or "").strip() if i_ngay is not None and i_ngay < len(dong) else ""
        gio = (dong[i_gio] or "").strip() if i_gio is not None and i_gio < len(dong) else ""
        jig_id = (dong[i_jig] or "").strip() if i_jig is not None and i_jig < len(dong) else ""
        if not jig_id:
            jig_id = jig_ma_dinh

        nhan_theo_mau: Dict[str, str] = {}
        for idx, mau in cot_nhan:
            gia_tri = (dong[idx] or "").strip() if idx < len(dong) else ""
            if gia_tri:
                nhan_theo_mau[mau] = gia_tri.upper()
        nhan_tong = ""
        if i_result_tong is not None and i_result_tong < len(dong):
            nhan_tong = (dong[i_result_tong] or "").strip().upper()
        if nhan_tong:
            nhan_theo_mau.setdefault("TOTAL", nhan_tong)
        nhan_theo_mau.setdefault("TOTAL", "UNKNOWN")
        if not ket_qua.nhan_theo_mau:
            # Nhãn cấp tệp: giữ bộ nhãn của dòng đầu (ổn định), vì mỗi bản ghi
            # đều đã mang nhãn riêng của đúng dòng và đúng màu.
            ket_qua.nhan_theo_mau = nhan_theo_mau

        ket_qua.so_dong += 1
        for idx, cot in cot_do:
            if idx >= len(dong):
                continue
            token = (dong[idx] or "").strip()
            gia_tri = _doi_so(token)
            nhan = nhan_theo_mau.get(cot.mau) or nhan_theo_mau.get("TOTAL", "UNKNOWN")
            if gia_tri is None:
                if not token:
                    continue
                ket_qua.ban_ghi.append(
                    BanGhiIris(
                        unit_serial=unit_serial, ngay=ngay, gio=gio, jig_id=jig_id,
                        metric_name=cot.ten_chuan(), value=None, unit=cot.don_vi,
                        mau=cot.mau, target_label=nhan,
                        ly_do_bo_qua=f"Giá trị '{token}' không phải số.",
                    )
                )
                continue
            if la_canh_loi(gia_tri):
                ket_qua.bo_qua_canh_loi += 1
                ket_qua.ban_ghi.append(
                    BanGhiIris(
                        unit_serial=unit_serial, ngay=ngay, gio=gio, jig_id=jig_id,
                        metric_name=cot.ten_chuan(), value=None, unit=cot.don_vi,
                        mau=cot.mau, target_label=nhan,
                        ly_do_bo_qua=(
                            f"Cột {cot.ten_cot} mang giá trị canh lỗi {gia_tri:g} "
                            "(máy không đo được)."
                        ),
                    )
                )
                continue
            ket_qua.ban_ghi.append(
                BanGhiIris(
                    unit_serial=unit_serial, ngay=ngay, gio=gio, jig_id=jig_id,
                    metric_name=cot.ten_chuan(), value=gia_tri, unit=cot.don_vi,
                    mau=cot.mau, target_label=nhan,
                )
            )
    return ket_qua


def _bo_don_vi(ten_cot: str) -> str:
    """Bỏ phần đơn vị ``[...]`` ở cuối tên cột."""
    return _RE_DON_VI_MOI.sub("", (ten_cot or "").strip()).strip()


def _la_cot_spec(ten: str) -> bool:
    """True khi tên cột thuộc nhóm giới hạn.

    Tên thật có đơn vị ở cuối (``Spec:BeamPosX:Lower[um]``), nên phải bỏ ``[…]``
    trước khi xét hậu tố ``:Lower``/``:Upper``; nếu không, cả cặp giới hạn vị trí
    chùm tia sẽ bị bỏ sót.
    """
    chuan = chuan_hoa_ten_cot(ten)
    if chuan.upper().startswith("SPEC:"):
        return True
    upper = _bo_don_vi(chuan).upper()
    return upper.endswith(":LOWER") or upper.endswith(":UPPER")


def doc_nhom_b_gioi_han(
    tieu_de: Sequence[str],
    cac_dong: Sequence[Sequence[str]],
) -> Dict[str, Dict[str, Any]]:
    """Đọc nhóm B (Spec/CamPos) thành ngưỡng theo (chỉ số, tên cột nguồn)."""
    ket_qua: Dict[str, Dict[str, Any]] = {}
    cot_nguon = [(i, chuan_hoa_ten_cot(t)) for i, t in enumerate(tieu_de) if _la_cot_spec(t)]
    for idx, ten in cot_nguon:
        gia_tri: List[float] = []
        for dong in cac_dong:
            if idx >= len(dong):
                continue
            so = _doi_so(dong[idx])
            if so is not None and not la_canh_loi(so):
                gia_tri.append(so)
        if not gia_tri:
            continue
        ket_qua[ten] = {
            "ten_cot_nguon": ten,
            "gia_tri": sorted(set(gia_tri)),
            "gia_tri_moi_nhat": gia_tri[-1],
            "so_dong": len(gia_tri),
        }
    return ket_qua


def doc_nhom_c_depth(
    cac_dong: Sequence[Sequence[str]],
    ten_tep: str = "",
) -> KetQuaDocIris:
    """Đọc nhóm C (Depth/Profile) thành chuỗi đo theo khối.

    Mỗi khối mở đầu bằng dòng ``ngày,giờ,mã_sản_phẩm``; các dòng sau là
    ``,,,,Beam:H:LD1`` (mào đầu khối), ``,,,,CamPos,…`` (trục vị trí camera) và
    ``,,,,imgHeight:<vị trí>,…`` hoặc ``,,,,Cam:<vị trí>,…`` (giá trị theo trục).

    Tên chỉ số giữ **cả** vị trí dòng **lẫn** vị trí cột trên trục ``CamPos``;
    nếu chỉ giữ vị trí dòng thì 17 cột của cùng một dòng bị gộp thành một chỉ số
    và mất thông tin trục.
    """
    ket_qua = KetQuaDocIris(loai="depth", so_cot=0)
    unit_hien_tai = ""
    ngay = ""
    gio = ""
    nhan_hien_tai = ""
    jig_id = Path(ten_tep).stem if ten_tep else "unknown"
    truc_camp: List[str] = []

    for dong in cac_dong:
        o = [str(x or "").strip() for x in dong]
        if not any(o):
            continue
        # Dòng mào đầu khối: ngày, giờ, serial nằm ở 3 ô đầu tiên.
        if o[0] and ghep_thoi_gian(o[0], o[1] if len(o) > 1 else "") is not None and len(o) > 2 and o[2]:
            ngay, gio = o[0], (o[1] if len(o) > 1 else "")
            unit_hien_tai = o[2]
            nhan_hien_tai = ""
            truc_camp = []
            ket_qua.so_dong += 1
            continue
        if not unit_hien_tai:
            continue
        o5 = o[4] if len(o) > 4 else ""
        o5_norm = o5.lower()
        # Trục vị trí camera: ``,,,,CamPos,-8,-7,…``.
        if o5_norm.startswith("camp"):
            truc_camp = [x for x in o[5:]]
            continue
        # Dòng mào đầu nhánh chùm tia: ``,,,,Beam:H:LD1`` — có dấu ``:`` như tên
        # chỉ số nhưng **không** kèm giá trị số nào, nên phải nhận diện bằng việc
        # thiếu ô số, không phải bằng việc thiếu dấu hai chấm.
        co_gia_tri_so = any(_doi_so(x) is not None for x in o[5:])
        if o5 and not co_gia_tri_so and not o5_norm.startswith(("cam:", "imgheight")):
            nhan_hien_tai = o5
            continue
        # Dòng giá trị: ô thứ 5 là ``<loại>:<vị trí>``, các ô sau là giá trị theo trục.
        if len(o) >= 6 and o5 and ":" in o5:
            ten_vien, _, vi_tri = o5.partition(":")
            for idx_o, token in enumerate(o[5:], start=5):
                gia_tri = _doi_so(token)
                if gia_tri is None:
                    continue
                if la_canh_loi(gia_tri):
                    ket_qua.bo_qua_canh_loi += 1
                    continue
                vi_tri_cot = ""
                chi_so_truc = idx_o - 5
                if chi_so_truc < len(truc_camp):
                    vi_tri_cot = truc_camp[chi_so_truc]
                ten_chi_so = f"DEPTH:{nhan_hien_tai}:{ten_vien}:{vi_tri}"
                if vi_tri_cot:
                    ten_chi_so = f"{ten_chi_so}:CAM{vi_tri_cot}"
                ket_qua.ban_ghi.append(
                    BanGhiIris(
                        unit_serial=unit_hien_tai, ngay=ngay, gio=gio, jig_id=jig_id,
                        metric_name=ten_chi_so.upper(), value=gia_tri, unit="",
                        mau="", target_label="UNKNOWN",
                    )
                )
    return ket_qua


def nhan_dien_loai_tep_log(duong_dan: str | Path) -> str:
    """Nhận diện loại tệp log Iris: ``unit_test``, ``spec``, ``depth`` hoặc ``khong_ro``.

    Chỉ đọc phần đầu tệp nên nhanh kể cả với tệp 4 MB. Không ném lỗi, để lớp gọi
    còn hiện thông báo tiếng Việt phù hợp.
    """
    path = Path(duong_dan)
    if not path.exists() or not path.is_file():
        return "khong_ro"
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            mau: List[List[str]] = []
            for dong in csv.reader(f):
                if any((o or "").strip() for o in dong):
                    mau.append([str(o or "").strip() for o in dong])
                if len(mau) >= 40:
                    break
    except (OSError, UnicodeDecodeError, csv.Error):
        return "khong_ro"
    if not mau:
        return "khong_ro"
    tieu_de = [chuan_hoa_ten_cot(t) for t in mau[0]]
    if la_ma_tran_rong(tieu_de):
        return "unit_test"
    if any(_la_cot_spec(t) for t in tieu_de):
        return "spec"
    # Nhóm C: có dòng mào đầu ``ngày,giờ,serial`` hoặc có ``CamPos``/``imgHeight``.
    for dong in mau:
        if la_ngay_iris(dong[0]) and len(dong) > 2 and dong[2]:
            return "depth"
        if any(o.lower().startswith(("camp", "cam:", "imgheight")) for o in dong):
            return "depth"
    return "khong_ro"


def nhan_dien_khoi_log_dan(text: str) -> str:
    """Nhận diện một **khối văn bản dán** thuộc loại log nào.

    Trả ``"depth"`` khi là khối đo sâu (nhóm C), ``"khong_ro"`` khi không nhận ra.
    Khối log rộng đã có đường riêng (``la_dong_log_iris``) nên không xử lý ở đây.
    """
    cac_dong = [d for d in (text or "").splitlines() if d.strip()]
    if len(cac_dong) < 3:
        return "khong_ro"
    mau = [tach_dong_don(d) for d in cac_dong[:40]]
    for o in mau:
        if len(o) > 4 and any(
            x.lower().startswith(("camp", "cam:", "imgheight")) for x in o
        ):
            return "depth"
    for o in mau:
        if o and la_ngay_iris(o[0]) and len(o) > 2 and o[2] and not tach_cot_do(o[0]):
            return "depth"
    return "khong_ro"


def parse_khoi_depth_dan(text: str, jig_id: str = "") -> KetQuaDocIris:
    """Phân tích một khối đo sâu đã dán trong chat."""
    cac_dong = [tach_dong_don(d) for d in (text or "").splitlines() if d.strip()]
    ket_qua = doc_nhom_c_depth(cac_dong, jig_id or "IrisLSU (log dán)")
    if jig_id:
        for ban_ghi in ket_qua.ban_ghi:
            ban_ghi.jig_id = jig_id
    return ket_qua


def thong_diep_khoi_depth(ket_qua: KetQuaDocIris) -> str:
    """Câu tiếng Việt tóm tắt khối đo sâu vừa dán."""
    hop_le = ket_qua.ban_ghi_hop_le()
    if not hop_le:
        return (
            "Khối log đo sâu không có giá trị đo nào dùng được. "
            "Các ô mang giá trị canh lỗi (999/999.9/9999.9) đã bị bỏ qua."
        )
    don_vi = sorted({b.unit_serial for b in hop_le})
    return (
        f"Đã tách {len(hop_le):,} giá trị đo sâu của {len(don_vi)} Unit "
        f"({', '.join(don_vi[:3])})."
    )


def doc_log_iris_tu_dong(duong_dan: str | Path) -> KetQuaDocIris:
    """Đọc **bất kỳ** tệp log Iris nào: tự nhận diện nhóm A / B / C rồi đọc.

    Đây là đường dùng chung để "log nào đưa vào cũng phân tích được": người dùng
    không phải biết tệp của mình thuộc nhóm nào.
    """
    path = Path(duong_dan)
    loai = nhan_dien_loai_tep_log(path)
    if loai == "unit_test":
        return doc_tep_log_iris(path)
    if loai == "depth":
        return doc_tep_depth(path)
    if loai == "spec":
        raise ValueError(
            f"Tệp {path.name} là tệp giới hạn (Spec/CamPos), không phải log đo. "
            "Hãy đưa tệp này vào ô 'Tệp giới hạn kèm theo' để hệ thống tự lấy ngưỡng."
        )
    raise ValueError(
        f"Chưa nhận diện được định dạng của tệp {path.name}. "
        "Hệ thống đọc được log đo rộng (UnitTest), tệp đo sâu (Depth/Profile) và tệp giới hạn (Spec/CamPos). "
        "Vui lòng kiểm tra lại tệp xuất từ JIG."
    )


def doc_tep_depth(duong_dan: str | Path) -> KetQuaDocIris:
    """Đọc một tệp đo sâu (nhóm C) từ đường dẫn."""
    path = Path(duong_dan)
    if not path.exists():
        raise ValueError(f"Không tìm thấy tệp log: {path.name}")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            cac_dong = [d for d in csv.reader(f) if any((o or "").strip() for o in d)]
    except OSError:
        raise ValueError("Không mở được tệp log. Vui lòng kiểm tra lại đường dẫn và quyền đọc tệp.")
    except UnicodeDecodeError:
        raise ValueError(f"Tệp log {path.name} không đúng chuẩn UTF-8. Vui lòng xuất lại từ JIG.")
    if not cac_dong:
        raise ValueError("Tệp log đang trống. Vui lòng kiểm tra lại xuất log từ JIG.")
    ket_qua = doc_nhom_c_depth(cac_dong, path.name)
    if not ket_qua.ban_ghi_hop_le():
        raise ValueError(
            f"Tệp {path.name} không có giá trị đo nào đọc được. "
            "Vui lòng kiểm tra lại tệp xuất từ JIG."
        )
    return ket_qua


def doc_tep_log_iris(duong_dan: str | Path) -> KetQuaDocIris:
    """Đọc một tệp log Iris (nhóm A) từ đường dẫn.

    Ném ``ValueError`` bằng tiếng Việt khi tệp trống, không đọc được hoặc
    không nhận diện được định dạng.
    """
    path = Path(duong_dan)
    if not path.exists():
        raise ValueError(f"Không tìm thấy tệp log: {path.name}")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            cac_dong = [d for d in csv.reader(f) if any((o or "").strip() for o in d)]
    except OSError:
        raise ValueError("Không mở được tệp log. Vui lòng kiểm tra lại đường dẫn và quyền đọc tệp.")
    except UnicodeDecodeError:
        raise ValueError(f"Tệp log {path.name} không đúng chuẩn UTF-8. Vui lòng xuất lại từ JIG.")
    if not cac_dong:
        raise ValueError("Tệp log đang trống. Vui lòng kiểm tra lại xuất log từ JIG.")
    tieu_de = [chuan_hoa_ten_cot(t) for t in cac_dong[0]]
    if not la_ma_tran_rong(tieu_de):
        raise ValueError(
            f"Tệp {path.name} không phải log Iris dạng ma trận rộng "
            f"({len(tieu_de)} cột). Vui lòng kiểm tra lại tệp xuất từ JIG."
        )
    return _doc_ban_ghi_nhom_a(tieu_de, cac_dong[1:], path.name)


def doc_log_iris(duong_dan: str | Path) -> List[BanGhiIris]:
    """Đọc log Iris và trả danh sách bản ghi chuẩn (đã bỏ canh lỗi 999)."""
    ket_qua = doc_tep_log_iris(duong_dan)
    return ket_qua.ban_ghi_hop_le()


def la_tep_log_iris(duong_dan: str | Path) -> bool:
    """Nhận diện nhanh tệp log Iris dạng ma trận rộng (không ném lỗi)."""
    try:
        return doc_tep_log_iris(duong_dan).loai == "unit_test"
    except (ValueError, OSError):
        return False


def la_dong_log_iris(dong: str) -> bool:
    """True khi **một dòng dán** trông giống dòng log Iris thật."""
    if not dong or "\n" in dong.strip("\n"):
        return False
    o = tach_dong_don(dong)
    if len(o) < NGUONG_COT_MA_TRAN_RONG:
        return False
    tieu_de = [chuan_hoa_ten_cot(t) for t in o]
    if la_ma_tran_rong(tieu_de):
        return False  # Đây là dòng tiêu đề, không phải dòng dữ liệu.
    return any(tach_cot_do(t) is not None for t in tieu_de) or la_ngay_iris(o[0])


def la_dong_tieu_de_iris(dong: str) -> bool:
    """True khi dòng dán là dòng tiêu đề của ma trận rộng."""
    o = tach_dong_don(dong)
    if len(o) < NGUONG_COT_MA_TRAN_RONG:
        return False
    return la_ma_tran_rong([chuan_hoa_ten_cot(t) for t in o])


def la_ngay_iris(token: str) -> bool:
    """True khi ô đầu dòng là ngày kiểu Iris (``2026.07.01`` / ``2026/07/01``)."""
    return bool(re.match(r"^\s*\d{4}[./-]\d{1,2}[./-]\d{1,2}\s*$", token or ""))


def tach_dong_don(dong: str) -> List[str]:
    """Tách một dòng dán thành các ô theo dấu phẩy (giữ nguyên số ô)."""
    try:
        reader = csv.reader([dong])
        return [o.strip() for o in next(reader, [])]
    except csv.Error:
        return [o.strip() for o in dong.split(",")]


def parse_dong_log_iris(
    dong: str,
    *,
    tieu_de: Optional[Sequence[str]] = None,
    jig_id: str = "",
) -> KetQuaDocIris:
    """Phân tích một dòng log Iris đã dán (kèm tiêu đề nếu người dùng dán cả hai).

    Không đoán bừa: khi thiếu tiêu đề và dòng không có cột nào nhận diện được,
    kết quả trả về có ``thieu_cot`` để lớp gọi hỏi lại bằng tiếng Việt.
    """
    cac_dong = [d for d in (dong or "").splitlines() if d.strip()]
    if not cac_dong:
        return KetQuaDocIris(loai="unit_test", thieu_cot=["dòng log"])
    tieu_de_hien_co: Optional[List[str]] = None
    dong_du_lieu: List[List[str]] = []
    for chi_so, mot_dong in enumerate(cac_dong):
        if chi_so == 0 and la_dong_tieu_de_iris(mot_dong):
            tieu_de_hien_co = [chuan_hoa_ten_cot(t) for t in tach_dong_don(mot_dong)]
            continue
        dong_du_lieu.append(tach_dong_don(mot_dong))
    if tieu_de_hien_co is None:
        if tieu_de:
            tieu_de_hien_co = [chuan_hoa_ten_cot(t) for t in tieu_de]
        elif dong_du_lieu and len(dong_du_lieu[0]) >= NGUONG_COT_MA_TRAN_RONG:
            # Ma trận rộng không kèm tiêu đề: 572–1.059 tên cột không thể đoán,
            # nên hỏi lại thay vì gán sai tên chỉ số.
            return KetQuaDocIris(
                loai="unit_test",
                so_cot=len(dong_du_lieu[0]),
                thieu_cot=["dòng tiêu đề của tệp log"],
            )
        else:
            # Không có tiêu đề: dùng đúng thứ tự cột đã ghi trong đặc tả 016.
            tieu_de_hien_co = _tieu_de_mac_dinh(len(dong_du_lieu[0]) if dong_du_lieu else 0)
    if not dong_du_lieu:
        return KetQuaDocIris(loai="unit_test", thieu_cot=["dòng dữ liệu"])
    ket_qua = _doc_ban_ghi_nhom_a(tieu_de_hien_co, dong_du_lieu, jig_id or "IrisLSU (log dán)")
    if jig_id:
        for ban_ghi in ket_qua.ban_ghi:
            ban_ghi.jig_id = jig_id
    return ket_qua


def _tieu_de_mac_dinh(so_o: int) -> List[str]:
    """Tiêu đề mặc định khi người dùng dán dòng trần không kèm tiêu đề.

    Thứ tự cột đầu của log Iris thật: ``DATE, TIME, SERIAL NUMBER, RESULT,
    RESULT:<MÀU>…`` rồi tới các cột chỉ số. Phần chỉ số không thể đoán tên,
    nên chỉ 4 ô đầu được đặt tên; phần còn lại để trống và sẽ bị bỏ qua thay
    vì gán sai tên chỉ số.
    """
    tieu_de = ["DATE", "TIME", "SERIAL NUMBER", "RESULT"]
    while len(tieu_de) < so_o:
        tieu_de.append("")
    return tieu_de


def thong_diep_thieu_cot(ket_qua: KetQuaDocIris, ten_tep: str = "") -> str:
    """Câu tiếng Việt nêu **đúng cột nào còn thiếu** thay cho câu chung chung."""
    if not ket_qua.thieu_cot:
        return ""
    if ket_qua.thieu_cot == ["dòng tiêu đề của tệp log"]:
        return (
            "Dòng log bạn dán không kèm dòng tiêu đề, mà log Iris có tới "
            f"{ket_qua.so_cot} cột nên hệ thống không thể đoán tên từng chỉ số. "
            "Vui lòng dán kèm dòng tiêu đề, hoặc mở Thẻ 1 và tải cả tệp log lên."
        )
    dau = f"Tệp {ten_tep} thiếu " if ten_tep else "Dữ liệu còn thiếu "
    return (
        f"{dau}{', '.join(ket_qua.thieu_cot)}. "
        "Vui lòng xuất lại tệp log từ JIG Iris kèm đầy đủ các cột này."
    )


def chuyen_ban_ghi_iris_sang_snapshot(
    cac_ket_qua: Sequence[KetQuaDocIris],
    *,
    nguon_tep: Optional[Sequence[str]] = None,
    now: Optional[datetime] = None,
) -> Any:
    """Chuyển kết quả đọc log Iris thành ``LsuDatasetSnapshot`` chuẩn.

    Mỗi giá trị đo hợp lệ thành một ``JigOutcomeResult`` với ``jig_id`` là mã
    máy đã lấy từ log, ``target_label`` là nhãn của đúng màu tương ứng. Nhờ vậy
    đường cổng dữ liệu, nối chuỗi và vẽ biểu đồ hiện có dùng lại nguyên vẹn,
    không cần định dạng trung gian mới.
    """
    import hashlib

    from aios_habit.production_prediction.lsu_iris import VIETNAM_TZ
    from aios_habit.production_prediction.models import JigOutcomeResult, LsuDatasetSnapshot

    thoi_diem = now or datetime.now(VIETNAM_TZ)
    jig_list: List[JigOutcomeResult] = []
    phan_tram = hashlib.sha256(b"iris-log-adapter").hexdigest()
    for ket_qua in cac_ket_qua:
        for chi_so, ban_ghi in enumerate(ket_qua.ban_ghi_hop_le(), start=1):
            jig_list.append(
                JigOutcomeResult(
                    jig_result_id=f"{phan_tram[:8]}_iris_{len(jig_list) + 1:06d}",
                    unit_serial=ban_ghi.unit_serial,
                    jig_id=ban_ghi.jig_id or "IrisLSU",
                    run_id=f"{ban_ghi.ngay} {ban_ghi.gio}".strip() or ban_ghi.metric_name,
                    event_time=ban_ghi.event_time,
                    metric_name=ban_ghi.metric_name,
                    value=ban_ghi.value,
                    unit=ban_ghi.unit or None,
                    jig_version="Iris LSU",
                    process_version="Iris LSU",
                    target_label=(ban_ghi.target_label or "UNKNOWN").upper(),
                    failure_code=None,
                    retest_outcome=None,
                    ingested_at=thoi_diem,
                    source_digest=phan_tram,
                )
            )
    gop = hashlib.sha256(
        ":".join([phan_tram] + [str(len(k.ban_ghi_hop_le())) for k in cac_ket_qua]).encode("utf-8")
    ).hexdigest()
    return LsuDatasetSnapshot(
        snapshot_id=f"snap_{gop[:16]}",
        created_at=thoi_diem,
        source_files={"jig_outcomes": ", ".join(nguon_tep or [])},
        component_measurements=[],
        unit_links=[],
        jig_outcomes=jig_list,
        content_digest=gop,
        parse_errors=[],
    )
