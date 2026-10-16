"""Unit tests for DESKTOP-BENCHMARK-KEYWORD-TOLERANCE-NORM-FIX-HOME.

Verifies:
1. Spacing normalization between numbers and measurement units for known pairs:
   - '3 s' / '3s'
   - '6 s' / '6s'
   - '1.1 mm' / '1.1mm'
   - '64.09 dot' / '64.09Dot'
   - '5.9 dot' / '5.9Dot'
2. Real benchmark answer matching for Q0677 ('3s', '6s') and Q0705 ('1.1mm', '64.09Dot', '5.9Dot').
3. Calibration of Q0635 keywords to authentic phrases in the target document (Slide 9).
4. Validation that question set files (JSON and JSONL) contain calibrated keywords for Q0635.
5. Invariant preservation: AND formula (doc_matched AND keywords_pass) remains strictly enforced.
6. Zero regression on standard non-unit keywords (dates, serials, Japanese text).
"""
import json
from pathlib import Path
import re
import pytest

from scripts.generate_stress_rerun_report import (
    normalize_keyword_text as gen_norm_kw,
    match_keywords_with_tolerance as gen_match_kw,
)
from scripts.run_desktop_stress_rerun import (
    normalize_keyword_text as runner_norm_kw,
    evaluate_checkpoint,
)


def test_unit_spacing_normalization_known_pairs():
    """Verify that all 5 known pairs normalize to identical forms across both runner and generator."""
    known_pairs = [
        ("3 s", "3s", "3 s"),
        ("6 s", "6s", "6 s"),
        ("1.1 mm", "1.1mm", "1.1 mm"),
        ("64.09 dot", "64.09Dot", "64.09 dot"),
        ("5.9 dot", "5.9Dot", "5.9 dot"),
    ]

    for variant_a, variant_b, expected_canonical in known_pairs:
        # Test in runner
        norm_runner_a = runner_norm_kw(variant_a)
        norm_runner_b = runner_norm_kw(variant_b)
        assert norm_runner_a == expected_canonical, f"Runner failed on {variant_a}: got {norm_runner_a}"
        assert norm_runner_b == expected_canonical, f"Runner failed on {variant_b}: got {norm_runner_b}"
        assert norm_runner_a == norm_runner_b

        # Test in generator
        norm_gen_a = gen_norm_kw(variant_a)
        norm_gen_b = gen_norm_kw(variant_b)
        assert norm_gen_a == expected_canonical, f"Generator failed on {variant_a}: got {norm_gen_a}"
        assert norm_gen_b == expected_canonical, f"Generator failed on {variant_b}: got {norm_gen_b}"
        assert norm_gen_a == norm_gen_b

        # Test tolerance matching
        matched_forward = gen_match_kw(f"Value is {variant_b} here", [variant_a])
        assert matched_forward == [variant_a], f"Failed to match expected '{variant_a}' in text '{variant_b}'"

        matched_backward = gen_match_kw(f"Value is {variant_a} here", [variant_b])
        assert matched_backward == [variant_b], f"Failed to match expected '{variant_b}' in text '{variant_a}'"


