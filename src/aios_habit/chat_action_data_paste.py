"""Chat action: dan log/CSV vao o chat -> phan tich + ve bieu do ngay trong cau tra loi.

UX-CHAT-CORE, diem dau #1 cua user: truoc day dan log/CSV vao khong duoc
phan tich/ve bieu do ngay. Action nay tu nhan dien noi dung dang vao la
bang/log (khong can go lenh) hoac bat hint tieng Viet, roi tra ve tom tat +
bang so lieu + bieu do trong cung mot vung tra loi.

Nhan bieu do trung thuc: "Bieu do tu du lieu ban vua dan" (khong dung nhan
"MÔ PHỎNG" gay hieu nham).

Tuong thich Python 3.11.
"""

from __future__ import annotations

import csv
import io
import re
from typing import List, Optional, Sequence, Tuple

from aios_habit.chat_action import (
    BLOCK_CHART,
    BLOCK_MARKDOWN,
    BLOCK_TABLE,
    ChatAction,
    ChatActionBlock,
    ChatActionOutcome,
    ChatActionRequest,
    normalize_text,
    register_action,
)

ACTION_NAME = "phan_tich_du_lieu_dan"
TITLE = "Phân tích dữ liệu vừa dán"

_HINTS = (
    "ve bieu do",
    "phan tich log",
    "phan tich du lieu",
    "thong ke du lieu",
)

# Gioi han an toan: khong om ca file log khong lo vao chat.
MAX_TEXT_CHARS = 200_000
MAX_ROWS = 5000
MAX_CHART_SERIES = 3

