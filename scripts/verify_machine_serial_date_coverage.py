# -*- coding: utf-8 -*-
"""Verification and Data Inventory Script for Ticket DESKTOP-HOME-MACHINE-SERIAL-DATE-COVERAGE.

Audits data coverage for machine name/model, serial number, occurrence date, and ticket number
across the 30,075 reconciled error cases DB (error_cases_reconciled.db) and the document library (library.sqlite).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = Path(r"C:\tmp\kdtps_standard\error_cases_reconciled.db")
LIB_PATH = Path(r"C:\AIOS_workspace_chat_rag_v2_production\bge_m3_hybrid\collections\tri_thuc\library.sqlite")
OUT_JSON = Path(r"D:\Sandbox\aios-dieu-phoi-desktop\hop-thu\lan-desktop\ket-qua\verification_machine_serial_date_coverage.json")

NA_VALUES = frozenset({"", "-", "—", "ー", "None", "null", "nan", None})


def is_valid(val: Any) -> bool:
    if val is None:
        return False
    s = str(val).strip()
    return bool(s and s not in NA_VALUES)


def audit_schema_and_coverage() -> Dict[str, Any]:
    assert DB_PATH.is_file(), f"Missing DB at {DB_PATH}"
    con = sqlite3.connect(f"file:{DB_PATH.resolve().as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    total_rows = cur.execute("SELECT COUNT(*) FROM error_cases").fetchone()[0]
    assert total_rows == 30075, f"Expected 30075 cases, got {total_rows}"

    cols_info = cur.execute("PRAGMA table_info(error_cases)").fetchall()
    cols_map = {r["name"]: r["type"] for r in cols_info}

    # Target concepts
    schema_status = {
        "ten_may_model": "machine_type" in cols_map,
        "so_serial_may": any(c in cols_map for c in ("serial", "serial_no", "so_may", "so_serial")),
        "ngay_phat_sinh": "occurred_at" in cols_map,
        "so_phieu": "no_dvd" in cols_map,
    }

    # Coverage counting across all 30075 rows
    rows = cur.execute("SELECT id, batch_id, no_dvd, machine_type, occurred_at, raw_json FROM error_cases").fetchall()

    cnt_machine = 0
    cnt_dvd = 0
    cnt_date = 0
    cnt_serial_g = 0

    batch_counts: Dict[int, Dict[str, int]] = {}

    for r in rows:
        bid = r["batch_id"]
        if bid not in batch_counts:
            batch_counts[bid] = {"total": 0, "machine": 0, "dvd": 0, "date": 0, "serial_g": 0}
        batch_counts[bid]["total"] += 1

        if is_valid(r["machine_type"]):
            cnt_machine += 1
            batch_counts[bid]["machine"] += 1

        if is_valid(r["no_dvd"]):
            cnt_dvd += 1
            batch_counts[bid]["dvd"] += 1

        if is_valid(r["occurred_at"]):
            cnt_date += 1
            batch_counts[bid]["date"] += 1

        rj = json.loads(r["raw_json"] or "{}")
        g = rj.get("G")
        if is_valid(g):
            cnt_serial_g += 1
            batch_counts[bid]["serial_g"] += 1

    batches_info = cur.execute(
        "SELECT id, source_file, sheet_name, sheet_type, rows_imported FROM import_batches ORDER BY id"
    ).fetchall()

    batch_details = []
    for b in batches_info:
        bid = b["id"]
        bc = batch_counts.get(bid, {"total": 0, "machine": 0, "dvd": 0, "date": 0, "serial_g": 0})
        batch_details.append({
            "batch_id": bid,
            "source_file": b["source_file"],
            "sheet_name": b["sheet_name"],
            "sheet_type": b["sheet_type"],
            "rows_imported": b["rows_imported"],
            "actual_rows": bc["total"],
            "machine_count": bc["machine"],
            "dvd_count": bc["dvd"],
            "date_count": bc["date"],
            "serial_g_count": bc["serial_g"],
            "serial_g_pct": round((bc["serial_g"] / bc["total"] * 100), 2) if bc["total"] else 0.0,
        })

    con.close()

    return {
        "total_cases": total_rows,
        "schema_columns": list(cols_map.keys()),
        "schema_status": schema_status,
        "coverage": {
            "so_phieu_no_dvd": {"count": cnt_dvd, "pct": round(cnt_dvd / total_rows * 100, 2)},
            "ngay_phat_sinh_occurred_at": {"count": cnt_date, "pct": round(cnt_date / total_rows * 100, 2)},
            "ten_may_machine_type": {"count": cnt_machine, "pct": round(cnt_machine / total_rows * 100, 2)},
            "so_serial_raw_json_g": {"count": cnt_serial_g, "pct": round(cnt_serial_g / total_rows * 100, 2)},
            "so_serial_in_schema": {"count": 0, "pct": 0.0},
        },
        "batch_details": batch_details,
    }


def audit_machine_queries() -> Dict[str, Any]:
    con = sqlite3.connect(f"file:{DB_PATH.resolve().as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    queries = {
        "iris_exact": {
            "name": "Iris (chính xác tuyệt đối)",
            "sql": "SELECT id, no_dvd, machine_type, occurred_at, raw_json FROM error_cases WHERE TRIM(machine_type) = 'Iris'",
        },
        "iris_substring": {
            "name": "Iris (chứa chuỗi con '%Iris%')",
            "sql": "SELECT id, no_dvd, machine_type, occurred_at, raw_json FROM error_cases WHERE machine_type LIKE '%Iris%'",
        },
        "6thnext_exact_nospace": {
            "name": "6thNext (chính xác không dấu cách)",
            "sql": "SELECT id, no_dvd, machine_type, occurred_at, raw_json FROM error_cases WHERE TRIM(machine_type) = '6thNext'",
        },
        "6thnext_exact_space": {
            "name": "6th Next (chính xác có dấu cách)",
            "sql": "SELECT id, no_dvd, machine_type, occurred_at, raw_json FROM error_cases WHERE TRIM(machine_type) = '6th Next'",
        },
        "6thnext_normalized": {
            "name": "6thNext / 6th Next (chuẩn hóa loại bỏ khoảng trắng)",
            "sql": "SELECT id, no_dvd, machine_type, occurred_at, raw_json FROM error_cases WHERE REPLACE(machine_type, ' ', '') LIKE '%6thNext%'",
        },
    }

    results = {}
    for qkey, qdata in queries.items():
        rows = cur.execute(qdata["sql"]).fetchall()
        cnt = len(rows)
        has_dvd = sum(1 for r in rows if is_valid(r["no_dvd"]))
        has_date = sum(1 for r in rows if is_valid(r["occurred_at"]))
        has_g = 0
        samples = []

        for r in rows:
            rj = json.loads(r["raw_json"] or "{}")
            g = rj.get("G")
            if is_valid(g):
                has_g += 1
                if len(samples) < 5:
                    samples.append({
                        "id": r["id"],
                        "no_dvd": r["no_dvd"],
                        "machine_type": r["machine_type"],
                        "occurred_at": r["occurred_at"],
                        "serial_raw_g": str(g).replace("\n", " | "),
                        "phenomenon": str(rj.get("I") or "")[:80],
                    })

        results[qkey] = {
            "name": qdata["name"],
            "sql": qdata["sql"],
            "total_cases": cnt,
            "has_dvd_count": has_dvd,
            "has_dvd_pct": round(has_dvd / cnt * 100, 2) if cnt else 0.0,
            "has_date_count": has_date,
            "has_date_pct": round(has_date / cnt * 100, 2) if cnt else 0.0,
            "has_serial_count": has_g,
            "has_serial_pct": round(has_g / cnt * 100, 2) if cnt else 0.0,
            "sample_rows": samples,
        }

    con.close()
    return results


def audit_document_library() -> Dict[str, Any]:
    assert LIB_PATH.is_file(), f"Missing library DB at {LIB_PATH}"
    con = sqlite3.connect(f"file:{LIB_PATH.resolve().as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    total_chunks = cur.execute("SELECT count(*) FROM chunks").fetchone()[0]

    # Keyword frequencies
    keywords = ["Serial", "Số máy", "機番", "Ngày phát sinh", "発生日", "Iris", "6th Next"]
    kw_counts = {}
    for kw in keywords:
        c = cur.execute("SELECT count(*) FROM chunks WHERE text LIKE ?", (f"%{kw}%",)).fetchone()[0]
        kw_counts[kw] = c

    # Test specific real serial numbers from DB cases
    test_serials = ["WD72Z12772", "3V2XM1930", "WD85X36474", "C9P1056J6209", "R4P3123438"]
    serial_findings = []
    for s in test_serials:
        matched = cur.execute(
            "SELECT chunk_id, source_name, text FROM chunks WHERE text LIKE ? LIMIT 3",
            (f"%{s}%",)
        ).fetchall()
        serial_findings.append({
            "serial": s,
            "match_count": len(matched),
            "sources": list({m["source_name"] for m in matched}),
        })

    con.close()

    return {
        "library_path": str(LIB_PATH),
        "total_chunks": total_chunks,
        "keyword_counts": kw_counts,
        "serial_in_docs_findings": serial_findings,
    }


def main() -> int:
    print("=== CHẠY KIỂM TOÁN VÉ DESKTOP-HOME-MACHINE-SERIAL-DATE-COVERAGE ===")
    schema_cov = audit_schema_and_coverage()
    print(f"Tổng số ca: {schema_cov['total_cases']}")
    print(f"Số phiếu (no_dvd): {schema_cov['coverage']['so_phieu_no_dvd']}")
    print(f"Ngày phát sinh (occurred_at): {schema_cov['coverage']['ngay_phat_sinh_occurred_at']}")
    print(f"Tên máy (machine_type): {schema_cov['coverage']['ten_may_machine_type']}")
    print(f"Số serial trong Schema: {schema_cov['coverage']['so_serial_in_schema']}")
    print(f"Số serial trong raw_json['G']: {schema_cov['coverage']['so_serial_raw_json_g']}")

    machine_q = audit_machine_queries()
    print("\n=== KẾT QUẢ TRUY VẤN IRIS & 6THNEXT ===")
    for k, v in machine_q.items():
        print(f"- {v['name']}: {v['total_cases']} ca | Phiếu: {v['has_dvd_pct']}% | Ngày: {v['has_date_pct']}% | Serial: {v['has_serial_pct']}%")

    doc_lib = audit_document_library()
    print("\n=== KHO TÀI LIỆU VĂN BẢN ===")
    print(f"Tổng số mảnh chunks: {doc_lib['total_chunks']}")
    print(f"Tần suất từ khóa: {doc_lib['keyword_counts']}")
    print(f"Kiểm tra serial thực tế: {doc_lib['serial_in_docs_findings']}")

    full_payload = {
        "ticket": "DESKTOP-HOME-MACHINE-SERIAL-DATE-COVERAGE",
        "schema_and_coverage": schema_cov,
        "machine_queries": machine_q,
        "document_library": doc_lib,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(full_payload, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Đã ghi kết quả kiểm chứng vào {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
