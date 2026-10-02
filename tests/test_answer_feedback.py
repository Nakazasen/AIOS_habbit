"""Tests cho answer_feedback: store JSONL, bat buoc ly do khi che, metric."""

import json

import pytest

from aios_habit import answer_feedback
from aios_habit.answer_feedback import (
    feedback_stats,
    get_feedback,
    iter_recent,
    record_feedback,
)


@pytest.fixture(autouse=True)
def _isolated_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    yield


def test_record_good_feedback_ok():
    result = record_feedback("conv1", "msg1", "cau hoi?", "cau tra loi", "huu_ich")
    assert result == {"ok": True}
    stored = get_feedback("conv1", "msg1")
    assert stored is not None
    assert stored["rating"] == "huu_ich"


def test_bad_feedback_requires_reason():
    result = record_feedback("conv1", "msg1", "cau hoi?", "cau tra loi", "chua_huu_ich")
    assert result["ok"] is False
    assert "lý do" in result["error_vi"]
    assert get_feedback("conv1", "msg1") is None


def test_bad_feedback_with_reason_ok():
    result = record_feedback(
        "conv1", "msg1", "cau hoi?", "cau tra loi", "chua_huu_ich", reason="tra loi thieu so lieu"
    )
    assert result["ok"] is True
    stored = get_feedback("conv1", "msg1")
    assert stored["reason"] == "tra loi thieu so lieu"


def test_invalid_rating_rejected():
    result = record_feedback("c", "m", "q", "a", "tam_duoc")
    assert result["ok"] is False


def test_long_texts_are_truncated():
    record_feedback("c", "m", "q" * 5000, "a" * 9000, "huu_ich")
    stored = get_feedback("c", "m")
    assert len(stored["question"]) <= answer_feedback.MAX_QUESTION_CHARS
    assert len(stored["answer_excerpt"]) <= answer_feedback.MAX_ANSWER_CHARS


def test_stats_counts_and_top_reasons():
    record_feedback("c", "m1", "q", "a", "huu_ich")
    record_feedback("c", "m2", "q", "a", "huu_ich")
    record_feedback("c", "m3", "q", "a", "chua_huu_ich", reason="thieu so lieu")
    record_feedback("c", "m4", "q", "a", "chua_huu_ich", reason="thieu so lieu")
    stats = feedback_stats()
    assert stats["total"] == 4
    assert stats["huu_ich"] == 2
    assert stats["chua_huu_ich"] == 2
    assert stats["ti_le_huu_ich"] == 0.5
    assert stats["top_ly_do_che"][0] == {"ly_do": "thieu so lieu", "so_lan": 2}


def test_stats_empty_is_zero():
    assert feedback_stats()["total"] == 0
    assert feedback_stats()["ti_le_huu_ich"] == 0.0


def test_iter_recent_respects_limit_and_skips_bad_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    path = answer_feedback.feedback_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"a": 1}\nnot json\n{"b": 2}\n', encoding="utf-8")
    assert len(iter_recent(limit=10)) == 2
    assert len(iter_recent(limit=1)) == 1


def test_never_writes_into_knowledge_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path))
    record_feedback("c", "m", "q", "a", "huu_ich")
    path = answer_feedback.feedback_file()
    assert path.name == "answer_feedback.jsonl"
    assert path.parent == tmp_path
    assert "tri_thuc" not in str(path) and "production" not in str(path)
