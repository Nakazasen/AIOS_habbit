import pytest
import pandas as pd
from pathlib import Path
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.case_prompt import build_prompt_pack, summarize_evidence_for_prompt
from aios_habit.case_audit import audit_case_cockpit_state
from aios_habit.case_graph import safe_mermaid_label, generate_case_mermaid
from aios_habit.case_ingest import safe_asset_filename, ingest_excel, save_uploaded_file

# 1. NotebookLM-safe prompt excludes local_only raw evidence
def test_notebooklm_safe_excludes_local_only():
    c = Case(case_id="C1", title="Test Case", current_situation="Situation Info")
    e1 = EvidenceItem(evidence_id="E1", case_id="C1", source_type="note", source_path="", title="Public Note", extracted_text="Public text content", privacy_level="cloud_allowed")
    e2 = EvidenceItem(evidence_id="E2", case_id="C1", source_type="note", source_path="", title="Private Note", extracted_text="Sensitive local text", privacy_level="local_only")
    
    prompt = build_prompt_pack(c, [e1, e2], "notebooklm_safe")
    assert "Sensitive local text" not in prompt
    assert "Public text content" in prompt
    assert "Một số bằng chứng local_only (chỉ lưu cục bộ) đã bị loại bỏ vì lý do riêng tư." in prompt

# 2. Gemini/GPT/Copilot prompt excludes local_only raw evidence by default
def test_cloud_targets_exclude_local_only_by_default():
    c = Case(case_id="C1", title="Test Case", current_situation="Situation Info")
    e1 = EvidenceItem(evidence_id="E1", case_id="C1", source_type="note", source_path="", title="Private Note", extracted_text="Sensitive local text", privacy_level="local_only")
    
    for target in ("gemini", "gpt", "copilot"):
        prompt = build_prompt_pack(c, [e1], target)
        assert "Sensitive local text" not in prompt
        assert "Một số bằng chứng local_only (chỉ lưu cục bộ) đã bị loại bỏ vì lý do riêng tư." in prompt

# 3. local_ai prompt can include local_only only when include_local_only=True
def test_local_ai_includes_local_only_only_when_requested():
    c = Case(case_id="C1", title="Test Case", current_situation="Situation Info")
    e1 = EvidenceItem(evidence_id="E1", case_id="C1", source_type="note", source_path="", title="Private Note", extracted_text="Sensitive local text", privacy_level="local_only")
    
    # False by default / explicitly False
    prompt_default = build_prompt_pack(c, [e1], "local_ai", include_local_only=False)
    assert "Sensitive local text" not in prompt_default
    assert "Một số bằng chứng local_only (chỉ lưu cục bộ) đã bị loại bỏ vì lý do riêng tư." in prompt_default
    
    # True explicitly
    prompt_explicit = build_prompt_pack(c, [e1], "local_ai", include_local_only=True)
    assert "Sensitive local text" in prompt_explicit
    assert "Một số bằng chứng local_only (chỉ lưu cục bộ) đã bị loại bỏ vì lý do riêng tư." not in prompt_explicit

# 4. Synthetic .xlsx ingest works using pandas/openpyxl
def test_xlsx_ingest_works(tmp_path):
    xlsx_path = tmp_path / "test_synthetic.xlsx"
    df = pd.DataFrame({"A": [1, 2], "B": ["X", "Y"]})
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Sheet1", index=False)
        
    ev = ingest_excel(str(xlsx_path), "C1", "E1", "test_synthetic.xlsx")
    assert ev.source_type == "excel"
    assert "Sheet1" in ev.extracted_text
    assert "A" in ev.extracted_text
    assert "B" in ev.extracted_text

# 5. Audit fails for active case with empty current_situation
def test_audit_fails_empty_situation():
    c = Case(case_id="C1", title="Test Title", current_situation="")
    result = audit_case_cockpit_state(c, [])
    assert result["status"] == "FAIL"
    assert any("tình huống bị trống" in err for err in result["errors"])

