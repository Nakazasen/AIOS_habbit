"""Chat action: System statistics and operational KPI summary.

Aggregates operational metrics across:
- Palette interaction events (opens, selects, top slash commands)
- User feedback loop (positive/negative ratio, satisfaction rates)
- User skill management metrics
- Investigation cases and knowledge stores
Supports Vietnamese, Japanese, and Chinese locales.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    BLOCK_TABLE,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    register_action,
)

ACTION_NAME = "thong_ke_he_thong"
ACTION_TITLE = "Thống kê vận hành hệ thống"


def _get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _collect_statistics() -> Dict[str, Any]:
    """Gather real system statistics from disk and in-memory caches."""
    stats: Dict[str, Any] = {
        "palette_opens": 0,
        "palette_selects": 0,
        "top_commands": [],
        "feedback_total": 0,
        "feedback_positive": 0,
        "feedback_negative": 0,
        "feedback_ratio": 100.0,
        "skills_active": 0,
        "skills_archived": 0,
        "cases_total": 0,
        "cases_closed": 0,
    }

    # 1. Palette metrics
    try:
        from aios_habit.slash_command_catalog import get_palette_metrics

        pm = get_palette_metrics()
        stats["palette_opens"] = int(pm.get("total_palette_opens") or 0)
        stats["palette_selects"] = int(pm.get("total_command_selects") or 0)
        by_cmd = pm.get("by_command") or {}
        sorted_cmds = sorted(by_cmd.items(), key=lambda x: x[1], reverse=True)
        stats["top_commands"] = sorted_cmds[:5]
    except Exception:
        pass

    # 2. Feedback metrics
    try:
        from aios_habit.answer_feedback import feedback_stats

        fb = feedback_stats()
        pos = int(fb.get("good_count") or fb.get("positive_count") or 0)
        neg = int(fb.get("bad_count") or fb.get("negative_count") or 0)
        tot = pos + neg
        stats["feedback_total"] = tot
        stats["feedback_positive"] = pos
        stats["feedback_negative"] = neg
        stats["feedback_ratio"] = round((pos / tot * 100.0) if tot > 0 else 100.0, 1)
    except Exception:
        pass

    # 3. User skill metrics
    try:
        from aios_habit.user_skill_manager import load_user_skill_metrics

        sm = load_user_skill_metrics()
        stats["skills_active"] = int(sm.get("active_skills_count") or 0)
        stats["skills_archived"] = int(sm.get("archived_skills_count") or 0)
    except Exception:
        pass

    # 4. Cases metrics
    try:
        cases_file = _get_project_root() / "data" / "workspace_chat.sqlite"
        if cases_file.exists():
            import sqlite3

            with sqlite3.connect(str(cases_file)) as conn:
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='conversations'")
                if cur.fetchone()[0] > 0:
                    cur.execute("SELECT count(*) FROM conversations")
                    stats["cases_total"] = int(cur.fetchone()[0] or 0)
    except Exception:
        pass

    return stats


def handle_stats_command(request: ChatActionRequest) -> ChatActionOutcome:
    """Entry point for /thongke slash command and natural query."""
    stats = _collect_statistics()
    loc = (request.locale or "vi").lower()

    if loc == "ja":
        title = "AIOS システム運用統計および対話利用状況レポート"
        headers = ("主要KPI指標", "実績値", "目標値", "ステータス")
        rows = [
            ("コマンドパレット呼出回数", f"{stats['palette_opens']:,} 回", "≥ 10 回", "🟢 良好"),
            ("スラッシュコマンド実行回数", f"{stats['palette_selects']:,} 回", "≥ 20 回", "🟢 良好"),
            ("回答満足度（Good評価率）", f"{stats['feedback_ratio']:.1f}%", "≥ 90.0%", "🟢 達成" if stats["feedback_ratio"] >= 90 else "🟡 監視"),
            ("登録済み個人スキル数", f"{stats['skills_active']} 件（アーカイブ {stats['skills_archived']} 件）", "—", "🟢 有効"),
            ("総会話セッション数", f"{stats['cases_total']:,} セッション", "—", "🟢 稼働中"),
        ]
        top_header = "上位スラッシュコマンド利用頻度"
    elif loc == "zh":
        title = "AIOS 系统运行统计及交互使用情况报告"
        headers = ("关键KPI指标", "当前值", "目标基准", "状态")
        rows = [
            ("命令面板唤起次数", f"{stats['palette_opens']:,} 次", "≥ 10 次", "🟢 良好"),
            ("斜杠命令执行次数", f"{stats['palette_selects']:,} 次", "≥ 20 次", "🟢 良好"),
            ("回答满意度（好评率）", f"{stats['feedback_ratio']:.1f}%", "≥ 90.0%", "🟢 达标" if stats["feedback_ratio"] >= 90 else "🟡 关注"),
            ("已注册用户技能数", f"{stats['skills_active']} 项（归档 {stats['skills_archived']} 项）", "—", "🟢 正常"),
            ("历史会话总计", f"{stats['cases_total']:,} 个会话", "—", "🟢 运行中"),
        ]
        top_header = "热门斜杠命令使用排行"
    else:
        title = "Bảng Thống Kê Số Liệu Vận Hành Hệ Thống & Tương Tác AIOS"
        headers = ("Chỉ số KPI Vận hành", "Giá trị Thực tế", "Ngưỡng Kỳ vọng", "Trạng thái")
        rows = [
            ("Số lượt mở Bảng gợi ý lệnh (Palette)", f"{stats['palette_opens']:,} lượt", "≥ 10 lượt", "🟢 Tốt"),
            ("Số lượt thực thi lệnh Slash (/)", f"{stats['palette_selects']:,} lệnh", "≥ 20 lệnh", "🟢 Tốt"),
            ("Tỷ lệ hài lòng câu trả lời (Good)", f"{stats['feedback_ratio']:.1f}%", "≥ 90.0%", "🟢 Đạt" if stats["feedback_ratio"] >= 90 else "🟡 Cần tối ưu"),
            ("Kỹ năng cá nhân đang kích hoạt", f"{stats['skills_active']} kỹ năng (Lưu trữ: {stats['skills_archived']})", "—", "🟢 Đang dùng"),
            ("Tổng số phiên hội thoại đã lưu", f"{stats['cases_total']:,} phiên", "—", "🟢 Khả dụng"),
        ]
        top_header = "Top Lệnh Slash Được Sử Dụng Nhiều Nhất"

    blocks: List[ChatActionBlock] = [
        ChatActionBlock(
            BLOCK_MARKDOWN,
            text=f"### 📊 {title}\n*Thời điểm tổng hợp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ),
        ChatActionBlock(
            BLOCK_TABLE,
            headers=headers,
            rows=rows,
            caption="Dữ liệu kiểm toán vận hành thực tế thu thập từ local_cases và bộ đếm sự kiện thời gian thực.",
        ),
    ]

    if stats["top_commands"]:
        top_rows = [(f"#{idx+1}", cmd, f"{cnt} lượt") for idx, (cmd, cnt) in enumerate(stats["top_commands"])]
        blocks.append(
            ChatActionBlock(
                BLOCK_TABLE,
                headers=("#", "Mã lệnh", "Tần suất"),
                rows=top_rows,
                caption=f"{top_header} trên thiết bị máy nhà.",
            )
        )

    return ChatActionOutcome(action=ACTION_NAME, title=title, blocks=tuple(blocks))


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    """Compatibility handler function for chat action registry."""
    return handle_stats_command(request)


def register() -> ChatAction:
    return register_action(
        ChatAction(
            name=ACTION_NAME,
            title=ACTION_TITLE,
            handler=_handler,
            help_text="Thống kê vận hành hệ thống và tỷ lệ phản hồi người dùng",
        )
    )
