from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List

from aios_habit.rag_evidence import RAGEvidenceItem, RAGEvidencePack
from aios_habit.source_router import classify_query_profile, route_evidence_by_profile


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
    composer_name: str = "deterministic_final_owner_composer_v2"
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
    if kind == "excel_mapping":
        return [
            f"- Bảng/tệp dữ liệu cho thấy các trường và dòng kiểm soát liên quan cần được đối chiếu: {top[0]} [E1].",
            "- Cần extract chính xác tên bảng, trường dữ liệu, khóa nối (join keys), và trạng thái (status flags).",
            "- Liệt kê mapping đích/nguồn, và đánh dấu nếu thiếu trường quan trọng.",
        ]
    if kind == "process_boundary":
        return [
            f"- Tài liệu quy trình nêu dấu hiệu về bước xử lý/chuyển giao: {top[0]} [E1].",
            "- Ranh giới tự động/thủ công: phần hệ thống tự chạy (cần check log) vs phần người dùng phải thao tác (cần owner check).",
            "- Cần tách rõ quy trình mô tả trong PDF/PPTX với thao tác thực tế đã xảy ra trong case.",
        ]
    if kind == "design_change":
        return [
            f"- Dấu hiệu thay đổi thiết kế (ECO/ECN/RC): {top[0]} [E1].",
            "- Đây là luồng design change, không áp dụng template table mapping thông thường.",
            "- Chú ý sự kiện thay thế linh kiện BOM/BOP, ngày bắt đầu chạy thay đổi, và xác nhận tồn kho cũ.",
        ]
    if kind == "screenshot_visible_facts":
        return [
            f"- Sự kiện nhìn thấy trực tiếp trong ảnh/OCR: {top[0]} [E1].",
            "- Chỉ liệt kê các trường, trạng thái, ID, text thực sự thấy trong ảnh; tách biệt phần có OCR uncertainty.",
            "- Mọi nguyên nhân phía sau ảnh chỉ là suy luận cho tới khi có log/database.",
        ]
    if kind == "screenshot_unsupported_inference":
        return [
            f"- Bằng chứng hình ảnh/màn hình: {top[0]} [E1].",
            "- KHÔNG SUY LUẬN trạng thái backend/database hoặc luồng ngầm nếu chỉ nhìn ảnh.",
            "- Liệt kê rõ những gì không thể kết luận từ ảnh này và yêu cầu cung cấp log hoặc config bổ sung.",
        ]
    if kind == "schema_tables_fields":
        return [
            f"- Schema/HTML cho thấy cấu trúc hoặc trường được trích xuất: {top[0]} [E1].",
            "- Cần liệt kê bảng, trường và quan hệ được định nghĩa cứng.",
            "- Không tự tiện suy diễn hành vi runtime từ schema.",
        ]
    if kind == "schema_unsupported_conclusions":
        return [
            f"- Phân tích schema/HTML: {top[0]} [E1].",
            "- Cảnh báo: từ schema không thể kết luận được logic hoạt động thực tế đang chạy hay luồng dữ liệu (runtime behavior).",
            "- Yêu cầu thêm log hệ thống hoặc tài liệu SOP vận hành.",
        ]
    if kind == "mixed_troubleshooting":
        return [
            f"- Điểm bắt đầu điều tra là bằng chứng có liên quan trực tiếp nhất: {top[0]} [E1].",
            "- Bắt buộc cung cấp đường hướng điều tra từng bước (step-by-step investigation path).",
            "- Nêu chuỗi log, cấu hình, và owner action tương ứng.",
        ]
    if kind == "missing_evidence":
        return [
            f"- Phân tích hiện tại: {top[0]} [E1].",
            "- Vẫn còn thiếu bằng chứng trọng yếu. Cần chỉ ra đích danh (artifact) nào bị thiếu và tại sao.",
            "- Đưa ra thứ tự ưu tiên các evidence cần bổ sung.",
        ]
    if kind == "owner_handover":
        return [
            f"- Trích xuất phục vụ bàn giao: {top[0]} [E1].",
            "- Tổng hợp định dạng handover ngắn gọn, nêu rõ next actions của owner.",
            "- Chỉ ra các rủi ro, deadline (nếu có), và người phụ trách.",
        ]
    # general
    return [
        f"- Bằng chứng chính cho câu hỏi là: {top[0]} [E1].",
        "- Các nguồn cần được đọc như một chuỗi dấu hiệu vận hành; kết luận chỉ nên bám vào nội dung đã được trích xuất và cite.",
    ]


