"""Canh bao theo xu huong voi SMA(20) (user chot 2026-10-03).

Nguyen tac (khac voi danh gia don diem):
- Diem bat thuong = gia tri lech khoi SMA(20) qua xa: |x - SMA20| > k * sigma,
  sigma la do lech chuan cua cac phan du neu trong cua so.
- Neu co nguong that (NguongChiSo): diem vuot nguong that cung tinh la
  bat thuong.
- CHI canh bao khi co XU HUONG: `diem_lien_tiep` diem bat thuong lien tiep
  o cuoi chuoi, hoac >= `toi_thieu` diem bat thuong trong `nhin_lai` diem
  gan nhat. Mot diem xau don le -> "Can bien", khong canh bao.
- Hop dong tra ve giong `evaluate_single_log_ewma` (trang_thai / chi_tiet /
  canh_bao / gia_tri) de cam vao duong diem tu dong hien co.

Tuong thich Python 3.11.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

WINDOW_DEFAULT = 20
K_DEFAULT = 3.0
DIEM_LIEN_TIEP_DEFAULT = 3
NHIN_LAI_DEFAULT = 5
TOI_THIEU_DEFAULT = 3


def sma(values: Sequence[float], window: int = WINDOW_DEFAULT) -> List[Optional[float]]:
    """Trung binh dong gian don. None cho (window-1) diem dau tien."""
    clean = [float(v) for v in values]
    result: List[Optional[float]] = []
    if window <= 0:
        raise ValueError("window phai > 0")
    running = 0.0
    for i, value in enumerate(clean):
        running += value
        if i >= window:
            running -= clean[i - window]
        if i >= window - 1:
            result.append(running / window)
        else:
            result.append(None)
    return result


def _stdev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance ** 0.5


def _vuot_nguong_that(value: float, nguong: Any) -> bool:
    try:
        tren = getattr(nguong, "gioi_han_tren", None)
        duoi = getattr(nguong, "gioi_han_duoi", None)
        if tren is not None and value > float(tren):
            return True
        if duoi is not None and value < float(duoi):
            return True
    except (TypeError, ValueError):
        pass
    return False


def detect_abnormal_sma(
    values: Sequence[float],
    window: int = WINDOW_DEFAULT,
    k: float = K_DEFAULT,
    nguong: Any = None,
) -> List[Dict]:
    """Danh dau diem bat thuong theo SMA(window).

    Baseline cua diem i la trung binh `window` diem LIEN TRUOC i, LOAI TRU
    cac diem da bi danh dau bat thuong (iterative) de diem xau khong nhiem
    baseline (masking). Tra ve list dict cho moi diem.
    """
    clean = [float(v) for v in values]
    points: List[Dict] = []
    abnormal_idx = set()
    for i, value in enumerate(clean):
        if i < window:
            points.append(
                {
                    "index": i,
                    "value": value,
                    "sma": None,
                    "residual": None,
                    "sigma": 0.0,
                    "abnormal": False,
                    "ly_do": "chua_du_cua_so",
                }
            )
            continue
        hist = [clean[j] for j in range(i - window, i) if j not in abnormal_idx]
        if len(hist) < max(2, window // 2):
            hist = [clean[j] for j in range(i - window, i)]
        baseline = sum(hist) / len(hist)
        sigma = _stdev([v - baseline for v in hist])
        residual = value - baseline
        vuot_nguong = _vuot_nguong_that(value, nguong) if nguong is not None else False
        if vuot_nguong:
            abnormal, ly_do = True, "vuot_nguong_that"
        elif sigma > 0 and abs(residual) > k * sigma:
            abnormal, ly_do = True, "lech_xa_sma"
        elif sigma == 0 and residual != 0:
            abnormal, ly_do = True, "nen_phang_nhung_lech"
        else:
            abnormal, ly_do = False, "binh_thuong"
        if abnormal:
            abnormal_idx.add(i)
        points.append(
            {
                "index": i,
                "value": value,
                "sma": baseline,
                "residual": residual,
                "sigma": sigma,
                "abnormal": abnormal,
                "ly_do": ly_do,
            }
        )
    return points


def danh_gia_xu_huong_sma(
    values: Sequence[float],
    window: int = WINDOW_DEFAULT,
    k: float = K_DEFAULT,
    diem_lien_tiep: int = DIEM_LIEN_TIEP_DEFAULT,
    nhin_lai: int = NHIN_LAI_DEFAULT,
    toi_thieu: int = TOI_THIEU_DEFAULT,
    nguong: Any = None,
) -> Dict[str, Any]:
    """Ket luan canh bao theo XU HUONG (khong bao tu mot diem xau don le)."""
    clean = [float(v) for v in values if isinstance(v, (int, float))]
    gia_tri = clean[-1] if clean else None
    if len(clean) < window:
        return {
            "trang_thai": "Cận biên",
            "chi_tiet": (
                "Chưa đủ điểm nền để kết luận xu hướng theo SMA(%d) "
                "(mới có %d điểm), cần thêm dữ liệu cùng JIG." % (window, len(clean))
            ),
            "canh_bao": False,
            "gia_tri": gia_tri,
            "diem_bat_thuong": [],
        }
    points = detect_abnormal_sma(clean, window, k, nguong)
    recent = points[-nhin_lai:] if nhin_lai > 0 else points
    abnormal_recent = [p for p in recent if p["abnormal"]]
    abnormal_all = [p for p in points if p["abnormal"]]
    consecutive = 0
    for point in reversed(points):
        if point["abnormal"]:
            consecutive += 1
        else:
            break
    if consecutive >= diem_lien_tiep:
        return {
            "trang_thai": "Vi phạm",
            "chi_tiet": (
                "Có xu hướng bất thường: %d điểm liên tiếp lệch xa SMA(%d). "
                "Điểm mới nhất %.3f so với SMA %.3f."
                % (consecutive, window, clean[-1], points[-1]["sma"])
            ),
            "canh_bao": True,
            "gia_tri": gia_tri,
            "diem_bat_thuong": [p["index"] for p in abnormal_recent],
        }
    if len(abnormal_recent) >= toi_thieu:
        return {
            "trang_thai": "Vi phạm",
            "chi_tiet": (
                "Có xu hướng bất thường: %d/%d điểm gần nhất bất thường so với "
                "SMA(%d)." % (len(abnormal_recent), len(recent), window)
            ),
            "canh_bao": True,
            "gia_tri": gia_tri,
            "diem_bat_thuong": [p["index"] for p in abnormal_recent],
        }
    if abnormal_recent:
        return {
            "trang_thai": "Cận biên",
            "chi_tiet": (
                "Mới có %d điểm bất thường đơn lẻ trong %d điểm gần nhất — "
                "một điểm xấu đơn lẻ chưa thành xu hướng, theo dõi thêm, "
                "chưa cảnh báo." % (len(abnormal_recent), len(recent))
            ),
            "canh_bao": False,
            "gia_tri": gia_tri,
            "diem_bat_thuong": [p["index"] for p in abnormal_recent],
        }
    if abnormal_all:
        return {
            "trang_thai": "Cận biên",
            "chi_tiet": (
                "Từng có %d điểm bất thường đơn lẻ nhưng chuỗi đã ổn định lại "
                "quanh SMA(%d) — chưa thành xu hướng, chưa cảnh báo."
                % (len(abnormal_all), window)
            ),
            "canh_bao": False,
            "gia_tri": gia_tri,
            "diem_bat_thuong": [p["index"] for p in abnormal_all],
        }
    return {
        "trang_thai": "Đạt",
        "chi_tiet": "Các điểm gần nhất đều nằm quanh SMA(%d), chưa thấy xu hướng xấu." % window,
        "canh_bao": False,
        "gia_tri": gia_tri,
        "diem_bat_thuong": [],
    }


def should_alert_series(
    values: Sequence[float],
    **kwargs: Any,
) -> bool:
    """Tien ich: chi hoi co canh bao xu huong hay khong."""
    return bool(danh_gia_xu_huong_sma(values, **kwargs).get("canh_bao"))


def gate_canh_bao_theo_xu_huong(
    ket_luan_diem: Dict[str, Any],
    xu_huong: Dict[str, Any],
) -> Dict[str, Any]:
    """Gate canh bao don-diem bang ket luan xu huong SMA (user chot 2026-10-03).

    Quy tac:
    - Tieu de bat thuong = diem HOAC xu huong (trung thuc phan loai diem,
      khong viet lai ket luan diem khi chua du bang chung xu huong).
    - Canh bao (email/thong bao) CHI khi co xu huong xac nhan:
      `canh_bao` cuoi = diem AND xu huong, tru khi xu huong bat duoc dich
      chuyen ben vung ma danh gia don diem bo sot (nen bi nhiem) thi nang
      ket luan theo xu huong.
    Tra ve dict ket_luan_diem da dieu chinh (sua tai cho + tra ve).
    """
    trend_alert = bool(xu_huong.get("canh_bao"))
    point_alert = bool(ket_luan_diem.get("canh_bao"))
    if trend_alert and not point_alert:
        ket_luan_diem["trang_thai"] = xu_huong.get(
            "trang_thai", ket_luan_diem.get("trang_thai")
        )
        ket_luan_diem["chi_tiet"] = str(xu_huong.get("chi_tiet", "") or "")
        ket_luan_diem["canh_bao"] = True
    else:
        ket_luan_diem["canh_bao"] = point_alert and trend_alert
    ket_luan_diem["xu_huong_sma"] = str(xu_huong.get("chi_tiet", "") or "")
    return ket_luan_diem
