# -*- coding: utf-8 -*-
"""Comprehensive regression and purity tests for ticket DESKTOP-HOME-ANSWER-LANGUAGE-PURITY-FIX.

Tests:
1. Question language detection and Japanese override exceptions.
2. Field-level translation of KDTPS technical terms, causes, remedies, phenomena.
3. Verification of C6770: "不要" elimination, no raw Japanese leaks, content preservation.
4. Verification of JAM4212: paper jam sensor mechanism and causes translated to Vietnamese.
5. Verification of F000: multi-line Japanese glossary and all 6 remedies translated.
6. Permitted identifier preservation: document names (*.xls, *.xlsx) and codes kept intact.
7. Continuous improvement logging in local_cases/answer_language_events.jsonl.
8. Regression: card summary and synthesized answer structure integrity.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import pytest

from aios_habit.answer_language_policy import (
    clean_katakana_middle_dots,
    has_japanese,
    is_vietnamese_question,
    log_language_purity_event,
    purify_markdown_text,
    translate_kdtps_field,
)
from aios_habit.chat_action import ChatActionRequest
from aios_habit.chat_action_error_lookup import (
    _open_ro,
    _render_cards,
    _render_synthesized_answer,
    extract_codes,
    lookup_glossary,
    resolve_db_path,
    search_similar,
)

JP_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")


class TestAnswerLanguagePolicy:
    """Core language policy rules (2.2)."""

    def test_is_vietnamese_question_detection(self):
        # Vietnamese queries
        assert is_vietnamese_question("Mã lỗi C6770 nguyên nhân là gì?") is True
        assert is_vietnamese_question("C6770") is True
        assert is_vietnamese_question("khắc phục lỗi kẹt giấy JAM4212") is True
        assert is_vietnamese_question("các ca của máy Iris năm 2024") is True

        # Valid exceptions: Japanese queries or explicit requests
        assert is_vietnamese_question("C6770のエラー原因は何ですか？") is False
        assert is_vietnamese_question("F000の対策を教えてください") is False
        assert is_vietnamese_question("Trích nguyên văn tiếng Nhật tài liệu tham chiếu") is False
        assert is_vietnamese_question("Mã lỗi này tiếng Nhật là gì?") is False
        assert is_vietnamese_question("Dịch câu trả lời sang tiếng Nhật") is False

    def test_translate_kdtps_fields(self):
        # Cause context
        c_trans, act = translate_kdtps_field("不要", field_name="cause")
        assert act == "dich"
        assert "Không xác định nguyên nhân bất thường" in c_trans

        # Remedy context
        r_trans, act = translate_kdtps_field("不要", field_name="remedy")
        assert act == "dich"
        assert "Không cần đối sách bổ sung" in r_trans

        # Electrical / Mechanical causes
        assert "Phần điện" in translate_kdtps_field("部品要因(電気)", "cause")[0]
        assert "Phần điện" in translate_kdtps_field("要因不明(電気)", "cause")[0]
        assert "Cơ khí" in translate_kdtps_field("原因不明（メカ）", "cause")[0]
        assert "Nhà cung cấp" in translate_kdtps_field("部品要因(Supplier)", "cause")[0]
        assert "Gia công ngoài" in translate_kdtps_field("部品要因(外制)", "cause")[0]
        assert "Linh kiện an toàn quan trọng" in translate_kdtps_field("安全重要部品", "general")[0]

        # Machine suffixes
        assert "Hạ vị" in translate_kdtps_field("Iris2020 下位", "machine")[0]
        assert "Thượng vị" in translate_kdtps_field("Iris2024 上位", "machine")[0]

        # Phenomena
        assert "Màn hình LCD hiển thị F000" in translate_kdtps_field("LCD画面にF000表示", "phenomenon")[0]
        assert "Màn hình LCD trắng xóa" in translate_kdtps_field("LCD画面　真っ白", "phenomenon")[0]
        assert "LSU SKEW không thể điều chỉnh" in translate_kdtps_field("LSU SKEW　調整不可", "phenomenon")[0]

    def test_clean_katakana_middle_dots(self):
        text = "・UNIT IH - Bản mạch IH <br>・Bản mạch IH - Bản mạch Engine"
        cleaned = clean_katakana_middle_dots(text)
        assert "・" not in cleaned
        assert "• UNIT IH" in cleaned

    def test_continuous_improvement_logging(self, tmp_path):
        log_file = tmp_path / "answer_language_events.jsonl"
        log_language_purity_event(
            question="C6770",
            route="test_route",
            detected_count=3,
            actions=["dich", "giu-dinh-danh"],
            details=[{"field": "cause", "raw": "不要", "trans": "Đã giải quyết"}],
            conversation_id="CONV-TEST-001",
            base_cases_dir=tmp_path,
        )
        assert log_file.exists()
        lines = log_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["route"] == "test_route"
        assert rec["detected_count"] == 3
        assert rec["actions"] == ["dich", "giu-dinh-danh"]
        assert rec["conversation_id"] == "CONV-TEST-001"


class TestRealDatabaseAnswers:
    """Verifies actual synthesized answers and cards against real database."""

    @pytest.fixture(scope="class")
    def db_conn(self):
        req = ChatActionRequest(question="C6770", notebook_id="NB-LAZY-DTL")
        p = resolve_db_path(req)
        assert p is not None and p.exists()
        conn = _open_ro(p)
        yield conn
        conn.close()

    def test_c6770_synthesized_answer_purity(self, db_conn):
        cases, codes, total = search_similar(db_conn, "Mã lỗi C6770 nguyên nhân là gì?")
        gloss = lookup_glossary(db_conn, codes)
        ans = _render_synthesized_answer(cases, codes, gloss, total, "Mã lỗi C6770 nguyên nhân là gì?")

        # 1. No raw "不要" standing alone
        assert not re.search(r"\b不要\b", ans)
        assert "- **Nguyên nhân 2:** 不要" not in ans
        assert "- **Đối sách:** 不要" not in ans

        # 2. Number of causes preserved (not dropped)
        assert "### 2. Nguyên nhân chính theo các báo cáo điều tra thực tế" in ans
        cause_matches = re.findall(r"- \*\*Nguyên nhân \d+:\*\*", ans)
        assert len(cause_matches) >= 2

        # 3. Only permitted identifiers have Japanese
        lines = ans.splitlines()
        for idx, line in enumerate(lines):
            if JP_RE.search(line):
                # Must be a document reference or filename
                assert any(ext in line for ext in [".xls", ".xlsx", ".pdf", ".csv"]) or "`" in line, (
                    f"Forbidden Japanese at line {idx}: {line}"
                )

    def test_jam4212_synthesized_answer_purity(self, db_conn):
        cases, codes, total = search_similar(db_conn, "Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?")
        gloss = lookup_glossary(db_conn, codes)
        ans = _render_synthesized_answer(cases, codes, gloss, total, "Mã lỗi JAM4212 nguyên nhân và xử lý thế nào?")

        # 1. Technical definition translated
        assert "定着センサー滞留" not in ans
        assert "Kẹt giấy tại cảm biến sấy" in ans

        # 2. Mechanism translated
        assert "中間巻き付き検知センサーOFF" not in ans
        assert "cảm biến phát hiện cuốn giấy trung gian ngắt (OFF)" in ans

        # 3. Causes translated
        assert "原因不明（メカ）" not in ans
        assert "Không rõ nguyên nhân (Cơ khí)" in ans

        # 4. Only permitted identifiers have Japanese
        lines = ans.splitlines()
        for idx, line in enumerate(lines):
            if JP_RE.search(line):
                assert any(ext in line for ext in [".xls", ".xlsx", ".pdf", ".csv"]) or "`" in line, (
                    f"Forbidden Japanese in JAM4212 at line {idx}: {line}"
                )

    def test_f000_synthesized_answer_purity(self, db_conn):
        cases, codes, total = search_similar(db_conn, "Mã lỗi F000 nguyên nhân và biện pháp xử lý là gì?")
        gloss = lookup_glossary(db_conn, codes)
        ans = _render_synthesized_answer(cases, codes, gloss, total, "Mã lỗi F000 nguyên nhân và biện pháp xử lý là gì?")

        # 1. Welcome screen message translated
        assert "Welcome画面のまま" not in ans
        assert "Màn hình dừng ở màn hình Welcome" in ans

        # 2. All 6 remedies translated into Vietnamese
        remedy_matches = re.findall(r"- \*\*Biện pháp \d+:\*\*", ans)
        assert len(remedy_matches) >= 6
        assert "Kiểm tra trạng thái kết nối của dây cáp" in ans
        assert "Thay thế bản mạch Main và kiểm tra hoạt động" in ans

        # 3. Only permitted identifiers have Japanese
        lines = ans.splitlines()
        for idx, line in enumerate(lines):
            if JP_RE.search(line):
                assert any(ext in line for ext in [".xls", ".xlsx", ".pdf", ".csv"]) or "`" in line, (
                    f"Forbidden Japanese in F000 at line {idx}: {line}"
                )

    def test_cards_rendering_purity(self, db_conn):
        cases, codes, total = search_similar(db_conn, "C6770")
        gloss = lookup_glossary(db_conn, codes)
        cards_text = _render_cards(cases, codes, gloss, total)

        # Cards must not contain raw 不要
        assert "- **Nguyên nhân:** 不要" not in cards_text
        assert "- **Đối sách:** 不要" not in cards_text

        # Lines must be pure Vietnamese or permitted filenames
        lines = cards_text.splitlines()
        for idx, line in enumerate(lines):
            if JP_RE.search(line):
                assert any(ext in line for ext in [".xls", ".xlsx", ".pdf", ".csv"]) or "`" in line, (
                    f"Forbidden Japanese in cards at line {idx}: {line}"
                )
