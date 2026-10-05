"""Periodic feedback review: SMA(20) trend alerts on daily dislike rates.

Ticket FEEDBACK-REVIEW-HOME reuses the ``feedback_loop_home`` store
(``local_cases/answer_feedback.jsonl``) without rewriting it:

- Daily dislike-rate series per question (``question_key``) and per topic.
- SMA(20) + sigma per series; anomaly when |rate - SMA| > k * sigma.
- Trend alert only when >= 3 consecutive anomalies, or >= 3 anomalies
  in the last 5 days. One bad point alone never alerts.
- Series shorter than 20 points use SMA(n) and are marked preliminary.
- Report (Markdown) is written to ``local_cases/`` only, never the index.
- Reuses flag ``AIOS_FEATURE_FEEDBACK_LOOP_HOME`` (default OFF).
  When the flag is off this module does nothing.

Compatible with Python 3.11.
"""

from __future__ import annotations

import argparse
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence

DEFAULT_WINDOW = 20
DEFAULT_K = 2.0


def review_enabled() -> bool:
    """Return True only when the shared feedback-loop flag is on."""
    from aios_habit import feedback_loop_home as loop

    return loop.feedback_loop_enabled()


def sma(values: Sequence[float], window: int = DEFAULT_WINDOW) -> float:
    """Simple moving average over the last ``window`` values."""
    items = [float(v) for v in list(values)]
    if not items:
        return 0.0
    span = max(1, int(window or 0))
    tail = items[-span:]
    return sum(tail) / len(tail)


def _dev_of(tail: Sequence[float]) -> float:
    """Population std-dev; tiny float noise collapses to 0.0."""
    items = [float(v) for v in list(tail)]
    count = len(items)
    if count <= 1:
        return 0.0
    mean = sum(items) / count
    var = sum((v - mean) ** 2 for v in items) / count
    if var <= 1e-18:
        return 0.0
    return math.sqrt(var)


def sigma(values: Sequence[float], window: int = DEFAULT_WINDOW) -> float:
    """Population std-dev over the last ``window`` values (0.0 when flat)."""
    items = [float(v) for v in list(values)]
    if not items:
        return 0.0
    span = max(1, int(window or 0))
    return _dev_of(items[-span:])


def sma_sigma(
    values: Sequence[float], window: int = DEFAULT_WINDOW
) -> Dict[str, object]:
    """SMA + sigma for the tail of ``values`` with a preliminary note."""
    items = [float(v) for v in list(values)]
    span = max(1, int(window or 0))
    used = min(len(items), span)
    tail = items[-span:] if items else []
    mean = sum(tail) / len(tail) if tail else 0.0
    dev = _dev_of(tail)
    return {
        "sma": mean,
        "sigma": dev,
        "diem_da_dung": used,
        "cua_so": span,
        "so_bo": used < span,
    }


def is_anomaly(value: float, ref_sma: float, ref_sigma: float, k: float = DEFAULT_K) -> bool:
    """One point is anomalous when it deviates more than k * sigma."""
    diff = abs(float(value) - float(ref_sma))
    spread = float(ref_sigma)
    if spread <= 0:
        return diff > 0
    return diff > float(k) * spread


def detect_anomalies(
    values: Sequence[float],
    window: int = DEFAULT_WINDOW,
    k: float = DEFAULT_K,
) -> List[Dict[str, object]]:
    """Rolling anomaly flags; each point is checked against its prior window."""
    items = [float(v) for v in list(values)]
    span = max(1, int(window or 0))
    out: List[Dict[str, object]] = []
    for idx, current in enumerate(items):
        baseline = items[max(0, idx - span): idx]
        if not baseline:
            out.append(
                {
                    "chi_so": idx,
                    "gia_tri": current,
                    "sma": float(current),
                    "sigma": 0.0,
                    "so_bo": True,
                    "bat_thuong": False,
                }
            )
            continue
        mean = sum(baseline) / len(baseline)
        if len(baseline) <= 1:
            dev = 0.0
        else:
            var = sum((v - mean) ** 2 for v in baseline) / len(baseline)
            dev = math.sqrt(var) if var > 0 else 0.0
        out.append(
            {
                "chi_so": idx,
                "gia_tri": current,
                "sma": mean,
                "sigma": dev,
                "so_bo": len(baseline) < span,
                "bat_thuong": is_anomaly(current, mean, dev, k),
            }
        )
    return out


