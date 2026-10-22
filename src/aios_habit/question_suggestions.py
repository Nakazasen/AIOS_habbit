"""Deterministic question suggestions for nontech users (007 extension).



English code comments by repo rule. Generated questions are Vietnamese and

come only from source titles and citation labels already visible in the UI.

No AI call, no new dependency, no raw document text used.

"""

from __future__ import annotations



from typing import Any, Dict, List, Sequence





def _clean_titles(values: Sequence[Any], limit: int = 3) -> List[str]:

    seen: List[str] = []

    for value in values:

        text = str(value or "").strip()

        if text and text not in seen:

            seen.append(text)

        if len(seen) >= limit:

            break

    return seen





def opening_suggestions(source_titles: Sequence[Any], limit: int = 3) -> List[str]:

    """Build up to `limit` opening questions from enabled source titles."""

    titles = _clean_titles(source_titles, limit=3)

    if not titles:

        return []

    if len(titles) == 1:

        name = titles[0]

        out = [

            f"Tóm tắt tài liệu {name}?",

            f"Tài liệu {name} có những nội dung chính nào?",

            f"Khi cần thì tra cứu tài liệu {name} thế nào?",

        ]

    else:

        out = [

            "Tóm tắt các tài liệu trong sổ này?",

            f"Tài liệu {titles[0]} và {titles[1]} khác nhau ở điểm nào?",

            f"Tài liệu {titles[0]} nói gì quan trọng nhất?",

        ]

    return out[: max(1, limit)]





def citation_labels_of(items: Sequence[Any]) -> List[str]:

    """Extract citation labels from evidence items (objects or dicts).



    The app badge stores dicts with `citation_id` like "[1]"; the RAG layer

    uses objects with `citation_label`. Both are accepted.

    """

    import re as _re



    labels: List[str] = []

    for item in items:

        if isinstance(item, dict):

            label = str(item.get("citation_label", "") or "").strip()

            if not label:

                candidate = str(item.get("citation_id", "") or "").strip()

                if _re.fullmatch(r"\[\w+\]", candidate):

                    label = candidate

        else:

            label = str(getattr(item, "citation_label", "") or "").strip()

            if not label:

                candidate = str(getattr(item, "citation_id", "") or "").strip()

                if _re.fullmatch(r"\[\w+\]", candidate):

                    label = candidate

        if label and label not in labels:

            labels.append(label)

        if len(labels) >= 3:

            break

    return labels





def followup_suggestions(citation_labels: Sequence[Any], limit: int = 3) -> List[str]:

    """Build up to `limit` follow-up questions from just-shown citations."""

    labels = _clean_titles(citation_labels, limit=3)

    if not labels:

        return [

            "Còn nguồn nào khác về nội dung này?",

            "Tóm tắt lại ngắn gọn hơn?",

            "Cho ví dụ cụ thể hơn?",

        ][: max(1, limit)]

    out = [

        f"Nói rõ hơn về {labels[0]}?",

        f"Còn nguồn nào khác ngoài {labels[0]}?",

    ]

    if len(labels) > 1:

        out.append(f"So sánh {labels[0]} với {labels[1]}?")

    else:

        out.append("Tóm tắt lại ngắn gọn hơn?")

    return out[: max(1, limit)]





def _short_source_name(title: Any, max_len: int = 40) -> str:

    """Shorten a document title for nontech suggestion buttons.



    Filenames use underscores and version codes, so underscores become

    spaces and cutting happens at a word boundary.

    """

    name = " ".join(str(title or "").replace("_", " ").split())

    if "." in name:

        stem, ext = name.rsplit(".", 1)

        if stem and len(ext) <= 5 and ext.replace("_", "").isalnum():

            name = stem

    if len(name) <= max_len:

        return name

    cut = name[:max_len].rsplit(" ", 1)

    return (cut[0] if cut[0] else name[:max_len]).rstrip() + "…"





def cited_sources_of(items: Sequence[Any]) -> List[tuple[str, str]]:

    """Extract (short name, raw title) pairs from evidence items."""

    pairs: List[tuple[str, str]] = []

    seen: set[str] = set()

    for item in items:

        if isinstance(item, dict):

            title = str(item.get("title", "") or "")

        else:

            title = str(getattr(item, "source_name", "") or getattr(item, "title", ""))

        raw = title.strip()

        short = _short_source_name(raw)

        if short and raw.casefold() not in seen:

            seen.add(raw.casefold())

            pairs.append((short, raw))

        if len(pairs) >= 3:

            break

    return pairs





def followup_suggestions_from_items(items: Sequence[Any], limit: int = 3) -> List[str]:

    """Follow-ups naming the just-cited documents in plain words."""

    shorts = [short for short, _raw in cited_sources_of(items)]

    if not shorts:

        return followup_suggestions([], limit=limit)

    out = [

        f"Nói rõ hơn về {shorts[0]}?",

        f"Còn nguồn nào khác ngoài {shorts[0]}?",

    ]

    if len(shorts) > 1:

        out.append(f"So sánh {shorts[0]} với {shorts[1]}?")

    else:

        out.append("Tóm tắt lại ngắn gọn hơn?")

    return out[: max(1, limit)]





