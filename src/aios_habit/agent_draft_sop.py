"""Draft SOP and investigation reports from evidence packs with strict fail-closed human approval.

Rules:
1. Soạn nháp SOP/báo cáo từ gói bằng chứng (chữ RAG + line_events suspected).
2. Mọi hành động đụng file nhà máy: FAIL-CLOSED đến khi người bấm duyệt trên UI tiếng Việt.
3. Không xóa file nhà máy trong bất kỳ trường hợp nào.
4. Trạng thái: draft | approved. Provenance rõ ràng.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
import uuid


DRAFT_STATUS_DRAFT = "draft"
DRAFT_STATUS_APPROVED = "approved"

PROTECTED_FACTORY_DIR_PATTERNS = (
    "tailieugoc",
    "tài liệu của tất cả dòng máy",
    "tai_lieu_cua_tat_ca_dong_may",
    "local_cases",
    "local_runs",
)

PROTECTED_FACTORY_FILE_EXTENSIONS = (
    ".csv",
    ".xlsx",
    ".xlsm",
    ".xls",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".dwg",
    ".sqlite",
    ".db",
)


class FactoryFileProtectionError(PermissionError):
    """Raised when an agent action cannot satisfy the factory-file safety contract."""


@dataclass(frozen=True)
class DraftProvenanceItem:
    source_id: str
    source_type: str
    title: str
    location: str
    provenance: str
    snippet: str


@dataclass(frozen=True)
class DraftDocument:
    draft_id: str
    doc_type: str  # 'sop' | 'report'
    title: str
    status: str  # 'draft' | 'approved'
    content_markdown: str
    author: str
    created_at: str
    provenance_items: tuple[DraftProvenanceItem, ...] = ()
    approval_metadata: dict[str, Any] = field(default_factory=dict)


def is_factory_protected_path(target_path: str | Path) -> bool:
    """Return True for factory source locations and raw factory file formats."""
    norm = str(target_path).replace("\\", "/").lower()
    for pattern in PROTECTED_FACTORY_DIR_PATTERNS:
        if pattern in norm:
            return True
    path_obj = Path(target_path)
    if path_obj.name in {"library.sqlite", "line_events.sqlite"}:
        return True
    return path_obj.suffix.lower() in PROTECTED_FACTORY_FILE_EXTENSIONS


def guard_factory_file_action(
    action: str,
    target_path: str | Path,
    *,
    approved: bool = False,
) -> None:
    """Fail-closed guard for factory file operations.

    - Deletion of factory files is ALWAYS prohibited.
    - Modification or creation requires explicit user approval.
    - Raw factory source directories are strictly write-protected.
    """
    act = str(action).lower().strip()
    path_obj = Path(target_path)

    if act in {"delete", "remove", "unlink", "rmdir"}:
        raise FactoryFileProtectionError(
            "Không được xóa file nhà máy trong bất kỳ trường hợp nào."
        )

    if act != "write":
        raise FactoryFileProtectionError(
            "Thao tác file này không được hỗ trợ; Agent chỉ được xuất nháp mới sau khi duyệt."
        )

    if not approved:
        raise FactoryFileProtectionError(
            "Mọi hành động sửa/ghi file nhà máy đều bị chặn (fail-closed) "
            "đến khi người dùng bấm duyệt trên giao diện tiếng Việt."
        )

    if is_factory_protected_path(path_obj):
        raise FactoryFileProtectionError(
            f"Không được ghi đè trực tiếp lên nguồn dữ liệu/tài liệu gốc của nhà máy: {path_obj.name}"
        )


def compose_draft_from_evidence(
    *,
    evidence_pack: Mapping[str, Any],
    doc_type: str = "sop",
    title: str = "Dự thảo Quy trình / Báo cáo Điều tra",
    author: str = "AIOS Habit Agent",
    target_station: str = "",
) -> DraftDocument:
    """Compose a draft SOP or investigation report from text citations and suspected line log events."""
    if doc_type not in {"sop", "report"}:
        raise ValueError("Loại tài liệu nháp chưa được hỗ trợ.")
    now_iso = datetime.now(timezone.utc).isoformat()
    draft_id = f"DRAFT-{uuid.uuid4().hex[:8].upper()}"

    evidence_items = list(evidence_pack.get("evidence_items") or [])
    line_events_matched = evidence_pack.get("line_events_matched") or {}
    if not line_events_matched and "events" in evidence_pack:
        line_events_matched = {"events": evidence_pack["events"]}

    provenance_list: list[DraftProvenanceItem] = []

    text_citations: list[dict[str, Any]] = []
    log_citations: list[dict[str, Any]] = []

    for item in evidence_items:
        src_type = str(item.get("source_type") or "rag_text")
        src_title = str(item.get("title") or "Tài liệu RAG")
        loc = str(item.get("location_info") or item.get("location") or "")
        text = str(item.get("text") or "")
        prov = str(item.get("provenance") or ("suspected" if src_type == "line_log" else "verified_text"))

        prov_item = DraftProvenanceItem(
            source_id=str(item.get("source_id") or "src-rag"),
            source_type=src_type,
            title=src_title,
            location=loc,
            provenance=prov,
            snippet=text[:200],
        )
        provenance_list.append(prov_item)

        if src_type == "line_log":
            log_citations.append({"title": src_title, "text": text, "provenance": prov, "location": loc})
        else:
            text_citations.append({"title": src_title, "text": text, "provenance": prov, "location": loc})

    events = line_events_matched.get("events") or ()
    if events and not log_citations:
        for ev in events:
            code = getattr(ev, "code", "") if hasattr(ev, "code") else ev.get("code", "")
            station = getattr(ev, "station", "") if hasattr(ev, "station") else ev.get("station", "")
            occurred_at = getattr(ev, "occurred_at", "") if hasattr(ev, "occurred_at") else ev.get("occurred_at", "")
            prov = getattr(ev, "provenance", "suspected") if hasattr(ev, "provenance") else ev.get("provenance", "suspected")
            dialect = getattr(ev, "dialect", "line_log") if hasattr(ev, "dialect") else ev.get("dialect", "line_log")

            summary_str = f"Sự kiện: {occurred_at} | {dialect} | mã {code} | trạm {station} | {prov}"
            prov_item = DraftProvenanceItem(
                source_id="line-events",
                source_type="line_log",
                title=f"Log {dialect} trạm {station}",
                location="line_events.sqlite",
                provenance=prov,
                snippet=summary_str,
            )
            provenance_list.append(prov_item)
            log_citations.append({
                "title": f"Log {dialect} ({station})",
                "text": summary_str,
                "provenance": prov,
                "location": "line_events.sqlite",
            })

    lines: list[str] = []
    lines.append(f"# {title.upper()}")
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append(f"> **Trạng thái:** NHÁP (Chưa phê duyệt) | **Mã dự thảo:** `{draft_id}` | **Ngày tạo:** `{now_iso}`")
    lines.append("> **Quy tắc an toàn:** Mọi hành động ghi ra file chính thức đều bị chặn cho đến khi người dùng bấm duyệt trên giao diện.")
    lines.append("")

    lines.append("## 1. Mục tiêu và phạm vi áp dụng")
    target_info = f" cho trạm/máy `{target_station}`" if target_station else ""
    if doc_type == "sop":
        lines.append(f"Dự thảo quy trình thao tác chuẩn (SOP){target_info} được tổng hợp tự động từ gói bằng chứng tri thức và log.")
    else:
        lines.append(f"Dự thảo báo cáo điều tra kỹ thuật{target_info} đối chiếu giữa tiêu chuẩn và sự kiện log thực tế.")
    lines.append("")

    lines.append("## 2. Căn cứ văn bản và tiêu chuẩn đã xác minh (RAG)")
    if text_citations:
        for idx, item in enumerate(text_citations, start=1):
            lines.append(f"### 2.{idx}. {item['title']}")
            if item["location"]:
                lines.append(f"- **Vị trí tài liệu:** `{item['location']}`")
            lines.append(f"- **Trạng thái xuất xứ:** `{item['provenance']}`")
            lines.append(f"- **Trích dẫn nội dung:**\n> {item['text']}")
            lines.append("")
    else:
        lines.append("*Chưa có trích đoạn văn bản RAG tương ứng trong gói bằng chứng.*")
        lines.append("")

    lines.append("## 3. Dữ liệu log điều tra liên quan (Nghi ngờ — Chưa phải chẩn đoán)")
    if log_citations:
        lines.append("> [!NOTE]")
        lines.append("> Các sự kiện log dưới đây có nguồn gốc `suspected` từ `line_events.sqlite`. Chúng phục vụ điều tra, không phải kết luận chẩn đoán nguyên nhân gốc.")
        lines.append("")
        for idx, item in enumerate(log_citations, start=1):
            lines.append(f"- **Sự kiện 3.{idx}:** {item['text']}")
        lines.append("")
    else:
        lines.append("*Không có sự kiện log nghi ngờ nào được ghi nhận trong gói bằng chứng này.*")
        lines.append("")

    lines.append("## 4. Nội dung quy trình / Đề xuất hành động (Dự thảo)")
    lines.append("1. **Kiểm tra hiện trường:** Xác minh tình trạng sensor, camera, hoặc cơ cấu chấp hành theo trích dẫn mục 2.")
    lines.append("2. **Đối chiếu log:** Kiểm tra lại mã lỗi và thời điểm phát sinh theo bảng log mục 3.")
    lines.append("3. **Biện pháp khắc phục:** Thực hiện đúng trình tự bảo dưỡng hoặc hiệu chuẩn quy định.")
    lines.append("4. **Đánh giá sau xử lý:** Chạy kiểm thử mẫu thử và xác nhận trạng thái trước khi cho phép máy hoạt động lại.")
    lines.append("")

    lines.append("## 5. Bảng truy vết nguồn gốc")
    lines.append("| STT | Nguồn | Loại | Vị trí | Trạng thái nguồn |")
    lines.append("|---|---|---|---|---|")
    for idx, p in enumerate(provenance_list, start=1):
        lines.append(f"| {idx} | {p.title} | `{p.source_type}` | `{p.location}` | **{p.provenance}** |")
    lines.append("")

    content_markdown = "\n".join(lines)

    return DraftDocument(
        draft_id=draft_id,
        doc_type=doc_type,
        title=title,
        status=DRAFT_STATUS_DRAFT,
        content_markdown=content_markdown,
        author=author,
        created_at=now_iso,
        provenance_items=tuple(provenance_list),
        approval_metadata={},
    )


def approve_draft_document(
    draft: DraftDocument,
    *,
    approver: str,
    notes: str = "",
) -> DraftDocument:
    """Explicitly approve a draft document on the Vietnamese UI."""
    if draft.status != DRAFT_STATUS_DRAFT:
        raise FactoryFileProtectionError("Chỉ tài liệu ở trạng thái nháp mới có thể được phê duyệt.")
    if not approver or not approver.strip():
        raise ValueError("Tên người duyệt không được để trống.")

    now_iso = datetime.now(timezone.utc).isoformat()
    updated_content = draft.content_markdown.replace(
        "**Trạng thái:** NHÁP (Chưa phê duyệt)",
        f"**Trạng thái:** ĐÃ DUYỆT | **Người duyệt:** `{approver}` | **Thời điểm:** `{now_iso}`",
    )

    metadata = {
        "approver": approver.strip(),
        "approved_at": now_iso,
        "notes": str(notes or "").strip(),
    }

    return DraftDocument(
        draft_id=draft.draft_id,
        doc_type=draft.doc_type,
        title=draft.title,
        status=DRAFT_STATUS_APPROVED,
        content_markdown=updated_content,
        author=draft.author,
        created_at=draft.created_at,
        provenance_items=draft.provenance_items,
        approval_metadata=metadata,
    )


def save_draft_document(
    doc: DraftDocument,
    output_path: str | Path,
    *,
    approved: bool = False,
) -> str:
    """Save an approved draft document to a file. Fails closed if not approved or doc is draft."""
    target = Path(output_path).resolve()

    guard_factory_file_action("write", target, approved=approved)

    if doc.status != DRAFT_STATUS_APPROVED:
        raise FactoryFileProtectionError(
            "Tài liệu vẫn ở trạng thái nháp chưa được duyệt. Không thể xuất/ghi ra file chính thức."
        )

    if target.exists():
        raise FactoryFileProtectionError(
            "Không được ghi đè file đang có. Agent chỉ được tạo file nháp mới sau khi duyệt."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc.content_markdown, encoding="utf-8")
    return str(target)
