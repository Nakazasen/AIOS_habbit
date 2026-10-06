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
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .jig_alert_cards import build_realtime_alert_card
from .stream_api import EVENTS_PATH
from .trend_alerts import danh_gia_xu_huong_sma, gate_canh_bao_theo_xu_huong


@dataclass
class RtConsumer:
    """AI consumer poll su kien realtime tu server JIG."""

    base_url: str
    auth_token: Optional[str] = None
    timeout_giay: float = 10.0
    so_lan_thu_toi_da: int = 3
    cursor: int = 0
    # Duong dan file luu cursor (tuy chon). Neu dat, consumer tu tai cursor
    # khi khoi tao va tu luu sau moi vong poll thanh cong -> restart van
    # resume dung cho (dac ta J1-RT muc 2). Ghi kieu atomic (file tam + doi ten).
    duong_dan_cursor: Optional[str | Path] = None
    _so_lan_loi_lien_tiep: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if self.duong_dan_cursor:
            self._tai_cursor_tu_dia()

    def _tai_cursor_tu_dia(self) -> None:
        """Khoi phuc cursor tu file da luu; giu cursor hien tai neu file loi."""
        try:
            duong_dan = Path(self.duong_dan_cursor) if self.duong_dan_cursor else None
            if duong_dan is not None and duong_dan.is_file():
                self.cursor = max(0, int(duong_dan.read_text(encoding="utf-8").strip() or 0))
        except (OSError, ValueError):
            pass

    def _luu_cursor_xuong_dia(self) -> None:
        if not self.duong_dan_cursor:
            return
        duong_dan = Path(self.duong_dan_cursor)
        duong_dan.parent.mkdir(parents=True, exist_ok=True)
        tam = duong_dan.with_name(duong_dan.name + ".tmp")
        tam.write_text(str(int(self.cursor)), encoding="utf-8")
        tam.replace(duong_dan)

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
        self._luu_cursor_xuong_dia()
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


def trich_gia_tri_su_kien(su_kien: Dict[str, Any]) -> Optional[float]:
    """Trich gia tri so tu mot su kien server (None neu khong co)."""
    noi_dung = su_kien.get("noi_dung") or {}
    for khoa in ("gia_tri", "value", "gia_tri_moi"):
        try:
            gia_tri = noi_dung.get(khoa)
        except AttributeError:
            gia_tri = None
        if isinstance(gia_tri, (int, float)):
            return float(gia_tri)
    return None


def gom_gia_tri_theo_chi_so(
    su_kien_list: List[Dict[str, Any]],
) -> Dict[Tuple[str, str], List[float]]:
    """Gom gia tri su kien theo (jig_id, metric), giu dung thu tu nhan."""
    gom: Dict[Tuple[str, str], List[float]] = {}
    for su_kien in su_kien_list or []:
        gia_tri = trich_gia_tri_su_kien(su_kien)
        if gia_tri is None:
            continue
        khoa = (str(su_kien.get("jig_id") or "—"), str(su_kien.get("metric") or "—"))
        gom.setdefault(khoa, []).append(gia_tri)
    return gom


