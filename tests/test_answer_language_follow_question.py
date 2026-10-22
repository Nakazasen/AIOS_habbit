# -*- coding: utf-8 -*-
"""Test suite for ticket DESKTOP-HOME-ANSWER-LANGUAGE-FOLLOW-QUESTION.

Covers:
1. Question language detection across vi, ja, zh-CN, en, and mixed queries.
2. Natural question vs bare lookup detection in vi, ja, and zh-CN.
3. Multilingual card rendering (Gate 3) with exact count 136 preserved.
4. Multilingual synthesized answer rendering (Gates 1 & 2).
5. Markdown text purification preserving target locale scripts.
6. RAG-v2 synthesis prompt language rule and bidirectional script mismatch validator.
7. Multilingual 5-tier ladder and draft fallback answers.
"""

from __future__ import annotations

import re
import pytest

from aios_habit.answer_language_policy import (
    detect_question_language,
    is_vietnamese_question,
    purify_markdown_text,
)
from aios_habit.chat_action import ChatActionRequest
from aios_habit.chat_action_error_lookup import (
    _open_ro,
    _render_cards,
    _render_synthesized_answer,
    extract_codes,
    is_natural_question,
    lookup_glossary,
    resolve_db_path,
    search_similar,
)
from aios_habit.rag_v2.synthesis import _provider_answer_has_script_mismatch


class TestQuestionLanguageDetection:
    """Verifies deterministic language detection from user question."""

    def test_vietnamese_questions(self):
        assert detect_question_language("Nguyên nhân lỗi C7620 là gì?") == "vi"
        assert detect_question_language("Lỗi kẹt giấy JAM4212 xử lý thế nào?") == "vi"
        assert detect_question_language("Các ca lỗi máy Iris năm 2024") == "vi"
        assert detect_question_language("C7620") == "vi"
        assert is_vietnamese_question("Nguyên nhân C7620") is True

    def test_japanese_questions(self):
        # Questions with Kana
        assert detect_question_language("C7620エラーの原因は何ですか？") == "ja"
        assert detect_question_language("用紙詰まりの対処法を教えてください") == "ja"
        assert detect_question_language("JAM4212の件数は？") == "ja"
        # Questions with Japanese particle markers
        assert detect_question_language("C7620の原因と対策") == "ja"
        assert detect_question_language("C7620の再発件数") == "ja"
        # Explicit Japanese requests
        assert detect_question_language("trả lời bằng tiếng nhật về C7620") == "ja"
        assert detect_question_language("answer in japanese about C7620") == "ja"
        assert detect_question_language("日本語で答えてください") == "ja"
        assert is_vietnamese_question("C7620の原因は何ですか？") is False

    def test_chinese_questions(self):
        # Simplified Chinese questions (Hanzi without Kana)
        assert detect_question_language("C7620故障的原因是什么？") == "zh-CN"
        assert detect_question_language("打印机卡纸如何处理？") == "zh-CN"
        assert detect_question_language("请问这个报错怎么解决？") == "zh-CN"
        # Chinese question markers
        assert detect_question_language("C7620发生原因与对策") == "zh-CN"
        assert detect_question_language("为什么报错C7620") == "zh-CN"
        # Explicit Chinese requests
        assert detect_question_language("trả lời bằng tiếng trung về C7620") == "zh-CN"
        assert detect_question_language("answer in chinese") == "zh-CN"
        assert detect_question_language("用中文回答") == "zh-CN"
        assert is_vietnamese_question("C7620故障的原因是什么？") is False

    def test_english_and_other_languages_fallback_to_vietnamese(self):
        # Ticket requirement: English and other languages retain Vietnamese answer
        assert detect_question_language("What is the cause of error C7620?") == "vi"
        assert detect_question_language("How to resolve paper jam JAM4212?") == "vi"
        assert detect_question_language("Please explain error C6770") == "vi"

    def test_mixed_queries(self):
        # Vietnamese with technical terms
        assert detect_question_language("Check log lỗi C7620 sensor giúp tôi") == "vi"
        assert detect_question_language("Số ca C7620 trong năm 2025") == "vi"
        # Japanese with alphanumeric codes
        assert detect_question_language("C7620のエラーコード調査") == "ja"
        # Chinese with alphanumeric codes
        assert detect_question_language("查询C7620错误代码") == "zh-CN"


