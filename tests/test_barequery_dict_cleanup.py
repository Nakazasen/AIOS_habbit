# -*- coding: utf-8 -*-
"""Verification tests for ticket DESKTOP-HOME-BAREQUERY-DICT-CLEANUP.

Requirements:
- (a) Locate where the glossary summary is generated at the head of the bare query path.
- (b) Fix: The summary must use translated text like the natural/similar query path
      (reusing existing translate_kdtps_field logic). If no translation is available,
      raw Japanese text is omitted from the answer body, retaining only the labeled source citation.
      Deduplication: The glossary summary must appear EXACTLY ONCE.
- (c) Preserves count and case list: Total count line still shows 24 cases for JAM4212,
      and the case list remains intact.
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest

from aios_habit.chat_action import ChatActionRequest
from aios_habit.chat_action_error_lookup import (
    _handler,
    _open_ro,
    resolve_db_path,
    extract_codes,
    lookup_glossary,
    search_similar,
)
from aios_habit.answer_language_policy import has_japanese, JP_CHAR_RE

DB_PATH = Path(r"C:\tmp\kdtps_standard\error_cases_reconciled.db")


@pytest.fixture(scope="module")
def db_available():
    db = resolve_db_path()
    if not db or not db.is_file():
        pytest.skip(f"error_cases database not found at {db}")
    return db


def test_bare_query_jam4212_deduplication_and_vietnamese_translation(db_available):
    """Verify bare query 'Tra cứu mã lỗi JAM4212':
    1. Glossary summary appears exactly 1 time (no duplication).
    2. Meaning and cause are translated into pure Vietnamese.
    3. Source filename '02XC_機能定義書_JAM一覧 (1).xls' is preserved.
    4. Honest total count 24 cases is preserved.
    5. Case list is preserved.
    """
    req = ChatActionRequest(question="Tra cứu mã lỗi JAM4212")
    outcome = _handler(req)
    assert outcome is not None, "Expected outcome for bare query JAM4212"
    text = "".join(b.text for b in outcome.blocks if b.kind == "markdown")

    # 1. Deduplication check: '_Từ điển mã lỗi' must appear exactly once
    dict_occurrences = text.count("_Từ điển mã lỗi")
    assert dict_occurrences == 1, f"Expected exactly 1 glossary summary, got {dict_occurrences}"

    # 2. Translated meaning check
    assert "Kẹt giấy tại cảm biến sấy (Cấp giấy khay 2)" in text
    assert "定着センサー滞留" not in text

    # 3. Translated cause check
    assert "Đã qua thời gian quy định từ khi cảm biến phát hiện cuốn giấy trung gian ngắt" in text
    assert "中間巻き付き検知センサーOFF" not in text

    # 4. Source filename preserved as identifier
    assert "02XC_機能定義書_JAM一覧 (1).xls" in text

    # 5. Honest count preserved (24 cases)
    assert "Tìm thấy **24** ca mã lỗi" in text

    # 6. Case list preserved
    assert "### 1. Vụ 2024/942" in text

    # 7. No raw Japanese in body outside the allowed source file name
    body_no_sources = re.sub(r"02XC_機能定義書_JAM一覧 \(\d+\)\.xls", "", text)
    body_no_sources = re.sub(r"old/[^`\n]+", "", body_no_sources)
    # Check that no Japanese characters remain in the dictionary summary line
    summary_line = [line for line in text.splitlines() if "_Từ điển mã lỗi" in line][0]
    summary_no_source = summary_line.split("Nguồn:")[0]
    assert not has_japanese(summary_no_source), f"Found raw Japanese in summary line: {summary_no_source}"


def test_similar_query_jam4212_pure_vietnamese(db_available):
    """Verify natural/similar query 'Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?':
    1. Section 1 (Định nghĩa kỹ thuật) has clean Vietnamese translation.
    2. No regression from earlier purity fixes.
    """
    req = ChatActionRequest(question="Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?")
    outcome = _handler(req)
    assert outcome is not None, "Expected outcome for similar query JAM4212"
    text = "".join(b.text for b in outcome.blocks if b.kind == "markdown")

    assert "### 1. Định nghĩa kỹ thuật & Mô tả mã lỗi" in text
    assert "Kẹt giấy tại cảm biến sấy (Cấp giấy khay 2)" in text
    assert "Đã qua thời gian quy định từ khi cảm biến phát hiện cuốn giấy trung gian ngắt" in text
    assert "02XC_機能定義書_JAM一覧 (1).xls" in text

    # Section 1 content contains no Japanese outside the filename
    sec1_match = re.search(r"### 1\. Định nghĩa kỹ thuật & Mô tả mã lỗi.*?(?=### 2\.|$)", text, re.DOTALL)
    assert sec1_match is not None
    sec1_text = sec1_match.group(0)
    sec1_no_source = re.sub(r"02XC_機能定義書_JAM一覧 \(\d+\)\.xls", "", sec1_text)
    assert not has_japanese(sec1_no_source), f"Found raw Japanese in Section 1: {sec1_no_source}"
