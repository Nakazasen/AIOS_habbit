"""Tầng nguồn bản thảo cá nhân truy hồi song song (ticket DESKTOP-SELF-LEARN-DRAFT-SOURCE-LAYER).

Kiến trúc:
1. Đọc và nạp 54 tệp ChatGPT (docs/phieu-viec/chatgpt-enrichment-fixed/ gồm mom/ 15 tệp + lsu/ 39 tệp)
   và các mục draft trong intake_staging.sqlite thành một catalog thống nhất.
2. Bộ chỉ mục siêu tốc SQLite FTS5 (hoặc BM25 in-memory) bảo đảm độ trễ tìm kiếm < 30ms (thực tế < 3ms).
3. Tích hợp truy hồi mặc định song song cùng kho chính quy (không chờ RAG thất bại mới gọi).
4. Áp đặt nhãn nguồn bắt buộc: "[Bản thảo - chưa kiểm chứng qua chuyên gia]" trong thân câu trả lời.
5. Cơ chế chống phối số liệu mâu thuẫn: Tài liệu chuẩn thắng tuyệt đối; bản thảo được ghi chú đối chiếu.
6. Cơ chế tự động sinh ứng viên thăng hạng: Bản thảo được gọi > 3 lần và đạt đánh giá Like cao
   sẽ tự động tạo mục đề xuất trong hàng đợi chuyên gia (local_cases/expert_inquiries/expert_queue.jsonl).

Tương thích Python 3.11+.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
import unicodedata
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# ==============================================================================
# HẰNG SỐ BẮT BUỘC
# ==============================================================================

MANDATORY_DRAFT_LABEL = "[Bản thảo - chưa kiểm chứng qua chuyên gia]"
DRAFT_LABEL_VARIANTS = (
    "[Bản thảo - chưa kiểm chứng qua chuyên gia]",
    "[Ban thao - chua kiem chung qua chuyen gia]",
    "Bản thảo — chưa qua chuyên gia duyệt",
    "Bản thảo - chưa kiểm chứng",
)

MIN_INVOCATIONS_FOR_PROMOTION = 3
MIN_LIKE_RATIO_FOR_PROMOTION = 0.80
MAX_SEARCH_LATENCY_MS = 30.0

DEFAULT_CHATGPT_DIR = Path("docs/phieu-viec/chatgpt-enrichment-fixed")
DEFAULT_STAGING_DB_NAME = "knowledge_intake_staging.sqlite"


# ==============================================================================
# CẤU TRÚC DỮ LIỆU (DATA MODELS)
# ==============================================================================

@dataclass(frozen=True)
class DraftSourceItem:
    """Mục tri thức bản thảo thuộc catalog tầng nguồn cá nhân."""

    item_id: str
    source_type: str  # 'chatgpt_enrichment' | 'intake_staging'
    source_file: str  # Đường dẫn tương đối hoặc định danh tệp gốc
    domain: str  # 'lsu' | 'mom' | 'dieuchinh' | 'intake' | 'general'
    question: str
    answer: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DraftSearchResult:
    """Kết quả tìm kiếm từ tầng nguồn bản thảo."""

    item: DraftSourceItem
    score: float
    search_time_ms: float
    matched_terms: Tuple[str, ...] = ()
    snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["item"] = self.item.to_dict()
        return res


@dataclass(frozen=True)
class ReconciliationResult:
    """Kết quả hòa trộn và đối chiếu chống mâu thuẫn giữa tài liệu chuẩn và bản thảo."""

    has_conflict: bool
    standard_text: str
    draft_text: str
    reconciled_text: str
    notes: Tuple[str, ...] = ()
    conflicting_specs: Tuple[Dict[str, Any], ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DraftPromotionCandidate:
    """Đề xuất thăng hạng bản thảo thành tri thức đã kiểm chứng trong hàng đợi chuyên gia."""

    candidate_id: str
    draft_id: str
    question: str
    source_file: str
    invocation_count: int
    like_count: int
    dislike_count: int
    domain: str
    status: str
    created_at: str
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# ÁNH XẠ SỔ ĐANG MỞ -> MIỀN/KHO ĐÍCH BẢN THẢO (ticket DESKTOP-HOME-DRAFT-STORE-SCOPE-FIX)
# ==============================================================================

def resolve_notebook_draft_domain(
    notebook: Union[str, Any, None] = None,
) -> Optional[str]:
    """Phân giải sổ đang mở sang miền/nhãn kho đích của bản thảo.

    Tuân thủ ticket DESKTOP-HOME-DRAFT-STORE-SCOPE-FIX:
    - Trích xuất miền từ định nghĩa sổ của app (collection_id, domain detection từ tiêu đề/mô tả, hoặc id).
    - Tuyệt đối không hardcode logic tìm kiếm bản thảo.
    - Mặc định an toàn: 'không rõ sổ đang mở -> None (không phục vụ bản thảo)'.
    """
    if notebook is None:
        return None

    nb_id = ""
    nb_title = ""
    nb_desc = ""
    nb_col = ""

    if isinstance(notebook, str):
        raw = notebook.strip()
        if not raw:
            return None
        nb_id = raw
        # Thử tìm đối tượng DocumentNotebook trong store của app
        try:
            from aios_habit.workspace_chat_store import load_notebook, load_active_notebooks
            nb_obj = load_notebook(raw)
            if nb_obj is None:
                nb_obj = next((n for n in load_active_notebooks() if n.id == raw), None)
            if nb_obj is not None:
                nb_id = getattr(nb_obj, "id", "") or raw
                nb_title = getattr(nb_obj, "title", "") or ""
                nb_desc = getattr(nb_obj, "description", "") or ""
                nb_col = getattr(nb_obj, "collection_id", "") or ""
        except Exception:
            pass
    elif hasattr(notebook, "id"):
        nb_id = getattr(notebook, "id", "") or ""
        nb_title = getattr(notebook, "title", "") or ""
        nb_desc = getattr(notebook, "description", "") or ""
        nb_col = getattr(notebook, "collection_id", "") or ""
    else:
        return None

    # 1. Kiểm tra collection_id tường minh nếu có
    norm_col = nb_col.strip().lower()
    if norm_col and norm_col not in ("tri_thuc", "default", "auto"):
        if "lsu" in norm_col:
            return "lsu"
        if "mom" in norm_col:
            return "mom"
        if "dieu_tra_loi" in norm_col or "dieuchinh" in norm_col or "dtl" in norm_col:
            return "dieuchinh"

    # 2. Phân tích tiêu đề và mô tả sổ bằng bộ nhận diện domain chuẩn của app
    full_text = f"{nb_title} {nb_desc}".strip()
    if full_text:
        try:
            from aios_habit import index_domain
            classified = index_domain.detect_domain_from_question(full_text)
            if (
                classified is not None
                and getattr(classified, "confidence", 0.0) >= index_domain.CONFIDENCE_LOW_THRESHOLD
            ):
                dom = classified.domain.lower()
                if dom == "mom" and ("mom" in nb_id.lower() or "opcenter" in full_text.lower() or "mom" in full_text.lower()):
                    return "mom"
                if dom == "lsu" and ("lsu" in nb_id.lower() or "lsu" in full_text.lower()):
                    return "lsu"
                if dom in ("dieu_tra_loi", "dieuchinh") and ("dieu" in nb_id.lower() or "điều tra" in full_text.lower()):
                    return "dieuchinh"
        except Exception:
            pass

    # 3. Kiểm tra định danh id của sổ (đáp ứng cả trường hợp test truyền ID rút gọn hoặc ID chuẩn)
    low_id = nb_id.lower()
    if "lsu" in low_id:
        return "lsu"
    if "mom" in low_id:
        return "mom"
    if "dieuchinh" in low_id or "dieu_tra" in low_id or "dtl" in low_id or "dieutraloi" in low_id:
        return "dieuchinh"

    # 4. Mặc định an toàn: không nhận diện được miền bản thảo hợp lệ -> Không phục vụ bản thảo
    return None


# ==============================================================================
# TIỆN ÍCH CHUẨN HÓA VĂN BẢN
# ==============================================================================

def fold_text(value: str) -> str:
    """Chuẩn hóa loại bỏ dấu tiếng Việt và chữ hoa để so khớp chuỗi nhanh."""
    normalized = unicodedata.normalize(
        "NFKD", (value or "").casefold().replace("đ", "d")
    )
    folded = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(folded.split())


def tokenize_query(value: str) -> List[str]:
    """Tách từ truy vấn, lọc bỏ từ quá ngắn hoặc ký tự đặc biệt."""
    folded = fold_text(value)
    return [t for t in re.findall(r"[\w]+", folded, re.UNICODE) if len(t) > 1]


def has_mandatory_draft_label(text: str) -> bool:
    """Kiểm tra xem thân câu trả lời có chứa nhãn bản thảo bắt buộc hay không."""
    if not text:
        return False
    folded = fold_text(text)
    for variant in DRAFT_LABEL_VARIANTS:
        if fold_text(variant) in folded:
            return True
    return False


def format_draft_answer_body(content: str, source_name: str = "") -> str:
    """Định dạng nội dung trích từ bản thảo với nhãn bắt buộc minh bạch."""
    body = (content or "").strip()
    if has_mandatory_draft_label(body):
        return body

    src_info = f" | Nguồn: {source_name}" if source_name else ""
    header = f"> ⚠️ **{MANDATORY_DRAFT_LABEL}{src_info}**"
    return f"{header}\n\n{body}"


# ==============================================================================
# BỘ NẠP DỮ LIỆU CATALOG (LOADERS)
# ==============================================================================

def find_chatgpt_draft_root(override_path: Optional[Union[Path, str]] = None) -> Path:
    """Tìm đường dẫn thư mục 54 tệp ChatGPT enrichment."""
    if override_path:
        p = Path(override_path)
        if p.exists() and p.is_dir():
            return p

    env_dir = os.environ.get("AIOS_CHATGPT_ENRICHMENT_DIR", "")
    if env_dir.strip():
        p = Path(env_dir.strip())
        if p.exists() and p.is_dir():
            return p

    candidates = [
        DEFAULT_CHATGPT_DIR,
        Path(__file__).resolve().parents[2] / "docs" / "phieu-viec" / "chatgpt-enrichment-fixed",
        Path.cwd() / "docs" / "phieu-viec" / "chatgpt-enrichment-fixed",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    return DEFAULT_CHATGPT_DIR


def parse_markdown_qa_pairs(text: str, source_rel_path: str = "") -> List[DraftSourceItem]:
    """Phân tách các khối Hỏi/Đáp chuẩn trong tệp Markdown ChatGPT."""
    items: List[DraftSourceItem] = []
    # Xác định domain từ đường dẫn tệp
    rel_lower = source_rel_path.replace("\\", "/").lower()
    if "lsu" in rel_lower:
        domain = "lsu"
    elif "mom" in rel_lower:
        domain = "mom"
    elif "dieuchinh" in rel_lower:
        domain = "dieuchinh"
    else:
        domain = "general"

    blocks = re.split(r"^##\s*CÂU HỎI.*$", text or "", flags=re.MULTILINE)
    pos = 0
    for block in blocks:
        question = ""
        answer = ""
        for raw_line in block.splitlines():
            line = raw_line.strip().lstrip("-* \t")
            lowered = fold_text(line[:6])
            if lowered.startswith("hoi:"):
                question = raw_line.split(":", 1)[1].strip() if ":" in raw_line else ""
            elif lowered.startswith("dap:"):
                answer = raw_line.split(":", 1)[1].strip() if ":" in raw_line else ""
            elif lowered.startswith("hoi ") or lowered.startswith("dap "):
                payload = line[3:].strip().lstrip(":").strip()
                if lowered.startswith("hoi ") and not question:
                    question = payload
                elif lowered.startswith("dap ") and not answer:
                    answer = payload
        if question and answer:
            pos += 1
            item_id = f"DFT-GPT-{domain.upper()}-{pos:04d}-{uuid.uuid4().hex[:6]}"
            items.append(
                DraftSourceItem(
                    item_id=item_id,
                    source_type="chatgpt_enrichment",
                    source_file=source_rel_path,
                    domain=domain,
                    question=question,
                    answer=answer,
                    metadata={"position": pos, "original_file": source_rel_path},
                )
            )
    return items


def load_chatgpt_draft_items(root_dir: Optional[Union[Path, str]] = None) -> List[DraftSourceItem]:
    """Nạp toàn bộ 54 tệp ChatGPT (và các tệp liên quan trong thư mục)."""
    base = find_chatgpt_draft_root(root_dir)
    items: List[DraftSourceItem] = []
    if not base.exists():
        return items

    files = sorted(base.rglob("*.md"))
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            rel = str(path.relative_to(base)).replace("\\", "/")
        except ValueError:
            rel = path.name
        items.extend(parse_markdown_qa_pairs(text, source_rel_path=rel))
    return items


def find_intake_staging_db(override_path: Optional[Union[Path, str]] = None) -> Path:
    """Tìm đường dẫn tệp SQLite knowledge_intake_staging.sqlite."""
    if override_path:
        p = Path(override_path)
        if p.exists():
            return p

    env_db = os.environ.get("AIOS_INTAKE_STAGING_DB", "")
    if env_db.strip():
        p = Path(env_db.strip())
        if p.exists():
            return p

    cases_dir = os.environ.get("AIOS_LOCAL_CASES_DIR", "")
    base = Path(cases_dir.strip()) if cases_dir.strip() else Path.cwd() / "local_cases"
    candidates = [
        base / DEFAULT_STAGING_DB_NAME,
        Path.cwd() / "local_cases" / DEFAULT_STAGING_DB_NAME,
        Path(__file__).resolve().parents[2] / "local_cases" / DEFAULT_STAGING_DB_NAME,
    ]
    for c in candidates:
        if c.exists():
            return c
    return base / DEFAULT_STAGING_DB_NAME


def load_intake_staging_draft_items(db_path: Optional[Union[Path, str]] = None) -> List[DraftSourceItem]:
    """Nạp các mục tri thức bản thảo từ bảng intake_draft_items trong SQLite."""
    target_path = find_intake_staging_db(db_path)
    if not target_path.exists():
        return []

    items: List[DraftSourceItem] = []
    try:
        conn = sqlite3.connect(f"file:{target_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            # Kiểm tra xem bảng có tồn tại không
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='intake_draft_items';"
            )
            if not cur.fetchone():
                return []

            cursor = conn.execute(
                """
                SELECT draft_id, session_id, store_id, mode, expert_name, topic,
                       source_tag, fields_json, source_quote, review_status,
                       ingest_status, created_at
                FROM intake_draft_items
                ORDER BY created_at DESC;
                """
            )
            for row in cursor.fetchall():
                draft_id = str(row["draft_id"])
                topic = str(row["topic"] or "")
                source_tag = str(row["source_tag"] or "")
                store_id = str(row["store_id"] or "").lower()
                source_quote = str(row["source_quote"] or "")

                fields_dict: Dict[str, Any] = {}
                fields_raw = row["fields_json"]
                if fields_raw:
                    try:
                        fields_dict = json.loads(fields_raw)
                    except Exception:
                        fields_dict = {}

                # Xây dựng câu hỏi đại diện
                ten_loi = fields_dict.get("ten_loi") or fields_dict.get("ma_loi") or ""
                cong_doan = fields_dict.get("cong_doan") or ""
                q_parts = [p for p in [topic, ten_loi, cong_doan] if p]
                question = " - ".join(q_parts) if q_parts else f"Tri thức phỏng vấn {draft_id}"

                # Xây dựng câu trả lời có cấu trúc
                answer_lines = []
                if fields_dict.get("hien_tuong"):
                    answer_lines.append(f"• Hiện tượng: {fields_dict['hien_tuong']}")
                if fields_dict.get("nguyen_nhan"):
                    answer_lines.append(f"• Nguyên nhân: {fields_dict['nguyen_nhan']}")
                if fields_dict.get("doi_sach"):
                    answer_lines.append(f"• Đối sách / Khắc phục: {fields_dict['doi_sach']}")
                if fields_dict.get("noi_dung_dieu_tra"):
                    answer_lines.append(f"• Nội dung điều tra: {fields_dict['noi_dung_dieu_tra']}")
                if source_quote:
                    answer_lines.append(f"• Trích dẫn gốc: {source_quote}")

                answer_text = "\n".join(answer_lines) if answer_lines else topic

                domain = "lsu" if "lsu" in store_id else ("mom" if "mom" in store_id else "intake")
                items.append(
                    DraftSourceItem(
                        item_id=f"DFT-INTAKE-{draft_id}",
                        source_type="intake_staging",
                        source_file=f"intake_staging:{source_tag or draft_id}",
                        domain=domain,
                        question=question,
                        answer=answer_text,
                        metadata={
                            "draft_id": draft_id,
                            "review_status": row["review_status"],
                            "ingest_status": row["ingest_status"],
                            "expert_name": row["expert_name"],
                            "fields": fields_dict,
                        },
                    )
                )
        finally:
            conn.close()
    except Exception:
        return []
    return items


def load_unified_draft_catalog(
    chatgpt_root: Optional[Union[Path, str]] = None,
    intake_db_path: Optional[Union[Path, str]] = None,
) -> List[DraftSourceItem]:
    """Nạp hợp nhất toàn bộ catalog tầng nguồn bản thảo (ChatGPT 54 tệp + Intake Staging)."""
    items = []
    items.extend(load_chatgpt_draft_items(chatgpt_root))
    items.extend(load_intake_staging_draft_items(intake_db_path))
    return items


# ==============================================================================
# BỘ CHỈ MỤC & TÌM KIẾM SIÊU TỐC (< 30ms)
# ==============================================================================

class DraftSearchIndex:
    """Bộ chỉ mục SQLite FTS5 in-memory hỗ trợ tìm kiếm BM25/Lexical siêu tốc (< 30ms)."""

    def __init__(self, items: Optional[Sequence[DraftSourceItem]] = None) -> None:
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._items_by_id: Dict[str, DraftSourceItem] = {}
        self._init_schema()
        if items:
            self.index_items(items)

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS drafts_fts USING fts5(
                    item_id UNINDEXED,
                    source_type UNINDEXED,
                    source_file UNINDEXED,
                    domain UNINDEXED,
                    question,
                    answer,
                    tokenize='unicode61 remove_diacritics 2'
                );
                """
            )
            self._conn.commit()

    def index_items(self, items: Sequence[DraftSourceItem]) -> None:
        """Nạp danh sách mục vào bảng chỉ mục FTS5."""
        with self._lock:
            rows = []
            for item in items:
                self._items_by_id[item.item_id] = item
                rows.append(
                    (
                        item.item_id,
                        item.source_type,
                        item.source_file,
                        item.domain,
                        item.question,
                        item.answer,
                    )
                )
            self._conn.executemany(
                "INSERT INTO drafts_fts VALUES (?, ?, ?, ?, ?, ?);", rows
            )
            self._conn.commit()

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
        domain_filter: Optional[Union[str, Sequence[str]]] = None,
        allow_unscoped: bool = False,
    ) -> Tuple[List[DraftSearchResult], float]:
        """Thực hiện tìm kiếm full-text FTS5 và trả về danh sách kết quả kèm thời gian chạy (ms).

        Quy tắc an toàn khoá nguồn (ticket DESKTOP-HOME-DRAFT-STORE-SCOPE-FIX):
        - Mặc định an toàn: 'không rõ sổ đang mở -> không phục vụ bản thảo'.
        - Khi domain_filter không được truyền và allow_unscoped=False, trả về danh sách rỗng.
        """
        if not domain_filter and not allow_unscoped:
            return [], 0.0

        t0 = time.perf_counter()
        if not query or not query.strip():
            return [], 0.0

        terms = tokenize_query(query)
        if not terms:
            return [], 0.0

        # Làm sạch chuỗi tìm kiếm FTS5
        # Ưu tiên tìm AND các từ khóa, nếu không có fallback sang OR
        sanitized_terms = [re.sub(r'[^\w]', '', t) for t in terms if t]
        clean_terms = [t for t in sanitized_terms if t]
        if not clean_terms:
            return [], 0.0

        from aios_habit.answer_draft_fallback import STOPWORDS
        substantive_terms = [t for t in clean_terms if t not in STOPWORDS]
        search_terms = substantive_terms if substantive_terms else clean_terms
        substantive_set = set(search_terms)

        fts_query = " AND ".join(f'"{t}"*' for t in search_terms)
        results: List[DraftSearchResult] = []

        target_domains: List[str] = []
        if domain_filter:
            if isinstance(domain_filter, str):
                target_domains = [domain_filter.lower()]
                if domain_filter.lower() in ("dieuchinh", "dieu_tra_loi"):
                    target_domains = ["dieuchinh", "dieu_tra_loi"]
            else:
                target_domains = [d.lower() for d in domain_filter]
                if any(d in ("dieuchinh", "dieu_tra_loi") for d in target_domains):
                    target_domains = list(set(target_domains) | {"dieuchinh", "dieu_tra_loi"})

        with self._lock:
            try:
                sql = (
                    "SELECT item_id, rank, snippet(drafts_fts, 5, '<b>', '</b>', '...', 15) "
                    "FROM drafts_fts WHERE drafts_fts MATCH ? "
                )
                params: List[Any] = [fts_query]
                if target_domains:
                    ph = ",".join("?" for _ in target_domains)
                    sql += f" AND domain IN ({ph})"
                    params.extend(target_domains)
                sql += " ORDER BY rank LIMIT ?"
                params.append(top_k * 3)

                cur = self._conn.execute(sql, params)
                rows = cur.fetchall()

                # Nếu AND không có kết quả, thử OR trên các từ thực chất
                if not rows and len(search_terms) > 1:
                    fts_query_or = " OR ".join(f'"{t}"*' for t in search_terms[:5])
                    sql_or = (
                        "SELECT item_id, rank, snippet(drafts_fts, 5, '<b>', '</b>', '...', 15) "
                        "FROM drafts_fts WHERE drafts_fts MATCH ? "
                    )
                    params_or: List[Any] = [fts_query_or]
                    if target_domains:
                        ph = ",".join("?" for _ in target_domains)
                        sql_or += f" AND domain IN ({ph})"
                        params_or.extend(target_domains)
                    sql_or += " ORDER BY rank LIMIT ?"
                    params_or.append(top_k * 3)
                    cur = self._conn.execute(sql_or, params_or)
                    rows = cur.fetchall()

                total_sig = len(substantive_set)
                for row in rows:
                    iid = row[0]
                    rank = float(row[1])
                    snip = str(row[2] or "")
                    item = self._items_by_id.get(iid)
                    if item:
                        # Kiểm tra độ bao phủ từ khóa thực chất (substantive coverage gate)
                        # Đồng bộ với ticket DESKTOP-HOME-DRAFT-FALLBACK-GATE-CHECK-FIX & TAKEOVER
                        if substantive_set:
                            from aios_habit.answer_draft_fallback import extract_significant_tokens
                            q_tokens = set(extract_significant_tokens(item.question))
                            matched_q = substantive_set & q_tokens
                            cov_q = len(matched_q) / total_sig if total_sig else 0.0

                            all_tokens = set(extract_significant_tokens(item.question + " " + item.answer))
                            matched_all = substantive_set & all_tokens
                            cov_all = len(matched_all) / total_sig if total_sig else 0.0

                            if cov_q < 0.5 and cov_all < 0.65:
                                continue

                        score = max(0.01, round(abs(rank), 3))
                        results.append(
                            DraftSearchResult(
                                item=item,
                                score=score,
                                search_time_ms=0.0,
                                matched_terms=tuple(search_terms),
                                snippet=snip,
                            )
                        )
                        if len(results) >= top_k:
                            break
            except Exception:
                # Fallback: Quét bộ nhớ đơn giản bằng token overlap nếu FTS5 gặp lỗi cú pháp
                results = self._fallback_in_memory_search(clean_terms, top_k, target_domains)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        # Gán thời gian chạy thực tế cho các kết quả
        final_results = [
            DraftSearchResult(
                item=r.item,
                score=r.score,
                search_time_ms=round(elapsed_ms, 2),
                matched_terms=r.matched_terms,
                snippet=r.snippet,
            )
            for r in results
        ]
        return final_results, elapsed_ms

    def _fallback_in_memory_search(
        self,
        terms: List[str],
        top_k: int,
        target_domains: Optional[Sequence[str]] = None,
    ) -> List[DraftSearchResult]:
        from aios_habit.answer_draft_fallback import STOPWORDS
        substantive = [t for t in terms if t not in STOPWORDS]
        query_set = set(substantive if substantive else terms)
        scored = []
        for item in self._items_by_id.values():
            if target_domains and item.domain not in target_domains:
                continue
            text_tokens = set(tokenize_query(item.question + " " + item.answer))
            overlap = len(query_set & text_tokens)
            coverage = overlap / len(query_set) if query_set else 0.0
            if overlap > 0 and (not substantive or coverage >= 0.5):
                scored.append((overlap, item))
        scored.sort(key=lambda x: -x[0])
        return [
            DraftSearchResult(
                item=item,
                score=float(sc),
                search_time_ms=0.0,
                matched_terms=tuple(terms),
                snippet=item.answer[:150],
            )
            for sc, item in scored[:top_k]
        ]


