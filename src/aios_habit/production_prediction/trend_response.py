"""Phan ung khi xu huong xau (no sau demo): canh bao + phan doan nguyen nhan
+ phoi hop dieu tra + luu bai hoc.

Nhan ket luan tu trend_alerts.danh_gia_xu_huong_sma(); khi co canh bao:
- `phan_doan_nguyen_nhan()`: gia thuyet theo hinh dang dich chuyen
  (dot ngot / troi dan / dao dong) — GHI RO la gia thuyet, khong phai ket luan.
- `de_xuat_dieu_tra()`: checklist phoi hop dieu tra theo hinh dang.
- `luu_bai_hoc()`: luu JSONL local_cases/trend_lessons.jsonl — KHONG vao kho tri thuc.

Tuong thich Python 3.11.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

HINH_DANG_DOT_NGOT = "dot_ngot"
HINH_DANG_TROI_DAN = "troi_dan"
HINH_DANG_DAO_DONG = "dao_dong"
HINH_DANG_CHUA_RO = "chua_ro"


def lessons_file() -> Path:
    base = Path(os.environ.get("AIOS_LOCAL_CASES_DIR", "") or Path.cwd() / "local_cases")
    return base / "trend_lessons.jsonl"


def phan_dang_dich_chuyen(
    values: Sequence[float],
    abnormal_indexes: Sequence[int],
    window: int = 20,
) -> Dict[str, Any]:
    """Phan loai hinh dang dich chuyen tu cac diem bat thuong (gia thuyet)."""
    clean = [float(v) for v in values]
    idx = sorted(set(int(i) for i in abnormal_indexes))
    if not idx or len(clean) < window + 1:
        return {"hinh_dang": HINH_DANG_CHUA_RO, "mo_ta": "Chưa đủ dữ liệu để phân dạng."}
    baseline_vals = clean[max(0, idx[0] - window) : idx[0]]
    baseline = sum(baseline_vals) / len(baseline_vals) if baseline_vals else clean[0]
    seg = [clean[i] for i in idx if 0 <= i < len(clean)]
    if not seg:
        return {"hinh_dang": HINH_DANG_CHUA_RO, "mo_ta": "Chưa đủ dữ liệu để phân dạng."}

    # Dao dong: dau phan du doi dau lien tuc.
    residuals = [v - baseline for v in seg]
    sign_changes = sum(
        1 for a, b in zip(residuals, residuals[1:]) if a * b < 0
    )
    if len(residuals) >= 3 and sign_changes >= len(residuals) - 1:
        return {
            "hinh_dang": HINH_DANG_DAO_DONG,
            "mo_ta": "Giá trị dao động quanh nền — nghi rung, lỏng đồ gá hoặc nhiễu đo.",
        }
    # Troi dan: xu huong don dieu theo thoi gian (kiem tra truoc dot ngot
    # vi doan leo doc deu cung co the vuot nguong do lech dot ngot).
    ups = sum(1 for a, b in zip(seg, seg[1:]) if b > a)
    downs = sum(1 for a, b in zip(seg, seg[1:]) if b < a)
    if len(seg) >= 3 and (ups >= len(seg) - 2 or downs >= len(seg) - 2):
        huong = "tăng dần" if ups > downs else "giảm dần"
        return {
            "hinh_dang": HINH_DANG_TROI_DAN,
            "mo_ta": f"Giá trị {huong} theo thời gian — nghi mòn dụng cụ, trôi nhiệt hoặc lão hóa.",
        }
    # Dot ngot: diem bat thuong dau tien da lech lon, cac diem sau on dinh quanh muc moi.
    first_jump = abs(seg[0] - baseline)
    seg_mean = sum(seg) / len(seg)
    seg_var = sum((v - seg_mean) ** 2 for v in seg) / len(seg)
    seg_std = seg_var ** 0.5
    if first_jump > 0 and seg_std < first_jump * 0.5:
        return {
            "hinh_dang": HINH_DANG_DOT_NGOT,
            "mo_ta": (
                "Dịch chuyển mức đột ngột rồi ổn định ở mức mới "
                f"({baseline:.3f} → {seg_mean:.3f}) — nghi đổi setup, thay đồ gá, "
                "đổi lô vật tư hoặc hiệu chuẩn lại."
            ),
        }
    return {
        "hinh_dang": HINH_DANG_CHUA_RO,
        "mo_ta": "Hình dạng chưa rõ — cần thêm điểm dữ liệu và đối chiếu log bảo trì.",
    }


def phan_doan_nguyen_nhan(
    values: Sequence[float],
    abnormal_indexes: Sequence[int],
    *,
    window: int = 20,
) -> Dict[str, Any]:
    """Gia thuyet nguyen nhan (ghi ro KHONG phai ket luan cuoi)."""
    phan_dang = phan_dang_dich_chuyen(values, abnormal_indexes, window)
    return {
        "gia_thuyet": phan_dang["mo_ta"],
        "hinh_dang": phan_dang["hinh_dang"],
        "luu_y": "Đây là giả thuyết từ hình dạng dữ liệu, cần chuyên gia xác nhận.",
    }


def de_xuat_dieu_tra(hinh_dang: str) -> List[str]:
    """Checklist phoi hop dieu tra theo hinh dang dich chuyen."""
    chung = [
        "Đối chiếu log bảo trì / thay đồ gá trong khoảng thời gian dịch chuyển.",
        "So sánh với ca sản xuất trước và sau để loại trừ yếu tố lô vật tư.",
        "Ghi lại kết quả điều tra vào bài học để lần sau nhận diện nhanh hơn.",
    ]
    rieng = {
        HINH_DANG_DOT_NGOT: [
            "Kiểm tra biên bản setup/đổi mã hàng tại thời điểm dịch chuyển.",
            "Xác nhận lại hiệu chuẩn thiết bị đo.",
        ],
        HINH_DANG_TROI_DAN: [
            "Kiểm tra độ mòn dụng cụ/đầu đo theo lịch bảo dưỡng.",
            "Đối chiếu nhiệt độ môi trường và nhiệt độ máy trong ca.",
        ],
        HINH_DANG_DAO_DONG: [
            "Kiểm tra độ rơ/lỏng của đồ gá và bulông kẹp.",
            "Xem lại nguồn nhiễu: khí nén, điện áp, rung nền.",
        ],
        HINH_DANG_CHUA_RO: [
            "Thu thêm dữ liệu rồi chạy lại phân dạng xu hướng.",
        ],
    }
    return rieng.get(hinh_dang, rieng[HINH_DANG_CHUA_RO]) + chung


def luu_bai_hoc(
    jig_id: str,
    metric: str,
    hinh_dang: str,
    gia_thuyet: str,
    ket_luan_chuyen_gia: str = "",
) -> Dict[str, Any]:
    """Luu bai hoc xu huong (van hanh, khong vao kho tri thuc)."""
    record = {
        "jig_id": str(jig_id or ""),
        "metric": str(metric or ""),
        "hinh_dang": hinh_dang,
        "gia_thuyet": str(gia_thuyet or "")[:2000],
        "ket_luan_chuyen_gia": str(ket_luan_chuyen_gia or "")[:2000],
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    path = lessons_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True}


def xu_ly_xu_huong_xau(
    jig_id: str,
    metric: str,
    values: Sequence[float],
    trend_result: Dict[str, Any],
    *,
    window: int = 20,
) -> Dict[str, Any]:
    """Goi khi trend verdict canh_bao=True: tra ve goi phan ung day du."""
    if not trend_result.get("canh_bao"):
        return {"co_xu_huong_xau": False}
    abnormal = list(trend_result.get("diem_bat_thuong") or [])
    doan = phan_doan_nguyen_nhan(values, abnormal, window=window)
    return {
        "co_xu_huong_xau": True,
        "canh_bao": trend_result.get("chi_tiet", ""),
        "phan_doan_nguyen_nhan": doan,
        "de_xuat_dieu_tra": de_xuat_dieu_tra(doan["hinh_dang"]),
    }


def dinh_kem_phan_ung(
    ket_luan: Dict[str, Any],
    jig_id: str,
    metric: str,
    values: Sequence[float],
    trend_result: Dict[str, Any],
    *,
    window: int = 20,
) -> Dict[str, Any]:
    """Dinh kem phan doan + de xuat dieu tra vao ket_luan khi co canh bao xu huong.

    Goi sau gate_canh_bao_theo_xu_huong(). Sua tai cho + tra ve ket_luan.
    """
    if not ket_luan.get("canh_bao"):
        return ket_luan
    phan_ung = xu_ly_xu_huong_xau(jig_id, metric, values, trend_result, window=window)
    if phan_ung.get("co_xu_huong_xau"):
        ket_luan["phan_doan_nguyen_nhan"] = phan_ung["phan_doan_nguyen_nhan"]["gia_thuyet"]
        ket_luan["luu_y_phan_doan"] = phan_ung["phan_doan_nguyen_nhan"]["luu_y"]
        ket_luan["de_xuat_dieu_tra"] = phan_ung["de_xuat_dieu_tra"]
    return ket_luan
