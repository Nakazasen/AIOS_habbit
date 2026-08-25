from __future__ import annotations

import os
import re
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from aios_habit.workspace_chat_models import (
    SOURCE_SCOPE_TEMPORARY,
    TemporaryConversationSource,
)
from aios_habit.workspace_chat_source_ingest import (
    MAX_UPLOAD_BYTES,
    ingest_and_extract_bytes,
)
from aios_habit.workspace_chat_store import (
    LOCAL_CHAT_DIR,
    promote_temporary_source_to_notebook,
    save_temporary_source,
    set_source_enabled,
)
from aios_habit.workspace_chat_ui import (
    PRIVACY_CHOICE_LOCAL_ONLY,
    PRIVACY_CHOICE_SENDABLE,
    owner_choice_to_privacy_label,
)

SUPPORTED_DOCUMENT_EXTENSIONS: set[str] = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".xls",
    ".xlsm",
    ".ppt",
    ".pptx",
    ".msg",
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".html",
    ".htm",
}

IGNORED_DIR_NAMES: set[str] = {
    ".git",
    ".svn",
    ".hg",
    ".venv",
    "venv",
    "env",
    ".env",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".antigravity",
    ".mypy_cache",
    ".ruff_cache",
}

MAX_FOLDER_SCAN_FILES: int = 10000
MAX_BATCH_FILE_SIZE_BYTES: int = MAX_UPLOAD_BYTES  # 10 MB default
FOLDER_IMPORT_PROGRESS_FILE = Path(LOCAL_CHAT_DIR) / "folder_import_progress.json"


def _folder_file_key_from_parts(path: Union[Path, str], size_bytes: int, modified_time_ns: int) -> str:
    # ``Path.resolve`` can issue a costly network lookup for every file on a
    # UNC share.  The scanner already supplies absolute paths, so a normalized
    # lexical path is stable enough here and keeps resume responsive on shares.
    normalized_path = os.path.normcase(os.path.abspath(os.fspath(path)))
    raw = f"{normalized_path}|{size_bytes}|{modified_time_ns}".encode("utf-8", "surrogatepass")
    return hashlib.sha256(raw).hexdigest()


def _folder_file_key(path: Path) -> str:
    stat = path.stat()
    return _folder_file_key_from_parts(path, stat.st_size, stat.st_mtime_ns)


def _scanned_file_key(item: "ScannedFileInfo") -> str:
    """Build a resume key from data already gathered during the directory scan."""
    return _folder_file_key_from_parts(item.path, item.size_bytes, item.modified_time_ns)


def _load_completed_folder_files() -> set[str]:
    try:
        value = json.loads(FOLDER_IMPORT_PROGRESS_FILE.read_text(encoding="utf-8"))
        return set(value.get("completed", [])) if isinstance(value, dict) else set()
    except (OSError, ValueError, TypeError):
        return set()


def _save_completed_folder_files(completed: set[str]) -> None:
    FOLDER_IMPORT_PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = FOLDER_IMPORT_PROGRESS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps({"completed": sorted(completed)}, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, FOLDER_IMPORT_PROGRESS_FILE)


def count_completed_folder_files(files: Sequence[Union[ScannedFileInfo, Path, str]]) -> int:
    completed = _load_completed_folder_files()
    total = 0
    for item in files:
        try:
            key = _scanned_file_key(item) if isinstance(item, ScannedFileInfo) else _folder_file_key(Path(item))
            total += key in completed
        except OSError:
            pass
    return total


def seed_completed_folder_files_from_titles(
    files: Sequence[ScannedFileInfo], existing_titles: Sequence[str],
) -> int:
    """Migrate pre-resume imports without guessing when a filename is duplicated."""
    completed = _load_completed_folder_files()
    titles = {str(title).strip().casefold() for title in existing_titles if str(title).strip()}
    by_name: dict[str, list[ScannedFileInfo]] = {}
    for item in files:
        by_name.setdefault(item.filename.casefold(), []).append(item)
    added = 0
    for filename, matches in by_name.items():
        if filename not in titles or len(matches) != 1:
            continue
        try:
            key = _scanned_file_key(matches[0])
        except OSError:
            continue
        if key not in completed:
            completed.add(key)
            added += 1
    if added:
        _save_completed_folder_files(completed)
    return added


