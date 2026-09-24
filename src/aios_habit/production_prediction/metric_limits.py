"""Ngưỡng trên/dưới thật theo (JIG, chỉ số) cho 016-iris-log-intake.

Kho ngưỡng cục bộ, thuần logic, không import Streamlit, không gọi mạng.

Nguồn ngưỡng có hai loại và **luôn được ghi rõ**:

- ``spec`` — đọc tự động từ tệp giới hạn của JIG (nhóm B: ``2026_08_Spec.csv``,
  ``2026_08_CamPos.csv``). Đây là ảnh chụp theo thời điểm, có thể đổi giữa các lô.
- ``nguoi_dung`` — người dùng nhập qua chat.

**Quy tắc an toàn (bắt buộc, có kiểm thử):** chỉ cặp ``:Lower``/``:Upper``
tường minh mới tự động có hiệu lực, vì đó là giới hạn hai phía do máy khai báo.
Các giá trị dạng dung sai một con số (``Spec:Bow[um] = 25``) **không** được
đem so trực tiếp với giá trị đo: đo thật trên 2ND-1004 cho thấy ``Bow:Black:0``
nằm trong khoảng −225…+22 nhưng vẫn được máy chấm ``OK``, nên ±25 sẽ báo động
giả hàng loạt. Chúng được lưu ở trạng thái ``cho_xac_nhan`` và chỉ dùng sau khi
người dùng xác nhận quy đổi.

**Tệp giới hạn là chuỗi theo thời điểm và theo số sê-ri.** ``2026_08_Spec.csv``
có 5.224 dòng và một S/N lặp lại nhiều lần với ngưỡng khác nhau (ví dụ S/N
``6GL1068C9206`` có cặp 50/200 mA, còn ``61C1068E6208`` có cặp 370/520 mA).
Vì vậy ``doc_nguong_tu_tep_gioi_han`` **bắt buộc** tra theo đúng ``unit_serial``
và chỉ lấy dòng có thời điểm không muộn hơn lúc đo. Tra theo dòng mới nhất của
cả tệp sẽ báo động giả lên 20% số Unit (đo được: 1/5 Unit OK bị gắn cờ sai).
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

MAC_DINH_NGUONG_PATH = Path("local_cases") / "metric_limits.json"

# Trạng thái hiệu lực của một ngưỡng.
HIEU_LUC = "hieu_luc"
CHO_XAC_NHAN = "cho_xac_nhan"

# Tên viết tắt chỉ số trong tệp Spec/CamPos → họ chỉ số trên log.
_BANG_VIET_TAT = {
    "bow": "BOW",
    "skew": "SKEW",
    "lightpath": "LIGHT_PATH",
    "beamdiameterh": "BEAM_DIAMETER:H",
    "beamdiameterv": "BEAM_DIAMETER:V",
    "beamposx": "BEAM_POS:X",
    "beamposy": "BEAM_POS:Y",
    "current": "APC:CURRENT",
    "voltage": "APC:VOLTAGE",
}


@dataclass
class NguongChiSo:
    """Ngưỡng của một chỉ số trên một JIG (tuỳ chọn theo từng số sê-ri)."""

    jig_id: str
    chi_so: str
    gioi_han_tren: Optional[float] = None
    gioi_han_duoi: Optional[float] = None
    nguon: str = ""
    thoi_diem_nguon: str = ""
    nguong_phan_tram: float = 80.0
    trang_thai: str = HIEU_LUC
    ghi_chu: str = ""
    ten_cot_nguon: str = ""
    unit_serial: str = ""
    hieu_luc_tu: str = ""

    def co_nguong(self) -> bool:
        return self.gioi_han_tren is not None or self.gioi_han_duoi is not None

    def hieu_luc(self) -> bool:
        return self.trang_thai == HIEU_LUC and self.co_nguong()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jig_id": self.jig_id,
            "chi_so": self.chi_so,
            "gioi_han_tren": self.gioi_han_tren,
            "gioi_han_duoi": self.gioi_han_duoi,
            "nguon": self.nguon,
            "thoi_diem_nguon": self.thoi_diem_nguon,
            "nguong_phan_tram": self.nguong_phan_tram,
            "trang_thai": self.trang_thai,
            "ghi_chu": self.ghi_chu,
            "ten_cot_nguon": self.ten_cot_nguon,
            "unit_serial": self.unit_serial,
            "hieu_luc_tu": self.hieu_luc_tu,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NguongChiSo":
        return cls(
            jig_id=str(data.get("jig_id", "")),
            chi_so=str(data.get("chi_so", "")),
            gioi_han_tren=_doi_so(data.get("gioi_han_tren")),
            gioi_han_duoi=_doi_so(data.get("gioi_han_duoi")),
            nguon=str(data.get("nguon", "")),
            thoi_diem_nguon=str(data.get("thoi_diem_nguon", "")),
            nguong_phan_tram=float(data.get("nguong_phan_tram", 80.0) or 80.0),
            trang_thai=str(data.get("trang_thai", HIEU_LUC)),
            ghi_chu=str(data.get("ghi_chu", "")),
            ten_cot_nguon=str(data.get("ten_cot_nguon", "")),
            unit_serial=str(data.get("unit_serial", "")),
            hieu_luc_tu=str(data.get("hieu_luc_tu", "")),
        )


@dataclass
class KhoNguong:
    """Kho ngưỡng, khoá theo ``(jig_id, chi_so, unit_serial, hieu_luc_tu)``.

    ``unit_serial`` rỗng nghĩa là ngưỡng dùng chung cho mọi Unit của JIG đó.
    ``hieu_luc_tu`` là mốc thời gian ngưỡng bắt đầu có hiệu lực (ISO). Cùng một
    S/N có thể có nhiều dải theo thời gian, nên phải giữ theo mốc chứ không chỉ
    theo S/N — nếu không, dải mới sẽ bị áp ngược cho lần đo cũ.
    """

    cac_nguong: Dict[Tuple[str, str, str, str], NguongChiSo] = field(default_factory=dict)

    def dat(self, nguong: NguongChiSo) -> None:
        self.cac_nguong[
            (nguong.jig_id, nguong.chi_so, nguong.unit_serial, nguong.hieu_luc_tu)
        ] = nguong

    def lay(
        self,
        jig_id: str,
        chi_so: str,
        unit_serial: str = "",
        luc_do: Any = None,
    ) -> Optional[NguongChiSo]:
        """Tra ngưỡng có hiệu lực cho ``(JIG, chỉ số, Unit)`` tại thời điểm đo.

        Khi truyền ``luc_do``, chỉ xét các bản ghi có mốc hiệu lực không muộn hơn
        thời điểm đo, rồi chọn mốc gần nhất — nhờ vậy dải mới không bị áp ngược
        cho lần đo cũ và ngược lại không dùng dải tương lai.

        Không bao giờ lấy ngưỡng của Unit khác, vì mỗi S/N có thể có dải khác
        nhau và tra sai S/N sẽ gây báo động giả.

        Bản ghi ``cho_xac_nhan`` (dung sai một con số) **không** được coi là
        ngưỡng khi còn ứng viên đã hiệu lực: nếu trả nó về, lớp gọi sẽ tưởng là
        không có ngưỡng và rơi về EWMA, làm mất hiệu lực ngưỡng dùng chung thật.
        """
        moc_do = _doi_moc(luc_do)
        ung_vien: List[Tuple[int, str, NguongChiSo]] = []
        for (jig_khoa, chi_so_khoa, sn_khoa, moc_khoa), nguong in sorted(self.cac_nguong.items()):
            if chi_so_khoa != chi_so:
                continue
            if sn_khoa:
                if not unit_serial or sn_khoa != unit_serial:
                    continue  # Ngưỡng của Unit khác: không bao giờ dùng.
            if jig_khoa and jig_id and jig_khoa != jig_id:
                continue
            if moc_do is not None and moc_khoa:
                moc_nguong = _doi_moc(moc_khoa)
                if moc_nguong is not None and moc_nguong > moc_do:
                    continue  # Ngưỡng chưa có hiệu lực tại thời điểm đo.
            # Ưu tiên: người dùng nhập tay > ngưỡng riêng của Unit > ngưỡng dùng
            # chung. Người dùng nhập qua chat không biết JIG/Unit nên tuyệt đối
            # không được để ngưỡng đọc tự động từ tệp đè lên ý muốn của họ.
            if nguong.nguon == "nguoi_dung":
                uu_tien = -2
            elif sn_khoa:
                uu_tien = 0
            else:
                uu_tien = 2
            ung_vien.append((uu_tien, moc_khoa, nguong))
        if not ung_vien:
            return None
        # Chỉ xét bản ghi đã hiệu lực; chỉ khi không có mới trả bản chờ xác nhận
        # (để lớp gọi còn nêu được lý do cho người dùng).
        da_hieu_luc = [u for u in ung_vien if u[2].hieu_luc()]
        chon = da_hieu_luc or ung_vien
        # Ưu tiên theo mức cụ thể (ngưỡng riêng của Unit, rồi người dùng nhập)
        # TRƯỚC, rồi mới tới mốc hiệu lực gần nhất. Ngưỡng người dùng nhập có
        # ``hieu_luc_tu`` rỗng nên luôn được coi là mới nhất.
        return max(chon, key=lambda u: (-u[0], u[1] or "9999"))[2]

    def xoa(self, jig_id: str, chi_so: str, unit_serial: str = "") -> bool:
        """Xoá mọi ngưỡng khớp ``(JIG, chỉ số, Unit)``; trả True nếu có xoá."""
        khoa = [
            k for k in self.cac_nguong
            if k[1] == chi_so and k[2] == unit_serial and (not jig_id or k[0] == jig_id)
        ]
        for k in khoa:
            del self.cac_nguong[k]
        return bool(khoa)

    def danh_sach(self) -> List[NguongChiSo]:
        return [self.cac_nguong[k] for k in sorted(self.cac_nguong)]

    def to_dict(self) -> Dict[str, Any]:
        return {"cac_nguong": [n.to_dict() for n in self.danh_sach()]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KhoNguong":
        kho = cls()
        for muc in data.get("cac_nguong", []) or []:
            if isinstance(muc, dict):
                kho.dat(NguongChiSo.from_dict(muc))
        return kho


def _doi_so(gia_tri: Any) -> Optional[float]:
    if gia_tri is None or gia_tri == "":
        return None
    try:
        return float(str(gia_tri).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _doi_moc(gia_tri: Any) -> Optional[datetime]:
    """Đổi mốc thời gian (datetime hoặc chuỗi ISO) thành ``datetime``."""
    if gia_tri is None or gia_tri == "":
        return None
    if isinstance(gia_tri, datetime):
        return gia_tri.replace(tzinfo=None) if gia_tri.tzinfo else gia_tri
    try:
        moc = datetime.fromisoformat(str(gia_tri))
    except (TypeError, ValueError):
        return None
    return moc.replace(tzinfo=None) if moc.tzinfo else moc


def _chuan_hoa(text: str) -> str:
    return re.sub(r"[\s_\-]+", "", (text or "").strip().lower())


def chuan_hoa_ten_cot(ten: str) -> str:
    """Chuẩn hoá tên cột: gộp khoảng trắng thừa và cắt hai đầu."""
    return " ".join((ten or "").strip().split())


def _la_cot_spec(ten: str) -> bool:
    """True khi tên cột thuộc nhóm giới hạn (``Spec:…`` hoặc ``:Lower``/``:Upper``)."""
    chuan = chuan_hoa_ten_cot(ten)
    if chuan.upper().startswith("SPEC:"):
        return True
    return la_gioi_han_tuong_minh(chuan)


def chi_so_tu_ten_cot(ten_cot: str) -> str:
    """Quy tên cột tệp giới hạn thành mã chỉ số chuẩn.

    ``Spec:BeamPosX:Lower[um]`` → ``BEAM_POS:X``; ``Spec:Bow[um]`` → ``BOW``.
    """
    ten = (ten_cot or "").strip()
    if ten.upper().startswith("SPEC:"):
        ten = ten.split(":", 1)[1]
    ten = re.sub(r"\[[^\]]*\]", "", ten).strip()
    phan = [p.strip() for p in ten.split(":") if p.strip()]
    if not phan:
        return ""
    # Bỏ hậu tố giới hạn nếu còn sót.
    phan = [p for p in phan if p.lower() not in ("lower", "upper")]
    dau = _chuan_hoa(phan[0])
    goc = _BANG_VIET_TAT.get(dau)
    if goc is None:
        goc = phan[0].upper()
    if len(phan) > 1 and goc in ("BEAM_DIAMETER", "BEAM_POS"):
        return f"{goc}:{phan[1].upper()}"
    return goc


def _bo_don_vi(ten_cot: str) -> str:
    """Bỏ phần đơn vị ``[...]`` để xét hậu tố giới hạn."""
    return re.sub(r"\[[^\]]*\]\s*$", "", (ten_cot or "").strip()).strip()


def la_gioi_han_tuong_minh(ten_cot: str) -> bool:
    """True khi tên cột là giới hạn hai phía tường minh (``:Lower``/``:Upper``).

    Tên thật có đơn vị ở cuối (``Spec:Current:Lower[mA]``), nên phải bỏ ``[…]``
    trước khi xét hậu tố.
    """
    upper = _bo_don_vi(ten_cot).upper()
    return upper.endswith(":LOWER") or upper.endswith(":UPPER")


def ngung_do_tu_tep_gioi_han(
    jig_id: str,
    cac_cot: Dict[str, Dict[str, Any]],
    *,
    nguon: str = "",
    thoi_diem: str = "",
    nguong_phan_tram: float = 80.0,
    unit_serial: str = "",
) -> List[NguongChiSo]:
    """Dựng ngưỡng từ kết quả ``iris_log_adapter.doc_nhom_b_gioi_han``.

    Cặp ``:Lower``/``:Upper`` tường minh → ``hieu_luc`` (dùng được ngay).
    Giá trị dung sai một con số (``Spec:Bow[um]``) → ``cho_xac_nhan`` kèm ghi
    chú tiếng Việt giải thích vì sao chưa dùng được.

    ``thoi_diem`` là mốc ngưỡng bắt đầu có hiệu lực; được ghi vào cả
    ``thoi_diem_nguon`` (để hiển thị) lẫn ``hieu_luc_tu`` (để tra theo thời
    điểm đo).
    """
    ket_qua: List[NguongChiSo] = []
    # Gom theo chỉ số: {chi_so: {"lower": (cot, gia_tri), "upper": (...)}}.
    gom: Dict[str, Dict[str, Tuple[str, float]]] = {}
    dung_sai: List[Tuple[str, str, float]] = []
    for ten_cot, thong_tin in (cac_cot or {}).items():
        gia_tri = _doi_so(thong_tin.get("gia_tri_moi_nhat"))
        if gia_tri is None:
            continue
        chi_so = chi_so_tu_ten_cot(ten_cot)
        if not chi_so:
            continue
        upper = _bo_don_vi(ten_cot).upper()
        if upper.endswith(":LOWER"):
            gom.setdefault(chi_so, {})["lower"] = (ten_cot, gia_tri)
        elif upper.endswith(":UPPER"):
            gom.setdefault(chi_so, {})["upper"] = (ten_cot, gia_tri)
        else:
            dung_sai.append((chi_so, ten_cot, gia_tri))

    for chi_so, cap in gom.items():
        duoi = cap.get("lower")
        tren = cap.get("upper")
        ket_qua.append(
            NguongChiSo(
                jig_id=jig_id,
                chi_so=chi_so,
                gioi_han_duoi=duoi[1] if duoi else None,
                gioi_han_tren=tren[1] if tren else None,
                nguon=nguon,
                thoi_diem_nguon=thoi_diem,
                nguong_phan_tram=nguong_phan_tram,
                trang_thai=HIEU_LUC,
                ghi_chu="Giới hạn hai phía tường minh do JIG khai báo, dùng được ngay.",
                ten_cot_nguon=", ".join(x[0] for x in (duoi, tren) if x),
                unit_serial=unit_serial,
                hieu_luc_tu=thoi_diem,
            )
        )
    for chi_so, ten_cot, gia_tri in dung_sai:
        ket_qua.append(
            NguongChiSo(
                jig_id=jig_id,
                chi_so=chi_so,
                gioi_han_tren=None,
                gioi_han_duoi=None,
                nguon=nguon,
                thoi_diem_nguon=thoi_diem,
                nguong_phan_tram=nguong_phan_tram,
                trang_thai=CHO_XAC_NHAN,
                ghi_chu=(
                    f"Tệp giới hạn ghi {ten_cot} = {gia_tri:g} nhưng đây là dung sai một con số, "
                    "không phải giới hạn trên/dưới. Cần người dùng xác nhận cách quy đổi "
                    "trước khi dùng để cảnh báo."
                ),
                ten_cot_nguon=ten_cot,
                unit_serial=unit_serial,
                hieu_luc_tu=thoi_diem,
            )
        )
    return ket_qua


def phan_loai_theo_nguong(
    gia_tri: Optional[float],
    nguong: Optional[NguongChiSo],
) -> Optional[Dict[str, Any]]:
    """So một giá trị đo với ngưỡng thật; trả ``None`` khi không có ngưỡng hiệu lực.

    Mức ``Cận biên`` bắt đầu từ ``nguong_phan_tram`` của dải dung sai, đúng như
    câu mô tả cấu hình người dùng đã thấy trên giao diện.
    """
    if gia_tri is None or nguong is None or not nguong.hieu_luc():
        return None
    tren = nguong.gioi_han_tren
    duoi = nguong.gioi_han_duoi
    phan_tram = nguong.nguong_phan_tram if nguong.nguong_phan_tram else 80.0
    if tren is not None and gia_tri > tren:
        return {
            "trang_thai": "Vi phạm",
            "canh_bao": True,
            "chi_tiet": (
                f"Giá trị {gia_tri:g} vượt giới hạn trên {tren:g} của {nguong.chi_so} "
                f"(nguồn: {nguong.nguon or 'chưa rõ'})."
            ),
        }
    if duoi is not None and gia_tri < duoi:
        return {
            "trang_thai": "Vi phạm",
            "canh_bao": True,
            "chi_tiet": (
                f"Giá trị {gia_tri:g} dưới giới hạn dưới {duoi:g} của {nguong.chi_so} "
                f"(nguồn: {nguong.nguon or 'chưa rõ'})."
            ),
        }
    # Dải dung sai hai phía: tính mức đã dùng tới.
    if tren is not None and duoi is not None and tren > duoi:
        tam = (tren + duoi) / 2
        nua_dai = (tren - duoi) / 2
        muc_dung = abs(gia_tri - tam) / nua_dai * 100.0 if nua_dai > 0 else 0.0
        if muc_dung >= phan_tram:
            return {
                "trang_thai": "Cận biên",
                "canh_bao": False,
                "chi_tiet": (
                    f"Giá trị {gia_tri:g} đã dùng {muc_dung:.0f}% dải dung sai "
                    f"[{duoi:g}, {tren:g}] của {nguong.chi_so}, chạm mức theo dõi {phan_tram:g}%."
                ),
            }
        return {
            "trang_thai": "Đạt",
            "canh_bao": False,
            "chi_tiet": (
                f"Giá trị {gia_tri:g} nằm trong dải dung sai [{duoi:g}, {tren:g}] "
                f"của {nguong.chi_so}."
            ),
        }
    return {
        "trang_thai": "Đạt",
        "canh_bao": False,
        "chi_tiet": f"Giá trị {gia_tri:g} nằm trong giới hạn đã khai báo của {nguong.chi_so}.",
    }


def _tim_cot(tieu_de: Sequence[str], ten_ung_vien: Iterable[str]) -> Optional[int]:
    chuan = [chuan_hoa_ten_cot(t).lower() for t in tieu_de]
    for ung_vien in ten_ung_vien:
        if ung_vien.lower() in chuan:
            return chuan.index(ung_vien.lower())
    return None


def _tim_cot_serial(tieu_de: Sequence[str]) -> Optional[int]:
    return _tim_cot(tieu_de, ("s/n", "serial number", "serial", "sn"))


def ghep_thoi_gian(ngay: str, gio: str) -> Optional[datetime]:
    """Ghép ngày/giờ của tệp giới hạn (``2026/08/01`` + ``13:21:48``)."""
    ngay_sach = chuan_hoa_ten_cot(ngay).replace(".", "-").replace("/", "-")
    gio_sach = chuan_hoa_ten_cot(gio)
    if not ngay_sach:
        return None
    for dinh_dang in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(f"{ngay_sach} {gio_sach}".strip(), dinh_dang)
        except ValueError:
            continue
    return None


def doc_nguong_tu_tep_gioi_han(
    duong_dan: str | Path,
    unit_serial: str,
    *,
    luc_do: Optional[Any] = None,
    jig_id: str = "",
    nguon: str = "",
) -> List[NguongChiSo]:
    """Đọc ngưỡng từ tệp Spec/CamPos **theo đúng S/N và thời điểm đo**.

    Tệp giới hạn là chuỗi theo thời điểm; mỗi S/N có thể xuất hiện nhiều lần với
    ngưỡng khác nhau. Hàm chỉ lấy dòng của đúng ``unit_serial`` và có thời điểm
    không muộn hơn ``luc_do``, rồi dựng ngưỡng bằng
    ``ngung_do_tu_tep_gioi_han``. Không có dòng phù hợp thì trả danh sách rỗng
    (không đoán, không dùng dòng của S/N khác).
    """
    path = Path(duong_dan)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            cac_dong = [r for r in csv.reader(f)]
    except (OSError, UnicodeDecodeError):
        return []
    if not cac_dong:
        return []
    tieu_de = [chuan_hoa_ten_cot(c) for c in cac_dong[0]]
    i_serial = _tim_cot_serial(tieu_de)
    i_ngay = _tim_cot(tieu_de, ("date",))
    i_gio = _tim_cot(tieu_de, ("time",))
    if i_serial is None:
        return []
    ung_vien: List[Tuple[Any, Sequence[str]]] = []
    for dong in cac_dong[1:]:
        if i_serial >= len(dong):
            continue
        if (dong[i_serial] or "").strip() != unit_serial:
            continue
        thoi_diem = None
        if i_ngay is not None and i_gio is not None:
            thoi_diem = ghep_thoi_gian(dong[i_ngay] if i_ngay < len(dong) else "",
                                       dong[i_gio] if i_gio < len(dong) else "")
        ung_vien.append((thoi_diem, dong))
    if not ung_vien:
        return []
    if luc_do is not None:
        khong_muon_hon = [u for u in ung_vien if u[0] is not None and u[0] <= luc_do]
        if not khong_muon_hon:
            # Không có dòng nào có thời điểm hợp lệ và không muộn hơn lúc đo:
            # trả rỗng thay vì lấy dòng tương lai hoặc dòng thiếu thời điểm, vì
            # làm vậy là rò rỉ thông tin tương lai vào quyết định cảnh báo.
            if any(u[0] is not None for u in ung_vien):
                return []
            # Toàn bộ dòng của S/N này đều thiếu thời điểm: không xác định được
            # mốc hiệu lực nên cũng không dùng.
            return []
        ung_vien = khong_muon_hon
    # Dòng mới nhất không muộn hơn lúc đo là dòng có hiệu lực.
    co_thoi_diem = [u for u in ung_vien if u[0] is not None]
    if co_thoi_diem:
        moc, dong_hieu_luc = max(co_thoi_diem, key=lambda u: u[0])
        hieu_luc_tu = moc.isoformat()
    else:
        dong_hieu_luc = ung_vien[-1][1]
        hieu_luc_tu = ""
    cac_cot: Dict[str, Dict[str, Any]] = {}
    for idx, ten in enumerate(tieu_de):
        if not _la_cot_spec(ten):
            continue
        gia_tri: List[float] = []
        for _, dong in ung_vien:
            if idx >= len(dong):
                continue
            so = _doi_so(dong[idx])
            if so is not None:
                gia_tri.append(so)
        if not gia_tri:
            continue
        hieu_luc = dong_hieu_luc[idx] if idx < len(dong_hieu_luc) else ""
        cac_cot[ten] = {
            "ten_cot_nguon": ten,
            "gia_tri": sorted(set(gia_tri)),
            "gia_tri_moi_nhat": _doi_so(hieu_luc) if _doi_so(hieu_luc) is not None else gia_tri[-1],
            "so_dong": len(gia_tri),
        }
    ten_nguon = nguon or path.name
    return ngung_do_tu_tep_gioi_han(
        jig_id,
        cac_cot,
        nguon=ten_nguon,
        unit_serial=unit_serial,
        thoi_diem=hieu_luc_tu,
    )


def nap_nguong_tu_tep_gioi_han(
    kho: KhoNguong,
    duong_dan: str | Path,
    cac_do_dac: Iterable[Any],
    *,
    jig_id: str = "",
    nguon: str = "",
) -> KhoNguong:
    """Nạp ngưỡng từ tệp Spec/CamPos cho từng lần đo trong ``cac_do_dac``.

    Mỗi lần đo tra đúng ``unit_serial`` và đúng thời điểm, nên nạp được nhiều
    dải khác nhau cho cùng một JIG. Ngưỡng đã hiệu lực không bị ghi đè.
    """
    for do_dac in cac_do_dac:
        unit_serial = str(getattr(do_dac, "unit_serial", "") or "").strip()
        if not unit_serial:
            continue
        luc_do = getattr(do_dac, "event_time", None)
        for nguong in doc_nguong_tu_tep_gioi_han(
            duong_dan, unit_serial, luc_do=luc_do, jig_id=jig_id, nguon=nguon
        ):
            # Khoá đã gồm mốc hiệu lực, nên nhiều dải theo thời gian cùng tồn tại
            # và mỗi lần đo tra đúng dải của mốc gần nhất không muộn hơn nó.
            khoa = (
                nguong.jig_id,
                nguong.chi_so,
                nguong.unit_serial,
                nguong.hieu_luc_tu,
            )
            hien_co = kho.cac_nguong.get(khoa)
            if hien_co is not None and hien_co.hieu_luc():
                continue
            # Người dùng nhập tay luôn thắng ngưỡng đọc tự động.
            if hien_co is not None and hien_co.nguon == "nguoi_dung":
                continue
            kho.dat(nguong)
    return kho


def doc_nguong(path: str | Path = MAC_DINH_NGUONG_PATH) -> KhoNguong:
    """Đọc kho ngưỡng cục bộ; trả kho rỗng khi thiếu tệp hoặc tệp hỏng."""
    duong_dan = Path(path)
    if not duong_dan.exists():
        return KhoNguong()
    try:
        du_lieu = json.loads(duong_dan.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return KhoNguong()
    if not isinstance(du_lieu, dict):
        return KhoNguong()
    return KhoNguong.from_dict(du_lieu)


def luu_nguong(kho: KhoNguong, path: str | Path = MAC_DINH_NGUONG_PATH) -> None:
    """Ghi kho ngưỡng ra tệp cục bộ (không bao giờ vào Git)."""
    duong_dan = Path(path)
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    duong_dan.write_text(
        json.dumps(kho.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def bang_nguong_van_ban(kho: KhoNguong, jig_id: str = "") -> str:
    """Bảng ngưỡng dạng văn bản để hiện thẳng trong chat."""
    muc = [n for n in kho.danh_sach() if not jig_id or n.jig_id == jig_id]
    if not muc:
        return "Chưa có ngưỡng nào được thiết lập cho JIG này."
    dong = ["Bảng ngưỡng theo dõi", "------------------------"]
    for n in muc:
        if n.trang_thai == CHO_XAC_NHAN:
            mo_ta = f"chờ xác nhận ({n.ten_cot_nguon or n.chi_so})"
        else:
            tren = f"{n.gioi_han_tren:g}" if n.gioi_han_tren is not None else "—"
            duoi = f"{n.gioi_han_duoi:g}" if n.gioi_han_duoi is not None else "—"
            mo_ta = f"dưới {duoi} / trên {tren} · mức theo dõi {n.nguong_phan_tram:g}%"
        dong.append(f"- {n.jig_id or 'mọi JIG'} · {n.chi_so}: {mo_ta}")
    dong.append("------------------------")
    dong.append(
        "Bạn chỉ cần nhắn, ví dụ: đặt ngưỡng trên 25 cho Bow, "
        "xem ngưỡng, hoặc xóa ngưỡng Bow."
    )
    return "\n".join(dong)


_SO_TRONG_CAU = re.compile(r"(-?\d+(?:[.,]\d+)?)")


def _khong_dau(text: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp lệnh chat (không phân biệt có dấu)."""
    chuoi = unicodedata.normalize("NFD", (text or "").strip().lower())
    khong_dau = "".join(ky_tu for ky_tu in chuoi if unicodedata.category(ky_tu) != "Mn")
    return khong_dau.replace("đ", "d")


