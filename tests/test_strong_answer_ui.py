import pytest

from aios_habit.case_models import EvidenceItem
from aios_habit.strong_answer_ui import (
    build_strong_answer_prompt_for_ui,
    prepare_local_evidence_answer,
    save_pasted_strong_answer,
)


def _ev(eid, title, text, privacy="local_only"):
    return EvidenceItem(
        evidence_id=eid,
        case_id="CASE-1",
        source_type="xlsx",
        source_path="fake",
        title=title,
        extracted_text=text,
        privacy_level=privacy,
    )


def test_ui_helper_returns_local_draft_not_final():
    prep = prepare_local_evidence_answer(
        "manual shipping existing line workflow master",
        [_ev("E1", "ManualShipping_ExistingLineAuto_InboundDownload.xlsx", "Workflow Resource ExistingLine ManualShipping content")],
    )
    assert prep.final_answer is False
    assert prep.local_draft.final_answer is False
    assert prep.local_draft.answer_kind == "local_evidence_draft"


def test_ui_prompt_export_blocks_direct_provider_call_for_local_only():
    prep = prepare_local_evidence_answer("manual shipping", [_ev("E1", "ManualShipping.xlsx", "ManualShipping ExistingLine Workflow")])
    export = build_strong_answer_prompt_for_ui(prep.question, prep.evidence_pack, prep.local_draft.answer_text)
    assert export.blocked_direct_provider_call is True
    assert "cloud bị chặn" in export.privacy_warning


def test_ui_prompt_contains_focus_instruction_from_source_aware_retrieval():
    prep = prepare_local_evidence_answer(
        "manual shipping existing line container oricon workflow master",
        [_ev("E1", "ManualShipping_ExistingLineAuto_InboundDownload.xlsx", "Workflow Resource ExistingLine ManualShipping Container Oricon")],
    )
    export = build_strong_answer_prompt_for_ui(prep.question, prep.evidence_pack, prep.local_draft.answer_text)
    assert "LƯU Ý TRỌNG TÂM" in export.prompt_text


def test_paste_back_requires_answer_text_and_model_name():
    prep = prepare_local_evidence_answer("manual shipping", [_ev("E1", "ManualShipping.xlsx", "ManualShipping Workflow")])
    with pytest.raises(ValueError):
        save_pasted_strong_answer("CASE-1", prep.question, "", "Gemini", prep.evidence_pack)
    with pytest.raises(ValueError):
        save_pasted_strong_answer("CASE-1", prep.question, "answer", "", prep.evidence_pack)


def test_paste_back_stores_kind_and_refs(monkeypatch):
    saved_items = []
    monkeypatch.setattr("aios_habit.strong_answer_ui.save_evidence", lambda ev: saved_items.append(ev))
    prep = prepare_local_evidence_answer("Workflow ManualShipping", [_ev("E1", "ManualShipping.xlsx", "ManualShipping Workflow")])
    saved = save_pasted_strong_answer("CASE-1", prep.question, "final answer", "Gemini 3.1", prep.evidence_pack)
    assert saved.answer_kind == "pasted_strong_model_answer"
    assert saved.evidence_ids
    assert saved.final_answer is True
    assert saved_items[0].source_type == "pasted_strong_model_answer"


def test_metadata_only_evidence_warns_and_not_final():
    prep = prepare_local_evidence_answer("manual shipping", [_ev("E1", "manual.pdf", "")])
    assert prep.evidence_pack.evidence_quality == "metadata_only"
    assert prep.local_draft.final_answer is False
    assert prep.metadata_only_warning


def test_no_cloud_provider_call_in_ui_helpers(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("provider call should not happen")
    monkeypatch.setattr("aios_habit.ai_provider_bridge._post_chat", fail)
    prep = prepare_local_evidence_answer("manual shipping", [_ev("E1", "ManualShipping.xlsx", "ManualShipping Workflow")])
    export = build_strong_answer_prompt_for_ui(prep.question, prep.evidence_pack, prep.local_draft.answer_text)
    assert export.prompt_text