# 6. Audit passes for valid case + valid evidence
def test_audit_passes_valid():
    c = Case(case_id="C1", title="Valid Case Title", current_situation="System has been recovered.")
    e = EvidenceItem(
        evidence_id="E1",
        case_id="C1",
        source_type="csv",
        source_path="manual",
        title="Valid Evidence",
        extracted_text="Some text here"
    )
    result = audit_case_cockpit_state(c, [e])
    assert result["status"] == "PASS"
    assert len(result["errors"]) == 0

# 7. Case Map Mermaid generation escapes quotes/brackets/newlines/special chars
def test_mermaid_escaping():
    c = Case(
        case_id="C1",
        title='Case "A" [bad] {curly} | pipe \n newline',
        current_situation="Sit",
        hypotheses=['Hypo "B" [bracket] | \n'],
        next_actions=['Action "C" [bracket] | \n'],
        decisions=['Decision "D" [bracket] | \n']
    )
    e = EvidenceItem(
        evidence_id="E1",
        case_id="C1",
        source_type='csv [type]',
        source_path="manual",
        title='Evidence "E" [title] | \n',
        extracted_text="text"
    )
    
    mermaid = generate_case_mermaid(c, [e])
    
    # Assert that sensitive characters inside inner labels are properly escaped or replaced
    assert "[bad]" not in mermaid
    assert "(bad)" in mermaid
    
    assert "{curly}" not in mermaid
    assert "(curly)" in mermaid
    
    assert "pipe" in mermaid
    assert "- pipe" in mermaid
    
    assert "newline" in mermaid

# 8. Handover generation still works after helper extraction
def test_handover_generation_check():
    c = Case(case_id="C1", title="My Handover Title", current_situation="My Situation details", next_actions=["My next action"])
    e = EvidenceItem(evidence_id="E1", case_id="C1", source_type="note", source_path="manual", title="My Note Title")
    
    md = f"# Case Handover: {c.title}\n"
    md += f"**Status:** {c.status} | **Priority:** {c.priority}\n\n"
    md += f"## What Happened (Situation)\n{c.current_situation}\n\n"
    md += "## Evidence\n"
    md += f"- {e.title} ({e.source_type})\n"
    
    assert "# Case Handover: My Handover Title" in md
    assert "My Situation details" in md
    assert "My Note Title (note)" in md

# 9. Store round-trip for save_case/load_cases and save_evidence/load_evidence
def test_store_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.case_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.case_store.CASES_FILE", tmp_path / "cases.jsonl")
    monkeypatch.setattr("aios_habit.case_store.EVIDENCE_FILE", tmp_path / "evidence.jsonl")
    monkeypatch.setattr("aios_habit.case_store.ASSETS_DIR", tmp_path / "assets")
    
    from aios_habit.case_store import save_case, load_cases, save_evidence, load_evidence
    
    c = Case(case_id="T_CASE_1", title="Test Roundtrip")
    save_case(c)
    
    loaded_cases = load_cases()
    assert len(loaded_cases) == 1
    assert loaded_cases[0].case_id == "T_CASE_1"
    
    e = EvidenceItem(evidence_id="T_EVD_1", case_id="T_CASE_1", source_type="csv", source_path="", title="Test EVD")
    save_evidence(e)
    
    loaded_ev = load_evidence()
    assert len(loaded_ev) == 1
    assert loaded_ev[0].evidence_id == "T_EVD_1"

# 10. Supported launcher content contains the Workspace Chat entry
def test_workspace_chat_launcher_contents_check():
    bat_content = Path("RUN_AIOS_WORKSPACE_CHAT.bat").read_text(encoding="utf-8")
    ps1_content = Path("scripts/run_workspace_chat.ps1").read_text(encoding="utf-8")

    assert "streamlit run" in bat_content.lower()
    assert "workspace_chat_app.py" in bat_content
    assert "streamlit run" in ps1_content.lower()
    assert "workspace_chat_app.py" in ps1_content
# Bonus: Filename sanitization / collision handling tests
def test_safe_asset_filename():
    assert "secret" in safe_asset_filename("..\\secret.png")
    assert "secret.png" in safe_asset_filename("..\\secret.png")
    assert "c.png" in safe_asset_filename("a/b/c.png")
    
    fn1 = safe_asset_filename("file.csv")
    fn2 = safe_asset_filename("file.csv")
    assert fn1 != fn2  # Must be unique prefix
