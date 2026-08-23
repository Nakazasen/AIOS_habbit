# -*- coding: utf-8 -*-
"""Automated Unit Tests for Centralized i18n Subsystem (Milestone 1).

Validates:
- 100% translation key parity across Vietnamese, Japanese, and Simplified Chinese.
- Fallback mechanisms on missing keys and unknown locales.
- AI language instruction injection with mandatory citation and evidence preservation.
- Evidence Graph vocabulary coverage.
- UTF-8 anti-mojibake integrity across all three languages.
"""
from __future__ import annotations

import json
import pytest

from aios_habit.i18n import (
    DEFAULT_LOCALE,
    LOCALE_NAMES,
    SUPPORTED_LOCALES,
    TRANSLATIONS,
    get_ai_language_instruction,
    get_supported_locales,
    normalize_locale,
    t,
)


def test_supported_locales_constants() -> None:
    """Verify supported locales and default fallback."""
    assert "vi" in SUPPORTED_LOCALES
    assert "ja" in SUPPORTED_LOCALES
    assert "zh-CN" in SUPPORTED_LOCALES
    assert DEFAULT_LOCALE == "vi"
    assert len(SUPPORTED_LOCALES) == 3


def test_get_supported_locales() -> None:
    """Verify get_supported_locales returns (code, name) tuples."""
    locales = get_supported_locales()
    assert len(locales) == 3
    assert ("vi", "Tiếng Việt") in locales
    assert ("ja", "日本語") in locales
    assert ("zh-CN", "简体中文") in locales


def test_normalize_locale_variations() -> None:
    """Verify normalize_locale correctly maps regional and formatted strings."""
    # Vietnamese
    assert normalize_locale("vi") == "vi"
    assert normalize_locale("vi-VN") == "vi"
    assert normalize_locale("vi_VN") == "vi"
    assert normalize_locale("VIETNAMESE") == "vi"

    # Japanese
    assert normalize_locale("ja") == "ja"
    assert normalize_locale("ja-JP") == "ja"
    assert normalize_locale("ja_JP") == "ja"
    assert normalize_locale("japanese") == "ja"

    # Chinese
    assert normalize_locale("zh") == "zh-CN"
    assert normalize_locale("zh-CN") == "zh-CN"
    assert normalize_locale("zh_CN") == "zh-CN"
    assert normalize_locale("zh-Hans") == "zh-CN"
    assert normalize_locale("zh-Hans-CN") == "zh-CN"
    assert normalize_locale("zh-SG") == "zh-CN"
    assert normalize_locale("chinese") == "zh-CN"

    # Invalid / None / Empty fallbacks
    assert normalize_locale(None) == "vi"
    assert normalize_locale("") == "vi"
    assert normalize_locale("   ") == "vi"
    assert normalize_locale("fr") == "vi"
    assert normalize_locale("de-DE") == "vi"
    assert normalize_locale("unknown_lang") == "vi"


def test_translations_key_parity_100_percent() -> None:
    """Verify 100% key parity across all three supported languages."""
    vi_keys = set(TRANSLATIONS["vi"].keys())
    ja_keys = set(TRANSLATIONS["ja"].keys())
    zh_keys = set(TRANSLATIONS["zh-CN"].keys())

    missing_in_ja = vi_keys - ja_keys
    extra_in_ja = ja_keys - vi_keys
    missing_in_zh = vi_keys - zh_keys
    extra_in_zh = zh_keys - vi_keys

    assert not missing_in_ja, f"Keys missing in Japanese dictionary: {missing_in_ja}"
    assert not extra_in_ja, f"Extra keys in Japanese dictionary: {extra_in_ja}"
    assert not missing_in_zh, f"Keys missing in Simplified Chinese dictionary: {missing_in_zh}"
    assert not extra_in_zh, f"Extra keys in Simplified Chinese dictionary: {extra_in_zh}"
    assert vi_keys == ja_keys == zh_keys


def test_all_translations_non_empty_and_valid() -> None:
    """Ensure all translation values are non-empty and non-whitespace."""
    for loc, d in TRANSLATIONS.items():
        assert loc in SUPPORTED_LOCALES
        for k, v in d.items():
            assert isinstance(v, str), f"Value for key '{k}' in '{loc}' is not a string"
            assert v.strip(), f"Value for key '{k}' in '{loc}' is empty or whitespace"


def test_t_lookup_exact_and_formatting() -> None:
    """Verify translation lookup for all languages with and without kwargs."""
    # Direct lookup
    assert t("open_notebook", locale="vi") == "Mở sổ"
    assert t("open_notebook", locale="ja") == "ノートを開く"
    assert t("open_notebook", locale="zh-CN") == "打开笔记本"

    # Kwargs formatting
    assert t("enabled_sources_count", locale="vi", count=3) == "Nguồn đang bật: 3"
    assert t("enabled_sources_count", locale="ja", count=5) == "有効なソース: 5"
    assert t("enabled_sources_count", locale="zh-CN", count=7) == "已启用来源: 7"


