import pytest
from pathlib import Path
from aios_habit.case_models import Case, EvidenceItem
from aios_habit.case_actions import generate_next_actions
from aios_habit.case_ingest import ingest_csv

def test_case_model_creates_valid_case():
    c = Case(case_id="TEST-1", title="Test Case")
    assert c.case_id == "TEST-1"
    assert c.status == "open"
    assert c.privacy_level == "local_only"

def test_evidence_item_links_to_case():
    e = EvidenceItem(evidence_id="EVD-1", case_id="TEST-1", source_type="chat_paste", source_path="", title="Log")
    assert e.case_id == "TEST-1"

def test_csv_ingest_reads_synthetic_file(tmp_path):
    csv_file = tmp_path / "synthetic.csv"
    csv_file.write_text("col1,col2\nval1,val2", encoding="utf-8")
    ev = ingest_csv(str(csv_file), "TEST-1", "EVD-1", "synthetic.csv")
    assert ev.source_type == "csv"
    assert "col1" in ev.extracted_text

def test_next_action_generation():
    c = Case(case_id="TEST-1", title="Test Case")
    actions = generate_next_actions(c, [])
    assert "Thêm ít nhất một nguồn bằng chứng." in actions
    
    e = EvidenceItem(evidence_id="EVD-1", case_id="TEST-1", source_type="screenshot", source_path="", title="Img", extracted_text="")
    actions2 = generate_next_actions(c, [e])
    assert "Mô tả nội dung ảnh chụp màn hình." in actions2