_TOPIC_STOPWORDS = frozenset({
    "la", "gi", "the", "nao", "cho", "vi", "du", "cu", "the", "hon",
    "ve", "cua", "trong", "cac", "nhung", "khong", "co", "duoc",
    "nay", "kia", "a", "nhe", "va", "voi", "tai", "de", "mot",
    "sao", "hay", "nhu",
})


def clean_question_for_topic(text: str, rstrip_q: bool = False) -> str:
    """Extract clean core question, stripping previous context wrappers and follow-up prefixes."""
    import re as _re

    lines = [l.strip() for l in str(text or "").splitlines() if l.strip()]
    core = ""
    for line in lines:
        if line.startswith("Bối cảnh câu trước:") or line.startswith("Trả lời trước:"):
            continue
        core = line
        break
    if not core:
        core = lines[0] if lines else ""

    # Strip suggestion prefixes to prevent compounding e.g. "So sánh So sánh..."
    prefix_patterns = [
        r"^(?:So\s+sánh\s+)+",
        r"^(?:Nói\s+rõ\s+hơn\s+về\s+)+",
        r"^(?:Cho\s+ví\s+dụ\s+về\s+)+",
        r"^(?:Tóm\s+tắt\s+(?:lại\s+)?(?:ngắn\s+gọn\s+hơn\s+trong\s+|trong\s+)?)+",
        r"^(?:Còn\s+nguồn\s+nào\s+khác\s+ngoài\s+)+",
    ]
    for pat in prefix_patterns:
        core = _re.sub(pat, "", core, flags=_re.IGNORECASE).strip()

    # Strip document comparison suffixes e.g. "giữa doc1 và doc2?"
    core = _re.sub(r"\s+giữa\s+.+\s+và\s+.+\??$", "", core, flags=_re.IGNORECASE).strip()
    core = _re.sub(r"\s+liên\s+quan\s+gì\s+đến\s+.+\??$", "", core, flags=_re.IGNORECASE).strip()
    core = _re.sub(r"\s+trong\s+.+\??$", "", core, flags=_re.IGNORECASE).strip()
    return core.rstrip("?") if rstrip_q else core


def topic_of(question: Any) -> str:
    """Extract the topic words of the last question for contextual follow-ups."""
    import re as _re
    import unicodedata as _ud

    clean = clean_question_for_topic(str(question or ""), rstrip_q=True)
    if not clean:
        return ""
    words = clean.split()
    kept: List[str] = []
    for word in words:
        plain = "".join(
            ch for ch in _ud.normalize("NFD", word.casefold()) if _ud.category(ch) != "Mn"
        )
        if plain and plain not in _TOPIC_STOPWORDS:
            kept.append(word)
        if len(kept) >= 10:
            break
    return " ".join(kept)


def contextual_followups(
    items: Sequence[Any],
    last_question: Any = "",
    limit: int = 3,
) -> List[tuple[str, str]]:
    """Follow-ups continuing the current topic like NotebookLM does.

    Returns (display, send) pairs: the button shows the short readable
    name while the sent question carries the FULL document title, so a
    cut display name never corrupts retrieval. Falls back to plain
    question strings when there is no topic or no cited source.
    """
    pairs = cited_sources_of(items)
    shorts = [short for short, _raw in pairs]
    raws = [raw for _short, raw in pairs]
    topic = topic_of(last_question)
    if not topic or not shorts:
        plain = followup_suggestions_from_items(items, limit=limit)
        return [(text, text) for text in plain]
    out = [
        (
            f"{topic} liên quan gì đến {shorts[0]}?",
            f"{topic} liên quan gì đến {raws[0]}?",
        ),
        (
            f"Cho ví dụ về {topic} trong {shorts[0]}?",
            f"Cho ví dụ về {topic} trong {raws[0]}?",
        ),
    ]
    if len(shorts) > 1:
        out.append((
            f"So sánh {topic} giữa {shorts[0]} và {shorts[1]}?",
            f"So sánh {topic} giữa {raws[0]} và {raws[1]}?",
        ))
    else:
        out.append((
            f"Tóm tắt {topic} trong {shorts[0]}?",
            f"Tóm tắt {topic} trong {raws[0]}?",
        ))
    return out[: max(1, limit)]


def contextual_send_text(chip: str, last_question: Any = "", last_answer: Any = "") -> str:
    """Expand a follow-up chip into a self-contained question.

    The previous question and the head of the previous answer travel with
    the chip so retrieval and synthesis stay on thread even when the model
    ignores chat history. Never nests multiple 'Bối cảnh câu trước:' layers.
    """
    import re as _re

    chip_text = str(chip or "").strip()
    if not chip_text:
        return ""
    if "Bối cảnh câu trước:" in chip_text:
        return chip_text

    parts = [chip_text]
    core_q = clean_question_for_topic(str(last_question or ""), rstrip_q=False)
    if core_q and core_q.casefold() not in chip_text.casefold():
        parts.append(f"Bối cảnh câu trước: {core_q[:200]}")

    clean_ans = " ".join(str(last_answer or "").split())
    if clean_ans and "Bối cảnh câu trước:" not in str(last_question or ""):
        clean_ans = _re.sub(r"#+\s+", "", clean_ans)
        parts.append(f"Trả lời trước: {clean_ans[:200]}")
    return "\n".join(part for part in parts if part)