def la_lenh_nguong(text: str) -> bool:
    """True khi câu chat là lệnh về ngưỡng theo chỉ số (016 T016-09)."""
    cau = _khong_dau(text)
    if not cau:
        return False
    co_dong_tu = any(
        tu in cau for tu in ("nguong", "gioi han", "dat nguong", "xoa nguong")
    )
    if not co_dong_tu:
        return False
    # Không giành lấy lệnh cấu hình cảnh báo chung (email/giãn cách/gộp tin).
    if any(tu in cau for tu in ("email", "gian cach", "gop tin", "bang cau hinh", "cau hinh canh bao")):
        return False
    # ``đổi ngưỡng 90`` (không có dấu %, không nêu trên/dưới) vẫn là ngưỡng phần
    # trăm dung sai của cảnh báo, không phải ngưỡng của một chỉ số. Nhưng
    # ``đổi ngưỡng trên 25 cho Bow`` nêu rõ phía và chỉ số nên vẫn là lệnh ngưỡng.
    if (cau.startswith("doi ") or cau.startswith("thay ")) and not (
        "tren" in cau or "duoi" in cau or "gioi han tren" in cau or "gioi han duoi" in cau
    ):
        return False
    if "%" in cau or "phan tram" in cau or "dung sai" in cau:
        return False
    return True


