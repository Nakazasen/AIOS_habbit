import pytest
from pathlib import Path
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.case_prompt import build_prompt_pack
from aios_habit.case_store import create_quick_case_with_evidence, load_cases, load_evidence

# 1. Case model supports current_situation and backward compatibility
def test_case_current_situation_field_and_backward_compatibility():
    # Test new case structure with situation
    c = Case(case_id="C_NEW", title="New Case", current_situation="This is the situation.")
    assert c.current_situation == "This is the situation."
    
    # Test backward compatibility (deserializing old dict representation lacking current_situation)
    old_data = {
        "case_id": "C_OLD",
        "title": "Old Case Title",
        "status": "open",
        "priority": "normal",
        "privacy_level": "local_only"
    }
    c_old = Case(**old_data)
    assert c_old.case_id == "C_OLD"
    assert c_old.title == "Old Case Title"
    assert c_old.current_situation == ""  # Defaults correctly

# 2. Quick intake helper saves case and evidence correctly
def test_create_quick_case_with_evidence_saving(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.case_store.CASES_FILE", tmp_path / "cases.jsonl")
    monkeypatch.setattr("aios_habit.case_store.EVIDENCE_FILE", tmp_path / "evidence.jsonl")
    monkeypatch.setattr("aios_habit.case_store.ASSETS_DIR", tmp_path / "assets")
    
    res = create_quick_case_with_evidence(
        title="Test Quick Intake Case",
        situation="System has anomaly at shipping queue",
        priority="high",
        privacy="local_only",
        chat_log="User: error mismatch\nAgent: checking",
        notes="A manual note was added",
        excel_csv_file_name="mock_data.csv",
        excel_csv_content_bytes=b"col1,col2\nval1,val2",
        img_file_name="mock_img.png",
        img_content_bytes=b"fake image data"
    )
    
    assert res["case_id"] is not None
    assert res["evidences_count"] == 4  # Chat log, manual note, CSV file, Image file
    
    # Load cases from store to verify persistence
    cases = load_cases()
    assert len(cases) == 1
    assert cases[0].case_id == res["case_id"]
    assert cases[0].title == "Test Quick Intake Case"
    assert cases[0].current_situation == "System has anomaly at shipping queue"
    assert cases[0].priority == "high"
    
    # Load evidence items from store to verify persistence
    evs = load_evidence()
    assert len(evs) == 4
    source_types = [e.source_type for e in evs]
    assert "chat_paste" in source_types
    assert "note" in source_types
    assert "csv" in source_types
    assert "screenshot" in source_types

# 3. Prompt pack and handover contain current situation
def test_prompt_pack_and_handover_contain_situation():
    c = Case(case_id="C1", title="My Title", current_situation="Underlying system failure")
    prompt = build_prompt_pack(c, [], "gemini", include_local_only=False)
    
    assert "Tình huống Hiện tại: Underlying system failure" in prompt
    
    # Test handover formatting containing situation
    md = f"# Bàn giao Hồ sơ Sự việc: {c.title}\n"
    md += f"## Tóm tắt Tình huống (Situation)\n{c.current_situation}\n\n"
    
    assert "# Bàn giao Hồ sơ Sự việc: My Title" in md
    assert "## Tóm tắt Tình huống (Situation)\nUnderlying system failure" in md
