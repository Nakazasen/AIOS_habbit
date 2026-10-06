"""Kho tham khảo Q&A staging cho lane C-Agent (vé WIRE-QA-CAGENT-PC0575).

Đọc file staging ``wire-qa-mapping.jsonl`` (3.392 cặp hỏi-đáp đã review chéo)
ở chế độ CHỈ ĐỌC, chọn tối đa 3 cặp liên quan nhất tới câu hỏi người dùng để:

- ghép vào prompt gửi C-Agent (template spec §1.2 — chỉ 2 mảnh ``câu hỏi gốc``
  và ``trả lời gốc``, không bịa trường "Bối cảnh");
- gắn nhãn ``Bản thảo — chưa qua chuyên gia duyệt`` + nguồn cặp Q&A vào câu
  trả lời (rào cứng spec §4).

Rào cứng an toàn: module không ghi vào vector DB/BM25 index production và
không tạo/ghi đè case chính thức. Bật/tắt bằng feature flag
``AIOS_FEATURE_WIRE_QA_CAGENT`` (mặc định tắt).
"""
from __future__ import annotations

import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from aios_habit.feature_flags import FEATURE_WIRE_QA_CAGENT, is_feature_enabled

ENV_MAPPING_PATH = "AIOS_WIRE_QA_MAPPING_PATH"
DEFAULT_MAPPING_RELATIVE_PATH = Path("docs") / "phieu-viec" / "ket-qua" / "wire-qa-mapping.jsonl"

MAX_REFERENCE_PAIRS = 3
# 1 mã/serial khớp = 10 điểm (áp đảo), 1 từ khóa dài khớp = 1 điểm; cần >= 3
# điểm (1 mã/serial, hoặc >= 3 từ khóa) mới coi là liên quan.
MIN_MATCH_SCORE = 3.0
_CODE_TERM_WEIGHT = 10.0
_WORD_TERM_WEIGHT = 1.0
_MIN_WORD_LENGTH = 4

DRAFT_LABEL_HEADER = "⚠️ **Bản thảo — chưa qua chuyên gia duyệt**"

SYSTEM_NOTE = (
    "DỮ LIỆU THAM KHẢO (BẢN THẢO) gồm các cặp hỏi-đáp kỹ thuật nội bộ chưa qua "
    "chuyên gia duyệt: ưu tiên thông tin trong phần này; giữ nguyên số liệu kỹ thuật, "
    "mã lỗi, serial và ký hiệu linh kiện; nếu tài liệu chưa ghi nhận thì nói rõ là chưa "
    "có thông tin, không tự bịa đặt."
)

_TOKEN_RE = re.compile(r"\w+(?:-\w+)*", re.UNICODE)
# Mã linh kiện kiểu F401 / Q402 / IC401 / D304 xuất hiện trong đáp án.
# KHÔNG gồm tiền tố "C" — trong kho này "C0980/C35" là mã lỗi/case, không phải linh kiện.
_COMPONENT_RE = re.compile(r"(?<![0-9a-z])(?:ic|f|q|d|r|k|th)\d{2,4}(?![0-9])")
# Câu hỏi hỏi "các bước kiểm tra linh kiện" -> ưu tiên cặp liệt kê linh kiện.
_COMPONENT_INTENT_MARKERS = ("kiểm tra", "linh kiện", "điểm đo", "đo kiểm")
# Câu hỏi hỏi "báo hiệu lỗi gì / định nghĩa" -> ưu tiên cặp định nghĩa mã lỗi.
_DEFINITION_INTENT_MARKERS = ("báo hiệu", "định nghĩa", "nghĩa là", "là gì")
_COMPONENT_BONUS_PER_HIT = 2.0
_COMPONENT_BONUS_CAP = 8.0
_DEFINITION_BONUS = 8.0
# Từ chức năng dài (>= 4 ký tự) xuất hiện dày đặc — bỏ để không tạo khớp nhiễu.
_STOPWORDS = frozenset({
    "anh", "bạn", "biết", "các", "cách", "cho", "chưa", "cần", "của", "đâu",
    "được", "gì", "hãy", "không", "khi", "làm", "một", "người", "như",
    "những", "nào", "phải", "sao", "sẽ", "theo", "thế", "trên", "trong",
    "với", "và",
})


@dataclass(frozen=True)
class WireQaPair:
    """Một cặp hỏi-đáp staging (5 trường dùng cho prompt/nhãn)."""

    id: str
    question: str
    answer: str
    source: str
    category: str


@dataclass(frozen=True)
class WireQaReference:
    """Khối tham khảo staging đã sẵn sàng để ghép vào lane C-Agent."""

    pairs: tuple[WireQaPair, ...]
    prompt_block: str
    label_block: str
    system_note: str


