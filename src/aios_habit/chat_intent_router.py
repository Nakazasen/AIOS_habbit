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
XEM_TIEN_DO_VU = "xem_tien_do_vu"        # view progress of active case
LAP_CAY_4M_VU = "lap_cay_4m_vu"          # build 4M + Why-Why tree for active case
TAO_VU_DIEU_TRA = "tao_vu_dieu_tra"      # create an investigation case via chat
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
    XEM_TIEN_DO_VU,
    LAP_CAY_4M_VU,
    TAO_VU_DIEU_TRA,
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
        XEM_TIEN_DO_VU,
        (
            "xem tien do vu",
            "tien do vu",
            "tien do ca",
            "xem tien do ca",
            "trang thai vu",
            "xem trang thai vu",
            "xem tien do",
            "tien do vu dieu tra",
        ),
    ),
    (
        LAP_CAY_4M_VU,
        (
            "lap cay 4m",
            "cay 4m",
            "cay dieu tra 4m",
            "lap cay dieu tra 4m",
            "phan tich 4m",
            "5 why",
            "why why",
            "lap cay why why",
            "cay why why",
        ),
    ),
    (
        TAO_VU_DIEU_TRA,
        (
            "tao vu dieu tra",
            "tao ho so dieu tra",
            "lap vu dieu tra",
            "mo vu dieu tra",
            "tao ca loi",
            "ghi nhan loi",
            "bao loi moi",
            "su co line",
            "loi line",
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


def extract_case_entities(text: str) -> Dict[str, str]:
    """Extract case entities (phenomenon, error_code, line, machine_type) from Vietnamese chat."""
    clean = (text or "").strip()
    if not clean:
        return {
            "phenomenon": "",
            "error_code": "",
            "line": "",
            "machine_type": "",
        }

    # 1. Error code (C, F, J, or JAM + 3-4 digits)
    code_match = re.search(
        r"\b(?:(JAM)\s*-?\s*(\d{3,4})|([CFJcfj])\s*-?\s*(\d{3,4}))\b",
        clean,
    )
    error_code = ""
    if code_match:
        if code_match.group(1):
            error_code = f"{code_match.group(1).upper()}{code_match.group(2)}"
        elif code_match.group(3):
            error_code = f"{code_match.group(3).upper()}{code_match.group(4)}"

    # 2. Line (Line, Chuyen, Day chuyen + ID)
    line_match = re.search(
        r"(?:ở\s+|tai\s+|tại\s+)?\b(?:line|chuyền|chuyen|dây\s*chuyền|day\s*chuyen)\s*([A-Za-z0-9_-]+)",
        clean,
        re.IGNORECASE,
    )
    line = ""
    if line_match:
        line_val = line_match.group(1).strip()
        line = f"Line {line_val.upper()}"

    # 3. Machine / Model
    machine_type = ""
    m_match = re.search(
        r"\b(máy\s+in|may\s+in|máy\s+photo|may\s+photo|máy\s+dán|may\s+dan|máy\s+hàn|may\s+han|máy\s+quét|may\s+quet|máy\s+đóng\s+gói|may\s+dong\s+goi|iris[A-Za-z0-9_-]*|polaris[A-Za-z0-9_-]*|kairos[A-Za-z0-9_-]*|virgo[A-Za-z0-9_-]*|bizhub[A-Za-z0-9_-]*)\b",
        clean,
        re.IGNORECASE,
    )
    if m_match:
        machine_type = m_match.group(1).strip()
    else:
        m_exp = re.search(
            r"(?:model|dòng\s*máy|dong\s*may|thiết\s*bị|thiet\s*bi|máy|may)\s*[:\s]\s*([A-Za-z0-9_-]+)",
            clean,
            re.IGNORECASE,
        )
        if m_exp:
            machine_type = m_exp.group(1).strip()

    # 4. Phenomenon: strip intent prefix and line clause
    prefix_re = re.compile(
        r"^(?:(?:tạo|lap|lập|mở|mo)\s+(?:vụ|vu|hồ\s+sơ|ho\s+so|ca|yêu\s+cầu|yeu\s+cau)?(?:\s+(?:điều\s+tra|dieu\s+tra))?(?:\s+(?:lỗi|loi))?(?:\s+(?:mới|moi))?|(?:ghi\s+nhận|báo|bao)\s+lỗi(?:\s+mới)?|sự\s+cố|su\s+co)\s*[:,-]?\s*",
        re.IGNORECASE,
    )
    remainder = prefix_re.sub("", clean).strip()
    if line_match:
        remainder = re.sub(
            r"(?:ở\s+|tai\s+|tại\s+)?\b(?:line|chuyền|chuyen|dây\s*chuyền|day\s*chuyen)\s*[A-Za-z0-9_-]+",
            "",
            remainder,
            flags=re.IGNORECASE,
        ).strip()
    phenomenon = re.sub(r"\s+", " ", remainder).strip(" :,-.")
    if not phenomenon:
        phenomenon = clean

    return {
        "phenomenon": phenomenon,
        "error_code": error_code,
        "line": line,
        "machine_type": machine_type,
    }


def extract_case_id_from_text(text: str) -> str:
    """Extract CASE-XXXX id if explicitly referenced in text."""
    clean = str(text or "").strip()
    m = re.search(r"\b(CASE-[A-Za-z0-9_-]+)\b", clean, re.IGNORECASE)
    return m.group(1).upper() if m else ""


def extract_slots(text: str, intent: str) -> Dict[str, str]:
    """Extract simple slots for a few intents (notebook title, case entities...)."""
    slots: Dict[str, str] = {}
    clean = (text or "").strip()
    if intent == TAO_VU_DIEU_TRA:
        return extract_case_entities(clean)
    elif intent in (XEM_TIEN_DO_VU, LAP_CAY_4M_VU):
        cid = extract_case_id_from_text(clean)
        return {"case_id": cid} if cid else {}
    elif intent == TAO_SO:
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
        XEM_TIEN_DO_VU: "Tôi hiểu bạn muốn xem tiến độ vụ điều tra.",
        LAP_CAY_4M_VU: "Tôi hiểu bạn muốn lập cây điều tra 4M và chuỗi Why-Why.",
        TAO_VU_DIEU_TRA: "Tôi hiểu bạn muốn tạo vụ điều tra lỗi mới.",
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
        XEM_TIEN_DO_VU: "Tiến độ vụ điều tra",
        LAP_CAY_4M_VU: "Cây điều tra 4M & Why-Why",
        TAO_VU_DIEU_TRA: "Tạo vụ điều tra",
        TAO_SO: "Tạo sổ",
        MO_SO: "Mở sổ",
        HO_SO_DIEU_TRA: "Hồ sơ điều tra",
        CONG_CU_NANG_CAO: "Công cụ JIG",
        DU_LIEU_DAN: "Phân tích dữ liệu vừa dán",
        HOI_DAP_CHUNG: "Trò chuyện",
        HOI_TAI_LIEU: "Hỏi tài liệu",
    }.get(intent, "")
