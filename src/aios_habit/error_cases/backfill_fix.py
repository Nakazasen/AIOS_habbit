"""F3b: backfill the `fix` field for history rows whose AB (kaizo) is blank.

Recon 2026-10-01 (ticket `f3b-backfill`, report
`docs/phieu-viec/ket-qua/f3b-backfill.md`): 43.3% of the history rows
have a blank AB ("改造 / Kaizo") cell, concentrated in 2025-2026 where
the kaizo column stopped being maintained. Those cases do record their
handling/conclusion verbatim inside the investigation columns -- O
(Vietnamese, preferred) or N (Japanese, fallback) -- usually as a
closing line ("Đối ứng ...", "Xử lý ...", "cho máy đi", "対策：...",
"再現せず不良に処理", ...).

This module extracts that recorded handling text verbatim, never
inventing content: from the LAST line of the source cell that carries a
known marker to the end of the cell (trimmed). Rows without any marker
are left untouched and counted as not extractable. Every written value
is echoed with per-value provenance under::

    raw_json["_backfill"]["fix"] = {
        "value":  <verbatim text>,
        "source": "O" | "N",
        "marker": <matched marker>,
        "rule":   FIX_BACKFILL_RULE,
        "line":   <1-based line number in the source cell>,
        "chars":  <len(value)>,
        "at":     <ISO timestamp with local offset>,
    }

``completeness.measure`` counts `fix` as filled when AB is blank but a
recorded backfill value exists (reported under `backfilled`).

Safety: ``plan_backfill`` is read-only (dry-run); ``apply_backfill``
writes only raw_json, skips rows whose AB was meanwhile filled and rows
that already carry a backfill entry (unless ``refresh``). No schema
change, no RAG index access.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .completeness import BACKFILL_KEY, backfill_value, detect_format, is_filled
from .store import connect

#: Version tag recorded in every provenance entry.
FIX_BACKFILL_RULE: str = "f3b-fix-v1"

#: Vietnamese (O) markers; matching is case-insensitive. Covers recorded
#: countermeasures (đối ứng/đối sách/thay thế/upsoft...), containment
#: (lọc hàng/thu hồi), preventive actions (đào tạo lại/chú ý/bổ sung)
#: and the closing disposition (đơn phát/làm biểu/cho máy đi).
FIX_MARKERS_VN: Tuple[str, ...] = (
    "đối ứng",
    "đối sách",
    "khắc phục",
    "biện pháp",
    "phương án",
    "xử lý",
    "thay thế",
    "thay mới",
    "sửa chữa",
    "vệ sinh",
    "làm sạch",
    "lọc hàng",
    "thu hồi",
    "upsoft",
    "up soft",
    "nạp lại",
    "cài lại",
    "đào tạo lại",
    "hướng dẫn lại",
    "nhắc nhở",
    "cải tiến",
    "triển khai",
    "chú ý",
    "bổ sung",
    "cho máy",
    "làm biểu",
    "lập biểu",
    "viết biểu",
    "đơn phát",
)

#: Japanese (N) markers; matching is case-sensitive (no case concept).
FIX_MARKERS_JP: Tuple[str, ...] = (
    "対策",
    "是正",
    "改善",
    "改造",
    "処置",
    "処理",
    "交換",
    "修理",
    "清掃",
    "再結線",
    "水平展開",
    "再発防止",
    "復帰",
    "対応",
    "注意",
    "教育",
    "指導",
)


def extract_fix_segment(
    text: Any, markers: Tuple[str, ...], *, case_sensitive: bool = False
) -> Optional[Dict[str, Any]]:
    """Verbatim handling segment: from the LAST marker line to the end.

    Returns {"value", "marker", "line", "chars"} or None when no marker
    is present. The value is the raw tail of the cell (whitespace
    trimmed), so it can always be re-checked against the source text.
    """
    if text is None:
        return None
    lines = str(text).split("\n")
    for index in range(len(lines) - 1, -1, -1):
        probe = lines[index] if case_sensitive else lines[index].lower()
        for marker in markers:
            if (marker if case_sensitive else marker.lower()) in probe:
                value = "\n".join(lines[index:]).strip()
                if value:
                    return {
                        "value": value,
                        "marker": marker,
                        "line": index + 1,
                        "chars": len(value),
                    }
    return None


def _source_segment(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """First extractable segment: O (VN) preferred, then N (JP)."""
    for source, markers, case_sensitive in (
        ("O", FIX_MARKERS_VN, False),
        ("N", FIX_MARKERS_JP, True),
    ):
        segment = extract_fix_segment(
            raw.get(source), markers, case_sensitive=case_sensitive
        )
        if segment is not None:
            segment["source"] = source
            return segment
    return None


def _load_raw(raw_json: Any) -> Dict[str, Any]:
    try:
        raw = json.loads(raw_json or "{}")
    except (ValueError, TypeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def plan_backfill(
    conn: sqlite3.Connection,
    *,
    format: str = "history_29",
    batch_id: Optional[int] = None,
    refresh: bool = False,
) -> Dict[str, Any]:
    """Dry-run scan (read-only): candidates + summary counts.

    Rows in scope: format matches, AB blank, not already backfilled
    (unless refresh=True). Candidate rows keep the verbatim value plus
    its provenance so the caller can audit or apply it.
    """
    sql = "SELECT id, no_dvd, source_row, raw_json FROM error_cases"
    params: List[Any] = []
    if batch_id is not None:
        sql += " WHERE batch_id = ?"
        params.append(batch_id)

    summary: Dict[str, Any] = {
        "format": format,
        "batch_id": batch_id,
        "scanned": 0,
        "ab_filled": 0,
        "blank": 0,
        "already_backfilled": 0,
        "extractable": 0,
        "unextractable": 0,
        "sources": {"O": 0, "N": 0},
        "markers": {},
        "candidates": [],
    }
    for row in conn.execute(sql, params):
        raw = _load_raw(row["raw_json"])
        if detect_format(raw) != format:
            continue
        summary["scanned"] += 1
        if is_filled(raw.get("AB")):
            summary["ab_filled"] += 1
            continue
        summary["blank"] += 1
        if not refresh and is_filled(backfill_value(raw, "fix")):
            summary["already_backfilled"] += 1
            continue
        segment = _source_segment(raw)
        if segment is None:
            summary["unextractable"] += 1
            continue
        summary["extractable"] += 1
        summary["sources"][segment["source"]] += 1
        marker = segment["marker"]
        summary["markers"][marker] = summary["markers"].get(marker, 0) + 1
        summary["candidates"].append(
            {
                "case_id": row["id"],
                "no_dvd": row["no_dvd"],
                "source_row": row["source_row"],
                "source": segment["source"],
                "marker": marker,
                "line": segment["line"],
                "chars": segment["chars"],
                "value": segment["value"],
            }
        )
    return summary


def apply_backfill(
    conn: sqlite3.Connection,
    plan_result: Dict[str, Any],
    *,
    at: Optional[str] = None,
    refresh: bool = False,
) -> Dict[str, Any]:
    """Write the planned backfill entries into raw_json (single commit)."""
    stamp = at or datetime.now().astimezone().isoformat(timespec="seconds")
    applied = skipped_ab_filled = skipped_existing = 0
    for candidate in plan_result.get("candidates", []):
        case_id = candidate["case_id"]
        fetched = conn.execute(
            "SELECT raw_json FROM error_cases WHERE id = ?", (case_id,)
        ).fetchone()
        if fetched is None:
            continue
        raw = _load_raw(fetched["raw_json"])
        if is_filled(raw.get("AB")):
            skipped_ab_filled += 1
            continue
        if not refresh and is_filled(backfill_value(raw, "fix")):
            skipped_existing += 1
            continue
        container = raw.get(BACKFILL_KEY)
        if not isinstance(container, dict):
            container = {}
        container["fix"] = {
            "value": candidate["value"],
            "source": candidate["source"],
            "marker": candidate["marker"],
            "rule": FIX_BACKFILL_RULE,
            "line": candidate["line"],
            "chars": candidate["chars"],
            "at": stamp,
        }
        raw[BACKFILL_KEY] = container
        conn.execute(
            "UPDATE error_cases SET raw_json = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(raw, ensure_ascii=False, default=str), case_id),
        )
        applied += 1
    conn.commit()
    return {
        "applied": applied,
        "skipped_ab_filled": skipped_ab_filled,
        "skipped_existing": skipped_existing,
        "at": stamp,
    }


def main(argv: Optional[List[str]] = None) -> int:
    """CLI: dry-run by default; --apply writes. Summary printed in Vietnamese."""
    parser = argparse.ArgumentParser(
        description="Backfill tro `fix` (cot AB) cho bang error_cases - mac dinh dry-run."
    )
    parser.add_argument("--db", required=True, help="duong dan SQLite error_cases")
    parser.add_argument("--apply", action="store_true", help="ghi that (mac dinh chi doc)")
    parser.add_argument("--format", default="history_29", help="format raw_json can backfill")
    parser.add_argument("--batch-id", type=int, default=None)
    parser.add_argument("--refresh", action="store_true", help="tinh lai ca dong da co backfill")
    parser.add_argument("--samples", type=int, default=5, help="in N gia tri mau")
    parser.add_argument("--json-out", default=None, help="ghi ket qua day du ra file JSON")
    args = parser.parse_args(argv)

    conn = connect(args.db)
    try:
        plan = plan_backfill(
            conn, format=args.format, batch_id=args.batch_id, refresh=args.refresh
        )
        apply_result = None
        if args.apply:
            apply_result = apply_backfill(conn, plan, refresh=args.refresh)
    finally:
        conn.close()

    print(f"[f3b-backfill] DB: {args.db}")
    print(
        f"  quet: {plan['scanned']} ca ({plan['format']}) | AB da day: {plan['ab_filled']}"
        f" | AB trong: {plan['blank']} | da backfill truoc: {plan['already_backfilled']}"
    )
    print(
        f"  trich duoc: {plan['extractable']}"
        f" (O {plan['sources']['O']} / N {plan['sources']['N']})"
        f" | khong trich duoc: {plan['unextractable']}"
    )
    top_markers = sorted(plan["markers"].items(), key=lambda kv: -kv[1])[:10]
    print("  marker dung nhieu nhat: " + ", ".join(f"{m} x{n}" for m, n in top_markers))
    if apply_result is not None:
        print(
            f"  DA GHI: {apply_result['applied']} ca"
            f" (bo qua: AB da day {apply_result['skipped_ab_filled']},"
            f" da co backfill {apply_result['skipped_existing']})"
            f" | luc: {apply_result['at']}"
        )
    else:
        print("  DRY-RUN: chua ghi gi (them --apply de ghi)")
    for candidate in plan["candidates"][: args.samples]:
        preview = candidate["value"].replace("\n", " | ")[:120]
        print(
            f"    - {candidate['no_dvd']} [{candidate['source']}:{candidate['line']}"
            f" {candidate['marker']}] {preview}"
        )
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"plan": plan, "apply": apply_result}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  ket qua day du: {args.json_out}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
