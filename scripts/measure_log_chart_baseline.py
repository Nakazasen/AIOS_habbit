# -*- coding: utf-8 -*-
"""Script do luong RAM va thoi gian xu ly file log kich thuoc lon tren code hien tai (DESKTOP-HOME-LOGCHART-CAP-RAISE)."""

from __future__ import annotations

import gc
import os
import sys
import time
import tracemalloc
from pathlib import Path
import psutil

# Setup path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from aios_habit.log_chart.parser import parse_log_file
from aios_habit.log_chart.recommender import build_initial_spec
from aios_habit.log_chart.renderer import render_chart_image

DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MASTER_CSV = DATA_DIR / "mau_csv_master_lsu.csv"
FILE_31MB = DATA_DIR / "2025_02_synthetic_30872058.csv"
FILE_64MB = DATA_DIR / "synthetic_64mb_67108864.csv"

TARGET_31MB_BYTES = 30872058
TARGET_64MB_BYTES = 67108864


def generate_exact_sized_lsu_csv(target_path: Path, target_bytes: int, known_units: dict) -> None:
    """Tao file CSV log LSU co kich thuoc byte-exact voi cac gia tri kiem chung duoc dinh truoc."""
    if target_path.exists() and target_path.stat().st_size == target_bytes:
        print(f"Tep {target_path.name} da ton tai voi dung kich thuoc {target_bytes:,} bytes.")
        return

    print(f"Dang tao tep {target_path.name} co dung kich thuoc {target_bytes:,} bytes...")
    lines = MASTER_CSV.read_text(encoding="utf-8").splitlines()
    header = lines[0]
    base_rows = lines[1:]

    output_lines = [header]
    current_bytes = len(header.encode("utf-8")) + 1

    idx = 0
    # Dung lai truoc muc tieu khoang 4KB de chen padding can byte chinh xac
    while True:
        base_cols = base_rows[idx % len(base_rows)].split(",")
        sec = idx % 60
        minute = (idx // 60) % 60
        hour = (idx // 3600) % 24
        base_cols[0] = f"2025.02.{(idx // 86400) % 28 + 1:02d}"
        base_cols[1] = f"{hour:02d}:{minute:02d}:{sec:02d}"
        unit_id = f"SIR_UNIT_{idx+1:06d}"
        base_cols[2] = unit_id

        if (idx + 1) in known_units:
            ov = known_units[idx + 1]
            for col_idx, val in ov.items():
                base_cols[col_idx] = str(val)

        row_str = ",".join(base_cols)
        row_bytes = len(row_str.encode("utf-8")) + 1

        if current_bytes + row_bytes > target_bytes - 4096:
            break

        output_lines.append(row_str)
        current_bytes += row_bytes
        idx += 1

    content = "\n".join(output_lines)
    raw = content.encode("utf-8")
    diff = target_bytes - len(raw)
    assert diff > 10, f"diff qua nho: {diff}"
    # b"\n# PAD:" la 7 bytes
    padding_bytes = b"\n# PAD:" + b"=" * (diff - 7)
    raw += padding_bytes
    assert len(raw) == target_bytes, f"Sai lech: {len(raw)} != {target_bytes}"
    target_path.write_bytes(raw)
    print(f"-> Da tao xong {target_path.name}: {len(raw):,} bytes.")


def benchmark_file(file_path: Path) -> dict:
    gc.collect()
    proc = psutil.Process()
    rss_before = proc.memory_info().rss

    tracemalloc.start()
    t0 = time.perf_counter()

    # 1. Parse log file
    table = parse_log_file(file_path)
    t_parse = time.perf_counter() - t0

    current_tm, peak_tm = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_after_parse = proc.memory_info().rss

    # 2. Render chart
    t1 = time.perf_counter()
    spec = build_initial_spec(table)
    png_bytes = render_chart_image(spec, table)
    t_render = time.perf_counter() - t1

    rss_after_render = proc.memory_info().rss
    t_total = time.perf_counter() - t0

    return {
        "file_name": file_path.name,
        "file_size_bytes": file_path.stat().st_size,
        "total_rows_parsed": table.total_rows,
        "total_columns": len(table.columns),
        "t_parse_sec": round(t_parse, 3),
        "t_render_sec": round(t_render, 3),
        "t_total_sec": round(t_total, 3),
        "tracemalloc_peak_mb": round(peak_tm / (1024 * 1024), 2),
        "rss_delta_parse_mb": round((rss_after_parse - rss_before) / (1024 * 1024), 2),
        "rss_peak_mb": round(max(rss_after_parse, rss_after_render) / (1024 * 1024), 2),
        "png_bytes": len(png_bytes),
    }


def main():
    # 3 gia tri doi chieu dac biet tai dong 1, 100, 1000
    # cot 8: SKEW:BLACK[um], cot 9: BOW:BLACK:-70[um], cot 24: LIGHT_PATH:BLACK:-140[mm]
    known_31mb = {
        1: {8: -320, 9: 52, 24: 0.25},
        100: {8: -155, 9: 45, 24: 0.28},
        1000: {8: -210, 9: 68, 24: 0.31},
    }

    generate_exact_sized_lsu_csv(FILE_31MB, TARGET_31MB_BYTES, known_31mb)
    generate_exact_sized_lsu_csv(FILE_64MB, TARGET_64MB_BYTES, known_31mb)

    print("\n--- Bat dau do luong tren file 31MB ---")
    res_31mb = benchmark_file(FILE_31MB)
    print(f"Ket qua 31MB: {res_31mb}")

    print("\n--- Bat dau do luong tren file 64MB ---")
    res_64mb = benchmark_file(FILE_64MB)
    print(f"Ket qua 64MB: {res_64mb}")


if __name__ == "__main__":
    main()