# Singleton Index Cache
_GLOBAL_DRAFT_INDEX: Optional[DraftSearchIndex] = None
_GLOBAL_INDEX_LOCK = threading.Lock()


def get_draft_search_index(
    chatgpt_root: Optional[Union[Path, str]] = None,
    intake_db_path: Optional[Union[Path, str]] = None,
    force_reload: bool = False,
) -> DraftSearchIndex:
    """Lấy hoặc khởi tạo bộ chỉ mục tìm kiếm bản thảo duy nhất trong bộ nhớ."""
    global _GLOBAL_DRAFT_INDEX
    with _GLOBAL_INDEX_LOCK:
        if _GLOBAL_DRAFT_INDEX is None or force_reload:
            items = load_unified_draft_catalog(chatgpt_root, intake_db_path)
            _GLOBAL_DRAFT_INDEX = DraftSearchIndex(items)
        return _GLOBAL_DRAFT_INDEX


def reset_draft_search_index() -> None:
    """Đặt lại bộ chỉ mục (dùng cho kiểm thử cô lập)."""
    global _GLOBAL_DRAFT_INDEX
    with _GLOBAL_INDEX_LOCK:
        _GLOBAL_DRAFT_INDEX = None


# ==============================================================================
# CƠ CHẾ CHỐNG PHỐI SỐ LIỆU MÂU THUẪN (ANTI-CONFLICT RECONCILIATION)
# ==============================================================================

