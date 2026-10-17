"""Step 3: investigation-tree generator (4M + Why-Why) for error cases.

Input: an error phenomenon (+ optional error code) -> a 4M investigation
tree (Man / Machine / Material / Method) plus a 5-Why chain, each item
carrying what to confirm and what data/artifacts to collect.
Output: an investigation checklist rendered as Markdown, exportable to a
file (.md or .docx) that can be pasted straight into the company report.
Target user: a newcomer (G3 and below) running the first investigation step
alone without needing to ask experienced engineers.

Provenance & Grounding (Requirement Step 3):
- Every branch and checklist item is grounded on similar historical cases
  (Step 1 error cases DB engine) and repository documents when available.
- When no historical case or document exists for a branch, it is explicitly
  marked as "Gợi ý chung (không có ca lịch sử tương tự trong kho)".
- Provenance (căn cứ) is explicitly traceable for every item; no technical
  details are ever fabricated.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .glossary import lookup as glossary_lookup

# ---------------------------------------------------------------------------
# 4M branches
# ---------------------------------------------------------------------------

BRANCHES: Tuple[str, ...] = ("Man", "Machine", "Material", "Method")

BRANCH_LABELS_VI: Dict[str, str] = {
    "Man": "Con người (Man)",
    "Machine": "Máy móc (Machine)",
    "Material": "Vật liệu (Material)",
    "Method": "Phương pháp (Method)",
}

# Generic, manufacturing-standard questions per branch. Each item is
# (question_to_confirm, data_or_artifacts_to_collect).
TEMPLATES_4M: Dict[str, List[Tuple[str, str]]] = {
    "Man": [
        ("Người thao tác có làm đúng quy trình chuẩn (SOP) không?",
         "Bản ghi thao tác, biên bản ca, phỏng vấn ngắn người thao tác"),
        ("Người thao tác đã được đào tạo cho công đoạn này chưa?",
         "Hồ sơ đào tạo, chứng chỉ/bậc tay nghề (G3 trở xuống cần kèm người hướng dẫn)"),
        ("Có thay đổi người hoặc đổi ca gần thời điểm phát sinh lỗi không?",
         "Lịch phân ca, biên bản bàn giao ca"),
        ("Người thao tác làm liên tục bao lâu trước khi lỗi xảy ra?",
         "Ghi nhận giờ làm ca, số giờ làm liên tục"),
    ],
    "Machine": [
        ("Máy có báo mã lỗi hoặc cảnh báo gì kèm theo không?",
         "Ảnh chụp màn hình mã lỗi, log máy tại thời điểm lỗi"),
        ("Lần bảo trì/bảo dưỡng gần nhất là khi nào, nội dung gì?",
         "Lịch sử bảo trì, phiếu bảo dưỡng"),
        ("Thông số vận hành tại thời điểm lỗi (tốc độ, nhiệt độ, áp suất...) có bất thường không?",
         "Log thông số, biểu đồ xu hướng (trend) quanh thời điểm lỗi"),
        ("Có linh kiện nào vừa thay hoặc sửa gần đây không?",
         "Phiếu thay linh kiện, giữ lại linh kiện cũ làm hiện vật"),
    ],
    "Material": [
        ("Lô nguyên vật liệu đang dùng là lô nào, có COA không?",
         "Nhãn lô, COA, phiếu nhập kho"),
        ("Vật liệu có đúng chủng loại/quy cách theo BOM không?",
         "Mẫu vật liệu thực tế, đối chiếu BOM"),
        ("Điều kiện bảo quản vật liệu (nhiệt độ, độ ẩm, hạn dùng) có đạt không?",
         "Log kho, hạn sử dụng trên bao bì"),
        ("Có đổi nhà cung cấp hoặc chuyển sang lô mới gần đây không?",
         "Lịch sử nhập liệu, mẫu so sánh lô cũ/lô mới"),
    ],
    "Method": [
        ("Quy trình thao tác chuẩn (SOP/WI) đang áp dụng là bản nào?",
         "SOP/WI hiện hành, số hiệu bản"),
        ("Thông số cài đặt (recipe/parameter) có bị thay đổi so với chuẩn không?",
         "Bản ghi thông số cài đặt, lịch sử chỉnh máy"),
        ("Điều kiện môi trường xưởng (nhiệt độ, độ ẩm, bụi) tại thời điểm lỗi?",
         "Log môi trường, ghi nhận quan trắc"),
        ("Có thay đổi phương pháp hoặc công đoạn nào gần đây không?",
         "Biên bản thay đổi (ECN), so sánh trước/sau thay đổi"),
    ],
}

# Which branches to emphasize per glossary code family. The first branch
# is rendered first and marked as the priority branch.
FAMILY_BRANCH_HINTS: Dict[str, Tuple[str, ...]] = {
    "C_CALL": ("Machine", "Method", "Man", "Material"),
    "F_SYSTEM": ("Machine", "Method", "Material", "Man"),
    "JAM": ("Machine", "Material", "Method", "Man"),
    "SCT_ADJ": ("Method", "Machine", "Material", "Man"),
}

# Phenomenon keywords -> extra targeted items (branch, question, data).
KEYWORD_ITEMS: List[Tuple[Tuple[str, ...], str, str, str]] = [
    (("kẹt", "jam", "tắc"), "Machine",
     "Vị trí kẹt cụ thể ở đâu trên đường đi của vật liệu/sản phẩm?",
     "Ảnh vị trí kẹt, vật liệu kẹt giữ lại làm hiện vật"),
    (("mã lỗi", "báo lỗi", "error"), "Machine",
     "Mã lỗi hiển thị đầy đủ là gì (chụp lại nguyên văn)?",
     "Ảnh chụp mã lỗi, tra từ điển mã lỗi (glossary)"),
    (("đứt", "gãy", "vỡ", "nứt"), "Material",
     "Mặt cắt/bề mặt hư hỏng có dấu hiệu gì (mỏi, quá tải, lỗi vật liệu)?",
     "Hiện vật hư hỏng, ảnh chụp cận cảnh mặt gãy/vỡ"),
    (("lệch", "sai vị trí", "không đều"), "Method",
     "Chuẩn gá/cữ và cách căn chỉnh lần cuối như thế nào?",
     "Biên bản căn chỉnh, ảnh vị trí chuẩn vs thực tế"),
    (("mùi", "khói", "cháy", "nóng"), "Machine",
     "Có dấu hiệu quá nhiệt/chập điện ở bộ phận nào?",
     "Ảnh hiện trường, log nhiệt độ, ngắt điện an toàn trước khi kiểm tra"),
]


@dataclass
class ChecklistItem:
    """One investigation step: what to confirm + what to collect + provenance."""
    branch: str
    question: str
    data_to_collect: str
    priority: bool = False
    can_cu: str = "Gợi ý chung (tiêu chuẩn 4M sản xuất, không có ca lịch sử tương tự trong kho)"
    source_id: str = ""
    is_generic: bool = True


@dataclass
class WhyNode:
    """One level of the 5-Why chain."""
    level: int
    question: str
    hint: str
    answer: str = ""
    can_cu: str = ""


@dataclass
class InvestigationTree:
    """Full investigation plan for one phenomenon."""
    phenomenon: str
    code: str = ""
    code_family: str = ""
    code_name: str = ""
    code_cause: str = ""
    code_remedy: str = ""
    branches: Dict[str, List[ChecklistItem]] = field(default_factory=dict)
    branch_order: List[str] = field(default_factory=list)
    why_chain: List[WhyNode] = field(default_factory=list)
    created_at: str = ""
    tree_id: str = ""
    similar_cases: List[Dict[str, Any]] = field(default_factory=list)
    branch_basis: Dict[str, str] = field(default_factory=dict)
    total_items: int = 0
    grounded_items_count: int = 0
    generic_items_count: int = 0

    def all_items(self) -> List[ChecklistItem]:
        return [it for b in self.branch_order for it in self.branches.get(b, [])]


# ---------------------------------------------------------------------------
# Builders & Provenance Analysis
# ---------------------------------------------------------------------------

def _match_keyword_items(phenomenon: str) -> List[ChecklistItem]:
    lowered = phenomenon.lower()
    items: List[ChecklistItem] = []
    for keywords, branch, question, data in KEYWORD_ITEMS:
        if any(k in lowered for k in keywords):
            items.append(ChecklistItem(
                branch=branch,
                question=question,
                data_to_collect=data,
                priority=True,
                can_cu="Khớp từ khóa hiện tượng (quy chuẩn phân tích lỗi KTD)",
                source_id="KEYWORD_RULE",
                is_generic=False,
            ))
    return items


def _branch_order(code_family: str) -> List[str]:
    hinted = FAMILY_BRANCH_HINTS.get(code_family or "")
    if hinted:
        return list(hinted)
    return list(BRANCHES)


def _detect_case_branch(case: Dict[str, Any]) -> str:
    """Classify which 4M branch a historical case primarily informs."""
    text = " ".join([
        str(case.get("doi_sach") or ""),
        str(case.get("nguyen_nhan") or ""),
        str(case.get("hien_tuong") or ""),
        str(case.get("investigation") or ""),
        str(case.get("category") or ""),
    ]).lower()

    # Man keywords
    if any(k in text for k in (
        "thao tác", "thao tac", "công nhân", "cong nhan", "người làm", "dao tao",
        "đào tạo", "sop", "wi", "quên", "sơ suất", "nhầm", "bỏ sót", "so suat"
    )):
        return "Man"

    # Material keywords
    if any(k in text for k in (
        "linh kiện", "linh kien", "vật liệu", "vat lieu", "part", "supplier",
        "nhà cung cấp", "nha cung cap", "lô", "lot", "nhựa", "nhua", "toner",
        "mực", "muc", "giấy", "giay", "ribbon", "rách", "rach", "nứt", "nut",
        "vỡ", "vo", "biến dạng", "bien dang", "cong vênh", "cong venh", "kích thước", "kich thuoc"
    )):
        return "Material"

    # Method keywords
    if any(k in text for k in (
        "căn chỉnh", "can chinh", "thông số", "thong so", "điều chỉnh", "dieu chinh",
        "tiêu chuẩn", "tieu chuan", "cài đặt", "cai dat", "recipe", "parameter",
        "phương pháp", "phuong phap", "layout", "gá", "ga", "cữ", "cu", "ecn", "bản vẽ", "ban ve"
    )):
        return "Method"

    # Machine keywords or default
    return "Machine"


def build_tree(
    phenomenon: str,
    *,
    code: str = "",
    code_family: str = "",
    conn=None,
    similar_cases: Optional[Sequence[Dict[str, Any]]] = None,
    doc_sources: Optional[Sequence[Dict[str, Any]]] = None,
) -> InvestigationTree:
    """Build a 4M + Why-Why investigation tree for a phenomenon.

    Enriched with:
    - Provenance (căn cứ) from Step 1 similar cases when available.
    - Document sources from the knowledge store.
    - Explicit marking of generic suggestions when no historical basis exists.
    - 5-level Why-Why chain seeded with historical cause/remedy.
    """
    phenomenon = (phenomenon or "").strip()
    if not phenomenon:
        raise ValueError("phenomenon must not be empty")

    tree = InvestigationTree(
        phenomenon=phenomenon,
        code=code.strip(),
        code_family=(code_family or "").strip().upper(),
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        tree_id=f"TREE-{uuid.uuid4().hex[:8].upper()}",
    )

    entry = None
    if tree.code and tree.code_family and conn is not None:
        entry = glossary_lookup(conn, tree.code_family, tree.code)
    if entry:
        tree.code_name = entry.get("name_vi") or entry.get("name_en") or entry.get("name_ja") or ""
        tree.code_cause = entry.get("cause") or ""
        tree.code_remedy = entry.get("remedy") or ""

    order = _branch_order(tree.code_family)
    tree.branch_order = order

    # 1. Fetch similar cases (Step 1 engine) if not provided
    matched_cases: List[Dict[str, Any]] = list(similar_cases) if similar_cases is not None else []
    if not matched_cases and conn is not None:
        try:
            from aios_habit.chat_action_error_lookup import search_similar
            q_search = f"{tree.code} {phenomenon}".strip()
            cases, _, _ = search_similar(conn, q_search, top_n=5)
            matched_cases = list(cases)
        except Exception:
            matched_cases = []

    if not matched_cases and conn is None:
        try:
            from aios_habit.chat_action import ChatActionRequest
            from aios_habit.chat_action_error_lookup import _open_ro, resolve_db_path, search_similar
            db_p = resolve_db_path(ChatActionRequest(question=f"{tree.code} {phenomenon}"))
            if db_p and db_p.is_file():
                c_ro = _open_ro(db_p)
                try:
                    cases, _, _ = search_similar(c_ro, f"{tree.code} {phenomenon}".strip(), top_n=5)
                    matched_cases = list(cases)
                finally:
                    c_ro.close()
        except Exception:
            matched_cases = []

    tree.similar_cases = matched_cases

    # 2. Build grounded items from similar cases
    grounded_by_branch: Dict[str, List[ChecklistItem]] = {b: [] for b in BRANCHES}
    seen_remedies: set = set()

    for sc in matched_cases:
        branch = _detect_case_branch(sc)
        sc_id = str(sc.get("no_dvd") or sc.get("id") or "N/A").strip()
        rem = str(sc.get("doi_sach") or "").strip()
        cau = str(sc.get("nguyen_nhan") or "").strip()
        prov = str(sc.get("bao_cao_goc") or "").strip()
        where = str(sc.get("where") or "").strip()

        focus = rem or cau
        if not focus or focus.lower() in seen_remedies:
            continue
        seen_remedies.add(focus.lower())

        q_item = f"Xác nhận đối sách/nguyên nhân theo ca #{sc_id}: {focus}?"
        d_item = f"Ảnh chụp hiện trường, biên bản xác nhận, đối chiếu phiếu #{sc_id}"
        if prov:
            d_item += f" ({prov})"
        can_cu = f"Ca lịch sử #{sc_id}"
        if prov:
            can_cu += f" ({prov})"
        if rem:
            can_cu += f" | Đối sách lịch sử: {rem}"
        elif cau:
            can_cu += f" | Nguyên nhân lịch sử: {cau}"
        if where:
            can_cu += f" [Khu vực: {where}]"

        grounded_by_branch[branch].append(ChecklistItem(
            branch=branch,
            question=q_item,
            data_to_collect=d_item,
            priority=True,
            can_cu=can_cu,
            source_id=sc_id,
            is_generic=False,
        ))

    # 3. Build grounded items from document sources if any
    for doc in (doc_sources or []):
        doc_title = str(doc.get("title") or doc.get("filename") or "Tài liệu kỹ thuật").strip()
        doc_branch = str(doc.get("branch") or "Method")
        if doc_branch not in grounded_by_branch:
            doc_branch = "Method"
        grounded_by_branch[doc_branch].append(ChecklistItem(
            branch=doc_branch,
            question=f"Đối chiếu tiêu chuẩn quy trình/thông số theo tài liệu: {doc_title}?",
            data_to_collect=f"Bản trích tài liệu {doc_title}, bảng đo thông số thực tế",
            priority=True,
            can_cu=f"Tài liệu trong kho: {doc_title}",
            source_id=doc_title,
            is_generic=False,
        ))

    # 4. Keyword items from phenomenon text
    keyword_items = _match_keyword_items(phenomenon)

    # 5. Populate branches
    for branch in order:
        items: List[ChecklistItem] = []

        # Grounded items come first
        items.extend(grounded_by_branch.get(branch, []))

        # Targeted keyword items next
        for kw in keyword_items:
            if kw.branch == branch:
                items.append(kw)

        # Generic template items
        for q, d in TEMPLATES_4M[branch]:
            items.append(ChecklistItem(
                branch=branch,
                question=q,
                data_to_collect=d,
                priority=False,
                can_cu="Gợi ý chung (tiêu chuẩn 4M sản xuất, không có ca lịch sử tương tự trong kho)",
                source_id="",
                is_generic=True,
            ))

        tree.branches[branch] = items

        # Branch basis label
        g_count = len(grounded_by_branch.get(branch, []))
        if g_count > 0:
            tree.branch_basis[branch] = f"Có căn cứ (Dựa trên {g_count} ca lịch sử / tài liệu kho)"
        else:
            tree.branch_basis[branch] = "Gợi ý chung (không có ca lịch sử tương tự trong kho)"

    # Emphasized (first) branch items get priority flag
    if order:
        for it in tree.branches[order[0]]:
            it.priority = True

    # 6. Count totals
    all_its = tree.all_items()
    tree.total_items = len(all_its)
    tree.grounded_items_count = sum(1 for it in all_its if not it.is_generic)
    tree.generic_items_count = sum(1 for it in all_its if it.is_generic)

    # 7. Build Why-Why chain with historical basis
    top_case = matched_cases[0] if matched_cases else None
    hist_cause = str(top_case.get("nguyen_nhan") or "") if top_case else ""
    hist_id = str(top_case.get("no_dvd") or top_case.get("id") or "") if top_case else ""

    tree.why_chain = build_why_chain(
        phenomenon,
        cause_hint=tree.code_cause,
        historical_cause=hist_cause,
        historical_id=hist_id,
    )

    return tree


def build_why_chain(
    phenomenon: str,
    *,
    cause_hint: str = "",
    historical_cause: str = "",
    historical_id: str = "",
) -> List[WhyNode]:
    """Build a 5-level Why-Why skeleton.

    Level 1 is seeded with the phenomenon, glossary cause hint, and historical
    similar case findings when present.
    """
    l1_hints: List[str] = ["Mô tả nguyên nhân trực tiếp quan sát được tại hiện trường."]
    l1_cancu = "Gợi ý chung"
    if historical_cause:
        l1_hints.append(f"Căn cứ ca tương tự #{historical_id}: Nguyên nhân lịch sử là '{historical_cause}'.")
        l1_cancu = f"Ca lịch sử #{historical_id}"
    elif cause_hint:
        l1_hints.append(f"Gợi ý từ từ điển mã lỗi: {cause_hint}.")
        l1_cancu = "Từ điển mã lỗi (Glossary)"
    else:
        l1_hints.append("[Gợi ý chung: Chưa có ca lịch sử tương tự trong kho]")

    hints = [
        " ".join(l1_hints),
        "Tìm điều kiện hoặc tác nhân đã tạo ra nguyên nhân trực tiếp đó.",
        "Tìm nguyên nhân sâu hơn: vì sao điều kiện đó tồn tại?",
        "Tiếp tục đào sâu: quy trình/quản lý nào đã để lọt?",
        "Chốt nguyên nhân gốc (root cause): điểm mà nếu khắc phục thì chuỗi trên không tái diễn.",
    ]
    chain = [WhyNode(
        level=1,
        question=f"Vì sao hiện tượng “{phenomenon}” xảy ra?",
        hint=hints[0],
        can_cu=l1_cancu,
    )]
    prev = "nguyên nhân vừa xác định ở bước trước"
    for i in range(2, 6):
        chain.append(WhyNode(
            level=i,
            question=f"Vì sao {prev} lại xảy ra?",
            hint=hints[i - 1],
            can_cu="Phân tích suy luận tại hiện trường",
        ))
    return chain


# ---------------------------------------------------------------------------
# Markdown rendering + export
# ---------------------------------------------------------------------------

def render_markdown(tree: InvestigationTree) -> str:
    """Render the full investigation plan as Markdown (Vietnamese)."""
    L: List[str] = []
    L.append(f"# Cây điều tra — {tree.phenomenon}")
    L.append("")
    L.append(f"Ngày lập: {tree.created_at}")
    if tree.code:
        name = f" — {tree.code_name}" if tree.code_name else ""
        L.append(f"Mã lỗi: {tree.code_family} {tree.code}{name}".rstrip())
    L.append("")
    L.append(
        f"> **Chỉ số căn cứ Bước 3:** Tổng cộng **{tree.total_items}** hạng mục | "
        f"**{tree.grounded_items_count}** có căn cứ lịch sử/tài liệu | "
        f"**{tree.generic_items_count}** gợi ý chung."
    )
    L.append("> Dữ liệu trong kế hoạch này do người điều tra thu thập và điền "
             "tay; không dán dữ liệu thật chưa phân loại vào đây.")
    L.append("")

    L.append("## 1. Cây điều tra 4M")
    L.append("")
    for branch in tree.branch_order:
        label = BRANCH_LABELS_VI.get(branch, branch)
        basis_tag = tree.branch_basis.get(branch, "Gợi ý chung")
        L.append(f"### {label} — {basis_tag}")
        L.append("")
        for it in tree.branches.get(branch, []):
            star = " ⭐" if it.priority else ""
            L.append(f"- [ ] {it.question}{star}")
            L.append(f"  - **Dữ liệu/hiện vật cần thu thập:** {it.data_to_collect}")
            L.append(f"  - **Căn cứ:** {it.can_cu}")
        L.append("")

    L.append("## 2. Chuỗi Why-Why (5 lần hỏi vì sao)")
    L.append("")
    for node in tree.why_chain:
        L.append(f"{node.level}. {node.question}")
        L.append(f"   - Gợi ý: {node.hint}")
        if node.can_cu:
            L.append(f"   - Căn cứ: {node.can_cu}")
        L.append("   - Trả lời: ___")
        L.append("")

    L.append("## 3. Tổng hợp dữ liệu/hiện vật cần thu thập")
    L.append("")
    seen = set()
    for it in tree.all_items():
        key = it.data_to_collect.strip()
        if key and key not in seen:
            seen.add(key)
            L.append(f"- [ ] {key}")
    L.append("")

    L.append("## 4. Bảng truy vết căn cứ từng nhánh (Provenance Traceability)")
    L.append("")
    L.append("| Nhánh 4M | Hạng mục xác nhận | Loại căn cứ | Nguồn căn cứ / Ca lịch sử |")
    L.append("| :--- | :--- | :--- | :--- |")
    for it in tree.all_items():
        b_label = BRANCH_LABELS_VI.get(it.branch, it.branch)
        kind = "Gợi ý chung" if it.is_generic else "Có căn cứ"
        clean_q = it.question.replace("|", "/")
        clean_c = it.can_cu.replace("|", "/")
        L.append(f"| {b_label} | {clean_q} | {kind} | {clean_c} |")
    L.append("")

    return "\n".join(L)


def export_markdown(tree: InvestigationTree, path: str | Path) -> Path:
    """Write the rendered plan to a Markdown file. Returns the path."""
    out = Path(path)
    if out.suffix.lower() != ".md":
        out = out.with_suffix(".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(tree), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Company report template (extracted from real KTD investigation reports)
# ---------------------------------------------------------------------------
# Field labels verbatim from the "Bao cao dieu tra" sheet of the real KTD
# reports shipped with the company data, in sheet order.
# The generated investigation plan goes into the
# "Investigation content and results" row so the exported file pastes
# straight into the company report form.

REPORT_TITLE = "Báo cáo điều tra lỗi/調査報告書"
REPORT_AUTHOR_LABEL = "Người Lập作成者："
REPORT_DATE_LABEL = "Ngày lập作成日："
REPORT_TABLE_HEAD = ("Item／項目", "Details／詳細")

REPORT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("model", "Model/モデル"),
    ("item_code", "Item code - Rev／品番 - Rev"),
    ("item_name", "Item name／品名"),
    ("serial_lot", "S.No (Lot)／シリアル番号（ロット）"),
    ("supplier", "Supplier/サプライヤー"),
    ("machine_no", "Machine\u3000No.／仕上げ-マシンNo."),
    ("occurrence_date", "Occurrence\u3000Date／発生日"),
    ("defect_contents", "Contents of defect／不具合内容"),
    ("line", "Line／ライン"),
    ("quantity", "Quantity／数量"),
    ("status_at_line", "Status of occurrence at Line\nラインでの発生状況"),
    ("reappear_rate", "Reappear rate(%)\n(Describe the reappear environment )"),
    ("investigation", "Investigation content and results\n調査内容と結果:"),
)


def _report_meta(tree: InvestigationTree, meta: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Merge caller meta over defaults. Unfilled fields stay blank for the
    investigator; the phenomenon seeds 'Contents of defect'."""
    merged = {key: "" for key, _ in REPORT_FIELDS}
    merged["defect_contents"] = tree.phenomenon
    if tree.code:
        code_line = f"{tree.code_family} {tree.code}".strip()
        if tree.code_name:
            code_line += f" — {tree.code_name}"
        merged["defect_contents"] += f" [{code_line}]"
    if meta:
        for key in merged:
            if key in meta and meta[key] is not None:
                merged[key] = str(meta[key])
    return merged


