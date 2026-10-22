"""Comprehensive verification test suite for DESKTOP-STEP5-AUTOCLASSIFY-RECURRENCE-HOME.

Verifies:
1. Classification accuracy >= 80% on isolated test split of real KDTPS data (zero test leakage).
2. Minority classes actively predicted (non-degenerate predictions).
3. Concrete provenance (căn cứ) provided for every suggestion; absence of evidence is declared.
4. Recurrence detection and countermeasure surfacing on the Preview Card.
5. User confirmation / editing of labels before saving without silent overwrite.
6. 3-point continuous improvement loop (inline feedback capture, measurable metrics, review surface).
7. Local-only feedback persistence in local_cases/ (never leaking to RAG).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import openpyxl
import pytest

from aios_habit.chat_action_create_case import (
    execute_confirm_case,
    extract_case_preview_marker,
    render_preview_card_text,
)
from aios_habit.chat_intent_router import (
    DANH_GIA_NHAN,
    XEM_PHAN_HOI,
    classify_intent,
    route,
)
from aios_habit.error_cases import init_db, start_batch, upsert_case
from aios_habit.error_cases.auto_classifier import (
    CAUSE_GROUPS,
    CAUSE_KEYWORDS,
    CAUSE_LABEL_VI,
    classify_error,
    classify_new_error,
    detect_recurrence,
)
from aios_habit.error_cases.autoclassify_feedback import (
    RATING_DUNG,
    RATING_MOT_PHAN,
    RATING_SAI,
    compute_autoclassify_metrics,
    format_autoclassify_review_summary,
    load_all_feedback,
    log_autoclassify_suggestion,
    record_autoclassify_feedback,
)

KDTPS_DIR = Path("data/kdtps_standard")
REAL_DATA_FILES = [
    KDTPS_DIR / "FY2027_che_tao_may_6thang_dau.xlsx",
    KDTPS_DIR / "FY2027_che_tao_may_6thang_cuoi.xlsx",
    KDTPS_DIR / "FY2027_cong_cu_dien.xlsx",
]

CAUSE_MAPPING: Dict[str, str] = {
    "部品要因(電気)": "linh_kien",
    "部品要因(Supplier)": "linh_kien",
    "部品要因(外制)": "linh_kien",
    "部品要因(TONER)": "linh_kien",
    "部品要因(部制)": "linh_kien",
    "メカ部品要因": "linh_kien",
    "部管": "linh_kien",
    "組立": "lap_rap",
    "作業": "lap_rap",
    "設計": "thiet_ke",
    "ソフト要因": "thiet_ke",
    "その他": "khac",
    "治具": "khac",
    "IT": "khac",
    "設備": "khac",
    "異物付着": "khac",
    "生管": "khac",
    "KDTCN": "khac",
    "不要": "khac",
    "要": "khac",
    "要因不明(製造)": "khac",
    "要因不明(電気)": "khac",
    "原因不明（メカ）": "khac",
    "原因不明（製造）": "khac",
    "原因不明(電気)": "khac",
    "静電気問題": "khac",
}


def _load_real_kdtps_dataset() -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load real company KDTPS data and split into 80% train / 20% test via deterministic hash."""
    all_cases: List[Dict[str, Any]] = []
    for fpath in REAL_DATA_FILES:
        if not fpath.is_file():
            continue
        wb = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
        ws = wb.active
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i < 2 or (row[0] is None and row[1] is None):
                continue
            raw_cause = str(row[24]).strip() if len(row) > 24 and row[24] is not None else ""
            group = CAUSE_MAPPING.get(raw_cause)
            if not group:
                continue

            case_uid = f"{fpath.stem}_{i}"
            no_dvd = str(row[0]).strip() if row[0] is not None else ""
            model = str(row[2]).strip() if row[2] is not None else ""
            line = str(row[3]).strip() if row[3] is not None else ""
            stage = str(row[4]).strip() if len(row) > 4 and row[4] is not None else ""
            phenomenon = str(row[7]).strip() if len(row) > 7 and row[7] is not None else ""
            op = str(row[11] or row[10] or "").strip() if len(row) > 11 else ""
            inv = str(row[13] or row[12] or "").strip() if len(row) > 13 else ""
            dept = str(row[14]).strip() if len(row) > 14 and row[14] is not None else ""
            part = str(row[16]).strip() if len(row) > 16 and row[16] is not None else ""
            supplier = str(row[19]).strip() if len(row) > 19 and row[19] is not None else ""
            countermeasure = str(row[25]).strip() if len(row) > 25 and row[25] is not None else ""

            combined_investigation = f"{op} {inv} {part} {supplier} {dept}".strip()
            all_cases.append({
                "uid": case_uid,
                "no_dvd": no_dvd,
                "machine_type": model,
                "line": line,
                "stage": stage,
                "dept": dept,
                "phenomenon": phenomenon,
                "investigation": combined_investigation,
                "countermeasure": countermeasure,
                "expected_cause": group,
                "raw_cause": raw_cause,
            })
        wb.close()

    train_split: List[Dict[str, Any]] = []
    test_split: List[Dict[str, Any]] = []
    for c in all_cases:
        h = hashlib.md5(c["uid"].encode("utf-8")).hexdigest()
        # Hash bucket % 10 < 2 gives clean 20% test split, completely disjoint from train
        if int(h[:8], 16) % 10 < 2:
            test_split.append(c)
        else:
            train_split.append(c)

    return train_split, test_split


