"""Step 3: investigation-tree generator (4M + Why-Why) for error cases.

Input: an error phenomenon (+ optional error code) -> a 4M investigation
tree (Man / Machine / Material / Method) plus a 5-Why chain, each item
carrying what to confirm and what data/artifacts to collect.
Output: an investigation checklist rendered as Markdown, exportable to a
file that can be pasted into a report. Target user: a newcomer (G3 and
below) running the first investigation step alone.

Glossary integration: when a (family, code) pair is given and a glossary
connection is available, the matching entry's name/cause/remedy seeds
branch emphasis and hint text. Everything else comes from generic,
manufacturing-standard 4M templates, so the generator works with no
glossary at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    """One investigation step: what to confirm + what to collect."""
    branch: str
    question: str
    data_to_collect: str
    priority: bool = False


@dataclass
class WhyNode:
    """One level of the 5-Why chain. `answer` is left blank for the
    investigator to fill in during the investigation."""
    level: int
    question: str
    hint: str
    answer: str = ""


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

    def all_items(self) -> List[ChecklistItem]:
        return [it for b in self.branch_order for it in self.branches.get(b, [])]


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _match_keyword_items(phenomenon: str) -> List[ChecklistItem]:
    lowered = phenomenon.lower()
    items: List[ChecklistItem] = []
    for keywords, branch, question, data in KEYWORD_ITEMS:
        if any(k in lowered for k in keywords):
            items.append(ChecklistItem(branch=branch, question=question,
                                      data_to_collect=data, priority=True))
    return items


def _branch_order(code_family: str) -> List[str]:
    hinted = FAMILY_BRANCH_HINTS.get(code_family or "")
    if hinted:
        return list(hinted)
    return list(BRANCHES)


def build_tree(
    phenomenon: str,
    *,
    code: str = "",
    code_family: str = "",
    conn=None,
) -> InvestigationTree:
    """Build a 4M + Why-Why investigation tree for a phenomenon.

    When `code`/`code_family` match a glossary entry (via `conn`), the
    entry's name/cause/remedy seed branch emphasis and hint text.
    """
    phenomenon = (phenomenon or "").strip()
    if not phenomenon:
        raise ValueError("phenomenon must not be empty")

    tree = InvestigationTree(
        phenomenon=phenomenon,
        code=code.strip(),
        code_family=(code_family or "").strip().upper(),
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
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
    keyword_items = _match_keyword_items(phenomenon)

    for branch in order:
        items = [
            ChecklistItem(branch=branch, question=q, data_to_collect=d)
            for q, d in TEMPLATES_4M[branch]
        ]
        # Targeted keyword items go first within their branch.
        for kw in keyword_items:
            if kw.branch == branch:
                items.insert(0, kw)
        tree.branches[branch] = items

    # Mark the emphasized (first) branch's items as priority.
    if order:
        for it in tree.branches[order[0]]:
            it.priority = True

    tree.why_chain = build_why_chain(phenomenon, cause_hint=tree.code_cause)
    return tree


def build_why_chain(phenomenon: str, *, cause_hint: str = "") -> List[WhyNode]:
    """Build a 5-level Why-Why skeleton. Answers are left blank for the
    investigator; level 1 is seeded from the phenomenon (and the
    glossary cause hint when available)."""
    hints = [
        "Mô tả nguyên nhân trực tiếp quan sát được tại hiện trường."
        + (f" Gợi ý từ từ điển mã lỗi: {cause_hint}" if cause_hint else ""),
        "Tìm điều kiện hoặc tác nhân đã tạo ra nguyên nhân trực tiếp đó.",
        "Tìm nguyên nhân sâu hơn: vì sao điều kiện đó tồn tại?",
        "Tiếp tục đào sâu: quy trình/quản lý nào đã để lọt?",
        "Chốt nguyên nhân gốc (root cause): điểm mà nếu khắc phục thì chuỗi trên không tái diễn.",
    ]
    chain = [WhyNode(level=1,
                     question=f"Vì sao hiện tượng “{phenomenon}” xảy ra?",
                     hint=hints[0])]
    prev = "nguyên nhân vừa xác định ở bước trước"
    for i in range(2, 6):
        chain.append(WhyNode(
            level=i,
            question=f"Vì sao {prev} lại xảy ra?",
            hint=hints[i - 1],
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
    L.append("> Dữ liệu trong kế hoạch này do người điều tra thu thập và điền "
             "tay; không dán dữ liệu thật chưa phân loại vào đây.")
    L.append("")

    L.append("## 1. Cây điều tra 4M")
    L.append("")
    for branch in tree.branch_order:
        label = BRANCH_LABELS_VI.get(branch, branch)
        L.append(f"### {label}")
        L.append("")
        for it in tree.branches.get(branch, []):
            star = " ⭐" if it.priority else ""
            L.append(f"- [ ] {it.question}{star}")
            L.append(f"  - Dữ liệu/hiện vật cần thu thập: {it.data_to_collect}")
        L.append("")

    L.append("## 2. Chuỗi Why-Why (5 lần hỏi vì sao)")
    L.append("")
    for node in tree.why_chain:
        L.append(f"{node.level}. {node.question}")
        L.append(f"   - Gợi ý: {node.hint}")
        L.append(f"   - Trả lời: ___")
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
# reports shipped with the company data (e.g.
# "Lịch sử lỗi/C Call/KTD-2026-08-0872-Iris2024-C33-A1-C4001.xlsx"),
# in sheet order. The generated investigation plan goes into the
# "Investigation content and results" row so the exported file pastes
# straight into the company report form.

REPORT_TITLE = "Báo cáo điều tra lỗi/調査報告書"
REPORT_AUTHOR_LABEL = "Người Lập作成者："
REPORT_DATE_LABEL = "Ngày lập作成日："
REPORT_TABLE_HEAD = ("Item／項目", "Details／詳細")

#: (meta key, verbatim Item label) in report-sheet order.
REPORT_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("model", "Model/モデル"),
    ("item_code", "Item code - Rev／品番 - Rev"),
    ("item_name", "Item name／品名"),
    ("serial_lot", "S.No (Lot)／シリアル番号（ロット）"),
    ("supplier", "Supplier/サプライヤー"),
    ("machine_no", "Machine No.／仕上げ-マシンNo."),
    ("occurrence_date", "Occurrence Date／発生日"),
    ("defect_contents", "Contents of defect／不具合内容"),
    ("line", "Line／ライン"),
    ("quantity", "Quantity／数量"),
    ("status_at_line", "Status of occurrence at Line／ラインでの発生状況"),
    ("reappear_rate", "Reappear rate(%)／(Describe the reappear environment)"),
    ("investigation", "Investigation content and results／調査内容と結果"),
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
        L.append(f"[{label}]")
        for it in tree.branches.get(branch, []):
            star = " (ưu tiên)" if it.priority else ""
            L.append(f"  - {it.question}{star}")
            L.append(f"    Thu thập: {it.data_to_collect}")
    L.append("CHUỖI WHY-WHY")
    for node in tree.why_chain:
        L.append(f"  {node.level}. {node.question}")
        L.append(f"     Gợi ý: {node.hint}")
        L.append("     Trả lời: ___")
    L.append("DỮ LIỆU/HIỆN VẬT CẦN THU THẬP")
    seen = set()
    for it in tree.all_items():
        key = it.data_to_collect.strip()
        if key and key not in seen:
            seen.add(key)
            L.append(f"  - [ ] {key}")
    return "\n".join(L)


def render_report(tree: InvestigationTree,
                  meta: Optional[Dict[str, str]] = None) -> str:
    """Render the plan in the company KTD report layout (Markdown).

    Header (title + report id, author, date), the Item/Details table with
    the verbatim company field labels, then the 4M + Why-Why plan in the
    'Investigation content and results' row. Blank fields are left for
    the investigator to fill by hand.
    """
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
        cell = value.replace("\n", "<br>") if value else ""
        L.append(f"| {label} | {cell} |")
    L.append("")
    inv_label = dict(REPORT_FIELDS)["investigation"]
    L.append(f"## {inv_label}")
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


def export_docx(tree: InvestigationTree, path: str | Path,
                meta: Optional[Dict[str, str]] = None) -> Path:
    """Write the company-format report as a Word document.

    Layout mirrors the KTD "Bao cao dieu tra" sheet: title, author/date,
    an Item/Details table, then the 4M tree, the Why-Why chain and the
    data/artifact checklist. Requires the ``python-docx`` package.
    """
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError as exc:  # pragma: no cover - dependency declared
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
        row[0].text = label
        row[1].text = fields[key]

    inv_label = dict(REPORT_FIELDS)["investigation"]
    doc.add_heading(inv_label, level=2)

    doc.add_heading("Cây điều tra 4M", level=3)
    for branch in tree.branch_order:
        doc.add_heading(BRANCH_LABELS_VI.get(branch, branch), level=4)
        for it in tree.branches.get(branch, []):
            star = " (ưu tiên)" if it.priority else ""
            doc.add_paragraph(f"{it.question}{star}", style="List Bullet")
            doc.add_paragraph(f"Thu thập: {it.data_to_collect}",
                              style="List Bullet 2")

    doc.add_heading("Chuỗi Why-Why", level=3)
    for node in tree.why_chain:
        doc.add_paragraph(f"{node.question}", style="List Number")
        doc.add_paragraph(f"Gợi ý: {node.hint}")
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
