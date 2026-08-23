"""Empirical Adversarial Challenge Test Suite for AIOS_habbit Commit A.

Authored by Empirical Challenger (Agent 2) to stress-test:
1. AI language instruction injection across vi, ja, zh-CN and invalid fallbacks.
2. Invariant citation and evidence preservation across prompt construction and bridges.
3. Outcome classification & limitation marker detection (including negation & compound edge cases).
4. 100% translation dictionary key parity and robust fallback.
5. UTF-8 anti-mojibake serialization integrity.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import pytest

from aios_habit.antigravity_bridge import (
    AntigravityBridgeResponse,
    call_antigravity_bridge,
)
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
from aios_habit.workspace_chat_ai_answer import (
    PRIVACY_MODE_CLOUD_ALLOWED,
    WorkspaceAIAnswerRequest,
    WorkspaceAIAnswerResult,
    WorkspaceAIContextSource,
    _fold_for_outcome_classification,
    _get_ai_disclaimer,
    build_workspace_ai_prompt,
    classify_workspace_ai_outcome,
    generate_workspace_ai_answer,
)


# ===========================================================================
# 1. AI Language Instruction Injection & Normalization Stress Tests
# ===========================================================================

class TestLanguageInstructionInjectionAdversarial:
    """Stress-test language instruction injection and locale normalization."""

    @pytest.mark.parametrize(
        "locale_input,expected_norm,expected_keyword",
        [
            ("vi", "vi", "Tiếng Việt"),
            ("vi-VN", "vi", "Tiếng Việt"),
            ("vi_vn", "vi", "Tiếng Việt"),
            ("VIETNAMESE", "vi", "Tiếng Việt"),
            ("ja", "ja", "日本語"),
            ("ja-JP", "ja", "日本語"),
            ("ja_jp", "ja", "日本語"),
            ("JAPANESE", "ja", "日本語"),
            ("zh", "zh-CN", "简体中文"),
            ("zh-CN", "zh-CN", "简体中文"),
            ("zh_cn", "zh-CN", "简体中文"),
            ("zh-Hans", "zh-CN", "简体中文"),
            ("zh-Hans-CN", "zh-CN", "简体中文"),
            ("zh-SG", "zh-CN", "简体中文"),
            ("CHINESE", "zh-CN", "简体中文"),
            ("zh-cmn", "zh-CN", "简体中文"),
            # Fallbacks
            (None, "vi", "Tiếng Việt"),
            ("", "vi", "Tiếng Việt"),
            ("   ", "vi", "Tiếng Việt"),
            ("fr", "vi", "Tiếng Việt"),
            ("de-DE", "vi", "Tiếng Việt"),
            ("es-ES", "vi", "Tiếng Việt"),
            ("unknown_locale_xyz", "vi", "Tiếng Việt"),
            (12345, "vi", "Tiếng Việt"),
            (["invalid", "type"], "vi", "Tiếng Việt"),
        ],
    )
    def test_normalize_locale_and_instruction_variants(
        self, locale_input: Any, expected_norm: str, expected_keyword: str
    ) -> None:
        """Verify normalization handles all expected variants, casing, and fallback types."""
        norm = normalize_locale(locale_input)
        assert norm == expected_norm
        instr = get_ai_language_instruction(locale_input)
        assert expected_keyword in instr
        assert "[1]" in instr
        assert "document.pdf" in instr

    def test_prompt_composer_headers_and_roles_across_all_languages(self) -> None:
        """Verify build_workspace_ai_prompt generates correct headers and roles for all 3 languages."""
        history = (
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
            {"role": "system", "content": "Inherited summary"},
        )
        src = WorkspaceAIContextSource(
            source_id="src_test",
            source_scope="notebook",
            source_type="xlsx",
            title="inventory_2026.xlsx",
            privacy_label="cloud_allowed",
            text="Item A: 100 units [1]",
            included_chars=22,
            truncated=False,
        )

        # 1. Vietnamese
        sys_vi, user_vi = build_workspace_ai_prompt(
            "Tồn kho là bao nhiêu?", (src,), history, answer_language="vi"
        )
        assert "Yêu cầu ngôn ngữ: Trả lời hoàn toàn bằng Tiếng Việt." in sys_vi
        assert "--- LỊCH SỬ HỘI THOẠI GẦN ĐÂY ---" in user_vi
        assert "[Người dùng]: Previous question" in user_vi
        assert "[Ngữ cảnh kế thừa]: Inherited summary" in user_vi
        assert "--- CÂU HỎI MỚI NHẤT ---" in user_vi
        assert "NGUỒN 1" in user_vi
        assert "Tiêu đề: inventory_2026.xlsx" in user_vi
        assert "Loại: Excel" in user_vi
        assert "Nội dung:" in user_vi

        # 2. Japanese
        sys_ja, user_ja = build_workspace_ai_prompt(
            "在庫数はいくつですか？", (src,), history, answer_language="ja"
        )
        assert "言語指示: 回答はすべて日本語で記述してください。" in sys_ja
        assert "--- 最近の会話履歴 ---" in user_ja
        assert "[ユーザー]: Previous question" in user_ja
        assert "[継承コンテキスト]: Inherited summary" in user_ja
        assert "--- 最新の質問 ---" in user_ja
        assert "ソース 1" in user_ja
        assert "タイトル: inventory_2026.xlsx" in user_ja
        assert "種別: Excel" in user_ja
        assert "内容:" in user_ja

        # 3. Simplified Chinese
        sys_zh, user_zh = build_workspace_ai_prompt(
            "库存数量是多少？", (src,), history, answer_language="zh-CN"
        )
        assert "语言指示: 请完全使用简体中文回答。" in sys_zh
        assert "--- 最近对话历史 ---" in user_zh
        assert "[用户]: Previous question" in user_zh
        assert "[继承上下文]: Inherited summary" in user_zh
        assert "--- 最新问题 ---" in user_zh
        assert "来源 1" in user_zh
        assert "标题: inventory_2026.xlsx" in user_zh
        assert "类型: Excel" in user_zh
        assert "内容:" in user_zh

    def test_bridge_language_instruction_injection_and_deduplication(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify call_antigravity_bridge injects language instruction without duplicating."""
        captured_payloads: List[Dict[str, Any]] = []

        def mock_urlopen(req: Any, timeout: Any = None) -> Any:
            data = json.loads(req.data.decode("utf-8"))
            captured_payloads.append(data)
            resp = MagicMock()
            resp.read.return_value = json.dumps({
                "choices": [{"message": {"content": "Bridge mocked response"}}]
            }).encode("utf-8")
            return resp

        import urllib.request
        from unittest.mock import MagicMock
        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

        # 1. No existing system prompt -> injects ja instruction
        call_antigravity_bridge(
            question="テスト質問",
            system_prompt="",
            answer_language="ja",
            privacy_mode="cloud_allowed",
        )
        assert len(captured_payloads) == 1
        sys_msg_1 = captured_payloads[0]["messages"][0]["content"]
        assert "言語指示: 回答はすべて日本語で記述してください。" in sys_msg_1

        # 2. Existing custom system prompt -> appends zh-CN instruction
        call_antigravity_bridge(
            question="测试问题",
            system_prompt="You are a system expert.",
            answer_language="zh-CN",
            privacy_mode="cloud_allowed",
        )
        assert len(captured_payloads) == 2
        sys_msg_2 = captured_payloads[1]["messages"][0]["content"]
        assert "You are a system expert." in sys_msg_2
        assert "语言指示: 请完全使用简体中文回答。" in sys_msg_2

        # 3. Existing system prompt already containing language instruction -> does NOT duplicate
        pre_existing_prompt = "Custom prompt.\n\n语言指示: 请完全使用简体中文回答。"
        call_antigravity_bridge(
            question="测试问题2",
            system_prompt=pre_existing_prompt,
            answer_language="zh-CN",
            privacy_mode="cloud_allowed",
        )
        assert len(captured_payloads) == 3
        sys_msg_3 = captured_payloads[2]["messages"][0]["content"]
        assert sys_msg_3.count("语言指示:") == 1


