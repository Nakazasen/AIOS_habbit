"""Vietnamese alert cards and live status capsule for US12 (T059, T064).

Pure data builders (no Streamlit dependency) so contract tests stay fast.
Thin Streamlit wrappers live in workspace_chat_ui.py.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_instant_log_card(
    dong_log: Dict[str, Any],
    ket_qua_ewma: Dict[str, Any],
    nguong_tham_khao: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the instant log inspection card shown directly on chat."""
    return {
        "loai_the": "kiem_tra_log_tuc_thi",
        "ma_unit": dong_log.get("unit_serial", "—"),
        "ma_jig": dong_log.get("jig_id", "—"),
        "thong_so": dong_log.get("metric", "—"),
        "gia_tri": dong_log.get("value", "—"),
        "don_vi": dong_log.get("unit", ""),
        "trang_thai": ket_qua_ewma.get("trang_thai", "Cận biên"),
        "chi_tiet": ket_qua_ewma.get("chi_tiet", ""),
        "nguong_tham_khao": nguong_tham_khao or "Đối chiếu dải dung sai tiêu chuẩn [USL, LSL].",
        "goi_y": ["Gửi email cảnh báo", "Lưu vào chuỗi theo dõi"],
    }


def build_realtime_alert_card(
    jig_id: str,
    metric: str,
    chi_tiet: str,
    muc_do: str = "Cần kiểm tra",
) -> Dict[str, Any]:
    """Build the prominent realtime alert card for event-driven alerts."""
    return {
        "loai_the": "canh_bao_realtime",
        "ma_jig": jig_id,
        "thong_so": metric,
        "muc_do": muc_do,
        "chi_tiet": chi_tiet,
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
