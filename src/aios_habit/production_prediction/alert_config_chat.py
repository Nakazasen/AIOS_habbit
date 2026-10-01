"""Text dashboard and natural-language alert config on Omnibar (US12 T062).

No settings page or modal is created. All configuration is visible as a
plain-text table inside the chat message and updated via natural chat.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

from aios_habit.production_prediction.chart_selection import (
    TEN_LOAI_BIEU_DO,
    goi_y_loai_bieu_do,
    liet_ke_loai_bieu_do,
)


@dataclass
class AlertConfig:
    nguoi_nhan: List[str] = field(default_factory=list)
    nguong_phan_tram: float = 80.0
    gian_cach_phut: int = 30
    gop_tin: bool = True
    theo_doi_ewma: bool = True
    # J1-CSV: loai bieu do tu dong dinh kem vao mail khi canh bao kich hoat.
    # Ma loai theo chart_selection.LOAI_BIEU_DO ("xu_huong" mac dinh).
    bieu_do_dinh_kem: List[str] = field(default_factory=lambda: ["xu_huong"])

    def to_dict(self) -> dict:
        return {
            "nguoi_nhan": list(self.nguoi_nhan),
            "nguong_phan_tram": self.nguong_phan_tram,
            "gian_cach_phut": self.gian_cach_phut,
            "gop_tin": self.gop_tin,
            "theo_doi_ewma": self.theo_doi_ewma,
            "bieu_do_dinh_kem": list(self.bieu_do_dinh_kem),
        }


def render_text_dashboard(config: AlertConfig) -> str:
    """Render the config as a plain-text table inside a chat message."""
    nhan = ", ".join(config.nguoi_nhan) if config.nguoi_nhan else "Chưa có người nhận"
    if config.bieu_do_dinh_kem:
        ten_bieu_do = ", ".join(
            TEN_LOAI_BIEU_DO.get(ma, ma) for ma in config.bieu_do_dinh_kem
        )
    else:
        ten_bieu_do = "Không đính kèm biểu đồ"
    return (
        "Bảng cấu hình cảnh báo\n"
        "------------------------\n"
        f"Người nhận: {nhan}\n"
        f"Điều kiện kích hoạt: khi chạm {config.nguong_phan_tram:g}% dung sai\n"
        f"Giãn cách chống spam: {config.gian_cach_phut} phút\n"
        f"Chế độ gộp tin: {'Bật' if config.gop_tin else 'Tắt'}\n"
        f"Theo dõi trôi dốc EWMA: {'Bật' if config.theo_doi_ewma else 'Tắt'}\n"
        f"Biểu đồ đính kèm mail: {ten_bieu_do}\n"
        "------------------------\n"
        "Bạn chỉ cần nhắn, ví dụ: thêm email to.truong@congty.local, "
        "đổi ngưỡng 90%, chọn biểu đồ gửi mail phân bố."
    )


_EMAIL_RE = re.compile(r"[\w.\-]+@[\w.\-]+\.\w+")
_PERCENT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
_MINUTES_RE = re.compile(r"(\d+)\s*phút")


def parse_config_command(text: str, config: AlertConfig) -> Tuple[AlertConfig, str]:
    """Update config from a natural Vietnamese chat command."""
    norm = (text or "").strip().lower()
    if not norm:
        return config, "Bạn nhắn thêm yêu cầu cấu hình, ví dụ: thêm email, đổi ngưỡng, đổi giãn cách."
    updated = AlertConfig(
        nguoi_nhan=list(config.nguoi_nhan),
        nguong_phan_tram=config.nguong_phan_tram,
        gian_cach_phut=config.gian_cach_phut,
        gop_tin=config.gop_tin,
        theo_doi_ewma=config.theo_doi_ewma,
        bieu_do_dinh_kem=list(config.bieu_do_dinh_kem),
    )
    if "thêm email" in norm or "them email" in norm:
        found = _EMAIL_RE.findall(text or "")
        if not found:
            return config, "Chưa thấy địa chỉ email hợp lệ trong tin nhắn."
        for email in found:
            if email not in updated.nguoi_nhan:
                updated.nguoi_nhan.append(email)
        return updated, f"Đã thêm {len(found)} địa chỉ email vào danh sách nhận cảnh báo."
    if "xóa email" in norm or "xoa email" in norm:
        found = _EMAIL_RE.findall(text or "")
        if not found:
            return config, "Bạn ghi rõ địa chỉ email cần xóa."
        updated.nguoi_nhan = [e for e in updated.nguoi_nhan if e not in found]
        return updated, f"Đã xóa {len(found)} địa chỉ email khỏi danh sách."
    if "ngưỡng" in norm or "nguong" in norm:
        match = _PERCENT_RE.search(norm.replace(",", "."))
        if not match:
            return config, "Bạn ghi ngưỡng theo dạng phần trăm, ví dụ: đổi ngưỡng 90%."
        percent = float(match.group(1).replace(",", "."))
        if not 1 <= percent <= 100:
            return config, "Ngưỡng phải trong khoảng 1% đến 100%."
        updated.nguong_phan_tram = percent
        return updated, f"Đã đổi ngưỡng kích hoạt thành {percent:g}% dung sai."
    if "giãn cách" in norm or "gian cach" in norm:
        match = _MINUTES_RE.search(norm)
        if not match:
            return config, "Bạn ghi thời gian giãn cách theo phút, ví dụ: đổi giãn cách 60 phút."
        minutes = int(match.group(1))
        if not 1 <= minutes <= 1440:
            return config, "Thời gian giãn cách phải từ 1 đến 1440 phút."
        updated.gian_cach_phut = minutes
        return updated, f"Đã đổi giãn cách chống spam thành {minutes} phút."
    if "gộp tin" in norm or "gop tin" in norm:
        if "tắt" in norm:
            updated.gop_tin = False
            return updated, "Đã tắt chế độ gộp tin."
        updated.gop_tin = True
        return updated, "Đã bật chế độ gộp tin."
    if "biểu đồ gửi mail" in norm or "bieu do gui mail" in norm:
        return _xu_ly_lenh_bieu_do_gui_mail(norm, config)
    return config, "Tôi chưa hiểu yêu cầu cấu hình. Bạn thử: thêm email, đổi ngưỡng 90%, đổi giãn cách 60 phút."


def _xu_ly_lenh_bieu_do_gui_mail(norm: str, config: AlertConfig) -> Tuple[AlertConfig, str]:
    """Chon/bo loai bieu do tu dong dinh kem vao mail khi canh bao (J1-CSV)."""
    ma_loai = goi_y_loai_bieu_do(norm)
    if ma_loai is None:
        return (
            config,
            "Chưa rõ loại biểu đồ. Vui lòng chọn một trong: "
            + liet_ke_loai_bieu_do()
            + ". Ví dụ: chọn biểu đồ gửi mail phân bố.",
        )
    ten_loai = TEN_LOAI_BIEU_DO.get(ma_loai, ma_loai)
    updated = AlertConfig(
        nguoi_nhan=list(config.nguoi_nhan),
        nguong_phan_tram=config.nguong_phan_tram,
        gian_cach_phut=config.gian_cach_phut,
        gop_tin=config.gop_tin,
        theo_doi_ewma=config.theo_doi_ewma,
        bieu_do_dinh_kem=list(config.bieu_do_dinh_kem),
    )
    la_bo = "bỏ biểu đồ" in norm or "bo bieu do" in norm
    if la_bo:
        if ma_loai in updated.bieu_do_dinh_kem:
            updated.bieu_do_dinh_kem = [m for m in updated.bieu_do_dinh_kem if m != ma_loai]
            return updated, "Đã bỏ biểu đồ " + ten_loai + " khỏi mail cảnh báo."
        return config, "Biểu đồ " + ten_loai + " vốn không có trong mail cảnh báo."
    if ma_loai in updated.bieu_do_dinh_kem:
        return config, "Biểu đồ " + ten_loai + " đã có trong mail cảnh báo rồi."
    updated.bieu_do_dinh_kem.append(ma_loai)
    return (
        updated,
        "Đã chọn biểu đồ " + ten_loai + " để tự động đính kèm vào mail "
        "mỗi khi cảnh báo kích hoạt.",
    )
