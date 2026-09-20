from pathlib import Path

import pytest

from aios_habit.shared_mailbox import (
    append_request,
    is_local_store_folder,
    list_requests,
    mark_done,
)


def test_mailbox_roundtrip_per_store(tmp_path: Path):
    first = tmp_path / "kho-a"
    second = tmp_path / "kho-b"
    first.mkdir()
    second.mkdir()
    created = append_request(first, "Kho A", "them quy trinh thang 9", "To Truong Ca")
    assert created.status == "open"
    assert [item.request_id for item in list_requests(first)] == [created.request_id]
    assert list_requests(second) == []
    done = mark_done(first, created.request_id, "May Kho")
    assert done.status == "done"
    assert done.handled_by == "May Kho"
    assert done.handled_at != ""


def test_mailbox_rejects_empty_and_unknown(tmp_path: Path):
    folder = tmp_path / "kho"
    folder.mkdir()
    with pytest.raises(ValueError):
        append_request(folder, "Kho", "   ", "Ai Do")
    with pytest.raises(ValueError):
        append_request(folder, "Kho", "them tai lieu", "   ")
    with pytest.raises(ValueError):
        mark_done(folder, "khong-co", "May Kho")


def test_local_store_detection(tmp_path: Path, monkeypatch):
    import os

    monkeypatch.chdir(tmp_path)
    local_folder = tmp_path / "local_cases" / "kho"
    local_folder.mkdir(parents=True)
    assert is_local_store_folder(local_folder) is True
    assert is_local_store_folder(os.path.abspath(os.sep)) is False
