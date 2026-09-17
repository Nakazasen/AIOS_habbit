"""Alert email composer with Monozukuri chart attachment (US12 T061).

Uses only smtplib and email.mime from the standard library.
Sending always requires an explicit user-approved proposal card
(human-in-the-loop); this module never sends silently.
"""

from __future__ import annotations

import re
import smtplib
from dataclasses import dataclass, field
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from time import time
from typing import Dict, List, Optional


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class AlertMailProposal:
    tieu_de: str
    tom_tat: str
    nguoi_nhan: List[str]
    ten_anh: str = "bieu_do_xu_huong.png"
    ma_duyet: str = ""


def kiem_tra_email(email: str) -> bool:
    return bool(_EMAIL_RE.match((email or "").strip()))


def build_alert_email(
    proposal: AlertMailProposal,
    noi_dung_html: Optional[str] = None,
    anh_png_bytes: Optional[bytes] = None,
    bao_cao_markdown: Optional[str] = None,
) -> MIMEMultipart:
    """Build a Vietnamese HTML alert email with inline chart image."""
    if not proposal.nguoi_nhan or not all(kiem_tra_email(e) for e in proposal.nguoi_nhan):
        raise ValueError("Danh sách người nhận email chưa hợp lệ.")
    if not proposal.tieu_de.strip() or not proposal.tom_tat.strip():
        raise ValueError("Thiếu tiêu đề hoặc tóm tắt cảnh báo.")
    msg = MIMEMultipart("related")
    msg["Subject"] = proposal.tieu_de
    msg["To"] = ", ".join(proposal.nguoi_nhan)
    body = noi_dung_html or (
        "<html><body>"
        "<h2>Cảnh báo xu hướng JIG</h2>"
        f"<p>{proposal.tom_tat}</p>"
        "<p>Đề xuất kiểm tra: đối chiếu lot linh kiện, Unit và lần đo gần nhất; "
        "giữ nguyên thông số máy cho đến khi tổ trưởng xác nhận.</p>"
        '<img src="cid:bieudoxu_huong" alt="Biểu đồ xu hướng" />'
        "</body></html>"
    )
    if "cid:bieudoxu_huong" not in body and anh_png_bytes:
        body = body.replace("</body>", '<img src="cid:bieudoxu_huong" alt="Biểu đồ xu hướng" /></body>')
    msg.attach(MIMEText(body, "html", "utf-8"))
    if anh_png_bytes:
        image = MIMEImage(anh_png_bytes, _subtype="png", name=proposal.ten_anh)
        image.add_header("Content-ID", "<bieudoxu_huong>")
        image.add_header("Content-Disposition", "inline", filename=proposal.ten_anh)
        msg.attach(image)
    if bao_cao_markdown:
        attachment = MIMEText(bao_cao_markdown, "plain", "utf-8")
        attachment.add_header("Content-Disposition", "attachment", filename="bao_cao_chi_tiet.md")
        msg.attach(attachment)
    return msg


def build_proposal_card(
    tieu_de: str,
    tom_tat: str,
    nguoi_nhan: List[str],
    ma_duyet: str,
) -> Dict[str, object]:
    """Build the preview card shown on chat before sending."""
    return {
        "loai_the": "de_xuat_email",
        "tieu_de": tieu_de,
        "tom_tat": tom_tat,
        "nguoi_nhan": list(nguoi_nhan),
        "ma_duyet": ma_duyet,
        "huong_dan": "Xem trước nội dung rồi bấm Gửi khi đồng ý, hoặc bấm Hủy.",
    }


def should_send(now_ts: float, last_sent_ts: Optional[float], cooldown_seconds: int) -> bool:
    """Apply cooldown anti-spam before sending another alert."""
    if cooldown_seconds <= 0:
        return True
    if last_sent_ts is None:
        return True
    return (now_ts - last_sent_ts) >= cooldown_seconds


def send_via_smtp(
    msg: MIMEMultipart,
    host: str,
    port: int,
    ten_dang_nhap: str,
    mat_khau: str,
    dung_tls: bool = True,
) -> Dict[str, object]:
    """Send via SMTP with fail-closed Vietnamese errors."""
    if not host.strip() or port <= 0:
        raise ValueError("Thiếu địa chỉ máy chủ gửi mail.")
    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            if dung_tls:
                server.starttls()
            if ten_dang_nhap:
                server.login(ten_dang_nhap, mat_khau)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise RuntimeError(
            "Chưa gửi được email cảnh báo. Kiểm tra mạng nội bộ và tài khoản gửi mail rồi thử lại."
        ) from exc
    return {"trang_thai": "Đã gửi", "thoi_diem": int(time())}


@dataclass
class AlertCooldownTracker:
    cooldown_seconds: int = 1800
    last_sent: Dict[str, float] = field(default_factory=dict)

    def duoc_phep_gui(self, khoa: str, now_ts: Optional[float] = None) -> bool:
        now = now_ts if now_ts is not None else time()
        return should_send(now, self.last_sent.get(khoa), self.cooldown_seconds)

    def danh_dau_da_gui(self, khoa: str, now_ts: Optional[float] = None) -> None:
        self.last_sent[khoa] = now_ts if now_ts is not None else time()
