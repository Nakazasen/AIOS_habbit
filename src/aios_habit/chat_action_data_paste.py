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


def _khoi_csv_lien_tuc(lines: Sequence[str]) -> Optional[str]:
    """Tim khoi CSV lien tuc dai nhat trong tin nhan.

    Nguoi dung thuong dan CSV kem cau lenh ("ve bieu do", "canh bao khi...")
    o dau/cuoi; chi can khoi du lieu lien tuc co cung so cot, khong doi ca
    tin nhan phai dong nhat.
    """
    if len(lines) < 2:
        return None
    tot_nhat: List[str] = []
    for delimiter in (",", ";", "\t"):
        counts = [ln.count(delimiter) for ln in lines]
        i = 0
        while i < len(lines):
            if counts[i] < 1:
                i += 1
                continue
            run = [lines[i]]
            j = i + 1
            while j < len(lines) and counts[j] == counts[i]:
                run.append(lines[j])
                j += 1
            # Khoi o dau tin nhan chap nhan tu 2 dong; khoi giua tin nhan can
            # it nhat 3 dong de tranh nhan nham 2 dong van xuoi trung co.
            nguong = 2 if i == 0 else 3
            if len(run) >= nguong and len(run) > len(tot_nhat):
                tot_nhat = run
            i = j
    if len(tot_nhat) >= 2:
        return "\n".join(tot_nhat)
    return None


def extract_pasted_block(question: str) -> Optional[str]:
    """Tach khoi du lieu duoc dan ra khoi cau chat. None neu khong thay."""
    lines = _candidate_lines(question)
    khoi_csv = _khoi_csv_lien_tuc(lines)
    if khoi_csv is not None:
        return khoi_csv
    if _looks_like_log(lines):
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


_FONT_UNG_HO_TIENG_VIET = (
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _font_bieu_do(size: int):
    """Font ve chu tieng Viet len bieu do Pillow.

    Tra ve (font, can_bo_dau): uu tien font he thong co dau; khong co thi
    dung font mac dinh cua Pillow va bo dau de khoi o vuong.
    """
    from PIL import ImageFont

    for duong_dan in _FONT_UNG_HO_TIENG_VIET:
        try:
            return ImageFont.truetype(duong_dan, size), False
        except Exception:
            continue
    return ImageFont.load_default(), True


def _bo_dau_chu(text: str) -> str:
    import unicodedata

    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def _draw_line_chart_matplotlib(
    headers: List[str], data: List[List[str]], numeric_cols: List[int]
) -> bytes:
    """Ve bieu do duong bang matplotlib. Tra ve PNG bytes (rong neu ve hong)."""
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


def _draw_line_chart_pillow(
    headers: List[str], data: List[List[str]], numeric_cols: List[int]
) -> bytes:
    """Ve bieu do duong don gian bang Pillow (fallback khi thieu matplotlib)."""
    from PIL import Image, ImageDraw

    series = []
    for col in numeric_cols[:MAX_CHART_SERIES]:
        values = []
        for row in data:
            number = _to_float(row[col]) if col < len(row) else None
            if number is not None:
                values.append(number)
        if values:
            series.append((headers[col], values))
    if not series:
        return b""
    rong, cao = 800, 420
    le_trai, le_phai, le_tren, le_duoi = 64, 24, 60, 48
    tat_ca = [v for _, day in series for v in day]
    nho_nhat, lon_nhat = min(tat_ca), max(tat_ca)
    if lon_nhat == nho_nhat:
        lon_nhat = nho_nhat + 1.0
    dem = (lon_nhat - nho_nhat) * 0.08
    nho_nhat, lon_nhat = nho_nhat - dem, lon_nhat + dem
    n = max(len(day) for _, day in series)
    anh = Image.new("RGB", (rong, cao), "white")
    ve = ImageDraw.Draw(anh)
    font, can_bo_dau = _font_bieu_do(15)

    def chu(s: str) -> str:
        return _bo_dau_chu(s) if can_bo_dau else s

    vung_rong, vung_cao = rong - le_trai - le_phai, cao - le_tren - le_duoi

    def toa_do(i: int, v: float):
        x = le_trai + (i / max(1, n - 1)) * vung_rong
        y = le_tren + vung_cao - ((v - nho_nhat) / (lon_nhat - nho_nhat)) * vung_cao
        return x, y

    for k in range(6):
        v = nho_nhat + (lon_nhat - nho_nhat) * k / 5
        _, y = toa_do(0, v)
        ve.line([(le_trai, y), (rong - le_phai, y)], fill=(230, 230, 230))
        ve.text((6, y - 9), chu(_fmt(v)), font=font, fill=(80, 80, 80))
    ve.line([(le_trai, le_tren), (le_trai, cao - le_duoi)], fill=(60, 60, 60), width=2)
    ve.line([(le_trai, cao - le_duoi), (rong - le_phai, cao - le_duoi)], fill=(60, 60, 60), width=2)
    mau_sac = [(31, 119, 180), (214, 39, 40), (44, 160, 44)]
    for chi_so, (nhan, day_so) in enumerate(series):
        mau = mau_sac[chi_so % len(mau_sac)]
        diem = [toa_do(i, v) for i, v in enumerate(day_so)]
        if len(diem) >= 2:
            ve.line(diem, fill=mau, width=2)
        for p in diem:
            ve.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=mau)
        gx = le_trai + 8 + chi_so * 210
        ve.rectangle([gx, 14, gx + 26, 28], fill=mau)
        ve.text((gx + 32, 12), chu(nhan[:20]), font=font, fill=(40, 40, 40))
    ve.text((le_trai, cao - 32), chu("dòng"), font=font, fill=(80, 80, 80))
    ve.text((le_trai, 36), chu("Biểu đồ từ dữ liệu bạn vừa dán"), font=font, fill=(30, 30, 30))
    bo_dem = io.BytesIO()
    anh.save(bo_dem, format="PNG")
    return bo_dem.getvalue()


