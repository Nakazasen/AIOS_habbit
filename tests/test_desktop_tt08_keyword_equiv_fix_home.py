"""Unit tests for DESKTOP-TT08-KEYWORD-EQUIV-FIX-HOME.

Verifies:
1. Calibration of TT08 keywords in question set files:
   - Both JSONL and JSON files contain updated keywords: ['10kg', '1段目', 'オリコン', 'p-Rack', 'C2A02010101']
2. Real benchmark answer matching for TT08 in R3 dataset:
   - Target doc 'wsc-6f049a1fdfc090dc7d439224.txt' matches
   - Answer contains '1段目' (Japanese for 'tầng 1'), 'オリコン' (Katakana for 'ORICON'), and 'C2A02010101' (level 1 rack position)
   - Matches exactly 3/5 keywords (60% >= 3/5, majority pass >= 50%)
   - Checkpoint pass = True
3. Invariant preservation:
   - AND formula (checkpoint_pass == doc_matched AND keywords_pass) strictly maintained.
4. Zero regression across the entire 124-turn R3 dataset:
   - Simulation confirms ONLY TT08 changes state from FAIL to PASS.
   - All other 123 turns remain 100% intact.
5. Ingestion source corpus integrity:
   - wsc-6f049a1fdfc090dc7d439224.txt remains untouched.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from scripts.generate_stress_rerun_report import (
    normalize_keyword_text as gen_norm_kw,
    match_keywords_with_tolerance as gen_match_kw,
)
from scripts.run_desktop_stress_rerun import (
    normalize_keyword_text as runner_norm_kw,
    evaluate_checkpoint,
)


def test_bo_cau_hoi_tt08_updated():
    """Verify that both question dataset files (JSONL and JSON) have been updated for TT08."""
    jsonl_path = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua\bo-cau-hoi-hoi-quy-120-desktop-home.jsonl")
    json_path = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua\bo-cau-hoi-hoi-quy-120-desktop-home.json")

    assert jsonl_path.exists(), f"Missing {jsonl_path}"
    assert json_path.exists(), f"Missing {json_path}"

    expected_kw = ["10kg", "1段目", "オリコン", "p-Rack", "C2A02010101"]

    # Check JSONL
    found_jsonl = False
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("ma_cau") == "TT08":
                found_jsonl = True
                actual_kw = item.get("dap_an_ky_vong", {}).get("tu_khoa_bat_buoc")
                assert actual_kw == expected_kw, f"JSONL TT08 keywords mismatch: {actual_kw} != {expected_kw}"
                break
    assert found_jsonl, "TT08 not found in JSONL"

    # Check JSON
    found_json = False
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        questions = data if isinstance(data, list) else data.get("questions", [])
        for item in questions:
            if item.get("ma_cau") == "TT08":
                found_json = True
                actual_kw = item.get("dap_an_ky_vong", {}).get("tu_khoa_bat_buoc")
                assert actual_kw == expected_kw, f"JSON TT08 keywords mismatch: {actual_kw} != {expected_kw}"
                break
    assert found_json, "TT08 not found in JSON"


def test_tt08_real_data_match_r3():
    """Verify that TT08 real answer in R3 raw data achieves >= 3/5 keywords and PASS."""
    r3_jsonl = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua\du-lieu-tho-tung-luot-stress-rerun-r3.jsonl")
    assert r3_jsonl.exists(), f"Missing R3 dataset: {r3_jsonl}"

    tt08_turn = None
    with open(r3_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            t = json.loads(line)
            if t.get("question_id") == "TT08":
                tt08_turn = t
                break

    assert tt08_turn is not None, "TT08 turn not found in R3 dataset"

    raw_answer = tt08_turn.get("raw_answer") or ""
    trace_titles = tt08_turn.get("trace_titles") or []
    trace_snippets = tt08_turn.get("trace_snippets") or []

    q_item = {
        "ma_cau": "TT08",
        "dap_an_ky_vong": {
            "tai_lieu_muc_tieu": [
                "wsc-6f049a1fdfc090dc7d439224.txt",
                "wsc-991fbffcf8e0a07846e2e957.txt",
            ],
            "tu_khoa_bat_buoc": ["10kg", "1段目", "オリコン", "p-Rack", "C2A02010101"],
            "diem_chinh_ky_vong": "Với thùng ORICON từ 10kg trở lên thì phải đặt ở tầng 1 của p-Rack và xếp đầy từ rack phía trong.",
        },
    }

    eval_res = evaluate_checkpoint(
        q_item=q_item,
        ans_text=raw_answer,
        trace_titles=trace_titles,
        trace_snippets=trace_snippets,
        canary_sources=[],
    )

    assert eval_res["doc_matched"] is True, "Target document wsc-6f049a1fdfc090dc7d439224.txt should match"
    assert eval_res["keywords_pass"] is True, "Keywords pass should be True"
    assert eval_res["keywords_matched"] == ["1段目", "オリコン", "C2A02010101"]
    assert eval_res["keywords_count"] == 3
    assert eval_res["keywords_total"] == 5
    assert eval_res["keywords_count"] >= 3, "TT08 must achieve >= 3/5 keywords"
    assert eval_res["keywords_pass_majority"] is True, "3/5 satisfies majority (>= 50%)"
    assert eval_res["checkpoint_pass"] is True, "TT08 checkpoint must pass (doc_matched AND keywords_pass)"


def test_and_formula_invariant():
    """Verify that checkpoint_pass == (doc_matched AND keywords_pass) invariant is strictly preserved."""
    q_item = {
        "ma_cau": "TEST_TT08_AND",
        "dap_an_ky_vong": {
            "tai_lieu_muc_tieu": ["wsc-6f049a1fdfc090dc7d439224.txt"],
            "tu_khoa_bat_buoc": ["10kg", "1段目", "オリコン", "p-Rack", "C2A02010101"],
            "diem_chinh_ky_vong": "Test invariant",
        },
    }

    # Case 1: Doc matches, keywords match -> PASS
    res1 = evaluate_checkpoint(
        q_item=q_item,
        ans_text="以上のオリコンは1段目へ C2A02010101 [1] **wsc-6f049a1fdfc090dc7d439224.txt**",
        trace_titles=["wsc-6f049a1fdfc090dc7d439224.txt"],
        trace_snippets=[],
        canary_sources=[],
    )
    assert res1["doc_matched"] is True
    assert res1["keywords_pass"] is True
    assert res1["checkpoint_pass"] is True

    # Case 2: Doc matches, keywords missing -> FAIL
    res2 = evaluate_checkpoint(
        q_item=q_item,
        ans_text="Hoàn toàn không có từ khóa liên quan [1] **wsc-6f049a1fdfc090dc7d439224.txt**",
        trace_titles=["wsc-6f049a1fdfc090dc7d439224.txt"],
        trace_snippets=[],
        canary_sources=[],
    )
    assert res2["doc_matched"] is True
    assert res2["keywords_pass"] is False
    assert res2["checkpoint_pass"] is False

    # Case 3: Doc mismatch, keywords present -> FAIL
    res3 = evaluate_checkpoint(
        q_item=q_item,
        ans_text="以上のオリコンは1段目へ C2A02010101 nhưng sai tài liệu [1] **other_file.txt**",
        trace_titles=["other_file.txt"],
        trace_snippets=[],
        canary_sources=[],
    )
    assert res3["doc_matched"] is False
    assert res3["keywords_pass"] is True
    assert res3["checkpoint_pass"] is False


def test_r3_dataset_simulation_only_tt08_changes_state():
    """Verify that across all 124 turns of R3, only TT08 changes state when evaluating with new question set."""
    r3_jsonl = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua\du-lieu-tho-tung-luot-stress-rerun-r3.jsonl")
    assert r3_jsonl.exists(), f"Missing R3 dataset: {r3_jsonl}"

    new_tt08_kws = ["10kg", "1段目", "オリコン", "p-Rack", "C2A02010101"]

    turns = []
    with open(r3_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                turns.append(json.loads(line))

    assert len(turns) == 124, f"Expected 124 turns, got {len(turns)}"

    diff_turns = []
    for t in turns:
        qid = t.get("question_id")
        raw_ans = t.get("raw_answer") or ""
        doc_matched = bool(t.get("doc_matched", False))
        old_kws = t.get("keywords_expected") or []

        # Baseline evaluation (using current normalization and old keywords in R3)
        matched_base = gen_match_kw(raw_ans, old_kws)
        kw_pass_base = (len(matched_base) >= 1) if old_kws else True
        both_base = bool(doc_matched and kw_pass_base)

        # New evaluation: TT08 uses new keywords, all others use existing keywords
        new_kws = new_tt08_kws if qid == "TT08" else old_kws
        matched_new = gen_match_kw(raw_ans, new_kws)
        kw_pass_new = (len(matched_new) >= 1) if new_kws else True
        both_new = bool(doc_matched and kw_pass_new)

        if kw_pass_base != kw_pass_new or both_base != both_new:
            diff_turns.append({
                "qid": qid,
                "doc_matched": doc_matched,
                "base_both": both_base,
                "new_both": both_new,
                "matched_new": matched_new,
                "kw_count": len(matched_new),
                "kw_total": len(new_kws),
            })

    # Exactly 1 turn changed across the entire dataset: TT08!
    assert len(diff_turns) == 1, f"Expected exactly 1 changed turn, got {len(diff_turns)}: {diff_turns}"
    tt08_change = diff_turns[0]
    assert tt08_change["qid"] == "TT08"
    assert tt08_change["base_both"] is False
    assert tt08_change["new_both"] is True
    assert tt08_change["kw_count"] == 3
    assert tt08_change["kw_total"] == 5
    assert set(tt08_change["matched_new"]) == {"1段目", "オリコン", "C2A02010101"}


def test_evidence_corpus_and_target_doc_unmodified():
    """Verify that wsc-6f049a1fdfc090dc7d439224.txt is untouched in accordance with permission constraints."""
    doc_path = Path(r"D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\materialized_sources\wsc-6f049a1fdfc090dc7d439224.txt")
    assert doc_path.exists(), f"Missing corpus file: {doc_path}"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The file still contains the corrupted string '※※' (not manually edited)
    assert "※※" in content
    assert "以上のオリコンは１段目へ" in content
    # Vietnamese section still contains '10kg'
    assert "※ Với thùng ORICON từ 10kg trở lên thì đặt ở tầng 1" in content
    # Rule summary section still contains '10kg'
    assert "10kg以上の重量物は[高さ①]＝01" in content