def test_real_data_test_split_accuracy_at_least_80_percent():
    """Requirement (c): Test classification accuracy >= 80% on an isolated test split of real data."""
    train_cases, test_cases = _load_real_kdtps_dataset()
    assert len(train_cases) >= 2000, f"Train set size too small: {len(train_cases)}"
    assert len(test_cases) >= 500, f"Test set size too small: {len(test_cases)}"

    # Ensure zero leakage between train and test
    train_ids = {c["uid"] for c in train_cases}
    test_ids = {c["uid"] for c in test_cases}
    overlap = train_ids & test_ids
    assert len(overlap) == 0, f"Found data leakage between train and test splits: {len(overlap)} cases"

    correct = 0
    predictions_counter = Counter()
    per_class_total = Counter()
    per_class_correct = Counter()

    for c in test_cases:
        expected = c["expected_cause"]
        per_class_total[expected] += 1

        pred = classify_error(
            error_code="",
            phenomenon=c["phenomenon"],
            investigation=c["investigation"],
            machine_type=c["machine_type"],
            line=c["line"],
        )
        predicted_grp = pred.nhom_nguyen_nhan
        predictions_counter[predicted_grp] += 1

        if predicted_grp == expected:
            correct += 1
            per_class_correct[expected] += 1

    overall_accuracy = correct / len(test_cases)
    print(f"\n[EVAL] Overall Test Accuracy: {overall_accuracy * 100:.2f}% ({correct}/{len(test_cases)})")
    for grp in ("khac", "linh_kien", "lap_rap", "thiet_ke"):
        tot = per_class_total[grp]
        cor = per_class_correct[grp]
        acc_str = f"{cor/tot*100:.1f}%" if tot else "N/A"
        print(f"[EVAL] - {grp}: Total {tot}, Predicted {predictions_counter[grp]}, Correct {cor} ({acc_str})")

    # 1. Verification: overall accuracy >= 82.29% (no regression from baseline 82.29%)
    assert overall_accuracy >= 0.8229, (
        f"Classification accuracy on real test set ({overall_accuracy*100:.2f}%) fell below baseline 82.29%"
    )

    # 2. Verification: lap_rap accuracy >= 60.0% (quality requirement of ticket DESKTOP-STEP5-LAPRAP-CLASS-IMPROVE-HOME)
    lap_rap_acc = per_class_correct["lap_rap"] / per_class_total["lap_rap"]
    assert lap_rap_acc >= 0.60, (
        f"lap_rap accuracy ({lap_rap_acc*100:.1f}%, {per_class_correct['lap_rap']}/{per_class_total['lap_rap']}) did not reach >= 60.0% target"
    )

    # 3. Verification: no class degrades > 3 percentage points from baseline (khac >= 86.8%, linh_kien >= 72.8%)
    khac_acc = per_class_correct["khac"] / per_class_total["khac"]
    linh_kien_acc = per_class_correct["linh_kien"] / per_class_total["linh_kien"]
    assert khac_acc >= 0.868, f"khac degraded below 86.8%: {khac_acc*100:.1f}%"
    assert linh_kien_acc >= 0.728, f"linh_kien degraded below 72.8%: {linh_kien_acc*100:.1f}%"

    # 4. Verification: non-degenerate predictions (minority groups are actively predicted)
    assert predictions_counter["linh_kien"] > 50, "linh_kien minority group collapsed"
    assert predictions_counter["lap_rap"] >= 15, "lap_rap minority group collapsed"


