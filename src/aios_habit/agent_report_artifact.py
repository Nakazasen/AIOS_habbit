"""UI helpers for the agent-report attachment card (UX-AGENT-REPORT, option A).

- The "Tai ve" (download) button is format-aware: .docx/.pptx are served as
  binary so the machine opens them in Word/PowerPoint right away; .md keeps
  the in-card text preview. No new buttons are added (chat-first rule).
- The "Hoan tac" (undo) button restores the one-touch backup the backend
  created (checkpoint_path) instead of going through the generic work queue.

Pure logic, no streamlit import: workspace_chat_ui calls these and renders.
Python 3.11 compatible.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from aios_habit.agent_doc_edit import ALLOWED_SUFFIXES

ARTIFACT_MIME: Dict[str, str] = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".md": "text/markdown",
    ".txt": "text/plain",
}

_BINARY_SUFFIXES = frozenset({".docx", ".pptx"})


def is_binary_artifact_suffix(suffix: str) -> bool:
    """True for formats the card cannot preview as text (.docx/.pptx)."""
    return str(suffix or "").lower() in _BINARY_SUFFIXES


def artifact_download_payload(path: Any) -> Dict[str, Any]:
    """Build the streamlit download_button payload for a report file.

    Returns {"ok", "data" (bytes for binary, str for text), "mime",
    "file_name", "is_binary", "error_vi"} — never raises.
    """
    try:
        target = Path(str(path or "").strip())
    except Exception:
        return {
            "ok": False,
            "data": "",
            "mime": "text/plain",
            "file_name": "bao-cao",
            "is_binary": False,
            "error_vi": "Đường dẫn file đính kèm không hợp lệ.",
        }
    if not target.is_file():
        return {
            "ok": False,
            "data": "",
            "mime": "text/plain",
            "file_name": target.name or "bao-cao",
            "is_binary": False,
            "error_vi": "Chưa tìm thấy file “%s” để tải." % target.name,
        }
    suffix = target.suffix.lower()
    mime = ARTIFACT_MIME.get(suffix, "application/octet-stream")
    is_binary = is_binary_artifact_suffix(suffix)
    try:
        data: Any = target.read_bytes() if is_binary else target.read_text(
            encoding="utf-8"
        )
    except Exception as exc:
        return {
            "ok": False,
            "data": "",
            "mime": mime,
            "file_name": target.name,
            "is_binary": is_binary,
            "error_vi": "Chưa đọc được file để tải: %s" % exc,
        }
    return {
        "ok": True,
        "data": data,
        "mime": mime,
        "file_name": target.name,
        "is_binary": is_binary,
        "error_vi": "",
    }


def verify_card_result_path(work_record: Any, raw_result_path: str) -> Optional[Path]:
    """Resolve the attachment card's verified result path (pure logic).

    Hoi quy 2026-10-03 (verify lan 3 cho-muse): luong tao bao cao trong chat
    (ARE-*) khong ghi dong agent_work_items; the dinh kem chi lay duoc duong
    dan tu comment metadata trong tin nhan. Uu tien result_ref cua dong viec
    (luong hang doi orchestrator); neu khong co dong viec, fallback sang kiem
    dung result_path ghi trong comment.

    Ca hai ung vien deu phai qua cong an toan voi goc bao cao cua agent duoc
    phep (default_doc_root(): ~/AIOS_bao_cao khi khong dat AIOS_DOC_ROOT);
    van chan ".." va file ngoai goc. Tra None neu khong co duong dan nao
    hop le.
    """
    from aios_habit.agent_doc_edit import default_doc_root
    from aios_habit.workspace_agent_policy import is_safe_artifact_path

    allowed_roots = (default_doc_root(),)
    # Trusted backend reference (orchestrator work row): full safe check
    # (doc root + controlled tmp for tests).
    if work_record is not None and getattr(work_record, "result_ref", None):
        cand = Path(str(work_record.result_ref).strip())
        if is_safe_artifact_path(cand, allowed_roots=allowed_roots):
            return cand
    # Untrusted metadata fallback (chat comment): doc-root only, no tmp
    # fallback — otherwise a forged sibling file under the pytest temp dir
    # would pass while pretending to be a report.
    if raw_result_path:
        try:
            raw = str(raw_result_path).strip()
            if raw and ".." not in Path(raw).parts:
                resolved = Path(raw).resolve()
                for root in allowed_roots:
                    try:
                        if resolved.is_relative_to(Path(root).resolve()):
                            return Path(raw)
                    except (ValueError, AttributeError):
                        continue
        except Exception:
            pass
    return None


def _safe_same_dir(result: Path, checkpoint: Path) -> bool:
    """Both paths must resolve inside the same directory (the doc root the
    backend wrote to) with no parent traversal."""
    for candidate in (result, checkpoint):
        if any(part == ".." for part in Path(str(candidate)).parts):
            return False
    try:
        resolved_result = result.resolve()
        resolved_checkpoint = checkpoint.resolve()
    except Exception:
        return False
    return resolved_result.parent == resolved_checkpoint.parent


def restore_report_backup(
    result_path: Any, checkpoint_path: Any
) -> Tuple[bool, str]:
    """One-touch undo for a report edit: restore the backend's backup copy.

    - Edit with a backup: the backup bytes are copied back over the result.
    - Create without a backup: the created file is removed.
    Refuses anything outside the backend's own output directory or outside
    the supported report suffixes. Never raises; messages are Vietnamese.
    """
    result_raw = str(result_path or "").strip()
    checkpoint_raw = str(checkpoint_path or "").strip()
    if not result_raw:
        return False, "Thiếu đường dẫn file cần hoàn tác."
    result = Path(result_raw)
    if result.suffix.lower() not in ALLOWED_SUFFIXES:
        return False, "Thao tác bị từ chối: loại tệp không được phép hoàn tác."
    if checkpoint_raw:
        checkpoint = Path(checkpoint_raw)
        if not _safe_same_dir(result, checkpoint):
            return False, "Thao tác bị từ chối: file sao lưu không nằm cùng thư mục báo cáo."
        if not checkpoint.is_file():
            return False, "Chưa tìm thấy file sao lưu “%s”." % checkpoint.name
        try:
            result.write_bytes(checkpoint.read_bytes())
        except Exception as exc:
            return False, "Chưa hoàn tác được: %s" % exc
        return True, "Đã hoàn tác — lấy lại bản gốc từ “%s”." % checkpoint.name
    # No backup: this was a create; undo removes the created file.
    if any(part == ".." for part in result.parts):
        return False, "Thao tác bị từ chối: đường dẫn không hợp lệ."
    try:
        resolved = result.resolve()
    except Exception:
        return False, "Đường dẫn file cần hoàn tác không hợp lệ."
    if not resolved.is_file():
        return False, "File đã được hoàn tác trước đó."
    try:
        resolved.unlink()
    except Exception as exc:
        return False, "Chưa xóa được file đã tạo: %s" % exc
    return True, "Đã hoàn tác — xóa file vừa tạo “%s”." % resolved.name