def _plan_as_text(tree: InvestigationTree) -> str:
    """The investigation plan as plain text (for the 'Investigation content
    and results' row and the docx body)."""
    L: List[str] = []
    L.append("KẾ HOẠCH ĐIỀU TRA (Cây điều tra 4M)")
    for branch in tree.branch_order:
        label = BRANCH_LABELS_VI.get(branch, branch)
        basis = tree.branch_basis.get(branch, "")
        basis_str = f" — {basis}" if basis else ""
        L.append(f"[{label}{basis_str}]")
        for it in tree.branches.get(branch, []):
            star = " (ưu tiên)" if it.priority else ""
            L.append(f"  - {it.question}{star}")
            L.append(f"    Thu thập: {it.data_to_collect}")
            L.append(f"    Căn cứ: {it.can_cu}")
    L.append("Chuỗi Why-Why")
    for node in tree.why_chain:
        L.append(f"  {node.level}. {node.question}")
        L.append(f"     Gợi ý: {node.hint}")
        if node.can_cu:
            L.append(f"     Căn cứ: {node.can_cu}")
        L.append("     Trả lời: ___")
    L.append("Dữ liệu/hiện vật cần thu thập")
    seen = set()
    for it in tree.all_items():
        key = it.data_to_collect.strip()
        if key and key not in seen:
            seen.add(key)
            L.append(f"  - [ ] {key}")
    return "\n".join(L)