class TestNaturalQuestionDetection:
    """Verifies distinction between natural questions and bare lookups across locales."""

    def test_vietnamese_queries(self):
        assert is_natural_question("Nguyên nhân lỗi C7620 là gì?") is True
        assert is_natural_question("C7620 khắc phục như thế nào") is True
        assert is_natural_question("C7620") is False

    def test_japanese_queries(self):
        assert is_natural_question("C7620エラーの原因は何ですか？") is True
        assert is_natural_question("C7620の原因と対策") is True
        assert is_natural_question("C7620の対策方法") is True
        assert is_natural_question("C7620") is False
        assert is_natural_question("C7620 エラー") is False

    def test_chinese_queries(self):
        assert is_natural_question("C7620故障的原因是什么？") is True
        assert is_natural_question("C7620 发生原因和对策") is True
        assert is_natural_question("C7620如何排查处理") is True
        assert is_natural_question("C7620") is False
        assert is_natural_question("C7620 错误") is False


class TestDatabaseRenderLanguageParity:
    """Verifies rendering of cards and synthesized answers across vi, ja, and zh-CN."""

    @pytest.fixture(scope="class")
    def db_conn(self):
        req = ChatActionRequest(question="C7620", notebook_id="NB-LAZY-DTL")
        p = resolve_db_path(req)
        assert p is not None and p.exists()
        conn = _open_ro(p)
        yield conn
        conn.close()

    def test_c7620_exact_case_count_integrity(self, db_conn):
        cases, codes, total = search_similar(db_conn, "C7620")
        assert "C7620" in codes
        assert total == 30075
        assert cases[0].get("exact_count") == 136

    def test_c7620_cards_multilingual(self, db_conn):
        cases, codes, total = search_similar(db_conn, "C7620")
        gloss = lookup_glossary(db_conn, codes)

        # 1. Vietnamese cards
        ans_vi = _render_cards(cases, codes, gloss, total, question="C7620", target_locale="vi")
        assert "136" in ans_vi
        assert "C7620" in ans_vi
        assert "Vụ" in ans_vi
        assert "Nguyên nhân:" in ans_vi or "Từ điển" in ans_vi

        # 2. Japanese cards (Gate 3 requirement)
        ans_ja = _render_cards(cases, codes, gloss, total, question="C7620の件数は？", target_locale="ja")
        assert "136" in ans_ja
        assert "C7620" in ans_ja
        assert "事例" in ans_ja
        # Verify Japanese headings from i18n
        assert "現象" in ans_ja
        assert "原因" in ans_ja
        assert "対策" in ans_ja
        # Verify raw Japanese content is preserved without unconditional translation to Vietnamese
        assert any(term in ans_ja for term in ["カラーレジスト", "IDセンサー", "転写ベルト", "ドラム", "基板", "コネクター", "LSU"])

        # 3. Simplified Chinese cards (Gate 3 requirement)
        ans_zh = _render_cards(cases, codes, gloss, total, question="C7620 发生次数", target_locale="zh-CN")
        assert "136" in ans_zh
        assert "C7620" in ans_zh
        assert "事例" in ans_zh
        assert "现象" in ans_zh
        assert "原因" in ans_zh
        assert "对策" in ans_zh

    def test_c7620_synthesized_answer_multilingual(self, db_conn):
        q_vi = "Nguyên nhân lỗi C7620 là gì?"
        cases, codes, total = search_similar(db_conn, q_vi)
        gloss = lookup_glossary(db_conn, codes)

        # 1. Vietnamese synthesized answer (Gate 4 regression)
        ans_vi = _render_synthesized_answer(cases, codes, gloss, total, q_vi, target_locale="vi")
        assert "136" in ans_vi
        assert "C7620" in ans_vi
        assert "1. Định nghĩa kỹ thuật" in ans_vi
        assert "2. Nguyên nhân chính" in ans_vi
        assert "3. Đối sách" in ans_vi
        assert "4. Danh sách các ca điều tra" in ans_vi

        # 2. Japanese synthesized answer (Gate 1 requirement)
        q_ja = "C7620エラーの原因は何ですか？"
        ans_ja = _render_synthesized_answer(cases, codes, gloss, total, q_ja, target_locale="ja")
        assert "136" in ans_ja
        assert "C7620" in ans_ja
        assert "1. 技術的定義" in ans_ja
        assert "2. 実際の調査報告" in ans_ja
        assert "3. 調査報告に基づく対策" in ans_ja
        assert "4. 照合対象の実調査事例一覧" in ans_ja
        # Accurate technical content
        assert any(term in ans_ja for term in ["カラーレジスト", "IDセンサー", "転写ベルト", "ドラム", "基板", "コネクター", "LSU"])

        # 3. Chinese synthesized answer (Gate 2 requirement)
        q_zh = "C7620故障的原因是什么？"
        ans_zh = _render_synthesized_answer(cases, codes, gloss, total, q_zh, target_locale="zh-CN")
        assert "136" in ans_zh
        assert "C7620" in ans_zh
        assert "1. 技术定义" in ans_zh
        assert "2. 实际调查报告" in ans_zh
        assert "3. 基于调查报告的对策" in ans_zh
        assert "4. 对应实际调查事例列表" in ans_zh