# ===========================================================================
# 2. Invariant Citation & Evidence Preservation Adversarial Tests
# ===========================================================================

class TestInvariantCitationAndEvidencePreservation:
    """Stress-test that citation IDs, filenames, error codes, file paths, and snippets are never mutated."""

    def test_verbatim_preservation_complex_adversarial_payload(self) -> None:
        """Verify prompt builder preserves exact characters across adversarial delimiters and formatting codes."""
        adversarial_text = (
            "Citation references: [1], [E1], [E2], [EVD-001], [EVD-9923]\n"
            "File names: inventory_2026.xlsx, log_2026.txt, 財務報告_2026.pdf, 系统配置.json\n"
            "Error codes: HTTP 404, HTTP 500, ERR_TIMEOUT, ERR_NULL_POINTER, 0x80070005\n"
            "Paths: /etc/nginx/nginx.conf, C:\\Windows\\System32\\drivers\\etc\\hosts, D:/Sandbox/data/report.pdf\n"
            "Formatting & Special: {key_name}, {{escaped_braces}}, %s, $HOME, <script>alert(1)</script>\n"
            "Raw table:\n| ID | Status | Note |\n| [E1] | OK | Verbatim |\n"
        )

        src = WorkspaceAIContextSource(
            source_id="src_adv_01",
            source_scope="notebook",
            source_type="plain_text",
            title="adversarial_test_log.txt",
            privacy_label="cloud_allowed",
            text=adversarial_text,
            included_chars=len(adversarial_text),
            truncated=False,
        )

        for lang in ("vi", "ja", "zh-CN"):
            sys_prompt, user_prompt = build_workspace_ai_prompt(
                question="Trích xuất các mã lỗi và mã trích dẫn?",
                context_sources=(src,),
                answer_language=lang,
            )

            # 1. Delimiter wrapping check
            assert "<<<SOURCE_CONTENT\n" in user_prompt
            assert "\nSOURCE_CONTENT" in user_prompt

            # 2. Exact verbatim content check inside SOURCE_CONTENT
            assert adversarial_text in user_prompt

            # 3. Individual critical token checks
            assert "[1]" in user_prompt
            assert "[E1]" in user_prompt
            assert "[EVD-001]" in user_prompt
            assert "inventory_2026.xlsx" in user_prompt
            assert "HTTP 404" in user_prompt
            assert "ERR_TIMEOUT" in user_prompt
            assert "/etc/nginx/nginx.conf" in user_prompt
            assert "C:\\Windows\\System32\\drivers\\etc\\hosts" in user_prompt
            assert "{key_name}" in user_prompt


