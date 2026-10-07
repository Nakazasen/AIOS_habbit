"""Module hiển thị dòng trạng thái chỉ mục trong khung chat (INDEX-STATUS-LINE-PC0575).

Cung cấp các hàm kiểm tra và định dạng dòng thông tin mảnh cho chỉ mục đang nạp:
- Tên tệp chỉ mục (vd: library.sqlite, workspace_chat.sqlite)
- Số lượng tài liệu và số lượng mảnh được đếm trực tiếp từ DB
- Mã nhận diện rút gọn 12 ký tự hex của vân tay logic (SHA-256 danh sách tài liệu)
- Tên backend (vd: ONNX fp32)
- Cảnh báo rõ ràng khi chỉ mục thiếu hoặc không đọc được
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
from pathlib import Path
import sqlite3
from typing import Any, Mapping, Optional, Tuple


WARNING_INDEX_UNAVAILABLE = "⚠ Không nạp được kho tri thức"


@dataclasses.dataclass(frozen=True)
class IndexStatusInfo:
    """Thông tin trạng thái chỉ mục đọc trực tiếp từ database."""

    db_name: str
    doc_count: int
    chunk_count: int
    fingerprint_12: str
    backend: str
    status_line: str
    is_error: bool = False
    error_detail: str = ""


def format_thousands_vi(value: int) -> str:
    """Định dạng số nguyên với dấu chấm phân cách hàng nghìn theo chuẩn tiếng Việt."""
    return f"{value:,}".replace(",", ".")


def resolve_display_backend_name(raw_name: Optional[str] = None) -> str:
    """Xác định tên backend hiển thị (ONNX fp32, ONNX int8, PyTorch...)."""
    name = (raw_name or os.environ.get("BGE_BACKEND", "") or "").strip().lower()
    if name in ("pytorch", "flagembedding"):
        return "PyTorch"
    if name == "onnx_int8":
        return "ONNX int8"
    if name in ("onnx", "fastembed-onnx", "onnxruntime", "auto", ""):
        return "ONNX fp32"
    # Nếu là chuỗi đã chuẩn hóa khác (vd 'ONNX fp32')
    return raw_name or "ONNX fp32"


def compute_logical_fingerprint(con: sqlite3.Connection) -> str:
    """Tính mã băm SHA-256 vân tay logic từ các tài liệu trong bảng chunks.
    
    Quy chuẩn đã chốt tại SRC-SYNC / INDEX-VERIFY:
    Mỗi tài liệu tương ứng một dòng 'mã|vân tay|số mảnh', sắp xếp theo mã,
    nối bằng ký tự xuống dòng (không thừa ở cuối), băm SHA-256.
    """
    cols = {r[1] for r in con.execute("PRAGMA table_info(chunks)").fetchall()}
    has_file_type = "file_type" in cols
    has_fp = "source_fingerprint" in cols

    if has_file_type and has_fp:
        query = """
            SELECT document_id,
                   COALESCE(MAX(CASE WHEN file_type != 'document_summary' THEN source_fingerprint END), '') AS fp,
                   COUNT(CASE WHEN file_type != 'document_summary' THEN 1 END) AS n_content
            FROM chunks
            GROUP BY document_id
            ORDER BY document_id
        """
    elif has_fp:
        query = """
            SELECT document_id,
                   COALESCE(MAX(source_fingerprint), '') AS fp,
                   COUNT(*) AS n_content
            FROM chunks
            GROUP BY document_id
            ORDER BY document_id
        """
    else:
        query = """
            SELECT document_id,
                   '' AS fp,
                   COUNT(*) AS n_content
            FROM chunks
            GROUP BY document_id
            ORDER BY document_id
        """

    rows = con.execute(query).fetchall()
    lines = [f"{r[0]}|{r[1]}|{r[2]}" for r in rows]
    payload = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


_INDEX_STATUS_MEMORY_CACHE: dict[Tuple[str, float, int, str], IndexStatusInfo] = {}


def get_index_status_info(
    db_path: Optional[Path | str],
    backend_name: Optional[str] = None,
) -> IndexStatusInfo:
    """Đọc dữ liệu từ SQLite DB chỉ mục và trả về đối tượng IndexStatusInfo.
    
    Khi có lỗi (tệp thiếu, hỏng, không có bảng chunks, hoặc lỗi đọc):
    Trả về IndexStatusInfo với is_error=True và status_line mang cảnh báo.
    """
    backend_display = resolve_display_backend_name(backend_name)
    if not db_path:
        return IndexStatusInfo(
            db_name="",
            doc_count=0,
            chunk_count=0,
            fingerprint_12="",
            backend=backend_display,
            status_line=WARNING_INDEX_UNAVAILABLE,
            is_error=True,
            error_detail="Đường dẫn chỉ mục trống",
        )

    resolved_path = Path(db_path)
    if not resolved_path.is_file():
        return IndexStatusInfo(
            db_name=resolved_path.name,
            doc_count=0,
            chunk_count=0,
            fingerprint_12="",
            backend=backend_display,
            status_line=WARNING_INDEX_UNAVAILABLE,
            is_error=True,
            error_detail=f"Tệp không tồn tại: {resolved_path}",
        )

    # Kiểm tra bộ nhớ đệm tiến trình (cache theo tệp, mtime và kích cỡ)
    try:
        stat_info = resolved_path.stat()
        cache_key = (
            resolved_path.resolve().as_posix(),
            stat_info.st_mtime,
            stat_info.st_size,
            backend_display,
        )
        if cache_key in _INDEX_STATUS_MEMORY_CACHE:
            return _INDEX_STATUS_MEMORY_CACHE[cache_key]
    except OSError:
        cache_key = None

    db_name = resolved_path.name
    try:
        # Mở chế độ read-only an toàn, không ghi/sửa tệp
        uri = f"file:{resolved_path.resolve().as_posix()}?mode=ro"
        con = sqlite3.connect(uri, uri=True, timeout=10.0)
        try:
            con.execute("PRAGMA query_only = ON")

            # Kiểm tra bảng chunks có tồn tại không
            table_exists = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chunks'"
            ).fetchone()
            if not table_exists:
                return IndexStatusInfo(
                    db_name=db_name,
                    doc_count=0,
                    chunk_count=0,
                    fingerprint_12="",
                    backend=backend_display,
                    status_line=WARNING_INDEX_UNAVAILABLE,
                    is_error=True,
                    error_detail="Không tìm thấy bảng chunks trong cơ sở dữ liệu",
                )

            # Đếm tổng số chunks
            chunk_count = int(con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
            if chunk_count <= 0:
                return IndexStatusInfo(
                    db_name=db_name,
                    doc_count=0,
                    chunk_count=0,
                    fingerprint_12="",
                    backend=backend_display,
                    status_line=WARNING_INDEX_UNAVAILABLE,
                    is_error=True,
                    error_detail="Bảng chunks rỗng (0 mảnh)",
                )

            # Đếm số lượng tài liệu duy nhất
            doc_count = int(con.execute("SELECT COUNT(DISTINCT document_id) FROM chunks").fetchone()[0])

            # Tính vân tay logic và lấy 12 ký tự hex đầu
            full_fp = compute_logical_fingerprint(con)
            fingerprint_12 = full_fp[:12]

            doc_formatted = format_thousands_vi(doc_count)
            chunk_formatted = format_thousands_vi(chunk_count)

            status_line = (
                f"Kho đang dùng: {db_name} · {doc_formatted} tài liệu · {chunk_formatted} mảnh "
                f"· mã {fingerprint_12} · {backend_display}"
            )

            res = IndexStatusInfo(
                db_name=db_name,
                doc_count=doc_count,
                chunk_count=chunk_count,
                fingerprint_12=fingerprint_12,
                backend=backend_display,
                status_line=status_line,
                is_error=False,
            )
            if cache_key is not None:
                _INDEX_STATUS_MEMORY_CACHE[cache_key] = res
            return res
        finally:
            con.close()
    except Exception as exc:
        return IndexStatusInfo(
            db_name=db_name,
            doc_count=0,
            chunk_count=0,
            fingerprint_12="",
            backend=backend_display,
            status_line=WARNING_INDEX_UNAVAILABLE,
            is_error=True,
            error_detail=str(exc),
        )


def get_cached_index_status_line(
    db_path: Optional[Path | str],
    backend_name: Optional[str] = None,
    session_state: Optional[Any] = None,
) -> Tuple[str, bool]:
    """Lấy dòng trạng thái chỉ mục có bộ nhớ đệm (cache theo phiên).
    
    Trả về (status_line, is_error).
    Nếu đã tính trong session_state (theo db_path), trả về ngay không tính lại.
    """
    cache_key = "wsc_index_status_cache"
    resolved_path_str = str(Path(db_path).resolve()) if db_path else ""

    if session_state is not None and hasattr(session_state, "get"):
        cached = session_state.get(cache_key)
        if (
            isinstance(cached, dict)
            and cached.get("path") == resolved_path_str
            and cached.get("status_line")
        ):
            return str(cached["status_line"]), bool(cached.get("is_error", False))

    info = get_index_status_info(db_path, backend_name=backend_name)
    line = info.status_line
    is_err = info.is_error

    if session_state is not None:
        try:
            session_state[cache_key] = {
                "path": resolved_path_str,
                "status_line": line,
                "is_error": is_err,
            }
        except Exception:
            pass

    return line, is_err


def resolve_active_index_db_path(collection_id: Optional[str] = None) -> Optional[Path]:
    """Xác định đường dẫn tệp SQLite chỉ mục mà app đang nạp.
    
    Tra cứu theo collection_runtime_layout tương thích cấu hình môi trường của app.
    """
    try:
        from aios_habit.workspace_chat_models import DEFAULT_COLLECTION_ID
        from aios_habit.workspace_chat_rag_v2_adapter import WorkspaceChatRagV2CanaryConfig
        from aios_habit.workspace_chat_store import collection_runtime_layout

        rag_config = WorkspaceChatRagV2CanaryConfig.from_env()
        target_collection = collection_id or DEFAULT_COLLECTION_ID
        profile_root = rag_config.runtime_root / rag_config.requested_profile
        collection_root, index_filename = collection_runtime_layout(target_collection, profile_root)
        candidate = collection_root / index_filename
        if candidate.is_file():
            return candidate

        # Thử đường dẫn legacy nếu thư mục collection chưa có
        legacy_candidate = rag_config.runtime_root / rag_config.requested_profile / "workspace_chat.sqlite"
        if legacy_candidate.is_file():
            return legacy_candidate

        return candidate
    except Exception:
        return None
