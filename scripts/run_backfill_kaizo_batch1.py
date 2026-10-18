"""Backfill Kaizo (countermeasure) for batch_id = 1 in reconciled error cases DB.

Ticket: DESKTOP-KDTPS-BACKFILL-KAIZO-HOME
Repository: Nakazasen/AIOS_habbit (branch: phieu-viec/rag-fix1)
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import openpyxl
import xlrd

sys.path.insert(0, r"D:\Sandbox\AIOS_habbit\src")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from aios_habit.error_cases.column_map import parse_date_cell
from aios_habit.error_cases.completeness import is_filled

# Re-use parsing functions from reconcile pipeline
sys.path.insert(0, r"C:\tmp\kdtps_standard")
from run_reconcile_pipeline import (
    BASE_DIR,
    EXTRACTED_DIR,
    WORK_DB,
    is_dash_or_empty,
    make_dedup_key,
    norm_key_part,
    normalize_cell,
    parse_legacy_daily_row,
    parse_standard_kdtps_row,
)


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_policy(cur: sqlite3.Cursor, where: str) -> dict[str, Any]:
    """Measure completeness using Step 0 Policy QĐ1 + QĐ2 formula."""
    sql = f"""
    SELECT
        COUNT(*) AS total,
        SUM(CASE WHEN process_stage IS NOT NULL AND TRIM(process_stage) != '' AND TRIM(process_stage) != 'ー' THEN 1 ELSE 0 END) AS stage_ok,
        SUM(CASE WHEN phenomenon IS NOT NULL AND TRIM(phenomenon) != '' AND TRIM(phenomenon) != 'ー' THEN 1 ELSE 0 END) AS phenom_ok,
        SUM(CASE WHEN error_code_i IS NOT NULL AND TRIM(error_code_i) != '' AND TRIM(error_code_i) != 'ー' THEN 1 ELSE 0 END) AS code_strict_ok,
        SUM(CASE WHEN COALESCE(error_code_i, error_code_h, error_name) IS NOT NULL AND TRIM(COALESCE(error_code_i, error_code_h, error_name)) != '' AND TRIM(COALESCE(error_code_i, error_code_h, error_name)) != 'ー' THEN 1 ELSE 0 END) AS code_policy_ok,
        SUM(CASE WHEN cause IS NOT NULL AND TRIM(cause) != '' AND TRIM(cause) != 'ー' THEN 1 ELSE 0 END) AS cause_ok,
        SUM(CASE WHEN countermeasure IS NOT NULL AND TRIM(countermeasure) != '' AND TRIM(countermeasure) != 'ー' THEN 1 ELSE 0 END) AS cm_policy_ok,
        SUM(CASE WHEN
            (process_stage IS NOT NULL AND TRIM(process_stage) != '' AND TRIM(process_stage) != 'ー') AND
            (phenomenon IS NOT NULL AND TRIM(phenomenon) != '' AND TRIM(phenomenon) != 'ー') AND
            (error_code_i IS NOT NULL AND TRIM(error_code_i) != '' AND TRIM(error_code_i) != 'ー') AND
            (cause IS NOT NULL AND TRIM(cause) != '' AND TRIM(cause) != 'ー') AND
            (countermeasure IS NOT NULL AND TRIM(countermeasure) != '' AND TRIM(countermeasure) != 'ー')
        THEN 1 ELSE 0 END) AS all5_strict_code_ok,
        SUM(CASE WHEN
            (process_stage IS NOT NULL AND TRIM(process_stage) != '' AND TRIM(process_stage) != 'ー') AND
            (phenomenon IS NOT NULL AND TRIM(phenomenon) != '' AND TRIM(phenomenon) != 'ー') AND
            (COALESCE(error_code_i, error_code_h, error_name) IS NOT NULL AND TRIM(COALESCE(error_code_i, error_code_h, error_name)) != '' AND TRIM(COALESCE(error_code_i, error_code_h, error_name)) != 'ー') AND
            (cause IS NOT NULL AND TRIM(cause) != '' AND TRIM(cause) != 'ー') AND
            (countermeasure IS NOT NULL AND TRIM(countermeasure) != '' AND TRIM(countermeasure) != 'ー')
        THEN 1 ELSE 0 END) AS all5_policy_ok
    FROM error_cases
    WHERE {where}
    """
    cur.execute(sql)
    return dict(cur.fetchone())


def run_backfill(execute_write: bool = True) -> dict[str, Any]:
    """Execute dry-run and actual backfill of Kaizo fields."""
    db_file = WORK_DB
    assert db_file.exists(), f"Target database not found: {db_file}"
    initial_sha = sha256_file(db_file)
    print(f"Target DB: {db_file} (initial SHA-256: {initial_sha})")

    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Integrity check before starting
    cur.execute("PRAGMA integrity_check")
    ic_before = cur.fetchone()[0]
    assert ic_before == "ok", f"Integrity check failed before start: {ic_before}"

    # Baseline before
    b1_before = measure_policy(cur, "batch_id = 1")
    new_before = measure_policy(cur, "batch_id > 1")
    all_before = measure_policy(cur, "1=1")

    print("\n--- BASELINE BEFORE BACKFILL ---")
    print(f"Batch 1:  total={b1_before['total']:,}, cm_ok={b1_before['cm_policy_ok']:,}, all5_policy={b1_before['all5_policy_ok']:,} ({b1_before['all5_policy_ok']/b1_before['total']*100:.2f}%)")
    print(f"Net New:  total={new_before['total']:,}, cm_ok={new_before['cm_policy_ok']:,}, all5_policy={new_before['all5_policy_ok']:,} ({new_before['all5_policy_ok']/new_before['total']*100:.2f}%)")
    print(f"Unified:  total={all_before['total']:,}, cm_ok={all_before['cm_policy_ok']:,}, all5_policy={all_before['all5_policy_ok']:,} ({all_before['all5_policy_ok']/all_before['total']*100:.2f}%)")

    # Fetch batch 1 empty countermeasure cases
    cur.execute(
        """
        SELECT id, no_dvd, occurred_at, machine_type, line, process_stage, phenomenon, countermeasure, raw_json
        FROM error_cases
        WHERE batch_id = 1
        ORDER BY id
        """
    )
    b1_rows = cur.fetchall()
    empty_b1 = [r for r in b1_rows if is_dash_or_empty(r["countermeasure"])]
    print(f"\nTotal Batch 1 cases: {len(b1_rows):,}")
    print(f"Batch 1 cases with empty countermeasure: {len(empty_b1):,}")

    # 25 Standard workbooks from Step 0 reconciliation
    workbooks_to_process = [
        {"rel_path": "FY2027上期機器製造 品質状況 Tình hình chất lượng chế tạo máy FY2027 (6 tháng đầu năm).xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "27col", "year": "2026", "tag": "FY27H1"},
        {"rel_path": "FY2027下期機器製造 品質状況 Tình hình chất lượng chế tạo máy FY2027 (6 tháng cuối năm).xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "27col", "year": "2026", "tag": "FY27H2"},
        {"rel_path": "FY2027電工製造 品質状況 Tình hình chất lượng chế tạo công cụ điện FY2027.xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "27col", "year": "2026", "tag": "FY27ET"},
        {"rel_path": "old/2022年機器製造 品質状況 Tình hình chất lượng chế tạo máy 2022(10～）.xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "32col", "year": "2022", "tag": "FY22H2"},
        {"rel_path": "old/2023年上期機器製造 品質状況 Tình hình chất lượng chế tạo máy 2023(6 tháng đầu năm).xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "32col", "year": "2023", "tag": "FY23H1"},
        {"rel_path": "old/2023年下期機器製造 品質状況Tình hình chất lượng chế tạo máy 2023(6 tháng cuối năm).xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "32col", "year": "2023", "tag": "FY23H2"},
        {"rel_path": "old/2024年4月～6月機器製造 品質状況 Tình hình chất lượng chế tạo máy 2024(quý 1).xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "27col_2024", "year": "2024", "tag": "FY24Q1"},
        {"rel_path": "old/2024年7月～9月機器製造 品質状況 Tình hình chất lượng chế tạo máy 2024(quý 2).xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "27col_2024", "year": "2024", "tag": "FY24Q2"},
        {"rel_path": "old/2024年10月～12月機器製造 品質状況 Tình hình chất lượng chế tạo máy 2024(quý 3).xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "27col_2024", "year": "2024", "tag": "FY24Q3"},
        {"rel_path": "old/2025年1月～3月機器製造 品質状況 Tình hình chất lượng chế tạo máy 2024(quý 4).xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "26col", "year": "2025", "tag": "FY24Q4"},
        {"rel_path": "old/2024年電工製造 品質状況 Tình hình chất lượng chế tạo KIT 2024.xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "27col_2024", "year": "2024", "tag": "FY24KIT"},
        {"rel_path": "old/FY2026上期機器製造 品質状況 Tình hình chất lượng chế tạo máy FY2026 (6 tháng đầu năm).xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "26col", "year": "2025", "tag": "FY26H1"},
        {"rel_path": "old/FY2026下期機器製造 品質状況 Tình hình chất lượng chế tạo máy FY2026 (6 tháng cuối năm).xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "27col", "year": "2025", "tag": "FY26H2"},
        {"rel_path": "old/FY2026電工製造 品質状況 Tình hình chất lượng chế tạo công cụ điện FY2026.xlsx", "sheet": "Sheet1", "parser": "standard", "layout": "27col", "year": "2025", "tag": "FY26ET"},
        {"rel_path": "old/Báo cáo chất lượng hàng ngày (Quan trọng)- 2019　MOI.xlsx", "sheet": "TOTAL", "parser": "legacy", "layout": "gen4_2019", "year": "2019", "tag": "D2019"},
        {"rel_path": "old/Báo cáo chất lượng hàng ngày KDTPS 2020.xlsx", "sheet": "TOTAL", "parser": "legacy", "layout": "gen4_2020", "year": "2020", "tag": "D2020"},
        {"rel_path": "old/Báo cáo chất lượng hàng ngày (Quan trọng) 日常不具合まとめ 2021.xlsx", "sheet": "TOTAL", "parser": "legacy", "layout": "gen4_2021_2022", "year": "2021", "tag": "D2021"},
        {"rel_path": "old/Báo cáo chất lượng hàng ngày (Quan trọng) 日常不具合まとめ 2022.xlsx", "sheet": "Sheet1", "parser": "legacy", "layout": "gen4_2021_2022", "year": "2022", "tag": "D2022"},
        {"rel_path": "old/2015/Loi ps trong cong doan ALL LINE 01.2015~12.2015.xls", "sheet": "TOTAL", "parser": "legacy", "layout": "gen2_2015", "year": "2015", "tag": "Y2015"},
        {"rel_path": "old/2016/Báo cáo chất lượng hàng ngày (Quan trọng)- 2016.xlsx", "sheet": "TOTAL", "parser": "legacy", "layout": "gen3_2016_2018", "year": "2016", "tag": "Y2016"},
        {"rel_path": "old/2017/Báo cáo chất lượng hàng ngày (Quan trọng)- 2017.xlsx", "sheet": "TOTAL (2)", "parser": "legacy", "layout": "gen3_2016_2018", "year": "2017", "tag": "Y2017"},
        {"rel_path": "old/2018/Báo cáo chất lượng hàng ngày (Quan trọng)- 2018.xlsx", "sheet": "TOTAL (2)", "parser": "legacy", "layout": "gen3_2016_2018", "year": "2018", "tag": "Y2018"},
        {"rel_path": "old/2019/Báo cáo chất lượng hàng ngày (Quan trọng)- 2019　MOI.xlsx", "sheet": "TOTAL", "parser": "legacy", "layout": "gen4_2019", "year": "2019", "tag": "Y2019"},
        {"rel_path": "old/2020/Báo cáo chất lượng hàng ngày KDTPS.xlsx", "sheet": "TOTAL", "parser": "legacy", "layout": "gen4_2020", "year": "2020", "tag": "Y2020"},
        {"rel_path": "old/2021/Báo cáo chất lượng hàng ngày (Quan trọng) 日常不具合まとめ 2021.xlsx", "sheet": "TOTAL", "parser": "legacy", "layout": "gen4_2021_2022", "year": "2021", "tag": "Y2021"},
    ]

    source_by_key: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()

    print("Parsing 25 standard workbooks ...")
    for wb_spec in workbooks_to_process:
        rel_path = wb_spec["rel_path"]
        fpath = EXTRACTED_DIR / rel_path
        sheet_name = wb_spec["sheet"]
        parser_type = wb_spec["parser"]
        layout = wb_spec["layout"]
        default_year = wb_spec["year"]

        raw_rows = []
        if fpath.suffix.lower() == ".xls":
            book = xlrd.open_workbook(str(fpath), on_demand=True)
            sh = book.sheet_by_name(sheet_name)
            for r_idx in range(sh.nrows):
                vals = tuple(sh.cell_value(r_idx, c_idx) for c_idx in range(min(sh.ncols, 35)))
                raw_rows.append((r_idx + 1, vals))
            book.release_resources()
        else:
            wb = openpyxl.load_workbook(str(fpath), read_only=True, data_only=True)
            ws = wb[sheet_name]
            for r_idx, row_vals in enumerate(ws.iter_rows(max_col=35, values_only=True), start=1):
                raw_rows.append((r_idx, row_vals))
            wb.close()

        for src_row_num, r_vals in raw_rows:
            if parser_type == "standard":
                parsed = parse_standard_kdtps_row(r_vals, layout, default_year=default_year, now_iso=now_iso)
            else:
                parsed = parse_legacy_daily_row(r_vals, layout, int(default_year), now_iso=now_iso)
            if not parsed:
                continue

            dkey = make_dedup_key(
                parsed["occurred_at"],
                parsed["machine_type"],
                parsed["line"],
                parsed["process_stage"],
                parsed["phenomenon"],
            )
            raw_kaizo = parsed.get("countermeasure_strict")
            cm_policy = parsed.get("countermeasure")
            source_by_key[dkey].append(
                {
                    "source_file": rel_path,
                    "source_row": src_row_num,
                    "kaizo_strict": raw_kaizo,
                    "cm_policy": cm_policy,
                }
            )

    se_lap = []
    khop_nguon_trong = []
    khong_khop = []

    for r in empty_b1:
        k = make_dedup_key(
            r["occurred_at"],
            r["machine_type"],
            r["line"],
            r["process_stage"],
            r["phenomenon"],
        )
        if k not in source_by_key:
            khong_khop.append((r, k))
        else:
            sources = source_by_key[k]
            best_kaizo = None
            best_src = None
            for s in sources:
                kz = s["kaizo_strict"]
                if not is_dash_or_empty(kz):
                    best_kaizo = kz
                    best_src = s
                    break
            if not best_kaizo:
                for s in sources:
                    kz = s["cm_policy"]
                    if not is_dash_or_empty(kz):
                        best_kaizo = kz
                        best_src = s
                        break

            if best_kaizo and not is_dash_or_empty(best_kaizo):
                se_lap.append((r, best_kaizo, best_src))
            else:
                khop_nguon_trong.append((r, k, sources))

    dry_run_count = len(se_lap)
    print(f"\n--- DRY-RUN CLASSIFICATION (1,900 CASES) ---")
    print(f"1. So ca se lap (matched and source has Kaizo):        {len(se_lap):,}")
    print(f"2. So ca khop nhung nguon trong (matched, source empty): {len(khop_nguon_trong):,}")
    print(f"3. So ca khong khop (unmatched):                         {len(khong_khop):,}")
    assert len(se_lap) + len(khop_nguon_trong) + len(khong_khop) == len(empty_b1)

    if not execute_write:
        conn.close()
        return {
            "se_lap": len(se_lap),
            "khop_nguon_trong": len(khop_nguon_trong),
            "khong_khop": len(khong_khop),
        }

    # Perform actual write
    print("\n--- PERFORMING ACTUAL WRITE ---")
    updated_count = 0
    for r, kz, src in se_lap:
        cur.execute("SELECT countermeasure, raw_json FROM error_cases WHERE id = ?", (r["id"],))
        row_now = cur.fetchone()
        curr_cm = row_now["countermeasure"]
        curr_raw_str = row_now["raw_json"]

        # Invariant: ONLY fill if empty
        if not is_dash_or_empty(curr_cm):
            raise RuntimeError(f"ABORT: ID {r['id']} already has countermeasure {curr_cm!r}! Invariant violated.")

        curr_raw = json.loads(curr_raw_str or "{}")
        curr_raw["AB"] = kz
        bf = curr_raw.get("_backfill", {})
        bf["fix"] = {
            "value": kz,
            "source": f"{src['source_file']}:{src['source_row']}",
            "marker": "backfill_kaizo_standard",
            "rule": "DESKTOP-KDTPS-BACKFILL-KAIZO-HOME",
            "line": src["source_row"],
            "chars": len(kz),
            "at": now_iso,
        }
        curr_raw["_backfill"] = bf
        new_raw_str = json.dumps(curr_raw, ensure_ascii=False)

        cur.execute(
            """
            UPDATE error_cases
            SET countermeasure = ?, raw_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (kz, new_raw_str, now_iso, r["id"]),
        )
        updated_count += 1

    print(f"Total rows actually updated in DB: {updated_count:,}")
    if updated_count != dry_run_count:
        conn.rollback()
        conn.close()
        raise RuntimeError(f"ABORT: Actual write count ({updated_count}) does NOT match dry-run count ({dry_run_count})!")

    # Commit changes
    conn.commit()
    print("Database transaction successfully committed!")

    # Verify integrity after commit
    cur.execute("PRAGMA integrity_check")
    ic_after = cur.fetchone()[0]
    print(f"PRAGMA integrity_check after write: {ic_after}")
    assert ic_after == "ok", f"Integrity check failed after write: {ic_after}"

    # Remeasure completeness after write
    b1_after = measure_policy(cur, "batch_id = 1")
    new_after = measure_policy(cur, "batch_id > 1")
    all_after = measure_policy(cur, "1=1")
    conn.close()

    final_sha = sha256_file(db_file)
    print(f"\nTarget DB final SHA-256: {final_sha}")

    print("\n--- METRICS COMPARISON (BEFORE vs AFTER) ---")
    print(f"Batch 1:")
    print(f"  All 5 Policy: {b1_before['all5_policy_ok']:,} ({b1_before['all5_policy_ok']/b1_before['total']*100:.2f}%) -> {b1_after['all5_policy_ok']:,} ({b1_after['all5_policy_ok']/b1_after['total']*100:.2f}%) [+{b1_after['all5_policy_ok'] - b1_before['all5_policy_ok']:,}]")
    print(f"Unified (30,075 cases):")
    print(f"  All 5 Policy: {all_before['all5_policy_ok']:,} ({all_before['all5_policy_ok']/all_before['total']*100:.2f}%) -> {all_after['all5_policy_ok']:,} ({all_after['all5_policy_ok']/all_after['total']*100:.2f}%) [+{all_after['all5_policy_ok'] - all_before['all5_policy_ok']:,}]")

    summary = {
        "executed_at": now_iso,
        "database_path": str(db_file),
        "initial_sha256": initial_sha,
        "final_sha256": final_sha,
        "integrity_check": ic_after,
        "counts": {
            "batch1_total": len(b1_rows),
            "batch1_empty_cm_before": len(empty_b1),
            "se_lap": dry_run_count,
            "actual_updated": updated_count,
            "khop_nguon_trong": len(khop_nguon_trong),
            "khong_khop": len(khong_khop),
        },
        "metrics_before": {
            "batch1": b1_before,
            "net_new": new_before,
            "unified": all_before,
        },
        "metrics_after": {
            "batch1": b1_after,
            "net_new": new_after,
            "unified": all_after,
        },
        "unmatched_details": [
            {
                "id": r["id"],
                "no_dvd": r["no_dvd"],
                "occurred_at": r["occurred_at"],
                "machine_type": r["machine_type"],
                "line": r["line"],
                "process_stage": r["process_stage"],
                "phenomenon": r["phenomenon"],
            }
            for r, k in khong_khop
        ],
    }

    out_file = BASE_DIR / "backfill_kaizo_results.json"
    out_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Summary written to {out_file}")
    return summary


if __name__ == "__main__":
    run_backfill(execute_write=True)