def _actions(kind: str, sufficient: bool) -> List[str]:
    common = [
        "1. Xác nhận câu hỏi owner cần quyết: lỗi ở đâu, ai xử lý, hay bước tiếp theo là gì.",
        "2. Đối chiếu từng claim với nguồn [E1], [E2] trước khi giao việc.",
    ]
    if kind == "excel_mapping":
        return common + [
            "3. Lập bảng mapping: trường nguồn, trường đích, khóa nối, trạng thái, owner dữ liệu.",
            "4. Kiểm tra các dòng thiếu mã tuyến/mã đơn/trạng thái và so với log vận hành.",
        ]
    if kind in ("process_boundary", "design_change"):
        return common + [
            "3. Tách bước tự động khỏi bước thủ công/phê duyệt trong quy trình.",
            "4. Kiểm tra log hệ thống cho bước tự động và hỏi owner cho bước thủ công.",
        ]
    if kind.startswith("screenshot"):
        return common + [
            "3. Ghi lại facts nhìn thấy trong ảnh; không suy diễn nguyên nhân từ ảnh đơn lẻ.",
            "4. Thu thêm log, export bảng hoặc SOP cho cùng thời điểm.",
        ]
    if kind in ("mixed_troubleshooting", "missing_evidence", "owner_handover"):
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
    profile = classify_query_profile(pack.query, target_source_type)
    routed = route_evidence_by_profile(items, profile, target_source_type)
    
    # We use primary items first, then supporting if we need more
    ordered_items = routed.primary_items + routed.supporting_items
    if not ordered_items and items:
        ordered_items = items  # ultimate fallback
        
    kind = profile.profile_id
    citation_ids = [_ref_id(i + 1) for i in range(len(ordered_items))]
    evidence_ids = [i.evidence_id for i in ordered_items]
    
    warnings: List[str] = routed.route_warnings.copy()
    if pack.privacy_mode == "local_only":
        warnings.append("Privacy: local_only evidence stays local; no cloud/provider call was made.")
    if pack.insufficient_evidence or not ordered_items:
        warnings.append("Evidence is insufficient; treat this as a bounded owner answer with explicit gaps.")

    if routed.missing_required_source_types:
        warnings.append(f"Missing target source types: {', '.join(routed.missing_required_source_types)}.")

    conclusion = _claim_lines(ordered_items, kind)
    actions = _actions(kind, bool(ordered_items) and not pack.insufficient_evidence)
    
    evidence_lines = []
    for idx, item in enumerate(ordered_items, 1):
        role = "Primary" if item in routed.primary_items else "Supporting"
        evidence_lines.append(f"- [E{idx}] [{role}] {item.source_title or item.citation_label}: {_clean(item.snippet, 170)}. Vì sao quan trọng: nguồn này neo claim vào {getattr(item, 'file_type', 'source')} và vị trí {_source_location(item)}.")

    table_rows = ["| Ref | Role | Source | Type | Location | Limitation |", "|---|---|---|---|---|---|"]
    for idx, item in enumerate(ordered_items, 1):
        role = "Primary" if item in routed.primary_items else "Supporting"
        limitation = "snippet trích xuất; cần mở nguồn nếu ra quyết định cuối" if len(item.text) > len(item.snippet) else "phạm vi bằng chứng hẹp"
        table_rows.append(f"| [E{idx}] | {role} | {item.source_title or item.citation_label} | {getattr(item, 'file_type', 'unknown')} | {_source_location(item)} | {limitation} |")
    if not ordered_items:
        table_rows.append("| n/a | n/a | no extracted content evidence | n/a | n/a | cần bổ sung nguồn nội dung |")

    if kind.startswith("screenshot"):
        understanding = "Facts nhìn thấy được tách khỏi suy luận: chỉ phần có trong ảnh/OCR được dùng làm bằng chứng; nguyên nhân cần log hoặc tài liệu đối chiếu."
    elif kind in ("process_boundary", "design_change"):
        understanding = "Quy trình được hiểu theo ranh giới tự động/thủ công: hệ thống tự kiểm tra dữ liệu/log, còn owner xác nhận ngoại lệ, phê duyệt và xử lý nghiệp vụ."
    elif kind == "excel_mapping":
        understanding = "Bằng chứng dạng bảng cần được hiểu qua mapping trường, khóa nối và quan hệ giữa dòng dữ liệu với bước vận hành."
    elif kind.startswith("schema"):
        understanding = "Schema/ERD/HTML chỉ chứng minh cấu trúc được nêu rõ; không tự chứng minh hành vi vận hành nếu thiếu log/SOP."
    elif kind in ("mixed_troubleshooting", "missing_evidence", "owner_handover"):
        understanding = "Câu hỏi cần một đường điều tra/handover: kết nối triệu chứng, cấu hình, log và owner action thay vì chỉ liệt kê snippets."
    else:
        understanding = "Bằng chứng được tổng hợp thành câu trả lời owner-facing, với giới hạn rõ về điều chưa thể kết luận."

    unsupported = [
        "- Không kết luận nguyên nhân gốc nếu chưa có log/chứng cứ cùng thời điểm.",
        "- Không kết luận trách nhiệm cá nhân nếu chưa có xác nhận owner hoặc audit trail.",
        "- Không kết luận AIOS thay thế NotebookLM; đây là câu trả lời local_owner có giới hạn.",
    ]
    if not ordered_items:
        unsupported.insert(0, "- Không kết luận nội dung tài liệu vì chưa có extracted content evidence.")
        
    if routed.missing_required_source_types:
        unsupported.insert(0, f"- BẮT BUỘC BỔ SUNG: Không thể kết luận đầy đủ do thiếu nguồn chính loại: {', '.join(routed.missing_required_source_types)}.")

    confidence = "medium" if ordered_items and not pack.insufficient_evidence else "low"
    if len(ordered_items) >= 4 and not pack.insufficient_evidence and routed.source_type_pass == "PASS":
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
        f"{confidence}: dựa trên {len(ordered_items)} nguồn nội dung hợp lệ; source_type_pass={routed.source_type_pass}; privacy={pack.privacy_mode}; insufficient_evidence={pack.insufficient_evidence}.",
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
        insufficient_evidence=pack.insufficient_evidence or not bool(ordered_items),
        confidence_label=confidence,
        warnings=warnings,
        metadata={"target_source_type": target_source_type, "answer_profile": kind, "source_type_pass": routed.source_type_pass},
    )


def final_owner_answer_to_dict(answer: FinalOwnerAnswer) -> Dict[str, Any]:
    return asdict(answer)
