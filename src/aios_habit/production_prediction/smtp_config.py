"""Cấu hình máy chủ gửi mail nội bộ, lưu ngoài Git (T016-10).

Mật khẩu chỉ nằm trong tệp runtime dưới local_cases. Bản to_dict() không trả mật khẩu.
Module này không nhập Streamlit và không tự gửi mail khi chưa có người duyệt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from aios_habit.production_prediction.alert_mailer import send_via_smtp

MAC_DINH_SMTP_PATH = Path("local_cases") / "smtp_config.json"

_LOI_CHUA_CAU_HINH_SMTP = (
    "Chưa cấu hình máy chủ gửi mail nội bộ. "
    "Vui lòng bổ sung máy chủ, cổng và tài khoản gửi mail trước khi gửi cảnh báo."
)
_LOI_GUI_CHUNG = (
    "Chưa gửi được email cảnh báo. "
    "Hãy kiểm tra mạng nội bộ, tài khoản gửi mail và danh sách người nhận, rồi thử gửi lại."
)


@dataclass
class SmtpConfig:
    host: str = ""
    port: int = 587
    ten_dang_nhap: str = ""
    mat_khau: str = ""
    dung_tls: bool = True
    nguoi_gui: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Bản công khai để hiển thị. Không kèm mật khẩu."""
        return {
            "host": self.host,
            "port": self.port,
            "ten_dang_nhap": self.ten_dang_nhap,
            "dung_tls": self.dung_tls,
            "nguoi_gui": self.nguoi_gui,
        }

    @classmethod
    def from_dict(cls, data: Optional[Mapping[str, Any]] = None) -> SmtpConfig:
        """Đọc cấu hình. Chấp nhận cả khóa mat_khau và password."""
        if not isinstance(data, Mapping):
            return cls()
        return cls(
            host=str(data.get("host") or "").strip(),
            port=_doc_cong(data.get("port", 587)),
            ten_dang_nhap=str(data.get("ten_dang_nhap") or "").strip(),
            mat_khau=_doc_mat_khau(data),
            dung_tls=_doc_bool(data.get("dung_tls", True)),
            nguoi_gui=str(data.get("nguoi_gui") or "").strip(),
        )


def _doc_cong(value: Any, mac_dinh: int = 587) -> int:
    if value is None or value == "":
        return mac_dinh
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _doc_bool(value: Any, mac_dinh: bool = True) -> bool:
    if value is None:
        return mac_dinh
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    chuoi = str(value).strip().lower()
    if chuoi in {"1", "true", "yes", "co", "có", "bat", "bật", "on"}:
        return True
    if chuoi in {"0", "false", "no", "khong", "không", "tat", "tắt", "off"}:
        return False
    return mac_dinh


def _doc_mat_khau(data: Mapping[str, Any]) -> str:
    if "mat_khau" in data:
        return str(data.get("mat_khau") or "")
    if "password" in data:
        return str(data.get("password") or "")
    return ""


def doc_smtp_config(path: Path | str = MAC_DINH_SMTP_PATH) -> SmtpConfig:
    """Đọc tệp cấu hình. Thiếu tệp hoặc tệp hỏng thì trả mặc định, không ném lỗi."""
    try:
        duong = MAC_DINH_SMTP_PATH if path is None else Path(path)
        data = json.loads(duong.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError, TypeError):
        return SmtpConfig()
    if not isinstance(data, dict):
        return SmtpConfig()
    try:
        return SmtpConfig.from_dict(data)
    except (TypeError, ValueError):
        return SmtpConfig()


def luu_smtp_config(config: SmtpConfig, path: Path | str = MAC_DINH_SMTP_PATH) -> None:
    """Ghi cấu hình UTF-8, kể cả mật khẩu, vào tệp runtime ngoài Git."""
    duong = MAC_DINH_SMTP_PATH if path is None else Path(path)
    duong.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "host": config.host,
        "port": int(config.port),
        "ten_dang_nhap": config.ten_dang_nhap,
        "mat_khau": config.mat_khau,
        "dung_tls": bool(config.dung_tls),
        "nguoi_gui": config.nguoi_gui,
    }
    duong.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def co_cau_hinh(config: SmtpConfig) -> bool:
    """Chỉ đúng khi đã có máy chủ và cổng lớn hơn 0."""
    if config is None:
        return False
    try:
        host = str(getattr(config, "host", "") or "").strip()
        port = int(getattr(config, "port", 0))
    except (TypeError, ValueError):
        return False
    return bool(host) and port > 0


def gui_voi_cau_hinh(msg: MIMEMultipart, config: SmtpConfig) -> Dict[str, object]:
    """Gửi qua SMTP đã cấu hình. Thiếu cấu hình thì dừng, không mở kết nối."""
    if not co_cau_hinh(config):
        raise ValueError(_LOI_CHUA_CAU_HINH_SMTP)
    return send_via_smtp(
        msg,
        host=config.host.strip(),
        port=int(config.port),
        ten_dang_nhap=config.ten_dang_nhap,
        mat_khau=config.mat_khau,
        dung_tls=bool(config.dung_tls),
    )


def thong_bao_loi_gui(exc: Exception) -> str:
    """Câu tiếng Việt kèm bước xử lý. Không trả nguyên văn lỗi gốc hay mật khẩu."""
    try:
        if isinstance(exc, ValueError) and str(exc) == _LOI_CHUA_CAU_HINH_SMTP:
            return _LOI_CHUA_CAU_HINH_SMTP
    except Exception:
        pass
    return _LOI_GUI_CHUNG