def test_auto_classification_with_concrete_provenance():
    """Requirement (a): Auto-suggest process stage, cause group, and department with concrete provenance (căn cứ)."""
    # Case with component supplier keywords
    pred_lk = classify_error(
        error_code="C0030",
        phenomenon="Lỗi linh kiện sensor đọc giá trị bất thường sau khi thay board",
        investigation="Phẩm quản linh kiện supplier kiểm tra xác nhận lỗi lô linh kiện",
    )
    assert pred_lk.nhom_nguyen_nhan == "linh_kien"
    assert pred_lk.nhom_nguyen_nhan_vi == "Linh kiện"
    assert "nhom_nguyen_nhan" in pred_lk.can_cu
    assert "Khớp từ khóa" in pred_lk.can_cu["nhom_nguyen_nhan"]

    # Case with assembly keywords
    pred_lr = classify_error(
        error_code="",
        phenomenon="Máy kẹt giấy do công nhân quên cắm cáp và lắp sai vị trí cụm sấy",
        investigation="Kiểm tra phát hiện chưa vặn ốc và tuột cáp",
    )
    assert pred_lr.nhom_nguyen_nhan == "lap_rap"
    assert pred_lr.nhom_nguyen_nhan_vi == "Lắp ráp"
    assert "Khớp từ khóa" in pred_lr.can_cu["nhom_nguyen_nhan"]
    assert pred_lr.cong_doan in ("Lắp ráp", "In ấn", "Kiểm tra")

    # Case with lack of evidence: MUST declare "Không đủ căn cứ suy luận" instead of hallucinating
    pred_unknown = classify_error(
        error_code="",
        phenomenon="Máy có tiếng kêu lạ không rõ",
        investigation="",
    )
    assert pred_unknown.nhom_nguyen_nhan == "khac"
    assert "Chưa đủ căn cứ" in pred_unknown.can_cu["nhom_nguyen_nhan"]
    assert pred_unknown.can_cu["cong_doan"] == "Không đủ căn cứ suy luận"
    assert pred_unknown.can_cu["bo_phan"] == "Không đủ căn cứ suy luận"


def test_recurrence_alert_on_preview_card(tmp_path, monkeypatch):
    """Requirement (b): Recurrence alert on Preview Card matching historical cases and surfacing countermeasures."""
    # Setup isolated test DB with 2 prior cases for C7620
    test_db = tmp_path / "test_error_cases.db"
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    batch_id = start_batch(
        conn,
        source_file="test_recurrence.xlsx",
        file_sha256="0" * 64,
        sheet_name="test",
        sheet_type="Máy in",
    )
    upsert_case(
        conn,
        batch_id=batch_id,
        source_row=1,
        fields={
            "no_dvd": "KDTPS-2026-0042",
            "sheet_type": "Máy in",
            "department": "Bảo trì",
            "machine_type": "Iris-LSU",
            "line": "Line 2",
            "error_code_c": "C7620",
            "investigation": "Vệ sinh sensor nhiệt độ và thay dây cáp kết nối cụm sấy",
        },
    )
    upsert_case(
        conn,
        batch_id=batch_id,
        source_row=2,
        fields={
            "no_dvd": "KDTPS-2026-0043",
            "sheet_type": "Máy in",
            "department": "Bảo trì",
            "machine_type": "Iris-LSU",
            "line": "Line 2",
            "error_code_c": "C7620",
            "investigation": "Căn chỉnh lại tiếp điểm nguồn và kiểm tra nhiệt trở",
        },
    )
    conn.commit()

    # Recurrence detection test
    alert = detect_recurrence(conn, error_code="C7620", window_hours=168.0, threshold=2)
    assert alert is not None
    assert alert.count >= 2
    assert "Tái phát" in alert.message_vi
    assert alert.suggested_remedy is not None
    assert "Vệ sinh sensor" in alert.suggested_remedy or "Căn chỉnh" in alert.suggested_remedy
    assert alert.suggested_from in ("KDTPS-2026-0042", "KDTPS-2026-0043")

    # Wire into preview card
    monkeypatch.setattr("aios_habit.chat_action_error_lookup.resolve_db_path", lambda req: test_db)
    text = "Tạo vụ điều tra lỗi mới: máy báo mã lỗi C7620 ở Line 2"
    preview_md = render_preview_card_text(text, slots={}, conversation_id="CONV-REC-01")

    assert "CẢNH BÁO TÁI PHÁT" in preview_md
    assert "C7620" in preview_md
    assert "Đối sách đã áp dụng" in preview_md
    marker = extract_case_preview_marker(preview_md)
    assert marker is not None
    assert marker["is_recurrence"] is True
    assert marker["recurrence_count"] >= 2
    conn.close()


