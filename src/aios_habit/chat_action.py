"""Framework `chat_action`: tools register actions, the chat calls them by question context.

Design (TOOL-2, extended by UX-CHAT-CORE for multi-intent):
- A tool registers one `ChatAction` (name, Vietnamese title, match hints, handler).
- On submit the Workspace Chat calls `handle_chat_text`: every registered action
  whose hint appears in the normalized question runs; their handlers each receive
  a `ChatActionRequest` (question + active notebook/workspace context) and return
  a `ChatActionOutcome` of rich blocks (markdown / GFM table / PNG chart).
- `dispatch_multi` merges the outcomes into one structured answer (one section per
  action) rendered by `render_outcome` into the assistant bubble; charts are
  embedded as base64 data URIs so they persist with the message (size capped).
- Actions marked `fallback=True` (generic catch-alls such as the bare-code error
  lookup) never piggyback on a specific action: when at least one non-fallback
  action matches, fallbacks are skipped.
- `match_action` / `dispatch` keep the legacy first-match behaviour for callers
  and tests that depend on registration priority.
- No extra UI controls: the single chat composer stays the only entry point.
  Fail-closed behind `AIOS_FEATURE_CHAT_ACTION` (default off).

Matching normalizes case, Vietnamese diacritics and whitespace, so hints are
written without diacritics and still match typed Vietnamese.
"""

from __future__ import annotations

import base64
import importlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

BLOCK_MARKDOWN = "markdown"
BLOCK_TABLE = "table"
BLOCK_CHART = "chart"
_BLOCK_KINDS = (BLOCK_MARKDOWN, BLOCK_TABLE, BLOCK_CHART)

# Keep persisted bubble markdown small: refuse to inline oversized charts.
CHART_MAX_BYTES = 400_000

# Action modules imported once by `load_builtin_actions` so they self-register.
BUILTIN_ACTION_MODULES: Tuple[str, ...] = (
    "aios_habit.chat_action_next_actions",
    "aios_habit.chat_action_answer_quality",
    "aios_habit.chat_action_expert_interview",
    "aios_habit.chat_action_prediction",
    "aios_habit.chat_action_visual_maps",
    "aios_habit.chat_action_case_form",
    # UX-CHAT-CORE: pasted log/CSV is analyzed + charted inline, no command needed.
    "aios_habit.chat_action_data_paste",
    # Report agent: "lap bao cao dieu tra cho ca <ma>" must outrank both the
    # Buoc 3 plan hints ("4m", ...) and the bare-code lookup fallback below.
    "aios_habit.chat_action_bao_cao_dieu_tra",
    # UX-AGENT-REPORT: tao/sua bao cao .docx/.pptx/.md bang loi trong chat.
    # Dang ky sau bao_cao_dieu_tra de lenh "bao cao dieu tra" ve dung action
    # chuyen biet (handler tu nhuong khi gap "dieu tra").
    "aios_habit.chat_action_agent_report",
    # B3: investigation-plan commands outrank the bare-code lookup fallback.
    "aios_habit.chat_action_dieu_tra",
    # B2: explicit feedback commands outrank the bare-code lookup fallback,
    # while tra_cuu_loi_tuong_tu stays last (lowest match priority).
    "aios_habit.chat_action_phan_hoi",
    # UX-INTERVIEW-FEEDBACK: vong lap cai thien goi y (bao cao cham cua chuyen gia).
    "aios_habit.chat_action_suggestion_review",
    # UX-INTERVIEW-FEEDBACK (UI): mo phien phong van chuyen gia ngay trong
    # khung chat (hoi tung cau, dap an thieu y bi nhac, xong luu nhap).
    "aios_habit.chat_action_interview_chat",
    # DESKTOP-KNOWLEDGE-INTAKE-ENGINE-HOME: bo may thu tri thuc chuyen gia cho moi kho
    "aios_habit.chat_action_knowledge_intake",
    # LOG-STREAM: nap file log lon theo stream, khong cat 50k dong.
    "aios_habit.chat_action_log_stream",
    # DESKTOP-HOME-STEP4-PERIODIC-REPORT-ACCEPTANCE: bao cao xu huong dinh ky theo tuan
    "aios_habit.chat_action_periodic_report",
    "aios_habit.chat_action_draft_approval",
    "aios_habit.chat_action_create_case",
    "aios_habit.chat_action_error_lookup",
)


def normalize_text(text: str) -> str:
    """Casefold, strip Vietnamese diacritics, collapse whitespace (for matching)."""
    decomposed = unicodedata.normalize("NFD", str(text or "").casefold())
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(without_marks.replace("đ", "d").split())


