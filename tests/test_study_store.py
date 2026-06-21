import pytest
from unittest.mock import MagicMock
from aios_habit.study_store import (
    StudyCard,
    load_study_cards,
    save_study_card,
    save_study_cards,
    delete_study_card,
    create_cards_from_chunks,
    create_cards_from_study_pack_import
)
from aios_habit.notebook_index import SourceChunk

@pytest.fixture(autouse=True)
def setup_mock_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("aios_habit.study_store.LOCAL_CASES_DIR", tmp_path)
    monkeypatch.setattr("aios_habit.study_store.STUDY_CARDS_FILE", tmp_path / "study_cards.jsonl")

# 1. test_save_load_study_card
def test_save_load_study_card():
    card = StudyCard(
        card_id="CARD-1",
        notebook_id="NB-1",
        workspace_id="WS-1",
        front="Q1?",
        back="A1",
        source_ref="Doc 1",
        tags=["tag1"]
    )
    save_study_card(card)
    
    loaded = load_study_cards()
    assert len(loaded) == 1
    assert loaded[0].card_id == "CARD-1"
    assert loaded[0].front == "Q1?"
    assert loaded[0].back == "A1"
    assert loaded[0].tags == ["tag1"]

# 2. test_create_cards_from_chunks
def test_create_cards_from_chunks(monkeypatch):
    mock_chunks = [
        SourceChunk(
            chunk_id="CH-1",
            notebook_id="NB-1",
            source_id="SRC-1",
            chunk_index=0,
            text="This is a chunk text content.",
            keywords=["laser", "power", "mirror"],
            privacy_level="local_only",
            source_title="LSU Doc",
            original_filename="lsu.txt",
            created_at="2026-06-21T00:00:00"
        )
    ]
    monkeypatch.setattr("aios_habit.notebook_index.load_chunks", lambda nb_id: mock_chunks)
    
    created = create_cards_from_chunks("NB-1", "WS-1")
    assert len(created) == 1
    assert "Nguồn này nói gì về: laser, power, mirror?" in created[0].front
    assert created[0].back == "This is a chunk text content."
    assert created[0].source_ref == "LSU Doc / SRC-1"
    assert created[0].tags == ["laser", "power", "mirror"]

# 3. test_create_cards_from_study_pack_import
def test_create_cards_from_study_pack_import():
    from aios_habit.notebook_import_store import NotebookBridgeImport
    import_rec = NotebookBridgeImport(
        import_id="IMP-1",
        notebook_id="NB-1",
        workspace_id="WS-1",
        import_type="study_pack_json",
        title="Study Pack Test",
        raw_text="",
        parsed_json={
            "flashcards": [
                {"front": "Q1", "back": "A1", "source_ref": "Doc 1"},
                {"front": "", "back": "A2"},  # invalid, should be skipped
                {"front": "Q3", "back": "A3", "source_ref": "Doc 3"}
            ]
        },
        mermaid_text=""
    )
    
    created = create_cards_from_study_pack_import(import_rec, "WS-1")
    assert len(created) == 2
    assert created[0].front == "Q1"
    assert created[0].back == "A1"
    assert created[0].source_ref == "Doc 1"
    assert created[1].front == "Q3"
    assert created[1].back == "A3"

# 4. test_study_card_defaults_local_only_draft
def test_study_card_defaults_local_only_draft():
    card = StudyCard(
        card_id="CARD-1",
        notebook_id="NB-1",
        workspace_id="WS-1",
        front="Q",
        back="A",
        source_ref="Doc",
        tags=[]
    )
    save_study_card(card)
    
    loaded = load_study_cards()
    assert len(loaded) == 1
    assert loaded[0].privacy_level == "local_only"
    assert loaded[0].status == "draft"

# 5. test_delete_study_card_requires_existing
def test_delete_study_card_requires_existing():
    # Empty store, should return False
    res = delete_study_card("CARD-NONEXIST")
    assert res is False
    
    # Add a card
    card = StudyCard(
        card_id="CARD-1",
        notebook_id="NB-1",
        workspace_id="WS-1",
        front="Q",
        back="A",
        source_ref="Doc",
        tags=[]
    )
    save_study_card(card)
    
    # Delete existing, should return True
    res2 = delete_study_card("CARD-1")
    assert res2 is True
    assert len(load_study_cards()) == 0