def test_user_confirmation_and_editing_without_silent_overwrite(tmp_path, monkeypatch):
    """Requirement (a): User can confirm or edit suggested labels before saving; never silently overwritten."""
    test_cases_dir = tmp_path / "local_cases"
    test_cases_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", test_cases_dir)
    monkeypatch.setattr("aios_habit.case_store.CASES_FILE", test_cases_dir / "cases.jsonl")
    monkeypatch.setattr("aios_habit.case_store.EVIDENCE_FILE", test_cases_dir / "evidence.jsonl")
    monkeypatch.setattr("aios_habit.case_store.ASSETS_DIR", test_cases_dir / "assets")
    monkeypatch.setattr("aios_habit.error_cases.autoclassify_feedback.LOCAL_CASES_DIR", test_cases_dir)
    monkeypatch.setattr("aios_habit.error_cases.autoclassify_feedback.LOCAL_FEEDBACK_FILE", test_cases_dir / "autoclassify_feedback.jsonl")

    # Preview data where auto-suggestion suggested 'khac', but reporter explicitly corrects to 'linh_kien' and 'Kiểm tra'
    preview_data = {
        "preview_id": "PREV-EDIT-001",
        "phenomenon": "Board mạch chập chờn không lên nguồn",
        "line": "Line 5",
        "machine_type": "Bizhub-550",
        "error_code": "C0040",
        "suggested_nhom_nguyen_nhan": "khac",
        "suggested_nhom_nguyen_nhan_vi": "Khác",
        "suggested_cong_doan": "Vận hành",
        "suggested_bo_phan": "Điện",
        # User explicitly edited before confirming:
        "confirmed_nhom_nguyen_nhan": "linh_kien",
        "confirmed_nhom_nguyen_nhan_vi": "Linh kiện",
        "confirmed_cong_doan": "Kiểm tra bo mạch",
        "confirmed_bo_phan": "Điện tử",
        "conversation_id": "CONV-EDIT-01",
    }

    result = execute_confirm_case(preview_data, conversation_id="CONV-EDIT-01")

    assert "Đã tạo thành công vụ điều tra" in result
    assert "Nhóm nguyên nhân:** **Linh kiện**" in result
    assert "Công đoạn:** Kiểm tra bo mạch" in result
    assert "Bộ phận phụ trách:** Điện tử" in result

    # Check that cases.jsonl stored the edited labels
    from aios_habit.case_store import load_cases
    cases = load_cases()
    assert len(cases) == 1
    stored_case = cases[0]
    assert "Linh kiện" in stored_case.current_situation
    assert "Kiểm tra bo mạch" in stored_case.current_situation