DOC_REF_RE = re.compile(
    r"\b(?:trong|theo|tai|xem\s+trong|trich\s+tu|tham\s+khao)\s+(?:email|tai\s+lieu|file|tep|van\s+ban|bao\s+cao|bien\s+ban|quy\s+trinh|tieu\s+chuan|huong\s+dan|so\s+tay|bang|sheet)\b|"
    r"\b[\w\-\.À-ỹ\(\) ]+\.(?:msg|pdf|docx|pptx|xlsx|csv|txt|doc|xls)\b|"
    r"\b(?:fw|fwd|re)\s*[:\s]|\b週報\b",
    re.IGNORECASE,
)

QUESTION_MARK_RE = re.compile(r"[\?？]")

INTERROGATIVE_RE = re.compile(
    r"\b(?:la\s+ai|ai\s+la|ai\s+da|ai\s+gui|ai\s+nhan|ai\s+lam|thuoc\s+ai|do\s+ai|cho\s+ai|ve\s+ai|cua\s+ai|ai\s+phu\s+trach|duoc\s+ai|ai)\b|"
    r"\b(?:la\s+gi|cai\s+gi|la\s+sao)\b|"
    r"\b(?:nhu\s+the\s+nao|the\s+nao|ra\s+sao|tai\s+sao|vi\s+sao|lam\s+sao)\b|"
    r"\b(?:o\s+dau|cho\s+nao|noi\s+nao|dau\s+ra)\b|"
    r"\b(?:khi\s+nao|bao\s+gio|ngay\s+nao|nam\s+nao|thang\s+nao|thoi\s+gian\s+nao|luc\s+nao)\b|"
    r"\bbao\s+nhieu\b|"
    r"\b(?:co\s+[^?.!:\n]{1,60}\s+khong\s*[\?？]|co\s+(?:phai|the|biet|ai|can|duoc|chac)\s+[^?.!:\n]{1,60}\s+khong\b|khong\s*[\?？]|phai\s+khong\??|dung\s+khong\??|chua\s*[\?？])\b|"
    r"\b(?:bo\s+phan|phong\s+ban|don\s+vi|cong\s+doan|chuyen|line|model|loi|tai\s+lieu|file|tep|bao\s+cao|muc|khoan|dieu|trang|dong|buoc|phan|loai)\s+nao\b|"
    r"\bnao\s*[\?？]",
    re.IGNORECASE,
)

SYSTEM_WORKFLOW_HINTS = (
    "tiep theo nen lam gi",
    "buoc tiep theo nen lam gi",
    "goi y viec nen lam",
    "viec nen lam tiep",
    "nen lam gi tiep",
    "lam gi tiep theo",
)

COMMAND_ACTION_START_RE = re.compile(
    # Periodic trend report (Step 4)
    r"^(?:bao\s+cao\s+xu\s+huong|sinh\s+bao\s+cao\s+xu\s+huong|bao\s+cao\s+dinh\s+ky|xuat\s+bao\s+cao\s+xu\s+huong|sinh\s+bao\s+cao\s+dinh\s+ky)\b|" \
    # Case form (Step 0)
    r"^(?:nhap\s+bao\s+cao|form\s+nhap|nhap\s+ca\s+loi|them\s+ca\s+loi|mau\s+bao\s+cao|phieu\s+bao\s+cao|bao\s+cao\s+loi\s+moi)\b|"
    # Knowledge intake / clipboard
    r"^(?:mo\s+phien\s+thu\s+tri\s+thuc|thu\s+tri\s+thuc|nap\s+tri\s+thuc|dan\s+tri\s+thuc|nhap\s+tri\s+thuc|xem\s+muc\s+cho\s+nap)\b|"
    # Step 3 Investigation Plan (4M + Why-Why) & Cases
    r"^(?:huong\s+dieu\s+tra|cay\s+dieu\s+tra|ke\s+hoach\s+dieu\s+tra|lap\s+ke\s+hoach\s+dieu\s+tra|lap\s+cay\s+dieu\s+tra|goi\s+y\s+huong\s+dieu\s+tra|bat\s+dau\s+dieu\s+tra|dieu\s+tra\s+buoc\s+dau|tao\s+vu\s+dieu\s+tra|mo\s+vu\s+dieu\s+tra|dieu\s+tra\s+loi)\b|"
    # Feedback
    r"^(?:xem\s+phan\s+hoi|gui\s+phan\s+hoi|y\s+kien\s+phan\s+hoi)\b|"
    # Expert interview
    r"^(?:phong\s+van\s+chuyen\s+gia|bat\s+dau\s+phong\s+van)\b|"
    # Agent report create/edit: supports tao/sua/chinh/cap nhat/thay/them vao slide/bao cao or specific file extension
    r"^(?:tao|lap|viet|sua|chinh|cap\s+nhat|thay|them\s+vao|bo\s+sung|xoa)\s+(?:bao\s+cao|slide|trinh\s+chieu|[\w\-\.À-ỹ\(\) ]+\.(?:docx|pptx|md|txt))\b|"
    r"^(?:them\s+slide|them\s+vao\s+slide)\b",
    re.IGNORECASE,
)