def format_size_bytes(size_bytes: int) -> str:
    """Format bytes count into human readable string (B, KB, MB, GB)."""
    if size_bytes < 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def clean_input_path(path_input: Union[str, Path]) -> str:
    """Clean and strip surrounding quotes/whitespace from user path input."""
    if isinstance(path_input, Path):
        return str(path_input)
    raw = str(path_input or "").strip()
    while len(raw) >= 2 and (
        (raw.startswith('"') and raw.endswith('"')) or
        (raw.startswith("'") and raw.endswith("'"))
    ):
        raw = raw[1:-1].strip()
    raw = raw.strip("\"' \t\r\n")
    return raw


def validate_directory_path(path_input: Union[str, Path]) -> Tuple[bool, Optional[Path], str]:
    """
    Validate that the input path exists, is a directory, is accessible, and has no null bytes.
    Returns (is_valid, resolved_path, error_message).
    """
    cleaned = clean_input_path(path_input)
    if not cleaned:
        return False, None, "Vui lòng nhập đường dẫn thư mục hợp lệ."

    if "\0" in cleaned:
        return False, None, "Đường dẫn chứa ký tự không hợp lệ."

    try:
        candidate = Path(cleaned).expanduser().resolve()
    except (OSError, ValueError, RuntimeError) as e:
        return False, None, f"Đường dẫn không hợp lệ: {e}"
    except Exception as e:
        return False, None, f"Đường dẫn không hợp lệ: {e}"

    try:
        if not candidate.exists():
            return False, None, f"Thư mục không tồn tại: {cleaned}"

        if not candidate.is_dir():
            return False, None, f"Đường dẫn không phải là thư mục: {cleaned}"
    except (OSError, ValueError, RuntimeError) as e:
        return False, None, f"Đường dẫn không hợp lệ hoặc không thể kiểm tra: {e}"
    except Exception as e:
        return False, None, f"Lỗi kiểm tra đường dẫn ({cleaned}): {e}"

    # Verify read permission
    try:
        with os.scandir(candidate) as it:
            next(it, None)
    except PermissionError:
        return False, None, f"Không có quyền truy cập hoặc đọc thư mục: {cleaned}"
    except OSError as e:
        return False, None, f"Không thể đọc thư mục ({cleaned}): {e}"

    return True, candidate, ""


@dataclass
class ScannedFileInfo:
    path: str
    relative_path: str
    filename: str
    extension: str
    size_bytes: int
    modified_time: str
    is_supported: bool
    modified_time_ns: int = 0
    unsupported_reason: str = ""


@dataclass
class DirectoryScanResult:
    ok: bool
    root_path: str
    error_message: str = ""
    total_files: int = 0
    supported_files: List[ScannedFileInfo] = field(default_factory=list)
    unsupported_files: List[ScannedFileInfo] = field(default_factory=list)
    total_supported_size_bytes: int = 0
    total_scanned_size_bytes: int = 0
    extension_counts: Dict[str, int] = field(default_factory=dict)
    scanned_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_recursive: bool = True
    truncated_by_limit: bool = False

    def supported_count(self) -> int:
        return len(self.supported_files)

    def unsupported_count(self) -> int:
        return len(self.unsupported_files)

    def formatted_supported_size(self) -> str:
        return format_size_bytes(self.total_supported_size_bytes)

    def formatted_total_size(self) -> str:
        return format_size_bytes(self.total_scanned_size_bytes)


