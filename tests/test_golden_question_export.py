"""Tests for golden_question_export: batch files + manifest SHA-256 round-trip."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aios_habit.golden_question_export import (
    FIXTURE_LABEL,
    export_batch,
    fixture_phenomena,
    load_phenomena_json,
    main,
)
from aios_habit.golden_question_schema import parse_question_line


def _exported(tmp_path: Path, batch_id: str = "KB-EXPORT-TEST"):
    phenomena = fixture_phenomena(batch_id)
    return export_batch(batch_id, phenomena, tmp_path / "batch", data_source_label=FIXTURE_LABEL)


def test_export_produces_three_files(tmp_path: Path):
    exported = _exported(tmp_path)
    assert exported.questions_path.exists()
    assert exported.form_path.exists()
    assert exported.manifest_path.exists()
    assert exported.total_questions == 25  # 5 phenomena x (3 + constraint fill)


def test_question_ids_unique_batch_wide(tmp_path: Path):
    exported = _exported(tmp_path)
    manifest = json.loads(exported.manifest_path.read_text(encoding="utf-8"))
    assert len(set(manifest["question_ids"])) == len(manifest["question_ids"])


def test_manifest_sha256_round_trip(tmp_path: Path):
    exported = _exported(tmp_path)
    manifest = json.loads(exported.manifest_path.read_text(encoding="utf-8"))
    assert manifest["batch_id"] == "KB-EXPORT-TEST"
    assert manifest["version"] == 1
    assert len(manifest["question_ids"]) == exported.total_questions

    for entry in manifest["files"]:
        path = exported.out_dir / entry["name"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], "SHA-256 mismatch for %s" % entry["name"]
    batch_digest = hashlib.sha256(
        "|".join(sorted(e["sha256"] for e in manifest["files"])).encode("utf-8")
    ).hexdigest()
    assert batch_digest == manifest["batch_sha256"]


def test_jsonl_lines_parse_and_link_cases(tmp_path: Path):
    from aios_habit.golden_question_schema import FORBIDDEN_SOURCE_FIELDS

    exported = _exported(tmp_path)
    lines = exported.questions_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == exported.total_questions
    for line in lines:
        payload = json.loads(line)
        question = parse_question_line(line)
        assert question.question_id in payload["question"]["question_id"]
        assert payload["case_context"]["case_ids"]  # >= 1 real (fixture) case
        assert payload["answer_form_schema"]["enrichment_label"]
        # No LLM-source field stored as actual data (the schema's
        # forbidden_fields list is documentation, not stored data).
        for section in ("question", "case_context", "gap_context"):
            assert not (set(payload[section].keys()) & set(FORBIDDEN_SOURCE_FIELDS))
        for hyp in payload["hypotheses"]:
            assert not (set(hyp.keys()) & set(FORBIDDEN_SOURCE_FIELDS))


def test_markdown_form_has_sections_and_empty_forms(tmp_path: Path):
    exported = _exported(tmp_path)
    text = exported.form_path.read_text(encoding="utf-8")
    assert text.count("## Hiện tượng:") == 5
    assert "Work IQ" in text and "Think deeper" in text
    # Empty form per question follows the GoldenAnswer schema fields.
    assert text.count("causal_mechanism:") == exported.total_questions
    assert text.count("discriminate_notes:") == exported.total_questions
    assert FIXTURE_LABEL in text


def test_load_phenomena_json(tmp_path: Path):
    payload = {
        "phenomena": [
            {
                "error_code": "F001",
                "phenomenon": "Hiện tượng thật từ DB",
                "case_ids": ["DB-1"],
                "error_group": "F CALL",
                "hypotheses": [{"hypothesis_id": "H1", "text": "giả thuyết 1"}],
            }
        ]
    }
    path = tmp_path / "phenomena.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    phenomena = load_phenomena_json(path, "KB-JSON")
    assert len(phenomena) == 1
    assert phenomena[0].error_code == "F001"
    exported = export_batch("KB-JSON", phenomena, tmp_path / "out")
    assert exported.total_questions >= 3


def test_cli_fixture_mode(tmp_path: Path):
    out_dir = tmp_path / "cli_batch"
    code = main(["--fixture", "--out-dir", str(out_dir), "--batch-id", "KB-CLI"])
    assert code == 0
    assert (out_dir / "batch_KB-CLI_questions.jsonl").exists()
    assert (out_dir / "batch_KB-CLI_phieu_hoi.md").exists()
    assert (out_dir / "batch_KB-CLI_manifest.json").exists()


def test_cli_requires_source(tmp_path: Path, capsys):
    code = main(["--out-dir", str(tmp_path / "x")])
    assert code == 2
