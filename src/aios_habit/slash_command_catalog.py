"""Danh mục lệnh hệ thống dùng chung (Single Source of Truth) - DESKTOP-HOME-SLASH-COMMAND-PALETTE.

Cung cấp danh mục duy nhất cho mọi lệnh slash (/) trong AIOS:
- Bảng gợi ý khi gõ "/" trong ô chat (workspace_chat_app.py) đọc từ đây.
- Mục danh mục lệnh trong cẩm nang (huongdan_command.py & HUONG-DAN-SU-DUNG-AIOS*.md) đọc từ đây.
- Định tuyến ý định (chat_intent_router.py) đồng bộ chặt chẽ với danh mục này.
- Ghi nhận sự kiện bảng gợi ý (mở, chọn lệnh) vào local_cases/palette_events.jsonl và palette_metrics.json.
"""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def _get_project_root() -> Path:
    """Trả về thư mục gốc của repo AIOS_habbit."""
    return Path(__file__).resolve().parent.parent.parent


def _get_local_cases_dir() -> Path:
    """Trả về thư mục local_cases để lưu metrics và logs cục bộ."""
    env_dir = os.environ.get("AIOS_LOCAL_CASES_DIR")
    if env_dir and Path(env_dir).is_dir():
        return Path(env_dir)
    p = _get_project_root() / "local_cases"
    p.mkdir(parents=True, exist_ok=True)
    return p


