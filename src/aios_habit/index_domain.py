"""Knowledge domain taxonomy for the split RAG index.

Three knowledge blocks, decided by the user (2026-10-03): everything is split,
no single mixed index is kept.

- ``lsu``         -- Laser Scan Unit / tool JIG knowledge (de tai anh 1).
- ``dieu_tra_loi`` -- error investigation knowledge, Steps 0-5 (de tai anh 2).
- ``mom``        -- MOM / MES / WMS system knowledge (separate system).

This module has no dependency on other ``aios_habit`` modules so it can be
used by offline tooling (split script, tests) without importing the app.
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, NamedTuple, Optional, Sequence, Set

DOMAIN_LSU = "lsu"
DOMAIN_DIEU_TRA_LOI = "dieu_tra_loi"
DOMAIN_MOM = "mom"
DOMAIN_TONG_HOP = "tong_hop"

DOMAINS = (DOMAIN_LSU, DOMAIN_DIEU_TRA_LOI, DOMAIN_MOM)
KNOWLEDGE_BLOCKS = (DOMAIN_LSU, DOMAIN_DIEU_TRA_LOI, DOMAIN_MOM, DOMAIN_TONG_HOP)

DOMAIN_DISPLAY = {
    DOMAIN_LSU: "LSU",
    DOMAIN_DIEU_TRA_LOI: "Điều tra lỗi",
    DOMAIN_MOM: "MOM",
    DOMAIN_TONG_HOP: "Tổng hợp",
}

# One on-disk collection per domain; the collection id matches the domain id.
DOMAIN_COLLECTION_IDS = {
    DOMAIN_LSU: "lsu",
    DOMAIN_DIEU_TRA_LOI: "dieu_tra_loi",
    DOMAIN_MOM: "mom",
    DOMAIN_TONG_HOP: "tong_hop",
}

# Legacy single mixed collection id (mirrors workspace_chat_models.DEFAULT_COLLECTION_ID).
LEGACY_COLLECTION_ID = "tri_thuc"

# Documents with no keyword signal at all are still assigned somewhere -- the
# split must not drop documents. They land in the error-investigation block
# because AIOS_habbit's core mission is the Steps 0-5 error investigation
# system, with confidence 0 so the manifest flags them for human review.
FALLBACK_DOMAIN = DOMAIN_DIEU_TRA_LOI

# Below this confidence the question/domain is reported as "ambiguous".
CONFIDENCE_LOW_THRESHOLD = 0.4

# Name/path hits count more than body-text hits: file names rarely lie.
NAME_PATH_WEIGHT = 3.0
TEXT_WEIGHT = 1.0
# Cap per-keyword hit count so one very long document cannot dominate.
MAX_HITS_PER_KEYWORD = 5

DOMAIN_ROUTING_ENV_VAR = "AIOS_DOMAIN_ROUTING_ENABLED"


class Classification(NamedTuple):
    domain: str
    confidence: float
    reason: str


# (regex, weight, label) per domain. Labels are used in the human reason string.
_KEYWORD_RULES: Mapping[str, Sequence[tuple[str, float, str]]] = {
    DOMAIN_LSU: (
        (r"\blsu\b", 2.0, "LSU"),
        (r"\bjig\b", 2.0, "jig"),
        ("治具", 2.5, "治具"),  # jig (kanji) -- log jig belongs to LSU
        (r"tape", 2.0, "tape"),  # tape attachment data belongs to LSU
        (r"\bmirror\b", 2.0, "mirror"),  # polygon mirror: core LSU part
        (r"log", 1.5, "log"),  # bare "log" leans LSU (log jig)
        (r"fintest", 2.0, "fintest"),
        (r"fin\s*test", 2.0, "fin test"),
        (r"\bselno\b", 2.0, "SelNo"),
        (r"bowskew", 2.0, "bowskew"),
        (r"laser\s*scan", 2.0, "laser scan"),
        (r"scan\s*unit", 1.5, "scan unit"),
        (r"polygon", 1.5, "polygon"),
        (r"tool\s*jig", 2.0, "tool jig"),
        (r"log\s*jig", 2.0, "log jig"),
        (r"lsu[\s_\-]*log", 1.5, "log LSU"),
        (r"\bskew\b", 2.5, "skew"),
        (r"\bbeam\b", 2.0, "beam"),
        ("beam径", 2.5, "beam径"),
        (r"\b(?:dmt|pmt)\b", 2.0, "DMT/PMT"),
        (r"dmt[\s_\-–—]+pmt", 3.0, "DMT-PMT"),
        (r"\b[gG]\d{1,2}\b", 2.0, "điểm đo G"),
        (r"\b(?:nominal|dung\s*sai|giới\s*hạn)\b", 1.5, "thông số đo lường"),
        (r"(?:\b|(?<=_))(?:mount[\s_]*ld|ld[\s_]*block)(?:\b|(?=_))", 2.5, "khối LD"),
        (r"(?:\b|(?<=_))iris(?:\b|(?=_))", 2.5, "Iris LSU"),
        (r"(?:\b|(?<=_))bow[\s_]*over[\s_]*adjust", 3.0, "BowOverAdjust"),
        (r"(?:\b|(?<=_))unit[\s_]*test", 2.0, "UnitTest"),
    ),
    DOMAIN_DIEU_TRA_LOI: (
        (r"\bkdtps\b", 2.0, "KDTPS"),
        (r"ktd[-_]", 3.0, "KTD-"),  # error-case list filename prefix
        (r"(?<!wsc)[_\-]c\d{4}", 2.5, "mã Cxxxx"),  # _C0650 style (no leading \b: hex names)
        (r"jam\d*", 2.5, "JAM"),  # paper jam codes: JAM4709, Jam0501...
        (r"error\d*", 2.0, "error"),  # Error56, Error80, ERROR 0801...
        ("エラー", 2.5, "エラー"),
        ("自己診断", 2.5, "自己診断"),  # self-diagnosis
        ("不具合", 2.5, "不具合"),  # defect/failure
        ("異常", 2.0, "異常"),  # abnormality
        ("エラーコード", 2.5, "エラーコード"),
        ("エラコード", 2.0, "エラコード"),  # common misspelling variant
        ("調査報告", 2.5, "調査報告"),  # investigation report (ja)
        ("调查报告", 2.5, "调查报告"),  # investigation report (zh)
        ("一覧表", 1.0, "一覧表"),  # list/table (error lists in this corpus)
        ("DRBFM", 2.5, "DRBFM"),  # Design Review Based on Failure Mode
        (r"maintenance[\s_\-]*mode", 2.0, "maintenance mode"),
        ("信号", 1.0, "信号"),  # signal (error signal docs)
        ("発生", 1.5, "発生"),  # occurred (ja)
        ("发生", 1.5, "发生"),  # occurred (zh)
        (r"\bng\b", 1.0, "NG"),
        # Hardware reference docs live in the error-investigation corpus
        # (user's Drive folder "Sơ đồ điện", error-code lists).
        ("回路図", 1.5, "回路図"),  # circuit diagram
        ("配線図", 1.5, "配線図"),  # wiring diagram
        ("ブロック図", 1.5, "ブロック図"),  # block diagram
        (r"30[23][a-z]{1,2}\d", 1.5, "part 30x"),  # Kyocera part numbers: 302XC, 302ND, 303V...
        (r"3v2[a-z]", 1.5, "part 3V2"),  # 3V2XC/XD/XF/ND...
        (r"7pa\w+", 1.5, "part 7PA"),
        (r"pa\d+[a-z]", 1.0, "part PA"),
        (r"\bassy", 1.0, "ASSY"),
        (r"pwb", 1.0, "PWB"),  # printed wiring board
        ("出荷検査", 1.5, "出荷検査"),  # shipping inspection (QA hold)
        (r"\bf\d{3}\b", 2.0, "mã Fxxx"),
        (r"hiện tượng", 1.5, "hiện tượng"),
        (r"nguyên nhân", 1.5, "nguyên nhân"),
        (r"đối sách", 1.5, "đối sách"),
        (r"điều tra", 1.0, "điều tra"),
        (r"bảng mã lỗi", 2.0, "bảng mã lỗi"),
        (r"mã lỗi", 1.5, "mã lỗi"),
        (r"error\s*code", 1.5, "error code"),
        (r"\b4m\b", 1.0, "4M"),
        (r"\bqcc\b", 1.0, "QCC"),
        (r"countermeasure", 1.5, "countermeasure"),
        (r"khắc phục", 1.0, "khắc phục"),
        (r"investigat", 1.0, "investigation"),
        (r"\blỗi\b", 0.5, "lỗi"),
    ),
    DOMAIN_MOM: (
        (r"\bmom\b", 2.0, "MOM"),
        (r"opcenter", 2.0, "Opcenter"),
        (r"\bmes\b", 1.5, "MES"),
        (r"\bwms\b", 1.5, "WMS"),
        ("仕様書", 2.0, "仕様書"),
        (r"revup", 1.5, "RevUp"),
        (r"\bagv\b", 1.5, "AGV"),
        (r"matecon", 1.5, "matecon"),
        (r"tanaban", 1.5, "tanaban"),
        (r"oricon", 1.5, "oricon"),
        (r"\bams\b", 1.0, "AMS"),
        (r"staging", 1.0, "staging"),
        ("出庫", 1.5, "出庫"),
        ("入庫", 1.5, "入庫"),
        ("インターフェイス", 1.0, "インターフェイス"),
        (r"giao diện hệ thống", 1.0, "giao diện hệ thống"),
    ),
}

_COMPILED_RULES: dict[str, tuple[tuple[re.Pattern[str], float, str], ...]] = {
    domain: tuple((re.compile(pattern, re.IGNORECASE), weight, label) for pattern, weight, label in rules)
    for domain, rules in _KEYWORD_RULES.items()
}


def _score_text(text: str, weight: float) -> tuple[dict[str, float], dict[str, list[str]]]:
    scores: dict[str, float] = {domain: 0.0 for domain in DOMAINS}
    hits: dict[str, list[str]] = {domain: [] for domain in DOMAINS}
    lowered = text or ""
    if not lowered.strip():
        return scores, hits
    for domain in DOMAINS:
        for pattern, kw_weight, label in _COMPILED_RULES[domain]:
            count = len(pattern.findall(lowered))
            if count:
                capped = min(count, MAX_HITS_PER_KEYWORD)
                scores[domain] += capped * kw_weight * weight
                hits[domain].append("%s×%d" % (label, capped))
    return scores, hits


def _combine(scores_a: dict[str, float], scores_b: dict[str, float]) -> dict[str, float]:
    return {domain: scores_a[domain] + scores_b[domain] for domain in DOMAINS}


def _build_classification(
    scores: dict[str, float],
    hits: dict[str, list[str]],
    *,
    source: str,
    no_signal_reason: str,
) -> Classification:
    ranked = sorted(DOMAINS, key=lambda d: scores[d], reverse=True)
    top, second = ranked[0], ranked[1]
    total_top = scores[top]
    if total_top <= 0:
        return Classification(
            FALLBACK_DOMAIN,
            0.0,
            "%s: %s" % (source, no_signal_reason),
        )
    confidence = total_top / (total_top + scores[second] + 1.0)
    detail = ", ".join(
        "%s(%s)" % (DOMAIN_DISPLAY[d], ", ".join(hits[d])) for d in ranked if hits[d]
    )
    return Classification(
        top,
        round(min(1.0, max(0.0, confidence)), 3),
        "%s: khớp từ khóa %s" % (source, detail),
    )


def classify_document(
    source_name: str,
    source_path: str,
    text_sample: str,
    ledger_hint: Optional[Mapping[str, str]] = None,
) -> Classification:
    """Classify one document into exactly one domain.

    Returns a ``Classification`` named tuple ``(domain, confidence, reason)``.
    ``confidence`` is in ``0..1``. Documents with no signal at all fall back
    to :data:`FALLBACK_DOMAIN` with confidence ``0.0`` so the split never
    drops a document; the manifest records the low confidence for review.
    """
    name_path = " ".join(part for part in (source_name or "", source_path or "") if part)
    name_scores, name_hits = _score_text(name_path, NAME_PATH_WEIGHT)
    text_scores, text_hits = _score_text(text_sample or "", TEXT_WEIGHT)
    scores = _combine(name_scores, text_scores)
    merged_hits = {
        domain: name_hits[domain] + [h for h in text_hits[domain] if h not in name_hits[domain]]
        for domain in DOMAINS
    }
    result = _build_classification(
        scores,
        merged_hits,
        source="tài liệu",
        no_signal_reason="không có tín hiệu từ khóa; gán mặc định minh bạch",
    )
    if ledger_hint:
        hint_bits = " ".join(
            str(ledger_hint.get(key) or "") for key in ("source_scope", "source_id", "source_fingerprint")
        )
        hint_scores, hint_hits = _score_text(hint_bits, NAME_PATH_WEIGHT)
        if sum(hint_scores.values()) > 0:
            scores = _combine(scores, hint_scores)
            merged_hits = {
                domain: merged_hits[domain] + [h for h in hint_hits[domain] if h not in merged_hits[domain]]
                for domain in DOMAINS
            }
            result = _build_classification(
                scores,
                merged_hits,
                source="tài liệu",
                no_signal_reason="không có tín hiệu từ khóa; gán mặc định minh bạch",
            )
        result = Classification(
            result.domain,
            result.confidence,
            result.reason + " | sổ nguồn: %s" % str(ledger_hint.get("source_id") or ledger_hint.get("source_scope") or "?"),
        )
    return result


def detect_domain_from_question(question: str) -> Classification:
    """Detect the knowledge domain a user question belongs to.

    Always returns a domain (never ``None``): a question with no signal is
    assigned the most plausible block with low confidence and a reason saying
    so, so the UI can state which block was chosen instead of searching
    silently.
    """
    scores, hits = _score_text(question or "", TEXT_WEIGHT)
    return _build_classification(
        scores,
        hits,
        source="câu hỏi",
        no_signal_reason="câu hỏi không rõ lĩnh vực; chọn khối khả dĩ nhất",
    )


def domain_routing_enabled() -> bool:
    """Feature flag for question-domain routing (default off until Phase B)."""
    return str(os.environ.get(DOMAIN_ROUTING_ENV_VAR, "0")).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DomainRoute:
    collection_id: Optional[str]
    domain: str
    applied: bool
    note: str
    detected: Optional[Classification] = None


def select_domain_collection(
    detected: Classification,
    base_collection_id: Optional[str],
    *,
    collection_exists: Optional[Callable[[str], bool]] = None,
) -> DomainRoute:
    """Decide which collection a question should search.

    The domain collection is used only when: routing is enabled, the question
    would otherwise hit the legacy mixed ``tri_thuc`` collection, and the
    domain collection actually exists. Otherwise the base collection is kept
    and the route reports ``applied=False`` with a reason.
    """
    domain = detected.domain if isinstance(detected, Classification) else str(detected)
    target = DOMAIN_COLLECTION_IDS.get(domain)
    if not domain_routing_enabled():
        return DomainRoute(base_collection_id, domain, False, "định tuyến lĩnh vực đang tắt", detected)
    if base_collection_id != LEGACY_COLLECTION_ID:
        return DomainRoute(
            base_collection_id, domain, False, "không phải kho tri_thuc: giữ nguyên kho hiện tại", detected
        )
    if target is None:
        return DomainRoute(base_collection_id, domain, False, "không có kho cho lĩnh vực", detected)
    exists = True if collection_exists is None else bool(collection_exists(target))
    if not exists:
        return DomainRoute(
            base_collection_id, domain, False, "kho lĩnh vực chưa tồn tại: dùng kho tri_thuc cũ", detected
        )
    return DomainRoute(target, domain, True, "chọn kho lĩnh vực", detected)


def lookup_ledger_hint(db_path: str | Path, document_id: str) -> Optional[dict[str, str]]:
    """Look up ``source_preparation_ledger`` for a document, if the table exists.

    Returns ``{"source_scope": ..., "source_id": ..., "source_fingerprint": ...}``
    or ``None`` when the DB/table/row is missing. Never raises: a missing
    ledger only means one less classification signal.
    """
    doc = (document_id or "").strip()
    if not doc:
        return None
    try:
        path = Path(db_path)
        if not path.is_file():
            return None
        uri = path.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=5.0)
        try:
            conn.execute("PRAGMA query_only=ON")
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='source_preparation_ledger'"
                ).fetchall()
            }
            if not tables:
                return None
            row = conn.execute(
                "SELECT source_scope, source_id, source_fingerprint "
                "FROM source_preparation_ledger WHERE document_id = ? LIMIT 1",
                (doc,),
            ).fetchone()
        finally:
            conn.close()
    except (sqlite3.Error, OSError, ValueError):
        return None
    if row is None:
        return None
    return {
        "source_scope": str(row[0] or ""),
        "source_id": str(row[1] or ""),
        "source_fingerprint": str(row[2] or ""),
    }


_DOMAIN_DOCUMENT_MAP_CACHE: Optional[dict[str, str]] = None
_DOMAIN_DOCUMENTS_CACHE: Optional[dict[str, tuple[str, ...]]] = None


def load_domain_document_map() -> dict[str, str]:
    """Load the mapping of document_id -> domain block from the bundled manifest."""
    global _DOMAIN_DOCUMENT_MAP_CACHE
    if _DOMAIN_DOCUMENT_MAP_CACHE is not None:
        return _DOMAIN_DOCUMENT_MAP_CACHE

    map_path = Path(__file__).resolve().parent / "domain_document_map.json"
    if map_path.is_file():
        try:
            import json
            with open(map_path, "r", encoding="utf-8") as f:
                _DOMAIN_DOCUMENT_MAP_CACHE = json.load(f)
                return _DOMAIN_DOCUMENT_MAP_CACHE
        except Exception:
            pass

    _DOMAIN_DOCUMENT_MAP_CACHE = {}
    return _DOMAIN_DOCUMENT_MAP_CACHE


def get_domain_counts() -> dict[str, int]:
    """Return document counts per domain block from the document map."""
    doc_map = load_domain_document_map()
    counts = {
        "auto": len(doc_map),
        DOMAIN_LSU: 0,
        DOMAIN_DIEU_TRA_LOI: 0,
        DOMAIN_MOM: 0,
        DOMAIN_TONG_HOP: 0,
    }
    for doc_id, dom in doc_map.items():
        if dom in counts:
            counts[dom] += 1
    return counts


def get_domain_document_ids(domain: Optional[str]) -> Optional[tuple[str, ...]]:
    """Return tuple of document_ids belonging to the given domain block.

    - If ``domain`` is None or 'auto': returns None (search across all documents in index).
    - If ``domain`` is in ('lsu', 'dieu_tra_loi', 'mom', 'tong_hop'): returns tuple of matching document_ids.
    """
    global _DOMAIN_DOCUMENTS_CACHE
    if domain is None or str(domain).strip().lower() in ("auto", "all", ""):
        return None

    norm_domain = str(domain).strip().lower()
    if _DOMAIN_DOCUMENTS_CACHE is None:
        doc_map = load_domain_document_map()
        grouped: dict[str, list[str]] = {d: [] for d in KNOWLEDGE_BLOCKS}
        for doc_id, dom in doc_map.items():
            if dom in grouped:
                grouped[dom].append(doc_id)
            else:
                grouped.setdefault(dom, []).append(doc_id)
        _DOMAIN_DOCUMENTS_CACHE = {d: tuple(sorted(ids)) for d, ids in grouped.items()}

    return _DOMAIN_DOCUMENTS_CACHE.get(norm_domain)


COVERING_CATALOG_INDEX_NAME = "idx_chunks_doc_source_catalog"
DOCUMENT_CATALOG_TABLE_NAME = "document_catalog"

_DOMAIN_ALL_SPECS_CACHE: dict[str, list[Any]] = {}
_DOMAIN_ALL_SPECS_STAT_CACHE: dict[str, tuple[int, int]] = {}


def clear_index_specs_cache() -> None:
    """Clear the in-memory SourceSpec catalog cache."""
    global _DOMAIN_ALL_SPECS_CACHE, _DOMAIN_ALL_SPECS_STAT_CACHE
    if isinstance(_DOMAIN_ALL_SPECS_CACHE, dict):
        _DOMAIN_ALL_SPECS_CACHE.clear()
    else:
        _DOMAIN_ALL_SPECS_CACHE = {}
    if isinstance(_DOMAIN_ALL_SPECS_STAT_CACHE, dict):
        _DOMAIN_ALL_SPECS_STAT_CACHE.clear()
    else:
        _DOMAIN_ALL_SPECS_STAT_CACHE = {}


def _catalog_manifest_path(db_path: Path) -> Path:
    return db_path.parent / f".{db_path.name}.catalog.local.json"


def _read_catalog_manifest(
    db_path: Path,
    mtime_ns: int,
    size_bytes: int,
) -> Optional[list[tuple[str, str, str]]]:
    manifest_path = _catalog_manifest_path(db_path)
    if not manifest_path.is_file():
        return None
    try:
        import json

        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            not isinstance(raw, dict)
            or int(raw.get("schema_version", 0)) != 1
            or int(raw.get("db_mtime_ns", -1)) != int(mtime_ns)
            or int(raw.get("db_size", -1)) != int(size_bytes)
        ):
            return None
        entries = raw.get("entries")
        if not isinstance(entries, list):
            return None
        return [
            (str(item[0]), str(item[1]), str(item[2]))
            for item in entries
            if isinstance(item, (list, tuple)) and len(item) >= 3
        ]
    except Exception:
        return None


def _write_catalog_manifest(
    db_path: Path,
    mtime_ns: int,
    size_bytes: int,
    rows: Sequence[tuple[Any, ...]],
) -> None:
    manifest_path = _catalog_manifest_path(db_path)
    tmp_path = manifest_path.with_suffix(f".{os.getpid()}.tmp")
    try:
        import json

        payload = {
            "schema_version": 1,
            "db_mtime_ns": int(mtime_ns),
            "db_size": int(size_bytes),
            "entries": [
                [str(r[0]), str(r[1] or ""), str(r[2] or "")]
                for r in rows
            ],
        }
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(tmp_path, manifest_path)
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass


def _query_index_catalog_rows(con: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """Load (document_id, MIN(source_path), MIN(source_name)) without scanning chunks table."""
    schema_objs = {
        (str(row[0]), str(row[1]))
        for row in con.execute(
            "SELECT type, name FROM sqlite_master WHERE type IN ('table', 'index')"
        ).fetchall()
    }
    if ("table", DOCUMENT_CATALOG_TABLE_NAME) in schema_objs:
        cat_rows = con.execute(
            f"SELECT document_id, source_path, source_name "
            f"FROM {DOCUMENT_CATALOG_TABLE_NAME} ORDER BY document_id"
        ).fetchall()
        if cat_rows:
            return [(str(r[0]), str(r[1] or ""), str(r[2] or "")) for r in cat_rows]

    has_covering_idx = ("index", COVERING_CATALOG_INDEX_NAME) in schema_objs
    has_doc_idx = ("index", "idx_chunks_document_id") in schema_objs

    if has_covering_idx or not has_doc_idx:
        sql = """
            WITH RECURSIVE docs(doc_id) AS (
                SELECT MIN(document_id) FROM chunks
                UNION ALL
                SELECT (SELECT MIN(document_id) FROM chunks WHERE document_id > docs.doc_id)
                FROM docs
                WHERE docs.doc_id IS NOT NULL
            )
            SELECT d.doc_id,
                   (SELECT MIN(source_path) FROM chunks WHERE document_id = d.doc_id),
                   (SELECT MIN(source_name) FROM chunks WHERE document_id = d.doc_id)
            FROM docs d
            WHERE d.doc_id IS NOT NULL
            ORDER BY d.doc_id
        """
    else:
        sql = """
            WITH RECURSIVE docs(doc_id) AS (
                SELECT MIN(document_id) FROM chunks
                UNION ALL
                SELECT (SELECT MIN(document_id) FROM chunks WHERE document_id > docs.doc_id)
                FROM docs
                WHERE docs.doc_id IS NOT NULL
            )
            SELECT d.doc_id,
                   (SELECT source_path FROM chunks WHERE document_id = d.doc_id LIMIT 1),
                   (SELECT source_name FROM chunks WHERE document_id = d.doc_id LIMIT 1)
            FROM docs d
            WHERE d.doc_id IS NOT NULL
            ORDER BY d.doc_id
        """
    raw_rows = con.execute(sql).fetchall()
    return [(str(r[0]), str(r[1] or ""), str(r[2] or "")) for r in raw_rows]


def ensure_index_catalog(db_path: Path | str) -> bool:
    """Ensure covering index on (document_id, source_path, source_name) and sidecar manifest."""
    path = Path(db_path)
    if not path.is_file():
        return False
    con: Optional[sqlite3.Connection] = None
    try:
        con = sqlite3.connect(str(path.resolve()), timeout=10.0)
        with con:
            con.execute(
                f"CREATE INDEX IF NOT EXISTS {COVERING_CATALOG_INDEX_NAME} "
                "ON chunks(document_id, source_path, source_name)"
            )
        rows = _query_index_catalog_rows(con)
    except Exception:
        return False
    finally:
        if con is not None:
            con.close()
    try:
        st = path.stat()
        _write_catalog_manifest(path.resolve(), st.st_mtime_ns, st.st_size, rows)
    except OSError:
        pass
    return True


def _build_source_specs(rows: Sequence[tuple[Any, ...]]) -> list[Any]:
    from aios_habit.rag_v2.pipeline import SourceSpec

    cwd_resolved = Path.cwd().resolve()
    try:
        cwd_entries = {name.lower() for name in os.listdir(cwd_resolved)}
    except OSError:
        cwd_entries = set()

    specs: list[Any] = []
    for r in rows:
        doc_id = str(r[0])
        raw = str(r[2] if r[2] else r[1])
        if (
            raw
            and "/" not in raw
            and "\\" not in raw
            and ":" not in raw
            and raw not in (".", "..")
            and raw.lower() not in cwd_entries
        ):
            resolved_p = cwd_resolved / raw
        else:
            resolved_p = Path(raw).resolve()
        spec = object.__new__(SourceSpec)
        object.__setattr__(spec, "path", resolved_p)
        object.__setattr__(spec, "source_id", doc_id)
        object.__setattr__(spec, "document_id", doc_id or _fallback_doc_id(resolved_p))
        object.__setattr__(spec, "privacy_labels", ("local_only",))
        object.__setattr__(spec, "enabled", True)
        object.__setattr__(spec, "owner_consent", True)
        object.__setattr__(spec, "language_hints", ("vi", "ja", "en"))
        specs.append(spec)
    return specs


def _fallback_doc_id(resolved_path: Path) -> str:
    from aios_habit.rag_v2.pipeline import _stable_document_id

    return _stable_document_id(resolved_path)


def load_all_index_specs(
    db_path: Path | str | None = None,
    *,
    use_manifest: bool = True,
) -> list[Any]:
    """Load SourceSpec objects for all documents in library.sqlite (cached per path)."""
    global _DOMAIN_ALL_SPECS_CACHE, _DOMAIN_ALL_SPECS_STAT_CACHE
    if not isinstance(_DOMAIN_ALL_SPECS_CACHE, dict):
        _DOMAIN_ALL_SPECS_CACHE = {}
    if not isinstance(_DOMAIN_ALL_SPECS_STAT_CACHE, dict):
        _DOMAIN_ALL_SPECS_STAT_CACHE = {}

    if db_path is None:
        prod_path = Path("C:/AIOS_workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite")
        db_path = prod_path if prod_path.is_file() else Path("local_runs/workspace_chat_rag_v2_production/bge_m3_hybrid/collections/tri_thuc/library.sqlite")
    else:
        db_path = Path(db_path)

    is_file = db_path.is_file()
    resolved_path = db_path.resolve() if is_file else db_path
    cache_key = str(resolved_path)

    current_stat: Optional[tuple[int, int]] = None
    if is_file:
        try:
            st = resolved_path.stat()
            current_stat = (int(st.st_mtime_ns), int(st.st_size))
        except OSError:
            current_stat = None

    if cache_key in _DOMAIN_ALL_SPECS_CACHE:
        cached_stat = _DOMAIN_ALL_SPECS_STAT_CACHE.get(cache_key)
        if cached_stat is None or current_stat is None or cached_stat == current_stat:
            return _DOMAIN_ALL_SPECS_CACHE[cache_key]

    if not is_file:
        return []

    try:
        rows: Optional[list[tuple[str, str, str]]] = None
        if use_manifest and current_stat is not None:
            rows = _read_catalog_manifest(resolved_path, current_stat[0], current_stat[1])

        if rows is None:
            uri = resolved_path.as_uri() + "?mode=ro"
            con = sqlite3.connect(uri, uri=True, timeout=10.0)
            try:
                rows = _query_index_catalog_rows(con)
            finally:
                con.close()
            if use_manifest and current_stat is not None and rows:
                _write_catalog_manifest(resolved_path, current_stat[0], current_stat[1], rows)

        specs = _build_source_specs(rows)
        _DOMAIN_ALL_SPECS_CACHE[cache_key] = specs
        if current_stat is not None:
            _DOMAIN_ALL_SPECS_STAT_CACHE[cache_key] = current_stat
        return specs
    except Exception:
        return []


CROSS_DOMAIN_EXACT_IDENTIFIER_ENV_VAR = "AIOS_RAG_CROSS_DOMAIN_EXACT_IDENTIFIER"

_EXACT_MECHANICAL_ID_PATTERNS = (
    re.compile(r"\b[gpdcwesGPDCHWES]\d{1,2}\b"),
    re.compile(r"\b3[vV]2[a-zA-Z0-9_-]+\b"),
    re.compile(r"\b30[23][a-zA-Z0-9_-]+\b"),
    re.compile(r"\b7[pP][a-zA-Z0-9_-]+\b"),
    re.compile(r"\b[kK][tT][dD][-_]\d+\b"),
    re.compile(r"\b[cC]\d{4}\b"),
    re.compile(r"\b[fF]\d{3}\b"),
    re.compile(r"\b[jJ][aA][mM]\d{3,4}\b"),
)


def cross_domain_exact_identifier_enabled() -> bool:
    """Feature flag for cross-domain search on exact identifiers (default enabled)."""
    return str(os.environ.get(CROSS_DOMAIN_EXACT_IDENTIFIER_ENV_VAR, "1")).strip().lower() in {
        "1", "true", "yes", "on"
    }


def extract_exact_mechanical_identifiers(text: str) -> tuple[str, ...]:
    """Extract mechanical identifiers (datum points, part codes, error codes)."""
    if not text:
        return ()
    found = []
    seen = set()
    for pat in _EXACT_MECHANICAL_ID_PATTERNS:
        for m in pat.finditer(text):
            tok = m.group(0).strip()
            key = tok.lower()
            if key not in seen:
                seen.add(key)
                found.append(tok)
    return tuple(found)


def _find_cross_domain_candidate_documents(
    db_path: Path | str,
    exact_identifiers: Sequence[str],
    question: Optional[str] = None,
    max_extra_docs: int = 5,
) -> tuple[str, ...]:
    """Find documents containing exact mechanical identifiers via FTS5 in library.sqlite."""
    if not exact_identifiers:
        return ()
    try:
        path = Path(db_path)
        if not path.is_file():
            return ()
        uri = path.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=5.0) as con:
            con.execute("PRAGMA query_only=ON")
            clauses = []
            params = []
            for tok in exact_identifiers:
                clauses.append(
                    "d1.document_id IN (SELECT document_id FROM chunks WHERE chunk_id IN (SELECT chunk_id FROM chunks_fts WHERE chunks_fts MATCH ?))"
                )
                params.append(f'"{tok}"')

            if question:
                q_low = question.lower()
                spec_terms = []
                if "nominal" in q_low:
                    spec_terms.extend(['"nominal"', '"kích thước"'])
                if "giới hạn" in q_low or "giới" in q_low:
                    spec_terms.extend(['"giới hạn"', '"dung sai"'])
                if "dung sai" in q_low:
                    spec_terms.append('"dung sai"')
                if "kích thước" in q_low:
                    spec_terms.append('"kích thước"')
                if spec_terms:
                    clauses.append(
                        "d1.document_id IN (SELECT document_id FROM chunks WHERE chunk_id IN (SELECT chunk_id FROM chunks_fts WHERE chunks_fts MATCH ?))"
                    )
                    params.append(" OR ".join(spec_terms))

            sql = f"""
                SELECT d1.document_id, MIN(COALESCE(d1.source_name, '')), COUNT(DISTINCT d1.chunk_id) as hits
                FROM chunks d1
                WHERE {" AND ".join(clauses)}
                GROUP BY d1.document_id
            """
            raw_rows = con.execute(sql, tuple(params)).fetchall()
            if not raw_rows:
                return ()

            q_clean = (question or "").lower().replace(":", " ").replace("-", " ").replace("/", " ").replace(">", " ").replace(".", " ")
            q_words = {w for w in q_clean.split() if len(w) >= 2} if question else set()

            scored = []
            for doc_id, s_name, hits in raw_rows:
                s_clean = str(s_name).lower().replace(":", " ").replace("-", " ").replace("/", " ").replace(">", " ").replace(".", " ").replace("(", " ").replace(")", " ")
                s_words = {w for w in s_clean.split() if len(w) >= 2}
                overlap = len(q_words & s_words) if q_words else 0
                scored.append((overlap, hits, str(doc_id)))

            # Khi câu hỏi nêu đích danh tên tài liệu (overlap >= 2 từ), ưu tiên tài liệu đích
            has_title_match = any(item[0] >= 2 for item in scored)
            if has_title_match:
                matched = [item for item in scored if item[0] >= 2]
                matched.sort(key=lambda item: (item[0], item[1]), reverse=True)
                return tuple(item[2] for item in matched[:max_extra_docs])

            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            return tuple(item[2] for item in scored[:max_extra_docs])
    except Exception:
        return ()


def get_specs_for_domain(
    domain: Optional[str],
    db_path: Path | str | None = None,
    question: Optional[str] = None,
) -> tuple[Any, ...]:
    """Return SourceSpecs for a given domain block, optionally adding exact-identifier cross-domain specs.

    If domain is None or 'auto', returns all documents in library.sqlite.
    If domain is 'lsu', returns LSU documents (92), plus controlled cross-domain documents
    if the question contains exact mechanical identifiers (e.g. g1/g2, part codes) and
    cross-domain rescue is enabled.
    """
    all_specs = load_all_index_specs(db_path)
    if not all_specs:
        return ()

    allowed_ids = get_domain_document_ids(domain)
    if allowed_ids is None:
        return tuple(all_specs)

    allowed_set = set(allowed_ids)
    if (
        question
        and cross_domain_exact_identifier_enabled()
        and db_path is not None
    ):
        exact_ids = extract_exact_mechanical_identifiers(question)
        if exact_ids:
            extra_doc_ids = _find_cross_domain_candidate_documents(
                db_path, exact_ids, question=question
            )
            for extra_id in extra_doc_ids:
                allowed_set.add(extra_id)

    return tuple(s for s in all_specs if s.document_id in allowed_set)
