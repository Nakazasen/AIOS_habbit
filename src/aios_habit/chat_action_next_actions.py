"""Builtin chat action: suggest the next work for the active knowledge notebook.

Wires the previously standalone `daily_next_actions.suggest_next_actions` tool
(TOOL-1 inventory: 47 lines, not wired) into the chat through the `chat_action`
framework. Read-only: reads the local notebook/case stores, writes nothing.
"""

from __future__ import annotations

from typing import Optional

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    BLOCK_TABLE,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    register_action,
)

ACTION_NAME = "goi_y_viec_tiep_theo"
ACTION_TITLE = "Gợi ý việc nên làm tiếp"

_HINTS = (
    "gợi ý việc nên làm",
    "việc nên làm tiếp",
    "nên làm gì tiếp",
    "bước tiếp theo nên làm gì",
    "tiếp theo nên làm gì",
    "làm gì tiếp theo",
)


def _message(text: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=text),),
    )


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    from aios_habit.daily_next_actions import suggest_next_actions

    notebook_id = str(request.notebook_id or "").strip()
    if not notebook_id:
        return _message(
            "Chưa có sổ tri thức nào đang mở nên chưa gợi ý được. "
            "Hãy mở một sổ tri thức rồi hỏi lại."
        )
    workspace_id = str(request.workspace_id or notebook_id).strip()
    try:
        actions = [str(item).strip() for item in suggest_next_actions(workspace_id, notebook_id)]
        actions = [item for item in actions if item]
    except Exception:
        return _message(
            "Chưa đọc được trạng thái sổ tri thức lúc này. Bạn thử lại sau nhé."
        )
    if not actions:
        return _message("Sổ tri thức đang ở trạng thái ổn, chưa có việc gì bắt buộc làm tiếp.")
    title = str(request.context.get("notebook_title") or "").strip()
    caption = f"Sổ: {title}" if title else ""
    table = ChatActionBlock(
        BLOCK_TABLE,
        headers=("#", "Việc nên làm tiếp"),
        rows=[(str(index), item) for index, item in enumerate(actions, start=1)],
        caption=caption,
    )
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(
            ChatActionBlock(
                BLOCK_MARKDOWN,
                text="Gợi ý các việc nên làm tiếp cho sổ này:",
            ),
            table,
        ),
    )


def register() -> ChatAction:
    return register_action(
        ChatAction(
            name=ACTION_NAME,
            title=ACTION_TITLE,
            hints=_HINTS,
            handler=_handler,
            description="Gợi ý các bước tiếp theo cho sổ tri thức đang mở (nối tool daily_next_actions).",
        )
    )


register()