def render_report(tree: InvestigationTree,
                  meta: Optional[Dict[str, str]] = None) -> str:
    """Render the plan in the company KTD report layout (Markdown)."""
    fields = _report_meta(tree, meta)
    plan = _plan_as_text(tree)
    report_id = (meta or {}).get("report_id", "")
    author = (meta or {}).get("author", "")
    date = (meta or {}).get("date", "")

    L: List[str] = []
    title = REPORT_TITLE + (f" — {report_id}" if report_id else "")
    L.append(f"# {title}")
    L.append("")
    L.append(f"{REPORT_AUTHOR_LABEL} {author}")
    L.append("")
    L.append(f"{REPORT_DATE_LABEL} {date}")
    L.append("")
    L.append(f"| {REPORT_TABLE_HEAD[0]} | {REPORT_TABLE_HEAD[1]} |")
    L.append("| --- | --- |")
    for key, label in REPORT_FIELDS:
        value = fields[key]
        if key == "investigation":
            continue  # rendered as its own section below
        label_cell = label.replace("\n", "<br>")
        cell = value.replace("\n", "<br>") if value else ""
        L.append(f"| {label_cell} | {cell} |")
    L.append("")
    inv_label = dict(REPORT_FIELDS)["investigation"]
    inv_heading = inv_label.replace("\n", "<br>")
    L.append(f"## {inv_heading}")
    L.append("")
    L.append("```")
    L.append(plan)
    L.append("```")
    L.append("")
    return "\n".join(L)