# ===========================================================================
# 3. Outcome Classification & Limitation Marker Detection Stress Tests
# ===========================================================================

class TestOutcomeClassificationAdversarial:
    """Stress-test outcome classification, limitation marker detection, and complex negation logic."""

    @pytest.mark.parametrize(
        "limitation_phrase",
        [
            # Vietnamese (accented and unaccented)
            "Hiện tại chưa đủ thông tin để xác nhận cấu hình.",
            "Tài liệu không đủ thông tin chi tiết về ngân sách.",
            "Hệ thống không tìm thấy đủ thông tin trong sổ.",
            "Phân tích cho thấy chưa đủ bằng chứng kết luận.",
            "Báo cáo này không đủ bằng chứng thực tế.",
            "Dữ liệu cung cấp không đầy đủ.",
            "Không tìm thấy thông tin liên quan trong các nguồn.",
            "Không có nguồn nào đề cập đến sự cố.",
            "Không có thông tin trong tài liệu hướng dẫn.",
            "Nguồn không đề cập đến tham số này.",
            "Tài liệu không đề cập đến ngày phát hành.",
            "Dữ liệu không đề cập chi tiết triển khai.",
            "Kết luận này dựa trên bằng chứng hiện có.",
            "Đánh giá dựa trên thông tin hiện có.",
            "Chỉ có thể kết luận trong phạm vi thông tin được cấp.",
            "Trường hợp này thiếu bằng chứng xác thực.",
            "Hồ sơ hiện thiếu thông tin.",
            "Vụ việc chưa đủ chứng cứ pháp lý.",
            "Hiện tại không đủ chứng cứ.",
            # Japanese
            "提示された資料には十分な証拠がありません。",
            "サーバー設定に関する証拠が不十分です。",
            "該当するパラメータについて十分な情報がありません。",
            "ログ分析において情報が不足しています。",
            "利用可能な証拠に基づく推論となります。",
            "提供された証拠に基づく限り、問題は確認できません。",
            "提供された情報に基づく回答です。",
            "マニュアルには記載されていません。",
            "該当の関数は見つかりません。",
            "仕様書には言及されていません。",
            "証拠不足のため、追加ログが必要です。",
            "根拠不足により判断を保留します。",
            "情報不足のため再調査が必要です。",
            # Simplified Chinese
            "根据现有记录，目前证据不足以支持该结论。",
            "在现有文档中没有足够的证据。",
            "系统参数信息不足，无法推导。",
            "参考来源中没有足够的信息。",
            "结论是根据现有证据得出的。",
            "基于现有证据的分析如下。",
            "基于可用证据，服务状态正常。",
            "根据提供的信息，配置未生效。",
            "在提供的文件中未找到相关信息。",
            "来源未提及具体的超时时间。",
            "文档未提及该接口定义。",
            "依据现有材料，无法确定具体原因。",
            # English
            "We cannot determine from the provided documents.",
            "The root cause cannot be determined from these logs.",
            "There is not enough information to conclude.",
            "We have insufficient information to proceed.",
            "There is insufficient evidence to support the claim.",
            "There is no evidence in the uploaded files.",
            "The term was not found in the provided context.",
            "The sources do not mention any downtime.",
            "The documents do not mention database migration.",
            "Based on available evidence, the build passed.",
            "Based on the provided information, the cluster is active.",
            "Within the scope of provided sources, no error occurred.",
        ],
    )
    def test_limitation_markers_positive_detection(self, limitation_phrase: str) -> None:
        """Verify all positive limitation phrases trigger 'answer_with_limits'."""
        outcome, grounding = classify_workspace_ai_outcome(
            limitation_phrase, provider_success=True, evidence_supplied=True
        )
        assert outcome == "answer_with_limits", f"Failed to detect limitation in: '{limitation_phrase}'"
        assert grounding == "explicit_answer_limitation"

    @pytest.mark.parametrize(
        "negated_phrase",
        [
            # Vietnamese
            "Dữ liệu đầy đủ, không phải là không đủ thông tin để kết luận.",
            "Tất cả bằng chứng rõ ràng, không phải là không đủ bằng chứng.",
            "Đã kiểm tra kỹ, không còn thiếu thông tin nào.",
            "Hồ sơ hoàn chỉnh, không thiếu thông tin.",
            "Toàn bộ tài liệu có sẵn, thông tin không thiếu.",
            "Chúng tôi có đầy đủ tài liệu và không thiếu bằng chứng.",
            "Số liệu đã chốt, bằng chứng không thiếu.",
            # Japanese
            "必要なデータは網羅されており、十分な証拠がないわけではない。",
            "調査は完了しており、情報が不足しているわけではない。",
            "すべてのログが揃っており、証拠が不十分なわけではない。",
            # Simplified Chinese
            "全部日志均已收集，并非证据不足。",
            "配置清单完整，并非信息不足。",
            "各项指标完备，信息充足。",
            "所有审计项达标，证据充足。",
            # English
            "The dataset is complete and not insufficient for evaluation.",
            "We have full logs and are not lacking information.",
            "The repository is healthy and not lacking evidence.",
            "The evidence is not insufficient to support this conclusion.",
        ],
    )
    def test_negated_limitations_classified_as_success(self, negated_phrase: str) -> None:
        """Verify negated limitations are correctly recognized as confident 'success' answers."""
        outcome, grounding = classify_workspace_ai_outcome(
            negated_phrase, provider_success=True, evidence_supplied=True
        )
        assert outcome == "success", f"Negation falsely triggered limitation in: '{negated_phrase}' (got '{outcome}')"
        assert grounding == "evidence_supplied_unverified"

    @pytest.mark.parametrize(
        "compound_text,expected_reason",
        [
            (
                "Dữ liệu này không thiếu bằng chứng, nhưng tài liệu không đề cập đến nguyên nhân sự cố.",
                "tài liệu không đề cập",
            ),
            (
                "十分な証拠がないわけではないが、提供された証拠に基づく推測に留まります。",
                "提供された証拠に基づく",
            ),
            (
                "并非证据不足，但来源未提及具体的部署端口。",
                "来源未提及",
            ),
            (
                "The analysis is not lacking evidence, however the documents do not mention SSL certificates.",
                "documents do not mention",
            ),
        ],
    )
    def test_compound_negation_with_real_limitation_still_limits(
        self, compound_text: str, expected_reason: str
    ) -> None:
        """Verify compound statements containing both a negation AND an actual limitation are classified as 'answer_with_limits'."""
        outcome, grounding = classify_workspace_ai_outcome(
            compound_text, provider_success=True, evidence_supplied=True
        )
        assert outcome == "answer_with_limits", f"Failed compound check on: '{compound_text}'"
        assert grounding == "explicit_answer_limitation"

    def test_fail_closed_on_provider_error_and_missing_evidence(self) -> None:
        """Verify strict fail-closed classification when provider fails or evidence is missing."""
        # 1. Provider failure overrides everything
        outcome1, grounding1 = classify_workspace_ai_outcome(
            "Câu trả lời hoàn hảo 100%", provider_success=False, evidence_supplied=True
        )
        assert outcome1 == "provider_error"
        assert grounding1 == "not_assessed_provider_failure"

        # 2. No evidence supplied overrides everything
        outcome2, grounding2 = classify_workspace_ai_outcome(
            "Câu trả lời không giới hạn", provider_success=True, evidence_supplied=False
        )
        assert outcome2 == "insufficient_evidence"
        assert grounding2 == "insufficient_evidence"


