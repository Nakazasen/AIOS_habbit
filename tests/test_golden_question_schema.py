"""Tests for golden_question_schema: accept good forms, reject vague ones."""
from __future__ import annotations

import pytest

from aios_habit.golden_question_schema import (
    ENRICHMENT_LABEL,
    REVIEWER_STATUS_PENDING,
    GoldenAnswer,
    GoldenQuestion,
    GoldenSchemaError,
    answer_form_json_schema,
    parse_answer_line,
)


def _good_answer_dict(**overrides):
    data = {
        "answer_id": "GA-GQ-KB-20261002-FCALL-01-03-1",
        "question_id": "GQ-KB-20261002-FCALL-01-03",
        "gap_id": "GAP-KB-20261002-FCALL-01-F000",
        "case_ids": ["2023/183"],
        "error_code": "F000",
        "error_group": "F CALL",
        "phenomenon": "Khi khởi động, màn hình LCD hiển thị F000, máy dừng không vào chế độ vận hành",
        "answer_text": "Đo điện áp tại đầu vào bo mạch lúc khởi động: nếu trên 21.6V mà vẫn F000 thì loại H2, giữ H1; nếu dưới 21.6V thì ưu tiên H2, kiểm tra nguồn trước khi thay bo.",
        "answer_state": "answered",
        "hypotheses": ["H1: lỗi bo mạch điều khiển", "H2: sụt áp nguồn cấp lúc khởi động"],
        "causal_mechanism": "Sụt áp lúc khởi động → bo mạch reset giữa chừng → firmware báo F000 và khóa máy",
        "m4_branches": ["Machine"],
        "evidence_to_collect": ["Số đo điện áp lúc khởi động (đồng hồ/kẹp dòng)", "Log nguồn nếu có"],
        "confirm_criteria": "Đo dưới 21.6V tại 3 lần khởi động liên tiếp",
        "refute_criteria": "Đo trên 21.6V ổn định mà vẫn F000",
        "discriminate_notes": "Ngưỡng 21.6V phân biệt H1/H2: dưới ngưỡng thì H2, trên ngưỡng mà lỗi thì H1",
        "question_loai": "discriminator",
        "thresholds": [{"name": "điện áp khởi động tối thiểu", "value": "21.6", "unit": "V", "tolerance": "±5%"}],
        "temp_countermeasure": "Khởi động lại sau khi kiểm tra CB nguồn; ghi lại số đo",
        "perm_countermeasure": "chua_xac_dinh",
        "recurrence_condition": "Tái phát khi nguồn tổng xưởng sụt lúc giờ cao điểm",
        "needs_expert_review": ["perm_countermeasure", "recurrence_condition"],
        "confidence": 0.75,
        "reviewer_status": "cho_chuyen_gia_phan_hoi",
        "enrichment_label": ENRICHMENT_LABEL,
    }
    data.update(overrides)
    return data


def _good_question_dict(**overrides):
    data = {
        "question_id": "GQ-KB-TEST-01",
        "text": "Giữa hai giả thuyết 'lỗi bo mạch' và 'sụt áp nguồn', dấu hiệu đo được nào phân biệt được hai khả năng này?",
        "target_gap_id": "GAP-1",
        "target_case_ids": ["2023/183"],
        "loai_cau_hoi": "discriminator",
        "muc_tieu": "Buộc người trả lời đưa ra phép thử phân biệt.",
        "gia_thuyet_lien_quan": ["H1", "H2"],
        "expected_evidence": ["measurement", "log"],
        "diem": 87.5,
        "diem_thanh_phan": {"D": 1.0, "G": 0.8, "E": 1.0, "W": 0.5, "N": 0.9, "F": 1.0},
    }
    data.update(overrides)
    return data


def test_accept_good_answer():
    answer = GoldenAnswer.from_dict(_good_answer_dict())
    assert answer.enrichment_label == ENRICHMENT_LABEL
    assert answer.reviewer_status == REVIEWER_STATUS_PENDING
    assert answer.to_dict()["answer_id"] == "GA-GQ-KB-20261002-FCALL-01-03-1"


def test_reject_vague_answered_form_missing_causality():
    data = _good_answer_dict()
    data["causal_mechanism"] = ""
    data["hypotheses"] = []
    with pytest.raises(GoldenSchemaError) as exc_info:
        GoldenAnswer.from_dict(data)
    assert "nhân quả/bằng chứng" in str(exc_info.value)


