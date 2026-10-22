# -*- coding: utf-8 -*-
"""Production Log Error Analyzer Script.
Parses CSV production logs and counts lines grouped by error code, JIG, and judge status.
Runs on Python 3.11.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

# Force UTF-8 output
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def analyze_production_log(csv_path: Path):
    print(f"=== ĐỌC VÀ PHÂN TÍCH TỆP LOG SẢN XUẤT THẬT ===")
    print(f"Đường dẫn tệp: {csv_path}")
    if not csv_path.is_file():
        print(f"LỖI: Tệp không tồn tại: {csv_path}")
        sys.exit(1)

    file_size = csv_path.stat().st_size
    print(f"Dung lượng tệp: {file_size:,} bytes")

    judge_counter = Counter()
    jig_counter = Counter()
    mode_counter = Counter()
    date_counter = Counter()
    total_lines = 0

    with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        headers = [h.strip() for h in (reader.fieldnames or [])]
        print(f"Số cột dữ liệu: {len(headers)} cột")
        print(f"Các cột chính: {headers[:10]}")

        for row in reader:
            total_lines += 1
            # Clean keys
            clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
            date_val = clean_row.get("DATE", "Unknown")
            jig_val = clean_row.get("JigNumber", "Unknown")
            mode_val = clean_row.get("Mode", "Unknown")
            judge_val = clean_row.get("TotalJudge", "") or mode_val

            date_counter[date_val] += 1
            jig_counter[jig_val] += 1
            mode_counter[mode_val] += 1
            judge_counter[judge_val] += 1

    print(f"\n--- KẾT QUẢ ĐẾM SỐ DÒNG THEO PHÂN LOẠI LỖI & PHÁN ĐỊNH ---")
    print(f"Tổng số dòng dữ liệu sản xuất: {total_lines:,} dòng")
    
    print(f"\n1. Thống kê theo Trạng thái Mode / Phán định (TotalJudge):")
    for judge, count in judge_counter.most_common():
        pct = (count / total_lines) * 100 if total_lines else 0
        print(f"   - [{judge}]: {count:,} dòng ({pct:.2f}%)")

    print(f"\n2. Thống kê theo Thiết bị JIG sản xuất (JigNumber):")
    for jig, count in jig_counter.most_common():
        pct = (count / total_lines) * 100 if total_lines else 0
        print(f"   - JIG {jig}: {count:,} dòng ({pct:.2f}%)")

    print(f"\n3. Thống kê theo Ngày phát sinh (DATE):")
    for d, count in sorted(date_counter.items()):
        print(f"   - Ngày {d}: {count:,} dòng")

    print(f"\n=== HOÀN TẤT PHÂN TÍCH THÀNH CÔNG TRÊN PYTHON 3.11 ===")
    return total_lines, judge_counter

if __name__ == "__main__":
    target_csv = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\\Sandbox\\AIOS_habbit\\Tài liệu của tất cả dòng máy\\Sirius LSU\\Sirius2_linearity\\Log\\1001-1\\2025_02_Error.csv")
    analyze_production_log(target_csv)
