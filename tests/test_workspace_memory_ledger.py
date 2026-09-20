from pathlib import Path

import pytest

from aios_habit.workspace_memory_service import (
    LEDGER_SOFT_CAP,
    LEDGER_STALE_DAYS,
    append_memory_decision,
    forget_ledger_memory,
    list_ledger_memories,
    make_memory_decision,
)


def _confirm(tmp_path: Path, statement: str, scope: str = "xuong"):
    decision = make_memory_decision(
        action="confirm",
        statement=statement,
        scope=scope,
        evidence_refs=("user_confirm",),
        actor_label="To Truong",
        memory_id=None,
        title=statement[:40],
    )
    return append_memory_decision(decision, path=tmp_path / "memory_decisions.jsonl")


def test_ledger_lists_user_lessons_newest_style(tmp_path: Path):
    first = _confirm(tmp_path, "Do JIG hai lan, lay lan sau")
    items, _fallback = list_ledger_memories(
        "tri_thuc", decisions_path=tmp_path / "memory_decisions.jsonl"
    )
    user_items = [item for item in items if item["source_kind"] == "user_memory"]
    assert len(user_items) == 1
    assert user_items[0]["actor_label"] == "To Truong"
    assert user_items[0]["manageable"] is True
    assert user_items[0]["source_id"] == first.memory_id


def test_ledger_forget_removes_immediately_with_trail(tmp_path: Path):
    created = _confirm(tmp_path, "Quy tac tam de quen")
    forgotten = forget_ledger_memory(
        created.memory_id, "To Truong",
        decisions_path=tmp_path / "memory_decisions.jsonl",
    )
    assert forgotten.action == "forget"
    items, _fallback = list_ledger_memories(
        "tri_thuc", decisions_path=tmp_path / "memory_decisions.jsonl"
    )
    assert all(item["source_id"] != created.memory_id for item in items)


def test_ledger_forget_unknown_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        forget_ledger_memory(
            "khong-co", "To Truong",
            decisions_path=tmp_path / "memory_decisions.jsonl",
        )


def test_ledger_budgets_sane():
    assert LEDGER_SOFT_CAP == 200
    assert LEDGER_STALE_DAYS == 30