def export_report(tree: InvestigationTree, path: str | Path,
                  meta: Optional[Dict[str, str]] = None) -> Path:
    """Write the company-format report. Dispatches on suffix:
    ``.md`` -> :func:`render_report`, ``.docx`` -> :func:`export_docx`."""
    out = Path(path)
    suffix = out.suffix.lower()
    if suffix == ".docx":
        return export_docx(tree, out, meta)
    out = out if suffix == ".md" else out.with_suffix(".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(tree, meta), encoding="utf-8")
    return out


def _set_cell_text(cell, text: str) -> None:
    """Set a docx table cell's text, keeping real line breaks."""
    cell.text = ""
    paragraph = cell.paragraphs[0]
    for index, line in enumerate(text.split("\n")):
        if index:
            paragraph.add_run().add_break()
        paragraph.add_run(line)


def export_docx(tree: InvestigationTree, path: str | Path,
                meta: Optional[Dict[str, str]] = None) -> Path:
    """Write the company-format report as a Word document."""
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError as exc:
        raise RuntimeError("python-docx is required for docx export") from exc

    fields = _report_meta(tree, meta)
    report_id = (meta or {}).get("report_id", "")
    author = (meta or {}).get("author", "")
    date = (meta or {}).get("date", "")

    doc = Document()
    for para in doc.paragraphs:
        for run in para.runs:
            run.font.size = Pt(11)

    title = REPORT_TITLE + (f" — {report_id}" if report_id else "")
    doc.add_heading(title, level=1)
    doc.add_paragraph(f"{REPORT_AUTHOR_LABEL} {author}")
    doc.add_paragraph(f"{REPORT_DATE_LABEL} {date}")

    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text = REPORT_TABLE_HEAD
    for key, label in REPORT_FIELDS:
        if key == "investigation":
            continue
        row = table.add_row().cells
        _set_cell_text(row[0], label)
        _set_cell_text(row[1], fields[key])

    inv_label = dict(REPORT_FIELDS)["investigation"]
    doc.add_heading(inv_label.replace("\n", " "), level=2)

    doc.add_heading("Cây điều tra 4M", level=3)
    for branch in tree.branch_order:
        b_label = BRANCH_LABELS_VI.get(branch, branch)
        b_basis = tree.branch_basis.get(branch, "")
        b_title = f"{b_label} — {b_basis}" if b_basis else b_label
        doc.add_heading(b_title, level=4)
        for it in tree.branches.get(branch, []):
            star = " (ưu tiên)" if it.priority else ""
            doc.add_paragraph(f"{it.question}{star}", style="List Bullet")
            doc.add_paragraph(f"Thu thập: {it.data_to_collect}",
                              style="List Bullet 2")
            doc.add_paragraph(f"Căn cứ: {it.can_cu}",
                              style="List Bullet 2")

    doc.add_heading("Chuỗi Why-Why", level=3)
    for node in tree.why_chain:
        doc.add_paragraph(f"{node.question}", style="List Number")
        doc.add_paragraph(f"Gợi ý: {node.hint}")
        if node.can_cu:
            doc.add_paragraph(f"Căn cứ: {node.can_cu}")
        doc.add_paragraph("Trả lời: ___")

    doc.add_heading("Dữ liệu/hiện vật cần thu thập", level=3)
    seen = set()
    for it in tree.all_items():
        key = it.data_to_collect.strip()
        if key and key not in seen:
            seen.add(key)
            doc.add_paragraph(key, style="List Bullet")

    out = Path(path)
    if out.suffix.lower() != ".docx":
        out = out.with_suffix(".docx")
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    return out