_TIMESTAMP_RE = re.compile(r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\d{1,2}:\d{2}(:\d{2})?")


def _candidate_lines(question: str) -> List[str]:
    lines = [ln.strip() for ln in (question or "").splitlines()]
    return [ln for ln in lines if ln]


def _looks_like_csv(lines: Sequence[str]) -> bool:
    """Nhieu dong co cung so cot ngan cach boi , ; hoac tab."""
    if len(lines) < 2:
        return False
    for delimiter in (",", ";", "\t"):
        counts = [ln.count(delimiter) for ln in lines[:20]]
        if counts[0] >= 1 and all(c == counts[0] for c in counts[1:]):
            return True
    return False


def _looks_like_log(lines: Sequence[str]) -> bool:
    if len(lines) < 3:
        return False
    stamped = sum(1 for ln in lines[:20] if _TIMESTAMP_RE.search(ln))
    return stamped >= max(2, len(lines[:20]) // 3)


def extract_pasted_block(question: str) -> Optional[str]:
    """Tach khoi du lieu duoc dan ra khoi cau chat. None neu khong thay."""
    lines = _candidate_lines(question)
    if _looks_like_csv(lines) or _looks_like_log(lines):
        return "\n".join(lines)
    return None


def _parse_csv_block(block: str) -> Tuple[List[str], List[List[str]]]:
    sample = block[:10000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(block), dialect)
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return [], []
    headers = [h.strip() or f"cot_{i + 1}" for i, h in enumerate(rows[0])]
    data = [r[: len(headers)] for r in rows[1 : MAX_ROWS + 1]]
    return headers, data


def _is_number(text: str) -> bool:
    try:
        float(text.replace(",", "").strip())
        return True
    except (ValueError, AttributeError):
        return False


def _numeric_columns(headers: List[str], data: List[List[str]]) -> List[int]:
    numeric = []
    for col in range(len(headers)):
        values = [row[col] for row in data if col < len(row) and row[col].strip()]
        if not values:
            continue
        if sum(1 for v in values if _is_number(v)) >= max(1, int(len(values) * 0.7)):
            numeric.append(col)
    return numeric


def _to_float(text: str) -> Optional[float]:
    try:
        return float(text.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def _describe_numeric(values: List[float]) -> str:
    if not values:
        return "-"
    ordered = sorted(values)
    mean = sum(values) / len(values)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    return (
        "số dòng: "
        + str(len(values))
        + ", min: "
        + _fmt(min(values))
        + ", max: "
        + _fmt(max(values))
        + ", trung bình: "
        + _fmt(mean)
        + ", trung vị: "
        + _fmt(median)
    )


def _fmt(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}"


def _draw_line_chart(
    headers: List[str], data: List[List[str]], numeric_cols: List[int]
) -> bytes:
    """Ve bieu do duong cho toi da 3 cot so. Tra ve PNG bytes (rong neu ve hong)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    series = []
    for col in numeric_cols[:MAX_CHART_SERIES]:
        values = []
        for row in data:
            number = _to_float(row[col]) if col < len(row) else None
            values.append(number if number is not None else float("nan"))
        if any(v == v for v in values):  # co it nhat mot so hop le
            series.append((headers[col], values))
    if not series:
        return b""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for label, values in series:
        ax.plot(range(len(values)), values, marker="o", markersize=3, label=label)
    ax.set_xlabel("dòng")
    ax.set_ylabel("giá trị")
    ax.set_title("Biểu đồ từ dữ liệu bạn vừa dán")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110)
    plt.close(fig)
    return buffer.getvalue()


def _analyze_log_block(block: str) -> ChatActionOutcome:
    lines = _candidate_lines(block)
    stamped = [ln for ln in lines if _TIMESTAMP_RE.search(ln)]
    keywords = ("error", "fail", "exception", "timeout", "warning", "loi")
    suspicious = [ln for ln in lines if any(k in ln.lower() for k in keywords)]
    summary = (
        "- Tổng số dòng: " + str(len(lines)) + "\n"
        "- Dòng có mốc thời gian: " + str(stamped) + "\n"
        "- Dòng nghi có lỗi/cảnh báo: " + str(len(suspicious))
    )
    blocks: List[ChatActionBlock] = [
        ChatActionBlock(kind=BLOCK_MARKDOWN, text="**Kết quả rà log:**\n" + summary)
    ]
    if suspicious:
        sample = suspicious[:10]
        blocks.append(
            ChatActionBlock(
                kind=BLOCK_TABLE,
                headers=["Dòng nghi lỗi/cảnh báo (tối đa 10 dòng đầu)"],
                rows=[(ln[:160],) for ln in sample],
                caption="Đây là các dòng chứa từ khóa lỗi — cần đối chiếu ngữ cảnh trước khi kết luận.",
            )
        )
    blocks.append(
        ChatActionBlock(
            kind=BLOCK_MARKDOWN,
            text="_Nếu bạn muốn hỏi sâu thêm về log này (nguyên nhân, đối sách), cứ hỏi tiếp ở câu sau nhé._",
        )
    )
    return ChatActionOutcome(action=ACTION_NAME, title=TITLE, blocks=tuple(blocks))


def _analyze_csv_block(block: str) -> Optional[ChatActionOutcome]:
    headers, data = _parse_csv_block(block)
    if not headers or not data:
        return None
    numeric_cols = _numeric_columns(headers, data)
    summary_lines = [
        "- Số dòng dữ liệu: " + str(len(data)),
        "- Số cột: " + str(len(headers)) + " (" + ", ".join(headers[:12]) + ")",
    ]
    table_rows = []
    for col in numeric_cols[:6]:
        values = []
        for row in data:
            if col >= len(row):
                continue
            number = _to_float(row[col])
            if number is not None:
                values.append(number)
        table_rows.append((headers[col], _describe_numeric(values)))
    blocks: List[ChatActionBlock] = [
        ChatActionBlock(kind=BLOCK_MARKDOWN, text="**Tóm tắt dữ liệu:**\n" + "\n".join(summary_lines))
    ]
    if table_rows:
        blocks.append(
            ChatActionBlock(
                kind=BLOCK_TABLE,
                headers=["Cột số", "Thống kê"],
                rows=table_rows,
                caption="Thống kê mô tả các cột số.",
            )
        )
    png = _draw_line_chart(headers, data, numeric_cols)
    if png:
        blocks.append(
            ChatActionBlock(
                kind=BLOCK_CHART,
                image_png=png,
                alt="Biểu đồ từ dữ liệu bạn vừa dán",
                caption="Biểu đồ từ dữ liệu bạn vừa dán (không phải mô phỏng).",
            )
        )
    preview = data[:10]
    blocks.append(
        ChatActionBlock(
            kind=BLOCK_TABLE,
            headers=headers,
            rows=[tuple(row) for row in preview],
            caption="10 dòng đầu của dữ liệu.",
        )
    )
    blocks.append(
        ChatActionBlock(
            kind=BLOCK_MARKDOWN,
            text="_Nếu bạn muốn hỏi sâu thêm về dữ liệu này, cứ hỏi tiếp ở câu sau nhé._",
        )
    )
    return ChatActionOutcome(action=ACTION_NAME, title=TITLE, blocks=tuple(blocks))


class _DataPasteAction(ChatAction):
    """Nhan dien noi dung dan vao la bang/log ma khong can go lenh."""

    def matches(self, request: ChatActionRequest) -> bool:
        if super().matches(request):
            return True
        block = extract_pasted_block(request.question or "")
        return block is not None


def _handler(request: ChatActionRequest) -> Optional[ChatActionOutcome]:
    question = (request.question or "")[:MAX_TEXT_CHARS]
    block = extract_pasted_block(question)
    if block is None:
        return None
    lines = _candidate_lines(block)
    if _looks_like_csv(lines):
        outcome = _analyze_csv_block(block)
        if outcome is not None:
            return outcome
    if _looks_like_log(lines):
        return _analyze_log_block(block)
    return None


def register() -> None:
    register_action(
        _DataPasteAction(
            name=ACTION_NAME,
            title=TITLE,
            hints=_HINTS,
            handler=_handler,
            description=(
                "Dán log/CSV vào ô chat: tự nhận diện, phân tích thống kê và vẽ "
                "biểu đồ ngay trong câu trả lời, không cần chuyển công cụ."
            ),
        )
    )


register()