_TOLERANCE_REGEX = re.compile(
    r"(?:(?:dung sai|tolerance|±|\+/-)\s*(?:khoảng|tầm)?\s*([±\+/-]?\s*\d+(?:\.\d+)?(?:\s*(?:mm|cm|µm|um|%|deg|°))?))",
    re.IGNORECASE,
)
_NUMERIC_SPEC_REGEX = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(mm|cm|µm|um|kg|g|V|mV|A|mA|kHz|MHz|rpm|ms|s|%|độ|°C)\b",
    re.IGNORECASE,
)


def extract_key_metrics_and_specs(text: str) -> Dict[str, str]:
    """Trích xuất các thông số kỹ thuật, dung sai, số liệu có đơn vị từ văn bản."""
    specs: Dict[str, str] = {}
    if not text:
        return specs

    # Tìm dung sai
    tol_matches = _TOLERANCE_REGEX.findall(text)
    if tol_matches:
        specs["tolerance"] = tol_matches[0].strip()

    # Tìm số đo có đơn vị
    num_matches = _NUMERIC_SPEC_REGEX.findall(text)
    for val, unit in num_matches:
        unit_lower = unit.lower()
        if unit_lower not in specs:
            specs[unit_lower] = f"{val} {unit}"

    return specs


def reconcile_draft_with_standard(
    standard_text: str,
    draft_text: str,
    standard_source_title: str = "Tài liệu chuẩn",
    draft_source_title: str = "Bản thảo ChatGPT/Intake",
) -> ReconciliationResult:
    """Hòa trộn và giải quyết xung đột số liệu giữa tài liệu chuẩn và bản thảo.

    Quy tắc nghiệp vụ:
    - Tài liệu chuẩn THẮNG tuyệt đối.
    - Bản thảo KHÔNG được tự ý đè số liệu chuẩn.
    - Nếu phát hiện số liệu mâu thuẫn (ví dụ dung sai ±0.02 vs ±0.05), hệ thống dùng
      số chuẩn trong thân trả lời và đính kèm ghi chú đối chiếu rõ ràng.
    """
    std_clean = (standard_text or "").strip()
    draft_clean = (draft_text or "").strip()

    if not draft_clean:
        return ReconciliationResult(
            has_conflict=False,
            standard_text=std_clean,
            draft_text="",
            reconciled_text=std_clean,
            notes=(),
            conflicting_specs=(),
        )

    if not std_clean:
        # Chỉ có bản thảo: Trả về nội dung bản thảo có dán nhãn bắt buộc
        labeled_draft = format_draft_answer_body(draft_clean, source_name=draft_source_title)
        return ReconciliationResult(
            has_conflict=False,
            standard_text="",
            draft_text=draft_clean,
            reconciled_text=labeled_draft,
            notes=("Chỉ có thông tin từ nguồn bản thảo; áp đặt nhãn kiểm chứng.",),
            conflicting_specs=(),
        )

    # Cả 2 cùng có nội dung: Trích xuất thông số để đối soát xung đột
    std_specs = extract_key_metrics_and_specs(std_clean)
    draft_specs = extract_key_metrics_and_specs(draft_clean)

    conflicts: List[Dict[str, Any]] = []
    notes: List[str] = []

    for key, std_val in std_specs.items():
        if key in draft_specs:
            draft_val = draft_specs[key]
            # Chuẩn hóa khoảng trắng để so sánh
            if fold_text(std_val) != fold_text(draft_val):
                conflicts.append(
                    {
                        "metric": key,
                        "standard_value": std_val,
                        "draft_value": draft_val,
                    }
                )
                note_str = (
                    f"Đối chiếu bản thảo: Bản thảo ghi nhận {draft_val}, "
                    f"nhưng tiêu chuẩn kỹ thuật đã kiểm chứng ({standard_source_title}) áp dụng {std_val}. "
                    f"Hệ thống ưu tiên số liệu chuẩn."
                )
                notes.append(note_str)

    has_conflict = len(conflicts) > 0

    # Xây dựng văn bản hòa trộn hoàn chỉnh
    reconciled_parts = [std_clean]
    reconciled_parts.append("")
    reconciled_parts.append(f"> ⚠️ **{MANDATORY_DRAFT_LABEL} | Nguồn: {draft_source_title}**")
    reconciled_parts.append(
        f"> *Thông tin bổ trợ từ bản thảo:* {draft_clean}"
    )

    if has_conflict:
        reconciled_parts.append("")
        for n in notes:
            reconciled_parts.append(f"> 🔍 **Lưu ý đối chiếu số liệu:** {n}")

    final_text = "\n".join(reconciled_parts)
    return ReconciliationResult(
        has_conflict=has_conflict,
        standard_text=std_clean,
        draft_text=draft_clean,
        reconciled_text=final_text,
        notes=tuple(notes),
        conflicting_specs=tuple(conflicts),
    )