def danh_gia_lo_su_kien_qua_cong_xu_huong(
    su_kien_list: List[Dict[str, Any]],
    lich_su_theo_chi_so: Optional[Dict[Tuple[str, str], List[float]]] = None,
    window: int = 20,
) -> List[Dict[str, Any]]:
    """Danh gia tung nhom (jig, metric) qua cong xu huong SMA(20).

    - Chuoi danh gia = lich su cu + gia tri moi trong lo.
    - Ket luan diem: su kien loai ``canh_bao_drift`` coi la diem vi pham,
      loai khac la can bien (khong bao don le).
    - Chi xu huong da xac nhan (>=3 diem bat thuong lien tiep hoac >=3/5
      diem gan nhat) moi ``canh_bao=True``. Diem don le -> "Cần biến".
    - KHONG doi hanh vi gate SMA(20) hien co, chi goi `danh_gia_xu_huong_sma`
      va `gate_canh_bao_theo_xu_huong`.
    """
    lich_su_theo_chi_so = lich_su_theo_chi_so or {}
    gom = gom_gia_tri_theo_chi_so(su_kien_list)
    # Map (jig, metric) -> su kien dai dien (lay su kien canh bao cuoi cung).
    dai_dien: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for su_kien in su_kien_list or []:
        khoa = (str(su_kien.get("jig_id") or "—"), str(su_kien.get("metric") or "—"))
        if khoa not in gom:
            continue
        cu = dai_dien.get(khoa)
        if cu is None or str(su_kien.get("loai") or "") == "canh_bao_drift":
            dai_dien[khoa] = su_kien
    ket_qua: List[Dict[str, Any]] = []
    for khoa, gia_tri_moi in gom.items():
        lich_su = list(lich_su_theo_chi_so.get(khoa) or [])
        chuoi = lich_su + list(gia_tri_moi)
        xu_huong = danh_gia_xu_huong_sma(chuoi, window=window)
        su_kien = dai_dien.get(khoa) or {}
        la_diem_bao = str(su_kien.get("loai") or "") == "canh_bao_drift"
        ket_luan_diem: Dict[str, Any] = {
            "trang_thai": "Vi phạm" if la_diem_bao else "Cận biên",
            "chi_tiet": str((su_kien.get("noi_dung") or {}).get("chi_tiet") or ""),
            "canh_bao": bool(la_diem_bao),
            "gia_tri": gia_tri_moi[-1] if gia_tri_moi else None,
        }
        gate_canh_bao_theo_xu_huong(ket_luan_diem, xu_huong)
        if not ket_luan_diem.get("canh_bao"):
            ket_luan_diem["trang_thai"] = "Cần biến"
        ket_qua.append({
            "jig_id": khoa[0],
            "metric": khoa[1],
            "su_kien": su_kien,
            "chuoi_danh_gia": chuoi,
            "xu_huong": xu_huong,
            "ket_luan": ket_luan_diem,
            "canh_bao": bool(ket_luan_diem.get("canh_bao")),
        })
    return ket_qua


def chuyen_lo_thanh_the_da_qua_cong(
    su_kien_list: List[Dict[str, Any]],
    lich_su_theo_chi_so: Optional[Dict[Tuple[str, str], List[float]]] = None,
    window: int = 20,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Chuyen lo su kien thanh (the_canh_bao, muc_can_bien).

    - Chi nhom co xu huong xac nhan moi thanh the canh bao (hien trong chat).
    - Nhom con lai (diem don le / du lieu on dinh) thanh muc "Cần biến",
      KHONG bao.
    """
    danh_gia = danh_gia_lo_su_kien_qua_cong_xu_huong(
        su_kien_list, lich_su_theo_chi_so, window
    )
    cac_the: List[Dict[str, Any]] = []
    cac_muc_can_bien: List[Dict[str, str]] = []
    for muc in danh_gia:
        if muc.get("canh_bao"):
            cac_the.append(dinh_dang_canh_bao(muc.get("su_kien") or {}))
        else:
            cac_muc_can_bien.append({
                "ma_jig": str(muc.get("jig_id") or "—"),
                "thong_so": str(muc.get("metric") or "—"),
                "trang_thai": "Cần biến",
                "ly_do": str((muc.get("xu_huong") or {}).get("chi_tiet") or ""),
            })
    return cac_the, cac_muc_can_bien


def dinh_dang_text_chat_cho_the_realtime(the: Dict[str, Any]) -> str:
    """Render the canh bao realtime thanh text nam trong vung tra loi chat."""
    dong = [
        "Cảnh báo realtime — %s — %s (%s)"
        % (the.get("ma_jig", "—"), the.get("thong_so", "—"), the.get("muc_do", "Cần kiểm tra")),
        str(the.get("chi_tiet", "")),
        str(the.get("huong_dan", "")),
    ]
    return "\n".join(d for d in dong if str(d).strip())


def tom_tat_can_bien_cho_chat(muc: Dict[str, Any]) -> str:
    """Render muc can bien (diem don le) thanh 1 dong trong chat, khong bao."""
    return "Cần biến — %s — %s: %s" % (
        muc.get("ma_jig", "—"), muc.get("thong_so", "—"), muc.get("ly_do", "")
    )