def has_trend_alert(flags: Sequence[bool]) -> bool:
    """Trend alert: 3 consecutive anomalies, or >=3 in the last 5 points."""
    items = [bool(f) for f in list(flags)]
    if not items:
        return False
    run = 0
    for flag in items:
        run = run + 1 if flag else 0
        if run >= 3:
            return True
    return sum(1 for f in items[-5:] if f) >= 3


def _record_date(record: Dict) -> str:
    raw = str(record.get("created_at", "") or "").strip()
    if not raw:
        return "khong-ro-ngay"
    try:
        parsed = datetime.fromisoformat(raw)
        return parsed.date().isoformat()
    except (ValueError, TypeError):
        return raw[:10] if len(raw) >= 10 else "khong-ro-ngay"


def _record_topic(record: Dict) -> str:
    topic = str(record.get("topic", "") or "").strip()
    if topic:
        return topic
    try:
        from aios_habit import feedback_loop_home as loop

        return str(loop.detect_topic(str(record.get("question", "") or "")) or "chua_phan_loai")
    except (ImportError, ValueError):
        return "chua_phan_loai"


def build_daily_rates(
    records: Sequence[Dict] | None = None,
    *,
    limit: int = 10000,
) -> Dict[str, Dict[str, List[Dict[str, object]]]]:
    """Daily dislike rates per question key and per topic, sorted by date."""
    from aios_habit import answer_feedback
    from aios_habit import feedback_loop_home as loop

    items = list(records) if records is not None else answer_feedback.iter_recent(limit=limit)
    per_question: Dict[str, Dict[str, Dict[str, object]]] = defaultdict(dict)
    per_topic: Dict[str, Dict[str, Dict[str, object]]] = defaultdict(dict)
    question_text: Dict[str, str] = {}
    for record in items:
        if not isinstance(record, dict):
            continue
        question = str(record.get("question", "") or "")
        key = loop.question_key(question) or "(cau_hoi_rong)"
        if key not in question_text:
            question_text[key] = question[:160]
        day = _record_date(record)
        topic = _record_topic(record)
        bad = 1 if str(record.get("rating", "") or "") == "chua_huu_ich" else 0
        for store, group in ((per_question, key), (per_topic, topic)):
            slot = store[group].setdefault(day, {"tong": 0, "che": 0})
            slot["tong"] = int(slot["tong"]) + 1
            slot["che"] = int(slot["che"]) + int(bad)

    def _to_series(
        grouped: Dict[str, Dict[str, Dict[str, object]]],
    ) -> Dict[str, List[Dict[str, object]]]:
        series: Dict[str, List[Dict[str, object]]] = {}
        for group, days in grouped.items():
            rows: List[Dict[str, object]] = []
            for day in sorted(days):
                total = int(days[day]["tong"] or 0)
                bad_count = int(days[day]["che"] or 0)
                rate = (bad_count / total) if total else 0.0
                rows.append(
                    {"ngay": day, "tong": total, "che": bad_count, "ti_le_che": round(rate, 3)}
                )
            series[group] = rows
        return series

    question_series = _to_series(per_question)
    topic_series = _to_series(per_topic)
    return {
        "theo_cau": question_series,
        "theo_chu_de": topic_series,
        "ten_cau_hoi": question_text,
    }