def test_t_fallback_behavior() -> None:
    """Verify fallback behavior for unknown locale, missing key, and invalid formatting."""
    # Unknown locale falls back to Vietnamese
    assert t("open_notebook", locale="unknown_locale") == "Mở sổ"
    assert t("open_notebook", locale=None) == "Mở sổ"

    # Completely unknown key returns key itself
    assert t("completely_unknown_key_xyz", locale="ja") == "completely_unknown_key_xyz"
    assert t("completely_unknown_key_xyz", locale="vi") == "completely_unknown_key_xyz"

    # Formatting error gracefully returns template string
    assert t("enabled_sources_count", locale="vi", wrong_arg=123) == "Nguồn đang bật: {count}"


def test_ai_language_instruction_injection() -> None:
    """Verify AI prompt language instruction injection in vi, ja, and zh-CN."""
    # Vietnamese
    vi_instr = get_ai_language_instruction("vi")
    assert "Tiếng Việt" in vi_instr
    assert "[1]" in vi_instr
    assert "document.pdf" in vi_instr
    assert "không dịch" in vi_instr or "Giữ nguyên" in vi_instr

    # Japanese
    ja_instr = get_ai_language_instruction("ja")
    assert "日本語" in ja_instr
    assert "[1]" in ja_instr
    assert "document.pdf" in ja_instr
    assert "翻訳せず" in ja_instr

    # Simplified Chinese
    zh_instr = get_ai_language_instruction("zh-CN")
    assert "简体中文" in zh_instr
    assert "[1]" in zh_instr
    assert "document.pdf" in zh_instr
    assert "严禁翻译" in zh_instr

    # Invalid / fallback
    fallback_instr = get_ai_language_instruction("invalid_locale")
    assert fallback_instr == vi_instr


def test_evidence_graph_vocabulary_coverage() -> None:
    """Verify all critical Evidence Graph terms exist and are localized."""
    evidence_graph_keys = [
        "evidence_graph",
        "evidence_graph_title",
        "nodes",
        "edges",
        "claims",
        "citations",
        "verifications",
        "node_type_question",
        "node_type_claim",
        "node_type_evidence",
        "node_type_source",
        "node_type_inference",
        "node_type_limitation",
        "node_type_action",
        "node_type_verification",
        "edge_supports",
        "edge_refutes",
        "edge_cites",
        "edge_derives_from",
        "edge_depends_on",
        "edge_contradicts",
        "edge_verifies",
        "edge_limits",
        "edge_recommends",
        "claim_direct_observation",
        "claim_inferred",
        "claim_unsupported",
        "citation_ref_id",
        "citation_source_title",
        "citation_snippet",
        "verification_status_verified",
        "verification_status_unverified",
        "verification_status_disputed",
        "verification_status_insufficient_evidence",
        "confidence_high",
        "confidence_medium",
        "confidence_low",
    ]

    for key in evidence_graph_keys:
        for loc in ("vi", "ja", "zh-CN"):
            val = t(key, locale=loc)
            assert val != key, f"Key '{key}' was not translated in locale '{loc}'"
            assert len(val.strip()) > 0


def test_utf8_anti_mojibake_serialization() -> None:
    """Verify multi-language strings serialize and deserialize without corruption."""
    multilingual_dict = {
        "vi": "Hệ thống AIOS WorkLens: truy xuất thông tin, đối soát bằng chứng và bảo toàn ngữ cảnh.",
        "ja": "証拠トレース契約：検索結果の引用ID、ファイルパス、抽出テキストの完全性検証。",
        "zh": "基于证据追踪的多语言工作区对话系统：中文分词与结构化数据校验。",
        "mixed": "[E1] /path/to/報告書_2026.xlsx -> ERR_NULL_POINTER: 処理失敗 (dữ liệu không hợp lệ)",
    }

    serialized = json.dumps(multilingual_dict, ensure_ascii=False, indent=2)
    # Ensure raw UTF-8 characters are in the JSON string, not \u escaped
    assert "Hệ thống" in serialized
    assert "証拠トレース契約" in serialized
    assert "基于证据追踪" in serialized

    deserialized = json.loads(serialized)
    assert deserialized == multilingual_dict


def test_t_formatting_with_multilingual_values() -> None:
    """Verify formatting works seamlessly with multilingual strings passed as kwargs."""
    assert t("enabled_sources_count", locale="vi", count="3 (Sổ tài liệu)") == "Nguồn đang bật: 3 (Sổ tài liệu)"
    assert t("enabled_sources_count", locale="ja", count="5 (マイノートブック)") == "有効なソース: 5 (マイノートブック)"
    assert t("enabled_sources_count", locale="zh-CN", count="7 (我的笔记本)") == "已启用来源: 7 (我的笔记本)"


def test_normalize_locale_extended_cases() -> None:
    """Verify normalize_locale handles tricky inputs such as non-strings and mixed case."""
    assert normalize_locale(123) == "vi"  # Non-string input
    assert normalize_locale(["vi"]) == "vi"  # Non-string list
    assert normalize_locale("ZH-HANS") == "zh-CN"
    assert normalize_locale("ZH-SG") == "zh-CN"
    assert normalize_locale("VI-VN") == "vi"
    assert normalize_locale("JA-JP") == "ja"
    assert normalize_locale("   ja_jp   ") == "ja"
    assert normalize_locale("   zh_hans_cn   ") == "zh-CN"
