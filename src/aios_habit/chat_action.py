"""Framework `chat_action`: tools register actions, the chat calls them by question context.

Design (TOOL-2):
- A tool registers one `ChatAction` (name, Vietnamese title, match hints, handler).
- On submit the Workspace Chat calls `handle_chat_text`: the first registered action
  whose hint appears in the normalized question wins; its handler receives a
  `ChatActionRequest` (question + active notebook/workspace context) and returns a
  `ChatActionOutcome` of rich blocks (markdown / GFM table / PNG chart).
- `render_outcome` turns the outcome into assistant bubble markdown; charts are
  embedded as base64 data URIs so they persist with the message (size capped).
- No extra UI controls: the single chat composer stays the only entry point.
  Fail-closed behind `AIOS_FEATURE_CHAT_ACTION` (default off).

Matching normalizes case, Vietnamese diacritics and whitespace, so hints are
written without diacritics and still match typed Vietnamese.
"""

from __future__ import annotations

import base64
import importlib
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
)


def normalize_text(text: str) -> str:
    """Casefold, strip Vietnamese diacritics, collapse whitespace (for matching)."""
    decomposed = unicodedata.normalize("NFD", str(text or "").casefold())
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(without_marks.replace("đ", "d").split())


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
    return tuple(_REGISTRY.values())


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
    outcome = dispatch(
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