def test_q0677_real_data_match():
    """Verify Q0677: Text containing '(3s)' and '(6s)' matches keywords ['3 s', '6 s']."""
    raw_answer_q0677 = (
        "Dựa trên các trích đoạn tài liệu đã tìm kiếm:\n\n"
        "[1] **Bong TAPE COVER GLASS Rev.00 VN.pptx**:\n"
        "※ Thử nghiệm + Tăng thời gian ép COVER GLASS: Đối sách tạm thời "
        "Thời gian ép Kết quả kiểm tra khe hơ ̉ giữa GLASS va ̀ LID "
        "Hiện tại (3s) NG Thử nghiệm (6s) NG + Tăng lực ép COVER GLASS: "
        "Lực ép Kết quả kiểm tra khe hơ ̉ giữa GLASS va ̀ LID Hiện tại (75 N) NG "
        "Thử nghiệm (100 N) OK Thử nghiệm (110 N) OK  Đề án: Tăng lực ép của đồ gá từ 75 N  110 N."
    )
    q_item = {
        "ma_cau": "Q0677",
        "dap_an_ky_vong": {
            "tai_lieu_muc_tieu": ["Bong TAPE COVER GLASS Rev.00 VN.pptx"],
            "tu_khoa_bat_buoc": ["3 s", "6 s"],
            "diem_chinh_ky_vong": "Hiện tại 3 s NG và thử nghiệm 6 s NG.",
        },
    }

    eval_res = evaluate_checkpoint(
        q_item=q_item,
        ans_text=raw_answer_q0677,
        trace_titles=["Bong TAPE COVER GLASS Rev.00 VN.pptx"],
        trace_snippets=[],
        canary_sources=[],
    )

    assert eval_res["doc_matched"] is True
    assert eval_res["keywords_pass"] is True
    assert eval_res["keywords_matched"] == ["3 s", "6 s"]
    assert eval_res["keywords_count"] == 2
    assert eval_res["keywords_total"] == 2
    assert eval_res["keywords_pass_strict"] is True
    assert eval_res["checkpoint_pass"] is True


def test_q0705_real_data_match():
    """Verify Q0705: Text containing '1.1mm', '64.09Dot', '5.9Dot' matches keywords ['1.1 mm', '64.09 dot', '5.9 dot']."""
    raw_answer_q0705 = (
        "Dựa trên các trích đoạn tài liệu đã tìm kiếm:\n\n"
        "[1] **Sirius 2 _ C7620_報告版 4.pptx**:\n"
        "Sirius 2 C7620 BOWSKEW 治具で Bk と光路高さの差分 BOWSKEW 治具 の光路高さ （ 1729LSU の平均値） "
        "情報整理 ① BOWSKEW 調整治具で 通常機の MAGENTA の光路高さの平均値は 1.1mm であり、 "
        "Bk との色ずれ量は 64.09Dot 。 上限 70Dot に対して、 C7620 エラーが発生しないための余裕範囲は約 5.9Dot 。"
    )
    q_item = {
        "ma_cau": "Q0705",
        "dap_an_ky_vong": {
            "tai_lieu_muc_tieu": ["Sirius 2 _ C7620_報告版 4.pptx"],
            "tu_khoa_bat_buoc": ["1.1 mm", "64.09 dot", "5.9 dot"],
            "diem_chinh_ky_vong": "Quang lộ Magenta 1.1 mm, sắc sai 64.09 dot, dư lượng 5.9 dot.",
        },
    }

    eval_res = evaluate_checkpoint(
        q_item=q_item,
        ans_text=raw_answer_q0705,
        trace_titles=["Sirius 2 _ C7620_報告版 4.pptx"],
        trace_snippets=[],
        canary_sources=[],
    )

    assert eval_res["doc_matched"] is True
    assert eval_res["keywords_pass"] is True
    assert eval_res["keywords_matched"] == ["1.1 mm", "64.09 dot", "5.9 dot"]
    assert eval_res["keywords_count"] == 3
    assert eval_res["keywords_total"] == 3
    assert eval_res["keywords_pass_strict"] is True
    assert eval_res["checkpoint_pass"] is True


def test_q0635_calibrated_keywords_match_target_document_slide9():
    """Verify Q0635 calibrated keywords match the actual text in Slide 9 of target document."""
    slide9_text = (
        "Điều chỉnh lượng sáng ( Điều chỉnh LASER POWER )\n"
        "Điều chỉnh lượng sáng là điều chỉnh lượng đầu ra của LASER DIODE ở vị trí phần trung tâm ảnh của ảnh trên DRUM.\n"
        "Phần trung tâm ảnh hầu như tương đương với phần trung tâm của Lens F, về cơ bản ở phần đó lượng sáng là lớn nhất.\n"
        "Nói cách khác lượng sáng càng xa trung tâm càng yếu. Xuất hiện hiện tượng nồng độ ở hai bên ảnh bị nhạt.\n"
        "Nếu hiện tượng xẩy ra rõ ràng ta đo lượng sáng xung quanh ngoài vùng trung tâm rồi tiến hành chỉnh sửa lượng sáng."
    )
    calibrated_keywords = ["lượng sáng", "trung tâm", "hai bên ảnh", "bị nhạt"]

    matched = gen_match_kw(slide9_text, calibrated_keywords)
    assert matched == calibrated_keywords, f"All calibrated keywords should match Slide 9: got {matched}"


