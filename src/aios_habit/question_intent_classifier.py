"""Question intent classifier for AIOS 5-Tier Answer Ladder (DESKTOP-SELF-LEARN-5TIER-ANSWER-LADDER).

Classifies user questions into 4 primary intent categories:
1. tra_cuu (Lookup): specific parameters, error codes, definitions, specifications, file locations.
2. tong_quan (Overview): workflow, procedure, feature introduction, architecture, high-level steps.
3. tong_hop (Synthesis): cross-source comparison, differences, multi-dimensional analysis, trends, stats.
4. mo_ho (Ambiguous): very short query, missing context/subject, or vague prompt needing disambiguation.

Provides contextual rephrasing suggestions for ambiguous questions to eliminate cold refusals.
Compatible with Python 3.11.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Sequence

INTENT_TRA_CUU = "tra_cuu"
INTENT_TONG_QUAN = "tong_quan"
INTENT_TONG_HOP = "tong_hop"
INTENT_MO_HO = "mo_ho"

VALID_INTENTS = (INTENT_TRA_CUU, INTENT_TONG_QUAN, INTENT_TONG_HOP, INTENT_MO_HO)

INTENT_DESCRIPTIONS = {
    INTENT_TRA_CUU: "Tra cứu thông số, mã lỗi, quy chuẩn hoặc vị trí cụ thể",
    INTENT_TONG_QUAN: "Tổng quan quy trình, chức năng hoặc kiến trúc hệ thống",
    INTENT_TONG_HOP: "Tổng hợp đa chiều, so sánh hoặc phân tích xu hướng",
    INTENT_MO_HO: "Câu hỏi mơ hồ, thiếu chủ ngữ hoặc cần làm rõ ý định",
}


@dataclass(frozen=True)
class QuestionIntentResult:
    """Classification outcome for a user question."""

    intent: str
    confidence: float
    matched_patterns: List[str] = field(default_factory=list)
    suggested_rephrasings: List[str] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "confidence": round(self.confidence, 3),
            "matched_patterns": list(self.matched_patterns),
            "suggested_rephrasings": list(self.suggested_rephrasings),
            "explanation": self.explanation,
        }


def _fold(value: str) -> str:
    """Normalize and fold text for accent-insensitive matching."""
    normalized = unicodedata.normalize(
        "NFKD", (value or "").casefold().replace("đ", "d")
    )
    folded = "".join(
        ch for ch in normalized if not unicodedata.combining(ch)
    )
    return " ".join(folded.split())


# Regex patterns indicating explicit lookup tokens (error codes, specific variable assignments)
_SPECIFIC_CODE_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:e-\d+|c-\d+|err-\d+|[a-z]{1,4}\d{3,5}|\w+\s*=\s*\w+|ctrlmode|dmt|pmt|ip|port)(?![A-Za-z0-9])",
    re.IGNORECASE,
)

# Ambiguous phrases / cry-for-help with zero actionable context
_AMBIGUOUS_PATTERNS = [
    r"\b(?:lỗi|loi)\b",
    r"\b(?:giúp|giup|giúp tôi|giup toi|cứu|cuu|cứu với|cuu voi)\b",
    r"\b(?:sao thế|sao the|sao vậy|sao vay|tại sao|tai sao|sao thế này)\b",
    r"\b(?:hư rồi|hu roi|hỏng rồi|hong roi|bị đơ|bi do|bị treo|bi treo)\b",
    r"\b(?:không chạy|khong chay|không chạy được|khong chay duoc|không được|khong duoc)\b",
    r"\b(?:làm sao|lam sao|làm sao đây|lam sao day|làm thế nào|lam the nao)\b",
    r"\b(?:sửa thế nào|sua the nao|cách sửa|cach sua|sửa sao|sua sao)\b",
    r"\b(?:làm thế nào để sửa|lam the nao de sua)\b",
    r"(?:[a-z0-9_-]+)\s+(?:bị lỗi|bi loi|bị hỏng|bi hong|hư rồi|hu roi)",
]

_SYNTHESIS_KEYWORDS = [
    "so sánh", "so sanh",
    "khác biệt", "khac biet",
    "khác nhau", "khac nhau",
    "giống nhau", "giong nhau",
    "tổng hợp", "tong hop",
    "đối chiếu", "doi chieu",
    "phân tích", "phan tich",
    "tỷ lệ lỗi giữa", "ty le loi giua",
    "thống kê", "thong ke",
    "xu hướng", "xu huong",
    "mối liên hệ", "moi lien he",
    "ưu nhược điểm", "uu nhuoc diem",
    "sự khác nhau", "su khac nhau",
    "điểm giống", "diem giong",
    "điểm khác", "diem khac",
    "so với", "so voi",
    "tổng quan và so sánh",
    "compare", "comparison", "difference", "versus", "vs",
]

_OVERVIEW_KEYWORDS = [
    "tổng quan", "tong quan",
    "quy trình", "quy trinh",
    "các bước", "cac buoc",
    "giới thiệu", "gioi thieu",
    "chức năng", "chuc nang",
    "nguyên lý", "nguyen ly",
    "kiến trúc", "kien truc",
    "hướng dẫn chung", "huong dan chung",
    "hoạt động thế nào", "hoat dong the nao",
    "gồm những gì", "gom nhung gi",
    "như thế nào", "nhu the nao",
    "vận hành", "van hanh",
    "danh sách bước", "danh sach buoc",
    "chu trình", "chu trinh",
    "bước nào", "buoc nao",
    "toàn bộ quy trình",
    "overview", "workflow", "architecture", "introduction", "procedure",
]

_LOOKUP_KEYWORDS = [
    "là gì", "la gi",
    "nghĩa là gì", "nghia la gi",
    "mã lỗi", "ma loi",
    "thông số", "thong so",
    "quy chuẩn", "quy chuan",
    "định nghĩa", "dinh nghia",
    "ở đâu", "o dau",
    "vị trí", "vi tri",
    "giá trị", "gia tri",
    "cấu hình", "cau hinh",
    "đơn vị", "don vi",
    "bao nhiêu", "bao nhieu",
    "ký hiệu", "ky hieu",
    "cú pháp", "cu phap",
    "địa chỉ", "dia chi",
    "bảng nào", "bang nao",
    "tệp nào", "tep nao",
    "file nào", "file nao",
    "lookup", "what is", "error code", "parameter", "specification",
]


def suggest_rephrasings(
    question: str,
    context_titles: Sequence[str] = (),
    playbook_domain: str = "",
) -> List[str]:
    """Generate 2 to 4 concrete, actionable rephrasings for ambiguous questions.

    Anchors on domain keywords (e.g. LSU, MOM, Jig) and enabled context source titles.
    """
    clean_q = question.strip().rstrip("?.!")
    folded = _fold(clean_q)

    # Detect entity / topic
    detected_topic = ""
    if "lsu" in folded:
        detected_topic = "LSU"
    elif "mom" in folded or "matecon" in folded or "opcenter" in folded:
        detected_topic = "MOM/Opcenter"
    elif "agv" in folded:
        detected_topic = "AGV"
    elif "jig" in folded:
        detected_topic = "Jig căn chỉnh"
    elif "wms" in folded:
        detected_topic = "WMS"
    elif context_titles:
        for title in context_titles:
            t_str = str(title).strip()
            if t_str:
                detected_topic = t_str
                break

    if detected_topic == "LSU":
        return [
            "Quy trình kiểm tra và các bước xử lý khi cụm LSU phát sinh lỗi?",
            "Cách tra cứu danh mục mã lỗi và đối sách khắc phục tiêu chuẩn cho LSU?",
            "Thông số kỹ thuật dung sai và kiểm tra tín hiệu laser của LSU?",
            "Phân tích nhật ký kiểm tra và xu hướng suy giảm hiệu suất jig LSU?",
        ]
    if detected_topic in ("MOM/Opcenter", "AGV", "WMS"):
        return [
            "Quy trình tích hợp và luồng lệnh giữa MOM, WMS và trạm AGV?",
            "Ý nghĩa và cách cấu hình các tham số ctrlMode trong hệ thống Matecon?",
            "Cách xử lý sự cố khi lệnh xuất nhập kho tự động bị ngắt kết nối?",
            "Tổng hợp các mã cảnh báo phổ biến trên giao diện MOM Opcenter?",
        ]
    if detected_topic == "Jig căn chỉnh":
        return [
            "Quy trình bảo dưỡng và các bước hiệu chuẩn định kỳ cho jig?",
            "Các dấu hiệu cảnh báo sớm khi hiệu suất jig bắt đầu suy giảm?",
            "Cách kiểm tra độ lặp lại và dung sai cơ khí của jig căn chỉnh?",
            "Biện pháp đối sách khi phát hiện dữ liệu kiểm tra jig lệch chuẩn?",
        ]

    # Clean generic fallback when no specific domain detected
    topic_label = clean_q if len(clean_q) <= 30 else clean_q[:28] + "..."
    if not topic_label:
        topic_label = "vấn đề đang gặp"

    return [
        f"Tổng quan quy trình và các bước xử lý liên quan đến {topic_label}?",
        f"Tra cứu thông số kỹ thuật, mã lỗi hoặc quy chuẩn cụ thể của {topic_label}?",
        f"So sánh các nguyên nhân phổ biến và giải pháp khắc phục cho {topic_label}?",
        f"Hướng dẫn kiểm tra thực tế và các bước phòng ngừa tái diễn cho {topic_label}?",
    ]


def classify_question_intent(
    question: str,
    context_titles: Sequence[str] = (),
    playbook_domain: str = "",
) -> QuestionIntentResult:
    """Classify the user question into one of 4 intent categories.

    Returns QuestionIntentResult with intent, confidence, matched patterns,
    and suggested rephrasings (populated especially for ambiguous queries).
    """
    raw_text = (question or "").strip()
    folded = _fold(raw_text)
    words = [w for w in re.split(r"\s+", raw_text) if w]
    word_count = len(words)

    if not folded or word_count == 0:
        suggestions = suggest_rephrasings("câu hỏi", context_titles, playbook_domain)
        return QuestionIntentResult(
            intent=INTENT_MO_HO,
            confidence=0.99,
            matched_patterns=["empty_question"],
            suggested_rephrasings=suggestions,
            explanation="Câu hỏi rỗng; cần người dùng cung cấp thông tin hoặc chọn gợi ý.",
        )

    # 1. Check for specific code/tokens FIRST to protect short valid queries like "Mã E-041 là gì?"
    has_specific_code = bool(_SPECIFIC_CODE_RE.search(raw_text))

    # 2. Check for Synthesis (tong_hop) - highest priority among substantive intents
    synthesis_matches = [k for k in _SYNTHESIS_KEYWORDS if k in folded]
    if synthesis_matches:
        return QuestionIntentResult(
            intent=INTENT_TONG_HOP,
            confidence=0.88 + min(0.1, len(synthesis_matches) * 0.03),
            matched_patterns=synthesis_matches,
            suggested_rephrasings=[],
            explanation=f"Phát hiện từ khóa tổng hợp/so sánh: {', '.join(synthesis_matches[:3])}.",
        )

    # 3. Check for Overview (tong_quan)
    overview_matches = [k for k in _OVERVIEW_KEYWORDS if k in folded]
    if overview_matches:
        return QuestionIntentResult(
            intent=INTENT_TONG_QUAN,
            confidence=0.85 + min(0.1, len(overview_matches) * 0.03),
            matched_patterns=overview_matches,
            suggested_rephrasings=[],
            explanation=f"Phát hiện từ khóa tổng quan/quy trình: {', '.join(overview_matches[:3])}.",
        )

    # 4. Check for Ambiguous (mo_ho) patterns
    is_ambiguous_match = False
    ambiguous_matched_pat = ""
    for pat in _AMBIGUOUS_PATTERNS:
        if re.search(pat, folded):
            is_ambiguous_match = True
            ambiguous_matched_pat = pat
            break

    # If ambiguous match without a specific code, or ultra-short (<= 3 words) without explicit code or lookup keywords
    if not has_specific_code:
        if is_ambiguous_match or (word_count <= 3 and not any(k in folded for k in ["la gi", "la gi?", "o dau", "bao nhieu"])):
            suggestions = suggest_rephrasings(raw_text, context_titles, playbook_domain)
            return QuestionIntentResult(
                intent=INTENT_MO_HO,
                confidence=0.92,
                matched_patterns=[ambiguous_matched_pat or f"short_query_len_{word_count}"],
                suggested_rephrasings=suggestions,
                explanation="Câu hỏi quá ngắn hoặc thiếu ngữ cảnh cụ thể; cần làm rõ ý định.",
            )

    # 5. Check for Lookup (tra_cuu)
    lookup_matches = [k for k in _LOOKUP_KEYWORDS if k in folded]
    if lookup_matches or has_specific_code:
        patterns = lookup_matches.copy()
        if has_specific_code:
            patterns.append("specific_technical_code")
        return QuestionIntentResult(
            intent=INTENT_TRA_CUU,
            confidence=0.86 + min(0.1, len(patterns) * 0.03),
            matched_patterns=patterns,
            suggested_rephrasings=[],
            explanation=f"Phát hiện yêu cầu tra cứu thông số/mã lỗi/định nghĩa: {', '.join(patterns[:3])}.",
        )

    # Default fallback: if query has reasonable length, classify as lookup with moderate confidence
    return QuestionIntentResult(
        intent=INTENT_TRA_CUU,
        confidence=0.60,
        matched_patterns=["default_inferred_lookup"],
        suggested_rephrasings=[],
        explanation="Không khớp từ khóa đặc thù; mặc định phân loại tra cứu thông tin.",
    )
