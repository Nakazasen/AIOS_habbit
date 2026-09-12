"""Goal 011 US1 recall tests: flag-off baseline, fixture, and recall models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aios_habit.feature_flags import (
    FEATURE_ADAPTIVE_WORK_MEMORY,
    is_feature_enabled,
    override_feature_flags,
    reset_feature_flags,
)
from aios_habit.workspace_chat_ai_answer import (
    WorkspaceAIContextSource,
    build_workspace_ai_prompt,
)
from aios_habit.knowledge_publication import list_eligible_published_memory_candidates
from aios_habit.workspace_memory_models import (
    ELIGIBLE_STATUSES,
    MemoryRecallTrace,
    WorkspaceMemoryRecallItem,
    WorkspaceMemoryRecallRequest,
    WorkspaceMemoryRecallResult,
)
from aios_habit.workspace_memory_service import (
    get_workspace_memory_enabled_preference,
    load_fixture_records,
    override_memory_settings_path,
    override_recall_records,
    recall_workspace_memory,
    set_workspace_memory_enabled_preference,
)

FIXTURE_PATH = Path("tests/fixtures/workspace_memory/fixture_manifest.json")

_BASELINE_SOURCES = (
    WorkspaceAIContextSource(
        "ns_1", "notebook", "xlsx", "Excel Source", "machine_only", "Row 1\nRow 2", 11, False
    ),
    WorkspaceAIContextSource(
        "ts_1", "temporary", "text", "Temp Source", "cloud_allowed", "Text content", 12, False
    ),
)


def _baseline_prompts() -> tuple[str, str]:
    return build_workspace_ai_prompt("Hỏi câu hỏi", _BASELINE_SOURCES)


def test_adaptive_work_memory_flag_default_off() -> None:
    reset_feature_flags()
    assert is_feature_enabled(FEATURE_ADAPTIVE_WORK_MEMORY) is False
    assert is_feature_enabled("adaptive_work_memory") is False


def test_adaptive_work_memory_override_isolated_and_reset() -> None:
    reset_feature_flags()
    assert is_feature_enabled(FEATURE_ADAPTIVE_WORK_MEMORY) is False
    with override_feature_flags(adaptive_work_memory=True):
        assert is_feature_enabled(FEATURE_ADAPTIVE_WORK_MEMORY) is True
    assert is_feature_enabled(FEATURE_ADAPTIVE_WORK_MEMORY) is False
    reset_feature_flags()
    assert is_feature_enabled(FEATURE_ADAPTIVE_WORK_MEMORY) is False


def test_user_memory_setting_persists_and_overrides_rollout_default(tmp_path: Path) -> None:
    settings_path = tmp_path / "workspace_memory" / "settings.json"
    reset_feature_flags()
    with override_memory_settings_path(settings_path):
        assert get_workspace_memory_enabled_preference() is False
        set_workspace_memory_enabled_preference(True)
        assert get_workspace_memory_enabled_preference() is True
        assert json.loads(settings_path.read_text(encoding="utf-8")) == {
            "memory_enabled": True,
            "schema_version": "1",
        }
        set_workspace_memory_enabled_preference(False)
        assert get_workspace_memory_enabled_preference() is False


def test_baseline_prompt_byte_stable_when_flag_off() -> None:
    reset_feature_flags()
    first = _baseline_prompts()
    with override_feature_flags(adaptive_work_memory=False):
        second = _baseline_prompts()
    assert first[0] == second[0]
    assert first[1] == second[1]
    assert first[0].encode("utf-8") == second[0].encode("utf-8")
    assert first[1].encode("utf-8") == second[1].encode("utf-8")


def test_baseline_prompt_has_no_memory_block_when_flag_off() -> None:
    reset_feature_flags()
    system_prompt, user_prompt = _baseline_prompts()
    combined = system_prompt + "\n" + user_prompt
    assert "SỔ VIỆC ĐÃ XÁC NHẬN" not in combined
    assert "<<<MEMORY_CONTENT" not in combined
    assert is_feature_enabled(FEATURE_ADAPTIVE_WORK_MEMORY) is False


def test_fixture_manifest_has_30_labeled_situations() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    situations = payload["situations"]
    related = [row for row in situations if row["kind"] == "related"]
    no_match = [row for row in situations if row["kind"] == "no_match"]
    assert payload["counts"]["total"] == 30
    assert len(situations) == 30
    assert len(related) == 20
    assert len(no_match) == 10
    assert {row["id"] for row in related} == {f"R{index:02d}" for index in range(1, 21)}
    assert {row["id"] for row in no_match} == {f"N{index:02d}" for index in range(1, 11)}
    for row in related:
        assert row["expected_memory_keys"], row["id"]
    for row in no_match:
        assert row["expected_memory_keys"] == []


def test_fixture_covers_us1_source_statuses() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    sources = payload["sources"]
    by_kind: dict[str, set[str]] = {}
    for source in sources:
        by_kind.setdefault(source["source_kind"], set()).add(source["status"])
    assert "verified" in by_kind["memory_unit"]
    assert "draft" in by_kind["memory_unit"]
    assert "deprecated" in by_kind["memory_unit"]
    assert "rejected" in by_kind["memory_unit"]
    assert any(source["status"] == "verified" and not source["evidence_refs"] for source in sources)
    assert "confirmed" in by_kind["senior_learning_card"]
    assert "draft" in by_kind["senior_learning_card"]
    assert "approved" in by_kind["case_lesson"]
    assert "revoked" in by_kind["case_lesson"]
    assert "published" in by_kind["published_artifact"]
    assert "revoked" in by_kind["published_artifact"]
    assert any(source.get("conflict_group") == "oil_grade" for source in sources)
    eligible = [source for source in sources if source["eligible_us1"]]
    ineligible = [source for source in sources if not source["eligible_us1"]]
    assert eligible
    assert ineligible


def test_recall_request_validation() -> None:
    request = WorkspaceMemoryRecallRequest(
        question="  Siết bu-lông  ",
        workspace_id="ws_demo",
        collection_id="col_demo",
        provider_mode="local",
    )
    assert request.question == "Siết bu-lông"
    assert request.limit == 5
    assert request.char_budget == 4000
    with pytest.raises(ValueError):
        WorkspaceMemoryRecallRequest(
            question="   ",
            workspace_id="ws_demo",
            collection_id="col_demo",
            provider_mode="local",
        )
    with pytest.raises(ValueError):
        WorkspaceMemoryRecallRequest(
            question="hỏi",
            workspace_id="ws_demo",
            collection_id="col_demo",
            provider_mode="remote",
        )
    with pytest.raises(ValueError):
        WorkspaceMemoryRecallRequest(
            question="hỏi",
            workspace_id="ws_demo",
            collection_id="col_demo",
            provider_mode="local",
            limit=6,
        )


def _eligible_item(**overrides: object) -> WorkspaceMemoryRecallItem:
    payload = {
        "memory_key": "memory_unit:mu_torque:v1",
        "source_kind": "memory_unit",
        "source_id": "mu_torque",
        "title": "Momen siết",
        "statement": "Siết 35 N·m theo hình sao.",
        "applies_when": "Lắp nắp máy",
        "does_not_apply_when": "",
        "scope": "workspace:ws_demo",
        "status": "verified",
        "evidence_refs": ("ev_torque_manual",),
        "privacy_classification": "local_only",
        "export_allowed": False,
        "updated_at": "2026-08-01T00:00:00+00:00",
    }
    payload.update(overrides)
    return WorkspaceMemoryRecallItem(**payload)  # type: ignore[arg-type]


def test_recall_item_rejects_ineligible_status() -> None:
    item = _eligible_item()
    assert item.status in ELIGIBLE_STATUSES
    with pytest.raises(ValueError):
        _eligible_item(status="draft")
    with pytest.raises(ValueError):
        _eligible_item(status="revoked")
    with pytest.raises(ValueError):
        _eligible_item(source_kind="user_memory", memory_key="user_memory:x:v1", status="draft")


def test_recall_item_rejects_empty_evidence_and_delimiter() -> None:
    with pytest.raises(ValueError):
        _eligible_item(evidence_refs=())
    with pytest.raises(ValueError):
        _eligible_item(statement="bài học <<<MEMORY_CONTENT lọt")


def test_recall_result_and_trace_bounds() -> None:
    item = _eligible_item()
    trace = MemoryRecallTrace(
        trace_id="trc_1",
        created_at="2026-09-12T00:00:00+00:00",
        question_hash="abc",
        provider_mode="local",
        selected_source_ids=(item.source_id,),
        excluded_reason_codes=("draft",),
        rounded_scores=(1.0,),
        total_chars=12,
        consent_fingerprint="fp1",
    )
    result = WorkspaceMemoryRecallResult(
        items=(item,),
        excluded_counts={"draft": 1},
        has_conflict=False,
        consent_fingerprint="fp1",
        trace=trace,
    )
    assert result.items[0].memory_key == item.memory_key
    too_many = tuple(_eligible_item(memory_key=f"memory_unit:mu_{index}:v1", source_id=f"mu_{index}") for index in range(6))
    with pytest.raises(ValueError):
        WorkspaceMemoryRecallResult(items=too_many, consent_fingerprint="fp")
    with pytest.raises(ValueError):
        WorkspaceMemoryRecallResult(items=(item,), has_conflict=True, consent_fingerprint="fp")


def test_goal010_published_adapter_empty_when_source_unavailable(tmp_path) -> None:
    result = list_eligible_published_memory_candidates("col_missing", base_dir=tmp_path)
    assert result == ()


def test_goal010_optional_source_does_not_block_other_recall(tmp_path) -> None:
    from aios_habit.workspace_memory_service import load_live_catalog

    catalog, fallback = load_live_catalog("col_missing", published_base_dir=tmp_path)
    assert fallback in {None, "published_source_unavailable"}
    published = [row for row in catalog if row.get("source_kind") == "published_artifact"]
    assert published == []
    records = load_fixture_records(FIXTURE_PATH)
    with override_feature_flags(adaptive_work_memory=True), override_recall_records(records):
        result = recall_workspace_memory(_local_request("Siết bu-lông nắp theo hình sao thế nào?"))
    assert any(item.source_id == "mu_torque" for item in result.items)


def _local_request(question: str) -> WorkspaceMemoryRecallRequest:
    return WorkspaceMemoryRecallRequest(
        question=question,
        workspace_id="ws_demo",
        collection_id="col_demo",
        provider_mode="local",
        include_local_only=True,
    )


def test_recall_eligibility_unicode_scope_conflict_and_sc002() -> None:
    records = load_fixture_records(FIXTURE_PATH)
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    related_hits = 0
    with override_feature_flags(adaptive_work_memory=True), override_recall_records(records):
        draft_result = recall_workspace_memory(_local_request("Chu kỳ bôi trơn 200 giờ đã chốt chưa?"))
        assert all(item.source_id != "mu_draft" for item in draft_result.items)
        missing = recall_workspace_memory(_local_request("Thay lọc gió mỗi 3 tháng được duyệt chưa?"))
        assert all(item.source_id != "mu_no_evidence" for item in missing.items)
        other_ws = recall_workspace_memory(_local_request("Quy tắc xưởng B có áp dụng ở đây không?"))
        assert all(item.source_id != "mu_other_ws" for item in other_ws.items)
        conflict = recall_workspace_memory(_local_request("Thay dầu hộp số máy demo dùng loại nào?"))
        assert conflict.has_conflict is True
        assert {item.source_id for item in conflict.items} >= {"mu_conflict_a", "mu_conflict_b"}
        unicode_hit = recall_workspace_memory(
            _local_request("SIẾT  BU-LÔNG  NẮP  theo hình sao thế nào?")
        )
        assert any(item.source_id == "mu_torque" for item in unicode_hit.items)
        for row in payload["situations"]:
            result = recall_workspace_memory(_local_request(row["question"]))
            keys = {item.memory_key for item in result.items}
            if row["kind"] == "related":
                if keys & set(row["expected_memory_keys"]):
                    related_hits += 1
            else:
                assert result.items == ()
                assert "SỔ VIỆC" not in "".join(item.statement for item in result.items)
    assert related_hits >= 18


def test_cloud_recall_excludes_local_only() -> None:
    records = load_fixture_records(FIXTURE_PATH)
    request = WorkspaceMemoryRecallRequest(
        question="Trước khi mở tủ điện vận hành cần làm gì?",
        workspace_id="ws_demo",
        collection_id="col_demo",
        provider_mode="cloud",
        include_local_only=False,
    )
    with override_feature_flags(adaptive_work_memory=True), override_recall_records(records):
        result = recall_workspace_memory(request)
    assert all(item.privacy_classification == "cloud_allowed" and item.export_allowed for item in result.items)
    assert all(item.source_id != "mu_torque" for item in result.items)


def test_format_memory_prompt_block_does_not_duplicate_statement_and_respects_budget() -> None:
    """F6 Regression: Prompt block formatter must not insert statement twice or double budget consumption."""
    from aios_habit.workspace_memory_models import WorkspaceMemoryRecallItem, WorkspaceMemoryRecallResult
    from aios_habit.workspace_memory_service import format_memory_prompt_block

    long_statement = "A" * 3901
    item = WorkspaceMemoryRecallItem(
        memory_key="memory_unit:mu_long:v1",
        source_kind="memory_unit",
        source_id="mu_long",
        title="Bài học dài",
        statement=long_statement,
        applies_when="Mọi lúc",
        does_not_apply_when="",
        scope="workspace:ws_demo",
        status="verified",
        evidence_refs=("ev_1",),
        privacy_classification="local_only",
        export_allowed=False,
        updated_at="2026-09-12T00:00:00+00:00",
    )
    result = WorkspaceMemoryRecallResult(
        items=(item,),
        consent_fingerprint="fp_test",
    )
    block = format_memory_prompt_block(result)

    payload = block.split("<<<MEMORY_CONTENT\n", 1)[1].rsplit("\nMEMORY_CONTENT", 1)[0]
    assert long_statement.startswith(payload)
    assert len(block) <= 4000
    assert "<<<MEMORY_CONTENT" in block
    assert "MEMORY_CONTENT" in block


def test_unicode_nfd_normalization_in_fold_vi_and_tokenize() -> None:
    """Unicode NFD (decomposed) Vietnamese strings must fold and tokenize identically to NFC."""
    import unicodedata
    from aios_habit.workspace_memory_service import fold_vi, tokenize, content_digest

    text_nfc = "Kiểm tra mức dầu trước khi bật máy"
    text_nfd = unicodedata.normalize("NFD", text_nfc)
    assert text_nfc != text_nfd  # different byte representations

    assert fold_vi(text_nfc) == fold_vi(text_nfd)
    assert fold_vi(text_nfd) == "kiem tra muc dau truoc khi bat may"
    assert tokenize(text_nfc) == tokenize(text_nfd)
    assert "dau" in tokenize(text_nfd)
    assert "kiem" in tokenize(text_nfd)
    assert content_digest(text_nfc, "workspace:ws1") == content_digest(text_nfd, "workspace:ws1")