def xu_ly_lenh_nguong(
    text: str,
    kho: KhoNguong,
    *,
    jig_id: str = "",
) -> Tuple[KhoNguong, str]:
    """Cập nhật kho ngưỡng từ một câu chat; trả (kho mới, lời nhắn tiếng Việt).

    Hỗ trợ: ``xem ngưỡng``, ``đặt ngưỡng trên 25 cho Bow``,
    ``đặt ngưỡng dưới 1.2 cho BeamPosX``, ``xóa ngưỡng Bow``.
    """
    cau = _khong_dau(text)
    if not cau:
        return kho, "Bạn nhắn yêu cầu về ngưỡng, ví dụ: đặt ngưỡng trên 25 cho Bow."
    if "xoa" in cau:
        chi_so = _tim_chi_so_trong_cau(cau, kho)
        if not chi_so:
            return kho, "Bạn ghi rõ chỉ số cần xóa ngưỡng, ví dụ: xóa ngưỡng Bow."
        da_xoa = kho.xoa(jig_id, chi_so)
        if not da_xoa:
            # Thử xóa không kèm JIG khi người dùng chưa nêu mã JIG.
            da_xoa = any(n.chi_so == chi_so and kho.xoa(n.jig_id, n.chi_so) for n in list(kho.danh_sach()))
        if not da_xoa:
            return kho, f"Không tìm thấy ngưỡng nào của {chi_so} để xóa."
        return kho, f"Đã xóa ngưỡng của {chi_so}.\n\n" + bang_nguong_van_ban(kho, jig_id)
    so = _SO_TRONG_CAU.search(cau)
    if so is None:
        return kho, bang_nguong_van_ban(kho, jig_id)
    chi_so = _tim_chi_so_trong_cau(cau, kho)
    if not chi_so:
        return kho, (
            "Bạn ghi rõ chỉ số cần đặt ngưỡng, ví dụ: đặt ngưỡng trên 25 cho Bow "
            "hoặc đặt ngưỡng dưới 1.2 cho BeamPosX."
        )
    gia_tri = _doi_so(so.group(1))
    if gia_tri is None:
        return kho, "Giá trị ngưỡng chưa phải là số. Vui lòng ghi lại, ví dụ: đặt ngưỡng trên 25 cho Bow."
    co_tren = "tren" in cau or "gioi han tren" in cau or "upper" in cau
    co_duoi = "duoi" in cau or "gioi han duoi" in cau or "lower" in cau
    if not co_tren and not co_duoi:
        return kho, (
            "Bạn cho biết đây là ngưỡng trên hay ngưỡng dưới, "
            "ví dụ: đặt ngưỡng trên 25 cho Bow."
        )
    cu = kho.lay(jig_id, chi_so)
    moi = NguongChiSo(
        jig_id=jig_id,
        chi_so=chi_so,
        gioi_han_tren=gia_tri if co_tren else (cu.gioi_han_tren if cu else None),
        gioi_han_duoi=gia_tri if co_duoi else (cu.gioi_han_duoi if cu else None),
        nguon="nguoi_dung",
        thoi_diem_nguon="",
        nguong_phan_tram=cu.nguong_phan_tram if cu else 80.0,
        trang_thai=HIEU_LUC,
        ghi_chu="Người dùng nhập qua chat.",
    )
    kho.dat(moi)
    phia = "trên" if co_tren else "dưới"
    return kho, (
        f"Đã đặt ngưỡng {phia} {gia_tri:g} cho {chi_so}"
        + (f" trên JIG {jig_id}" if jig_id else "")
        + ".\n\n" + bang_nguong_van_ban(kho, jig_id)
    )


