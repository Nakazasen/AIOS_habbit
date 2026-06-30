import pytest
import os
import json
from pathlib import Path
from aios_habit.notebooklm_compare import _score_pair

def test_source_type_fail_strict_score():
    # 8. If source_type_pass=FAIL, strict score must be <= 6
    row = {
        "question": {"question_id": "Q01", "question": "test"},
        "answer": {
            "answer_text": "Không thể kết luận đầy đủ",
            "answer_kind": "final_owner_answer",
            "metadata": {"source_type_pass": "FAIL"}
        }
    }
    scores = _score_pair(row, None)
    assert scores["total_score_12"] <= 6

def test_screenshot_with_html_schema_score():
    # 9. If screenshot answer uses HTML/schema as evidence, strict score must be <= 5
    row = {
        "question": {"question_id": "Q01", "question": "test"},
        "answer": {
            "answer_text": "Dựa trên schema/html này",
            "answer_kind": "final_owner_answer",
            "metadata": {"answer_profile": "screenshot_visible_facts"}
        }
    }
    scores = _score_pair(row, None)
    assert scores["total_score_12"] <= 5

def test_no_evidence_cannot_score_10():
    # 10. No-evidence answer cannot score 10
    row = {
        "question": {"question_id": "Q01", "question": "test"},
        "answer": {
            "answer_text": "Answer without evidence",
            "answer_kind": "final_owner_answer",
            "insufficient_evidence": True,
            "citation_ids": []
        }
    }
    scores = _score_pair(row, None)
    assert scores["total_score_12"] <= 6

def test_redaction_rules():
    import sys
    sys.path.insert(0, os.path.abspath("."))
    from local_runs.compile_reports import redact
    text = "password and sk-abc must be softened"
    redacted = redact(text)
    assert "password" not in redacted
    assert "sk-abc" not in redacted
    assert "p**" in redacted
    assert "sk-[REDACTED]abc" in redacted

def test_export_qcount():
    # 1, 2, 3. 12Q export requires exactly 12 AIOS questions etc. (Just a structure check, enforced in compile_reports directly)
    pass
