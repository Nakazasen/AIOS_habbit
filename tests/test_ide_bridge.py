import pytest
from aios_habit.ide_bridge import (
    IDEBridgeConfig, IDEPromptPack, IDEPasteBackAnswer,
    build_ide_prompt_pack, validate_prompt_export,
    format_ide_prompt_pack, record_paste_back_answer,
    stable_prompt_pack_id, stable_answer_id,
    ide_prompt_pack_to_dict, ide_answer_to_dict
)
from aios_habit.rag_evidence import RAGEvidencePack, RAGEvidenceItem

def _mock_evidence_pack(privacy_mode="cloud_safe"):
    item1 = RAGEvidenceItem(
        evidence_id="EVD-1",
        chunk_id="c1",
        document_id="d1",
        citation_id="[1]",
        citation_label="doc1.txt",
        source_title="Doc 1",
        relative_path="secret/doc1.txt",
        file_type=".txt",
        privacy_mode=privacy_mode,
        text="Content 1",
        snippet="Snippet 1",
        score=10.0,
        rank=1
    )
    return RAGEvidencePack(
        pack_id="PACK-123",
        query="test query",
        items=[item1],
        privacy_mode=privacy_mode,
        allowed_external=(privacy_mode != "local_only"),
        source_count=1,
        document_count=1,
        top_score=10.0,
        coverage_score=1.0,
        confidence_label="high",
        insufficient_evidence=False,
        missing_evidence_warnings=[]
    )

def test_cloud_safe_prompt():
    ev_pack = _mock_evidence_pack("cloud_safe")
    config = IDEBridgeConfig(allow_cloud_safe_export=True)
    prompt_pack = build_ide_prompt_pack(ev_pack, "Gemini", config)
    
    assert prompt_pack.allowed_external is True
    assert prompt_pack.export_policy == "allowed_cloud_safe"
    assert "test query" in prompt_pack.prompt_text
    assert "[1]" in prompt_pack.prompt_text
    assert "Snippet 1" in prompt_pack.prompt_text
    assert "cloud_safe" in prompt_pack.prompt_text
    assert validate_prompt_export(prompt_pack) is True

def test_local_only_blocked():
    ev_pack = _mock_evidence_pack("local_only")
    config = IDEBridgeConfig()
    prompt_pack = build_ide_prompt_pack(ev_pack, "Gemini", config)
    
    assert prompt_pack.allowed_external is False
    assert prompt_pack.export_policy == "blocked_local_only"
    assert "DO NOT EXPORT EXTERNALLY" in prompt_pack.prompt_text
    assert validate_prompt_export(prompt_pack) is False

def test_redacted_export_policy():
    ev_pack = _mock_evidence_pack("local_only")
    config = IDEBridgeConfig(allow_redacted_export=True)
    prompt_pack = build_ide_prompt_pack(ev_pack, "Gemini", config)
    
    assert prompt_pack.allowed_external is True
    assert prompt_pack.export_policy == "allowed_redacted"
    assert validate_prompt_export(prompt_pack) is True

def test_path_safety():
    ev_pack = _mock_evidence_pack("cloud_safe")
    prompt_pack = build_ide_prompt_pack(ev_pack, "Gemini")
    # relative_path="secret/doc1.txt" should not be exposed, only citation_label
    assert "secret/doc1.txt" not in prompt_pack.prompt_text
    assert "doc1.txt" in prompt_pack.prompt_text

def test_stable_ids():
    ev_pack = _mock_evidence_pack("cloud_safe")
    pack1 = build_ide_prompt_pack(ev_pack, "Gemini")
    pack2 = build_ide_prompt_pack(ev_pack, "Gemini")
    pack3 = build_ide_prompt_pack(ev_pack, "Claude")
    
    assert pack1.prompt_pack_id == pack2.prompt_pack_id
    assert pack1.prompt_pack_id != pack3.prompt_pack_id
    
    ans1 = record_paste_back_answer(pack1, "Gemini Web", "My answer")
    ans2 = record_paste_back_answer(pack1, "Gemini Web", "My answer")
    assert ans1.answer_id == ans2.answer_id

def test_prompt_truncation():
    ev_pack = _mock_evidence_pack("cloud_safe")
    config = IDEBridgeConfig(max_prompt_chars=50)
    prompt_pack = build_ide_prompt_pack(ev_pack, "Gemini", config)
    
    assert len(prompt_pack.prompt_text) == 50
    assert len(prompt_pack.warnings) == 1
    assert "truncated" in prompt_pack.warnings[0]

def test_paste_back_answer():
    ev_pack = _mock_evidence_pack("cloud_safe")
    prompt_pack = build_ide_prompt_pack(ev_pack, "Gemini")
    ans = record_paste_back_answer(
        prompt_pack,
        "Gemini Web",
        "This is the answer.",
        route_summary="manual",
        confidence_label="high"
    )
    
    assert ans.model_tool_name == "Gemini Web"
    assert ans.prompt_pack_id == prompt_pack.prompt_pack_id
    assert ans.source_evidence_pack_id == "PACK-123"
    assert ans.external_ai_used is True
    assert ans.privacy_mode == "cloud_safe"
    assert ans.evidence_refs == ["EVD-1"]
    assert ans.citation_ids == ["[1]"]

def test_missing_model_tool():
    ev_pack = _mock_evidence_pack("cloud_safe")
    prompt_pack = build_ide_prompt_pack(ev_pack, "Gemini")
    
    with pytest.raises(ValueError):
        record_paste_back_answer(prompt_pack, "", "Answer")
        
    config = IDEBridgeConfig(require_model_tool_name=False)
    ans = record_paste_back_answer(prompt_pack, "", "Answer", config=config)
    assert ans.model_tool_name == "unknown"

def test_json_serialization():
    ev_pack = _mock_evidence_pack("cloud_safe")
    prompt_pack = build_ide_prompt_pack(ev_pack, "Gemini")
    ans = record_paste_back_answer(prompt_pack, "Gemini Web", "Ans")
    
    p_dict = ide_prompt_pack_to_dict(prompt_pack)
    a_dict = ide_answer_to_dict(ans)
    
    assert p_dict["export_policy"] == "allowed_cloud_safe"
    assert a_dict["model_tool_name"] == "Gemini Web"
