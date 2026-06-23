from aios_habit.case_handover import build_handover_markdown
from aios_habit.case_models import Case, EvidenceItem


def test_internal_handover_keeps_local_source_pointer():
    case = Case(
        case_id="CASE-1",
        title="Synthetic handover",
        current_situation="Synthetic situation",
        next_actions=["Synthetic next check"],
        privacy_level="local_only",
    )
    evidence = EvidenceItem(
        evidence_id="EVID-1",
        case_id=case.case_id,
        source_type="document",
        source_path="docs/synthetic.pdf#SYNTHETIC-CHUNK-1",
        title="Synthetic source",
        privacy_level="local_only",
    )

    markdown = build_handover_markdown(case, [evidence], export_mode="local")

    assert "Nguồn tham chiếu" in markdown
    assert evidence.source_path in markdown
    assert "Synthetic next check" in markdown
    assert "Cảnh báo Bảo mật" in markdown


def test_external_handover_does_not_leak_local_source_pointer():
    case = Case(case_id="CASE-1", title="Synthetic handover", privacy_level="local_only")
    evidence = EvidenceItem(
        evidence_id="EVID-1",
        case_id=case.case_id,
        source_type="document",
        source_path="docs/private.pdf#PRIVATE-CHUNK",
        title="Private source",
        privacy_level="local_only",
    )

    for mode in ("redacted", "cloud_safe"):
        markdown = build_handover_markdown(case, [evidence], export_mode=mode)
        assert evidence.source_path not in markdown