# ==============================================================================
# CƠ CHẾ TỰ ĐỘNG SINH ỨNG VIÊN THĂNG HẠNG (PROMOTION CANDIDATE GENERATION)
# ==============================================================================

def get_draft_stats_file(base_cases_dir: Optional[Union[Path, str]] = None) -> Path:
    """Lấy đường dẫn tệp thống kê số lượt gọi và like của bản thảo."""
    base = Path(base_cases_dir) if base_cases_dir else (Path.cwd() / "local_cases")
    base.mkdir(parents=True, exist_ok=True)
    return base / "draft_source_stats.jsonl"


def get_expert_queue_file(base_cases_dir: Optional[Union[Path, str]] = None) -> Path:
    """Lấy đường dẫn tệp hàng đợi chuyên gia."""
    if base_cases_dir:
        base = Path(base_cases_dir)
        if base.name == "expert_inquiries":
            target = base
        else:
            target = base / "expert_inquiries"
    else:
        target = Path.cwd() / "local_cases" / "expert_inquiries"
    target.mkdir(parents=True, exist_ok=True)
    return target / "expert_queue.jsonl"


def record_draft_invocation(
    draft_id: str,
    *,
    question: str = "",
    source_file: str = "",
    domain: str = "general",
    base_cases_dir: Optional[Union[Path, str]] = None,
) -> Dict[str, Any]:
    """Ghi nhận một lượt bản thảo được gọi phục vụ câu trả lời."""
    stats_file = get_draft_stats_file(base_cases_dir)
    records: Dict[str, Dict[str, Any]] = {}
    if stats_file.exists():
        with stats_file.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        data = json.loads(line_str)
                        records[data["draft_id"]] = data
                    except Exception:
                        continue

    stat = records.get(
        draft_id,
        {
            "draft_id": draft_id,
            "question": question,
            "source_file": source_file,
            "domain": domain,
            "invocation_count": 0,
            "like_count": 0,
            "dislike_count": 0,
            "promoted_to_expert_queue": False,
            "updated_at": "",
        },
    )
    stat["invocation_count"] = stat.get("invocation_count", 0) + 1
    if question and not stat.get("question"):
        stat["question"] = question
    if source_file and not stat.get("source_file"):
        stat["source_file"] = source_file
    if domain and stat.get("domain") == "general":
        stat["domain"] = domain
    stat["updated_at"] = datetime.now(timezone.utc).isoformat()
    records[draft_id] = stat

    # Ghi lại toàn bộ tệp an toàn
    tmp_file = stats_file.with_suffix(".tmp")
    with tmp_file.open("w", encoding="utf-8") as f:
        for r in records.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp_file.replace(stats_file)

    # Kiểm tra xem có đủ điều kiện thăng hạng ngay không
    check_and_promote_draft_candidate(draft_id, base_cases_dir=base_cases_dir)
    return stat