def test_continuous_improvement_feedback_loop_3_points(tmp_path, monkeypatch):
    """Requirement (d): 3-point continuous improvement loop (inline feedback, measurable metrics, review surface)."""
    test_cases_dir = tmp_path / "local_cases"
    test_cases_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("aios_habit.error_cases.autoclassify_feedback.LOCAL_CASES_DIR", test_cases_dir)
    monkeypatch.setattr("aios_habit.error_cases.autoclassify_feedback.LOCAL_FEEDBACK_FILE", test_cases_dir / "autoclassify_feedback.jsonl")

    # Point 1: Catch label feedback inline
    fid1 = log_autoclassify_suggestion(
        case_id="CASE-20261017-0001",
        suggested_nhom_nguyen_nhan="linh_kien",
        suggested_cong_doan="Kiểm tra",
        suggested_bo_phan="Điện",
        conversation_id="CONV-FB-01",
    )
    fid2 = log_autoclassify_suggestion(
        case_id="CASE-20261017-0002",
        suggested_nhom_nguyen_nhan="lap_rap",
        suggested_cong_doan="Lắp ráp",
        suggested_bo_phan="Cơ khí",
        conversation_id="CONV-FB-01",
    )
    fid3 = log_autoclassify_suggestion(
        case_id="CASE-20261017-0003",
        suggested_nhom_nguyen_nhan="khac",
        suggested_cong_doan="Vận hành",
        suggested_bo_phan="Bảo trì",
        conversation_id="CONV-FB-01",
    )

    # User rates the suggestions
    record_autoclassify_feedback(case_id="CASE-20261017-0001", rating="đúng", feedback_id=fid1)
    record_autoclassify_feedback(case_id="CASE-20261017-0002", rating="một phần", user_correction="Linh kiện", feedback_id=fid2)
    record_autoclassify_feedback(case_id="CASE-20261017-0003", rating="sai", user_correction="Thiết kế", feedback_id=fid3)

    records = load_all_feedback()
    assert len(records) == 3
    assert records[0]["rating"] == RATING_DUNG
    assert records[1]["rating"] == RATING_MOT_PHAN
    assert records[2]["rating"] == RATING_SAI

    # Point 2: Measurable metrics
    metrics = compute_autoclassify_metrics()
    assert metrics["total_cases_logged"] == 3
    assert metrics["total_rated"] == 3
    assert metrics["coverage_percent"] == 100.0
    # Positive rate = (đúng + một phần) / 3 = 2/3 = 66.7%
    assert metrics["accuracy_percent"] == 66.7
    assert metrics["ratings_count"][RATING_DUNG] == 1
    assert metrics["ratings_count"][RATING_MOT_PHAN] == 1
    assert metrics["ratings_count"][RATING_SAI] == 1

    # Point 3: Review surface
    summary_md = format_autoclassify_review_summary()
    assert "Bề Mặt Xem Lại Phân Loại Tự Động & Tái Phát" in summary_md
    assert "Tỷ lệ bao phủ phản hồi (Coverage):" in summary_md
    assert "100.0%" in summary_md
    assert "Độ chính xác ghi nhận từ người dùng:" in summary_md
    assert "66.7%" in summary_md
    assert "local_cases/autoclassify_feedback.jsonl" in summary_md


def test_chat_intent_routing_danh_gia_nhan_and_review():
    """Verify chat router routes label rating and review surface commands cleanly."""
    intent_dung, slots_dung = route("đúng nhãn")
    assert intent_dung == DANH_GIA_NHAN
    assert slots_dung["rating"] == "đúng"

    intent_sai, slots_sai = route("sai nhãn, sửa nhãn thành linh kiện")
    assert intent_sai == DANH_GIA_NHAN
    assert slots_sai["rating"] == "sai"
    assert slots_sai.get("correction") == "linh_kien"

    intent_review, slots_review = route("xem phản hồi phân loại")
    assert intent_review == XEM_PHAN_HOI
    assert slots_review.get("loai_phan_hoi") == "phan_loai"