# ===========================================================================
# 4. i18n Dictionary Key Parity, Non-Empty, and Fallback Tests
# ===========================================================================

class TestI18nDictionaryParityAndFallbackAdversarial:
    """Stress-test dictionary parity, non-empty values, and formatting resilience."""

    def test_100_percent_key_parity_all_three_languages(self) -> None:
        """Verify exact 100% key parity across vi, ja, and zh-CN."""
        vi_keys = set(TRANSLATIONS["vi"].keys())
        ja_keys = set(TRANSLATIONS["ja"].keys())
        zh_keys = set(TRANSLATIONS["zh-CN"].keys())

        assert vi_keys == ja_keys, f"Parity diff (vi vs ja): {vi_keys ^ ja_keys}"
        assert vi_keys == zh_keys, f"Parity diff (vi vs zh-CN): {vi_keys ^ zh_keys}"
        assert len(vi_keys) >= 120, f"Expected >=120 keys, found {len(vi_keys)}"

    def test_all_translations_non_empty_and_no_whitespace(self) -> None:
        """Verify no translation key has empty string or whitespace-only value."""
        for loc in SUPPORTED_LOCALES:
            for k, v in TRANSLATIONS[loc].items():
                assert isinstance(v, str), f"Key '{k}' in '{loc}' is not a string"
                assert len(v.strip()) > 0, f"Key '{k}' in '{loc}' is empty or whitespace"

    def test_t_function_resilience_adversarial(self) -> None:
        """Verify t() handles formatting crashes, unknown keys, and unicode arguments gracefully."""
        # 1. Broken formatting args -> returns template string without raising exception
        template = t("enabled_sources_count", locale="vi", non_existent_arg="test")
        assert template == "Nguồn đang bật: {count}"

        # 2. Unicode and special character formatting
        formatted = t("enabled_sources_count", locale="ja", count="5 (監査完了: [E1])")
        assert formatted == "有効なソース: 5 (監査完了: [E1])"

        # 3. Completely unknown key returns key itself
        assert t("UNKNOWN_KEY_9999", locale="zh-CN") == "UNKNOWN_KEY_9999"


