from aios_habit.domain_playbooks import (
    GENERAL_PLAYBOOK,
    MANUFACTURING_PLAYBOOK,
    get_domain_playbook,
    select_domain_playbook,
)
from aios_habit.final_answer_composer import compose_final_owner_answer
from aios_habit.rag_evidence import build_evidence_pack
from aios_habit.rag_ingest import RAGChunk
from aios_habit.rag_search import create_rag_search_schema, index_rag_chunks, search_rag_chunks


def _pack(query):
    import sqlite3

    chunks = [
        RAGChunk(
            chunk_id="C1",
            document_id="D1",
            element_ids=["e1"],
            text="Application log shows timeout at 09:00.",
            source_title="runbook.pdf",
            source_path="runbook.pdf",
            relative_path="runbook.pdf",
            citation_label="p1",
            file_type="pdf",
            element_types=["text"],
            page_numbers=[1],
            sheet_names=[],
            slide_numbers=[],
            section_labels=[],
            row_ranges=[],
            cell_ranges=[],
            privacy_mode="local_only",
        )
    ]
    conn = sqlite3.connect(":memory:")
    try:
        create_rag_search_schema(conn)
        index_rag_chunks(conn, chunks)
        return build_evidence_pack(query, search_rag_chunks(conn, query, limit=5))
    finally:
        conn.close()


def test_default_domain_is_general():
    assert select_domain_playbook("What is the policy?") == GENERAL_PLAYBOOK


def test_manufacturing_playbook_only_activates_with_explicit_terms_and_allowance():
    assert select_domain_playbook("MOM WMS handoff", allow_domain_assist=False) == GENERAL_PLAYBOOK
    assert select_domain_playbook("MOM WMS handoff", allow_domain_assist=True) == MANUFACTURING_PLAYBOOK


def test_requested_manufacturing_playbook_requires_allowance():
    assert select_domain_playbook("general question", requested_playbook=MANUFACTURING_PLAYBOOK) == GENERAL_PLAYBOOK
    assert select_domain_playbook("general question", requested_playbook=MANUFACTURING_PLAYBOOK, allow_domain_assist=True) == MANUFACTURING_PLAYBOOK


def test_manufacturing_specific_action_text_absent_in_general_mode():
    answer = compose_final_owner_answer(_pack("general troubleshooting path"))
    text = answer.answer_text.lower()
    assert "interface records" not in text
    assert "mom" not in text
    assert "wms" not in text
    assert "agv" not in text


def test_manufacturing_specific_action_text_allowed_in_playbook_mode():
    answer = compose_final_owner_answer(
        _pack("MOM WMS AGV troubleshooting path"),
        domain_playbook=MANUFACTURING_PLAYBOOK,
        allow_domain_assist=True,
    )
    assert answer.metadata["domain_playbook"] == MANUFACTURING_PLAYBOOK
    assert "interface records" in answer.answer_text


def test_domain_playbook_cannot_override_missing_evidence():
    answer = compose_final_owner_answer(
        _pack("MOM WMS AGV troubleshooting path"),
        target_source_type="png",
        domain_playbook=MANUFACTURING_PLAYBOOK,
        allow_domain_assist=True,
    )
    assert answer.metadata["source_type_pass"] in {"FAIL", "PARTIAL"}
    assert answer.confidence_label == "low"
    assert "Missing target source types" in "\n".join(answer.warnings)


def test_known_playbook_can_be_loaded():
    playbook = get_domain_playbook(MANUFACTURING_PLAYBOOK)
    assert playbook.playbook_id == MANUFACTURING_PLAYBOOK
    assert playbook.action_reminders
