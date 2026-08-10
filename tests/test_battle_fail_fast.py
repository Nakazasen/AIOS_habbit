from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from battle_notebooklm_rag_v2 import ProgressHeartbeat, assess_fail_fast, write_stopped_early_report  # noqa: E402


def test_fail_fast_waits_for_minimum_sample_then_stops_on_unusable_rate() -> None:
    rows = [{"question_id": f"q-{index}", "status": "success", "expected_type": "answerable", "item_count": 0, "answer_mode": "abstain"} for index in range(3)]
    assert assess_fail_fast(rows[:2])["should_stop"] is False
    decision = assess_fail_fast(rows)
    assert decision["should_stop"] is True
    assert decision["reasons"] == ["unusable_answerable_rate_exceeded"]
    assert decision["unusable_rate"] == 1.0


def test_fail_fast_stops_immediately_on_false_support() -> None:
    decision = assess_fail_fast([{"question_id": "q-risk", "score": {"expected_answer_type": "insufficient", "false_support": True}}])
    assert decision["should_stop"] is True
    assert "false_support_detected" in decision["reasons"]


def test_stopped_early_report_and_progress_heartbeat(tmp_path: Path) -> None:
    progress_path = tmp_path / "progress.json"
    with ProgressHeartbeat(progress_path, stage="unit_test", total=4, interval_seconds=0.05) as progress:
        progress.update(completed=1, current="q-1")
        time.sleep(0.12)
        snapshot = json.loads(progress_path.read_text(encoding="utf-8"))
        assert snapshot["status"] == "RUNNING"
        assert snapshot["completed"] == 1
        progress.mark_stopped_early()
    final_snapshot = json.loads(progress_path.read_text(encoding="utf-8"))
    assert final_snapshot["status"] == "STOPPED_EARLY"
    result = write_stopped_early_report(tmp_path, run_id="run-test", stage="unit_test", decision={"should_stop": True, "reasons": ["false_support_detected"]}, completed_rows=[{"question_id": "q-1"}], total=4)
    assert result["status"] == "STOPPED_EARLY"
    report = json.loads((tmp_path / "stopped_early_report.json").read_text(encoding="utf-8"))
    assert report["remaining"] == 3
    assert report["analysis"]["safe_to_promote"] is False
    assert (tmp_path / "partial_results.jsonl").is_file()
