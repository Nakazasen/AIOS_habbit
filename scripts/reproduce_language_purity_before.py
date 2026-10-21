# -*- coding: utf-8 -*-
import json
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

req = ChatActionRequest(question="C6770", notebook_id="NB-LAZY-DTL")
conn = _open_ro(resolve_db_path(req))

questions = [
    ("C6770", "Mã lỗi C6770 nguyên nhân là gì?"),
    ("JAM4212", "Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?"),
    ("F000", "Mã lỗi F000 nguyên nhân và biện pháp xử lý là gì?"),
]

results = {}
for q_id, q_text in questions:
    codes = extract_codes(q_text) or [q_id]
    cases, _, total = search_similar(conn, q_text)
    gloss = lookup_glossary(conn, codes)
    ans = _render_synthesized_answer(cases, codes, gloss, total, q_text)
    results[q_id] = {
        "question": q_text,
        "codes": codes,
        "total": total,
        "cases_count": len(cases),
        "verbatim_answer_before": ans,
    }

out_p = APP_DIR / "docs" / "phieu-viec" / "ket-qua" / "language_purity_before_verbatim.json"
out_p.parent.mkdir(parents=True, exist_ok=True)
out_p.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved BEFORE verbatim answers to: {out_p}")
for q_id, data in results.items():
    print(f"=== {q_id}: Length {len(data['verbatim_answer_before'])} chars ===")
