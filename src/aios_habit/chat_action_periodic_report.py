"""Builtin chat action: Báo cáo xu hướng định kỳ theo tuần (DESKTOP-HOME-STEP4-PERIODIC-REPORT-ACCEPTANCE).

Cho phép người dùng trực tiếp yêu cầu sinh báo cáo xu hướng định kỳ từ thanh chat (Omnibar)
trên giao diện thật của ứng dụng:
- Bảng tỉ lệ phát sinh theo đủ 5 chiều: model / line / cong doan / loai giay / may cap thap.
- Cổng cảnh báo giữ nguyên chuẩn SMA(20) (chống báo ảo từ điểm đơn lẻ, chỉ báo khi có xu hướng liên tiếp >= 3 điểm).
- Xuất tệp Markdown chuẩn nghiệp vụ tại local_cases/bao_cao_xu_huong/ và biểu đồ SPC PNG nếu có.
- Trả về rich blocks trong bong bóng trả lời của trợ lý.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from aios_habit.chat_action import (
    BLOCK_CHART,
    BLOCK_MARKDOWN,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    normalize_text,
    register_action,
)
from aios_habit.production_prediction.periodic_trend_report import (
    KetQuaBaoCaoDinhKy,
    tao_bao_cao_dinh_ky_tuan,
)

ACTION_NAME = "bao_cao_xu_huong_dinh_ky"
TITLE = "Báo cáo xu hướng định kỳ (theo tuần)"

_HINTS = (
    "bao cao xu huong dinh ky",
    "sinh bao cao xu huong dinh ky",
    "xuat bao cao xu huong dinh ky",
    "tao bao cao xu huong dinh ky",
    "bao cao xu huong",
    "sinh bao cao xu huong",
    "xuat bao cao xu huong",
    "tao bao cao xu huong",
    "bao cao dinh ky tuan",
    "sinh bao cao dinh ky tuan",
    "xuat bao cao dinh ky tuan",
    "bao cao dinh ky",
    "sinh bao cao dinh ky",
    "xuat bao cao dinh ky",
)

_WEEK_ISO_RE = re.compile(r"\b(20\d\d-[wW]\d{2})\b")


def extract_target_week(question: str) -> Optional[str]:
    """Trích xuất tuần ISO (dạng YYYY-Www) từ câu hỏi nếu người dùng có chỉ định."""
    m = _WEEK_ISO_RE.search(question or "")
    if m:
        return m.group(1).upper()
    return None


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    target_week = extract_target_week(request.question)
    try:
        res: KetQuaBaoCaoDinhKy = tao_bao_cao_dinh_ky_tuan(ky_tuan=target_week)
    except Exception as exc:
        err_msg = f"⚠️ Không thể sinh báo cáo xu hướng định kỳ: {exc}"
        return ChatActionOutcome(
            action=ACTION_NAME,
            title=TITLE,
            blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=err_msg),),
        )

    blocks = [
        ChatActionBlock(
            BLOCK_MARKDOWN,
            text=res.bao_cao_markdown,
        )
    ]

    # Đính kèm ảnh biểu đồ SPC nếu có
    if res.duong_dan_bieu_do:
        for chart_path_str in res.duong_dan_bieu_do:
            p = Path(chart_path_str)
            if p.is_file():
                try:
                    img_bytes = p.read_bytes()
                    blocks.append(
                        ChatActionBlock(
                            BLOCK_CHART,
                            image_png=img_bytes,
                            caption=f"Biểu đồ SPC: {p.stem}",
                            alt=p.stem,
                        )
                    )
                except Exception:
                    pass

    return ChatActionOutcome(
        action=ACTION_NAME,
        title=TITLE,
        blocks=tuple(blocks),
    )


def register() -> None:
    register_action(
        ChatAction(
            name=ACTION_NAME,
            title=TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Báo cáo xu hướng định kỳ theo tuần từ kho log LSU/JIG: "
                "bảng tỉ lệ 5 chiều (model/line/công đoạn/loại giấy/máy cấp thấp), "
                "cổng cảnh báo SMA(20) W=20 k=1.5, biểu đồ xu hướng và đối chiếu số đếm tay."
            ),
        )
    )


register()