def staging_path() -> Path:
    """Đường dẫn file staging; ghi đè bằng ``AIOS_WIRE_QA_MAPPING_PATH`` nếu có."""
    override = os.environ.get(ENV_MAPPING_PATH, "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / DEFAULT_MAPPING_RELATIVE_PATH


@lru_cache(maxsize=4)
def _load_pairs_cached(path_str: str, mtime_ns: int) -> tuple[WireQaPair, ...]:
    pairs: list[WireQaPair] = []
    try:
        with open(path_str, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                question = str(row.get("question") or "").strip()
                answer = str(row.get("answer") or "").strip()
                if not question or not answer:
                    continue
                pairs.append(
                    WireQaPair(
                        id=str(row.get("id") or "").strip(),
                        question=question,
                        answer=answer,
                        source=str(row.get("source") or "").strip(),
                        category=str(row.get("category") or "").strip(),
                    )
                )
    except OSError:
        return ()
    return tuple(pairs)


def load_staging_pairs(path: Path | None = None) -> tuple[WireQaPair, ...]:
    """Nạp toàn bộ cặp staging (cache theo đường dẫn + mtime; lỗi đọc -> rỗng)."""
    target = path or staging_path()
    try:
        mtime_ns = target.stat().st_mtime_ns
    except OSError:
        return ()
    return _load_pairs_cached(str(target), mtime_ns)


def _is_code_term(token: str) -> bool:
    has_digit = any(ch.isdigit() for ch in token)
    if not has_digit:
        return False
    has_alpha = any(ch.isalpha() for ch in token)
    return has_alpha or len(token) >= 6


def _query_terms(question: str) -> tuple[frozenset[str], frozenset[str]]:
    code_terms: set[str] = set()
    word_terms: set[str] = set()
    for token in _TOKEN_RE.findall(str(question or "").lower()):
        if len(token) < 2:
            continue
        if any(ch.isdigit() for ch in token):
            if _is_code_term(token):
                code_terms.add(token)
            # Số thuần ngắn (năm, ngày) không phải mã/serial lẫn từ khóa.
            continue
        if len(token) >= _MIN_WORD_LENGTH and token not in _STOPWORDS:
            word_terms.add(token)
    return frozenset(code_terms), frozenset(word_terms)


def _pair_tokens(pair: WireQaPair) -> frozenset[str]:
    return frozenset(_TOKEN_RE.findall(f"{pair.question}\n{pair.answer}".lower()))


def select_relevant_pairs(
    question: str,
    pairs: Sequence[WireQaPair],
    *,
    limit: int = MAX_REFERENCE_PAIRS,
) -> tuple[WireQaPair, ...]:
    """Chọn tối đa ``limit`` cặp liên quan nhất (điểm >= ngưỡng; tie-break theo id)."""
    code_terms, word_terms = _query_terms(question)
    if not code_terms and not word_terms:
        return ()
    q_text = str(question or "").lower()
    component_intent = any(marker in q_text for marker in _COMPONENT_INTENT_MARKERS)
    definition_intent = any(marker in q_text for marker in _DEFINITION_INTENT_MARKERS)
    scored: list[tuple[float, WireQaPair]] = []
    for pair in pairs:
        pair_text = f"{pair.question}\n{pair.answer}".lower()
        code_hits = {term for term in code_terms if term in pair_text}
        score = _CODE_TERM_WEIGHT * len(code_hits) + _WORD_TERM_WEIGHT * len(
            word_terms & _pair_tokens(pair)
        )
        if component_intent:
            components = set(_COMPONENT_RE.findall(pair_text))
            score += min(_COMPONENT_BONUS_CAP, _COMPONENT_BONUS_PER_HIT * len(components))
        if definition_intent:
            if any(re.search(re.escape(term) + r"\s*(?:là|nghĩa là)", pair_text) for term in code_terms):
                score += _DEFINITION_BONUS
        if score >= MIN_MATCH_SCORE:
            scored.append((score, pair))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    return tuple(pair for _, pair in scored[: max(1, int(limit))])


def _render_prompt_block(pairs: Sequence[WireQaPair]) -> str:
    lines = ["--- DỮ LIỆU THAM KHẢO (BẢN THẢO) ---"]
    for pair in pairs:
        lines.append(f"[Nguồn: {pair.source} | {pair.id} | Khối: {pair.category}]")
        lines.append(f"- Câu hỏi gốc: {pair.question}")
        lines.append(f"- Trả lời gốc: {pair.answer}")
        lines.append("")
    return "\n".join(lines).strip()


def _render_label_block(pairs: Sequence[WireQaPair]) -> str:
    entries = "; ".join(f"Khối {pair.category} — Cặp Q&A #{pair.id}" for pair in pairs)
    return f"> {DRAFT_LABEL_HEADER}\n> *Nguồn dữ liệu tham khảo: {entries}*"


def build_wire_qa_reference(question: str) -> WireQaReference | None:
    """Trả về khối tham khảo staging cho câu hỏi, hoặc ``None`` khi tắt/không khớp."""
    if not is_feature_enabled(FEATURE_WIRE_QA_CAGENT):
        return None
    if not str(question or "").strip():
        return None
    pairs = select_relevant_pairs(question, load_staging_pairs())
    if not pairs:
        return None
    return WireQaReference(
        pairs=pairs,
        prompt_block=_render_prompt_block(pairs),
        label_block=_render_label_block(pairs),
        system_note=SYSTEM_NOTE,
    )
