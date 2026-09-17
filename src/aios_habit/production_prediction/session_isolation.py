"""Zero-UI session isolation for US12 (Moc 6 T065).

Personal/office chat space is inviolable: machine alerts never interrupt it.
Realtime JIG alerts only appear in the dedicated watchdog session or via
independent email to the responsible owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


WATCHDOG_HINTS = ("truc ban", "trực ban", "watchdog", "jig", "cong doan", "công đoạn", "nha may", "nhà máy")
PERSONAL_HINTS = ("ca nhan", "cá nhân", "van phong", "văn phòng")


@dataclass
class SessionPersona:
    ten_phien: str = ""
    che_do: str = "ca_nhan"  # "ca_nhan" or "truc_ban"

    def to_dict(self) -> Dict[str, str]:
        return {"ten_phien": self.ten_phien, "che_do": self.che_do}


def classify_session(ten_phien: str = "", che_do: Optional[str] = None) -> str:
    """Classify a chat session as personal (quiet) or watchdog (alerts allowed)."""
    if che_do in ("ca_nhan", "truc_ban"):
        return che_do
    norm = (ten_phien or "").strip().lower()
    if any(h in norm for h in WATCHDOG_HINTS) and not any(h in norm for h in PERSONAL_HINTS):
        return "truc_ban"
    return "ca_nhan"


def should_deliver_machine_alert(loai_phien: str) -> bool:
    """Machine alerts are only delivered in the watchdog session."""
    return loai_phien == "truc_ban"


def parse_persona_command(text: str, current: SessionPersona) -> tuple[SessionPersona, str]:
    """One-touch persona setup via a natural Omnibar sentence."""
    norm = (text or "").strip().lower()
    if "bật trực ban" in norm or "bat truc ban" in norm:
        return SessionPersona(ten_phien=current.ten_phien, che_do="truc_ban"), \
            "Đã bật chế độ trực ban công đoạn. Cảnh báo JIG sẽ hiện ở phiên này."
    if "tắt trực ban" in norm or "tat truc ban" in norm or "chế độ cá nhân" in norm or "che do ca nhan" in norm:
        return SessionPersona(ten_phien=current.ten_phien, che_do="ca_nhan"), \
            "Đã về chế độ cá nhân yên tĩnh. Cảnh báo máy sẽ không chen vào cuộc trò chuyện này."
    return current, "Bạn nhắn “bật trực ban” để nhận cảnh báo JIG, hoặc “chế độ cá nhân” để giữ yên tĩnh."


def filter_alert_for_session(alert: Dict[str, object], loai_phien: str) -> Optional[Dict[str, object]]:
    """Return the alert only when the session is allowed to see it."""
    if should_deliver_machine_alert(loai_phien):
        return alert
    return None
