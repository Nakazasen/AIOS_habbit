"""Nhap nguyen mot tep CSV log JIG mot lan (ve J1-CSV).

Pure logic (khong phu thuoc Streamlit) de contract test chay nhanh.
Ho tro hai dinh dang san pham dang hieu:

- Ma tran rong Iris (BOWSKEW): dong tieu de duoc adapter nhan dien.
- Dong log rieng le kieu 7 cot: timestamp, unit_serial, jig_id, metric,
  value, unit, status.

Chong nhap trung cap tep: van tay sha256 + kich thuoc + mtime luu trong
bang JSON canh kho; tep khong doi thi bo qua ngay tu cua, khong doc lai.
Bang nhap tep la tep cuc bo (local_cases), khong bao gio commit.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from aios_habit.production_prediction.iris_log_adapter import (
    la_dong_tieu_de_iris,
    parse_dong_log_iris,
    thong_diep_thieu_cot,
)
from aios_habit.production_prediction.jig_log_ingest import parse_jig_log_line
from aios_habit.production_prediction.log_archive import (
    MAC_DINH_KHO_PATH,
    VIETNAM_TZ,
    ghi_ban_ghi,
    ghi_dong_log_jig,
)

MAC_DINH_BANG_NHAP_TEP = Path("local_cases") / "jig_log_archive" / "bang_nhap_tep.json"


@dataclass
class NhapTepKetQua:
    """Ket qua mot lan nhap tep CSV log JIG."""

    ten_tep: str
    dinh_dang: str  # "iris_rong" | "dong_le" | ""
    van_tay: str
    da_ghi: int = 0
    bo_qua_rong: int = 0
    bi_cat: int = 0
    bo_qua_vi_trung: bool = False
    thoi_gian: str = ""


def tinh_van_tay_tep(duong_dan: str | Path) -> str:
    """Tinh sha256 cua tep de phat hien tep da nhap."""
    sha = hashlib.sha256()
    with open(duong_dan, "rb") as f:
        for khoi in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(khoi)
    return sha.hexdigest()


def doc_bang_nhap_tep(duong_dan: str | Path = MAC_DINH_BANG_NHAP_TEP) -> Dict[str, Any]:
    """Doc bang van tay cac tep da nhap; tep chua co thi tra dict rong."""
    duong = Path(duong_dan)
    if not duong.exists():
        return {}
    try:
        du_lieu = json.loads(duong.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return du_lieu if isinstance(du_lieu, dict) else {}


def luu_bang_nhap_tep(
    bang: Dict[str, Any], duong_dan: str | Path = MAC_DINH_BANG_NHAP_TEP
) -> None:
    """Luu bang van tay xuong dia (tep cuc bo, khong commit)."""
    duong = Path(duong_dan)
    duong.parent.mkdir(parents=True, exist_ok=True)
    duong.write_text(json.dumps(bang, ensure_ascii=False, indent=2), encoding="utf-8")


def _khoa_tep(duong_dan: str | Path) -> str:
    return str(Path(duong_dan).resolve())


def _dong_dau_tien(van_ban: str) -> str:
    for dong in van_ban.splitlines():
        if dong.strip():
            return dong
    return ""


def nhap_tep_csv_log(
    duong_dan: str | Path,
    *,
    kho: str | Path = MAC_DINH_KHO_PATH,
    bang_nhap_tep: str | Path = MAC_DINH_BANG_NHAP_TEP,
    ghi_luc: Optional[datetime] = None,
) -> NhapTepKetQua:
    """Nhap nguyen mot tep CSV log JIG vao kho, chong trung cap tep.

    Tra ve ``NhapTepKetQua`` voi ``bo_qua_vi_trung=True`` khi tep khong doi
    so voi lan nhap truoc (khong doc lai, khong ghi them dong nao).
    Nem ``ValueError`` tieng Viet khi tep khong ton tai, khong phai CSV,
    hoac khong dung dinh dang log JIG san pham dang hieu.
    """
    duong = Path(duong_dan)
    if not duong.is_file():
        raise ValueError(
            "Không tìm thấy tệp " + str(duong_dan) + ". "
            "Vui lòng kiểm tra lại đường dẫn rồi nhập lại."
        )
    if duong.suffix.lower() != ".csv":
        raise ValueError(
            "Tệp " + duong.name + " không phải CSV. "
            "Chức năng nhập tệp log hiện chỉ nhận tệp .csv."
        )
    thong_tin = duong.stat()
    van_tay = tinh_van_tay_tep(duong)
    bang = doc_bang_nhap_tep(bang_nhap_tep)
    khoa = _khoa_tep(duong)
    cu = bang.get(khoa)
    if (
        isinstance(cu, dict)
        and cu.get("sha256") == van_tay
        and cu.get("kich_thuoc") == thong_tin.st_size
        and cu.get("mtime") == thong_tin.st_mtime
    ):
        return NhapTepKetQua(
            ten_tep=duong.name,
            dinh_dang=str(cu.get("dinh_dang") or ""),
            van_tay=van_tay,
            bo_qua_vi_trung=True,
            thoi_gian=str(cu.get("thoi_gian") or ""),
        )
    try:
        van_ban = duong.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        raise ValueError(
            "Không đọc được tệp " + duong.name + ". "
            "Vui lòng kiểm tra quyền đọc tệp rồi thử lại."
        )
    dong_dau = _dong_dau_tien(van_ban)
    if not dong_dau:
        raise ValueError("Tệp " + duong.name + " đang trống, không có gì để nhập.")
    if la_dong_tieu_de_iris(dong_dau):
        ket_qua = _nhap_ma_tran_iris(duong, van_ban, kho, ghi_luc)
    else:
        ket_qua = _nhap_dong_le(duong, van_ban, kho, ghi_luc)
    bang[khoa] = {
        "sha256": van_tay,
        "kich_thuoc": thong_tin.st_size,
        "mtime": thong_tin.st_mtime,
        "dinh_dang": ket_qua.dinh_dang,
        "da_ghi": ket_qua.da_ghi,
        "thoi_gian": ket_qua.thoi_gian,
    }
    luu_bang_nhap_tep(bang, bang_nhap_tep)
    return ket_qua


def _nhap_ma_tran_iris(
    duong: Path, van_ban: str, kho: str | Path, ghi_luc: Optional[datetime]
) -> NhapTepKetQua:
    ket_qua_doc = parse_dong_log_iris(van_ban)
    if ket_qua_doc.thieu_cot:
        raise ValueError(thong_diep_thieu_cot(ket_qua_doc, duong.name))
    hop_le = ket_qua_doc.ban_ghi_hop_le()
    if not hop_le:
        raise ValueError(
            "Tệp " + duong.name + " không có giá trị đo nào dùng được. "
            "Các ô mang giá trị canh lỗi 999 (máy không đo được) đã bị bỏ qua."
        )
    luc = ghi_luc or datetime.now(VIETNAM_TZ)
    ket_qua_ghi = ghi_ban_ghi(hop_le, nguon="tep", tep=str(duong), kho=kho, ghi_luc=luc)
    return NhapTepKetQua(
        ten_tep=duong.name,
        dinh_dang="iris_rong",
        van_tay=tinh_van_tay_tep(duong),
        da_ghi=int(ket_qua_ghi.get("da_ghi", 0)),
        bo_qua_rong=int(ket_qua_ghi.get("bo_qua_rong", 0)),
        bi_cat=int(ket_qua_ghi.get("bi_cat", 0)),
        thoi_gian=luc.replace(microsecond=0).isoformat(),
    )


def _nhap_dong_le(
    duong: Path, van_ban: str, kho: str | Path, ghi_luc: Optional[datetime]
) -> NhapTepKetQua:
    cac_dong_log: List[Any] = []
    for dong in van_ban.splitlines():
        if not dong.strip():
            continue
        da_phan_tich = parse_jig_log_line(dong)
        if da_phan_tich is not None:
            cac_dong_log.append(da_phan_tich)
    if not cac_dong_log:
        raise ValueError(
            "Tệp " + duong.name + " không chứa dòng log JIG nào hệ thống hiểu được. "
            "Hệ thống hiện nhận hai dạng: ma trận rộng Iris (có dòng tiêu đề) "
            "hoặc dòng log 7 cột (thời điểm, mã Unit, mã JIG, tên thông số, "
            "giá trị, đơn vị, trạng thái)."
        )
    ket_qua_ghi = ghi_dong_log_jig(
        cac_dong_log, kho=kho, nguon="tep", ghi_luc=ghi_luc
    )
    luc = ghi_luc or datetime.now(VIETNAM_TZ)
    return NhapTepKetQua(
        ten_tep=duong.name,
        dinh_dang="dong_le",
        van_tay=tinh_van_tay_tep(duong),
        da_ghi=int(ket_qua_ghi.get("da_ghi", 0)),
        bo_qua_rong=int(ket_qua_ghi.get("bo_qua_rong", 0)),
        bi_cat=int(ket_qua_ghi.get("bi_cat", 0)),
        thoi_gian=luc.replace(microsecond=0).isoformat(),
    )


def thong_diep_nhap_tep(ket_qua: NhapTepKetQua) -> str:
    """Cau tieng Viet bao ket qua nhap tep de hien thang trong chat."""
    if ket_qua.bo_qua_vi_trung:
        return (
            "Tệp " + ket_qua.ten_tep + " đã nhập trước đó và nội dung không đổi, "
            "nên hệ thống bỏ qua để tránh ghi trùng."
        )
    ten_dinh_dang = (
        "ma trận rộng Iris" if ket_qua.dinh_dang == "iris_rong" else "dòng log riêng lẻ"
    )
    dong = [
        "Đã nhập " + format(ket_qua.da_ghi, ",d") + " giá trị đo từ tệp "
        + ket_qua.ten_tep + " (" + ten_dinh_dang + ") vào kho log.",
        "Bạn có thể nhắn tiếp: vẽ biểu đồ cho JIG vừa nhập, hoặc hỏi kho log có gì.",
    ]
    if ket_qua.bi_cat:
        dong.append(
            "Lưu ý: tệp quá lớn nên chỉ nhập "
            + format(ket_qua.da_ghi, ",d")
            + " dòng đầu, còn "
            + format(ket_qua.bi_cat, ",d")
            + " dòng chưa nhập. Vui lòng chia nhỏ tệp rồi nhập tiếp."
        )
    return "\n".join(dong)