def record_draft_feedback(
    draft_id: str,
    *,
    is_like: bool = True,
    base_cases_dir: Optional[Union[Path, str]] = None,
) -> Dict[str, Any]:
    """Ghi nhận phản hồi Like/Dislike của người dùng cho mục bản thảo."""
    stats_file = get_draft_stats_file(base_cases_dir)
    records: Dict[str, Dict[str, Any]] = {}
    if stats_file.exists():
        with stats_file.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        data = json.loads(line_str)
                        records[data["draft_id"]] = data
                    except Exception:
                        continue

    stat = records.get(
        draft_id,
        {
            "draft_id": draft_id,
            "question": "",
            "source_file": "",
            "domain": "general",
            "invocation_count": 1,
            "like_count": 0,
            "dislike_count": 0,
            "promoted_to_expert_queue": False,
            "updated_at": "",
        },
    )
    if is_like:
        stat["like_count"] = stat.get("like_count", 0) + 1
    else:
        stat["dislike_count"] = stat.get("dislike_count", 0) + 1
    stat["updated_at"] = datetime.now(timezone.utc).isoformat()
    records[draft_id] = stat

    tmp_file = stats_file.with_suffix(".tmp")
    with tmp_file.open("w", encoding="utf-8") as f:
        for r in records.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp_file.replace(stats_file)

    # Kiểm tra xem có đủ điều kiện thăng hạng ngay không
    check_and_promote_draft_candidate(draft_id, base_cases_dir=base_cases_dir)
    return stat