def test_bo_cau_hoi_q0635_updated():
    """Verify that both question dataset files (JSONL and JSON) have been calibrated for Q0635."""
    jsonl_path = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua\bo-cau-hoi-hoi-quy-120-desktop-home.jsonl")
    json_path = Path(r"D:\Sandbox\aios-dieu-phoi\hop-thu\lan-desktop\ket-qua\bo-cau-hoi-hoi-quy-120-desktop-home.json")

    assert jsonl_path.exists(), f"Missing {jsonl_path}"
    assert json_path.exists(), f"Missing {json_path}"

    expected_kw = ["lượng sáng", "trung tâm", "hai bên ảnh", "bị nhạt"]

    # Check JSONL
    found_jsonl = False
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("ma_cau") == "Q0635":
                found_jsonl = True
                actual_kw = item.get("dap_an_ky_vong", {}).get("tu_khoa_bat_buoc")
                assert actual_kw == expected_kw, f"JSONL Q0635 keywords mismatch: {actual_kw}"
                break
    assert found_jsonl, "Q0635 not found in JSONL"

    # Check JSON
    found_json = False
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        questions = data if isinstance(data, list) else data.get("questions", [])
        for item in questions:
            if item.get("ma_cau") == "Q0635":
                found_json = True
                actual_kw = item.get("dap_an_ky_vong", {}).get("tu_khoa_bat_buoc")
                assert actual_kw == expected_kw, f"JSON Q0635 keywords mismatch: {actual_kw}"
                break
    assert found_json, "Q0635 not found in JSON"


def test_and_formula_invariant():
    """Verify that checkpoint_pass == (doc_matched AND keywords_pass) invariant is strictly preserved."""
    q_item = {
        "ma_cau": "TEST_AND",
        "dap_an_ky_vong": {
            "tai_lieu_muc_tieu": ["test_doc.pptx"],
            "tu_khoa_bat_buoc": ["1.1 mm"],
            "diem_chinh_ky_vong": "Test",
        },
    }

    # Case 1: Doc matches, keywords match -> PASS
    res1 = evaluate_checkpoint(
        q_item=q_item,
        ans_text="Answer with 1.1mm [1] **test_doc.pptx**",
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
        ans_text="Answer with 1.1mm but wrong doc [1] **other_file.pptx**",
        trace_titles=["other_file.pptx"],
        trace_snippets=[],
        canary_sources=[],
    )
    assert res3["doc_matched"] is False
    assert res3["keywords_pass"] is True
    assert res3["checkpoint_pass"] is False


def test_no_regression_on_standard_keywords():
    """Ensure standard keywords (dates, numbers, alphanumeric codes, CJK) are unaffected by unit normalization."""
    std_cases = [
        ("Nguyen Van Cuong ngày 2025-02-12 mã KTD-2025-02-0140", "2025-02-12"),
        ("Đạt chuẩn 3153 bản ghi và 3.153 tổng số", "3153"),
        ("Đạt chuẩn 3153 bản ghi và 3.153 tổng số", "3.153"),
        ("Yellow 1304件, Cyan 1035件, Magenta 814件", "1304件"),
        ("Yellow 1304件, Cyan 1035件, Magenta 814件", "1035件"),
        ("2月19日にC23/C24でNG率が上昇", "2月19日"),
        ("Phát hiện lỗi BOWSKEW trên máy Sirius", "BOWSKEW"),
    ]

    for text, kw in std_cases:
        matched = gen_match_kw(text, [kw])
        assert matched == [kw], f"Standard keyword failed to match: '{kw}' in '{text}'"