_RE_MA_CHI_SO_TRONG_CAU = re.compile(r"\b([A-Z][A-Z0-9_]{2,}(?::[A-Z0-9_+\-]+)+)\b")


def _tim_chi_so_trong_cau(cau: str, kho: KhoNguong) -> str:
    """Tìm chỉ số được nhắc trong câu, ưu tiên mã đã có trong kho ngưỡng.

    Người dùng phải gõ được **mã chỉ số thật** (kể cả mã dài của log đo sâu như
    ``DEPTH:BEAM:H:LD1:IMGHEIGHT:+140``) vì đó chính là gợi ý hệ thống in ra.
    """
    cau_goc = (cau or "").strip()
    cau_khong_dau = _khong_dau(cau_goc)
    da_biet = sorted({n.chi_so for n in kho.danh_sach()}, key=len, reverse=True)
    for chi_so in da_biet:
        if _khong_dau(chi_so) in cau_khong_dau or _chuan_hoa(chi_so) in _chuan_hoa(cau_khong_dau):
            return chi_so
    # Mã chỉ số gõ thẳng trong câu (giữ nguyên chữ hoa, xét trên **câu gốc** vì
    # ``_khong_dau`` làm mất dấu '+' và chữ hoa của mã).
    ung_vien = _RE_MA_CHI_SO_TRONG_CAU.findall(cau_goc.upper())
    if ung_vien:
        # Chọn mã dài nhất: ``DEPTH:…:+140`` thay vì ``DEPTH:…`` nếu người dùng gõ đủ.
        return max(ung_vien, key=len)
    for ten, ma in (
        ("bow", "BOW"), ("do lech", "BOW"), ("độ lệch", "BOW"),
        ("skew", "SKEW"), ("do nghieng", "SKEW"), ("độ nghiêng", "SKEW"),
        ("beamposx", "BEAM_POS:X"), ("beamposy", "BEAM_POS:Y"),
        ("lightpath", "LIGHT_PATH"), ("duong di anh sang", "LIGHT_PATH"),
        ("beamdiameterh", "BEAM_DIAMETER:H"), ("beamdiameterv", "BEAM_DIAMETER:V"),
        ("current", "APC:CURRENT"), ("voltage", "APC:VOLTAGE"),
    ):
        if _khong_dau(ten) in cau_khong_dau:
            return ma
    return ""
