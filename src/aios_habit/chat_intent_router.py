"""Chat-first intent router (UX-CHAT-CORE).

Replaces the 3-branch "Navigation" radio: every chat sentence is classified
here and the app routes it to the existing handler. The user NEVER has to
pick a branch.

Algorithm: Vietnamese keyword matching (diacritics-insensitive), fully
deterministic, no LLM call -> testable and works offline.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Optional, Tuple

# Recognized intents. "hoi_tai_lieu" is the default fallback.
CANH_BAO_NGUONG = "canh_bao_nguong"      # threshold alert request
VE_BIEU_DO = "ve_bieu_do"                # chart request (runs the JIG chart branch)
TAO_SO = "tao_so"                        # create a notebook
MO_SO = "mo_so"                          # open a notebook
HO_SO_DIEU_TRA = "ho_so_dieu_tra"        # open the investigation case workspace
CONG_CU_NANG_CAO = "cong_cu_nang_cao"    # open the advanced JIG analysis tools
HOI_DAP_CHUNG = "hoi_dap_chung"          # small talk / greeting
HOI_TAI_LIEU = "hoi_tai_lieu"            # document Q&A (RAG) fallback
DU_LIEU_DAN = "du_lieu_dan"              # pasted CSV/log block in the message

TAT_CA_Y_DINH = (
    CANH_BAO_NGUONG,
    VE_BIEU_DO,
    TAO_SO,
    MO_SO,
    HO_SO_DIEU_TRA,
    CONG_CU_NANG_CAO,
    HOI_DAP_CHUNG,
    HOI_TAI_LIEU,
    DU_LIEU_DAN,
)


def _khong_dau(text: str) -> str:
    """Lowercase + strip Vietnamese diacritics for keyword matching."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip()


# Priority order: specific intents first, generic ones last.
_QUY_TAC: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        CANH_BAO_NGUONG,
        (
            "canh bao khi", "dat nguong", "thiet lap nguong",
            "thiet lap canh bao", "canh bao vuot", "nguong canh bao",
            "liet ke canh bao", "xoa canh bao", "tat canh bao",
        ),
    ),
    (
        VE_BIEU_DO,
        (
            "ve bieu do",
        ),
    ),
    (
        TAO_SO,
        ("tao so", "tao so tai lieu", "tao so moi", "lap so"),
    ),
    (
        MO_SO,
        ("mo so",),
    ),
    (
        HO_SO_DIEU_TRA,
        (
            "mo ho so", "ho so dieu tra",
            "day aios", "phong van chuyen gia",
        ),
    ),
    (
        CONG_CU_NANG_CAO,
        (
            "cong cu nang cao", "mo lsu", "cong cu jig",
        ),
    ),
    (
        HOI_DAP_CHUNG,
        (
            "xin chao", "chao ban", "chao aios", "hello",
            "cam on", "thank", "ban la ai", "gioi thieu",
        ),
    ),
)


def classify_intent(text: str) -> str:
    """Classify one chat sentence. Always returns a valid intent."""
    intents = classify_all_intents(text)
    return intents[0][0] if intents else HOI_TAI_LIEU


def _co_khoi_du_lieu_dan(text: str) -> bool:
    """True when the message carries a pasted CSV/log block.

    Imported lazily so this router stays dependency-free for unit tests.
    """
    try:
        from aios_habit.chat_action_data_paste import extract_pasted_block
    except Exception:
        return False
    try:
        return extract_pasted_block(text or "") is not None
    except Exception:
        return False


