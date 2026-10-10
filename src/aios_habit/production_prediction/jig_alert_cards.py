"""Vietnamese alert cards and live status capsule for US12 (T059, T064).

Pure data builders (no Streamlit dependency) so contract tests stay fast.
Thin Streamlit wrappers live in workspace_chat_ui.py.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

SO_DIEM_WARMUP_MAC_DINH: int = 20


def tao_nhan_warmup(so_diem: int, nguong: int = SO_DIEM_WARMUP_MAC_DINH) -> str:
    """Tạo nhãn giải thích khi chuỗi dữ liệu đang trong giai đoạn tích lũy nền."""
    return f"Đang tích lũy dữ liệu nền ({so_diem}/{nguong} điểm) — chưa đủ cơ sở kết luận xu hướng."


def trich_so_diem_nen(
    so_diem: Optional[int] = None,
    ket_qua_ewma: Optional[Dict[str, Any]] = None,
    dong_log: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """Trích xuất số điểm chuỗi dữ liệu từ các nguồn truyền vào."""
    if so_diem is not None:
        try:
            return int(so_diem)
        except (ValueError, TypeError):
            pass
    if ket_qua_ewma:
        for key in ("so_diem", "n", "so_diem_nen", "so_diem_chuoi"):
            if ket_qua_ewma.get(key) is not None:
                try:
                    return int(ket_qua_ewma[key])
                except (ValueError, TypeError):
                    pass
        for text_key in ("xu_huong_sma", "chi_tiet"):
            val = str(ket_qua_ewma.get(text_key, "") or "")
            m = re.search(r"mới có (\d+) điểm", val)
            if m:
                return int(m.group(1))
    if dong_log:
        for key in ("so_diem", "n"):
            if dong_log.get(key) is not None:
                try:
                    return int(dong_log[key])
                except (ValueError, TypeError):
                    pass
    return None


def build_instant_log_card(
    dong_log: Dict[str, Any],
    ket_qua_ewma: Dict[str, Any],
    nguong_tham_khao: Optional[str] = None,
    so_diem: Optional[int] = None,
) -> Dict[str, Any]:
    """Build the instant log inspection card shown directly on chat.

    The reference line reports the real per-metric limits when the verdict was
    decided by them, instead of the generic "[USL, LSL]" sentence.
    """
    if nguong_tham_khao is None and ket_qua_ewma.get("nguon_nguong") is not None:
        nguon = str(ket_qua_ewma.get("nguon_nguong") or "").strip()
        nguong_tham_khao = (
            f"Đối chiếu giới hạn thật khai báo trong tệp của JIG ({nguon})."
            if nguon
            else "Đối chiếu giới hạn thật khai báo trong tệp của JIG."
        )
    n = trich_so_diem_nen(so_diem, ket_qua_ewma, dong_log)
    nhan_warmup = (
        tao_nhan_warmup(n, SO_DIEM_WARMUP_MAC_DINH)
        if (n is not None and n < SO_DIEM_WARMUP_MAC_DINH)
        else None
    )
    return {
        "loai_the": "kiem_tra_log_tuc_thi",
        "ma_unit": dong_log.get("unit_serial", "—"),
        "ma_jig": dong_log.get("jig_id", "—"),
        "thong_so": dong_log.get("metric", "—"),
        "gia_tri": dong_log.get("value", "—"),
        "don_vi": dong_log.get("unit", ""),
        "trang_thai": ket_qua_ewma.get("trang_thai", "Cận biên"),
        "chi_tiet": ket_qua_ewma.get("chi_tiet", ""),
        "xu_huong_sma": ket_qua_ewma.get("xu_huong_sma", ""),
        "nhan_warmup": nhan_warmup,
        "so_diem": n,
        "phan_doan_nguyen_nhan": ket_qua_ewma.get("phan_doan_nguyen_nhan", ""),
        "de_xuat_dieu_tra": ket_qua_ewma.get("de_xuat_dieu_tra", []),
        "nguong_tham_khao": nguong_tham_khao or "Đối chiếu dải dung sai tiêu chuẩn [USL, LSL].",
        "goi_y": ["Gửi email cảnh báo", "Lưu vào chuỗi theo dõi"],
    }


def build_realtime_alert_card(
    jig_id: str,
    metric: str,
    chi_tiet: str,
    muc_do: str = "Cần kiểm tra",
    gia_tri: Optional[float] = None,
    don_vi: str = "",
    sma: Optional[float] = None,
    muc_lech: Optional[str | float] = None,
    so_diem_lien_tiep: Optional[int] = None,
    thoi_diem: Optional[str] = None,
    alert_id: Optional[str] = None,
    residual: Optional[float] = None,
    sigma: Optional[float] = None,
    deviation_pct: Optional[float] = None,
    deviation_sigma: Optional[float] = None,
    timestamp: Optional[str] = None,
    nguon: str = "",
) -> Dict[str, Any]:
    """Build the prominent realtime alert card for event-driven alerts."""
    jid = str(jig_id or "—")
    met = str(metric or "—")
    eff_time = str(thoi_diem or timestamp or "")
    eff_alert_id = alert_id or f"ALT-{jid}-{met}".replace(" ", "_")
    return {
        "loai_the": "canh_bao_realtime",
        "alert_id": eff_alert_id,
        "jig_id": jid,
        "ma_jig": jid,
        "metric": met,
        "thong_so": met,
        "muc_do": muc_do,
        "chi_tiet": chi_tiet,
        "gia_tri": gia_tri,
        "don_vi": don_vi,
        "sma": sma,
        "sma20": sma,
        "residual": residual,
        "sigma": sigma,
        "muc_lech": str(muc_lech) if muc_lech is not None else "",
        "deviation_pct": deviation_pct,
        "deviation_sigma": deviation_sigma,
        "so_diem_lien_tiep": so_diem_lien_tiep,
        "thoi_diem": eff_time,
        "timestamp": eff_time,
        "nguon": nguon,
        "huong_dan": "Mở phiên trực ban công đoạn để xem biểu đồ và duyệt email cảnh báo.",
    }


def build_live_status_capsule(
    dang_ket_noi: bool,
    toc_do_dong_phut: float = 0.0,
    so_jig: int = 0,
) -> Dict[str, Any]:
    """Build the header live status capsule (no chat spam)."""
    if dang_ket_noi:
        return {
            "trang_thai": "Đang nghe luồng JIG",
            "chi_tiet": f"{toc_do_dong_phut:g} dòng/phút, {so_jig} JIG đang theo dõi.",
        }
    return {
        "trang_thai": "Chưa kết nối luồng",
        "chi_tiet": "Dán dòng log thủ công hoặc kiểm tra cổng nhận log nội bộ.",
    }


def build_watch_list_entry(unit_serial: str, ly_do: str) -> Dict[str, str]:
    return {"ma_unit": unit_serial, "ly_do": ly_do, "trang_thai": "Đang theo dõi"}


def summarize_watch_list(entries: List[Dict[str, str]]) -> str:
    if not entries:
        return "Chưa có Unit nào trong chuỗi theo dõi."
    lines = [f"- {e.get('ma_unit', '—')}: {e.get('ly_do', '')}" for e in entries]
    return "Chuỗi theo dõi\n" + "\n".join(lines)
