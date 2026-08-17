import json
import logging
from pathlib import Path

import pytest

from aios_habit import local_jsonl


def test_load_jsonl_warns_without_exposing_record_contents(tmp_path, caplog):
    path = tmp_path / "records.jsonl"
    path.write_text('{not json}\n{"id": "valid"}\n', encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="aios_habit.local_jsonl"):
        records = local_jsonl.load_jsonl_records(path, lambda record: record["id"])

    assert records == ["valid"]
    assert "records.jsonl at line 1" in caplog.text
    assert "{not json}" not in caplog.text


def test_atomic_write_jsonl_replaces_complete_file(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text('{"id": "old"}\n', encoding="utf-8")

    local_jsonl.atomic_write_jsonl(path, [{"id": "new"}])

    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [{"id": "new"}]
    assert not list(tmp_path.glob("*.tmp"))


def test_batch_write_rolls_back_a_partial_replacement(tmp_path, monkeypatch):
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    first.write_text('{"id": "first-old"}\n', encoding="utf-8")
    second.write_text('{"id": "second-old"}\n', encoding="utf-8")
    original_first = first.read_bytes()
    original_second = second.read_bytes()
    real_replace = local_jsonl.os.replace

    def fail_second_replacement(source, destination):
        if Path(destination) == second and str(source).endswith(".tmp"):
            raise OSError("simulated replacement failure")
        return real_replace(source, destination)

    monkeypatch.setattr(local_jsonl.os, "replace", fail_second_replacement)

    with pytest.raises(OSError, match="simulated replacement failure"):
        local_jsonl.atomic_write_jsonl_batch(((first, [{"id": "first-new"}]), (second, [{"id": "second-new"}])))

    assert first.read_bytes() == original_first
    assert second.read_bytes() == original_second
    assert not list(tmp_path.glob(".*.tmp"))
    assert not list(tmp_path.glob(".*.bak"))
