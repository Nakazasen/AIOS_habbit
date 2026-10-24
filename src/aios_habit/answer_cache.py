# -*- coding: utf-8 -*-
"""Tầng nhớ câu trả lời ở cấp máy (DESKTOP-HOME-UX-ANSWER-CACHE).

- Lưu trữ hoàn toàn trong `local_cases` của máy (KHÔNG ghi vào kho tri thức).
- Khóa tra cứu = câu hỏi đã chuẩn hóa (bỏ dấu cách thừa, thường hóa, cắt khoảng trắng/dấu câu ở hai đầu)
  + kho/khối tri thức đang chọn + vân tay dữ liệu (fingerprint) của các kho liên quan tại thời điểm trả lời.
- Chỉ khớp CHÍNH XÁC theo khóa này (không khớp mờ / bán tương tự).
- Khi trúng khóa: trả ngay câu trả lời đã lưu kèm trích dẫn / bằng chứng gắn theo câu,
  kèm dòng chữ "Trả lời nhanh từ câu hỏi đã hỏi trước — dữ liệu chốt lúc <giờ>" và nút "Hỏi lại".
- Khi đổi vân tay dữ liệu của kho liên quan: bản ghi cũ tự động không còn khớp và bị thay thế bởi lượt chạy tươi.
- Khi người dùng bấm "không thích" trên câu trả lời: đánh dấu vô hiệu bản ghi của khóa đó để lần hỏi tiếp theo
  chạy tươi (tránh khóa lỗi vào bộ nhớ).
- Đếm đo (metric): mỗi lượt hỏi ghi một dòng vào `local_cases/answer_cache_metrics.jsonl`
  (thời điểm, trúng bộ nhớ hay không, thời gian trả lời ms, khóa đã băm ẩn danh - không ghi câu hỏi thô).

Tương thích Python 3.11.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

CACHE_STORE_FILENAME = "answer_cache.jsonl"
CACHE_METRICS_FILENAME = "answer_cache_metrics.jsonl"

# Dấu câu và khoảng trắng ở hai đầu câu hỏi cần cắt khi chuẩn hóa khóa
_EDGE_PUNCT_AND_SPACE_RE = re.compile(
    r"^[\s\.,;:\?!\?？!！。、，；：\"'“”‘’\(\)\[\]\{\}…\-–—_~`]+|"
    r"[\s\.,;:\?!\?？!！。、，；：\"'“”‘’\(\)\[\]\{\}…\-–—_~`]+$"
)


def resolve_local_cases_dir(base_dir: Optional[Path | str] = None) -> Path:
    """Xác định thư mục local_cases hiện hành (tôn trọng biến môi trường AIOS_LOCAL_CASES_DIR)."""
    if base_dir is not None:
        p = Path(base_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p
    env_dir = os.environ.get("AIOS_LOCAL_CASES_DIR", "").strip()
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p
    cwd_lc = Path.cwd() / "local_cases"
    if cwd_lc.exists():
        return cwd_lc
    repo_lc = Path(__file__).resolve().parent.parent.parent / "local_cases"
    repo_lc.mkdir(parents=True, exist_ok=True)
    return repo_lc


def cache_store_file(base_dir: Optional[Path | str] = None) -> Path:
    """Đường dẫn tệp lưu các bản ghi bộ nhớ câu trả lời trong local_cases."""
    return resolve_local_cases_dir(base_dir) / CACHE_STORE_FILENAME


def cache_metrics_file(base_dir: Optional[Path | str] = None) -> Path:
    """Đường dẫn tệp lưu metric từng lượt hỏi trong local_cases."""
    return resolve_local_cases_dir(base_dir) / CACHE_METRICS_FILENAME


def normalize_question_for_cache(question: str) -> str:
    """Chuẩn hóa câu hỏi làm thành phần khóa:
    - Cắt khoảng trắng và dấu câu ở hai đầu
    - Thường hóa (casefold / lower)
    - Bỏ dấu cách thừa ở giữa (gom nhiều khoảng trắng liên tiếp thành 1 dấu cách)
    - Giữ nguyên dấu tiếng Việt và nội dung từ ngữ để chỉ khớp CHÍNH XÁC (không khớp mờ).
    """
    raw = str(question or "").strip()
    if not raw:
        return ""
    stripped = _EDGE_PUNCT_AND_SPACE_RE.sub("", raw)
    collapsed = " ".join(stripped.split())
    lowered = collapsed.lower()
    return _EDGE_PUNCT_AND_SPACE_RE.sub("", lowered).strip()


def normalize_scope_id(
    notebook_id: str = "",
    forced_domain: Optional[str] = None,
    collection_id: Optional[str] = None,
) -> str:
    """Chuẩn hóa định danh kho/khối tri thức đang chọn."""
    nb = str(notebook_id or "").strip()
    dom = str(forced_domain or "").strip().lower()
    col = str(collection_id or "").strip().lower()
    if not dom or dom == "auto":
        dom = col or "auto"
    return f"nb:{nb}|dom:{dom}"


def compute_relevant_data_fingerprint(
    notebook_id: str = "",
    forced_domain: Optional[str] = None,
    collection_id: Optional[str] = None,
    extra_source_ids: Optional[Sequence[str]] = None,
    override_fingerprint: Optional[str] = None,
) -> str:
    """Tính vân tay dữ liệu (fingerprint) của các kho liên quan tại thời điểm trả lời.

    Kết hợp:
    - Biến môi trường hoặc tham số override (phục vụ kiểm thử vô hiệu hóa khi đổi vân tay).
    - Vân tay logic của chỉ mục SQLite đang dùng (qua index_status.get_index_status_info).
    - Kích thước + mtime của DB tra cứu lỗi (error_cases_reconciled.db) nếu ở sổ điều tra lỗi.
    - Danh sách nguồn đính kèm bổ sung (nếu có).
    """
    if override_fingerprint is not None and str(override_fingerprint).strip():
        return str(override_fingerprint).strip()

    env_override = os.environ.get("AIOS_ANSWER_CACHE_DATA_FINGERPRINT_OVERRIDE", "").strip()
    if env_override:
        return env_override

    parts: List[str] = []

    # 1. Xác định collection chỉ mục liên quan
    target_col = (
        str(forced_domain).strip().lower()
        if (forced_domain and str(forced_domain).strip().lower() != "auto")
        else (str(collection_id or "").strip().lower() or "")
    )
    if not target_col:
        nb_upper = str(notebook_id or "").strip().upper()
        if nb_upper in ("NB-LAZY-DTL", "DIEU_TRA_LOI"):
            target_col = "dieu_tra_loi"
        elif nb_upper in ("NB-LAZY-LSU", "LSU"):
            target_col = "lsu"
        elif nb_upper in ("MOM_OPCENTER", "MOM"):
            target_col = "mom"
        elif nb_upper in ("NB-C26E1C84", "TONG_HOP"):
            target_col = "tong_hop"
        else:
            target_col = "tri_thuc"

    try:
        from aios_habit.index_status import get_index_status_info, resolve_active_index_db_path

        idx_path = resolve_active_index_db_path(target_col)
        if idx_path and Path(idx_path).is_file():
            info = get_index_status_info(idx_path)
            if not info.is_error and info.fingerprint_12:
                parts.append(f"idx:{target_col}:{info.fingerprint_12}:{info.doc_count}:{info.chunk_count}")
            else:
                st = Path(idx_path).stat()
                parts.append(f"idx_stat:{target_col}:{st.st_size}:{int(st.st_mtime)}")
        else:
            parts.append(f"idx:{target_col}:none")
    except Exception:
        parts.append(f"idx:{target_col}:err")

    # 2. Nếu liên quan đến kho điều tra lỗi, đưa vân tay của DB ca lỗi vào
    if str(notebook_id or "").strip() in ("NB-LAZY-DTL", "dieu_tra_loi") or target_col == "dieu_tra_loi":
        try:
            from aios_habit.chat_action_error_lookup import resolve_db_path

            db_p = resolve_db_path()
            if db_p and Path(db_p).is_file():
                st_db = Path(db_p).stat()
                parts.append(f"ec_db:{Path(db_p).name}:{st_db.st_size}:{int(st_db.st_mtime)}")
        except Exception:
            pass

    # 3. Các nguồn chọn thêm trong hội thoại (nếu có)
    if extra_source_ids:
        sorted_srcs = sorted({str(s).strip() for s in extra_source_ids if str(s).strip()})
        if sorted_srcs:
            parts.append("srcs:" + ",".join(sorted_srcs))

    raw_fp = "|".join(parts)
    return hashlib.sha256(raw_fp.encode("utf-8")).hexdigest()[:16]


def build_cache_key(
    question: str,
    *,
    scope_id: str,
    data_fingerprint: str,
) -> Tuple[str, str]:
    """Tạo bộ khóa chuẩn hóa và mã băm ẩn danh (key_hash) cho câu hỏi.

    Trả về (composite_key, key_hash).
    Nếu câu hỏi rỗng sau chuẩn hóa thì trả về ("", "").
    """
    norm_q = normalize_question_for_cache(question)
    if not norm_q:
        return ("", "")
    norm_scope = str(scope_id or "").strip()
    norm_fp = str(data_fingerprint or "").strip()
    composite = f"q={norm_q}||scope={norm_scope}||fp={norm_fp}"
    key_hash = hashlib.sha256(composite.encode("utf-8")).hexdigest()[:24]
    return (composite, key_hash)


def build_question_scope_hash(question: str, *, scope_id: str) -> str:
    """Tính mã băm theo (câu hỏi chuẩn hóa + scope_id) để hỗ trợ vô hiệu hóa khi người dùng bấm Không thích."""
    norm_q = normalize_question_for_cache(question)
    if not norm_q:
        return ""
    norm_scope = str(scope_id or "").strip()
    raw = f"q={norm_q}||scope={norm_scope}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


@dataclass
class AnswerCacheEntry:
    """Bản ghi tầng nhớ câu trả lời trong local_cases."""

    key_hash: str
    question_scope_hash: str
    normalized_question: str
    scope_id: str
    data_fingerprint: str
    answer_text: str
    notebook_id: str = ""
    evidence_items: List[Dict[str, Any]] = field(default_factory=list)
    trace_dict: Optional[Dict[str, Any]] = None
    message_metadata: Dict[str, Any] = field(default_factory=dict)
    badge_data: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    snapshot_time_display: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S %d/%m/%Y"))
    invalidated: bool = False
    invalidated_reason: str = ""
    invalidated_at: str = ""
    hit_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AnswerCacheEntry:
        return cls(
            key_hash=str(data.get("key_hash") or ""),
            question_scope_hash=str(data.get("question_scope_hash") or ""),
            normalized_question=str(data.get("normalized_question") or ""),
            scope_id=str(data.get("scope_id") or ""),
            data_fingerprint=str(data.get("data_fingerprint") or ""),
            answer_text=str(data.get("answer_text") or ""),
            notebook_id=str(data.get("notebook_id") or ""),
            evidence_items=list(data.get("evidence_items") or []),
            trace_dict=dict(data["trace_dict"]) if isinstance(data.get("trace_dict"), Mapping) else None,
            message_metadata=dict(data.get("message_metadata") or {}),
            badge_data=dict(data.get("badge_data") or {}),
            created_at=str(data.get("created_at") or ""),
            snapshot_time_display=str(data.get("snapshot_time_display") or ""),
            invalidated=bool(data.get("invalidated", False)),
            invalidated_reason=str(data.get("invalidated_reason") or ""),
            invalidated_at=str(data.get("invalidated_at") or ""),
            hit_count=int(data.get("hit_count", 0) or 0),
        )


def _read_all_entries(base_dir: Optional[Path | str] = None) -> List[AnswerCacheEntry]:
    path = cache_store_file(base_dir)
    if not path.is_file():
        return []
    entries: List[AnswerCacheEntry] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    if isinstance(raw, dict) and raw.get("key_hash"):
                        entries.append(AnswerCacheEntry.from_dict(raw))
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue
    except OSError:
        return []
    return entries


def _write_all_entries_atomic(
    entries: Sequence[AnswerCacheEntry],
    base_dir: Optional[Path | str] = None,
) -> None:
    path = cache_store_file(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
        suffix=".tmp",
    )
    tmp_path = Path(tmp.name)
    try:
        for entry in entries:
            tmp.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        tmp.flush()
        tmp.close()
        tmp_path.replace(path)
    except Exception:
        try:
            tmp.close()
        except Exception:
            pass
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def lookup_cached_answer(
    question: str,
    *,
    scope_id: str,
    data_fingerprint: str,
    bypass_cache: bool = False,
    base_dir: Optional[Path | str] = None,
) -> Optional[AnswerCacheEntry]:
    """Tra cứu câu trả lời trong tầng nhớ theo đúng khóa chính xác:
    (normalized_question, scope_id, data_fingerprint).

    Nếu bypass_cache=True (người dùng bấm 'Hỏi lại'), trả về None để chạy tươi.
    Nếu bản ghi đã bị đánh dấu invalidated (do dislike), trả về None.
    Nếu vân tay dữ liệu đã thay đổi, khóa không khớp -> trả về None.
    """
    if bypass_cache:
        return None
    norm_q = normalize_question_for_cache(question)
    if not norm_q:
        return None
    _, key_hash = build_cache_key(question, scope_id=scope_id, data_fingerprint=data_fingerprint)
    if not key_hash:
        return None

    entries = _read_all_entries(base_dir)
    matched_idx = -1
    for idx, entry in enumerate(entries):
        if (
            entry.key_hash == key_hash
            and entry.normalized_question == norm_q
            and entry.scope_id == str(scope_id or "").strip()
            and entry.data_fingerprint == str(data_fingerprint or "").strip()
            and not entry.invalidated
        ):
            matched_idx = idx

    if matched_idx < 0:
        return None

    hit_entry = entries[matched_idx]
    hit_entry.hit_count += 1
    try:
        _write_all_entries_atomic(entries, base_dir=base_dir)
    except Exception:
        pass
    return hit_entry


def store_cached_answer(
    question: str,
    *,
    scope_id: str,
    data_fingerprint: str,
    answer_text: str,
    notebook_id: str = "",
    evidence_items: Optional[Sequence[Dict[str, Any]]] = None,
    trace_dict: Optional[Dict[str, Any]] = None,
    message_metadata: Optional[Mapping[str, Any]] = None,
    badge_data: Optional[Mapping[str, Any]] = None,
    snapshot_time_display: Optional[str] = None,
    base_dir: Optional[Path | str] = None,
) -> Optional[AnswerCacheEntry]:
    """Lưu hoặc cập nhật câu trả lời mới vào tầng nhớ local_cases.

    Ghi đè các bản ghi cũ cùng (normalized_question, scope_id) để đảm bảo bản ghi mới
    sau khi bấm 'Hỏi lại' hoặc sau khi đổi vân tay dữ liệu là bản ghi duy nhất có hiệu lực.
    """
    norm_q = normalize_question_for_cache(question)
    clean_ans = str(answer_text or "").strip()
    if not norm_q or not clean_ans:
        return None

    _, key_hash = build_cache_key(question, scope_id=scope_id, data_fingerprint=data_fingerprint)
    q_scope_hash = build_question_scope_hash(question, scope_id=scope_id)

    now = datetime.now()
    now_iso = now.isoformat(timespec="seconds")
    snap_display = str(snapshot_time_display or "").strip() or now.strftime("%H:%M:%S %d/%m/%Y")

    # Chuẩn hóa danh sách bằng chứng để serialize JSON an toàn
    serializable_ev: List[Dict[str, Any]] = []
    for item in evidence_items or ():
        if isinstance(item, Mapping):
            d_item = {}
            for k, v in item.items():
                if k == "citation_ref" and hasattr(v, "to_dict"):
                    d_item[k] = v.to_dict()
                elif isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                    d_item[k] = v
                else:
                    d_item[k] = str(v)
            serializable_ev.append(d_item)

    clean_meta: Dict[str, Any] = {}
    if isinstance(message_metadata, Mapping):
        for k, v in message_metadata.items():
            if k == "evidence_items":
                continue
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                clean_meta[k] = v
            elif isinstance(v, tuple):
                clean_meta[k] = list(v)

    clean_badge: Dict[str, Any] = {}
    if isinstance(badge_data, Mapping):
        for k, v in badge_data.items():
            if k == "evidence_items":
                continue
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                clean_badge[k] = v
            elif isinstance(v, tuple):
                clean_badge[k] = list(v)

    new_entry = AnswerCacheEntry(
        key_hash=key_hash,
        question_scope_hash=q_scope_hash,
        normalized_question=norm_q,
        scope_id=str(scope_id or "").strip(),
        data_fingerprint=str(data_fingerprint or "").strip(),
        answer_text=clean_ans,
        notebook_id=str(notebook_id or "").strip(),
        evidence_items=serializable_ev,
        trace_dict=dict(trace_dict) if isinstance(trace_dict, Mapping) else None,
        message_metadata=clean_meta,
        badge_data=clean_badge,
        created_at=now_iso,
        snapshot_time_display=snap_display,
        invalidated=False,
        invalidated_reason="",
        invalidated_at="",
        hit_count=0,
    )

    entries = _read_all_entries(base_dir)
    kept: List[AnswerCacheEntry] = [
        e for e in entries
        if not (e.normalized_question == norm_q and e.scope_id == new_entry.scope_id)
    ]
    kept.append(new_entry)
    _write_all_entries_atomic(kept, base_dir=base_dir)
    return new_entry


def invalidate_cached_answer(
    question: str,
    *,
    scope_id: Optional[str] = None,
    key_hash: Optional[str] = None,
    reason: str = "disliked_by_user",
    base_dir: Optional[Path | str] = None,
) -> int:
    """Vô hiệu hóa bản ghi trong bộ nhớ khi người dùng bấm 'không thích' (tránh khóa lỗi vào bộ nhớ).

    Nếu scope_id được cung cấp, vô hiệu hóa đúng (normalized_question, scope_id).
    Nếu scope_id để trống (None/""), vô hiệu hóa mọi bản ghi khớp normalized_question (hoặc key_hash).
    Trả về số lượng bản ghi đã bị đánh dấu vô hiệu.
    """
    norm_q = normalize_question_for_cache(question) if question else ""
    target_key_hash = str(key_hash or "").strip()
    target_scope = str(scope_id or "").strip() if scope_id is not None else ""

    if not norm_q and not target_key_hash:
        return 0

    entries = _read_all_entries(base_dir)
    if not entries:
        return 0

    now_iso = datetime.now().isoformat(timespec="seconds")
    count = 0
    for entry in entries:
        if entry.invalidated:
            continue
        match = False
        if target_key_hash and entry.key_hash == target_key_hash:
            match = True
        elif norm_q and entry.normalized_question == norm_q:
            if not target_scope or entry.scope_id == target_scope or entry.scope_id.endswith(f"|dom:{target_scope}") or entry.scope_id.startswith(f"nb:{target_scope}|"):
                match = True
        if match:
            entry.invalidated = True
            entry.invalidated_reason = reason
            entry.invalidated_at = now_iso
            count += 1

    if count > 0:
        _write_all_entries_atomic(entries, base_dir=base_dir)
    return count


def record_cache_turn_metric(
    *,
    cache_hit: bool,
    response_time_ms: float,
    key_hash: str,
    scope_id: str = "",
    data_fingerprint: str = "",
    bypass_requested: bool = False,
    conversation_id: str = "",
    base_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Ghi một dòng metric cho mỗi lượt hỏi vào `local_cases/answer_cache_metrics.jsonl`.

    TUYỆT ĐỐI KHÔNG ghi nội dung câu hỏi thô vào tệp metric hay ra ngoài: chỉ ghi `key_hash` đã băm ẩn danh.
    """
    path = cache_metrics_file(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        "cache_hit": bool(cache_hit),
        "response_time_ms": round(max(0.0, float(response_time_ms)), 2),
        "key_hash": str(key_hash or "anon"),
        "scope_id": str(scope_id or ""),
        "data_fingerprint": str(data_fingerprint or ""),
        "bypass_requested": bool(bypass_requested),
        "conversation_id": str(conversation_id or ""),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def compute_cache_metrics_summary(
    base_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Tổng hợp số liệu từ `local_cases/answer_cache_metrics.jsonl`:
    - Tổng số lượt hỏi (total_turns)
    - Số lượt trúng bộ nhớ (hit_count)
    - Số lượt không trúng / chạy tươi (miss_count)
    - Tỷ lệ trúng (hit_rate_pct)
    - Thời gian trung bình nhánh trúng (avg_hit_ms)
    - Thời gian trung bình nhánh không trúng (avg_miss_ms)
    """
    path = cache_metrics_file(base_dir)
    records: List[Dict[str, Any]] = []
    if path.is_file():
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        if isinstance(rec, dict) and "cache_hit" in rec:
                            records.append(rec)
                    except (json.JSONDecodeError, ValueError):
                        continue
        except OSError:
            pass

    total = len(records)
    hit_times = [float(r.get("response_time_ms", 0.0)) for r in records if r.get("cache_hit") is True]
    miss_times = [float(r.get("response_time_ms", 0.0)) for r in records if not r.get("cache_hit")]

    hit_count = len(hit_times)
    miss_count = len(miss_times)
    hit_rate_pct = round((hit_count / total) * 100.0, 2) if total > 0 else 0.0
    avg_hit_ms = round(sum(hit_times) / hit_count, 2) if hit_count > 0 else 0.0
    avg_miss_ms = round(sum(miss_times) / miss_count, 2) if miss_count > 0 else 0.0

    return {
        "total_turns": total,
        "hit_count": hit_count,
        "miss_count": miss_count,
        "hit_rate_pct": hit_rate_pct,
        "avg_hit_ms": avg_hit_ms,
        "avg_miss_ms": avg_miss_ms,
        "records": records,
    }


def format_fast_answer_notice(snapshot_time_display: str, locale: str = "vi") -> str:
    """Định dạng dòng chữ nhỏ dưới câu trả lời lấy từ bộ nhớ (Mục 2b)."""
    snap = str(snapshot_time_display or "").strip() or datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    return f"⚡ Trả lời nhanh từ câu hỏi đã hỏi trước — dữ liệu chốt lúc {snap}"


def serialize_evidence_items_for_cache(items: Sequence[Any]) -> List[Dict[str, Any]]:
    """Chuẩn hóa danh sách trích dẫn thành dict tuần tự hóa JSON an toàn cho answer_cache."""
    serialized: List[Dict[str, Any]] = []
    for raw in items or ():
        if not isinstance(raw, Mapping):
            continue
        item_dict = {
            k: v
            for k, v in raw.items()
            if k != "citation_ref" and isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }
        cite_ref = raw.get("citation_ref")
        if cite_ref is not None:
            for attr in ("id", "ref_type", "label", "source_file", "sheet_name", "source_row", "case_id", "page_or_sheet", "raw_text"):
                val = getattr(cite_ref, attr, None)
                if val is not None and attr not in item_dict:
                    item_dict[attr] = val
        serialized.append(item_dict)
    return serialized


def apply_cached_answer_to_conversation(
    cached_entry: AnswerCacheEntry,
    *,
    conversation_id: str,
    question: str,
    notebook_id: str = "",
    user_message_id: str = "",
    reply_to_message_id: Optional[str] = None,
) -> tuple[Any, Dict[str, Any]]:
    """Ghi tin nhắn người dùng, bản sao EvidenceTrace và câu trả lời từ bộ nhớ vào cuộc trò chuyện."""
    import uuid
    from aios_habit.workspace_chat_models import ChatMessage
    from aios_habit.workspace_chat_store import load_messages, save_evidence_trace, save_message
    from aios_habit.evidence_trace import EvidenceTrace

    existing = load_messages(conversation_id)
    user_msg = None
    if user_message_id:
        for m in existing:
            if getattr(m, "id", "") == user_message_id:
                user_msg = m
                break
    if user_msg is None and existing and existing[-1].role == "user" and (existing[-1].content or "").strip() == question.strip():
        user_msg = existing[-1]
    if user_msg is None:
        user_msg = ChatMessage(
            id=user_message_id or f"MSG-U-{uuid.uuid4().hex[:8].upper()}",
            conversation_id=conversation_id,
            role="user",
            content=question,
            reply_to_message_id=reply_to_message_id,
        )
        save_message(user_msg)

    assistant_msg_id = f"MSG-A-{uuid.uuid4().hex[:8].upper()}"
    trace_id = f"TRC-{uuid.uuid4().hex[:8].upper()}"
    eff_nb_id = notebook_id or cached_entry.notebook_id or ""
    ev_items = serialize_evidence_items_for_cache(cached_entry.evidence_items)

    try:
        if cached_entry.trace_dict and isinstance(cached_entry.trace_dict, dict):
            tr_data = dict(cached_entry.trace_dict)
            tr_data["trace_id"] = trace_id
            tr_data["conversation_id"] = conversation_id
            tr_data["notebook_id"] = eff_nb_id
            tr_data["user_message_id"] = user_msg.id
            tr_data["assistant_message_id"] = assistant_msg_id
            tr_data["query"] = question
            tr_meta = dict(tr_data.get("metadata") or {})
            tr_meta["evidence_items"] = ev_items
            tr_meta["cache_hit"] = True
            tr_meta["cache_key_hash"] = cached_entry.key_hash
            tr_data["metadata"] = tr_meta
            trace_obj = EvidenceTrace.from_dict(tr_data)
        else:
            trace_obj = EvidenceTrace(
                trace_id=trace_id,
                conversation_id=conversation_id,
                notebook_id=eff_nb_id,
                user_message_id=user_msg.id,
                assistant_message_id=assistant_msg_id,
                query=question,
                answer_text=cached_entry.answer_text,
                provenance={
                    "operational_mode": "answer_cache_hit",
                    "cache_key_hash": cached_entry.key_hash,
                    "cache_snapshot_time": cached_entry.snapshot_time_display,
                },
                metadata={
                    "evidence_items": ev_items,
                    "cache_hit": True,
                    "cache_key_hash": cached_entry.key_hash,
                },
            )
        save_evidence_trace(trace_obj)
    except Exception:
        pass

    msg_meta = dict(cached_entry.message_metadata or {})
    msg_meta.update({
        "cache_hit": True,
        "cache_snapshot_time": cached_entry.snapshot_time_display,
        "cached_question": question,
        "cache_key_hash": cached_entry.key_hash,
        "scope_id": cached_entry.scope_id,
        "notebook_id": eff_nb_id,
        "evidence_items": ev_items,
    })

    asst_msg = ChatMessage(
        id=assistant_msg_id,
        conversation_id=conversation_id,
        role="assistant",
        content=cached_entry.answer_text,
        trace_id=trace_id,
        metadata=msg_meta,
    )
    save_message(asst_msg)

    badge = dict(cached_entry.badge_data or {})
    if not badge.get("type"):
        badge["type"] = "ai_answered"
    badge.update({
        "conversation_id": conversation_id,
        "message_id": assistant_msg_id,
        "trace_id": trace_id,
        "cache_hit": True,
        "cache_snapshot_time": cached_entry.snapshot_time_display,
        "cached_question": question,
        "cache_key_hash": cached_entry.key_hash,
        "evidence_items": ev_items,
    })
    return asst_msg, badge


def capture_last_assistant_turn_to_cache(
    question: str,
    *,
    conversation_id: str,
    scope_id: str,
    data_fingerprint: str,
    notebook_id: str = "",
    badge: Optional[Mapping[str, Any]] = None,
    base_dir: Optional[Path | str] = None,
) -> Optional[AnswerCacheEntry]:
    """Thu thập câu trả lời mới nhất của trợ lý trong hội thoại kèm trích dẫn theo câu để lưu vào answer_cache."""
    if not question or not conversation_id:
        return None
    if isinstance(badge, Mapping):
        if badge.get("type") in ("local_fallback_offered", "insufficient_context", "handoff_pending"):
            return None
        if badge.get("cagent_incident"):
            return None

    from aios_habit.workspace_chat_store import load_evidence_trace, load_messages
    from aios_habit.workspace_chat_ui import extract_evidence_items_for_message

    msgs = load_messages(conversation_id)
    last_asst = next((m for m in reversed(msgs) if getattr(m, "role", "") == "assistant"), None)
    if last_asst is None:
        return None

    content = str(getattr(last_asst, "content", "") or "").strip()
    if not content or content.startswith("⚠️"):
        return None

    trace_obj = None
    trace_dict = None
    if getattr(last_asst, "trace_id", None):
        try:
            trace_obj = load_evidence_trace(str(last_asst.trace_id))
            if trace_obj is not None and hasattr(trace_obj, "to_dict"):
                trace_dict = trace_obj.to_dict()
        except Exception:
            trace_obj = None

    ev_items_raw = extract_evidence_items_for_message(
        msg=last_asst,
        display_content=content,
        trace=trace_obj,
        badge_data=badge,
        notebook_id=notebook_id,
    )
    ev_items = serialize_evidence_items_for_cache(ev_items_raw)

    # Chuẩn bị metadata cho bản ghi answer_cache (không gọi save_message thêm lần 2 để tránh nhân đôi dòng trong jsonl)
    msg_meta = dict(getattr(last_asst, "metadata", None) or {})
    msg_meta["scope_id"] = scope_id
    if notebook_id and "notebook_id" not in msg_meta:
        msg_meta["notebook_id"] = notebook_id
    if ev_items and not msg_meta.get("evidence_items"):
        msg_meta["evidence_items"] = ev_items
    msg_meta["cached_question"] = question

    return store_cached_answer(
        question,
        answer_text=content,
        scope_id=scope_id,
        data_fingerprint=data_fingerprint,
        notebook_id=notebook_id,
        evidence_items=ev_items,
        trace_dict=trace_dict,
        message_metadata=msg_meta,
        badge_data=badge,
        base_dir=base_dir,
    )