# ===========================================================================
# 5. UTF-8 Anti-Mojibake Serialization Tests
# ===========================================================================

class TestUTF8AntiMojibakeSerializationAdversarial:
    """Stress-test UTF-8 anti-mojibake serialization across complex multilingual structures."""

    def test_complex_multilingual_json_serialization(self) -> None:
        """Verify complex multi-byte structures serialize and deserialize without ASCII escaping or mojibake."""
        data = {
            "vietnamese": "Đơn vị vận hành hệ thống AIOS: Kiểm thử tự động, đối soát bằng chứng 100%.",
            "japanese": "日本語テスト：引用識別子 [E1]、ファイルパス /var/log/監査.log、およびエラーコード ERR_001。",
            "chinese": "简体中文测试：证据追踪数据契约、多语言提示词注入与严格的去乱码保证。",
            "mixed_tokens": "[EVD-88] /opt/aios/データ_2026.xlsx -> HTTP 500: 内部错误 (Lỗi máy chủ nội bộ)",
        }

        serialized = json.dumps(data, ensure_ascii=False, indent=2)

        # Ensure raw characters exist in string
        assert "Kiểm thử tự động" in serialized
        assert "日本語テスト" in serialized
        assert "简体中文测试" in serialized
        assert "\\u" not in serialized  # Strict anti-mojibake / ensure_ascii=False check

        deserialized = json.loads(serialized)
        assert deserialized == data