# BẢNG DANH MỤC LỆNH CHUẨN (NGUỒN SỰ THẬT DUY NHẤT)
# Mỗi bản ghi đại diện cho một lệnh slash hệ thống đang sống trong AIOS.
_SLASH_COMMANDS_CATALOG: Tuple[Dict[str, Any], ...] = (
    {
        "command": "/huongdan",
        "aliases": ["/huong-dan", "/guide", "/help", "/使い方", "/使用指南"],
        "category": "Hướng dẫn sử dụng",
        "category_ja": "利用ガイド",
        "category_zh": "使用指南",
        "description": "Mở cẩm nang hướng dẫn sử dụng AIOS (hỗ trợ 3 ngôn ngữ Việt/Nhật/Trung)",
        "description_ja": "AIOS台帳利用マニュアルを開く（日・越・中3言語対応）",
        "description_zh": "打开 AIOS 台账使用指南（支持越/中/日三语）",
        "natural_query": "hướng dẫn sử dụng aios",
        "natural_query_ja": "使い方",
        "natural_query_zh": "使用指南",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "huong_dan",
    },
    {
        "command": "/baocaodinhky",
        "aliases": ["/baocaoxuhuong"],
        "category": "Báo cáo & Xu hướng",
        "category_ja": "レポート・トレンド",
        "category_zh": "报告与趋势",
        "description": "Xuất báo cáo xu hướng định kỳ tình hình lỗi theo dây chuyền và tuần sản xuất",
        "description_ja": "生産ライン別および週別の障害トレンド定期レポートを出力（ステップ4）",
        "description_zh": "导出按产线和周期的故障趋势定期报告（第4步）",
        "natural_query": "báo cáo xu hướng định kỳ",
        "natural_query_ja": "定期トレンドレポート",
        "natural_query_zh": "定期趋势报告",
        "context_required": "Bất kỳ sổ nào",
        "context_required_ja": "すべてのノート",
        "context_required_zh": "任意台账",
        "intent": "bao_cao_xu_huong",
    },
    {
        "command": "/autoclassify",
        "aliases": ["/phanloai", "/autoclassify-feedback", "/autoclassify-review"],
        "category": "Phân loại Bước 5",
        "category_ja": "ステップ5自動分類",
        "category_zh": "第5步自动分类",
        "description": "Xem tổng hợp thống kê và đánh giá nhãn phân loại tự động sự cố Bước 5",
        "description_ja": "ステップ5の障害自動分類ラベルの統計および評価サマリーを表示",
        "description_zh": "查看第5步故障自动分类标签的统计数据与评价汇总",
        "natural_query": "xem phản hồi phân loại",
        "natural_query_ja": "分類フィードバック確認",
        "natural_query_zh": "查看分类反馈",
        "context_required": "Bất kỳ sổ nào (đọc từ local_cases)",
        "context_required_ja": "すべてのノート（local_casesから読込）",
        "context_required_zh": "任意台账（从 local_cases 读取）",
        "intent": "xem_phan_hoi",
    },
    {
        "command": "/investigation",
        "aliases": ["/investigation-feedback", "/investigation-review"],
        "category": "Điều tra sự cố",
        "category_ja": "障害調査業務",
        "category_zh": "故障调查业务",
        "description": "Xem tổng hợp đánh giá và góp ý cây điều tra sự cố 4M Bước 3",
        "description_ja": "ステップ3の4M障害調査ツリーに対する評価・フィードバックサマリーを表示",
        "description_zh": "查看第3步 4M 故障调查分析树的评价与反馈统计汇总",
        "natural_query": "xem phản hồi điều tra",
        "natural_query_ja": "調査フィードバック確認",
        "natural_query_zh": "查看调查反馈",
        "context_required": "Bất kỳ sổ nào (đọc từ local_cases)",
        "context_required_ja": "すべてのノート（local_casesから読込）",
        "context_required_zh": "任意台账（从 local_cases 读取）",
        "intent": "xem_phan_hoi",
    },
    {
        "command": "/danhgiadieutra",
        "aliases": [],
        "category": "Điều tra sự cố",
        "category_ja": "障害調査業務",
        "category_zh": "故障调查业务",
        "description": "Đánh giá nhanh gợi ý cây điều tra 4M (đúng hướng, thiếu nhánh, không hữu ích)",
        "description_ja": "4M調査ツリーの提案を迅速に評価（方向性良好、枝不足、有用でない）",
        "description_zh": "快速评价 4M 调查树建议（方向正确、缺少分支、不实用）",
        "natural_query": "cây điều tra đúng hướng",
        "natural_query_ja": "調査ツリー方向性良好",
        "natural_query_zh": "调查树方向正确",
        "context_required": "Sổ Điều tra lỗi (ngữ cảnh ca điều tra đang mở)",
        "context_required_ja": "障害調査ノート（進行中の調査ケース文脈）",
        "context_required_zh": "故障调查台账（正在进行的调查案例上下文）",
        "intent": "danh_gia_dieu_tra",
    },
    {
        "command": "/danhgianhan",
        "aliases": [],
        "category": "Phân loại Bước 5",
        "category_ja": "ステップ5自動分類",
        "category_zh": "第5步自动分类",
        "description": "Đánh giá độ chính xác của nhãn phân loại tự động Bước 5 (đúng nhãn, sai, một phần)",
        "description_ja": "ステップ5の自動分類ラベルの正確性を評価（正確、誤り、一部）",
        "description_zh": "评价第5步自动分类标签的准确性（正确、错误、部分符合）",
        "natural_query": "đánh giá đúng nhãn",
        "natural_query_ja": "ラベル正確性評価",
        "natural_query_zh": "评价正确标签",
        "context_required": "Sổ Điều tra lỗi (ngữ cảnh phân loại sự cố)",
        "context_required_ja": "障害調査ノート（分類中のケース文脈）",
        "context_required_zh": "故障调查台账（分类中的案例上下文）",
        "intent": "danh_gia_nhan",
    },
    {
        "command": "/close-case",
        "aliases": ["/closecase", "/dong-vu", "/dongvu"],
        "category": "Đóng vụ điều tra",
        "category_ja": "ケース終了",
        "category_zh": "关闭案例",
        "description": "Đóng vụ điều tra sự cố kèm bắt buộc ghi nhận nguyên nhân thật và biện pháp khắc phục",
        "description_ja": "根本原因と対策の必須記録ゲートを経て障害調査ケースをクローズ（ステップ2）",
        "description_zh": "关闭故障调查案例，执行根本原因与纠正措施的强制录入门禁（第2步）",
        "natural_query": "đóng vụ điều tra",
        "natural_query_ja": "障害ケース終了",
        "natural_query_zh": "关闭调查案例",
        "context_required": "Sổ Điều tra lỗi (yêu cầu mã vụ, nguyên nhân và đối sách)",
        "context_required_ja": "障害調査ノート（ケースID、原因、対策が必要）",
        "context_required_zh": "故障调查台账（需提供案例号、原因及对策）",
        "intent": "dong_vu",
    },
    {
        "command": "/feedback",
        "aliases": ["/phanhoi", "/xemphanhoi"],
        "category": "Phản hồi hệ thống",
        "category_ja": "システム評価",
        "category_zh": "系统反馈",
        "description": "Xem tổng hợp thống kê tỷ lệ hài lòng (đạt/chê) và lý do phản hồi đáp án AI",
        "description_ja": "ローカルAI回答に対する満足度（Good/Bad比率）および理由の統計サマリーを表示",
        "description_zh": "查看本地 AI 答复的满意度统计（点赞/点踩比例）及理由汇总",
        "natural_query": "xem phản hồi",
        "natural_query_ja": "回答フィードバック確認",
        "natural_query_zh": "查看回答反馈",
        "context_required": "Bất kỳ sổ nào (đọc từ local_cases)",
        "context_required_ja": "すべてのノート（local_casesから読込）",
        "context_required_zh": "任意台账（从 local_cases 读取）",
        "intent": "xem_phan_hoi",
    },
)