def scan_local_directory(
    path_input: Union[str, Path],
    recursive: bool = True,
    ignore_hidden: bool = True,
    max_files: int = MAX_FOLDER_SCAN_FILES,
) -> DirectoryScanResult:
    """
    Scan a local directory for supported documents.
    Safely traverses directories while preventing symlink cycles and handling permission errors.
    """
    valid, root_path, err_msg = validate_directory_path(path_input)
    cleaned_input = clean_input_path(path_input)

    if not valid or root_path is None:
        return DirectoryScanResult(
            ok=False,
            root_path=cleaned_input,
            error_message=err_msg,
            is_recursive=recursive,
        )

    supported_files: List[ScannedFileInfo] = []
    unsupported_files: List[ScannedFileInfo] = []
    extension_counts: Dict[str, int] = {}
    total_supported_size = 0
    total_scanned_size = 0
    truncated_by_limit = False

    visited_realpaths: set[str] = set()

    if recursive:
        for dirpath, dirnames, filenames in os.walk(root_path, topdown=True, followlinks=False):
            # Guard against symlink cycles
            try:
                real_dir = os.path.realpath(dirpath)
                if real_dir in visited_realpaths:
                    dirnames.clear()
                    continue
                visited_realpaths.add(real_dir)
            except Exception:
                pass

            # Filter out ignored/hidden directories in place
            if ignore_hidden:
                dirnames[:] = [
                    d for d in dirnames
                    if not d.startswith(".") and d.lower() not in IGNORED_DIR_NAMES
                ]
            else:
                dirnames[:] = [
                    d for d in dirnames
                    if d.lower() not in IGNORED_DIR_NAMES
                ]

            for fname in filenames:
                if ignore_hidden and fname.startswith("."):
                    continue

                if (len(supported_files) + len(unsupported_files)) >= max_files:
                    truncated_by_limit = True
                    break

                file_full_path = Path(dirpath) / fname
                try:
                    rel_path = file_full_path.relative_to(root_path).as_posix()
                except ValueError:
                    rel_path = fname

                ext = file_full_path.suffix.lower()
                size_bytes = 0
                mtime_iso = ""
                mtime_ns = 0

                try:
                    st = file_full_path.stat()
                    size_bytes = st.st_size
                    mtime_iso = datetime.fromtimestamp(st.st_mtime).isoformat()
                    mtime_ns = st.st_mtime_ns
                except (OSError, PermissionError) as e:
                    unsupported_files.append(
                        ScannedFileInfo(
                            path=str(file_full_path),
                            relative_path=rel_path,
                            filename=fname,
                            extension=ext,
                            size_bytes=0,
                            modified_time="",
                            is_supported=False,
                            unsupported_reason=f"Không thể đọc thông tin tập tin: {e}",
                        )
                    )
                    continue

                total_scanned_size += size_bytes
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

                if ext in SUPPORTED_DOCUMENT_EXTENSIONS:
                    info = ScannedFileInfo(
                        path=str(file_full_path),
                        relative_path=rel_path,
                        filename=fname,
                        extension=ext,
                        size_bytes=size_bytes,
                        modified_time=mtime_iso,
                        modified_time_ns=mtime_ns,
                        is_supported=True,
                        unsupported_reason="",
                    )
                    supported_files.append(info)
                    total_supported_size += size_bytes
                else:
                    info = ScannedFileInfo(
                        path=str(file_full_path),
                        relative_path=rel_path,
                        filename=fname,
                        extension=ext,
                        size_bytes=size_bytes,
                        modified_time=mtime_iso,
                        modified_time_ns=mtime_ns,
                        is_supported=False,
                        unsupported_reason="Định dạng chưa được hỗ trợ",
                    )
                    unsupported_files.append(info)

            if truncated_by_limit:
                dirnames.clear()
                break
    else:
        # Non-recursive: list immediate contents only
        try:
            with os.scandir(root_path) as it:
                raw_entries = list(it)
            entries = sorted(raw_entries, key=lambda p: p.name.lower())
        except (OSError, PermissionError) as e:
            return DirectoryScanResult(
                ok=False,
                root_path=str(root_path),
                error_message=f"Lỗi khi đọc danh sách thư mục: {e}",
                is_recursive=False,
            )

        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    continue
            except (OSError, PermissionError):
                pass

            fname = entry.name
            if ignore_hidden and fname.startswith("."):
                continue

            if (len(supported_files) + len(unsupported_files)) >= max_files:
                truncated_by_limit = True
                break

            file_full_path = Path(entry.path)
            ext = file_full_path.suffix.lower()
            size_bytes = 0
            mtime_iso = ""
            mtime_ns = 0

            try:
                st = file_full_path.stat()
                size_bytes = st.st_size
                mtime_iso = datetime.fromtimestamp(st.st_mtime).isoformat()
                mtime_ns = st.st_mtime_ns
            except (OSError, PermissionError) as e:
                unsupported_files.append(
                    ScannedFileInfo(
                        path=str(file_full_path),
                        relative_path=fname,
                        filename=fname,
                        extension=ext,
                        size_bytes=0,
                        modified_time="",
                        modified_time_ns=0,
                        is_supported=False,
                        unsupported_reason=f"Không thể đọc thông tin tập tin: {e}",
                    )
                )
                continue

            total_scanned_size += size_bytes
            extension_counts[ext] = extension_counts.get(ext, 0) + 1

            if ext in SUPPORTED_DOCUMENT_EXTENSIONS:
                info = ScannedFileInfo(
                    path=str(file_full_path),
                    relative_path=fname,
                    filename=fname,
                    extension=ext,
                    size_bytes=size_bytes,
                    modified_time=mtime_iso,
                    modified_time_ns=mtime_ns,
                    is_supported=True,
                    unsupported_reason="",
                )
                supported_files.append(info)
                total_supported_size += size_bytes
            else:
                info = ScannedFileInfo(
                    path=str(file_full_path),
                    relative_path=fname,
                    filename=fname,
                    extension=ext,
                    size_bytes=size_bytes,
                        modified_time=mtime_iso,
                        modified_time_ns=mtime_ns,
                    is_supported=False,
                    unsupported_reason="Định dạng chưa được hỗ trợ",
                )
                unsupported_files.append(info)

    total_files = len(supported_files) + len(unsupported_files)

    return DirectoryScanResult(
        ok=True,
        root_path=str(root_path),
        error_message="",
        total_files=total_files,
        supported_files=supported_files,
        unsupported_files=unsupported_files,
        total_supported_size_bytes=total_supported_size,
        total_scanned_size_bytes=total_scanned_size,
        extension_counts=extension_counts,
        is_recursive=recursive,
        truncated_by_limit=truncated_by_limit,
    )