SOURCE_DOC_INQUIRY_RE = re.compile(
    r"\b(?:trong|theo|tai|xem\s+trong|trich\s+tu|tham\s+khao)\s+(?:email|tai\s+lieu|file|tep|van\s+ban|bao\s+cao|bien\s+ban|quy\s+trinh|tieu\s+chuan|huong\s+dan|so\s+tay|bang|sheet)\b|"
    r"\b(?:fw|fwd|re)\s*[:\s]|\b週報\b|\.msg\b",
    re.IGNORECASE,
)

POLITE_PREFIXES = (
    "hay ",
    "vui long ",
    "cho toi ",
    "chay ",
    "xin ",
    "giup toi ",
    "lam on ",
    "nho ban ",
)


def strip_command_prefix(norm_text: str) -> str:
    t = norm_text.strip()
    for prefix in POLITE_PREFIXES:
        if t.startswith(prefix):
            t = t[len(prefix) :].strip()
            break
    return t


def is_document_lookup_query(text: str) -> bool:
    """Xác định liệu câu chat có phải là câu hỏi tra cứu tài liệu (RAG query) hay không.

    Quy tắc cách ly định tuyến (DESKTOP-ROUTER-INTENT-KEYWORD-ISOLATION-HOME):
    - Câu hỏi tra cứu tài liệu thông thường có chứa các từ khóa hành động
      (vd 'gửi báo cáo', 'báo cáo tuần', 'tạo báo cáo', 'thu tri thức')
      PHẢI đi đường RAG như câu hỏi thường, không bao giờ bị chat_action chặn.
    """
    raw = str(text or "").strip()
    norm = normalize_text(raw)

    # 1. Nộp form đã điền (có >= 3 trường nhãn hoặc bắt đầu bằng 'nộp báo cáo')
    try:
        from aios_habit.error_cases.case_form import looks_like_filled_form

        if looks_like_filled_form(raw) or norm.startswith(("nop bao cao", "gui bao cao:")):
            return False
    except Exception:
        pass

    # 2. Câu hỏi quy trình hệ thống (vd: 'tiếp theo nên làm gì') do goi_y_viec_tiep_theo xử lý
    if any(h in norm for h in SYSTEM_WORKFLOW_HINTS):
        return False

    # 3. Lệnh thao tác thật trong ứng dụng (tạo case, mở phiên nạp, tạo/sửa báo cáo, xem phản hồi...)
    clean_norm = strip_command_prefix(norm)
    has_qmark = bool(QUESTION_MARK_RE.search(raw))
    has_interrogative = bool(INTERROGATIVE_RE.search(norm))
    has_source_inquiry = bool(SOURCE_DOC_INQUIRY_RE.search(raw))

    if COMMAND_ACTION_START_RE.match(clean_norm):
        if not has_qmark and not has_interrogative and not has_source_inquiry:
            return False

    # 4. Dẫn nguồn tài liệu (tệp, email .msg, .pdf, 'trong email', 'theo tài liệu'...)
    has_doc_ref = bool(DOC_REF_RE.search(raw))

    if has_doc_ref or has_qmark or has_interrogative or has_source_inquiry:
        return True

    return False


@dataclass(frozen=True)
class ChatActionRequest:
    """Context the chat passes to every action: question + active workspace state."""

    question: str
    locale: str = "vi"
    conversation_id: str = ""
    notebook_id: str = ""
    workspace_id: str = ""
    context: Mapping[str, Any] = field(default_factory=dict)

    @property
    def normalized_question(self) -> str:
        return normalize_text(self.question)


