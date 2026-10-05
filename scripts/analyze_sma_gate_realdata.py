"""Script phan tich kiem chung cong canh bao xu huong SMA(20) tren log JIG that.

Phuc vu ve: SMA-GATE-REALDATA-HOME
Du lieu: 2026_08_Master.csv (132 dong thuc te)
Cac chi so kiem chung:
  - Do am (Humidity): nguong duoi 40.0%
  - TaktTime: nguong tren 200.0s
  - Nhiet do (Temperature): nguong duoi 20.0°C

Tuong thich Python 3.11.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

# Dam bao import duoc src/
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from aios_habit.production_prediction.jig_log_ingest import evaluate_single_log_ewma
from aios_habit.production_prediction.metric_limits import NguongChiSo
from aios_habit.production_prediction.trend_alerts import (
    danh_gia_xu_huong_sma,
    detect_abnormal_sma,
    gate_canh_bao_theo_xu_huong,
)

CSV_PATH_DEFAULT = Path(
    r"C:\tmp\lsu1-deploy\data\lsu\Iris LSU\thu nghiem 6pcs do thong so va log"
    r"\2ND-1002_JIG BEAM\2026_08_Master.csv"
)


def load_master_csv(csv_path: Path = CSV_PATH_DEFAULT) -> Dict[str, Any]:
    """Nap tep CSV log JIG that va trich xuat 3 chuoi chi so."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Khong tim thay tep CSV log JIG that tai: {csv_path}")

    with open(csv_path, encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        header = [c.strip() for c in next(reader)]

        takt_idx = header.index("TaktTime")
        temp_idx = header.index("Temperature")
        humid_idx = header.index("Humidity")
        time_idx = header.index("TIME")
        date_idx = header.index("Date") if "Date" in header else 0
        serial_idx = header.index("Serial") if "Serial" in header else 3
        jig_idx = header.index("JIG") if "JIG" in header else 2

        rows = list(reader)

    records = []
    takts = []
    temps = []
    humids = []

    for idx, r in enumerate(rows):
        takt_val = float(r[takt_idx])
        temp_val = float(r[temp_idx])
        humid_val = float(r[humid_idx])

        rec = {
            "index": idx,
            "date": r[date_idx].strip(),
            "time": r[time_idx].strip(),
            "serial": r[serial_idx].strip(),
            "jig": r[jig_idx].strip(),
            "takttime": takt_val,
            "temperature": temp_val,
            "humidity": humid_val,
        }
        records.append(rec)
        takts.append(takt_val)
        temps.append(temp_val)
        humids.append(humid_val)

    return {
        "csv_path": str(csv_path),
        "total_rows": len(rows),
        "records": records,
        "takts": takts,
        "temps": temps,
        "humids": humids,
    }


def analyze_metric(
    name: str,
    values: List[float],
    records: List[Dict[str, Any]],
    nguong: NguongChiSo,
    check_vp_fn: Any,
    k: float = 3.0,
    window: int = 20,
) -> Dict[str, Any]:
    """Phan tich chi tiet mot chi so theo SMA va cong gate."""
    n = len(values)

    # 1. Danh sach vi pham nguong don diem
    single_violations = []
    for i, val in enumerate(values):
        if check_vp_fn(val):
            rec = records[i]
            single_violations.append(
                {
                    "row_index": i,
                    "date": rec["date"],
                    "time": rec["time"],
                    "serial": rec["serial"],
                    "value": val,
                }
            )

    # 2. Phat hien diem bat thuong tren toan bo chuoi
    pts_with_nguong = detect_abnormal_sma(values, window=window, k=k, nguong=nguong)
    abnormal_all_nguong = [p for p in pts_with_nguong if p["abnormal"]]

    pts_pure_sma = detect_abnormal_sma(values, window=window, k=k, nguong=None)
    abnormal_all_pure = [p for p in pts_pure_sma if p["abnormal"]]

    # 3. Mo phong tuan tu theo thoi gian (nhu khi tung log den)
    sequential_results = []
    blocked_violations = []
    confirmed_violations = []
    spurious_trend_alerts = []

    for i in range(n):
        val = values[i]
        hist = values[:i]
        series_so_far = values[: i + 1]

        # Don diem
        res_single = evaluate_single_log_ewma(val, hist, nguong=nguong)
        point_alert = bool(res_single.get("canh_bao"))

        # Xu huong SMA
        res_trend = danh_gia_xu_huong_sma(
            series_so_far, window=window, k=k, nguong=nguong
        )
        trend_alert = bool(res_trend.get("canh_bao"))

        # Gate ket hop
        res_gated = gate_canh_bao_theo_xu_huong(dict(res_single), res_trend)
        final_alert = bool(res_gated.get("canh_bao"))

        is_vp = check_vp_fn(val)

        item = {
            "row_index": i,
            "value": val,
            "is_violation": is_vp,
            "point_alert": point_alert,
            "trend_alert": trend_alert,
            "final_alert": final_alert,
            "trend_status": res_trend.get("trang_thai"),
            "trend_detail": res_trend.get("chi_tiet"),
        }
        sequential_results.append(item)

        if is_vp:
            if not final_alert:
                blocked_violations.append(item)
            else:
                confirmed_violations.append(item)
        else:
            if final_alert:
                spurious_trend_alerts.append(item)

    return {
        "metric_name": name,
        "total_points": n,
        "k": k,
        "window": window,
        "min_value": min(values) if values else None,
        "max_value": max(values) if values else None,
        "mean_value": sum(values) / n if n else None,
        "single_violation_count": len(single_violations),
        "single_violations": single_violations,
        "abnormal_full_with_nguong_count": len(abnormal_all_nguong),
        "abnormal_full_pure_sma_count": len(abnormal_all_pure),
        "abnormal_full_pure_sma": abnormal_all_pure,
        "gate_blocked_count": len(blocked_violations),
        "trend_confirmed_count": len(confirmed_violations),
        "spurious_alerts_count": len(spurious_trend_alerts),
        "blocked_details": blocked_violations,
        "confirmed_details": confirmed_violations,
        "sequential_results": sequential_results,
    }


def evaluate_k_sensitivity(
    values: List[float],
    k_range: List[float],
    nguong: NguongChiSo,
    window: int = 20,
) -> List[Dict[str, Any]]:
    """Khao sat do nhay cua he so k (1.0 den 4.0)."""
    results = []
    for k in k_range:
        pts_pure = detect_abnormal_sma(values, window=window, k=k, nguong=None)
        abn_pure = [p for p in pts_pure if p["abnormal"]]

        # Kiem tra co canh bao xu huong nao trong suot chuoi khong
        trend_alert_steps = 0
        for i in range(len(values)):
            series = values[: i + 1]
            res = danh_gia_xu_huong_sma(series, window=window, k=k, nguong=None)
            if res.get("canh_bao"):
                trend_alert_steps += 1

        results.append(
            {
                "k": k,
                "abnormal_points_count": len(abn_pure),
                "trend_alert_steps": trend_alert_steps,
            }
        )
    return results


def run_full_analysis(csv_path: Path = CSV_PATH_DEFAULT) -> Dict[str, Any]:
    """Chay toan bo phan tich va tra ve ket qua tong the."""
    data = load_master_csv(csv_path)
    records = data["records"]

    # 1. Do am (Humidity): nguong duoi 40.0%
    nguong_humid = NguongChiSo(
        jig_id="2ND-1002",
        chi_so="Humidity",
        gioi_han_duoi=40.0,
        nguon="nguoi_dung",
    )
    res_humid = analyze_metric(
        "Humidity",
        data["humids"],
        records,
        nguong_humid,
        lambda v: v < 40.0,
    )

    # 2. TaktTime: nguong tren 200.0s
    nguong_takt = NguongChiSo(
        jig_id="2ND-1002",
        chi_so="TaktTime",
        gioi_han_tren=200.0,
        nguon="nguoi_dung",
    )
    res_takt = analyze_metric(
        "TaktTime",
        data["takts"],
        records,
        nguong_takt,
        lambda v: v > 200.0,
    )

    # 3. Nhiet do (Temperature): nguong duoi 20.0°C
    nguong_temp = NguongChiSo(
        jig_id="2ND-1002",
        chi_so="Temperature",
        gioi_han_duoi=20.0,
        nguon="nguoi_dung",
    )
    res_temp = analyze_metric(
        "Temperature",
        data["temps"],
        records,
        nguong_temp,
        lambda v: v < 20.0,
    )

    # Khao sat k
    k_range = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    sens_humid = evaluate_k_sensitivity(data["humids"], k_range, nguong_humid)
    sens_takt = evaluate_k_sensitivity(data["takts"], k_range, nguong_takt)
    sens_temp = evaluate_k_sensitivity(data["temps"], k_range, nguong_temp)

    total_single_vp = (
        res_humid["single_violation_count"]
        + res_takt["single_violation_count"]
        + res_temp["single_violation_count"]
    )
    total_blocked = (
        res_humid["gate_blocked_count"]
        + res_takt["gate_blocked_count"]
        + res_temp["gate_blocked_count"]
    )
    total_confirmed = (
        res_humid["trend_confirmed_count"]
        + res_takt["trend_confirmed_count"]
        + res_temp["trend_confirmed_count"]
    )

    summary = {
        "csv_path": str(csv_path),
        "total_rows": data["total_rows"],
        "total_single_violations": total_single_vp,
        "total_gate_blocked": total_blocked,
        "total_trend_confirmed": total_confirmed,
        "metrics": {
            "Humidity": res_humid,
            "TaktTime": res_takt,
            "Temperature": res_temp,
        },
        "k_sensitivity": {
            "Humidity": sens_humid,
            "TaktTime": sens_takt,
            "Temperature": sens_temp,
        },
    }
    return summary


if __name__ == "__main__":
    path_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else CSV_PATH_DEFAULT
    print(f"--- BAT DAU PHAN TICH SMA-GATE-REALDATA-HOME ---")
    print(f"File du lieu: {path_arg}")

    summary = run_full_analysis(path_arg)

    print(f"\nTong so dong: {summary['total_rows']}")
    print(f"Tong so vi pham nguong don diem: {summary['total_single_violations']}")
    print(f"Tong so bi cong gate chan: {summary['total_gate_blocked']} ({summary['total_gate_blocked']/summary['total_single_violations']*100:.1f}%)")
    print(f"Tong so thanh canh bao xu huong that: {summary['total_trend_confirmed']} ({summary['total_trend_confirmed']/summary['total_single_violations']*100:.1f}%)")

    print("\n--- CHI TIET 21 DIEM VI PHAM NGUONG DON DIEM ---")
    for name, m in summary["metrics"].items():
        print(f"\nChi so: {name} (Nguong vi pham: {m['single_violation_count']} diem)")
        for v in m["single_violations"]:
            idx = v["row_index"]
            seq = m["sequential_results"][idx]
            # Lay them thong so SMA tai thoi diem do
            val = v["value"]
            print(
                f"  Dong {idx:3d} | {v['date']} {v['time']} | Serial: {v['serial']} | "
                f"Gia tri: {val:6.1f} | Point alert: {seq['point_alert']} | "
                f"Trend alert: {seq['trend_alert']} | Final alert: {seq['final_alert']} | "
                f"Trang thai xu huong: {seq['trend_status']}"
            )


    print("\n--- KHAO SAT DO NHAY HE SO k ---")
    print(f"{'k':<6} | {'Do am (pure SMA)':<18} | {'TaktTime (pure SMA)':<20} | {'Nhiet do (pure SMA)':<20}")
    print("-" * 72)
    s_h = summary["k_sensitivity"]["Humidity"]
    s_tk = summary["k_sensitivity"]["TaktTime"]
    s_tp = summary["k_sensitivity"]["Temperature"]
    for i in range(len(s_h)):
        k_val = s_h[i]["k"]
        print(f"{k_val:<6.1f} | {s_h[i]['abnormal_points_count']:<18} | {s_tk[i]['abnormal_points_count']:<20} | {s_tp[i]['abnormal_points_count']:<20}")

