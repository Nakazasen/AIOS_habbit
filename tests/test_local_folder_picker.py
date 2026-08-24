from __future__ import annotations

from aios_habit.local_folder_picker import choose_local_folder


def test_choose_local_folder_returns_existing_directory(tmp_path) -> None:
    path, error = choose_local_folder(dialog=lambda: str(tmp_path))

    assert path == str(tmp_path)
    assert error == ""


def test_choose_local_folder_reports_cancel_without_error() -> None:
    path, error = choose_local_folder(dialog=lambda: "")

    assert path == ""
    assert error == ""


def test_choose_local_folder_reports_dialog_failure() -> None:
    def raise_dialog() -> str:
        raise RuntimeError("no desktop")

    path, error = choose_local_folder(dialog=raise_dialog)

    assert path == ""
    assert "Không thể mở" in error
