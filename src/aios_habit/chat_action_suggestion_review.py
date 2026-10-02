"""Chat action: xem bao cao cai thien goi y (vong lap UX-INTERVIEW-FEEDBACK).

Hoi "xem bao cao cai thien goi y" / "goi y bi che" -> hien metric + danh sach
goi y can nan lai theo cham cua chuyen gia (chi doc, khong vao kho tri thuc).
"""

from __future__ import annotations

from typing import Optional

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    register_action,
)

ACTION_NAME = "bao_cao_cai_thien_goi_y"
ACTION_TITLE = "Báo cáo cải thiện gợi ý"

_HINTS = (
    "báo cáo cải thiện gợi ý",
    "gợi ý bị chê",
    "xem lại gợi ý sai",
    "thống kê gợi ý",
)


def _message(text: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=text),),
    )


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    from aios_habit import suggestion_feedback

    report = suggestion_feedback.improvement_report(limit=10)
    stats = report["stats"]
    lines = [
        "## Vòng cải thiện gợi ý",
        "",
        f"- Tổng lượt chấm: **{stats['total']}**",
        f"- Tỉ lệ gợi ý đúng: **{stats['ti_le_dung'] * 100:.1f}%** "
        f"(đúng {stats['dung']}, một phần {stats['mot_phan']}, sai {stats['sai']})",
        "",
    ]
    if stats["top_ly_do_sai"]:
        lines.append("**Lý do bị chê nhiều nhất:**")
        for item in stats["top_ly_do_sai"][:5]:
            lines.append(f"- {item['ly_do']} ({item['so_lan']} lần)")
        lines.append("")
    items = report["can_nan_lai"]
    if not items:
        lines.append("Chưa có gợi ý nào bị chê cần nắn lại. Vòng lặp đang sạch.")
    else:
        lines.append(f"**{report['so_muc_can_xem_lai']} gợi ý cần nắn lại (mới nhất trước):**")
        for item in items:
            lines.append("")
            verdict = "sai" if item["verdict"] == "sai" else "đúng một phần"
            lines.append(f"- **{item['suggestion_id']}** — chuyên gia chấm *{verdict}*:")
            if item["goi_y_goc"]:
                lines.append(f"  - Gợi ý gốc: {item['goi_y_goc']}")
            lines.append(f"  - Lý do: {item['ly_do']}")
            lines.append(f"  - Nguyên nhân thật: {item['nguyen_nhan_that']}")
            lines.append(f"  - Nắn lại: {item['noi_dung_nan_lai']}")
    lines.append("")
    lines.append(
        "_Ghi chú: đây là dữ liệu vận hành cho vòng cải thiện, "
        "không phải tri thức đã duyệt._"
    )
    return _message("\n".join(lines))


def register() -> ChatAction:
    return register_action(
        ChatAction(
            name=ACTION_NAME,
            title=ACTION_TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Xem báo cáo vòng cải thiện gợi ý: metric chấm của chuyên gia "
                "và danh sách gợi ý cần nắn lại (chỉ đọc)."
            ),
        )
    )


register()
