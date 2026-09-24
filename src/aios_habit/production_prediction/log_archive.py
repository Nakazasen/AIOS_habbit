"""Kho lưu dòng log JIG để AI phân tích lại (016 — yêu cầu "cho từng dòng log vào file").

Mỗi dòng log người dùng dán vào chat, hoặc mỗi giá trị tách ra từ tệp log họ tải
lên, được ghi thêm (append-only) thành **một dòng JSON** trong kho cục bộ:

``local_cases/jig_log_archive/YYYY-MM.jsonl``

Nhờ vậy câu hỏi kiểu "hôm nay JIG nào bất thường" có dữ liệu thật để phân tích
thay vì chỉ nằm trong tin nhắn chat. Kho nằm ngoài Git, chỉ đọc/ghi cục bộ, không
gọi mạng.

Định dạng một dòng (JSON object):
``{"ts": <ISO thời điểm đo>, "ghi_luc": <ISO lúc ghi>, "nguon": "dan_tay|tep",
"tep": "<tên tệp>", "unit_serial": ..., "jig_id": ..., "metric_name": ...,
"value": ..., "unit": ..., "target_label": ...}``
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

VIETNAM_TZ = timezone(timedelta(hours=7))

MAC_DINH_KHO_PATH = Path("local_cases") / "jig_log_archive"

# Giới hạn chống phình kho khi người dùng tải tệp lớn: mỗi lần nạp tối đa 50.000 dòng.
GIOI_HAN_DONG_MOI_LAN = 50_000


@dataclass
class DongKhoLog:
    """Một dòng đã lưu trong kho."""

    ts: Optional[str]
    ghi_luc: str
    nguon: str
    tep: str
    unit_serial: str
    jig_id: str
    metric_name: str
    value: Optional[float]
    unit: str
    target_label: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.ts,
            "ghi_luc": self.ghi_luc,
            "nguon": self.nguon,
            "tep": self.tep,
            "unit_serial": self.unit_serial,
            "jig_id": self.jig_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "target_label": self.target_label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DongKhoLog":
        return cls(
            ts=data.get("ts"),
            ghi_luc=str(data.get("ghi_luc", "")),
            nguon=str(data.get("nguon", "")),
            tep=str(data.get("tep", "")),
            unit_serial=str(data.get("unit_serial", "")),
            jig_id=str(data.get("jig_id", "")),
            metric_name=str(data.get("metric_name", "")),
            value=data.get("value"),
            unit=str(data.get("unit", "")),
            target_label=str(data.get("target_label", "")),
        )


def _duong_dan_thang(thang: datetime, kho: Path) -> Path:
    return Path(kho) / f"{thang.strftime('%Y-%m')}.jsonl"


def _ten_an_toan(duong_dan: str) -> str:
    """Chỉ giữ **tên tệp**, không bao giờ ghi đường dẫn tuyệt đối vào kho.

    Kho log là tệp cục bộ nhưng vẫn có thể bị sao chép/chia sẻ; đường dẫn tuyệt
    đối tới thư mục dữ liệu nhà máy không được nằm trong đó.
    """
    if not duong_dan:
        return ""
    try:
        return Path(str(duong_dan)).name
    except (OSError, ValueError):
        return str(duong_dan)


def ghi_ban_ghi(
    cac_ban_ghi: Iterable[Any],
    *,
    nguon: str,
    tep: str = "",
    kho: str | Path = MAC_DINH_KHO_PATH,
    ghi_luc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Ghi thêm các bản ghi log vào kho.

    Trả về ``{"da_ghi": n, "bo_qua_rong": n, "bi_cat": n}``. ``bi_cat`` > 0 nghĩa
    là đã chạm giới hạn ``GIOI_HAN_DONG_MOI_LAN`` và phần còn lại **không** được
    ghi; lớp gọi phải nói rõ cho người dùng thay vì im lặng cắt dữ liệu.
    """
    cac_dong: List[DongKhoLog] = []
    bo_qua_rong = 0
    bi_cat = 0
    luc = (ghi_luc or datetime.now(VIETNAM_TZ)).replace(microsecond=0)
    moc = luc.isoformat()
    for ban_ghi in cac_ban_ghi:
        gia_tri = getattr(ban_ghi, "value", None)
        if gia_tri is None:
            bo_qua_rong += 1
            continue
        if len(cac_dong) >= GIOI_HAN_DONG_MOI_LAN:
            bi_cat += 1
            continue
        su_kien = getattr(ban_ghi, "event_time", None)
        cac_dong.append(
            DongKhoLog(
                ts=su_kien.isoformat() if su_kien is not None else None,
                ghi_luc=moc,
                nguon=nguon,
                tep=_ten_an_toan(tep) or _ten_an_toan(str(getattr(ban_ghi, "jig_id", "") or "")),
                unit_serial=str(getattr(ban_ghi, "unit_serial", "") or ""),
                jig_id=_ten_an_toan(str(getattr(ban_ghi, "jig_id", "") or "")),
                metric_name=str(getattr(ban_ghi, "metric_name", "") or ""),
                value=float(gia_tri),
                unit=str(getattr(ban_ghi, "unit", "") or ""),
                target_label=str(getattr(ban_ghi, "target_label", "") or ""),
            )
        )
    da_ghi = _ghi_dong(cac_dong, Path(kho), luc)
    return {"da_ghi": da_ghi, "bo_qua_rong": bo_qua_rong, "bi_cat": bi_cat}