@dataclass
class BatchIngestItemResult:
    path: str
    filename: str
    ok: bool
    relative_path: str = ""
    source_id: Optional[str] = None
    notebook_source_id: Optional[str] = None
    error_code: Optional[str] = None
    owner_message: str = ""
    size_bytes: int = 0


@dataclass
class BatchIngestSummary:
    total_files: int
    success_count: int
    fail_count: int
    skipped_count: int
    success_files: List[str]
    failed_files: List[str]
    errors_by_file: Dict[str, str]
    item_results: List[BatchIngestItemResult] = field(default_factory=list)
    has_truncated: bool = False


def create_batch_temporary_source(
    conversation_id: str,
    title: str,
    source_type: str,
    content_preview: str,
    content_text: str,
    owner_choice: str,
    enable_source: bool = False,
    managed_path: str = "",
) -> TemporaryConversationSource:
    """Helper to save a temporary source and optionally enable it."""
    import uuid

    privacy_label = owner_choice_to_privacy_label(owner_choice)
    ts = TemporaryConversationSource(
        id=f"SRC-{uuid.uuid4().hex[:8].upper()}",
        conversation_id=conversation_id,
        source_type=source_type,
        title=title,
        content_preview=content_preview,
        content_text=content_text,
        privacy_label=privacy_label,
        managed_path=managed_path,
    )
    save_temporary_source(ts)
    if enable_source:
        set_source_enabled(conversation_id, SOURCE_SCOPE_TEMPORARY, ts.id, True)
    return ts


