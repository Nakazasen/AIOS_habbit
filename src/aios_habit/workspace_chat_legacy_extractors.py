"""Local-only readers for legacy Office and Outlook message files."""

from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from aios_habit.document_extractors import extract_text_chunks_from_file


def extract_legacy_ppt(path: Path) -> tuple[str, str]:
    """Convert an old ``.ppt`` with installed PowerPoint, then extract slide text."""
    with TemporaryDirectory(prefix="aios_ppt_") as folder:
        output = Path(folder) / "converted.pptx"
        script = (
            "$ErrorActionPreference='Stop';"
            "$a=New-Object -ComObject PowerPoint.Application; $p=$null;"
            "try {$p=$a.Presentations.Open($args[0],$false,$true,$false);"
            "$p.SaveAs($args[1],24)} finally {if($p){$p.Close()};$a.Quit()}"
        )
        try:
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script, str(path), str(output)],
                check=True, capture_output=True, text=True, timeout=90,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            return "", "Không thể mở PowerPoint để đọc file .ppt cũ."
        if not output.is_file():
            return "", "PowerPoint không tạo được bản đọc cho file .ppt."
        text = "\n\n".join(
            str(chunk.get("text") or "").strip()
            for chunk in extract_text_chunks_from_file(output)
            if str(chunk.get("text") or "").strip()
        )
        return (text, "") if text else ("", "File .ppt không có nội dung chữ để đọc.")


def extract_outlook_msg(path: Path) -> tuple[str, str]:
    """Read the normal email fields from a local Outlook ``.msg`` file."""
    try:
        import extract_msg
    except ImportError:
        return "", "Thiếu bộ đọc email Outlook .msg trên máy này."
    try:
        message = extract_msg.openMsg(str(path))
        try:
            fields = (
                ("Tiêu đề", getattr(message, "subject", "")),
                ("Người gửi", getattr(message, "sender", "")),
                ("Ngày gửi", getattr(message, "date", "")),
                ("Nội dung", getattr(message, "body", "")),
            )
            text = "\n".join(f"{name}: {value}" for name, value in fields if str(value or "").strip()).strip()
        finally:
            message.close()
    except Exception:
        return "", "Không thể đọc email .msg này."
    return (text, "") if text else ("", "Email .msg không có nội dung chữ để đọc.")
