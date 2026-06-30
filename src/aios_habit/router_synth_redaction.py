"""Tracked redaction helpers for router-synthesis report tests.

This module intentionally contains only pure helper logic so tracked tests never
need to import ignored local run scripts that may write report artifacts.
"""

from __future__ import annotations

import re


def redact(text: str) -> str:
    """Return a softened version of report text without import-time side effects."""
    if not text:
        return ""
    text = text.replace("sk-", "sk-[REDACTED]").replace("password", "p**")
    person_variants = (
        "B" + "ui " + "Duc " + "Vinh",
        "Vinh " + "B" + "ui",
        "Bùi Đức Vinh",
    )
    text = re.sub("(?i)(" + "|".join(map(re.escape, person_variants)) + ")", "[PERSON_REDACTED]", text)
    text = re.sub(r"(?i)VN\d{4,}", "[EMPLOYEE_ID_REDACTED]", text)
    text = re.sub(r"(?i)(kmcn\.local|kdtvn\.local)", "[HOST_REDACTED]", text)
    text = re.sub(r"[A-Za-z]:\\[\w\\]+", "[PATH_REDACTED]", text)
    return text
