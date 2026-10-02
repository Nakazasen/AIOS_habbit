"""Chat action: nap file log lon theo stream (khong cat 50k dong).

Cau hoi kieu: "nạp file log D:\\logs\\jig.csv" / "đọc file log './a.log'".
Khong tim thay duong dan -> hoi lai user chi ro duong dan file.
"""

from __future__ import annotations

import re
from typing import Optional

from aios_habit.chat_action import (
    BLOCK_MARKDOWN,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    register_action,
)

ACTION_NAME = "nap_file_log"
ACTION_TITLE = "Nạp file log theo stream"

_HINTS = (
    "nạp file log",
    "đọc file log",
    "stream log",
    "nạp log từ file",
)

_DUONG_DAN_RE = re.compile(
    r'"([^"]+)"|\'([^\']+)\'|([A-Za-z]:\\\\[^\\s]+|/[^\s]+|\./[^\s]+|[A-Za-z]:\\[^\\s]+)'
)


def _tach_duong_dan(cau_hoi: str) -> Optional[str]:
    tran = _DUONG_DAN_RE.search(cau_hoi or "")
    if not tran:
        return None
    return next((nhom for nhom in tran.groups() if nhom), None)


def _message(text: str) -> ChatActionOutcome:
    return ChatActionOutcome(
        action=ACTION_NAME,
        title=ACTION_TITLE,
        blocks=(ChatActionBlock(BLOCK_MARKDOWN, text=text),),
    )


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    from aios_habit.production_prediction.log_stream_ingest import nap_file_log

    duong_dan = _tach_duong_dan(request.question)
    if not duong_dan:
        return _message(
            "Bạn muốn nạp file log nào? Cho mình đường dẫn file nhé, ví dụ:\n"
            "`nạp file log \"D:\\logs\\jig-01.csv\"`"
        )
    tien_trinh_cuoi: dict = {}
    for cap_nhat in nap_file_log(duong_dan):
        tien_trinh_cuoi = cap_nhat
    if not tien_trinh_cuoi.get("ok", True):
        return _message(f"Không nạp được file: {tien_trinh_cuoi.get('error_vi', '')}")
    dong = [
        f"## Đã nạp file log: `{duong_dan}`",
        "",
        f"- Định dạng nhận diện: **{tien_trinh_cuoi.get('dinh_dang', 'lạ')}**",
        f"- Đã đọc: **{tien_trinh_cuoi.get('da_doc', 0):,}** dòng",
        f"- Đã lưu: **{tien_trinh_cuoi.get('da_ghi', 0):,}** giá trị theo "
        f"{tien_trinh_cuoi.get('dot', 1)} đợt (không cắt bỏ)",
    ]
    if tien_trinh_cuoi.get("bo_qua_rong"):
        dong.append(f"- Bỏ qua dòng trống: {tien_trinh_cuoi['bo_qua_rong']:,}")
    if tien_trinh_cuoi.get("tiep_tuc_tu_dong"):
        dong.append(
            f"- Tiếp tục từ lần trước (dòng {tien_trinh_cuoi['tiep_tuc_tu_dong']:,})."
        )
    dong += [
        "",
        "_File lớn được nạp theo từng đợt, có checkpoint để nạp dở thì chạy tiếp._",
    ]
    return _message("\n".join(dong))


def register() -> ChatAction:
    return register_action(
        ChatAction(
            name=ACTION_NAME,
            title=ACTION_TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Nạp file log lớn theo stream (không cắt 50k dòng), "
                "tự nhận diện định dạng, có resume."
            ),
        )
    )


register()