def analyze_series(
    rates: Sequence[float],
    window: int = DEFAULT_WINDOW,
    k: float = DEFAULT_K,
) -> Dict[str, object]:
    """SMA/sigma + anomalies + trend verdict for one rate series."""
    values = [float(v) for v in list(rates)]
    span = max(1, int(window or 0))
    summary = sma_sigma(values, span)
    details = detect_anomalies(values, span, float(k))
    flags = [bool(row["bat_thuong"]) for row in details]
    alert = has_trend_alert(flags)
    return {
        "sma": summary["sma"],
        "sigma": summary["sigma"],
        "diem_da_dung": summary["diem_da_dung"],
        "so_bo": summary["so_bo"],
        "chi_tiet": details,
        "diem_bat_thuong": [row["chi_so"] for row in details if row["bat_thuong"]],
        "canh_bao_xu_huong": alert,
    }


def _local_cases_dir() -> Path:
    from aios_habit import feedback_loop_home as loop

    return loop._local_cases_dir()


def run_periodic_review(
    records: Sequence[Dict] | None = None,
    *,
    window: int = DEFAULT_WINDOW,
    k: float = DEFAULT_K,
    output_path: str = "",
    limit: int = 10000,
) -> Dict[str, object]:
    """Run one periodic review; writes a Markdown report to local_cases only."""
    from aios_habit import answer_feedback
    from aios_habit import feedback_loop_home as loop

    if not review_enabled():
        return {
            "ok": False,
            "tat_co": True,
            "thong_bao": "Co AIOS_FEATURE_FEEDBACK_LOOP_HOME dang tat nen khong chay xem lai.",
        }
    items = list(records) if records is not None else answer_feedback.iter_recent(limit=limit)
    metrics = loop.compute_loop_metrics(items)
    daily = build_daily_rates(items)
    span = max(1, int(window or 0))
    factor = float(k)

    cau_alert: List[Dict[str, object]] = []
    for key, rows in daily["theo_cau"].items():
        rates = [float(r.get("ti_le_che", 0.0) or 0.0) for r in rows]
        result = analyze_series(rates, span, factor)
        if result["canh_bao_xu_huong"]:
            cau_alert.append(
                {
                    "khoa_cau_hoi": key[:120],
                    "cau_hoi": str(daily["ten_cau_hoi"].get(key, "") or "")[:160],
                    "so_ngay": len(rows),
                    "sma": round(float(result["sma"] or 0.0), 3),
                    "sigma": round(float(result["sigma"] or 0.0), 3),
                    "so_bo": bool(result["so_bo"]),
                    "ngay_bat_thuong": [
                        str(rows[i].get("ngay", "")) for i in result["diem_bat_thuong"]
                    ],
                }
            )
    cau_alert.sort(key=lambda row: str(row.get("khoa_cau_hoi", "")))

    chu_de_alert: List[Dict[str, object]] = []
    for topic, rows in daily["theo_chu_de"].items():
        rates = [float(r.get("ti_le_che", 0.0) or 0.0) for r in rows]
        result = analyze_series(rates, span, factor)
        if result["canh_bao_xu_huong"]:
            chu_de_alert.append(
                {
                    "chu_de": topic,
                    "so_ngay": len(rows),
                    "sma": round(float(result["sma"] or 0.0), 3),
                    "sigma": round(float(result["sigma"] or 0.0), 3),
                    "so_bo": bool(result["so_bo"]),
                    "ngay_bat_thuong": [
                        str(rows[i].get("ngay", "")) for i in result["diem_bat_thuong"]
                    ],
                }
            )
    chu_de_alert.sort(key=lambda row: str(row.get("chu_de", "")))

    flagged = loop.flag_answers_for_fix(items)
    flagged_keys = {str(row.get("khoa_cau_hoi", "")) for row in flagged}
    alert_keys = {str(row.get("khoa_cau_hoi", "")) for row in cau_alert}
    de_xuat: List[str] = []
    for row in cau_alert:
        key = str(row.get("khoa_cau_hoi", ""))
        if key in flagged_keys:
            de_xuat.append(
                "Uu tien 1: sua goc cau '%s' (vua co xu huong xau vua bi che tu 2 may tro len)."
                % (str(row.get("cau_hoi", "") or key)[:120])
            )
    for row in cau_alert:
        key = str(row.get("khoa_cau_hoi", ""))
        if key not in flagged_keys:
            de_xuat.append(
                "Uu tien 2: theo doi cau '%s' (co xu huong xau %d ngay, ngay bat thuong: %s)."
                % (
                    str(row.get("cau_hoi", "") or key)[:120],
                    int(row.get("so_ngay", 0) or 0),
                    ", ".join([str(v) for v in row.get("ngay_bat_thuong", [])][:5]) or "?",
                )
            )
    for row in flagged:
        key = str(row.get("khoa_cau_hoi", ""))
        if key not in alert_keys:
            de_xuat.append(
                "Uu tien 3: sua goc cau '%s' (bi che %d lan tu %d may, chua co xu huong ro)."
                % (
                    str(row.get("cau_hoi", "") or key)[:120],
                    int(row.get("che", 0) or 0),
                    int(row.get("so_may", 0) or 0),
                )
            )
    for row in metrics.get("theo_chu_de", []):
        if int(row.get("tong", 0) or 0) >= 3 and float(row.get("ti_le_che", 0.0) or 0.0) > 0.3:
            de_xuat.append(
                "Xem lai chu de %s (bi che %d/%d)."
                % (row.get("chu_de", "?"), row.get("che", 0), row.get("tong", 0))
            )
            break
    if not de_xuat:
        de_xuat.append("So lieu on. Giu nhip xem lai dinh ky.")

    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    if str(output_path or "").strip():
        report_path = Path(str(output_path).strip())
    else:
        report_path = _local_cases_dir() / ("feedback_review_%s.md" % stamp)
    lines: List[str] = []
    lines.append("# Bao cao xem lai dinh ky phan hoi")
    lines.append("")
    lines.append("- Thoi gian: %s" % datetime.now().astimezone().isoformat(timespec="seconds"))
    lines.append("- Co so: SMA(%d) + sigma, nguong k=%.2f" % (span, factor))
    lines.append(
        "- Quy tac: diem bat thuong khi |ti le che - SMA| > k*sigma; "
        "chi canh bao khi co 3 diem bat thuong lien tiep hoac >=3 trong 5 ngay gan nhat."
    )
    lines.append(
        "- Tong: %d luot (%d khen / %d che, ti le che %.3f)"
        % (
            int(metrics.get("tong", 0) or 0),
            int(metrics.get("khen", 0) or 0),
            int(metrics.get("che", 0) or 0),
            float(metrics.get("ti_le_che", 0.0) or 0.0),
        )
    )
    do_dai_dai_nhat = 0
    ngay_phan_biet = set()
    for nhom in (daily.get("theo_cau") or {}, daily.get("theo_chu_de") or {}):
        for rows in nhom.values():
            do_dai_dai_nhat = max(do_dai_dai_nhat, len(rows or []))
            for dong in rows or []:
                ngay_phan_biet.add(str(dong.get("ngay", "")))
    so_ngay_du_lieu = len([n for n in ngay_phan_biet if n and n != "khong-ro-ngay"])
    if do_dai_dai_nhat < span:
        lines.append(
            "- Chuoi du lieu: chuoi dai nhat %d ngay trong %d ngay co du lieu "
            "(chua du %d diem, so bo; khong canh bao gia tu du lieu it)."
            % (do_dai_dai_nhat, so_ngay_du_lieu, span)
        )
    else:
        lines.append(
            "- Chuoi du lieu: chuoi dai nhat %d ngay trong %d ngay co du lieu."
            % (do_dai_dai_nhat, so_ngay_du_lieu)
        )
    lines.append("")
    lines.append("## Bang xep hang cau bi che nhieu nhat")
    lines.append("")
    lines.append("| STT | Cau hoi | Tong | Che | Ti le che | So may |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    top_rows = list(metrics.get("theo_cau_tra_loi", []) or [])[:10]
    if not top_rows:
        lines.append("| - | Chua co du lieu | - | - | - | - |")
    for idx, row in enumerate(top_rows, start=1):
        lines.append(
            "| %d | %s | %d | %d | %.3f | %d |"
            % (
                idx,
                str(row.get("cau_hoi", "") or row.get("khoa_cau_hoi", ""))[:80].replace("|", " "),
                int(row.get("tong", 0) or 0),
                int(row.get("che", 0) or 0),
                float(row.get("ti_le_che", 0.0) or 0.0),
                int(row.get("so_may", 0) or 0),
            )
        )
    lines.append("")
    lines.append("## Canh bao xu huong (cau co xu huong xau di)")
    lines.append("")
    if not cau_alert:
        lines.append("- Khong co canh bao xu huong. Mot diem xau don le khong canh bao.")
    for row in cau_alert:
        note = " (chua du 20 diem, so bo)" if row.get("so_bo") else ""
        lines.append(
            "- %s: %d ngay, SMA=%.3f sigma=%.3f, ngay bat thuong: %s%s"
            % (
                str(row.get("cau_hoi", "") or row.get("khoa_cau_hoi", ""))[:120],
                int(row.get("so_ngay", 0) or 0),
                float(row.get("sma", 0.0) or 0.0),
                float(row.get("sigma", 0.0) or 0.0),
                ", ".join([str(v) for v in row.get("ngay_bat_thuong", [])][:8]) or "?",
                note,
            )
        )
    lines.append("")
    lines.append("## Chu de bi che tang")
    lines.append("")
    if not chu_de_alert:
        lines.append("- Khong co chu de nao co xu huong xau ro.")
    for row in chu_de_alert:
        note = " (chua du 20 diem, so bo)" if row.get("so_bo") else ""
        lines.append(
            "- %s: %d ngay, SMA=%.3f sigma=%.3f, ngay bat thuong: %s%s"
            % (
                row.get("chu_de", "?"),
                int(row.get("so_ngay", 0) or 0),
                float(row.get("sma", 0.0) or 0.0),
                float(row.get("sigma", 0.0) or 0.0),
                ", ".join([str(v) for v in row.get("ngay_bat_thuong", [])][:8]) or "?",
                note,
            )
        )
    lines.append("")
    lines.append("## De xuat sua goc theo thu tu uu tien")
    lines.append("")
    for idx, text in enumerate(de_xuat, start=1):
        lines.append("%d. %s" % (idx, text))
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "ok": True,
        "bao_cao": str(report_path),
        "tong": int(metrics.get("tong", 0) or 0),
        "ti_le_che": float(metrics.get("ti_le_che", 0.0) or 0.0),
        "canh_bao_cau": cau_alert,
        "canh_bao_chu_de": chu_de_alert,
        "de_xuat": de_xuat,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Chay vong xem lai dinh ky SMA(20) (chi khi duoc goi).",
    )
    parser.add_argument("--cua-so", dest="window", type=int, default=DEFAULT_WINDOW)
    parser.add_argument("--k", dest="k", type=float, default=DEFAULT_K)
    parser.add_argument("--dau-ra", dest="output", type=str, default="")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_periodic_review(window=args.window, k=args.k, output_path=args.output)
    if not result.get("ok"):
        print(str(result.get("thong_bao", "Co dang tat nen khong chay.")))
        return 0
    print("Da ghi bao cao: %s" % result.get("bao_cao", ""))
    print(
        "Tong %d luot, ti le che %.3f, canh bao %d cau / %d chu de."
        % (
            int(result.get("tong", 0) or 0),
            float(result.get("ti_le_che", 0.0) or 0.0),
            len(result.get("canh_bao_cau", []) or []),
            len(result.get("canh_bao_chu_de", []) or []),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