def _ghi_dong(cac_dong: List[DongKhoLog], kho: Path, luc: datetime) -> int:
    """Ghi danh sách dòng đã chuẩn hoá xuống tệp JSONL theo tháng."""
    if not cac_dong:
        return 0
    duong_dan = _duong_dan_thang(luc, kho)
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    with duong_dan.open("a", encoding="utf-8") as f:
        for dong in cac_dong:
            f.write(json.dumps(dong.to_dict(), ensure_ascii=False) + "\n")
    return len(cac_dong)


def doc_kho(
    kho: str | Path = MAC_DINH_KHO_PATH,
    *,
    thang: Optional[datetime] = None,
) -> List[DongKhoLog]:
    """Đọc kho log; mặc định đọc mọi tháng, có thể giới hạn một tháng."""
    goc = Path(kho)
    if not goc.exists():
        return []
    if thang is not None:
        cac_tep = [_duong_dan_thang(thang, goc)]
    else:
        cac_tep = sorted(goc.glob("*.jsonl"))
    ket_qua: List[DongKhoLog] = []
    for tep in cac_tep:
        if not tep.exists():
            continue
        try:
            with tep.open("r", encoding="utf-8") as f:
                for dong in f:
                    dong = dong.strip()
                    if not dong:
                        continue
                    try:
                        du_lieu = json.loads(dong)
                    except ValueError:
                        continue
                    if isinstance(du_lieu, dict):
                        ket_qua.append(DongKhoLog.from_dict(du_lieu))
        except OSError:
            continue
    return ket_qua


def lich_su_theo_jig(
    kho: str | Path = MAC_DINH_KHO_PATH,
    *,
    jig_id: str = "",
    metric_name: str = "",
    limit: int = 200,
) -> List[float]:
    """Lấy chuỗi giá trị gần nhất theo JIG và chỉ số, để đối chiếu xu hướng."""
    cac_dong = [d for d in doc_kho(kho) if d.value is not None]
    if jig_id:
        cac_dong = [d for d in cac_dong if d.jig_id == jig_id]
    if metric_name:
        cac_dong = [d for d in cac_dong if d.metric_name == metric_name]
    cac_dong.sort(key=lambda d: (d.ts or "", d.ghi_luc))
    return [float(d.value) for d in cac_dong[-limit:]]  # type: ignore[arg-type]


