from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List

from aios_habit.rag_evidence import RAGEvidenceItem, RAGEvidencePack


@dataclass
class FinalOwnerAnswer:
    draft_id: str
    pack_id: str
    query: str
    answer_text: str
    citation_ids: List[str]
    evidence_ids: List[str]
    privacy_mode: str
    allowed_external: bool
    insufficient_evidence: bool
    confidence_label: str
    warnings: List[str] = field(default_factory=list)
    composer_name: str = "deterministic_final_owner_composer_v1"
    provider_call: bool = False
    notebooklm_call: bool = False
    answer_kind: str = "final_owner_answer"
    final_answer: bool = True
    requires_strong_model_or_human_review: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, str] = field(default_factory=dict)


def _stable_final_id(pack: RAGEvidencePack) -> str:
    raw = f"final:{pack.pack_id}:{pack.query}:" + "|".join(i.evidence_id for i in pack.items)
    return "FANS-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()


def _valid_items(pack: RAGEvidencePack, max_items: int) -> List[RAGEvidenceItem]:
    return [i for i in pack.items if i.metadata.get("_is_metadata_only") != "True"][:max_items]


def _ref_id(index: int) -> str:
    return f"[E{index}]"


def _clean(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return text[: limit - 1].rstrip() + "…" if len(text) > limit else text


def _question_kind(question: str, items: Iterable[RAGEvidenceItem], target_source_type: str = "") -> str:
    q = question.lower()
    types = " ".join([target_source_type.lower()] + [i.file_type.lower() for i in items])
    if any(k in q for k in ["troubleshoot", "điều tra", "kiem tra", "kiểm tra", "next action", "handover", "bàn giao", "missing evidence"]):
        return "mixed"
    if any(t in types for t in ["xlsx", "xls", "csv", "spreadsheet"]):
        return "excel"
    if any(t in types for t in ["pdf", "ppt", "pptx"]):
        return "process"
    if any(t in types for t in ["png", "jpg", "jpeg", "ocr", "screenshot"]):
        return "screenshot"
    if any(t in types for t in ["html", "htm", "schema", "erd"]):
        return "schema"
    return "general"


def _source_location(item: RAGEvidenceItem) -> str:
    parts: List[str] = []
    if item.page_numbers:
        parts.append("pages " + ",".join(map(str, item.page_numbers)))
    if item.sheet_names:
        parts.append("sheets " + ",".join(item.sheet_names))
    if item.slide_numbers:
        parts.append("slides " + ",".join(map(str, item.slide_numbers)))
    return "; ".join(parts) or item.citation_label or item.relative_path or item.source_title


def _claim_lines(items: List[RAGEvidenceItem], kind: str) -> List[str]:
    if not items:
        return ["- Chưa có bằng chứng nội dung đủ để trả lời trực tiếp; cần bổ sung nguồn trước khi ra quyết định."]
    top = [_clean(i.snippet, 160) for i in items[:3]]
    if kind == "excel":
        return [
            f"- Bảng/tệp dữ liệu cho thấy các trường và dòng kiểm soát liên quan cần được đối chiếu: {top[0]} [E1].",
            "- Nên hiểu đây là quan hệ giữa master data, mã tuyến/đơn, trạng thái xử lý và bước vận hành; không chỉ là một đoạn văn rời rạc.",
            "- Nếu có nhiều sheet/cột, cần map cột nguồn, khóa nối và cột kết quả trước khi kết luận lỗi thuộc WMS/MOM/AGV.",
        ]
    if kind == "process":
        return [
            f"- Tài liệu quy trình nêu dấu hiệu về bước xử lý/chuyển giao: {top[0]} [E1].",
            "- Phần tự động là phần hệ thống có thể kiểm tra từ log, trạng thái, mapping hoặc rule; phần thủ công là xác nhận nghiệp vụ, phê duyệt và xử lý ngoại lệ.",
            "- Cần tách rõ quy trình mô tả trong PDF/PPTX với thao tác thực tế đã xảy ra trong case.",
        ]
    if kind == "screenshot":
        return [
            f"- Sự kiện nhìn thấy trực tiếp trong ảnh/OCR: {top[0]} [E1].",
            "- Mọi nguyên nhân phía sau ảnh chỉ là suy luận cho tới khi có log, bảng cấu hình hoặc tài liệu quy trình đối chiếu.",
        ]
    if kind == "schema":
        return [
            f"- Schema/HTML cho thấy cấu trúc hoặc trường được trích xuất: {top[0]} [E1].",
            "- Có thể liệt kê bảng/trường/quan hệ được nêu rõ, nhưng chưa được kết luận hành vi vận hành nếu thiếu log hoặc SOP.",
        ]
    if kind == "mixed":
        return [
            f"- Điểm bắt đầu điều tra là bằng chứng có liên quan trực tiếp nhất: {top[0]} [E1].",
            "- Cần nối bằng chứng cấu hình, log chạy thực tế, quy trình thao tác và xác nhận owner để tránh nhầm giữa nguyên nhân và triệu chứng.",
            "- Đầu ra nên là đường điều tra và bàn giao việc cần làm, không phải kết luận đóng nếu bằng chứng còn thiếu.",
        ]
    return [
        f"- Bằng chứng chính cho câu hỏi là: {top[0]} [E1].",
        "- Các nguồn cần được đọc như một chuỗi dấu hiệu vận hành; kết luận chỉ nên bám vào nội dung đã được trích xuất và cite.",
    ]


def _actions(kind: str, sufficient: bool) -> List[str]:
    common = [
        "1. Xác nhận câu hỏi owner cần quyết: lỗi ở đâu, ai xử lý, hay bước tiếp theo là gì.",
        "2. Đối chiếu từng claim với nguồn [E1], [E2] trước khi giao việc.",
    ]
    if kind == "excel":
        return common + [
            "3. Lập bảng mapping: trường nguồn, trường đích, khóa nối, trạng thái, owner dữ liệu.",
            "4. Kiểm tra các dòng thiếu mã tuyến/mã đơn/trạng thái và so với log vận hành.",
        ]
    if kind == "process":
        return common + [
            "3. Tách bước tự động khỏi bước thủ công/phê duyệt trong quy trình.",
            "4. Kiểm tra log hệ thống cho bước tự động và hỏi owner cho bước thủ công.",
        ]
    if kind == "screenshot":
        return common + [
            "3. Ghi lại facts nhìn thấy trong ảnh; không suy diễn nguyên nhân từ ảnh đơn lẻ.",
            "4. Thu thêm log, export bảng hoặc SOP cho cùng thời điểm.",
        ]
    if kind == "mixed":
        return common + [
            "3. Dựng timeline: thời điểm phát sinh, hệ thống liên quan, bước handoff, người xử lý.",
            "4. Thu missing evidence: log WMS/MOM/AGV, mapping hiện hành, ảnh lỗi, xác nhận owner.",
            "5. Bàn giao: ghi rõ giả thuyết, bằng chứng ủng hộ, bằng chứng còn thiếu, người chịu trách nhiệm và hạn kiểm tra.",
        ]
    return common + [
        "3. Nếu bằng chứng chưa đủ, yêu cầu đúng nguồn còn thiếu thay vì chốt nguyên nhân.",
    ]


def compose_final_owner_answer(pack: RAGEvidencePack, target_source_type: str = "", case_context: str = "", max_items: int = 6) -> FinalOwnerAnswer:
    items = _valid_items(pack, max_items)
    kind = _question_kind(pack.query, items, target_source_type)
    citation_ids = [_ref_id(i + 1) for i in range(len(items))]
    evidence_ids = [i.evidence_id for i in items]
    warnings: List[str] = []
    if pack.privacy_mode == "local_only":
        warnings.append("Privacy: local_only evidence stays local; no cloud/provider call was made.")
    if pack.insufficient_evidence or not items:
        warnings.append("Evidence is insufficient; treat this as a bounded owner answer with explicit gaps.")

    conclusion = _claim_lines(items, kind)
    actions = _actions(kind, bool(items) and not pack.insufficient_evidence)
    evidence_lines = []
    for idx, item in enumerate(items, 1):
        evidence_lines.append(f"- [E{idx}] {item.source_title or item.citation_label}: {_clean(item.snippet, 170)}. Vì sao quan trọng: nguồn này neo claim vào {item.file_type or 'source'} và vị trí {_source_location(item)}.")

    table_rows = ["| Ref | Source | Type | Location | Limitation |", "|---|---|---|---|---|"]
    for idx, item in enumerate(items, 1):
        limitation = "snippet trích xuất; cần mở nguồn nếu ra quyết định cuối" if len(item.text) > len(item.snippet) else "phạm vi bằng chứng hẹp"
        table_rows.append(f"| [E{idx}] | {item.source_title or item.citation_label} | {item.file_type or 'unknown'} | {_source_location(item)} | {limitation} |")
    if not items:
        table_rows.append("| n/a | no extracted content evidence | n/a | n/a | cần bổ sung nguồn nội dung |")

    if kind == "screenshot":
        understanding = "Facts nhìn thấy được tách khỏi suy luận: chỉ phần có trong ảnh/OCR được dùng làm bằng chứng; nguyên nhân cần log hoặc tài liệu đối chiếu."
    elif kind == "process":
        understanding = "Quy trình được hiểu theo ranh giới tự động/thủ công: hệ thống tự kiểm tra dữ liệu/log, còn owner xác nhận ngoại lệ, phê duyệt và xử lý nghiệp vụ."
    elif kind == "excel":
        understanding = "Bằng chứng dạng bảng cần được hiểu qua mapping trường, khóa nối và quan hệ giữa dòng dữ liệu với bước vận hành."
    elif kind == "schema":
        understanding = "Schema/ERD/HTML chỉ chứng minh cấu trúc được nêu rõ; không tự chứng minh hành vi vận hành nếu thiếu log/SOP."
    elif kind == "mixed":
        understanding = "Câu hỏi cần một đường điều tra/handover: kết nối triệu chứng, cấu hình, log và owner action thay vì chỉ liệt kê snippets."
    else:
        understanding = "Bằng chứng được tổng hợp thành câu trả lời owner-facing, với giới hạn rõ về điều chưa thể kết luận."

    unsupported = [
        "- Không kết luận nguyên nhân gốc nếu chưa có log/chứng cứ cùng thời điểm.",
        "- Không kết luận trách nhiệm cá nhân nếu chưa có xác nhận owner hoặc audit trail.",
        "- Không kết luận AIOS thay thế NotebookLM; đây là câu trả lời local_owner có giới hạn.",
    ]
    if not items:
        unsupported.insert(0, "- Không kết luận nội dung tài liệu vì chưa có extracted content evidence.")

    confidence = "medium" if items and not pack.insufficient_evidence else "low"
    if len(items) >= 4 and not pack.insufficient_evidence:
        confidence = "high"

    sections = [
        "## Kết luận ngắn",
        *conclusion[:6],
        "",
        "## Cách hiểu từ bằng chứng",
        understanding + (f" Bối cảnh case: {case_context}" if case_context else ""),
        "",
        "## Bằng chứng chính",
        *(evidence_lines or ["- Chưa có [E1] vì không có evidence nội dung hợp lệ."]),
        "",
        "## Hướng xử lý / kiểm tra",
        *actions,
        "",
        "## Không được kết luận nếu chưa có thêm bằng chứng",
        *unsupported,
        "",
        "## Bảng nguồn",
        *table_rows,
        "",
        "## Mức tin cậy",
        f"{confidence}: dựa trên {len(items)} nguồn nội dung hợp lệ; privacy={pack.privacy_mode}; insufficient_evidence={pack.insufficient_evidence}.",
    ]

    return FinalOwnerAnswer(
        draft_id=_stable_final_id(pack),
        pack_id=pack.pack_id,
        query=pack.query,
        answer_text="\n".join(sections),
        citation_ids=citation_ids,
        evidence_ids=evidence_ids,
        privacy_mode=pack.privacy_mode,
        allowed_external=pack.allowed_external,
        insufficient_evidence=pack.insufficient_evidence or not bool(items),
        confidence_label=confidence,
        warnings=warnings,
        metadata={"target_source_type": target_source_type, "answer_profile": kind},
    )


def final_owner_answer_to_dict(answer: FinalOwnerAnswer) -> Dict[str, Any]:
    return asdict(answer)