def ingest_scanned_files_batch(
    files: Sequence[Union[ScannedFileInfo, Path, str]],
    conversation_id: str,
    privacy_choice: str,
    enable_now: bool = False,
    save_to_notebook: bool = True,
    notebook_id: str = "",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    max_file_size: int = MAX_BATCH_FILE_SIZE_BYTES,
) -> BatchIngestSummary:
    """
    Process a list of files sequentially or in bounded batches through the extraction
    and storage pipeline. Gracefully handles corrupted, locked, or unreadable files.
    """
    total_items = len(files)
    success_count = 0
    fail_count = 0
    skipped_count = 0
    success_files: List[str] = []
    failed_files: List[str] = []
    errors_by_file: Dict[str, str] = {}
    item_results: List[BatchIngestItemResult] = []
    has_truncated = False
    completed = _load_completed_folder_files()

    for idx, item in enumerate(files):
        if isinstance(item, ScannedFileInfo):
            file_path = Path(item.path)
            filename = item.filename
            relative_path = item.relative_path
        elif isinstance(item, (str, Path)):
            file_path = Path(item)
            filename = file_path.name
            relative_path = file_path.name
        else:
            file_path = Path(str(item))
            filename = file_path.name
            relative_path = file_path.name

        display_name = relative_path if relative_path and relative_path != filename else filename
        try:
            file_key = _scanned_file_key(item) if isinstance(item, ScannedFileInfo) else _folder_file_key(file_path)
        except OSError:
            file_key = ""
        if file_key and file_key in completed:
            skipped_count += 1
            item_results.append(BatchIngestItemResult(path=str(file_path), filename=filename, relative_path=relative_path, ok=True, error_code="already_imported", owner_message="Đã nhập trước đó, bỏ qua."))
            continue

        if progress_callback:
            try:
                progress_callback(idx + 1, total_items, display_name)
            except Exception:
                pass

        # 1. Existence and type validation
        try:
            exists_and_is_file = file_path.exists() and file_path.is_file()
        except (OSError, PermissionError):
            exists_and_is_file = False

        if not exists_and_is_file:
            fail_count += 1
            failed_files.append(display_name)
            err_msg = "Tập tin không tồn tại hoặc đã bị di chuyển."
            errors_by_file[display_name] = err_msg
            item_results.append(
                BatchIngestItemResult(
                    path=str(file_path),
                    filename=filename,
                    relative_path=relative_path,
                    ok=False,
                    error_code="not_found",
                    owner_message=err_msg,
                )
            )
            continue

        # 2. Size validation
        try:
            size_bytes = file_path.stat().st_size
        except (OSError, PermissionError) as e:
            fail_count += 1
            failed_files.append(display_name)
            err_msg = f"Không thể kiểm tra dung lượng tập tin (bị khóa hoặc lỗi quyền): {e}"
            errors_by_file[display_name] = err_msg
            item_results.append(
                BatchIngestItemResult(
                    path=str(file_path),
                    filename=filename,
                    relative_path=relative_path,
                    ok=False,
                    error_code="permission_error",
                    owner_message=err_msg,
                )
            )
            continue

        if size_bytes == 0:
            fail_count += 1
            failed_files.append(display_name)
            err_msg = "Tập tin rỗng hoặc không có nội dung đọc được."
            errors_by_file[display_name] = err_msg
            item_results.append(
                BatchIngestItemResult(
                    path=str(file_path),
                    filename=filename,
                    relative_path=relative_path,
                    ok=False,
                    size_bytes=0,
                    error_code="empty",
                    owner_message=err_msg,
                )
            )
            continue

        if size_bytes > max_file_size:
            fail_count += 1
            failed_files.append(display_name)
            err_msg = f"Tập tin vượt quá giới hạn dung lượng ({format_size_bytes(max_file_size)})."
            errors_by_file[display_name] = err_msg
            item_results.append(
                BatchIngestItemResult(
                    path=str(file_path),
                    filename=filename,
                    relative_path=relative_path,
                    ok=False,
                    size_bytes=size_bytes,
                    error_code="oversized",
                    owner_message=err_msg,
                )
            )
            continue

        # 3. Read file bytes with error resilience for locked files
        try:
            file_bytes = file_path.read_bytes()
        except PermissionError:
            fail_count += 1
            failed_files.append(display_name)
            err_msg = "Tập tin đang bị khóa bởi tiến trình khác hoặc không có quyền đọc."
            errors_by_file[display_name] = err_msg
            item_results.append(
                BatchIngestItemResult(
                    path=str(file_path),
                    filename=filename,
                    relative_path=relative_path,
                    ok=False,
                    size_bytes=size_bytes,
                    error_code="locked",
                    owner_message=err_msg,
                )
            )
            continue
        except OSError as e:
            fail_count += 1
            failed_files.append(display_name)
            err_msg = f"Lỗi đọc tập tin: {e}"
            errors_by_file[display_name] = err_msg
            item_results.append(
                BatchIngestItemResult(
                    path=str(file_path),
                    filename=filename,
                    relative_path=relative_path,
                    ok=False,
                    size_bytes=size_bytes,
                    error_code="io_error",
                    owner_message=err_msg,
                )
            )
            continue

        # 4. Extract and ingest bytes
        extract_res = ingest_and_extract_bytes(file_bytes, filename, privacy_choice)

        if extract_res.get("ok"):
            ext = extract_res.get("metadata", {}).get("extension", "").lower()
            source_title = extract_res.get("filename") or filename
            ts = create_batch_temporary_source(
                conversation_id=conversation_id,
                title=source_title,
                source_type=ext.replace(".", "") or "txt",
                content_preview=extract_res.get("preview", ""),
                content_text=extract_res.get("text", ""),
                owner_choice=privacy_choice,
                enable_source=enable_now,
                managed_path=extract_res.get("metadata", {}).get("managed_path", ""),
            )

            nb_src_id = None
            if save_to_notebook and notebook_id:
                try:
                    nb_src = promote_temporary_source_to_notebook(conversation_id, ts.id, notebook_id)
                    nb_src_id = nb_src.id if nb_src else None
                except Exception:
                    # Non-fatal: temporary source is still created
                    pass

            success_count += 1
            if file_key:
                completed.add(file_key)
                _save_completed_folder_files(completed)
            success_files.append(display_name)
            if extract_res.get("metadata", {}).get("truncated"):
                has_truncated = True

            item_results.append(
                BatchIngestItemResult(
                    path=str(file_path),
                    filename=filename,
                    relative_path=relative_path,
                    ok=True,
                    source_id=ts.id,
                    notebook_source_id=nb_src_id,
                    size_bytes=size_bytes,
                    owner_message=extract_res.get("owner_message", "Đã đọc và trích xuất thành công."),
                )
            )
        else:
            fail_count += 1
            failed_files.append(display_name)
            err_msg = extract_res.get("owner_message") or "Không thể đọc và trích xuất tập tin."
            errors_by_file[display_name] = err_msg
            item_results.append(
                BatchIngestItemResult(
                    path=str(file_path),
                    filename=filename,
                    relative_path=relative_path,
                    ok=False,
                    size_bytes=size_bytes,
                    error_code=extract_res.get("error_code") or "extraction_failed",
                    owner_message=err_msg,
                )
            )

    return BatchIngestSummary(
        total_files=total_items,
        success_count=success_count,
        fail_count=fail_count,
        skipped_count=skipped_count,
        success_files=success_files,
        failed_files=failed_files,
        errors_by_file=errors_by_file,
        item_results=item_results,
        has_truncated=has_truncated,
    )


def ingest_local_folder(
    folder_path: Union[str, Path],
    conversation_id: str,
    privacy_choice: str = PRIVACY_CHOICE_LOCAL_ONLY,
    recursive: bool = True,
    enable_now: bool = False,
    save_to_notebook: bool = True,
    notebook_id: str = "",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Tuple[DirectoryScanResult, BatchIngestSummary]:
    """
    Convenience end-to-end function: Scan folder and batch ingest all supported documents.
    """
    scan_result = scan_local_directory(folder_path, recursive=recursive)
    if not scan_result.ok or not scan_result.supported_files:
        summary = BatchIngestSummary(
            total_files=0,
            success_count=0,
            fail_count=0,
            skipped_count=0,
            success_files=[],
            failed_files=[],
            errors_by_file={},
            item_results=[],
        )
        return scan_result, summary

    summary = ingest_scanned_files_batch(
        files=scan_result.supported_files,
        conversation_id=conversation_id,
        privacy_choice=privacy_choice,
        enable_now=enable_now,
        save_to_notebook=save_to_notebook,
        notebook_id=notebook_id,
        progress_callback=progress_callback,
    )
    return scan_result, summary