def test_thiet_ke_split_and_accuracy_on_reconciled_db():
    """Ticket DESKTOP-HOME-STEP5-CLASSIFY-WEAK-CLASS-FIX Requirement 2.2 & 2.4:
    Build independent evaluation split for class 'thiet_ke' from reconciled DB (30,075 cases).
    Verify deterministic split (leakage == 0) and accuracy improvement over baseline (0.0%).
    """
    reconciled_db = Path("C:/tmp/kdtps_standard/error_cases_reconciled.db")
    if not reconciled_db.is_file():
        pytest.skip(f"Reconciled DB not found at {reconciled_db}")

    conn = sqlite3.connect(reconciled_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, no_dvd, cause, raw_json, phenomenon, investigation, countermeasure, machine_type, line, error_code_c, error_code_h, error_code_i FROM error_cases"
        ).fetchall()
        assert len(rows) == 30075, f"Expected 30075 cases in reconciled DB, found {len(rows)}"

        thiet_ke_cases: List[Dict[str, Any]] = []
        for r in rows:
            cause_val = str(r["cause"] or "").strip()
            grp = CAUSE_MAPPING.get(cause_val)
            if not grp and r["raw_json"]:
                try:
                    raw = json.loads(r["raw_json"])
                    y_val = str(raw.get("Y") or raw.get("要因") or "").strip()
                    grp = CAUSE_MAPPING.get(y_val)
                except Exception:
                    pass
            if grp == "thiet_ke":
                uid = f"reconciled_{r['id']}"
                thiet_ke_cases.append({
                    "uid": uid,
                    "id": r["id"],
                    "no_dvd": r["no_dvd"],
                    "machine_type": r["machine_type"] or "",
                    "line": r["line"] or "",
                    "error_code": r["error_code_c"] or r["error_code_h"] or r["error_code_i"] or "",
                    "phenomenon": r["phenomenon"] or "",
                    "investigation": r["investigation"] or "",
                    "countermeasure": r["countermeasure"] or "",
                    "expected_cause": "thiet_ke",
                    "raw_cause": cause_val,
                })

        assert len(thiet_ke_cases) == 80, f"Expected exactly 80 thiet_ke cases in DB, found {len(thiet_ke_cases)}"

        train_split: List[Dict[str, Any]] = []
        test_split: List[Dict[str, Any]] = []
        for c in thiet_ke_cases:
            h = hashlib.md5(c["uid"].encode("utf-8")).hexdigest()
            if int(h[:8], 16) % 10 < 2:
                test_split.append(c)
            else:
                train_split.append(c)

        assert len(train_split) == 58, f"Expected 58 train thiet_ke cases, got {len(train_split)}"
        assert len(test_split) == 22, f"Expected 22 test thiet_ke cases, got {len(test_split)}"

        # Verify zero leakage
        train_ids = {c["uid"] for c in train_split}
        test_ids = {c["uid"] for c in test_split}
        overlap = train_ids & test_ids
        assert len(overlap) == 0, f"Data leakage in thiet_ke split: {len(overlap)}"

        # Evaluate test split accuracy
        correct = 0
        pred_counter = Counter()
        for c in test_split:
            pred = classify_error(
                error_code=c["error_code"],
                phenomenon=c["phenomenon"],
                investigation=c["investigation"],
                machine_type=c["machine_type"],
                line=c["line"],
            )
            pred_counter[pred.nhom_nguyen_nhan] += 1
            if pred.nhom_nguyen_nhan == "thiet_ke":
                correct += 1

        accuracy = correct / len(test_split)
        print(f"\n[EVAL] Reconciled DB thiet_ke Test Accuracy: {accuracy*100:.2f}% ({correct}/{len(test_split)})")
        print(f"[EVAL] Predictions breakdown: {dict(pred_counter)}")

        # Verification: accuracy improved over 0.0% baseline, >= 40.0%
        assert accuracy >= 0.40, f"thiet_ke test accuracy ({accuracy*100:.2f}%) did not reach target >= 40%"
    finally:
        conn.close()


def test_c7620_recurrence_exact_count_control():
    """Ticket DESKTOP-HOME-STEP5-CLASSIFY-WEAK-CLASS-FIX Requirement 2.4:
    Preserve recurrence alert behavior and verify control case C7620 is exactly 136 times.
    """
    reconciled_db = Path("C:/tmp/kdtps_standard/error_cases_reconciled.db")
    if not reconciled_db.is_file():
        pytest.skip(f"Reconciled DB not found at {reconciled_db}")

    conn = sqlite3.connect(reconciled_db)
    try:
        alert = detect_recurrence(conn, error_code="C7620")
        assert alert is not None, "C7620 recurrence alert must fire"
        assert alert.count == 136, f"Expected exactly 136 occurrences for C7620, found {alert.count}"
        assert "136 lần" in alert.message_vi
        assert "FY27H2/263" in alert.message_vi
    finally:
        conn.close()
