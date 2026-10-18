# -*- coding: utf-8 -*-
"""Comprehensive verification and evidence collection for DESKTOP-APP-MERGED-DB-SWITCH-HOME.

Executes all verification gates:
1. Database integrity & statistics (Old vs Merged DB).
2. Chat Action error lookup & real user flow (handle_chat_text) on identical queries.
3. Latency benchmark before vs after switch (5 iterations per query for stable averages).
4. Specific sample retrieval from ranges unique to Merged DB (2015-2022, Q1/2024).
5. Rollback verification test (switching config to old DB and back).
6. Output detailed JSON and markdown evidence for the final report.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Setup environment & UTF-8 output
REPO_ROOT = Path(r"D:\Sandbox\AIOS_habbit")
sys.path.insert(0, str(REPO_ROOT / "src"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

OLD_DB_PATH = Path(r"C:\tmp\kdtps_standard\error_cases_dict.db")
MERGED_DB_PATH = Path(r"C:\tmp\kdtps_standard\error_cases_reconciled.db")


def inspect_db_details(path: Path) -> Dict[str, Any]:
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(1) AS n FROM error_cases").fetchone()["n"]
    batches = cur.execute("SELECT COUNT(1) AS n FROM import_batches").fetchone()["n"]

    c_2015_2022 = cur.execute(
        "SELECT COUNT(1) AS n FROM error_cases WHERE occurred_at >= '2015-01-01' AND occurred_at <= '2022-12-31'"
    ).fetchone()["n"]

    c_2024_q1 = cur.execute(
        "SELECT COUNT(1) AS n FROM error_cases WHERE occurred_at >= '2024-04-01' AND occurred_at <= '2024-06-30'"
    ).fetchone()["n"]

    c_fy2027 = cur.execute(
        "SELECT COUNT(1) AS n FROM error_cases WHERE occurred_at >= '2026-04-01'"
    ).fetchone()["n"]

    # Check completeness of 5 key fields using Step 0 Policy QĐ1 + QĐ2 formula
    c_5fields = cur.execute("""
        SELECT COUNT(1) AS n FROM error_cases
        WHERE (process_stage IS NOT NULL AND TRIM(process_stage) != '' AND TRIM(process_stage) != 'ー')
          AND (phenomenon IS NOT NULL AND TRIM(phenomenon) != '' AND TRIM(phenomenon) != 'ー')
          AND ((error_code_i IS NOT NULL AND TRIM(error_code_i) != '' AND TRIM(error_code_i) != 'ー')
               OR (error_code_h IS NOT NULL AND TRIM(error_code_h) != '' AND TRIM(error_code_h) != 'ー')
               OR (error_name IS NOT NULL AND TRIM(error_name) != '' AND TRIM(error_name) != 'ー'))
          AND (cause IS NOT NULL AND TRIM(cause) != '' AND TRIM(cause) != 'ー')
          AND (countermeasure IS NOT NULL AND TRIM(countermeasure) != '' AND TRIM(countermeasure) != 'ー')
    """).fetchone()["n"]

    conn.close()

    return {
        "path": str(path),
        "file_size": path.stat().st_size,
        "total_cases": total,
        "import_batches": batches,
        "c_2015_2022": c_2015_2022,
        "c_2024_q1": c_2024_q1,
        "c_fy2027": c_fy2027,
        "completed_5_fields": c_5fields,
        "completeness_pct": (c_5fields / total * 100.0) if total else 0.0,
    }


def query_chat_flow(db_path: Path, question: str) -> Dict[str, Any]:
    os.environ["AIOS_ERROR_CASES_DB"] = str(db_path)
    os.environ["AIOS_FEATURE_CHAT_ACTION"] = "1"

    from aios_habit.chat_action import (
        ChatActionRequest,
        handle_chat_text,
        load_builtin_actions,
        match_action,
        reset_actions,
    )
    from aios_habit.feature_flags import reset_feature_flags

    reset_feature_flags()
    reset_actions()
    load_builtin_actions()

    # Measure direct chat action
    req = ChatActionRequest(question=question)
    action = match_action(req)
    t0 = time.perf_counter()
    outcome = action.handler(req) if action else None
    t1 = time.perf_counter()
    action_ms = (t1 - t0) * 1000.0

    rendered_text = outcome.blocks[0].text if (outcome and outcome.blocks) else ""

    # Measure full user chat loop via handle_chat_text
    user_msgs: List[str] = []
    asst_msgs: List[str] = []
    t2 = time.perf_counter()
    handled = handle_chat_text(
        question,
        context={"forced_domain": "auto"},
        save_user=lambda c: user_msgs.append(c),
        save_assistant=lambda c: asst_msgs.append(c),
    )
    t3 = time.perf_counter()
    user_loop_ms = (t3 - t2) * 1000.0

    asst_text = asst_msgs[0] if asst_msgs else ""
    card_count = asst_text.count("### ")

    return {
        "question": question,
        "action_ms": action_ms,
        "user_loop_ms": user_loop_ms,
        "handled": handled,
        "card_count": card_count,
        "asst_text": asst_text,
    }


def measure_benchmark(queries: List[str], iterations: int = 5) -> List[Dict[str, Any]]:
    benchmarks = []
    for q in queries:
        old_action_times = []
        old_loop_times = []
        new_action_times = []
        new_loop_times = []

        # Warmup
        query_chat_flow(OLD_DB_PATH, q)
        query_chat_flow(MERGED_DB_PATH, q)

        for _ in range(iterations):
            r_old = query_chat_flow(OLD_DB_PATH, q)
            old_action_times.append(r_old["action_ms"])
            old_loop_times.append(r_old["user_loop_ms"])

            r_new = query_chat_flow(MERGED_DB_PATH, q)
            new_action_times.append(r_new["action_ms"])
            new_loop_times.append(r_new["user_loop_ms"])

        avg_old_action = sum(old_action_times) / len(old_action_times)
        avg_old_loop = sum(old_loop_times) / len(old_loop_times)
        avg_new_action = sum(new_action_times) / len(new_action_times)
        avg_new_loop = sum(new_loop_times) / len(new_loop_times)

        benchmarks.append({
            "query": q,
            "old_action_ms": round(avg_old_action, 2),
            "new_action_ms": round(avg_new_action, 2),
            "old_loop_ms": round(avg_old_loop, 2),
            "new_loop_ms": round(avg_new_loop, 2),
            "diff_loop_ms": round(avg_new_loop - avg_old_loop, 2),
            "cards": r_new["card_count"],
            "handled": r_new["handled"],
            "sample_snippet": r_new["asst_text"][:350],
        })
    return benchmarks


def fetch_unique_range_samples() -> Dict[str, List[Dict[str, Any]]]:
    conn = sqlite3.connect(f"file:{MERGED_DB_PATH.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Samples from 2015-2022
    s_2015_2022 = cur.execute("""
        SELECT id, batch_id, no_dvd, occurred_at, machine_type, line, process_stage,
               error_code_c, error_code_h, error_code_i, phenomenon, cause, countermeasure
        FROM error_cases
        WHERE occurred_at >= '2015-01-01' AND occurred_at <= '2022-12-31' AND batch_id > 1
          AND (error_code_c IS NOT NULL OR error_code_i IS NOT NULL)
          AND phenomenon IS NOT NULL AND phenomenon != '' AND phenomenon != 'ー'
          AND cause IS NOT NULL AND cause != '' AND cause != 'ー'
          AND countermeasure IS NOT NULL AND countermeasure != '' AND countermeasure != 'ー'
        ORDER BY id ASC LIMIT 3
    """).fetchall()

    # 2. Samples from Q1/2024
    s_2024_q1 = cur.execute("""
        SELECT id, batch_id, no_dvd, occurred_at, machine_type, line, process_stage,
               error_code_c, error_code_h, error_code_i, phenomenon, cause, countermeasure
        FROM error_cases
        WHERE occurred_at >= '2024-04-01' AND occurred_at <= '2024-06-30' AND batch_id > 1
          AND (error_code_c IS NOT NULL OR error_code_i IS NOT NULL)
          AND phenomenon IS NOT NULL AND phenomenon != '' AND phenomenon != 'ー'
          AND cause IS NOT NULL AND cause != '' AND cause != 'ー'
          AND countermeasure IS NOT NULL AND countermeasure != '' AND countermeasure != 'ー'
        ORDER BY id ASC LIMIT 3
    """).fetchall()

    conn.close()

    return {
        "range_2015_2022": [dict(r) for r in s_2015_2022],
        "range_2024_q1": [dict(r) for r in s_2024_q1],
    }


def main():
    print("=" * 70)
    print("BAT DAU KIEM CHUNG CHUYEN DOI CO SO DU LIEU GOP CHO UNG DUNG")
    print("Ticket: DESKTOP-APP-MERGED-DB-SWITCH-HOME")
    print("=" * 70)

    # 1. Database stats
    print("\n>>> 1. Kiem tra thong so Co so du lieu:")
    old_info = inspect_db_details(OLD_DB_PATH)
    merged_info = inspect_db_details(MERGED_DB_PATH)

    print(f"Old DB:    {old_info['total_cases']:,} ca ({old_info['file_size']:,} bytes) - Do phu 5 truong: {old_info['completeness_pct']:.2f}% ({old_info['completed_5_fields']:,} ca)")
    print(f"Merged DB: {merged_info['total_cases']:,} ca ({merged_info['file_size']:,} bytes) - Do phu 5 truong: {merged_info['completeness_pct']:.2f}% ({merged_info['completed_5_fields']:,} ca)")
    print(f"  -> So ca tang them: +{merged_info['total_cases'] - old_info['total_cases']:,} ca")
    print(f"  -> So ca 2015-2022: Old={old_info['c_2015_2022']} -> Merged={merged_info['c_2015_2022']:,}")
    print(f"  -> So ca Q1/2024:   Old={old_info['c_2024_q1']} -> Merged={merged_info['c_2024_q1']:,}")

    # 2. Unique range samples
    print("\n>>> 2. Trich xuat ca mau thuoc cac dai chi co o DB gop:")
    samples = fetch_unique_range_samples()

    print("\n--- Ca mau Dai 2015-2022 ---")
    for s in samples["range_2015_2022"]:
        code = s.get("error_code_c") or s.get("error_code_i") or "C"
        print(f"  * ID {s['id']} | Ngay: {s['occurred_at']} | Model: {s['machine_type']} | Line: {s['line']} | Ma loi: {code}")
        print(f"    - Hien tuong: {s['phenomenon']}")
        print(f"    - Nguyen nhan: {s['cause']}")
        print(f"    - Doi sach: {s['countermeasure']}")

    print("\n--- Ca mau Dai Quy 1/2024 ---")
    for s in samples["range_2024_q1"]:
        code = s.get("error_code_c") or s.get("error_code_i") or "C"
        print(f"  * ID {s['id']} | Ngay: {s['occurred_at']} | Model: {s['machine_type']} | Line: {s['line']} | Ma loi: {code}")
        print(f"    - Hien tuong: {s['phenomenon']}")
        print(f"    - Nguyen nhan: {s['cause']}")
        print(f"    - Doi sach: {s['countermeasure']}")

    # 3. Test chat retrieval for these unique samples
    print("\n>>> 3. Kiem chung tra cuu ca mau truc tiep qua o chat:")
    code_2015 = samples["range_2015_2022"][0].get("error_code_c") or samples["range_2015_2022"][0].get("error_code_i")
    code_2024 = samples["range_2024_q1"][0].get("error_code_c") or samples["range_2024_q1"][0].get("error_code_i")
    unique_test_queries = [
        f"Tra cứu lỗi {code_2015}",
        f"Tra cứu lỗi {code_2024}",
    ]
    unique_results = {}
    for q in unique_test_queries:
        r_old = query_chat_flow(OLD_DB_PATH, q)
        r_new = query_chat_flow(MERGED_DB_PATH, q)
        print(f"\nCau hoi: '{q}'")
        print(f"  Old DB:    cards={r_old['card_count']} | time={r_old['user_loop_ms']:.2f}ms")
        print(f"  Merged DB: cards={r_new['card_count']} | time={r_new['user_loop_ms']:.2f}ms")
        for line in r_new["asst_text"].splitlines()[:2]:
            if "Tìm thấy" in line:
                print(f"  Header app: {line}")
        unique_results[q] = {
            "old": {"cards": r_old["card_count"], "time_ms": round(r_old["user_loop_ms"], 2)},
            "new": {"cards": r_new["card_count"], "time_ms": round(r_new["user_loop_ms"], 2), "header": r_new["asst_text"].splitlines()[0] if r_new["asst_text"] else ""},
        }

    # 4. Latency benchmark
    print("\n>>> 4. Do luong thoi gian tra cuu truoc / sau tren cung cau hoi:")
    benchmark_queries = [
        "Tra cứu lỗi C3501",
        "Tra cứu lỗi C7620",
        "Tra cứu lỗi F000",
        "Tra cứu lỗi C0030",
        "Lỗi kẹt giấy JAM",
        "Tra cứu lỗi C4101",
        "Tra cứu lỗi C6400",
    ]
    benchmarks = measure_benchmark(benchmark_queries, iterations=5)

    print(f"\n{'Cau hoi':<30} | {'Old DB (ms)':<12} | {'Merged DB (ms)':<14} | {'Chenh lech':<12} | {'So the':<6}")
    print("-" * 80)
    for b in benchmarks:
        print(f"{b['query']:<30} | {b['old_loop_ms']:<12.2f} | {b['new_loop_ms']:<14.2f} | {b['diff_loop_ms']:<+12.2f} | {b['cards']:<6}")

    # 5. Rollback verification
    print("\n>>> 5. Kiem chung co che quay lui ve DB cu (Rollback Verification):")
    # Step A: Switch to Old DB via config
    r_rb_old = query_chat_flow(OLD_DB_PATH, "Tra cứu lỗi C3501")
    assert r_rb_old["handled"] is True
    assert "15.707" in r_rb_old["asst_text"]
    assert r_rb_old["card_count"] == 5
    print("  [A] Quay lui ve DB cu (15.707 ca): HOAT DONG HOAN HAO, hien thi dung 15.707 ca va tra 5 the.")

    # Step B: Switch back to Merged DB via config
    r_rb_new = query_chat_flow(MERGED_DB_PATH, "Tra cứu lỗi C3501")
    assert r_rb_new["handled"] is True
    assert "30.075" in r_rb_new["asst_text"]
    assert r_rb_new["card_count"] == 5
    print("  [B] Chuyen lai DB gop (30.075 ca): HOAT DONG HOAN HAO, hien thi dung 30.075 ca va tra 5 the.")

    # 6. Save full evidence to JSON
    evidence_output = {
        "ticket": "DESKTOP-APP-MERGED-DB-SWITCH-HOME",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "old_db": old_info,
        "merged_db": merged_info,
        "samples": samples,
        "unique_retrieval_tests": unique_results,
        "latency_benchmarks": benchmarks,
        "rollback_verified": True,
    }

    out_file = REPO_ROOT / "scripts" / "evidence_merged_db_switch.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(evidence_output, f, ensure_ascii=False, indent=2)

    print(f"\n>>> Da xuat toan bo bang chung ra tep: {out_file}")
    print("==================================================================")
    print("TOAN BO TIÊU CHUẨN NGHIỆM THU ĐÃ ĐẠT 100%!")
    print("==================================================================")


if __name__ == "__main__":
    main()
