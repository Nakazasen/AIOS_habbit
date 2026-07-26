import json
from pathlib import Path
import subprocess
import sys

from aios_habit.rag_v2 import SourceSpec


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rag_v2_dev.py"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_dev_cli_help_has_local_commands_and_no_credential_surface():
    result = _run("--help")
    output = result.stdout.lower()
    assert result.returncode == 0
    assert all(command in output for command in ("ingest", "query", "inspect", "evaluate"))
    assert "local-only" in output
    assert "api-key" not in output
    assert "provider" in output  # truthful no-provider description only


def test_dev_cli_end_to_end_incremental_query_and_safe_inspect(tmp_path):
    runtime = tmp_path / "runtime"
    source = tmp_path / "guide.txt"
    raw_text = "Synthetic release protocol uses a bounded verification checklist."
    source.write_text(raw_text, encoding="utf-8")
    common = ("--runtime-root", runtime)

    first = _run(*common, "ingest", "--source", source)
    second = _run(*common, "ingest", "--source", source)
    query = _run(*common, "query", "bounded verification", "--source", source)
    inspect = _run(*common, "inspect", "--source", source)

    assert first.returncode == second.returncode == query.returncode == inspect.returncode == 0
    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    query_payload = json.loads(query.stdout)
    inspect_payload = json.loads(inspect.stdout)
    assert first_payload["converted_count"] == 1
    assert second_payload["skipped_count"] == 1
    assert query_payload["provider_used"] is False
    assert query_payload["item_count"] == 1
    assert query_payload["items"][0]["source_name"] == "guide.txt"
    assert inspect_payload["mode"] == "local_only"
    assert str(source) not in inspect.stdout
    assert raw_text not in inspect.stdout
    assert (runtime / "rag_v2_dev.sqlite").is_file()


def test_dev_cli_evaluate_uses_selected_sources_and_returns_local_metrics(tmp_path):
    runtime = tmp_path / "runtime"
    source = tmp_path / "reference.txt"
    source.write_text("A synthetic archive contains the delta procedure.", encoding="utf-8")
    document_id = SourceSpec(source).document_id
    questions = tmp_path / "questions.json"
    questions.write_text(json.dumps({"questions": [
        {
            "question_id": "answerable-1",
            "question": "delta procedure",
            "expected_answer_type": "answerable",
            "expected_document_ids": [document_id],
            "expected_source_names": ["reference.txt"],
            "expected_privacy": "local_only",
        },
        {
            "question_id": "insufficient-1",
            "question": "nonexistent omega protocol",
            "expected_answer_type": "insufficient",
        },
    ]}), encoding="utf-8")

    ingest = _run("--runtime-root", runtime, "ingest", "--source", source)
    evaluate = _run(
        "--runtime-root", runtime,
        "evaluate", "--questions", questions, "--source", source,
    )

    assert ingest.returncode == 0
    assert evaluate.returncode == 0
    payload = json.loads(evaluate.stdout)
    assert payload["mode"] == "local_only"
    assert payload["provider_used"] is False
    assert payload["question_count"] == 2
    assert payload["retrieval_hit_rate"] == 1.0
    assert payload["privacy_pass_rate"] == 1.0
    assert payload["pass_fail"] == "PASS"


def test_dev_cli_missing_source_is_fail_soft_and_nonzero(tmp_path):
    result = _run(
        "--runtime-root", tmp_path / "runtime",
        "ingest", "--source", tmp_path / "missing.txt",
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["failed_count"] == 1
    assert payload["items"][0]["warning_codes"] == ["source_unavailable"]
