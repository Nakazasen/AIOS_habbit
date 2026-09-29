"""Tests for the TOOL-4 chat action running LSU Iris shadow-risk prediction."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from aios_habit import chat_action
from aios_habit import chat_action_prediction
from aios_habit.chat_action import ChatActionRequest
from aios_habit.chat_action_prediction import ACTION_NAME
from aios_habit.feature_flags import reset_feature_flags
from aios_habit.production_prediction.evaluation import ReplayProtocol
from aios_habit.production_prediction.lsu_iris import (
    evaluate_data_gate_rubric,
    join_lsu_trace,
    normalize_records,
    read_lsu_source,
)
from aios_habit.production_prediction.repository import ProductionPredictionRepository

FIXTURE_BASE = Path(__file__).parent / "fixtures" / "lsu_iris"


@pytest.fixture(autouse=True)
def _clean_state():
    reset_feature_flags()
    chat_action.reset_actions()
    yield
    reset_feature_flags()
    chat_action.reset_actions()


def _load_fixture(fixture: str):
    snapshot = read_lsu_source(
        FIXTURE_BASE / fixture / "component_lots.csv",
        FIXTURE_BASE / fixture / "unit_lots.csv",
        FIXTURE_BASE / fixture / "jig_outcomes.csv",
    )
    normalized = normalize_records(snapshot)
    traces = join_lsu_trace(normalized)
    return snapshot, normalized, traces


def _build_store(tmp_path: Path, fixture: str = "time_series") -> Path:
    db_path = tmp_path / "pred.sqlite"
    snapshot, normalized, traces = _load_fixture(fixture)
    gate_report = evaluate_data_gate_rubric(snapshot, normalized, traces)
    repo = ProductionPredictionRepository(db_path)
    assert repo.register_lsu_snapshot(normalized, gate_report) is True
    return db_path


def _fast_protocol() -> ReplayProtocol:
    return ReplayProtocol.default_lsu_iris(baseline_minimum_points=2, control_limit_std=1.0)


def _ask(question: str, db_path: Path):
    chat_action.load_builtin_actions()
    outcome = chat_action.dispatch(
        ChatActionRequest(question=question, context={"prediction_db_path": str(db_path)})
    )
    assert outcome is not None
    return outcome


def _render(outcome) -> str:
    return chat_action.render_outcome(outcome)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_builtin_registry_includes_prediction_module():
    assert "aios_habit.chat_action_prediction" in chat_action.BUILTIN_ACTION_MODULES
    chat_action.load_builtin_actions()
    assert ACTION_NAME in [action.name for action in chat_action.registered_actions()]


@pytest.mark.parametrize(
    "question",
    (
        "Dự đoán rủi ro cho SYN_UNIT_001",
        "du doan rui ro SYN_UNIT_001",
        "Chạy dự đoán lỗi SYN_UNIT_001",
    ),
)
def test_action_matches_accented_and_unaccented_questions(tmp_path, question):
    outcome = _ask(question, _build_store(tmp_path))
    assert outcome.action == ACTION_NAME


def test_unrelated_question_is_not_handled(tmp_path):
    chat_action.load_builtin_actions()
    assert (
        chat_action.dispatch(
            ChatActionRequest(
                question="Tóm tắt tài liệu này giúp tôi",
                context={"prediction_db_path": str(_build_store(tmp_path))},
            )
        )
        is None
    )


def test_missing_store_returns_guidance_and_creates_nothing(tmp_path):
    db_path = tmp_path / "missing.sqlite"
    rendered = _render(_ask("Dự đoán rủi ro", db_path))
    assert "chưa có kho dự đoán cục bộ" in rendered
    assert not db_path.exists()


def test_empty_store_returns_guidance(tmp_path):
    db_path = tmp_path / "empty.sqlite"
    ProductionPredictionRepository(db_path)
    rendered = _render(_ask("Dự đoán rủi ro", db_path))
    assert "chưa có gói dữ liệu nào" in rendered


def test_unit_question_shows_trace_and_single_unit_run(tmp_path, monkeypatch):
    monkeypatch.setattr(chat_action_prediction, "_protocol", _fast_protocol)
    rendered = _render(_ask("Dự đoán rủi ro cho SYN_UNIT_001", _build_store(tmp_path)))
    assert "Hồ sơ đơn vị “SYN_UNIT_001”" in rendered
    assert "Mã lô" in rendered
    assert "Kết quả đo JIG" in rendered
    assert "đã xử lý 1/1 đơn vị" in rendered


def test_unknown_target_returns_guidance(tmp_path):
    rendered = _render(_ask("Dự đoán rủi ro cho SYN_UNIT_999", _build_store(tmp_path)))
    assert "Không tìm thấy gói dữ liệu hoặc mã đơn vị" in rendered
    assert "SYN_UNIT_999" in rendered


def test_latest_snapshot_run_reports_risk_table(tmp_path, monkeypatch):
    monkeypatch.setattr(chat_action_prediction, "_protocol", _fast_protocol)
    rendered = _render(_ask("Dự đoán rủi ro", _build_store(tmp_path)))
    assert "toàn bộ đơn vị trong gói" in rendered
    assert "đã xử lý 15/15 đơn vị" in rendered
    assert "Mức rủi ro" in rendered
    assert "Cần kiểm tra" in rendered


def test_snapshot_id_question_selects_named_package(tmp_path, monkeypatch):
    monkeypatch.setattr(chat_action_prediction, "_protocol", _fast_protocol)
    db_path = _build_store(tmp_path)
    repo = ProductionPredictionRepository(db_path, read_only=True)
    snapshot_id = str(repo.list_snapshots()[0]["snapshot_id"])
    rendered = _render(_ask(f"Dự đoán gói {snapshot_id[:12]}", db_path))
    assert "toàn bộ đơn vị trong gói" in rendered


def test_default_protocol_reports_no_alerts(tmp_path):
    rendered = _render(_ask("Dự đoán rủi ro", _build_store(tmp_path)))
    assert "Không phát hiện đơn vị nào vượt ngưỡng" in rendered


def test_read_only_repository_never_writes_or_backs_up(tmp_path):
    db_path = _build_store(tmp_path)
    other_snapshot, other_normalized, other_traces = _load_fixture("valid")
    other_gate = evaluate_data_gate_rubric(other_snapshot, other_normalized, other_traces)
    before = {path.name for path in tmp_path.iterdir()}
    repo = ProductionPredictionRepository(db_path, read_only=True)
    assert len(repo.list_snapshots()) == 1
    assert {path.name for path in tmp_path.iterdir()} == before
    with pytest.raises(sqlite3.OperationalError):
        repo.register_lsu_snapshot(other_normalized, other_gate)


def test_dispatch_is_read_only_and_creates_no_backup(tmp_path, monkeypatch):
    monkeypatch.setattr(chat_action_prediction, "_protocol", _fast_protocol)
    db_path = _build_store(tmp_path)
    before = _sha(db_path)
    before_files = {path.name for path in tmp_path.iterdir()}
    _ask("Dự đoán rủi ro", db_path)
    assert _sha(db_path) == before
    assert {path.name for path in tmp_path.iterdir()} == before_files


def test_handle_chat_text_saves_prediction_bubble(tmp_path, monkeypatch):
    monkeypatch.setattr(chat_action_prediction, "_protocol", _fast_protocol)
    db_path = _build_store(tmp_path)
    saved: list[tuple[str, str]] = []
    handled = chat_action.handle_chat_text(
        "Dự đoán rủi ro cho SYN_UNIT_001",
        conversation_id="C1",
        context={"prediction_db_path": str(db_path)},
        save_user=lambda content: saved.append(("user", content)),
        save_assistant=lambda content: saved.append(("assistant", content)),
    )
    assert handled is True
    assert [role for role, _ in saved] == ["user", "assistant"]
    assert "Dự đoán rủi ro (LSU Iris)" in saved[1][1]
    assert "SYN_UNIT_001" in saved[1][1]