def get_command_catalog() -> List[Dict[str, Any]]:
    """Trả về toàn bộ danh mục lệnh slash hệ thống."""
    return [dict(item) for item in _SLASH_COMMANDS_CATALOG]


def get_all_alive_slash_commands() -> Set[str]:
    """Trả về tập hợp toàn bộ các chuỗi lệnh slash đang sống (bao gồm cả lệnh chính và biến thể)."""
    cmds: Set[str] = set()
    for item in _SLASH_COMMANDS_CATALOG:
        cmds.add(item["command"])
        for alias in item.get("aliases", []):
            cmds.add(alias)
    return cmds


def generate_manual_commands_markdown(lang: str = "vi") -> str:
    """Sinh nội dung bảng markdown cẩm nang danh mục lệnh theo ngôn ngữ chuẩn."""
    norm_lang = (lang or "vi").strip().lower()

    if norm_lang == "ja":
        lines = [
            "## 9. システムコマンド一覧（スラッシュコマンド）",
            "",
            "チャット入力欄で `/` を入力すると、システムコマンドの候補パレットがポップアップ表示されます。",
            "また、同等の自然言語文を通常どおり入力しても、AIOS は自動的に意図を認識して該当機能を実行します。",
            "",
            "| 主要コマンド & エイリアス | 同等の自然言語文 | 機能・用途 | 必要なコンテキスト | 機能グループ |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for item in _SLASH_COMMANDS_CATALOG:
            aliases_str = ", ".join(f"`{a}`" for a in item["aliases"]) if item["aliases"] else "（なし）"
            cmd_display = f"**`{item['command']}`**<br>別名: {aliases_str}"
            nat_display = f"`{item['natural_query_ja']}`<br>*(越: `{item['natural_query']}`)*"
            desc = item["description_ja"]
            ctx = item["context_required_ja"]
            cat = item["category_ja"]
            lines.append(f"| {cmd_display} | {nat_display} | {desc} | {ctx} | **{cat}** |")
        lines.append("")
        lines.append("*ヒント: チャット枠で `/` を入力して ↑↓ キーで選択し、Enter を押すとコマンドが入力欄に挿入されます。送信ボタンを押すと実行されます。*")
        return "\n".join(lines)

    elif norm_lang == "zh":
        lines = [
            "## 9. 系统命令目录（斜杠命令 Slash Commands）",
            "",
            "在聊天输入框中输入 `/` 时，系统将弹出浮动命令建议面板。",
            "用户亦可直接输入等效的自然语言语句，AIOS 将自动识别意图并运行对应功能。",
            "",
            "| 主要命令与变体 | 等效自然语言语句 | 功能用途 | 适用上下文 | 功能分组 |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for item in _SLASH_COMMANDS_CATALOG:
            aliases_str = ", ".join(f"`{a}`" for a in item["aliases"]) if item["aliases"] else "（无）"
            cmd_display = f"**`{item['command']}`**<br>变体: {aliases_str}"
            nat_display = f"`{item['natural_query_zh']}`<br>*(越: `{item['natural_query']}`)*"
            desc = item["description_zh"]
            ctx = item["context_required_zh"]
            cat = item["category_zh"]
            lines.append(f"| {cmd_display} | {nat_display} | {desc} | {ctx} | **{cat}** |")
        lines.append("")
        lines.append("*提示: 在聊天框中输入 `/` 并使用 ↑↓ 键选择，按 Enter 即可将命令插入输入框，点击发送按钮即可执行。*")
        return "\n".join(lines)

    else:
        lines = [
            "## 9. DANH MỤC LỆNH HỆ THỐNG (SLASH COMMANDS)",
            "",
            "Khi gõ `/` ở đầu ô soạn câu hỏi, hệ thống sẽ tự động hiển thị bảng gợi ý lệnh kèm mô tả và câu tự nhiên tương đương.",
            "Người dùng cũng có thể gõ câu nói tự nhiên thông thường, AIOS sẽ tự động nhận diện ý định và kích hoạt tính năng tương ứng.",
            "",
            "| Lệnh chính & Biến thể | Câu tự nhiên tương đương | Công dụng chức năng | Ngữ cảnh cần thiết | Nhóm tính năng |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for item in _SLASH_COMMANDS_CATALOG:
            aliases_str = ", ".join(f"`{a}`" for a in item["aliases"]) if item["aliases"] else "*(không)*"
            cmd_display = f"**`{item['command']}`**<br>Biến thể: {aliases_str}"
            nat_display = f"`{item['natural_query']}`"
            desc = item["description"]
            ctx = item["context_required"]
            cat = item["category"]
            lines.append(f"| {cmd_display} | {nat_display} | {desc} | {ctx} | **{cat}** |")
        lines.append("")
        lines.append("*Mẹo: Gõ `/` trong ô chat, dùng phím ↑/↓ để di chuyển, Enter để chèn lệnh vào ô soạn thảo, sau đó bấm Gửi để thực thi.*")
        return "\n".join(lines)


def record_palette_event(
    action: str,  # "open" | "select"
    command: str = "",
    query: str = "",
    conversation_id: str = "",
) -> None:
    """Ghi nhận sự kiện bảng gợi ý lệnh vào local_cases (Vòng lặp cải thiện liên tục)."""
    try:
        lc_dir = _get_local_cases_dir()
        events_file = lc_dir / "palette_events.jsonl"
        metrics_file = lc_dir / "palette_metrics.json"

        now_iso = datetime.datetime.now().astimezone().isoformat()
        evt = {
            "timestamp": now_iso,
            "action": str(action or "unknown").strip().lower(),
            "command": str(command or "").strip(),
            "query": str(query or "").strip(),
            "conversation_id": str(conversation_id or "").strip(),
        }

        with open(events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(evt, ensure_ascii=False) + "\n")

        # Cập nhật số liệu tích lũy
        metrics = {
            "total_palette_opens": 0,
            "total_command_selects": 0,
            "by_command": {},
            "by_action": {},
            "last_event_at": now_iso,
        }
        if metrics_file.is_file():
            try:
                metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        act = evt["action"]
        act_dict = metrics.setdefault("by_action", {})
        act_dict[act] = act_dict.get(act, 0) + 1

        if act == "open":
            metrics["total_palette_opens"] = metrics.get("total_palette_opens", 0) + 1
        elif act == "select":
            metrics["total_command_selects"] = metrics.get("total_command_selects", 0) + 1
            cmd = evt["command"]
            if cmd:
                cmd_dict = metrics.setdefault("by_command", {})
                cmd_dict[cmd] = cmd_dict.get(cmd, 0) + 1

        metrics["last_event_at"] = now_iso
        metrics_file.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_palette_metrics() -> Dict[str, Any]:
    """Đọc dữ liệu thống kê sự kiện bảng gợi ý từ local_cases."""
    metrics_file = _get_local_cases_dir() / "palette_metrics.json"
    if metrics_file.is_file():
        try:
            return json.loads(metrics_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "total_palette_opens": 0,
        "total_command_selects": 0,
        "by_command": {},
        "by_action": {},
    }