def test_reject_answered_form_missing_evidence():
    data = _good_answer_dict()
    data["evidence_to_collect"] = []
    data["confirm_criteria"] = ""
    with pytest.raises(GoldenSchemaError):
        GoldenAnswer.from_dict(data)


def test_reject_discriminator_without_notes():
    data = _good_answer_dict()
    data["discriminate_notes"] = ""
    with pytest.raises(GoldenSchemaError) as exc_info:
        GoldenAnswer.from_dict(data)
    assert "discriminate_notes" in str(exc_info.value)


def test_uncertain_answer_requires_needs_expert_review():
    data = _good_answer_dict(answer_state="uncertain", confidence=0.5)
    data["hypotheses"] = []
    data["causal_mechanism"] = ""
    data["m4_branches"] = []
    data["evidence_to_collect"] = []
    data["confirm_criteria"] = ""
    answer = GoldenAnswer.from_dict(data)  # structural causality not required
    assert answer.answer_state == "uncertain"

    data2 = _good_answer_dict(answer_state="uncertain", confidence=0.5, needs_expert_review=[])
    data2["hypotheses"] = []
    data2["causal_mechanism"] = ""
    data2["m4_branches"] = []
    data2["evidence_to_collect"] = []
    data2["confirm_criteria"] = ""
    with pytest.raises(GoldenSchemaError) as exc_info:
        GoldenAnswer.from_dict(data2)
    assert "needs_expert_review" in str(exc_info.value)


def test_reject_forbidden_llm_source_fields():
    data = _good_answer_dict(answered_by="copilot", model_name="gpt-4")
    with pytest.raises(GoldenSchemaError) as exc_info:
        GoldenAnswer.from_dict(data)
    assert "LLM" in str(exc_info.value)


def test_reject_wrong_enrichment_label():
    data = _good_answer_dict(enrichment_label="kiến thức chuyên gia")
    with pytest.raises(GoldenSchemaError):
        GoldenAnswer.from_dict(data)


def test_reject_bad_confidence_and_short_text():
    data = _good_answer_dict(confidence=1.5)
    with pytest.raises(GoldenSchemaError):
        GoldenAnswer.from_dict(data)
    data = _good_answer_dict(answer_text="quá ngắn")
    with pytest.raises(GoldenSchemaError):
        GoldenAnswer.from_dict(data)


def test_reject_skipped_state_in_batch():
    data = _good_answer_dict(answer_state="skipped")
    with pytest.raises(GoldenSchemaError):
        GoldenAnswer.from_dict(data)


def test_reject_bad_threshold_shape():
    data = _good_answer_dict(thresholds=[{"name": "x"}])
    with pytest.raises(GoldenSchemaError):
        GoldenAnswer.from_dict(data)


def test_reject_invalid_m4_branch():
    data = _good_answer_dict(m4_branches=["Robot"])
    with pytest.raises(GoldenSchemaError):
        GoldenAnswer.from_dict(data)


def test_accept_good_question_and_reject_bad_loai():
    question = GoldenQuestion.from_dict(_good_question_dict())
    assert question.diem == 87.5
    with pytest.raises(GoldenSchemaError):
        GoldenQuestion.from_dict(_good_question_dict(loai_cau_hoi="tu_bia"))
    with pytest.raises(GoldenSchemaError):
        GoldenQuestion.from_dict(_good_question_dict(target_case_ids=[]))
    # Scored question must carry all six components.
    with pytest.raises(GoldenSchemaError):
        GoldenQuestion.from_dict(_good_question_dict(diem_thanh_phan={"D": 1.0}))


def test_answer_form_json_schema_contract():
    schema = answer_form_json_schema()
    assert "answer_text" in schema["required"]
    assert "causal_mechanism" in schema["conditionally_required_when_answered"]
    assert "answered_by" in schema["forbidden_fields"]
    assert schema["enrichment_label"] == ENRICHMENT_LABEL


def test_parse_answer_line_round_trip():
    import json

    line = json.dumps(_good_answer_dict(), ensure_ascii=False)
    answer = parse_answer_line(line)
    assert answer.answer_id.startswith("GA-")
    with pytest.raises(GoldenSchemaError):
        parse_answer_line("{not json")