def tom_tat_kho(kho: str | Path = MAC_DINH_KHO_PATH) -> Dict[str, Any]:
    """Tóm tắt kho để hiển thị trong chat bằng tiếng Việt."""
    cac_dong = doc_kho(kho)
    if not cac_dong:
        return {"so_dong": 0, "jig": [], "chi_so": [], "don_vi": [], "moi_nhat": ""}
    jig = sorted({d.jig_id for d in cac_dong if d.jig_id})
    chi_so = sorted({d.metric_name for d in cac_dong if d.metric_name})
    don_vi = sorted({d.unit_serial for d in cac_dong if d.unit_serial})
    moc = sorted(d.ghi_luc for d in cac_dong if d.ghi_luc)
    return {
        "so_dong": len(cac_dong),
        "jig": jig,
        "chi_so": chi_so,
        "don_vi": don_vi,
        "moi_nhat": moc[-1] if moc else "",
    }


def bang_tom_tat_kho_van_ban(kho: str | Path = MAC_DINH_KHO_PATH) -> str:
    """Bảng tóm tắt kho log dạng văn bản để hiện thẳng trong chat."""
    tom_tat = tom_tat_kho(kho)
    if not tom_tat["so_dong"]:
        return (
            "Kho log JIG đang trống. Hãy dán một dòng log hoặc tải tệp log ở Thẻ 1, "
            "hệ thống sẽ tự lưu lại để phân tích."
        )
    dong = [
        "Kho log JIG đã lưu",
        "------------------------",
        f"Số dòng: {tom_tat['so_dong']:,}",
        f"Lần ghi mới nhất: {tom_tat['moi_nhat'] or '—'}",
        f"Mã JIG ({len(tom_tat['jig'])}): {', '.join(tom_tat['jig'][:6]) or '—'}",
        f"Số Unit: {len(tom_tat['don_vi']):,}",
        f"Chỉ số ({len(tom_tat['chi_so'])}): {', '.join(tom_tat['chi_so'][:6]) or '—'}",
        "------------------------",
        "Bạn có thể hỏi tiếp: kho log có gì, hoặc dán thêm dòng log để phân tích.",
    ]
    return "\n".join(dong)


def ghi_dong_log_jig(
    cac_dong_log: Iterable[Any],
    *,
    kho: str | Path = MAC_DINH_KHO_PATH,
    ghi_luc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Ghi các dòng log dán tay (``jig_log_ingest.JigLogLine``) vào kho.

    Tách riêng khỏi ``ghi_ban_ghi`` vì dòng dán tay không có thuộc tính
    ``event_time`` dạng ``datetime`` mà là ``timestamp`` dạng chuỗi ISO.
    """
    cac_dong: List[DongKhoLog] = []
    bo_qua_rong = 0
    bi_cat = 0
    luc = (ghi_luc or datetime.now(VIETNAM_TZ)).replace(microsecond=0)
    moc = luc.isoformat()
    for dong in cac_dong_log:
        gia_tri = getattr(dong, "value", None)
        if gia_tri is None:
            bo_qua_rong += 1
            continue
        if len(cac_dong) >= GIOI_HAN_DONG_MOI_LAN:
            bi_cat += 1
            continue
        ts = getattr(dong, "timestamp", None)
        # ``jig_id`` của dòng dán tay có thể chứa đường dẫn người dùng dán vào;
        # chỉ giữ tên, không bao giờ ghi đường dẫn dữ liệu nhà máy vào kho.
        jig_id = _ten_an_toan(str(getattr(dong, "jig_id", "") or ""))
        cac_dong.append(
            DongKhoLog(
                ts=str(ts) if ts else None,
                ghi_luc=moc,
                nguon="dan_tay",
                tep=jig_id,
                unit_serial=str(getattr(dong, "unit_serial", "") or ""),
                jig_id=jig_id,
                metric_name=str(getattr(dong, "metric", "") or ""),
                value=float(gia_tri),
                unit=str(getattr(dong, "unit", "") or ""),
                target_label=str(getattr(dong, "status", "") or ""),
            )
        )
    da_ghi = _ghi_dong(cac_dong, Path(kho), luc)
    return {"da_ghi": da_ghi, "bo_qua_rong": bo_qua_rong, "bi_cat": bi_cat}


def la_lenh_kho_log(text: str) -> bool:
    """True khi câu chat hỏi về kho log đã lưu."""
    cau = (text or "").strip().lower()
    if not cau:
        return False
    return "kho log" in cau or "log da luu" in cau or "lịch sử log" in cau or "lich su log" in cau