class TestPurifyMarkdownTextPerLocale:
    """Verifies purify_markdown_text preserves valid CJK characters according to target locale."""

    def test_purify_preserves_japanese_when_target_is_ja(self):
        text = "## 1. エラー定義\n- エラーコード: `C7620`\n・フラットケーブルの接触不良"
        purified = purify_markdown_text(text, "C7620エラーの原因は？", target_locale="ja")
        assert "エラー定義" in purified
        assert "接触不良" in purified
        # Middle dot converted to bullet
        assert "• フラットケーブル" in purified

    def test_purify_preserves_chinese_when_target_is_zh(self):
        text = "## 1. 错误定义\n- 错误代码: `C7620`\n排线接触不良，需要更换组件。"
        purified = purify_markdown_text(text, "C7620故障原因是什么？", target_locale="zh-CN")
        assert "错误定义" in purified
        assert "排线接触不良" in purified


class TestRagV2SynthesisMultilingual:
    """Verifies bidirectional script mismatch detection in RAG synthesis."""

    def test_script_mismatch_catches_wrong_language(self):
        # 1. Japanese question with purely Latin answer -> Mismatch!
        q_ja = "C7620エラーの原因は何ですか？"
        ans_latin = "The cause of error C7620 is flat cable disconnection."
        assert _provider_answer_has_script_mismatch(q_ja, ans_latin) is True

        # 2. Chinese question with purely Latin answer -> Mismatch!
        q_zh = "C7620故障的原因是什么？"
        assert _provider_answer_has_script_mismatch(q_zh, ans_latin) is True

        # 3. Vietnamese question with CJK answer -> Mismatch!
        q_vi = "Nguyên nhân lỗi C7620 là gì?"
        ans_ja = "エラーコードC7620の原因はフラットケーブルの不良です。"
        assert _provider_answer_has_script_mismatch(q_vi, ans_ja) is True

    def test_script_mismatch_passes_matching_language(self):
        # Japanese question with Japanese answer -> OK
        q_ja = "C7620エラーの原因は何ですか？"
        ans_ja = "エラーコードC7620の原因はフラットケーブルの接触不良または基板の故障です。"
        assert _provider_answer_has_script_mismatch(q_ja, ans_ja) is False

        # Chinese question with Chinese answer -> OK
        q_zh = "C7620故障的原因是什么？"
        ans_zh = "错误代码C7620的主要原因是排线接触不良或主板故障。"
        assert _provider_answer_has_script_mismatch(q_zh, ans_zh) is False

        # Vietnamese question with Vietnamese answer -> OK
        q_vi = "Nguyên nhân lỗi C7620 là gì?"
        ans_vi = "Nguyên nhân chính của lỗi C7620 là do lỏng cáp dẹt hoặc hỏng bo mạch."
        assert _provider_answer_has_script_mismatch(q_vi, ans_vi) is False


class TestDraftFallbackAndFiveTierLadderMultilingual:
    """Verifies draft fallback and 5-tier ladder formatters in ja and zh-CN."""

    def test_format_draft_answer_multilingual(self):
        from aios_habit.answer_draft_fallback import DraftEntry, format_draft_answer

        entry = DraftEntry(
            question="C7620エラーの原因は？",
            answer="フラットケーブルの接触不良が原因です。",
            source_file="report.xlsx",
        )

        # Japanese
        draft_ja = format_draft_answer(entry, target_locale="ja")
        assert "フラットケーブル" in draft_ja
        assert "下書き" in draft_ja

        # Chinese
        draft_zh = format_draft_answer(entry, target_locale="zh-CN")
        assert "草稿" in draft_zh

    def test_format_tier_5_actions_markdown_multilingual(self):
        from aios_habit.final_answer_composer import format_tier_5_actions_markdown

        # Japanese
        res_ja = format_tier_5_actions_markdown([{"action": "ケーブル点検"}], target_locale="ja")
        assert "次のアクション" in res_ja or "推奨アクション" in res_ja or "ケーブル点検" in res_ja

        # Chinese
        res_zh = format_tier_5_actions_markdown([{"action": "检查排线"}], target_locale="zh-CN")
        assert "后续操作" in res_zh or "建议操作" in res_zh or "检查排线" in res_zh
