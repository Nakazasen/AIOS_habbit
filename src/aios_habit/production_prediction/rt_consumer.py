"""Prototype AI nhan realtime tu server JIG (J1-RT).

Lop ``RtConsumer`` poll endpoint ``GET /api/v1/jig/events`` theo cursor:
chi lay su kien moi hon cursor, khong bao gio tien cursor khi gap loi,
tu dong thu lai (retry) voi backoff mu. Loi tra ve bang tieng Viet.

Chi dung thu vien chuan (urllib), khong phu thuoc ben ngoai.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .jig_alert_cards import build_realtime_alert_card
from .stream_api import EVENTS_PATH


@dataclass
class RtConsumer:
    """AI consumer poll su kien realtime tu server JIG."""

    base_url: str
    auth_token: Optional[str] = None
    timeout_giay: float = 10.0
    so_lan_thu_toi_da: int = 3
    cursor: int = 0
    _so_lan_loi_lien_tiep: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def _tieu_de(self) -> Dict[str, str]:
        tieu_de = {"Accept": "application/json"}
        if self.auth_token:
            tieu_de["Authorization"] = "Bearer " + self.auth_token
        return tieu_de

    def _get_events(self, tu_cursor: int, gioi_han: int = 200) -> Tuple[List[Dict[str, Any]], int]:
        tham_so = urllib.parse.urlencode({"since": tu_cursor, "limit": gioi_han})
        url = self.base_url + EVENTS_PATH + "?" + tham_so
        yeu_cau = urllib.request.Request(url, headers=self._tieu_de(), method="GET")
        try:
            with urllib.request.urlopen(yeu_cau, timeout=self.timeout_giay) as tra_loi:
                than = json.loads(tra_loi.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise ValueError("Máy chủ từ chối: sai hoặc thiếu mã truy cập.") from None
            if exc.code == 404:
                raise ValueError("Máy chủ chưa có địa chỉ lấy sự kiện.") from None
            raise ValueError("Máy chủ báo lỗi HTTP %d." % exc.code) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ValueError("Không kết nối được tới máy chủ JIG.") from exc
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Máy chủ trả về dữ liệu không hợp lệ.") from exc
        if not isinstance(than, dict) or not isinstance(than.get("su_kien"), list):
            raise ValueError("Máy chủ trả về dữ liệu không hợp lệ.")
        return than["su_kien"], int(than.get("cursor_moi", tu_cursor))

    def lay_su_kien_moi(self, gioi_han: int = 200) -> Tuple[List[Dict[str, Any]], int]:
        """Lay su kien moi hon cursor hien tai, co retry. Khong doi cursor khi loi."""
        loi_cuoi: Optional[Exception] = None
        for lan in range(self.so_lan_thu_toi_da):
            try:
                su_kien, cursor_moi = self._get_events(self.cursor, gioi_han)
                self._so_lan_loi_lien_tiep = 0
                return su_kien, cursor_moi
            except Exception as exc:  # noqa: BLE001 - gom loi de retry
                loi_cuoi = exc
                self._so_lan_loi_lien_tiep += 1
                if lan < self.so_lan_thu_toi_da - 1:
                    time.sleep(min(0.5 * (2 ** lan), 5.0))
        raise ValueError(
            "Không lấy được sự kiện sau %d lần thử: %s" % (self.so_lan_thu_toi_da, loi_cuoi)
        ) from loi_cuoi

    def chay_mot_vong(
        self,
        xu_ly: Callable[[Dict[str, Any]], None],
        gioi_han: int = 200,
    ) -> int:
        """Mot vong poll: lay su kien -> goi xu_ly tung su kien -> tien cursor.

        Cursor chi tien khi lay thanh cong VA xu ly xong toan bo.
        Tra ve so su kien da xu ly.
        """
        su_kien, cursor_moi = self.lay_su_kien_moi(gioi_han)
        for mot in su_kien:
            xu_ly(mot)
        self.cursor = cursor_moi
        return len(su_kien)


def dinh_dang_canh_bao(su_kien: Dict[str, Any]) -> Dict[str, Any]:
    """Chuyen mot su kien server thanh the canh bao tieng Viet de hien len chat."""
    noi_dung = su_kien.get("noi_dung") or {}
    chi_tiet = str(noi_dung.get("chi_tiet") or "Có dấu hiệu trôi thông số, cần kiểm tra trước khi phát sinh NG.")
    gia_tri = noi_dung.get("gia_tri")
    if gia_tri is not None:
        don_vi = str(noi_dung.get("don_vi") or "")
        chi_tiet = ("%s (giá trị: %s %s)" % (chi_tiet, gia_tri, don_vi)).strip()
    nguon = str(noi_dung.get("nguon") or "")
    if nguon == "SIMULATED_REALTIME":
        chi_tiet += " [Dữ liệu phát lại mô phỏng]"
    return build_realtime_alert_card(
        jig_id=str(su_kien.get("jig_id") or "—"),
        metric=str(su_kien.get("metric") or "—"),
        chi_tiet=chi_tiet,
        muc_do="Cần kiểm tra",
    )