def classify_all_intents(text: str) -> list:
    """Classify ALL intents present in one chat message.

    A single message may carry several intents (e.g. pasted CSV + a chart
    request + a threshold alert). Returns a list of (intent, slots) in
    priority order; the caller is expected to run every one of them.
    The single-intent ``classify_intent`` keeps returning the first entry,
    so existing callers are unaffected.
    """
    clean = text or ""
    norm = _khong_dau(clean)
    if not norm:
        return [(HOI_DAP_CHUNG, {})]
    ngan = len(norm) < 80
    found: list = []
    for y_dinh, cum_tu in _QUY_TAC:
        if y_dinh in (HO_SO_DIEU_TRA, CONG_CU_NANG_CAO) and not ngan:
            continue
        if y_dinh == VE_BIEU_DO and "gui mail" in norm:
            # "bieu do gui mail" belongs to alert-config commands, not charting.
            continue
        for cum in cum_tu:
            if cum in norm:
                # Avoid "mo so" misfiring on "mo ho so".
                if y_dinh == MO_SO and "mo ho so" in norm:
                    continue
                found.append((y_dinh, extract_slots(clean, y_dinh)))
                break
    # Pasted data is orthogonal to keywords: a pasted CSV/log block is its
    # own intent even when the sentence also asks for an alert or a chart.
    if _co_khoi_du_lieu_dan(clean):
        found.insert(0, (DU_LIEU_DAN, {}))
    if not found:
        found.append((HOI_TAI_LIEU, {}))
    return found


def extract_slots(text: str, intent: str) -> Dict[str, str]:
    """Extract simple slots for a few intents (notebook title...)."""
    slots: Dict[str, str] = {}
    clean = (text or "").strip()
    if intent == TAO_SO:
        mau = re.compile(
            r"(?:tạo|tao)\s+sổ(?:\s+tài\s+liệu)?\s+(.+)$",
            re.IGNORECASE,
        )
        m = mau.search(clean)
        if m:
            slots["ten_so"] = m.group(1).strip().strip("\"'")
    elif intent == MO_SO:
        mau = re.compile(r"mở\s+sổ\s+(.+)$", re.IGNORECASE)
        m = mau.search(clean)
        if m:
            slots["ten_so"] = m.group(1).strip().strip("\"'")
    return slots


def route(text: str) -> Tuple[str, Dict[str, str]]:
    """Single entry point: (intent, slots)."""
    intent = classify_intent(text)
    return intent, extract_slots(text, intent)


def giai_thich_y_dinh(intent: str) -> str:
    """Short Vietnamese note shown in chat so the user sees what the app understood."""
    return {
        CANH_BAO_NGUONG: "Tôi hiểu đây là yêu cầu cảnh báo ngưỡng.",
        VE_BIEU_DO: "Tôi hiểu bạn muốn vẽ biểu đồ.",
        TAO_SO: "Tôi hiểu bạn muốn tạo sổ tài liệu mới.",
        MO_SO: "Tôi hiểu bạn muốn mở một sổ tài liệu.",
        HO_SO_DIEU_TRA: "Tôi hiểu bạn muốn mở hồ sơ điều tra.",
        CONG_CU_NANG_CAO: "Tôi hiểu bạn muốn mở công cụ phân tích JIG.",
        DU_LIEU_DAN: "Tôi thấy bạn đã dán dữ liệu, tôi sẽ phân tích ngay.",
        HOI_DAP_CHUNG: "",
        HOI_TAI_LIEU: "",
    }.get(intent, "")


def nhan_y_dinh(intent: str) -> str:
    """Short Vietnamese label for one intent (section header in a merged reply)."""
    return {
        CANH_BAO_NGUONG: "Cảnh báo ngưỡng",
        VE_BIEU_DO: "Vẽ biểu đồ",
        TAO_SO: "Tạo sổ",
        MO_SO: "Mở sổ",
        HO_SO_DIEU_TRA: "Hồ sơ điều tra",
        CONG_CU_NANG_CAO: "Công cụ JIG",
        DU_LIEU_DAN: "Phân tích dữ liệu vừa dán",
        HOI_DAP_CHUNG: "Trò chuyện",
        HOI_TAI_LIEU: "Hỏi tài liệu",
    }.get(intent, "")