def _ve_bieu_do_ket_qua(
    headers: List[str], data: List[List[str]], numeric_cols: List[int]
) -> Tuple[bytes, str]:
    """Ve bieu do, tra ve (png_bytes, ly_do_loi).

    Uu tien matplotlib; thieu thi dung Pillow (may nha co san). Khong bao gio
    nem loi ra ngoai. ly_do_loi rong nghia la: ve duoc, hoac khong co gi de
    ve (khong co cot so hop le) — truong hop sau khong can ghi chu.
    """
    try:
        png = _draw_line_chart_matplotlib(headers, data, numeric_cols)
        if png:
            return png, ""
        return b"", ""
    except ImportError as exc:
        ly_do_thieu = "thiếu thư viện matplotlib ({})".format(exc)
    except Exception as exc:
        return b"", "matplotlib báo lỗi: {}".format(exc)
    try:
        png = _draw_line_chart_pillow(headers, data, numeric_cols)
        if png:
            return png, ""
        return b"", ""
    except Exception as exc:
        return b"", ly_do_thieu + "; Pillow báo lỗi: {}".format(exc)


def _draw_line_chart(
    headers: List[str], data: List[List[str]], numeric_cols: List[int]
) -> bytes:
    """Ve bieu do duong, tra ve PNG bytes. KHONG bao gio nem loi ra ngoai.

    Uu tien matplotlib; thieu thi dung Pillow (may nha co san). Ve hong thi
    tra ve rong — bang thong ke van duoc giu nguyen trong cau tra loi.
    """
    png, _ly_do = _ve_bieu_do_ket_qua(headers, data, numeric_cols)
    return png


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
    # Ve bieu do: loi ve KHONG duoc lam roi bang thong ke phia tren.
    # Ve hong van giu du bang + preview, kem ly do ro rang.
    png = b""
    ly_do_khong_ve = ""
    if numeric_cols:
        try:
            png, ly_do_khong_ve = _ve_bieu_do_ket_qua(headers, data, numeric_cols)
        except Exception as exc:
            png, ly_do_khong_ve = b"", "lỗi không ngờ khi vẽ: {}".format(exc)
    if png:
        blocks.append(
            ChatActionBlock(
                kind=BLOCK_CHART,
                image_png=png,
                alt="Biểu đồ từ dữ liệu bạn vừa dán",
                caption="Biểu đồ từ dữ liệu bạn vừa dán (không phải mô phỏng).",
            )
        )
    elif ly_do_khong_ve:
        blocks.append(
            ChatActionBlock(
                kind=BLOCK_MARKDOWN,
                text="Không vẽ được biểu đồ vì " + ly_do_khong_ve + ".",
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
