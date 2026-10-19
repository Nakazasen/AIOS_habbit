"""Chat Action: Thu tri thức chuyên gia (DESKTOP-KNOWLEDGE-INTAKE-ENGINE-HOME).

Tích hợp vào app chat máy nhà qua khung `chat_action`:
1. Mở phiên thu tri thức mới:
   - Tự động nhận diện Chế độ: PHỎNG VẤN (AI dẫn hỏi 4M + Why-Why) hoặc DẠY (AI học, chuyên gia giảng).
   - Nhận diện Kho đích (mặc định Kho LSU, sẵn sàng mở rộng kho khác qua hồ sơ đích).
   - Khởi tạo phiên, lưu vào staging store và nhúng marker `aios_intake_session` để render widget tương tác.
2. Bề mặt xem lại & Vòng lặp cải thiện 3 điểm:
   - Xem danh sách các mục CHỜ NẠP (`CHO_NAP`) theo từng kho đích.
   - Báo cáo tỉ lệ duyệt, độ đủ khuôn và số phiên theo kho/chế độ.

Tương thích Python 3.11: không dùng f-string nhiều dòng (PEP 701), không type statement.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    normalize_text,
    register_action,
)
from aios_habit.chat_intake_ui import (
    intake_session_marker,
    register_live_session,
)
from aios_habit.intake_metrics import format_review_surface_markdown
from aios_habit.intake_staging import IntakeStagingStore
from aios_habit.intake_target_profiles import (
    STORE_ID_DIEU_TRA_LOI,
    STORE_ID_LSU,
    get_target_profile,
    list_target_profiles,
)
from aios_habit.knowledge_intake_engine import (
    MODE_DAY,
    MODE_PHONG_VAN,
    KnowledgeIntakeEngine,
)

ACTION_NAME = "thu_tri_thuc_chuyen_gia"
ACTION_TITLE = "Thu tri thức chuyên gia"

_HINTS = (
    "thu tri thuc",
    "phong van tri thuc",
    "day kien thuc",
    "mo phien thu tri thuc",
    "bat dau thu tri thuc",
    "xem muc cho nap",
    "xem cac muc cho nap",
    "muc cho nap",
    "danh sach cho nap",
    "thong ke thu tri thuc",
    "kiem tra muc cho nap",
    "phien day kien thuc",
    "phien phong van tri thuc",
)


def _message(text: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=text),),
    )


def _parse_store_id(norm_text: str) -> str:
    """Xác định kho đích từ câu hỏi."""
    if "kho lsu" in norm_text or "lsu" in norm_text:
        return STORE_ID_LSU
    # Các kho trong tương lai
    if "dieu tra" in norm_text:
        return STORE_ID_DIEU_TRA_LOI
    if "mom" in norm_text or "opcenter" in norm_text:
        return "kho_mom"
    if "tong hop" in norm_text:
        return "kho_tong_hop"
    return STORE_ID_LSU


def _parse_mode(norm_text: str) -> str:
    """Xác định chế độ: Dạy hoặc Phỏng vấn."""
    if any(k in norm_text for k in ("day kien thuc", "chuyen gia day", "che do day", "nguoi day", "giang bai")):
        return MODE_DAY
    return MODE_PHONG_VAN


def _parse_expert_name(raw_text: str, norm_text: str) -> str:
    """Trích xuất tên chuyên gia hoặc người dạy từ câu lệnh."""
    match = re.search(
        r"(?:chuyên gia|chuyen gia|người dạy|nguoi day|kỹ sư|ky su)\s+([^,\.\n]+?)(?=\s+(?:về|ve|kho|chủ đề|chu de)\b|$)",
        raw_text,
        re.IGNORECASE,
    )
    if match:
        name = match.group(1).strip()
        if len(name) >= 2 and not name.lower().startswith("kho"):
            return name
    return "chưa xác nhận"


def _parse_topic(raw_text: str, norm_text: str) -> str:
    """Trích xuất chủ đề hoặc mã lỗi của phiên."""
    # Tìm mã lỗi (ví dụ C7620)
    match_code = re.search(r"\b([CFJcfj]\s*-?\d{3,4}|JAM\s*-?\d{3,4})\b", raw_text)
    if match_code:
        return "Lỗi %s" % match_code.group(1).upper()
    # Tìm sau từ khóa 'về' hoặc 'chủ đề'
    match_topic = re.search(
        r"(?:về|ve|chủ đề|chu de)\s+([^,\.\n]+?)(?=\s+(?:chuyên gia|chuyen gia|người dạy|nguoi day|kỹ sư|ky su|kho)\b|$)",
        raw_text,
        re.IGNORECASE,
    )
    if match_topic:
        return match_topic.group(1).strip()
    return "Kinh nghiệm vận hành và điều tra lỗi"


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    norm = request.normalized_question
    raw = request.question

    # Nhánh 1: Bề mặt xem lại & thống kê metric (Vòng lặp cải thiện 3 điểm)
    if any(
        k in norm
        for k in (
            "xem muc cho nap",
            "xem cac muc cho nap",
            "muc cho nap",
            "danh sach cho nap",
            "thong ke thu tri thuc",
            "kiem tra muc cho nap",
        )
    ):
        store_id = _parse_store_id(norm)
        staging = IntakeStagingStore()
        md = format_review_surface_markdown(store_id=store_id, staging_store=staging)
        return _message(md)

    # Nhánh 2: Mở phiên thu tri thức mới
    store_id = _parse_store_id(norm)
    profile = get_target_profile(store_id)
    if profile is None:
        return _message(
            "Chưa tìm thấy Hồ sơ đích cho kho “%s”. Hiện tại hệ thống đang hỗ trợ hồ sơ mẫu: **Kho LSU**."
            % store_id
        )

    mode = _parse_mode(norm)
    expert_name = _parse_expert_name(raw, norm)
    topic = _parse_topic(raw, norm)

    staging = IntakeStagingStore()
    engine = KnowledgeIntakeEngine(staging_store=staging)

    try:
        session = engine.start_session(
            store_id=store_id,
            mode=mode,
            topic=topic,
            expert_name=expert_name,
        )
    except Exception as exc:
        return _message("Chưa mở được phiên thu tri thức: %s" % exc)

    # Đăng ký session vào live store trong memory
    register_live_session(session)

    mode_label = "CHẾ ĐỘ DẠY (Chuyên gia giảng, AI học & làm rõ)" if mode == MODE_DAY else "CHẾ ĐỘ PHỎNG VẤN (AI dẫn hỏi 4M + Why-Why)"
    first_turn = session.turns[0]

    lines = [
        "### 🎙️ Khởi động Phiên thu tri thức chuyên gia — %s" % session.session_id,
        "",
        "- **Hồ sơ đích:** %s (`%s`)" % (profile.display_name, profile.store_id),
        "- **Chế độ:** **%s**" % mode_label,
        "- **Chủ đề:** %s" % topic,
        "- **Người tham gia:** %s" % expert_name,
        "- **Đường nạp đích:** `%s` (sẽ do adapter nạp sau này xử lý)" % profile.ingest_route,
        "",
        "---",
        "#### ❓ Câu hỏi đầu tiên:",
        "**%s**" % first_turn.question_text,
        "",
        "> *Nhập câu trả lời ngay dưới đây. Khi hoàn thành, hệ thống sẽ tự động tổng hợp nháp theo đúng khuôn của hồ sơ đích và mở vòng duyệt tại chỗ.*",
        "",
        intake_session_marker(session.session_id, session.store_id),
    ]

    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text="\n".join(lines)),),
    )


def register() -> ChatAction:
    return register_action(
        ChatAction(
            name=ACTION_NAME,
            title=ACTION_TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Thu tri thức chuyên gia cho mọi kho qua hồ sơ đích: chế độ phỏng vấn (4M + Why-Why) "
                "hoặc chế độ dạy (AI đóng vai người học), tổng hợp nháp trích nguyên văn và duyệt tại chỗ (CHO_NAP)."
            ),
        )
    )


register()
