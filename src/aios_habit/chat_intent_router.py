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
TAO_SO = "tao_so"                        # create a notebook
MO_SO = "mo_so"                          # open a notebook
HO_SO_DIEU_TRA = "ho_so_dieu_tra"        # open the investigation case workspace
CONG_CU_NANG_CAO = "cong_cu_nang_cao"    # open the advanced JIG analysis tools
HOI_DAP_CHUNG = "hoi_dap_chung"          # small talk / greeting
HOI_TAI_LIEU = "hoi_tai_lieu"            # document Q&A (RAG) fallback

TAT_CA_Y_DINH = (
    CANH_BAO_NGUONG,
    TAO_SO,
    MO_SO,
    HO_SO_DIEU_TRA,
    CONG_CU_NANG_CAO,
    HOI_DAP_CHUNG,
    HOI_TAI_LIEU,
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
    norm = _khong_dau(text or "")
    if not norm:
        return HOI_DAP_CHUNG
    # View-opening intents only fire on short pure commands: a long message
    # (e.g. pasted logs + "phân tích giúp tôi") must reach the analysis
    # pipeline, not open a view.
    ngan = len(norm) < 80
    for y_dinh, cum_tu in _QUY_TAC:
        if y_dinh in (HO_SO_DIEU_TRA, CONG_CU_NANG_CAO) and not ngan:
            continue
        for cum in cum_tu:
            if cum in norm:
                # Avoid "mo so" misfiring on "mo ho so".
                if y_dinh == MO_SO and "mo ho so" in norm:
                    continue
                return y_dinh
    return HOI_TAI_LIEU


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
        TAO_SO: "Tôi hiểu bạn muốn tạo sổ tài liệu mới.",
        MO_SO: "Tôi hiểu bạn muốn mở một sổ tài liệu.",
        HO_SO_DIEU_TRA: "Tôi hiểu bạn muốn mở hồ sơ điều tra.",
        CONG_CU_NANG_CAO: "Tôi hiểu bạn muốn mở công cụ phân tích JIG.",
        HOI_DAP_CHUNG: "",
        HOI_TAI_LIEU: "",
    }.get(intent, "")
