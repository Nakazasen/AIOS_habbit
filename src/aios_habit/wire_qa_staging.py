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
import unicodedata
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
    "có thông tin, không tự bịa đặt. Không tự viết lại nhãn "
    "'Bản thảo — chưa qua chuyên gia duyệt' hay dòng 'Nguồn dữ liệu tham khảo' trong "
    "câu trả lời — hệ thống tự gắn nhãn này."
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
# Câu hỏi truy vấn xuất hiện NGUYÊN VĂN (sau chuẩn hoá khoảng trắng/dấu câu) trong
# câu hỏi của cặp — tín hiệu khớp chắc chắn nhất: phải áp đảo mọi bonus và không
# ngưỡng nào loại được (vá lỗi recall Q0703/Q1034/Q1827… của vé MATCHER-FIX).
_VERBATIM_QUESTION_BONUS = 100.0
# Chỉ bật khớp nguyên văn khi câu chuẩn hoá đủ dài — tránh chuỗi ngắn ("hi", "mã")
# tình cờ là chuỗi con của nhiều câu hỏi khác.
_MIN_VERBATIM_QUESTION_LENGTH = 6
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


@lru_cache(maxsize=8192)
def _normalize_question_text(text: str) -> str:
    """Chuẩn hoá câu hỏi để so khớp nguyên văn: NFKC, thường hoá, bỏ dấu câu, gộp khoảng trắng.

    Câu hỏi LSU trộn Việt/Trung/Nhật nên chỉ đổi dấu câu thành khoảng trắng (``\\w``
    giữ nguyên chữ Hán/Kana và chữ có dấu, kể cả khi dính liền thành mạch dài) rồi
    gộp khoảng trắng — không tách từ, không bỏ chữ/số.
    """
    normalized = unicodedata.normalize("NFKC", str(text or "")).lower()
    normalized = re.sub(r"[^\w\s]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def select_relevant_pairs(
    question: str,
    pairs: Sequence[WireQaPair],
    *,
    limit: int = MAX_REFERENCE_PAIRS,
) -> tuple[WireQaPair, ...]:
    """Chọn tối đa ``limit`` cặp liên quan nhất (điểm >= ngưỡng; tie-break theo id).

    Điểm = khớp thật (mã/serial 10, từ khóa 1, câu hỏi trùng nguyên văn sau chuẩn
    hoá 100) + bonus theo ý định. Bonus chỉ cộng khi cặp đã có khớp thật và không
    bao giờ vượt điểm gốc nên không thể đảo thứ tự liên quan (vá Q0671/Q0658).
    """
    code_terms, word_terms = _query_terms(question)
    question_norm = _normalize_question_text(question)
    can_match_verbatim = len(question_norm) >= _MIN_VERBATIM_QUESTION_LENGTH
    if not code_terms and not word_terms and not can_match_verbatim:
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
        if can_match_verbatim and question_norm in _normalize_question_text(pair.question):
            # Câu hỏi người dùng trùng nguyên văn câu hỏi của cặp (sau chuẩn hoá):
            # giữ cặp bất kể ngưỡng và xếp trên mọi cặp chỉ có bonus.
            score += _VERBATIM_QUESTION_BONUS
        if score > 0:
            bonus = 0.0
            if component_intent:
                components = set(_COMPONENT_RE.findall(pair_text))
                bonus += min(_COMPONENT_BONUS_CAP, _COMPONENT_BONUS_PER_HIT * len(components))
            if definition_intent:
                if any(
                    re.search(re.escape(term) + r"\s*(?:là|nghĩa là)", pair_text)
                    for term in code_terms
                ):
                    bonus += _DEFINITION_BONUS
            # Bonus chỉ tinh chỉnh giữa các cặp đã có khớp thật: không bao giờ vượt
            # điểm gốc (chống bonus +8 lấn át cặp đúng 5,0 như Q0671/Q0658).
            score += min(bonus, score)
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


def strip_echoed_draft_label(text: str) -> str:
    """Bỏ khối nhãn bản thảo do MODEL tự viết lại ở đầu câu trả lời.

    Model nhìn thấy nhãn trong lịch sử hội thoại nên đôi khi tự "nhại" lại
    (kèm danh sách cặp Q&A riêng của nó); hệ thống đã có nhãn chính thức nên
    phần nhại ở đầu phải bị cắt để tránh hiển thị hai nhãn.
    """
    lines = str(text or "").splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    head = lines[index].strip() if index < len(lines) else ""
    is_echoed_label = head.startswith(">") and (
        ("Bản thảo" in head and "chưa qua chuyên gia duyệt" in head)
        or "Nguồn dữ liệu tham khảo:" in head
    )
    if not is_echoed_label:
        return str(text or "").strip()
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith(">") or not line:
            index += 1
            continue
        break
    return "\n".join(lines[index:]).strip()


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