@dataclass(frozen=True)
class ChatActionBlock:
    """One rich render block of an action result.

    Kinds:
    - `markdown`: plain markdown text (`text`).
    - `table`: GFM table (`headers`, `rows`, optional `caption`).
    - `chart`: PNG bytes (`image_png`), rendered as markdown data URI image.
    """

    kind: str
    text: str = ""
    headers: Sequence[str] = ()
    rows: Sequence[Sequence[str]] = ()
    caption: str = ""
    image_png: bytes = b""
    alt: str = ""

    def __post_init__(self) -> None:
        if self.kind not in _BLOCK_KINDS:
            raise ValueError(f"unknown chat action block kind: {self.kind!r}")
        if self.kind == BLOCK_TABLE:
            object.__setattr__(self, "headers", tuple(str(h) for h in self.headers))
            object.__setattr__(
                self, "rows", tuple(tuple(str(c) for c in row) for row in self.rows)
            )
            if not self.headers:
                raise ValueError("table block requires at least one header")
        if self.kind == BLOCK_CHART:
            object.__setattr__(self, "image_png", bytes(self.image_png or b""))


@dataclass(frozen=True)
class ChatActionOutcome:
    """Result of one action, ready to render into the answer area."""

    action: str
    title: str
    blocks: Sequence[ChatActionBlock] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "blocks", tuple(self.blocks))


ChatActionHandler = Callable[[ChatActionRequest], Optional[ChatActionOutcome]]


@dataclass(frozen=True)
class ChatAction:
    """A registered tool action: hints match the question, handler builds the result."""

    name: str
    title: str
    hints: Sequence[str]
    handler: ChatActionHandler
    description: str = ""
    fallback: bool = False

    def __post_init__(self) -> None:
        if not str(self.name or "").strip():
            raise ValueError("chat action requires a name")
        if not str(self.title or "").strip():
            raise ValueError(f"chat action {self.name!r} requires a title")
        normalized_hints = tuple(
            hint for hint in (normalize_text(h) for h in self.hints) if hint
        )
        if not normalized_hints:
            raise ValueError(f"chat action {self.name!r} requires at least one hint")
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "hints", normalized_hints)

    def matches(self, request: ChatActionRequest) -> bool:
        if is_document_lookup_query(request.question):
            if self.name == "goi_y_viec_tiep_theo" and any(
                hint in request.normalized_question for hint in self.hints
            ):
                return True
            return False
        normalized = request.normalized_question
        return any(hint in normalized for hint in self.hints)


# Registration order is match priority (first hit wins).
_REGISTRY: dict[str, ChatAction] = {}
_builtin_loaded = False


def register_action(action: ChatAction) -> ChatAction:
    """Register an action (same name replaces the previous one, keeping its slot)."""
    _REGISTRY[action.name] = action
    return action


def unregister_action(name: str) -> None:
    _REGISTRY.pop(name, None)


def registered_actions() -> Tuple[ChatAction, ...]:
    non_fallback = [a for a in _REGISTRY.values() if not a.fallback]
    fallback = [a for a in _REGISTRY.values() if a.fallback]
    return tuple(non_fallback + fallback)


def reset_actions() -> None:
    """Test hook: clear the registry and re-arm builtin action loading."""
    global _builtin_loaded
    _REGISTRY.clear()
    _builtin_loaded = False


def load_builtin_actions() -> None:
    """Import builtin action modules once so they register themselves.

    Also calls each module's `register()` explicitly: after `reset_actions`
    the module is already cached in `sys.modules`, so import side effects
    alone would not re-register the action.
    """
    global _builtin_loaded
    if _builtin_loaded:
        return
    for module_name in BUILTIN_ACTION_MODULES:
        module = importlib.import_module(module_name)
        register = getattr(module, "register", None)
        if callable(register):
            register()
    _builtin_loaded = True


def match_action(request: ChatActionRequest) -> Optional[ChatAction]:
    for action in registered_actions():
        if action.matches(request):
            return action
    return None


def match_all_actions(request: ChatActionRequest) -> Tuple[ChatAction, ...]:
    """Return every registered action whose hints match, in priority order.

    Unlike `match_action`, this does not stop at the first hit: one chat
    message may carry several intents ("paste this log, draw a chart and set
    a threshold") and each matching action gets to run.
    """
    return tuple(action for action in registered_actions() if action.matches(request))


def _merge_outcomes(
    matched: Sequence[Tuple[ChatAction, ChatActionOutcome]],
) -> ChatActionOutcome:
    """Merge several action outcomes into one structured answer.

    Each action becomes its own section headed by its title, so the single
    assistant bubble carries every requested result without extra UI.
    """
    blocks: list[ChatActionBlock] = []
    for action, outcome in matched:
        title = outcome.title.strip() or action.title.strip()
        blocks.append(ChatActionBlock(kind=BLOCK_MARKDOWN, text=f"### {title}"))
        blocks.extend(outcome.blocks)
    return ChatActionOutcome(
        action="+".join(action.name for action, _ in matched),
        title=f"Đã xử lý {len(matched)} việc trong một câu trả lời",
        blocks=tuple(blocks),
    )


