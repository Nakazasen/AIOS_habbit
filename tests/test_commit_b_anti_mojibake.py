# -*- coding: utf-8 -*-
r"""Tier 1, Tier 2, & Tier 3 Test Suite for Commit B: Verbatim Byte/Text & Anti-Mojibake Preservation.

Opaque-box and requirement-driven test suite validating:
1. 100% verbatim byte and text preservation across multilingual domains:
   - Vietnamese with full diacritics (huyền, sắc, hỏi, ngã, nặng; ă, â, đ, ê, ô, ơ, ư)
   - Japanese with Kanji, Hiragana, Katakana, and Japanese punctuation (「」、『』、・)
   - Simplified Chinese with Hanzi, technical terminology, and Chinese punctuation (《》，)
2. Exact preservation of:
   - File names, managed paths, and system directory structures
   - Technical error codes (e.g. ERR_HTTP_503_UNAVAILABLE, E_BGE_M3_GPU_OOM_0x8007000E)
   - Citation IDs and reference anchors ([1], [E1], EVD-001, [DOC-01:p.4], [証拠-01], [证据-01])
3. UTF-8 serialization / deserialization fidelity:
   - JSON string serialization using `ensure_ascii=False` (raw UTF-8 bytes, no \uXXXX escapes)
   - Local JSONL file persistence (`atomic_write_jsonl`, `traces.jsonl`) round-trip byte identity
   - Strict resistance to encoding decay, double-encoding, or mojibake corruption.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pytest

import aios_habit.workspace_chat_store as chat_store
from aios_habit.case_models import EvidenceItem
from aios_habit.evidence_trace_schema import (
    EvidenceEdge,
    EvidenceNode,
    EvidenceTrace,
    EvidenceTraceContract,
)
from aios_habit.i18n import get_ai_language_instruction, normalize_locale
from aios_habit.ide_handoff_bridge import (
    build_full_bundle_request,
    build_ide_prompt_markdown,
    build_prompt_md,
    import_ide_response,
    verify_bundle_integrity,
    write_ide_handoff_bundle,
)
from aios_habit.local_jsonl import atomic_write_jsonl, clear_jsonl_cache, load_jsonl_records


# ---------------------------------------------------------------------------
# Multilingual Test Corpus
# ---------------------------------------------------------------------------

MULTILINGUAL_CORPUS: list[dict[str, Any]] = [
    {
        "language": "vi",
        "locale": "vi",
        "doc_filename": "Biên_bản_họp_MOM_2026_08_23_Vận_hành_Kho.docx",
        "doc_path": "D:/Dự án AIOS/Hồ sơ tài liệu/2026/Biên bản/MOM_Kho_InterStock.docx",
        "citation_id": "[EVD-VI-001]",
        "error_code": "ERR_KHO_INTERSTOCK_SYNC_TIMEOUT_0x80040111",
        "query": "Quy trình đối soát biên bản họp MOM và tồn kho WMS thực hiện ra sao?",
        "source_title": "Tài liệu hướng dẫn vận hành Opcenter & WMS liên kho",
        "snippet": (
            "Tiếng Việt có dấu: ắ, ằ, ẳ, ẵ, ặ, ấ, ầ, ẩ, ẫ, ậ, é, è, ẻ, ẽ, ẹ, "
            "ế, ề, ể, ễ, ệ, ó, ò, ỏ, õ, ọ, ố, ồ, ổ, ỗ, ộ, ớ, ờ, ở, ỡ, ợ, "
            "ú, ù, ủ, ũ, ụ, ứ, ừ, sử, nữ, ự, ý, ỳ, ỷ, ỹ, ỵ, đ. "
            "Hệ thống tự động đồng bộ số liệu kiểm đếm từ thiết bị PDA về máy chủ."
        ),
        "answer": "Theo tài liệu [EVD-VI-001], quy trình đối soát tự động đồng bộ từ thiết bị PDA về máy chủ.",
    },
    {
        "language": "ja",
        "locale": "ja",
        "doc_filename": "品質管理規定_第3版_Rev2_製造実行手順書.pdf",
        "doc_path": "D:/AIOS_プロジェクト/資料/2026年/製造/品質管理規定_第3版.pdf",
        "citation_id": "[証拠-JA-002]",
        "error_code": "ERR_OPCENTER_BARCODE_MISMATCH_0x00000032",
        "query": "オプセンターの品質管理規定におけるバーコード検証ルールは何ですか？",
        "source_title": "株式会社オプセンター 製造実行システム（MES）運用基準書",
        "snippet": (
            "【重要規定】製造ラインへの原材料投入時、オペレータは必ずハンディターミナルで"
            "二次元コードを読み取り、ロット番号と有効期限の整合性を確認すること。"
            "システムがインターロックを発動した場合、管理者の承認なしに解除してはならない。"
        ),
        "answer": "規定 [証拠-JA-002] に従い、原材料投入時は二次元コードをスキャンして整合性を確認します。",
    },
    {
        "language": "zh-CN",
        "locale": "zh-CN",
        "doc_filename": "生产调度与仓库集成接口规范_v2.4_最终版.xlsx",
        "doc_path": "D:/AIOS工作区/技术规范/2026/接口文档/生产调度与仓库集成.xlsx",
        "citation_id": "[证据-ZH-003]",
        "error_code": "ERR_MES_WMS_PAYLOAD_SCHEMA_INVALID_0xC0000005",
        "query": "MES与WMS系统对接时物料出库的数据校验规则是什么？",
        "source_title": "智能制造执行系统（MES）与仓库管理系统（WMS）数据交互标准",
        "snippet": (
            "物料出库接口校验逻辑：系统在接收到领料单据后，首先比对WMS库存货位状态，"
            "若存在冻结或检验中批次，严禁生成拣货任务；必须由质量保证部（QA）在线解冻并附具检验报告。"
        ),
        "answer": "根据规范 [证据-ZH-003]，系统比对WMS货位状态，冻结批次严禁生成拣货任务。",
    },
]


# ---------------------------------------------------------------------------
# Tier 1 Tests: Verbatim Character & Byte Preservation in Dataclasses
# ---------------------------------------------------------------------------

class TestVerbatimMultiLanguageDataclass:
    """Verifies that EvidenceTrace and EvidenceNode hold strings with 100% character integrity."""

    @pytest.mark.parametrize("corpus_entry", MULTILINGUAL_CORPUS, ids=lambda c: c["language"])
    def test_verbatim_fields_in_evidence_trace(self, corpus_entry: dict[str, Any]) -> None:
        """Verify filenames, paths, error codes, citation IDs, and snippets retain exact unicode."""
        node_source = EvidenceNode(
            id=f"src_{corpus_entry['language']}",
            node_type="source",
            title=corpus_entry["source_title"],
            snippet=corpus_entry["snippet"],
            source_id=corpus_entry["doc_path"],
            metadata={
                "filename": corpus_entry["doc_filename"],
                "error_code": corpus_entry["error_code"],
            },
            language=corpus_entry["language"],
        )
        node_cit = EvidenceNode(
            id=f"cit_{corpus_entry['language']}",
            node_type="citation",
            title=corpus_entry["citation_id"],
            snippet=corpus_entry["snippet"][:50],
            source_id=node_source.id,
            citation_id=corpus_entry["citation_id"],
            language=corpus_entry["language"],
        )
        node_ans = EvidenceNode(
            id=f"ans_{corpus_entry['language']}",
            node_type="answer",
            title="Answer",
            snippet=corpus_entry["answer"],
            language=corpus_entry["language"],
        )
        edge_cit = EvidenceEdge(
            source_id=node_cit.id,
            target_id=node_source.id,
            relation_type="extracted_from",
        )
        edge_ans = EvidenceEdge(
            source_id=node_ans.id,
            target_id=node_cit.id,
            relation_type="cites",
        )

        trace = EvidenceTrace(
            schema_version="rag-trace/v1",
            trace_id=f"trc_mojibake_{corpus_entry['language']}",
            query=corpus_entry["query"],
            answer_text=corpus_entry["answer"],
            ui_locale=corpus_entry["locale"],
            answer_language=corpus_entry["locale"],
            source_language=corpus_entry["locale"],
            nodes=[node_source, node_cit, node_ans],
            edges=[edge_cit, edge_ans],
            metadata={"error_code": corpus_entry["error_code"]},
        )

        # Assert exact in-memory string equality
        assert trace.query == corpus_entry["query"]
        assert trace.answer_text == corpus_entry["answer"]
        assert node_source.metadata["filename"] == corpus_entry["doc_filename"]
        assert node_source.source_id == corpus_entry["doc_path"]
        assert node_source.metadata["error_code"] == corpus_entry["error_code"]
        assert node_cit.citation_id == corpus_entry["citation_id"]
        assert node_source.snippet == corpus_entry["snippet"]

        # Validate against contract
        is_valid, errors = EvidenceTraceContract.validate_trace(trace)
        assert is_valid, f"Trace validation failed for {corpus_entry['language']}: {errors}"


# ---------------------------------------------------------------------------
# Tier 2 Tests: UTF-8 JSON Serialization & ensure_ascii=False Verification
# ---------------------------------------------------------------------------

class TestUTF8JSONSerialization:
    """Verifies that JSON serialization emits direct UTF-8 bytes without escape degradation."""

    @pytest.mark.parametrize("corpus_entry", MULTILINGUAL_CORPUS, ids=lambda c: c["language"])
    def test_json_serialization_ensure_ascii_false(self, corpus_entry: dict[str, Any]) -> None:
        """Verify that to_json(ensure_ascii=False) contains raw UTF-8 characters, not \\uXXXX escapes."""
        node = EvidenceNode(
            id="src_1",
            node_type="source",
            title=corpus_entry["source_title"],
            snippet=corpus_entry["snippet"],
            source_id=corpus_entry["doc_path"],
            citation_id=corpus_entry["citation_id"],
        )
        trace = EvidenceTrace(
            schema_version="rag-trace/v1",
            trace_id=f"trc_{corpus_entry['language']}",
            query=corpus_entry["query"],
            answer_text=corpus_entry["answer"],
            ui_locale=corpus_entry["locale"],
            answer_language=corpus_entry["locale"],
            source_language=corpus_entry["locale"],
            nodes=[node],
            edges=[],
            metadata={"filename": corpus_entry["doc_filename"]},
        )

        json_str = trace.to_json(ensure_ascii=False)

        # The serialized string must directly contain non-ASCII characters
        assert corpus_entry["doc_filename"] in json_str
        assert corpus_entry["citation_id"] in json_str
        assert corpus_entry["query"] in json_str
        assert corpus_entry["snippet"] in json_str

        # Ensure no escaped Unicode sequences like \u00e0 or \u65e5 appear for standard text
        # (check key unique multilingual substrings)
        if corpus_entry["language"] == "vi":
            assert "\\u0103" not in json_str  # 'ă' should be verbatim
            assert "kiểm đếm" in json_str.lower()
        elif corpus_entry["language"] == "ja":
            assert "\\u54c1\\u8cea" not in json_str  # '品質' should be verbatim
            assert "品質管理規定" in json_str
        elif corpus_entry["language"] == "zh-CN":
            assert "\\u667a\\u80fd" not in json_str  # '智能' should be verbatim
            assert "智能制造执行系统" in json_str

        # Round-trip deserialization
        deserialized = EvidenceTrace.from_json(json_str)
        assert deserialized.query == corpus_entry["query"]
        assert deserialized.answer_text == corpus_entry["answer"]
        assert deserialized.nodes[0].snippet == corpus_entry["snippet"]
        assert deserialized.metadata["filename"] == corpus_entry["doc_filename"]


# ---------------------------------------------------------------------------
# Tier 2 & 3 Tests: JSONL File Persistence & Storage Round-Trip
# ---------------------------------------------------------------------------

class TestJSONLStorageAntiMojibake:
    """Verifies durable file persistence in traces.jsonl with UTF-8 encoding."""

    def test_jsonl_file_raw_bytes_and_atomic_roundtrip(self, tmp_path: Path) -> None:
        """Write records to JSONL file and check raw bytes on disk and deserialized content."""
        traces_file = tmp_path / "traces_mojibake.jsonl"

        traces: list[EvidenceTrace] = []
        for entry in MULTILINGUAL_CORPUS:
            node = EvidenceNode(
                id=f"src_{entry['language']}",
                node_type="source",
                title=entry["source_title"],
                snippet=entry["snippet"],
                source_id=entry["doc_path"],
                citation_id=entry["citation_id"],
            )
            t = EvidenceTrace(
                schema_version="rag-trace/v1",
                trace_id=f"trc_{entry['language']}",
                query=entry["query"],
                answer_text=entry["answer"],
                ui_locale=entry["locale"],
                answer_language=entry["locale"],
                source_language=entry["locale"],
                nodes=[node],
                edges=[],
                metadata={
                    "filename": entry["doc_filename"],
                    "error_code": entry["error_code"],
                },
            )
            traces.append(t)

        # Atomic write to JSONL
        atomic_write_jsonl(traces_file, traces)

        # 1. Inspect raw disk bytes
        raw_bytes = traces_file.read_bytes()
        # Decode as UTF-8 strictly (will raise UnicodeDecodeError if corrupted)
        decoded_text = raw_bytes.decode("utf-8")

        for entry in MULTILINGUAL_CORPUS:
            assert entry["doc_filename"] in decoded_text
            assert entry["citation_id"] in decoded_text
            assert entry["error_code"] in decoded_text
            assert entry["snippet"] in decoded_text

        # 2. Reload via load_jsonl_records
        clear_jsonl_cache()
        loaded_traces = load_jsonl_records(traces_file, EvidenceTrace.from_dict)
        assert len(loaded_traces) == len(MULTILINGUAL_CORPUS)

        for orig, loaded in zip(traces, loaded_traces):
            assert loaded.trace_id == orig.trace_id
            assert loaded.query == orig.query
            assert loaded.answer_text == orig.answer_text
            assert loaded.ui_locale == orig.ui_locale
            assert loaded.nodes[0].title == orig.nodes[0].title
            assert loaded.nodes[0].snippet == orig.nodes[0].snippet
            assert loaded.metadata["filename"] == orig.metadata["filename"]
            assert loaded.metadata["error_code"] == orig.metadata["error_code"]

    def test_special_characters_and_punctuation_integrity(self, tmp_path: Path) -> None:
        """Verify complex formatting, symbols, quotation marks, and math symbols survive roundtrip."""
        complex_text = (
            "Dấu ngoặc kép: “English quotes”, «French quotes», 「Japanese brackets」, 『White brackets』, 《Chinese titles》. "
            "Ký tự toán học & logic: ∀x ∈ S, ∃y : x ∧ y ⇒ z; ∑, ∏, √, ≈, ≠, ≤, ≥. "
            "Ký tự đặc biệt: \tTab, /forward/slash, \\backslash, &amp; <xml>tag</xml>, @#$%^*~. "
            "Biểu tượng tiền tệ & đơn vị: 1.000.000₫, 10,000¥, 5,000€, $100, 25°C, 100m²."
        )
        node = EvidenceNode(
            id="src_special",
            node_type="source",
            title="Đặc biệt / 特別 / 特殊 [SYM-999]",
            snippet=complex_text,
            source_id="local_cases/docs/special_chars.txt",
        )
        trace = EvidenceTrace(
            schema_version="rag-trace/v1",
            trace_id="trc_special_chars",
            query="Kiểm tra ký tự đặc biệt?",
            answer_text="Kết quả chứa đầy đủ ký tự [SYM-999].",
            nodes=[node],
            edges=[],
            metadata={"complex_text": complex_text},
        )

        test_file = tmp_path / "special.jsonl"
        atomic_write_jsonl(test_file, [trace])
        clear_jsonl_cache()

        loaded_list = load_jsonl_records(test_file, EvidenceTrace.from_dict)
        assert len(loaded_list) == 1
        loaded_trace = loaded_list[0]

        assert loaded_trace.nodes[0].snippet == complex_text
        assert loaded_trace.metadata["complex_text"] == complex_text
        assert loaded_trace.nodes[0].title == "Đặc biệt / 特別 / 特殊 [SYM-999]"


# ---------------------------------------------------------------------------
# Tier 3 Tests: IDE Handoff Bridge Multilingual Bundle & UTF-8 Round-Trip
# ---------------------------------------------------------------------------

class TestIDEHandoffAntiMojibake:
    """Verifies that IDE Handoff Bridge bundles, manifests, prompts, and responses retain 100% UTF-8 fidelity."""

    @pytest.mark.parametrize("corpus_entry", MULTILINGUAL_CORPUS, ids=lambda c: c["language"])
    def test_ide_handoff_bundle_files_utf8_fidelity(self, tmp_path: Path, corpus_entry: dict[str, Any]) -> None:
        """Verify all bundle files on disk contain raw UTF-8 characters and no mojibake or escaped bytes."""
        item = EvidenceItem(
            evidence_id=f"EVD-{corpus_entry['language'].upper()}-1",
            case_id=f"CASE-{corpus_entry['language'].upper()}",
            source_type="doc",
            source_path=corpus_entry["doc_path"],
            title=corpus_entry["source_title"],
            extracted_text=corpus_entry["snippet"],
            privacy_level="local_only",
        )

        req = write_ide_handoff_bundle(
            case_id=item.case_id,
            question=corpus_entry["query"],
            bundle_scope="active_case_all",
            evidence_items=[item],
            root=tmp_path,
            answer_language=corpus_entry["locale"],
            request_id=f"REQ-ANTI-{corpus_entry['language'].upper()}",
        )

        # 1. Inspect manifest.json
        manifest_raw = (req.bundle_dir / "manifest.json").read_bytes().decode("utf-8")
        assert corpus_entry["query"] in manifest_raw
        assert corpus_entry["locale"] in manifest_raw
        assert "\\u" not in manifest_raw

        manifest = json.loads(manifest_raw)
        assert manifest["answer_language"] == corpus_entry["locale"]
        assert manifest["question"] == corpus_entry["query"]

        # 2. Inspect prompt.md & prompt_for_antigravity.md
        prompt_raw = (req.bundle_dir / "prompt.md").read_bytes().decode("utf-8")
        prompt_anti_raw = (req.bundle_dir / "prompt_for_antigravity.md").read_bytes().decode("utf-8")

        assert prompt_raw == prompt_anti_raw
        assert corpus_entry["query"] in prompt_raw
        assert "[1]" in prompt_raw
        assert "[E1]" in prompt_raw
        assert "EVD-001" in prompt_raw
        assert "document.pdf" in prompt_raw
        assert "\\u" not in prompt_raw

        if corpus_entry["language"] == "vi":
            assert "Yêu cầu ngôn ngữ: Trả lời hoàn toàn bằng Tiếng Việt." in prompt_raw
            assert "Giữ nguyên vẹn 100%" in prompt_raw
        elif corpus_entry["language"] == "ja":
            assert "言語指示: 回答はすべて日本語で記述してください。" in prompt_raw
            assert "原文のまま100%保持してください。" in prompt_raw
        elif corpus_entry["language"] == "zh-CN":
            assert "语言指示: 请完全使用简体中文回答。" in prompt_raw
            assert "请100%完整保留所有引用ID" in prompt_raw

        # 3. Inspect evidence_full.jsonl
        jsonl_raw = (req.bundle_dir / "evidence_full.jsonl").read_bytes().decode("utf-8")
        assert corpus_entry["snippet"] in jsonl_raw
        assert corpus_entry["source_title"] in jsonl_raw
        assert corpus_entry["doc_path"] in jsonl_raw
        assert "\\u" not in jsonl_raw

        # 4. Inspect evidence_full.md
        md_raw = (req.bundle_dir / "evidence_full.md").read_bytes().decode("utf-8")
        assert corpus_entry["snippet"] in md_raw
        assert corpus_entry["source_title"] in md_raw

        # 5. Verify cryptographic integrity
        ok, errors = verify_bundle_integrity(req.bundle_dir)
        assert ok is True
        assert len(errors) == 0

    @pytest.mark.parametrize("corpus_entry", MULTILINGUAL_CORPUS, ids=lambda c: c["language"])
    def test_ide_handoff_response_import_multilingual_utf8(self, tmp_path: Path, corpus_entry: dict[str, Any]) -> None:
        """Verify importing a response with multilingual answer text, citations, and error codes."""
        item = EvidenceItem(
            evidence_id=f"EVD-{corpus_entry['language'].upper()}-1",
            case_id=f"CASE-{corpus_entry['language'].upper()}",
            source_type="doc",
            source_path=corpus_entry["doc_path"],
            title=corpus_entry["source_title"],
            extracted_text=corpus_entry["snippet"],
            privacy_level="local_only",
        )

        req = write_ide_handoff_bundle(
            case_id=item.case_id,
            question=corpus_entry["query"],
            bundle_scope="active_case_all",
            evidence_items=[item],
            root=tmp_path,
            answer_language=corpus_entry["locale"],
            request_id=f"REQ-RESP-{corpus_entry['language'].upper()}",
        )

        # Write inbox response.json in target language
        response_payload = {
            "schema_version": "ide_handoff_response_v1",
            "request_id": req.request_id,
            "status": "completed",
            "model_tool_name": "Antigravity IDE AI (Multilingual)",
            "answer_text": corpus_entry["answer"],
            "answer_markdown": corpus_entry["answer"],
            "cited_evidence_ids": [item.evidence_id],
            "evidence_ids_used": [item.evidence_id],
            "limitations": [f"Hạn chế / 制限 / 限制: {corpus_entry['error_code']}"],
            "confidence": "high",
            "confidence_label": "high",
            "privacy_acknowledged": True,
            "used_full_bundle": True,
            "unsupported_claims": [],
            "recommended_next_actions": [f"Hành động tiếp theo / 次のアクション / 下一步: {corpus_entry['doc_filename']}"],
        }

        resp_file = tmp_path / "inbox" / req.request_id / "response.json"
        resp_file.parent.mkdir(parents=True, exist_ok=True)
        resp_file.write_text(json.dumps(response_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        result = import_ide_response(resp_file, root=tmp_path)
        assert result.ok is True
        assert result.final_answer is True
        assert result.response["answer_text"] == corpus_entry["answer"]
        assert result.response["evidence_ids_used"] == [item.evidence_id]
