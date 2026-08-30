"""Native folder chooser for the local Windows-hosted Workspace Chat app."""
from __future__ import annotations

from pathlib import Path
from typing import Callable


def _open_native_folder_dialog(title: str = "Chọn thư mục tài liệu") -> str:
    """Open the operating-system folder picker and return its selected path."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    try:
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        return str(filedialog.askdirectory(title=title, mustexist=True) or "")
    finally:
        root.destroy()


def choose_local_folder(
    *,
    dialog: Callable[[], str] | None = None,
    title: str = "Chọn thư mục tài liệu",
) -> tuple[str, str]:
    """Return ``(path, error_message)`` without scanning or importing files."""
    opener = dialog if dialog is not None else (lambda: _open_native_folder_dialog(title))
    try:
        selected = str(opener() or "").strip()
    except Exception:
        return "", "Không thể mở cửa sổ chọn thư mục. Bạn vẫn có thể dán đường dẫn thủ công."
    if not selected:
        return "", ""
    path = Path(selected)
    if not path.is_dir():
        return "", "Thư mục đã chọn không còn tồn tại hoặc không thể truy cập."
    return str(path), ""
