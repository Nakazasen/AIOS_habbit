"""Native folder chooser for the local Windows-hosted Workspace Chat app."""
from __future__ import annotations

from pathlib import Path
from typing import Callable


def _open_native_folder_dialog() -> str:
    """Open the operating-system folder picker and return its selected path."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    try:
        root.withdraw()
        root.attributes("-topmost", True)
        root.update()
        return str(filedialog.askdirectory(title="Chọn thư mục tài liệu", mustexist=True) or "")
    finally:
        root.destroy()


def choose_local_folder(
    *,
    dialog: Callable[[], str] = _open_native_folder_dialog,
) -> tuple[str, str]:
    """Return ``(path, error_message)`` without scanning or importing files."""
    try:
        selected = str(dialog() or "").strip()
    except Exception:
        return "", "Không thể mở cửa sổ chọn thư mục. Bạn vẫn có thể dán đường dẫn thủ công."
    if not selected:
        return "", ""
    path = Path(selected)
    if not path.is_dir():
        return "", "Thư mục đã chọn không còn tồn tại hoặc không thể truy cập."
    return str(path), ""
