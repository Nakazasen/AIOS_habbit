from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from aios_habit.workspace_chat_models import (
    WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT,
    WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES,
)
from aios_habit.workspace_chat_excel import extract_xlsx_text
from aios_habit.document_extractors import extract_text_chunks_from_file

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

def sanitize_filename(filename: str) -> str:
    """Sanitize the filename to prevent path traversal and clean unwanted characters."""
    name = Path(filename).name
    # Keep only alphanumeric characters, dots, underscores, dashes
    name = re.sub(r"[^\w\.\-]", "_", name)
    # Prevent multiple dots or traversal attempts
    name = re.sub(r"\.+", ".", name)
    name = name.strip("_.")
    return name or "uploaded_file"

def ingest_and_extract_bytes(
    file_bytes: bytes,
    filename: str,
    privacy_label: str = "machine_only",
) -> Dict[str, Any]:
    """
    Adapter to receive file bytes and filename, write to a temp file safely,
    extract text, clean up, and return a standardized dictionary result.
    """
    safe_name = sanitize_filename(filename)
    ext = Path(safe_name).suffix.lower()

    # Preflight size check
    if not file_bytes:
        return {
            "ok": False,
            "filename": safe_name,
            "error_code": "empty",
            "owner_message": "Tập tin rỗng hoặc không có nội dung đọc được.",
            "text": "",
            "preview": "",
            "metadata": {"file_size_bytes": 0, "extension": ext},
        }

    file_size = len(file_bytes)
    if file_size > MAX_UPLOAD_BYTES:
        return {
            "ok": False,
            "filename": safe_name,
            "error_code": "oversized",
            "owner_message": "Tập tin vượt quá giới hạn dung lượng cho phép.",
            "text": "",
            "preview": "",
            "metadata": {"file_size_bytes": file_size, "extension": ext},
        }

    # Handle XLSX using existing robust module workspace_chat_excel
    if ext in {".xlsx", ".xlsm"}:
        xlsx_res = extract_xlsx_text(file_bytes, safe_name)
        owner_msg = xlsx_res.owner_message
        # Sanitize Excel messages if they leak trace or generic English error
        if not xlsx_res.ok:
            owner_msg = "Không thể đọc tập tin này. Vui lòng kiểm tra lại tập tin hoặc thử định dạng khác."
        elif "chỉ đọc một phần" in xlsx_res.owner_message.lower():
            owner_msg = "File Excel lớn nên AIOS chỉ đọc một phần nội dung. Bạn có thể chia file nhỏ hơn nếu cần."
        else:
            owner_msg = "Đã đọc và trích xuất thành công tài liệu."

        return {
            "ok": xlsx_res.ok,
            "filename": xlsx_res.filename,
            "error_code": "malformed" if not xlsx_res.ok else None,
            "owner_message": owner_msg,
            "text": xlsx_res.text,
            "preview": xlsx_res.preview,
            "metadata": {
                "file_size_bytes": file_size,
                "extension": ext,
                "sheet_names": xlsx_res.sheet_names,
                "truncated": xlsx_res.truncated,
                "raw_warning": xlsx_res.owner_message if not xlsx_res.ok else "",
            },
        }

    # Handle other plain text formats (TXT, MD) directly in memory
    if ext in {".txt", ".md", ".markdown"}:
        try:
            text = file_bytes.decode("utf-8", errors="replace").strip()
            if not text:
                return {
                    "ok": False,
                    "filename": safe_name,
                    "error_code": "empty",
                    "owner_message": "Tập tin rỗng hoặc không có nội dung đọc được.",
                    "text": "",
                    "preview": "",
                    "metadata": {"file_size_bytes": file_size, "extension": ext},
                }
            # Limit sizes
            if len(text.encode("utf-8")) > WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES:
                text = text.encode("utf-8")[:WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES].decode("utf-8", errors="ignore")
                text += "\n[Nội dung đã bị cắt bớt do vượt quá giới hạn lưu trữ dữ liệu của Workspace Chat]"
            preview = text[:WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT]
            return {
                "ok": True,
                "filename": safe_name,
                "error_code": None,
                "owner_message": "Đã đọc và trích xuất thành công tài liệu.",
                "text": text,
                "preview": preview,
                "metadata": {"file_size_bytes": file_size, "extension": ext},
            }
        except Exception as e:
            return {
                "ok": False,
                "filename": safe_name,
                "error_code": "malformed",
                "owner_message": "Không thể đọc tập tin này. Vui lòng kiểm tra lại tập tin hoặc thử định dạng khác.",
                "text": "",
                "preview": "",
                "metadata": {"file_size_bytes": file_size, "extension": ext, "raw_error": str(e)},
            }

    # Handle CSV
    if ext == ".csv":
        try:
            csv_str = file_bytes.decode("utf-8", errors="replace").strip()
            lines = [line.strip() for line in csv_str.splitlines() if line.strip()]
            if not lines:
                return {
                    "ok": False,
                    "filename": safe_name,
                    "error_code": "empty",
                    "owner_message": "Tập tin rỗng hoặc không có nội dung đọc được.",
                    "text": "",
                    "preview": "",
                    "metadata": {"file_size_bytes": file_size, "extension": ext},
                }
            # Form a table-like readable preview and full text
            text = "\n".join(lines)
            if len(text.encode("utf-8")) > WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES:
                text = text.encode("utf-8")[:WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES].decode("utf-8", errors="ignore")
                text += "\n[Nội dung CSV đã bị cắt bớt do quá dài]"
            preview_lines = lines[:15]
            preview = "\n".join(preview_lines)
            return {
                "ok": True,
                "filename": safe_name,
                "error_code": None,
                "owner_message": "Đã đọc và trích xuất thành công tài liệu.",
                "text": text,
                "preview": preview,
                "metadata": {
                    "file_size_bytes": file_size,
                    "extension": ext,
                    "row_count": len(lines),
                },
            }
        except Exception as e:
            return {
                "ok": False,
                "filename": safe_name,
                "error_code": "malformed",
                "owner_message": "Không thể đọc tập tin này. Vui lòng kiểm tra lại tập tin hoặc thử định dạng khác.",
                "text": "",
                "preview": "",
                "metadata": {"file_size_bytes": file_size, "extension": ext, "raw_error": str(e)},
            }

    # Allowed complex document formats parsed via document_extractors
    supported_complex_exts = {".pdf", ".docx", ".pptx", ".html", ".htm", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
    if ext not in supported_complex_exts:
        return {
            "ok": False,
            "filename": safe_name,
            "error_code": "unsupported",
            "owner_message": "Định dạng tập tin này chưa được hỗ trợ.",
            "text": "",
            "preview": "",
            "metadata": {"file_size_bytes": file_size, "extension": ext},
        }

    # Write to safe temp file to call document_extractors
    temp_dir = tempfile.gettempdir()
    unique_id = uuid.uuid4().hex[:8]
    temp_path = Path(temp_dir) / f"wsc_extract_{unique_id}_{safe_name}"

    try:
        with open(temp_path, "wb") as tmp:
            tmp.write(file_bytes)

        # Call the existing document_extractors module
        chunks = extract_text_chunks_from_file(temp_path)

        # Process results
        has_text = False
        text_parts = []
        warnings = []
        is_dependency_missing = False
        missing_dep_msg = ""
        is_ocr_missing = False
        is_malformed = False

        for chunk in chunks:
            status = chunk.get("extraction_status", "")
            chunk_text = chunk.get("text", "").strip()

            if status in {"failed_with_reason", "parse_failed", "zip_failed", "unsupported_no_local_tool"}:
                # If complex documents return failed status, they are malformed
                if ext in {".docx", ".pptx", ".xlsx", ".xlsm"}:
                    is_malformed = True

            if status == "dependency_missing":
                is_dependency_missing = True
                missing_dep_msg = chunk.get("warning", "") or "pymupdf4llm/fitz missing"
            elif status == "unsupported_no_local_ocr" or "local OCR unavailable" in (chunk.get("warning", "") or ""):
                is_ocr_missing = True

            if chunk_text:
                has_text = True
                text_parts.append(chunk_text)
            
            chunk_warn = chunk.get("warning", "")
            if chunk_warn and chunk_warn not in warnings and "unsupported" not in chunk_warn.lower():
                warnings.append(chunk_warn)

        # Clean up text parts
        combined_text = "\n\n".join(text_parts).strip()

        # Handle specific error cases first
        if is_malformed:
            return {
                "ok": False,
                "filename": safe_name,
                "error_code": "malformed",
                "owner_message": "Không thể đọc tập tin này. Vui lòng kiểm tra lại tập tin hoặc thử định dạng khác.",
                "text": "",
                "preview": "",
                "metadata": {"file_size_bytes": file_size, "extension": ext, "raw_warnings": warnings},
            }

        if is_dependency_missing and ext == ".pdf":
            return {
                "ok": False,
                "filename": safe_name,
                "error_code": "dependency_missing",
                "owner_message": "Không thể đọc PDF vì máy hiện chưa có bộ đọc PDF tùy chọn.",
                "text": "",
                "preview": "",
                "metadata": {"file_size_bytes": file_size, "extension": ext, "raw_warning": missing_dep_msg},
            }

        # If it's an image and OCR failed due to missing tools
        if is_ocr_missing and ext in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
            return {
                "ok": False,
                "filename": safe_name,
                "error_code": "dependency_missing",
                "owner_message": "Không thể đọc ảnh vì máy hiện chưa có bộ đọc chữ trong ảnh.",
                "text": "",
                "preview": "",
                "metadata": {"file_size_bytes": file_size, "extension": ext},
            }

        if not has_text:
            return {
                "ok": False,
                "filename": safe_name,
                "error_code": "empty",
                "owner_message": "Tập tin rỗng hoặc không có nội dung đọc được.",
                "text": "",
                "preview": "",
                "metadata": {"file_size_bytes": file_size, "extension": ext, "raw_warnings": warnings},
            }

        # Apply sizes limits
        if len(combined_text.encode("utf-8")) > WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES:
            combined_text = combined_text.encode("utf-8")[:WORKSPACE_CHAT_SOURCE_TEXT_LIMIT_BYTES].decode("utf-8", errors="ignore")
            combined_text += "\n[Nội dung đã bị cắt bớt do quá dài]"

        preview = combined_text[:WORKSPACE_CHAT_SOURCE_PREVIEW_LIMIT]

        return {
            "ok": True,
            "filename": safe_name,
            "error_code": None,
            "owner_message": "Đã đọc và trích xuất thành công tài liệu.",
            "text": combined_text,
            "preview": preview,
            "metadata": {
                "file_size_bytes": file_size,
                "extension": ext,
                "raw_warnings": warnings,
            },
        }

    except Exception as e:
        return {
            "ok": False,
            "filename": safe_name,
            "error_code": "malformed",
            "owner_message": "Không thể đọc tập tin này. Vui lòng kiểm tra lại tập tin hoặc thử định dạng khác.",
            "text": "",
            "preview": "",
            "metadata": {"file_size_bytes": file_size, "extension": ext, "raw_error": str(e)},
        }

    finally:
        # Guarantee temp file cleanup in all success/failure/exception branches
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
