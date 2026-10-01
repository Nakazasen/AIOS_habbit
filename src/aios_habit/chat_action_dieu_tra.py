"""Builtin chat action: gợi ý hướng điều tra (B3).

The user describes an error phenomenon in the single chat box; the action
builds a 4M + Why-Why investigation tree (see
``aios_habit.error_cases.investigation_tree``) and renders it inside the
answer bubble: what to confirm per 4M branch, the Why-Why chain and the
data/artifact collection checklist. Markdown and Word files in the company
KTD report layout are saved under ``local_runs/dieu_tra/`` so the plan can
be pasted straight into the investigation report.

Read-only with respect to data stores: nothing is written to any DB or
index. Fail-closed: any problem (including python-docx missing for the
.docx file) still returns the markdown plan in chat; only a total failure
returns None so the chat keeps its normal RAG answer flow.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    normalize_text,
    register_action,
)
from aios_habit.error_cases.column_map import extract_code_from_text
from aios_habit.error_cases.investigation_tree import (
    BRANCH_LABELS_VI,
    export_report,
    build_tree,
)

ACTION_NAME = "goi_y_huong_dieu_tra"
TITLE = "Gợi ý hướng điều tra"

_HINTS = (
    "huong dieu tra",
    "cay dieu tra",
    "ke hoach dieu tra",
    "lap ke hoach dieu tra",
    "4m",
    "why-why",
    "why why",
    "5 why",
    "nam why",
    "dieu tra loi nay",
    "bat dau dieu tra",
    "dieu tra buoc dau",
)

# Trigger phrases stripped to recover the phenomenon from the question.
# Matching runs on a diacritic-folded copy; the returned phenomenon keeps
# the original text (diacritics intact) via an index map, so keyword
# matching in the tree generator still sees "kẹt", "mã lỗi", ...
_TRIGGER_RE = re.compile(
    r"^(?:(?:cho|hay|giup|xin)\s+(?:toi|em|anh|chi|minh)\s+)?"
    r"(?:lap|len|tao|viet|goi\s*y)?\s*"
    r"(?:huong|cay|ke\s*hoach)?\s*"
    r"dieu\s*tra\s*(?:4m|why[\s-]*why|5\s*why)?\s*"
    r"(?:cho|:)?\s*"
    r"(?:(?:voi\s+)?hien\s*tuong\s*:?)?\s*"
)


def _fold_with_map(text: str):
    """Diacritic-fold ``text`` char by char, returning (folded, index_map)
    where index_map[out_pos] is the source position in ``text``."""
    out_chars: List[str] = []
    index_map: List[int] = []
    for i, ch in enumerate(text):
        if ch in "đĐ":
            # U+0111 has no NFKD decomposition; fold explicitly.
            base = "d"
        else:
            decomp = unicodedata.normalize("NFKD", ch)
            base = "".join(c for c in decomp if not unicodedata.combining(c))
        for b in base.casefold():
            out_chars.append(b)
            index_map.append(i)
    return "".join(out_chars), index_map


def extract_phenomenon(question: str) -> str:
    """Recover the phenomenon text from a chat question.

    Trigger phrases ("gợi ý hướng điều tra cho ...", "lập cây điều tra
    4M: ...") are stripped on a diacritic-folded copy; the remainder is
    sliced from the ORIGINAL text so diacritics survive. Returns ""
    when nothing usable remains.
    """
    text = (question or "").strip().strip("\"'“”‘’")
    if not text:
        return ""
    folded, index_map = _fold_with_map(text)
    m = _TRIGGER_RE.match(folded)
    if m and m.end() > 0:
        cut = index_map[m.end() - 1] + 1  # first original char past the trigger
        remainder = text[cut:]
    else:
        remainder = text
    remainder = re.sub(r"\s+", " ", remainder).strip(" :,-–—")
    return remainder

_EXPORT_DIRNAME = "dieu_tra"
_MAX_SLUG = 40


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode(
        "ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:_MAX_SLUG] or "dieu-tra"


def _local_runs_dir() -> Path:
    # <repo>/src/aios_habit/chat_action_dieu_tra.py -> parents[2] == <repo>
    root = Path(__file__).resolve().parents[2]
    out = root / "local_runs" / _EXPORT_DIRNAME
    out.mkdir(parents=True, exist_ok=True)
    return out


def _render_chat(tree) -> str:
    L: List[str] = []
    L.append(f"## {TITLE}")
    L.append("")
    L.append(f"**Hiện tượng:** {tree.phenomenon}")
    if tree.code:
        name = f" — {tree.code_name}" if tree.code_name else ""
        code_line = f"{tree.code_family} {tree.code}".strip()
        L.append(f"**Mã lỗi:** {code_line}{name}")
    L.append("")
    L.append("### Cây điều tra 4M")
    L.append("")
    for branch in tree.branch_order:
        label = BRANCH_LABELS_VI.get(branch, branch)
        L.append(f"**{label}**")
        L.append("")
        for it in tree.branches.get(branch, []):
            star = " ⭐" if it.priority else ""
            L.append(f"- [ ] {it.question}{star}")
            L.append(f"  - *Thu thập:* {it.data_to_collect}")
        L.append("")
    L.append("### Chuỗi Why-Why")
    L.append("")
    for node in tree.why_chain:
        L.append(f"{node.level}. {node.question}")
        L.append(f"   - *Gợi ý:* {node.hint}")
    L.append("")
    L.append("Điền câu trả lời từng bước khi điều tra; tick [ ] khi xong hạng mục.")
    return "\n".join(L)


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    try:
        phenomenon = extract_phenomenon(request.question)
        if not phenomenon:
            return ChatActionOutcome(
                action=ACTION_NAME,
                title=TITLE,
                blocks=(
                    ChatActionBlock(
                        kind=BLOCK_MARKDOWN,
                        text=("Mô tả hiện tượng lỗi cần điều tra cho tôi "
                              "(ví dụ: *LCD báo C4001 khi in tờ White thử*), "
                              "tôi sẽ gợi ý cây điều tra 4M + chuỗi Why-Why "
                              "kèm danh sách dữ liệu/hiện vật cần thu thập."),
                    ),
                ),
            )
        code = extract_code_from_text(phenomenon) or ""
        tree = build_tree(phenomenon, code=code)
        text = _render_chat(tree)

        # Save company-format files (md + docx) for pasting into the report.
        saved: List[str] = []
        try:
            outdir = _local_runs_dir()
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            base = outdir / f"{stamp}-{_slug(phenomenon)}"
            meta = {"date": datetime.now().strftime("%Y-%m-%d")}
            for suffix in (".md", ".docx"):
                try:
                    p = export_report(tree, base.with_suffix(suffix), meta)
                    saved.append(str(p))
                except Exception:
                    continue  # one format failing must not kill the other
        except Exception:
            pass
        if saved:
            text += ("\n\n---\n**File kế hoạch (đúng mẫu báo cáo công ty):**\n"
                     + "\n".join(f"- `{p}`" for p in saved))
        else:
            text += ("\n\n---\n_Không lưu được file (thiếu python-docx hoặc lỗi "
                     "ghi đĩa) — kế hoạch vẫn đầy đủ ở trên._")
        return ChatActionOutcome(
            action=ACTION_NAME,
            title=TITLE,
            blocks=(ChatActionBlock(kind=BLOCK_MARKDOWN, text=text),),
        )
    except Exception:
        return None


def register() -> None:
    register_action(
        ChatAction(
            name=ACTION_NAME,
            title=TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Gợi ý hướng điều tra: nhập hiện tượng lỗi, nhận cây điều tra "
                "4M (Con người/Máy móc/Vật liệu/Phương pháp) + chuỗi Why-Why "
                "kèm hạng mục cần xác nhận và dữ liệu/hiện vật cần thu thập; "
                "xuất file đúng mẫu báo cáo điều tra công ty."
            ),
        )
    )


register()