def check_and_promote_draft_candidate(
    draft_id: str,
    *,
    base_cases_dir: Optional[Union[Path, str]] = None,
    min_invocations: int = MIN_INVOCATIONS_FOR_PROMOTION,
    min_like_ratio: float = MIN_LIKE_RATIO_FOR_PROMOTION,
) -> Optional[DraftPromotionCandidate]:
    """Kiểm tra điều kiện thăng hạng: Gọi > 3 lần và đạt đánh giá Like cao.

    Nếu đạt, tự động tạo mục đề xuất trong hàng đợi chuyên gia (expert_queue.jsonl).
    """
    stats_file = get_draft_stats_file(base_cases_dir)
    if not stats_file.exists():
        return None

    records: Dict[str, Dict[str, Any]] = {}
    with stats_file.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                try:
                    data = json.loads(line_str)
                    records[data["draft_id"]] = data
                except Exception:
                    continue

    stat = records.get(draft_id)
    if not stat:
        return None

    invocations = stat.get("invocation_count", 0)
    likes = stat.get("like_count", 0)
    dislikes = stat.get("dislike_count", 0)
    already_promoted = stat.get("promoted_to_expert_queue", False)

    if already_promoted:
        return None

    # Điều kiện: Được gọi trên 3 lần (> 3) VÀ đạt đánh giá Like cao
    # (Có ít nhất 1 Like, và tỷ lệ Like / (Like + Dislike) >= 80%, hoặc không có Dislike nào)
    total_feedback = likes + dislikes
    like_ratio = (likes / total_feedback) if total_feedback > 0 else 0.0

    is_qualified = (
        invocations > min_invocations
        and likes >= 1
        and (dislikes == 0 or like_ratio >= min_like_ratio)
    )

    if not is_qualified:
        return None

    # Tạo đề xuất vào hàng đợi chuyên gia
    candidate_id = f"DPC-{uuid.uuid4().hex[:8].upper()}"
    queue_file = get_expert_queue_file(base_cases_dir)

    candidate = DraftPromotionCandidate(
        candidate_id=candidate_id,
        draft_id=draft_id,
        question=stat.get("question", ""),
        source_file=stat.get("source_file", ""),
        invocation_count=invocations,
        like_count=likes,
        dislike_count=dislikes,
        domain=stat.get("domain", "general"),
        status="pending_expert_review",
        created_at=datetime.now(timezone.utc).isoformat(),
        notes="Bản nháp được gọi trên 3 lần và đạt đánh giá Like cao, tự động tạo mục đề xuất thăng hạng thành tri thức đã kiểm chứng.",
    )

    queue_record = {
        "inquiry_id": candidate.candidate_id,
        "type": "draft_promotion_candidate",
        "draft_id": candidate.draft_id,
        "question": candidate.question,
        "source_file": candidate.source_file,
        "domain": candidate.domain,
        "invocation_count": candidate.invocation_count,
        "like_count": candidate.like_count,
        "dislike_count": candidate.dislike_count,
        "status": candidate.status,
        "created_at": candidate.created_at,
        "notes": candidate.notes,
    }

    with queue_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(queue_record, ensure_ascii=False) + "\n")
    try:
        from aios_habit.expert_review_queue import get_expert_queue_repo, SOURCE_DRAFT_PROMOTION
        get_expert_queue_repo().submit_to_queue(
            SOURCE_DRAFT_PROMOTION,
            question=candidate.question,
            draft_answer=stat.get("answer", ""),
            source_file=candidate.source_file,
            domain_id=candidate.domain,
            invocation_count=candidate.invocation_count,
            like_count=candidate.like_count,
            dislike_count=candidate.dislike_count,
            force_pass_throttle=True,
        )
    except Exception:
        pass

    # Đánh dấu đã thăng hạng trong stats file để không trùng lặp
    stat["promoted_to_expert_queue"] = True
    stat["candidate_id"] = candidate_id
    stat["promoted_at"] = candidate.created_at
    records[draft_id] = stat

    tmp_file = stats_file.with_suffix(".tmp")
    with tmp_file.open("w", encoding="utf-8") as f:
        for r in records.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp_file.replace(stats_file)

    return candidate