def dispatch_multi(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    """Match every intent in the question and run all matching handlers.

    A failing handler only drops its own section; the remaining actions still
    answer, and no raw traceback ever reaches the chat. Returns `None` when
    nothing matches (or every handler failed), so the chat keeps its normal
    answer flow.
    """
    try:
        load_builtin_actions()
        matched = [action for action in registered_actions() if action.matches(request)]
        if not matched:
            return None
        # Generic fallbacks must not piggyback on a specific action's answer.
        specific = [action for action in matched if not action.fallback]
        actions = specific or matched
        done: list[Tuple[ChatAction, ChatActionOutcome]] = []
        for action in actions:
            try:
                outcome = action.handler(request)
            except Exception:
                outcome = None
            if outcome is not None:
                done.append((action, outcome))
        if not done:
            return None
        if len(done) == 1:
            return done[0][1]
        return _merge_outcomes(done)
    except Exception:
        return None


def dispatch(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    """Match the question and run the first matching handler.

    Any failure (builtin import, handler error) falls back to `None` so the
    chat keeps its normal answer flow instead of leaking a raw traceback.
    """
    try:
        load_builtin_actions()
        action = match_action(request)
        if action is None:
            return None
        return action.handler(request)
    except Exception:
        return None


def _table_cell(value: Any) -> str:
    text = str(value if value is not None else "").replace("\r", " ").replace("\n", " ")
    return text.replace("|", "\\|").strip()


def _render_table(block: ChatActionBlock) -> str:
    lines = [
        "| " + " | ".join(_table_cell(h) for h in block.headers) + " |",
        "| " + " | ".join("---" for _ in block.headers) + " |",
    ]
    for row in block.rows:
        cells = list(row)[: len(block.headers)]
        cells += [""] * (len(block.headers) - len(cells))
        lines.append("| " + " | ".join(_table_cell(c) for c in cells) + " |")
    rendered = "\n".join(lines)
    if block.caption.strip():
        rendered += f"\n\n*{block.caption.strip()}*"
    return rendered


def _render_chart(block: ChatActionBlock) -> str:
    caption = block.caption.strip()
    if not block.image_png:
        return f"*{caption}*" if caption else ""
    if len(block.image_png) > CHART_MAX_BYTES:
        note = f"*{caption}*" if caption else "*Biểu đồ*"
        return note + "\n\n*(Ảnh biểu đồ quá lớn để nhúng vào chat.)*"
    encoded = base64.b64encode(block.image_png).decode("ascii")
    alt = block.alt.strip() or caption or "biểu đồ"
    rendered = f"![{alt}](data:image/png;base64,{encoded})"
    if caption:
        rendered += f"\n\n*{caption}*"
    return rendered


def _render_block(block: ChatActionBlock) -> str:
    if block.kind == BLOCK_MARKDOWN:
        return block.text.strip()
    if block.kind == BLOCK_TABLE:
        return _render_table(block)
    return _render_chart(block)


def render_outcome(outcome: ChatActionOutcome) -> str:
    """Render an outcome to markdown for the assistant bubble (answer area)."""
    parts = []
    if outcome.title.strip():
        parts.append(f"**{outcome.title.strip()}**")
    for block in outcome.blocks:
        rendered = _render_block(block)
        if rendered:
            parts.append(rendered)
    return "\n\n".join(parts)


def handle_chat_text(
    question: str,
    *,
    conversation_id: str = "",
    notebook_id: str = "",
    workspace_id: str = "",
    locale: str = "vi",
    context: Optional[Mapping[str, Any]] = None,
    save_user: Optional[Callable[[str], Any]] = None,
    save_assistant: Optional[Callable[[str], Any]] = None,
) -> bool:
    """Chat entry point: dispatch the question, save both messages, report handled."""
    clean = str(question or "").strip()
    if not clean:
        return False
    outcome = dispatch_multi(
        ChatActionRequest(
            question=clean,
            locale=locale,
            conversation_id=conversation_id,
            notebook_id=notebook_id,
            workspace_id=workspace_id,
            context=dict(context or {}),
        )
    )
    if outcome is None:
        return False
    if save_user is not None:
        save_user(clean)
    if save_assistant is not None:
        save_assistant(render_outcome(outcome))
    return True


def chat_action_enabled() -> bool:
    """Feature flag check for the app hook (fail-closed, default off)."""
    from aios_habit.feature_flags import FEATURE_CHAT_ACTION, is_feature_enabled

    return is_feature_enabled(FEATURE_CHAT_ACTION)
