# -*- coding: utf-8 -*-
"""Capture AFTER verbatim answers and verify language purity."""

import json
import re
import sys
from pathlib import Path

APP_DIR = Path("D:/Sandbox/AIOS_habbit")
sys.path.insert(0, str(APP_DIR / "src"))

from aios_habit.chat_action import ChatActionRequest
from aios_habit.chat_action_error_lookup import (
    _open_ro,
    _render_cards,
    _render_synthesized_answer,
    extract_codes,
    lookup_glossary,
    resolve_db_path,
    search_similar,
)
from aios_habit.answer_language_policy import has_japanese

req = ChatActionRequest(question="C6770", notebook_id="NB-LAZY-DTL")
conn = _open_ro(resolve_db_path(req))

questions = [
    ("C6770", "Mã lỗi C6770 nguyên nhân là gì?"),
    ("JAM4212", "Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?"),
    ("F000", "Mã lỗi F000 nguyên nhân và biện pháp xử lý là gì?"),
]

jp_re = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")

results = {}
for q_id, q_text in questions:
    codes = extract_codes(q_text) or [q_id]
    cases, _, total = search_similar(conn, q_text)
    gloss = lookup_glossary(conn, codes)
    ans = _render_synthesized_answer(cases, codes, gloss, total, q_text)

    # Scan for remaining Japanese
    lines = ans.splitlines()
    remaining_jp_lines = []
    for idx, line in enumerate(lines):
        if jp_re.search(line):
            is_identifier = any(ext in line for ext in [".xls", ".xlsx", ".pdf", ".csv"]) or "`" in line
            remaining_jp_lines.append({
                "line_no": idx,
                "text": line,
                "is_permitted_identifier": is_identifier,
            })

    results[q_id] = {
        "question": q_text,
        "codes": codes,
        "total": total,
        "cases_count": len(cases),
        "verbatim_answer_after": ans,
        "remaining_jp_lines_count": len(remaining_jp_lines),
        "remaining_jp_lines": remaining_jp_lines,
    }

out_p = APP_DIR / "docs" / "phieu-viec" / "ket-qua" / "language_purity_after_verbatim.json"
out_p.parent.mkdir(parents=True, exist_ok=True)
out_p.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved AFTER verbatim answers to: {out_p}")

for q_id, data in results.items():
    print(f"\n=== {q_id} ===")
    print(f"Length: {len(data['verbatim_answer_after'])} chars")
    print(f"Remaining JP lines: {data['remaining_jp_lines_count']}")
    for r in data["remaining_jp_lines"]:
        status = "PERMITTED IDENTIFIER" if r["is_permitted_identifier"] else "VIOLATION"
        print(f"  [{status}] Line {r['line_no']}: {r['text'][:80]}")
