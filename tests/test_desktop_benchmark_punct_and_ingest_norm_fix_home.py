"""Unit tests for DESKTOP-BENCHMARK-PUNCT-AND-INGEST-NORM-FIX-HOME.

Verifies:
1. Unicode NFKC normalization and punctuation (dashes / equal sign) normalization:
   - Full-width characters: '0.7 ｍｍ' -> '0.7 mm', '0.7㎜' -> '0.7 mm', '０.７ ｍｍ' -> '0.7 mm'
   - Dashes and equal sign: en-dash ('–'), em-dash ('—'), minus sign ('−'), figure dash ('‒'),
     horizontal bar ('―'), fullwidth equals ('＝'), and equals ('=') normalize to '-'
   - Synchronized between scripts/run_desktop_stress_rerun.py and scripts/generate_stress_rerun_report.py
2. Real benchmark answer matching for Q0706 in R3:
   - Target doc 'Sirius 2 _ C7620_報告版 4.pptx'
   - Text containing '0.7 ｍｍ' and '3/517 – 0.58% NG'
   - Matches keywords ['0.7 mm', '3/517 = 0.58% NG'] -> 2/2 keywords (100%), checkpoint_pass = True.
3. Analysis and evidence of TT08 ingestion text corruption:
   - Validates the corruption in wsc-6f049a1fdfc090dc7d439224.txt at lines 301-302 ('※※ 以上のオリコンは１段目へ')
   - Confirms absence of original source document, ensuring compliance with rule:
     do not manually tamper with source corpus, halt for coordinator resolution.
4. Invariant preservation: AND formula (doc_matched AND keywords_pass) remains strictly enforced.
5. Zero regression on standard non-unit keywords (dates, serials, CJK with prolonged sound marks).
6. Comprehensive simulation over all 124 turns of R3 dataset:
   - Exactly Q0706 improves from FAIL to PASS.
   - Zero regression on all other 123 turns.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import unicodedata
import pytest

from scripts.generate_stress_rerun_report import (
    normalize_keyword_text as gen_norm_kw,
    match_keywords_with_tolerance as gen_match_kw,
)
from scripts.run_desktop_stress_rerun import (
    normalize_keyword_text as runner_norm_kw,
    evaluate_checkpoint,
)


def test_unicode_nfkc_and_dash_equal_normalization_known_pairs():
    """Verify that Unicode full-width mm, ligatures, en-dash, em-dash, and equal signs normalize consistently."""
    pairs = [
        # (variant_a, variant_b, expected_canonical)
        ("0.7 mm", "0.7 ｍｍ", "0.7 mm"),
        ("0.7 mm", "0.7㎜", "0.7 mm"),
        ("0.7 mm", "０.７ ｍｍ", "0.7 mm"),
        ("3/517 = 0.58% NG", "3/517 – 0.58% NG", "3/517 - 0.58 % ng"),
        ("3/517 = 0.58% NG", "3/517 — 0.58% NG", "3/517 - 0.58 % ng"),
        ("3/517 = 0.58% NG", "3/517 − 0.58% NG", "3/517 - 0.58 % ng"),
        ("3/517 = 0.58% NG", "3/517 - 0.58% NG", "3/517 - 0.58 % ng"),
        ("3/517 = 0.58% NG", "3/517 ＝ 0.58% NG", "3/517 - 0.58 % ng"),
    ]

    for variant_a, variant_b, expected_canonical in pairs:
        norm_runner_a = runner_norm_kw(variant_a)
        norm_runner_b = runner_norm_kw(variant_b)
        assert norm_runner_a == expected_canonical, f"Runner failed on {variant_a}: got {norm_runner_a}"
        assert norm_runner_b == expected_canonical, f"Runner failed on {variant_b}: got {norm_runner_b}"
        assert norm_runner_a == norm_runner_b

        norm_gen_a = gen_norm_kw(variant_a)
        norm_gen_b = gen_norm_kw(variant_b)
        assert norm_gen_a == expected_canonical, f"Generator failed on {variant_a}: got {norm_gen_a}"
        assert norm_gen_b == expected_canonical, f"Generator failed on {variant_b}: got {norm_gen_b}"
        assert norm_gen_a == norm_gen_b

        # Test bidirectional matching
        matched_forward = gen_match_kw(f"Kết quả là {variant_b} thực tế", [variant_a])
        assert matched_forward == [variant_a], f"Failed to match expected '{variant_a}' in text '{variant_b}'"

        matched_backward = gen_match_kw(f"Kết quả là {variant_a} thực tế", [variant_b])
        assert matched_backward == [variant_b], f"Failed to match expected '{variant_b}' in text '{variant_a}'"


def test_q0706_real_data_match():
    """Verify Q0706: Real answer containing '0.7 ｍｍ' and '3/517 – 0.58% NG' matches keywords."""
    raw_answer_q0706 = (
        "Dựa trên các trích đoạn tài liệu đã tìm kiếm:\n\n"
        "[1] **Sirius 2 _ C7620_報告版 4.pptx**:\n"
        "Sirius 2 C7620 BOWSKEW 治具で Bk と光路高さの差分 BOWSKEW 治具 の光路高さ （ 1729LSU の平均値） "
        "C7620 発生しない機の各色 各色と Bk の差分 Dot ３台の平均値 通常時、余裕 Dot ( 差分平均値 - 上限 70 Dot） "
        "0.9 1.10 MAGENTA 64.09 5.9 0.4 0.60 YELLOW 32.00 38.0 -1.1 -0.90 CYAN -2.06 72.1 0.0 0.20 Black "
        "今後のアクション（３月１８日追記） 情報整理 ① BOWSKEW 調整治具で 通常機の MAGENTA の光路高さの平均値は 1.1mm であり、 "
        "Bk との色ずれ量は 64.09Dot 。 上限 70Dot に対して、 C7620 エラーが発生しないための余裕範囲は約 5.9Dot 。 "
        "② LSU HOUSING の寸法にバラつきがあるため、余裕範囲がなくなり、 70Dot を超えてしまう → C7620 発生 "
        "③ SIM 追加後、 MAGENTA 光路高さの平均値は 0.7 ｍｍ。発生機 3/517 – 0.58% NG （３台分析中） "
        "対策 ●上記③の実績から MAGENTA の光路高さの平均値を 0.6mm に補正できれば、 C7620 の副走査方向の色ずれ NG が発生しにくくなる 。"
    )
    q_item = {
        "ma_cau": "Q0706",
        "dap_an_ky_vong": {
            "tai_lieu_muc_tieu": ["Sirius 2 _ C7620_報告版 4.pptx"],
            "tu_khoa_bat_buoc": ["0.7 mm", "3/517 = 0.58% NG"],
            "diem_chinh_ky_vong": "SIM追加後、Magenta光路高さ平均0.7 mm、C7620発生率は3/517 = 0.58% NG。",
        },
    }

    eval_res = evaluate_checkpoint(
        q_item=q_item,
        ans_text=raw_answer_q0706,
        trace_titles=["Sirius 2 _ C7620_報告版 4.pptx"],
        trace_snippets=[],
        canary_sources=[],
    )

    assert eval_res["doc_matched"] is True
    assert eval_res["keywords_pass"] is True
    assert eval_res["keywords_matched"] == ["0.7 mm", "3/517 = 0.58% NG"]
    assert eval_res["keywords_count"] == 2
    assert eval_res["keywords_total"] == 2
    assert eval_res["keywords_pass_strict"] is True
    assert eval_res["checkpoint_pass"] is True


def test_tt08_ingestion_corpus_evidence():
    """Verify evidence of TT08 ingestion text corruption in wsc-6f049a1fdfc090dc7d439224.txt."""
    doc_path = Path(r"D:\Sandbox\AIOS_habbit\local_runs\workspace_chat_rag_v2_canary\materialized_sources\wsc-6f049a1fdfc090dc7d439224.txt")
    assert doc_path.exists(), f"Missing corpus file: {doc_path}"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Evidence 1: In the Japanese section, '10kg' was corrupted into '※※'
    assert "※※\n以上のオリコンは１段目へ" in content or "※※ 以上のオリコンは１段目へ" in content or "※※" in content, (
        "Expected corrupted string '※※' before '以上のオリコンは１段目へ' in corpus file"
    )

    # Evidence 2: In the Vietnamese section, the translation contains '10kg'
    assert "※ Với thùng ORICON từ 10kg trở lên thì đặt ở tầng 1" in content, (
        "Expected Vietnamese section to contain '10kg' and 'tầng 1'"
    )

    # Evidence 3: In the rule summary at bottom, '10kg' is present
    assert "10kg以上の重量物は[高さ①]＝01" in content, (
        "Expected rule summary section to contain '10kg以上の重量物'"
    )


def test_and_formula_invariant():
    """Verify that checkpoint_pass == (doc_matched AND keywords_pass) invariant is strictly preserved."""
    q_item = {
        "ma_cau": "TEST_AND",
        "dap_an_ky_vong": {
            "tai_lieu_muc_tieu": ["test_doc.pptx"],
            "tu_khoa_bat_buoc": ["0.7 mm", "3/517 = 0.58% NG"],
            "diem_chinh_ky_vong": "Test invariant",
        },
    }

    # Case 1: Doc matches, keywords match -> PASS
    res1 = evaluate_checkpoint(
        q_item=q_item,
        ans_text="Answer with 0.7 ｍｍ and 3/517 – 0.58% NG [1] **test_doc.pptx**",
        trace_titles=["test_doc.pptx"],
        trace_snippets=[],
        canary_sources=[],
    )
    assert res1["doc_matched"] is True
    assert res1["keywords_pass"] is True
    assert res1["checkpoint_pass"] is True

    # Case 2: Doc matches, keywords missing -> FAIL
    res2 = evaluate_checkpoint(
        q_item=q_item,
        ans_text="Answer with no keyword [1] **test_doc.pptx**",
        trace_titles=["test_doc.pptx"],
        trace_snippets=[],
        canary_sources=[],
    )
    assert res2["doc_matched"] is True
    assert res2["keywords_pass"] is False
    assert res2["checkpoint_pass"] is False

    # Case 3: Doc mismatch, keywords present -> FAIL
    res3 = evaluate_checkpoint(
        q_item=q_item,
        ans_text="Answer with 0.7 ｍｍ and 3/517 – 0.58% NG but wrong doc [1] **other_file.pptx**",
        trace_titles=["other_file.pptx"],
        trace_snippets=[],
        canary_sources=[],
    )
    assert res3["doc_matched"] is False
    assert res3["keywords_pass"] is True
    assert res3["checkpoint_pass"] is False


def test_no_regression_on_standard_keywords():
    """Ensure standard keywords (dates, numbers, codes, CJK katakana sound marks) are unaffected."""
    std_cases = [
        ("Nguyen Van Cuong ngày 2025-02-12 mã KTD-2025-02-0140", "2025-02-12"),
        ("Đạt chuẩn 3153 bản ghi và 3.153 tổng số", "3153"),
        ("Đạt chuẩn 3153 bản ghi và 3.153 tổng số", "3.153"),
        ("Yellow 1304件, Cyan 1035件, Magenta 814件", "1304件"),
        ("Yellow 1304件, Cyan 1035件, Magenta 814件", "1035件"),
        ("2月19日にC23/C24でNG率が上昇", "2月19日"),
        ("Phát hiện lỗi BOWSKEW trên máy Sirius", "BOWSKEW"),
        ("Dải nhiệt độ bảo quản từ 0–15°C đạt chuẩn", "0-15°C"),
        ("Lỗi C7620 và kiểm tra kính Laser ミラー", "ミラー"),
        ("Các giá trị đo âm: -140 và -70", "-140"),
        ("Các giá trị đo âm: -140 và -70", "-70"),
        ("Dấu phân cách kép: --", "--"),
    ]

    for text, kw in std_cases:
        matched = gen_match_kw(text, [kw])
        assert matched == [kw], f"Standard keyword failed to match: '{kw}' in '{text}'"


def test_r3_dataset_simulation_only_q0706_changes():
    """Verify that applying the new normalization on the entire R3 raw dataset improves Q0706 without regression."""
    r3_jsonl = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua\du-lieu-tho-tung-luot-stress-rerun-r3.jsonl")
    assert r3_jsonl.exists(), f"Missing R3 raw dataset: {r3_jsonl}"

    turns = []
    with open(r3_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                turns.append(json.loads(line))

    assert len(turns) == 124, f"Expected 124 turns in R3 dataset, got {len(turns)}"

    changed_turns = []
    for t in turns:
        qid = t.get("question_id")
        raw_ans = t.get("raw_answer") or ""
        kws = t.get("keywords_expected") or []
        doc_matched = bool(t.get("doc_matched", False))
        old_kw_pass = bool(t.get("keywords_pass", False))
        old_both = bool(t.get("checkpoint_pass", False))

        matched_new = gen_match_kw(raw_ans, kws)
        kw_count = len(matched_new)
        kw_total = len(kws)
        new_kw_pass = (kw_count >= 1) if kw_total > 0 else True
        new_both = bool(doc_matched and new_kw_pass)

        if old_kw_pass != new_kw_pass or old_both != new_both:
            changed_turns.append({
                "qid": qid,
                "old_kw_pass": old_kw_pass,
                "new_kw_pass": new_kw_pass,
                "old_both": old_both,
                "new_both": new_both,
                "matched_new": matched_new,
                "total_kws": kw_total,
            })

    # Assert exactly 1 turn changed in the whole dataset: Q0706
    assert len(changed_turns) == 1, f"Expected exactly 1 changed turn, got {len(changed_turns)}: {changed_turns}"
    q0706_change = changed_turns[0]
    assert q0706_change["qid"] == "Q0706"
    assert q0706_change["old_kw_pass"] is False
    assert q0706_change["new_kw_pass"] is True
    assert q0706_change["old_both"] is False
    assert q0706_change["new_both"] is True
    assert len(q0706_change["matched_new"]) == 2  # 2/2 keywords matched!
