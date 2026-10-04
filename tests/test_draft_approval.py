"""Tests for draft_approval: PIN, label swap, log, versions, metrics."""

import pytest

from aios_habit import draft_approval as approval
from aios_habit.answer_draft_fallback import DRAFT_LABEL


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_LOCAL_CASES_DIR", str(tmp_path / "local_cases"))
    monkeypatch.delenv(approval.FLAG_ENV_KEY, raising=False)
    approval.clear_draft_approval_override()
    yield
    approval.clear_draft_approval_override()


def test_flag_defaults_off_and_can_turn_on(monkeypatch):
    assert approval.draft_approval_enabled() is False
    monkeypatch.setenv(approval.FLAG_ENV_KEY, "1")
    assert approval.draft_approval_enabled() is True
    approval.set_draft_approval_override(False)
    assert approval.draft_approval_enabled() is False


def test_pin_format_and_error_has_no_hint():
    assert approval.pin_format_ok("1234") is True
    assert approval.pin_format_ok("123456") is True
    assert approval.pin_format_ok("123") is False
    assert approval.pin_format_ok("1234567") is False
    assert approval.pin_format_ok("12a4") is False
    bad = approval.set_pin("12a")
    assert bad["ok"] is False
    assert "4" in bad["error_vi"]


def test_pin_roundtrip_and_wrong_has_no_hint():
    assert approval.set_pin("4826")["ok"] is True
    assert approval.verify_pin("4826")["ok"] is True
    bad = approval.verify_pin("0000")
    assert bad["ok"] is False
    assert "PIN" in bad["error_vi"]
    # Must not leak the real PIN or any hint.
    assert "4826" not in bad["error_vi"]


def test_pin_lock_after_repeated_failures():
    assert approval.set_pin("7712")["ok"] is True
    for _ in range(approval.MAX_FAILED_ATTEMPTS):
        approval.verify_pin("0000")
    assert approval.is_locked() is True
    locked = approval.verify_pin("7712")
    assert locked["ok"] is False


def test_approve_swaps_label_and_logs_three_fields():
    answer = "Nội dung đáp.\n\n" + DRAFT_LABEL
    labeled = approval.apply_approval_label(answer, "Cô Lan", "2026-10-05")
    assert labeled["ok"] is True
    assert labeled["label"] == "Đã duyệt bởi Cô Lan, ngày 2026-10-05"
    assert approval.is_draft_answer(answer) is True
    assert approval.is_approved_answer(labeled["answer_text"]) is True
    saved = approval.record_decision("mom/batch-01.md#1", "Cô Lan", "approved")
    rec = saved["record"]
    assert rec["pair_id"] == "mom/batch-01.md#1"
    assert rec["reviewer_name"] == "Cô Lan"
    assert rec["decided_at"]
    assert approval.read_decisions()[-1]["pair_id"] == "mom/batch-01.md#1"


def test_reject_requires_reason():
    missing = approval.record_decision("p1", "Anh Minh", "rejected", reason="")
    assert missing["ok"] is False
    ok = approval.record_decision("p1", "Anh Minh", "rejected", reason="Thiếu nguồn.")
    assert ok["ok"] is True


def test_revise_keeps_old_version():
    old = "Đáp cũ.\n\n" + DRAFT_LABEL
    new = "Đáp mới đã sửa."
    kept = approval.create_revised_version("p9", old, new, "Cô Lan")
    assert kept["ok"] is True
    assert kept["record"]["version"] == 1
    kept2 = approval.create_revised_version("p9", new, new + " thêm.", "Cô Lan")
    assert kept2["record"]["version"] == 2
    versions = approval.get_versions("p9")
    assert len(versions) == 2
    assert versions[0]["old_answer"] == old


def test_unapprove_restores_draft_label():
    answer = "Nội dung.\n\n" + DRAFT_LABEL
    labeled = approval.apply_approval_label(answer, "Cô Lan", "2026-10-05")
    restored = approval.remove_approval_label(labeled["answer_text"])
    assert restored["ok"] is True
    assert DRAFT_LABEL in restored["answer_text"]


def test_metrics_per_batch_counts_approved_rejected_pending():
    approval.record_decision("mom/batch-01.md#1", "A", "approved", source_file="mom/batch-01.md")
    approval.record_decision("mom/batch-01.md#2", "A", "rejected", reason="Sai.", source_file="mom/batch-01.md")
    approval.record_decision("lsu/batch-16.md#1", "A", "revised", source_file="lsu/batch-16.md")
    metrics = approval.compute_approval_metrics(total_tracked=4)
    assert metrics.approved == 2
    assert metrics.rejected == 1
    assert metrics.pending == 1
    assert metrics.approval_rate == 0.5
    assert metrics.by_batch["batch-01"]["da_duyet"] == 1
    hints = approval.approval_review_hints(metrics)
    assert hints


def test_chat_action_returns_none_when_flag_off():
    from aios_habit.chat_action_draft_approval import _handler
    from aios_habit.chat_action import ChatActionRequest

    req = ChatActionRequest(question="liệt kê bản thảo chưa duyệt", conversation_id="c1")
    assert _handler(req) is None
